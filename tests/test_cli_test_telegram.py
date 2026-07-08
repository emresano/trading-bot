# tests/test_cli_test_telegram.py
"""F5-B2a.1 — main.py `--test-telegram` alt komutu (notifier durumu + maskeli test
mesajı). `notifier` enjekte edilir → gerçek HTTP/ağ YOK."""
from __future__ import annotations

import main as main_mod
from notify.telegram_bot import TelegramConfig, TelegramNotifier


def _patch_config(monkeypatch, enabled: bool):
    monkeypatch.setattr(main_mod, "load_config", lambda path: {"telegram": {"enabled": enabled}})
    monkeypatch.setattr(main_mod, "_load_secrets", lambda: ())


def test_test_telegram_log_only_no_token(monkeypatch, capsys):
    _patch_config(monkeypatch, enabled=True)
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    rc = main_mod._cmd_test_telegram("ignored.yaml")
    out = capsys.readouterr().out
    assert rc == 1
    assert "LOG-ONLY" in out and "TELEGRAM_TOKEN" in out
    assert "gönderilmedi" in out


def test_test_telegram_config_disabled(monkeypatch, capsys):
    _patch_config(monkeypatch, enabled=False)
    monkeypatch.setenv("TELEGRAM_TOKEN", "SECRET-TOK-123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    rc = main_mod._cmd_test_telegram("ignored.yaml")
    out = capsys.readouterr().out
    assert rc == 1
    assert "LOG-ONLY" in out and "kasıtlı kapalı" in out
    assert "SECRET-TOK-123" not in out


def test_test_telegram_active_sends_masked_message(monkeypatch, capsys):
    _patch_config(monkeypatch, enabled=True)
    monkeypatch.setenv("TELEGRAM_TOKEN", "SECRET-TOK-123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    sent = []
    fake_notifier = TelegramNotifier(TelegramConfig(enabled=True, chat_id="42", token_present=True),
                                     sender=sent.append, known_secrets=("SECRET-TOK-123",))
    rc = main_mod._cmd_test_telegram("ignored.yaml", notifier=fake_notifier)
    out = capsys.readouterr().out
    assert rc == 0
    assert "ACTIVE" in out
    assert "BAŞARILI" in out
    assert sent, "test mesajı gönderilmedi"
    assert "SECRET-TOK-123" not in out and "SECRET-TOK-123" not in sent[0]


def test_test_telegram_send_failure_reflected_in_exit_code(monkeypatch, capsys):
    _patch_config(monkeypatch, enabled=True)
    monkeypatch.setenv("TELEGRAM_TOKEN", "TOK")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")

    def _boom_factory(tok, cid):
        def _s(_text):
            raise TimeoutError("timeout")
        return _s

    fake_notifier = TelegramNotifier(TelegramConfig(enabled=True, chat_id="42", token_present=True),
                                     http_factory=_boom_factory)
    rc = main_mod._cmd_test_telegram("ignored.yaml", notifier=fake_notifier)
    out = capsys.readouterr().out
    assert rc == 1
    assert "BAŞARISIZ" in out
