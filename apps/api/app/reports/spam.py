from __future__ import annotations

import hashlib
import time
from functools import lru_cache
from typing import Protocol

import redis as redis_client

from app.config import settings


class DuplicateDetector(Protocol):
    def is_duplicate(self, key: str) -> bool: ...

    def record(self, key: str) -> None: ...


class MemoryDuplicateDetector:
    """Exact-duplicate detector for dev/fallback use."""

    def __init__(self, window_s: int) -> None:
        self._window_s = window_s
        self._seen: dict[str, float] = {}

    def is_duplicate(self, key: str) -> bool:
        seen_at = self._seen.get(key)
        return seen_at is not None and time.monotonic() - seen_at <= self._window_s

    def record(self, key: str) -> None:
        self._seen[key] = time.monotonic()


class RedisDuplicateDetector:
    def __init__(self, redis_url: str, window_s: int) -> None:
        self._client = redis_client.from_url(redis_url)
        self._window_s = window_s

    def is_duplicate(self, key: str) -> bool:
        return bool(self._client.get(f"report_dup:{key}"))

    def record(self, key: str) -> None:
        self._client.set(f"report_dup:{key}", "1", ex=self._window_s)


def report_key(segment_id: int, category: str, description_redacted: str, client: str) -> str:
    """Exact-duplicate key: same reporter, segment, category and content."""
    payload = f"{client}|{segment_id}|{category}|{description_redacted}"
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


@lru_cache(maxsize=1)
def get_duplicate_detector() -> DuplicateDetector:
    try:
        probe = redis_client.from_url(settings.redis_url, socket_connect_timeout=2)
        probe.ping()
        probe.close()
    except redis_client.RedisError:
        return MemoryDuplicateDetector(settings.report_duplicate_window_s)
    return RedisDuplicateDetector(settings.redis_url, settings.report_duplicate_window_s)
