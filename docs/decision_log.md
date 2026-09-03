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