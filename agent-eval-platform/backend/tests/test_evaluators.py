"""评估引擎单元测试：规则指标 / 越界拒绝 / Mock Judge / 成本计算。"""
import pytest

from app.domains.evaluation.service import _rule_score, _clamp, run_evaluator
from app.domains.governance.budget import judge_cost, daily_key, JudgeBudget
from app import models
from app.core.config import settings


def make_ev(ev_type="rule", cfg=None):
    ev = models.Evaluator(workspace_id="ws-x", name="t", type=ev_type, config=cfg or {})
    return ev


def make_trace(tool_ok=1, tool_total=1, errs=0, payload=None):
    from types import SimpleNamespace
    steps = [{"kind": "tool", "status": "ok"}] * tool_ok
    steps += [{"kind": "tool", "status": "error"}] * (tool_total - tool_ok)
    steps += [{"kind": "llm", "status": "ok", "output": "回复内容"}] * max(0, errs)
    if payload is not None:
        return SimpleNamespace(payload=payload)
    return SimpleNamespace(payload={"turns": [{"role": "user", "message": "需求", "steps": steps}]})


def test_rule_tool_success():
    ev = make_ev(cfg={"tool_success": True})
    s = run_evaluator(ev, make_trace(2, 3))
    assert abs(s["score"] - 2 / 3) < 1e-3 and not s["failed"]


def test_rule_keywords_hit():
    ev = make_ev(cfg={"keywords": ["订单", "物流"]})
    tr = make_trace(payload={"turns": [{"message": "订单物流查询", "steps": [{"kind": "llm", "status": "ok"}]}]})
    s = run_evaluator(ev, tr)
    assert 0 <= s["score"] <= 1


def test_rule_no_error_penalty():
    ev = make_ev(cfg={"no_error": True})
    tr = make_trace(tool_ok=0, tool_total=2)  # 2 个出错工具
    s = run_evaluator(ev, tr)
    assert s["score"] < 1


def test_rule_schema_check():
    import json
    ev = make_ev(cfg={"schema": {"type": "object", "required": ["score"]}})
    tr = make_trace(payload={"turns": [{"message": "x", "steps": [{"kind": "llm", "status": "ok", "output": json.dumps({"score": 0.8})}]}]})
    assert run_evaluator(ev, tr)["score"] == 1.0
    bad = make_trace(payload={"turns": [{"message": "x", "steps": [{"kind": "llm", "status": "ok", "output": "{}"}]}]})
    assert run_evaluator(ev, bad)["score"] == 0.0


def test_clamp_out_of_range_rejected():
    with pytest.raises(Exception):
        _clamp(1.2)
    with pytest.raises(Exception):
        _clamp(-0.1)


def test_mock_judge_bounds():
    ev = make_ev("llm", {"judge_model": "x"})
    for _ in range(5):
        s = run_evaluator(ev, make_trace(2, 3), db=None)
        assert 0 <= s["score"] <= 1 and not s["failed"]


def test_judge_cost_calculation():
    assert judge_cost("deepseek-v4-flash", 1_000_000, 0) == 0.8
    assert judge_cost("unknown-model", 0, 1_000_000) == 2.0


def test_budget_record_and_exceed(db):
    b = JudgeBudget(db)
    assert not b.exceeded()
    b.record("deepseek-v4-flash", 1_000_000, 0)
    monkey = db.query(models.JudgeDailyStat).filter_by(day=daily_key()).first()
    assert monkey.calls == 1 and abs(monkey.cost - 0.8) < 1e-6
    # 人为抬高到超限
    monkey.cost = settings.judge_daily_limit_yuan
    db.commit()
    assert JudgeBudget(db).exceeded()
