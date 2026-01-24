import asyncio
import time
from collections import deque
from typing import Any

from src.utils.logger import logger


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, max_requests: int, time_window: float = 60.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()

            while self._timestamps and self._timestamps[0] <= now - self.time_window:
                self._timestamps.popleft()

            if len(self._timestamps) >= self.max_requests:
                sleep_time = self._timestamps[0] - (now - self.time_window)
                if sleep_time > 0:
                    logger.info(
                        "rate_limiter.throttled",
                        sleep_seconds=round(sleep_time, 2),
                        queue_size=len(self._timestamps),
                    )
                    await asyncio.sleep(sleep_time)

            self._timestamps.append(time.monotonic())

    async def __aenter__(self) -> "RateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


# Pre-configured limiters for different APIs
uspto_limiter = RateLimiter(max_requests=45, time_window=60.0)
epo_limiter = RateLimiter(max_requests=10, time_window=60.0)
