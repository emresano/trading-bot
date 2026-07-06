# tools/gate_ablation.py
"""Salt-okunur gate ablasyon (counterfactual) analizi — DIAGNOSTICS_v6.md Paket 3.

Hiçbir strateji eşiği/gate/parametre DEĞİŞTİRİLMEZ. Bu araç yalnızca "bu gate
olmasaydı ne olurdu" sorusuna, izole (portföy/nakit/breaker etkileşimsiz,
sabit 1R risk) bir sinyal-kalite ölçümüyle cevap arar — bu bir backtest
DEĞİLDİR, yalnızca sinyal kalitesi ölçümüdür.
"""
from __future__ import annotations
from typing import Optional

import pandas as pd

from strategy.signal_engine import (
    ENTRY_GATES,
    compute_target,
    evaluate_exit,
    prepare_row_context,
)

GATE_NAMES = [g.__name__.replace("gate_", "") for g in ENTRY_GATES]


def compute_gate_matrix(daily_features: dict[str, pd.DataFrame], cfg) -> pd.DataFrame:
    """Her (sembol, tarih) için 10 gate'in PASS/FAIL sonucunu (kısa devre YOK,
    hepsi bağımsız değerlendirilir) döner."""
    min_history = cfg.signal.min_history_bars
    rows = []
    for sym, df in daily_features.items():
        for i in range(min_history, len(df)):
            d = prepare_row_context(df, i)
            row = {"symbol": sym, "date": df.index[i], "pos": i}
            for gate, name in zip(ENTRY_GATES, GATE_NAMES):
                row[name] = gate(d, None, cfg).passed
            rows.append(row)
    return pd.DataFrame(rows)


def find_counterfactual_candidates(matrix: pd.DataFrame, gate_name: str) -> pd.DataFrame:
    """Diğer 9 gate'i geçip YALNIZCA `gate_name`'den elenen (sembol, tarih, pos)
    satırlarını döner."""
    other_gates = [g for g in GATE_NAMES if g != gate_name]
    mask = (~matrix[gate_name]) & matrix[other_gates].all(axis=1)
    return matrix[mask][["symbol", "date", "pos"]].reset_index(drop=True)


def simulate_isolated_entry(df: pd.DataFrame, signal_idx: int, cfg) -> Optional[dict]:
    """`signal_idx`: sinyalin dayandığı (kapanmış) barın konumu. t+1 açılışında
    dolar; ileriye doğru stop/target (stop öncelikli, Bölüm 12.2) veya
    evaluate_exit sinyaliyle kapanır. Portföy/nakit/breaker/korelasyon YOK —
    yalnızca bu tek sinyalin R-multiple sonucu. Veri yetersizse None döner."""
    if signal_idx + 1 >= len(df):
        return None

    d = df.iloc[signal_idx]
    entry_ref = float(d["close"])
    stop = entry_ref - cfg.signal.atr_stop_mult * float(d["atr"])
    if entry_ref <= stop:
        return None
    target = compute_target(d, cfg)

    fill_idx = signal_idx + 1
    fill_price = float(df["open"].iloc[fill_idx]) * (1 + cfg.costs.slippage_bps / 1e4)
    per_share_risk = fill_price - stop
    if per_share_risk <= 0:
        return None

    for i in range(fill_idx, len(df)):
        bar = df.iloc[i]
        hit_stop = bar["low"] <= stop
        hit_target = bar["high"] >= target
        if hit_stop or hit_target:
            if hit_stop:  # STOP ÖNCELİKLİ (Bölüm 12.2), gerçek motorla tutarlı
                exit_price = stop * (1 - cfg.costs.slippage_bps / 1e4)
                reason = "STOP"
            else:
                exit_price = target
                reason = "TARGET"
            r_multiple = (exit_price - fill_price) / per_share_risk
            return {"r_multiple": r_multiple, "exit_reason": reason, "bars_held": i - fill_idx}

        window = df.iloc[: i + 1]
        sig = evaluate_exit("ISOLATED", window, cfg)
        if sig.action.value == "EXIT_LONG":
            if i + 1 < len(df):
                exit_price = float(df["open"].iloc[i + 1]) * (1 - cfg.costs.slippage_bps / 1e4)
                r_multiple = (exit_price - fill_price) / per_share_risk
                return {"r_multiple": r_multiple, "exit_reason": "SIGNAL_EXIT", "bars_held": i + 1 - fill_idx}
            return None  # veri tam çıkıştan önce bitti

    return None  # veri sonuna kadar pozisyon açık kaldı — ölçülemez


def run_ablation_for_gate(daily_features: dict[str, pd.DataFrame], matrix: pd.DataFrame, gate_name: str, cfg) -> pd.DataFrame:
    candidates = find_counterfactual_candidates(matrix, gate_name)
    results = []
    for _, row in candidates.iterrows():
        df = daily_features[row["symbol"]]
        r = simulate_isolated_entry(df, row["pos"], cfg)
        if r is not None:
            r["symbol"] = row["symbol"]
            r["date"] = row["date"]
            results.append(r)
    return pd.DataFrame(results)


def summarize_isolated(results: pd.DataFrame) -> dict:
    if results.empty:
        return {"n": 0, "win_rate": 0.0, "avg_r": 0.0, "profit_factor": 0.0}
    n = len(results)
    wins = results[results["r_multiple"] > 0]
    losses = results[results["r_multiple"] <= 0]
    win_rate = len(wins) / n
    avg_r = results["r_multiple"].mean()
    gross_win = wins["r_multiple"].sum()
    gross_loss = -losses["r_multiple"].sum()
    if gross_loss > 0:
        pf = gross_win / gross_loss
    else:
        pf = float("inf") if gross_win > 0 else 0.0
    return {"n": n, "win_rate": win_rate, "avg_r": avg_r, "profit_factor": pf}


def run_baseline_isolated(daily_features: dict[str, pd.DataFrame], trades_df: pd.DataFrame, cfg) -> pd.DataFrame:
    """Gerçekleşen trade'lerin SİNYAL barını (giriş tarihinden bir önceki bar)
    bulup AYNI izole simülatörle yeniden ölçer — adil kıyas tabanı."""
    results = []
    for _, trade in trades_df.iterrows():
        sym = trade["symbol"]
        df = daily_features.get(sym)
        if df is None:
            continue
        entry_date = pd.Timestamp(trade["entry_date"])
        if entry_date not in df.index:
            continue
        fill_idx = df.index.get_loc(entry_date)
        signal_idx = fill_idx - 1
        if signal_idx < 0:
            continue
        r = simulate_isolated_entry(df, signal_idx, cfg)
        if r is not None:
            r["symbol"] = sym
            r["date"] = df.index[signal_idx]
            results.append(r)
    return pd.DataFrame(results)
