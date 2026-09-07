"""access 域的数据模型。"""
import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ...core.db import Base
from ...shared.ids import uid


class App(Base):
    __tablename__ = "apps"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uid("app-"))
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(32), default="AgentScope")  # 智能体类型：AgentScope/OpenCode/Hermes Agent/CodeBuddy/其他
    # LoongSuite 接入通道。可空——存量应用没有该字段，置 NOT NULL 会让迁移失败；
    # 为空时读接口按 type 推导（见 services/access.channel_of），显式赋值优先。
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model: Mapped[str] = mapped_column(String(64), default="qwen-plus")
    version: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(16), default="none")  # none/reporting/connected/interrupted
    api_key: Mapped[str] = mapped_column(String(128), default="")
    last_report_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
