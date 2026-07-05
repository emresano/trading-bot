import pandas as pd
import pytest

from tools.data_audit import (
    audit_symbol,
    check_jumps,
    check_missing_bars,
    _tolerance_boundary_proof,
)


def _clean_df(n=30, start="2024-01-01"):
    idx = pd.date_range(start, periods=n, freq="1D", tz="UTC")
    close = [100.0 + i * 0.1 for i in range(n)]
    return pd.DataFrame({
        "open": close, "high": [c + 0.5 for c in close], "low": [c - 0.5 for c in close],
        "close": close, "volume": [1000.0] * n,
    }, index=idx)


def test_check_missing_bars_flags_day_missing_in_minority_symbol():
    # 5 sembolden 4'ü o günü içeriyor (%80 >= %70 eşiği) -> "beklenen gün" sayılır
    base = _clean_df(n=10)
    data = {
        "A": base, "B": base, "C": base, "D": base,
        "E": base.drop(base.index[5]),
    }
    missing = check_missing_bars(data)
    assert len(missing["E"]) == 1
    assert missing["A"] == []


def test_check_missing_bars_no_flag_when_all_symbols_agree():
    df_a = _clean_df(n=10)
    df_b = _clean_df(n=10)
    missing = check_missing_bars({"A": df_a, "B": df_b})
    assert missing["A"] == []
    assert missing["B"] == []


def test_check_jumps_detects_large_move():
    df = _clean_df(n=30)
    df.loc[df.index[15], "close"] = df.loc[df.index[14], "close"] * 1.30  # %30 sıçrama
    jumps = check_jumps(df)
    assert len(jumps) == 1
    assert jumps.iloc[0]["return"] == pytest.approx(0.30, abs=1e-6)


def test_check_jumps_empty_when_no_large_moves():
    df = _clean_df(n=30)
    jumps = check_jumps(df)
    assert jumps.empty


def test_check_jumps_classifies_volume_backed_move_as_real():
    df = _clean_df(n=40)  # rolling(20) için sıçrama barından önce yeterli geçmiş
    df.loc[df.index[30], "close"] = df.loc[df.index[29], "close"] * 1.30
    df.loc[df.index[30], "volume"] = 5000.0  # ort. hacmin çok üstü
    jumps = check_jumps(df)
    assert "gerçek hareket" in jumps.iloc[0]["classification"]


def test_audit_symbol_pass_for_clean_data():
    df = _clean_df(n=30)
    result = audit_symbol("TEST", df, missing_days=[])
    assert result["status"] == "PASS"
    assert result["quality_passed"]
    assert result["zero_or_negative_price_count"] == 0
    assert result["duplicate_date_count"] == 0


def test_audit_symbol_warn_on_jump_but_quality_ok():
    df = _clean_df(n=30)
    df.loc[df.index[15], "close"] = df.loc[df.index[14], "close"] * 1.30
    df.loc[df.index[15], "high"] = df.loc[df.index[15], "close"] + 0.5
    df.loc[df.index[15], "low"] = df.loc[df.index[15], "close"] - 0.5
    df.loc[df.index[15], "open"] = df.loc[df.index[15], "close"]
    result = audit_symbol("TEST", df, missing_days=[])
    assert result["status"] == "WARN"


def test_audit_symbol_fail_on_negative_price():
    df = _clean_df(n=30)
    df.loc[df.index[10], ["open", "high", "low", "close"]] = -5.0
    result = audit_symbol("TEST", df, missing_days=[])
    assert result["status"] == "FAIL"
    assert result["zero_or_negative_price_count"] > 0


def test_audit_symbol_warn_on_missing_days():
    df = _clean_df(n=30)
    result = audit_symbol("TEST", df, missing_days=[df.index[0]])
    assert result["status"] == "WARN"


# --- OHLC tolerans sınır kanıtı ---

def test_tolerance_boundary_proof_epsilon_and_small_pass_large_fails():
    lines = _tolerance_boundary_proof()
    assert any("epsilon" in ln and "PASS" in ln for ln in lines)
    assert any("%0.3" in ln and "PASS" in ln for ln in lines)
    assert any("%5" in ln and "FAIL" in ln for ln in lines)
