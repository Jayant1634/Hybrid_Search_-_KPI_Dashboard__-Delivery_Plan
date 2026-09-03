from __future__ import annotations

import pytest

from app.search.normalize import min_max, normalize, z_score

_FIVE = {"a": 10.0, "b": 20.0, "c": 30.0, "d": 40.0, "e": 50.0}


def test_min_max_five_values() -> None:
    result = min_max(_FIVE)
    assert result == pytest.approx(
        {"a": 0.0, "b": 0.25, "c": 0.5, "d": 0.75, "e": 1.0}
    )


def test_min_max_empty() -> None:
    assert min_max({}) == {}


def test_min_max_constant_scores_all_one() -> None:
    assert min_max({"a": 7.0, "b": 7.0}) == {"a": 1.0, "b": 1.0}


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


def test_dispatcher_routes_by_name() -> None:
    assert normalize("min_max", _FIVE) == min_max(_FIVE)
    assert normalize("z_score", _FIVE) == z_score(_FIVE)


def test_dispatcher_rejects_unknown_name() -> None:
    with pytest.raises(ValueError) as excinfo:
        normalize("softmax", _FIVE)
    assert "softmax" in str(excinfo.value)
