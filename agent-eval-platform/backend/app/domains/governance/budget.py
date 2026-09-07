"""LLM-as-Judge 成本保护：日额度台账 + 超额自动暂停关联任务并通知。"""
import datetime
import logging

from sqlalchemy.orm import Session

from ...core.config import settings
from ... import models

log = logging.getLogger("agenteval.budget")

# 裁判模型定价（元 / 1M tokens）：(输入, 输出)，未登记模型用兜底值
JUDGE_PRICES = {
    "deepseek-v4-flash": (0.8, 2.0),
    "deepseek-v3": (1.0, 2.5),
    "qwen-max": (2.0, 6.0),
    "qwen-plus": (1.2, 4.0),
}
DEFAULT_PRICE = (1.0, 2.0)


def judge_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pi, po = JUDGE_PRICES.get(model, DEFAULT_PRICE)
    return round((input_tokens * pi + output_tokens * po) / 1_000_000, 6)


def daily_key() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


class JudgeBudget:
    """基于 DB 台账的日额度。"""

    def __init__(self, db: Session):
        self.db = db

    def _stat(self) -> models.JudgeDailyStat:
        stat = self.db.query(models.JudgeDailyStat).filter_by(day=daily_key()).first()
        if not stat:
            stat = models.JudgeDailyStat(day=daily_key())
            self.db.add(stat)
            self.db.flush()
        return stat

    def spent(self) -> float:
        return self._stat().cost or 0

    def exceeded(self) -> bool:
        return self.spent() >= settings.judge_daily_limit_yuan

    def record(self, model: str, input_tokens: int, output_tokens: int) -> float:
        cost = judge_cost(model, input_tokens, output_tokens)
        st = self._stat()
        st.calls = (st.calls or 0) + 1
        st.cost = round((st.cost or 0) + cost, 6)
        self.db.commit()
        log.info("Judge 成本记账：%s ¥%.4f（今日累计 ¥%.2f / 上限 ¥%.2f）",
                 model, cost, st.cost, settings.judge_daily_limit_yuan)
        return cost


def auto_pause_budget_tasks(db: Session, ws_id: str) -> int:
    """额度超限时，自动暂停使用 LLM/Agent 评估器的在线任务并通知创建人。返回暂停数。"""
    paused = 0
    tasks = (db.query(models.EvalTask)
             .filter(models.EvalTask.workspace_id == ws_id,
                     models.EvalTask.status == "running").all())
    evs = {e.id: e for e in db.query(models.Evaluator).filter(models.Evaluator.type.in_(["llm", "agent"])).all()}
    for t in tasks:
        if any(eid in evs for eid in (t.evaluator_ids or [])):
            t.status = "error"
            t.err_msg = (f"LLM-as-Judge 裁判模型日额度已达上限（¥{settings.judge_daily_limit_yuan:.2f}），"
                         f"任务已自动暂停，恢复后从断点继续消费")
            db.add(models.Notification(
                workspace_id=ws_id, type="告警",
                title=f"评估任务异常：{t.name}",
                body=t.err_msg, link=f"/tasks/{t.id}"))
            paused += 1
    if paused:
        db.commit()
    return paused
