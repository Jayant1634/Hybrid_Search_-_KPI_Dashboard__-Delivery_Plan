"""Vector index over unit-length embeddings using faiss IndexFlatIP.

Vectors are assumed L2-normalised, so inner product equals cosine similarity.
"""

from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from numpy.typing import NDArray

_INDEX_FILE = "index.faiss"
_DOC_IDS_FILE = "doc_ids.json"


class VectorIndex:
    """In-memory cosine-similarity index keyed by ``doc_id``."""

    def __init__(self, doc_ids: list[str], index: faiss.Index) -> None:
        self._doc_ids = doc_ids
        self._index = index

    @property
    def dimension(self) -> int:
        return int(self._index.d)

    @classmethod
    def build(cls, doc_ids: list[str], vectors: NDArray[np.float32]) -> VectorIndex:
        """Build an index from ``doc_ids`` and a matching ``(n, dim)`` matrix."""
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim != 2:
            raise ValueError(f"vectors must be 2-D, got {matrix.ndim} dimensions")
        if matrix.shape[0] != len(doc_ids):
            raise ValueError(
                "doc_ids and vectors length mismatch: "
                f"{len(doc_ids)} != {matrix.shape[0]}"
            )
        if matrix.shape[0] == 0:
            raise ValueError("cannot build VectorIndex from an empty corpus")
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        return cls(list(doc_ids), index)

    def query(
        self, vector: NDArray[np.float32], k: int
    ) -> list[tuple[str, float]]:
        """Return ``(doc_id, score)`` for the ``k`` nearest docs, score desc."""
        row = np.asarray(vector, dtype=np.float32).reshape(1, -1)
        if row.shape[1] != self.dimension:
            raise ValueError(
                f"query vector dimension {row.shape[1]} "
                f"does not match index dimension {self.dimension}"
            )
        k = min(k, len(self._doc_ids))
        scores, indices = self._index.search(row, k)
        results: list[tuple[str, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            results.append((self._doc_ids[idx], float(score)))
        return results

    def save(self, folder: Path | str) -> None:
        """Write the faiss index and doc ids into ``folder``."""
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(folder / _INDEX_FILE))
        (folder / _DOC_IDS_FILE).write_text(
            json.dumps(self._doc_ids), encoding="utf-8"
        )

    @classmethod
    def load(cls, folder: Path | str) -> VectorIndex:
        """Load an index previously written by :meth:`save`."""
        folder = Path(folder)
        index = faiss.read_index(str(folder / _INDEX_FILE))
        doc_ids = json.loads((folder / _DOC_IDS_FILE).read_text(encoding="utf-8"))
        return cls(list(doc_ids), index)
