from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import SearchService
from app.api.main import create_app
from app.config import load_config
from app.index.__main__ import build_indexes
from app.ingest.writer import Doc, write_jsonl


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
        yield test_client


def test_health_has_version_and_commit(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert body["commit"]
    assert body["index"]["doc_count"] == 6


def test_search_returns_score_breakdown_and_snippet(client: TestClient) -> None:
    resp = client.post("/search", json={"query": "volcano erupts lava"})
    assert resp.status_code == 200
    body = resp.json()
    assert "request_id" in body
    assert isinstance(body["took_ms"], (int, float))
    assert body["results"]
    first = body["results"][0]
    for field in ("bm25_score", "vector_score", "hybrid_score", "snippet"):
        assert field in first


def test_top_k_is_respected(client: TestClient) -> None:
    resp = client.post("/search", json={"query": "volcano", "top_k": 2})
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 2


def test_alpha_extremes_give_different_orders(client: TestClient) -> None:
    query = {"query": "bread flour water yeast crust", "top_k": 6}
    bm25_only = client.post("/search", json={**query, "alpha": 1.0}).json()
    vector_only = client.post("/search", json={**query, "alpha": 0.0}).json()

    bm25_order = [r["doc_id"] for r in bm25_only["results"]]
    vector_order = [r["doc_id"] for r in vector_only["results"]]
    assert bm25_order != vector_order


def test_bad_request_fails_validation(client: TestClient) -> None:
    resp = client.post("/search", json={"query": ""})
    assert resp.status_code == 422
