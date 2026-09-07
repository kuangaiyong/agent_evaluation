from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...core.db import get_db
from ... import models
from ..identity.deps import current_workspace

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("")
def list_notifs(ws=Depends(current_workspace), db: Session = Depends(get_db), type_: str = ""):
    q = db.query(models.Notification).filter_by(workspace_id=ws["id"])
    if type_:
        q = q.filter(models.Notification.type == type_)
    rows = q.order_by(models.Notification.created_at.desc()).limit(50).all()
    return [{"id": n.id, "type": n.type, "title": n.title, "body": n.body, "link": n.link,
             "unread": n.unread, "time": n.created_at.strftime("%Y-%m-%d %H:%M")} for n in rows]

@router.post("/{nid}/read")
def read(nid: str, ws=Depends(current_workspace), db: Session = Depends(get_db)):
    n = db.query(models.Notification).filter_by(id=nid, workspace_id=ws["id"]).first()
    if n:
        n.unread = False
        db.commit()
    return {"ok": True}

@router.post("/read-all")
def read_all(ws=Depends(current_workspace), db: Session = Depends(get_db)):
    db.query(models.Notification).filter_by(workspace_id=ws["id"]).update({"unread": False})
    db.commit()
    return {"ok": True}
