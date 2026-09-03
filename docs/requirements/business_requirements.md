# Business requirements

## Purpose (s1)

This assignment validates claimed experience with (a) hybrid search pipelines (BM25 + semantic) and (b) building KPI dashboards. You will deliver a fully working, end-to-end system that runs on a CPU-only machine and can be brought up via a single shell script (s1).

A key requirement is transparent, incremental use of Codex (or similar coding assistant): you must provide granular, step-by-step instructions to Codex and retain a full prompt/response log. Blanket prompts are disallowed (s1).

## What this validates (s2)

- Hybrid retrieval (lexical + semantic) implementation and tuning (s2)
- Production-style API design, logging, metrics, tests, and evaluation (s2)
- Frontend dashboard development and data visualization (s2)
- Debugging skill: induce failures, diagnose, and recover cleanly (s2)
- Reproducibility: one-command setup + run on CPU (Linux/macOS) (s2)

## What “done” looks like (s12)

Evaluation rubric (100 points) (s12):

| Category | What we look for | Points |
| --- | --- | ---: |
| Hybrid retrieval correctness | BM25 + vector + clear normalization + explainable scoring (s12) | 20 |
| Engineering quality | Clean structure, typing, error handling, readability (s12) | 15 |
| Reproducibility | up.sh works; minimal steps; no hidden dependencies (s12) | 15 |
| Evaluation rigor | qrels, metrics, 5+ experiments, results tracked and visualized (s12) | 15 |
| Dashboard usefulness | KPI panels, query analytics, eval trends, debug view (s12) | 10 |
| Observability | Structured logs, metrics endpoint, traceable failures (s12) | 10 |
| Testing | Meaningful unit + contract tests; catches regressions (s12) | 10 |
| Codex protocol | Granular prompts, mapped to commits, clear edits/ownership (s12) | 5 |

## Submission requirements (s11)

- Public GitHub repo OR zipped folder (s11)
- >= 15 meaningful commits; each commit message describes what changed and what was validated (s11)
- Short screen recording (5–8 minutes): up.sh, search, dashboard KPIs, at least one break/fix scenario (s11)
- README includes: how to run, how to run tests, how to run eval (s11)
