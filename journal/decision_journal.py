# journal/decision_journal.py
"""Karar günlüğü — yapılandırılmış JSONL (HARDENING B4, Faz 5 F5A-5).

D1-uyarlı şema: her değerlendirilen gün için kompozit, MA(N), bant, teyit sayacı,
rejim kararı, planlanan/gerçekleşen emirler, breaker durumu. Amaç: "bot neden bu
kararı verdi/vermedi" sorusu her zaman SAYILARLA yanıtlanabilsin.

10-gate'in "10 gate'in sayısal değeri" şemasının D1 karşılığı: regime_core tek bir
kompozit-eşik kararıdır → gate yerine kompozit/MA/bant/teyit alanları loglanır.

Kimlik bilgileri HER YERDE maskeli (journal.masking). Her satır JSON; append-only.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

from journal.masking import sanitize

DEFAULT_JOURNAL = Path("runtime/decision_journal.jsonl")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DecisionJournal:
    def __init__(self, path: Path | str = DEFAULT_JOURNAL,
                 known_secrets: Iterable[str] = (),
                 ma_period: Optional[int] = None, band_pct: Optional[float] = None,
                 confirm_days: Optional[int] = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.known_secrets = tuple(known_secrets)
        self.ma_period = ma_period
        self.band_pct = band_pct
        self.confirm_days = confirm_days

    def _write(self, record: dict) -> None:
        clean = sanitize(record, self.known_secrets)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(clean, ensure_ascii=False, default=str) + "\n")

    def record_decision(self, dec: Any) -> None:
        """DailyDecision (execution.regime_core_runner) → JSONL. Duck-typed
        (import bağımlılığı yok)."""
        rec = {
            "ts": _utcnow_iso(),
            "type": "decision",
            "date": str(getattr(dec, "date", None)),
            "regime": {
                "composite": _num(getattr(dec, "composite", None)),
                "ma": _num(getattr(dec, "ma", None)),
                "ma_period": self.ma_period,
                "upper_band": _num(getattr(dec, "upper_band", None)),
                "lower_band": _num(getattr(dec, "lower_band", None)),
                "band_pct": self.band_pct,
                "confirm_count": getattr(dec, "confirm_count", None),
                "confirm_days": self.confirm_days,
                "signal_yesterday": getattr(dec, "signal_yesterday", None),
            },
            "in_position_before": getattr(dec, "in_position_before", None),
            "action": getattr(dec, "action", None),
            "planned_orders": getattr(dec, "planned_qty", {}),
            "executed_order_ids": getattr(dec, "executed_order_ids", []),
            "account": {
                "equity_before": _num(getattr(dec, "equity_before", None)),
                "equity_after": _num(getattr(dec, "equity_after", None)),
                "cash_after": _num(getattr(dec, "cash_after", None)),
                "interest_accrued": _num(getattr(dec, "interest_accrued", None)),
            },
            "breaker": {
                "state": getattr(dec, "breaker_state", None),
                "drawdown": _num(getattr(dec, "drawdown", None)),
                "peak_equity": _num(getattr(dec, "peak_equity", None)),
            },
        }
        self._write(rec)

    def record_signal_evaluation(self, *, date, composite: float, ma: float,
                                 upper_band: float, lower_band: float, confirm_count: int,
                                 regime_on: bool, in_position: bool, mode: str = "observe") -> None:
        """Gözlem modu 'değerlendirilen sinyal' kaydı (B7-D1 önerisi): paper hesabı
        henüz başlatılmadan (go_live_date=null) her gün rejim değerlendirmesini
        loglar. Bir İŞLEM DEĞİL — B7 karnesinde 'değerlendirilen sinyal' = günlük
        rejim değerlendirmesi (bkz. PHASE5B1_REVIEW.md B7-D1 önerisi)."""
        self._write({
            "ts": _utcnow_iso(), "type": "signal_eval", "mode": mode,
            "date": str(date),
            "regime": {
                "composite": _num(composite), "ma": _num(ma), "ma_period": self.ma_period,
                "upper_band": _num(upper_band), "lower_band": _num(lower_band),
                "band_pct": self.band_pct, "confirm_count": confirm_count,
                "confirm_days": self.confirm_days, "regime_on": bool(regime_on),
            },
            "in_position": bool(in_position),
        })

    def record_event(self, level: str, category: str, message: str) -> None:
        """Serbest olay kaydı (INFO/WARN/ERROR/CRITICAL). Kimlik maskeli."""
        self._write({"ts": _utcnow_iso(), "type": "event",
                     "level": level, "category": category, "message": message})

    def record_order_event(self, request: dict, response: dict, status: str) -> None:
        """Emir olayı — istek/yanıt özeti MASKELİ (B4). Kimlik bilgileri sanitize edilir."""
        self._write({"ts": _utcnow_iso(), "type": "order_event", "status": status,
                     "request": request, "response": response})

    def record_alarm(self, alarm: dict) -> None:
        self._write({"ts": _utcnow_iso(), "type": "alarm", **alarm})

    # ------------------------------------------------------------------ okuma (test/rapor)
    def read_all(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
        return None if f != f else f  # NaN → None
    except (TypeError, ValueError):
        return v
