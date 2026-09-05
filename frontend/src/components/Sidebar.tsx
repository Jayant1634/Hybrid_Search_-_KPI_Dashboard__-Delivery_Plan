import ThemeToggle from './ThemeToggle'
import type { Page } from '../App'

interface Props {
  current: Page
  onNavigate: (p: Page) => void
  dark: boolean
  onToggleTheme: () => void
  indexing?: boolean
  indexingPercent?: number
  indexingGranularity?: string | null
}

const NAV: { page: Page; label: string; icon: React.ReactNode }[] = [
  {
    page: 'home',
    label: 'Home',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M2 6.5L8 2l6 4.5V14H10v-3H6v3H2V6.5z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    page: 'search',
    label: 'Search',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.4" />
        <path d="M11 11l2.5 2.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    page: 'kpis',
    label: 'KPIs',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M3 12V8M8 12V4M13 12V6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    page: 'evaluation',
    label: 'Evaluation',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect x="3" y="2.5" width="10" height="11" rx="1.2" stroke="currentColor" strokeWidth="1.4" />
        <path d="M5.5 6h5M5.5 8.5h5M5.5 11h3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    page: 'debug',
    label: 'Debug',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <path d="M4 8h8M6.5 5.5L5 3.5M9.5 5.5L11 3.5M6.5 10.5L5 12.5M9.5 10.5L11 12.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        <circle cx="8" cy="8" r="2.6" stroke="currentColor" strokeWidth="1.4" />
      </svg>
    ),
  },
  {
    page: 'health',
    label: 'System',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect x="1.5" y="3.5" width="13" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.4" />
        <path d="M5 8h1.5l1-2 1.5 4 1-2H11" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
]

export default function Sidebar({
  current,
  onNavigate,
  dark,
  onToggleTheme,
  indexing = false,
  indexingPercent = 0,
  indexingGranularity = null,
}: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <rect width="28" height="28" rx="4" fill="#7823DC" />
          <circle cx="14" cy="14" r="5.5" stroke="#fff" strokeWidth="1.6" />
          <circle cx="14" cy="14" r="2" fill="#fff" />
        </svg>
        <div className="sidebar-logo-text">
          <span className="sidebar-wordmark">Kearney</span>
          <span className="sidebar-subword">Search</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-nav-group-label">Navigation</div>
        {NAV.map(({ page, label, icon }) => (
          <button
            key={page}
            className={`sidebar-nav-item ${current === page ? 'active' : ''}`}
            onClick={() => onNavigate(page)}
          >
            <span className="sidebar-nav-icon">{icon}</span>
            {label}
            {page === 'health' && indexing && (
              <span className="sidebar-running-badge">
                Running {Math.round(indexingPercent)}%
              </span>
            )}
            {current === page && <span className="sidebar-active-indicator" />}
          </button>
        ))}
        {indexing && (
          <div className="sidebar-indexing-note" role="status">
            Indexing {indexingGranularity ?? 'corpus'} · {Math.round(indexingPercent)}%
          </div>
        )}
      </nav>

      <div className="sidebar-bottom">
        <button
          className={`sidebar-nav-item ${current === 'settings' ? 'active' : ''}`}
          onClick={() => onNavigate('settings')}
        >
          <span className="sidebar-nav-icon">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="2.2" stroke="currentColor" strokeWidth="1.4" />
              <path
                d="M8 1.5l.6 1.4 1.5-.3.9 1.3 1.4.6-.3 1.5 1.3.9-.6 1.4.3 1.5-1.4.6-.9 1.3-1.5-.3L8 14.5l-.6-1.4-1.5.3-.9-1.3-1.4-.6.3-1.5-1.3-.9.6-1.4-.3-1.5 1.4-.6.9-1.3 1.5.3L8 1.5z"
                stroke="currentColor"
                strokeWidth="1.2"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          Settings
          {current === 'settings' && <span className="sidebar-active-indicator" />}
        </button>
        <ThemeToggle dark={dark} onToggle={onToggleTheme} />
      </div>
    </aside>
  )
}
