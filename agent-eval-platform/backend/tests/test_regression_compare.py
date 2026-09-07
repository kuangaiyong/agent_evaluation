"""回归对比的对齐与归因。

评审指出两个问题，这里各配一个用例：
1. base/comp 原按 trace_id 对齐，但两个版本是不同的 Trace 行、id 零交集，
   导致 comp 分恒 0、每行都被判成退化、「主要退化原因」恒空。应按 session_id 对齐。
2. 归因原取 comp 侧绝对分最低的评估器，会把「本来就低但没退化」的项报成元凶。
   应取 base→comp 跌幅最大的那个。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.core.db import Base
from app.domains.quality.api_regression import _run_regression


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    s = sessionmaker(bind=engine)()
    s.add_all([
        models.Workspace(id="ws-a", name="A"),
        models.App(id="app-1", workspace_id="ws-a", name="被测", type="AgentScope"),
        models.Dataset(id="ds-1", workspace_id="ws-a", name="回归集", type="回归集"),
    ])
    for i in range(3):
        s.add(models.DatasetSample(dataset_id="ds-1", session_id=f"se-{i}"))
    s.commit()
    yield s
    s.close()
    engine.dispose()


def _trace(session_id, version, tool_ok):
    """工具成功率评估器只看 steps 的 status，用它构造可控的分差。"""
    return models.Trace(
        workspace_id="ws-a", app_id="app-1", session_id=session_id, version=version,
        payload={"turns": [{"role": "user", "message": "x", "steps": [
            {"kind": "tool", "status": "ok" if tool_ok else "error"}]}]})


def test_versions_align_by_session_not_trace_id(db):
    """两版对同一批 session 各有一条 Trace，trace id 不同，仍必须能对上。"""
    for i in range(3):
        db.add(_trace(f"se-{i}", "v1", True))
        db.add(_trace(f"se-{i}", "v2", True))   # 两版表现一致 → 不应判为退化
    db.add(models.Evaluator(id="ev-1", workspace_id="ws-a", name="工具成功率",
                            type="rule", status="published", config={"tool_success": True}))
    db.commit()

    run = _run_regression(db, "ws-a", "对齐验证", "ds-1", "app-1", "v1", "v2")
    rep = run.report
    assert len(rep["rows"]) == 3, "按 session 对齐后每条会话都应出现在报告里"
    assert rep["comp_score"] > 0, "comp 分不应恒为 0（trace_id 对齐时的症状）"
    assert rep["degraded"] == 0, "两版表现一致时不应判为退化"
    assert all(abs(r["delta"]) < 1e-6 for r in rep["rows"])


def test_degradation_reason_names_the_evaluator_that_dropped_most(db):
    """归因要指向跌得最狠的评估器，而不是绝对分最低的那个。

    构造：会话 se-0 在 v2 工具失败 → 「工具成功率」从 1.0 掉到 0.0（跌 1.0）；
    「常低分项」两版都是同一个低分（没跌）。元凶应是前者。
    """
    db.add(_trace("se-0", "v1", True))
    db.add(_trace("se-0", "v2", False))
    db.add_all([
        models.Evaluator(id="ev-1", workspace_id="ws-a", name="工具成功率",
                         type="rule", status="published", config={"tool_success": True}),
        # 关键词评估器在两版上给出相同的低分，属于「本来就低但没退化」
        models.Evaluator(id="ev-2", workspace_id="ws-a", name="常低分项",
                         type="rule", status="published", config={"keywords": ["永不命中的词"]}),
    ])
    db.commit()

    run = _run_regression(db, "ws-a", "归因验证", "ds-1", "app-1", "v1", "v2")
    row = next(r for r in run.report["rows"] if r["delta"] < 0)
    assert row["reason"] == "工具成功率", f"归因指错了：{row['reason']}"


def test_reason_is_blank_when_not_degraded(db):
    """没退化的行不给原因——否则报告里全是噪声。"""
    db.add(_trace("se-0", "v1", True))
    db.add(_trace("se-0", "v2", True))
    db.add(models.Evaluator(id="ev-1", workspace_id="ws-a", name="工具成功率",
                            type="rule", status="published", config={"tool_success": True}))
    db.commit()

    run = _run_regression(db, "ws-a", "噪声验证", "ds-1", "app-1", "v1", "v2")
    assert all(r["reason"] == "" for r in run.report["rows"])
