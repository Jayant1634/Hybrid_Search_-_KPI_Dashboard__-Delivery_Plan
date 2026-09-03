"""Fetch Simple English Wikipedia extracts into data/raw markdown files."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

API_URL = "https://simple.wikipedia.org/w/api.php"
LICENSE = "CC BY-SA 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
MIN_EXTRACT_CHARS = 400
SLEEP_SECONDS = 0.5
RETRY_ATTEMPTS = 3
USER_AGENT = "KearneyHSS/0.1 (educational; corpus fetch; python urllib)"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class SeedRow:
    topic: str
    title: str


@dataclass(frozen=True)
class PageExtract:
    title: str
    extract: str
    source: str


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def slugify(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    if not slug:
        raise ValueError(f"empty slug for {value!r}")
    return slug


def article_slug(topic: str, title: str) -> str:
    return f"{slugify(topic)}-{slugify(title)}"


def wiki_source_url(title: str) -> str:
    return "https://simple.wikipedia.org/wiki/" + urllib.parse.quote(
        title.replace(" ", "_"),
        safe="()'_-,.",
    )


def read_seed(path: Path) -> list[SeedRow]:
    rows: list[SeedRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        topic, title = line.split("\t", 1)
        rows.append(SeedRow(topic=topic.strip(), title=title.strip()))
    return rows


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def render_attribution(articles: list[tuple[str, str]]) -> str:
    lines = [
        "These articles come from Simple English Wikipedia and are licensed under CC BY-SA 4.0.",
        (
            "See the license at "
            f"{LICENSE_URL} "
            "for how to credit authors and share adaptations."
        ),
        "",
    ]
    lines.extend(f"{title} {url}" for title, url in articles)
    return "\n".join(lines) + "\n"


def render_markdown(
    *,
    title: str,
    source: str,
    topic: str,
    fetched: str,
    body: str,
) -> str:
    return (
        "---\n"
        f"title: {_yaml_quote(title)}\n"
        f"source: {_yaml_quote(source)}\n"
        f"license: {_yaml_quote(LICENSE)}\n"
        f"topic: {_yaml_quote(topic)}\n"
        f"fetched: {_yaml_quote(fetched)}\n"
        "---\n"
        "\n"
        f"{body.rstrip()}\n"
    )


def _api_url(title: str) -> str:
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "prop": "extracts|info",
        "explaintext": "1",
        "exsectionformat": "plain",
        "redirects": "1",
        "inprop": "url",
        "titles": title,
    }
    return API_URL + "?" + urllib.parse.urlencode(params)


def fetch_extract(title: str) -> PageExtract | None:
    request = urllib.request.Request(
        _api_url(title),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    pages = payload.get("query", {}).get("pages", [])
    if not pages:
        return None
    page = pages[0]
    if page.get("missing"):
        return None
    extract = str(page.get("extract") or "").strip()
    resolved = str(page.get("title") or title)
    source = str(page.get("fullurl") or wiki_source_url(resolved))
    return PageExtract(title=resolved, extract=extract, source=source)


def fetch_with_retry(title: str, attempts: int = RETRY_ATTEMPTS) -> PageExtract | None:
    last_error: BaseException | None = None
    for attempt in range(attempts):
        try:
            page = fetch_extract(title)
            if page is None:
                print(f"skipped: {title} (missing)")
            return page
        except (OSError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(SLEEP_SECONDS)
    print(f"skipped: {title} (failed after {attempts} tries: {last_error})")
    return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Simple English Wikipedia plain-text extracts into data/raw."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Fetch at most N titles from the seed file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, root: Path | None = None) -> int:
    args = parse_args(argv)
    repo = root if root is not None else repo_root()
    raw_dir = repo / "data" / "raw"
    seed_path = raw_dir / "seed_titles.txt"
    if not seed_path.is_file():
        print(f"seed file not found: {seed_path.as_posix()}", file=sys.stderr)
        return 1

    rows = read_seed(seed_path)
    if args.limit is not None:
        rows = rows[: max(args.limit, 0)]

    raw_dir.mkdir(parents=True, exist_ok=True)
    fetched = today_iso()
    wrote = 0
    skipped = 0
    kept: list[tuple[str, str]] = []

    for index, row in enumerate(rows):
        if index > 0:
            time.sleep(SLEEP_SECONDS)
        page = fetch_with_retry(row.title)
        if page is None:
            skipped += 1
            continue
        if len(page.extract) < MIN_EXTRACT_CHARS:
            print(
                f"skipped: {row.title} "
                f"(extract {len(page.extract)} chars, need {MIN_EXTRACT_CHARS})"
            )
            skipped += 1
            continue

        slug = article_slug(row.topic, row.title)
        out_path = raw_dir / f"{slug}.md"
        out_path.write_text(
            render_markdown(
                title=page.title,
                source=page.source,
                topic=row.topic,
                fetched=fetched,
                body=page.extract,
            ),
            encoding="utf-8",
        )
        kept.append((page.title, page.source))
        wrote += 1

    (raw_dir / "ATTRIBUTION.md").write_text(
        render_attribution(kept),
        encoding="utf-8",
    )
    print(f"wrote {wrote}, skipped {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
