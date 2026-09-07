"""quality 域的数据模型。"""
import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ...core.db import Base
from ...shared.ids import uid


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
