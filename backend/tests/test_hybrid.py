from __future__ import annotations

import pytest

from app.search.bm25 import BM25Index
from app.search.filters import SearchFilters
from app.search.hybrid import HybridSearcher, SearchResult
from app.search.vector import VectorIndex
from tests.conftest import SAMPLE_DOCS, FakeEmbedder

_QUERY = "volcano erupts lava and ash"


@pytest.fixture
def searcher(fake_embedder: FakeEmbedder) -> HybridSearcher:
    doc_ids = [doc["doc_id"] for doc in SAMPLE_DOCS]
    vectors = fake_embedder.encode([doc["text"] for doc in SAMPLE_DOCS])
    bm25 = BM25Index.build(SAMPLE_DOCS)
    vector = VectorIndex.build(doc_ids, vectors)
    docs_by_id = {doc["doc_id"]: doc for doc in SAMPLE_DOCS}
    return HybridSearcher(bm25, vector, fake_embedder, docs_by_id)


def _ids(results: list[SearchResult]) -> list[str]:
    return [result.doc_id for result in results]


def test_alpha_one_matches_bm25_order(
    searcher: HybridSearcher, fake_embedder: FakeEmbedder
) -> None:
    bm25 = BM25Index.build(SAMPLE_DOCS)
    expected = [doc_id for doc_id, _ in bm25.query(_QUERY, top_k=len(SAMPLE_DOCS))]
    results = searcher.search(_QUERY, top_k=len(SAMPLE_DOCS), alpha=1.0)
    assert _ids(results) == expected


def test_alpha_zero_matches_vector_order(
    searcher: HybridSearcher, fake_embedder: FakeEmbedder
) -> None:
    doc_ids = [doc["doc_id"] for doc in SAMPLE_DOCS]
    vectors = fake_embedder.encode([doc["text"] for doc in SAMPLE_DOCS])
    vector = VectorIndex.build(doc_ids, vectors)
    query_vec = fake_embedder.encode([_QUERY])[0]
    expected = [doc_id for doc_id, _ in vector.query(query_vec, k=len(SAMPLE_DOCS))]
    results = searcher.search(_QUERY, top_k=len(SAMPLE_DOCS), alpha=0.0)
    assert _ids(results) == expected


def test_top_k_respected(searcher: HybridSearcher) -> None:
    results = searcher.search(_QUERY, top_k=3, alpha=0.5)
    assert len(results) == 3


def test_hybrid_blend_and_range(searcher: HybridSearcher) -> None:
    alpha = 0.5
    results = searcher.search(_QUERY, top_k=len(SAMPLE_DOCS), alpha=alpha)
    for result in results:
        expected = alpha * result.bm25_norm + (1.0 - alpha) * result.vector_norm
        assert result.hybrid_score == pytest.approx(expected)
        assert 0.0 <= result.bm25_norm <= 1.0
        assert 0.0 <= result.vector_norm <= 1.0
        assert 0.0 <= result.hybrid_score <= 1.0
    scores = [result.hybrid_score for result in results]
    assert scores == sorted(scores, reverse=True)


def test_filtered_search_excludes_and_highlights(searcher: HybridSearcher) -> None:
    # Keep only docs created on or before 2024-01-17 (doc-001..doc-003).
    filters = SearchFilters(created_to="2024-01-17T00:00:00Z")
    results = searcher.search(_QUERY, top_k=len(SAMPLE_DOCS), alpha=0.5, filters=filters)
    ids = {result.doc_id for result in results}
    assert {"doc-004", "doc-005", "doc-006"}.isdisjoint(ids)
    by_id = {result.doc_id: result for result in results}
    # doc-001 shares volcano/lava/ash with the query, so its snippet highlights.
    assert "<em>" in by_id["doc-001"].snippet


def test_result_carries_raw_and_normalised(searcher: HybridSearcher) -> None:
    results = searcher.search(_QUERY, top_k=1, alpha=0.5)
    top = results[0]
    assert top.title
    assert top.source == "sample"
    assert top.created_at
    assert isinstance(top.bm25_raw, float)
    assert isinstance(top.vector_raw, float)
    assert isinstance(top.bm25_norm, float)
    assert isinstance(top.vector_norm, float)
