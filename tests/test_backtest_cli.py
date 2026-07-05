from types import SimpleNamespace

import numpy as np
import pandas as pd

from backtest.cli import generate_report


def make_cfg():
    signal = SimpleNamespace(
        ema_fast=5, ema_slow=10, adx_period=5, adx_min=20,
        rsi_period=7, rsi_entry_low=40, rsi_entry_high=55,
        macd=(3, 6, 3), atr_period=5, atr_stop_mult=1.5, atr_anomaly_mult=2.0,
        bb_period=7, bb_std=2.0, swing_lookback=10, swing_fractal_n=1,
        volume_confirm_mult=1.5, min_history_bars=15,
    )
    risk = SimpleNamespace(
        risk_per_trade_pct=0.0075, daily_loss_limit_pct=0.5, weekly_loss_limit_pct=0.5,
        max_open_positions=2, max_position_notional_pct=0.25, max_drawdown_breaker_pct=0.10,
        min_rr=1.8, correlation_lookback_days=90, correlation_max=0.85, news_blackout=False,
    )
    costs = SimpleNamespace(commission_bps=10, slippage_bps=5)
    backtest = SimpleNamespace(
        initial_equity=100_000.0, monte_carlo_runs=200, random_seed=42,
        walk_forward=SimpleNamespace(train_months=2, test_months=1, step_months=1),
    )
    safety = SimpleNamespace(kill_switch_file="runtime/__nonexistent_kill_switch_for_tests__")
    return SimpleNamespace(signal=signal, risk=risk, costs=costs, backtest=backtest, safety=safety)


def _flat_series(n=500, start="2020-01-01"):
    idx = pd.date_range(start, periods=n, freq="1D", tz="UTC")
    close = np.full(n, 100.0)
    return pd.DataFrame({"open": close, "high": close + 0.1, "low": close - 0.1,
                        "close": close, "volume": np.full(n, 1000.0)}, index=idx)


def test_generate_report_writes_report_and_trades_csv(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    out = generate_report(["TEST"], cfg, lambda s: df, tmp_path)
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "trades.csv").exists()
    content = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Backtest Raporu" in content
    assert "Kırmızı Bayraklar" in content


def test_report_flags_low_trade_count(tmp_path):
    cfg = make_cfg()
    df = _flat_series()  # düz seri -> muhtemelen 0 trade
    out = generate_report(["TEST"], cfg, lambda s: df, tmp_path)
    assert out["metrics"].trade_count < 30
    assert any("Trade sayısı" in rf for rf in out["red_flags"])


def test_sweep_writes_27_row_csv(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    generate_report(["TEST"], cfg, lambda s: df, tmp_path, do_sweep=True)
    sweep_path = tmp_path / "sweep_results.csv"
    assert sweep_path.exists()
    sweep_df = pd.read_csv(sweep_path)
    assert len(sweep_df) == 27


def test_walk_forward_and_monte_carlo_and_regime_split_do_not_crash(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    out = generate_report(
        ["TEST"], cfg, lambda s: df, tmp_path,
        do_walk_forward=True, do_monte_carlo=True, do_regime_split=True,
    )
    content = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Walk-Forward" in content
    assert "Monte Carlo" in content
    assert "Rejim Kırılımı" in content


def test_report_is_deterministic_across_runs(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    generate_report(["TEST"], cfg, lambda s: df, out_a, do_walk_forward=True, do_monte_carlo=True, do_sweep=True)
    generate_report(["TEST"], cfg, lambda s: df, out_b, do_walk_forward=True, do_monte_carlo=True, do_sweep=True)
    assert (out_a / "report.md").read_text() == (out_b / "report.md").read_text()
    assert (out_a / "trades.csv").read_text() == (out_b / "trades.csv").read_text()
    assert (out_a / "sweep_results.csv").read_text() == (out_b / "sweep_results.csv").read_text()


# --- Benchmark kıyası (bilgilendirici, kabul kriterine dahil değil) ---

def test_benchmark_section_appears_with_comparison_table(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    bench_df = _flat_series(n=500)
    bench_df["close"] = bench_df["close"] * 1.1  # endeks farklı bir getiri göstersin

    out = generate_report(
        ["TEST"], cfg, lambda s: df, tmp_path,
        do_benchmark=True, benchmark_loader=lambda: bench_df,
    )
    content = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Benchmark Kıyası" in content
    assert "Endeks Al-Tut" in content
    assert "Sadece Nakit" in content
    assert out["benchmark_metrics"] is not None


def test_benchmark_section_absent_when_not_requested(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    out = generate_report(["TEST"], cfg, lambda s: df, tmp_path)
    content = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Benchmark Kıyası" not in content
    assert out["benchmark_metrics"] is None
