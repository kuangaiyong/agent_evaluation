import hashlib
import hmac
import json
import time
import httpx
from fastapi import APIRouter, Depends, HTTPException
from ...core.config import settings
from sqlalchemy.orm import Session
from ...core.db import get_db
from ... import models, schemas
from ..identity.deps import current_workspace, require_write, audit
from ..evaluation.service import run_evaluator, quality_hint_of

router = APIRouter(prefix="/api/regression", tags=["regression"])

def _run_regression(db, ws_id, name, dataset_id, app_id, base_ver, comp_ver):
    """对同一数据集（sessions）在两个版本轨迹上分别评估，产出对比报告。"""
    ds = db.get(models.Dataset, dataset_id)
    sessions = [s.session_id for s in db.query(models.DatasetSample).filter_by(dataset_id=dataset_id)]
    evaluators = db.query(models.Evaluator).filter_by(workspace_id=ws_id, status="published").all()
    def eval_version(ver):
        q = db.query(models.Trace).filter(models.Trace.workspace_id == ws_id,
                                          models.Trace.version == ver,
                                          models.Trace.session_id.in_(sessions))
        if app_id:
            q = q.filter(models.Trace.app_id == app_id)
        traces = q.all()
        rows, scores = [], []
        for t in traces:
            vals, per_ev = [], {}
            for ev in evaluators:
                if ev.type == "human":
                    continue
                r = run_evaluator(ev, t, quality_hint_of(t), db)
                if r["score"] is not None and not r["failed"]:
                    vals.append(r["score"])
                    per_ev[ev.name] = r["score"]
            avg = round(sum(vals) / len(vals), 4) if vals else 0
            if vals:
                scores.append(avg)
            # 按 session_id 归并：同一条会话在两个版本各有一条 Trace，trace id 不同
            rows.append({"session_id": t.session_id, "trace_id": t.id,
                         "score": avg, "per_ev": per_ev})
        total = round(sum(scores) / len(scores), 4) if scores else 0
        return total, rows
    b, brows = eval_version(base_ver)
    c, crows = eval_version(comp_ver)
    by_session = {r["session_id"]: r for r in crows}
    diffs = []
    for r in brows:
        cur = by_session.get(r["session_id"])
        if cur is None:
            continue          # 对比版本没跑过这条会话，无从比较
        delta = round(cur["score"] - r["score"], 4)
        # 归因 = 跌得最狠的评估器。只有确实退化的行才给原因，否则是噪声。
        reason = ""
        if delta < -0.005:
            drops = [(cur["per_ev"].get(n, 0) - b, n) for n, b in r["per_ev"].items()]
            if drops:
                worst = min(drops)
                reason = worst[1] if worst[0] < 0 else ""
        diffs.append({"trace_id": cur["trace_id"], "base": r["score"], "comp": cur["score"],
                      "delta": delta, "reason": reason})
    degraded = [d for d in diffs if d["delta"] < -0.005]
    improved = len([d for d in diffs if d["delta"] > 0.005])
    verdict = "publish" if (c >= b and len(degraded) <= 10) else "block"
    run = models.RegressionRun(workspace_id=ws_id, name=name, dataset_id=dataset_id,
                               app_id=app_id, base_ver=base_ver, comp_ver=comp_ver,
                               report={"base_score": b, "comp_score": c,
                                       "degraded": len(degraded), "improved": improved,
                                       "verdict": verdict, "rows": diffs[:200]})
    db.add(run)
    db.commit()
    return run


def _mask_url(url: str) -> str:
    if not url:
        return ""
    return url[: len(url) // 2] + "****" + url[-4:] if len(url) > 8 else "****"


def _deliver_gate_webhook(db, run) -> str:
    """回归结论 → CI 门禁回调（HMAC-SHA256 签名）。失败不阻断，状态记入报告的 webhook 字段。"""
    url = settings.gate_webhook_url
    if not url:
        return "未配置"
    ds = db.get(models.Dataset, run.dataset_id)
    payload = {
        "event": "regression_gate",
        "run_id": run.id,
        "name": run.name,
        "dataset": ds.name if ds else "",
        "base_ver": run.base_ver,
        "comp_ver": run.comp_ver,
        "report": run.report or {},
        "verdict": (run.report or {}).get("verdict", ""),
        "ts": int(time.time() * 1000),
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    sig = hmac.new((settings.gate_webhook_secret or "").encode(), body, hashlib.sha256).hexdigest()
    status = "failed"
    try:
        r = httpx.post(url, content=body, timeout=10,
                       headers={"content-type": "application/json",
                                "x-agenteval-signature": sig,
                                "x-agenteval-event": "regression_gate"})
        status = "sent" if r.status_code < 300 else f"HTTP {r.status_code}"
    except Exception as exc:
        status = f"failed: {type(exc).__name__}"
    report = dict(run.report or {})
    report["webhook"] = {"url": _mask_url(url), "status": status,
                         "at": time.strftime("%Y-%m-%d %H:%M:%S")}
    run.report = report
    db.commit()
    return status


@router.get("/runs")
def runs(ws=Depends(current_workspace), db: Session = Depends(get_db)):
    rows = db.query(models.RegressionRun).filter_by(workspace_id=ws["id"]).order_by(
        models.RegressionRun.created_at.desc()).all()
    out = []
    for r in rows:
        ds = db.get(models.Dataset, r.dataset_id)
        rep = r.report or {}
        out.append({"id": r.id, "name": r.name, "dataset": ds.name if ds else "",
                    "base_ver": r.base_ver, "comp_ver": r.comp_ver,
                    "base_score": rep.get("base_score"), "comp_score": rep.get("comp_score"),
                    "degraded": rep.get("degraded"), "improved": rep.get("improved"),
                    "verdict": rep.get("verdict"),
                    "time": r.created_at.strftime("%Y-%m-%d %H:%M")})
    return out

@router.post("/runs")
def create_run(data: schemas.RegressionIn, ws=Depends(require_write), db: Session = Depends(get_db)):
    run = _run_regression(db, ws["id"], data.name, data.dataset_id, data.app_id,
                          data.base_ver, data.comp_ver)
    audit(db, ws["id"], "当前用户", "创建回归实验", data.name)
    db.commit()
    _deliver_gate_webhook(db, run)
    return {"id": run.id, "ok": True}


@router.get("/gate-info")
def gate_info(ws=Depends(current_workspace), db: Session = Depends(get_db)):
    """展示门禁回调配置（URL 掩码）与最近一次送达状态。"""
    last = (db.query(models.RegressionRun).filter_by(workspace_id=ws["id"])
            .order_by(models.RegressionRun.created_at.desc()).first())
    wb = (last.report or {}).get("webhook", {}) if last else {}
    return {
        "url": _mask_url(settings.gate_webhook_url) if settings.gate_webhook_url else "",
        "configured": bool(settings.gate_webhook_url),
        "secret_set": bool(settings.gate_webhook_secret),
        "rule": "平均分提升 ≥ 0.01 且退化样本 ≤ 10 才允许发布",
        "last": wb,
    }


@router.post("/webhook-echo")
def webhook_echo(request: dict, x_agenteval_signature: str = " "):
    """调试用回声端点：CI 门禁验证时可把 GATE_WEBHOOK_URL 指向这里，拦截并打日志。"""
    return {"received": True, "event": request.get("event"), "run_id": request.get("run_id"),
            "verdict": request.get("verdict"), "sig_ok": bool(x_agenteval_signature)}
@router.get("/runs/{rid}")
def run_detail(rid: str, ws=Depends(current_workspace), db: Session = Depends(get_db)):
    r = db.get(models.RegressionRun, rid)
    if not r or r.workspace_id != ws["id"]:
        raise HTTPException(404, "回归实验不存在")
    return {"id": r.id, "name": r.name, "base_ver": r.base_ver, "comp_ver": r.comp_ver,
            "report": r.report or {},
            "time": r.created_at.strftime("%Y-%m-%d %H:%M")}
