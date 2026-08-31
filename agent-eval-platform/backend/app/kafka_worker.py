"""Kafka 消费 Worker：从 ingest 队列消费 OTLP 事件 → 归一化 → 落库 → 自动评估。

两种事件源可混用：
1. FastAPI OTLP 网关（鉴权入口）：JSON 信封 {app_id, encoding, data}，已解出应用
2. OTel Collector（内网可信入口）：kafkaexporter 直接写入 ExportTraceServiceRequest proto，
   应用归属由 Resource 属性 agenteval.app.id 决定（回退 service.name 精确匹配）
"""
import base64
import logging
import re
import sys

from .config import settings
from .db import SessionLocal
from . import models
from .services import otlp_gateway
from .services.worker import eval_trace_on_tasks
from .services.clickhouse_store import write_trace_and_events
from .kafkaio import consume_loop, ConsumptionMessage

log = logging.getLogger("agenteval.kafka.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


def _proto_from_bytes(raw: bytes):
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
    req = ExportTraceServiceRequest()
    req.ParseFromString(raw)
    return req


def _resource_attr(req, key: str) -> str:
    try:
        for rs in req.resource_spans:
            for kv in rs.resource.attributes:
                if kv.key == key:
                    return str(kv.value.string_value or kv.value.stringValue or "")
    except Exception:
        pass
    return ""


def resolve_app(db, msg: ConsumptionMessage):
    if msg.app_id:
        return db.get(models.App, msg.app_id)
    raw = msg.raw
    if hasattr(raw, "resource_spans"):
        candidate = _resource_attr(raw, "agenteval.app.id") or _resource_attr(raw, "service.name")
        if not candidate:
            return None
        found = db.get(models.App, candidate)
        if found:
            return found
        # service.name 语义：优先精确匹配应用名
        return db.query(models.App).filter(models.App.name == candidate).first()
    return None


def handle(msg: ConsumptionMessage) -> None:
    db = SessionLocal()
    try:
        raw = msg.raw
        if isinstance(raw, bytes):
            msg.raw = _proto_from_bytes(raw)
        app = resolve_app(db, msg)
        if not app:
            raise ValueError("无法识别 Application（缺少 app_id / agenteval.app.id / service.name 映射）")
        req = msg.raw
        trace, merged = otlp_gateway.ingest_otel_payload(db, app, req)
        if merged:
            # 合并补齐后清空旧评估与 Bad Case，重新评估
            db.query(models.ScoreRecord).filter_by(trace_id=trace.id).delete()
            db.query(models.BadCase).filter_by(trace_id=trace.id).delete()
            trace.score_avg = None
            trace.evaluated = False
            db.commit()
        tasks = db.query(models.EvalTask).filter_by(mode="online", status="running",
                                                    workspace_id=app.workspace_id).all()
        if tasks:
            eval_trace_on_tasks(db, tasks, trace)
        write_trace_and_events(db, trace)
        log.info("已处理 %s -> trace %s（会话 %s）", app.name, trace.id, trace.session_id)
    finally:
        db.close()


def main() -> None:
    log.info("AgentEval Worker 启动 · Kafka=%s topic=%s group=%s",
             settings.kafka_brokers, settings.kafka_topic, settings.kafka_group)
    try:
        consume_loop(handle)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
