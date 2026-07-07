# risk/direction.py
"""Yön-farkındalıklı short mekanikleri (EXPANSION.md Bölüm 9.1/9.2).

E2 KAPSAMI: yalnızca motor YETENEĞİ (Direction mekaniği) — short GATE seti
tasarımı KAPSAM DIŞI (Bölüm 8). Bu modül saf fonksiyonlardır (IO yok):
stop/hedef aynalama, R:R, birim-risk, genel boyutlama (quote-ccy + marjin),
intrabar fill (stop-önceliği) ve MTM. LONG durumunda değerler mevcut çekirdek
davranışıyla birebir örtüşür (BIST golden korunur).

Not (Bölüm 8): `direction_mode: two_sided` bir profil, short gate seti
tanımlanana kadar backtest'te AKTİVE EDİLMEZ; bu yüzden run_backtest ana döngüsü
LONG-only kalır. Buradaki mekanikler tasarım turunda (FX aktivasyonu) ve
PaperBroker'da (Faz 5) tüketilecektir; şimdi tam test edilir.
"""
from __future__ import annotations

import math
from typing import Optional

from core.models import Direction, RejectReason, Side


def per_unit_risk(entry: float, stop: float) -> float:
    """Birim başına risk (quote ccy) — her iki yönde abs(entry-stop) > 0 beklenir."""
    return abs(entry - stop)


def compute_stop_target(entry: float, atr: float, atr_stop_mult: float,
                        direction: Direction, nearest_level: Optional[float] = None) -> tuple[float, float]:
    """Yön-aynalı stop/hedef (Bölüm 9.1).
    LONG:  stop = entry - k·atr (altta), hedef = max(nearest_resistance, entry + 2·(entry-stop)).
    SHORT: stop = entry + k·atr (üstte), hedef = min(nearest_support, entry - 2·(stop-entry)).
    `nearest_level` LONG'da direnç, SHORT'ta destek; None ise 2R fallback."""
    if direction == Direction.SHORT:
        stop = entry + atr_stop_mult * atr
        fallback = entry - 2 * (stop - entry)
        target = min(nearest_level, fallback) if nearest_level is not None else fallback
        return stop, target
    stop = entry - atr_stop_mult * atr
    fallback = entry + 2 * (entry - stop)
    target = max(nearest_level, fallback) if nearest_level is not None else fallback
    return stop, target


def reward_risk(entry: float, stop: float, target: float, direction: Direction) -> float:
    """R:R — LONG (target-entry)/(entry-stop); SHORT (entry-target)/(stop-entry).
    Geçersiz stop yönünde 0.0 (LONG'da entry<=stop, SHORT'ta entry>=stop)."""
    if direction == Direction.SHORT:
        return (entry - target) / (stop - entry) if stop > entry else 0.0
    return (target - entry) / (entry - stop) if entry > stop else 0.0


def size_position(
    equity: float, risk_per_trade_pct: float, entry: float, stop: float,
    *, direction: Direction = Direction.LONG, qty_step: float = 1.0,
    max_position_notional_pct: float, commission_bps: float,
    cash: float, quote_to_sleeve_rate: Optional[float] = None,
    max_leverage: Optional[float] = None, free_margin: Optional[float] = None,
) -> tuple[float, Optional[RejectReason]]:
    """Genel boyutlama (Bölüm 9.2 süperseti). Dönen: (qty, reject|None).

    - per_unit_risk = abs(entry-stop); quote_ccy != sleeve_ccy ise
      quote_to_sleeve_rate'e bölünür (örn. USDJPY için ÷ USDJPY kuru).
    - qty = floor(risk_amount / per_unit_risk / qty_step) × qty_step.
    - hisse: notional + nakit kırpmaları (mevcut BIST mantığı).
    - FX (max_leverage verilirse): qty ≤ (free_margin × max_leverage) / entry;
      yetmezse MARGIN_INSUFFICIENT."""
    pur = per_unit_risk(entry, stop)
    if pur <= 0:
        return 0.0, RejectReason.POSITION_TOO_SMALL
    if quote_to_sleeve_rate is not None:
        pur = pur / quote_to_sleeve_rate

    risk_amount = equity * risk_per_trade_pct
    qty = math.floor(risk_amount / pur / qty_step) * qty_step

    # notional tavanı (fiyat üzerinden — yön-bağımsız)
    max_notional = equity * max_position_notional_pct
    qty = min(qty, math.floor(max_notional / entry / qty_step) * qty_step)

    # nakit kırpması (hisse; long alımda nakit gerekir)
    if max_leverage is None:
        qty = min(qty, math.floor(cash / (entry * (1 + commission_bps / 1e4)) / qty_step) * qty_step)
    else:
        # FX marjin kırpması
        fm = free_margin if free_margin is not None else cash
        margin_qty = math.floor((fm * max_leverage) / entry / qty_step) * qty_step
        if margin_qty < qty_step:
            return 0.0, RejectReason.MARGIN_INSUFFICIENT
        qty = min(qty, margin_qty)

    if qty < qty_step:
        return 0.0, RejectReason.POSITION_TOO_SMALL
    return qty, None


def intrabar_fill(bar_high: float, bar_low: float, stop: float, target: float,
                  direction: Direction, slippage_bps: float) -> Optional[tuple[float, str]]:
    """Intrabar stop/target fill (stop-ÖNCELİKLİ, yön-simetrik — Bölüm 9.1).
    LONG:  stop tetik low<=stop (slippage aleyhte, altta), target high>=target (limit, slippagesiz).
    SHORT: stop tetik high>=stop (slippage aleyhte, üstte), target low<=target.
    Dönen: (fill_price, "STOP"|"TARGET") ya da None (tetik yok)."""
    if direction == Direction.SHORT:
        hit_stop = bar_high >= stop
        hit_target = bar_low <= target
        if hit_stop:
            return stop * (1 + slippage_bps / 1e4), "STOP"   # aleyhte: stop'un ÜSTÜNDE dolar
        if hit_target:
            return target, "TARGET"
        return None
    hit_stop = bar_low <= stop
    hit_target = bar_high >= target
    if hit_stop:
        return stop * (1 - slippage_bps / 1e4), "STOP"       # aleyhte: stop'un ALTINDA dolar
    if hit_target:
        return target, "TARGET"
    return None


def unrealized_pnl(entry: float, last: float, qty: float, direction: Direction) -> float:
    """MTM (Bölüm 9.1): LONG qty×(last-entry); SHORT qty×(entry-last)."""
    if direction == Direction.SHORT:
        return qty * (entry - last)
    return qty * (last - entry)


def realized_pnl(entry_fill: float, exit_fill: float, qty: float, direction: Direction) -> float:
    """Kapanış P&L'i (komisyon hariç): LONG qty×(exit-entry); SHORT qty×(entry-exit)."""
    if direction == Direction.SHORT:
        return qty * (entry_fill - exit_fill)
    return qty * (exit_fill - entry_fill)


def entry_side(direction: Direction) -> Side:
    return Side.SELL if direction == Direction.SHORT else Side.BUY


def exit_side(direction: Direction) -> Side:
    return Side.BUY if direction == Direction.SHORT else Side.SELL
