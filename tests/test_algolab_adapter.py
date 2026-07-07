# tests/test_algolab_adapter.py
"""F5A-8 — AlgoLab adapter iskeleti testleri. AĞSIZ / CANLI ÇAĞRI YOK (fixture)."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import stat

import pandas as pd
import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from core.models import Side
from execution.broker_adapter import BrokerError
from execution.algolab.auth import AlgoLabAuth
from execution.algolab.client import RateLimitedClient, AlgoLabRateLimit
from execution.algolab.adapter import AlgoLabAdapter, _parse_candles, _parse_positions

_KEY = b"0123456789abcdef0123456789abcdef"          # 32 bayt AES anahtarı
_API_CODE = base64.b64encode(_KEY).decode()
_API_KEY = "API-" + _API_CODE


def _auth(transport=None, session_file="runtime/_test_session.json"):
    return AlgoLabAuth(_API_KEY, "12345678901", "sifre123", transport=transport,
                       session_file=session_file)


# ------------------------------------------------------------------ kripto
def test_encrypt_roundtrip():
    a = _auth()
    ct = a._encrypt("hello")
    # AES-CBC IV=0 ile çöz → orijinal
    cipher = AES.new(_KEY, AES.MODE_CBC, b"\0" * 16)
    pt = unpad(cipher.decrypt(base64.b64decode(ct)), 16).decode()
    assert pt == "hello"


def test_checker_is_sha256():
    a = _auth()
    endpoint, payload = "/api/LoginUser", {"a": 1}
    expected = hashlib.sha256((_API_KEY + endpoint + json.dumps(payload).replace(" ", "")).encode()).hexdigest()
    assert a._checker(endpoint, payload) == expected


def test_no_transport_blocks_live_call():
    """F5-A: transport yoksa canlı çağrı YASAK — açık hata."""
    a = _auth(transport=None)
    with pytest.raises(BrokerError, match="canlı çağrı YASAK"):
        a.login_user()


# ------------------------------------------------------------------ login akışı (fixture transport)
def test_login_flow_and_session_file_600(tmp_path):
    calls = []

    def fake_transport(endpoint, payload, headers):
        calls.append((endpoint, payload, headers))
        if endpoint == "/api/LoginUser":
            return {"success": True, "content": {"token": "TOK123"}}
        if endpoint == "/api/LoginUserControl":
            return {"success": True, "content": {"hash": "HASH_ABC"}}
        return {"success": False, "message": "?"}

    sf = tmp_path / "session.json"
    a = _auth(transport=fake_transport, session_file=sf)
    a.login_user()
    assert a.token == "TOK123"
    a.login_user_control("123456")
    assert a.hash == "HASH_ABC"
    # session dosyası yazıldı + 600 izni
    assert sf.exists()
    assert stat.S_IMODE(os.stat(sf).st_mode) == 0o600
    # login çağrıları APIKEY + Checker başlıklarını taşıdı
    assert all("APIKEY" in h and "Checker" in h for _, _, h in calls)


def test_load_session(tmp_path):
    sf = tmp_path / "session.json"
    sf.write_text(json.dumps({"hash": "H1"}))
    a = _auth(session_file=sf)
    assert a.load_session() is True and a.hash == "H1"


def test_failed_login_raises(tmp_path):
    a = _auth(transport=lambda e, p, h: {"success": False, "message": "hatalı şifre"},
              session_file=tmp_path / "s.json")
    with pytest.raises(BrokerError, match="hatalı şifre"):
        a.login_user()


# ------------------------------------------------------------------ throttle / backoff
def test_client_throttles():
    t = {"v": 0.0}
    slept = []
    client = RateLimitedClient(transport=lambda e, p, h: {"success": True},
                               throttle_sec=5.0, sleep_fn=lambda s: slept.append(s),
                               monotonic_fn=lambda: t["v"])
    client.request("/x", {}, {})   # ilk istek: bekleme yok
    assert slept == []
    client.request("/x", {}, {})   # hemen ardından: ~5s bekle
    assert slept and abs(slept[0] - 5.0) < 1e-9


def test_client_backoff_then_success():
    seq = iter([AlgoLabRateLimit(), AlgoLabRateLimit(), {"success": True, "ok": 1}])
    slept = []

    def transport(e, p, h):
        v = next(seq)
        if isinstance(v, Exception):
            raise v
        return v

    client = RateLimitedClient(transport=transport, throttle_sec=0.0,
                               sleep_fn=lambda s: slept.append(s), monotonic_fn=lambda: 0.0)
    res = client.request("/x", {}, {})
    assert res["ok"] == 1
    assert slept == [5.0, 10.0]   # iki geri çekilme sonra başarı


def test_client_gives_up_after_retries():
    def transport(e, p, h):
        raise AlgoLabRateLimit()
    client = RateLimitedClient(transport=transport, throttle_sec=0.0,
                               sleep_fn=lambda s: None, monotonic_fn=lambda: 0.0)
    with pytest.raises(BrokerError, match="rate-limit"):
        client.request("/x", {}, {})


# ------------------------------------------------------------------ parse (fixture)
def test_parse_candles():
    payload = {"content": [
        {"Date": "2024-01-02T21:00:00Z", "Open": 100, "High": 105, "Low": 99, "Close": 104, "Volume": 1000},
        {"Date": "2024-01-03T21:00:00Z", "Open": 104, "High": 106, "Low": 103, "Close": 105, "Volume": 1200},
    ]}
    df = _parse_candles(payload)
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.tz is not None and len(df) == 2
    assert df["close"].iloc[-1] == 105.0


def test_parse_positions_skips_zero():
    payload = {"content": [{"code": "THYAO", "totalstock": "100", "cost": "95.5"},
                           {"code": "GARAN", "totalstock": "0", "cost": "0"}]}
    pos = _parse_positions(payload)
    assert len(pos) == 1 and pos[0].symbol == "THYAO" and pos[0].quantity == 100


# ------------------------------------------------------------------ adapter (fixture transport)
def test_adapter_submit_market_order_builds_sendorder():
    captured = {}

    def transport(endpoint, payload, headers):
        captured["endpoint"] = endpoint
        captured["payload"] = payload
        return {"success": True, "content": {"orderId": "ORD-9"}}

    auth = _auth()
    auth.hash = "SESSIONHASH"   # login edilmiş varsay
    client = RateLimitedClient(transport=transport, throttle_sec=0.0,
                               sleep_fn=lambda s: None, monotonic_fn=lambda: 0.0)
    adapter = AlgoLabAdapter(auth, client)
    ids = adapter.submit_market_order("THYAO", Side.BUY, 50)
    assert ids == ["ORD-9"]
    assert captured["endpoint"] == "/api/SendOrder"
    assert captured["payload"]["symbol"] == "THYAO"
    assert captured["payload"]["direction"] == "BUY"
    assert captured["payload"]["lot"] == "50"
