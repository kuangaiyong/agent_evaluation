"""仪表盘聚合查询。"""
import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from .. import models

def range_days(r: str) -> int:
    return {"7d": 7, "30d": 30, "90d": 90}.get(r, 7)

def dashboard(db: Session, ws_id: str, r: str = "7d", app_id: str = ""):
    days = range_days(r)
    from .clickhouse_store import dashboard_aggregates
    ch = dashboard_aggregates(db, ws_id, days, app_id)
    if ch is not None and ch["kpi"]["total"] > 0:
        return _dashboard_from_ch(ch, ws_id, db, days)
    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    tq = db.query(models.Trace).filter(models.Trace.workspace_id == ws_id, models.Trace.created_at >= since)
    if app_id:
        tq = tq.filter(models.Trace.app_id == app_id)
    traces = tq.all()
    scores = [t.score_avg for t in traces if t.score_avg is not None]
    apps = db.query(models.App).filter_by(workspace_id=ws_id).all()
    tasks = db.query(models.EvalTask).filter(models.EvalTask.workspace_id == ws_id,
                                             models.EvalTask.created_at >= since).count()
    pending = db.query(models.BadCase).filter_by(workspace_id=ws_id, status="pending").count()
    bias = db.query(func.avg(models.Evaluator.bias_rate)).filter_by(workspace_id=ws_id).scalar() or 0
    low_rate = round(sum(1 for s in scores if s < 0.6) / len(scores) * 100, 1) if scores else 0
    # 趋势（按日）
    trend = []
    for i in range(days):
        d0 = since + datetime.timedelta(days=i) - datetime.timedelta(hours=datetime.datetime.utcnow().hour % 24)
        day_scores = [t.score_avg for t in traces if t.created_at.strftime("%Y-%m-%d") == d0.strftime("%Y-%m-%d") and t.score_avg is not None]
        trend.append(round(sum(day_scores) / len(day_scores), 3) if day_scores else None)
    trend = [v if v is not None else (trend[i - 1] if i > 0 and trend[i - 1] else 0.7) for i, v in enumerate(trend)]
    ranking = []
    for a in apps:
        at = [t.score_avg for t in db.query(models.Trace).filter(models.Trace.app_id == a.id,
                                                                 models.Trace.created_at >= since) if t.score_avg is not None]
        if at:
            ranking.append({"app": a.name, "score": round(sum(at) / len(at), 3)})
    ranking.sort(key=lambda x: -x["score"])
    recent_bad = (db.query(models.BadCase)
                  .filter_by(workspace_id=ws_id)
                  .order_by(models.BadCase.created_at.desc()).limit(6).all())
    alerts = []
    err_tasks = db.query(models.EvalTask).filter_by(workspace_id=ws_id, status="error").all()
    inter_apps = [a for a in apps if a.status == "interrupted"]
    return {
        "kpi": {
            "apps": len(apps),
            "online_apps": sum(1 for a in apps if a.status == "connected"),
            "tasks": tasks,
            "score": round(sum(scores) / len(scores), 3) if scores else 0,
            "low_rate": low_rate,
            "pending_bad": pending,
            "bias": round(bias, 1),
        },
        "trend": trend,
        "ranking": ranking,
        "recent_bad": [
            {"id": b.id, "score": b.score, "threshold": b.threshold,
             "app": (db.get(models.Trace, b.trace_id).app_id if b.trace_id else "")}
            for b in recent_bad
        ],
        "alerts": {
            "error_tasks": [{"id": t.id, "name": t.name, "err_msg": t.err_msg} for t in err_tasks],
            "interrupted_apps": [{"id": a.id, "name": a.name} for a in inter_apps],
        },
    }


def _dashboard_from_ch(ch, ws_id: str, db: Session, days: int):
    """ClickHouse 聚合结果组装为仪表盘响应（KPI 其余字段仍取 PG 控制面）。"""
    apps = db.query(models.App).filter_by(workspace_id=ws_id).all()
    pending = db.query(models.BadCase).filter_by(workspace_id=ws_id, status="pending").count()
    bias = db.query(func.avg(models.Evaluator.bias_rate)).filter_by(workspace_id=ws_id).scalar() or 0
    tasks = db.query(models.EvalTask).filter(models.EvalTask.workspace_id == ws_id).count()
    trend = [v for _, v in ch["trend"]]
    if not trend:
        trend = [0.7] * days
    recent_bad = (db.query(models.BadCase).filter_by(workspace_id=ws_id)
                  .order_by(models.BadCase.created_at.desc()).limit(6).all())
    err_tasks = db.query(models.EvalTask).filter_by(workspace_id=ws_id, status="error").all()
    inter_apps = [a for a in apps if a.status == "interrupted"]
    return {
        "kpi": {
            "apps": len(apps), "online_apps": sum(1 for a in apps if a.status == "connected"),
            "tasks": tasks, "score": ch["kpi"]["avg_score"],
            "low_rate": ch["kpi"]["low_rate"], "pending_bad": pending, "bias": round(bias, 1),
        },
        "trend": trend,
        "ranking": [{"app": n, "score": s} for n, s in ch["ranking"]],
        "recent_bad": [{"id": b.id, "score": b.score, "threshold": b.threshold, "app": ""} for b in recent_bad],
        "alerts": {"error_tasks": [{"id": t.id, "name": t.name, "err_msg": t.err_msg} for t in err_tasks],
                   "interrupted_apps": [{"id": a.id, "name": a.name} for a in inter_apps]},
    }
