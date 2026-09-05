from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.loadtest.burst import (
    BurstHit,
    DEFAULT_QUERY,
    MAX_COUNT,
    MIN_COUNT,
    _summarise,
    run_search_burst,
)


def test_summarise_percentiles_and_counts() -> None:
    hits = [
        BurstHit(status=200, latency_ms=10.0, took_ms=8.0, result_count=3, error=None),
        BurstHit(status=200, latency_ms=20.0, took_ms=18.0, result_count=2, error=None),
        BurstHit(status=500, latency_ms=30.0, took_ms=None, result_count=None, error="boom"),
    ]
    summary = _summarise(hits, wall_ms=40.0)
    assert summary.sent == 3
    assert summary.ok == 2
    assert summary.failed == 1
    assert summary.wall_ms == 40.0
    assert summary.p50 == 20.0
    assert summary.avg_ms == 20.0
    assert summary.min_ms == 10.0
    assert summary.max_ms == 30.0


def test_run_search_burst_rejects_out_of_range_count() -> None:
    with pytest.raises(ValueError, match="count"):
        run_search_burst(object(), None, query="volcano", count=MIN_COUNT - 1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="count"):
        run_search_burst(object(), None, query="volcano", count=MAX_COUNT + 1)  # type: ignore[arg-type]


def test_load_test_request_allows_count_above_fifty() -> None:
    from app.api.routes_dashboard import LoadTestRequest

    assert MAX_COUNT == 200
    assert LoadTestRequest(query="volcano", count=51).count == 51
    assert LoadTestRequest(query="volcano", count=200).count == 200


def test_locustfile_defines_search_user() -> None:
    path = Path(__file__).resolve().parents[1] / "app" / "loadtest" / "locustfile.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    classes = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    assert "SearchUser" in classes
    assert DEFAULT_QUERY == "volcano"
