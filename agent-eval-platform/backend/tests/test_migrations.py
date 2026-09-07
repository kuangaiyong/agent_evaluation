"""Alembic 迁移的回归测试。

取代原先的 test_ensure_schema.py。被测对象变了（手写增量 DDL → Alembic），
但要守住的东西没变：**声明了的表结构必须真的落到库上，且不能静默失效**。

原来的坑是「PG 专有语法在 SQLite 上报错被吞掉，迁移形同虚设而测试全绿」。
换 Alembic 后对应的新坑是「改了 model 忘了生成 migration」—— 同样静默，
同样能让测试全绿。test_no_pending_model_changes 就是挡这个的。
"""
import os

import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext

from app import models  # noqa: F401  聚合入口，必须先 import 才能收全 metadata
from app.core.db import Base

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cfg(url):
    c = Config(os.path.join(BACKEND, "alembic.ini"))
    c.set_main_option("script_location", os.path.join(BACKEND, "alembic"))
    c.set_main_option("sqlalchemy.url", url)
    return c


def _fresh_db(tmp_path):
    """建一个跑完全部迁移的临时库。"""
    url = "sqlite:///" + str(tmp_path / "m.db").replace("\\", "/")
    command.upgrade(_cfg(url), "head")
    return url


def test_upgrade_creates_every_declared_table(tmp_path):
    """空库跑完迁移后，表必须与 metadata 声明的完全一致。

    少建一张表不会报错，只会在运行时报「表不存在」—— 正是要挡的那类静默失效。
    """
    url = _fresh_db(tmp_path)
    engine = sa.create_engine(url)
    got = set(sa.inspect(engine).get_table_names()) - {"alembic_version"}
    want = set(Base.metadata.tables)
    assert got == want, f"少建 {sorted(want - got)}；多建 {sorted(got - want)}"
    engine.dispose()


def test_columns_that_used_to_need_manual_backfill_are_present(tmp_path):
    """这五列原先靠 ensure_schema 的 ADD_COLUMNS 手工补，现在必须由迁移建出来。

    它们是历史上真出过问题的列，单独钉住，防止拆分 models 或改迁移时漏掉。
    """
    url = _fresh_db(tmp_path)
    engine = sa.create_engine(url)
    insp = sa.inspect(engine)
    for table, col in [("traces", "otel_trace_id"), ("evaluators", "metric_code"),
                       ("apps", "channel"), ("dataset_samples", "gold"),
                       ("memberships", "created_at")]:
        cols = {c["name"] for c in insp.get_columns(table)}
        assert col in cols, f"{table}.{col} 没被迁移建出来"
    engine.dispose()


def test_no_pending_model_changes(tmp_path):
    """模型与迁移之间不得有漂移。

    挡的是最容易犯也最难发现的错：改了 domains/*/models.py 却忘了
    `alembic revision --autogenerate`。代码照跑、测试照绿，直到部署到一个
    全新环境才发现表结构对不上。
    """
    url = _fresh_db(tmp_path)
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True,
                                                     "render_as_batch": True})
        diff = compare_metadata(ctx, Base.metadata)
    engine.dispose()
    assert not diff, (
        "模型与迁移不一致，请跑 `alembic revision --autogenerate -m \"...\"` 补一版迁移。\n"
        "差异：\n" + "\n".join("  " + str(d) for d in diff))


def test_upgrade_is_idempotent(tmp_path):
    """重复升级到 head 不应报错 —— 部署脚本可能重复执行。"""
    url = _fresh_db(tmp_path)
    command.upgrade(_cfg(url), "head")      # 第二次，应安静返回
    engine = sa.create_engine(url)
    with engine.connect() as conn:
        rev = MigrationContext.configure(conn).get_current_revision()
    assert rev is not None
    engine.dispose()


def test_downgrade_to_base_removes_everything(tmp_path):
    """能降级回空库。

    不是为了真的回滚生产，而是验证迁移写全了 downgrade —— autogenerate 生成的
    downgrade 若被手工改坏，只有真跑一次才知道。
    """
    url = _fresh_db(tmp_path)
    command.downgrade(_cfg(url), "base")
    engine = sa.create_engine(url)
    left = set(sa.inspect(engine).get_table_names()) - {"alembic_version"}
    engine.dispose()
    assert not left, f"降级后仍残留表：{sorted(left)}"
