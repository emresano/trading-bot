# backtest/regime_core_us.py
"""EXPANSION E4 (US adil test) — D1 (regime_core) spike'ının CostModel-farkında
yürütme döngüsü.

**Neden ayrı modül:** `backtest/regime_core.py`nin `run_regime_core`'u S1/S1b'nin
MÜHÜRLÜ sonuçlarını üretir; ona DOKUNMAM (auditör o dosyada sıfır diff görür,
S1/S1b bayt-bayt tekrar üretilebilir kalır). Bu modül SİNYAL mantığını
(`build_composite`, `compute_regime_signal`) o dosyadan İTHAL ederek YENİDEN
KULLANIR — yani anahtarlama tarihleri D1 ile BİREBİR aynı sinyal kodundan gelir
— ve yalnızca YÜRÜTME/MALİYET katmanını E2 `CostModel` (costs/base.py) ile
soyutlar. US için `UsEquitiesCostModel` (commission=0, SATIŞTA SEC+TAF,
slippage 5bps) geçilir.

**Parite kanıtı** (tests/test_e4_us.py): BIST-eşdeğeri bir CostModel
(commission=10bps her iki yön, SEC/TAF=0, slippage=5bps) ile bu döngü,
`run_regime_core`'un basit-bps modelini (S1/S1b) ~1e-9 göreli tolERANSta
yeniden üretir ve anahtarlama tarihleri BİREBİR aynıdır.

Nakit tahakkuku (S1b mekaniği) `cash_rate` ile korunur — `cash_rate=None`
(US kararı = %0) → hiç tahakkuk yok (S1b ile aynı nötrleme). Yürütme kuralı
D1 spike'ı ile aynı: sinyal t KAPANIŞINDA, işlem t+1 KAPANIŞINDA.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from backtest.regime_core import (
    CASH_YIELD_HAIRCUT,
    RegimeCoreConfig,
    RegimeCoreResult,
    Switch,
    _build_daily_cash_rate,
    build_composite,
    compute_regime_signal,
)
from core.models import Side
from costs.base import CostModel


def run_regime_core_costmodel(
    daily_closes: dict[str, pd.Series],
    cfg: RegimeCoreConfig,
    cost_model: CostModel,
    date_range: Optional[tuple[pd.Timestamp, pd.Timestamp]] = None,
    cash_rate: Optional[pd.Series] = None,
    haircut: float = CASH_YIELD_HAIRCUT,
) -> RegimeCoreResult:
    """`run_regime_core` (S1b) ile AYNI döngü ve AYNI sinyal — tek fark:
    komisyon/slippage `cfg.commission_bps/slippage_bps` yerine `cost_model`
    üzerinden uygulanır. `cfg`'nin bps alanları BU çağrıda YOK SAYILIR
    (cost_model maliyetin tek sahibi).

    `haircut` (E4b): nakit tahakkuku kırpması, ondalık (varsayılan 0.02 = S1b/TRY
    200bp; US E4b'de config'ten 0.005 = 50bp geçilir). `cash_rate=None` iken
    (E4/%0) etkisizdir — tahakkuk bloğu hiç çalışmaz.

    ENTER sizing: her sembol için bütçe = equity_before/len(symbols);
    qty = floor(bütçe / birim_maliyet), birim_maliyet = fill + entry_costs(fill,1)
    (linear komisyon modeli için doğru; US'te commission=0 → birim=fill).
    """
    composite, fill_log = build_composite(daily_closes)
    regime_on = compute_regime_signal(composite, cfg.ma_period, cfg.band_pct, cfg.confirm_days)

    all_dates = composite.index
    daily_cash_rate = _build_daily_cash_rate(cash_rate, all_dates)
    cash = cfg.initial_equity
    quantities: dict[str, int] = {}
    in_position = False
    switches: list[Switch] = []
    equity_points: list[tuple[pd.Timestamp, float]] = []

    def _equity_on(date: pd.Timestamp) -> float:
        if not in_position:
            return cash
        total = cash
        for sym, qty in quantities.items():
            px_series = daily_closes[sym]
            if date in px_series.index:
                total += qty * float(px_series.loc[date])
            else:
                prior = px_series.loc[:date]
                total += qty * float(prior.iloc[-1]) if len(prior) else 0.0
        return total

    for i, date in enumerate(all_dates):
        signal_yesterday = bool(regime_on.iloc[i - 1]) if i > 0 else False

        # Nakit getirisi tahakkuku (S1b): BUGÜNÜN transition'ından ÖNCEKİ
        # in_position durumuna göre. cash_rate=None (US) → blok hiç çalışmaz.
        if i > 0 and not in_position and daily_cash_rate is not None:
            days_elapsed = (date - all_dates[i - 1]).days
            annual_rate = daily_cash_rate.loc[date]
            if pd.notna(annual_rate) and days_elapsed > 0:
                r_net = max(float(annual_rate) - haircut, 0.0)
                cash *= (1 + r_net / 365) ** days_elapsed

        # t+1 yürütme: dünün sinyal DEĞİŞİMİNİ bugün kapanışta uygula.
        if i > 0 and signal_yesterday != in_position:
            equity_before = _equity_on(date)
            if signal_yesterday and not in_position:
                # ENTER: equity'yi eşit böl, CostModel maliyetleri, negatif cash yasak.
                per_symbol_budget = equity_before / len(cfg.symbols)
                new_quantities: dict[str, int] = {}
                spent = 0.0
                for sym in cfg.symbols:
                    px_series = daily_closes[sym]
                    if date not in px_series.index:
                        continue
                    fill_price = cost_model.slippage_price(float(px_series.loc[date]), Side.BUY)
                    unit_cost = fill_price + cost_model.entry_costs(fill_price, 1.0)
                    qty = int(np.floor(per_symbol_budget / unit_cost))
                    if qty < 1:
                        continue
                    cost = fill_price * qty + cost_model.entry_costs(fill_price, qty)
                    new_quantities[sym] = qty
                    spent += cost
                cash = equity_before - spent
                quantities = new_quantities
                in_position = True
                switches.append(Switch(date=date, action="ENTER",
                                       equity_before=equity_before, equity_after=_equity_on(date)))
            elif not signal_yesterday and in_position:
                # EXIT: tüm pozisyonları sat (SATIŞTA SEC+TAF dahil), %100 nakit.
                proceeds = 0.0
                for sym, qty in quantities.items():
                    px_series = daily_closes[sym]
                    if date in px_series.index:
                        ref = float(px_series.loc[date])
                    else:
                        prior = px_series.loc[:date]
                        ref = float(prior.iloc[-1]) if len(prior) else 0.0
                    fill_price = cost_model.slippage_price(ref, Side.SELL)
                    proceeds += fill_price * qty - cost_model.exit_costs(fill_price, qty)
                cash = cash + proceeds
                quantities = {}
                in_position = False
                switches.append(Switch(date=date, action="EXIT",
                                       equity_before=equity_before, equity_after=cash))

        equity_today = _equity_on(date)
        if date_range is None or (date_range[0] <= date < date_range[1]):
            equity_points.append((date, equity_today))

    equity_curve = pd.Series(dict(equity_points)).sort_index() if equity_points else pd.Series(dtype=float)
    return RegimeCoreResult(
        equity_curve=equity_curve, composite=composite, regime_on=regime_on,
        switches=switches, composite_fill_log=fill_log,
    )
