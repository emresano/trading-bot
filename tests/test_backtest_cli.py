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


# --- Rapor damgaları (HARDENING.md A1: tekrarlanabilirlik) ---

def test_stamps_appear_in_report_when_provided(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    stamps = {"git_commit": "abc123", "config_hash": "deadbeef", "snapshot_manifest_hash": "cafef00d"}
    generate_report(["TEST"], cfg, lambda s: df, tmp_path, stamps=stamps)
    content = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "abc123" in content
    assert "deadbeef" in content
    assert "cafef00d" in content


def test_stamps_absent_by_default(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    generate_report(["TEST"], cfg, lambda s: df, tmp_path)
    content = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "Git commit" not in content


# --- Veri temizleme raporlaması (v7 harness düzeltme turu) ---

def test_ghost_bars_removed_reported_and_written_to_csv(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    ghost_log = [
        {"symbol": "EREGL", "date": pd.Timestamp("2024-04-08", tz="UTC"),
         "reason": "tek-sembolde-var + volume=0 + OHLC≈onceki_kapanis (hayalet bar)"},
    ]
    generate_report(["TEST"], cfg, lambda s: df, tmp_path, ghost_bars_removed=ghost_log)
    content = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "1 hayalet bar elendi" in content
    assert (tmp_path / "ghost_bars_removed.csv").exists()
    csv_content = (tmp_path / "ghost_bars_removed.csv").read_text(encoding="utf-8")
    assert "EREGL" in csv_content


def test_ghost_bars_removed_zero_reported_without_csv_file(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    generate_report(["TEST"], cfg, lambda s: df, tmp_path, ghost_bars_removed=[])
    content = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "0 hayalet bar elendi" in content
    assert not (tmp_path / "ghost_bars_removed.csv").exists()


def test_ghost_bars_removed_absent_by_default(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    generate_report(["TEST"], cfg, lambda s: df, tmp_path)
    content = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "hayalet bar" not in content


# --- Portföy ablasyon turu: disabled_gates/trace geçişi ---

def test_disabled_gates_and_trace_forwarded_to_main_run_backtest(tmp_path, monkeypatch):
    import backtest.cli as cli_mod
    calls = []
    original = cli_mod.run_backtest

    def _spy(*args, **kwargs):
        calls.append(kwargs)
        return original(*args, **kwargs)

    monkeypatch.setattr(cli_mod, "run_backtest", _spy)

    cfg = make_cfg()
    df = _flat_series()
    trace: list = []
    generate_report(["TEST"], cfg, lambda s: df, tmp_path, disabled_gates=["rsi"], trace=trace)

    assert len(calls) == 1
    assert calls[0]["disabled_gates"] == ["rsi"]
    assert calls[0]["trace"] is trace


def test_disabled_gates_and_trace_absent_by_default_do_not_change_report(tmp_path):
    cfg = make_cfg()
    df = _flat_series()
    out_with = generate_report(["TEST"], cfg, lambda s: df, tmp_path / "a")
    out_without = generate_report(["TEST"], cfg, lambda s: df, tmp_path / "b",
                                  disabled_gates=None, trace=None)
    assert out_with["metrics"].total_return == out_without["metrics"].total_return
    assert out_with["metrics"].trade_count == out_without["metrics"].trade_count


# --- Monte Carlo kırmızı bayrağı: worst-5% (dd_p5), dd_p95 DEĞİL (harness düzeltme turu) ---

def test_monte_carlo_red_flag_uses_worst_5_percent_not_best_case(tmp_path, monkeypatch):
    """dd_p95 (en iyi %5 senaryo) breaker eşiğinin altında kalsa bile, dd_p5
    (en kötü %5 senaryo) eşiği aşıyorsa kırmızı bayrak tetiklenmeli. Eski
    davranış (dd_p95 kontrolü) bu senaryoyu KAÇIRIRDI."""
    import backtest.cli as cli_mod

    cfg = make_cfg()
    cfg.risk.max_drawdown_breaker_pct = 0.10
    df = _flat_series()

    def fake_run_monte_carlo(trades, cfg):
        return {"dd_p5": -0.15, "dd_median": -0.08, "dd_p95": -0.02, "trade_count": 10}

    monkeypatch.setattr(cli_mod, "run_monte_carlo", fake_run_monte_carlo)

    out = generate_report(["TEST"], cfg, lambda s: df, tmp_path, do_monte_carlo=True)
    assert any("worst-5%" in rf for rf in out["red_flags"])


def test_monte_carlo_no_red_flag_when_worst_5_percent_within_threshold(tmp_path, monkeypatch):
    import backtest.cli as cli_mod

    cfg = make_cfg()
    cfg.risk.max_drawdown_breaker_pct = 0.10
    df = _flat_series()

    def fake_run_monte_carlo(trades, cfg):
        return {"dd_p5": -0.05, "dd_median": -0.03, "dd_p95": -0.01, "trade_count": 10}

    monkeypatch.setattr(cli_mod, "run_monte_carlo", fake_run_monte_carlo)

    out = generate_report(["TEST"], cfg, lambda s: df, tmp_path, do_monte_carlo=True)
    assert not any("worst-5%" in rf or "Monte Carlo" in rf for rf in out["red_flags"])
