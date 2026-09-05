"""Per-IP token-bucket rate limiter used as a FastAPI dependency.

Meant to be attached only to ``POST /search`` and ``POST /feedback``. Each
client IP gets a bucket of ``rate_limit_per_minute`` tokens (from config
unless overridden) that refills continuously over a 60-second window.
When the bucket is empty the dependency raises HTTP 429 with a
``Retry-After`` header. Tests inject time via ``clock``.
"""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import HTTPException, Request

from app.config import load_config

Clock = Callable[[], float]

LIMITED_PATHS = frozenset({"/search", "/feedback"})


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


class RateLimiter:
    """Token bucket keyed by client IP.

    Capacity equals ``rate_per_minute`` (burst of one minute). Tokens refill
    at ``rate_per_minute / 60`` per second. ``clock`` is ``() -> float`` and
    defaults to ``time.monotonic``.
    """

    def __init__(
        self,
        rate_per_minute: int | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.rate_per_minute = (
            load_config().rate_limit_per_minute
            if rate_per_minute is None
            else rate_per_minute
        )
        self._clock: Clock = clock or time.monotonic
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def allow(self, client_ip: str) -> bool:
        """Consume one token for ``client_ip``. True if the request may proceed."""
        return self.take(client_ip) is None

    def take(self, client_ip: str) -> int | None:
        """Consume one token. Return None if allowed, else Retry-After seconds."""
        rate = self.rate_per_minute
        if rate <= 0:
            return 60
        refill_per_second = rate / 60.0
        with self._lock:
            now = self._clock()
            bucket = self._buckets.get(client_ip)
            if bucket is None:
                bucket = _Bucket(tokens=float(rate), updated_at=now)
                self._buckets[client_ip] = bucket
            elapsed = max(0.0, now - bucket.updated_at)
            bucket.tokens = min(float(rate), bucket.tokens + elapsed * refill_per_second)
            bucket.updated_at = now
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return None
            wait = (1.0 - bucket.tokens) / refill_per_second
            return max(1, math.ceil(wait))

    def __call__(self, request: Request) -> None:
        """FastAPI dependency: 429 + Retry-After when this IP is over limit.

        No-ops on paths other than ``/search`` and ``/feedback``.
        """
        if request.url.path not in LIMITED_PATHS:
            return
        client_ip = request.client.host if request.client else "unknown"
        retry_after = self.take(client_ip)
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail="rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )


def rate_limit(request: Request) -> None:
    """App-state FastAPI dependency; builds a config-backed limiter on first use.

    Honours ``app.state.rate_limiter`` when tests (or ``create_app``) inject one.
    """
    limiter = getattr(request.app.state, "rate_limiter", None)
    if limiter is None:
        limiter = RateLimiter()
        request.app.state.rate_limiter = limiter
    limiter(request)
