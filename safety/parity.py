# safety/parity.py
"""Günlük parite kontrolü (HARDENING B5, Faz 5 F5A-6).

"Aynı kod + aynı veri → aynı karar." Her gün kapanıştan sonra otomatik iş: günün
(ve tüm geçmişin) verisiyle sinyal motoru OFFLINE koşulur (run_regime_core_prod, aynı
SAF fonksiyonlar) ve üretilen anahtarlamalar CANLI karar günlüğüyle diff'lenir.

Fark = KIRMIZI ALARM. F5A-2 parite testi runner ↔ backtest özdeşliğini zaten kanıtladı;
bu iş üretimde VERİ KAYMASI / kod kayması / state bozulmasını yakalar (canlı defter
taze offline yeniden-koşumla çelişirse bir şey yanlış).

NOT (sapma ≠ hata): kapanışa-yakın yürütme fiyatı vs backtest tam-kapanış fiyatı
equity'de küçük fark yaratır — parite kararı DECISION düzeyindedir (anahtarlama
tarihi/aksiyonu), equity float farkı parite başarısızlığı SAYILMAZ (PHASE5_PLAN #3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import pandas as pd

from strategy.regime_core import RegimeCoreParams, RegimeCoreBreaker, run_regime_core_prod


@dataclass
class ParityResult:
    matched: bool
    offline_switches: list[tuple] = field(default_factory=list)   # [(Timestamp, action)]
    live_switches: list[tuple] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)
    red_alarm: bool = False

    def summary(self) -> str:
        if self.matched:
            return f"PARİTE OK — {len(self.offline_switches)} anahtarlama offline↔canlı özdeş"
        return "PARİTE FARKI (KIRMIZI ALARM): " + "; ".join(self.mismatches)


def _live_switches_from_journal(journal_rows: list[dict]) -> list[tuple]:
    out = []
    for r in journal_rows:
        if r.get("type") == "decision" and r.get("action") in ("ENTER", "EXIT"):
            out.append((pd.Timestamp(r["date"]), r["action"]))
    return out


def check_parity(closes: dict[str, pd.Series], params: RegimeCoreParams,
                 journal_rows: list[dict],
                 cash_rate: Optional[pd.Series] = None,
                 breaker: Optional[RegimeCoreBreaker] = None,
                 alarm_hook: Optional[Callable[[dict], None]] = None) -> ParityResult:
    """Offline yeniden-koşum ↔ canlı karar günlüğü anahtarlama diff'i."""
    offline = run_regime_core_prod(closes, params, cash_rate=cash_rate, breaker=breaker)
    offline_switches = [(pd.Timestamp(s.date), s.action) for s in offline.switches]
    live_switches = _live_switches_from_journal(journal_rows)

    mismatches: list[str] = []
    if len(offline_switches) != len(live_switches):
        mismatches.append(f"anahtarlama sayısı: offline={len(offline_switches)} canlı={len(live_switches)}")
    for i, (o, l) in enumerate(zip(offline_switches, live_switches)):
        if o != l:
            mismatches.append(f"#{i}: offline={o[1]}@{o[0].date()} canlı={l[1]}@{l[0].date()}")

    matched = len(mismatches) == 0
    result = ParityResult(matched=matched, offline_switches=offline_switches,
                          live_switches=live_switches, mismatches=mismatches,
                          red_alarm=not matched)
    if not matched and alarm_hook is not None:
        alarm_hook({"category": "PARITY", "level": "CRITICAL", "message": result.summary()})
    return result
