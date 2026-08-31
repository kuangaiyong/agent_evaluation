from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models
from ..deps import current_workspace
from ..services.assembler import count_steps

router = APIRouter(prefix="/api", tags=["observability"])

@router.get("/traces")
def list_traces(ws=Depends(current_workspace), db: Session = Depends(get_db),
                app_id: str = "", status: str = "", session_id: str = "", page: int = 1, size: int = 20):
    q = db.query(models.Trace).filter_by(workspace_id=ws["id"])
    if app_id:
        q = q.filter_by(app_id=app_id)
    if status:
        q = q.filter_by(status=status)
    if session_id:
        q = q.filter(models.Trace.session_id.contains(session_id))
    total = q.count()
    rows = q.order_by(models.Trace.created_at.desc()).offset((page - 1) * size).limit(size).all()
    apps = {a.id: a.name for a in db.query(models.App).filter_by(workspace_id=ws["id"])}
    return {"total": total, "items": [{
        "id": t.id, "session_id": t.session_id, "app": apps.get(t.app_id, t.app_id),
        "app_id": t.app_id, "model": t.model, "version": t.version, "status": t.status,
        "duration_ms": t.duration_ms, "tokens": t.tokens, "score_avg": t.score_avg,
        "evaluated": t.evaluated, "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for t in rows]}

@router.get("/traces/{trace_id}")
def trace_detail(trace_id: str, ws=Depends(current_workspace), db: Session = Depends(get_db)):
    t = db.get(models.Trace, trace_id)
    if not t or t.workspace_id != ws["id"]:
        raise HTTPException(404, "轨迹不存在")
    turns, steps = count_steps(t.payload)
    scores = db.query(models.ScoreRecord).filter_by(trace_id=t.id).all()
    app = db.get(models.App, t.app_id)
    return {
        "id": t.id, "session_id": t.session_id, "app": app.name if app else "", "app_id": t.app_id,
        "model": t.model, "version": t.version, "status": t.status,
        "duration_ms": t.duration_ms, "tokens": t.tokens, "cost": t.cost,
        "turns": turns, "steps": steps, "payload": t.payload,
        "score_avg": t.score_avg, "evaluated": t.evaluated,
        "created_at": t.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "scores": [{"evaluator_id": s.evaluator_id, "score": s.score, "version": s.version,
                    "failed": s.failed, "meta": s.meta,
                    "time": s.created_at.strftime("%Y-%m-%d %H:%M:%S")} for s in scores],
    }

@router.get("/sessions/{session_id}/replay")
def session_replay(session_id: str, ws=Depends(current_workspace), db: Session = Depends(get_db)):
    rows = (db.query(models.Trace).filter_by(workspace_id=ws["id"], session_id=session_id)
            .order_by(models.Trace.created_at).all())
    return {"session_id": session_id, "traces": [{
        "id": t.id, "version": t.version, "status": t.status, "score_avg": t.score_avg,
        "turns": t.payload.get("turns", []), "created_at": t.created_at.strftime("%H:%M:%S"),
    } for t in rows]}
