"""access 的请求/响应模型。"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class AppCreate(BaseModel):
    name: str
    type: str = "AgentScope"
    model: str = "qwen-plus"
