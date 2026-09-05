import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import HealthPage from './pages/HealthPage'
import SettingsPage from './pages/SettingsPage'
import KpisPage from './pages/KpisPage'
import EvaluationPage from './pages/EvaluationPage'
import DebugPage from './pages/DebugPage'
import { getHealth } from './api'
import { useReindexJob } from './useReindexJob'
import './App.css'

export type Page = 'home' | 'search' | 'health' | 'settings' | 'kpis' | 'evaluation' | 'debug'

function useTheme() {
  const [dark, setDark] = useState<boolean>(() => {
    const stored = localStorage.getItem('theme')
    if (stored) return stored === 'dark'
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  return { dark, toggle: () => setDark(d => !d) }
}

export default function App() {
  const [page, setPage] = useState<Page>('home')
  const { dark, toggle } = useTheme()
  const [build, setBuild] = useState<{ version: string; commit: string } | null>(null)
  const reindexJob = useReindexJob(page !== 'home')

  useEffect(() => {
    let cancelled = false
    getHealth()
      .then(health => {
        if (!cancelled) setBuild({ version: health.version, commit: health.commit })
      })
      .catch(() => {
        /* footer stays empty if /health is down */
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (page === 'home') {
    return <HomePage dark={dark} onToggleTheme={toggle} onNavigate={setPage} />
  }

  return (
    <div className="app-shell">
      <Sidebar
        current={page}
        onNavigate={setPage}
        dark={dark}
        onToggleTheme={toggle}
        indexing={reindexJob.running}
        indexingPercent={reindexJob.progress?.percent ?? 0}
        indexingGranularity={reindexJob.progress?.granularity ?? null}
      />
      <main className="app-main">
        {page === 'search' && <SearchPage />}
        {page === 'health' && (
          <HealthPage
            progress={reindexJob.progress}
            reindexError={reindexJob.error}
            reindexNote={reindexJob.note}
            onSwitch={reindexJob.start}
          />
        )}
        {page === 'settings' && <SettingsPage />}
        {page === 'kpis' && <KpisPage />}
        {page === 'evaluation' && <EvaluationPage />}
        {page === 'debug' && <DebugPage />}
        <footer className="app-footer">
          <div className="app-footer-inner">
            <span className="app-footer-brand">Kearney Search Intelligence</span>
            <div className="app-footer-meta">
              {build ? (
                <>
                  <span>{build.version}</span>
                  <span className="footer-sep">·</span>
                  <span>{build.commit}</span>
                </>
              ) : (
                <span>CPU-only · Python 3.11+</span>
              )}
            </div>
          </div>
        </footer>
      </main>
    </div>
  )
}
