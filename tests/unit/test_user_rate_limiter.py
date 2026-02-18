"""Tests for per-user token bucket limiter."""

import pytest

from src.utils.user_rate_limiter import UserRateLimiter


@pytest.mark.asyncio
async def test_per_user_buckets_are_isolated() -> None:
    limiter = UserRateLimiter(max_requests=1, refill_window_seconds=60.0)
    limiter._redis_unavailable = True

    first_user_first = await limiter.allow_request("user:1")
    first_user_second = await limiter.allow_request("user:1")
    second_user_first = await limiter.allow_request("user:2")

    assert first_user_first is True
    assert first_user_second is False
    assert second_user_first is True


class _FakePipeline:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    def hset(self, *args, **kwargs):
        return None

    def expire(self, *args, **kwargs):
        return None

    async def execute(self):
        return None


class _FakeRedis:
    async def hgetall(self, key: str):
        return {}

    def pipeline(self, transaction: bool = True):
        return _FakePipeline()


@pytest.mark.asyncio
async def test_allow_request_redis_path() -> None:
    limiter = UserRateLimiter(max_requests=2, refill_window_seconds=60.0)
    allowed = await limiter._allow_request_redis(_FakeRedis(), "user:1")
    assert allowed is True
