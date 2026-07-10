# backtest/regime_core_gated.py
"""D5-BIST CHALLENGER simülatörü — "D1 + fırsat-maliyeti (faiz) kapısı".

STATUS.md KALICI KAYIT 23 · Mühür: `D5_CRITERIA.md` (bu dosyadan ÖNCEKİ commit).
**Offline araştırma spike'ı; ÜRETİM DEĞİL; HÜKÜM YOK.**

**BAĞIMSIZ MODÜL.** `backtest/regime_core.py` (S1/S1b simülatörü), `strategy/`,
`risk/`, `execution/`, `safety/`, `notify/`, `main.py`, `backtest/engine.py` ve
`config/config.yaml` DEĞİŞTİRİLMEZ; buradan YALNIZCA **import** edilir →
v7.1-golden çapası ve D1 paper hattı yapısal olarak korunur.

Tasarım (mühürlü, `D5_CRITERIA.md` §1 — bu turda değiştirilemez):
- **D1 mekaniği AYNEN**: kompozit, MA(N=200)±b(%1) / M=3-gün teyitli giriş,
  1-gün çıkış; t+1 KAPANIŞ yürütmesi; tam-lot eşit bölme; komisyon+slipaj;
  rejim KAPALI günlerde nakde ACT/365 tahakkuk (200bp haircut'lı).
- **TEK EK KATMAN — sepet-düzeyi fırsat-maliyeti kapısı** (§1.2/§1.3):
  kompozitin trailing 252 işlem-günü getirisi, HAM `TRY_ON_RATE`'in aynı
  takvim penceresinde bileşiklenen getirisinden büyük değilse → NAKİT.
  Kapı D1'in kendi asimetrisini kullanır: açılış 3 gün teyitli, kapanış tek gün.
- **Efektif pozisyon = `rejim_ON` VE `kapı_AÇIK`.** Kapı yalnızca KISITLAR;
  D1'in kapalı olduğu bir günde asla pozisyon AÇTIRMAZ.
- Isınma (§1.5): ilk `lookback_bars` barda kapı DEĞERLENDİRİLEMEZ → KAPALI
  (muhafazakâr; genişleyen-pencere yaklaşıklığı KULLANILMAZ, look-ahead yok).

**Sadakat kanıtı (kopya-riskine karşı test edilen değişmez):** aşağıdaki yürütme
döngüsü `backtest.regime_core.run_regime_core`'un döngüsüyle aynı olmak
ZORUNDADIR. `gate_cfg=None` verildiğinde bu modül D1'i yeniden üretir ve
`tests/test_d5_bist.py::test_gate_none_is_bit_identical_to_d1` bunun equity
eğrisi/anahtarlamalar/rejim serisi düzeyinde **bit-bit** doğru olduğunu her
koşuda kanıtlar. Bir sapma olursa test kırmızı yanar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from backtest.regime_core import (
    CASH_YIELD_HAIRCUT,
    RegimeCoreConfig,
    Switch,
    _build_daily_cash_rate,
    build_composite,
    compute_cash_only_curve,
    compute_regime_signal,
)

__all__ = [
    "GateConfig",
    "GatedRegimeCoreResult",
    "compute_trailing_returns",
    "compute_opportunity_gate",
    "run_regime_core_gated",
]


@dataclass(frozen=True)
class GateConfig:
    """Fırsat-maliyeti kapısı — MÜHÜRLÜ sabitler (`config/d5_bist.yaml::gate`)."""

    lookback_bars: int = 252          # ≈ 12 ay (dual-momentum varsayılanı)
    confirm_days: int = 3             # açılış teyidi (D1'in M'iyle aynı)
    close_days: int = 1               # kapanış tek gün (D1'in çıkış kuralıyla aynı)
    signal_rate_haircut: float = 0.0  # SİNYAL eşiği HAM oranı kullanır (D4US §1.5 emsali)
    warmup_gate_closed: bool = True   # ilk lookback_bars bar: kapı KAPALI


@dataclass
class GatedRegimeCoreResult:
    """`RegimeCoreResult` ile AYNI alanlar (aynı OOS/metrik makinesinden geçebilsin)
    + kapı teşhis serileri."""

    equity_curve: pd.Series
    composite: pd.Series
    regime_on: pd.Series              # D1'in ham rejim sinyali (kapısız)
    switches: list[Switch] = field(default_factory=list)
    composite_fill_log: list[dict] = field(default_factory=list)
    # --- D5'e özgü teşhis (kriter değil, analiz girdisi) ---
    gate_open: pd.Series = field(default_factory=lambda: pd.Series(dtype=bool))
    effective_on: pd.Series = field(default_factory=lambda: pd.Series(dtype=bool))
    stock_ret: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    cash_ret: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    favorable: pd.Series = field(default_factory=lambda: pd.Series(dtype=bool))


# --------------------------------------------------------------------------- kapı


def compute_trailing_returns(
    composite: pd.Series, cash_rate: pd.Series, lookback_bars: int, haircut: float = 0.0
) -> tuple[pd.Series, pd.Series]:
    """Trailing `lookback_bars` İŞLEM GÜNÜ üzerinden (i) kompozitin toplam getirisi,
    (ii) nakdin AYNI TAKVİM penceresinde bileşiklenen getirisi.

    Nakit bileşiklemesi, `backtest/regime_core.py::compute_cash_only_curve`nin
    **yeniden kullanımıdır** (yeniden yazılmaz → drift imkânsız): aynı
    `(1 + r/365) ** takvim_gün_farkı` formülü, aynı ffill'li günlük oran serisi.
    Tek fark `haircut=0.0` — kapı bir SİNYAL EŞİĞİdir, nakit-bacağı getirisi değil
    (`D5_CRITERIA.md` §1.4; emsal `D4US_CRITERIA.md` §1.5).

    İlk `lookback_bars` bar için ikisi de NaN (tanımsız) — geleceğe bakılmaz."""
    if lookback_bars < 1:
        raise ValueError("lookback_bars >= 1 olmalı")

    cash_index = compute_cash_only_curve(composite.index, cash_rate, 1.0, haircut=haircut)
    cash_index = cash_index.reindex(composite.index)

    stock_ret = composite / composite.shift(lookback_bars) - 1.0
    cash_ret = cash_index / cash_index.shift(lookback_bars) - 1.0
    stock_ret.name, cash_ret.name = "stock_ret", "cash_ret"
    return stock_ret, cash_ret


def compute_opportunity_gate(
    composite: pd.Series, cash_rate: pd.Series, gcfg: GateConfig
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Kapı durum makinesi — `compute_regime_signal` ile AYNI kalıp (asimetrik
    histerezis): açılış `confirm_days` gün üst üste teyitli, kapanış `close_days`
    gün. Tanımsız (ısınma) barlarda kapı KAPALI ve durum SIFIRLANIR.

    Döner: (gate_open, stock_ret, cash_ret, favorable)."""
    stock_ret, cash_ret = compute_trailing_returns(
        composite, cash_rate, gcfg.lookback_bars, gcfg.signal_rate_haircut
    )
    valid = stock_ret.notna() & cash_ret.notna()
    favorable = (stock_ret > cash_ret) & valid          # NaN karşılaştırması False üretir
    unfavorable = valid & ~favorable

    confirmed_open = favorable.rolling(gcfg.confirm_days).sum() >= gcfg.confirm_days
    confirmed_close = unfavorable.rolling(gcfg.close_days).sum() >= gcfg.close_days

    gate_open = pd.Series(False, index=composite.index)
    state = False
    for i in range(len(composite)):
        if not bool(valid.iloc[i]):
            # Isınma / tanımsız: kapı KAPALI (muhafazakâr, §1.5). warmup_gate_closed
            # False ise bile geleceğe bakmadan bir karar üretilemez → yine KAPALI.
            state = False
            gate_open.iloc[i] = False
            continue
        if not state and bool(confirmed_open.iloc[i]):
            state = True
        elif state and bool(confirmed_close.iloc[i]):
            state = False
        gate_open.iloc[i] = state

    gate_open.name = "gate_open"
    return gate_open, stock_ret, cash_ret, favorable


# ------------------------------------------------------------------- kapılı simülatör


def run_regime_core_gated(
    daily_closes: dict[str, pd.Series],
    cfg: RegimeCoreConfig,
    gate_cfg: Optional[GateConfig] = None,
    date_range: Optional[tuple[pd.Timestamp, pd.Timestamp]] = None,
    cash_rate: Optional[pd.Series] = None,
) -> GatedRegimeCoreResult:
    """D1 + kapı. `gate_cfg=None` → kapı YOK → **D1'in birebir yeniden üretimi**
    (bu, döngünün sadakatinin test edilebilir kanıtıdır; bkz. modül docstring'i).

    `cash_rate` kapı için ZORUNLUDUR (`gate_cfg` verildiyse). `date_range`
    semantiği `run_regime_core` ile aynı: kompozit/MA/kapı HER ZAMAN tam tarihçe
    üzerinden hesaplanır, yalnız equity_curve dilimlenir (OOS'ta warm-up korunur)."""
    composite, fill_log = build_composite(daily_closes)
    regime_on = compute_regime_signal(composite, cfg.ma_period, cfg.band_pct, cfg.confirm_days)

    if gate_cfg is None:
        gate_open = pd.Series(True, index=composite.index, name="gate_open")
        stock_ret = pd.Series(np.nan, index=composite.index)
        cash_ret = pd.Series(np.nan, index=composite.index)
        favorable = pd.Series(False, index=composite.index)
    else:
        if cash_rate is None:
            raise ValueError("D5 kapısı `cash_rate` olmadan değerlendirilemez.")
        gate_open, stock_ret, cash_ret, favorable = compute_opportunity_gate(
            composite, cash_rate, gate_cfg
        )

    effective_on = regime_on & gate_open
    effective_on.name = "effective_on"

    # ----------------------------------------------------------------------
    # Aşağısı `backtest.regime_core.run_regime_core`nin yürütme döngüsüyle
    # AYNIdır; TEK fark `regime_on` yerine `effective_on` okunmasıdır.
    # Değişmez, testle çapalanmıştır: gate_cfg=None → bit-bit D1.
    # ----------------------------------------------------------------------
    all_dates = composite.index
    daily_cash_rate = _build_daily_cash_rate(cash_rate, all_dates)
    cash = cfg.initial_equity
    quantities: dict[str, int] = {}
    in_position = False
    switches: list[Switch] = []
    equity_points: list[tuple[pd.Timestamp, float]] = []

    commission_frac = cfg.commission_bps / 1e4
    slippage_frac = cfg.slippage_bps / 1e4

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
        signal_yesterday = bool(effective_on.iloc[i - 1]) if i > 0 else False

        # Nakit getirisi tahakkuku (S1b) — BUGÜNÜN transition'ından ÖNCEKİ
        # `in_position` durumuna göre; ENTER gününü dahil, EXIT gününü hariç tutar.
        if i > 0 and not in_position and daily_cash_rate is not None:
            days_elapsed = (date - all_dates[i - 1]).days
            annual_rate = daily_cash_rate.loc[date]
            if pd.notna(annual_rate) and days_elapsed > 0:
                r_net = max(float(annual_rate) - CASH_YIELD_HAIRCUT, 0.0)
                cash *= (1 + r_net / 365) ** days_elapsed

        if i > 0 and signal_yesterday != in_position:
            equity_before = _equity_on(date)
            if signal_yesterday and not in_position:
                per_symbol_budget = equity_before / len(cfg.symbols)
                new_quantities = {}
                spent = 0.0
                for sym in cfg.symbols:
                    px_series = daily_closes[sym]
                    if date not in px_series.index:
                        continue
                    fill_price = float(px_series.loc[date]) * (1 + slippage_frac)
                    qty = int(np.floor(per_symbol_budget / (fill_price * (1 + commission_frac))))
                    if qty < 1:
                        continue
                    cost = fill_price * qty * (1 + commission_frac)
                    new_quantities[sym] = qty
                    spent += cost
                cash = equity_before - spent
                quantities = new_quantities
                in_position = True
                switches.append(Switch(date=date, action="ENTER",
                                       equity_before=equity_before, equity_after=_equity_on(date)))
            elif not signal_yesterday and in_position:
                proceeds = 0.0
                for sym, qty in quantities.items():
                    px_series = daily_closes[sym]
                    if date in px_series.index:
                        fill_price = float(px_series.loc[date]) * (1 - slippage_frac)
                    else:
                        prior = px_series.loc[:date]
                        fill_price = float(prior.iloc[-1]) * (1 - slippage_frac) if len(prior) else 0.0
                    proceeds += fill_price * qty * (1 - commission_frac)
                cash = cash + proceeds
                quantities = {}
                in_position = False
                switches.append(Switch(date=date, action="EXIT",
                                       equity_before=equity_before, equity_after=cash))

        equity_today = _equity_on(date)
        if date_range is None or (date_range[0] <= date < date_range[1]):
            equity_points.append((date, equity_today))

    equity_curve = pd.Series(dict(equity_points)).sort_index() if equity_points else pd.Series(dtype=float)
    return GatedRegimeCoreResult(
        equity_curve=equity_curve, composite=composite, regime_on=regime_on,
        switches=switches, composite_fill_log=fill_log,
        gate_open=gate_open, effective_on=effective_on,
        stock_ret=stock_ret, cash_ret=cash_ret, favorable=favorable,
    )
