"""ingest 的请求/响应模型。"""
from typing import Any, Optional
from pydantic import BaseModel, Field


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
