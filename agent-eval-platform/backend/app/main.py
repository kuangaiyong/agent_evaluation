from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import Base, engine, SessionLocal, ensure_schema
from .config import settings
from .seed import seed
from .services.worker import start_worker
from .services.clickhouse_store import ensure_schema as ch_ensure_schema
from .routers import (auth, system, notifications, apps, ingest, traces, evaluators, metrics,
                      tasks, badcases, datacenter, dashboard, regression, otlp)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    ch_ensure_schema()
    if settings.seed_on_start:
        db = SessionLocal()
        try:
            seed(db)
        finally:
            db.close()
    worker = start_worker()
    yield
    worker.cancel()

app = FastAPI(title="TAgentEval 智能体评测平台", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
for r in (auth, system, notifications, apps, ingest, traces, evaluators, metrics,
          tasks, badcases, datacenter, dashboard, regression, otlp):
    app.include_router(r.router)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "agenteval", "mock_judge": not settings.llm_api_key}
