import { useState, useCallback } from 'react'
import InfoTip, { InfoLabel } from '../components/InfoTip'
import ResultCard from '../components/ResultCard'
import { INFO_TIPS } from '../infoTips'
import { search, type DatasetName, type Normalization, type SearchFilters, type SearchResult } from '../api'

const PAGE_SIZE = 5

function localDateToIso(value: string, endOfDay: boolean): string {
  if (!value) return ''
  return endOfDay ? `${value}T23:59:59` : `${value}T00:00:00`
}

function clampPage(page: number, total: number, size: number): number {
  const pages = Math.max(1, Math.ceil(total / size))
  return Math.min(pages, Math.max(1, page))
}

function pageItems<T>(items: T[], page: number, size: number): T[] {
  const start = (page - 1) * size
  return items.slice(start, start + size)
}

function TablePager({
  page,
  total,
  pageSize,
  onPage,
}: {
  page: number
  total: number
  pageSize: number
  onPage: (page: number) => void
}) {
  if (total <= pageSize) return null
  const pages = Math.ceil(total / pageSize)
  const from = (page - 1) * pageSize + 1
  const to = Math.min(total, page * pageSize)
  const windowStart = Math.max(1, Math.min(page - 2, pages - 4))
  const windowEnd = Math.min(pages, windowStart + 4)
  const nums: number[] = []
  for (let n = windowStart; n <= windowEnd; n += 1) nums.push(n)
  return (
    <nav className="table-pager" aria-label="Result pages">
      <span className="table-pager-meta">
        {from}–{to} of {total}
      </span>
      <div className="table-pager-btns">
        <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Prev
        </button>
        {nums.map(n => (
          <button
            key={n}
            type="button"
            aria-current={n === page ? 'page' : undefined}
            onClick={() => onPage(n)}
          >
            {n}
          </button>
        ))}
        <button type="button" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </button>
      </div>
    </nav>
  )
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(10)
  const [alpha, setAlpha] = useState(0.5)
  const [normalization, setNormalization] = useState<Normalization>('minmax')
  const [rrfK, setRrfK] = useState('')
  const [minVectorScore, setMinVectorScore] = useState(0.2)
  const [dataset, setDataset] = useState<'' | DatasetName>('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [createdFrom, setCreatedFrom] = useState('')
  const [createdTo, setCreatedTo] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<SearchResult[]>([])
  const [requestId, setRequestId] = useState('')
  const [tookMs, setTookMs] = useState<number | null>(null)
  const [searched, setSearched] = useState(false)
  const [page, setPage] = useState(1)
  const rrfKReady =
    normalization !== 'rrf' ||
    (rrfK.trim() !== '' && Number.isInteger(Number(rrfK)) && Number(rrfK) >= 0)

  const handleSearch = useCallback(async () => {
    const q = query.trim()
    if (!q) return
    setLoading(true)
    setError(null)
    setSearched(true)
    setPage(1)
    const filters: SearchFilters = {}
    if (dataset) filters.dataset = dataset
    if (sourceFilter.trim()) filters.source_contains = sourceFilter.trim()
    if (createdFrom) filters.created_from = localDateToIso(createdFrom, false)
    if (createdTo) filters.created_to = localDateToIso(createdTo, true)
    const hasFilters = Object.keys(filters).length > 0

    if (normalization === 'rrf') {
      const parsed = Number(rrfK)
      if (rrfK.trim() === '' || !Number.isInteger(parsed) || parsed < 0) {
        setError('RRF needs k: the smoothing constant in 1/(k + rank). Enter an integer ≥ 0.')
        setLoading(false)
        return
      }
    }

    try {
      const parsedK = Number(rrfK)
      const resp = await search({
        query: q,
        top_k: topK,
        alpha,
        normalization,
        min_vector_score: minVectorScore,
        ...(normalization === 'rrf' ? { rrf_k: parsedK } : {}),
        filters: hasFilters ? filters : null,
      })
      setResults(resp.results)
      setRequestId(resp.request_id)
      setTookMs(resp.took_ms)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [query, topK, alpha, normalization, rrfK, minVectorScore, dataset, sourceFilter, createdFrom, createdTo])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleSearch()
  }

  const handleClear = () => {
    setQuery('')
    setResults([])
    setTookMs(null)
    setSearched(false)
    setError(null)
    setPage(1)
  }

  const safePage = clampPage(page, results.length, PAGE_SIZE)
  const visible = pageItems(results, safePage, PAGE_SIZE)
  const rankOffset = (safePage - 1) * PAGE_SIZE

  return (
    <div className="page-container">
      <style>{`
        .page-container { gap: 16px; padding-top: 28px; }
        .page-title { font-size: 26px; }
        .page-desc { font-size: 13px; }
        .search-panel { padding: 16px 18px; gap: 14px; }
        .results-list { gap: 8px; }
        .table-pager {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-top: 4px;
          padding-top: 10px;
          border-top: 1px solid var(--c-border);
          font-size: 12px;
          color: var(--c-muted);
        }
        .table-pager-btns { display: flex; gap: 4px; }
        .table-pager button {
          min-width: 28px;
          height: 28px;
          padding: 0 8px;
          border: 1px solid var(--c-border);
          background: var(--c-surface);
          color: var(--c-text);
          border-radius: 4px;
          font-size: 12px;
        }
        .table-pager button:disabled { opacity: 0.45; }
        .table-pager button[aria-current='page'] {
          border-color: var(--purple);
          color: var(--purple);
          background: var(--purple-tint);
        }
      `}</style>
      <div className="page-header">
        <div className="page-eyebrow">Hybrid Search</div>
        <h1 className="page-title">Search Documents</h1>
        <p className="page-desc">
          BM25 + vector fusion retrieval with explainable per-document scoring.
          Choose a dataset to search Wikipedia, Kearney contracts, or both.
        </p>
      </div>

      <div className="search-panel">
        <div className="search-field-row">
          <div className="search-field">
            <svg className="search-field-icon" width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.4" />
              <path d="M11 11l2.5 2.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
            </svg>
            <input
              className="search-input"
              type="text"
              placeholder="Enter your search query…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              autoFocus
            />
            {query && (
              <button className="search-clear" onClick={handleClear} title="Clear">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <path d="M2 2l8 8M10 2L2 10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                </svg>
              </button>
            )}
          </div>
          <button
            className="btn-primary search-go"
            onClick={handleSearch}
            disabled={loading || !query.trim() || !rrfKReady}
          >
            {loading ? <span className="spinner" /> : 'Search'}
          </button>
        </div>

        <div className="search-params">
          <InfoTip className="param-group" label="Top K" hint={INFO_TIPS.topK}>
            <label className="param-label"><InfoLabel text="Top K" /></label>
            <input
              type="number"
              className="param-input"
              min={1} max={50}
              value={topK}
              onChange={e => setTopK(Math.min(50, Math.max(1, Number(e.target.value))))}
            />
          </InfoTip>

          <InfoTip className="param-group param-alpha" label="Alpha" hint={INFO_TIPS.alpha}>
            <label className="param-label">
              <InfoLabel text="Alpha" />
              <span className="param-value-badge">{alpha.toFixed(2)}</span>
            </label>
            <div className="alpha-range-row">
              <span className="range-end-label">BM25</span>
              <input
                type="range"
                className="param-range"
                min={0} max={1} step={0.05}
                value={alpha}
                onChange={e => setAlpha(Number(e.target.value))}
              />
              <span className="range-end-label">Vector</span>
            </div>
          </InfoTip>

          <InfoTip className="param-group param-alpha" label="Min vector" hint={INFO_TIPS.minVector}>
            <label className="param-label">
              <InfoLabel text="Min vector" />
              <span className="param-value-badge">{minVectorScore.toFixed(2)}</span>
            </label>
            <div className="alpha-range-row">
              <span className="range-end-label">Off</span>
              <input
                type="range"
                className="param-range"
                min={0} max={1} step={0.05}
                value={minVectorScore}
                onChange={e => setMinVectorScore(Number(e.target.value))}
              />
              <span className="range-end-label">1.00</span>
            </div>
          </InfoTip>

          <InfoTip className="param-group" label="Dataset" hint={INFO_TIPS.dataset}>
            <label className="param-label"><InfoLabel text="Dataset" /></label>
            <select
              className="param-select"
              value={dataset}
              onChange={e => setDataset(e.target.value as '' | DatasetName)}
            >
              <option value="">All datasets</option>
              <option value="wikipedia">Wikipedia</option>
              <option value="contracts">Kearney Contracts</option>
            </select>
          </InfoTip>

          <InfoTip className="param-group" label="Normalisation" hint={INFO_TIPS.normalisation}>
            <label className="param-label"><InfoLabel text="Normalisation" /></label>
            <select
              className="param-select"
              value={normalization}
              onChange={e => setNormalization(e.target.value as Normalization)}
            >
              <option value="minmax">Min-Max</option>
              <option value="zscore">Z-Score</option>
              <option value="rrf">RRF</option>
            </select>
          </InfoTip>

          {normalization === 'rrf' && (
            <InfoTip className="param-group param-alpha" label="RRF k" hint={INFO_TIPS.rrfK}>
              <label className="param-label">
                <InfoLabel text="RRF k" />
                {rrfK.trim() !== '' && (
                  <span className="param-value-badge">{rrfK}</span>
                )}
              </label>
              <input
                type="number"
                className="param-input"
                min={0}
                max={10000}
                step={1}
                placeholder="enter k"
                value={rrfK}
                onChange={e => setRrfK(e.target.value)}
              />
            </InfoTip>
          )}

          <button
            className="btn-ghost filter-toggle-btn"
            onClick={() => setShowFilters(s => !s)}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M1 3h12M3 7h8M5 11h4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
            </svg>
            {showFilters ? 'Hide filters' : 'Filters'}
          </button>
        </div>

        {showFilters && (
          <div className="filter-row">
            <InfoTip className="param-group" label="Source contains" hint={INFO_TIPS.sourceContains}>
              <label className="param-label"><InfoLabel text="Source contains" /></label>
              <input
                type="text"
                className="param-input filter-input"
                placeholder="e.g. wikipedia or msa"
                value={sourceFilter}
                onChange={e => setSourceFilter(e.target.value)}
              />
            </InfoTip>
            <InfoTip className="param-group" label="Created from" hint={INFO_TIPS.createdFrom}>
              <label className="param-label"><InfoLabel text="Created from" /></label>
              <input
                type="date"
                className="param-input filter-input"
                value={createdFrom}
                onChange={e => setCreatedFrom(e.target.value)}
              />
            </InfoTip>
            <InfoTip className="param-group" label="Created to" hint={INFO_TIPS.createdTo}>
              <label className="param-label"><InfoLabel text="Created to" /></label>
              <input
                type="date"
                className="param-input filter-input"
                value={createdTo}
                onChange={e => setCreatedTo(e.target.value)}
              />
            </InfoTip>
          </div>
        )}
      </div>

      {error && <div className="error-banner">{error}</div>}

      {!error && tookMs !== null && (
        <div className="results-meta-bar">
          <span className="results-count">
            {results.length} result{results.length !== 1 ? 's' : ''}
          </span>
          <span className="results-took">{tookMs.toFixed(1)} ms</span>
          <span className="results-reqid">
            <span className="meta-label">request</span> {requestId.slice(0, 8)}…
          </span>
        </div>
      )}

      {results.length > 0 && (
        <div className="results-list">
          {visible.map((r, i) => (
            <ResultCard
              key={r.doc_id}
              result={r}
              requestId={requestId}
              rank={rankOffset + i + 1}
              query={query}
            />
          ))}
          <TablePager
            page={safePage}
            total={results.length}
            pageSize={PAGE_SIZE}
            onPage={setPage}
          />
        </div>
      )}

      {searched && !loading && !error && results.length === 0 && (
        <div className="empty-state">
          <div className="empty-icon">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <circle cx="18" cy="18" r="12" stroke="var(--c-border)" strokeWidth="1.5" />
              <path d="M27 27l8 8" stroke="var(--c-border)" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M13 18h10M18 13v10" stroke="var(--c-muted)" strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
            </svg>
          </div>
          <p className="empty-title">No results</p>
          <p className="empty-desc">No documents matched <strong>"{query}"</strong>. Try lowering min vector or adjusting filters.</p>
        </div>
      )}
    </div>
  )
}
