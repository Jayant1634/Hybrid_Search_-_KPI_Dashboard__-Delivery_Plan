# Decision log

## Template

Context:
Options:
Decision:
Consequences:

## 2026-09-03 — backend/ + editable install

Context:
The brief is inconsistent about layout. §6 shows CLIs as `python -m app.ingest`
(and index, eval) run from the repo root, with `data/` also at the repo root.
§10's suggested tree puts Python under something like `backend/`. A reviewer
must be able to follow the documented commands without rewriting them.

Options:
1. Put the `app` package at the repo root (`./app/`, `./tests/`). Commands
   work with no install, but the root mixes Python, Vite, scripts, and data.
2. A `src/` layout under `backend/` (`backend/src/app`). Clean packaging, but
   `python -m app.ingest` from the root needs PYTHONPATH or an install, and
   the extra `src/` directory is not in the brief.
3. `backend/app/` as package `app`, with `backend/pyproject.toml`, installed
   editable from the root: `pip install -e backend`. `data/` stays at the repo
   root. Config finds the root by walking up to `up.sh` or `.git`.

Decision:
Option 3.

- The brief's commands stay verbatim: `python -m app.ingest`, `python -m app.index`,
  `python -m app.eval` from the repo root after `pip install -e backend`.
- `data/raw`, `data/processed`, `data/index`, `data/eval`, `data/metrics` match
  §6 instead of living under `backend/`.
- Frontend, `up.sh`, and `scripts/` stay at the root; Python code is one folder
  the reviewer can ignore when they are looking at the UI.
- Pytest config lives in `backend/pyproject.toml` (`testpaths = tests`), so
  `python -m pytest` from the backend package still finds `backend/tests`.

Consequences:
`up.sh` and a fresh clone must run `pip install -e backend` or `python -m app.*`
will fail with ModuleNotFoundError. Paths never go through `backend/`;
`config.py` resolves `repo_root` first, then builds `data/...` from that.
Windows uses `.venv/Scripts`, Linux/macOS `.venv/bin`; both work because we
call the venv's Python rather than relying on cwd.

## 2026-09-03 — min-max vs z-score normalisation

Context:
Hybrid scoring is `hybrid = alpha * norm_bm25 + (1 - alpha) * norm_vector`. BM25
and cosine live on different scales, so each side has to be rescaled before the
blend. The assignment wants two strategies and a written reason for the default.

Options:
1. Min-max as default (linear rescale, min -> 0, max -> 1). Z-score as the
   alternative (centre by mean, divide by std, then squash back to 0..1).
2. Z-score as default, min-max as the alternative.
3. Reciprocal rank fusion, which avoids raw scores entirely.

Decision:
Option 1. Default is min-max (`HSS_NORMALISATION=minmax`, search-layer name
`min_max`). Z-score (`zscore` / `z_score`) stays available on `/search` and
on the eval CLI.

Why min-max is the default:
- Bounded in 0..1, so the three score bars on a result are readable and the
  hybrid value is just a weighted average of two unit scores.
- Interpretable: 1 is the best candidate on that side for this query, 0 is the
  worst. A reviewer can check the breakdown without knowing BM25's raw range.
- Cosine on unit vectors is already roughly 0..1; min-max does not distort it
  much. BM25 is the side that actually needs rescaling.

When z-score is better:
- BM25 is heavy-tailed. One very high lexical hit stretches the min-max range,
  so every other BM25 score collapses toward 0 and alpha barely matters.
- Z-score scores relative to the candidate-set mean, so a single outlier does
  not flatten the rest. Use it when the BM25 distribution for a query is
  obviously skewed (many near-zero, one huge hit).

Consequences:
The dashboard and eval default to min-max. Phase 14 still runs alpha 0.5 with
z-score as one of the recorded experiments so we can see whether the skew
case actually moves nDCG. Scenario C is about constant BM25 (all zeros on a
paraphrase query), which is a divide-by-zero in min-max, not a reason to
change the default.

## 2026-09-03 — eval qrels labelling

Context:
Need >= 25 queries with 3–10 relevant docs each for nDCG/Recall/MRR.
Helper only prints top 20; labels have to be human.

Options:
1. Label only from helper top 20
2. Use helper as a pool, skip junk hits, copy ids for paraphrases from the matching lexical topic
3. Let the agent invent qrels from titles alone

Decision:
Option 2. 33 queries (q01–q33). Binary relevant=1. Never marked seed_titles or
ATTRIBUTION. Paraphrases are q30–q33 (volcanoes, computers, WWII, nutrition).
q30–q33 reuse the lexical topic's qrels so a miss in the hybrid top 20 is not
treated as "not relevant".

Consequences:
Eval will not score 1.0. Paraphrases should look worse at alpha=1 than alpha=0.
q32/q33 are the better zero-overlap candidates for Scenario C.

## 2026-09-04 — phase 14, default alpha

Context:
`scripts/run_experiments.sh` ran the FR-21 set: alpha 0 / 0.3 / 0.5 / 0.7 / 1
with minmax, alpha 0.5 with zscore, `paraphrase-albert-small-v2`, and
`--sentence-split`. 8 rows in `data/metrics/experiments.csv`, n=33 each.
Need a default `HSS_DEFAULT_ALPHA` from that sweep.

Options:
1. 0.0 (pure vector). Strong (nDCG 0.8566) but ignores BM25, so hybrid is unused.
2. 0.3. Best of the sweep: nDCG 0.8588, recall 0.8265, MRR 0.9773.
3. 0.5. The previous default. Worse than 0.3 (nDCG 0.8178, recall 0.7739).
4. 0.7 or 1.0. More BM25. Worst numbers; alpha=1 is nDCG 0.6865 because the
   paraphrase queries have almost no lexical overlap.

Decision:
Option 2. Default alpha is 0.3 (`HSS_DEFAULT_ALPHA=0.3` in `.env.example`).
A little BM25 on top of the vectors is the peak; more BM25 pulls lexical
near-misses above the paraphrase hits.

Other rows, for the record:
- zscore at alpha 0.5 matched minmax exactly (nDCG 0.8178). No reason to
  change the phase 8 default.
- Albert at alpha 0.5: nDCG 0.8290, slightly above MiniLM 0.5, below MiniLM 0.3.
  Stay on MiniLM (smaller, already the index default).
- sentence-split at alpha 0.5 matched document-level 0.5 exactly. Keep
  document-level ingest; the extra newlines did not move metrics.

Consequences:
Search and eval without `--alpha` now blend 30% BM25 / 70% vector. Phase 20
Scenario C still uses a paraphrase query; alpha 0.3 will lean on the vector
side there, which is what we want.

## 2026-09-05 — semantic confidence gate

Context:
A contracts-only search for an unmatched query (`Bruce wayne`, `supernova`)
still returned rank 1 with hybrid 1.0000. Word counts were 0. BM25 raw was
0.000. Vector raw was ~0.047. Min-max then mapped both sides to 1.0 because
the candidate pool was all equally weak. The assignment (s6.3) asks for a
ranked `top_k` list with explainable scores. It does not require returning
hits when nothing is relevant. s6.4 / FR-15 even asks the KPI page to track
zero-result queries, which the always-return-`top_k` path never produced
except when a metadata filter wiped the set.

Options:
1. Leave it. Hybrid 1.0 on noise is “best of a bad pool,” but it looks like
   a perfect match and hides the empty-result KPI.
2. Gate on raw vector cosine before normalisation. Drop any candidate whose
   `vector_raw` is below `min_vector_score`. Default 0.2 on `/search` and the
   Search page. 0.0 disables the gate (eval and existing unit tests).
3. Gate on hybrid or BM25 instead. A lexical miss already scores BM25 0;
   the misleading 1.0 comes from normalising that zero pool plus a near-zero
   cosine. Hybrid after min-max cannot tell “confident” from “least bad.”

Decision:
Option 2. `POST /search` now accepts `min_vector_score` (0..1, default 0.2).
`HybridSearcher.search` drops candidates with `vector_raw < min_vector_score`
before min-max / z-score, then ranks what remains. If none remain, the API
returns `results: []` so the Search empty state and KPI zero-result tile can
fire. The Search page exposes a Min vector slider (Off … 1.00), default 0.20.

0.2 sits above the ~0.05 noise floor seen on unmatched contract queries and
below real MiniLM hits (volcano-style queries were ~0.39). Set the slider to
Off (0.00) to recover the old always-return-`top_k` behaviour.

Consequences:
Nonsense queries against contracts now come back empty at the default.
Strong BM25-only hits with a weak vector score are also dropped unless the
user lowers the slider. Eval still calls the searcher without the field, so
the layer default 0.0 leaves nDCG / Recall / MRR unchanged.

## 2026-09-05 — KPI latency burst (Locust + in-process)

Context:
KPI p50/p95 looked thin or wrong because they came from a handful of
sequential `/search` clicks. Needed a way to send many hits at once, a
library for bigger multi-user load, and a written decision for that
testing approach.

Options:
1. Embed Locust (gevent `HttpUser`) inside FastAPI and hit localhost
   `/search`. Same worker, real HTTP.
2. Locust as the CLI/library for multi-user HTTP. KPI button uses an
   in-process concurrent `HybridSearcher.search` burst and persists
   `requests` rows. Cap the burst so one click cannot lock the CPU.
3. Browser `Promise.all` of `/search` only, no Python load tool.

Decision:
Option 2. Locust 2.42.6 is the out-of-process driver
(`locust -f app/loadtest/locustfile.py --host http://127.0.0.1:8000`).
The KPI drawer calls `POST /api/dashboard/kpi/load-test`, which runs N
hybrid searches together, records `latency_ms` (searcher wall time, same
clock as `took_ms`), and lets the existing KPI aggregations recompute.

The first burst cap was 50. That was only a safety default, not an
assignment rule. 50 concurrent searches is too small to judge p95 under
load, so the cap is 200 (minimum still 2, default still 20). Locust
remains the path for longer HTTP soaks.

Results:
- Nested ASGI and Locust-in-process hung or broke pytest (gevent
  monkey-patch). Those paths were dropped.
- `pytest tests/test_loadtest.py tests/test_api_dashboard.py`: 15 passed
  in 3.23s on the first burst (n=4, query `volcano`, 4/4 ok, KPI total
  +4).
- Count 1 stays 422. Count above the cap stays 422.

Consequences:
Burst rows mix with live Search-page rows. Burst latency is searcher
time, not full HTTP middleware time. True HTTP multi-user load stays on
the Locust CLI. Restart the API before using the new route or the new
cap.

## 2026-09-05 — min-max zero-spread maps to 1, not 0

Context:
`min_max` is `(score - min) / (max - min)`. When every score in the pool
is the same, `max - min` is 0 and you cannot divide. The function has to
pick a constant in `0..1` for every doc. After Scenario C that constant
was `0.0` (treat a tied pool as “no information,” so an all-zero BM25
list does not look like a perfect lexical hit). The working copy in
`backend/app/search/normalize.py` now returns `1.0` instead.

That matches the original min-max reading: 1 is the best candidate on
that side for this query. If every candidate is tied, they are all the
best, so they all get 1. Mapping the max of a constant set to 0 was
the wrong end of the range.

Options:
1. Keep `0.0` on zero spread (Scenario C fix). Avoids `bm25_norm=1.0` on
   a no-overlap query, but it says the tied max is the worst score.
2. Map zero spread to `1.0`. Every tied doc is equally the max, so they
   all get 1. Divide-by-zero is still guarded; no NaNs.
3. Map to `0.5`, skip the side, or emit NaN. Midpoint hides “best of
   pool.” NaN already broke ranking once.

Decision:
Option 2. In `min_max`, `if spread == 0.0` returns `{doc_id: 1.0 ...}`.
`z_score` is unchanged: constant input still returns `0.0` because a
zero standard deviation is “no variation,” not “all best.”

The weak-hit problem that first looked like hybrid 1.0000 on nonsense
queries stays on the semantic confidence gate (`min_vector_score`), not
on flipping min-max’s tied max down to 0.

Consequences:
A candidate pool with identical BM25 (or identical vector) scores will
show that side as 1.0 after min-max. Hybrid is then `alpha * 1 +
(1 - alpha) * other_norm` on that side. The docstring on `min_max` still
says zero spread maps to `0.0`. `tests/test_normalize.py` still expects
`0.0` for both normalisers. Neither was updated in this prompt.

## 2026-09-05 — RRF as a third normaliser, k is user input

Context:
Min-max and z-score both rescale raw BM25 / cosine magnitudes. A single
huge lexical hit still stretches min-max and, less often, z-score. The
phase-8 note listed reciprocal rank fusion as option 3 and left it unused.
Needed a rank-only method on `/search` and a written reason, including
what the free parameter `k` is.

Options:
1. Keep only min-max and z-score.
2. Add RRF with a hardcoded `k = 60` (Cormack, Clarke, Buettcher 2009).
3. Add RRF as a third normaliser, but require the caller to supply `k`
   whenever RRF is selected. No product default.

Decision:
Option 3. RRF is available next to min-max and z-score
(`normalization=rrf` / search-layer `rrf`). Default stays min-max.
`k` is request input only (`rrf_k` on `/search`, `--rrf-k` on eval, the
RRF k field on the Search page). It is not filled in by config or code.

Why RRF was added:
- It ignores raw score magnitudes. Rank 1 vs rank 2 is the same whether
  BM25 was 1000 vs 10 or 2 vs 1, so one outlier cannot flatten the list.
- That is the case min-max handles badly and z-score only partly: a
  heavy-tailed BM25 pool.
- Fusion is still `hybrid = alpha * rrf_bm25 + (1 - alpha) * rrf_vector`,
  i.e. weighted RRF, so alpha keeps its meaning.
- The assignment asked for at least two strategies and a reason. RRF is
  the rank-based third method, not a replacement default.

What `k` is:
- Each side is sorted, dense-ranked (ties share a rank), then scored as
  `1 / (k + rank)`. Rank 1 is the best raw score on that side.
- `k` is a rank-smoothing constant, not a top-k cutoff (that is still
  `top_k`).
- Small `k`: top ranks dominate. `k = 0` is pure `1 / rank` (rank 1 = 1,
  rank 2 = 0.5, rank 3 ≈ 0.33).
- Large `k`: `1/(k+1)` and `1/(k+2)` are almost equal, so mid-ranks stay
  competitive and the blend is flatter.
- Papers often use 60. That is a published suggestion, not a hidden
  default here. The user types the integer. `/search` 422s if
  `normalization` is `rrf` and `rrf_k` is missing.

Consequences:
The Search k field appears only when Normalisation is RRF, empty until
typed. Eval with `--normalization rrf` without `--rrf-k` exits 1. KPI
burst still uses config normalisation (minmax unless someone changes
`HSS_NORMALISATION`); if that is ever `rrf`, the burst must be given
`rrf_k` or it refuses. Tied / single-doc RRF pools still map to 1.0 so
the score bars stay readable.



## 2026-09-05 — z-score and RRF constant pools map to 1, not 0

Context:
The previous entry left `z_score` returning `0.0` on a constant set
(zero standard deviation is “no variation”). That diverged from
`min_max`, which already maps zero-spread to `1.0`. A one-doc pool
(`{"a": 3.5}`) and a tied pair both hit that branch, so z-score showed
the only / tied winner as the worst score. RRF has the same one-file
case: rank 1 is `1 / (60 + 1) ≈ 0.016`, which reads as ~0 on the score
bars.

Options:
1. Keep z-score at `0.0` on zero std (previous decision). Consistent
   with “no variation,” inconsistent with min-max and with a single
   surviving hit.
2. Map zero-std / single-rank pools to `1.0` for z-score and RRF, same
   as min-max: every tied doc is equally the best of the pool.
3. Leave RRF at `1/(k+rank)` even for a single rank. Magnitudes stay
   theoretically correct, but a lone survivor looks like a zero.

Decision:
Option 2. `z_score` returns `{doc_id: 1.0 ...}` when `std == 0.0`.
`rrf` returns `{doc_id: 1.0 ...}` when every doc shares rank 1 (one
file or a constant set). Multi-rank RRF is unchanged (`1 / (k + rank)`,
`k=60`). Docstrings and `tests/test_normalize.py` now expect `1.0` for
constant and single-score inputs on all three normalisers.

Consequences:
A one-file or all-tied pool shows 1.0 on min-max, z-score, and RRF.
Hybrid on that side is `alpha * 1 + (1 - alpha) * other_norm` (or the
other way around). The previous entry’s claim that z-score stays at
`0.0` is superseded. The weak-hit problem remains on
`min_vector_score` (lexical matches now bypass that floor).
