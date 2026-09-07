"""增量迁移的回归测试。

为什么值得单独测：早先 ensure_schema 用的是 `ADD COLUMN IF NOT EXISTS`——PostgreSQL
专有语法，SQLite 报语法错后被 except 吞掉。结果迁移在测试环境静默失效，而测试套件
（跑的正是 SQLite）全绿，等于这几条迁移从来没被验证过。这个文件就是防它复发。
"""
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import app.db as dbmod


def _cols(engine, table):
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def _with_engine(monkeypatch):
    """把 db 模块的 engine 换成一次性内存库，避免碰到真实配置。"""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    monkeypatch.setattr(dbmod, "engine", engine)
    return engine


def test_adds_missing_column_to_existing_table(monkeypatch):
    """模拟存量库：apps 表已存在但没有 channel 列。"""
    engine = _with_engine(monkeypatch)
    with engine.begin() as c:
        c.execute(sa.text("CREATE TABLE apps (id VARCHAR(32) PRIMARY KEY, name VARCHAR(64), type VARCHAR(32))"))
        c.execute(sa.text("INSERT INTO apps (id, name, type) VALUES ('app-old', '存量应用', 'AgentScope')"))
    assert "channel" not in _cols(engine, "apps")

    dbmod.ensure_schema()

    assert "channel" in _cols(engine, "apps"), "存量表必须被补上新列"
    row = engine.connect().execute(sa.text("SELECT name, type, channel FROM apps WHERE id='app-old'")).first()
    assert row == ("存量应用", "AgentScope", None), "原有行不能被破坏，新列为空"


def test_is_idempotent(monkeypatch):
    engine = _with_engine(monkeypatch)
    with engine.begin() as c:
        c.execute(sa.text("CREATE TABLE apps (id VARCHAR(32) PRIMARY KEY, name VARCHAR(64))"))
    dbmod.ensure_schema()
    before = _cols(engine, "apps")
    dbmod.ensure_schema()          # 重复执行不应报错也不应重复加列
    assert _cols(engine, "apps") == before


def test_skips_absent_tables(monkeypatch):
    """表还不存在时（全新库，create_all 尚未跑）应安静跳过，不抛异常。"""
    engine = _with_engine(monkeypatch)
    dbmod.ensure_schema()
    assert not sa.inspect(engine).has_table("apps")


def test_all_declared_columns_are_applied(monkeypatch):
    """ADD_COLUMNS 里声明的每一列都要真的落到表上——防止只改声明没生效。"""
    engine = _with_engine(monkeypatch)
    with engine.begin() as c:
        for table in dbmod.ADD_COLUMNS:
            c.execute(sa.text(f"CREATE TABLE {table} (id VARCHAR(32) PRIMARY KEY)"))
    dbmod.ensure_schema()
    for table, cols in dbmod.ADD_COLUMNS.items():
        got = _cols(engine, table)
        for name, _ in cols:
            assert name in got, f"{table}.{name} 声明了却没落库"
