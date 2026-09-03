import { useState, useEffect, useCallback } from 'react'
import HealthGrid from '../components/HealthGrid'
import { getHealth, type HealthResponse } from '../api'

export default function HealthPage() {
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

  return (
    <div className="page-container">
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

      {!health && loading && (
        <div className="empty-state">
          <span className="spinner spinner-dark spinner-lg" />
          <p className="empty-desc">Checking system status…</p>
        </div>
      )}
    </div>
  )
}
