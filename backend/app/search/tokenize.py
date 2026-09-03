"""Tokenize text for search: lowercase words, drop single chars and stopwords."""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"\w+")

STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "if",
        "of",
        "to",
        "in",
        "on",
        "at",
        "by",
        "for",
        "with",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "he",
        "she",
        "they",
        "we",
        "you",
        "his",
        "her",
        "their",
        "not",
        "from",
        "into",
    }
)


def tokenize(text: str) -> list[str]:
    """Lowercase, split on ``\\w+``, drop single-char tokens and stopwords."""
    tokens: list[str] = []
    for match in _WORD_RE.finditer(text.lower()):
        token = match.group()
        if len(token) == 1:
            continue
        if token in STOPWORDS:
            continue
        tokens.append(token)
    return tokens
