"""Kafka 队列工具：网关发布事件、Worker 消费事件（兼容 Collector 直发 proto 与网关 JSON 信封）。"""
import base64
import json
import logging
import time

from .config import settings

log = logging.getLogger("agenteval.kafka")

try:
    from kafka import KafkaProducer, KafkaConsumer  # kafka-python-ng
except Exception:  # pragma: no cover
    KafkaProducer = KafkaConsumer = None


def kafka_enabled() -> bool:
    return bool(settings.kafka_brokers) and KafkaProducer is not None


def make_producer():
    return KafkaProducer(
        bootstrap_servers=settings.kafka_brokers.split(","),
        acks=1, linger_ms=100, retries=5,
        request_timeout_ms=10000, api_version_auto_timeout_ms=10000,
    )


def publish(app_id: str, payload: dict | bytes, encoding: str = "json") -> None:
    """发布摄入事件。payload: dict（json）或 ExportTraceServiceRequest proto bytes（proto）。"""
    if not kafka_enabled():
        raise RuntimeError("Kafka 未配置")
    envelope = {
        "app_id": app_id,
        "encoding": encoding,
        "data": payload if encoding == "json" else base64.b64encode(payload).decode(),
        "ts": int(time.time() * 1000),
    }
    prod = make_producer()
    try:
        prod.send(settings.kafka_topic, key=app_id.encode(), value=json.dumps(envelope).encode("utf-8"))
        prod.flush(timeout=10)
        prod.close(timeout=5)
    except Exception:
        try:
            prod.close(timeout=1)
        except Exception:
            pass
        raise


class ConsumptionMessage:
    def __init__(self):
        self.app_id = ""
        self.raw: bytes | dict | None = None   # proto bytes 或 json dict


def consume_loop(handler, poll_interval: int = 1, max_iters: int = 0):
    """阻塞消费循环。handler(msg: ConsumptionMessage) -> None；异常则写 DLQ 后继续。"""
    if not kafka_enabled():
        raise RuntimeError("Kafka 未配置")
    consumer = KafkaConsumer(
        settings.kafka_topic,
        bootstrap_servers=settings.kafka_brokers.split(","),
        group_id=settings.kafka_group,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        api_version_auto_timeout_ms=10000,
    )
    log.info("Worker 已连接 Kafka %s topic=%s", settings.kafka_brokers, settings.kafka_topic)
    iters = 0
    while True:
        if max_iters and iters >= max_iters:
            break
        iters += 1
        for _, records in consumer.poll(timeout_ms=1000).items():
            for record in records:
                value = record.value or b""
                msg = ConsumptionMessage()
                try:
                    raw_json = json.loads(value.decode("utf-8"))
                    msg.app_id = raw_json.get("app_id", "")
                    if raw_json.get("encoding") == "proto":
                        msg.raw = base64.b64decode(raw_json["data"])
                    else:
                        msg.raw = raw_json.get("data", {})
                except Exception:
                    # Collector 路径：kafkaexporter otlp_proto 编码，消息体即 ExportTraceServiceRequest proto
                    msg.raw = value
                try:
                    handler(msg)
                    consumer.commit()
                except Exception as exc:
                    log.exception("处理失败，写入 DLQ")
                    try:
                        prod = make_producer()
                        prod.send(settings.kafka_dlq, key=msg.app_id.encode() or b"unknown",
                                  value=value)
                        prod.flush(timeout=10)
                        prod.close(timeout=5)
                    except Exception:
                        log.exception("DLQ 写入失败")
                    consumer.commit()
