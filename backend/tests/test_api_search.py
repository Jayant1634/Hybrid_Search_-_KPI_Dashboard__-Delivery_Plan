from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import SearchService
from app.api.main import create_app
from app.config import load_config
from app.index.__main__ import build_indexes
from app.ingest.writer import Doc, write_jsonl
from app.storage.db import connect
from app.storage.repo import select_feedback


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


def _feedback_rows(request_id: str | None = None) -> list[sqlite3.Row]:
    conn = connect(load_config().sqlite_path)
    try:
        return select_feedback(conn, request_id=request_id)
    finally:
        conn.close()


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


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"query": ""}, "query"),
        ({"query": "x" * 501}, "query"),
        ({"query": "q", "top_k": 0}, "top_k"),
        ({"query": "q", "top_k": 51}, "top_k"),
        ({"query": "q", "alpha": -0.1}, "alpha"),
        ({"query": "q", "alpha": 1.1}, "alpha"),
        ({"query": "q", "normalization": "foo"}, "normalization"),
        ({"query": "q", "filters": {"created_from": "not-a-date"}}, "created_from"),
    ],
)
def test_search_validation_errors(
    client: TestClient, payload: dict[str, object], field: str
) -> None:
    resp = client.post("/search", json=payload)
    assert resp.status_code == 422
    assert field in resp.text


def test_feedback_stores_row(client: TestClient) -> None:
    resp = client.post(
        "/feedback",
        json={
            "request_id": "req-1",
            "doc_id": "doc-001",
            "relevant": True,
            "comment": "good hit",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    rows = _feedback_rows(request_id="req-1")
    assert len(rows) == 1
    assert rows[0]["doc_id"] == "doc-001"
    assert rows[0]["relevant"] == 1


def test_feedback_unknown_doc_is_404(client: TestClient) -> None:
    resp = client.post(
        "/feedback",
        json={
            "request_id": "req-1",
            "doc_id": "doc-missing",
            "relevant": False,
        },
    )
    assert resp.status_code == 404
    rows = _feedback_rows()
    assert rows == []
