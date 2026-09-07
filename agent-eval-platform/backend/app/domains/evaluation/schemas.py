"""evaluation 的请求/响应模型。"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class EvaluatorIn(BaseModel):
    name: str
    type: str = "rule"                    # rule/llm/agent/human
    config: dict = {}
    status: str = "draft"

class TaskIn(BaseModel):
    name: str
    mode: str = "online"
    app_id: Optional[str] = None
    dataset_id: Optional[str] = None
    version_filter: str = ""
    evaluator_ids: list[str] = []
    sample_rate: int = 100
    threshold: float = 0.6
