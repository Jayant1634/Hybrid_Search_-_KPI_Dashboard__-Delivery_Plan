import { useState, useEffect, useCallback } from 'react'
import HealthGrid from '../components/HealthGrid'
import {
  getHealth,
  type HealthResponse,
  type IndexGranularity,
  type ReindexProgress,
} from '../api'

const GRANULARITIES: { value: IndexGranularity; label: string; hint: string }[] = [
  { value: 'document', label: 'Document', hint: 'One vector per file.' },
  {
    value: 'sentence',
    label: 'Sentence',
    hint: 'One vector per packed chunk; covers the whole file.',
  },
]

interface Props {
  progress: ReindexProgress | null
  reindexError: string | null
  reindexNote: string | null
  onSwitch: (granularity: IndexGranularity) => void
}

export default function HealthPage({
  progress,
  reindexError,
  reindexNote,
  onSwitch,
}: Props) {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastChecked, setLastChecked] = useState<string | null>(null)

  const fetchHealth = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const h = await getHealth()
      setHealth(h)
      setLastChecked(new Date().toLocaleTimeString())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHealth()
  }, [fetchHealth])

  useEffect(() => {
    if (progress && !progress.running && progress.percent === 100) {
      void fetchHealth()
    }
  }, [progress?.running, progress?.percent, fetchHealth])

  const reindexing = progress?.running ? progress.granularity : null

  return (
    <div className="page-container">
      <style>{`
        .page-container { gap: 16px; padding-top: 28px; padding-bottom: 24px; }
        .page-title { font-size: 26px; }
        .page-desc { font-size: 13px; max-width: 58ch; }
        .page-header-row { align-items: center; }
        .reindex-head { align-items: center; }
        .reindex-head .page-eyebrow { margin-bottom: 2px; }
      `}</style>
      <div className="page-header page-header-row">
        <div>
          <div className="page-eyebrow">Observability</div>
          <h1 className="page-title">System Health</h1>
          <p className="page-desc">
            Live status of the Hybrid Search API and the loaded document index.
          </p>
        </div>
        <div className="header-actions">
          {lastChecked && <span className="last-checked">Checked {lastChecked}</span>}
          <button className="btn-secondary" onClick={fetchHealth} disabled={loading}>
            {loading ? <span className="spinner spinner-dark" /> : 'Refresh'}
          </button>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {health && <HealthGrid health={health} />}

      {health?.index && (
        <div className="reindex-panel">
          <div className="reindex-head">
            <div>
              <div className="page-eyebrow">Index granularity</div>
              <p className="page-desc">
                What each vector represents. Switching re-encodes the corpus and
                can take a while on large corpora.
              </p>
            </div>
            <div className="reindex-controls" role="group" aria-label="Index granularity">
              {GRANULARITIES.map(option => {
                const active = health.index?.granularity === option.value && !reindexing
                const busy = reindexing === option.value
                return (
                  <button
                    key={option.value}
                    type="button"
                    className={`btn-secondary reindex-btn${active ? ' is-active' : ''}`}
                    title={option.hint}
                    aria-pressed={active}
                    disabled={reindexing !== null}
                    onClick={() => onSwitch(option.value)}
                  >
                    {busy ? <span className="spinner spinner-dark" /> : option.label}
                  </button>
                )
              })}
            </div>
          </div>
          {reindexing && (
            <div className="reindex-status">
              <div className="reindex-status-line">
                {progress?.phase === 'finishing'
                  ? `Finishing ${reindexing} index…`
                  : `Rebuilding as ${reindexing}… ${Math.round(progress?.percent ?? 0)}%`}
                {progress && progress.total > 0 && progress.phase !== 'finishing' && (
                  <span className="reindex-status-counts">
                    {' '}
                    ({progress.done.toLocaleString()}/{progress.total.toLocaleString()} chunks)
                  </span>
                )}
              </div>
              <div
                className="reindex-bar"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(progress?.percent ?? 0)}
                aria-label="Reindex progress"
              >
                <div
                  className="reindex-bar-fill"
                  style={{ width: `${Math.min(100, Math.max(0, progress?.percent ?? 0))}%` }}
                />
              </div>
            </div>
          )}
          {reindexNote && !reindexing && (
            <div className="reindex-status is-ok">{reindexNote}</div>
          )}
          {reindexError && <div className="error-banner">{reindexError}</div>}
        </div>
      )}

      {!health && loading && (
        <div className="empty-state">
          <span className="spinner spinner-dark spinner-lg" />
          <p className="empty-desc">Checking system status…</p>
        </div>
      )}
    </div>
  )
}
