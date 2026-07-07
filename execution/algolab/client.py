# execution/algolab/client.py
"""Throttle'lı AlgoLab HTTP istemcisi (CLAUDE.md Bölüm 11.3, Faz 5 F5A-8).

AlgoLab bilinen kısıtı: ~5 sn/istek. Tüm çağrılar tek RateLimitedClient'tan geçer:
Lock + son istek zamanı; gerekirse bekler. 429/limit hatasında üstel geri çekilme
(5→10→20 sn, 3 deneme), sonra BrokerError.

F5-A: `transport` ve `sleep_fn` enjekte edilebilir → ağsız/zaman-sıçramasız test.
CANLI ÇAĞRI YOK.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from execution.broker_adapter import BrokerError

BACKOFF_SEQUENCE = (5.0, 10.0, 20.0)


class AlgoLabRateLimit(Exception):
    """transport bunu fırlatırsa istemci üstel geri çekilir (429 karşılığı)."""


class RateLimitedClient:
    def __init__(self, transport: Callable[[str, dict, dict], dict],
                 throttle_sec: float = 5.1,
                 sleep_fn: Optional[Callable[[float], None]] = None,
                 monotonic_fn: Optional[Callable[[], float]] = None):
        self._transport = transport
        self.throttle_sec = throttle_sec
        self._sleep = sleep_fn or time.sleep
        self._now = monotonic_fn or time.monotonic
        self._lock = threading.Lock()
        self._last_request_at: Optional[float] = None
        self.slept_total = 0.0   # test/denetim

    def _throttle(self) -> None:
        if self._last_request_at is not None:
            elapsed = self._now() - self._last_request_at
            wait = self.throttle_sec - elapsed
            if wait > 0:
                self._sleep(wait)
                self.slept_total += wait
        self._last_request_at = self._now()

    def request(self, endpoint: str, payload: dict, headers: dict) -> dict:
        with self._lock:
            last_err: Optional[Exception] = None
            for attempt, backoff in enumerate((0.0,) + BACKOFF_SEQUENCE):
                if backoff > 0:
                    self._sleep(backoff)
                    self.slept_total += backoff
                self._throttle()
                try:
                    return self._transport(endpoint, payload, headers)
                except AlgoLabRateLimit as e:
                    last_err = e
                    continue
            raise BrokerError(f"AlgoLab rate-limit: {len(BACKOFF_SEQUENCE)} denemeden sonra "
                              f"başarısız ({endpoint}): {last_err}")
