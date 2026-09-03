from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.search.vector import VectorIndex
from tests.conftest import FakeEmbedder

_DOCS = [
    ("doc-a", "A volcano erupts lava and ash from magma deep in the earth."),
    ("doc-b", "Bread is baked from dough of flour, water, and yeast."),
    ("doc-c", "Lava cools into volcanic rock after a volcano erupts."),
]


def _build_index(embedder: FakeEmbedder) -> VectorIndex:
    doc_ids = [doc_id for doc_id, _ in _DOCS]
    vectors = embedder.encode([text for _, text in _DOCS])
    return VectorIndex.build(doc_ids, vectors)


def test_doc_finds_itself_first(fake_embedder: FakeEmbedder) -> None:
    index = _build_index(fake_embedder)
    for doc_id, text in _DOCS:
        query_vec = fake_embedder.encode([text])[0]
        results = index.query(query_vec, k=3)
        assert results[0][0] == doc_id
        assert results[0][1] == pytest.approx(1.0, abs=1e-5)


def test_save_load_roundtrip(
    fake_embedder: FakeEmbedder, tmp_path: Path
) -> None:
    index = _build_index(fake_embedder)
    folder = tmp_path / "vector"
    index.save(folder)
    assert (folder / "index.faiss").is_file()
    assert (folder / "doc_ids.json").is_file()

    loaded = VectorIndex.load(folder)
    query_vec = fake_embedder.encode([_DOCS[0][1]])[0]
    assert loaded.query(query_vec, k=3) == index.query(query_vec, k=3)


def test_query_wrong_dimension_raises(fake_embedder: FakeEmbedder) -> None:
    index = _build_index(fake_embedder)
    bad_vector = np.ones(3, dtype=np.float32)
    with pytest.raises(ValueError) as excinfo:
        index.query(bad_vector, k=1)
    message = str(excinfo.value)
    assert "3" in message
    assert str(fake_embedder.dimension) in message
