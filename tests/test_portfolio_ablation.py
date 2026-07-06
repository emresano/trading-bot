import pandas as pd
import pytest

from tools.portfolio_ablation import (
    VARIANTS,
    compute_gap_proximity,
    compute_time_in_market_and_capital_utilization,
    convert_equity_to_usd,
)


def test_variants_cover_the_five_required_combinations():
    assert set(VARIANTS.keys()) == {"baseline", "no_trend", "no_regime", "no_rsi", "no_trend_regime_rsi"}
    assert VARIANTS["baseline"] == []
    assert VARIANTS["no_trend"] == ["trend"]
    assert VARIANTS["no_regime"] == ["regime"]
    assert VARIANTS["no_rsi"] == ["rsi"]
    assert set(VARIANTS["no_trend_regime_rsi"]) == {"trend", "regime", "rsi"}


def test_time_in_market_and_utilization_empty_trace():
    result = compute_time_in_market_and_capital_utilization([])
    assert result == {"time_in_market_pct": 0.0, "avg_capital_utilization_pct": 0.0}


def test_time_in_market_and_utilization_computed_correctly():
    trace = [
        {"equity": 100_000.0, "positions": {}},
        {"equity": 100_000.0, "positions": {"AAA": {"notional": 25_000.0}}},
        {"equity": 100_000.0, "positions": {"AAA": {"notional": 25_000.0}, "BBB": {"notional": 25_000.0}}},
        {"equity": 100_000.0, "positions": {}},
    ]
    result = compute_time_in_market_and_capital_utilization(trace)
    # 2/4 gün pozisyonlu
    assert result["time_in_market_pct"] == pytest.approx(50.0)
    # utilization: [0, 0.25, 0.50, 0] ortalaması = 0.1875 -> %18.75
    assert result["avg_capital_utilization_pct"] == pytest.approx(18.75)


def test_time_in_market_ignores_none_notional():
    trace = [{"equity": 100_000.0, "positions": {"AAA": {"notional": None}}}]
    result = compute_time_in_market_and_capital_utilization(trace)
    assert result["time_in_market_pct"] == pytest.approx(100.0)  # positions dict boş değil
    assert result["avg_capital_utilization_pct"] == pytest.approx(0.0)  # None katkı vermiyor


def test_convert_equity_to_usd_divides_by_rate():
    idx = pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC")
    equity = pd.Series([100_000.0, 110_000.0, 105_000.0], index=idx)
    usdtry = pd.Series([30.0, 30.0, 30.0], index=idx)
    usd = convert_equity_to_usd(equity, usdtry)
    assert usd.iloc[0] == pytest.approx(100_000.0 / 30.0)
    assert usd.iloc[1] == pytest.approx(110_000.0 / 30.0)


def test_convert_equity_to_usd_forward_fills_missing_fx_dates():
    idx = pd.date_range("2024-01-01", periods=3, freq="1D", tz="UTC")
    equity = pd.Series([100_000.0, 110_000.0, 105_000.0], index=idx)
    # USDTRY yalnızca ilk günde veri veriyor -> ffill ile diğer günlere taşınmalı
    usdtry = pd.Series([30.0], index=idx[:1])
    usd = convert_equity_to_usd(equity, usdtry)
    assert usd.iloc[1] == pytest.approx(110_000.0 / 30.0)
    assert usd.iloc[2] == pytest.approx(105_000.0 / 30.0)


def test_convert_equity_to_usd_empty_curve_returns_empty():
    result = convert_equity_to_usd(pd.Series(dtype=float), pd.Series(dtype=float))
    assert result.empty


def test_compute_gap_proximity_empty_trades():
    result = compute_gap_proximity(pd.DataFrame(columns=["symbol", "entry_date", "exit_date"]), [], {})
    assert result == {"total_trades": 0, "trades_near_suspicious_day": 0, "pct": 0.0}


def test_compute_gap_proximity_flags_trade_within_window():
    idx = pd.date_range("2024-01-01", periods=20, freq="1D", tz="UTC")
    df = pd.DataFrame({"close": range(20)}, index=idx)
    cleaned = {"AAA": df}
    suspicious_days = [("AAA", idx[10])]
    trades_df = pd.DataFrame([
        {"symbol": "AAA", "entry_date": idx[8], "exit_date": idx[9]},  # 2 bar uzakta -> yakın
        {"symbol": "AAA", "entry_date": idx[0], "exit_date": idx[1]},  # çok uzak
    ])
    result = compute_gap_proximity(trades_df, suspicious_days, cleaned, window=5)
    assert result["total_trades"] == 2
    assert result["trades_near_suspicious_day"] == 1
    assert result["pct"] == pytest.approx(50.0)


def test_compute_gap_proximity_ignores_other_symbols():
    idx = pd.date_range("2024-01-01", periods=20, freq="1D", tz="UTC")
    df = pd.DataFrame({"close": range(20)}, index=idx)
    cleaned = {"AAA": df, "BBB": df}
    suspicious_days = [("AAA", idx[10])]
    trades_df = pd.DataFrame([
        {"symbol": "BBB", "entry_date": idx[10], "exit_date": idx[10]},  # aynı tarih ama farklı sembol
    ])
    result = compute_gap_proximity(trades_df, suspicious_days, cleaned, window=5)
    assert result["trades_near_suspicious_day"] == 0
