from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import SearchService
from app.api.main import create_app
from app.config import load_config
from app.index.__main__ import build_indexes
from app.ingest.writer import Doc, write_jsonl
from app.storage.db import connect
from app.storage.repo import insert_log, insert_request

_NOW = datetime.now(timezone.utc).isoformat()


def _seed_rows() -> None:
    conn = connect(load_config().sqlite_path)
    try:
        insert_request(
            conn,
            request_id="r1",
            query="volcano",
            latency_ms=12.0,
            result_count=3,
            created_at=_NOW,
        )
        insert_request(
            conn,
            request_id="r2",
            query="ghost",
            latency_ms=8.0,
            result_count=0,
            created_at=_NOW,
        )
        insert_log(
            conn,
            severity="ERROR",
            message="boom",
            request_id="r2",
            created_at=_NOW,
        )
    finally:
        conn.close()


@pytest.fixture
def client(
    tmp_repo: Path,
    fake_embedder,
    sample_docs: list[dict[str, str]],
) -> TestClient:
    settings = load_config()
    docs = [Doc(**doc) for doc in sample_docs]
    write_jsonl(docs, settings.processed_dir / "docs.jsonl")
    build_indexes(docs, settings.index_dir, fake_embedder, settings.embedding_model)
    service = SearchService.load(fake_embedder)
    app = create_app(search_service=service)
    with TestClient(app) as test_client:
        _seed_rows()
        yield test_client


def test_kpi_summary_returns_expected_keys(client: TestClient) -> None:
    resp = client.get("/api/dashboard/kpi/summary", params={"window": "24h"})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {
        "total",
        "p50",
        "p95",
        "zero_result_count",
        "error_count",
    }
    assert body["total"] == 2
    assert body["zero_result_count"] == 1


def test_kpi_volume_returns_expected_keys(client: TestClient) -> None:
    resp = client.get("/api/dashboard/kpi/volume", params={"window": "24h"})
    assert resp.status_code == 200
    body = resp.json()
    assert body
    assert set(body[0]) == {"bucket", "count"}


def test_kpi_top_queries_returns_expected_keys(client: TestClient) -> None:
    resp = client.get(
        "/api/dashboard/kpi/top-queries",
        params={"window": "7d", "limit": 10},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body
    assert set(body[0]) == {"query", "count", "avg_latency_ms"}


def test_kpi_zero_results_returns_expected_keys(client: TestClient) -> None:
    resp = client.get("/api/dashboard/kpi/zero-results", params={"window": "24h"})
    assert resp.status_code == 200
    body = resp.json()
    assert body
    assert set(body[0]) == {"query", "count", "last_seen"}
    assert body[0]["query"] == "ghost"


def test_experiments_empty_when_csv_missing(client: TestClient) -> None:
    resp = client.get("/api/dashboard/experiments")
    assert resp.status_code == 200
    assert resp.json() == []


def test_experiments_returns_csv_row_keys(client: TestClient) -> None:
    path = load_config().metrics_dir / "experiments.csv"
    path.write_text(
        "timestamp,commit,tag,alpha,normalization,model,"
        "preprocessing,ndcg10,recall10,mrr10,n_queries\n"
        "2026-09-04T00:00:00+00:00,abc,base,0.5,minmax,fake,none,"
        "0.8,0.7,0.6,33\n",
        encoding="utf-8",
    )
    resp = client.get("/api/dashboard/experiments")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert set(body[0]) == {
        "timestamp",
        "commit",
        "tag",
        "alpha",
        "normalization",
        "model",
        "preprocessing",
        "ndcg10",
        "recall10",
        "mrr10",
        "n_queries",
    }


def test_logs_returns_expected_keys(client: TestClient) -> None:
    resp = client.get(
        "/api/dashboard/logs",
        params={"window": "24h", "level": "ERROR", "limit": 50},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body
    assert set(body[0]) == {"created_at", "severity", "message", "request_id"}
    assert body[0]["message"] == "boom"


def test_bad_window_is_422(client: TestClient) -> None:
    resp = client.get("/api/dashboard/kpi/summary", params={"window": "yesterday"})
    assert resp.status_code == 422


def test_limit_over_100_is_422(client: TestClient) -> None:
    resp = client.get("/api/dashboard/logs", params={"limit": 101})
    assert resp.status_code == 422


def test_kpi_load_test_fires_concurrent_searches(client: TestClient) -> None:
    from app.loadtest.burst import run_search_burst

    direct = run_search_burst(
        client.app.state.search_service.searcher,
        None,
        query="volcano",
        count=4,
        top_k=5,
    )
    assert direct.sent == 4
    assert direct.ok == 4


def test_kpi_load_test_endpoint_persists_rows(client: TestClient) -> None:
    before = client.get("/api/dashboard/kpi/summary", params={"window": "24h"})
    assert before.status_code == 200
    prior_total = before.json()["total"]

    resp = client.post(
        "/api/dashboard/kpi/load-test",
        json={"query": "volcano", "count": 4, "top_k": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {
        "sent",
        "ok",
        "failed",
        "wall_ms",
        "p50",
        "p95",
        "avg_ms",
        "min_ms",
        "max_ms",
    }
    assert body["sent"] == 4
    assert body["ok"] == 4
    assert body["failed"] == 0
    assert body["p50"] > 0.0

    after = client.get("/api/dashboard/kpi/summary", params={"window": "24h"})
    assert after.status_code == 200
    assert after.json()["total"] == prior_total + 4


def test_kpi_load_test_rejects_count_of_one(client: TestClient) -> None:
    resp = client.post(
        "/api/dashboard/kpi/load-test",
        json={"query": "volcano", "count": 1},
    )
    assert resp.status_code == 422


def test_kpi_load_test_rejects_count_over_two_hundred(client: TestClient) -> None:
    resp = client.post(
        "/api/dashboard/kpi/load-test",
        json={"query": "volcano", "count": 201},
    )
    assert resp.status_code == 422
