"""公开摄入端点：SDK/HTTP 直推，X-Api-Key 鉴权，进入轨迹组装。"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from ...core.db import get_db
from ... import models, schemas
from .assembler import assemble_trace
from ..eval_runner.worker import eval_trace_on_tasks
from ..store.clickhouse_store import write_trace_and_events

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

def _app_by_key(db: Session, key: str):
    if not key:
        raise HTTPException(401, "缺少 x-api-key")
    return db.query(models.App).filter_by(api_key=key).first() or (lambda: (_ for _ in ()).throw(HTTPException(401, "API Key 无效")))()

@router.post("/trace")
def ingest_trace(data: schemas.IngestTrace, x_api_key: str = Header(default=""), db: Session = Depends(get_db)):
    app = _app_by_key(db, x_api_key)
    trace = assemble_trace(db, app, data.model_dump())
    tasks = db.query(models.EvalTask).filter_by(mode="online", status="running",
                                                workspace_id=app.workspace_id).all()
    eval_trace_on_tasks(db, tasks, trace)
    write_trace_and_events(db, trace, app.name)
    return {"trace_id": trace.id, "session_id": trace.session_id, "evaluated": trace.evaluated,
            "score_avg": trace.score_avg}

@router.post("/plain")
def ingest_plain(payload: dict, x_api_key: str = Header(default=""), db: Session = Depends(get_db)):
    """极简接入：{session_id, user, assistant} → 自动生成单 Turn 结构。"""
    app = _app_by_key(db, x_api_key)
    data = {
        "session_id": payload.get("session_id", ""),
        "model": payload.get("model", app.model),
        "version": payload.get("version", app.version),
        "turns": [{
            "role": "user", "message": payload.get("user", ""),
            "steps": [
                {"kind": "llm", "name": "LLM · 推理", "status": "ok", "duration_ms": 600, "tokens": 300,
                 "input": {"user_msg": payload.get("user")} , "output": payload.get("assistant", "")},
            ],
        }],
    }
    return ingest_trace(schemas.IngestTrace(**data), x_api_key, db)
