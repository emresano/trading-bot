# strategy/family_registry.py
"""Strateji-ailesi soyutlaması + registry (P1 üretim portu, tasarım çerçevesi #1).

Mevcut 10-gate huni (`ten_gate`) ile rejim-filtreli çekirdek (`regime_core`), AYNI
üretim runtime'ı altında config'ten seçilebilir İKİ AİLE olur. gate_registry
ruhu: seçim TEK bir sınırda (aile dispatch) yapılır — çekirdek modüllerde
aile-özel `if family == ...` dallanması YOKTUR. Her aile kendi çekirdek
fonksiyonunu (run_backtest / run_regime_core_prod) sarar; iki çekirdek birbirinden
bağımsızdır (ten_gate v7.1-golden'ı bit-bit korur — sadece delege eder).

E2 deseniyle tutarlı (MarketSpec/CostModel/gate_registry gibi bir registry).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd


@dataclass
class FamilyResult:
    family_id: str
    equity_curve: pd.Series
    events: list[dict] = field(default_factory=list)   # normalize: [{date, action, ...}]
    extra: dict = field(default_factory=dict)           # aile-özel (trades / switches / breaker)


class StrategyFamily(ABC):
    """Bir strateji ailesinin üretim sözleşmesi. `run(ctx)` → FamilyResult.
    `ctx` ailenin ihtiyaç duyduğu girdileri taşır (semboller, config, veri
    yükleyici, vb.) — ortak bir veri şeması dayatılmaz (aileler farklı yürütme
    modellerine sahip); ortak olan yalnızca SEÇİM ve SONUÇ şeklidir."""

    family_id: str

    @abstractmethod
    def run(self, ctx: dict[str, Any]) -> FamilyResult: ...


class TenGateFamily(StrategyFamily):
    """Mevcut 10-gate huni — backtest/engine.py::run_backtest'i SARAR (davranış-nötr).
    ctx: {symbols, cfg, load_daily, breaker_file?, cost_model?}."""

    family_id = "ten_gate"

    def run(self, ctx: dict[str, Any]) -> FamilyResult:
        from backtest.engine import run_backtest
        res = run_backtest(
            ctx["symbols"], ctx["cfg"], ctx["load_daily"],
            breaker_file=ctx.get("breaker_file"), cost_model=ctx.get("cost_model"),
        )
        events = [
            {"date": t.exit_date, "action": "TRADE", "symbol": t.symbol,
             "entry_date": t.entry_date, "pnl": t.pnl, "exit_reason": t.exit_reason}
            for t in res.trades
        ]
        return FamilyResult("ten_gate", res.equity_curve, events, {"trades": res.trades, "result": res})


class RegimeCoreFamily(StrategyFamily):
    """Rejim-filtreli çekirdek — strategy/regime_core.py::run_regime_core_prod'ı SARAR.
    ctx: {closes, params, cash_rate?, breaker?, date_range?}."""

    family_id = "regime_core"

    def run(self, ctx: dict[str, Any]) -> FamilyResult:
        from strategy.regime_core import run_regime_core_prod
        res = run_regime_core_prod(
            ctx["closes"], ctx["params"], date_range=ctx.get("date_range"),
            cash_rate=ctx.get("cash_rate"), breaker=ctx.get("breaker"),
        )
        events = [
            {"date": s.date, "action": s.action,
             "equity_before": s.equity_before, "equity_after": s.equity_after}
            for s in res.switches
        ]
        return FamilyResult("regime_core", res.equity_curve, events, {
            "switches": res.switches, "composite": res.composite, "regime_on": res.regime_on,
            "breaker_events": res.breaker_events, "freeze_trips": res.freeze_trips,
            "enters_blocked_by_freeze": res.enters_blocked_by_freeze,
            "alarm_trips": res.alarm_trips, "result": res,
        })


_FAMILY_BUILDERS: dict[str, Callable[[], StrategyFamily]] = {
    "ten_gate": TenGateFamily,
    "regime_core": RegimeCoreFamily,
}


def build_family(family_id: str) -> StrategyFamily:
    """family_id → StrategyFamily. Bilinmeyen isim = hata (sessiz atlama YASAK)."""
    try:
        return _FAMILY_BUILDERS[family_id]()
    except KeyError as exc:
        raise ValueError(
            f"Bilinmeyen strateji ailesi: '{family_id}' (kayıtlı: {sorted(_FAMILY_BUILDERS)})"
        ) from exc


def family_id_from_config(cfg_dict: dict, default: str = "ten_gate") -> str:
    """config sözlüğünden `strategy_family` alanını okur; yoksa default (ten_gate).
    config/config.yaml bu alanı içermez → 10-gate; config/regime_core.yaml içerir."""
    fid = cfg_dict.get("strategy_family", default)
    if fid not in _FAMILY_BUILDERS:
        raise ValueError(
            f"config.strategy_family='{fid}' bilinmiyor (kayıtlı: {sorted(_FAMILY_BUILDERS)})"
        )
    return fid
