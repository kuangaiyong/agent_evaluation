from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas
from ..deps import current_workspace, require_write, audit
from ..services.worker import offline_batch
from ..services.evaluators import run_evaluator, quality_hint_of

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

def _json(t: models.EvalTask, db):
    evs = [db.get(models.Evaluator, e) for e in (t.evaluator_ids or [])]
    app = db.get(models.App, t.app_id) if t.app_id else None
    ds = db.get(models.Dataset, t.dataset_id) if t.dataset_id else None
    return {"id": t.id, "name": t.name, "mode": t.mode, "status": t.status,
            "app": app.name if app else "", "dataset": ds.name if ds else "",
            "evaluators": [{"id": e.id, "name": e.name} for e in evs if e],
            "sample_rate": t.sample_rate, "threshold": t.threshold, "stats": t.stats or {},
            "err_msg": t.err_msg, "created_at": t.created_at.strftime("%Y-%m-%d"),
            "updated_at": t.updated_at.strftime("%Y-%m-%d %H:%M")}

@router.get("")
def list_tasks(ws=Depends(current_workspace), db: Session = Depends(get_db), mode: str = ""):
    q = db.query(models.EvalTask).filter_by(workspace_id=ws["id"])
    if mode:
        q = q.filter_by(mode=mode)
    return [_json(t, db) for t in q.order_by(models.EvalTask.created_at.desc()).all()]

@router.post("")
def create_task(data: schemas.TaskIn, ws=Depends(require_write), db: Session = Depends(get_db)):
    t = models.EvalTask(workspace_id=ws["id"], name=data.name, mode=data.mode, app_id=data.app_id,
                        dataset_id=data.dataset_id, version_filter=data.version_filter,
                        evaluator_ids=data.evaluator_ids, sample_rate=data.sample_rate,
                        threshold=data.threshold, status="created")
    db.add(t)
    db.flush()
    audit(db, ws["id"], "当前用户", "创建评估任务", t.name)
    db.commit()
    return _json(t, db)

@router.get("/{tid}")
def detail(tid: str, ws=Depends(current_workspace), db: Session = Depends(get_db)):
    t = db.get(models.EvalTask, tid)
    if not t or t.workspace_id != ws["id"]:
        raise HTTPException(404, "任务不存在")
    return _json(t, db)

@router.post("/{tid}/update")
def update_task(tid: str, data: dict, ws=Depends(require_write), db: Session = Depends(get_db)):
    t = db.get(models.EvalTask, tid)
    if not t or t.workspace_id != ws["id"]:
        raise HTTPException(404, "任务不存在")
    if "evaluator_ids" in data and isinstance(data["evaluator_ids"], list):
        t.evaluator_ids = data["evaluator_ids"]
    if "threshold" in data:
        t.threshold = float(data["threshold"])
    if "sample_rate" in data:
        t.sample_rate = int(data["sample_rate"])
    audit(db, ws["id"], "当前用户", "更新评估任务配置", t.name)
    db.commit()
    return _json(t, db)


@router.post("/{tid}/action")
def action(tid: str, data: dict, background: BackgroundTasks = None,
           ws=Depends(require_write), db: Session = Depends(get_db)):
    t = db.get(models.EvalTask, tid)
    if not t or t.workspace_id != ws["id"]:
        raise HTTPException(404, "任务不存在")
    act = data.get("action", "")
    if act == "start":
        if t.mode == "online":
            t.status = "running"
            audit(db, ws["id"], "当前用户", "启动评估任务", t.name)
            db.commit()
            return _json(t, db)
        # 离线：响应后后台执行批次
        background.add_task(offline_batch, t.id)
        t.status = "running"
        db.commit()
        return _json(t, db)
    if act == "pause" and t.status == "running":
        t.status = "paused"
    elif act == "resume" and t.status in ("paused", "error", "created"):
        t.status = "running"
        if t.mode == "offline":
            background.add_task(offline_batch, t.id)
    elif act == "terminate":
        t.status = "terminated"
    audit(db, ws["id"], "当前用户", f"任务状态变更：{act}", t.name)
    db.commit()
    return _json(t, db)

@router.get("/{tid}/results")
def results(tid: str, ws=Depends(current_workspace), db: Session = Depends(get_db), limit: int = 20):
    t = db.get(models.EvalTask, tid)
    if not t or t.workspace_id != ws["id"]:
        raise HTTPException(404, "任务不存在")
    rows = (db.query(models.ScoreRecord, models.Trace, models.Evaluator)
            .join(models.Trace, models.Trace.id == models.ScoreRecord.trace_id)
            .join(models.Evaluator, models.Evaluator.id == models.ScoreRecord.evaluator_id)
            .filter(models.ScoreRecord.task_id == t.id)
            .order_by(models.ScoreRecord.id.desc()).limit(limit).all())
    return [{"trace_id": s.trace_id, "evaluator": e.name, "score": s.score, "version": s.version,
             "failed": s.failed, "meta": s.meta,
             "time": s.created_at.strftime("%H:%M:%S")} for s, tr, e in rows]
