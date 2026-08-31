"""OTLP/HTTP Trace 摄入端点（自研网关）。

POST /api/otlp/v1/traces
- content-type: application/x-protobuf（默认） / application/json
- 鉴权头: x-api-key（或 Authorization: Bearer <key>）
- 响应: ExportTraceServiceResponse（与请求编码一致；JSON 模式返回 partialSuccess）
"""
import json
import logging
import http

from fastapi import APIRouter, Depends, Header, Request, Response, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from .. import models
from ..services.otlp_gateway import ingest_otel_payload
from ..config import settings
from ..kafkaio import kafka_enabled, publish
from ..services.worker import eval_trace_on_tasks
from ..services.clickhouse_store import write_trace_and_events

router = APIRouter(prefix="/api/otlp", tags=["otlp"])

log = logging.getLogger("agenteval.otlp")

PROTOBUF = "application/x-protobuf"


def _decode_body(body: bytes, content_type: str):
    content_type = (content_type or PROTOBUF).split(";")[0].strip().lower()
    if content_type.startswith("application/json"):
        try:
            return json.loads(body.decode("utf-8")) if body else {}
        except Exception as exc:
            raise HTTPException(400, detail=f"OTLP JSON 解析失败: {exc}")
    if content_type == PROTOBUF or not content_type:
        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
            ExportTraceServiceRequest,
        )
        req = ExportTraceServiceRequest()
        try:
            req.ParseFromString(body or b"")
        except Exception as exc:
            raise HTTPException(400, detail=f"OTLP protobuf 解析失败: {exc}")
        return req
    raise HTTPException(415, detail=f"不支持的 Content-Type: {content_type}")


def _encode_response(ok: bool, rejected: int, content_type: str) -> tuple[bytes, str]:
    content_type = (content_type or PROTOBUF).split(";")[0].strip().lower()
    if content_type.startswith("application/json"):
        data = {"partialSuccess": {"rejectedSpans": rejected or 0,
                                   "errorMessage": "" if ok else "网关处理失败"}}
        return json.dumps(data).encode("utf-8"), "application/json"
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
        ExportTraceServiceResponse,
    )
    resp = ExportTraceServiceResponse()
    resp.partial_success.rejected_spans = rejected or 0
    if not ok:
        resp.partial_success.error_message = "网关处理失败"
    return resp.SerializeToString(), PROTOBUF


def _resolve_app(db: Session, x_api_key: str, authorization: str) -> models.App | None:
    key = x_api_key
    if not key and authorization.startswith("Bearer "):
        key = authorization[7:]
    if not key:
        return None
    return db.query(models.App).filter_by(api_key=key).first()


@router.post("/v1/traces")
async def otlp_ingest(request: Request,
                      x_api_key: str = Header(default=""),
                      authorization: str = Header(default=""),
                      db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", PROTOBUF)
    body = await request.body()
    app = _resolve_app(db, x_api_key, authorization)
    if not app:
        # OTLP 语义：非 2xx 触发 exporter 重试；401 应避免无限重试，用 400 标明
        raise HTTPException(401, "无效的 x-api-key，请在接入中心获取")

    try:
        decoded = _decode_body(body, content_type)
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("OTLP 网关处理失败")
        data, ct = _encode_response(False, 1, content_type)
        return Response(content=data, media_type=ct, status_code=200)

    # 生产化：Kafka 队列削峰（发布即返回）；Kafka 未配置或发布失败则内联处理（开发模式）
    if kafka_enabled():
        try:
            encoding = "json" if isinstance(decoded, dict) else "proto"
            payload = decoded if isinstance(decoded, dict) else decoded.SerializeToString()
            publish(app.id, payload, encoding)
            log.info("已发布至 Kafka topic=%s app=%s", settings.kafka_topic, app.name)
            data, ct = _encode_response(True, 0, content_type)
            return Response(content=data, media_type=ct, status_code=200)
        except Exception as exc:
            log.warning("Kafka 发布失败，降级为内联处理：%s", exc)

    trace = ingest_otel_payload(db, app, decoded)
    from ..services.worker import eval_trace_on_tasks
    tasks = db.query(models.EvalTask).filter_by(mode="online", status="running",
                                                workspace_id=app.workspace_id).all()
    if tasks:
        eval_trace_on_tasks(db, tasks, trace)
    write_trace_and_events(db, trace)

    data, ct = _encode_response(True, 0, content_type)
    return Response(content=data, media_type=ct, status_code=200)
