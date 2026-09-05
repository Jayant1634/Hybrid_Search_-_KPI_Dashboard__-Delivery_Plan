import { useEffect, useState } from 'react'
import CallGraphView from '../components/CallGraphView'
import InfoTip, { InfoLabel } from '../components/InfoTip'
import type { CallGraphDoc } from '../callgraphTypes'
import { INFO_TIPS } from '../infoTips'

export default function SettingsPage() {
  const [graph, setGraph] = useState<CallGraphDoc | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetch('/callgraph/graph.json')
      .then(async r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}: ${await r.text()}`)
        return r.json() as Promise<CallGraphDoc>
      })
      .then(doc => {
        if (!cancelled) {
          setGraph(doc)
          setError(null)
        }
      })
      .catch(e => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const s = graph?.stats

  return (
    <div className="page-container page-container-wide">
      <div className="page-header">
        <div className="page-eyebrow">Internals</div>
        <h1 className="page-title">Call graph</h1>
        <p className="page-desc">
          Files and functions that nobody calls are the BFS start set. One hop out from those
          roots, then Kahn topological order. Hop along an edge to walk a path.
        </p>
      </div>

      {s && (
        <div className="cg-stats">
          <InfoTip className="cg-stat" label="Files" hint={INFO_TIPS.cgFiles}>
            <div className="cg-stat-value">{s.file_count}</div>
            <div className="cg-stat-label"><InfoLabel text="Files" /></div>
          </InfoTip>
          <InfoTip className="cg-stat" label="Functions" hint={INFO_TIPS.cgFunctions}>
            <div className="cg-stat-value">{s.function_count}</div>
            <div className="cg-stat-label"><InfoLabel text="Functions" /></div>
          </InfoTip>
          <InfoTip className="cg-stat" label="Uncalled files" hint={INFO_TIPS.cgUncalledFiles}>
            <div className="cg-stat-value">{s.uncalled_file_count}</div>
            <div className="cg-stat-label"><InfoLabel text="Uncalled files" /></div>
          </InfoTip>
          <InfoTip className="cg-stat" label="Uncalled functions" hint={INFO_TIPS.cgUncalledFunctions}>
            <div className="cg-stat-value">{s.uncalled_function_count}</div>
            <div className="cg-stat-label"><InfoLabel text="Uncalled functions" /></div>
          </InfoTip>
          <InfoTip className="cg-stat" label="File edges" hint={INFO_TIPS.cgFileEdges}>
            <div className="cg-stat-value">{s.file_edge_count}</div>
            <div className="cg-stat-label"><InfoLabel text="File edges" /></div>
          </InfoTip>
          <InfoTip className="cg-stat" label="Call edges" hint={INFO_TIPS.cgCallEdges}>
            <div className="cg-stat-value">{s.function_edge_count}</div>
            <div className="cg-stat-label"><InfoLabel text="Call edges" /></div>
          </InfoTip>
        </div>
      )}

      {graph && (
        <p className="cg-generated">
          Generated {graph.generated_at} · <code>python -m app.callgraph</code>
        </p>
      )}

      {error && <div className="error-banner">{error}</div>}

      {loading && (
        <div className="empty-state">
          <span className="spinner spinner-dark spinner-lg" />
          <p className="empty-desc">Loading call graph…</p>
        </div>
      )}

      {graph && <CallGraphView graph={graph} />}
    </div>
  )
}
