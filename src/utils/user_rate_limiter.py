"""Per-user token bucket rate limiting with Redis fallback."""

import asyncio
import math
import time
from typing import Any, cast

import redis.asyncio as aioredis
from redis.asyncio import Redis

from src.config import settings
from src.utils.logger import logger


class UserRateLimiter:
    """Token bucket limiter keyed by user ID (or client IP for anonymous traffic)."""

    def __init__(self, max_requests: int, refill_window_seconds: float = 60.0) -> None:
        self.capacity = float(max_requests)
        self.refill_rate = self.capacity / refill_window_seconds
        self._memory_buckets: dict[str, tuple[float, float]] = {}
        self._memory_lock = asyncio.Lock()
        self._redis_client: Redis | None = None
        self._redis_unavailable = False

    async def allow_request(self, key: str) -> bool:
        """Return True when request is within limit."""
        redis_client = await self._get_redis_client()
        if redis_client:
            try:
                return await self._allow_request_redis(redis_client, key)
            except Exception as exc:  # pragma: no cover - fallback path
                logger.warning("rate_limit.redis_failed", error=str(exc))
        return await self._allow_request_memory(key)

    async def _get_redis_client(self) -> Redis | None:
        if self._redis_unavailable:
            return None
        if self._redis_client is not None:
            return self._redis_client

        try:
            redis_factory = cast(Any, aioredis).from_url
            client = cast(
                Redis,
                redis_factory(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                ),
            )
            await client.ping()
            self._redis_client = client
            return client
        except Exception as exc:
            logger.warning("rate_limit.redis_unavailable", error=str(exc))
            self._redis_unavailable = True
            return None

    async def _allow_request_redis(self, client: Redis, key: str) -> bool:
        now = time.time()
        bucket_key = f"rate_limit:user:{key}"

        values_result = client.hgetall(bucket_key)
        if isinstance(values_result, dict):
            values = values_result
        else:
            values = await values_result
        tokens = float(values.get("tokens", str(self.capacity)))
        last_refill = float(values.get("last_refill", str(now)))

        elapsed = max(0.0, now - last_refill)
        tokens = min(self.capacity, tokens + (elapsed * self.refill_rate))

        allowed = tokens >= 1.0
        if allowed:
            tokens -= 1.0

        ttl_seconds = max(60, int(math.ceil((self.capacity / self.refill_rate) * 2)))
        async with client.pipeline(transaction=True) as pipeline:
            pipeline.hset(
                bucket_key,
                mapping={
                    "tokens": f"{tokens:.6f}",
                    "last_refill": f"{now:.6f}",
                },
            )
            pipeline.expire(bucket_key, ttl_seconds)
            await pipeline.execute()

        return allowed

    async def _allow_request_memory(self, key: str) -> bool:
        now = time.time()
        async with self._memory_lock:
            tokens, last_refill = self._memory_buckets.get(key, (self.capacity, now))
            elapsed = max(0.0, now - last_refill)
            tokens = min(self.capacity, tokens + (elapsed * self.refill_rate))

            allowed = tokens >= 1.0
            if allowed:
                tokens -= 1.0

            self._memory_buckets[key] = (tokens, now)
            return allowed


user_rate_limiter = UserRateLimiter(max_requests=settings.rate_limit_per_minute)
