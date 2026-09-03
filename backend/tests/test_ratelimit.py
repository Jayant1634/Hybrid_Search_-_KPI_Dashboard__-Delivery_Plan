from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.ratelimit import RateLimiter


class _Clock:
    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_allows_n_then_denies() -> None:
    limiter = RateLimiter(rate_per_minute=3, clock=_Clock())
    ip = "10.0.0.1"
    assert limiter.allow(ip)
    assert limiter.allow(ip)
    assert limiter.allow(ip)
    assert not limiter.allow(ip)


def test_refills_over_time() -> None:
    clock = _Clock()
    limiter = RateLimiter(rate_per_minute=2, clock=clock)
    ip = "10.0.0.1"
    assert limiter.allow(ip)
    assert limiter.allow(ip)
    assert not limiter.allow(ip)
    clock.now += 30.0
    assert limiter.allow(ip)
    assert not limiter.allow(ip)


def test_endpoint_gives_429_when_app_created_with_limit_of_2() -> None:
    limiter = RateLimiter(rate_per_minute=2)
    app = FastAPI(dependencies=[Depends(limiter)])

    @app.post("/search")
    def search() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        assert client.post("/search").status_code == 200
        assert client.post("/search").status_code == 200
        resp = client.post("/search")
        assert resp.status_code == 429
        assert resp.headers.get("retry-after")
        assert client.get("/health").status_code == 200
