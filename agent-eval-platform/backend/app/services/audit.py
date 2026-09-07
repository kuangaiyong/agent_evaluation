"""关键操作的高风险判定。

评测结论会影响发布决策，改分数的动机是真实存在的。三类操作能直接改变结论，
因此单独标出来：改评分器 rubric、改金标准、重跑评估任务。

判定放服务端：规则散到前端会导致换个客户端就失效，也没法在审计导出里保持一致。
按 action 文案的关键词匹配——action 是自由文本，各处写法不完全统一，所以匹配的是
「动作 + 对象」的组合词而非全等。
"""

HIGH_RISK_PATTERNS = (
    ("评分器", "rubric"),   # 改评分器 rubric
    ("评分器", "修改"),
    ("金标准",),            # 改金标准
    ("重跑",),              # 重跑评估任务
)


def is_high_risk(action: str) -> bool:
    """action 命中任一组关键词（组内全部出现）即为高风险。"""
    if not action:
        return False
    return any(all(k in action for k in group) for group in HIGH_RISK_PATTERNS)
