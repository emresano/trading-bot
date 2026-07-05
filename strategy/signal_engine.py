# strategy/signal_engine.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd

from core.models import Signal, SignalAction

# Girdi sözleşmesi: daily_df ve (varsa) h4_df, çağrılmadan önce
# indicators.engine.build_features(df, cfg) ile işlenmiş olmalı — evaluate_entry/
# evaluate_exit yalnızca son (kapanmış) bar üzerinde çalışır, kendi indikatörünü
# hesaplamaz (Bölüm 3.1 ilke 2: saf çekirdek, IO/hesaplama kenar modüllerde).


@dataclass(frozen=True)
class GateResult:
    passed: bool
    name: str
    detail: str


Gate = Callable[..., GateResult]  # (daily_row, h4_row, cfg) -> GateResult


def _compute_stop(d: pd.Series, cfg) -> float:
    return float(d["close"]) - cfg.signal.atr_stop_mult * float(d["atr"])


def compute_target(d: pd.Series, cfg) -> float:
    """max(nearest_resistance, entry + 2×(entry-stop)); nearest_resistance NaN ise
    doğrudan entry + 2×(entry-stop) (mevcut fallback).

    Gerekçe: pullback girişinde en-yakın-direnç tanım gereği girişe yakındır (aksi
    halde zaten kırılmış/aşılmış olurdu) — resistance'ı doğrudan hedef almak yapısal
    olarak R:R'yi neredeyse her zaman düşürür (gate_diagnostics.py ölçümüyle
    doğrulandı). max() ile en az 2R'lik bir hedef garantilenir; resistance daha
    uzaktaysa (daha iyi bir hedef sunuyorsa) o kullanılır."""
    stop = _compute_stop(d, cfg)
    entry = float(d["close"])
    fallback = entry + 2 * (entry - stop)
    resistance = d.get("nearest_resistance", float("nan"))
    if pd.notna(resistance):
        return max(float(resistance), fallback)
    return fallback


def gate_trend(d: pd.Series, h4: Optional[pd.Series], cfg) -> GateResult:
    ema_fast_col = f"ema_{cfg.signal.ema_fast}"
    ema_slow_col = f"ema_{cfg.signal.ema_slow}"
    ok = bool(d["close"] > d[ema_slow_col] and d[ema_fast_col] > d[ema_slow_col])
    return GateResult(ok, "trend",
                      f"close={d['close']:.2f} ema{cfg.signal.ema_slow}={d[ema_slow_col]:.2f} "
                      f"ema{cfg.signal.ema_fast}={d[ema_fast_col]:.2f}")


def gate_regime(d: pd.Series, h4: Optional[pd.Series], cfg) -> GateResult:
    ok = bool(d["adx"] >= cfg.signal.adx_min)
    return GateResult(ok, "regime", f"ADX={d['adx']:.2f} < min {cfg.signal.adx_min} → yatay piyasa" if not ok
                      else f"ADX={d['adx']:.2f} >= min {cfg.signal.adx_min}")


def gate_rsi(d: pd.Series, h4: Optional[pd.Series], cfg) -> GateResult:
    ok = bool(cfg.signal.rsi_entry_low <= d["rsi"] <= cfg.signal.rsi_entry_high)
    return GateResult(ok, "rsi", f"RSI={d['rsi']:.2f} bant=[{cfg.signal.rsi_entry_low},{cfg.signal.rsi_entry_high}]")


def gate_macd(d: pd.Series, h4: Optional[pd.Series], cfg) -> GateResult:
    prev_hist = d.get("macd_hist_prev1", float("nan"))
    rising = bool(pd.notna(prev_hist) and d["macd_hist"] > prev_hist)
    above_signal = bool(d["macd"] > d["macd_signal"])
    ok = above_signal or rising
    return GateResult(ok, "macd",
                      f"MACD={d['macd']:.3f} signal={d['macd_signal']:.3f} "
                      f"above_signal={above_signal} hist_rising={rising}")


def gate_atr_anomaly(d: pd.Series, h4: Optional[pd.Series], cfg) -> GateResult:
    threshold = float(d["atr_ma20"]) * cfg.signal.atr_anomaly_mult
    ok = bool(d["atr"] <= threshold)
    return GateResult(ok, "atr_anomaly",
                      f"ATR={d['atr']:.3f} eşik={threshold:.3f} (atr_ma20×{cfg.signal.atr_anomaly_mult})")


def gate_bb_overextension(d: pd.Series, h4: Optional[pd.Series], cfg) -> GateResult:
    ok = bool(d["close"] <= d["bb_high"])
    return GateResult(ok, "bb_overextension", f"close={d['close']:.2f} bb_high={d['bb_high']:.2f}")


def gate_structure_rr(d: pd.Series, h4: Optional[pd.Series], cfg) -> GateResult:
    entry = float(d["close"])
    stop = _compute_stop(d, cfg)
    if entry <= stop:
        return GateResult(False, "structure_rr", f"geçersiz stop: entry={entry:.2f} stop={stop:.2f}")
    target = compute_target(d, cfg)
    rr = (target - entry) / (entry - stop)
    ok = bool(rr >= cfg.risk.min_rr)
    return GateResult(ok, "structure_rr", f"RR={rr:.2f} min={cfg.risk.min_rr} target={target:.2f} stop={stop:.2f}")


def gate_volume(d: pd.Series, h4: Optional[pd.Series], cfg) -> GateResult:
    ok = bool(d["vol_confirm"])
    return GateResult(ok, "volume", f"vol_confirm={ok}")


def gate_trigger_4h(d: pd.Series, h4: Optional[pd.Series], cfg) -> GateResult:
    if h4 is not None:
        ok = bool(h4["pat_engulf"] or h4["pat_pin"] or h4["pat_inside_break"])
        return GateResult(ok, "trigger_4h",
                          f"mode=4h engulf={bool(h4['pat_engulf'])} pin={bool(h4['pat_pin'])} "
                          f"inside_break={bool(h4['pat_inside_break'])}")

    # Degrade mod genişletmesi: son 3 barda (bugün dahil) mum formasyonu OLUŞTU
    # VEYA bugünkü kapanış önceki barın high'ının üstünde (basit breakout tetiği).
    # Gerekçe: tek barlık mum formasyonu şartı + günlük veri, gate_diagnostics.py
    # ölçümünde kümülatif geçişi sıfıra indiren asıl darboğazdı.
    pattern_recent = bool(d.get("pattern_recent_3bar", False))
    breakout = bool(d.get("close_above_prev_high", False))
    ok = pattern_recent or breakout
    return GateResult(ok, "trigger_4h",
                      f"mode=degrade(1d) pattern_last_3bar={pattern_recent} "
                      f"close_above_prev_high={breakout}")


def gate_mtf(d: pd.Series, h4: Optional[pd.Series], cfg) -> GateResult:
    if h4 is None:
        return GateResult(True, "mtf", "SKIP-PASS: 4h veri yok (degrade mod)")
    ema_fast_col = f"ema_{cfg.signal.ema_fast}"
    ok = bool(h4["close"] > h4[ema_fast_col])
    return GateResult(ok, "mtf", f"4h close={h4['close']:.2f} 4h ema{cfg.signal.ema_fast}={h4[ema_fast_col]:.2f}")


ENTRY_GATES: list[Gate] = [
    gate_trend, gate_regime, gate_rsi, gate_macd,
    gate_atr_anomaly, gate_bb_overextension,
    gate_structure_rr, gate_volume, gate_trigger_4h, gate_mtf,
]


def prepare_row_context(daily_df: pd.DataFrame, i: int) -> pd.Series:
    """i konumundaki barın Series'ini, çoklu-bar bağlam gerektiren gate'ler için
    gerekli türetilmiş alanlarla zenginleştirir (macd_hist_prev1, pattern_recent_3bar,
    close_above_prev_high). evaluate_entry ve backtest/gate_diagnostics.py AYNI
    fonksiyonu kullanır — böylece üretim değerlendirmesi ile teşhis ölçümü arasında
    davranış sapması olmaz."""
    d = daily_df.iloc[i].copy()
    d["macd_hist_prev1"] = float(daily_df["macd_hist"].iloc[i - 1]) if i >= 1 else float("nan")

    pattern_cols = ["pat_engulf", "pat_pin", "pat_inside_break"]
    recent = daily_df[pattern_cols].iloc[max(0, i - 2): i + 1]
    d["pattern_recent_3bar"] = bool(recent.to_numpy().any())
    d["close_above_prev_high"] = bool(i >= 1 and daily_df["close"].iloc[i] > daily_df["high"].iloc[i - 1])
    return d

_SNAPSHOT_FIELDS = (
    "close", "adx", "rsi", "macd", "macd_signal", "macd_hist",
    "atr", "atr_ma20", "bb_low", "bb_mid", "bb_high", "nearest_support", "nearest_resistance",
)


def snapshot_features(d: pd.Series, h4: Optional[pd.Series], cfg) -> dict[str, float]:
    features: dict[str, float] = {}
    for key in _SNAPSHOT_FIELDS:
        if key in d.index:
            val = d[key]
            features[key] = float(val) if pd.notna(val) else float("nan")
    ema_fast_col = f"ema_{cfg.signal.ema_fast}"
    ema_slow_col = f"ema_{cfg.signal.ema_slow}"
    if ema_fast_col in d.index:
        features["ema_fast"] = float(d[ema_fast_col]) if pd.notna(d[ema_fast_col]) else float("nan")
    if ema_slow_col in d.index:
        features["ema_slow"] = float(d[ema_slow_col]) if pd.notna(d[ema_slow_col]) else float("nan")
    if h4 is not None:
        if "close" in h4.index:
            features["h4_close"] = float(h4["close"]) if pd.notna(h4["close"]) else float("nan")
        if ema_fast_col in h4.index:
            features["h4_ema_fast"] = float(h4[ema_fast_col]) if pd.notna(h4[ema_fast_col]) else float("nan")
    return features


def evaluate_entry(symbol: str, daily_df: pd.DataFrame, h4_df: Optional[pd.DataFrame], cfg) -> Signal:
    d = prepare_row_context(daily_df, len(daily_df) - 1)  # SON KAPANMIŞ günlük bar
    h4 = h4_df.iloc[-1] if h4_df is not None and not h4_df.empty else None

    results: list[str] = []
    features = snapshot_features(d, h4, cfg)
    for gate in ENTRY_GATES:
        r = gate(d, h4, cfg)
        results.append(f"[{'PASS' if r.passed else 'FAIL'}] {r.name}: {r.detail}")
        if not r.passed:
            return Signal(symbol, d.name, SignalAction.HOLD_CASH, results, features,
                          entry_ref_price=float(d["close"]))

    stop = _compute_stop(d, cfg)
    target = compute_target(d, cfg)
    return Signal(symbol, d.name, SignalAction.ENTER_LONG, results, features,
                  entry_ref_price=float(d["close"]),
                  suggested_stop=stop, suggested_target=target)


def evaluate_exit(symbol: str, daily_df: pd.DataFrame, cfg) -> Signal:
    """Açık pozisyon için her günlük bar kapanışında çağrılır.
    close < ema_fast VEYA (macd_hist üç bardır düşüyor VE macd < signal) → EXIT_LONG."""
    d = daily_df.iloc[-1]
    reasons: list[str] = []

    ema_fast_col = f"ema_{cfg.signal.ema_fast}"
    close_below_ema_fast = bool(d["close"] < d[ema_fast_col])
    reasons.append(
        f"[{'TETIK' if close_below_ema_fast else 'pas'}] close<ema{cfg.signal.ema_fast}: "
        f"close={d['close']:.2f} ema{cfg.signal.ema_fast}={d[ema_fast_col]:.2f}"
    )

    declining_3 = False
    if len(daily_df) >= 3:
        h0 = daily_df["macd_hist"].iloc[-1]
        h1 = daily_df["macd_hist"].iloc[-2]
        h2 = daily_df["macd_hist"].iloc[-3]
        declining_3 = bool(h0 < h1 < h2)
    macd_below_signal = bool(d["macd"] < d["macd_signal"])
    momentum_collapse = declining_3 and macd_below_signal
    reasons.append(
        f"[{'TETIK' if momentum_collapse else 'pas'}] momentum_collapse: "
        f"hist_3bar_dususte={declining_3} macd<signal={macd_below_signal}"
    )

    action = SignalAction.EXIT_LONG if (close_below_ema_fast or momentum_collapse) else SignalAction.HOLD_POSITION
    features = snapshot_features(d, None, cfg)
    return Signal(symbol, d.name, action, reasons, features, entry_ref_price=float(d["close"]))


def _main() -> None:
    import argparse

    from core.config import load_config
    from data.historical import load_cached
    from indicators.engine import build_features

    parser = argparse.ArgumentParser(description="Belirli bir tarih için sinyal huni kararlarını basar (debug)")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD — o tarihe kadarki günlük veriyle huni koşturulur")
    parser.add_argument("--config", default="config/config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    daily = load_cached(args.symbol, "1d")
    if daily.empty:
        print(f"UYARI: {args.symbol} için cache boş. Önce şunu çalıştırın: "
              f"python -m data.historical --symbols {args.symbol}")
        return

    daily = daily.loc[:args.date]
    if daily.empty:
        print(f"UYARI: {args.date} tarihinde/öncesinde veri yok.")
        return
    if len(daily) < cfg.signal.min_history_bars:
        print(f"UYARI: {args.date} itibarıyla yalnızca {len(daily)} bar var "
              f"(min {cfg.signal.min_history_bars}); sonuçlar güvenilmez olabilir.")

    feats = build_features(daily, cfg)
    signal = evaluate_entry(args.symbol, feats, None, cfg)

    print(f"{signal.symbol} — {signal.ts} — {signal.action.value}")
    for line in signal.reasons:
        print(f"  {line}")
    if signal.action == SignalAction.ENTER_LONG:
        print(f"  stop={signal.suggested_stop:.2f} target={signal.suggested_target:.2f}")


if __name__ == "__main__":
    _main()
