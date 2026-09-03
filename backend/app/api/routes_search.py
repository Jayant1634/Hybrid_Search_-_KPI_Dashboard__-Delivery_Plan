"""HTTP routes: ``GET /health`` and ``POST /search``.

``/search`` maps the validated request onto the loaded ``HybridSearcher``,
translates the API-facing ``normalization``/``filters`` into the search layer's
vocabulary, and returns each hit's full score breakdown and snippet plus a
``request_id`` and ``took_ms``. ``/health`` reports liveness, build info, and the
built index's metadata.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.api.deps import SearchService, get_commit, get_version
from app.api.schemas import SearchRequest
from app.config import load_config
from app.index.metadata import IndexMetadata
from app.observability.metrics import render as render_metrics
from app.search.filters import SearchFilters

router = APIRouter()

# API normalization names -> search-layer normaliser keys.
_NORMALIZATION = {"minmax": "min_max", "zscore": "z_score"}


class IndexMeta(BaseModel):
    """Metadata describing the currently loaded index."""

    model: str
    dimension: int
    corpus_hash: str
    doc_count: int
    built_at: str


class HealthResponse(BaseModel):
    """Liveness plus build and index information."""

    status: str
    version: str
    commit: str
    index: IndexMeta | None


class SearchResultItem(BaseModel):
    """One ranked hit with its full, explainable score breakdown."""

    doc_id: str
    title: str
    bm25_score: float
    vector_score: float
    bm25_norm: float
    vector_norm: float
    hybrid_score: float
    snippet: str


class SearchResponse(BaseModel):
    """Ranked results for one query plus request-tracing metadata."""

    request_id: str
    took_ms: float
    results: list[SearchResultItem]


def _get_service(request: Request) -> SearchService:
    return request.app.state.search_service


def _index_metadata() -> IndexMeta | None:
    try:
        meta = IndexMetadata.load(load_config().index_dir)
    except (FileNotFoundError, OSError, ValueError, KeyError):
        return None
    return IndexMeta(**asdict(meta))


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report liveness, build info, and the loaded index's metadata."""
    return HealthResponse(
        status="ok",
        version=get_version(),
        commit=get_commit(),
        index=_index_metadata(),
    )


@router.get("/metrics")
def metrics() -> PlainTextResponse:
    """Prometheus text exposition of in-process request and search metrics."""
    return PlainTextResponse(
        render_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.post("/search", response_model=SearchResponse)
def search(payload: SearchRequest, request: Request) -> SearchResponse:
    """Run a hybrid search and return the ranked, explainable results."""
    service = _get_service(request)

    filters = None
    if payload.filters is not None:
        filters = SearchFilters(
            source_contains=payload.filters.source_contains,
            created_from=payload.filters.created_from,
            created_to=payload.filters.created_to,
        )

    start = time.perf_counter()
    hits = service.searcher.search(
        query=payload.query,
        top_k=payload.top_k,
        alpha=payload.alpha,
        normalization=_NORMALIZATION[payload.normalization],
        filters=filters,
    )
    took_ms = (time.perf_counter() - start) * 1000.0

    results = [
        SearchResultItem(
            doc_id=hit.doc_id,
            title=hit.title,
            bm25_score=hit.bm25_raw,
            vector_score=hit.vector_raw,
            bm25_norm=hit.bm25_norm,
            vector_norm=hit.vector_norm,
            hybrid_score=hit.hybrid_score,
            snippet=hit.snippet,
        )
        for hit in hits
    ]

    return SearchResponse(
        request_id=uuid.uuid4().hex,
        took_ms=took_ms,
        results=results,
    )
