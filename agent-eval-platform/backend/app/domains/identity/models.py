"""identity 域的数据模型。"""
import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ...core.db import Base
from ...shared.ids import uid


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
    # 加入该空间的时间。可空——存量成员关系补不出来。
    # 用 default（Python 侧）而非 server_default：ensure_schema 补的是裸列，没有 DDL 默认值，
    # 若依赖 server_default，升级过的库里此后所有新成员都会落 NULL。
    created_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True,
                                                                 default=datetime.datetime.utcnow)
