# execution/broker_adapter.py
"""Çekirdeğin dış dünyayla tek temas noktası (CLAUDE.md Bölüm 4.3).

Implementasyonlar: PaperBroker (dahili simülatör, Faz 5), AlgoLabAdapter (F5-B).
Tüm metodlar senkron; hata durumunda BrokerError fırlatır (sessiz None dönmek yasak).

F5-A EK (additive, geriye uyumlu — CLAUDE.md 2.4): `submit_market_order`. regime_core
ailesi bracket kullanmaz (per-sembol stop/target yok; "stop" = rejim çıkışı); basket
enter/exit'i düz market emirleriyle yürütür. `submit_bracket_order` 10-gate için kalır.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from core.models import AccountState, Position, Side


class BrokerError(Exception):
    pass


class BrokerAdapter(ABC):
    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def get_account_state(self) -> AccountState: ...

    @abstractmethod
    def get_bars(self, symbol: str, timeframe: str, lookback: int) -> pd.DataFrame:
        """DataFrame index=UTC DatetimeIndex, kolonlar: open, high, low, close, volume.
        timeframe ∈ {"1d","4h","1h"}. Son bar KAPANMIŞ bar olmalı."""

    @abstractmethod
    def get_last_price(self, symbol: str) -> float: ...

    @abstractmethod
    def submit_market_order(self, symbol: str, side: Side, quantity: int) -> list[str]:
        """Düz piyasa emri (F5-A eki). regime_core basket enter/exit için. Dönen:
        broker order id listesi. Doldurulan fiyat get_last_price ± slippage."""

    @abstractmethod
    def submit_bracket_order(self, symbol: str, side: Side, quantity: int,
                             stop_price: float, target_price: float) -> list[str]:
        """Piyasa emri + broker tarafında bekleyen stop ve hedef (10-gate için)."""

    @abstractmethod
    def close_position(self, symbol: str) -> None: ...

    @abstractmethod
    def cancel_all_orders(self, symbol: str) -> None: ...

    @abstractmethod
    def get_positions(self) -> list[Position]: ...

    @abstractmethod
    def get_open_orders(self) -> list[dict]: ...

    @abstractmethod
    def is_market_open(self) -> bool: ...
