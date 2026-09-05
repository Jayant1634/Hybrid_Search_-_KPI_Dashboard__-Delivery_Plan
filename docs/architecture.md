# Architecture

CPU-only hybrid search (BM25 + vectors) and a KPI dashboard. Ingest and index CLIs, a FastAPI service, SQLite logs, a React UI, and an eval CLI that writes a CSV. Two processes locally: API on 8000, Vite on 5173 (proxies to the API).

Full picture: [high-level design](design/high_level_design.md).

## SQLite

Copied from [low-level design](design/low_level_design.md).

```sql
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    query TEXT NOT NULL,
    latency_ms REAL,
    top_k INTEGER,
    alpha REAL,
    result_count INTEGER,
    error TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    relevant INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    request_id TEXT
);
```

## Data movement

1. Ingest CLI: `data/raw` → JSONL in `data/processed`.
2. Index CLI: JSONL → BM25 + vector indexes.
3. FastAPI reads those indexes; writes query logs and latency to SQLite.
4. React dashboard talks only to the API (Vite proxy).
5. Eval CLI calls the API and appends `data/metrics/experiments.csv`; the Evaluation page reads that file.

## Docs

- [Business requirements](requirements/business_requirements.md)
- [Functional requirements](requirements/functional_requirements.md)
- [Technical requirements](requirements/technical_requirements.md)
- [High-level design](design/high_level_design.md)
- [Low-level design](design/low_level_design.md)
- [Prompt log](codex_log.md)
