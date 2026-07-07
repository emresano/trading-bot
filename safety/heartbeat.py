# safety/heartbeat.py
"""Heartbeat + Watchdog (HARDENING B6 / CLAUDE.md 13.3, Faz 5 F5A-7).

main.py her heartbeat_interval_sec'te `runtime/heartbeat` dosyasına UTC timestamp
yazar. Watchdog AYRI süreçtir: dosya yaşı > heartbeat_stale_sec ise Telegram'a
CRITICAL "bot sessiz — pozisyonlar broker bracket'larıyla korunuyor" gönderir.
Watchdog'un tek bağımlılığı Telegram'dır (bot çökse de ayakta kalır).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DEFAULT_HEARTBEAT = Path("runtime/heartbeat")


def write_heartbeat(path: Path | str = DEFAULT_HEARTBEAT) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(datetime.now(timezone.utc).isoformat())


def heartbeat_age_sec(path: Path | str = DEFAULT_HEARTBEAT,
                      now: Optional[datetime] = None) -> Optional[float]:
    """Son heartbeat'ten bu yana geçen saniye. Dosya yoksa None."""
    p = Path(path)
    if not p.exists():
        return None
    ts = datetime.fromisoformat(p.read_text().strip())
    now = now or datetime.now(timezone.utc)
    return (now - ts).total_seconds()


class Watchdog:
    def __init__(self, notifier, stale_sec: int, path: Path | str = DEFAULT_HEARTBEAT):
        self.notifier = notifier
        self.stale_sec = stale_sec
        self.path = Path(path)
        self._alarmed = False

    def check(self, now: Optional[datetime] = None) -> bool:
        """Bayat mı? Bayatsa (bir kez) CRITICAL bildirir. Döner: stale bool."""
        age = heartbeat_age_sec(self.path, now)
        stale = age is None or age > self.stale_sec
        if stale and not self._alarmed:
            detail = "dosya yok" if age is None else f"yaş {age:.0f}s > {self.stale_sec}s"
            self.notifier.send(f"CRITICAL: bot sessiz ({detail}) — pozisyonlar broker "
                               f"korumasında, kontrol edin.")
            self._alarmed = True
        elif not stale:
            self._alarmed = False
        return stale
