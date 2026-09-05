from __future__ import annotations

from pathlib import Path

import pytest

from app.api.deps import SearchService, get_commit, get_version
from app.config import load_config
from app.index.__main__ import build_indexes
from app.ingest.writer import Doc, write_jsonl


def _write_corpus(docs: list[dict[str, str]]) -> list[Doc]:
    settings = load_config()
    typed = [Doc(**doc) for doc in docs]
    write_jsonl(typed, settings.processed_dir / "docs.jsonl")
    return typed


def test_get_version_matches_pyproject() -> None:
    assert get_version() == "0.1.0"


def test_get_commit_never_raises_and_returns_str() -> None:
    commit = get_commit()
    assert isinstance(commit, str)
    assert commit != ""


def test_get_commit_falls_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.api.deps as deps

    monkeypatch.setattr(deps.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    monkeypatch.setenv("HSS_COMMIT", "deadbeef")
    assert get_commit() == "deadbeef"


def test_get_commit_falls_back_to_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.api.deps as deps

    monkeypatch.setattr(deps.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    monkeypatch.delenv("HSS_COMMIT", raising=False)
    assert get_commit() == "unknown"


def test_search_service_loads_and_searches(
    tmp_repo: Path,
    fake_embedder,
    sample_docs: list[dict[str, str]],
) -> None:
    settings = load_config()
    docs = _write_corpus(sample_docs)
    build_indexes(docs, settings.index_dir, fake_embedder, settings.embedding_model)

    service = SearchService.load(fake_embedder)
    assert set(service.docs_by_id) == {doc.doc_id for doc in docs}

    results = service.searcher.search("volcano erupts lava", top_k=3)
    assert 1 <= len(results) <= 3
    assert all(0.0 <= r.hybrid_score <= 1.0 for r in results)


def test_missing_corpus_raises_ingest_command(
    tmp_repo: Path, fake_embedder
) -> None:
    with pytest.raises(RuntimeError) as excinfo:
        SearchService.load(fake_embedder)
    assert "python -m app.ingest" in str(excinfo.value)


def test_missing_index_raises_build_command(
    tmp_repo: Path,
    fake_embedder,
    sample_docs: list[dict[str, str]],
) -> None:
    _write_corpus(sample_docs)
    with pytest.raises(RuntimeError) as excinfo:
        SearchService.load(fake_embedder)
    assert "python -m app.index" in str(excinfo.value)
