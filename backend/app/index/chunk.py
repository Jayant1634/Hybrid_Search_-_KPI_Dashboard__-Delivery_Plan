"""Pack a document's sentences into embedding-sized chunks.

Sentence-granularity indexing stores one vector per chunk instead of one per
document. Rather than embedding each sentence alone (noisy: "It erupted."), we
greedily pack consecutive whole sentences until the next one would push the
chunk past ``max_tokens``. Every chunk therefore stays inside the model's input
window while, together, the chunks cover the whole file.

Token counts are estimated (``~1.3`` subword tokens per whitespace word) so we
never need to load the real tokenizer at index time.
"""

from __future__ import annotations

import math

from app.ingest.split import split_sentences

_TOKENS_PER_WORD = 1.3


def estimate_tokens(text: str) -> int:
    """Rough subword-token count for ``text`` (never below 1 for real text)."""
    words = len(text.split())
    if words == 0:
        return 0
    return max(1, int(math.ceil(words * _TOKENS_PER_WORD)))


def chunk_document(text: str, *, max_tokens: int) -> list[str]:
    """Split ``text`` into chunks of whole sentences, each ~``max_tokens`` long.

    A single sentence longer than ``max_tokens`` becomes its own chunk (the
    model truncates it); it is never split mid-sentence. Empty input yields an
    empty list.
    """
    budget = max(1, int(max_tokens))
    sentences = split_sentences(text)
    if not sentences:
        stripped = text.strip()
        return [stripped] if stripped else []

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for sentence in sentences:
        sentence_tokens = estimate_tokens(sentence)
        if current and current_tokens + sentence_tokens > budget:
            chunks.append(" ".join(current))
            current = []
            current_tokens = 0
        current.append(sentence)
        current_tokens += sentence_tokens
    if current:
        chunks.append(" ".join(current))
    return chunks
