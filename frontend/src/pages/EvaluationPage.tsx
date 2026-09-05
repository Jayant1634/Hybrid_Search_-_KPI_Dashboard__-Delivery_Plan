import { useEffect, useMemo, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const PURPLE = '#7823DC'

const COLUMNS = [
  { key: 'timestamp', label: 'Timestamp' },
  { key: 'commit', label: 'Commit' },
  { key: 'tag', label: 'Tag' },
  { key: 'alpha', label: 'Alpha' },
  { key: 'normalization', label: 'Normalization' },
  { key: 'model', label: 'Model' },
  { key: 'preprocessing', label: 'Preprocessing' },
  { key: 'ndcg10', label: 'nDCG@10' },
  { key: 'recall10', label: 'Recall@10' },
  { key: 'mrr10', label: 'MRR@10' },
  { key: 'n_queries', label: 'n' },
] as const

const CHART_METRICS = [
  { key: 'ndcg', label: 'nDCG@10' },
  { key: 'recall', label: 'Recall@10' },
  { key: 'mrr', label: 'MRR@10' },
] as const

type ColumnKey = (typeof COLUMNS)[number]['key']
type ChartMetric = (typeof CHART_METRICS)[number]['key']
type SortDir = 'asc' | 'desc'

const NUMERIC = new Set<ColumnKey>([
  'alpha',
  'ndcg10',
  'recall10',
  'mrr10',
  'n_queries',
])

interface ExperimentRow {
  timestamp: string
  commit: string
  tag: string
  alpha: string
  normalization: string
  model: string
  preprocessing: string
  ndcg10: string
  recall10: string
  mrr10: string
  n_queries: string
}

interface ChartPoint extends ExperimentRow {
  ndcg: number
  recall: number
  mrr: number
  label: string
}

async function fetchExperiments(): Promise<ExperimentRow[]> {
  const res = await fetch('/api/dashboard/experiments')
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`HTTP ${res.status}: ${body}`)
  }
  return res.json() as Promise<ExperimentRow[]>
}

function parseTime(value: string): number {
  const ms = Date.parse(value)
  return Number.isNaN(ms) ? 0 : ms
}

function formatTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatMetric(value: string): string {
  const n = Number(value)
  return Number.isFinite(n) ? n.toFixed(4) : value
}

function compareRows(
  a: ExperimentRow,
  b: ExperimentRow,
  key: ColumnKey,
  dir: SortDir,
): number {
  let cmp = 0
  if (key === 'timestamp') {
    cmp = parseTime(a.timestamp) - parseTime(b.timestamp)
  } else if (NUMERIC.has(key)) {
    cmp = Number(a[key]) - Number(b[key])
  } else {
    cmp = a[key].localeCompare(b[key])
  }
  if (cmp === 0) cmp = parseTime(a.timestamp) - parseTime(b.timestamp)
  return dir === 'asc' ? cmp : -cmp
}

function ExperimentTooltip({
  active,
  payload,
  metric,
}: {
  active?: boolean
  payload?: ReadonlyArray<{ payload: ChartPoint }>
  metric: ChartMetric
}) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  return (
    <div className="eval-tooltip">
      {CHART_METRICS.map(item => (
        <div
          key={item.key}
          className={
            item.key === metric
              ? 'eval-tooltip-metric eval-tooltip-metric-active'
              : 'eval-tooltip-metric'
          }
        >
          {item.label} {row[item.key].toFixed(4)}
        </div>
      ))}
      <div><span>tag</span> {row.tag}</div>
      <div><span>alpha</span> {row.alpha}</div>
      <div><span>normalization</span> {row.normalization}</div>
      <div><span>model</span> {row.model}</div>
      <div><span>commit</span> {row.commit}</div>
    </div>
  )
}

export default function EvaluationPage() {
  const [rows, setRows] = useState<ExperimentRow[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortKey, setSortKey] = useState<ColumnKey>('timestamp')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [chartMetric, setChartMetric] = useState<ChartMetric>('ndcg')
  const selectedMetric =
    CHART_METRICS.find(item => item.key === chartMetric) ?? CHART_METRICS[0]

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchExperiments()
      .then(data => {
        if (cancelled) return
        setRows(data)
        setError(null)
      })
      .catch(err => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const chartData = useMemo<ChartPoint[]>(() => {
    return [...(rows ?? [])]
      .sort((a, b) => parseTime(a.timestamp) - parseTime(b.timestamp))
      .map(row => ({
        ...row,
        ndcg: Number(row.ndcg10),
        recall: Number(row.recall10),
        mrr: Number(row.mrr10),
        label: formatTime(row.timestamp),
      }))
  }, [rows])

  const tableRows = useMemo(() => {
    return [...(rows ?? [])].sort((a, b) => compareRows(a, b, sortKey, sortDir))
  }, [rows, sortKey, sortDir])

  function onSort(key: ColumnKey) {
    if (key === sortKey) {
      setSortDir(dir => (dir === 'asc' ? 'desc' : 'asc'))
      return
    }
    setSortKey(key)
    setSortDir(NUMERIC.has(key) ? 'desc' : 'asc')
  }

  return (
    <div className="page-container page-container-wide">
      <style>{`
        .eval-panel {
          background: var(--c-surface);
          border: 1px solid var(--c-border);
          border-radius: 8px;
          padding: 20px 22px;
          box-shadow: var(--shadow-sm);
        }
        .eval-panel h2 {
          font-size: 15px;
          font-weight: 600;
          color: var(--c-heading);
          margin-bottom: 14px;
        }
        .eval-panel-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 14px;
        }
        .eval-panel-head h2 { margin-bottom: 0; }
        .eval-metric-field {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .eval-metric-field label {
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: var(--c-muted);
        }
        .eval-tooltip-metric-active { color: var(--purple); }
        .eval-plot { width: 100%; height: 280px; }
        .eval-table-wrap { overflow-x: auto; }
        .eval-table { width: 100%; border-collapse: collapse; min-width: 920px; }
        .eval-table th {
          text-align: left;
          padding: 0 10px 10px 0;
          border-bottom: 1px solid var(--c-border);
          white-space: nowrap;
        }
        .eval-table th:last-child,
        .eval-table td:last-child { padding-right: 0; }
        .eval-th {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          border: none;
          background: none;
          padding: 0;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: var(--c-muted);
          cursor: pointer;
        }
        .eval-th:hover { color: var(--c-heading); }
        .eval-th.active { color: var(--purple); }
        .eval-caret { font-size: 10px; }
        .eval-table td {
          padding: 10px 10px 10px 0;
          font-size: 13px;
          color: var(--c-text);
          border-bottom: 1px solid var(--c-border);
          vertical-align: top;
        }
        .eval-table tr:last-child td { border-bottom: none; }
        .eval-num { font-family: var(--mono); font-variant-numeric: tabular-nums; }
        .eval-mono { font-family: var(--mono); }
        .eval-tooltip {
          background: var(--c-surface);
          border: 1px solid var(--c-border);
          border-radius: 6px;
          padding: 10px 12px;
          box-shadow: var(--shadow-md);
          font-size: 12px;
          color: var(--c-text);
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .eval-tooltip-metric {
          font-weight: 600;
          color: var(--c-heading);
          margin-bottom: 4px;
        }
        .eval-tooltip span {
          color: var(--c-muted);
          margin-right: 6px;
        }
      `}</style>

      <div className="page-header">
        <div className="page-eyebrow">Offline eval</div>
        <h1 className="page-title">Evaluation</h1>
        <p className="page-desc">
          nDCG@10, Recall@10, and MRR@10 across experiment runs, plus the full scored table.
        </p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading && rows === null && (
        <div className="empty-state">
          <span className="spinner spinner-dark spinner-lg" />
          <p className="empty-desc">Loading experiment runs…</p>
        </div>
      )}

      {rows !== null && rows.length === 0 && (
        <div className="empty-state">
          <p className="empty-title">No experiment runs</p>
          <p className="empty-desc">
            There are no rows in experiments.csv yet. Score a query set with the
            eval CLI to plot nDCG@10, Recall@10, and MRR@10 here.
          </p>
        </div>
      )}

      {rows !== null && rows.length > 0 && (
        <>
          <section className="eval-panel">
            <div className="eval-panel-head">
              <h2>{selectedMetric.label} across runs</h2>
              <div className="eval-metric-field">
                <label htmlFor="eval-chart-metric">Metric</label>
                <select
                  id="eval-chart-metric"
                  className="param-select"
                  value={chartMetric}
                  onChange={event => setChartMetric(event.target.value as ChartMetric)}
                >
                  {CHART_METRICS.map(item => (
                    <option key={item.key} value={item.key}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="eval-plot">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 12, left: 8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--c-border)" />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: 'var(--c-muted)', fontSize: 11 }}
                    tickLine={false}
                    axisLine={{ stroke: 'var(--c-border)' }}
                  />
                  <YAxis
                    domain={[0, 1]}
                    tick={{ fill: 'var(--c-muted)', fontSize: 11 }}
                    tickFormatter={value => Number(value).toFixed(2)}
                    tickLine={false}
                    axisLine={{ stroke: 'var(--c-border)' }}
                    width={44}
                  />
                  <Tooltip
                    content={<ExperimentTooltip metric={chartMetric} />}
                  />
                  <Line
                    type="monotone"
                    dataKey={selectedMetric.key}
                    name={selectedMetric.label}
                    stroke={PURPLE}
                    strokeWidth={2}
                    dot={{ r: 3, fill: PURPLE }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>

          <section className="eval-panel">
            <h2>Experiment runs</h2>
            <div className="eval-table-wrap">
              <table className="eval-table">
                <thead>
                  <tr>
                    {COLUMNS.map(col => {
                      const active = col.key === sortKey
                      return (
                        <th
                          key={col.key}
                          aria-sort={
                            active
                              ? sortDir === 'asc'
                                ? 'ascending'
                                : 'descending'
                              : 'none'
                          }
                        >
                          <button
                            type="button"
                            className={active ? 'eval-th active' : 'eval-th'}
                            onClick={() => onSort(col.key)}
                          >
                            {col.label}
                            {active && (
                              <span className="eval-caret" aria-hidden="true">
                                {sortDir === 'asc' ? '↑' : '↓'}
                              </span>
                            )}
                          </button>
                        </th>
                      )
                    })}
                  </tr>
                </thead>
                <tbody>
                  {tableRows.map((row, index) => (
                    <tr key={`${row.timestamp}-${row.tag}-${index}`}>
                      <td className="eval-num">{formatTime(row.timestamp)}</td>
                      <td className="eval-mono">{row.commit}</td>
                      <td>{row.tag}</td>
                      <td className="eval-num">{row.alpha}</td>
                      <td>{row.normalization}</td>
                      <td className="eval-mono">{row.model}</td>
                      <td>{row.preprocessing}</td>
                      <td className="eval-num">{formatMetric(row.ndcg10)}</td>
                      <td className="eval-num">{formatMetric(row.recall10)}</td>
                      <td className="eval-num">{formatMetric(row.mrr10)}</td>
                      <td className="eval-num">{row.n_queries}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
