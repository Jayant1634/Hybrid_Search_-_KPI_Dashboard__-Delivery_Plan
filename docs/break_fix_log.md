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

- break was env-only (`HSS_EMBEDDING_MODEL` in `backend/.env`); not a git commit
- `fa2cbe7` `fix: catch embedding model mismatch at startup`

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

`CREATE TABLE IF NOT EXISTS` is a no-op when the table already exists. Adding
`client_id` to the create statement and to `insert_request` updated only the
code, not `data/hss.sqlite`. The on-disk `requests` table stayed on the v1
shape (no `client_id`). Middleware swallows the persist failure so `/search`
still 200s; `burst.py` does not, so the KPI load-test 500s.

### Fix

Replace the create-if-not-exists block with numbered SQL migrations in
`backend/app/storage/migrations/`:

- `001_initial.sql` — the v1 schema (three tables; `requests` without
  `client_id`), still `CREATE TABLE IF NOT EXISTS` so it is a no-op on the
  already-created production tables;
- `002_add_client_id.sql` — `ALTER TABLE requests ADD COLUMN client_id TEXT
  NOT NULL DEFAULT ''` (a NOT NULL add needs a default).

`db.py` keeps a `schema_version(version, applied_at)` table. `migrate()`
discovers `NNN_*.sql`, applies every file above the current version, each in
its own transaction (`BEGIN` / `COMMIT`, `ROLLBACK` on failure), and records
the version in the same transaction. Re-running is a no-op.
`init_schema()` just calls `migrate()`, so lifespan in `main.py` is unchanged.

Documented in `docs/architecture.md` (SQLite section).

### How I verified

The three new tests in `test_db.py`:

- a fresh db ends at version 2 with the `client_id` column;
- a db built from `001` only upgrades and takes an insert;
- running `migrate` twice does nothing.

```
tests/test_db.py + tests/test_repo.py: 19 passed in 0.29s
full suite: 327 passed, 8 xfailed
```

Against the live `data/hss.sqlite`: migrated to version 2, `client_id` added,
all 175 existing rows preserved, second `migrate()` a no-op.
`POST /search` persisted (175 → 176). `POST /api/dashboard/kpi/load-test`
returned 200 (`sent` 3 / `ok` 3 / `failed` 0) instead of 500.

### Commits

- `1d31038` `break: add requests.client_id without migrating existing sqlite`
- `d3006e5` `fix: replace create-if-not-exists with numbered sqlite migrations and schema_version`

## Scenario C: Hybrid scoring regression (s9.3)

### What I broke

Removed the equal-scores guard from `min_max` in
`backend/app/search/normalize.py`. When every score in the candidate pool is
the same (zero spread), the function used to return `1.0` for each doc. After
the break it divides by `high - low == 0` and produces NaN.

### What happened

The labelled paraphrases (q30–q33) still have lexical hits, so they did not
trip the bug. A query with no word overlap (`fnord xyzzy qwertyplugh`) does:
every BM25 raw score is `0.0`, then `bm25_norm` and `hybrid_score` become NaN.

Numpy warning:

```
D:\Kearney\backend\app\search\normalize.py:29: RuntimeWarning: invalid value encountered in divide
  scaled = (values - low) / spread
```

In-process search (NaNs):

```
cbcc5908a5bc bm25_raw 0.0 bm25_norm nan hybrid nan
8d68e7e11e32 bm25_raw 0.0 bm25_norm nan hybrid nan
0bfd9125ac29 bm25_raw 0.0 bm25_norm nan hybrid nan
bdf984cf6c4a bm25_raw 0.0 bm25_norm nan hybrid nan
7d4a0de39e3b bm25_raw 0.0 bm25_norm nan hybrid nan
```

`POST /search` 200, `request_id` `6f7d4fbd09354e16b0cf260dfb7eaf9d`. JSON
serializes those NaNs as `null`:

```
"bm25_score":0.0,"bm25_norm":null,"hybrid_score":null
```

Unit-level constant input after the break:

```
{'a': nan, 'b': nan, 'c': nan}
```

Eval with `--tag broken-minmax` (alpha 0.3, minmax, MiniLM). Bad csv row:

```
2026-09-05T09:12:28.949172+00:00,d3006e5,broken-minmax,0.3,minmax,all-MiniLM-L6-v2,,0.8561525967885509,0.8214646464646465,0.9772727272727273,33
```

```
eval: n=33 ndcg10=0.8562 recall10=0.8215 mrr10=0.9773 -> data/metrics/experiments.csv
```

Means stayed finite because the 33 eval queries still have BM25 spread, so
ranking was not all-NaN. Phase 14 `alpha-0.3` was nDCG 0.8588 / recall 0.8265
/ MRR 0.9773.

Constant-score tests failed:

```
FAILED tests/test_normalize.py::test_min_max_constant_scores_all_one
AssertionError: assert {'a': nan, 'b': nan} == {'a': 1.0, 'b': 1.0}
FAILED tests/test_search_edgecases.py::test_normalize_single_score_is_one
AssertionError: assert {'a': nan} == {'a': 1.0}
2 failed, 7 passed, 4 warnings in 1.89s
```

### Root cause

Min-max is `(score - min) / (max - min)`. A no-overlap query puts `0.0` on
every BM25 candidate, so the denominator is 0. Numpy emits
`RuntimeWarning: invalid value encountered in divide` and every `bm25_norm`
is NaN. Hybrid is `alpha * NaN + (1 - alpha) * vector_norm` → NaN. Sort
then compares NaNs, so rank order is no longer by score.

### Fix

In `normalize.py`, restore the zero-spread guard on both `min_max` and
`z_score`: constant input returns `0.0` for every doc (not `1.0`, which
was treating an all-zero BM25 list as a perfect lexical hit).

In `hybrid.py`, after each side is normalised, replace any non-finite
normalised score with `0.0` and log a warning that includes the query:

```
non-finite normalised score for query %r; replaced with 0
```

### How I verified

Tests first (both failed on the broken code), then the fix.

```
FAILED tests/test_normalize.py::test_constant_input_returns_zeros_for_both_normalisers
AssertionError: assert {'a': nan, 'b': nan} == {'a': 0.0, 'b': 0.0}
FAILED tests/test_hybrid.py::test_no_overlap_query_never_produces_non_finite_score
assert False
 +  where False = <built-in function isfinite>(nan)
2 failed, 2 warnings in 0.35s
```

After the fix (`test_normalize.py` + `test_hybrid.py`):

```
..................                                                       [100%]
18 passed in 0.23s
```

Eval with `--tag fixed-minmax`, same knobs as phase 14 `alpha-0.3`:

```
eval: n=33 ndcg10=0.8562 recall10=0.8215 mrr10=0.9773 -> data/metrics/experiments.csv
```

```
2026-09-05T09:22:06.545385+00:00,d3006e5,fixed-minmax,0.3,minmax,all-MiniLM-L6-v2,none,0.8561525967885509,0.8214646464646465,0.9772727272727273,33
```

Bit-identical to `broken-minmax`. Does not match phase 14 (nDCG 0.8588 /
recall 0.8265). MRR matches. Constant BM25 all-0 vs all-1 would not change
rank order, and the on-disk index was rebuilt 2026-09-04, after the
2026-09-03 phase 14 sweep.

`test_search_edgecases.py::test_normalize_single_score_is_one` still expects
`1.0` for a single score; it now sees `0.0`. That file was not part of the
fix prompt.

### Commits

- `605369d` `break: drop min_max equal-score guard (NaN on constant BM25), fix: map constant scores to 0 and clamp non-finite hybrid norms`
