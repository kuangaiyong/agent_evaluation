"""dataset 的请求/响应模型。"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class DatasetIn(BaseModel):
    name: str
    type: str = "评测集"
