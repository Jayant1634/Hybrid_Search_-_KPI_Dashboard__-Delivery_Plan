# Low-level design

Data shapes, modules, and error mapping. No folder tree.

## Document record (s6.1)

JSONL, one object per line. Fields: `doc_id`, `title`, `text`, `source`, `created_at`.

```json
{"doc_id": "doc-001", "title": "Example", "text": "Body text.", "source": "sample", "created_at": "2024-01-15T00:00:00Z"}
```

## Index metadata (s6.2)

Stored with the indexes. Fields: embedding model name, dimension, corpus hash, build timestamp.

```json
{"embedding_model": "sentence-transformers/all-MiniLM-L6-v2", "dimension": 384, "corpus_hash": "sha256:...", "build_timestamp": "2026-09-03T10:00:00Z"}
```

Model name is an example of a small CPU sentence-transformers model (s5/s6.2), not a locked choice.

## SQLite (s6.3, s6.6)

Minimal tables. `request_log` columns are the s6.6 log fields plus `created_at`. `feedback` is for optional `POST /feedback`. `error_log` supports the debug page (time range + severity).

**request_log:** `request_id`, `query`, `latency_ms`, `top_k`, `alpha`, `result_count`, `error`, `created_at`

**feedback:** `request_id`, `doc_id`, `relevant`, `created_at`

**error_log:** `created_at`, `severity`, `message`, `request_id`

## experiments.csv (s6.5)

Params we vary: alpha, embedding model, preprocessing. Metrics: nDCG@10, Recall@10, MRR@10.

```
timestamp,commit,alpha,embedding_model,preprocessing,ndcg_at_10,recall_at_10,mrr_at_10
```

## API contracts (s6.3)

### `GET /health`

```json
{"status": "OK", "version": "0.1.0", "commit": "abc1234"}
```

### `POST /search`

Request:

```json
{"query": "example question", "top_k": 10, "alpha": 0.5, "filters": {}}
```

Response (each result has `bm25_score`, `vector_score`, `hybrid_score`, and a snippet):

```json
{
  "results": [
    {
      "doc_id": "doc-001",
      "title": "Example",
      "bm25_score": 0.8,
      "vector_score": 0.6,
      "hybrid_score": 0.7,
      "snippet": "...highlight..."
    }
  ]
}
```

### `POST /feedback` (optional)

```json
{"request_id": "req-001", "doc_id": "doc-001", "relevant": true}
```

### `GET /metrics`

Basic counters and latency summary. Prometheus-style text is acceptable. JSON example:

```json
{"request_count": 0, "latency_ms": {"p50": 0, "p95": 0}}
```

## Modules

One piece each. Signatures will change.

- **config** — settings (paths, model name, alpha default, rate limit). `load_config() -> Settings`
- **ingest** — clean text and write JSONL. `clean_text(text: str) -> str`; `ingest(input_dir: Path, out_dir: Path) -> Path`
- **bm25** — lexical index over title + text. `BM25Index.build(docs)`; `BM25Index.query(query: str, top_k: int) -> list[tuple[str, float]]`
- **embeddings / vector index** — CPU sentence-transformers + vector search. `VectorIndex.build(docs)`; `VectorIndex.query(query: str, top_k: int) -> list[tuple[str, float]]`
- **hybrid** — two normalisation strategies, then `hybrid = alpha * norm_bm25 + (1-alpha) * norm_vector`. `normalize(scores: list[float], strategy: str) -> list[float]`; `combine(bm25, vector, alpha, strategy) -> list[tuple[str, float, float, float]]`
- **snippets** — highlight snippet per hit. `snippet(text: str, query: str) -> str`
- **eval** — nDCG@10, Recall@10, MRR@10; append `experiments.csv`. `ndcg_at_10(...)`; `recall_at_10(...)`; `mrr_at_10(...)`; `run_eval(queries, qrels) -> Path`
- **api routes** — `/health`, `/search`, `/metrics`, optional `/feedback`. FastAPI handlers; search returns per-result `bm25_score`, `vector_score`, `hybrid_score`, `snippet`.
- **logging and metrics** — structured JSON request logs (s6.6 fields) and counters / latency for `/metrics`. `log_request(...)`; `metrics_snapshot() -> dict`
- **sqlite** — `request_log`, `feedback`, `error_log`. `insert_request_log(...)`; `insert_feedback(...)`; `insert_error(...)`

## Errors

- Bad input → **422**
- Rate limited → **429**
- Index missing → **do not start**; print a clear message
- Anything else → **500** with `request_id` in the body
