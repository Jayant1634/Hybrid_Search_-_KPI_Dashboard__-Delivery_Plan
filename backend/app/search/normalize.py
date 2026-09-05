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

    When all scores are equal (zero spread) every doc gets ``1.0``. An empty
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
        return {doc_id: 1.0 for doc_id in ids}
    scaled = (values - low) / spread
    return {doc_id: float(value) for doc_id, value in zip(ids, scaled)}


def z_score(scores: Mapping[str, float]) -> dict[str, float]:
    """Standardise ``scores`` then squash into ``0..1`` preserving order.

    Scores are centred and scaled by their standard deviation, then passed
    through min-max so the result lands in ``0..1``. This keeps the relative
    ordering of the inputs. When all scores are equal (zero standard
    deviation) every doc gets ``1.0``, matching ``min_max`` on a constant
    set: each doc is equally the best of the pool. An empty input yields
    an empty output.
    """
    if not scores:
        return {}
    ids = list(scores)
    values = np.asarray([scores[doc_id] for doc_id in ids], dtype=np.float64)
    std = float(values.std())
    if std == 0.0:
        return {doc_id: 1.0 for doc_id in ids}
    standardised = (values - float(values.mean())) / std
    return min_max({doc_id: float(v) for doc_id, v in zip(ids, standardised)})


def rrf(scores: Mapping[str, float], *, k: int) -> dict[str, float]:
    """Map ``scores`` to reciprocal ranks ``1 / (k + rank)``.

    ``k`` is required (no product default). It is a rank-smoothing constant:
    the score of rank ``r`` is ``1 / (k + r)``. Small ``k`` lets the top
    ranks dominate (``k = 0`` is pure ``1 / rank``); large ``k`` flattens
    the gaps so mid-ranked docs stay competitive.

    Ignores raw magnitudes: the highest score is rank 1, the next distinct
    score is rank 2 (dense ranks; ties share a rank). Values already sit in
    ``(0, 1/(k+1)]`` when ``k >= 0``, so they stay inside ``0..1`` without
    a second rescale. An empty input yields an empty output. A constant
    (or single-score) set all share rank 1; that is the same tied-pool case
    as ``min_max`` and ``z_score``, so every doc gets ``1.0``.
    """
    if k < 0:
        raise ValueError("k must be >= 0")
    if not scores:
        return {}
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    result: dict[str, float] = {}
    rank = 0
    previous: float | None = None
    for doc_id, value in ordered:
        if previous is None or value != previous:
            rank += 1
        previous = value
        result[doc_id] = 1.0 / (k + rank)
    if rank == 1:
        return {doc_id: 1.0 for doc_id in result}
    return result


_NORMALIZERS: dict[str, Callable[[Mapping[str, float]], dict[str, float]]] = {
    "min_max": min_max,
    "z_score": z_score,
    "rrf": rrf,
}


def normalize(
    name: str,
    scores: Mapping[str, float],
    *,
    k: int | None = None,
) -> dict[str, float]:
    """Dispatch to a normaliser by ``name``; reject unknown names.

    ``k`` is required when ``name`` is ``rrf`` and ignored otherwise.
    """
    try:
        func = _NORMALIZERS[name]
    except KeyError:
        known = ", ".join(sorted(_NORMALIZERS))
        raise ValueError(
            f"unknown normalizer {name!r}; expected one of: {known}"
        ) from None
    if name == "rrf":
        if k is None:
            raise ValueError("rrf requires k")
        return rrf(scores, k=k)
    return func(scores)
