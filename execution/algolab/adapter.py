# execution/algolab/adapter.py
"""AlgoLab BrokerAdapter implementasyonu (CLAUDE.md Bölüm 11.4, Faz 5 F5A-8).

**KAPATILMIŞ-BROKER REFERANSI (F5-B1, 2026-07-07):** AlgoLab 2025-12-31'de kapatıldı;
canlı entegrasyon İPTAL. Bu modül CANLI KULLANILMAZ — BrokerAdapter implementasyon
deseni için referans. F5-B2 yerine ManualExecutionAdapter tasarlanacak.


**DOĞRULANMAMIŞ — REFERANS (oanda.py emsali):** endpoint adları ve yanıt ALAN
ADLARI AlgoLab'ın topluluk-bilinen davranışına dayanır; F5-B'nin İLK işi resmî
dokümanla karşılaştırıp bu dosyaya düzeltme notu eklemektir (CLAUDE.md 11 + 16 #1).
Parse fonksiyonları (`_parse_candles`, `_parse_positions`) ağsız fixture'la test
edilir — bu formatın DOĞRU YORUMLANDIĞINI kanıtlar, API'nin onu GERÇEKTEN
döndürdüğünü DEĞİL.

CANLI ÇAĞRI YOK (F5-A): tüm çağrılar RateLimitedClient.transport üzerinden; F5-A
testleri fake transport enjekte eder. Bracket AlgoLab'da native değilse üç ayrı emir
(piyasa + stop + limit) ile taklit edilir — ÇAĞIRAN bilmez (regime_core zaten market
kullanır; bracket 10-gate içindir).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from core.models import AccountState, Position, Side
from execution.broker_adapter import BrokerAdapter, BrokerError
from execution.algolab.auth import AlgoLabAuth
from execution.algolab.client import RateLimitedClient

# BrokerAdapter.timeframe → AlgoLab GetCandleData period (dakika; günlük=1440). DOĞRULANACAK.
_PERIOD_MAP = {"1d": "1440", "1h": "60", "4h": "240"}


def _parse_candles(payload: dict) -> pd.DataFrame:
    """GetCandleData yanıtı → kanonik df (UTC index, ohlcv). VARSAYILAN format
    (DOĞRULANACAK): {"content": [{"Date": "...", "Open":..,"High":..,"Low":..,
    "Close":..,"Volume":..}, ...]}."""
    rows, index = [], []
    for c in payload.get("content", []) or []:
        index.append(pd.Timestamp(c["Date"]))
        rows.append({"open": float(c["Open"]), "high": float(c["High"]),
                     "low": float(c["Low"]), "close": float(c["Close"]),
                     "volume": float(c.get("Volume", 0))})
    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(rows, index=pd.DatetimeIndex(index, name="ts"))
    df.index = df.index.tz_localize("UTC") if df.index.tz is None else df.index.tz_convert("UTC")
    return df.sort_index()


def _parse_positions(payload: dict) -> list[Position]:
    """InstantPosition yanıtı → Position listesi. VARSAYILAN format (DOĞRULANACAK):
    {"content": [{"code": "THYAO", "totalstock": "100", "cost": "95.5"}, ...]}."""
    out = []
    for p in payload.get("content", []) or []:
        qty = int(float(p.get("totalstock", 0)))
        if qty == 0:
            continue
        out.append(Position(symbol=p["code"], quantity=qty, avg_price=float(p.get("cost", 0)),
                            stop_price=0.0, target_price=0.0,
                            opened_at=pd.Timestamp.now(tz="UTC").to_pydatetime()))
    return out


class AlgoLabAdapter(BrokerAdapter):
    def __init__(self, auth: AlgoLabAuth, client: RateLimitedClient):
        self.auth = auth
        self.client = client

    def _call(self, endpoint: str, payload: dict, authorized: bool = True) -> dict:
        headers = self.auth._headers(endpoint, payload, authorized)
        data = self.client.request(endpoint, payload, headers)
        if not data.get("success", False):
            raise BrokerError(f"AlgoLab {endpoint}: {data.get('message')}")
        return data

    def connect(self) -> None:
        if not self.auth.hash and not self.auth.load_session():
            raise BrokerError("AlgoLab: session yok — önce `python -m execution.algolab.auth login`")

    def get_bars(self, symbol: str, timeframe: str, lookback: int) -> pd.DataFrame:
        period = _PERIOD_MAP[timeframe]
        data = self._call("/api/GetCandleData", {"symbol": symbol, "period": period})
        return _parse_candles(data).tail(lookback)

    def get_last_price(self, symbol: str) -> float:
        data = self._call("/api/GetEquityInfo", {"symbol": symbol})
        return float(data["content"]["last"])   # DOĞRULANACAK alan

    def submit_market_order(self, symbol: str, side: Side, quantity: int) -> list[str]:
        payload = {"symbol": symbol, "direction": "BUY" if side == Side.BUY else "SELL",
                   "pricetype": "piyasa", "lot": str(quantity), "sms": False, "email": False}
        data = self._call("/api/SendOrder", payload)
        return [str(data["content"].get("orderId", data.get("message", "")))]

    def submit_bracket_order(self, symbol: str, side: Side, quantity: int,
                             stop_price: float, target_price: float) -> list[str]:
        # AlgoLab native bracket yoksa: piyasa + stop + limit (üç emir). DOĞRULANACAK.
        raise BrokerError("AlgoLab bracket F5-B'de doğrulanacak (regime_core market kullanır)")

    def close_position(self, symbol: str) -> None:
        positions = {p.symbol: p.quantity for p in self.get_positions()}
        if symbol in positions:
            self.submit_market_order(symbol, Side.SELL, positions[symbol])

    def cancel_all_orders(self, symbol: str) -> None:
        for o in self.get_open_orders():
            if o.get("symbol") == symbol:
                self._call("/api/DeleteOrder", {"id": o.get("id")})

    def get_positions(self) -> list[Position]:
        return _parse_positions(self._call("/api/InstantPosition", {}))

    def get_account_state(self) -> AccountState:
        raise BrokerError("AlgoLab get_account_state F5-B'de (InstantPosition+CashFlow alanları doğrulanacak)")

    def get_open_orders(self) -> list[dict]:
        return self._call("/api/TodaysTransaction", {}).get("content", []) or []

    def is_market_open(self) -> bool:
        from core.clock import is_bist_session, now_utc
        return is_bist_session(now_utc())
