# notify/eod_summary.py
"""Gün sonu (EOD) özeti (HARDENING B6, Faz 5 F5A-7).

D1-uyarlı: rejim durumu (basket/nakit), günün P&L'i, equity, modellenmiş faiz,
breaker durumu, aktif FREEZE switch'leri, ertesi gün takvim notu. 10-gate'in "eleyen
gate istatistiği" karşılığı D1'de rejim/kompozit durumudur.
"""
from __future__ import annotations

from typing import Optional


def build_eod_summary(*, date, equity: float, cash: float, day_pnl: float,
                      in_position: bool, breaker_state: str = "OK",
                      frozen_switches: Optional[list[str]] = None,
                      modeled_interest_total: float = 0.0,
                      next_calendar_note: str = "") -> str:
    frozen = frozen_switches or []
    regime = "BASKET (rejim ON)" if in_position else "NAKİT (rejim OFF)"
    lines = [
        f"📊 EOD Özet — {date}",
        f"Rejim: {regime}",
        f"Equity: {equity:,.0f} TRY  (nakit: {cash:,.0f})",
        f"Günün P&L: {day_pnl:+,.0f} TRY",
        f"Modellenmiş faiz (kümülatif): {modeled_interest_total:,.0f} TRY",
        f"Breaker: {breaker_state}",
        f"Aktif FREEZE: {', '.join(frozen) if frozen else 'yok'}",
    ]
    if next_calendar_note:
        lines.append(f"Yarın: {next_calendar_note}")
    return "\n".join(lines)
