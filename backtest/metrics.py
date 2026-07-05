# backtest/metrics.py
from __future__ import annotations
from dataclasses import dataclass

import numpy as np
import pandas as pd

from backtest.engine import Trade

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class Metrics:
    total_return: float
    cagr: float
    max_drawdown: float
    sharpe: float
    win_rate: float
    profit_factor: float
    avg_r_multiple: float
    expectancy: float
    trade_count: int
    time_in_cash_pct: float


def compute_metrics(equity_curve: pd.Series, trades: list[Trade]) -> Metrics:
    if equity_curve.empty:
        return Metrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 100.0)

    total_return = float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1)

    days = (equity_curve.index[-1] - equity_curve.index[0]).days
    years = days / 365.25
    cagr = float((equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / years) - 1) if years > 0 else 0.0

    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1
    max_drawdown = float(drawdown.min())

    daily_returns = equity_curve.pct_change().dropna()
    sharpe = (
        float(daily_returns.mean() / daily_returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR))
        if daily_returns.std() > 0 else 0.0
    )

    trade_count = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    win_rate = len(wins) / trade_count if trade_count else 0.0

    gross_profit = sum(t.pnl for t in wins)
    gross_loss = -sum(t.pnl for t in losses)
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    else:
        profit_factor = float("inf") if gross_profit > 0 else 0.0

    avg_r_multiple = sum(t.r_multiple for t in trades) / trade_count if trade_count else 0.0
    expectancy = sum(t.pnl for t in trades) / trade_count if trade_count else 0.0

    total_days = len(equity_curve)
    covered_days: set = set()
    for t in trades:
        mask = (equity_curve.index >= t.entry_date) & (equity_curve.index <= t.exit_date)
        covered_days.update(equity_curve.index[mask])
    time_in_cash_pct = 100.0 * (1 - len(covered_days) / total_days) if total_days else 100.0

    return Metrics(
        total_return=total_return, cagr=cagr, max_drawdown=max_drawdown, sharpe=sharpe,
        win_rate=win_rate, profit_factor=profit_factor, avg_r_multiple=avg_r_multiple,
        expectancy=expectancy, trade_count=trade_count, time_in_cash_pct=time_in_cash_pct,
    )


def compute_buy_hold_metrics(price_df: pd.DataFrame, initial_equity: float) -> Metrics:
    """Bir fiyat serisi (örn. bir endeks) için al-tut senaryosunun getiri/CAGR/
    drawdown/Sharpe'ını compute_metrics ile AYNI formüllerle hesaplar (trades=[]
    olduğundan win_rate/profit_factor/expectancy anlamsız/0 döner — yalnızca
    return/CAGR/DD/Sharpe alanları bu fonksiyon için geçerlidir). Bilgilendirici
    bir karşılaştırma aracıdır, kabul kriterlerinin bir parçası değildir."""
    if price_df.empty:
        return compute_metrics(pd.Series(dtype=float), [])
    equity_curve = price_df["close"] / price_df["close"].iloc[0] * initial_equity
    return compute_metrics(equity_curve, [])


def cash_only_metrics() -> Metrics:
    """Sadece-nakit senaryosu: getiri/CAGR/drawdown/Sharpe hepsi sıfır."""
    return Metrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0, 100.0)


def classify_regime(daily_df: pd.DataFrame, cfg) -> pd.Series:
    """bull: close > ema_slow VE ema_slow 20 bar öncesinden yüksek.
    bear: close < ema_slow VE ema_slow 20 bar öncesinden düşük. Aksi: sideways."""
    ema_slow_col = f"ema_{cfg.signal.ema_slow}"
    ema = daily_df[ema_slow_col]
    ema_20_ago = ema.shift(20)
    bull = (daily_df["close"] > ema) & (ema > ema_20_ago)
    bear = (daily_df["close"] < ema) & (ema < ema_20_ago)
    regime = pd.Series("sideways", index=daily_df.index)
    regime[bull.fillna(False)] = "bull"
    regime[bear.fillna(False)] = "bear"
    return regime


def regime_breakdown(trades: list[Trade], regimes_by_symbol: dict[str, pd.Series]) -> pd.DataFrame:
    """Her trade'in giriş tarihindeki rejime göre gruplandırılmış: trade sayısı, win rate, toplam R."""
    rows = []
    for t in trades:
        regime_series = regimes_by_symbol.get(t.symbol)
        regime = regime_series.get(t.entry_date, "unknown") if regime_series is not None else "unknown"
        rows.append({"regime": regime, "pnl": t.pnl, "r_multiple": t.r_multiple, "win": t.pnl > 0})

    if not rows:
        return pd.DataFrame(columns=["regime", "trade_count", "win_rate", "total_r"])

    df = pd.DataFrame(rows)
    grouped = df.groupby("regime").agg(
        trade_count=("pnl", "count"),
        win_rate=("win", "mean"),
        total_r=("r_multiple", "sum"),
    ).reset_index()
    return grouped
