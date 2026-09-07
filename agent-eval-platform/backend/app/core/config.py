from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://agenteval:agenteval@localhost:5433/agenteval"
    jwt_secret: str = "change-me-in-prod-please"
    jwt_expire_minutes: int = 24 * 60
    llm_api_base: str = ""
    llm_api_key: str = ""
    llm_judge_model: str = "qwen-max"
    auto_eval_interval: int = 5
    upload_dir: str = "/data/uploads"
    seed_on_start: bool = True
    # 启动时自动把库升到最新版本。多实例部署要关掉：并发启动会同时抢着跑迁移。
    auto_migrate: bool = True
    otlp_skip_span_ops: str = "format,embed"   # 网关默认跳过这些操作的 span
    otlp_max_attr_chars: int = 8000
    # Kafka 队列（生产化网关：FastAPI 鉴权入口 → Kafka → Worker 消费 → 归一化/评估）
    kafka_brokers: str = ""              # 为空 = 直连模式（开发/单机）；设置后走队列
    kafka_topic: str = "agenteval-ingest"
    kafka_dlq: str = "agenteval-ingest-dlq"
    kafka_group: str = "agenteval-worker"
    # 真实 LLM-as-Judge 成本保护
    judge_daily_limit_yuan: float = 50.0
    # 回归门禁 Webhook（CI 回调）
    gate_webhook_url: str = ""
    gate_webhook_secret: str = ""
    # ClickHouse 事件层（轨迹/评分事件 · TTL 热数据 30 天 · 仪表盘聚合读 CH）
    clickhouse_enabled: bool = False
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_user: str = "agenteval"
    clickhouse_password: str = "agenteval"
    clickhouse_db: str = "agenteval"

    class Config:
        env_file = ".env"

settings = Settings()
