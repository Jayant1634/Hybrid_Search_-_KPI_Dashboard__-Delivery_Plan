import { useCallback, useEffect, useState } from 'react'
import { getLogs, type LogEntry } from '../api'

type SeverityFilter = 'all' | 'debug' | 'info' | 'warning' | 'error'

interface Filters {
  severity: SeverityFilter
  from: string
  to: string
  limit: number
}

type LogRow = LogEntry & Record<string, unknown>

const DEFAULTS: Filters = {
  severity: 'all',
  from: '',
  to: '',
  limit: 100,
}

const TABLE_KEYS = new Set(['created_at', 'severity', 'message'])

function clampLimit(value: number): number {
  if (!Number.isFinite(value)) return DEFAULTS.limit
  return Math.min(100, Math.max(1, Math.trunc(value)))
}

function levelParam(severity: SeverityFilter): string | undefined {
  if (severity === 'all') return undefined
  return severity.toUpperCase()
}

function parseTs(value: string): number {
  const ms = Date.parse(value)
  return Number.isNaN(ms) ? 0 : ms
}

function inRange(row: LogRow, fromLocal: string, toLocal: string): boolean {
  const ts = parseTs(row.created_at)
  if (fromLocal) {
    const start = new Date(fromLocal).getTime()
    if (!Number.isNaN(start) && ts < start) return false
  }
  if (toLocal) {
    const end = new Date(toLocal).getTime()
    if (!Number.isNaN(end) && ts > end) return false
  }
  return true
}

async function fetchLogs(filters: Filters): Promise<LogRow[]> {
  const fromIso = filters.from ? new Date(filters.from) : null
  const toIso = filters.to ? new Date(filters.to) : null
  const rows = (await getLogs({
    level: levelParam(filters.severity),
    from: fromIso && !Number.isNaN(fromIso.getTime()) ? fromIso.toISOString() : undefined,
    to: toIso && !Number.isNaN(toIso.getTime()) ? toIso.toISOString() : undefined,
    limit: filters.limit,
  })) as LogRow[]
  return rows.filter(row => inRange(row, filters.from, filters.to))
}

function formatTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function extraJson(row: LogRow): string {
  const extra: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(row)) {
    if (!TABLE_KEYS.has(key)) extra[key] = value
  }
  return JSON.stringify(extra, null, 2)
}

function rowKey(row: LogRow, index: number): string {
  return `${row.created_at}-${row.severity}-${row.request_id ?? ''}-${index}`
}

function severityClass(severity: string): string {
  const upper = severity.toUpperCase()
  if (upper === 'ERROR' || upper === 'CRITICAL') return 'badge-err'
  if (upper === 'WARNING') return 'debug-badge-warn'
  return 'badge-ok'
}

export default function DebugPage() {
  const [draft, setDraft] = useState<Filters>(DEFAULTS)
  const [applied, setApplied] = useState<Filters>(DEFAULTS)
  const [rows, setRows] = useState<LogRow[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState<string | null>(null)

  const load = useCallback(async (filters: Filters) => {
    setLoading(true)
    setError(null)
    setOpen(null)
    try {
      const next = await fetchLogs(filters)
      setRows(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(DEFAULTS)
  }, [load])

  function apply() {
    const next = { ...draft, limit: clampLimit(draft.limit) }
    setDraft(next)
    setApplied(next)
    void load(next)
  }

  function reset() {
    setDraft(DEFAULTS)
    setApplied(DEFAULTS)
    void load(DEFAULTS)
  }

  return (
    <div className="page-container page-container-wide">
      <style>{`
        .debug-dt { width: 210px; }
        .debug-actions { display: flex; gap: 10px; align-items: flex-end; }
        .debug-panel {
          background: var(--c-surface);
          border: 1px solid var(--c-border);
          border-radius: 8px;
          padding: 20px 22px;
          box-shadow: var(--shadow-sm);
        }
        .debug-table-wrap { overflow-x: auto; }
        .debug-table { width: 100%; border-collapse: collapse; }
        .debug-table th {
          text-align: left;
          font-size: 11px;
          font-weight: 600;
          letter-spacing: 0.06em;
          text-transform: uppercase;
          color: var(--c-muted);
          padding: 0 12px 10px 0;
          border-bottom: 1px solid var(--c-border);
          white-space: nowrap;
        }
        .debug-table td {
          padding: 10px 12px 10px 0;
          font-size: 13px;
          color: var(--c-text);
          border-bottom: 1px solid var(--c-border);
          vertical-align: top;
        }
        .debug-table tr:last-child td { border-bottom: none; }
        .debug-table .debug-expand-row td { border-bottom: 1px solid var(--c-border); }
        .debug-msg { word-break: break-word; }
        .debug-num { font-family: var(--mono); font-variant-numeric: tabular-nums; }
        .debug-expand {
          border: none;
          background: var(--c-surface-2);
          color: var(--c-secondary);
          border-radius: 4px;
          width: 28px;
          height: 28px;
          font-size: 14px;
          line-height: 1;
        }
        .debug-expand[aria-expanded='true'] { color: var(--purple); background: var(--purple-tint); }
        .debug-json {
          margin: 0;
          padding: 12px 14px;
          background: var(--c-bg-alt);
          border: 1px solid var(--c-border);
          border-radius: 6px;
          font-family: var(--mono);
          font-size: 12px;
          line-height: 1.5;
          color: var(--c-text);
          white-space: pre-wrap;
          word-break: break-word;
        }
        .debug-badge-warn {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          font-size: 13px;
          font-weight: 600;
          padding: 4px 12px;
          border-radius: 4px;
          background: rgba(196, 122, 0, 0.12);
          color: var(--warning);
        }
      `}</style>

      <div className="page-header">
        <div className="page-eyebrow">Observability</div>
        <h1 className="page-title">Debug</h1>
        <p className="page-desc">
          Structured logs. Choose all to show every level, not just errors.
        </p>
      </div>

      <div className="search-panel">
        <div className="search-params" style={{ borderTop: 'none', paddingTop: 0 }}>
          <div className="param-group">
            <label className="param-label" htmlFor="debug-severity">Severity</label>
            <select
              id="debug-severity"
              className="param-select"
              value={draft.severity}
              onChange={e => setDraft(f => ({ ...f, severity: e.target.value as SeverityFilter }))}
            >
              <option value="all">all (every level)</option>
              <option value="debug">debug</option>
              <option value="info">info</option>
              <option value="warning">warning</option>
              <option value="error">error</option>
            </select>
          </div>
          <div className="param-group">
            <label className="param-label" htmlFor="debug-from">From</label>
            <input
              id="debug-from"
              type="datetime-local"
              className="param-input debug-dt"
              value={draft.from}
              onChange={e => setDraft(f => ({ ...f, from: e.target.value }))}
            />
          </div>
          <div className="param-group">
            <label className="param-label" htmlFor="debug-to">To</label>
            <input
              id="debug-to"
              type="datetime-local"
              className="param-input debug-dt"
              value={draft.to}
              onChange={e => setDraft(f => ({ ...f, to: e.target.value }))}
            />
          </div>
          <div className="param-group">
            <label className="param-label" htmlFor="debug-limit">Limit</label>
            <input
              id="debug-limit"
              type="number"
              className="param-input"
              min={1}
              max={100}
              value={draft.limit}
              onChange={e => setDraft(f => ({ ...f, limit: clampLimit(Number(e.target.value)) }))}
            />
          </div>
          <div className="debug-actions">
            <button type="button" className="btn-primary" onClick={apply} disabled={loading}>
              Apply
            </button>
            <button type="button" className="btn-secondary" onClick={reset} disabled={loading}>
              Reset
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading && rows === null && (
        <div className="empty-state">
          <span className="spinner spinner-dark spinner-lg" />
          <p className="empty-desc">Loading logs…</p>
        </div>
      )}

      {rows !== null && rows.length === 0 && !loading && (
        <div className="empty-state">
          <p className="empty-title">No logs</p>
          <p className="empty-desc">
            Nothing matched {applied.severity === 'all' ? 'all severities' : applied.severity}
            {applied.from || applied.to ? ' in this time range' : ''}.
          </p>
        </div>
      )}

      {rows !== null && rows.length > 0 && (
        <section className="debug-panel">
          <div className="debug-table-wrap">
            <table className="debug-table">
              <thead>
                <tr>
                  <th aria-hidden="true" />
                  <th>Time</th>
                  <th>Severity</th>
                  <th>Message</th>
                  <th>Request</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => {
                  const key = rowKey(row, index)
                  const expanded = open === key
                  return (
                    <LogRows
                      key={key}
                      row={row}
                      rowId={key}
                      expanded={expanded}
                      onToggle={() => setOpen(expanded ? null : key)}
                    />
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}

function LogRows({
  row,
  rowId,
  expanded,
  onToggle,
}: {
  row: LogRow
  rowId: string
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <>
      <tr>
        <td>
          <button
            type="button"
            className="debug-expand"
            aria-expanded={expanded}
            aria-controls={`${rowId}-json`}
            onClick={onToggle}
          >
            {expanded ? '▾' : '▸'}
          </button>
        </td>
        <td className="debug-num">{formatTime(row.created_at)}</td>
        <td>
          <span className={`status-badge ${severityClass(row.severity)}`}>
            {row.severity}
          </span>
        </td>
        <td className="debug-msg">{row.message}</td>
        <td className="debug-num">{row.request_id ?? '—'}</td>
      </tr>
      {expanded && (
        <tr className="debug-expand-row">
          <td colSpan={5}>
            <pre id={`${rowId}-json`} className="debug-json">{extraJson(row)}</pre>
          </td>
        </tr>
      )}
    </>
  )
}
