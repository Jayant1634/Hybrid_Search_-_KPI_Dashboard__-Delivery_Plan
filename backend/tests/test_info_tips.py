"""Hover info copy: no inline RRF wall of text, tips wired on every page."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "src"

REQUIRED_KEYS = (
    "topK",
    "alpha",
    "minVector",
    "rrfK",
    "dataset",
    "normalisation",
    "p50",
    "p95",
    "ndcg10",
    "recall10",
    "mrr10",
    "bm25",
    "vector",
    "hybrid",
    "rank",
)

WIRED_PAGES = (
    FRONTEND / "pages" / "SearchPage.tsx",
    FRONTEND / "pages" / "KpisPage.tsx",
    FRONTEND / "pages" / "EvaluationPage.tsx",
    FRONTEND / "pages" / "DebugPage.tsx",
    FRONTEND / "pages" / "SettingsPage.tsx",
    FRONTEND / "components" / "HealthGrid.tsx",
    FRONTEND / "components" / "ResultCard.tsx",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_info_tips_export_required_keys() -> None:
    text = _read(FRONTEND / "infoTips.ts")
    keys = set(re.findall(r"^\s{2}([A-Za-z][A-Za-z0-9]*):", text, flags=re.MULTILINE))
    missing = [key for key in REQUIRED_KEYS if key not in keys]
    assert missing == [], missing
    assert "Score is 1/(k + rank)" in text


def test_search_page_rrf_help_is_hover_not_inline() -> None:
    page = _read(FRONTEND / "pages" / "SearchPage.tsx")
    assert "Score is 1/(k + rank)" not in page
    assert "INFO_TIPS.rrfK" in page
    assert "from '../components/InfoTip'" in page


def test_pages_import_info_tip() -> None:
    for path in WIRED_PAGES:
        source = _read(path)
        assert "InfoTip" in source, path.as_posix()
        assert "INFO_TIPS" in source, path.as_posix()


def test_info_tip_uses_portal_popover() -> None:
    source = _read(FRONTEND / "components" / "InfoTip.tsx")
    assert "createPortal" in source
    assert 'role="tooltip"' in source
    assert "onMouseEnter" in source
