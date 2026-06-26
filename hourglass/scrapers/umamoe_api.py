from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

BASE_URL = "https://uma.moe/api/v4/circles"
TIMEOUT_SECONDS = 30


class StaleDataError(Exception):
    """Raised when fetched data is not fresh and the club should be re-queued later."""


class UmamoeClient:
    def __init__(
        self,
        session,
        rate_limiter,
        *,
        api_key: str | None = None,
        max_retries: int = 3,
        base_delay: float = 10.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._session = session
        self._limiter = rate_limiter
        self._api_key = api_key
        self._max_retries = max(int(max_retries), 1)
        self._base_delay = float(base_delay)
        self._sleep = sleep

    def _headers(self) -> dict:
        headers = {"Accept-Encoding": "gzip, deflate"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    async def fetch_circle(self, circle_id, year: int, month: int) -> dict | None:
        params = {"circle_id": circle_id, "year": year, "month": month}
        for attempt in range(self._max_retries):
            await self._limiter.acquire()
            try:
                async with self._session.get(
                    BASE_URL,
                    params=params,
                    headers=self._headers(),
                    timeout=TIMEOUT_SECONDS,
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    logger.warning(
                        "uma.moe non-200 for circle %s: %s (attempt %d)",
                        circle_id,
                        resp.status,
                        attempt + 1,
                    )
            except Exception as exc:  # network/timeout
                logger.warning(
                    "uma.moe request error for circle %s: %r (attempt %d)",
                    circle_id,
                    exc,
                    attempt + 1,
                )

            if attempt < self._max_retries - 1:
                await self._sleep(self._base_delay * (2 ** attempt))

        return None
