"""observability 域的数据模型。"""
import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ...core.db import Base
from ...shared.ids import uid


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
