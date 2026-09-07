"""指标库只读接口测试。

用真实文档同步出真实的 92 条字典，走真实登录拿 token，打真实路由——不打桩。
"""
import pathlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.core.db import Base, get_db
from app.core.security import hash_password
from app.domains.evaluation.metric_dict import parse_dictionary, sync_metrics

DOC = (pathlib.Path(__file__).resolve().parents[3]
       / "智能体评测体系" / "01-指标体系与指标字典.md")

pytestmark = pytest.mark.skipif(not DOC.exists(), reason=f"指标字典不在预期路径：{DOC}")


@pytest.fixture()
def api_db():
    """TestClient 在另一个线程跑应用，普通的 :memory: 连接过不去线程边界，
    所以这里用 StaticPool + check_same_thread=False，让两个线程共享同一个内存库。"""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    s = Session()
    yield s, Session
    s.close()
    engine.dispose()


@pytest.fixture()
def db(api_db):
    """本模块用自己的库覆盖 conftest 的 db，测试侧读写走这个 session。"""
    return api_db[0]


@pytest.fixture()
def client(api_db):
    """真实 FastAPI 应用 + 真实登录；关掉 seed，只留本用例要的数据。"""
    db, Session = api_db
    from app.core.config import settings
    settings.seed_on_start = False
    from app.main import app

    db.add_all([
        models.Workspace(id="ws-a", name="A 团队"),
        models.Workspace(id="ws-b", name="B 团队"),
        models.User(id="u-1", email="a@corp.com", name="甲", role="dev",
                    password_hash=hash_password("pw123456")),
        models.Membership(user_id="u-1", workspace_id="ws-a", role="dev"),
        models.Membership(user_id="u-1", workspace_id="ws-b", role="dev"),
    ])
    sync_metrics(db, parse_dictionary(DOC.read_text(encoding="utf-8")))

    def _get_db():
        # 每个请求一个 session，别把测试线程的 session 跨线程共用
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


def test_requires_auth():
    from app.core.config import settings
    settings.seed_on_start = False
    from app.main import app
    with TestClient(app) as c:
        assert c.get("/api/metrics").status_code == 401


def test_list_returns_whole_dictionary(client):
    body = client.get("/api/metrics").json()
    assert body["total"] == 92 and body["count"] == 92
    first = body["items"][0]
    assert first["code"] == "A-01"
    assert first["definition"] and first["threshold"]
    assert first["evaluators"] == []


def test_filters_narrow_the_list(client):
    by_layer = client.get("/api/metrics", params={"layer": "L5"}).json()
    assert by_layer["count"] == 9 and {i["layer"] for i in by_layer["items"]} == {"L5"}

    by_group = client.get("/api/metrics", params={"group": "L"}).json()
    assert by_group["count"] == 8 and {i["group_code"] for i in by_group["items"]} == {"L"}

    by_q = client.get("/api/metrics", params={"q": "L-01"}).json()
    assert by_q["count"] == 1 and by_q["items"][0]["code"] == "L-01"


def test_facets_come_from_data_not_hardcoded(client):
    f = client.get("/api/metrics/facets").json()
    assert set(f["layers"]) == {"L1", "L2", "L3", "L4", "L5", "元"}
    assert "全柱" in f["pillars"], "「全柱」是字典里的真实取值，不能被前端写死的 4 柱漏掉"
    assert len(f["groups"]) == 12


def test_detail_carries_notes_with_source(client):
    m = client.get("/api/metrics/C-08").json()
    assert m["collection"], "C-08 的采集字段已补齐"
    assert "arXiv:2605.27141" in m["notes"], "带出处的实测数字要能从接口读到"


def test_unknown_code_404(client):
    r = client.get("/api/metrics/Z-99")
    assert r.status_code == 404 and "sync_metrics" in r.json()["detail"]


def test_coverage_is_scoped_to_workspace(client, db):
    """B 团队的评估器不能把 A 团队的覆盖度格子填满。"""
    assert client.get("/api/metrics/coverage").json()["done"] == 0

    db.add(models.Evaluator(workspace_id="ws-b", name="B 的评估器", type="llm", metric_code="C-03"))
    db.commit()
    assert client.get("/api/metrics/coverage").json()["done"] == 0, "跨空间泄漏了覆盖度"

    db.add(models.Evaluator(workspace_id="ws-a", name="A 的评估器", type="llm", metric_code="C-03"))
    db.commit()
    cov = client.get("/api/metrics/coverage").json()
    assert cov["done"] == 1 and cov["total"] == 92


def test_list_shows_bound_evaluators(client, db):
    db.add(models.Evaluator(workspace_id="ws-a", name="任务完成度", type="llm",
                            metric_code="C-03", version="v5"))
    db.commit()
    items = client.get("/api/metrics", params={"q": "C-03"}).json()["items"]
    assert [e["name"] for e in items[0]["evaluators"]] == ["任务完成度"]
