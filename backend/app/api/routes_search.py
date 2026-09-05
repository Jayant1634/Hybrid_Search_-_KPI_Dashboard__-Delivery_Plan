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

import threading
import time
import uuid
from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.api.deps import SearchService, get_commit, get_commit_message, get_version
from app.api.schemas import FeedbackRequest, ReindexRequest, SearchRequest
from app.config import load_config
from app.index.__main__ import build_indexes
from app.index.metadata import IndexMetadata
from app.index.progress import fail, finishing, finish, snapshot, try_start, update
from app.ingest.writer import read_jsonl
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
_NORMALIZATION = {"minmax": "min_max", "zscore": "z_score", "rrf": "rrf"}


class IndexMeta(BaseModel):
    """Metadata describing the currently loaded index."""

    model: str
    dimension: int
    corpus_hash: str
    doc_count: int
    built_at: str
    granularity: str = "document"
    vector_count: int = 0


class HealthResponse(BaseModel):
    """Liveness plus build and index information."""

    status: str
    version: str
    commit: str
    commit_message: str = ""
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


class ReindexProgress(BaseModel):
    """Live encode progress for an in-flight ``POST /reindex``."""

    running: bool
    granularity: str | None
    done: int
    total: int
    percent: float
    phase: str
    error: str | None = None


class ReindexResponse(BaseModel):
    """Acknowledgement that a rebuild was started in the background."""

    started: bool
    already_running: bool
    progress: ReindexProgress


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
        commit_message=get_commit_message(),
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
        rrf_k=payload.rrf_k,
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


def _progress_model() -> ReindexProgress:
    status = snapshot()
    return ReindexProgress(
        running=status.running,
        granularity=status.granularity,
        done=status.done,
        total=status.total,
        percent=status.percent,
        phase=status.phase,
        error=status.error,
    )


def _run_reindex(
    app: object,
    granularity: str,
    embedder: object,
    docs: object,
    settings: object,
) -> None:
    """Encode + reload the search service; always clears the running flag."""
    try:
        build_indexes(
            docs,
            settings.index_dir,
            embedder,
            settings.embedding_model,
            granularity=granularity,
            on_progress=update,
        )
        finishing()
        app.state.search_service = SearchService.load(embedder, settings)  # type: ignore[attr-defined]
        finish()
    except Exception as exc:
        fail(str(exc))


@router.post("/reindex", response_model=ReindexResponse, status_code=202)
def reindex(payload: ReindexRequest, request: Request) -> ReindexResponse:
    """Start a background rebuild at ``granularity`` and return immediately.

    Poll ``GET /reindex/progress`` for the live percent. A second start while
    one is running is rejected with 409.
    """
    service = _get_service(request)
    settings = load_config()

    docs_path = settings.processed_dir / "docs.jsonl"
    if not docs_path.is_file():
        raise HTTPException(
            status_code=409,
            detail=f"corpus not found at {docs_path}; ingest first",
        )
    docs = read_jsonl(docs_path)
    if not docs:
        raise HTTPException(status_code=409, detail="corpus is empty; ingest first")

    if not try_start(payload.granularity):
        raise HTTPException(status_code=409, detail="a reindex is already running")

    worker = threading.Thread(
        target=_run_reindex,
        args=(
            request.app,
            payload.granularity,
            service.searcher.embedder,
            docs,
            settings,
        ),
        name="hss-reindex",
        daemon=True,
    )
    worker.start()
    return ReindexResponse(
        started=True,
        already_running=False,
        progress=_progress_model(),
    )


@router.get("/reindex/progress", response_model=ReindexProgress)
def reindex_progress() -> ReindexProgress:
    """Return the latest encode-batch snapshot for a live rebuild."""
    return _progress_model()


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
