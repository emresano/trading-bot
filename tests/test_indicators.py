from pathlib import Path

import pandas as pd
import pytest

from core.config import load_config
from indicators.engine import (
    add_atr,
    add_candle_patterns,
    build_features,
)

FIXTURES = Path(__file__).parent / "fixtures"
TOL = 1e-6

# thyao_daily_2022.csv son 5 barı için beklenen değerler — pandas-ta-classic 0.6.52
# ile bir kez üretilip buraya sabitlendi (Bölüm 7.4). Amaç: kütüphane sürüm
# değişikliğinde sessiz davranış kaymasını yakalamak.
EXPECTED_LAST_5 = {
    "2022-12-25": {
        "ema_50": 117.09614741544722, "ema_200": 75.36658071612116,
        "adx": 47.495417531354235, "rsi": 68.45977824650348,
        "macd": 7.8970711174303005, "macd_signal": 8.595857671498932, "macd_hist": -0.6987865540686311,
        "atr": 4.703319860842195, "atr_ma20": 4.924135104150546,
        "bb_low": 118.3544227820489, "bb_mid": 134.03339538574218, "bb_high": 149.71236798943545,
        "swing_high": False, "swing_low": False,
        "nearest_support": 137.54528690175397, "nearest_resistance": 143.21123058197554,
    },
    "2022-12-26": {
        "ema_50": 117.98618592921798, "ema_200": 76.00763095294187,
        "adx": 47.17025848023095, "rsi": 64.99787084563222,
        "macd": 7.515511476058606, "macd_signal": 8.379788432410868, "macd_hist": -0.8642769563522616,
        "atr": 4.618567652562229, "atr_ma20": 4.950256160717595,
        "bb_low": 121.69056567754497, "bb_mid": 135.21542510986328, "bb_high": 148.74028454218157,
        "swing_high": True, "swing_low": False,
        "nearest_support": 137.54528690175397, "nearest_resistance": 143.2112240829161,
    },
    "2022-12-27": {
        "ema_50": 118.72639356779338, "ema_200": 76.61314189582693,
        "adx": 45.128530928710056, "rsi": 59.851396658038055,
        "macd": 6.89713793251056, "macd_signal": 8.083258332430807, "macd_hist": -1.186120399920247,
        "atr": 4.756178611589483, "atr_ma20": 4.989513561980563,
        "bb_low": 125.47874966509112, "bb_mid": 136.19719429016112, "bb_high": 146.9156389152311,
        "swing_high": False, "swing_low": True,
        "nearest_support": 133.9308281486409, "nearest_resistance": 137.7406646710608,
    },
    "2022-12-28": {
        "ema_50": 119.52185343247551, "ema_200": 77.23401232589022,
        "adx": 43.23264105944066, "rsi": 62.21418569462332,
        "macd": 6.505498693520707, "macd_signal": 7.767706404648787, "macd_hist": -1.26220771112808,
        "atr": 4.744405325716154, "atr_ma20": 5.021082429041669,
        "bb_low": 128.6838829587199, "bb_mid": 137.07150573730468, "bb_high": 145.45912851588946,
        "swing_high": False, "swing_low": False,
        "nearest_support": 137.54528690175397, "nearest_resistance": 143.2112240829161,
    },
    "2022-12-29": {
        "ema_50": 120.23248564506532, "ema_200": 77.83509653014521,
        "adx": 41.87128413864629, "rsi": 59.80225071171732,
        "macd": 6.015422189591618, "macd_signal": 7.4172495616373535, "macd_hist": -1.4018273720457355,
        "atr": 4.747428267771632, "atr_ma20": 5.048303032395171,
        "bb_low": 131.2565598002169, "bb_mid": 137.68694229125975, "bb_high": 144.1173247823026,
        "swing_high": False, "swing_low": False,
        "nearest_support": 137.54528690175397, "nearest_resistance": 137.7406646710608,
    },
}


@pytest.fixture(scope="module")
def golden_features():
    cfg = load_config()
    df = pd.read_csv(FIXTURES / "thyao_daily_2022.csv", parse_dates=["ts"], index_col="ts")
    return build_features(df, cfg)


def test_golden_fixture_has_expected_shape(golden_features):
    assert len(golden_features) == 316


def test_golden_last_5_bars_match_reference(golden_features):
    tail = golden_features.tail(5)
    assert [ts.date().isoformat() for ts in tail.index] == list(EXPECTED_LAST_5.keys())
    for ts, row in tail.iterrows():
        date = ts.date().isoformat()
        expected = EXPECTED_LAST_5[date]
        for field, value in expected.items():
            actual = row[field]
            if isinstance(value, bool):
                assert bool(actual) == value, f"{date} {field}: beklenen {value}, alınan {actual}"
            else:
                assert actual == pytest.approx(value, abs=TOL), f"{date} {field}: beklenen {value}, alınan {actual}"


def test_rsi_bounded_0_100(golden_features):
    rsi = golden_features["rsi"].dropna()
    assert (rsi >= 0).all() and (rsi <= 100).all()


def test_atr_always_positive(golden_features):
    atr = golden_features["atr"].dropna()
    assert (atr > 0).all()


def test_bbands_ordering(golden_features):
    valid = golden_features.dropna(subset=["bb_low", "bb_mid", "bb_high"])
    assert (valid["bb_low"] <= valid["bb_mid"]).all()
    assert (valid["bb_mid"] <= valid["bb_high"]).all()


def test_swing_last_n_bars_never_true(golden_features):
    n = 2  # config.yaml: signal.swing_fractal_n
    tail = golden_features.iloc[-n:]
    assert not tail["swing_high"].any()
    assert not tail["swing_low"].any()


def test_build_features_does_not_mutate_input():
    cfg = load_config()
    df = pd.read_csv(FIXTURES / "thyao_daily_2022.csv", parse_dates=["ts"], index_col="ts")
    original_cols = list(df.columns)
    build_features(df, cfg)
    assert list(df.columns) == original_cols


def _atr_frame():
    idx = pd.date_range("2024-01-01", periods=30, freq="1D", tz="UTC")
    close = pd.Series(range(100, 130), index=idx, dtype=float)
    high = close + 1.0
    low = close - 1.0
    open_ = close.shift(1).fillna(close.iloc[0])
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close,
                         "volume": 1000.0}, index=idx)


def test_add_atr_column_present_and_positive():
    df = add_atr(_atr_frame(), period=14)
    assert "atr" in df.columns and "atr_ma20" in df.columns
    assert (df["atr"].dropna() > 0).all()


# --- Mum formasyonu testleri: elle kurgulanmış 5-6 barlık mini senaryolar ---

def _candles(rows):
    idx = pd.date_range("2024-01-01", periods=len(rows), freq="1D", tz="UTC")
    return pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close"]).assign(volume=1000.0)


def test_bullish_engulfing_detected():
    rows = [
        [100, 101, 95, 96],   # kırmızı bar
        [95, 105, 94, 103],   # yeşil, öncekinin gövdesini kapsıyor
    ]
    df = add_candle_patterns(_candles(rows))
    assert df["pat_engulf"].iloc[-1] == True  # noqa: E712


def test_bullish_engulfing_not_detected_when_not_covering_body():
    rows = [
        [100, 101, 95, 96],
        [97, 105, 96, 99],  # gövdeyi tam kapsamıyor (open > prev_close olabilir ama close < prev_open)
    ]
    df = add_candle_patterns(_candles(rows))
    assert df["pat_engulf"].iloc[-1] == False  # noqa: E712


def test_bullish_pin_bar_detected():
    rows = [
        [100, 101, 99, 100.5],
        [100, 101, 90, 100.8],  # uzun alt fitil, küçük gövde, kapanış üstte
    ]
    df = add_candle_patterns(_candles(rows))
    assert df["pat_pin"].iloc[-1] == True  # noqa: E712


def test_bullish_pin_bar_not_detected_for_normal_candle():
    rows = [
        [100, 101, 99, 100.5],
        [100, 103, 98, 102],  # normal gövde, belirgin fitil yok
    ]
    df = add_candle_patterns(_candles(rows))
    assert df["pat_pin"].iloc[-1] == False  # noqa: E712


def test_inside_bar_breakout_detected():
    rows = [
        [100, 110, 90, 105],   # mother bar (geniş range)
        [104, 106, 96, 102],   # inside bar (mother'ın içinde)
        [102, 112, 101, 109],  # breakout: close > inside barın high'ı (106)
    ]
    df = add_candle_patterns(_candles(rows))
    assert df["pat_inside_break"].iloc[-1] == True  # noqa: E712


def test_inside_bar_breakout_not_detected_without_breakout():
    rows = [
        [100, 110, 90, 105],
        [104, 106, 96, 102],
        [102, 105, 101, 103],  # kapanış inside barın high'ının altında kalıyor
    ]
    df = add_candle_patterns(_candles(rows))
    assert df["pat_inside_break"].iloc[-1] == False  # noqa: E712
