from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest
from numpy.typing import NDArray

from app.api.deps import SearchService, get_commit, get_commit_message, get_version
from app.config import load_config
from app.index.__main__ import build_indexes
from app.index.metadata import IndexMetadata
from app.ingest.writer import Doc, write_jsonl


class _DimEmbedder:
    """Deterministic Embedder with a configurable output dimension."""

    def __init__(self, dimension: int) -> None:
        self.dimension = dimension

    def encode(
        self,
        texts: list[str],
        on_progress: object | None = None,
    ) -> NDArray[np.float32]:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        rows = []
        for text in texts:
            seed = int.from_bytes(hashlib.sha256(text.encode()).digest()[:8], "little")
            vec = np.random.default_rng(seed).standard_normal(self.dimension)
            norm = float(np.linalg.norm(vec)) or 1.0
            rows.append(vec / norm)
        if on_progress is not None:
            on_progress(len(texts), len(texts))  # type: ignore[operator]
        return np.asarray(np.stack(rows), dtype=np.float32)


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


def test_get_commit_message_never_raises_and_returns_str() -> None:
    message = get_commit_message()
    assert isinstance(message, str)


def test_get_commit_message_falls_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.api.deps as deps

    monkeypatch.setattr(deps.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    monkeypatch.setenv("HSS_COMMIT_MESSAGE", "compact health cards")
    assert get_commit_message() == "compact health cards"


def test_get_commit_message_falls_back_to_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.api.deps as deps

    monkeypatch.setattr(deps.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    monkeypatch.delenv("HSS_COMMIT_MESSAGE", raising=False)
    assert get_commit_message() == ""


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


def test_mismatch_fail_raises_naming_models_and_dims(
    tmp_repo: Path,
    sample_docs: list[dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HSS_EMBEDDING_MODEL", "model-a")
    monkeypatch.setenv("HSS_INDEX_ON_MISMATCH", "fail")
    load_config.cache_clear()
    settings = load_config()
    docs = _write_corpus(sample_docs)
    build_indexes(docs, settings.index_dir, _DimEmbedder(8), "model-a")

    # Switch the running model + embedder to a different name and dimension.
    monkeypatch.setenv("HSS_EMBEDDING_MODEL", "model-b")
    load_config.cache_clear()

    with pytest.raises(RuntimeError) as excinfo:
        SearchService.load(_DimEmbedder(4))

    message = str(excinfo.value)
    assert "model-a" in message
    assert "model-b" in message
    assert "8" in message
    assert "4" in message
    assert "python -m app.index" in message


def test_mismatch_rebuild_rebuilds_and_loads(
    tmp_repo: Path,
    sample_docs: list[dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HSS_EMBEDDING_MODEL", "model-a")
    load_config.cache_clear()
    settings = load_config()
    docs = _write_corpus(sample_docs)
    build_indexes(docs, settings.index_dir, _DimEmbedder(8), "model-a")

    # Switch to a new model + dimension and ask for an automatic rebuild.
    monkeypatch.setenv("HSS_EMBEDDING_MODEL", "model-b")
    monkeypatch.setenv("HSS_INDEX_ON_MISMATCH", "rebuild")
    load_config.cache_clear()

    service = SearchService.load(_DimEmbedder(4))

    meta = IndexMetadata.load(settings.index_dir)
    assert meta.model == "model-b"
    assert meta.dimension == 4
    assert set(service.docs_by_id) == {doc.doc_id for doc in docs}

    # The rebuilt index matches the embedder, so a query no longer mismatches.
    results = service.searcher.search("volcano erupts lava", top_k=3)
    assert isinstance(results, list)
