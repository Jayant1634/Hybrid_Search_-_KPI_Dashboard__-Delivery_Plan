"""Per-request middleware: request id, timing, structured logging.

Every request gets a ``request_id`` (the client's ``X-Request-ID`` is reused when
present, otherwise one is generated), is timed, and produces a single info log
line with ``request_id``, ``path``, ``status`` and ``latency_ms``. ``POST
/search`` additionally writes a row to the ``requests`` table. Any unhandled
exception is logged at error level and answered with a 500 that carries the
``request_id`` in its body.
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.observability.metrics import record_request, record_search_latency
from app.storage.repo import insert_request

logger = logging.getLogger("app.api.request")

REQUEST_ID_HEADER = "X-Request-ID"
_SEARCH_PATH = "/search"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request id, time the request, log it, and persist searches."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        is_search = request.url.path == _SEARCH_PATH

        params = await _read_search_params(request) if is_search else {}

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000.0
            logger.error(
                "request failed",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "status": 500,
                    "latency_ms": latency_ms,
                    "error": str(exc),
                },
            )
            if is_search:
                _persist_search(
                    request, request_id, params, latency_ms, None, str(exc)
                )
                record_search_latency(latency_ms)
            record_request(request.url.path, 500)
            return JSONResponse(
                status_code=500,
                content={
                    "request_id": request_id,
                    "detail": "internal server error",
                },
                headers={REQUEST_ID_HEADER: request_id},
            )

        result_count: int | None = None
        if is_search:
            response, result_count = await _capture_result_count(response)

        latency_ms = (time.perf_counter() - start) * 1000.0
        logger.info(
            "request",
            extra={
                "request_id": request_id,
                "path": request.url.path,
                "status": response.status_code,
                "latency_ms": latency_ms,
            },
        )
        if is_search:
            error = (
                None
                if response.status_code < 400
                else f"status {response.status_code}"
            )
            _persist_search(
                request, request_id, params, latency_ms, result_count, error
            )
            record_search_latency(latency_ms)
        record_request(request.url.path, response.status_code)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response


async def _read_search_params(request: Request) -> dict[str, object]:
    """Best-effort parse of the JSON search body for logging fields."""

    try:
        raw = await request.body()
        data = json.loads(raw) if raw else {}
    except (ValueError, UnicodeDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        "query": data.get("query"),
        "top_k": data.get("top_k"),
        "alpha": data.get("alpha"),
        "normalization": data.get("normalization"),
    }


async def _capture_result_count(response: Response) -> tuple[Response, int | None]:
    """Drain the streamed response, rebuild it, and count ``results``."""

    chunks = [chunk async for chunk in response.body_iterator]  # type: ignore[attr-defined]
    body = b"".join(
        chunk if isinstance(chunk, bytes) else str(chunk).encode() for chunk in chunks
    )
    count: int | None = None
    try:
        payload = json.loads(body) if body else {}
        results = payload.get("results") if isinstance(payload, dict) else None
        if isinstance(results, list):
            count = len(results)
    except (ValueError, UnicodeDecodeError):
        count = None
    rebuilt = Response(
        content=body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )
    return rebuilt, count


def _persist_search(
    request: Request,
    request_id: str,
    params: dict[str, object],
    latency_ms: float,
    result_count: int | None,
    error: str | None,
) -> None:
    """Write one row to the ``requests`` table; never raise into the request."""

    conn = getattr(request.app.state, "db", None)
    if conn is None:
        return
    query = params.get("query")
    top_k = params.get("top_k")
    alpha = params.get("alpha")
    try:
        insert_request(
            conn,
            request_id=request_id,
            query=str(query) if query is not None else "",
            latency_ms=latency_ms,
            top_k=int(top_k) if isinstance(top_k, int) else None,
            alpha=float(alpha) if isinstance(alpha, (int, float)) else None,
            result_count=result_count,
            error=error,
        )
    except Exception:
        logger.exception(
            "failed to persist request row", extra={"request_id": request_id}
        )
