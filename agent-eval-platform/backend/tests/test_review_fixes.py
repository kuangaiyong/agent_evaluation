"""代码评审发现的问题的回归测试。

每个用例对应一条 finding：先能复现问题，再由修复使其通过。评审报的两条严重项
都是「测试跑 SQLite 所以全绿」掩盖掉的，所以这里特意构造能暴露它们的场景。
"""
import datetime

import pytest
import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.core.db as dbmod
from app import models
from app.core.db import Base, get_db
from app.core.security import hash_password


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    db = Session()
    from app.core.config import settings
    settings.seed_on_start = False
    from app.main import app

    db.add_all([
        models.Workspace(id="ws-a", name="A 团队"),
        models.User(id="u-1", email="a@corp.com", name="甲", role="admin",
                    password_hash=hash_password("pw123456")),
        models.Membership(user_id="u-1", workspace_id="ws-a", role="admin"),
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
        c.headers["Authorization"] = "Bearer " + r.json()["token"]
        c.headers["X-Workspace"] = "ws-a"
        yield c, db
    app.dependency_overrides.clear()
    db.close()
    engine.dispose()


def test_high_risk_filter_is_pushed_down_before_limit(client):
    """高风险记录比 limit 窗口更早时，「仅高风险」仍必须能查到。

    修复前：先 limit(30) 再在 Python 侧过滤 → 最近 30 条里没有高风险就返回空，
    而更早的高风险记录确实存在，界面却说「没有符合条件的记录」。
    """
    c, db = client
    base = datetime.datetime(2026, 1, 1, 0, 0, 0)
    # 3 条高风险（最早），随后 50 条普通操作把它们挤出默认窗口
    for i in range(3):
        db.add(models.AuditLog(workspace_id="ws-a", actor="王", action="修改评分器 rubric",
                               obj=f"C-0{i}", created_at=base + datetime.timedelta(seconds=i)))
    for i in range(50):
        db.add(models.AuditLog(workspace_id="ws-a", actor="李", action="创建 Agent 应用",
                               obj=f"app-{i}", created_at=base + datetime.timedelta(hours=1, seconds=i)))
    db.commit()

    assert len(c.get("/api/system/audits", params={"limit": 30}).json()) == 30
    rows = c.get("/api/system/audits", params={"limit": 30, "high_risk": True}).json()
    assert len(rows) == 3, "高风险记录在 limit 窗口之外时被漏掉了"
    assert all(r["high_risk"] for r in rows)


def test_high_risk_and_actor_intersect_after_pushdown(client):
    c, db = client
    db.add_all([
        models.AuditLog(workspace_id="ws-a", actor="王", action="修改金标准", obj="ds-1"),
        models.AuditLog(workspace_id="ws-a", actor="李", action="重跑评估任务", obj="tk-1"),
        models.AuditLog(workspace_id="ws-a", actor="王", action="邀请成员", obj="赵"),
    ])
    db.commit()
    rows = c.get("/api/system/audits", params={"actor": "王", "high_risk": True}).json()
    assert [r["action"] for r in rows] == ["修改金标准"]


def test_new_membership_always_gets_joined_at():
    """新增的成员关系必须带上加入时间。

    这条测的是**模型定义**，与建表方式无关，所以从 ensure_schema 换成 Alembic 后依然要留着。
    历史上出过的问题：Membership.created_at 用 server_default，而当时手工补的是裸 TIMESTAMP
    没有 DDL 默认值，SQLAlchemy 因 server_default 在 INSERT 中省略该列 → 新成员永远落 NULL。
    修法是改用 Python 侧 default，本测试钉住这个行为。
    """
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(bind=engine)
    s = Session()
    s.add(models.Membership(user_id="u-新", workspace_id="ws-a", role="dev"))
    s.commit()
    row = s.query(models.Membership).filter_by(user_id="u-新").first()
    assert row.created_at is not None, "新成员的加入时间落了 NULL"
    s.close()
    engine.dispose()

def test_app_update_truncates_channel_to_column_length(client):
    """channel 列是 VARCHAR(32)，超长输入必须截断而不是撞库报 500。"""
    c, db = client
    db.add(models.App(id="app-1", workspace_id="ws-a", name="x", type="AgentScope"))
    db.commit()
    r = c.post("/api/apps/app-1/update", json={"channel": "通" * 80})
    assert r.status_code == 200
    assert len(db.get(models.App, "app-1").channel) <= 32
