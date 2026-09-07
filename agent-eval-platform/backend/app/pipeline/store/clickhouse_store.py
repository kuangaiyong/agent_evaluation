"""ClickHouse 事件层：轨迹 / 评分 / Bad Case 事件表（双写 + TTL）。

- PG 继续承担控制面与在线查询（用户/应用/评估器/任务/数据集/复核流）；
- ClickHouse 承担事件与分析（仪表盘聚合、趋势、根因分析），热数据 30 天 TTL，
  评分与 Bad Case 事件保留 365 天（长周期统计）；
- 未启用时（CLICKHOUSE_ENABLED=false）自动退化为纯 PG（开发/单机模式）。
"""
import logging
import datetime

from sqlalchemy.orm import Session

from ...core.config import settings
from ... import models

log = logging.getLogger("agenteval.clickhouse")

DDL = [
    """CREATE TABLE IF NOT EXISTS traces_ch (
        trace_id      String,
        workspace_id  String,
        app_id        String,
        app_name      String,
        session_id    String,
        model         String,
        version       String,
        status        String,
        duration_ms   UInt64,
        tokens        UInt64,
        cost          Float64,
        score_avg     Nullable(Float64),
        otel_trace_id String,
        created_at    DateTime,
        updated_at    DateTime
    ) ENGINE = ReplacingMergeTree(updated_at)
    PARTITION BY toYYYYMMDD(created_at)
    ORDER BY (workspace_id, app_id, created_at)
    TTL created_at + INTERVAL 30 DAY DELETE""",
    """CREATE TABLE IF NOT EXISTS score_records_ch (
        score_id     UInt64,
        task_id      String,
        evaluator_id String,
        trace_id     String,
        score        Nullable(Float64),
        version      String,
        failed       UInt8,
        created_at   DateTime
    ) ENGINE = ReplacingMergeTree(created_at)
    PARTITION BY toYYYYMMDD(created_at)
    ORDER BY (task_id, trace_id, evaluator_id)
    TTL created_at + INTERVAL 365 DAY DELETE""",
    """CREATE TABLE IF NOT EXISTS bad_cases_ch (
        bad_case_id     String,
        workspace_id    String,
        trace_id        String,
        evaluator_id    String,
        score           Float64,
        threshold       Float64,
        status          String,
        created_at      DateTime
    ) ENGINE = ReplacingMergeTree(created_at)
    PARTITION BY toYYYYMMDD(created_at)
    ORDER BY (workspace_id, created_at)
    TTL created_at + INTERVAL 365 DAY DELETE""",
]


def enabled() -> bool:
    return bool(settings.clickhouse_enabled)


def _client():
    from clickhouse_connect import get_client
    return get_client(host=settings.clickhouse_host, port=settings.clickhouse_port,
                      username=settings.clickhouse_user, password=settings.clickhouse_password,
                      database=settings.clickhouse_db, connect_timeout=10)


def ensure_schema() -> None:
    if not enabled():
        return
    try:
        c = _client()
        for ddl in DDL:
            c.command(ddl)
        c.close()
        log.info("ClickHouse schema 已就绪（traces_ch / score_records_ch / bad_cases_ch，TTL 30d/365d）")
    except Exception as exc:
        log.warning("ClickHouse schema 初始化失败（继续 PG-only）：%s", exc)


# ---------- 行映射 ----------
def _trace_row(tr: models.Trace, app_name: str) -> list:
    return [tr.id, tr.workspace_id, tr.app_id, app_name, tr.session_id, tr.model or "",
            tr.version or "", tr.status, int(tr.duration_ms or 0), int(tr.tokens or 0),
            float(tr.cost or 0), tr.score_avg, tr.otel_trace_id or "",
            tr.created_at or datetime.datetime.utcnow(),
            datetime.datetime.utcnow(),]


def _score_rows(db: Session, trace_id: str) -> list:
    rows = db.query(models.ScoreRecord).filter_by(trace_id=trace_id).all()
    return [[r.id, r.task_id, r.evaluator_id, r.trace_id, r.score, r.version or "",
             int(bool(r.failed)), r.created_at or datetime.datetime.utcnow()]
            for r in rows]


def _bad_rows(db: Session, trace_id: str) -> list:
    rows = db.query(models.BadCase).filter_by(trace_id=trace_id).all()
    return [[b.id, b.workspace_id, b.trace_id, b.evaluator_id, float(b.score),
             float(b.threshold or 0), b.status,
             b.created_at or datetime.datetime.utcnow()]
            for b in rows]


# ---------- 写入 ----------
def write_trace_and_events(db: Session, trace: models.Trace, app_name: str = "") -> bool:
    """双写：轨迹 + 该轨迹的评分/Bad Case 事件 → ClickHouse。失败仅告警，不影响主链路。"""
    if not enabled():
        return False
    try:
        app_name = app_name or (db.get(models.App, trace.app_id).name if db.get(models.App, trace.app_id) else "")
        c = _client()
        c.insert("traces_ch", [_trace_row(trace, app_name)],
                 column_names=["trace_id", "workspace_id", "app_id", "app_name", "session_id",
                               "model", "version", "status", "duration_ms", "tokens", "cost",
                               "score_avg", "otel_trace_id", "created_at", "updated_at"])
        sr = _score_rows(db, trace.id)
        if sr:
            c.insert("score_records_ch", sr,
                     column_names=["score_id", "task_id", "evaluator_id", "trace_id", "score",
                                   "version", "failed", "created_at"])
        br = _bad_rows(db, trace.id)
        if br:
            c.insert("bad_cases_ch", br,
                     column_names=["bad_case_id", "workspace_id", "trace_id", "evaluator_id",
                                   "score", "threshold", "status", "created_at"])
        c.close()
        log.info("CH 双写完成 trace=%s（scores=%d, bad=%d）", trace.id, len(sr), len(br))
        return True
    except Exception as exc:
        log.warning("ClickHouse 双写失败（跳过）：%s", exc)
        return False


# ---------- 聚合（仪表盘 CH-first，失败回退 PG 由调用方处理） ----------
def dashboard_aggregates(db: Session, ws_id: str, days: int, app_id: str = ""):
    """返回 {kpi, trend, ranking} 或 None（未启用/无数据/异常时由调用方回退 PG）。"""
    if not enabled():
        return None
    since = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    # 注：ws_id/app_id 均为平台内部标识（白名单来源 DB），直接拼接安全；
    # clickhouse-connect 默认服务端绑定不支持 %(name)s 客户端占位符。
    cond = "workspace_id = '" + ws_id + "' AND created_at >= '" + since + "'"
    if app_id:
        cond += " AND app_id = '" + app_id + "'"
    try:
        c = _client()
        kpi = c.query("""
            SELECT count() AS total,
                   countIf(score_avg IS NOT NULL) AS scored,
                   avgIf(score_avg, score_avg IS NOT NULL) AS avg_score,
                   countIf(score_avg < 0.6) AS low_count
            FROM traces_ch WHERE """ + cond).result_rows[0]
        trend = c.query("""
            SELECT toDate(created_at) AS d, round(avgIf(score_avg, score_avg IS NOT NULL), 3) AS s
            FROM traces_ch WHERE """ + cond + " GROUP BY d ORDER BY d").result_rows
        ranking = c.query("""
            SELECT app_name AS app, round(avgIf(score_avg, score_avg IS NOT NULL), 3) AS s
            FROM traces_ch WHERE """ + cond + """ AND score_avg IS NOT NULL
            GROUP BY app_name ORDER BY s DESC""").result_rows
        c.close()
        return {
            "kpi": {
                "total": int(kpi[0]), "scored": int(kpi[1]),
                "avg_score": round(float(kpi[2]), 4) if kpi[2] is not None else 0,
                "low_rate": round(float(kpi[3]) / float(kpi[1]) * 100, 1) if kpi[1] else 0,
            },
            "trend": [[str(r[0]), round(float(r[1]), 3)] for r in trend],
            "ranking": [[r[0], round(float(r[1]), 3)] for r in ranking],
        }
    except Exception as exc:
        log.warning("ClickHouse 聚合查询失败（回退 PG）：%s", exc)
        return None
