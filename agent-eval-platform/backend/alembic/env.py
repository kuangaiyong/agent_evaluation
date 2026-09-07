"""Alembic 运行环境。

三个关键配置，每个都对应一个踩过的坑：

1. **连接串从 app.core.config 读，不写在 alembic.ini 里**
   否则 ini 里的 URL 与应用实际用的 DATABASE_URL 会漂移，迁移跑在错误的库上。

2. **target_metadata 取自 app.models 这个聚合入口**
   聚合入口 import 了所有域的模型，Base.metadata 才收得全。直接 import
   `core.db.Base` 拿到的是空 metadata —— autogenerate 会认为「所有表都该删掉」。

3. **render_as_batch=True**
   SQLite 不支持大部分 ALTER TABLE 语法。旧的 ensure_schema 就栽在这里：
   用了 PostgreSQL 专有的 `ADD COLUMN IF NOT EXISTS`，SQLite 报语法错后被 except
   吞掉，迁移在测试环境静默失效而测试照样全绿。batch 模式让 Alembic 在 SQLite 上
   走「建新表 → 拷数据 → 换名」，两个方言都能跑。
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# 让 alembic 能 import 到 app 包（alembic/ 与 app/ 同级）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings          # noqa: E402
from app.core.db import Base                  # noqa: E402
import app.models                             # noqa: E402,F401  聚合入口，触发全部域的模型注册

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 取值优先级：调用方显式设定 > DATABASE_URL 环境变量 > app 配置。
#
# 注意「调用方优先」这一条不能省：早先这里无条件用环境变量覆盖，结果是
# `config.set_main_option("sqlalchemy.url", ...)` 形同虚设 —— 测试指定了临时库，
# 迁移却跑到 DATABASE_URL 指向的内存库上，跑完即消失，表一张也没建出来。
_url = config.get_main_option("sqlalchemy.url", None) or os.getenv("DATABASE_URL") or settings.database_url
config.set_main_option("sqlalchemy.url", _url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,      # 类型变化也纳入 autogenerate，否则改字段类型会被漏掉
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
