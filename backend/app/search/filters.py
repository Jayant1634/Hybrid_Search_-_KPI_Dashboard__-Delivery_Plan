"""Pre-ranking filters over document metadata.

``SearchFilters`` captures the optional constraints a caller can put on the
candidate set before scoring: a substring the ``source`` must contain and an
inclusive ``created_at`` range. ``apply`` keeps only the docs that satisfy every
set constraint. Timestamps are compared lexically, which is correct for the
ISO-8601 ``created_at`` values we store.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchFilters:
    """Optional pre-ranking constraints; ``None`` means "do not filter"."""

    source_contains: str | None = None
    created_from: str | None = None
    created_to: str | None = None

    def matches(self, doc: Mapping[str, str]) -> bool:
        """Return whether ``doc`` satisfies every set constraint."""
        if self.source_contains:
            if self.source_contains not in doc.get("source", ""):
                return False
        created_at = doc.get("created_at", "")
        if self.created_from and created_at < self.created_from:
            return False
        if self.created_to and created_at > self.created_to:
            return False
        return True


def apply(
    docs: Iterable[Mapping[str, str]], filters: SearchFilters
) -> list[Mapping[str, str]]:
    """Return the docs from ``docs`` that satisfy ``filters``."""
    return [doc for doc in docs if filters.matches(doc)]
