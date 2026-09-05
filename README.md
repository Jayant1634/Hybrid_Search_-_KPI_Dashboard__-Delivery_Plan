# Hybrid search + KPI dashboard

CPU-only hybrid search (BM25 + vectors) and a React KPI dashboard. Ingest and index CLIs, a FastAPI service, SQLite logs, and an eval CLI that writes a CSV. Two local processes: API on 8000, Vite on 5173 (proxies to the API).

```mermaid
flowchart LR
  ingest[Ingest CLI] --> index[Index CLI]
  index --> api[FastAPI]
  api --> sqlite[SQLite]
  dash[React dashboard] --> api
  api --> dash
  eval[Eval CLI] --> api
  eval --> dash
```

fresh clone timing: ~12–18 min cold (`./up.sh` on Windows 11: venv + CPU torch/pip + npm ci + ingest + MiniLM index 16.99s for 359 docs / 384-dim); warm restart with artifacts present starts API + UI in under 15s.

## How to run

Needs Python 3.11+, Node 20+, and git. On Windows use Git Bash.

```bash
./up.sh
```

`up.sh` creates `.venv` if missing, installs pinned deps, runs ingest + index only when artifacts are missing, then starts both processes and prints the URLs:

- API: http://127.0.0.1:8000
- UI: http://127.0.0.1:5173

Stop with `./down.sh` or Ctrl+C in the `up.sh` terminal.

Windows-only API process (after the venv exists): `python backend/run.py` from the repo root, or `python run.py` from `backend/`.

## How to run tests

From the repo root, after the venv exists (Linux/macOS `.venv/bin/python`, Windows Git Bash `.venv/Scripts/python.exe`):

```bash
.venv/bin/python -m pytest backend/tests
# Windows Git Bash:
.venv/Scripts/python.exe -m pytest backend/tests
```

Skip tests that load the real embedding model with `-m "not slow"`. Frontend has no test runner; `npm run build --prefix frontend` is the typecheck + production build.

## How to run eval

Run from the repo root with the venv Python (`python` below means `.venv/bin/python` or `.venv/Scripts/python.exe`):

```bash
python -m app.ingest --input data/raw --out data/processed
python -m app.index --input data/processed/docs.jsonl
python -m app.eval --queries data/eval/queries.jsonl --qrels data/eval/qrels.json
```

Eval appends one row to `data/metrics/experiments.csv` (timestamp, commit, tag, alpha, normalization, model, metrics). Optional flags: `--alpha`, `--normalization minmax|zscore`, `--tag`, `--model`.

## Experiments

```bash
./scripts/run_experiments.sh
```

Runs the FR-21 set (alpha sweep, z-score, alternate model, sentence-split) and restores the default ingest + index.

## Break/fix

- Scenario A: Semantic index mismatch — [docs/break_fix_log.md](docs/break_fix_log.md#scenario-a-semantic-index-mismatch-s91)
- Scenario B: Schema migration break — [docs/break_fix_log.md](docs/break_fix_log.md#scenario-b-schema-migration-break-s92)
- Scenario C: Hybrid scoring regression — [docs/break_fix_log.md](docs/break_fix_log.md#scenario-c-hybrid-scoring-regression-s93)

## Deviations

None.

## Docs

- [Architecture](docs/architecture.md)
- [Business requirements](docs/requirements/business_requirements.md)
- [Functional requirements](docs/requirements/functional_requirements.md)
- [Technical requirements](docs/requirements/technical_requirements.md)
- [High-level design](docs/design/high_level_design.md)
- [Low-level design](docs/design/low_level_design.md)
- [Decision log](docs/decision_log.md)
- [Break/fix log](docs/break_fix_log.md)
- [Prompt log](docs/codex_log.md)
