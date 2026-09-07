"""接入通道推导与审计高风险判定。

两者都是「规则放服务端」的决定：通道口径若靠前端推导，新增工具就要改前端；
高风险判定若放前端，换个客户端就失效。所以两者都在这里单测。
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.db import Base, get_db
from app.security import hash_password
from app.services.access import channel_of, CHANNEL_PY, CHANNEL_PILOT, CHANNEL_OTLP
from app.services.audit import is_high_risk


# ───────── 接入通道推导（纯函数，不碰 DB）─────────

def make_app(type_, channel=None):
    return models.App(workspace_id="ws-a", name="x", type=type_, channel=channel)


@pytest.mark.parametrize("type_, expect", [
    ("AgentScope", CHANNEL_PY),
    ("OpenCode", CHANNEL_PILOT),
    ("Hermes Agent", CHANNEL_PILOT),
    ("CodeBuddy", CHANNEL_OTLP),
    ("某个没登记的新工具", CHANNEL_OTLP),
])
def test_channel_derived_from_type(type_, expect):
    assert channel_of(make_app(type_)) == expect


def test_explicit_channel_wins_over_derivation():
    a = make_app("AgentScope", channel=CHANNEL_OTLP)
    assert channel_of(a) == CHANNEL_OTLP, "显式赋值必须优先于按 type 推导"


def test_blank_channel_falls_back_to_derivation():
    assert channel_of(make_app("OpenCode", channel="   ")) == CHANNEL_PILOT


# ───────── 高风险判定 ─────────

@pytest.mark.parametrize("action, expect", [
    ("修改评分器 rubric", True),
    ("修改评分器权重", True),
    ("修改金标准", True),
    ("重跑评估任务", True),
    ("创建 Agent 应用", False),
    ("邀请成员", False),
    ("发布评估器版本", False),
    ("", False),
])
def test_high_risk_judgement(action, expect):
    assert is_high_risk(action) is expect


# ───────── 接口层：筛选与叠加 ─────────

@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    db = Session()

    from app.config import settings
    settings.seed_on_start = False
    from app.main import app

    db.add_all([
        models.Workspace(id="ws-a", name="A 团队"),
        models.User(id="u-1", email="a@corp.com", name="甲", role="admin",
                    password_hash=hash_password("pw123456")),
        models.Membership(user_id="u-1", workspace_id="ws-a", role="admin"),
        models.App(id="app-1", workspace_id="ws-a", name="用例生成", type="AgentScope"),
        models.App(id="app-2", workspace_id="ws-a", name="脚本生成", type="OpenCode"),
        models.App(id="app-3", workspace_id="ws-a", name="研发助手", type="CodeBuddy"),
        models.AuditLog(workspace_id="ws-a", actor="王", action="修改评分器 rubric", obj="C-03"),
        models.AuditLog(workspace_id="ws-a", actor="李", action="重跑评估任务", obj="tk-1"),
        models.AuditLog(workspace_id="ws-a", actor="王", action="邀请成员", obj="赵"),
        models.AuditLog(workspace_id="ws-a", actor="陈", action="创建 Agent 应用", obj="app-9"),
    ])
    db.commit()

    def _get_db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        r = c.post("/api/auth/login", json={"email": "a@corp.com", "password": "pw123456"})
        assert r.status_code == 200, r.text
        c.headers["Authorization"] = "Bearer " + r.json()["token"]
        c.headers["X-Workspace"] = "ws-a"
        yield c
    app.dependency_overrides.clear()
    db.close()
    engine.dispose()


def test_app_list_carries_type_and_channel(client):
    rows = {a["name"]: a for a in client.get("/api/apps").json()}
    assert rows["用例生成"]["type"] == "AgentScope" and rows["用例生成"]["channel"] == CHANNEL_PY
    assert rows["脚本生成"]["channel"] == CHANNEL_PILOT
    assert rows["研发助手"]["channel"] == CHANNEL_OTLP


def test_audits_carry_high_risk_flag(client):
    rows = client.get("/api/system/audits").json()
    flags = {r["action"]: r["high_risk"] for r in rows}
    assert flags["修改评分器 rubric"] is True
    assert flags["重跑评估任务"] is True
    assert flags["邀请成员"] is False


def test_audits_filter_by_actor(client):
    rows = client.get("/api/system/audits", params={"actor": "王"}).json()
    assert len(rows) == 2 and {r["actor"] for r in rows} == {"王"}


def test_audits_only_high_risk(client):
    rows = client.get("/api/system/audits", params={"high_risk": True}).json()
    assert len(rows) == 2 and all(r["high_risk"] for r in rows)


def test_audits_actor_and_high_risk_intersect(client):
    """两个条件叠加取交集：王有 2 条，其中只有 1 条是高风险。"""
    rows = client.get("/api/system/audits", params={"actor": "王", "high_risk": True}).json()
    assert len(rows) == 1 and rows[0]["action"] == "修改评分器 rubric"


def test_audit_actors_come_from_data(client):
    assert client.get("/api/system/audit-actors").json() == ["李", "王", "陈"]
