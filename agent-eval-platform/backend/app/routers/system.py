from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas
from ..deps import current_user, current_workspace, require_write, require_admin, audit
from ..security import hash_password

router = APIRouter(prefix="/api/system", tags=["system"])

@router.get("/workspaces")
def workspaces(user=Depends(current_user), db: Session = Depends(get_db)):
    rows = (db.query(models.Membership, models.Workspace)
            .join(models.Workspace, models.Workspace.id == models.Membership.workspace_id)
            .filter(models.Membership.user_id == user.id).all())
    return [{"id": w.id, "name": w.name, "env": w.env, "description": w.description,
             "role": m.role} for m, w in rows]

@router.get("/members")
def members(ws=Depends(current_workspace), db: Session = Depends(get_db)):
    rows = (db.query(models.Membership, models.User)
            .join(models.User, models.User.id == models.Membership.user_id)
            .filter(models.Membership.workspace_id == ws["id"]).all())
    return [{"id": u.id, "name": u.name, "email": u.email, "role": m.role} for m, u in rows]

@router.post("/members/invite")
def invite(data: schemas.InviteIn, ws=Depends(require_write), req: Request = None, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(email=data.email).first()
    if not user:
        user = models.User(email=data.email, name=data.name, role=data.role,
                           password_hash=hash_password("dev123"))
        db.add(user)
        db.flush()
    if not db.query(models.Membership).filter_by(user_id=user.id, workspace_id=ws["id"]).first():
        db.add(models.Membership(user_id=user.id, workspace_id=ws["id"], role=data.role))
    audit(db, ws["id"], "当前用户", "邀请成员", f"{data.email} → {data.role}")
    db.commit()
    return {"ok": True}

@router.get("/audits")
def audits(ws=Depends(current_workspace), db: Session = Depends(get_db), limit: int = 30):
    rows = (db.query(models.AuditLog).filter_by(workspace_id=ws["id"])
            .order_by(models.AuditLog.created_at.desc()).limit(limit).all())
    return [{"id": a.id, "actor": a.actor, "action": a.action, "obj": a.obj,
             "result": a.result, "ip": a.ip,
             "time": a.created_at.strftime("%Y-%m-%d %H:%M:%S")} for a in rows]

@router.get("/role-permissions")
def role_permissions():
    return {
        "admin": "全部操作权限",
        "dev": "接入 / 评估 / 复核",
        "ro": "仅查看（写操作提示需要开发权限）",
    }
