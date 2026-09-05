"""Pydantic v2 request/response models for the search API.

These models define and validate the JSON contract for the HTTP layer:
``/search`` (query + tuning knobs -> ranked results with full score
breakdowns), ``/health`` (liveness), and ``/feedback`` (relevance signals).
Defaults for ``alpha`` and ``normalization`` are read from the app config so a
caller that omits them gets the deployment's configured behaviour.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.config import load_config

Normalization = Literal["minmax", "zscore", "rrf"]


def _default_alpha() -> float:
    return load_config().default_alpha


def _default_normalization() -> Normalization:
    name = load_config().normalisation
    return name if name in ("minmax", "zscore", "rrf") else "minmax"


class SearchFiltersModel(BaseModel):
    """Optional pre-ranking constraints on the candidate set."""

    model_config = ConfigDict(extra="forbid")

    source_contains: str | None = None
    created_from: str | None = None
    created_to: str | None = None
    dataset: Literal["wikipedia", "contracts"] | None = None

    @field_validator("created_from", "created_to")
    @classmethod
    def _must_be_iso8601(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("must be an ISO-8601 datetime") from exc
        return value



class SearchRequest(BaseModel):
    """A hybrid-search query with optional tuning and filters."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=10, ge=1, le=50)
    alpha: float = Field(default_factory=_default_alpha, ge=0.0, le=1.0)
    normalization: Normalization = Field(default_factory=_default_normalization)
    min_vector_score: float = Field(default=0.2, ge=0.0, le=1.0)
    rrf_k: int | None = Field(default=None, ge=0, le=10000)
    filters: SearchFiltersModel | None = None

    @model_validator(mode="after")
    def _rrf_k_required_for_rrf(self) -> SearchRequest:
        if self.normalization == "rrf" and self.rrf_k is None:
            raise ValueError("rrf_k is required when normalization is rrf")
        return self


class SearchResultItem(BaseModel):
    """A single ranked hit with its full, explainable score breakdown."""

    doc_id: str
    title: str
    bm25_raw: float
    vector_raw: float
    bm25_norm: float
    vector_norm: float
    hybrid_score: float
    snippet: str


class SearchResponse(BaseModel):
    """The ranked results for one search plus request-tracing metadata."""

    request_id: str
    took_ms: float
    results: list[SearchResultItem]


class HealthResponse(BaseModel):
    """Liveness signal for the API."""

    status: Literal["ok"] = "ok"


class FeedbackRequest(BaseModel):
    """A relevance signal tying a document back to an earlier search."""

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1)
    doc_id: str = Field(min_length=1)
    relevant: bool
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    """Acknowledgement that a feedback signal was accepted."""

    status: Literal["accepted"] = "accepted"
