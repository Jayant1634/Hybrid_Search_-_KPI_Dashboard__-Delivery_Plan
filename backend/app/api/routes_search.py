"""HTTP routes: ``GET /health``, ``POST /search``, ``GET /documents/{id}``,
and ``POST /feedback``.

``/search`` maps the validated request onto the loaded ``HybridSearcher``,
translates the API-facing ``normalization``/``filters`` into the search layer's
vocabulary, and returns each hit's full score breakdown and snippet plus a
``request_id`` and ``took_ms``. ``GET /documents/{doc_id}`` returns the stored
document (title, source, full text) plus optional query-term occurrences and
highlighted body when ``q`` is passed. ``/feedback`` stores a relevance signal
for a known ``doc_id`` (404 otherwise). ``/health`` reports liveness, build
info, and the built index's metadata.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.api.deps import SearchService, get_commit, get_version
from app.api.schemas import FeedbackRequest, SearchRequest
from app.config import load_config
from app.index.metadata import IndexMetadata
from app.observability.metrics import render as render_metrics
from app.search.filters import SearchFilters
from app.search.highlight import (
    closest_document_words,
    count_occurrences,
    highlight_document,
)
from app.search.tokenize import tokenize
from app.storage.repo import insert_feedback

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
    source: str
    created_at: str
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


class FeedbackResponse(BaseModel):
    """Acknowledgement that a feedback signal was stored."""

    ok: bool = True


class TermCount(BaseModel):
    """How many document words contain one query term."""

    term: str
    count: int


class ClosestWord(BaseModel):
    """A document token nearest the query embedding, plus how often it appears."""

    term: str
    count: int
    score: float


class DocumentDetail(BaseModel):
    """Full stored document plus optional query-term highlighting."""

    doc_id: str
    title: str
    source: str
    created_at: str
    text: str
    highlighted_text: str
    occurrences: list[TermCount]
    closest: list[ClosestWord]


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
            dataset=payload.filters.dataset,
        )

    start = time.perf_counter()
    hits = service.searcher.search(
        query=payload.query,
        top_k=payload.top_k,
        alpha=payload.alpha,
        normalization=_NORMALIZATION[payload.normalization],
        filters=filters,
        min_vector_score=payload.min_vector_score,
    )
    took_ms = (time.perf_counter() - start) * 1000.0

    results = [
        SearchResultItem(
            doc_id=hit.doc_id,
            title=hit.title,
            source=hit.source,
            created_at=hit.created_at,
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


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: str, request: Request, q: str = "") -> DocumentDetail:
    """Return one corpus document, with query-term highlights when ``q`` is set."""
    service = _get_service(request)
    doc = service.docs_by_id.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")

    terms = tokenize(q) if q.strip() else []
    body = doc.get("text", "")
    closest = (
        closest_document_words(body, q, service.searcher.embedder)
        if terms
        else []
    )
    return DocumentDetail(
        doc_id=doc["doc_id"],
        title=doc.get("title", ""),
        source=doc.get("source", ""),
        created_at=doc.get("created_at", ""),
        text=body,
        highlighted_text=highlight_document(
            body, terms, [row[0] for row in closest]
        ),
        occurrences=[
            TermCount(term=term, count=count)
            for term, count in count_occurrences(body, terms)
        ],
        closest=[
            ClosestWord(term=term, count=count, score=score)
            for term, count, score in closest
        ],
    )


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(
    payload: FeedbackRequest, request: Request
) -> FeedbackResponse:
    """Store a relevance signal for a document that exists in the corpus."""
    service = _get_service(request)
    if payload.doc_id not in service.docs_by_id:
        raise HTTPException(status_code=404, detail="document not found")
    insert_feedback(
        request.app.state.db,
        request_id=payload.request_id,
        doc_id=payload.doc_id,
        relevant=payload.relevant,
    )
    return FeedbackResponse(ok=True)
