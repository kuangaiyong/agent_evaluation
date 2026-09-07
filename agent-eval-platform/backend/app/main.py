from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.db import SessionLocal
from .core.migrate import upgrade_to_head
from .core.config import settings
from .seed import seed
from .pipeline.eval_runner.worker import start_worker
from .pipeline.store.clickhouse_store import ensure_schema as ch_ensure_schema
from .domains.identity import api_auth, api_space
from .domains.access import api as api_access
from .domains.observability import api as api_traces
from .domains.evaluation import api_evaluators, api_tasks, api_metrics
from .domains.dataset import api as api_dataset
from .domains.quality import api_badcases, api_regression
from .domains.governance import api as api_notify
from .domains.console import api as api_dashboard
from .pipeline.ingest import otlp, ingest

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_migrate:
        upgrade_to_head()      # 单机部署省事；多实例请关掉它，改在部署流程里跑 alembic upgrade head
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
for r in (api_auth, api_space, api_notify, api_access, ingest, api_traces,
          api_evaluators, api_metrics, api_tasks, api_badcases, api_dataset,
          api_dashboard, api_regression, otlp):
    app.include_router(r.router)

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "agenteval", "mock_judge": not settings.llm_api_key}
