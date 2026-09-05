import { useEffect, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

type TimeWindow = '1h' | '24h' | '7d'
type DatasetName = 'wikipedia' | 'contracts'

const WINDOWS: TimeWindow[] = ['1h', '24h', '7d']
const REFRESH_MS = 30_000
const PURPLE = '#7823DC'
const DEFAULT_QUERY = 'volcano'
const MIN_COUNT = 2
const MAX_COUNT = 200
const DEFAULT_COUNT = 20

interface KpiSummary {
  total: number
  p50: number
  p95: number
  zero_result_count: number
  error_count: number
}

interface VolumePoint {
  bucket: string
  count: number
}

interface TopQuery {
  query: string
  count: number
  avg_latency_ms: number
}

interface ZeroResultQuery {
  query: string
  count: number
  last_seen: string
}

interface KpiData {
  summary: KpiSummary
  volume: VolumePoint[]
  topQueries: TopQuery[]
  zeroQueries: ZeroResultQuery[]
}

interface LoadTestResult {
  sent: number
  ok: number
  failed: number
  wall_ms: number
  p50: number
  p95: number
  avg_ms: number
  min_ms: number
  max_ms: number
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`HTTP ${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

async function loadKpis(range: TimeWindow): Promise<KpiData> {
  const q = `window=${encodeURIComponent(range)}`
  const [summary, volume, topQueries, zeroQueries] = await Promise.all([
    fetchJson<KpiSummary>(`/api/dashboard/kpi/summary?${q}`),
    fetchJson<VolumePoint[]>(`/api/dashboard/kpi/volume?${q}`),
    fetchJson<TopQuery[]>(`/api/dashboard/kpi/top-queries?${q}&limit=10`),
    fetchJson<ZeroResultQuery[]>(`/api/dashboard/kpi/zero-results?${q}&limit=10`),
  ])
  return { summary, volume, topQueries, zeroQueries }
}

async function runLoadTest(body: {
  query: string
  count: number
  dataset: DatasetName | ''
}): Promise<LoadTestResult> {
  const payload: Record<string, string | number> = {
    query: body.query,
    count: body.count,
  }
  return fetchJson<LoadTestResult>('/api/dashboard/kpi/load-test', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(
      body.dataset ? { ...payload, dataset: body.dataset } : payload,
    ),
  })
}

function formatMs(value: number): string {
  return `${value.toFixed(1)} ms`
}

function parseBucket(bucket: string): Date | null {
  const raw = bucket.includes('T')
    ? bucket.endsWith('Z') || /[+-]\d\d:\d\d$/.test(bucket)
      ? bucket
      : `${bucket}Z`
    : `${bucket}T00:00:00Z`
  const date = new Date(raw)
  return Number.isNaN(date.getTime()) ? null : date
}

function formatBucket(bucket: string): string {
  const date = parseBucket(bucket)
  if (!date) return bucket
  if (bucket.includes('T')) {
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function formatSeen(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function clampCount(value: number): number {
  if (!Number.isFinite(value)) return DEFAULT_COUNT
  return Math.min(MAX_COUNT, Math.max(MIN_COUNT, Math.trunc(value)))
}

export default function KpisPage() {
  const [range, setRange] = useState<TimeWindow>('24h')
  const [data, setData] = useState<KpiData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastChecked, setLastChecked] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [probeQuery, setProbeQuery] = useState(DEFAULT_QUERY)
  const [probeCount, setProbeCount] = useState(DEFAULT_COUNT)
  const [probeDataset, setProbeDataset] = useState<DatasetName | ''>('')
  const [firing, setFiring] = useState(false)
  const [burst, setBurst] = useState<LoadTestResult | null>(null)
  const [burstError, setBurstError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    const run = async (showSpinner: boolean) => {
      if (showSpinner) setLoading(true)
      try {
        const next = await loadKpis(range)
        if (cancelled) return
        setData(next)
        setError(null)
        setLastChecked(new Date().toLocaleTimeString())
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void run(true)
    const id = window.setInterval(() => {
      void run(false)
    }, REFRESH_MS)

    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [range])

  useEffect(() => {
    if (!drawerOpen) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !firing) setDrawerOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [drawerOpen, firing])

  const refreshQuietly = async () => {
    try {
      const next = await loadKpis(range)
      setData(next)
      setError(null)
      setLastChecked(new Date().toLocaleTimeString())
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  const fireBurst = async () => {
    const query = probeQuery.trim()
    if (!query || firing) return
    setFiring(true)
    setBurstError(null)
    try {
      const result = await runLoadTest({
        query,
        count: clampCount(probeCount),
        dataset: probeDataset,
      })
      setBurst(result)
      await refreshQuietly()
    } catch (err) {
      setBurstError(err instanceof Error ? err.message : String(err))
    } finally {
      setFiring(false)
    }
  }

  const chartData = (data?.volume ?? []).map(point => ({
    ...point,
    label: formatBucket(point.bucket),
  }))

  return (
    <div className="page-container page-container-wide">
      <style>{`
        .kpi-dash-tables {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
        }
        @media (max-width: 900px) {
          .kpi-dash-tables { grid-template-columns: 1fr; }
        }
        .kpi-dash-panel {
          background: var(--c-surface);
          border: 1px solid var(--c-border);
          border-radius: 8px;
          padding: 20px 22px;
          box-shadow: var(--shadow-sm);
        }
        .kpi-dash-panel h2 {
          font-size: 15px;
          font-weight: 600;
          color: var(--c-heading);
          margin-bottom: 14px;
        }
        .kpi-dash-plot { width: 100%; height: 280px; }
        .kpi-dash-table { width: 100%; border-collapse: collapse; }
        .kpi-dash-table th {
          text-align: left;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: var(--c-muted);
          padding: 0 8px 10px 0;
          border-bottom: 1px solid var(--c-border);
        }
        .kpi-dash-table td {
          padding: 10px 8px 10px 0;
          font-size: 13px;
          color: var(--c-text);
          border-bottom: 1px solid var(--c-border);
          vertical-align: top;
        }
        .kpi-dash-table td:last-child,
        .kpi-dash-table th:last-child { padding-right: 0; text-align: right; }
        .kpi-dash-table tr:last-child td { border-bottom: none; }
        .kpi-dash-query { word-break: break-word; }
        .kpi-dash-num { font-family: var(--mono); font-variant-numeric: tabular-nums; }
        .kpi-dash-empty {
          font-size: 13px;
          color: var(--c-secondary);
          padding: 12px 0 4px;
        }
        .kpi-latency-row {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 16px;
        }
        .kpi-latency-copy { max-width: 640px; }
        .kpi-latency-copy p {
          margin: 0;
          font-size: 13px;
          color: var(--c-secondary);
          line-height: 1.5;
        }
        .kpi-drawer-root {
          position: fixed;
          inset: 0;
          z-index: 40;
          display: flex;
          justify-content: flex-end;
        }
        .kpi-drawer-dim {
          position: absolute;
          inset: 0;
          background: rgba(10, 10, 10, 0.42);
          border: none;
          padding: 0;
          cursor: pointer;
        }
        .kpi-drawer {
          position: relative;
          width: min(440px, 100vw);
          height: 100%;
          background: var(--c-surface);
          border-left: 1px solid var(--c-border);
          box-shadow: -12px 0 40px rgba(0, 0, 0, 0.18);
          display: flex;
          flex-direction: column;
        }
        .kpi-drawer-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
          padding: 22px 22px 16px;
          border-bottom: 1px solid var(--c-border);
        }
        .kpi-drawer-head h2 {
          margin: 0 0 4px;
          font-size: 20px;
          font-weight: 700;
          letter-spacing: -0.02em;
          color: var(--c-heading);
        }
        .kpi-drawer-head p {
          margin: 0;
          font-size: 13px;
          color: var(--c-secondary);
          line-height: 1.45;
        }
        .kpi-drawer-body {
          flex: 1;
          overflow: auto;
          padding: 20px 22px 28px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .kpi-field { display: flex; flex-direction: column; gap: 6px; }
        .kpi-field label {
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: var(--c-muted);
        }
        .kpi-field input, .kpi-field select {
          width: 100%;
          height: 40px;
          padding: 0 12px;
          background: var(--c-bg);
          border: 1px solid var(--c-border-strong);
          border-radius: 5px;
          font-size: 14px;
          color: var(--c-heading);
          outline: none;
        }
        .kpi-field input:focus, .kpi-field select:focus {
          border-color: var(--purple);
          box-shadow: 0 0 0 3px var(--purple-tint);
        }
        .kpi-field-hint { font-size: 12px; color: var(--c-muted); }
        .kpi-drawer-note {
          font-size: 13px;
          color: var(--c-secondary);
          line-height: 1.5;
          background: var(--c-surface-2);
          border: 1px solid var(--c-border);
          border-radius: 6px;
          padding: 12px 14px;
        }
        .kpi-drawer-actions {
          display: flex;
          gap: 10px;
          padding-top: 4px;
        }
        .kpi-burst-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 10px;
        }
        .kpi-burst-tile {
          background: var(--c-bg);
          border: 1px solid var(--c-border);
          border-radius: 6px;
          padding: 12px 14px;
        }
        .kpi-burst-tile span {
          display: block;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: var(--c-muted);
          margin-bottom: 6px;
        }
        .kpi-burst-tile strong {
          font-size: 18px;
          font-weight: 700;
          font-family: var(--mono);
          color: var(--c-heading);
        }
      `}</style>

      <div className="page-header page-header-row">
        <div>
          <div className="page-eyebrow">Observability</div>
          <div className="page-title-row">
            <span className="page-title-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 16 16" fill="none">
                <path d="M3 12V8M8 12V4M13 12V6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
              </svg>
            </span>
            <h1 className="page-title">KPIs</h1>
          </div>
          <p className="page-desc">
            Query volume, latency, and zero-result rates for the selected window.
          </p>
        </div>
        <div className="header-actions">
          {lastChecked && <span className="last-checked">Checked {lastChecked}</span>}
          <button type="button" className="btn-secondary" onClick={() => setDrawerOpen(true)}>
            Test latency
          </button>
          <div className="cg-toggle" role="group" aria-label="Time window">
            {WINDOWS.map(option => (
              <button
                key={option}
                type="button"
                className={option === range ? 'active' : undefined}
                aria-pressed={option === range}
                onClick={() => setRange(option)}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {!data && loading && (
        <div className="empty-state">
          <span className="spinner spinner-dark spinner-lg" />
          <p className="empty-desc">Loading KPI window…</p>
        </div>
      )}

      {data && (
        <>
          <div className="health-grid">
            <div className="health-card">
              <div className="hc-head">
                <span className="hc-icon" aria-hidden="true">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.4" />
                    <path d="M8 5v3.2L10 10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <div className="hc-eyebrow">p50 latency</div>
              </div>
              <div className="hc-metric">{formatMs(data.summary.p50)}</div>
            </div>
            <div className="health-card">
              <div className="hc-head">
                <span className="hc-icon" aria-hidden="true">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M2.5 10.5A5.5 5.5 0 1 1 13.5 10.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
                    <path d="M8 8l2.2-1.4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
                    <path d="M4 13h8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
                  </svg>
                </span>
                <div className="hc-eyebrow">p95 latency</div>
              </div>
              <div className="hc-metric">{formatMs(data.summary.p95)}</div>
            </div>
            <div className="health-card">
              <div className="hc-head">
                <span className="hc-icon" aria-hidden="true">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M3 12V8M8 12V4M13 12V6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
                  </svg>
                </span>
                <div className="hc-eyebrow">Total requests</div>
              </div>
              <div className="hc-metric">{data.summary.total.toLocaleString()}</div>
            </div>
            <div className="health-card">
              <div className="hc-head">
                <span className="hc-icon" aria-hidden="true">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.4" />
                    <path d="M4.2 4.2l7.6 7.6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
                  </svg>
                </span>
                <div className="hc-eyebrow">Zero results</div>
              </div>
              <div className="hc-metric">{data.summary.zero_result_count.toLocaleString()}</div>
            </div>
          </div>

          {/* <section className="kpi-dash-panel">
            <div className="kpi-latency-row">
              <div className="kpi-latency-copy">
                <h2>Latency load test</h2>
                <p>
                  Fire a burst of concurrent hybrid searches so p50 / p95 are measured
                  on many hits at once, not a single click. Each hit is stored in
                  SQLite like a live search. Locust is the CLI driver for longer
                  multi-user HTTP soaks.
                </p>
              </div>
              <button type="button" className="btn-primary" onClick={() => setDrawerOpen(true)}>
                Open test
              </button>
            </div>
          </section> */}

          <section className="kpi-dash-panel">
            <h2>Volume per bucket</h2>
            {chartData.length === 0 ? (
              <p className="kpi-dash-empty">No requests in this window.</p>
            ) : (
              <div className="kpi-dash-plot">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--c-border)" />
                    <XAxis
                      dataKey="label"
                      tick={{ fill: 'var(--c-muted)', fontSize: 11 }}
                      tickLine={false}
                      axisLine={{ stroke: 'var(--c-border)' }}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fill: 'var(--c-muted)', fontSize: 11 }}
                      tickLine={false}
                      axisLine={{ stroke: 'var(--c-border)' }}
                      width={36}
                    />
                    <Tooltip
                      formatter={value => [value ?? 0, 'Requests']}
                      labelFormatter={label => String(label)}
                    />
                    <Line
                      type="monotone"
                      dataKey="count"
                      name="Requests"
                      stroke={PURPLE}
                      strokeWidth={2}
                      dot={{ r: 3, fill: PURPLE }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </section>

          <div className="kpi-dash-tables">
            <section className="kpi-dash-panel">
              <h2>Top queries</h2>
              {data.topQueries.length === 0 ? (
                <p className="kpi-dash-empty">No queries in this window.</p>
              ) : (
                <table className="kpi-dash-table">
                  <thead>
                    <tr>
                      <th>Query</th>
                      <th>Count</th>
                      <th>Avg latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.topQueries.map(row => (
                      <tr key={row.query}>
                        <td className="kpi-dash-query">{row.query}</td>
                        <td className="kpi-dash-num">{row.count}</td>
                        <td className="kpi-dash-num">{formatMs(row.avg_latency_ms)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>

            <section className="kpi-dash-panel">
              <h2>Zero-result queries</h2>
              {data.zeroQueries.length === 0 ? (
                <p className="kpi-dash-empty">No zero-result queries in this window.</p>
              ) : (
                <table className="kpi-dash-table">
                  <thead>
                    <tr>
                      <th>Query</th>
                      <th>Count</th>
                      <th>Last seen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.zeroQueries.map(row => (
                      <tr key={row.query}>
                        <td className="kpi-dash-query">{row.query}</td>
                        <td className="kpi-dash-num">{row.count}</td>
                        <td className="kpi-dash-num">{formatSeen(row.last_seen)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </div>
        </>
      )}

      {drawerOpen && (
        <div className="kpi-drawer-root">
          <button
            type="button"
            className="kpi-drawer-dim"
            aria-label="Close latency test"
            disabled={firing}
            onClick={() => {
              if (!firing) setDrawerOpen(false)
            }}
          />
          <aside
            className="kpi-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="kpi-load-title"
          >
            <header className="kpi-drawer-head">
              <div>
                <h2 id="kpi-load-title">Latency burst</h2>
                <p>Send the hits together, then read p50 / p95 from this run.</p>
              </div>
              <button
                type="button"
                className="btn-ghost"
                disabled={firing}
                onClick={() => setDrawerOpen(false)}
              >
                Close
              </button>
            </header>
            <div className="kpi-drawer-body">
              <p className="kpi-drawer-note">
                The API starts every search at the same time on the loaded indexes,
                times each one, and writes a <code>requests</code> row so the tiles
                here refresh. Use Locust from a second process when you want real
                HTTP multi-user load against <code>/search</code>.
              </p>

              <div className="kpi-field">
                <label htmlFor="kpi-probe-query">Query</label>
                <input
                  id="kpi-probe-query"
                  value={probeQuery}
                  onChange={event => setProbeQuery(event.target.value)}
                  disabled={firing}
                  maxLength={500}
                />
              </div>

              <div className="kpi-field">
                <label htmlFor="kpi-probe-count">Concurrent hits</label>
                <input
                  id="kpi-probe-count"
                  type="number"
                  min={MIN_COUNT}
                  max={MAX_COUNT}
                  value={probeCount}
                  onChange={event => setProbeCount(clampCount(Number(event.target.value)))}
                  disabled={firing}
                />
                <span className="kpi-field-hint">
                  {MIN_COUNT}–{MAX_COUNT} requests, all started together.
                </span>
              </div>

              <div className="kpi-field">
                <label htmlFor="kpi-probe-dataset">Dataset</label>
                <select
                  id="kpi-probe-dataset"
                  value={probeDataset}
                  onChange={event =>
                    setProbeDataset(event.target.value as DatasetName | '')
                  }
                  disabled={firing}
                >
                  <option value="">All corpora</option>
                  <option value="wikipedia">Wikipedia</option>
                  <option value="contracts">Contracts</option>
                </select>
              </div>

              <div className="kpi-drawer-actions">
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => void fireBurst()}
                  disabled={firing || !probeQuery.trim()}
                >
                  {firing ? 'Firing…' : `Fire ${clampCount(probeCount)} hits`}
                </button>
              </div>

              {burstError && <div className="error-banner">{burstError}</div>}

              {burst && (
                <div className="kpi-burst-grid">
                  <div className="kpi-burst-tile">
                    <span>Sent / ok</span>
                    <strong>
                      {burst.sent} / {burst.ok}
                    </strong>
                  </div>
                  <div className="kpi-burst-tile">
                    <span>Failed</span>
                    <strong>{burst.failed}</strong>
                  </div>
                  <div className="kpi-burst-tile">
                    <span>Burst p50</span>
                    <strong>{formatMs(burst.p50)}</strong>
                  </div>
                  <div className="kpi-burst-tile">
                    <span>Burst p95</span>
                    <strong>{formatMs(burst.p95)}</strong>
                  </div>
                  <div className="kpi-burst-tile">
                    <span>Average</span>
                    <strong>{formatMs(burst.avg_ms)}</strong>
                  </div>
                  <div className="kpi-burst-tile">
                    <span>Wall clock</span>
                    <strong>{formatMs(burst.wall_ms)}</strong>
                  </div>
                </div>
              )}
            </div>
          </aside>
        </div>
      )}
    </div>
  )
}
