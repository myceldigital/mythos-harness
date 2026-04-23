from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass(slots=True)
class RateLimitResult:
    allowed: bool
    retry_after_s: int = 0
    detail: str = ""


class RateLimiter:
    async def check(
        self, identity: str, *, requests_per_window: int, window_seconds: int
    ) -> RateLimitResult:
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    def __init__(self) -> None:
        self._bucket: dict[str, deque[float]] = defaultdict(deque)

    async def check(
        self, identity: str, *, requests_per_window: int, window_seconds: int
    ) -> RateLimitResult:
        now = time.monotonic()
        window_start = now - window_seconds
        history = self._bucket[identity]
        while history and history[0] < window_start:
            history.popleft()
        if len(history) >= requests_per_window:
            retry_after = max(1, int(history[0] + window_seconds - now))
            return RateLimitResult(
                allowed=False,
                retry_after_s=retry_after,
                detail="rate_limited",
            )
        history.append(now)
        return RateLimitResult(allowed=True)


class RedisRateLimiter(RateLimiter):
    """Distributed fixed-window limiter using Redis INCR + EXPIRE."""

    def __init__(self, redis_url: str, prefix: str = "mythos") -> None:
        self.redis_url = redis_url
        self.prefix = prefix
        self._redis: Redis | None = None
        self._lock = asyncio.Lock()

    async def check(
        self, identity: str, *, requests_per_window: int, window_seconds: int
    ) -> RateLimitResult:
        redis = await self._client()
        now_epoch = int(time.time())
        window_index = now_epoch // window_seconds
        key = f"{self.prefix}:rl:{identity}:{window_index}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds + 1)
        if count > requests_per_window:
            window_end = (window_index + 1) * window_seconds
            retry_after = max(1, window_end - now_epoch)
            return RateLimitResult(
                allowed=False,
                retry_after_s=retry_after,
                detail="rate_limited",
            )
        return RateLimitResult(allowed=True)

    async def _client(self) -> Redis:
        if self._redis is not None:
            return self._redis
        async with self._lock:
            if self._redis is None:
                self._redis = Redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                )
            return self._redis
