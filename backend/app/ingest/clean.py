"""Clean raw document text for ingest."""

from __future__ import annotations

import re
import unicodedata

from .split import split_sentences

MIN_TEXT_CHARS = 200
MAX_TEXT_CHARS = 20_000

_REF_MARKER_RE = re.compile(r"\[\d+\]")
_TAIL_RE = re.compile(
    r"(?im)^(?:References|Related pages|Other websites)\s*$",
)
_WHITESPACE_RE = re.compile(r"\s+")


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        if value[0] == '"':
            return inner.replace("\\\\", "\\").replace('\\"', '"')
        return inner.replace("\\\\", "\\").replace("\\'", "'")
    return value


def split_front_matter(raw: str) -> tuple[dict[str, str], str]:
    """Split ``key: value`` front matter between --- markers from the body."""
    lines = raw.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, raw
    closing: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing = index
            break
    if closing is None:
        return {}, raw
    meta: dict[str, str] = {}
    for line in lines[1:closing]:
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        if key:
            meta[key] = _unquote(value.strip())
    body = "\n".join(lines[closing + 1 :]).lstrip("\n")
    return meta, body


def _drop_wiki_tail(text: str) -> str:
    match = _TAIL_RE.search(text)
    if match is None:
        return text
    return text[: match.start()].rstrip()


def _cap_at_sentence(text: str, limit: int = MAX_TEXT_CHARS) -> str:
    if len(text) <= limit:
        return text
    sentences = split_sentences(text)
    if not sentences:
        return text[:limit].rstrip()
    kept: list[str] = []
    size = 0
    for sent in sentences:
        joined_len = len(sent) if not kept else size + 1 + len(sent)
        if joined_len <= limit:
            kept.append(sent)
            size = joined_len
            continue
        if not kept:
            return text[:limit].rstrip()
        if joined_len <= limit + 500:
            kept.append(sent)
        break
    return " ".join(kept)


def clean_text(text: str) -> str:
    """Unicode-normalise, drop refs and wiki tails, collapse whitespace, cap length."""
    normalised = unicodedata.normalize("NFC", text)
    normalised = normalised.replace("\r\n", "\n").replace("\r", "\n")
    without_refs = _REF_MARKER_RE.sub("", normalised)
    without_tail = _drop_wiki_tail(without_refs)
    collapsed = _WHITESPACE_RE.sub(" ", without_tail).strip()
    return _cap_at_sentence(collapsed)


def is_too_short(text: str, min_chars: int = MIN_TEXT_CHARS) -> bool:
    """True when ``text`` is under ``min_chars`` (default 200)."""
    return len(text) < min_chars
