from __future__ import annotations

from app.index.chunk import chunk_document, estimate_tokens


def test_empty_text_yields_no_chunks() -> None:
    assert chunk_document("", max_tokens=100) == []
    assert chunk_document("   ", max_tokens=100) == []


def test_short_doc_is_a_single_chunk() -> None:
    text = "Lava is hot. Ash is grey."
    assert chunk_document(text, max_tokens=100) == ["Lava is hot. Ash is grey."]


def test_packs_consecutive_sentences_until_budget() -> None:
    text = "One two three. Four five six. Seven eight nine."
    # ~4 tokens per sentence; a 5-token budget forces one sentence per chunk.
    chunks = chunk_document(text, max_tokens=5)
    assert chunks == ["One two three.", "Four five six.", "Seven eight nine."]


def test_whole_sentences_are_never_split() -> None:
    long_sentence = "word " * 50
    text = f"{long_sentence.strip()}. Short tail here."
    chunks = chunk_document(text, max_tokens=5)
    # The long sentence overflows but stays intact as its own chunk.
    assert chunks[0].startswith("word word")
    assert "Short tail here." in chunks[-1]
    assert all(chunk.strip() for chunk in chunks)


def test_estimate_tokens_scales_with_words() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("one") >= 1
    assert estimate_tokens("one two three four") > estimate_tokens("one two")
