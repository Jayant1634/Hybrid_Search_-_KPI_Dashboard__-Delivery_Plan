export type Normalization = "minmax" | "zscore";

export type DatasetName = "wikipedia" | "contracts";

export interface SearchFilters {
  source_contains?: string | null;
  created_from?: string | null;
  created_to?: string | null;
  dataset?: DatasetName | null;
}

export interface SearchRequest {
  query: string;
  top_k?: number;
  alpha?: number;
  normalization?: Normalization;
  min_vector_score?: number;
  filters?: SearchFilters | null;
}

export interface SearchResult {
  doc_id: string;
  title: string;
  source: string;
  created_at: string;
  bm25_score: number;
  vector_score: number;
  bm25_norm: number;
  vector_norm: number;
  hybrid_score: number;
  snippet: string;
}

export interface SearchResponse {
  request_id: string;
  took_ms: number;
  results: SearchResult[];
}

export interface FeedbackRequest {
  request_id: string;
  doc_id: string;
  relevant: boolean;
  comment?: string | null;
}

export interface FeedbackResponse {
  status: "accepted";
}

export interface IndexMeta {
  model: string;
  dimension: number;
  corpus_hash: string;
  doc_count: number;
  built_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  commit: string;
  index: IndexMeta | null;
}

export interface KpiSummary {
  total_queries: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  zero_result_rate: number;
  feedback_positive_rate: number;
}

export interface VolumePoint {
  ts: string;
  count: number;
}

export interface TopQuery {
  query: string;
  count: number;
  avg_latency_ms: number;
}

export interface ZeroResultQuery {
  query: string;
  count: number;
  last_seen: string;
}

export interface ExperimentRow {
  experiment_id: string;
  name: string;
  alpha: number;
  normalization: Normalization;
  queries: number;
  avg_latency_ms: number;
  mrr: number;
  created_at: string;
}

export interface LogEntry {
  ts: string;
  level: string;
  message: string;
  request_id?: string | null;
}

async function _fetch<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HTTP ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export interface TermOccurrence {
  term: string;
  count: number;
}

export interface ClosestWord {
  term: string;
  count: number;
  score: number;
}

export interface DocumentDetail {
  doc_id: string;
  title: string;
  source: string;
  created_at: string;
  text: string;
  highlighted_text: string;
  occurrences: TermOccurrence[];
  closest: ClosestWord[];
}

export async function search(req: SearchRequest): Promise<SearchResponse> {
  return _fetch<SearchResponse>("/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function getDocument(
  docId: string,
  query?: string,
): Promise<DocumentDetail> {
  const params = new URLSearchParams();
  if (query?.trim()) params.set("q", query.trim());
  const qs = params.toString();
  return _fetch<DocumentDetail>(
    `/documents/${encodeURIComponent(docId)}${qs ? `?${qs}` : ""}`,
  );
}

export async function submitFeedback(req: FeedbackRequest): Promise<FeedbackResponse> {
  return _fetch<FeedbackResponse>("/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function getHealth(): Promise<HealthResponse> {
  return _fetch<HealthResponse>("/health");
}

export async function getKpiSummary(window: string): Promise<KpiSummary> {
  return _fetch<KpiSummary>(`/metrics/kpi?window=${encodeURIComponent(window)}`);
}

export async function getKpiVolume(window: string): Promise<VolumePoint[]> {
  return _fetch<VolumePoint[]>(`/metrics/volume?window=${encodeURIComponent(window)}`);
}

export async function getTopQueries(window: string, limit?: number): Promise<TopQuery[]> {
  const params = new URLSearchParams({ window });
  if (limit !== undefined) params.set("limit", String(limit));
  return _fetch<TopQuery[]>(`/metrics/top-queries?${params}`);
}

export async function getZeroResultQueries(window: string, limit?: number): Promise<ZeroResultQuery[]> {
  const params = new URLSearchParams({ window });
  if (limit !== undefined) params.set("limit", String(limit));
  return _fetch<ZeroResultQuery[]>(`/metrics/zero-results?${params}`);
}

export async function getExperiments(): Promise<ExperimentRow[]> {
  return _fetch<ExperimentRow[]>("/api/experiments");
}

export async function getLogs(params: {
  level?: string;
  from?: string;
  to?: string;
  limit?: number;
}): Promise<LogEntry[]> {
  const p = new URLSearchParams();
  if (params.level) p.set("level", params.level);
  if (params.from) p.set("from", params.from);
  if (params.to) p.set("to", params.to);
  if (params.limit !== undefined) p.set("limit", String(params.limit));
  return _fetch<LogEntry[]>(`/api/logs?${p}`);
}
