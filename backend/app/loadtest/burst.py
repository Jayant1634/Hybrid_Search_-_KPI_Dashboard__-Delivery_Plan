"""Fire N hybrid searches at once and persist them like live ``/search``.

The KPI drawer calls this in-process so we do not HTTP-loop back into the
same uvicorn worker (that deadlocks with ``BaseHTTPMiddleware``). Locust
(``locustfile.py``) is the out-of-process driver for longer soaks.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.config import load_config
from app.observability.metrics import percentile
from app.search.filters import SearchFilters
from app.search.hybrid import HybridSearcher
from app.storage.repo import insert_request

DEFAULT_QUERY = "volcano"
DEFAULT_COUNT = 20
MIN_COUNT = 2
MAX_COUNT = 200

_NORMALIZATION = {"minmax": "min_max", "zscore": "z_score", "rrf": "rrf"}


@dataclass(frozen=True)
class BurstHit:
    status: int
    latency_ms: float
    took_ms: float | None
    result_count: int | None
    error: str | None


@dataclass(frozen=True)
class BurstResult:
    sent: int
    ok: int
    failed: int
    wall_ms: float
    p50: float
    p95: float
    avg_ms: float
    min_ms: float
    max_ms: float


def _summarise(hits: list[BurstHit], wall_ms: float) -> BurstResult:
    latencies = [hit.latency_ms for hit in hits]
    ok = sum(1 for hit in hits if 200 <= hit.status < 400)
    return BurstResult(
        sent=len(hits),
        ok=ok,
        failed=len(hits) - ok,
        wall_ms=wall_ms,
        p50=percentile(latencies, 50),
        p95=percentile(latencies, 95),
        avg_ms=(sum(latencies) / len(latencies)) if latencies else 0.0,
        min_ms=min(latencies) if latencies else 0.0,
        max_ms=max(latencies) if latencies else 0.0,
    )


def _one_search(
    searcher: HybridSearcher,
    *,
    query: str,
    top_k: int,
    alpha: float,
    normalization: str,
    filters: SearchFilters | None,
    rrf_k: int | None,
) -> BurstHit:
    start = time.perf_counter()
    try:
        hits = searcher.search(
            query=query,
            top_k=top_k,
            alpha=alpha,
            normalization=normalization,
            filters=filters,
            rrf_k=rrf_k,
        )
        latency_ms = (time.perf_counter() - start) * 1000.0
        return BurstHit(
            status=200,
            latency_ms=latency_ms,
            took_ms=latency_ms,
            result_count=len(hits),
            error=None,
        )
    except Exception as exc:
        latency_ms = (time.perf_counter() - start) * 1000.0
        return BurstHit(
            status=500,
            latency_ms=latency_ms,
            took_ms=None,
            result_count=None,
            error=str(exc),
        )


def run_search_burst(
    searcher: HybridSearcher,
    conn: sqlite3.Connection | None,
    *,
    query: str,
    count: int,
    top_k: int = 10,
    alpha: float | None = None,
    dataset: str | None = None,
    rrf_k: int | None = None,
) -> BurstResult:
    """Run ``count`` searches concurrently and write ``requests`` rows."""

    if count < MIN_COUNT or count > MAX_COUNT:
        raise ValueError(f"count must be {MIN_COUNT}..{MAX_COUNT}")

    settings = load_config()
    used_alpha = settings.default_alpha if alpha is None else alpha
    norm_key = _NORMALIZATION.get(settings.normalisation, "min_max")
    if norm_key == "rrf" and rrf_k is None:
        raise ValueError("rrf requires rrf_k")
    filters = SearchFilters(dataset=dataset) if dataset is not None else None

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=count) as pool:
        futures = [
            pool.submit(
                _one_search,
                searcher,
                query=query,
                top_k=top_k,
                alpha=used_alpha,
                normalization=norm_key,
                filters=filters,
                rrf_k=rrf_k,
            )
            for _ in range(count)
        ]
        hits = [future.result() for future in futures]
    wall_ms = (time.perf_counter() - wall_start) * 1000.0

    if conn is not None:
        for hit in hits:
            insert_request(
                conn,
                request_id=uuid.uuid4().hex,
                query=query,
                latency_ms=hit.latency_ms,
                top_k=top_k,
                alpha=used_alpha,
                result_count=hit.result_count,
                error=hit.error,
            )

    return _summarise(hits, wall_ms)
