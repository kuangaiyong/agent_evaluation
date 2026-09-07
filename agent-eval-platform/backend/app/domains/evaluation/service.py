"""评估引擎：规则指标 / LLM-as-Judge（OpenAI 兼容 or 内置 Mock）/ 人工反馈。
所有评估器输出必须归一化到 [0,1]，越界拒绝并记为评估失败。"""
import json, random, re, difflib
import httpx
from ...core.config import settings

class ScoreOutOfRange(Exception):
    pass

def _clamp(s: float) -> float:
    s = round(float(s), 4)
    if s < 0 or s > 1:
        raise ScoreOutOfRange(s)
    return s

def _steps_of(trace) -> list[dict]:
    return [st for t in trace.payload.get("turns", []) for st in t.get("steps", [])]

def _tool_stats(trace):
    steps = [s for s in _steps_of(trace) if s["kind"] == "tool"]
    ok = sum(1 for s in steps if s["status"] == "ok")
    return ok, len(steps)

def _rule_score(eval_cfg, trace) -> tuple[float, str]:
    steps = _steps_of(trace)
    reasons = []
    score = 1.0
    cfg = eval_cfg or {}
    if cfg.get("tool_success"):
        ok, total = _tool_stats(trace)
        if total:
            score = min(score, ok / total)
            reasons.append(f"工具调用成功率 {ok}/{total}")
    if cfg.get("keywords"):
        kws = cfg["keywords"]
        if kws:
            texts = json.dumps(trace.payload, ensure_ascii=False)
            hit = sum(1 for k in kws if k in texts)
            score = min(score, 0.3 + 0.7 * (hit / len(kws)))
            reasons.append(f"关键词命中 {hit}/{len(kws)}")
    if cfg.get("regex"):
        try:
            if not re.search(cfg["regex"], json.dumps(trace.payload, ensure_ascii=False)):
                score = min(score, 0.0)
                reasons.append("正则未命中")
        except re.error:
            reasons.append("正则非法（跳过）")
    if cfg.get("schema") and isinstance(cfg["schema"], dict):
        out = trace.payload.get("turns", [{}])[-1].get("steps", [{}])[-1].get("output", "")
        ok = _schema_ok(cfg["schema"], out)
        score = min(score, 1.0 if ok else 0.0)
        reasons.append("JSON Schema 校验" + ("通过" if ok else "不通过"))
    if cfg.get("no_error"):
        errs = sum(1 for s in steps if s["status"] == "error")
        score = min(score, 1.0 if errs == 0 else max(0.0, 1 - errs * 0.2))
        reasons.append(f"错误步骤 {errs} 个")
    return _clamp(score), "；".join(reasons) or "规则全部通过"

def _schema_ok(schema, out: str) -> bool:
    if not isinstance(out, str):
        out = json.dumps(out, ensure_ascii=False)
    try:
        data = json.loads(out)
    except Exception:
        return False
    if schema.get("type") == "object" and not isinstance(data, dict):
        return False
    for k in schema.get("required", []):
        if k not in data:
            return False
    return True

MOCK_JUDGE_EXCUSES = [
    "回答与工具事实存在矛盾，证据支持度不足",
    "用户目标未被完整满足，关键步骤缺失",
    "回答正确且引用了工具证据，用户目标达成",
    "存在轻度幻觉：在不可证明状态上继续生成",
    "规划合理，工具调用得当，中间步骤可复核",
    "回答格式不合规，未按约定输出 JSON 结构",
]

def _mock_judge(eval_cfg, trace, quality_hint: float = None) -> tuple[float, str]:
    """离线可跑的确定性 Mock：基于工具成功率/错误步数/长度启发式 + 少量波动。"""
    ok, total = _tool_stats(trace)
    steps = _steps_of(trace)
    errs = sum(1 for s in steps if s["status"] == "error")
    base = 0.95
    if total:
        base = base * (0.35 + 0.65 * (ok / total))
    base -= errs * 0.12
    n_turns = len(trace.payload.get("turns", []))
    base = min(1.0, base + min(n_turns - 1, 3) * 0.03)
    # 抖动保证每次调用略有差异（演示效果）
    base += random.uniform(-0.04, 0.04)
    if quality_hint is not None:
        base = (base + quality_hint) / 2
    reason = MOCK_JUDGE_EXCUSES[min(len(MOCK_JUDGE_EXCUSES) - 1, max(0, int((1 - base) * 6)))]
    return _clamp(base), f"[Mock Judge] {reason}"

def _llm_judge(eval_cfg, trace, quality_hint: float = None, db=None) -> tuple[float, str]:
    cfg = eval_cfg or {}
    if settings.llm_api_key and settings.llm_api_base:
        try:
            prompt = cfg.get("prompt") or (
                "你是评分裁判。请基于工具事实证据评判 Agent 表现，输出 JSON {\"score\": <0-1>, \"reason\": \"...\"}。"
            )
            body = {
                "model": cfg.get("judge_model") or settings.llm_judge_model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": json.dumps(trace.payload, ensure_ascii=False)[:12000]},
                ],
                "temperature": float(cfg.get("temperature", 0.1)),
            }
            r = httpx.post(f"{settings.llm_api_base.rstrip('/')}/chat/completions",
                           json=body, headers={"Authorization": f"Bearer {settings.llm_api_key}"}, timeout=30)
            r.raise_for_status()
            resp = r.json()
            content = resp["choices"][0]["message"]["content"]
            m = re.search(r"\{[^{}]*\}", content)
            data = json.loads(m.group(0)) if m else {"score": 0.5, "reason": content}
            usage = resp.get("usage") or {}
            if db is not None:
                from .budget import JudgeBudget
                JudgeBudget(db).record(
                    cfg.get("judge_model") or settings.llm_judge_model,
                    int(usage.get("prompt_tokens") or 0),
                    int(usage.get("completion_tokens") or 0))
            return _clamp(data.get("score", 0.5)), f"[LLM Judge {cfg.get('judge_model', '')}] " + str(data.get("reason", ""))
        except Exception as e:
            return _mock_judge(eval_cfg, trace, quality_hint)[0], f"[Judge 回退 Mock] {e}"
    return _mock_judge(eval_cfg, trace, quality_hint)

def run_evaluator(ev: dict, trace, quality_hint: float = None, db=None) -> dict:
    """返回 {score, reason, failed}"""
    cfg = ev.config if isinstance(ev.config, dict) else {}
    try:
        if ev.type == "rule":
            score, reason = _rule_score(cfg, trace)
        elif ev.type in ("llm", "agent"):
            if db is not None and settings.llm_api_key:
                from .budget import JudgeBudget
                if JudgeBudget(db).exceeded():
                    return {"score": None, "reason": "裁判模型日额度已达上限，本次跳过真实调用（任务将自动暂停）",
                            "failed": False, "budget_hit": True}
            score, reason = _llm_judge(cfg, trace, quality_hint, db)
        else:  # human：自动评估返回 None（等待人工）
            return {"score": None, "reason": "人工评估器，待标注", "failed": False}
        return {"score": score, "reason": reason, "failed": False}
    except ScoreOutOfRange:
        return {"score": None, "reason": "Score 越界（>1 或 <0），已拒绝并记为评估失败", "failed": True}
    except Exception as e:
        return {"score": None, "reason": f"评估异常：{e}", "failed": True}

def quality_hint_of(trace):
    """Bad/Good 先验，仅用于 Mock 演示更贴近原型数值。"""
    payload = trace.payload or {}
    first_msg = (payload.get("turns") or [{}])[0].get("message", "")
    if "WX20260821" in first_msg or "订单" in first_msg:
        return 0.30
    if "重构" in first_msg or "缓存" in first_msg:
        return 0.90
    return None
