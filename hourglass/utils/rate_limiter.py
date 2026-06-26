from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable


class RateLimiter:
    """Async token bucket. Holding the lock across the wait gives FIFO fairness."""

    def __init__(
        self,
        rate_per_min: float,
        burst: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.rate_per_sec = max(float(rate_per_min), 1.0) / 60.0
        self.capacity = float(max(int(burst), 1))
        self._tokens = self.capacity
        self._clock = clock
        self._sleep = sleep
        self._updated = clock()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._updated
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate_per_sec)
            self._updated = now

    async def acquire(self) -> None:
        async with self._lock:
            self._refill()
            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / self.rate_per_sec
                await self._sleep(wait)
                self._refill()
            self._tokens -= 1.0
