from types import SimpleNamespace

import pandas as pd
import pytest

from data.adapters.yf_us import YfUsAdapter


def _fixture_raw_df() -> pd.DataFrame:
    """yfinance'in America/New_York tz-aware döndürdüğü ham format (Capitalized
    kolonlar + Dividends/Stock Splits) — gerçek bir download'a dayanmadan."""
    idx = pd.to_datetime(
        ["2024-01-02 00:00:00-05:00", "2024-01-03 00:00:00-05:00", "2024-01-04 00:00:00-05:00"]
    )
    return pd.DataFrame({
        "Open": [100.0, 101.0, 102.0], "High": [101.0, 102.0, 103.0],
        "Low": [99.0, 100.0, 101.0], "Close": [100.5, 101.5, 102.5],
        "Volume": [1_000_000, 1_100_000, 1_200_000],
        "Dividends": [0.0, 0.0, 0.0], "Stock Splits": [0.0, 0.0, 0.0],
    }, index=idx)


class _FakeTicker:
    def __init__(self, symbol, raw_df):
        self.symbol = symbol
        self._raw_df = raw_df
        self.history_calls = []

    def history(self, **kwargs):
        self.history_calls.append(kwargs)
        return self._raw_df


def test_fetch_history_returns_canonical_schema(monkeypatch):
    fixture = _fixture_raw_df()
    fake_ticker_holder = {}

    def _fake_ticker_factory(symbol):
        t = _FakeTicker(symbol, fixture)
        fake_ticker_holder["ticker"] = t
        return t

    monkeypatch.setattr("data.adapters.yf_us.yf.Ticker", _fake_ticker_factory)

    adapter = YfUsAdapter()
    df, meta = adapter.fetch_history("AAPL", "1d", start=pd.Timestamp("2024-01-01").date())

    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df.index.tz is not None
    # New York negatif ofset -> takvim günü kaymamalı
    assert list(df.index.strftime("%Y-%m-%d")) == ["2024-01-02", "2024-01-03", "2024-01-04"]
    assert meta.adapter_id == "yf_us"
    assert meta.source == "yfinance"
    assert "auto_adjust=True" in meta.correction_policy
    assert meta.volume_kind == "shares"

    call = fake_ticker_holder["ticker"].history_calls[0]
    assert call["auto_adjust"] is True
    assert call["interval"] == "1d"


def test_fetch_history_empty_result(monkeypatch):
    monkeypatch.setattr("data.adapters.yf_us.yf.Ticker",
                        lambda symbol: _FakeTicker(symbol, pd.DataFrame()))
    adapter = YfUsAdapter()
    df, meta = adapter.fetch_history("NOSUCHTICKER", "1d", start=pd.Timestamp("2024-01-01").date())
    assert df.empty
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


def test_fetch_latest_returns_tail(monkeypatch):
    fixture = _fixture_raw_df()
    monkeypatch.setattr("data.adapters.yf_us.yf.Ticker",
                        lambda symbol: _FakeTicker(symbol, fixture))
    adapter = YfUsAdapter()
    df = adapter.fetch_latest("AAPL", "1d", lookback=2)
    assert len(df) == 2
    assert list(df.index.strftime("%Y-%m-%d")) == ["2024-01-03", "2024-01-04"]
