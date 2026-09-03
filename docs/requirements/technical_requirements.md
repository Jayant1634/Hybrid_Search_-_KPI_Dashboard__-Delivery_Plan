# Technical requirements

Source: assignment sections 3 and 5, plus the Windows 11 note below.

## Constraints (s3)

- CPU-only (no GPU dependency) (s3)
- Runnable end-to-end via `./up.sh` on a fresh machine (after system prerequisites in the assignment) (s3)
- All services locally runnable; no paid cloud services (s3)
- No hard-coded absolute paths; works from repo root (s3)
- All steps documented; reviewer reproduces in <= 30 minutes on a typical laptop (s3)
- Codex usage incremental and auditable (see assignment section 8) (s3)

## Stack (s5)

Deviations must be justified in the README (s5). Vespa/Marqo not required; heavier infra must still run on a typical laptop and start from `./up.sh` (s5).

| Layer | Choice |
| --- | --- |
| Backend | Python 3.11+, FastAPI, Uvicorn (s5) |
| Search | rank-bm25 (or equivalent); sentence-transformers; FAISS (CPU) or hnswlib (s5) |
| Storage | SQLite (logs/queries/metrics) + local filesystem for indexes (s5) |
| Frontend | React + Vite (preferred) OR Streamlit (acceptable) (s5) |
| Testing | pytest (backend) (s5) |
| Packaging | `requirements.txt` (or uv/poetry) + a single `./up.sh` (s5) |

## Versions

- Python: 3.11+ (s5)
- Node: not specified in the assignment. Needed if using React + Vite (s5).

## Dev vs reviewer machines (not in the assignment)

Development is Windows 11 + Git Bash. Reviewer runs Linux or macOS. `./up.sh` must work on the reviewer OS.

- Bash scripts: LF line endings (not CRLF).
- venv: `./.venv/Scripts` on Windows, `./.venv/bin` on Linux/macOS; detect, do not hard-code.
- Paths: `pathlib` only; no absolute paths (also s3).
- Do not use `pkill`. Stop processes in a way that works on Linux/macOS without assuming Windows tools.
