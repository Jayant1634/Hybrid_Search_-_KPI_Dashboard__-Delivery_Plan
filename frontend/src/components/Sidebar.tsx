import ThemeToggle from './ThemeToggle'

type Page = 'home' | 'search' | 'health'

interface Props {
  current: Page
  onNavigate: (p: Page) => void
  dark: boolean
  onToggleTheme: () => void
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

export default function Sidebar({ current, onNavigate, dark, onToggleTheme }: Props) {
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
            {current === page && <span className="sidebar-active-indicator" />}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <ThemeToggle dark={dark} onToggle={onToggleTheme} />
        <div className="sidebar-version">v0.1.0 · Hybrid Search API</div>
      </div>
    </aside>
  )
}
