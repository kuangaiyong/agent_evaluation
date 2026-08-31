from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=10)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass


def ensure_schema():
    """轻量迁移：create_all 不会 ALTER 已有表，这里补幂等的增量 DDL。"""
    from sqlalchemy import text
    extra = {
        "traces": [
            "ALTER TABLE traces ADD COLUMN IF NOT EXISTS otel_trace_id VARCHAR(64)",
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_traces_otel_trace_id ON traces (otel_trace_id)",
        ],
        "evaluators": [
            "ALTER TABLE evaluators ADD COLUMN IF NOT EXISTS metric_code VARCHAR(8)",
            "CREATE INDEX IF NOT EXISTS ix_evaluators_metric_code ON evaluators (metric_code)",
        ],
    }
    with engine.begin() as conn:
        for table, stmts in extra.items():
            for st in stmts:
                try:
                    conn.execute(text(st))
                except Exception:
                    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
