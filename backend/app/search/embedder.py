"""CPU sentence-transformers embedder behind a small protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from app.config import load_config

_DEVICE = "cpu"
_BATCH_SIZE = 32


@runtime_checkable
class Embedder(Protocol):
    """Encode texts into L2-normalised float32 vectors."""

    dimension: int

    def encode(self, texts: list[str]) -> NDArray[np.float32]: ...


class SentenceTransformerEmbedder:
    """sentence-transformers on CPU; model name from ``load_config()``."""

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        model_name = load_config().embedding_model
        self._model = SentenceTransformer(model_name, device=_DEVICE)
        if hasattr(self._model, "get_embedding_dimension"):
            dimension = self._model.get_embedding_dimension()
        else:
            dimension = self._model.get_sentence_embedding_dimension()
        if dimension is None:
            raise ValueError(f"model {model_name!r} has no sentence embedding dimension")
        self.dimension = int(dimension)

    def encode(self, texts: list[str]) -> NDArray[np.float32]:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        embeddings = self._model.encode(
            texts,
            batch_size=_BATCH_SIZE,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(embeddings, dtype=np.float32)
