import { type HealthResponse } from '../api'

interface Props {
  health: HealthResponse
}

export default function HealthGrid({ health }: Props) {
  const ok = health.status === 'ok'
  return (
    <div className="health-grid">
      <div className="health-card hc-primary">
        <div className="hc-eyebrow">API Status</div>
        <div className="hc-value">
          <span className={`status-badge ${ok ? 'badge-ok' : 'badge-err'}`}>
            <span className="badge-dot" />
            {ok ? 'Operational' : 'Degraded'}
          </span>
        </div>
      </div>

      <div className="health-card">
        <div className="hc-eyebrow">Version</div>
        <div className="hc-value mono">{health.version || '—'}</div>
      </div>

      <div className="health-card">
        <div className="hc-eyebrow">Commit</div>
        <div className="hc-value mono">{health.commit ? health.commit.slice(0, 7) : '—'}</div>
      </div>

      {health.index ? (
        <>
          <div className="health-card hc-wide">
            <div className="hc-eyebrow">Index Model</div>
            <div className="hc-value mono sm">{health.index.model}</div>
          </div>
          <div className="health-card">
            <div className="hc-eyebrow">Documents</div>
            <div className="hc-metric">{health.index.doc_count.toLocaleString()}</div>
          </div>
          <div className="health-card">
            <div className="hc-eyebrow">Embedding Dim.</div>
            <div className="hc-metric">{health.index.dimension}</div>
          </div>
          <div className="health-card hc-wide">
            <div className="hc-eyebrow">Built At</div>
            <div className="hc-value mono sm">{health.index.built_at}</div>
          </div>
          <div className="health-card hc-full">
            <div className="hc-eyebrow">Corpus Hash</div>
            <div className="hc-value mono sm muted">{health.index.corpus_hash}</div>
          </div>
        </>
      ) : (
        <div className="health-card hc-wide">
          <div className="hc-eyebrow">Index</div>
          <div className="hc-value muted">Not loaded</div>
        </div>
      )}
    </div>
  )
}
