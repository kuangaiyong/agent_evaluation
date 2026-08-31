"""指标库（只读）。

字典的权威源是文档，写入只走 `scripts/sync_metrics.py`，所以这里没有任何写接口——
一旦开了在线编辑，平台就会长出第二套跟文档对不上的指标体系。
字典本身是全局的；覆盖度按工作空间算，因为评估器是按空间隔离的。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..deps import current_workspace
from ..services.metric_dict import coverage as calc_coverage

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def _json(m: models.Metric, mapped: dict[str, list[dict]]) -> dict:
    return {"code": m.code, "group_code": m.group_code, "group_name": m.group_name,
            "name": m.name, "layer": m.layer, "pillar": m.pillar,
            "definition": m.definition, "formula": m.formula, "collection": m.collection,
            "pitfall": m.pitfall, "threshold": m.threshold, "notes": m.notes,
            "evaluators": mapped.get(m.code, [])}


@router.get("")
def list_metrics(layer: str = "", pillar: str = "", group: str = "", q: str = "",
                 ws=Depends(current_workspace), db: Session = Depends(get_db)):
    query = db.query(models.Metric)
    if layer:
        query = query.filter(models.Metric.layer == layer)
    if pillar:
        query = query.filter(models.Metric.pillar == pillar)
    if group:
        query = query.filter(models.Metric.group_code == group)
    if q:
        like = f"%{q}%"
        query = query.filter(models.Metric.name.like(like) | models.Metric.code.like(like))
    rows = query.order_by(models.Metric.code).all()

    # 本空间挂靠了这些指标的评估器，一次查完，别在循环里查库
    mapped: dict[str, list[dict]] = {}
    for ev in (db.query(models.Evaluator)
               .filter(models.Evaluator.workspace_id == ws["id"],
                       models.Evaluator.metric_code.isnot(None)).all()):
        mapped.setdefault(ev.metric_code, []).append(
            {"id": ev.id, "name": ev.name, "type": ev.type, "version": ev.version,
             "status": ev.status})

    return {"total": db.query(models.Metric).count(), "count": len(rows),
            "items": [_json(m, mapped) for m in rows]}


@router.get("/facets")
def facets(ws=Depends(current_workspace), db: Session = Depends(get_db)):
    """筛选项取值域，由字典实际内容决定——别在前端写死 5 层 4 柱，文档里还有「全柱」和「元」。"""
    def distinct(col):
        return sorted({v for (v,) in db.query(col).distinct() if v})
    groups = sorted({(g, n) for g, n in db.query(models.Metric.group_code, models.Metric.group_name)})
    return {"layers": distinct(models.Metric.layer),
            "pillars": distinct(models.Metric.pillar),
            "groups": [{"code": g, "name": n} for g, n in groups]}


@router.get("/coverage")
def coverage(ws=Depends(current_workspace), db: Session = Depends(get_db)):
    return calc_coverage(db, workspace_id=ws["id"])


@router.get("/{code}")
def get_metric(code: str, ws=Depends(current_workspace), db: Session = Depends(get_db)):
    from fastapi import HTTPException
    m = db.get(models.Metric, code)
    if not m:
        raise HTTPException(404, f"指标 {code} 不在字典里；字典由 scripts/sync_metrics.py 同步")
    evs = (db.query(models.Evaluator)
           .filter_by(workspace_id=ws["id"], metric_code=code).all())
    return _json(m, {code: [{"id": e.id, "name": e.name, "type": e.type,
                             "version": e.version, "status": e.status} for e in evs]})
