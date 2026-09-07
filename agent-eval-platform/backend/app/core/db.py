import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

log = logging.getLogger("agenteval.db")

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=10)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass


# 给已有表补的列：表名 → [(列名, 类型)]。create_all 只建新表，不会 ALTER 已有表。
ADD_COLUMNS = {
    "traces": [("otel_trace_id", "VARCHAR(64)")],
    "evaluators": [("metric_code", "VARCHAR(8)")],
    "apps": [("channel", "VARCHAR(32)")],
    "dataset_samples": [("gold", "TEXT")],
    "memberships": [("created_at", "TIMESTAMP")],
}

# 索引用 IF NOT EXISTS，这个语法 PostgreSQL 与 SQLite 都支持
ADD_INDEXES = [
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_traces_otel_trace_id ON traces (otel_trace_id)",
    "CREATE INDEX IF NOT EXISTS ix_evaluators_metric_code ON evaluators (metric_code)",
]


def ensure_schema():
    """轻量迁移：补 create_all 覆盖不到的增量 DDL。

    加列走「先查后加」，不用 `ADD COLUMN IF NOT EXISTS`——后者是 PostgreSQL 专有语法，
    SQLite 会报语法错。早先的写法把异常吞掉，结果是迁移在 SQLite 上静默失效，而测试
    （跑的正是 SQLite）照样全绿，等于这些迁移从来没被验证过。先查后加两个方言都支持。

    失败只记日志不抛出：迁移问题不该让服务起不来，但也不能像以前那样无声无息。
    为此**每条 DDL 各开一个事务**——PostgreSQL 里事务块内一条语句失败后，后续语句
    全部 InFailedSqlTransaction，块退出时的 COMMIT 也会抛错，一条失败就会拖垮其余
    补列并让 lifespan 崩溃。共用一个事务时 SQLite 测试照样全绿，掩盖了这一点。
    """
    from sqlalchemy import text, inspect

    def run(stmt, ok_msg, err_msg):
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            if ok_msg:
                log.info(ok_msg)
        except Exception:
            log.exception(err_msg)

    insp = inspect(engine)
    for table, cols in ADD_COLUMNS.items():
        if not insp.has_table(table):
            continue
        existing = {c["name"] for c in insp.get_columns(table)}
        for name, ddl_type in cols:
            if name in existing:
                continue
            run(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}",
                f"已为 {table} 补列 {name}", f"为 {table} 补列 {name} 失败")
    for stmt in ADD_INDEXES:
        run(stmt, None, f"建索引失败：{stmt}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
