"""quality 的请求/响应模型。"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class ReviewIn(BaseModel):
    conclusion: str = "confirm"           # confirm/misjudge/pending
    root_cause: str = ""
    note: str = ""

class BatchReviewIn(BaseModel):
    ids: list[str]
    conclusion: str = "confirm"
    root_cause: str = ""

class RegressionIn(BaseModel):
    name: str
    dataset_id: str
    app_id: Optional[str] = None
    base_ver: str
    comp_ver: str
