"""CPU sentence-transformers embedder behind a small protocol."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

from app.config import load_config

_DEVICE = "cpu"
_BATCH_SIZE = 32

ProgressCallback = Callable[[int, int], None]


@runtime_checkable
class Embedder(Protocol):
    """Encode texts into L2-normalised float32 vectors."""

    dimension: int

    def encode(
        self,
        texts: list[str],
        on_progress: ProgressCallback | None = None,
    ) -> NDArray[np.float32]: ...


class SentenceTransformerEmbedder:
    """sentence-transformers on CPU; model name from ``load_config()``."""

    def __init__(self) -> None:
        from sentence_transformers import SentenceTransformer

        config = load_config()
        model_name = config.embedding_model
        self._model = SentenceTransformer(model_name, device=_DEVICE)
        # Lift the model's default input window (256 for all-MiniLM-L6-v2) up to
        # HSS_MAX_SEQ_LENGTH so a document embedding is not silently truncated at
        # 256 tokens. The transformer still has a hard architectural ceiling
        # (512 positions for MiniLM); values above that are clamped by the model.
        max_seq_length = int(config.max_seq_length)
        if max_seq_length > 0:
            try:
                self._model.max_seq_length = max_seq_length
            except Exception:  # pragma: no cover - defensive, model-specific
                pass
        if hasattr(self._model, "get_embedding_dimension"):
            dimension = self._model.get_embedding_dimension()
        else:
            dimension = self._model.get_sentence_embedding_dimension()
        if dimension is None:
            raise ValueError(f"model {model_name!r} has no sentence embedding dimension")
        self.dimension = int(dimension)

    def encode(
        self,
        texts: list[str],
        on_progress: ProgressCallback | None = None,
    ) -> NDArray[np.float32]:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        rows: list[NDArray[np.float32]] = []
        total = len(texts)
        for start in range(0, total, _BATCH_SIZE):
            batch = texts[start : start + _BATCH_SIZE]
            embeddings = self._model.encode(
                batch,
                batch_size=_BATCH_SIZE,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            rows.append(np.asarray(embeddings, dtype=np.float32))
            if on_progress is not None:
                on_progress(min(start + len(batch), total), total)
        return np.vstack(rows)
