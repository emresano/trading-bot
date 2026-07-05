# backtest/montecarlo.py
from __future__ import annotations

import numpy as np

from backtest.engine import Trade


def monte_carlo_dd(trade_returns: np.ndarray, runs: int, seed: int) -> dict:
    """Bölüm 12.6 referans implementasyonu, aynen."""
    rng = np.random.default_rng(seed)
    dds = np.empty(runs)
    for i in range(runs):
        eq = (1 + rng.permutation(trade_returns)).cumprod()
        dds[i] = (eq / np.maximum.accumulate(eq) - 1.0).min()
    p5, p50, p95 = np.percentile(dds, [5, 50, 95])
    return {"dd_p5": p5, "dd_median": p50, "dd_p95": p95}


def trade_returns_from_trades(trades: list[Trade], risk_per_trade_pct: float) -> np.ndarray:
    """Her trade'in R-multiple'ını risk_per_trade_pct ile ölçekleyerek yaklaşık
    equity-üzerinden-getiri serisi üretir — pozisyon boyutlaması her trade'i
    ~risk_per_trade_pct kadar riske ettiği için r_multiple × risk_per_trade_pct,
    o trade'in equity'ye oranla getirisinin makul bir yaklaşıklamasıdır."""
    return np.array([t.r_multiple * risk_per_trade_pct for t in trades])


def run_monte_carlo(trades: list[Trade], cfg) -> dict:
    """dd_p95 (kötü senaryo), config'teki max_drawdown_breaker_pct'e yakın/aşkınsa
    breaker canlıda sık tetiklenecek demektir — rapora kırmızı bayrak (Bölüm 12.6)."""
    returns = trade_returns_from_trades(trades, cfg.risk.risk_per_trade_pct)
    if len(returns) == 0:
        return {"dd_p5": 0.0, "dd_median": 0.0, "dd_p95": 0.0, "trade_count": 0}
    result = monte_carlo_dd(returns, cfg.backtest.monte_carlo_runs, cfg.backtest.random_seed)
    result["trade_count"] = len(returns)
    return result
