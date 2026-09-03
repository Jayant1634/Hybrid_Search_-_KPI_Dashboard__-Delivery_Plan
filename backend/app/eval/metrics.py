"""Ranking metrics: nDCG@k, Recall@k, and MRR@k.

Each function takes a ranked list of doc ids and a mapping of relevant
``doc_id -> gain``. Gain is graded for nDCG; Recall and MRR treat any
gain > 0 as relevant. ``k`` defaults to 10. DCG uses the standard
``gain / log2(i + 1)`` discount with 1-based ranks.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

DEFAULT_K = 10


def _gains(ranked: Sequence[str], relevant: Mapping[str, float], k: int) -> list[float]:
    cutoff = max(k, 0)
    return [float(relevant.get(doc_id, 0.0)) for doc_id in ranked[:cutoff]]


def _dcg(gains: Sequence[float]) -> float:
    total = 0.0
    for rank, gain in enumerate(gains, start=1):
        if gain <= 0.0:
            continue
        total += gain / math.log2(rank + 1)
    return total


def _positives(relevant: Mapping[str, float]) -> set[str]:
    return {doc_id for doc_id, gain in relevant.items() if float(gain) > 0.0}


def ndcg_at_k(
    ranked: Sequence[str],
    relevant: Mapping[str, float],
    k: int = DEFAULT_K,
) -> float:
    """Normalised DCG at ``k``. Returns 0.0 when there is no positive gain."""
    dcg = _dcg(_gains(ranked, relevant, k))
    ideal = sorted((float(gain) for gain in relevant.values()), reverse=True)
    idcg = _dcg(ideal[: max(k, 0)])
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def recall_at_k(
    ranked: Sequence[str],
    relevant: Mapping[str, float],
    k: int = DEFAULT_K,
) -> float:
    """Fraction of relevant ids that appear in the top ``k``. 0.0 if none."""
    positives = _positives(relevant)
    if not positives:
        return 0.0
    retrieved = set(ranked[: max(k, 0)])
    return len(retrieved & positives) / len(positives)


def mrr_at_k(
    ranked: Sequence[str],
    relevant: Mapping[str, float],
    k: int = DEFAULT_K,
) -> float:
    """Reciprocal rank of the first relevant id in the top ``k``, else 0.0."""
    positives = _positives(relevant)
    for rank, doc_id in enumerate(ranked[: max(k, 0)], start=1):
        if doc_id in positives:
            return 1.0 / rank
    return 0.0
