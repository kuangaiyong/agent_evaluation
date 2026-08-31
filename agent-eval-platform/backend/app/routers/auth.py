from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas
from ..security import verify_password, make_token
from ..deps import current_user, user_default_ws

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
def login(data: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(email=data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "账号或密码错误")
    ws_id = user_default_ws(db, user)
    m = db.query(models.Membership).filter_by(user_id=user.id, workspace_id=ws_id).first()
    return {
        "token": make_token(user.id, user.role, ws_id),
        "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role},
        "workspace": {"id": ws_id, "role_in_ws": m.role},
    }

@router.get("/me")
def me(user=Depends(current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}
