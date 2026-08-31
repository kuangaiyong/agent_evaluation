"""OTLP 网关归一化测试：JSON/protobuf 双形态、父子关系、脱敏、跨批次合并。"""
import json

from app.services.otlp_gateway import normalize_export, redact, _decode_bytes64


def span(name, tid, sid, pid, op="", attrs=None, code=0, msg=""):
    return {
        "traceId": tid, "spanId": sid, "parentSpanId": pid, "name": name,
        "startTimeUnixNano": "1000000000", "endTimeUnixNano": "1800000000",
        "attributes": [{"key": k, "value": {"stringValue": str(v)}} for k, v in (attrs or {}).items()]
        + ([{"key": "gen_ai.operation.name", "value": {"stringValue": op}}] if op else []),
        "status": {"code": code, "message": msg},
    }


def make_json_req():
    # traceId/spanId 在 JSON 形态为 base64
    import base64
    tid = base64.b64encode(bytes.fromhex("a" * 32)).decode()
    aid = base64.b64encode(bytes.fromhex("0000000000000001")).decode()
    lid = base64.b64encode(bytes.fromhex("0000000000000002")).decode()
    fmt = base64.b64encode(bytes.fromhex("0000000000000004")).decode()
    req = {"resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "t"}}]},
        "scopeSpans": [{"scope": {}, "spans": [
            span("invoke_agent 测试", tid, aid, "", "invoke_agent",
                 {"gen_ai.input.messages": json.dumps([{"role": "user", "content": "订单 13812345678"}], ensure_ascii=False),
                  "gen_ai.conversation.id": "conv-1"}),
            span("chat m", tid, lid, aid, "chat",
                 {"gen_ai.usage.input_tokens": 10, "gen_ai.usage.output_tokens": 5}),
            span("format x", tid, fmt, aid, "format", {}),
        ]}]}]}
    return req


def test_json_normalization_structure():
    req = make_json_req()
    norm = normalize_export(req, None)
    assert norm["session_id"] == "conv-1"
    assert norm["status"] == "ok"
    # format 被跳过 → 1 turn 1 step（chat）
    assert len(norm["turns"]) == 1
    steps = norm["turns"][0]["steps"]
    assert len(steps) == 1 and steps[0]["kind"] == "llm" and steps[0]["tokens"] == 15
    assert "138****5678" in norm["turns"][0]["message"]
    assert "13812345678" not in norm["turns"][0]["message"]


def test_redact_phone_email():
    assert redact("联系 13812345678 或 zhangsan@corp.com 咨询") == "联系 138****5678 或 zh***@corp.com 咨询"


def test_decode_base64():
    import base64
    assert _decode_bytes64(base64.b64encode(bytes.fromhex("aaaa")).decode()) == "aaaa"


def test_proto_normalization_structure():
    """protobuf 形态：父子关系应正确（一次 invoke_agent 根 = 1 Turn；format/embed 跳过）。"""
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
    tid = bytes.fromhex("bb" * 16)
    aid = bytes.fromhex("0000000000000001")
    lid = bytes.fromhex("0000000000000002")
    fmt = bytes.fromhex("0000000000000004")
    req = ExportTraceServiceRequest()
    rs = req.resource_spans.add()
    ss = rs.scope_spans.add()

    def add(sid, pid, name, op="", code=0):
        s = ss.spans.add()
        s.trace_id = tid
        s.span_id = sid
        if pid:
            s.parent_span_id = pid
        s.name = name
        s.start_time_unix_nano = 1_000_000_000
        s.end_time_unix_nano = 1_800_000_000
        s.status.code = code
        if op:
            kv = s.attributes.add()
            kv.key = "gen_ai.operation.name"
            kv.value.string_value = op

    add(aid, None, "invoke_agent x", "invoke_agent")
    add(lid, aid, "chat m", "chat")
    add(fmt, aid, "format x", "format")
    norm = normalize_export(req, None)
    assert len(norm["turns"]) == 1
    assert len(norm["turns"][0]["steps"]) == 1  # chat；format 跳过
