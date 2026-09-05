"""Edge-case and bug-hunt suite for the whole search stack.

Covers tokenize, BM25, vector, normalize, filters, highlight, hybrid fusion,
request validation, and the HTTP search/document routes. Tests named
``test_bug_*`` assert the *safe / intended* behaviour and are marked
``xfail(strict=True)`` until the matching source file is fixed.

Run::

    python -m pytest tests/test_search_edgecases.py -v
    python -m pytest tests/test_search_edgecases.py -v -k "not test_bug_"
    python -m pytest tests/test_search_edgecases.py -v -k test_bug_
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.deps import SearchService
from app.api.main import create_app
from app.api.schemas import SearchRequest
from app.config import load_config
from app.index.__main__ import build_indexes
from app.ingest.writer import Doc, write_jsonl
from app.search.bm25 import BM25Index
from app.search.filters import SearchFilters, apply
from app.search.highlight import (
    count_occurrences,
    highlight_containing,
    make_snippet,
    unique_terms,
)
from app.search.hybrid import HybridSearcher, SearchResult
from app.search.normalize import min_max, normalize, z_score
from app.search.tokenize import tokenize
from app.search.vector import VectorIndex
from tests.conftest import SAMPLE_DOCS, FakeEmbedder

_QUERY = "volcano erupts lava"


def _searcher(docs: list[dict[str, str]], embedder: FakeEmbedder) -> HybridSearcher:
    doc_ids = [doc["doc_id"] for doc in docs]
    vectors = embedder.encode([doc["text"] for doc in docs])
    return HybridSearcher(
        BM25Index.build(docs),
        VectorIndex.build(doc_ids, vectors),
        embedder,
        {doc["doc_id"]: doc for doc in docs},
    )


def _ids(results: list[SearchResult]) -> list[str]:
    return [result.doc_id for result in results]


@pytest.fixture
def searcher(fake_embedder: FakeEmbedder) -> HybridSearcher:
    return _searcher(SAMPLE_DOCS, fake_embedder)


@pytest.fixture
def client(
    tmp_repo: Path,
    fake_embedder: FakeEmbedder,
    sample_docs: list[dict[str, str]],
) -> TestClient:
    settings = load_config()
    docs = [Doc(**doc) for doc in sample_docs]
    write_jsonl(docs, settings.processed_dir / "docs.jsonl")
    build_indexes(docs, settings.index_dir, fake_embedder, settings.embedding_model)
    service = SearchService.load(fake_embedder)
    app = create_app(search_service=service)
    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Tokenize
# ---------------------------------------------------------------------------


def test_tokenize_unicode_latin_and_cjk() -> None:
    assert tokenize("café lava") == ["café", "lava"]
    assert tokenize("火山 lava") == ["火山", "lava"]


def test_tokenize_drops_emoji_and_punctuation_only() -> None:
    assert tokenize("lava 🌋 ash") == ["lava", "ash"]
    assert tokenize("!!! ???") == []
    assert tokenize("   \t\n") == []


def test_tokenize_keeps_multichar_digits_drops_single() -> None:
    assert tokenize("42 7 007 rocks") == ["42", "007", "rocks"]


def test_tokenize_underscore_is_one_token() -> None:
    assert tokenize("lava_flow ash") == ["lava_flow", "ash"]


def test_tokenize_apostrophe_splits_contraction() -> None:
    # \\w+ treats apostrophe as a break, so "don't" becomes "don" + "t".
    assert tokenize("don't erupt") == ["don", "erupt"]


def test_tokenize_null_byte_and_newline_are_separators() -> None:
    assert tokenize("lava\x00ash") == ["lava", "ash"]
    assert tokenize("lava\nash") == ["lava", "ash"]


def test_tokenize_sql_and_regex_looking_input_does_not_raise() -> None:
    tokens = tokenize("'; DROP TABLE docs; -- lava.*")
    assert "lava" in tokens
    assert tokenize("a.b+c?") == []


# ---------------------------------------------------------------------------
# BM25
# ---------------------------------------------------------------------------


def test_bm25_empty_corpus_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        BM25Index.build([])


def test_bm25_empty_or_stopword_query_scores_zero() -> None:
    index = BM25Index.build(SAMPLE_DOCS)
    for query in ("", "   ", "the a an", "!!!"):
        results = index.query(query)
        assert len(results) == len(SAMPLE_DOCS)
        assert all(score == 0.0 for _, score in results)


def test_bm25_title_only_term_still_ranks_that_doc_first() -> None:
    index = BM25Index.build(SAMPLE_DOCS)
    results = index.query("volcanoes")
    assert results[0][0] == "doc-001"
    assert results[0][1] > 0.0


def test_bm25_missing_title_or_text_does_not_crash() -> None:
    index = BM25Index.build(
        [
            {"doc_id": "a", "title": "", "text": "lava ash"},
            {"doc_id": "b", "title": "Bread", "text": ""},
        ]
    )
    results = index.query("lava")
    assert {doc_id for doc_id, _ in results} == {"a", "b"}
    # With N=2 and df=1, rank_bm25 IDF is log(1.5/1.5) = 0, so the score
    # can be 0.0 even on the document that contains the term.
    assert all(isinstance(score, float) for _, score in results)


def test_bm25_single_doc_corpus_still_returns_a_row() -> None:
    index = BM25Index.build(
        [{"doc_id": "only", "title": "Volcanoes", "text": "A volcano erupts lava"}]
    )
    results = index.query("volcanoes")
    assert len(results) == 1
    assert results[0][0] == "only"
    assert isinstance(results[0][1], float)


# ---------------------------------------------------------------------------
# Vector
# ---------------------------------------------------------------------------


def test_vector_empty_corpus_raises(fake_embedder: FakeEmbedder) -> None:
    with pytest.raises(ValueError, match="empty"):
        VectorIndex.build([], fake_embedder.encode([]))


def test_vector_k_larger_than_corpus_returns_all(fake_embedder: FakeEmbedder) -> None:
    ids = [doc["doc_id"] for doc in SAMPLE_DOCS]
    index = VectorIndex.build(ids, fake_embedder.encode([doc["text"] for doc in SAMPLE_DOCS]))
    query_vec = fake_embedder.encode(["lava"])[0]
    results = index.query(query_vec, k=500)
    assert len(results) == len(SAMPLE_DOCS)


def test_vector_length_mismatch_raises(fake_embedder: FakeEmbedder) -> None:
    vectors = fake_embedder.encode(["one", "two"])
    with pytest.raises(ValueError, match="mismatch"):
        VectorIndex.build(["only-one"], vectors)


# ---------------------------------------------------------------------------
# Normalize
# ---------------------------------------------------------------------------


def test_normalize_single_score_is_one() -> None:
    assert min_max({"a": 3.5}) == {"a": 1.0}
    assert z_score({"a": 3.5}) == {"a": 1.0}


def test_normalize_negative_bm25_values_stay_in_unit_range() -> None:
    raw = {"a": -0.3, "b": 0.0, "c": 1.2}
    for name in ("min_max", "z_score", "rrf"):
        scaled = normalize(name, raw, k=60 if name == "rrf" else None)
        assert set(scaled) == set(raw)
        assert all(0.0 <= value <= 1.0 for value in scaled.values())
        assert scaled["c"] > scaled["a"]


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


def test_filters_source_contains_is_case_sensitive() -> None:
    docs = [{"doc_id": "a", "source": "Wiki/Volcano", "created_at": "2024-01-15T00:00:00Z"}]
    assert apply(docs, SearchFilters(source_contains="Wiki")) == docs
    assert apply(docs, SearchFilters(source_contains="wiki")) == []


def test_filters_empty_source_contains_is_ignored() -> None:
    docs = [{"doc_id": "a", "source": "wiki", "created_at": "2024-01-15T00:00:00Z"}]
    assert apply(docs, SearchFilters(source_contains="")) == docs


def test_filters_inverted_date_range_matches_nothing() -> None:
    docs = [{"doc_id": "a", "source": "s", "created_at": "2024-01-15T00:00:00Z"}]
    filters = SearchFilters(
        created_from="2024-02-01T00:00:00Z",
        created_to="2024-01-01T00:00:00Z",
    )
    assert apply(docs, filters) == []


def test_filters_whitespace_source_matches_nothing_on_sample() -> None:
    docs = [{"doc_id": "a", "source": "wiki/volcanoes", "created_at": "2024-01-15T00:00:00Z"}]
    assert apply(docs, SearchFilters(source_contains=" ")) == []


# ---------------------------------------------------------------------------
# Highlight — contracts that should hold
# ---------------------------------------------------------------------------


def test_highlight_xss_payload_is_escaped() -> None:
    raw = "<script>alert(1)</script> lava"
    snippet = make_snippet(raw, ["lava"])
    contained = highlight_containing(raw, ["lava"])
    for out in (snippet, contained):
        assert "<script>" not in out
        assert "&lt;script&gt;" in out
        assert "<em>lava</em>" in out


def test_highlight_unicode_term() -> None:
    assert highlight_containing("café latte", ["café"]) == "<em>café</em> latte"
    assert make_snippet("café latte", ["café"]) == "<em>café</em> latte"


def test_highlight_cjk_term() -> None:
    assert "<em>火山</em>" in highlight_containing("火山 と lava", ["火山"])


def test_highlight_prefix_vs_whole_word_are_different() -> None:
    text = "A volcano erupts"
    assert "<em>" not in make_snippet(text, ["volc"])
    assert highlight_containing(text, ["volc"]) == "A <em>volcano</em> erupts"


def test_highlight_unique_terms_dedupes_and_lowercases() -> None:
    assert unique_terms(["Lava", "lava", "  ", "ASH"]) == ["lava", "ash"]


def test_highlight_empty_text_is_empty_string() -> None:
    assert make_snippet("", ["lava"]) == ""
    assert highlight_containing("", ["lava"]) == ""
    assert count_occurrences("", ["lava"]) == [("lava", 0)]


def test_highlight_counts_agree_with_containing_on_plain_words() -> None:
    text = "Calcium is a chemical element. Chemical compounds of calcium."
    terms = ["chem", "calcium"]
    html_out = highlight_containing(text, terms)
    counts = dict(count_occurrences(text, terms))
    assert html_out.count("<em>") == sum(counts.values())


# ---------------------------------------------------------------------------
# Hybrid
# ---------------------------------------------------------------------------


def test_hybrid_whitespace_and_stopword_queries_still_return_top_k(
    searcher: HybridSearcher,
) -> None:
    for query in ("", "   ", "the a an", "!!!"):
        results = searcher.search(query, top_k=3, alpha=1.0)
        assert len(results) == 3
        assert _ids(results) == ["doc-001", "doc-002", "doc-003"]
        assert all(result.bm25_raw == 0.0 for result in results)
        assert all("<em>" not in result.snippet for result in results)


def test_hybrid_top_k_larger_than_corpus_returns_all(searcher: HybridSearcher) -> None:
    results = searcher.search(_QUERY, top_k=50, alpha=0.5)
    assert len(results) == len(SAMPLE_DOCS)


def test_hybrid_unknown_normalization_raises(searcher: HybridSearcher) -> None:
    with pytest.raises(ValueError, match="unknown normalizer"):
        searcher.search(_QUERY, normalization="softmax")


def test_hybrid_rrf_requires_k(searcher: HybridSearcher) -> None:
    with pytest.raises(ValueError, match="rrf requires rrf_k"):
        searcher.search(_QUERY, normalization="rrf")


def test_hybrid_filter_can_return_zero_hits(searcher: HybridSearcher) -> None:
    results = searcher.search(
        _QUERY,
        top_k=6,
        filters=SearchFilters(source_contains="no-such-source"),
    )
    assert results == []


def test_hybrid_source_filter_keeps_matching_docs(searcher: HybridSearcher) -> None:
    results = searcher.search(
        _QUERY,
        top_k=6,
        filters=SearchFilters(source_contains="sample"),
    )
    assert {result.source for result in results} == {"sample"}
    assert len(results) == len(SAMPLE_DOCS)


def test_hybrid_title_only_hit_has_no_snippet_mark(
    searcher: HybridSearcher,
) -> None:
    results = searcher.search("volcanoes", top_k=6, alpha=1.0)
    assert results[0].doc_id == "doc-001"
    assert results[0].bm25_raw > 0.0
    # snippets are built from body text only, and the body says "volcano".
    assert "<em>" not in results[0].snippet


def test_hybrid_scores_are_finite_and_sorted(searcher: HybridSearcher) -> None:
    results = searcher.search(_QUERY, top_k=6, alpha=0.4, normalization="z_score")
    scores = [result.hybrid_score for result in results]
    assert scores == sorted(scores, reverse=True)
    for result in results:
        for value in (
            result.bm25_raw,
            result.vector_raw,
            result.bm25_norm,
            result.vector_norm,
            result.hybrid_score,
        ):
            assert np.isfinite(value)
        assert 0.0 <= result.bm25_norm <= 1.0
        assert 0.0 <= result.vector_norm <= 1.0


def test_hybrid_missing_doc_metadata_does_not_crash(
    fake_embedder: FakeEmbedder,
) -> None:
    docs = list(SAMPLE_DOCS)
    bm25 = BM25Index.build(docs)
    ids = [doc["doc_id"] for doc in docs]
    vector = VectorIndex.build(ids, fake_embedder.encode([doc["text"] for doc in docs]))
    searcher = HybridSearcher(bm25, vector, fake_embedder, {})
    results = searcher.search(_QUERY, top_k=2)
    assert len(results) == 2
    assert results[0].title == ""
    assert results[0].snippet == ""


def test_hybrid_candidate_pool_drops_tied_docs_past_50(
    fake_embedder: FakeEmbedder,
) -> None:
    docs = [
        {
            "doc_id": f"d{index:03d}",
            "title": "Same",
            "text": "identical text for every document here",
            "source": "s",
            "created_at": "2024-01-01T00:00:00Z",
        }
        for index in range(1, 61)
    ]
    results = _searcher(docs, fake_embedder).search("identical", top_k=50, alpha=1.0)
    returned = {result.doc_id for result in results}
    assert len(results) == 50
    assert "d060" not in returned
    assert "d001" in returned


def test_hybrid_minmax_and_zscore_keep_same_top_doc(
    searcher: HybridSearcher,
) -> None:
    minmax = searcher.search(_QUERY, top_k=1, normalization="min_max")
    zscored = searcher.search(_QUERY, top_k=1, normalization="z_score")
    fused = searcher.search(_QUERY, top_k=1, normalization="rrf", rrf_k=60)
    assert minmax[0].doc_id == zscored[0].doc_id == fused[0].doc_id == "doc-001"


# ---------------------------------------------------------------------------
# Schema / request validation
# ---------------------------------------------------------------------------


def test_schema_whitespace_query_is_accepted() -> None:
    req = SearchRequest(query="   ")
    assert req.query == "   "


def test_schema_500_char_query_is_accepted() -> None:
    req = SearchRequest(query="x" * 500)
    assert len(req.query) == 500


def test_schema_accepts_date_only_filter() -> None:
    req = SearchRequest(query="lava", filters={"created_to": "2024-01-15"})
    assert req.filters is not None
    assert req.filters.created_to == "2024-01-15"


def test_schema_rejects_blank_created_from() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(query="lava", filters={"created_from": "not-a-date"})


# ---------------------------------------------------------------------------
# HTTP API
# ---------------------------------------------------------------------------


def test_api_sql_and_xss_queries_do_not_500(client: TestClient) -> None:
    payloads = [
        {"query": "'; DROP TABLE requests; --"},
        {"query": "<script>alert(1)</script>"},
        {"query": "lava.*+?[a-z]"},
        {"query": "café 火山"},
        {"query": "x" * 500},
        {"query": "x"},
        {"query": "   "},
        {"query": "the a an"},
    ]
    for payload in payloads:
        resp = client.post("/search", json=payload)
        assert resp.status_code == 200, payload
        body = resp.json()
        assert "request_id" in body
        assert body["took_ms"] >= 0
        assert isinstance(body["results"], list)


def test_api_request_ids_are_unique(client: TestClient) -> None:
    seen: set[str] = set()
    for _ in range(5):
        resp = client.post("/search", json={"query": "lava", "top_k": 1})
        assert resp.status_code == 200
        request_id = resp.json()["request_id"]
        assert request_id not in seen
        seen.add(request_id)


def test_api_source_filter_and_zero_results(client: TestClient) -> None:
    kept = client.post(
        "/search",
        json={
            "query": "lava",
            "top_k": 6,
            "min_vector_score": 0,
            "filters": {"source_contains": "sample"},
        },
    )
    assert kept.status_code == 200
    assert len(kept.json()["results"]) == 6

    empty = client.post(
        "/search",
        json={"query": "lava", "top_k": 6, "filters": {"source_contains": "wikipedia"}},
    )
    assert empty.status_code == 200
    assert empty.json()["results"] == []


def test_api_created_range_keeps_early_docs(client: TestClient) -> None:
    resp = client.post(
        "/search",
        json={
            "query": "lava",
            "top_k": 6,
            "min_vector_score": 0,
            "filters": {
                "created_from": "2024-01-15T00:00:00Z",
                "created_to": "2024-01-17T00:00:00Z",
            },
        },
    )
    assert resp.status_code == 200
    ids = {row["doc_id"] for row in resp.json()["results"]}
    assert "doc-001" in ids
    assert "doc-003" in ids
    assert "doc-006" not in ids


def test_api_zscore_and_minmax_both_200(client: TestClient) -> None:
    for name in ("minmax", "zscore", "rrf"):
        payload: dict[str, object] = {
            "query": "lava",
            "top_k": 3,
            "normalization": name,
            "min_vector_score": 0,
        }
        if name == "rrf":
            payload["rrf_k"] = 60
        resp = client.post(
            "/search",
            json=payload,
        )
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 3


def test_api_document_prefix_query_highlights(client: TestClient) -> None:
    resp = client.get("/documents/doc-001", params={"q": "volc"})
    assert resp.status_code == 200
    body = resp.json()
    assert "<em>volcano</em>" in body["highlighted_text"]
    by_term = {row["term"]: row["count"] for row in body["occurrences"]}
    assert by_term["volc"] >= 1


def test_api_document_stopword_query_has_no_marks(client: TestClient) -> None:
    resp = client.get("/documents/doc-001", params={"q": "the a an"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["occurrences"] == []
    assert "<em>" not in body["highlighted_text"]


def test_api_document_escapes_html_in_body(client: TestClient) -> None:
    resp = client.get("/documents/doc-001", params={"q": "<script>"})
    assert resp.status_code == 200
    assert "<script>" not in resp.json()["highlighted_text"]


def test_api_extra_field_is_422(client: TestClient) -> None:
    resp = client.post("/search", json={"query": "lava", "unknown": True})
    assert resp.status_code == 422


def test_api_results_never_contain_raw_angle_brackets_from_corpus(
    client: TestClient,
) -> None:
    resp = client.post("/search", json={"query": "<script> lava", "top_k": 6})
    assert resp.status_code == 200
    for row in resp.json()["results"]:
        assert "<script>" not in row["snippet"]


# ---------------------------------------------------------------------------
# Bugs — assert the behaviour a caller should be able to rely on.
# Marked xfail(strict=True) so the suite stays green until someone fixes
# the named source file; an unexpected pass will fail the run.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="BUG: make_snippet IndexError when window is shorter than a match",
)
def test_bug_snippet_tiny_window_does_not_crash() -> None:
    """window shorter than the match must not raise; default search uses 240."""
    for window in (0, 1, 3):
        out = make_snippet("hello lava now", ["lava"], window=window)
        assert isinstance(out, str)


@pytest.mark.xfail(
    strict=True,
    reason="BUG: make_snippet IndexError when window is negative",
)
def test_bug_snippet_negative_window_does_not_crash() -> None:
    out = make_snippet("hello lava now", ["lava"], window=-1)
    assert isinstance(out, str)


@pytest.mark.xfail(
    strict=True,
    reason="BUG: highlight wraps 'amp' inside the escaped &amp; entity",
)
def test_bug_highlight_does_not_break_ampersand_entity() -> None:
    out = highlight_containing("rock & lava", ["amp"])
    assert "&<em>amp</em>;" not in out
    assert "<em>" not in out
    assert "&amp;" in out


@pytest.mark.xfail(
    strict=True,
    reason="BUG: make_snippet wraps 'amp' inside the escaped &amp; entity",
)
def test_bug_snippet_does_not_break_ampersand_entity() -> None:
    out = make_snippet("rock & lava", ["amp"])
    assert "&<em>amp</em>;" not in out
    assert "<em>" not in out


@pytest.mark.xfail(
    strict=True,
    reason="BUG: highlight wraps 'lt'/'quot' inside escaped HTML entities",
)
def test_bug_highlight_does_not_break_lt_and_quot_entities() -> None:
    lt = highlight_containing("a < b", ["lt"])
    quot = highlight_containing('say "hi"', ["quot"])
    assert "&<em>lt</em>;" not in lt
    assert "&<em>quot</em>;" not in quot
    assert "<em>" not in lt
    assert "<em>" not in quot


@pytest.mark.xfail(
    strict=True,
    reason="BUG: highlight_containing marks 'amp' but count_occurrences does not",
)
def test_bug_highlight_and_counts_agree_on_ampersand_text() -> None:
    text = "rock & lava"
    html_out = highlight_containing(text, ["amp"])
    counts = dict(count_occurrences(text, ["amp"]))
    assert ("<em>" in html_out) == (counts.get("amp", 0) > 0)


@pytest.mark.xfail(
    strict=True,
    reason="BUG: date-only created_to excludes same-day ISO timestamps",
)
def test_bug_date_only_created_to_includes_that_calendar_day() -> None:
    doc = {
        "doc_id": "x",
        "source": "wiki",
        "created_at": "2024-01-15T00:00:00Z",
    }
    assert SearchFilters(created_to="2024-01-15").matches(doc)


@pytest.mark.xfail(
    strict=True,
    reason="BUG: API created_to=YYYY-MM-DD drops docs from that day",
)
def test_bug_api_date_only_created_to_keeps_same_day_doc(client: TestClient) -> None:
    resp = client.post(
        "/search",
        json={
            "query": "volcano",
            "top_k": 6,
            "filters": {"created_to": "2024-01-15"},
        },
    )
    assert resp.status_code == 200
    ids = {row["doc_id"] for row in resp.json()["results"]}
    assert "doc-001" in ids
