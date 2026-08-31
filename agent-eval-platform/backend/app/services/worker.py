"""评估 Worker：进程内 asyncio 循环。
- 在线任务：每 N 秒轮询运行中任务，按采样率评估新轨迹，阈值以下自动入 Bad Case 队列
- 离线任务：start 时以 asyncio 任务执行批量评估
"""
import asyncio, random, logging
from sqlalchemy.orm import Session
from ..config import settings
from ..db import SessionLocal
from .. import models
from .evaluators import run_evaluator, quality_hint_of

log = logging.getLogger("agenteval.worker")

def eval_trace_on_tasks(db: Session, tasks: list[models.EvalTask], trace: models.Trace, force: bool = False) -> dict:
    """对一条轨迹在所有给定任务上评估（各自采样率 + 阈值），返回 {task_id: stats}。"""
    results = {}
    for task in tasks:
        if task.status != "running" and not force:
            continue
        if not force and random.random() * 100 > task.sample_rate:
            continue
        done = db.query(models.ScoreRecord).filter_by(task_id=task.id, trace_id=trace.id).count()
        if done > 0:
            continue
        scores, failed = [], 0
        per_ev = []
        for evid in (task.evaluator_ids or []):
            ev = db.get(models.Evaluator, evid)
            if not ev:
                continue
            out = run_evaluator(ev, trace, quality_hint_of(trace), db)
            db.add(models.ScoreRecord(task_id=task.id, evaluator_id=evid, trace_id=trace.id,
                                      score=out["score"], version=ev.version,
                                      meta={"reason": out["reason"], "type": ev.type}, failed=out["failed"]))
            per_ev.append((evid, out))
            if out["failed"]:
                failed += 1
            elif out["score"] is not None:
                scores.append(out["score"])
        if scores:
            avg = round(sum(scores) / len(scores), 4)
            trace.score_avg = avg
            trace.evaluated = True
            st = task.stats or {}
            st["count"] = st.get("count", 0) + 1
            st["avg"] = round((st.get("avg", 0) * (st["count"] - 1) + avg) / st["count"], 4)
            st["low"] = st.get("low", 0) + (1 if avg < task.threshold else 0)
            st["fail"] = st.get("fail", 0) + failed
            task.stats = dict(st)
            if any(out.get("budget_hit") for _, out in per_ev):
                from .budget import auto_pause_budget_tasks
                auto_pause_budget_tasks(db, task.workspace_id)
            # 低于阈值 → Bad Case 自动入队（每个评估器低分也入队）
            for evid, out in per_ev:
                if out["score"] is not None and out["score"] < task.threshold:
                    exist = db.query(models.BadCase).filter_by(trace_id=trace.id, task_id=task.id, evaluator_id=evid).first()
                    if not exist:
                        db.add(models.BadCase(workspace_id=task.workspace_id, trace_id=trace.id, task_id=task.id,
                                              evaluator_id=evid, score=out["score"], threshold=task.threshold))
        results[task.id] = task.stats
    db.commit()
    return results

async def offline_batch(task_id: str):
    """离线任务批次评估（后台 asyncio 任务）。"""
    db = SessionLocal()
    try:
        task = db.get(models.EvalTask, task_id)
        if not task:
            return
        task.status = "running"
        db.commit()
        q = (db.query(models.Trace)
             .filter(models.Trace.workspace_id == task.workspace_id,
                     models.Trace.version == (task.version_filter or models.Trace.version)))
        if task.dataset_id:
            ds = db.get(models.Dataset, task.dataset_id)
            sessions = [s.session_id for s in db.query(models.DatasetSample).filter_by(dataset_id=task.dataset_id)]
            q = q.filter(models.Trace.session_id.in_(sessions)) if sessions else q.filter(False)
        if task.app_id:
            q = q.filter(models.Trace.app_id == task.app_id)
        traces = q.limit(500).all()
        if not traces:
            task.status = "completed"
            task.stats = {"count": 0, "low": 0, "fail": 0, "avg": 0}
            db.commit()
            return
        st = {"count": 0, "low": 0, "fail": 0, "avg": 0}
        for tr in traces:
            for evid in (task.evaluator_ids or []):
                ev = db.get(models.Evaluator, evid)
                if not ev:
                    continue
                out = run_evaluator(ev, tr, quality_hint_of(tr), db)
                db.add(models.ScoreRecord(task_id=task.id, evaluator_id=evid, trace_id=tr.id,
                                          score=out["score"], version=ev.version,
                                          meta={"reason": out["reason"], "type": ev.type}, failed=out["failed"]))
                if out["failed"]:
                    st["fail"] += 1
                elif out["score"] is not None:
                    st["count"] += 1
                    st["avg"] = round((st["avg"] * (st["count"] - 1) + out["score"]) / st["count"], 4)
                    if out["score"] < task.threshold:
                        st["low"] += 1
                        if not db.query(models.BadCase).filter_by(trace_id=tr.id, task_id=task.id, evaluator_id=evid).first():
                            db.add(models.BadCase(workspace_id=task.workspace_id, trace_id=tr.id, task_id=task.id,
                                                  evaluator_id=evid, score=out["score"], threshold=task.threshold))
                tr.score_avg = out["score"]
                tr.evaluated = True
        task.stats = st
        task.status = "completed"
        db.commit()
    except Exception as e:
        log.exception("offline batch failed")
        db.rollback()
        task = db.get(models.EvalTask, task_id)
        if task:
            task.status = "error"
            task.err_msg = str(e)[:240]
            db.commit()
    finally:
        db.close()

def rebuild_stats(db, task):
    """从 score_records 重算任务统计（自愈：JSON 变更追踪只对新数据生效）。"""
    rows = db.query(models.ScoreRecord).filter_by(task_id=task.id, failed=False).all()
    scores = [r.score for r in rows if r.score is not None]
    fails = db.query(models.ScoreRecord).filter_by(task_id=task.id, failed=True).count()
    task.stats = dict(count=len(scores), low=sum(1 for s in scores if s < task.threshold),
                      fail=fails, avg=round(sum(scores) / len(scores), 4) if scores else 0)

async def online_loop():
    db = SessionLocal()
    try:
        tasks = db.query(models.EvalTask).filter_by(mode="online", status="running").all()
        for task in tasks:
            rebuild_stats(db, task)
        for task in tasks:
            q = db.query(models.Trace).filter(models.Trace.workspace_id == task.workspace_id)
            if task.app_id:
                q = q.filter(models.Trace.app_id == task.app_id)
            q = q.order_by(models.Trace.created_at.desc()).limit(50)
            for tr in q.all():
                eval_trace_on_tasks(db, [task], tr)
        db.commit()  # rebuild_stats 的 JSON 变更需显式提交
    except Exception as e:
        log.warning("online loop error: %s", e)
        db.rollback()
    finally:
        db.close()

def start_worker():
    """FastAPI lifespan 中启动。"""
    async def _loop():
        while True:
            try:
                await online_loop()
            except Exception:
                log.exception("worker loop")
            await asyncio.sleep(max(1, settings.auto_eval_interval))
    return asyncio.ensure_future(_loop())
