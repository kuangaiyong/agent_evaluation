from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ...core.db import get_db
from ... import models, schemas
from ..identity.deps import current_workspace, require_write, audit

router = APIRouter(prefix="/api/badcases", tags=["badcases"])

def _json(b: models.BadCase, db, with_detail: bool = False):
    tr = db.get(models.Trace, b.trace_id)
    ev = db.get(models.Evaluator, b.evaluator_id)
    t = db.get(models.EvalTask, b.task_id)
    app = db.get(models.App, tr.app_id) if tr else None
    out = {"id": b.id, "trace_id": b.trace_id, "app": app.name if app else "",
           "task": t.name if t else "", "evaluator": ev.name if ev else "",
           "score": b.score, "threshold": b.threshold, "status": b.status,
           "root_cause": b.root_cause,
           "time": b.created_at.strftime("%Y-%m-%d %H:%M:%S")}
    if with_detail:
        out["trace"] = tr.payload if tr else {}
        out["score_meta"] = (db.query(models.ScoreRecord)
                             .filter_by(trace_id=b.trace_id, evaluator_id=b.evaluator_id)
                             .order_by(models.ScoreRecord.id.desc()).first())
    return out

@router.get("")
def list_bad(ws=Depends(current_workspace), db: Session = Depends(get_db),
            status: str = "", evaluator: str = "", page: int = 1, size: int = 20):
    q = db.query(models.BadCase).filter_by(workspace_id=ws["id"])
    if status:
        q = q.filter_by(status=status)
    total = q.count()
    rows = q.order_by(models.BadCase.created_at.desc()).offset((page-1)*size).limit(size).all()
    items = [_json(b, db) for b in rows]
    stats = {
        "pending": db.query(models.BadCase).filter_by(workspace_id=ws["id"], status="pending").count(),
        "confirmed_7d": db.query(models.BadCase)
            .filter(models.BadCase.workspace_id == ws["id"], models.BadCase.status == "confirmed").count(),
        "misjudged_7d": db.query(models.BadCase)
            .filter(models.BadCase.workspace_id == ws["id"], models.BadCase.status == "misjudged").count(),
    }
    return {"total": total, "stats": stats, "items": items}

@router.get("/{bid}")
def detail(bid: str, ws=Depends(current_workspace), db: Session = Depends(get_db)):
    b = db.get(models.BadCase, bid)
    if not b or b.workspace_id != ws["id"]:
        raise HTTPException(404, "Bad Case 不存在")
    return _json(b, db, with_detail=True)

@router.post("/{bid}/review")
def review(bid: str, data: schemas.ReviewIn, user=Depends(current_workspace), db: Session = Depends(get_db)):
    from ..identity.deps import require_write
    ws = require_write(ws=user)
    b = db.get(models.BadCase, bid)
    if not b or b.workspace_id != ws["id"]:
        raise HTTPException(404, "Bad Case 不存在")
    if data.conclusion == "confirm":
        b.status = "confirmed"; b.root_cause = data.root_cause
    elif data.conclusion == "misjudge":
        b.status = "misjudged"; b.root_cause = data.root_cause or "误判·答案正确"
    else:
        b.status = "pending2"
    b.note = data.note
    import datetime
    b.reviewed_at = datetime.datetime.utcnow()
    audit(db, ws["id"], "当前用户", "提交复核结论", f"{b.id} → {b.status}")
    db.commit()
    return _json(b, db)

@router.post("/batch")
def batch_review(data: schemas.BatchReviewIn, user=Depends(current_workspace), db: Session = Depends(get_db)):
    from ..identity.deps import require_write
    ws = require_write(ws=user)
    n = 0
    for bid in data.ids:
        b = db.get(models.BadCase, bid)
        if not b or b.workspace_id != ws["id"]:
            continue
        if data.conclusion == "confirm":
            b.status = "confirmed"; b.root_cause = data.root_cause
        elif data.conclusion == "misjudge":
            b.status = "misjudged"; b.root_cause = "误判·批量"
        else:
            b.status = "pending2"
        n += 1
    audit(db, ws["id"], "当前用户", "批量复核", f"{n} 条 → {data.conclusion}")
    db.commit()
    return {"ok": True, "count": n}
