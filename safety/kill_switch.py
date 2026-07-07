# safety/kill_switch.py
"""Kill-switch hiyerarşisi (HARDENING B3, Faz 5 F5A-4).

Bağımsız switch'ler; her biri tetiklenince loglanır, bildirir ve kendi FREEZE
dosyasını yazar. **TÜM FREEZE çıkışları YALNIZCA kullanıcı komutuyla** (dosyayı elle
siler / Telegram onaylı komut). Otomatik reset YOK.

Switch'ler (config/regime_core.yaml::safety):
  1. Drawdown breaker  — RegimeCoreBreaker (ALARM -%25 / FREEZE -%40, KALICI KAYIT 6).
  2. Günlük zarar limiti — daily_loss_limit_pct.
  3. Ardışık N zarar   — consecutive_losses_freeze (D1'e uyarlı muhafazakâr varsayılan).
  4. Veri anomalisi    — data_stale_sec + data_max_price_jump_pct.
  5. API hata oranı    — api_error_freeze_count / api_error_window_sec.

Eşikler config'tedir (kod sabiti DEĞİL) ve ÖNERİDİR (kullanıcı gözden geçirmesine tabi).
"""
from __future__ import annotations

import sqlite3
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from strategy.regime_core import RegimeCoreBreaker, BreakerState

DEFAULT_FREEZE_DIR = Path("runtime/freeze")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SwitchConfig:
    alarm_drawdown_pct: float = 0.25
    freeze_drawdown_pct: float = 0.40
    daily_loss_limit_pct: float = 0.08
    consecutive_losses_freeze: int = 4
    data_stale_sec: int = 172800
    data_max_price_jump_pct: float = 0.20
    api_error_freeze_count: int = 5
    api_error_window_sec: int = 300

    @classmethod
    def from_yaml_dict(cls, safety: dict) -> "SwitchConfig":
        return cls(
            alarm_drawdown_pct=safety.get("alarm_drawdown_pct", 0.25),
            freeze_drawdown_pct=safety.get("freeze_drawdown_pct", 0.40),
            daily_loss_limit_pct=safety.get("daily_loss_limit_pct", 0.08),
            consecutive_losses_freeze=safety.get("consecutive_losses_freeze", 4),
            data_stale_sec=safety.get("data_stale_sec", 172800),
            data_max_price_jump_pct=safety.get("data_max_price_jump_pct", 0.20),
            api_error_freeze_count=safety.get("api_error_freeze_count", 5),
            api_error_window_sec=safety.get("api_error_window_sec", 300),
        )


@dataclass
class TripEvent:
    switch: str
    level: str          # WARN | CRITICAL
    reason: str
    freeze: bool         # True = FREEZE dosyası yazıldı/aktif


# switch adları = FREEZE dosya adları
SW_DRAWDOWN = "BREAKER"           # RegimeCoreBreaker kendi dosyasını yazar
SW_DAILY_LOSS = "DAILY_LOSS"
SW_CONSEC_LOSS = "CONSEC_LOSS"
SW_DATA = "DATA_ANOMALY"
SW_API = "API_ERROR"


class KillSwitchManager:
    def __init__(self, cfg: SwitchConfig, freeze_dir: Path | str = DEFAULT_FREEZE_DIR,
                 breaker: Optional[RegimeCoreBreaker] = None,
                 alarm_hook: Optional[Callable[[dict], None]] = None,
                 state_path: Optional[Path | str] = None):
        self.cfg = cfg
        self.freeze_dir = Path(freeze_dir)
        self.freeze_dir.mkdir(parents=True, exist_ok=True)
        self.breaker = breaker
        self.alarm_hook = alarm_hook
        self._api_errors: deque[float] = deque()
        # ardışık-zarar sayacı kalıcı (süreç yeniden başlasa da korunur)
        self.state_path = Path(state_path) if state_path else self.freeze_dir / "ks_state.sqlite"
        self._conn = sqlite3.connect(str(self.state_path))
        self._conn.execute("CREATE TABLE IF NOT EXISTS ks_state (k TEXT PRIMARY KEY, v REAL)")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------ freeze dosyaları
    def _freeze_path(self, name: str) -> Path:
        if name == SW_DRAWDOWN and self.breaker is not None and self.breaker.freeze_file is not None:
            return self.breaker.freeze_file
        return self.freeze_dir / name

    def _write_freeze(self, name: str, reason: str) -> bool:
        p = self._freeze_path(name)
        if p.exists():
            return False
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"date={_utcnow_iso()} switch={name}\n{reason}\n"
                     f"(FREEZE — yeni ENTER yok; reset YALNIZ kullanıcı)\n")
        return True

    def any_frozen(self) -> bool:
        return len(self.frozen_switches()) > 0

    def frozen_switches(self) -> list[str]:
        out = []
        for name in (SW_DAILY_LOSS, SW_CONSEC_LOSS, SW_DATA, SW_API):
            if (self.freeze_dir / name).exists():
                out.append(name)
        if self.breaker is not None and self.breaker.freeze_active():
            out.append(SW_DRAWDOWN)
        return out

    def clear(self, name: str) -> None:
        """KULLANICI KOMUTU (otomatik DEĞİL): bir switch'in FREEZE'ini temizle."""
        p = self._freeze_path(name)
        if p.exists():
            p.unlink()
        if name == SW_CONSEC_LOSS:
            self._set_state("consec_losses", 0)

    # ------------------------------------------------------------------ kalıcı sayaç
    def _get_state(self, k: str, default: float = 0.0) -> float:
        r = self._conn.execute("SELECT v FROM ks_state WHERE k=?", (k,)).fetchone()
        return float(r[0]) if r else default

    def _set_state(self, k: str, v: float) -> None:
        self._conn.execute("INSERT INTO ks_state (k,v) VALUES (?,?) "
                           "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
        self._conn.commit()

    # ------------------------------------------------------------------ olay girdileri
    def record_trade_result(self, pnl: float) -> Optional[TripEvent]:
        """Bir round-trip (EXIT) kapandığında P&L bildir. Ardışık zarar sayacı."""
        n = int(self._get_state("consec_losses", 0))
        n = n + 1 if pnl < 0 else 0
        self._set_state("consec_losses", n)
        if n >= self.cfg.consecutive_losses_freeze:
            reason = f"ardışık {n} zararlı round-trip >= {self.cfg.consecutive_losses_freeze}"
            froze = self._write_freeze(SW_CONSEC_LOSS, reason)
            return self._emit(SW_CONSEC_LOSS, "CRITICAL", reason, froze)
        return None

    def note_api_error(self, now: Optional[float] = None) -> Optional[TripEvent]:
        t = now if now is not None else datetime.now(timezone.utc).timestamp()
        self._api_errors.append(t)
        while self._api_errors and t - self._api_errors[0] > self.cfg.api_error_window_sec:
            self._api_errors.popleft()
        if len(self._api_errors) >= self.cfg.api_error_freeze_count:
            reason = (f"{len(self._api_errors)} hata / {self.cfg.api_error_window_sec}s >= "
                      f"{self.cfg.api_error_freeze_count}")
            froze = self._write_freeze(SW_API, reason)
            return self._emit(SW_API, "CRITICAL", reason, froze)
        return None

    def note_api_ok(self) -> None:
        self._api_errors.clear()

    # ------------------------------------------------------------------ döngü değerlendirmesi
    def evaluate_cycle(self, equity: float, peak: float, daily_pnl: float,
                       last_bar_age_sec: Optional[float] = None,
                       max_intraday_jump_pct: Optional[float] = None,
                       date=None) -> list[TripEvent]:
        """Her günlük döngüde çağrılır. Drawdown breaker + günlük zarar + veri
        anomalisi switch'lerini değerlendirir. Döner: tetiklenen olaylar."""
        events: list[TripEvent] = []

        # 1. Drawdown breaker
        if self.breaker is not None and peak > 0:
            st = self.breaker.evaluate(date, equity, peak)
            dd = 1 - equity / peak
            if st == BreakerState.FREEZE:
                events.append(self._emit(SW_DRAWDOWN, "CRITICAL",
                                         f"drawdown {dd:.2%} >= FREEZE {self.cfg.freeze_drawdown_pct:.0%}", True))
            elif st == BreakerState.ALARM:
                events.append(self._emit(SW_DRAWDOWN, "WARN",
                                         f"drawdown {dd:.2%} >= ALARM {self.cfg.alarm_drawdown_pct:.0%} (bildirim)", False))

        # 2. Günlük zarar limiti
        if equity > 0 and daily_pnl <= -self.cfg.daily_loss_limit_pct * equity:
            reason = f"günlük P&L {daily_pnl:.0f} <= -{self.cfg.daily_loss_limit_pct:.0%}×equity"
            froze = self._write_freeze(SW_DAILY_LOSS, reason)
            events.append(self._emit(SW_DAILY_LOSS, "CRITICAL", reason, froze))

        # 4a. Veri donması
        if last_bar_age_sec is not None and last_bar_age_sec > self.cfg.data_stale_sec:
            reason = f"son bar yaşı {last_bar_age_sec:.0f}s > {self.cfg.data_stale_sec}s (feed donması)"
            froze = self._write_freeze(SW_DATA, reason)
            events.append(self._emit(SW_DATA, "CRITICAL", reason, froze))
        # 4b. Fiyat sıçraması
        if max_intraday_jump_pct is not None and max_intraday_jump_pct > self.cfg.data_max_price_jump_pct:
            reason = f"fiyat sıçraması {max_intraday_jump_pct:.2%} > {self.cfg.data_max_price_jump_pct:.0%} (bozuk veri şüphesi)"
            froze = self._write_freeze(SW_DATA, reason)
            events.append(self._emit(SW_DATA, "CRITICAL", reason, froze))
        return events

    def _emit(self, switch: str, level: str, reason: str, freeze: bool) -> TripEvent:
        ev = TripEvent(switch=switch, level=level, reason=reason, freeze=freeze)
        if self.alarm_hook is not None:
            self.alarm_hook({"category": "KILL_SWITCH", "level": level,
                             "switch": switch, "message": reason, "freeze": freeze})
        return ev
