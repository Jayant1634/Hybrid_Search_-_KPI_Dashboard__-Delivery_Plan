import json
import urllib.parse
import urllib.request
from pathlib import Path

path = Path("data/raw/seed_titles.txt")
rows = []
for line in path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line:
        continue
    topic, title = line.split("\t", 1)
    rows.append((topic, title))

headers = {"User-Agent": "HSS-corpus-check/0.1 (local; seed title validation)"}
missing = []
ok = 0
batch_size = 50
for i in range(0, len(rows), batch_size):
    batch = rows[i : i + batch_size]
    url = "https://simple.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "titles": "|".join(t for _, t in batch),
            "format": "json",
            "redirects": "1",
            "formatversion": "2",
        }
    )
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    query = data.get("query", {})
    normalized = {n["from"]: n["to"] for n in query.get("normalized", [])}
    redir = {r["from"]: r["to"] for r in query.get("redirects", [])}
    pages_by_title = {p["title"]: p for p in query.get("pages", [])}
    for topic, orig in batch:
        current = orig
        current = normalized.get(current, current)
        current = redir.get(current, current)
        page = pages_by_title.get(current) or pages_by_title.get(orig)
        if page is None or page.get("missing"):
            missing.append((topic, orig))
        else:
            ok += 1

topics = [t for t, _ in rows]
from collections import Counter

counts = Counter(topics)
print(f"rows={len(rows)} topics={len(counts)} ok={ok} missing={len(missing)}")
print("topic counts:", dict(counts))
for topic, title in missing:
    print(f"MISSING\t{topic}\t{title}")
