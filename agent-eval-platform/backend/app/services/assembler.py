"""轨迹组装：把 SDK/HTTP 上报的原始数据组装为 Session/Turn/Step 标准结构。"""
import uuid, datetime
from sqlalchemy.orm import Session
from .. import models

def assemble_trace(db: Session, app, data: dict) -> models.Trace:
    """data: {session_id, model, version, turns:[{role,message,steps:[...]}]}"""
    session_id = (data.get("session_id") or f"s-{datetime.date.today():%Y%m%d}-{uuid.uuid4().hex[:4]}")[:64]
    turns = []
    total_dur = total_tok = 0
    has_error = False
    for t in data.get("turns", []):
        steps = []
        for s in t.get("steps", []):
            dur = max(0, int(s.get("duration_ms", 0) or 0))
            tok = max(0, int(s.get("tokens", 0) or 0))
            if s.get("kind") == "tool" and not s.get("name"):
                s["name"] = f"工具 · {s.get('tool', 'tool')}"
            steps.append({
                "kind": s.get("kind", "llm"), "name": s.get("name", ""), "tool": s.get("tool", ""),
                "status": s.get("status", "ok"), "duration_ms": dur, "tokens": tok,
                "input": s.get("input"), "output": s.get("output"), "error": s.get("error", ""),
                "model": s.get("model", ""),
            })
            total_dur += dur; total_tok += tok
            if steps[-1]["status"] == "error":
                has_error = True
        turns.append({"role": t.get("role", "user"), "message": t.get("message", ""), "steps": steps})
    tr = models.Trace(
        workspace_id=app.workspace_id, app_id=app.id,
        session_id=session_id, model=data.get("model") or app.model,
        version=data.get("version") or app.version, status="error" if has_error else "ok",
        duration_ms=total_dur, tokens=total_tok,
        cost=round(total_tok / 1_000_000 * 0.02, 4),  # ¥0.02 / 1M token（演示计价）
        payload={"turns": turns},
    )
    touch_app(app)
    db.add(tr)
    db.commit()
    db.refresh(tr)
    return tr

def touch_app(app) -> None:
    """上报后更新应用接入状态（未接入 → 上报中 → 已接入）与最近上报时间。"""
    import datetime
    app.last_report_at = datetime.datetime.utcnow()
    if app.status == "none":
        app.status = "reporting"
    elif app.status == "reporting":
        app.status = "connected"

def count_steps(payload) -> tuple[int, int]:
    turns = payload.get("turns", [])
    return len(turns), sum(len(t.get("steps", [])) for t in turns)
