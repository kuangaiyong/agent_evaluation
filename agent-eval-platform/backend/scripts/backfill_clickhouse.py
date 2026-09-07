"""存量数据回填：PG(控制面) → ClickHouse(事件层)。

用法（容器内）：
    docker exec agent-eval-platform-api-1 python scripts/backfill_clickhouse.py
"""
import sys

sys.path.insert(0, "/app")

from app.core.db import SessionLocal
from app import models
from app.pipeline.store.clickhouse_store import (_client, _trace_row, _score_rows,
                                           _bad_rows, enabled, ensure_schema)


def main() -> None:
    if not enabled():
        print("ClickHouse 未启用（CLICKHOUSE_ENABLED=false），跳过")
        return
    ensure_schema()
    db = SessionLocal()
    c = _client()
    apps = {a.id: a.name for a in db.query(models.App).all()}
    try:
        traces = db.query(models.Trace).all()
        for i, tr in enumerate(traces, 1):
            c.insert("traces_ch", [_trace_row(tr, apps.get(tr.app_id, ""))],
                     column_names=["trace_id", "workspace_id", "app_id", "app_name", "session_id",
                                   "model", "version", "status", "duration_ms", "tokens", "cost",
                                   "score_avg", "otel_trace_id", "created_at", "updated_at"])
            sr = _score_rows(db, tr.id)
            if sr:
                c.insert("score_records_ch", sr,
                         column_names=["score_id", "task_id", "evaluator_id", "trace_id", "score",
                                       "version", "failed", "created_at"])
            br = _bad_rows(db, tr.id)
            if br:
                c.insert("bad_cases_ch", br,
                         column_names=["bad_case_id", "workspace_id", "trace_id", "evaluator_id",
                                       "score", "threshold", "status", "created_at"])
            if i % 50 == 0:
                print(f"已回填 {i}/{len(traces)}")
        print(f"回填完成：traces={len(traces)}")
    finally:
        c.close()
        db.close()


if __name__ == "__main__":
    main()
