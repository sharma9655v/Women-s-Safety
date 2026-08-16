from __future__ import annotations

import hashlib
import time
from collections import deque
from functools import lru_cache
from typing import Protocol

import redis as redis_client
from fastapi import Request

from app.config import settings

RateLimitWindowS = 3600


class RateLimiter(Protocol):
    def allow(self, client_key: str) -> bool: ...


class MemoryRateLimiter:
    """Sliding-window limiter, dev/fallback backend."""

    def __init__(self, limit: int, window_s: int) -> None:
        self._limit = limit
        self._window_s = window_s
        self._hits: dict[str, deque[float]] = {}

    def allow(self, client_key: str) -> bool:
        now = time.monotonic()
        hits = self._hits.setdefault(client_key, deque())
        while hits and now - hits[0] > self._window_s:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        return True


class RedisRateLimiter:
    """Fixed-window limiter with atomic INCR + EXPIRE."""

    def __init__(
        self, redis_url: str, limit: int, window_s: int, prefix: str = "ratelimit"
    ) -> None:
        self._client = redis_client.from_url(redis_url)
        self._limit = limit
        self._window_s = window_s
        self._prefix = prefix

    def allow(self, client_key: str) -> bool:
        bucket = f"{self._prefix}:{client_key}:{int(time.time()) // self._window_s}"
        pipe = self._client.pipeline()
        pipe.incr(bucket)
        pipe.expire(bucket, self._window_s * 2)
        count = pipe.execute()[0]
        return int(count) <= self._limit


def client_key(request: Request) -> str:
    """Pseudonymous client identifier: a hash of the client IP.

    Only the hash is ever stored or logged — never the address itself.
    X-Forwarded-For is trusted only when TRUST_PROXY=1 (the app sits behind
    a reverse proxy that overwrites the header). Otherwise a client could
    set it themselves and bypass per-client rate limits.
    """
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            ip = first
        else:
            ip = request.client.host if request.client is not None else "unknown"
    else:
        ip = request.client.host if request.client is not None else "unknown"
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


@lru_cache(maxsize=8)
def get_rate_limiter(
    prefix: str = "report_ratelimit",
    limit: int | None = None,
    window_s: int = RateLimitWindowS,
) -> RateLimiter:
    """Backend-aware limiter: Redis when reachable, else in-memory.

    ``limit`` defaults to the report limit for backward compatibility; route
    and future endpoints pass their own limits and bucket prefixes.
    """
    if limit is None:
        limit = settings.report_rate_limit_per_hour
    try:
        probe = redis_client.from_url(settings.redis_url, socket_connect_timeout=2)
        probe.ping()
        probe.close()
    except redis_client.RedisError:
        return MemoryRateLimiter(limit, window_s)
    return RedisRateLimiter(settings.redis_url, limit, window_s, prefix=prefix)
