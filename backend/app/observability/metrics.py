"""In-process request counters and search-latency percentiles.

Kept in memory (no Prometheus client library). Counters are keyed by path and
status; search latencies keep the last ``LATENCY_WINDOW`` values and expose
p50 / p95 / count / sum. ``render`` emits Prometheus text exposition format.
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque

LATENCY_WINDOW = 1000

_lock = threading.Lock()
_request_counts: dict[tuple[str, int], int] = defaultdict(int)
_search_latencies: deque[float] = deque(maxlen=LATENCY_WINDOW)
_search_sum: float = 0.0
_search_count: int = 0


def reset() -> None:
    """Clear all in-process metrics (tests)."""

    global _search_sum, _search_count
    with _lock:
        _request_counts.clear()
        _search_latencies.clear()
        _search_sum = 0.0
        _search_count = 0


def record_request(path: str, status: int) -> None:
    """Increment the request counter for ``(path, status)``."""

    with _lock:
        _request_counts[(path, status)] += 1


def record_search_latency(latency_ms: float) -> None:
    """Append one search latency, keeping only the last ``LATENCY_WINDOW``."""

    global _search_sum, _search_count
    with _lock:
        if len(_search_latencies) == _search_latencies.maxlen:
            _search_sum -= _search_latencies[0]
            _search_count -= 1
        _search_latencies.append(latency_ms)
        _search_sum += latency_ms
        _search_count += 1


def percentile(values: list[float], p: float) -> float:
    """Linear-interpolated percentile of ``values`` (``p`` in 0..100).

    Empty input returns ``0.0``. Index is ``(n - 1) * p / 100`` between the
    bracketing sorted samples.
    """

    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (p / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def snapshot() -> dict[str, object]:
    """Return a consistent copy of counter and latency state."""

    with _lock:
        latencies = list(_search_latencies)
        counts = dict(_request_counts)
        total = _search_count
        total_sum = _search_sum
    return {
        "request_counts": counts,
        "search_latencies": latencies,
        "search_count": total,
        "search_sum": total_sum,
        "p50": percentile(latencies, 50),
        "p95": percentile(latencies, 95),
    }


def render() -> str:
    """Prometheus text exposition of the current metrics."""

    snap = snapshot()
    lines: list[str] = [
        "# HELP http_requests_total Total HTTP requests by path and status.",
        "# TYPE http_requests_total counter",
    ]
    counts: dict[tuple[str, int], int] = snap["request_counts"]  # type: ignore[assignment]
    for (path, status), value in sorted(counts.items()):
        lines.append(
            f'http_requests_total{{path="{path}",status="{status}"}} {value}'
        )

    lines.extend(
        [
            "# HELP search_latency_ms Search request latency in milliseconds.",
            "# TYPE search_latency_ms summary",
            f'search_latency_ms{{quantile="0.5"}} {snap["p50"]}',
            f'search_latency_ms{{quantile="0.95"}} {snap["p95"]}',
            f"search_latency_ms_sum {snap['search_sum']}",
            f"search_latency_ms_count {snap['search_count']}",
        ]
    )
    return "\n".join(lines) + "\n"
