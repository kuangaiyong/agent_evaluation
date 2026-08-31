from typing import Any, Optional
from pydantic import BaseModel, Field

class LoginIn(BaseModel):
    email: str
    password: str

class AppCreate(BaseModel):
    name: str
    type: str = "AgentScope"
    model: str = "qwen-plus"

class IngestStep(BaseModel):
    kind: str = "llm"                     # llm / tool
    name: str = ""
    tool: str = ""
    status: str = "ok"                    # ok / error
    duration_ms: int = 0
    tokens: int = 0
    input: Any = None
    output: Any = None
    error: str = ""
    model: str = ""

class IngestTurn(BaseModel):
    role: str = "user"
    message: str = ""
    steps: list[IngestStep] = []

class IngestTrace(BaseModel):
    session_id: str = ""
    model: str = ""
    version: str = ""
    turns: list[IngestTurn] = []

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

class ReviewIn(BaseModel):
    conclusion: str = "confirm"           # confirm/misjudge/pending
    root_cause: str = ""
    note: str = ""

class BatchReviewIn(BaseModel):
    ids: list[str]
    conclusion: str = "confirm"
    root_cause: str = ""

class DatasetIn(BaseModel):
    name: str
    type: str = "评测集"

class RegressionIn(BaseModel):
    name: str
    dataset_id: str
    app_id: Optional[str] = None
    base_ver: str
    comp_ver: str

class InviteIn(BaseModel):
    email: str
    name: str
    role: str = "dev"
