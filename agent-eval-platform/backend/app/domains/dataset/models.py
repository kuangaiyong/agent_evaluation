"""dataset 域的数据模型。"""
import datetime
from sqlalchemy import String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ...core.db import Base
from ...shared.ids import uid


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
    # 金标准（期望产出）。可空——从轨迹导入的条目先入库、再人工补录，
    # 未补录的条目不参与门禁判定（见 specs/data-center）。
    gold: Mapped[str | None] = mapped_column(Text, nullable=True)
