# notify/telegram_bot.py
"""Telegram bildirim + komut iskeleti (HARDENING B6, Faz 5 F5A-7).

CONFIG-GATED: telegram.enabled=false ya da token yoksa notifier no-op (yalnız loglar).
TOKEN'SIZ TEST: `sender` enjekte edilebilir (fixture test → gerçek HTTP YOK, F5-A).

Komut güvenliği (B6 + CLAUDE.md 13.4):
- Yalnızca izinli chat_id kabul edilir (diğer herkes reddedilir).
- Durum komutları READ-ONLY: /status, /report.
- Eylem komutları ÇİFT ONAY ister: /pause, /resume, /kill (`... CONFIRM`).
- **"real moda geç" komutu HİÇBİR BİÇİMDE YOK** (Durma Noktası 2'nin uzantısı) —
  router böyle bir komutu tanımaz ve açıkça reddeder.
Tüm giden mesajlar journal.masking ile maskelenir (token/hash/TC no sızmaz).
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable, Optional

from journal.masking import mask_secret

TELEGRAM_API = "https://api.telegram.org"

# Kesinlikle var olmayacak / reddedilecek komut kökleri (Durma Noktası 2).
_FORBIDDEN = {"real", "gorec", "gerçek", "gercek", "golive", "go_live", "live_real"}
_ACTION_CMDS = {"pause", "resume", "kill"}
_READONLY_CMDS = {"status", "report"}


@dataclass
class TelegramConfig:
    enabled: bool = False
    chat_id: Optional[str] = None      # izinli tek chat
    token_present: bool = False        # secrets.env'de TELEGRAM_TOKEN var mı (değeri DEĞİL)


def make_http_sender(token: str, chat_id: str, *, timeout: float = 10.0, retries: int = 3,
                     base_backoff: float = 1.0,
                     poster: Optional[Callable[[dict], object]] = None,
                     sleep: Optional[Callable[[float], None]] = None) -> Callable[[str], None]:
    """Gerçek Bot API `sendMessage` göndericisi (F5-B2a).

    - timeout + 3 deneme + üstel bekleme (base_backoff × 2^attempt).
    - Kalıcı başarısızlıkta son istisnayı YÜKSELTİR; çağıran (TelegramNotifier.send)
      bunu yakalar → günlük döngü ASLA bildirim yüzünden kırılmaz.
    - `poster`/`sleep` test için enjekte edilir (gerçek HTTP/uyku YOK).
    Token URL'e gömülür; asla loglanmaz (çağıran zaten maskeli metin gönderir)."""
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    _sleep = sleep or time.sleep

    def _default_poster(payload: dict) -> object:
        import requests  # lazy — offline/token'sız yollarda import yok
        return requests.post(url, json=payload, timeout=timeout)

    post = poster or _default_poster

    def _send(text: str) -> None:
        payload = {"chat_id": chat_id, "text": text}
        last_exc: Optional[BaseException] = None
        for attempt in range(retries):
            try:
                resp = post(payload)
                if getattr(resp, "status_code", None) == 200:
                    return
                code = getattr(resp, "status_code", "?")
                last_exc = RuntimeError(f"Telegram HTTP {code}")
            except Exception as exc:  # ağ/timeout — tekrar dene
                last_exc = exc
            if attempt < retries - 1:
                _sleep(base_backoff * (2 ** attempt))
        raise last_exc or RuntimeError("Telegram gönderimi kalıcı başarısız")

    return _send


class TelegramNotifier:
    """Giden bildirim. `sender(text)` enjekte edilebilir (test); yoksa+enabled+token
    varsa gerçek Bot API HTTP göndericisi kurulur. enabled=False → no-op (log-only).

    Kalıcı gönderim hatası çağırana YANSIMAZ: yakalanır, `logger` varsa WARN düşer,
    `send` False döner — günlük döngü bildirim yüzünden kırılmaz."""

    def __init__(self, config: TelegramConfig, sender: Optional[Callable[[str], None]] = None,
                 known_secrets=(), logger: Optional[Callable[[str], None]] = None,
                 http_factory: Optional[Callable[..., Callable[[str], None]]] = None):
        self.config = config
        self.known_secrets = tuple(known_secrets)
        self._logger = logger
        # sender enjekte edilmediyse ve etkinse: gerçek HTTP göndericisi (token env'den).
        if sender is None and config.enabled:
            sender = self._build_http_sender(http_factory)
        self._sender = sender
        self.sent: list[str] = []   # test/denetim izi (maskeli)

    def _build_http_sender(self, http_factory) -> Optional[Callable[[str], None]]:
        token = os.environ.get("TELEGRAM_TOKEN")
        chat_id = self.config.chat_id
        if not token or not chat_id:
            return None   # token/chat yoksa log-only davranış korunur
        factory = http_factory or make_http_sender
        return factory(token, str(chat_id))

    def send(self, text: str) -> bool:
        masked = mask_secret(text, self.known_secrets)
        self.sent.append(masked)
        if not self.config.enabled or self._sender is None:
            return False
        try:
            self._sender(masked)
            return True
        except Exception as exc:
            # kalıcı başarısızlık — döngüyü kırma, WARN düş (maskeli).
            if self._logger is not None:
                try:
                    self._logger(mask_secret(
                        f"Telegram gönderimi kalıcı başarısız: {type(exc).__name__}",
                        self.known_secrets))
                except Exception:
                    pass
            return False


class CommandRouter:
    """Gelen Telegram komutlarını yönlendirir. Eylem komutları çift onaylı; 'real' YOK."""

    def __init__(self, allowed_chat_id: str,
                 status_provider: Optional[Callable[[], str]] = None,
                 report_provider: Optional[Callable[[], str]] = None,
                 pause_fn: Optional[Callable[[], None]] = None,
                 resume_fn: Optional[Callable[[], None]] = None,
                 kill_fn: Optional[Callable[[], None]] = None):
        self.allowed_chat_id = str(allowed_chat_id)
        self.status_provider = status_provider
        self.report_provider = report_provider
        self.pause_fn = pause_fn
        self.resume_fn = resume_fn
        self.kill_fn = kill_fn

    def handle(self, chat_id, text: str) -> str:
        if str(chat_id) != self.allowed_chat_id:
            return "REDDEDİLDİ: yetkisiz chat_id"
        parts = text.strip().split()
        if not parts:
            return "boş komut"
        cmd = parts[0].lstrip("/").lower()
        confirm = len(parts) > 1 and parts[1].upper() == "CONFIRM"

        if cmd in _FORBIDDEN:
            return ("REDDEDİLDİ: 'real'/gerçek-para moduna geçiş komutu YOKTUR ve "
                    "hiçbir zaman olmayacaktır (Durma Noktası 2). Bu yalnızca kullanıcının "
                    "editörde elle yapabileceği bir eylemdir.")

        if cmd in _READONLY_CMDS:
            if cmd == "status":
                return self.status_provider() if self.status_provider else "durum sağlayıcı yok"
            return self.report_provider() if self.report_provider else "rapor sağlayıcı yok"

        if cmd in _ACTION_CMDS:
            if not confirm:
                return f"ONAY GEREKLİ: eylemi doğrulamak için `/{cmd} CONFIRM` gönderin."
            if cmd == "pause":
                if self.pause_fn:
                    self.pause_fn()
                return "PAUSE onaylandı — yeni ENTER durduruldu (kill-switch dosyası yazıldı)."
            if cmd == "resume":
                if self.resume_fn:
                    self.resume_fn()
                return "RESUME onaylandı — kill-switch temizlendi."
            if cmd == "kill":
                if self.kill_fn:
                    self.kill_fn()
                return "KILL onaylandı — pause + tüm açık pozisyonlar kapatıldı."

        return f"bilinmeyen komut: /{cmd}"
