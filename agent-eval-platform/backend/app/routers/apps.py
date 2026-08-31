from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..db import get_db
from .. import models, schemas
from ..deps import current_workspace, require_write, audit
from ..security import gen_api_key

router = APIRouter(prefix="/api/apps", tags=["apps"])

def _app_json(a: models.App, db):
    traces24 = db.query(models.Trace).filter_by(app_id=a.id).count()
    scores = [t.score_avg for t in db.query(models.Trace).filter_by(app_id=a.id) if t.score_avg is not None]
    return {
        "id": a.id, "name": a.name, "type": a.type, "model": a.model, "version": a.version,
        "status": a.status, "api_key_masked": (a.api_key[:7] + "****" + a.api_key[-4:]) if a.api_key else "",
        "traces24h": traces24,
        "avg_score": round(sum(scores) / len(scores), 2) if scores else None,
        "last_report_at": a.last_report_at.strftime("%Y-%m-%d %H:%M") if a.last_report_at else "",
    }

@router.get("")
def list_apps(ws=Depends(current_workspace), db: Session = Depends(get_db)):
    apps = db.query(models.App).filter_by(workspace_id=ws["id"]).order_by(models.App.created_at).all()
    return [_app_json(a, db) for a in apps]

@router.post("")
def create_app(data: schemas.AppCreate, ws=Depends(require_write), req: Request = None, db: Session = Depends(get_db)):
    a = models.App(workspace_id=ws["id"], name=data.name, type=data.type, model=data.model,
                   api_key=gen_api_key())
    db.add(a)
    db.flush()
    db.add(models.AuditLog(workspace_id=ws["id"], actor="当前用户", action="创建 Agent 应用", obj=f"{a.name}（{a.id}）"))
    db.commit()
    return _app_json(a, db) | {"api_key_full": a.api_key} | {"endpoint": "http://<platform>/api/ingest/trace"}


@router.post("/{app_id}/update")
def update_app(app_id: str, data: dict, ws=Depends(require_write), db: Session = Depends(get_db)):
    """编辑应用配置：名称 / 类型 / 默认被测模型 / 版本号。"""
    a = db.get(models.App, app_id)
    if not a or a.workspace_id != ws["id"]:
        raise HTTPException(404, "应用不存在")
    changes = []
    for field, label in (("name", "名称"), ("type", "类型"), ("model", "默认被测模型"), ("version", "版本号")):
        if field in data and data[field] is not None:
            new = str(data[field]).strip()[:64]
            if getattr(a, field) != new:
                changes.append(label + ": " + (getattr(a, field) or "-") + " -> " + new)
                setattr(a, field, new)
    db.add(models.AuditLog(workspace_id=ws["id"], actor="当前用户",
                           action="更新应用配置", obj=f"{a.name}（" + "；".join(changes or ["无变化"]) + "）"))
    db.commit()
    return _app_json(a, db)

@router.post("/{app_id}/key")
def rotate_key(app_id: str, ws=Depends(require_write), db: Session = Depends(get_db)):
    a = db.get(models.App, app_id)
    if not a or a.workspace_id != ws["id"]:
        raise HTTPException(404, "应用不存在")
    a.api_key = gen_api_key()
    db.add(models.AuditLog(workspace_id=ws["id"], actor="当前用户", action="轮换 API Key", obj=a.name))
    db.commit()
    return {"api_key_full": a.api_key}

@router.post("/{app_id}/verify")
def verify(app_id: str, ws=Depends(current_workspace), db: Session = Depends(get_db)):
    """接入自检：模拟上报链路与清洗校验。"""
    a = db.get(models.App, app_id)
    if not a or a.workspace_id != ws["id"]:
        raise HTTPException(404, "应用不存在")
    db.query(models.Trace).filter_by(app_id=a.id).first()
    if a.status == "none":
        a.status = "reporting"
    elif a.status == "reporting":
        a.status = "connected"
    else:
        a.status = "connected"
    db.commit()
    return {"ok": True, "status": a.status}
