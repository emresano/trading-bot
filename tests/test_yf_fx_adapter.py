import pandas as pd

from data.adapters.yf_fx import FX_YF_SYMBOL_MAP, YfFxAdapter


def _fixture_raw_df() -> pd.DataFrame:
    """yfinance'in FX için Europe/London tz-aware döndürdüğü ham format."""
    idx = pd.to_datetime(
        ["2024-01-01 00:00:00+00:00", "2024-01-02 00:00:00+00:00", "2024-01-03 00:00:00+00:00"], utc=True
    )
    return pd.DataFrame({
        "Open": [1.10, 1.101, 1.102], "High": [1.105, 1.106, 1.107],
        "Low": [1.095, 1.096, 1.097], "Close": [1.102, 1.103, 1.104],
        "Volume": [0, 0, 0],
        "Dividends": [0.0, 0.0, 0.0], "Stock Splits": [0.0, 0.0, 0.0],
    }, index=idx)


class _FakeTicker:
    def __init__(self, symbol, raw_df):
        self.symbol = symbol
        self._raw_df = raw_df

    def history(self, **kwargs):
        return self._raw_df


def test_symbol_map_covers_the_three_expansion_instruments():
    assert set(FX_YF_SYMBOL_MAP.keys()) == {"EUR_USD", "GBP_USD", "USD_JPY"}
    assert FX_YF_SYMBOL_MAP["EUR_USD"] == "EURUSD=X"


def test_fetch_history_maps_symbol_and_returns_canonical_schema(monkeypatch):
    fixture = _fixture_raw_df()
    captured = {}

    def _fake_ticker_factory(symbol):
        captured["symbol"] = symbol
        return _FakeTicker(symbol, fixture)

    monkeypatch.setattr("data.adapters.yf_fx.yf.Ticker", _fake_ticker_factory)

    adapter = YfFxAdapter()
    df, meta = adapter.fetch_history("EUR_USD", "1d", start=pd.Timestamp("2024-01-01").date())

    assert captured["symbol"] == "EURUSD=X"
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert meta.adapter_id == "yf_fx"
    assert meta.volume_kind == "none"
    assert meta.source == "yfinance"
    assert meta.download_params["yf_symbol"] == "EURUSD=X"


def test_fetch_history_empty_result(monkeypatch):
    monkeypatch.setattr("data.adapters.yf_fx.yf.Ticker",
                        lambda symbol: _FakeTicker(symbol, pd.DataFrame()))
    adapter = YfFxAdapter()
    df, meta = adapter.fetch_history("EUR_USD", "1d", start=pd.Timestamp("2024-01-01").date())
    assert df.empty


def test_fetch_latest_returns_tail(monkeypatch):
    fixture = _fixture_raw_df()
    monkeypatch.setattr("data.adapters.yf_fx.yf.Ticker",
                        lambda symbol: _FakeTicker(symbol, fixture))
    adapter = YfFxAdapter()
    df = adapter.fetch_latest("GBP_USD", "1d", lookback=2)
    assert len(df) == 2
