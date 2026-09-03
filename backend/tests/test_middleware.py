from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.deps import SearchService
from app.api.main import create_app
from app.config import load_config
from app.index.__main__ import build_indexes
from app.ingest.writer import Doc, write_jsonl
from app.storage.db import connect
from app.storage.repo import select_requests


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


def test_two_searches_write_two_rows(built_service: SearchService) -> None:
    settings = load_config()
    app = create_app(search_service=built_service)
    with TestClient(app) as client:
        first = client.post(
            "/search", json={"query": "volcano erupts lava", "top_k": 3}
        )
        second = client.post("/search", json={"query": "bread flour yeast"})
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.headers["X-Request-ID"]

    reader = connect(settings.sqlite_path)
    try:
        rows = select_requests(reader)
    finally:
        reader.close()

    assert len(rows) == 2
    queries = {row["query"] for row in rows}
    assert queries == {"volcano erupts lava", "bread flour yeast"}
    for row in rows:
        assert row["latency_ms"] is not None
        assert row["result_count"] is not None
        assert row["error"] is None


def test_reuses_client_request_id_header(built_service: SearchService) -> None:
    app = create_app(search_service=built_service)
    with TestClient(app) as client:
        resp = client.post(
            "/search",
            json={"query": "volcano"},
            headers={"X-Request-ID": "client-supplied-id"},
        )
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == "client-supplied-id"


def test_forced_exception_returns_500_with_request_id(
    built_service: SearchService,
) -> None:
    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("forced failure")

    built_service.searcher.search = _boom  # type: ignore[method-assign]
    app = create_app(search_service=built_service)

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/search",
            json={"query": "anything"},
            headers={"X-Request-ID": "explode-id"},
        )

    assert resp.status_code == 500
    body = resp.json()
    assert body["request_id"] == "explode-id"
    assert resp.headers["X-Request-ID"] == "explode-id"
