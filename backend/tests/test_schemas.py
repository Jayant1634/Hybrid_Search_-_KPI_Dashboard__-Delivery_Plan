from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schemas import (
    FeedbackRequest,
    SearchRequest,
)
from app.config import load_config


def test_defaults_come_from_config() -> None:
    req = SearchRequest(query="volcano")
    cfg = load_config()
    assert req.top_k == 10
    assert req.alpha == cfg.default_alpha
    assert req.normalization == "minmax"
    assert req.min_vector_score == 0.2
    assert req.filters is None


def test_valid_request_with_filters() -> None:
    req = SearchRequest(
        query="volcano",
        top_k=5,
        alpha=0.3,
        normalization="zscore",
        filters={"source_contains": "wiki", "dataset": "contracts"},
    )
    assert req.alpha == 0.3
    assert req.normalization == "zscore"
    assert req.filters is not None
    assert req.filters.source_contains == "wiki"
    assert req.filters.dataset == "contracts"


@pytest.mark.parametrize(
    "payload",
    [
        {"query": ""},  # too short
        {"query": "x" * 501},  # too long
        {"query": "q", "top_k": 0},  # below range
        {"query": "q", "top_k": 51},  # above range
        {"query": "q", "alpha": -0.1},  # below range
        {"query": "q", "alpha": 1.1},  # above range
        {"query": "q", "min_vector_score": -0.1},
        {"query": "q", "min_vector_score": 1.1},
        {"query": "q", "normalization": "softmax"},  # not allowed
        {"top_k": 5},  # missing query
        {"query": "q", "unknown": 1},  # extra field forbidden
        {"query": "q", "filters": {"dataset": "patents"}},
    ],
)
def test_bad_search_requests_fail_validation(payload: dict) -> None:
    with pytest.raises(ValidationError):
        SearchRequest(**payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"doc_id": "d1", "relevant": True},  # missing request_id
        {"request_id": "r1", "relevant": True},  # missing doc_id
        {"request_id": "r1", "doc_id": "d1"},  # missing relevant
        {"request_id": "", "doc_id": "d1", "relevant": True},  # empty id
        {"request_id": "r1", "doc_id": "d1", "relevant": "maybe"},  # bad bool
    ],
)
def test_bad_feedback_requests_fail_validation(payload: dict) -> None:
    with pytest.raises(ValidationError):
        FeedbackRequest(**payload)
