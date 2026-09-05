"""Score normalisation helpers for fusing retriever result lists.

Each function takes a mapping of ``doc_id -> raw score`` and returns a new
mapping of ``doc_id -> score`` rescaled into the ``0..1`` range. This lets us
combine scores from different retrievers (e.g. BM25 and cosine similarity) that
live on incomparable scales.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

import numpy as np


def min_max(scores: Mapping[str, float]) -> dict[str, float]:
    """Rescale ``scores`` linearly so the min maps to 0 and the max to 1.

    When all scores are equal (zero spread) every doc gets ``0.0``. An empty
    input yields an empty output.
    """
    if not scores:
        return {}
    ids = list(scores)
    values = np.asarray([scores[doc_id] for doc_id in ids], dtype=np.float64)
    low = float(values.min())
    high = float(values.max())
    spread = high - low
    if spread == 0.0:
        return {doc_id: 0.0 for doc_id in ids}
    scaled = (values - low) / spread
    return {doc_id: float(value) for doc_id, value in zip(ids, scaled)}


def z_score(scores: Mapping[str, float]) -> dict[str, float]:
    """Standardise ``scores`` then squash into ``0..1`` preserving order.

    Scores are centred and scaled by their standard deviation, then passed
    through min-max so the result lands in ``0..1``. This keeps the relative
    ordering of the inputs. When all scores are equal every doc gets ``0.0``.
    An empty input yields an empty output.
    """
    if not scores:
        return {}
    ids = list(scores)
    values = np.asarray([scores[doc_id] for doc_id in ids], dtype=np.float64)
    std = float(values.std())
    if std == 0.0:
        return {doc_id: 0.0 for doc_id in ids}
    standardised = (values - float(values.mean())) / std
    return min_max({doc_id: float(v) for doc_id, v in zip(ids, standardised)})


_NORMALIZERS: dict[str, Callable[[Mapping[str, float]], dict[str, float]]] = {
    "min_max": min_max,
    "z_score": z_score,
}


def normalize(name: str, scores: Mapping[str, float]) -> dict[str, float]:
    """Dispatch to a normaliser by ``name``; reject unknown names."""
    try:
        func = _NORMALIZERS[name]
    except KeyError:
        known = ", ".join(sorted(_NORMALIZERS))
        raise ValueError(
            f"unknown normalizer {name!r}; expected one of: {known}"
        ) from None
    return func(scores)
