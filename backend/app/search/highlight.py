"""Build HTML snippets that highlight query terms inside a longer text.

``make_snippet`` HTML-escapes the source text, finds whole-word matches of the
query terms, then picks the ``window``-wide slice containing the most matches.
Matches are wrapped in ``<em>`` tags and a horizontal ellipsis (``…``) marks any
end that was cut away from the surrounding text. When no term matches we fall
back to the start of the text.
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterable

ELLIPSIS = "\u2026"


def _clip_end(text: str, limit: int) -> int:
    """Return an end index <= ``limit`` that never splits a word in ``text``."""
    if limit >= len(text):
        return len(text)
    if limit <= 0:
        return 0
    # A clean cut lands on whitespace or just after a word.
    if text[limit].isspace() or text[limit - 1].isspace():
        return limit
    # Inside a word: back up to drop the partial trailing word.
    cut = limit
    while cut > 0 and not text[cut - 1].isspace():
        cut -= 1
    return cut


def _snap_start(text: str, index: int, upper: int) -> int:
    """Move ``index`` forward to a word start, never past ``upper``."""
    if index <= 0:
        return 0
    if index >= upper:
        return upper
    if text[index - 1].isspace():
        return index
    cut = index
    while cut < upper and not text[cut].isspace():
        cut += 1
    while cut < upper and text[cut].isspace():
        cut += 1
    return cut


def make_snippet(text: str, terms: Iterable[str], window: int = 240) -> str:
    """Return an HTML snippet of ``text`` highlighting whole-word ``terms``.

    The text is HTML-escaped first, so the result is safe to drop into markup.
    The ``window``-character slice with the most whole-word term matches is
    chosen; matched words are wrapped in ``<em>`` tags and ``…`` marks any cut
    end. With no matches the snippet starts at the beginning of the text.
    """
    escaped = html.escape(text)
    cleaned = [term for term in terms if term and term.strip()]

    matches: list[re.Match[str]] = []
    if cleaned:
        pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(term) for term in cleaned) + r")\b",
            re.IGNORECASE,
        )
        matches = list(pattern.finditer(escaped))

    if not matches:
        end = _clip_end(escaped, window)
        body = escaped[:end]
        if end < len(escaped):
            body = body.rstrip() + ELLIPSIS
        return body

    # Anchor a window at each match start, count matches fully inside it, and
    # keep the earliest window with the highest count.
    best_start = matches[0].start()
    best_count = -1
    best_last = matches[0].end()
    for anchor in matches:
        start = anchor.start()
        stop = start + window
        inside = [m for m in matches if m.start() >= start and m.end() <= stop]
        if len(inside) > best_count:
            best_count = len(inside)
            best_start = start
            best_last = inside[-1].end()

    # Right-align the window on the last covered match so we keep as much
    # leading context as fits, then snap the ends to word boundaries.
    win_start = max(0, best_last - window)
    win_start = _snap_start(escaped, win_start, best_start)
    win_end = _clip_end(escaped, win_start + window)

    included = [
        m for m in matches if m.start() >= win_start and m.end() <= win_end
    ]

    parts: list[str] = []
    cursor = win_start
    for m in included:
        parts.append(escaped[cursor : m.start()])
        parts.append("<em>")
        parts.append(escaped[m.start() : m.end()])
        parts.append("</em>")
        cursor = m.end()
    parts.append(escaped[cursor:win_end])
    body = "".join(parts)

    prefix = ELLIPSIS if win_start > 0 else ""
    suffix = ELLIPSIS if win_end < len(escaped) else ""
    return f"{prefix}{body}{suffix}"
