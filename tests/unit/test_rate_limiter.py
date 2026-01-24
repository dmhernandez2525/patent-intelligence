import asyncio
import time

import pytest

from src.utils.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limit():
    limiter = RateLimiter(max_requests=5, time_window=1.0)

    for _ in range(5):
        await limiter.acquire()


@pytest.mark.asyncio
async def test_rate_limiter_throttles_over_limit():
    limiter = RateLimiter(max_requests=2, time_window=0.5)

    start = time.monotonic()
    for _ in range(3):
        await limiter.acquire()
    elapsed = time.monotonic() - start

    assert elapsed >= 0.3


@pytest.mark.asyncio
async def test_rate_limiter_context_manager():
    limiter = RateLimiter(max_requests=10, time_window=1.0)

    async with limiter:
        pass  # Should not raise
