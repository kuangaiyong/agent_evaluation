from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .db import get_db
from .security import parse_token
from . import models

def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    try:
        payload = parse_token(authorization[7:])
    except Exception:
        raise HTTPException(401, "登录已过期，请重新登录")
    user = db.get(models.User, payload["sub"])
    if not user:
        raise HTTPException(401, "用户不存在")
    return user

def current_workspace(user: models.User = Depends(current_user),
                      x_workspace: str = Header(default=""),
                      db: Session = Depends(get_db)):
    ws_id = x_workspace or user_default_ws(db, user)
    m = db.query(models.Membership).filter_by(user_id=user.id, workspace_id=ws_id).first()
    if not m:
        raise HTTPException(403, "无权访问该工作空间")
    return {"id": m.workspace_id, "role": m.role}

def user_default_ws(db, user):
    m = db.query(models.Membership).filter_by(user_id=user.id).first()
    if not m:
        raise HTTPException(403, "未加入任何工作空间")
    return m.workspace_id

def require_write(ws=Depends(current_workspace)):
    if ws["role"] not in ("admin", "dev"):
        raise HTTPException(403, "该操作需要开发权限")
    return ws

def require_admin(ws=Depends(current_workspace)):
    if ws["role"] != "admin":
        raise HTTPException(403, "该操作需要管理员权限")
    return ws

def audit(db, ws_id, actor, action, obj, result="成功", ip=""):
    db.add(models.AuditLog(workspace_id=ws_id, actor=actor, action=action, obj=obj, result=result, ip=ip))
