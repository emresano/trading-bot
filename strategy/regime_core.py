# strategy/regime_core.py
"""Rejim-Filtreli Çekirdek (D1) — ÜRETİM strateji ailesi (P1 üretim portu).

KALICI KAYIT 6 ile kabul edilen D1 ailesinin üretim implementasyonu. Referans
ölçüm: REGIME_CORE_S1B.md. "backtest=canlı aynı fonksiyon" ilkesi (CLAUDE.md
Bölüm 3.1): sinyal (build_composite/compute_regime_signal) ve boyutlama
(plan_enter/plan_exit) SAF fonksiyonlardır; backtest sürücüsü (run_regime_core_prod)
ve gelecekteki canlı döngü (Faz 5, kapsam dışı) AYNI fonksiyonları çağırır.

BAĞIMSIZLIK: bu modül `backtest/regime_core.py` SPIKE'ına BAĞIMLI DEĞİLDİR
(spike REFERANS olarak kalır, üretim kodu ondan bağımsızdır — P1 kapsam notu).
Semantik BİREBİR korunur (hiçbir eşik/parametre değişmez):
- 12 sembol eşit ağırlık kompozit (t0-normalize kapanış ortalaması).
- GİRİŞ: close > MA(N)×(1+b) ardışık M gün; ÇIKIŞ: close < MA(N)×(1−b) tek gün.
- Yürütme: sinyal t kapanışı → işlem t+1 KAPANIŞ fiyatı.
- Komisyon commission_bps + slippage slippage_bps; TAM-LOT (kesirli hisse yok),
  artık nakit nakit bacağında kalır ve tahakkuk alır.
- Nakit dönemde TRY_ON_RATE − 200bp, ACT/365, takvim-günü üssü, ENTER günü
  DAHİL / EXIT günü HARİÇ.
- Breaker (KALICI KAYIT 6): ALARM -%25, FREEZE -%40 (bkz. RegimeCoreBreaker).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd

CASH_YIELD_HAIRCUT = 0.02  # 200bp — muhafazakâr kırpma (spike ile aynı sabit)


@dataclass(frozen=True)
class RegimeCoreParams:
    symbols: list[str]
    ma_period: int = 200          # N
    band_pct: float = 0.01        # b
    confirm_days: int = 3         # M (giriş teyidi; çıkış her zaman 1 gün)
    commission_bps: float = 10.0
    slippage_bps: float = 5.0
    initial_equity: float = 100_000.0
    cash_yield_haircut: float = CASH_YIELD_HAIRCUT
    # Breaker (KALICI KAYIT 6) — bilgi amaçlı varsayılanlar; breaker nesnesi ayrı verilir.
    alarm_drawdown_pct: float = 0.25
    freeze_drawdown_pct: float = 0.40


@dataclass
class Switch:
    date: pd.Timestamp
    action: str          # "ENTER" | "EXIT"
    equity_before: float
    equity_after: float


class BreakerState(str, Enum):
    OK = "OK"
    ALARM = "ALARM"     # bildirim; DAVRANIŞ DEĞİŞMEZ
    FREEZE = "FREEZE"   # yeni ENTER yok (çıkış devam); reset yalnız kullanıcı


@dataclass
class RegimeCoreProdResult:
    equity_curve: pd.Series
    composite: pd.Series
    regime_on: pd.Series
    switches: list[Switch] = field(default_factory=list)
    composite_fill_log: list[dict] = field(default_factory=list)
    breaker_events: list[dict] = field(default_factory=list)   # [{date, state, drawdown, equity, peak}]
    freeze_trips: int = 0                  # FREEZE breaker tetiklenme (edge) sayısı — kriter D: 0 olmalı
    enters_blocked_by_freeze: int = 0      # FREEZE aktifken atlanan ENTER sayısı (sonuç)
    alarm_trips: int = 0                   # bildirim-only ALARM epizot sayısı


# ============================================================ SAF SİNYAL (backtest=canlı)

def build_composite(daily_closes: dict[str, pd.Series]) -> tuple[pd.Series, list[dict]]:
    """t0-normalize (t0 = en geç başlayan sembolün ilk günü) eşit-ağırlık kompozit.
    Tekil eksik gün: son bilinen normalize değerle taşınır (ffill), loglanır."""
    t0 = max(s.index[0] for s in daily_closes.values())
    union_dates: set = set()
    for s in daily_closes.values():
        union_dates |= set(s.index)
    all_dates = sorted(d for d in union_dates if d >= t0)

    normalized: dict[str, pd.Series] = {}
    for sym, closes in daily_closes.items():
        s = closes.loc[closes.index >= t0]
        normalized[sym] = s / float(s.iloc[0])

    fill_log: list[dict] = []
    aligned_cols = {}
    for sym, series in normalized.items():
        reindexed = series.reindex(all_dates)
        for d in reindexed.index[reindexed.isna()]:
            fill_log.append({"symbol": sym, "date": d, "action": "forward_fill"})
        aligned_cols[sym] = reindexed.ffill()

    matrix = pd.DataFrame(aligned_cols).dropna(how="any")
    composite = matrix.mean(axis=1)
    composite.index.name = "ts"
    return composite, fill_log


def compute_regime_signal(composite: pd.Series, ma_period: int, band_pct: float,
                          confirm_days: int) -> pd.Series:
    """Asimetrik histerezis rejim sinyali (giriş teyitli, çıkış tek gün).
    Döner bool Series; True = o günün kapanışında rejim ON kararı."""
    ma = composite.rolling(ma_period).mean()
    upper = ma * (1 + band_pct)
    lower = ma * (1 - band_pct)
    above_upper = composite > upper
    below_lower = composite < lower
    confirmed_entry = above_upper.rolling(confirm_days).sum() >= confirm_days

    regime_on = pd.Series(False, index=composite.index)
    state = False
    for i in range(len(composite)):
        if pd.isna(ma.iloc[i]):
            regime_on.iloc[i] = False
            continue
        if not state and bool(confirmed_entry.iloc[i]):
            state = True
        elif state and bool(below_lower.iloc[i]):
            state = False
        regime_on.iloc[i] = state
    return regime_on


# ============================================================ SAF BOYUTLAMA (backtest=canlı)

def mark_to_market(cash: float, quantities: dict[str, int], prices: dict[str, float]) -> float:
    """Nakit + Σ qty×fiyat. `prices` her tutulan sembol için (bugünkü ya da son
    bilinen) ham fiyatı içermeli — canlıda broker son fiyatı, backtest'te sürücü sağlar."""
    total = cash
    for sym, qty in quantities.items():
        total += qty * prices[sym]
    return total


def plan_enter(equity: float, prices_today: dict[str, float], symbols: list[str],
               commission_bps: float, slippage_bps: float) -> tuple[dict[str, int], float]:
    """TAM-LOT eşit-ağırlık giriş planı (saf). equity'yi len(symbols)'e böler; her
    sembolde slippage'lı fill fiyatından tam sayı lot alır (komisyon dahil bütçeye
    sığacak kadar); artık nakit döner. `prices_today`: yalnızca o gün fiyatı OLAN
    semboller (olmayanlar atlanır — spike semantiği). Döner: (quantities, cash_after)."""
    commission_frac = commission_bps / 1e4
    slippage_frac = slippage_bps / 1e4
    per_symbol_budget = equity / len(symbols)
    quantities: dict[str, int] = {}
    spent = 0.0
    for sym in symbols:
        if sym not in prices_today:
            continue
        fill_price = prices_today[sym] * (1 + slippage_frac)
        qty = int(np.floor(per_symbol_budget / (fill_price * (1 + commission_frac))))
        if qty < 1:
            continue
        quantities[sym] = qty
        spent += fill_price * qty * (1 + commission_frac)
    cash_after = equity - spent
    return quantities, cash_after


def plan_exit(quantities: dict[str, int], exit_prices: dict[str, float],
              commission_bps: float, slippage_bps: float) -> float:
    """Tüm pozisyonları satış geliri (saf). `exit_prices`: her tutulan sembol için
    ham fiyat (bugünkü ya da son bilinen — sürücü sağlar). Döner: toplam proceeds."""
    commission_frac = commission_bps / 1e4
    slippage_frac = slippage_bps / 1e4
    proceeds = 0.0
    for sym, qty in quantities.items():
        fill_price = exit_prices[sym] * (1 - slippage_frac)
        proceeds += fill_price * qty * (1 - commission_frac)
    return proceeds


def _build_daily_cash_rate(cash_rate: Optional[pd.Series], all_dates: pd.DatetimeIndex) -> Optional[pd.Series]:
    if cash_rate is None:
        return None
    return cash_rate.reindex(all_dates, method="ffill").bfill()


# ============================================================ BREAKER (KALICI KAYIT 6)

class RegimeCoreBreaker:
    """D1 ailesi breaker'ı (KALICI KAYIT 6): ALARM -%25 (bildirim, davranış
    değişmez), FREEZE -%40 (yeni ENTER yok; rejim ÇIKIŞI devam eder; reset yalnız
    kullanıcı — freeze_file'ı elle siler). Backtest'te izole freeze_file kullanılır."""

    def __init__(self, alarm_pct: float = 0.25, freeze_pct: float = 0.40,
                 freeze_file: Optional[Path] = None,
                 alarm_hook: Optional[Callable[[dict], None]] = None):
        self.alarm_pct = alarm_pct
        self.freeze_pct = freeze_pct
        self.freeze_file = freeze_file
        self.alarm_hook = alarm_hook
        self._alarm_latched = False

    def freeze_active(self) -> bool:
        if self.freeze_file is None:
            return False
        return self.freeze_file.exists()

    def evaluate(self, date, equity: float, peak: float) -> BreakerState:
        """Günlük drawdown'a göre durum. FREEZE eşiğinde freeze_file yazılır
        (kalıcı; yalnız kullanıcı siler). ALARM eşiğinde hook çağrılır (bir kez
        latch'lenir — her gün spam etmez; peak yenilenince reset olur)."""
        if peak <= 0:
            return BreakerState.OK
        drawdown = 1 - (equity / peak)
        if drawdown >= self.freeze_pct:
            if self.freeze_file is not None and not self.freeze_file.exists():
                self.freeze_file.parent.mkdir(parents=True, exist_ok=True)
                self.freeze_file.write_text(
                    f"date={date} equity={equity} peak={peak} drawdown={drawdown:.4f} "
                    f"esik={self.freeze_pct} (FREEZE — reset yalnız kullanıcı)\n"
                )
            return BreakerState.FREEZE
        if drawdown >= self.alarm_pct:
            if not self._alarm_latched and self.alarm_hook is not None:
                self.alarm_hook({"date": date, "equity": equity, "peak": peak, "drawdown": drawdown})
            self._alarm_latched = True
            return BreakerState.ALARM
        # peak'e yaklaşınca alarm latch reset (yeni bir düşüş yeni bir bildirim üretebilsin)
        if drawdown < self.alarm_pct * 0.5:
            self._alarm_latched = False
        return BreakerState.OK


# ============================================================ BACKTEST SÜRÜCÜSÜ (aynı saf fonksiyonlar)

def run_regime_core_prod(
    daily_closes: dict[str, pd.Series],
    params: RegimeCoreParams,
    date_range: Optional[tuple[pd.Timestamp, pd.Timestamp]] = None,
    cash_rate: Optional[pd.Series] = None,
    breaker: Optional[RegimeCoreBreaker] = None,
) -> RegimeCoreProdResult:
    """Üretim backtest döngüsü — SPIKE ile BİREBİR aynı semantik, saf fonksiyonlarla.
    Breaker verilirse FREEZE aktifken yeni ENTER atlanır (çıkış devam eder); ALARM
    bildirim-only. `cash_rate=None` → tahakkuk yok (S1 davranışı)."""
    composite, fill_log = build_composite(daily_closes)
    regime_on = compute_regime_signal(composite, params.ma_period, params.band_pct, params.confirm_days)

    all_dates = composite.index
    daily_cash_rate = _build_daily_cash_rate(cash_rate, all_dates)
    cash = params.initial_equity
    quantities: dict[str, int] = {}
    in_position = False
    switches: list[Switch] = []
    equity_points: list[tuple[pd.Timestamp, float]] = []
    breaker_events: list[dict] = []
    freeze_trips = 0
    enters_blocked_by_freeze = 0
    alarm_trips = 0
    prev_breaker_state = BreakerState.OK
    peak_equity = params.initial_equity

    def _prices_for_mtm(date) -> dict[str, float]:
        """Tutulan her sembol için ham fiyat: bugünkü varsa o, yoksa son bilinen."""
        out: dict[str, float] = {}
        for sym in quantities:
            px = daily_closes[sym]
            if date in px.index:
                out[sym] = float(px.loc[date])
            else:
                prior = px.loc[:date]
                out[sym] = float(prior.iloc[-1]) if len(prior) else 0.0
        return out

    for i, date in enumerate(all_dates):
        signal_yesterday = bool(regime_on.iloc[i - 1]) if i > 0 else False

        # Nakit getirisi tahakkuku (S1b): transition ÖNCESİ in_position'a göre.
        if i > 0 and not in_position and daily_cash_rate is not None:
            days_elapsed = (date - all_dates[i - 1]).days
            annual_rate = daily_cash_rate.loc[date]
            if pd.notna(annual_rate) and days_elapsed > 0:
                r_net = max(float(annual_rate) - params.cash_yield_haircut, 0.0)
                cash *= (1 + r_net / 365) ** days_elapsed

        # t+1 yürütme: dünün sinyal değişimini bugünün kapanışında uygula.
        if i > 0 and signal_yesterday != in_position:
            equity_before = mark_to_market(cash, quantities, _prices_for_mtm(date))
            if signal_yesterday and not in_position:
                # ENTER — breaker FREEZE aktifse ATLA (yeni pozisyon yok).
                if breaker is not None and breaker.freeze_active():
                    enters_blocked_by_freeze += 1
                    breaker_events.append({"date": date, "state": "FREEZE_BLOCK_ENTER",
                                           "equity": equity_before, "peak": peak_equity})
                else:
                    prices_today = {sym: float(daily_closes[sym].loc[date])
                                    for sym in params.symbols if date in daily_closes[sym].index}
                    quantities, cash = plan_enter(equity_before, prices_today, params.symbols,
                                                  params.commission_bps, params.slippage_bps)
                    in_position = True
                    switches.append(Switch(date, "ENTER", equity_before,
                                           mark_to_market(cash, quantities, _prices_for_mtm(date))))
            elif not signal_yesterday and in_position:
                # EXIT — her zaman serbest (breaker çıkışı engellemez).
                proceeds = plan_exit(quantities, _prices_for_mtm(date),
                                     params.commission_bps, params.slippage_bps)
                cash = cash + proceeds
                quantities = {}
                in_position = False
                switches.append(Switch(date, "EXIT", equity_before, cash))

        equity_today = mark_to_market(cash, quantities, _prices_for_mtm(date)) if quantities else cash
        peak_equity = max(peak_equity, equity_today)

        # Breaker değerlendirmesi (gün sonu equity'ye göre; FREEZE gelecekteki ENTER'ları etkiler).
        # ALARM epizot bazlı sayılır (bildirim latch'iyle tutarlı: bir excursion'da
        # bir kez; drawdown alarm_pct/2 altına inince epizot kapanır — aynı derin
        # düşüşteki 25% çizgisi yeniden-geçişleri MÜKERRER SAYILMAZ). FREEZE edge bazlı.
        if breaker is not None:
            state = breaker.evaluate(date, equity_today, peak_equity)
            drawdown_now = 1 - equity_today / peak_equity
            if drawdown_now < breaker.alarm_pct * 0.5:
                prev_breaker_state = BreakerState.OK   # epizot kapandı → latch reset
            if state == BreakerState.ALARM and prev_breaker_state != BreakerState.ALARM:
                alarm_trips += 1
                breaker_events.append({"date": date, "state": "ALARM", "drawdown": drawdown_now,
                                       "equity": equity_today, "peak": peak_equity})
                prev_breaker_state = BreakerState.ALARM
            elif state == BreakerState.FREEZE and prev_breaker_state != BreakerState.FREEZE:
                freeze_trips += 1
                breaker_events.append({"date": date, "state": "FREEZE_TRIP", "drawdown": drawdown_now,
                                       "equity": equity_today, "peak": peak_equity})
                prev_breaker_state = BreakerState.FREEZE

        if date_range is None or (date_range[0] <= date < date_range[1]):
            equity_points.append((date, equity_today))

    equity_curve = pd.Series(dict(equity_points)).sort_index() if equity_points else pd.Series(dtype=float)
    return RegimeCoreProdResult(
        equity_curve=equity_curve, composite=composite, regime_on=regime_on,
        switches=switches, composite_fill_log=fill_log, breaker_events=breaker_events,
        freeze_trips=freeze_trips, enters_blocked_by_freeze=enters_blocked_by_freeze,
        alarm_trips=alarm_trips,
    )
