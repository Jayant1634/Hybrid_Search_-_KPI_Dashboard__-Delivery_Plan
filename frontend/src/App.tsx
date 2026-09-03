import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import HealthPage from './pages/HealthPage'
import SettingsPage from './pages/SettingsPage'
import './App.css'

type Page = 'home' | 'search' | 'health' | 'settings'

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

  if (page === 'home') {
    return <HomePage dark={dark} onNavigate={setPage} />
  }

  return (
    <div className="app-shell">
      <Sidebar current={page} onNavigate={setPage} dark={dark} onToggleTheme={toggle} />
      <main className="app-main">
        {page === 'search' && <SearchPage />}
        {page === 'health' && <HealthPage />}
        {page === 'settings' && <SettingsPage />}
      </main>
    </div>
  )
}
