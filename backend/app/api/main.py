"""FastAPI application factory.

``create_app`` wires the routes and loads the ``SearchService`` once during the
lifespan startup, storing it on ``app.state`` for the request handlers. A
prebuilt service (or a specific embedder) can be injected for tests; otherwise
the real sentence-transformers embedder is used.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.deps import SearchService
from app.api.routes_search import router
from app.search.embedder import Embedder


def create_app(
    search_service: SearchService | None = None,
    embedder: Embedder | None = None,
) -> FastAPI:
    """Build the FastAPI app, loading the search service in the lifespan."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        service = search_service
        if service is None:
            active_embedder = embedder
            if active_embedder is None:
                from app.search.embedder import SentenceTransformerEmbedder

                active_embedder = SentenceTransformerEmbedder()
            service = SearchService.load(active_embedder)
        app.state.search_service = service
        yield

    app = FastAPI(title="Hybrid Search API", lifespan=lifespan)
    app.include_router(router)
    return app
