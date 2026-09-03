import type { Page } from '../App'

interface Props {
  current: string
  onNavigate(p: Page): void
}

const LINKS: [Page, string][] = [
  ['home', 'Home'],
  ['search', 'Search'],
  ['kpis', 'KPIs'],
  ['evaluation', 'Evaluation'],
  ['debug', 'Debug'],
  ['health', 'System'],
]

export default function Navbar({ current, onNavigate }: Props) {
  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <button className="navbar-brand" onClick={() => onNavigate('home')}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <rect width="20" height="20" rx="3" fill="#7823DC" />
            <circle cx="10" cy="10" r="4" stroke="#fff" strokeWidth="1.5" />
            <circle cx="10" cy="10" r="1.5" fill="#fff" />
          </svg>
          <span className="navbar-brand-text">Search Intelligence</span>
        </button>

        <div className="navbar-links">
          {LINKS.map(([page, label]) => (
            <button
              key={page}
              className={`navbar-link ${current === page ? 'active' : ''}`}
              onClick={() => onNavigate(page)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </nav>
  )
}
