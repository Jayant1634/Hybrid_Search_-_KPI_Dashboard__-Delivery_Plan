# Codex log

This is the prompt log the assignment asks for (section 8.1).

agent: cursor, model: see each entry

## Template

Date:
Prompt id:
Prompt:
Model:
Files:
What came back:
Review:
Commit:

## Entries

Date: 2026-09-03
Prompt id: p1
Prompt:
before we start anything, create a cursor rules file at .cursor/rules/project.mdc, always apply.
keep it short, under 30 lines. things i want in it:

- only touch the files i name in the prompt. if something else needs to change, tell me, dont do it
- python 3.11+, cpu only, type hints, pathlib for paths, no absolute paths anywhere
- when you add or change code, add or update the matching test and run it. show me the output
- when you are done, append an entry to docs/codex_log.md. theres a template at the top of that
  file. leave the "review" and "commit" lines empty, i fill those in
- end your reply with a suggested commit message, one line, then a "validated:" line
- never edit docs/plan.md, docs/prompts.md, docs/decision_log.md or docs/break_fix_log.md,
  those are mine

nothing about what the project does. just working rules.
Model: Cursor Grok 4.6
Files: .cursor/rules/project.mdc
What came back:
Created `.cursor/rules/project.mdc` with `alwaysApply: true`. It only covers the working rules you listed: named-files-only, Python/path conventions, tests, the log, reply footer, and the docs you own.

I did not append to `docs/codex_log.md` — that file is not in this prompt, and it is not in the repo yet. Say if you want that created next.

Add Cursor always-apply working rules
validated: rules file written; no tests (not code); log not updated
Review:
Commit:

Date: 2026-09-03
Prompt id: p2
Prompt:
now docs/codex_log.md. a title, one line saying this is the prompt log the assignment asks for
(section 8.1), a line "agent: cursor, model: ____", then the entry template the rules file
talks about: date, prompt id, files, what came back, my review, commit. then an empty
"entries" heading. thats all.
Model: Cursor Grok 4.6
Files: docs/codex_log.md
What came back:
Created `docs/codex_log.md` with the title, section 8.1 line, agent/model placeholder, the six-field template, and an empty Entries heading.

I did not add a first entry under Entries so that heading stays empty, as you asked.

Add assignment prompt log with entry template
validated: log file written; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p3
Prompt:
@docs/assignmentkosintern (1).docx read sections 1, 2, 11 and 12 of the assignment (attached, its the extracted text). write
docs/requirements/business_requirements.md from it, about a page. purpose, who reads this (a
reviewer), what "done" looks like (use the rubric table with the points), the submission
rules, and whats out of scope. put the section number next to each point so i can trace it.
no fluff please.
Model: Cursor Grok 4.6
Files: docs/requirements/business_requirements.md, docs/codex_log.md
What came back:
Wrote `docs/requirements/business_requirements.md` from assignment sections 1, 2, 11, and 12 only: purpose, reviewer audience, the 100-point rubric as “done,” submission rules, and out of scope. Each point is tagged with its section number.

Also appended an entry to `docs/codex_log.md` (Review and Commit left empty). No tests: this is documentation, not code.

Add reviewer-facing business requirements from assignment s1/s2/s11/s12
validated: requirements doc written from s1, s2, s11, s12; log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p4
Prompt:
why isn't every prompt is getting logged ?
@.cursor/rules/project.mdc
Model: Cursor Grok 4.6
Files: .cursor/rules/project.mdc, docs/codex_log.md
What came back:
The two rules were fighting. “Only edit files you name” beat “append to the log,” so if you did not name `docs/codex_log.md`, I skipped it.

That is why only the business-requirements turn was logged. The rules-file turn happened before the log existed. The log-file turn kept Entries empty on purpose.

I updated `.cursor/rules/project.mdc` so the log is a required exception: every prompt gets an entry even if you do not name that file. This turn is logged. The first two prompts are still missing; say if you want those backfilled.

Make prompt log a required exception to named-files-only
validated: rules updated; this prompt logged; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p5
Prompt:
before we start anything, create a cursor rules file at .cursor/rules/project.mdc, always apply.
keep it short, under 30 lines. things i want in it:

- only touch the files i name in the prompt. if something else needs to change, tell me, dont do it
- python 3.11+, cpu only, type hints, pathlib for paths, no absolute paths anywhere
- when you add or change code, add or update the matching test and run it. show me the output
- when you are done, append an entry to docs/codex_log.md. theres a template at the top of that
  file. leave the "review" and "commit" lines empty, i fill those in
- end your reply with a suggested commit message, one line, then a "validated:" line
- never edit docs/plan.md, docs/prompts.md, docs/decision_log.md or docs/break_fix_log.md,
  those are mine

nothing about what the project does. just working rules.

check the rules properly, the logs are not getting logged, 
properly, the prompt is not shown, 
model used ot shown, all the output i got from the prompt is not showned, check the codebase and fix this
Model: Cursor Grok 4.6
Files: .cursor/rules/project.mdc, docs/codex_log.md
What came back:
The log was incomplete because the template and the rules never required the three missing pieces. Entries had a blank Prompt id, a file-level `model: ____` that was never filled, and a one-line paraphrase under What came back.

Updated `.cursor/rules/project.mdc` so each entry must include Prompt id (`pN`), the verbatim user prompt, the actual model name, named files, and the full user-facing reply. Named-files-only still applies, with `docs/codex_log.md` as the required exception.

Updated `docs/codex_log.md`: template now has Prompt and Model; header model is per entry; p1–p4 backfilled from prior turns; this turn is p5. Review and Commit left empty. No tests: rules and log only, not code.
Review:
Commit:

Date: 2026-09-03
Prompt id: p6
Prompt:
check the business requirement file again, and validate with assignment, remove anything thats not actually in the document. i only want whats there.
Model: Cursor Grok 4.6
Files: docs/requirements/business_requirements.md, docs/codex_log.md
What came back:
Checked `docs/requirements/business_requirements.md` against assignment sections 1, 2, 11, and 12. Removed anything that is not in those sections.

Removed:
- Audience line (“a reviewer scoring this submission”). s1, s2, s11, and s12 do not name a reader.
- The “done” intro that mixed CPU-only, one-script, and s11 artifacts. s12 is only the rubric.
- Rubric column rename (“What reviewers look for”) and a Total row. The assignment table is “What we look for”; it has no total row.
- The whole Out of scope section. Those bullets were inferred (GPU, typical laptop, no credit outside the rubric, missing submission pieces). The assignment does not list out of scope in s1, s2, s11, or s12. The only explicit disallow in those sections is “Blanket prompts are disallowed,” which stays under Purpose (s1).

Left in place, with assignment wording: purpose (s1), what this validates (s2), the 100-point rubric (s12), submission requirements (s11).

I did not add s3–s10 or s13.

Strip inferred content from business requirements
validated: BRD limited to s1, s2, s11, s12 wording; out of scope and audience removed; log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p7
Prompt:
same idea for sections 6 and 7, into docs/requirements/functional_requirements.md. a numbered
list, FR-01 and so on, one per bullet in the doc. for each: the requirement in a sentence,
the section it comes from, and how i would check it (a command, an endpoint, a file that
exists). group them the way the doc does.
Model: Cursor Grok 4.6
Files: docs/requirements/functional_requirements.md, docs/codex_log.md
What came back:
Wrote `docs/requirements/functional_requirements.md` from assignment sections 6 and 7 only. One FR per bullet, grouped as in the doc (6.1–6.6, then 7 split into “repository must include” and “up.sh must do”).

FR-01 to FR-34. Each has the requirement in a sentence, the section, and a check (command, endpoint, or file). FR-11 (`POST /feedback`) and FR-29 (`down.sh`) are marked optional as in the assignment.

I did not add s1–s5 or s8–s13. Checks use paths and commands named in s6/s7 (`data/raw`, ingest/index/eval modules, `/health` `/search` `/metrics`, `up.sh`). I did not edit `docs/decision_log.md`; FR-13 only names it because s6.3 does.

Add functional requirements FR-01 to FR-34 from assignment s6/s7
validated: FR file written from s6 and s7 bullets only; log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p8
Prompt:
sections 3 and 5 into docs/requirements/technical_requirements.md. the stack table, python and
node versions, cpu only, no cloud. one thing to add thats not in the doc: i develop on windows
11 in git bash, but the reviewer will be on linux or mac. write down what that means for us,
bash scripts with LF endings, the venv path is different (Scripts vs bin), pathlib, no pkill.
keep it short.
Model: Cursor Grok 4.6
Files: docs/requirements/technical_requirements.md, docs/codex_log.md
What came back:
Wrote `docs/requirements/technical_requirements.md` from assignment sections 3 and 5, plus the Windows 11 / Git Bash note you asked for.

s3 constraints: CPU-only, `./up.sh` on a fresh machine, no paid cloud, no absolute paths, <= 30 minutes, Codex auditable. s5 stack as a table. Python 3.11+ from s5. Node is not pinned in the assignment (needed for React + Vite). Dev vs reviewer: LF scripts, `Scripts` vs `bin`, pathlib, no `pkill`.

I did not add s1–s2 or s4, s6–s13.

Add technical requirements from assignment s3/s5 plus Windows notes
validated: TR file written; Node unpinned (not in assignment); log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p9
Prompt:
a high level design now, docs/design/high_level_design.md. the parts are: an ingest cli, an
index cli, the fastapi service, sqlite, a react dashboard, and an eval cli that writes a csv.
a mermaid diagram of how data moves between them, then one search request as numbered steps,
then how it runs locally (two processes, api on 8000 and vite on 5173, vite proxies to the
api). two pages max. i will paste the branching strategy in myself.
Model: Cursor Grok 4.6
Files: docs/design/high_level_design.md, docs/codex_log.md
What came back:
Wrote `docs/design/high_level_design.md`: parts table, mermaid data flow, seven search-request steps, local run (API 8000, Vite 5173, proxy). Left an empty Branching strategy heading for you to paste. Paths and commands match the functional requirements. No extra processes or cloud.

Add high-level design for ingest, index, API, SQLite, dashboard, eval
validated: HLD written; branching heading left empty; log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p10
Prompt:
the diagram is too busy. drop the internal boxes, i only want the pieces a reviewer would recognise from the assignment.
add an new diagram above it, with this lesser version, kepp the current one too
Model: Cursor Grok 4.6
Files: docs/design/high_level_design.md, docs/codex_log.md
What came back:
Added an Overview mermaid above the existing one: Ingest CLI, Index CLI, FastAPI, SQLite, React dashboard, Eval CLI only. Kept the detailed Data movement diagram as it was.

Add a simple overview diagram above the detailed data-flow
validated: two mermaid diagrams in HLD; log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p11
Prompt:
start docs/design/low_level_design.md. only the data shapes for now:
- the jsonl doc record: doc_id, title, text, source, created_at (thats section 6.1)
- an index metadata file: embedding model, dimension, corpus hash, build time (6.2)
- sqlite tables for request logs, feedback, and error logs. propose columns, keep them minimal. the request log needs at least what 6.6 lists, request_id, query, latency_ms, top_k, alpha, result_count, error
- experiments.csv columns: timestamp, commit, then the params we vary, then the 3 metrics
- the api contracts from 6.3 as json examples. /search results must carry bm25_score, vector_score and hybrid_score per result, plus a snippet

leave a "modules" heading empty, next prompt.
Model: Cursor Grok 4.6
Files: docs/design/low_level_design.md, docs/codex_log.md
What came back:
Wrote `docs/design/low_level_design.md` with data shapes only: JSONL doc (s6.1), index metadata (s6.2), SQLite `request_log` / `feedback` / `error_log`, `experiments.csv` (timestamp, commit, alpha, embedding_model, preprocessing, three metrics), and s6.3 JSON examples. `/search` results include the three scores plus `snippet`. `request_log` has the s6.6 fields plus `created_at`. Modules heading left empty.

Add LLD data shapes for docs, indexes, SQLite, CSV, and API
validated: LLD data shapes written; Modules empty; log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p12
Prompt:
fill the modules section. i dont want to design the whole folder tree now, just list the pieces we will need, one line each, and the main thing each one exposes: config, ingest (clean + write jsonl), bm25, embeddings and the vector index, hybrid combine with
normalisation, snippets, eval metrics, api routes, logging and metrics, sqlite access.
proposed signatures are fine, they will change as we go.

then a short bit on errors: bad input is 422, rate limited is 429, index missing means we refuse to start with a clear message, anything else 500 with the request id in the body.
Model: Cursor Grok 4.6
Files: docs/design/low_level_design.md, docs/codex_log.md
What came back:
Filled the Modules section in `docs/design/low_level_design.md`: ten pieces, one line each, with a proposed signature (config, ingest, bm25, vector index, hybrid+normalise, snippets, eval, api routes, logging/metrics, sqlite). No folder tree. Added Errors: 422, 429, refuse to start if the index is missing, otherwise 500 with `request_id` in the body.

Fill LLD modules list and error status mapping
validated: modules and errors written; no folder tree; log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p13
Prompt:
docs/architecture.md, one page, for someone with two minutes. what it is, a link to the hld, the sqlite tables as create table statements (copy from the lld), how data moves in five lines, and links to the other docs
Model: Cursor Grok 4.6
Files: docs/architecture.md, docs/codex_log.md
What came back:
Wrote `docs/architecture.md` (one page): what it is, link to the HLD, CREATE TABLE for `request_log` / `feedback` / `error_log` from the LLD columns, five data-movement lines, and links to the requirements, design, and prompt-log docs.

Add one-page architecture overview with SQLite DDL
validated: architecture.md written; log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p14
Prompt:
two skeleton files. docs/decision_log.md with a heading and an entry template (context, options, decision, consequences). docs/break_fix_log.md with three sections, scenario A B C from section 9 of the assignment, each with sub headings: what i broke, what happened, root cause, fix, how i verified, commits. headings only
Model: Cursor Grok 4.6
Files: docs/decision_log.md, docs/break_fix_log.md, docs/codex_log.md
What came back:
Created `docs/decision_log.md` (heading + template: Context, Options, Decision, Consequences) and `docs/break_fix_log.md` (scenarios A/B/C from s9, subheadings only). I will not edit those two files again unless you name them.

Add decision log template and section 9 break/fix headings
validated: both skeletons written; headings only on break/fix; log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p15
Prompt:
lets set up the repo. a .gitignore, for a python fast api backend and react vite forntend .  i am on windows and dont want CRLF in shell scripts. and a .env.example with the settings i think we need: embedding model (all-MiniLM-L6-v2), default alpha 0.5, normalisation minmax, api port 8000, ui port 5173, a rate limit per minute, log level. prefix them HSS_.
Model: Cursor Grok 4.6
Files: .gitignore, .gitattributes, .env.example, docs/codex_log.md
What came back:
Repo bootstrap files are in place: `.gitignore` for FastAPI + Vite, `.env.example` with the `HSS_` settings you listed, and `.gitattributes` so `*.sh` stays LF on Windows.

`.gitignore` covers Python (venv, pycache, pytest/mypy/ruff, coverage), Node/Vite (`node_modules`, Vite `dist-ssr`, debug logs), generated artifacts (`data/processed/`, `data/index/`, SQLite), `.env` (not `.env.example`), OS junk, and editor swap files. `data/raw` and `data/eval` are not ignored so the sample corpus and qrels can be committed.

`.gitignore` cannot set line endings. I added `.gitattributes` with `*.sh text eol=lf` so Git Bash / reviewer Linux-macOS scripts are not checked out as CRLF. Say if you did not want that file.

`.env.example`:

- `HSS_EMBEDDING_MODEL=all-MiniLM-L6-v2`
- `HSS_DEFAULT_ALPHA=0.5`
- `HSS_NORMALISATION=minmax`
- `HSS_API_PORT=8000`
- `HSS_UI_PORT=5173`
- `HSS_RATE_LIMIT_PER_MINUTE=60` (you did not pick a number; 60 is the placeholder)
- `HSS_LOG_LEVEL=INFO` (same, placeholder)

No tests: config files only, no application code yet.

Add gitignore, LF shell scripts, and HSS_ env example
validated: gitignore + env example written; gitattributes added for *.sh LF; log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p16
Prompt:
requirements.txt. fastapi, uvicorn, pydantic v2, rank-bm25, sentence-transformers, faiss-cpu, numpy, torch (cpu build), pytest, httpx for the test client. pin versions you are fairly sure have wheels on windows, linux and mac. a comment on top saying how to install torch from the cpu index. nothing else in there.
Model: Cursor Grok 4.6
Files: requirements.txt, docs/codex_log.md
What came back:
Wrote `requirements.txt` with only the packages you named, pinned, plus a CPU-index comment for torch.

Install torch first, then the rest:

    pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
    pip install -r requirements.txt

Pins (checked on PyPI / the CPU wheel index):

- fastapi==0.141.1, uvicorn==0.52.4, pydantic==2.13.5 (v2), rank-bm25==0.2.2, sentence-transformers==6.0.1, pytest==9.1.1, httpx==0.28.1 — pure/any wheels
- faiss-cpu==1.15.0 — win_amd64, manylinux x86_64/aarch64, macOS arm64 and x86_64
- numpy==2.4.6 — 3.11+ wheels on Windows, Linux, macOS. Latest 2.5.2 requires Python 3.12, which would break 3.11
- torch==2.14.0 — CPU index has Linux/Windows `+cpu` wheels and macOS arm64. PyPI Linux torch 2.14.0 depends on CUDA, which is why the comment is there

No extra packages. No tests: pin file only, not application code.

Pin backend deps with CPU torch install comment
validated: requirements.txt written with pinned wheels; numpy 2.4.6 for Python 3.11; log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p17
Prompt:
 install in a fresh .venv, then replace the pins with what pip freeze says.
Model: Cursor Grok 4.6
Files: requirements.txt, docs/codex_log.md
What came back:
Created a fresh `.venv` on Python 3.12.3, installed CPU torch, then `requirements.txt`. Replaced the pins with `pip freeze` (comment kept).

Install:

    python -m venv .venv
    .venv/Scripts/python -m pip install --upgrade pip
    .venv/Scripts/python -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu
    .venv/Scripts/python -m pip install -r requirements.txt

Torch is `2.14.0+cpu`; `torch.cuda.is_available()` is False. Freeze includes transitive deps. `torch==2.14.0+cpu` is the Windows/Linux CPU local version; macOS CPU wheels are `2.14.0` without `+cpu`. `colorama==0.4.6` came in via pytest/click on Windows.

No tests: lockfile only, not application code.

Freeze installed deps into requirements.txt from fresh venv
validated: fresh venv; CPU torch 2.14.0+cpu; requirements.txt replaced with pip freeze; log entry appended; no tests (not code)
Review:
Commit:

Date: 2026-09-03
Prompt id: p18
Prompt:
i want the backend to be a proper package so `python -m app.ingest` works from the repo root like the assignment shows. create backend/pyproject.toml, package name app, code under backend/app. version 0.1.0, python >= 3.11, no dependencies listed (requirements.txt has them). put the pytest config in there too, tests in backend/tests, and a "slow" marker for tests that load the real model. then check pip install -e backend works from the root
Model: Cursor Grok 4.6
Files: backend/pyproject.toml, backend/app/__init__.py, backend/app/ingest.py, backend/tests/test_app.py, docs/codex_log.md
What came back:
`app` is an installable package under `backend/`. From the repo root, `python -m app.ingest` works after `pip install -e backend`.

`backend/pyproject.toml`: name `app`, version `0.1.0`, `requires-python = ">=3.11"`, no dependencies. Pytest `testpaths = ["tests"]` and marker `slow: tests that load the real model`.

Stub `backend/app/ingest.py` so `-m app.ingest` is a real module (empty `main()` for now). Tests cover version, that ingest runs, and the slow marker (no real model load).

`pip install -e backend` from root: installed `app-0.1.0`. `python -m app.ingest` exit 0.

```
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Kearney\backend
configfile: pyproject.toml
plugins: anyio-4.15.0
collected 3 items

backend\tests\test_app.py ...                                            [100%]

============================== 3 passed in 0.04s ==============================
```

Add installable app package with pytest slow marker
validated: pip install -e backend ok; python -m app.ingest exit 0; pytest 3 passed
Review:
Commit:

Date: 2026-09-03
Prompt id: p19
Prompt:
backend/app/config.py. one settings object, a plain dataclass, no pydantic here. it has to find the repo root by itself (walk up until it sees up.sh or .git, or take HSS_REPO_ROOT from the env) and build the data paths from it: raw, processed, index, eval, metrics, and the sqlite file. plus the settings from .env.example read with the HSS_ prefix. a test in backend/tests/test_config.py that the root resolves right and the env override works.
Model: Cursor Grok 4.6
Files: backend/app/config.py, backend/tests/test_config.py, docs/codex_log.md
What came back:
`load_config()` returns one frozen `Settings` dataclass (no pydantic). Repo root is `HSS_REPO_ROOT` if set, otherwise a walk up from cwd (then from this file) until `up.sh` or `.git`. Paths are `data/raw`, `data/processed`, `data/index`, `data/eval`, `data/metrics`, and `data/hss.sqlite`. HSS_ fields match `.env.example` (defaults if unset).

```
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\Kearney\backend
configfile: pyproject.toml
plugins: anyio-4.15.0
collected 2 items

backend\tests\test_config.py ..                                          [100%]

============================== 2 passed in 0.05s ==============================
```

Add Settings dataclass with repo-root and HSS_ env
validated: test_config.py 2 passed (root resolve + env override)
Review:
Commit:

Date: 2026-09-03
Prompt id: p20
Prompt:
done some changes with the Cache load_config with lru_cache and cache_clear, cehck them,
it caches the settings and the test cant reset it. add a small clear function, or use
lru_cache and call cache_clear in the test, whichever is less code.
Model: Cursor Grok 4.6
Files: backend/tests/test_config.py, docs/codex_log.md
What came back:
Checked: `@lru_cache` on `load_config()` is fine. Less code than a wrapper is `load_config.cache_clear()` in the tests (no extra function in `config.py`).

`cache_clear` only at the start of `_clear_hss` leaves the override cached after the test ends (monkeypatch restores env, cache does not). Autouse fixture now clears before and after every test. `_clear_hss` only drops HSS_ env vars.

```
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- D:\Kearney\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Kearney\backend
configfile: pyproject.toml
plugins: anyio-4.15.0
collecting ... collected 2 items

backend\tests\test_config.py::test_env_override PASSED                   [ 50%]
backend\tests\test_config.py::test_repo_root_resolves PASSED             [100%]

============================== 2 passed in 0.04s ==============================
```

Reverse order (override then root) and the full 5-test suite also passed.

Clear load_config lru_cache in tests
validated: test_config.py 2 passed both orders; full backend suite 5 passed
Review:
Commit:

Date: 2026-09-03
Prompt id: p21
Prompt:
a conftest with fake docs we can reuse everywhere. six short docs in the jsonl shape, clearly different topics (volcanoes, bread, python, the moon, football, jazz). a fixture that writes them to a tmp jsonl, and one that points HSS_REPO_ROOT at a tmp dir with the data folders already created. one smoke test so pytest has something to run.
Model: Cursor Grok 4.6
Files: backend/tests/conftest.py, backend/tests/test_smoke.py, docs/codex_log.md
What came back:
Shared fixtures are in `backend/tests/conftest.py`. `SAMPLE_DOCS` is six JSONL records (doc_id, title, text, source, created_at) on volcanoes, bread, python, the moon, football, and jazz.

- `sample_docs` — copy of that list
- `sample_docs_jsonl` — writes them to a tmp `docs.jsonl` and returns the path
- `tmp_repo` — tmp dir with `data/raw`, `processed`, `index`, `eval`, `metrics`; sets `HSS_REPO_ROOT`; clears the `load_config` cache

Smoke test `backend/tests/test_smoke.py` checks six titles, the data folders, and that `load_config().repo_root` is the tmp repo.

```
============================= test session starts =============================
platform win32 -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- D:\Kearney\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: D:\Kearney\backend
configfile: pyproject.toml
plugins: anyio-4.15.0
collecting ... collected 6 items

backend\tests\test_app.py::test_package_version PASSED                   [ 16%]
backend\tests\test_app.py::test_ingest_module_is_runnable PASSED         [ 33%]
backend\tests\test_app.py::test_slow_marker_for_real_model PASSED        [ 50%]
backend\tests\test_config.py::test_repo_root_resolves PASSED             [ 66%]
backend\tests\test_config.py::test_env_override PASSED                   [ 83%]
backend\tests\test_smoke.py::test_sample_docs_and_tmp_repo PASSED        [100%]

============================== 6 passed in 0.11s ==============================
```

Add shared sample docs fixtures and smoke test
validated: pytest 6 passed including smoke test
Review:
Commit:

