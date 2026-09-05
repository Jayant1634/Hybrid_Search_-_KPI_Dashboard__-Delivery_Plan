import { type HealthResponse } from '../api'
import { INFO_TIPS } from '../infoTips'
import InfoTip, { InfoLabel } from './InfoTip'

interface Props {
  health: HealthResponse
}

function shortCommit(commit: string): string {
  if (!commit) return '—'
  return commit.length > 7 ? commit.slice(0, 7) : commit
}

export default function HealthGrid({ health }: Props) {
  const ok = health.status === 'ok'
  return (
    <div className="health-grid">
      <InfoTip className="health-card hc-primary" label="API Status" hint={INFO_TIPS.apiStatus}>
        <div className="hc-eyebrow"><InfoLabel text="API Status" /></div>
        <div className="hc-value">
          <span className={`status-badge ${ok ? 'badge-ok' : 'badge-err'}`}>
            <span className="badge-dot" />
            {ok ? 'Operational' : 'Degraded'}
          </span>
        </div>
      </InfoTip>

      <InfoTip className="health-card" label="Version" hint={INFO_TIPS.version}>
        <div className="hc-eyebrow"><InfoLabel text="Version" /></div>
        <div className="hc-value mono">{health.version || '—'}</div>
      </InfoTip>

      <InfoTip className="health-card hc-wide" label="Commit" hint={INFO_TIPS.commit}>
        <div className="hc-eyebrow"><InfoLabel text="Commit" /></div>
        <div className="hc-commit">
          <div className="hc-value mono">{shortCommit(health.commit)}</div>
          {health.commit_message ? (
            <div className="hc-commit-name">{health.commit_message}</div>
          ) : null}
        </div>
      </InfoTip>

      {health.index ? (
        <>
          <InfoTip className="health-card" label="Documents" hint={INFO_TIPS.documents}>
            <div className="hc-eyebrow"><InfoLabel text="Documents" /></div>
            <div className="hc-metric">{(health.index.doc_count ?? 0).toLocaleString()}</div>
          </InfoTip>
          <InfoTip className="health-card" label="Vectors" hint={INFO_TIPS.vectorCount}>
            <div className="hc-eyebrow"><InfoLabel text="Vectors" /></div>
            <div className="hc-metric">{(health.index.vector_count ?? 0).toLocaleString()}</div>
          </InfoTip>
          <InfoTip className="health-card" label="Embedding Dim." hint={INFO_TIPS.embeddingDim}>
            <div className="hc-eyebrow"><InfoLabel text="Embedding Dim." /></div>
            <div className="hc-metric">{health.index.dimension}</div>
          </InfoTip>
          <InfoTip className="health-card" label="Granularity" hint={INFO_TIPS.granularity}>
            <div className="hc-eyebrow"><InfoLabel text="Granularity" /></div>
            <div className="hc-value mono sm">{health.index.granularity}</div>
          </InfoTip>
          <InfoTip className="health-card hc-wide" label="Index Model" hint={INFO_TIPS.indexModel}>
            <div className="hc-eyebrow"><InfoLabel text="Index Model" /></div>
            <div className="hc-value mono sm">{health.index.model}</div>
          </InfoTip>
          <InfoTip className="health-card hc-wide" label="Built At" hint={INFO_TIPS.builtAt}>
            <div className="hc-eyebrow"><InfoLabel text="Built At" /></div>
            <div className="hc-value mono sm">{health.index.built_at}</div>
          </InfoTip>
          <InfoTip className="health-card hc-full" label="Corpus Hash" hint={INFO_TIPS.corpusHash}>
            <div className="hc-eyebrow"><InfoLabel text="Corpus Hash" /></div>
            <div className="hc-value mono sm muted">{health.index.corpus_hash}</div>
          </InfoTip>
        </>
      ) : (
        <InfoTip className="health-card hc-wide" label="Index" hint={INFO_TIPS.indexMissing}>
          <div className="hc-eyebrow"><InfoLabel text="Index" /></div>
          <div className="hc-value muted">Not loaded</div>
        </InfoTip>
      )}
    </div>
  )
}
