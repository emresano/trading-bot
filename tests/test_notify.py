# tests/test_notify.py
"""F5A-7 — izleme + Telegram iskeleti testleri (HARDENING B6). Token'sız, HTTP yok."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from notify.telegram_bot import (
    TelegramNotifier, TelegramConfig, CommandRouter, make_http_sender,
)
from notify.eod_summary import build_eod_summary
from safety.heartbeat import write_heartbeat, heartbeat_age_sec, Watchdog


class _Resp:
    def __init__(self, status_code):
        self.status_code = status_code


# ------------------------------------------------------------------ notifier
def test_notifier_disabled_is_noop():
    n = TelegramNotifier(TelegramConfig(enabled=False))
    assert n.send("merhaba") is False
    assert n.sent == ["merhaba"]  # denetim izi tutulur ama gönderilmez


def test_notifier_uses_injected_sender_and_masks():
    captured = []
    n = TelegramNotifier(TelegramConfig(enabled=True), sender=captured.append)
    assert n.send("token=API-SECRET123 fill oldu") is True
    assert "API-SECRET123" not in captured[0]
    assert "***" in captured[0]


# ------------------------------------------------------------------ gerçek HTTP gönderici (mock)
def test_http_sender_posts_masked_payload_on_success():
    posts = []
    send = make_http_sender("TOK", "42", poster=lambda p: posts.append(p) or _Resp(200))
    send("merhaba")
    assert posts == [{"chat_id": "42", "text": "merhaba"}]


def test_http_sender_retries_then_succeeds():
    calls = {"n": 0}
    sleeps = []

    def poster(_payload):
        calls["n"] += 1
        return _Resp(200 if calls["n"] == 3 else 500)

    send = make_http_sender("TOK", "42", poster=poster, sleep=sleeps.append)
    send("x")
    assert calls["n"] == 3                 # iki başarısız + bir başarılı
    assert sleeps == [1.0, 2.0]            # üstel bekleme (base×2^attempt)


def test_http_sender_raises_after_persistent_failure():
    def poster(_payload):
        raise ConnectionError("ağ yok")

    send = make_http_sender("TOK", "42", poster=poster, sleep=lambda _s: None)
    with pytest.raises(ConnectionError):
        send("x")


def test_notifier_builds_http_sender_from_env(monkeypatch):
    """enabled + token(env) + chat_id → gerçek HTTP göndericisi kurulur; sender enjekte YOK."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "SECRET-TOK")
    posts = []
    factory = lambda tok, cid: (lambda text: posts.append((tok, cid, text)))
    n = TelegramNotifier(TelegramConfig(enabled=True, chat_id="42", token_present=True),
                         http_factory=factory, known_secrets=("SECRET-TOK",))
    assert n.send("selam") is True
    assert posts == [("SECRET-TOK", "42", "selam")]


def test_notifier_persistent_failure_never_raises_and_warns(monkeypatch):
    monkeypatch.setenv("TELEGRAM_TOKEN", "TOK")
    warns = []

    def boom_factory(tok, cid):
        def _s(_text):
            raise TimeoutError("timeout")
        return _s

    n = TelegramNotifier(TelegramConfig(enabled=True, chat_id="42", token_present=True),
                         http_factory=boom_factory, logger=warns.append)
    assert n.send("mesaj") is False        # döngü kırılmaz
    assert n.sent == ["mesaj"]             # denetim izi yine tutulur
    assert warns and "kalıcı başarısız" in warns[0]


def test_notifier_no_token_stays_log_only(monkeypatch):
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    n = TelegramNotifier(TelegramConfig(enabled=True, chat_id="42", token_present=True))
    assert n.send("x") is False            # göndericisiz → log-only
    assert n.sent == ["x"]


# ------------------------------------------------------------------ komut router
def _router(**kw):
    return CommandRouter(allowed_chat_id="42", **kw)


def test_unauthorized_chat_rejected():
    r = _router(status_provider=lambda: "OK")
    assert "REDDEDİLDİ" in r.handle("999", "/status")


def test_status_readonly():
    r = _router(status_provider=lambda: "equity=100000")
    assert r.handle("42", "/status") == "equity=100000"


def test_action_requires_double_confirm():
    calls = []
    r = _router(pause_fn=lambda: calls.append("pause"))
    first = r.handle("42", "/pause")
    assert "ONAY GEREKLİ" in first and calls == []   # tek komutla çalışmaz
    second = r.handle("42", "/pause CONFIRM")
    assert "onaylandı" in second and calls == ["pause"]


def test_kill_requires_confirm():
    calls = []
    r = _router(kill_fn=lambda: calls.append("kill"))
    assert "ONAY GEREKLİ" in r.handle("42", "/kill")
    assert calls == []
    assert "onaylandı" in r.handle("42", "/kill CONFIRM")
    assert calls == ["kill"]


@pytest.mark.parametrize("cmd", ["/real", "/real CONFIRM", "/gercek", "/golive", "/go_live"])
def test_no_real_command_exists(cmd):
    """Durma Noktası 2: 'real moda geç' komutu HİÇBİR biçimde yok — hepsi reddedilir,
    hiçbir fonksiyon çağrılmaz."""
    calls = []
    r = _router(pause_fn=lambda: calls.append("x"), kill_fn=lambda: calls.append("x"))
    reply = r.handle("42", cmd)
    assert "REDDEDİLDİ" in reply and "Durma Noktası 2" in reply
    assert calls == []


def test_unknown_command():
    r = _router()
    assert "bilinmeyen" in r.handle("42", "/wat")


# ------------------------------------------------------------------ heartbeat / watchdog
def test_heartbeat_write_and_age(tmp_path):
    p = tmp_path / "heartbeat"
    write_heartbeat(p)
    age = heartbeat_age_sec(p)
    assert age is not None and age < 5
    assert heartbeat_age_sec(tmp_path / "yok") is None


def test_watchdog_alarms_when_stale(tmp_path):
    p = tmp_path / "heartbeat"
    write_heartbeat(p)
    n = TelegramNotifier(TelegramConfig(enabled=True), sender=lambda t: None)
    wd = Watchdog(n, stale_sec=900, path=p)
    now = datetime.now(timezone.utc)
    assert wd.check(now=now) is False               # taze
    stale_now = now + timedelta(seconds=1000)
    assert wd.check(now=stale_now) is True           # bayat → alarm
    assert any("CRITICAL" in m for m in n.sent)
    # tekrar bayat → aynı alarm bir kez (latch)
    before = len(n.sent)
    wd.check(now=stale_now)
    assert len(n.sent) == before


def test_watchdog_missing_heartbeat_is_stale(tmp_path):
    n = TelegramNotifier(TelegramConfig(enabled=True), sender=lambda t: None)
    wd = Watchdog(n, stale_sec=900, path=tmp_path / "yok")
    assert wd.check() is True


# ------------------------------------------------------------------ EOD özet
def test_eod_summary_contents():
    s = build_eod_summary(date="2024-06-03", equity=101_000, cash=101_000, day_pnl=250,
                          in_position=False, breaker_state="OK", frozen_switches=[],
                          modeled_interest_total=1234, next_calendar_note="yarım gün")
    assert "NAKİT" in s and "101,000" in s and "+250" in s
    assert "Modellenmiş faiz" in s and "yarım gün" in s
