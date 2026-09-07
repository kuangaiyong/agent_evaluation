"""governance 域的数据模型。"""
import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ...core.db import Base
from ...shared.ids import uid


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
