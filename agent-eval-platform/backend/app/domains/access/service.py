"""接入通道的口径。

通道按被测对象的**形态**划分，不按产品名——按产品名切分的老口径（AgentScope /
OpenCode / HTTP API）遇到新工具就无处归类，CodeBuddy 就是被它卡住的例子。

存量应用没有 channel 字段，读接口按 type 推导；显式赋值优先于推导。
"""

CHANNEL_PY = "① Python Agent"
CHANNEL_PILOT = "② Pilot"
CHANNEL_OTLP = "③ OTLP 直推"

# 智能体类型 → 通道。未登记的类型一律落到 ③：它是兜底通道，任何支持 OTLP 的工具都能走。
TYPE_TO_CHANNEL = {
    "AgentScope": CHANNEL_PY,      # 应用内插桩，包裹启动命令
    "OpenCode": CHANNEL_PILOT,     # 本地 Coding CLI，Pilot 注入插件
    "Hermes Agent": CHANNEL_PILOT,  # 同上
}


def channel_of(app) -> str:
    """应用的接入通道：显式赋值优先，为空时按 type 推导。"""
    explicit = (getattr(app, "channel", None) or "").strip()
    return explicit or TYPE_TO_CHANNEL.get(app.type, CHANNEL_OTLP)
