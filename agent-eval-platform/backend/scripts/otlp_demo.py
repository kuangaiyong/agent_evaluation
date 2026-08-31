"""OTLP 网关验证脚本：构造 AgentScope 语义的 OTLP 载荷（protobuf + JSON），推送到网关。

用法（在 api 容器内或安装了 opentelemetry-proto 的环境）：
    python scripts/otlp_demo.py [api_base] [api_key]
"""
import sys
import json
import base64
import time

import httpx
from google.protobuf.json_format import MessageToJson

from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.trace.v1.trace_pb2 import Span, Status
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue


def kv(key: str, value) -> KeyValue:
    v = AnyValue()
    if isinstance(value, bool):
        v.bool_value = value
    elif isinstance(value, int):
        v.int_value = value
    else:
        v.string_value = str(value)
    return KeyValue(key=key, value=v)


def span(name: str, tid: bytes, sid: bytes, pid: bytes, op: str = "", attrs: dict = None,
         start: int = 0, dur_ms: int = 800, err: str = "") -> Span:
    s = Span()
    s.trace_id = tid
    s.span_id = sid
    if pid:
        s.parent_span_id = pid
    s.name = name
    s.kind = Span.SpanKind.SPAN_KIND_INTERNAL
    s.start_time_unix_nano = start
    s.end_time_unix_nano = start + dur_ms * 1_000_000
    if op:
        s.attributes.append(kv("gen_ai.operation.name", op))
    for k, v in (attrs or {}).items():
        s.attributes.append(kv(k, v))
    if err:
        s.status.code = Status.StatusCode.STATUS_CODE_ERROR
        s.status.message = err
    else:
        s.status.code = Status.StatusCode.STATUS_CODE_OK
    return s


def build_request() -> ExportTraceServiceRequest:
    trace_id = bytes.fromhex("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    agent_id = bytes.fromhex("0000000000000001")
    llm_id = bytes.fromhex("0000000000000002")
    tool_id = bytes.fromhex("0000000000000003")
    fmt_id = bytes.fromhex("0000000000000004")
    now = time.time_ns()

    spans = [
        # 根：invoke_agent（一次 reply）
        span("invoke_agent 测试用例设计专家", trace_id, agent_id, b"", op="invoke_agent",
             attrs={"gen_ai.agent.name": "测试用例设计专家",
                    "gen_ai.conversation.id": "conv-demo-0001",
                    "gen_ai.input.messages": json.dumps(
                        [{"role": "user", "content": "帮我对微信APP登录功能做测试用例设计，手机号 13812345678 备用"}],
                        ensure_ascii=False)},
             start=now, dur_ms=2600),
        # LLM：chat deepseek-v4-flash（内容序列化 + token usage）
        span("chat deepseek-v4-flash", trace_id, llm_id, agent_id, op="chat",
             attrs={"gen_ai.request.model": "deepseek-v4-flash",
                    "gen_ai.input.messages": json.dumps(
                        [{"role": "system", "content": "你是资深测试工程师"}], ensure_ascii=False),
                    "gen_ai.output.messages": json.dumps(
                        [{"role": "assistant", "content": "# 测试用例设计\n| 用例编号 | 场景 | 预期 |"}],
                        ensure_ascii=False),
                    "gen_ai.usage.input_tokens": 1520,
                    "gen_ai.usage.output_tokens": 1340},
             start=now + 200 * 1_000_000, dur_ms=1800),
        # 工具：execute_tool save_markdown（保存用例文件）
        span("execute_tool save_markdown", trace_id, tool_id, agent_id, op="execute_tool",
             attrs={"gen_ai.tool.name": "save_markdown",
                    "gen_ai.tool.call.arguments": json.dumps(
                        {"path": "testcase_outputs/测试用例_微信登录.md"}, ensure_ascii=False),
                    "gen_ai.tool.call.result": json.dumps({"saved": True, "lines": 42},
                                                          ensure_ascii=False)},
             start=now + 2100 * 1_000_000, dur_ms=120),
        # 失败工具：execute_tool search_orders（演示 error step + 脱敏邮箱）
        span("execute_tool search_orders", trace_id, bytes.fromhex("0000000000000005"), agent_id,
             op="execute_tool",
             attrs={"gen_ai.tool.name": "search_orders",
                    "gen_ai.tool.call.args": "{}",
                    "gen_ai.tool.call.result": "{}",
                    "agentscope.function.input": json.dumps(
                        {"email": "zhangsan@corp.com, order 13812345678"}, ensure_ascii=False)},
             start=now + 2250 * 1_000_000, dur_ms=300, err="HTTP 404 · NoSuchLogistics"),
        # 应被跳过的 span：format
        span("format messages", trace_id, fmt_id, agent_id, op="format",
             attrs={"agentscope.format.count": 2}, start=now + 100 * 1_000_000, dur_ms=50),
    ]
    req = ExportTraceServiceRequest()
    rs = req.resource_spans.add()
    rs.resource.attributes.append(kv("service.name", "testcase-designer-agent"))
    ss = rs.scope_spans.add()
    ss.scope.name = "agentscope"
    for sp in spans:
        ss.spans.append(sp)
    return req


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    key = sys.argv[2] if len(sys.argv) > 2 else "ak_live_demo_ast001"

    req = build_request()

    # 1) protobuf
    t0 = time.time()
    r = httpx.post(
        f"{base}/api/otlp/v1/traces",
        content=req.SerializeToString(),
        headers={"content-type": "application/x-protobuf", "x-api-key": key},
        timeout=15,
    )
    print(f"[protobuf] HTTP {r.status_code} ({time.time() - t0:.2f}s) => {r.content[:80]}")

    # 2) JSON（base64 traceId）
    body = json.loads(MessageToJson(req))
    jr = httpx.post(
        f"{base}/api/otlp/v1/traces",
        json=body,
        headers={"content-type": "application/json", "x-api-key": key},
        timeout=15,
    )
    print(f"[json]     HTTP {jr.status_code} => {jr.text[:120]}")

    # 3) 幂等：重发 protobuf
    r2 = httpx.post(
        f"{base}/api/otlp/v1/traces",
        content=req.SerializeToString(),
        headers={"content-type": "application/x-protobuf", "x-api-key": key},
        timeout=15,
    )
    print(f"[dedup]    HTTP {r2.status_code}（重复 traceId 应成功且不新增）")


if __name__ == "__main__":
    main()
