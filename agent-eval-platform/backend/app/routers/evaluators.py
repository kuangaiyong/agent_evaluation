from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, Text
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas
from ..deps import current_workspace, require_write, audit
from ..services.evaluators import run_evaluator, quality_hint_of

router = APIRouter(prefix="/api/evaluators", tags=["evaluators"])

TYPE_LABEL = {"rule": "规则指标", "llm": "LLM-as-Judge", "agent": "Agent-as-Judge", "human": "人工反馈"}

def _json(ev: models.Evaluator, db):
    bound = (db.query(models.EvalTask)
                 .filter(func.cast(models.EvalTask.evaluator_ids, Text).like('%' + ev.id + '%')).count())
    return {"id": ev.id, "name": ev.name, "type": ev.type, "type_label": TYPE_LABEL.get(ev.type, ev.type),
            "preset": ev.preset, "version": ev.version, "status": ev.status, "config": ev.config,
            "bias_rate": ev.bias_rate, "bound_tasks": bound,
            "updated": ev.created_at.strftime("%Y-%m-%d")}

@router.get("")
def list_evs(ws=Depends(current_workspace), db: Session = Depends(get_db)):
    rows = db.query(models.Evaluator).filter_by(workspace_id=ws["id"]).order_by(models.Evaluator.created_at).all()
    return [_json(e, db) for e in rows]

@router.post("")
def create_ev(data: schemas.EvaluatorIn, ws=Depends(require_write), db: Session = Depends(get_db)):
    cfg = data.config or {}
    cfg.setdefault("judge_model", "qwen-max")
    cfg.setdefault("temperature", 0.1)
    e = models.Evaluator(workspace_id=ws["id"], name=data.name, type=data.type, config=cfg,
                         status="published" if data.status == "published" else "draft",
                         created_by="当前用户")
    db.add(e)
    db.flush()
    audit(db, ws["id"], "当前用户", "创建评估器", f"{e.name}（{TYPE_LABEL.get(e.type)}）")
    db.commit()
    return _json(e, db)

@router.post("/{eid}/trial")
def trial(eid: str, data: dict, ws=Depends(current_workspace), db: Session = Depends(get_db)):
    e = db.get(models.Evaluator, eid)
    if not e or e.workspace_id != ws["id"]:
        raise HTTPException(404, "评估器不存在")
    trace_ids = data.get("trace_ids", []) or ([] if data.get("trace_id") is None else [data["trace_id"]])
    out = []
    for tid in trace_ids:
        t = db.get(models.Trace, tid)
        if not t or t.workspace_id != ws["id"]:
            continue
        r = run_evaluator(e, t, quality_hint_of(t), db)
        out.append({"trace_id": tid, **r})
    return {"evaluator": _json(e, db), "results": out}

@router.post("/{eid}/publish")
def publish(eid: str, ws=Depends(require_write), db: Session = Depends(get_db)):
    e = db.get(models.Evaluator, eid)
    if not e or e.workspace_id != ws["id"]:
        raise HTTPException(404, "评估器不存在")
    v = int((e.version or "v1").replace("v", "") or 1)
    e.version = f"v{v + 1}"
    e.status = "published"
    db.add(models.AuditLog(workspace_id=ws["id"], actor="当前用户", action="发布评估器版本", obj=e.name))
    db.commit()
    return _json(e, db)

@router.post("/{eid}/set-status")
def set_status(eid: str, data: dict, ws=Depends(require_write), db: Session = Depends(get_db)):
    e = db.get(models.Evaluator, eid)
    if not e or e.workspace_id != ws["id"]:
        raise HTTPException(404, "评估器不存在")
    e.status = data.get("status", e.status)
    db.commit()
    return _json(e, db)
