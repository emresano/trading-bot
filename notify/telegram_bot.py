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

from dataclasses import dataclass
from typing import Callable, Optional

from journal.masking import mask_secret

# Kesinlikle var olmayacak / reddedilecek komut kökleri (Durma Noktası 2).
_FORBIDDEN = {"real", "gorec", "gerçek", "gercek", "golive", "go_live", "live_real"}
_ACTION_CMDS = {"pause", "resume", "kill"}
_READONLY_CMDS = {"status", "report"}


@dataclass
class TelegramConfig:
    enabled: bool = False
    chat_id: Optional[str] = None      # izinli tek chat
    token_present: bool = False        # secrets.env'de TELEGRAM_TOKEN var mı (değeri DEĞİL)


class TelegramNotifier:
    """Giden bildirim. `sender(text)` enjekte edilebilir (test); yoksa+enabled ise
    gerçek HTTP (F5-B'de bağlanır). enabled=False → no-op."""

    def __init__(self, config: TelegramConfig, sender: Optional[Callable[[str], None]] = None,
                 known_secrets=()):
        self.config = config
        self._sender = sender
        self.known_secrets = tuple(known_secrets)
        self.sent: list[str] = []   # test/denetim izi (maskeli)

    def send(self, text: str) -> bool:
        masked = mask_secret(text, self.known_secrets)
        self.sent.append(masked)
        if not self.config.enabled:
            return False
        if self._sender is not None:
            self._sender(masked)
            return True
        # Gerçek HTTP F5-B'de (token secrets.env'den). F5-A: canlı çağrı YOK.
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
