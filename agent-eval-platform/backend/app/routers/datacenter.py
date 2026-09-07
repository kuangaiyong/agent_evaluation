import json, csv, io, os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from ..db import get_db
from ..config import settings
from .. import models, schemas
from ..deps import current_workspace, require_write, audit

router = APIRouter(prefix="/api", tags=["datacenter"])

@router.get("/datasets")
def list_datasets(ws=Depends(current_workspace), db: Session = Depends(get_db)):
    rows = db.query(models.Dataset).filter_by(workspace_id=ws["id"]).all()
    out = []
    for d in rows:
        n = db.query(models.DatasetSample).filter_by(dataset_id=d.id).count()
        # 金标准完成度：未补录金标准的条目不参与门禁，所以这个比值要显式露出来
        gold = (db.query(models.DatasetSample)
                .filter(models.DatasetSample.dataset_id == d.id,
                        models.DatasetSample.gold.isnot(None),
                        models.DatasetSample.gold != "").count())
        out.append({"id": d.id, "name": d.name, "type": d.type, "version": d.version,
                    "samples": n, "gold": gold, "refs": d.refs or [],
                    "updated": d.updated_at.strftime("%Y-%m-%d")})
    return out

@router.post("/datasets")
def create_dataset(data: schemas.DatasetIn, ws=Depends(require_write), db: Session = Depends(get_db)):
    d = models.Dataset(workspace_id=ws["id"], name=data.name, type=data.type)
    db.add(d); db.flush()
    audit(db, ws["id"], "当前用户", "创建数据集", d.name)
    db.commit()
    return {"id": d.id, "name": d.name, "type": d.type, "version": d.version, "samples": 0}

@router.get("/datasets/{did}")
def dataset_detail(did: str, ws=Depends(current_workspace), db: Session = Depends(get_db)):
    d = db.get(models.Dataset, did)
    if not d or d.workspace_id != ws["id"]:
        raise HTTPException(404, "数据集不存在")
    samples = (db.query(models.DatasetSample, models.Trace)
               .join(models.Trace, models.Trace.session_id == models.DatasetSample.session_id)
               .filter(models.DatasetSample.dataset_id == did).all())
    rows = []
    seen = set()
    for s, tr in samples:
        if tr.id in seen:
            continue
        seen.add(tr.id)
        rows.append({"trace_id": tr.id, "session_id": tr.session_id, "app": tr.app_id,
                     "label": s.label, "score": tr.score_avg,
                     "time": tr.created_at.strftime("%Y-%m-%d")})
    return {"id": d.id, "name": d.name, "type": d.type, "version": d.version,
            "refs": d.refs or [], "samples": rows[:200]}

@router.post("/datasets/{did}/delete")
def delete_dataset(did: str, ws=Depends(require_write), db: Session = Depends(get_db)):
    d = db.get(models.Dataset, did)
    if not d or d.workspace_id != ws["id"]:
        raise HTTPException(404, "数据集不存在")
    if d.refs:
        raise HTTPException(409, f"数据集被引用：{'、'.join(d.refs)}，禁止删除")
    db.delete(d)
    db.query(models.DatasetSample).filter_by(dataset_id=did).delete()
    audit(db, ws["id"], "当前用户", "删除数据集", d.name)
    db.commit()
    return {"ok": True}

@router.post("/datasets/{did}/from-traces")
def from_traces(did: str, data: dict, ws=Depends(require_write), db: Session = Depends(get_db)):
    d = db.get(models.Dataset, did)
    if not d or d.workspace_id != ws["id"]:
        raise HTTPException(404, "数据集不存在")
    session_ids = [t.session_id for t in db.query(models.Trace)
                   .filter(models.Trace.id.in_(data.get("trace_ids", []))).all()]
    for sid in session_ids:
        if not db.query(models.DatasetSample).filter_by(dataset_id=did, session_id=sid).first():
            db.add(models.DatasetSample(dataset_id=did, session_id=sid,
                                        label=data.get("label", "轨迹导入")))
    v = int((d.version or "v1")[1:])
    d.version = f"v{v+1}"
    db.commit()
    return {"ok": True, "added": len(session_ids), "version": d.version}

@router.post("/datasets/{did}/upload")
async def upload(did: str, ws=Depends(require_write), file: UploadFile = File(...), db: Session = Depends(get_db)):
    d = db.get(models.Dataset, did)
    if not d or d.workspace_id != ws["id"]:
        raise HTTPException(404, "数据集不存在")
    raw = await file.read()
    if len(raw) > 100 * 1024 * 1024:
        raise HTTPException(400, "单文件 ≤ 100MB")
    errors, ok_rows, sid = [], 0, None
    try:
        if file.filename.endswith(".csv"):
            text = raw.decode("utf-8-sig")
            for i, line in enumerate(csv.DictReader(io.StringIO(text)), 1):
                if not line.get("session_id"):
                    errors.append(f"第 {i} 行 · session_id 字段缺失")
                    continue
                ok_rows += 1
                db.add(models.DatasetSample(dataset_id=did, session_id=line["session_id"],
                                            label=line.get("label", "")))
        else:
            payload = json.loads(raw.decode("utf-8"))
            items = payload if isinstance(payload, list) else payload.get("samples", [])
            for i, s in enumerate(items, 1):
                if not isinstance(s, dict) or not s.get("session_id"):
                    errors.append(f"第 {i} 条 · session_id 字段缺失（required）")
                    continue
                ok_rows += 1
                db.add(models.DatasetSample(dataset_id=did, session_id=s["session_id"],
                                            label=s.get("label", "")))
    except Exception as e:
        raise HTTPException(400, f"文件解析失败：{e}")
    v = int((d.version or "v1")[1:])
    d.version = f"v{v+1}"
    db.commit()
    return {"ok": True, "rows": ok_rows, "errors": errors[:20], "version": d.version}

@router.get("/trajectories")
def trajectories(ws=Depends(current_workspace), db: Session = Depends(get_db),
                 app_id: str = "", evaluated: str = "", page: int = 1, size: int = 20):
    q = db.query(models.Trace).filter_by(workspace_id=ws["id"])
    if app_id:
        q = q.filter_by(app_id=app_id)
    if evaluated:
        q = q.filter_by(evaluated=True)
    total = q.count()
    rows = q.order_by(models.Trace.created_at.desc()).offset((page-1)*size).limit(size).all()
    apps = {a.id: a.name for a in db.query(models.App).filter_by(workspace_id=ws["id"])}
    from ..services.assembler import count_steps
    return {"total": total, "items": [{
        "id": t.id, "session_id": t.session_id, "app": apps.get(t.app_id, t.app_id),
        "turn_count": count_steps(t.payload)[0], "tokens": t.tokens,
        "evaluated": t.evaluated, "score_avg": t.score_avg,
        "time": t.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    } for t in rows]}
