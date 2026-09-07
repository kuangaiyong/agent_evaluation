"""数据库迁移入口。

取代了原先的 `ensure_schema()` —— 那是一套手写的「先查后加」增量 DDL，它踩过三个坑，
换 Alembic 的动机就是把这三个坑变成框架保证的事：

1. **方言差异**：旧代码最初用 `ADD COLUMN IF NOT EXISTS`，这是 PostgreSQL 专有语法，
   SQLite 报语法错后被 except 吞掉 —— 迁移在测试环境静默失效，而测试（跑的正是 SQLite）
   照样全绿。现在由 Alembic 的 `render_as_batch` 处理，SQLite 走「建新表→拷数据→换名」。
2. **事务粒度**：PostgreSQL 里事务块内一条语句失败后，后续全部 InFailedSqlTransaction。
   旧代码为此不得不给每条 DDL 单开事务。Alembic 按 revision 管理事务，不用手工拆。
3. **无版本概念**：旧代码靠「查一下列在不在」判断是否要补，既慢又无法表达删列、改类型、
   数据迁移。Alembic 有 `alembic_version` 表记录当前版本，升降级都可追溯。

**多实例部署时要关掉 auto_migrate**：并发启动会同时抢着跑迁移。届时改为在部署流程里
单独执行 `alembic upgrade head`，应用启动只做校验。
"""
import logging
import os

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from .config import settings
from .db import engine

log = logging.getLogger("agenteval.migrate")

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _alembic_config() -> Config:
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", settings.database_url))
    return cfg


def current_revision() -> str | None:
    with engine.connect() as conn:
        return MigrationContext.configure(conn).get_current_revision()


def head_revision() -> str | None:
    return ScriptDirectory.from_config(_alembic_config()).get_current_head()


def upgrade_to_head() -> None:
    """把库升到最新版本。

    失败**不吞异常**：schema 没升上去就启动，后果是运行时报「列不存在」，
    比启动失败更难排查。旧的 ensure_schema 吞异常正是它静默失效的原因之一。
    """
    cur, head = current_revision(), head_revision()
    if cur == head:
        log.info("数据库已是最新版本 %s", head)
        return
    log.info("数据库迁移 %s -> %s", cur or "(空库)", head)
    command.upgrade(_alembic_config(), "head")
    log.info("迁移完成")
