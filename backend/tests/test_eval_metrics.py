"""Hand-checked nDCG / Recall / MRR numbers. Working is in the comments."""

from __future__ import annotations

import math

import pytest

from app.eval.metrics import mrr_at_k, ndcg_at_k, recall_at_k


def test_perfect_ranking_is_one_on_all_three() -> None:
    # ranked = [a, b, c], relevant = {a:1, b:1, c:1}, k defaults to 10
    # DCG  = 1/log2(2) + 1/log2(3) + 1/log2(4)
    #      = 1/1 + 1/log2(3) + 1/2
    # IDCG = same (ideal order is any permutation of the three relevants)
    # nDCG = DCG/IDCG = 1.0
    # Recall = 3/3 = 1.0
    # MRR    = 1/1 = 1.0  (first hit at rank 1)
    ranked = ["a", "b", "c"]
    relevant = {"a": 1.0, "b": 1.0, "c": 1.0}
    assert ndcg_at_k(ranked, relevant) == pytest.approx(1.0)
    assert recall_at_k(ranked, relevant) == pytest.approx(1.0)
    assert mrr_at_k(ranked, relevant) == pytest.approx(1.0)


def test_one_relevant_at_rank_3() -> None:
    # ranked = [x, y, a], relevant = {a:1}, k=10
    # DCG  = 0/log2(2) + 0/log2(3) + 1/log2(4)
    #      = 0 + 0 + 1/2
    #      = 0.5
    # IDCG = 1/log2(2) = 1/1 = 1.0
    # nDCG = 0.5 / 1.0 = 0.5
    # Recall = 1/1 = 1.0  (the only relevant is inside top-10)
    # MRR    = 1/3
    ranked = ["x", "y", "a"]
    relevant = {"a": 1.0}
    assert ndcg_at_k(ranked, relevant) == pytest.approx(0.5)
    assert recall_at_k(ranked, relevant) == pytest.approx(1.0)
    assert mrr_at_k(ranked, relevant) == pytest.approx(1.0 / 3.0)


def test_two_relevant_at_ranks_1_and_3() -> None:
    # ranked = [d1, d2, d3, d4], relevant = {d1:1, d3:1}, k=4
    # DCG  = 1/log2(2) + 0/log2(3) + 1/log2(4) + 0/log2(5)
    #      = 1/1 + 0 + 1/2 + 0
    #      = 1.5
    # IDCG = 1/log2(2) + 1/log2(3)   (both relevants packed at the top)
    #      = 1 + 1/log2(3)
    # nDCG = 1.5 / (1 + 1/log2(3))
    # Recall = 2/2 = 1.0
    # MRR    = 1/1 = 1.0
    ranked = ["d1", "d2", "d3", "d4"]
    relevant = {"d1": 1.0, "d3": 1.0}
    expected_ndcg = 1.5 / (1.0 + 1.0 / math.log2(3))
    assert ndcg_at_k(ranked, relevant, k=4) == pytest.approx(expected_ndcg)
    assert recall_at_k(ranked, relevant, k=4) == pytest.approx(1.0)
    assert mrr_at_k(ranked, relevant, k=4) == pytest.approx(1.0)


def test_k_cuts_off_a_hit_at_rank_3() -> None:
    # same list as rank-3 case, but k=2 so the hit is outside the window
    # DCG  = 0/log2(2) + 0/log2(3) = 0
    # IDCG = 1/log2(2) = 1
    # nDCG = 0/1 = 0
    # Recall = 0/1 = 0
    # MRR    = 0  (no relevant in top-2)
    ranked = ["x", "y", "a"]
    relevant = {"a": 1.0}
    assert ndcg_at_k(ranked, relevant, k=2) == pytest.approx(0.0)
    assert recall_at_k(ranked, relevant, k=2) == pytest.approx(0.0)
    assert mrr_at_k(ranked, relevant, k=2) == pytest.approx(0.0)


def test_graded_ndcg_high_then_low() -> None:
    # ranked = [a, b, c], relevant = {a:3, c:1}, k=3
    # DCG  = 3/log2(2) + 0/log2(3) + 1/log2(4)
    #      = 3/1 + 0 + 1/2
    #      = 3.5
    # IDCG = 3/log2(2) + 1/log2(3)   (grade 3 first, then grade 1)
    #      = 3 + 1/log2(3)
    # nDCG = 3.5 / (3 + 1/log2(3))
    # Recall = 2/2 = 1.0
    # MRR    = 1/1 = 1.0
    ranked = ["a", "b", "c"]
    relevant = {"a": 3.0, "c": 1.0}
    expected_ndcg = 3.5 / (3.0 + 1.0 / math.log2(3))
    assert ndcg_at_k(ranked, relevant, k=3) == pytest.approx(expected_ndcg)
    assert recall_at_k(ranked, relevant, k=3) == pytest.approx(1.0)
    assert mrr_at_k(ranked, relevant, k=3) == pytest.approx(1.0)


def test_empty_inputs_are_zero() -> None:
    # no ranked hits and/or no relevant docs → DCG=0, IDCG=0 → nDCG=0
    # Recall = 0 (nothing to retrieve / nothing retrieved)
    # MRR    = 0
    assert ndcg_at_k([], {"a": 1.0}) == pytest.approx(0.0)
    assert recall_at_k([], {"a": 1.0}) == pytest.approx(0.0)
    assert mrr_at_k([], {"a": 1.0}) == pytest.approx(0.0)
    assert ndcg_at_k(["a"], {}) == pytest.approx(0.0)
    assert recall_at_k(["a"], {}) == pytest.approx(0.0)
    assert mrr_at_k(["a"], {}) == pytest.approx(0.0)
