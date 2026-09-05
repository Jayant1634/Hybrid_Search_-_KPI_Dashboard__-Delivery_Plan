from __future__ import annotations

import sys
from collections.abc import Iterator
from types import ModuleType
from typing import Any

import numpy as np
import pytest

from app.config import load_config
from app.search.embedder import Embedder, SentenceTransformerEmbedder


class _FakeSentenceTransformer:
    """Stand-in so tests never download a real model."""

    last: _FakeSentenceTransformer | None = None

    def __init__(self, model_name: str, device: str | None = None) -> None:
        self.model_name = model_name
        self.device = device
        self.encode_kwargs: dict[str, Any] | None = None
        type(self).last = self

    max_seq_length = 256

    def get_embedding_dimension(self) -> int:
        return 4

    def encode(
        self,
        texts: list[str],
        batch_size: int = 32,
        normalize_embeddings: bool = False,
        convert_to_numpy: bool = True,
        **kwargs: object,
    ) -> np.ndarray:
        self.encode_kwargs = {
            "batch_size": batch_size,
            "normalize_embeddings": normalize_embeddings,
            "convert_to_numpy": convert_to_numpy,
            **kwargs,
        }
        raw = np.ones((len(texts), 4), dtype=np.float64)
        raw[:, 0] = np.arange(1, len(texts) + 1, dtype=np.float64)
        if normalize_embeddings:
            norms = np.linalg.norm(raw, axis=1, keepdims=True)
            raw = raw / norms
        return raw


@pytest.fixture
def fake_st(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[_FakeSentenceTransformer]]:
    """Inject a fake module so tests never import (or download) the real model."""
    _FakeSentenceTransformer.last = None
    load_config.cache_clear()
    fake_mod = ModuleType("sentence_transformers")
    fake_mod.SentenceTransformer = _FakeSentenceTransformer  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_mod)
    yield _FakeSentenceTransformer
    load_config.cache_clear()


def test_uses_model_name_from_config(
    fake_st: type[_FakeSentenceTransformer],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HSS_EMBEDDING_MODEL", "fake-mini-model")
    load_config.cache_clear()
    embedder = SentenceTransformerEmbedder()
    assert fake_st.last is not None
    assert fake_st.last.model_name == "fake-mini-model"
    assert fake_st.last.device == "cpu"
    assert embedder.dimension == 4
    assert isinstance(embedder, Embedder)


def test_default_lifts_max_seq_length(
    fake_st: type[_FakeSentenceTransformer],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HSS_MAX_SEQ_LENGTH", raising=False)
    load_config.cache_clear()
    SentenceTransformerEmbedder()
    assert fake_st.last is not None
    # Default HSS_MAX_SEQ_LENGTH is 512, lifting MiniLM's 256 window.
    assert fake_st.last.max_seq_length == 512


def test_env_sets_max_seq_length(
    fake_st: type[_FakeSentenceTransformer],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HSS_MAX_SEQ_LENGTH", "384")
    load_config.cache_clear()
    SentenceTransformerEmbedder()
    assert fake_st.last is not None
    assert fake_st.last.max_seq_length == 384


def test_encode_returns_normalised_float32(
    fake_st: type[_FakeSentenceTransformer],
) -> None:
    embedder = SentenceTransformerEmbedder()
    vectors = embedder.encode(["volcano", "bread"])
    assert vectors.dtype == np.float32
    assert vectors.shape == (2, 4)
    norms = np.linalg.norm(vectors, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-6)
    assert fake_st.last is not None
    assert fake_st.last.encode_kwargs is not None
    assert fake_st.last.encode_kwargs["batch_size"] == 32
    assert fake_st.last.encode_kwargs["normalize_embeddings"] is True


def test_encode_reports_batch_progress(
    fake_st: type[_FakeSentenceTransformer],
) -> None:
    embedder = SentenceTransformerEmbedder()
    seen: list[tuple[int, int]] = []
    texts = [f"text-{i}" for i in range(40)]
    embedder.encode(texts, on_progress=lambda done, total: seen.append((done, total)))
    assert seen == [(32, 40), (40, 40)]


def test_encode_empty_list_has_zero_rows(
    fake_st: type[_FakeSentenceTransformer],
) -> None:
    embedder = SentenceTransformerEmbedder()
    vectors = embedder.encode([])
    assert vectors.dtype == np.float32
    assert vectors.shape == (0, embedder.dimension)
    assert fake_st.last is not None
    assert fake_st.last.encode_kwargs is None


def test_fake_embedder_shape_and_norm(fake_embedder: Embedder) -> None:
    vectors = fake_embedder.encode(["volcano", "bread"])
    assert vectors.dtype == np.float32
    assert vectors.shape == (2, 8)
    assert fake_embedder.dimension == 8
    norms = np.linalg.norm(vectors.astype(np.float64), axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-6)
