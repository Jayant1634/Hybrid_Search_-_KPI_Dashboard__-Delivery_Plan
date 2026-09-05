"""Hybrid search fusing BM25 and vector scores into one ranking.

Each side contributes its top candidates; the union is normalised per side and
combined as ``hybrid = alpha * norm_bm25 + (1 - alpha) * norm_vector``. Every
result carries its raw and normalised component scores so a caller can explain
exactly why a document ranked where it did.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .bm25 import BM25Index
from .embedder import Embedder
from .filters import SearchFilters, apply
from .highlight import make_snippet
from .normalize import normalize
from .tokenize import tokenize
from .vector import VectorIndex

_CANDIDATE_POOL = 50


@dataclass(frozen=True)
class SearchResult:
    """A single ranked hit with its full score breakdown (explainability)."""

    doc_id: str
    title: str
    source: str
    created_at: str
    bm25_raw: float
    vector_raw: float
    bm25_norm: float
    vector_norm: float
    hybrid_score: float
    snippet: str


class HybridSearcher:
    """Combine a BM25 index and a vector index into a single ranking."""

    def __init__(
        self,
        bm25: BM25Index,
        vector: VectorIndex,
        embedder: Embedder,
        docs_by_id: Mapping[str, Mapping[str, str]],
    ) -> None:
        self._bm25 = bm25
        self._vector = vector
        self._embedder = embedder
        self._docs_by_id = docs_by_id

    @property
    def embedder(self) -> Embedder:
        return self._embedder

    def search(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = 0.5,
        normalization: str = "min_max",
        filters: SearchFilters | None = None,
        min_vector_score: float = 0.0,
    ) -> list[SearchResult]:
        """Return the ``top_k`` hits ranked by the hybrid score.

        Takes the top candidates from each side, unions them (a document
        missing on one side scores 0 there), drops any that fail ``filters``,
        drops any whose raw vector score is below ``min_vector_score``,
        normalises each side over the surviving candidates with
        ``normalization``, then blends with ``alpha``. Each result carries a
        snippet highlighting the query tokens.
        """
        pool = len(self._docs_by_id) if filters is not None else _CANDIDATE_POOL
        bm25_raw = dict(self._bm25.query(query, top_k=pool))
        query_vector = self._embedder.encode([query])[0]
        vector_raw = dict(self._vector.query(query_vector, k=pool))

        doc_ids = list(bm25_raw.keys() | vector_raw.keys())
        if filters is not None:
            kept = apply(
                (self._docs_by_id[d] for d in doc_ids if d in self._docs_by_id),
                filters,
            )
            allowed = {doc["doc_id"] for doc in kept}
            doc_ids = [doc_id for doc_id in doc_ids if doc_id in allowed]

        bm25_union = {doc_id: bm25_raw.get(doc_id, 0.0) for doc_id in doc_ids}
        vector_union = {doc_id: vector_raw.get(doc_id, 0.0) for doc_id in doc_ids}
        if min_vector_score > 0.0:
            doc_ids = [
                doc_id
                for doc_id in doc_ids
                if vector_union[doc_id] >= min_vector_score
            ]
            bm25_union = {doc_id: bm25_union[doc_id] for doc_id in doc_ids}
            vector_union = {doc_id: vector_union[doc_id] for doc_id in doc_ids}

        bm25_norm = normalize(normalization, bm25_union)
        vector_norm = normalize(normalization, vector_union)

        hybrid = {
            doc_id: alpha * bm25_norm[doc_id]
            + (1.0 - alpha) * vector_norm[doc_id]
            for doc_id in doc_ids
        }
        ranked = sorted(doc_ids, key=lambda doc_id: (-hybrid[doc_id], doc_id))

        terms = tokenize(query)
        results: list[SearchResult] = []
        for doc_id in ranked[:top_k]:
            doc = self._docs_by_id.get(doc_id, {})
            results.append(
                SearchResult(
                    doc_id=doc_id,
                    title=doc.get("title", ""),
                    source=doc.get("source", ""),
                    created_at=doc.get("created_at", ""),
                    bm25_raw=bm25_union[doc_id],
                    vector_raw=vector_union[doc_id],
                    bm25_norm=bm25_norm[doc_id],
                    vector_norm=vector_norm[doc_id],
                    hybrid_score=hybrid[doc_id],
                    snippet=make_snippet(doc.get("text", ""), terms),
                )
            )
        return results
