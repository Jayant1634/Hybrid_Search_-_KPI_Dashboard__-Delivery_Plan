from pathlib import Path

from app.search.bm25 import BM25Index

TOY_CORPUS = [
    {
        "doc_id": "doc-a",
        "title": "Volcano",
        "text": "A volcano erupts lava and ash from magma deep in the earth.",
    },
    {
        "doc_id": "doc-b",
        "title": "Bread",
        "text": "Bread is baked from dough of flour, water, and yeast.",
    },
    {
        "doc_id": "doc-c",
        "title": "Lava rock",
        "text": "Lava cools into volcanic rock after a volcano erupts.",
    },
]


def _order(results: list[tuple[str, float]]) -> list[str]:
    return [doc_id for doc_id, _ in results]


def test_query_ranks_relevant_docs_first() -> None:
    index = BM25Index.build(TOY_CORPUS)
    results = index.query("volcano lava")
    assert _order(results) == ["doc-a", "doc-c", "doc-b"]
    assert results[0][1] >= results[1][1] >= results[2][1]


def test_query_returns_all_docs_with_scores() -> None:
    index = BM25Index.build(TOY_CORPUS)
    results = index.query("bread")
    assert len(results) == 3
    assert results[0][0] == "doc-b"
    assert results[0][1] > 0.0


def test_ties_broken_by_doc_id_for_determinism() -> None:
    index = BM25Index.build(TOY_CORPUS)
    results = index.query("nonexistent term")
    assert all(score == 0.0 for _, score in results)
    assert _order(results) == ["doc-a", "doc-b", "doc-c"]


def test_top_k_limits_results() -> None:
    index = BM25Index.build(TOY_CORPUS)
    results = index.query("volcano lava", top_k=2)
    assert _order(results) == ["doc-a", "doc-c"]


def test_scores_for_all_returns_dict_for_every_doc() -> None:
    index = BM25Index.build(TOY_CORPUS)
    scores = index.scores_for_all("volcano lava")
    assert set(scores) == {"doc-a", "doc-b", "doc-c"}
    assert scores["doc-a"] > scores["doc-b"]
    assert dict(index.query("volcano lava")) == scores


def test_save_load_roundtrip(tmp_path: Path) -> None:
    index = BM25Index.build(TOY_CORPUS)
    folder = tmp_path / "index"
    index.save(folder)
    assert (folder / "bm25.pkl").is_file()

    loaded = BM25Index.load(folder)
    query = "volcano lava"
    assert loaded.query(query) == index.query(query)
