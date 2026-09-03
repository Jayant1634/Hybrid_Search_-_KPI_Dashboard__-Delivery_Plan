from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import SearchService
from app.api.main import create_app
from app.config import load_config
from app.index.__main__ import build_indexes
from app.ingest.writer import Doc, write_jsonl
from app.observability.metrics import percentile, record_search_latency, reset, snapshot


def test_percentile_p50_p95_on_known_list() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    # Linear interpolation at (n-1)*p/100: p50 -> index 4.5 -> 55; p95 -> 8.55 -> 95.5
    assert percentile(values, 50) == 55.0
    assert percentile(values, 95) == pytest.approx(95.5)


def test_percentile_empty_and_single() -> None:
    assert percentile([], 50) == 0.0
    assert percentile([42.0], 95) == 42.0


def test_search_latency_window_and_snapshot() -> None:
    reset()
    for value in (10.0, 20.0, 30.0):
        record_search_latency(value)
    snap = snapshot()
    assert snap["search_count"] == 3
    assert snap["search_sum"] == 60.0
    assert snap["p50"] == 20.0


@pytest.fixture
def built_service(
    tmp_repo: Path,
    fake_embedder,
    sample_docs: list[dict[str, str]],
) -> SearchService:
    settings = load_config()
    docs = [Doc(**doc) for doc in sample_docs]
    write_jsonl(docs, settings.processed_dir / "docs.jsonl")
    build_indexes(
        docs, settings.index_dir, fake_embedder, settings.embedding_model
    )
    return SearchService.load(fake_embedder)


def test_metrics_endpoint_shows_count_3_after_three_searches(
    built_service: SearchService,
) -> None:
    reset()
    app = create_app(search_service=built_service)
    with TestClient(app) as client:
        for _ in range(3):
            resp = client.post("/search", json={"query": "volcano"})
            assert resp.status_code == 200
        metrics = client.get("/metrics")

    assert metrics.status_code == 200
    assert "text/plain" in metrics.headers["content-type"]
    body = metrics.text
    assert "search_latency_ms_count 3" in body
    assert 'http_requests_total{path="/search",status="200"} 3' in body
