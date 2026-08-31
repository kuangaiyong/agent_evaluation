"""演示：向本地平台推一条轨迹（可用作 SDK 接入示例）。"""
import sys, json, urllib.request

BASE = "http://localhost:8000"

def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "ak_live_demo_ast001"
    payload = {
        "session_id": "s-demo-0001",
        "model": "qwen-plus",
        "version": "v2.4.1",
        "turns": [{
            "role": "user",
            "message": "帮我查一下订单 WX20260821 的物流信息",
            "steps": [
                {"kind": "tool", "name": "工具 · search_orders", "tool": "search_orders",
                 "status": "ok", "duration_ms": 340, "output": {"found": True, "logistics": "运输中"}},
                {"kind": "llm", "name": "LLM · 生成回复", "status": "ok", "duration_ms": 820,
                 "tokens": 360, "output": "您的订单正在运输中，预计明天送达。"},
            ],
        }],
    }
    req = urllib.request.Request(f"{BASE}/api/ingest/trace", data=json.dumps(payload).encode(),
                                 headers={"x-api-key": key, "content-type": "application/json"})
    print(urllib.request.urlopen(req).read().decode())

if __name__ == "__main__":
    main()
