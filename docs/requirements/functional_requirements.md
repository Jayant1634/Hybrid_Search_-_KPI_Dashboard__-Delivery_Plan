# Functional requirements

Source: assignment sections 6 and 7. One FR per bullet. Optional items are marked as in the assignment.

## 6.1 Data ingestion

**FR-01.** Provide a sample corpus of at least 300 documents that is legally redistributable (public domain / open license).
- Section: 6.1
- Check: count documents under `data/raw` (>= 300); confirm the stated license is public domain or open.

**FR-02.** Ingest with `python -m app.ingest --input data/raw --out data/processed`.
- Section: 6.1
- Check: run that command; confirm it completes.

**FR-03.** Normalize into JSONL with fields `doc_id`, `title`, `text`, `source`, `created_at`.
- Section: 6.1
- Check: open `data/processed` JSONL and confirm those fields are present.

**FR-04.** Apply basic preprocessing: whitespace cleanup, optional sentence splitting, and safeguards for extremely long docs.
- Section: 6.1
- Check: inspect ingest output in `data/processed` for cleaned whitespace and length handling.

## 6.2 Indexing

**FR-05.** Build a BM25 index over (title + text); artifacts under `data/index/bm25/`.
- Section: 6.2
- Check: `data/index/bm25/` exists and is non-empty after index.

**FR-06.** Build a vector index using a small sentence-transformers model (CPU); artifacts under `data/index/vector/`.
- Section: 6.2
- Check: `data/index/vector/` exists and is non-empty after index.

**FR-07.** Store index metadata (embedding model name, dimension, corpus hash, build timestamp) to support validation on startup.
- Section: 6.2
- Check: metadata file exists under `data/index/` with those four fields.

**FR-08.** Index with `python -m app.index --input data/processed/docs.jsonl`.
- Section: 6.2
- Check: run that command; confirm it completes.

## 6.3 Hybrid search API

**FR-09.** `GET /health` returns OK + version + commit hash.
- Section: 6.3
- Check: `GET /health`.

**FR-10.** `POST /search` accepts `{query, top_k, alpha, filters}` and returns ranked results with `bm25_score`, `vector_score`, `hybrid_score`, and highlight snippets.
- Section: 6.3
- Check: `POST /search` with those fields; confirm scores and snippets on each result.

**FR-11.** `POST /feedback` logs relevance feedback (optional; bonus).
- Section: 6.3
- Check: `POST /feedback` (skip if not implemented).

**FR-12.** `GET /metrics` returns basic counters and a latency summary (Prometheus-style text acceptable).
- Section: 6.3
- Check: `GET /metrics`.

**FR-13.** Hybrid scoring is explicit and configurable (example: `hybrid = alpha * norm_bm25 + (1-alpha) * norm_vector`); include at least two normalization strategies and justify the choice in `docs/decision_log.md`.
- Section: 6.3
- Check: `POST /search` with two `alpha` values; confirm two normalization strategies exist; confirm the justification is in `docs/decision_log.md`.

## 6.4 Dashboard

**FR-14.** Search page: query box + results list + per-result score breakdown and highlights.
- Section: 6.4
- Check: open the UI Search page (URL printed by `up.sh`) and run a query.

**FR-15.** KPI page: p50/p95 latency, request volume over time, top queries, zero-result queries.
- Section: 6.4
- Check: open the UI KPI page.

**FR-16.** Evaluation page: experiment table + nDCG@10 trend line across runs.
- Section: 6.4
- Check: open the UI Evaluation page.

**FR-17.** Debug page: structured error logs filtered by time range and severity.
- Section: 6.4
- Check: open the UI Debug page.

## 6.5 Evaluation harness

**FR-18.** Create labeled eval data: at least 25 queries, each with 3–10 relevant docs (qrels).
- Section: 6.5
- Check: `data/eval/queries.jsonl` has >= 25 queries; `data/eval/qrels.json` has 3–10 relevant docs per query.

**FR-19.** Eval script: `python -m app.eval --queries data/eval/queries.jsonl --qrels data/eval/qrels.json`.
- Section: 6.5
- Check: run that command; confirm it completes.

**FR-20.** Compute nDCG@10, Recall@10, MRR@10; append to `data/metrics/experiments.csv` with timestamp + git commit.
- Section: 6.5
- Check: after eval, `data/metrics/experiments.csv` has those metrics plus timestamp and git commit.

**FR-21.** Run >= 5 experiments varying alpha, embedding model, or preprocessing; visualize in the dashboard.
- Section: 6.5
- Check: `data/metrics/experiments.csv` has >= 5 rows; Evaluation page shows the trend.

## 6.6 Observability & quality

**FR-22.** Structured JSON logs per request: `request_id`, `query`, `latency_ms`, `top_k`, `alpha`, `result_count`, `error` (if any).
- Section: 6.6
- Check: issue `POST /search`; confirm a JSON log line with those fields.

**FR-23.** Persist query logs and latency into SQLite; include schema in README or `docs/architecture.md`.
- Section: 6.6
- Check: SQLite file exists after requests; schema is documented in `README.md` or `docs/architecture.md`.

**FR-24.** Unit tests for preprocessing, BM25 scoring, vector search, hybrid combination, and API contracts.
- Section: 6.6
- Check: run tests covering those five areas.

**FR-25.** Basic security hygiene: input validation, rate limiting (simple), and no secrets in repo.
- Section: 6.6
- Check: `POST /search` with invalid input; repeat requests to hit the limiter; confirm no secrets are committed.

## 7 End-to-end run requirements

### Repository must include

**FR-26.** `README.md` with architecture overview and 1-minute quickstart.
- Section: 7
- Check: `README.md` exists and contains both.

**FR-27.** `requirements.txt` (or lockfile) with pinned versions.
- Section: 7
- Check: `requirements.txt` or a lockfile exists with pinned versions.

**FR-28.** `up.sh` that sets up the environment, builds indexes (if missing), and launches backend + frontend.
- Section: 7
- Check: `up.sh` exists; run `./up.sh`.

**FR-29.** `down.sh` to stop services cleanly (optional).
- Section: 7
- Check: `down.sh` exists and stops services (skip if not implemented).

### `up.sh` must do, at minimum

**FR-30.** Create/activate local virtual environment (`./.venv`) if missing.
- Section: 7
- Check: after `./up.sh`, `./.venv` exists.

**FR-31.** Install dependencies.
- Section: 7
- Check: `./up.sh` installs dependencies without a separate manual install step.

**FR-32.** Download/prepare sample data (if not present).
- Section: 7
- Check: on a tree without sample data, `./up.sh` produces `data/raw`.

**FR-33.** Run ingest + index only when artifacts are missing.
- Section: 7
- Check: second `./up.sh` with artifacts present does not rebuild; delete artifacts and confirm ingest + index run.

**FR-34.** Start API + UI and print local URLs.
- Section: 7
- Check: `./up.sh` prints local URLs; those URLs respond.
