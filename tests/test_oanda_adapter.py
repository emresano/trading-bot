import pandas as pd
import pytest

from data.adapters.oanda import OandaAdapter, OandaAuthError, _parse_candles_response


def _fixture_payload() -> dict:
    """OANDA v20 dokümantasyonundaki örnek yanıt formatına dayanan sabit fixture
    (ağsız — gerçek bir API çağrısına dayanmaz, yalnızca ayrıştırma mantığını sınar)."""
    return {
        "candles": [
            {"complete": True, "volume": 12345, "time": "2024-01-01T22:00:00.000000000Z",
             "mid": {"o": "1.1000", "h": "1.1050", "l": "1.0950", "c": "1.1020"}},
            {"complete": True, "volume": 13456, "time": "2024-01-02T22:00:00.000000000Z",
             "mid": {"o": "1.1020", "h": "1.1080", "l": "1.0990", "c": "1.1040"}},
            {"complete": False, "volume": 100, "time": "2024-01-03T22:00:00.000000000Z",
             "mid": {"o": "1.1040", "h": "1.1041", "l": "1.1039", "c": "1.1040"}},
        ]
    }


def test_parse_candles_response_excludes_incomplete_candle():
    df = _parse_candles_response(_fixture_payload())
    assert len(df) == 2  # 3. mum complete=False, dışlanmalı
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]
    assert df["close"].iloc[0] == pytest.approx(1.1020)


def test_parse_candles_response_empty_when_no_complete_candles():
    payload = {"candles": [{"complete": False, "volume": 1, "time": "2024-01-01T00:00:00Z",
                            "mid": {"o": "1", "h": "1", "l": "1", "c": "1"}}]}
    df = _parse_candles_response(payload)
    assert df.empty


def test_parse_candles_response_sorted_and_tz_aware():
    df = _parse_candles_response(_fixture_payload())
    assert df.index.tz is not None
    assert df.index.is_monotonic_increasing


def test_headers_raises_without_token():
    adapter = OandaAdapter(api_token=None)
    with pytest.raises(OandaAuthError):
        adapter._headers()


def test_headers_ok_with_token():
    adapter = OandaAdapter(api_token="fake-token-for-test")
    headers = adapter._headers()
    assert headers["Authorization"] == "Bearer fake-token-for-test"


def test_fetch_history_uses_mocked_requests_and_returns_canonical_schema(monkeypatch):
    calls = {}

    class _FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return _fixture_payload()

    def _fake_get(url, headers, params, timeout):
        calls["url"] = url
        calls["params"] = params
        return _FakeResponse()

    monkeypatch.setattr("data.adapters.oanda.requests.get", _fake_get)

    adapter = OandaAdapter(api_token="fake-token")
    df, meta = adapter.fetch_history("EUR_USD", "1d", start=pd.Timestamp("2024-01-01").date())

    assert len(df) == 2
    assert "EUR_USD" in calls["url"]
    assert calls["params"]["granularity"] == "D"
    assert meta.adapter_id == "oanda"
    assert meta.volume_kind == "tick"
