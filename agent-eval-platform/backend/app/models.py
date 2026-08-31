import uuid, datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def uid(prefix=""):
    return prefix + uuid.uuid4().hex[:8]

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uid("u-"))
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16), default="dev")  # admin/dev/ro
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uid("ws-"))
    name: Mapped[str] = mapped_column(String(64))
    env: Mapped[str] = mapped_column(String(16), default="生产")  # 生产/测试
    description: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    role: Mapped[str] = mapped_column(String(16), default="dev")

class App(Base):
    __tablename__ = "apps"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uid("app-"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(32), default="AgentScope")  # AgentScope/OpenCode/自研 Agent
    model: Mapped[str] = mapped_column(String(64), default="qwen-plus")
    version: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="none")  # none/reporting/connected/interrupted
    api_key: Mapped[str] = mapped_column(String(128), default="")
    last_report_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

class Trace(Base):
    __tablename__ = "traces"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uid("tr-"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str] = mapped_column(String(64), default="")
    version: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="ok")  # ok/error
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0)
    otel_trace_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)        # {turns:[{role,message,steps:[...]}]}
    evaluated: Mapped[bool] = mapped_column(Boolean, default=False)
    score_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

class Metric(Base):
    """指标字典（只读）。

    权威源是文档 `智能体评测体系/01-指标体系与指标字典.md`，平台是消费方不是编辑方：
    改指标改文档，再跑 `scripts/sync_metrics.py` 同步，不提供在线编辑。
    主键用指标编号本身（A-01），这样 evaluators.metric_code 可读且无需 join 就能看懂。
    """
    __tablename__ = "metrics"
    code: Mapped[str] = mapped_column(String(8), primary_key=True)            # A-01
    group_code: Mapped[str] = mapped_column(String(2), index=True)            # A
    group_name: Mapped[str] = mapped_column(String(64))                       # 效果与完成度
    name: Mapped[str] = mapped_column(String(128))                            # 任务成功率（Success Rate, SR）
    layer: Mapped[str] = mapped_column(String(8), index=True)                 # L1..L5/元
    pillar: Mapped[str] = mapped_column(String(64), index=True)               # 模型与推理/工具/记忆/环境与交互/全柱/元/评测集/评分层
    definition: Mapped[str] = mapped_column(Text, default="")
    formula: Mapped[str] = mapped_column(Text, default="")
    collection: Mapped[str] = mapped_column(Text, default="")
    pitfall: Mapped[str] = mapped_column(Text, default="")
    threshold: Mapped[str] = mapped_column(Text, default="")
    # 固定五项之外的带标签正文（实测量级 / 注入哪几类故障 …），逐行保留原标签。
    # 这些条目带着 arXiv 出处，是引用纪律的依据，不能在解析时丢掉。
    notes: Mapped[str] = mapped_column(Text, default="")
    synced_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class Evaluator(Base):
    __tablename__ = "evaluators"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uid("ev-"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    # 挂靠的指标编号。DB 上可空——存量评估器没有映射，置 NOT NULL 会让迁移失败；
    # 「必填」在新建/发布路径上拦，未挂靠的存量条目由指标库的覆盖度视图暴露出来。
    metric_code: Mapped[str | None] = mapped_column(ForeignKey("metrics.code"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(16))  # rule/llm/agent/human
    preset: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[str] = mapped_column(String(16), default="v1")
    status: Mapped[str] = mapped_column(String(16), default="draft")  # published/draft
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    bias_rate: Mapped[float] = mapped_column(Float, default=0)
    created_by: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

class EvalTask(Base):
    __tablename__ = "eval_tasks"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uid("task-"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    mode: Mapped[str] = mapped_column(String(16))  # online/offline
    status: Mapped[str] = mapped_column(String(16), default="created")
    app_id: Mapped[str | None] = mapped_column(ForeignKey("apps.id"), nullable=True)
    dataset_id: Mapped[str | None] = mapped_column(ForeignKey("datasets.id"), nullable=True)
    version_filter: Mapped[str] = mapped_column(String(32), default="")
    evaluator_ids: Mapped[list] = mapped_column(JSON, default=list)
    sample_rate: Mapped[int] = mapped_column(Integer, default=100)
    threshold: Mapped[float] = mapped_column(Float, default=0.6)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)   # {count, low, fail, avg, last_low}
    err_msg: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class ScoreRecord(Base):
    __tablename__ = "score_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("eval_tasks.id"), index=True)
    evaluator_id: Mapped[str] = mapped_column(ForeignKey("evaluators.id"), index=True)
    trace_id: Mapped[str] = mapped_column(ForeignKey("traces.id"), index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    version: Mapped[str] = mapped_column(String(16), default="")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    failed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

class BadCase(Base):
    __tablename__ = "bad_cases"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uid("bc-"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    trace_id: Mapped[str] = mapped_column(ForeignKey("traces.id"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("eval_tasks.id"), index=True)
    evaluator_id: Mapped[str] = mapped_column(ForeignKey("evaluators.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float, default=0.6)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/confirmed/misjudged/pending2
    root_cause: Mapped[str] = mapped_column(String(128), default="")
    note: Mapped[str] = mapped_column(String(512), default="")
    reviewer_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

class Dataset(Base):
    __tablename__ = "datasets"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uid("ds-"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    type: Mapped[str] = mapped_column(String(16), default="评测集")  # 评测集/回归集/经典 Case
    version: Mapped[str] = mapped_column(String(16), default="v1")
    refs: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

class DatasetSample(Base):
    __tablename__ = "dataset_samples"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    label: Mapped[str] = mapped_column(String(64), default="")  # 优质样本/Bad Case/误判样本

class RegressionRun(Base):
    __tablename__ = "regression_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uid("rgn-"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), index=True)
    app_id: Mapped[str | None] = mapped_column(ForeignKey("apps.id"), nullable=True)
    base_ver: Mapped[str] = mapped_column(String(32))
    comp_ver: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="completed")
    report: Mapped[dict] = mapped_column(JSON, default=dict)  # {base_score, comp_score, degraded, improved, rows, verdict}
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

class JudgeDailyStat(Base):
    """LLM-as-Judge 裁判模型的日调用成本台账（成本保护）。"""
    __tablename__ = "judge_daily_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day: Mapped[str] = mapped_column(String(16), unique=True, index=True)   # YYYY-MM-DD
    calls: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(128))  # 可以写于 audit 表
    obj: Mapped[str] = mapped_column(String(256))
    result: Mapped[str] = mapped_column(String(32), default="成功")
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uid("nt-"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    type: Mapped[str] = mapped_column(String(16), default="系统")  # 告警/门禁/到期/系统
    title: Mapped[str] = mapped_column(String(256))
    body: Mapped[str] = mapped_column(String(1024), default="")
    link: Mapped[str] = mapped_column(String(128), default="")
    unread: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
