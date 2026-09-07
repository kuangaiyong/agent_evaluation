"""identity 的请求/响应模型。"""
from typing import Any, Optional
from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str
    password: str

class InviteIn(BaseModel):
    email: str
    name: str
    role: str = "dev"
