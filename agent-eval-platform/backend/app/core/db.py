import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings

log = logging.getLogger("agenteval.db")

# 表结构演进由 Alembic 负责，见 core/migrate.py。
# 这里只管连接与会话 —— 早先的 ensure_schema() 手写增量 DDL 已移除。

engine = create_engine(settings.database_url, pool_pre_ping=True, pool_size=10)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
