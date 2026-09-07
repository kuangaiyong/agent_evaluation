"""ClickHouse 事件层测试：行映射、DDL TTL、双写失败降级。"""
import datetime

import pytest

from app.pipeline.store.clickhouse_store import (_trace_row, _score_rows, _bad_rows,
                                           DDL, enabled, write_trace_and_events)
from app import models


def test_ddl_contains_ttl():
    joined = "\n".join(DDL)
    assert "INTERVAL 30 DAY DELETE" in joined      # 轨迹热数据 30 天
    assert "INTERVAL 365 DAY DELETE" in joined     # 评分/Bad Case 365 天
    assert "ReplacingMergeTree" in joined          # 幂等回填去重


def test_trace_row_mapping():
    tr = models.Trace(id="tr-1", workspace_id="ws-1", app_id="app-1", session_id="s-1",
                      model="m", version="v1", status="ok", duration_ms=1000, tokens=200,
                      cost=0.01, score_avg=0.8, otel_trace_id=None,
                      payload={"turns": []})
    tr.created_at = datetime.datetime(2026, 8, 24, 15, 0, 0)
    row = _trace_row(tr, "智能客服助手")
    assert row[0] == "tr-1" and row[3] == "智能客服助手" and row[10] == 0.01
    assert row[13] == datetime.datetime(2026, 8, 24, 15, 0, 0)   # DateTime 对象


def test_score_bad_rows_mapping(db):
    tr = models.Trace(id="tr-9", workspace_id="ws-1", app_id="app-1", session_id="s-9",
                      payload={"turns": []})
    db.add(tr)
    db.flush()
    db.add(models.ScoreRecord(task_id="task-1", evaluator_id="ev-1", trace_id="tr-9",
                              score=0.5, version="v2", meta={}))
    db.add(models.BadCase(workspace_id="ws-1", trace_id="tr-9", task_id="task-1",
                          evaluator_id="ev-1", score=0.5, threshold=0.6))
    db.commit()
    rows = _score_rows(db, "tr-9")
    assert rows and rows[0][1] == "task-1" and rows[0][4] == 0.5
    bad = _bad_rows(db, "tr-9")
    assert bad and bad[0][0].startswith("bc-")


def test_write_disabled_fallback(monkeypatch):
    monkeypatch.setattr("app.pipeline.store.clickhouse_store.settings", type("S", (), {"clickhouse_enabled": False})())
    # 未启用 → 不抛错且返回 False（主链路不受影响）
    assert write_trace_and_events(None, None) is False
