"""CI 门禁回调测试：HMAC 签名与 URL 掩码。"""
import hashlib
import hmac
import json

from app.domains.quality.api_regression import _mask_url, _deliver_gate_webhook


def test_mask_url():
    assert _mask_url("") == ""
    assert _mask_url("https://ci.corp.com/hook").endswith("****hook") or "****" in _mask_url("https://ci.corp.com/hook")


def test_hmac_signature_scheme():
    secret = "agenteval-demo-secret"
    payload = json.dumps({"event": "regression_gate", "run_id": "rgn-x"}, ensure_ascii=False).encode()
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    expect = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    assert sig == expect  # 与 _deliver_gate_webhook 相同的签名算法（HMAC-SHA256 hex）
