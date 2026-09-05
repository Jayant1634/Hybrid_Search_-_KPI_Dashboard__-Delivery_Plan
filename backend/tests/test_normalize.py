from __future__ import annotations

import pytest

from app.search.normalize import min_max, normalize, rrf, z_score

_FIVE = {"a": 10.0, "b": 20.0, "c": 30.0, "d": 40.0, "e": 50.0}
_K = 60


def test_min_max_five_values() -> None:
    result = min_max(_FIVE)
    assert result == pytest.approx(
        {"a": 0.0, "b": 0.25, "c": 0.5, "d": 0.75, "e": 1.0}
    )


def test_min_max_empty() -> None:
    assert min_max({}) == {}


def test_constant_input_returns_ones_for_all_normalisers() -> None:
    constant = {"a": 7.0, "b": 7.0}
    assert min_max(constant) == {"a": 1.0, "b": 1.0}
    assert z_score(constant) == {"a": 1.0, "b": 1.0}
    assert rrf(constant, k=_K) == {"a": 1.0, "b": 1.0}


def test_single_score_is_one_for_all_normalisers() -> None:
    assert min_max({"a": 3.5}) == {"a": 1.0}
    assert z_score({"a": 3.5}) == {"a": 1.0}
    assert rrf({"a": 3.5}, k=_K) == {"a": 1.0}


def test_z_score_five_values_in_unit_range() -> None:
    result = z_score(_FIVE)
    assert min(result.values()) == pytest.approx(0.0)
    assert max(result.values()) == pytest.approx(1.0)
    assert all(0.0 <= v <= 1.0 for v in result.values())


def test_z_score_keeps_ordering() -> None:
    scores = {"a": 3.0, "b": 100.0, "c": -5.0, "d": 42.0, "e": 7.5}
    result = z_score(scores)
    ranked_in = sorted(scores, key=scores.__getitem__)
    ranked_out = sorted(result, key=result.__getitem__)
    assert ranked_in == ranked_out


def test_z_score_empty() -> None:
    assert z_score({}) == {}


def test_rrf_five_values_uses_caller_k() -> None:
    result = rrf(_FIVE, k=_K)
    assert result == pytest.approx(
        {
            "a": 1.0 / (_K + 5),
            "b": 1.0 / (_K + 4),
            "c": 1.0 / (_K + 3),
            "d": 1.0 / (_K + 2),
            "e": 1.0 / (_K + 1),
        }
    )


def test_rrf_different_k_changes_scores() -> None:
    steep = rrf(_FIVE, k=0)
    flat = rrf(_FIVE, k=100)
    assert steep["e"] == pytest.approx(1.0)
    assert steep["a"] == pytest.approx(0.2)
    assert flat["e"] > flat["a"]
    assert (flat["e"] - flat["a"]) < (steep["e"] - steep["a"])


def test_rrf_ignores_score_magnitude() -> None:
    stretched = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0, "e": 1000.0}
    assert rrf(stretched, k=_K) == pytest.approx(rrf(_FIVE, k=_K))


def test_rrf_ties_share_dense_rank() -> None:
    result = rrf({"a": 10.0, "b": 20.0, "c": 20.0, "d": 30.0}, k=_K)
    assert result["d"] == pytest.approx(1.0 / (_K + 1))
    assert result["b"] == pytest.approx(1.0 / (_K + 2))
    assert result["c"] == pytest.approx(1.0 / (_K + 2))
    assert result["a"] == pytest.approx(1.0 / (_K + 3))


def test_rrf_empty() -> None:
    assert rrf({}, k=_K) == {}


def test_rrf_rejects_negative_k() -> None:
    with pytest.raises(ValueError, match="k must be >= 0"):
        rrf(_FIVE, k=-1)


def test_rrf_requires_k() -> None:
    with pytest.raises(TypeError):
        rrf(_FIVE)  # type: ignore[call-arg]


def test_dispatcher_routes_by_name() -> None:
    assert normalize("min_max", _FIVE) == min_max(_FIVE)
    assert normalize("z_score", _FIVE) == z_score(_FIVE)
    assert normalize("rrf", _FIVE, k=_K) == rrf(_FIVE, k=_K)


def test_dispatcher_rrf_requires_k() -> None:
    with pytest.raises(ValueError, match="rrf requires k"):
        normalize("rrf", _FIVE)


def test_dispatcher_rejects_unknown_name() -> None:
    with pytest.raises(ValueError) as excinfo:
        normalize("softmax", _FIVE)
    assert "softmax" in str(excinfo.value)
