"""Sentence splitting for ingest, including a later sentence-split option."""

from __future__ import annotations

import re

_END_PUNCT = frozenset(".!?")
_CLOSERS = frozenset("\"')]")

_TITLE_ABBREVS = frozenset(
    {
        "dr",
        "mr",
        "mrs",
        "ms",
        "prof",
        "sr",
        "jr",
        "st",
        "vs",
        "etc",
        "inc",
        "ltd",
        "corp",
        "co",
        "gen",
        "col",
        "capt",
        "rev",
        "sgt",
        "hon",
        "no",
        "vol",
        "fig",
        "al",
    }
)
_DOTTED_ABBREVS = frozenset(
    {
        "e.g",
        "i.e",
        "a.m",
        "p.m",
        "n.b",
        "u.s",
        "u.k",
        "u.s.a",
        "e.u",
        "d.c",
        "ph.d",
        "m.d",
        "b.a",
        "m.a",
    }
)
_DOTTED_ACRONYM_RE = re.compile(r"(?:[A-Za-z]\.)+[A-Za-z]$")


def _token_before_period(text: str, period_index: int) -> str:
    index = period_index - 1
    while index >= 0 and (text[index].isalnum() or text[index] == "."):
        index -= 1
    return text[index + 1 : period_index]


def _is_abbreviation(token: str) -> bool:
    lowered = token.lower()
    if lowered in _TITLE_ABBREVS or lowered in _DOTTED_ABBREVS:
        return True
    if _DOTTED_ACRONYM_RE.fullmatch(token):
        return True
    return len(token) == 1 and token.isalpha()


def _is_sentence_end(text: str, punct_start: int, after: int) -> bool:
    if after < len(text) and not text[after].isspace():
        return False
    index = after
    while index < len(text) and text[index].isspace():
        index += 1
    at_end = index >= len(text)
    if text[punct_start] in "!?":
        return True
    token = _token_before_period(text, punct_start)
    if _is_abbreviation(token):
        return False
    if at_end:
        return True
    nxt = text[index]
    return nxt.isupper() or nxt in "\"'(["


def split_sentences(text: str) -> list[str]:
    """Split ``text`` into sentences, keeping Dr. / U.S. / e.g. as one unit."""
    stripped = text.strip()
    if not stripped:
        return []
    sentences: list[str] = []
    start = 0
    length = len(stripped)
    index = 0
    while index < length:
        if stripped[index] in _END_PUNCT:
            after = index + 1
            while after < length and stripped[after] in _END_PUNCT:
                after += 1
            while after < length and stripped[after] in _CLOSERS:
                after += 1
            if _is_sentence_end(stripped, index, after):
                piece = stripped[start:after].strip()
                if piece:
                    sentences.append(piece)
                start = after
                index = after
                continue
        index += 1
    tail = stripped[start:].strip()
    if tail:
        sentences.append(tail)
    return sentences
