"""BM25 scoring over title + text using rank-bm25."""

from __future__ import annotations

import pickle
from collections.abc import Iterable, Mapping
from pathlib import Path

from rank_bm25 import BM25Okapi

from .tokenize import tokenize

_MODEL_FILE = "bm25.pkl"


class BM25Index:
    """In-memory BM25 index keyed by ``doc_id`` over title + text."""

    def __init__(self, doc_ids: list[str], model: BM25Okapi) -> None:
        self._doc_ids = doc_ids
        self._model = model

    @staticmethod
    def _doc_tokens(doc: Mapping[str, str]) -> list[str]:
        title = doc.get("title", "") or ""
        text = doc.get("text", "") or ""
        return tokenize(f"{title} {text}")

    @classmethod
    def build(cls, docs: Iterable[Mapping[str, str]]) -> BM25Index:
        """Build an index from docs having ``doc_id``, ``title`` and ``text``."""
        doc_ids: list[str] = []
        corpus: list[list[str]] = []
        for doc in docs:
            doc_ids.append(doc["doc_id"])
            corpus.append(cls._doc_tokens(doc))
        if not corpus:
            raise ValueError("cannot build BM25Index from an empty corpus")
        model = BM25Okapi(corpus)
        return cls(doc_ids, model)

    def query(self, text: str, top_k: int | None = None) -> list[tuple[str, float]]:
        """Return ``(doc_id, score)`` sorted by score desc, ties broken by doc_id."""
        tokens = tokenize(text)
        scores = self._model.get_scores(tokens)
        ranked = sorted(
            zip(self._doc_ids, (float(score) for score in scores)),
            key=lambda pair: (-pair[1], pair[0]),
        )
        if top_k is not None:
            ranked = ranked[:top_k]
        return ranked

    def scores_for_all(self, text: str) -> dict[str, float]:
        """Return a ``doc_id -> score`` dict for every doc (for later hybrid step)."""
        tokens = tokenize(text)
        scores = self._model.get_scores(tokens)
        return {
            doc_id: float(score) for doc_id, score in zip(self._doc_ids, scores)
        }

    def save(self, folder: Path | str) -> None:
        """Pickle the model and doc ids into ``folder``."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        payload = {"doc_ids": self._doc_ids, "model": self._model}
        with (folder / _MODEL_FILE).open("wb") as handle:
            pickle.dump(payload, handle)

    @classmethod
    def load(cls, folder: Path | str) -> BM25Index:
        """Load an index previously written by :meth:`save`."""
        folder = Path(folder)
        with (folder / _MODEL_FILE).open("rb") as handle:
            payload = pickle.load(handle)
        return cls(payload["doc_ids"], payload["model"])
