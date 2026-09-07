"""指标字典解析与同步测试。

解析部分直接跑仓库里真实的 01 分册，不用样例文本——格式一旦被改动，这些测试要能立刻报警。
"""
import pathlib

import pytest

from app import models
from app.domains.evaluation.metric_dict import parse_dictionary, sync_metrics, coverage

DOC = (pathlib.Path(__file__).resolve().parents[3]
       / "智能体评测体系" / "01-指标体系与指标字典.md")

# 跨册同步的基线：改指标必须同步改这里（见仓库 CLAUDE.md）
EXPECTED_TOTAL = 92
EXPECTED_GROUPS = 12

needs_doc = pytest.mark.skipif(not DOC.exists(), reason=f"指标字典不在预期路径：{DOC}")


@pytest.fixture(scope="module")
def rows():
    if not DOC.exists():
        pytest.skip(f"指标字典不在预期路径：{DOC}")
    return parse_dictionary(DOC.read_text(encoding="utf-8"))


@needs_doc
def test_parses_expected_count(rows):
    assert len(rows) == EXPECTED_TOTAL
    assert len({r["group_code"] for r in rows}) == EXPECTED_GROUPS


@needs_doc
def test_codes_unique_and_well_formed(rows):
    codes = [r["code"] for r in rows]
    assert len(set(codes)) == len(codes), "指标编号有重复"
    for c in codes:
        g, _, seq = c.partition("-")
        assert g.isupper() and len(g) == 1 and seq.isdigit() and len(seq) == 2, c


@needs_doc
def test_every_metric_has_core_fields(rows):
    for r in rows:
        assert r["name"], f"{r['code']} 缺名称"
        assert r["layer"], f"{r['code']} 缺层"
        assert r["pillar"], f"{r['code']} 缺柱"
        assert r["definition"], f"{r['code']} 缺定义"
        assert r["group_name"], f"{r['code']} 没归到任何组"


@needs_doc
def test_layer_values_are_known(rows):
    assert {r["layer"] for r in rows} <= {"L1", "L2", "L3", "L4", "L5", "元"}


@needs_doc
def test_dual_pillar_splits_on_first_separator(rows):
    """`L3 · 记忆 · 环境与交互` 这种双柱条目，只能在第一个分隔符上切。"""
    dual = [r for r in rows if " · " in r["pillar"]]
    assert dual, "文档里应至少有一条双柱指标（回归保护）"
    for r in dual:
        assert r["layer"].startswith("L"), r
        assert not r["pillar"].startswith("L"), r


@needs_doc
def test_no_labelled_bullet_is_dropped(rows):
    """核心不变量：文档里每一条 `- **标签**：正文` 都必须落进某个字段。

    最早的解析器把标签写死成五项，结果 `陷阱一`/`陷阱二`、`实测量级` 这些变体被静默丢弃，
    而它们恰恰带着 arXiv 出处。这条断言就是防它复发。
    """
    import re
    text = DOC.read_text(encoding="utf-8").replace("\r\n", "\n")
    heads = list(re.finditer(r"^\*\*([A-Z]-\d{2})\s·\s.+?\*\*\s*｜", text, re.M))
    by_code = {r["code"]: r for r in rows}

    for i, h in enumerate(heads):
        body = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        body = re.split(r"^#{2,4}\s", body, maxsplit=1, flags=re.M)[0]
        labels = re.findall(r"^-\s+\*\*(.+?)\*\*\s*[：:]", body, re.M)
        captured = "\n".join(by_code[h.group(1)][c] for c in
                             ("definition", "formula", "collection", "pitfall", "threshold", "notes"))
        assert len(labels) == len([ln for ln in captured.split("\n") if ln.strip()]), \
            f"{h.group(1)} 有 {len(labels)} 条正文，只捕获到 {len(captured.splitlines())} 条：{labels}"


@needs_doc
def test_numbered_pitfall_variants_merge(rows):
    """C-07 写的是「陷阱一 / 陷阱二」，两段都得进 pitfall，不能只留一段。"""
    c07 = next(r for r in rows if r["code"] == "C-07")
    assert c07["pitfall"].count("\n") >= 1, "陷阱一/陷阱二 应合并成多行"
    assert "利用" in c07["pitfall"] and "全上下文" in c07["pitfall"]


@needs_doc
def test_unknown_labels_land_in_notes_with_label(rows):
    """`实测量级` 这类未登记标签进 notes，且保留标签名——否则读的人不知道这段是什么。"""
    c08 = next(r for r in rows if r["code"] == "C-08")
    assert c08["notes"].startswith("实测量级："), c08["notes"][:40]
    assert "arXiv:2605.27141" in c08["notes"], "带出处的实测数字不能丢"


@needs_doc
def test_collection_present_for_every_metric(rows):
    """C-08 曾经缺「采集」，补上后 92 条应全有——缺了说明文档又漏了。"""
    missing = [r["code"] for r in rows if not r["collection"]]
    assert not missing, f"这些指标缺「采集」：{missing}"


@needs_doc
def test_gate_metrics_carry_threshold(rows):
    """L-01 / L-02 是平台门禁指标，阈值必须解析出来。"""
    by_code = {r["code"]: r for r in rows}
    assert "90%" in by_code["L-01"]["threshold"], by_code["L-01"]["threshold"]
    assert "0.7" in by_code["L-02"]["threshold"], by_code["L-02"]["threshold"]


def test_missing_pillar_separator_yields_empty_pillar():
    """格式漂移时 pillar 必须留空让上层报出来，不能兜底成 layer 假装数据正常。"""
    doc = "### A 组 · 效果与完成度\n\n**A-01 · 只有层没有柱** ｜ L2\n\n- **定义**：x\n"
    (row,) = parse_dictionary(doc)
    assert row["layer"] == "L2"
    assert row["pillar"] == "", "缺分隔符时不能把 layer 当 pillar 兜底"


def test_sync_inserts_then_is_idempotent(db, rows):
    first = sync_metrics(db, rows)
    assert first["added"] == len(rows) and first["updated"] == 0
    assert db.query(models.Metric).count() == len(rows)

    second = sync_metrics(db, rows)
    assert second == {"added": 0, "updated": 0, "unchanged": len(rows), "stale": []}


def test_sync_updates_only_changed_row(db, rows):
    sync_metrics(db, rows)
    target = db.get(models.Metric, rows[0]["code"])
    target.definition = "被人手改过的旧值"
    db.commit()

    stat = sync_metrics(db, rows)
    assert stat["updated"] == 1 and stat["unchanged"] == len(rows) - 1
    assert db.get(models.Metric, rows[0]["code"]).definition == rows[0]["definition"]


def test_sync_reports_stale_without_deleting(db, rows):
    sync_metrics(db, rows)
    db.add(models.Metric(code="Z-99", group_code="Z", group_name="已下线组", name="旧指标",
                         layer="L2", pillar="工具"))
    db.commit()

    stat = sync_metrics(db, rows)
    assert stat["stale"] == ["Z-99"]
    assert db.get(models.Metric, "Z-99") is not None, "stale 指标不能被静默删除"


def test_coverage_counts_only_mapped_evaluators(db, rows):
    sync_metrics(db, rows)
    before = coverage(db)
    assert before["total"] == len(rows) and before["done"] == 0

    db.add(models.Evaluator(workspace_id="ws-x", name="任务完成度", type="llm",
                            metric_code="C-03"))
    db.add(models.Evaluator(workspace_id="ws-x", name="未挂靠的评估器", type="rule"))
    db.commit()

    after = coverage(db)
    assert after["done"] == 1, "只有挂了 metric_code 的评估器才算覆盖"
    c03 = db.get(models.Metric, "C-03")
    cell = next(c for c in after["cells"] if c["layer"] == c03.layer and c["pillar"] == c03.pillar)
    assert cell["done"] == 1 and cell["total"] >= 1


def test_coverage_cells_sum_to_total(db, rows):
    sync_metrics(db, rows)
    cov = coverage(db)
    assert sum(c["total"] for c in cov["cells"]) == cov["total"] == len(rows)
