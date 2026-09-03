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

const WINDOWS: TimeWindow[] = ['1h', '24h', '7d']
const REFRESH_MS = 30_000
const PURPLE = '#7823DC'

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

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
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

export default function KpisPage() {
  const [range, setRange] = useState<TimeWindow>('24h')
  const [data, setData] = useState<KpiData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastChecked, setLastChecked] = useState<string | null>(null)

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
      `}</style>

      <div className="page-header page-header-row">
        <div>
          <div className="page-eyebrow">Observability</div>
          <h1 className="page-title">KPIs</h1>
          <p className="page-desc">
            Query volume, latency, and zero-result rates for the selected window.
          </p>
        </div>
        <div className="header-actions">
          {lastChecked && <span className="last-checked">Checked {lastChecked}</span>}
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
              <div className="hc-eyebrow">p50 latency</div>
              <div className="hc-metric">{formatMs(data.summary.p50)}</div>
            </div>
            <div className="health-card">
              <div className="hc-eyebrow">p95 latency</div>
              <div className="hc-metric">{formatMs(data.summary.p95)}</div>
            </div>
            <div className="health-card">
              <div className="hc-eyebrow">Total requests</div>
              <div className="hc-metric">{data.summary.total.toLocaleString()}</div>
            </div>
            <div className="health-card">
              <div className="hc-eyebrow">Zero results</div>
              <div className="hc-metric">{data.summary.zero_result_count.toLocaleString()}</div>
            </div>
          </div>

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
    </div>
  )
}
