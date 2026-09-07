from fastapi import APIRouter, Depends, Request
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from ...core.db import get_db
from ... import models, schemas
from .deps import current_user, current_workspace, require_write, require_admin, audit
from ...core.security import hash_password
from ..governance.audit import HIGH_RISK_PATTERNS, is_high_risk

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
    # 账号来源由是否有本地口令推导，不额外存字段：接了组织身份源之后，
    # 那些用户没有本地口令，这里自然显示为组织账号。
    return [{"id": u.id, "name": u.name, "email": u.email, "role": m.role,
             "source": "本地账号" if u.password_hash else "组织账号",
             "joined_at": m.created_at.strftime("%Y-%m-%d") if m.created_at else "—"}
            for m, u in rows]

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
def audits(ws=Depends(current_workspace), db: Session = Depends(get_db), limit: int = 30,
           actor: str = "", high_risk: bool = False):
    """关键操作留痕。

    high_risk 由 action 在服务端判定（见 services/audit.is_high_risk），不放前端——
    规则散到前端会导致换个客户端就失效。
    """
    q = db.query(models.AuditLog).filter_by(workspace_id=ws["id"])
    if actor:
        q = q.filter(models.AuditLog.actor.like(f"%{actor}%"))
    if high_risk:
        # 必须下推成 SQL 条件再 limit。先 limit 后过滤会漏：最近 30 条里没有高风险、
        # 而更早的记录里有时，界面会显示「没有符合条件的记录」，但它们确实存在。
        q = q.filter(or_(*[and_(*[models.AuditLog.action.contains(k) for k in group])
                          for group in HIGH_RISK_PATTERNS]))
    rows = q.order_by(models.AuditLog.created_at.desc()).limit(limit).all()
    return [{"id": a.id, "actor": a.actor, "action": a.action, "obj": a.obj,
             "result": a.result, "ip": a.ip, "high_risk": is_high_risk(a.action),
             "time": a.created_at.strftime("%Y-%m-%d %H:%M:%S")} for a in rows]


@router.get("/audit-actors")
def audit_actors(ws=Depends(current_workspace), db: Session = Depends(get_db)):
    """筛选下拉的取值域，由实际数据决定而非前端写死。"""
    rows = db.query(models.AuditLog.actor).filter_by(workspace_id=ws["id"]).distinct().all()
    return sorted({a for (a,) in rows if a})

@router.get("/role-permissions")
def role_permissions():
    return {
        "admin": "全部操作权限",
        "dev": "接入 / 评估 / 复核",
        "ro": "仅查看（写操作提示需要开发权限）",
    }
