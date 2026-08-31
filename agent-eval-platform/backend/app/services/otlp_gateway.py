"""OTLP 网关：接收 OpenTelemetry OTLP/HTTP Trace 数据，归一化为平台 Trajectory。

覆盖：
- 内容协商：application/x-protobuf（默认）与 application/json
- 多租户鉴权：x-api-key（或 Authorization: Bearer）→ 应用/工作空间
- 字段归一化：OTel Span → Session/Turn/Step（AgentScope GenAI 语义 + 通用规则）
- 密钥脱敏：入参/出参/messages 中的 PII（手机号/邮箱/身份证）打码
- 幂等去重：otel_trace_id 唯一，exporter 重试不产生重复数据
"""
import json
import re
import datetime
import base64
import logging

from sqlalchemy.orm import Session

from ..config import settings
from .. import models
from ..services.assembler import touch_app

log = logging.getLogger("agenteval.otlp")

# ---------- 支持的操作名（GenAI semantic conventions 的 gen_ai.operation.name）----------
OP_CHAT = "chat"
OP_TOOL = "execute_tool"
OP_INVOKE_AGENT = "invoke_agent"
SKIP_OPS = {x.strip() for x in settings.otlp_skip_span_ops.split(",") if x.strip()}

# ---------- 属性键 ----------
ATTR = {
    "operation": "gen_ai.operation.name",
    "agent_name": "gen_ai.agent.name",
    "agent_id": "gen_ai.agent.id",
    "conversation": "gen_ai.conversation.id",
    "model": "gen_ai.request.model",
    "input_messages": "gen_ai.input.messages",
    "output_messages": "gen_ai.output.messages",
    "input_tokens": "gen_ai.usage.input_tokens",
    "output_tokens": "gen_ai.usage.output_tokens",
    "tool_name": "gen_ai.tool.name",
    "tool_args": "gen_ai.tool.call.arguments",
    "tool_result": "gen_ai.tool.call.result",
    "func_input": "agentscope.function.input",
    "func_name": "agentscope.function.name",
    "func_output": "agentscope.function.output",
}

_PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_IDCARD = re.compile(r"\d{17}[\dXx]")


def redact(text: str) -> str:
    """PII 脱敏：保留前 3 后 2，中间打码。"""
    if not isinstance(text, str) or not text:
        return text
    text = _IDCARD.sub(lambda m: m.group(0)[:6] + "*********" + m.group(0)[-1], text)
    text = _PHONE.sub(lambda m: m.group(0)[:3] + "****" + m.group(0)[-4:], text)
    text = _EMAIL.sub(lambda m: m.group(0)[:2] + "***@" + m.group(0).split("@")[1], text)
    return text


def _truncate(text: str) -> str:
    maxc = settings.otlp_max_attr_chars
    if text and len(text) > maxc:
        return text[: maxc // 2] + "\n[truncated]\n" + text[-maxc // 2 :]
    return text


def _decode_bytes64(value) -> str:
    """OTLP traceId/spanId：protobuf 为 bytes，JSON 为 base64。"""
    try:
        if isinstance(value, str):
            raw = base64.b64decode(value)
        else:
            raw = bytes(value)
        return raw.hex()
    except Exception:
        return ""


def _field(obj, camel, default=None):
    """兼容 protobuf 消息（snake_case）与 JSON dict（camelCase）两种 OTLP 形态。"""
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", camel).lower()
    try:
        if isinstance(obj, dict):
            return obj.get(camel, obj.get(snake, default))
        if hasattr(obj, snake):
            return getattr(obj, snake)
        if hasattr(obj, camel):
            return getattr(obj, camel)
    except Exception:
        pass
    return default


# ---------- 属性序列化 ----------
def _attr_value(value) -> object:
    """把 OTLP AnyValue 转为 Python 值（AttributeValue 为 protobuf 消息或 dict）。"""
    if value is None:
        return None
    get = getattr(value, "WhichOneof", None)
    if get is not None:
        kind = get("value")
        if kind is None:
            return None
        v = getattr(value, kind)
        if kind == "arrayValue":
            return [_attr_value(x) for x in (v.values or [])]
        if kind == "kvlistValue":
            return {kv.key: _attr_value(kv.value) for kv in (v.values or [])}
        return v
    if isinstance(value, dict):
        for k in ("stringValue", "intValue", "boolValue", "doubleValue"):
            if k in value:
                return value[k]
        if "arrayValue" in value:
            return [_attr_value(x) for x in value["arrayValue"].get("values", [])]
        if "kvlistValue" in value:
            return {kv["key"]: _attr_value(kv["value"]) for kv in value["kvlistValue"].get("values", [])}
        return value.get("stringValue")
    return value


def _attrs_to_dict(attributes) -> dict:
    """OTLP RepeatedField<KeyValue> → dict。"""
    out = {}
    for kv in attributes or []:
        key = kv.key if hasattr(kv, "key") else kv.get("key", "")
        val = _attr_value(kv.value if hasattr(kv, "value") else kv.get("value"))
        if isinstance(val, int):
            val = int(val)
        out[key] = val
    return out


def _norm_text(value) -> str:
    """把属性值转成便于展示的文本（JSON 字符串尝试解析为对象）。"""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return _truncate(redact(json.dumps(value, ensure_ascii=False)))
    s = str(value)
    # AgentScope 将 messages 序列化为 JSON 字符串，尝试还原为对象展示
    if s.startswith("[") or s.startswith("{"):
        try:
            obj = json.loads(s)
            return _truncate(redact(json.dumps(obj, ensure_ascii=False)))
        except Exception:
            pass
    return _truncate(redact(s))


def _span_status(span) -> tuple[str, str]:
    """返回 (status, error_message)。status.code: 0=UNSET 1=OK 2=ERROR"""
    try:
        st = _field(span, "status")
        code = _field(st, "code", 0)
        msg = _field(st, "message", "")
    except Exception:
        code, msg = 0, ""
    if code == 2:
        return "error", msg or "span error"
    return "ok", ""


# ---------- 主流程：请求 → Trajectory ----------
def normalize_export(request, app: models.App) -> dict:
    """把 ExportTraceServiceRequest（protobuf 消息或 dict）归一化为轨迹字典与 OTel 元信息。"""
    resource_spans = _field(request, "resourceSpans") or []
    spans = []
    for rs in resource_spans:
        for ss in _field(rs, "scopeSpans") or []:
            scope = _field(ss, "scope") or {}
            scope_name = _field(scope, "name", "")
            for sp in _field(ss, "spans") or []:
                spans.append((sp, scope_name))
    if not spans:
        raise ValueError("OTLP 内容为空：未找到任何 span")

    trace_id = _decode_bytes64(_field(spans[0][0], "traceId", ""))
    all_span_ids = {_decode_bytes64(_field(sp, "spanId", "")) for sp, _ in spans}

    span_infos = []
    children: dict[str, list[int]] = {}
    roots = []
    for idx, (sp, scope_name) in enumerate(spans):
        attrs = _attrs_to_dict(_field(sp, "attributes") or [])
        sid = _decode_bytes64(_field(sp, "spanId", ""))
        pid = _decode_bytes64(_field(sp, "parentSpanId", ""))
        st = _span_status(sp)
        start = int(_field(sp, "startTimeUnixNano", 0) or 0)
        end = int(_field(sp, "endTimeUnixNano", 0) or 0)
        info = {
            "id": sid, "parent": pid, "attrs": attrs, "name": _field(sp, "name", "") or "",
            "kind": "tool" if (attrs.get(ATTR["operation"]) == OP_TOOL
                                  or (attrs.get(ATTR["operation"]) not in SKIP_OPS
                                      and attrs.get(ATTR["func_name"])))
            else ("llm" if attrs.get(ATTR["operation"]) == OP_CHAT else "other"),
            "operation": attrs.get(ATTR["operation"]) or "",
            "status": st[0], "error": st[1],
            "start": start, "end": end, "duration_ms": max(0, (end - start) // 1_000_000),
            "tokens": ((int(attrs.get(ATTR["input_tokens"]) or 0)) +
                       (int(attrs.get(ATTR["output_tokens"]) or 0))),
            "scope": scope_name,
        }
        span_infos.append(info)
        children.setdefault(pid, []).append(idx)
        if not pid or pid not in all_span_ids:
            roots.append(idx)

    # 会话：优先 gen_ai.conversation.id，回退 trace_id
    conversation = ""
    for info in span_infos:
        conversation = info["attrs"].get(ATTR["conversation"]) or conversation
    session_id = str(conversation or trace_id or f"s-otel-{uuid_hex()}")[:64]

    # 每个 root span → 一个 Turn（含其子孙 span 作为 Step）
    turns = []
    seen = set()

    def collect(idx: int) -> list[dict]:
        out = [] if span_infos[idx]["kind"] == "other" else [_to_step(span_infos[idx])]
        seen.add(idx)
        for ci in children.get(span_infos[idx]["id"], []):
            if ci not in seen:
                out.extend(collect(ci))
        return out

    for ridx in sorted(roots, key=lambda i: span_infos[i]["start"]):
        root = span_infos[ridx]
        seen.add(ridx)
        steps = []
        for ci in children.get(root["id"], []):
            steps.extend(collect(ci))
        if not steps and root["kind"] != "other":
            steps = [_to_step(root)]
        turn_msg = _norm_text(root["attrs"].get(ATTR["input_messages"])) or "用户请求"
        turns.append({"role": "user", "message": turn_msg[:4000], "steps": steps[:60]})

    if not turns:
        turns = [{"role": "user", "message": "用户请求", "steps": [_to_step(s) for s in span_infos if s["kind"] != "other"][:60]}]

    has_error = any(info["status"] == "error" for info in span_infos)
    total_dur = sum(t["duration_ms"] for t in span_infos)
    total_tok = sum(t["tokens"] for t in span_infos)
    user_msg = turns[0]["message"] if turns else ""

    return {
        "otel_trace_id": trace_id,
        "session_id": session_id,
        "model": next((str(i["attrs"].get(ATTR["model"]) or "") for i in span_infos if i["attrs"].get(ATTR["model"])), (app.model if app else "") or ""),
        "status": "error" if has_error else "ok",
        "duration_ms": total_dur,
        "tokens": total_tok,
        "turns": turns,
        "user_message": user_msg,
    }


def _to_step(info: dict) -> dict:
    attrs = info["attrs"]
    if info["kind"] == "tool":
        fname = attrs.get(ATTR["func_name"])
        return {
            "kind": "tool", "name": f"工具 · {attrs.get(ATTR['tool_name']) or fname or info['name']}",
            "tool": str(attrs.get(ATTR["tool_name"]) or fname or "tool"), "status": info["status"],
            "duration_ms": info["duration_ms"], "tokens": 0,
            "input": _norm_text(attrs.get(ATTR["tool_args"])) or _norm_text(attrs.get(ATTR["func_input"])),
            "output": _norm_text(attrs.get(ATTR["tool_result"])) or _norm_text(attrs.get(ATTR["func_output"])),
            "error": info["error"], "model": "",
        }
    return {
        "kind": "llm", "name": info["name"] or "LLM · 调用", "tool": "",
        "status": info["status"], "duration_ms": info["duration_ms"], "tokens": info["tokens"],
        "input": _norm_text(attrs.get(ATTR["input_messages"])) or _norm_text(attrs.get(ATTR["func_input"])),
        "output": _norm_text(attrs.get(ATTR["output_messages"])) or _norm_text(attrs.get(ATTR["func_output"])),
        "error": info["error"], "model": str(attrs.get(ATTR["model"]) or ""),
    }


def uuid_hex() -> str:
    import uuid
    return uuid.uuid4().hex[:8]


def _step_count(norm) -> int:
    return sum(len(t.get("steps", [])) for t in norm.get("turns", []))


def ingest_otel_payload(db: Session, app: models.App, request, norm: dict | None = None):
    """归一化 + 落库 + 幂等去重 + 跨批量合并。

    AgentScope 会分批导出同一会话的 span（如第一批仅 formatter span、第二批才是
    chat/invoke_agent），每批携带同一 traceId。合并策略：
    - 已存在的 trace 若步骤更少，用新批次补齐（替换 payload/状态/token），并返回 merged=True
      （调用方需清空旧评估后重评）；
    - 幂等：新批次不包含有效步骤时直接跳过。
    返回 (trace, merged)。
    """
    norm = norm or normalize_export(request, app)
    tid = norm["otel_trace_id"]
    new_steps = _step_count(norm)
    if tid:
        exist = db.query(models.Trace).filter_by(app_id=app.id, otel_trace_id=tid).first()
        if exist:
            old_steps = _step_count({"turns": exist.payload.get("turns", [])})
            # 按 (kind, name) 签名做步骤并集：AgentScope 分多批导出，每批可能只含部分 span
            seen = {(st["kind"], st["name"]) for t in exist.payload.get("turns", []) for st in t.get("steps", [])}
            merged = []
            for t in norm["turns"]:
                for st in t.get("steps", []):
                    sig = (st["kind"], st["name"])
                    if sig not in seen:
                        seen.add(sig)
                        merged.append(st)
            if merged:
                log.info("跨批次合并：trace %s 追加 %d 步（%s -> %s）", tid, len(merged), old_steps, old_steps + len(merged))
                exist_turns = list(exist.payload.get("turns", []))
                if exist_turns:
                    exist_turns[0]["steps"] = exist_turns[0].get("steps", []) + merged
                else:
                    exist_turns = [{"role": "user", "message": norm.get("user_message", "用户请求"), "steps": merged}]
                exist.payload = {"turns": exist_turns}
                exist.tokens = (exist.tokens or 0) + norm["tokens"]
                exist.duration_ms = (exist.duration_ms or 0) + norm["duration_ms"]
                if norm["status"] == "error":
                    exist.status = "error"
                exist.model = norm["model"] or exist.model
                exist.score_avg = None
                exist.evaluated = False
                db.commit()
                return exist, True
            log.info("幂等：OTel trace %s 已存在（无新步骤），跳过", tid)
            return exist, False
    trace = models.Trace(
        workspace_id=app.workspace_id, app_id=app.id, session_id=norm["session_id"],
        model=norm["model"], version=app.version, status=norm["status"],
        duration_ms=norm["duration_ms"], tokens=norm["tokens"],
        cost=round(norm["tokens"] / 1_000_000 * 0.02, 4),
        otel_trace_id=tid,
        payload={"turns": norm["turns"]},
    )
    touch_app(app)
    db.add(trace)
    db.commit()
    db.refresh(trace)
    return trace, False
