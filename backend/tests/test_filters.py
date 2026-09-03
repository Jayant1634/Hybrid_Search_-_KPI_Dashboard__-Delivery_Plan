from __future__ import annotations

from app.search.filters import SearchFilters, apply

_DOCS = [
    {"doc_id": "a", "source": "wiki/volcanoes", "created_at": "2024-01-15T00:00:00Z"},
    {"doc_id": "b", "source": "wiki/bread", "created_at": "2024-02-10T00:00:00Z"},
    {"doc_id": "c", "source": "blog/python", "created_at": "2024-03-05T00:00:00Z"},
]


def _ids(docs: list) -> list[str]:
    return [doc["doc_id"] for doc in docs]


def test_no_constraints_keeps_everything() -> None:
    assert _ids(apply(_DOCS, SearchFilters())) == ["a", "b", "c"]


def test_source_contains_substring() -> None:
    assert _ids(apply(_DOCS, SearchFilters(source_contains="wiki"))) == ["a", "b"]


def test_created_range_is_inclusive() -> None:
    filters = SearchFilters(
        created_from="2024-01-15T00:00:00Z",
        created_to="2024-02-10T00:00:00Z",
    )
    assert _ids(apply(_DOCS, filters)) == ["a", "b"]


def test_constraints_combine() -> None:
    filters = SearchFilters(source_contains="wiki", created_from="2024-02-01T00:00:00Z")
    assert _ids(apply(_DOCS, filters)) == ["b"]


def test_missing_fields_do_not_crash() -> None:
    assert apply([{"doc_id": "x"}], SearchFilters(source_contains="wiki")) == []
