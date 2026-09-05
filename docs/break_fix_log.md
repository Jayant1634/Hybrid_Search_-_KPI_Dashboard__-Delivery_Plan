# Break/fix log

Assignment section 9. Headings only.

## Scenario A: Semantic index mismatch (s9.1)

### What I broke

Set `HSS_EMBEDDING_MODEL=sentence-transformers/paraphrase-albert-small-v2` in
`backend/.env` (the file `run.py` actually loads) without rebuilding the vector
index. The on-disk faiss index was still the one built with `all-MiniLM-L6-v2`.

### What happened

The API started cleanly with the Albert model (`python run.py` from `backend/`,
which loads `.env`): the 768-dim weights loaded and `Application startup complete`
was logged. `GET /health` still reported the old built index:

```
{"status":"ok","version":"0.1.0","commit":"d76276a","index":{"model":"all-MiniLM-L6-v2","dimension":384,"corpus_hash":"sha256:ecbe92d2ed9b56c4edbfc1c75950162fd9df68c02a7ef8e37ffcd3423f926c33","doc_count":759,"built_at":"2026-09-04T21:56:59.778314+00:00"}}
```

`POST /search {"query":"software license agreement","top_k":5}` returned a 500:

```
STATUS 500
REQUEST-ID 5e8afe71ec084eeb8ab94f08f087afd7
BODY {"request_id":"5e8afe71ec084eeb8ab94f08f087afd7","detail":"internal server error"}
```

The persisted error for that request (from the `requests` table):

```
query vector dimension 768 does not match index dimension 384
```

### Root cause

The running embedder (`paraphrase-albert-small-v2`) emits 768-dim vectors, but the
faiss `IndexFlatIP` was built at 384 dims with `all-MiniLM-L6-v2`. `VectorIndex.query`
guards on `row.shape[1] != self.dimension` and raises; the API middleware turns the
unhandled error into a 500 and writes the message to the request row. Startup does
not catch this because nothing at load time compares the embedder dimension against
the index metadata.

### Fix

Move the check to startup so the app refuses to load a mismatched index instead
of failing on the first query. In `config.py` add `HSS_INDEX_ON_MISMATCH`
(`Settings.index_on_mismatch`, default `fail`). In `deps.py`, `SearchService.load`
loads `IndexMetadata` and calls `_reconcile_index(meta, embedder, docs, settings)`
before building the searcher. It compares the built index's `model`/`dimension`
against `settings.embedding_model` and `embedder.dimension`:

- match -> continue;
- mismatch + `HSS_INDEX_ON_MISMATCH=rebuild` -> `build_indexes(...)` in place with
  the current embedder, then load the fresh index;
- mismatch + `fail` (default) -> raise `RuntimeError` naming both models, both
  dimensions, and the rebuild command, e.g.:

```
index/embedder mismatch: index was built with model 'all-MiniLM-L6-v2' (dimension 384) but the loaded embedder is model 'sentence-transformers/paraphrase-albert-small-v2' (dimension 768). Rebuild the index with: python -m app.index (or set HSS_INDEX_ON_MISMATCH=rebuild).
```

### How I verified

Implemented and confirmed both `HSS_INDEX_ON_MISMATCH` modes.

`fail` (default), against the real on-disk MiniLM index (384-dim) with a
768-dim Albert-named embedder and no rebuild:

```
index/embedder mismatch: index was built with model 'all-MiniLM-L6-v2' (dimension 384) but the loaded embedder is model 'sentence-transformers/paraphrase-albert-small-v2' (dimension 768). Rebuild the index with: python -m app.index (or set HSS_INDEX_ON_MISMATCH=rebuild).
```

That `RuntimeError` is raised in `SearchService.load` at startup, before any
`/search` request.

`rebuild`, via `test_mismatch_rebuild_rebuilds_and_loads`: index built as
`model-a`/8-dim, then load with `model-b`/4-dim and `HSS_INDEX_ON_MISMATCH=rebuild`
rewrites metadata to `model-b`/4 and a query succeeds.

```
tests/test_deps.py::test_mismatch_fail_raises_naming_models_and_dims PASSED
tests/test_deps.py::test_mismatch_rebuild_rebuilds_and_loads PASSED
============================== 2 passed in 0.95s ==============================
```

Did not rebuild the real corpus index. To recover a running instance: set
`HSS_EMBEDDING_MODEL` back to the built model (`all-MiniLM-L6-v2`), or rebuild
with `python -m app.index`, or start with `HSS_INDEX_ON_MISMATCH=rebuild`.

### Commits

- `break: reproduce semantic index mismatch (albert vs MiniLM) -> 500 on /search`
- `fix: catch embedder/index mismatch at startup via HSS_INDEX_ON_MISMATCH`

(commit SHAs pending; not yet committed)

## Scenario B: Schema migration break (s9.2)

### What I broke

Added `client_id TEXT NOT NULL` to the `requests` `CREATE TABLE` in
`backend/app/storage/db.py` and to the `INSERT` in `backend/app/storage/repo.py`.
Restarted against the existing `data/hss.sqlite`. `CREATE TABLE IF NOT EXISTS`
does not alter an already-created table, so the on-disk `requests` rows stayed
on the old schema (no `client_id` column; 175 rows).

### What happened

The API reloaded cleanly (`Application startup complete`). Search still returned
results (`POST /search` 200, `took_ms` ~16) but the request row was not written.
`requests` stayed at 175. Server log:

```
failed to persist request row
Traceback (most recent call last):
  File "backend/app/api/middleware.py", line 162, in _persist_search
    insert_request(
  File "backend/app/storage/repo.py", line 71, in insert_request
    cursor = conn.execute(
sqlite3.OperationalError: table requests has no column named client_id
INFO:     127.0.0.1:56500 - "POST /search HTTP/1.1" 200 OK
```

KPI tiles still loaded (`GET /api/dashboard/kpi/summary?window=24h` 200):

```
{"total":149,"p50":512.7699999138713,"p95":1109.0029600076377,"zero_result_count":16,"error_count":5}
```

The new search is missing from those totals. The KPI latency-burst action
(`POST /api/dashboard/kpi/load-test`) 500s because `burst.py` inserts without
swallowing the same column error:

```
STATUS 500
REQUEST-ID f3674cfea44b4d1fbf0ab20ba6714953
BODY {"request_id":"f3674cfea44b4d1fbf0ab20ba6714953","detail":"internal server error"}
```

Screenshot note: KPIs page still shows the existing 24h cards (p50 / p95 /
Total requests / Zero results) and the volume chart; no red banner on first
paint because those GETs do not touch `client_id`. After Search, the new query
does not appear in Top queries or volume. Opening Test latency and firing hits
puts `HTTP 500: {"request_id":"...","detail":"internal server error"}` in the
drawer error banner. No PNG captured this session (no browser tool); this is
the on-screen state against the live Vite tab at `http://localhost:5173/`.

### Root cause

### Fix

### How I verified

### Commits

- `break: add requests.client_id without migrating existing sqlite`

(commit SHA pending)

## Scenario C: Hybrid scoring regression (s9.3)

### What I broke

### What happened

### Root cause

### Fix

### How I verified

### Commits
