# notify/eod_summary.py
"""Gün sonu (EOD) özeti (HARDENING B6, Faz 5 F5A-7).

D1-uyarlı: rejim durumu (basket/nakit), günün P&L'i, equity, modellenmiş faiz,
breaker durumu, aktif FREEZE switch'leri, ertesi gün takvim notu. 10-gate'in "eleyen
gate istatistiği" karşılığı D1'de rejim/kompozit durumudur.
"""
from __future__ import annotations

from typing import Optional


def build_eod_summary(*, date, equity: float, cash: float, day_pnl: float,
                      in_position: bool, regime_on: Optional[bool] = None,
                      observe_mode: bool = False, breaker_state: str = "OK",
                      frozen_switches: Optional[list[str]] = None,
                      modeled_interest_total: float = 0.0,
                      next_calendar_note: str = "",
                      cash_rate_status: Optional[dict] = None,
                      telegram_status: Optional[tuple[str, str]] = None,
                      data_final: Optional[bool] = None,
                      data_final_reason: Optional[str] = None) -> str:
    frozen = frozen_switches or []
    # F5-B2a.1 mikro-düzeltme: "rejim" (compute_regime_signal çıktısı) ve "pozisyon"
    # (broker'da sepet tutuluyor mu) BAĞIMSIZ kavramlar — özellikle observe modda
    # pozisyon HER ZAMAN NAKİT'tir (hesap başlatılmadı) ama rejim ON olabilir. Eskiden
    # tek satırda `in_position`'dan türetilen "rejim" metni bu iki durumu karıştırıyordu.
    pos_text = "SEPETTE" if in_position else "NAKİT"
    if observe_mode:
        pos_text += " (observe — hesap başlatılmadı)"
    lines = [f"📊 EOD Özet — {date}"]
    if data_final is not None:  # F5-B2a.2: drift/provisional sessizce EOD'de kaybolmasın
        if data_final:
            lines.append("Veri: FINAL ✓")
        else:
            reason = data_final_reason or "sinyal kesinleşmedi"
            lines.append(f"Veri: PROVISIONAL ⚠ ({reason})")
    if regime_on is not None:
        lines.append(f"Rejim: {'ON' if regime_on else 'OFF'}")
    lines += [
        f"Pozisyon: {pos_text}",
        f"Equity: {equity:,.0f} TRY  (nakit: {cash:,.0f})",
        f"Günün P&L: {day_pnl:+,.0f} TRY",
        f"Modellenmiş faiz (kümülatif): {modeled_interest_total:,.0f} TRY",
    ]
    if cash_rate_status:  # K1: faiz değeri + kaynak tarihi + bayatlık
        r = cash_rate_status.get("rate_pct")
        sd = cash_rate_status.get("source_date")
        stale = cash_rate_status.get("staleness_days")
        flag = " ⚠️BAYAT" if cash_rate_status.get("stale") else ""
        lines.append(f"Faiz (TRY_ON_RATE): {r}% (kaynak {sd}, bayatlık {stale}g{flag})")
    lines += [
        f"Breaker: {breaker_state}",
        f"Aktif FREEZE: {', '.join(frozen) if frozen else 'yok'}",
    ]
    if telegram_status:  # F5-B2a.1: konfig-niyet ↔ çalışma-durumu uyuşmazlığı hiç sessiz kalmasın
        state, reason = telegram_status
        lines.append(f"TELEGRAM: {state}" if state == "ACTIVE" else f"TELEGRAM: {state} ({reason})")
    if next_calendar_note:
        lines.append(f"Yarın: {next_calendar_note}")
    return "\n".join(lines)
