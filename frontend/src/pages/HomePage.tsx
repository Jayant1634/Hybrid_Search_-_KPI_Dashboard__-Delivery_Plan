import { useEffect, useState, type ReactNode } from 'react'
import VantaHero from '../components/VantaHero'
import Navbar from '../components/Navbar'
import { getHealth, type HealthResponse } from '../api'
import type { Page } from '../App'

interface Props {
  dark: boolean
  onToggleTheme: () => void
  onNavigate: (p: Page) => void
}

function Icon({ children }: { children: ReactNode }) {
  return (
    <svg className="home-icon" width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden>
      {children}
    </svg>
  )
}

const ICONS = {
  query: (
    <Icon>
      <circle cx="9.5" cy="9.5" r="5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M13.2 13.2L18 18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </Icon>
  ),
  retrieve: (
    <Icon>
      <path d="M4 6h6M4 11h14M4 16h9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="16.5" cy="6" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="16.5" cy="16" r="2" stroke="currentColor" strokeWidth="1.5" />
    </Icon>
  ),
  gate: (
    <Icon>
      <path d="M4 5h14l-5 6.5V18l-4-2v-4.5L4 5z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </Icon>
  ),
  norm: (
    <Icon>
      <path d="M4 16V8M9 16V5M14 16v-5M18 16V7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </Icon>
  ),
  fuse: (
    <Icon>
      <path d="M4 6h6v10H4zM12 6h6v10h-6z" stroke="currentColor" strokeWidth="1.5" />
      <path d="M10 11h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </Icon>
  ),
  explain: (
    <Icon>
      <rect x="4" y="4" width="14" height="14" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M7 8h8M7 11h8M7 14h5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </Icon>
  ),
  hybrid: (
    <Icon>
      <circle cx="8" cy="11" r="4" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="14" cy="11" r="4" stroke="currentColor" strokeWidth="1.5" />
    </Icon>
  ),
  knobs: (
    <Icon>
      <circle cx="7" cy="11" r="2.2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="15" cy="11" r="2.2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M7 4.5v4M15 4.5v4M7 13.2V17.5M15 13.2V17.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </Icon>
  ),
  layers: (
    <Icon>
      <path d="M11 4l8 4-8 4-8-4 8-4z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M4 12l7 3.5L18 12M4 15.5l7 3.5 7-3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </Icon>
  ),
  search: (
    <Icon>
      <circle cx="9.5" cy="9.5" r="4.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M13 13l4.5 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </Icon>
  ),
  kpis: (
    <Icon>
      <path d="M5 16V11M11 16V6M17 16V9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </Icon>
  ),
  eval: (
    <Icon>
      <rect x="5" y="4" width="12" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 8h6M8 11h6M8 14h3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </Icon>
  ),
  debug: (
    <Icon>
      <circle cx="11" cy="11" r="3" stroke="currentColor" strokeWidth="1.5" />
      <path d="M5 11h3M14 11h3M8.5 8L6.5 5.5M13.5 8l2-2.5M8.5 14l-2 2.5M13.5 14l2 2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </Icon>
  ),
  health: (
    <Icon>
      <rect x="3.5" y="6" width="15" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M7 11h2l1.5-2.5 2 5L14 11h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </Icon>
  ),
  graph: (
    <Icon>
      <circle cx="6" cy="7" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="16" cy="7" r="2" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="11" cy="16" r="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 8l6 0M7.5 9l2.8 5M14.5 9l-2.8 5" stroke="currentColor" strokeWidth="1.5" />
    </Icon>
  ),
}

const WORKFLOW = [
  {
    id: 'query',
    num: '01',
    title: 'Query in',
    detail: 'The text is tokenised for BM25 and encoded with the same MiniLM used at index time.',
    icon: ICONS.query,
  },
  {
    id: 'retrieve',
    num: '02',
    title: 'Dual retrieve',
    detail: 'BM25 and FAISS each return a pool of 50. The union is the candidate set.',
    icon: ICONS.retrieve,
  },
  {
    id: 'gate',
    num: '03',
    title: 'Filter & gate',
    detail: 'Dataset, source, and date filters apply. min_vector drops weak semantic-only hits; a real BM25 match stays.',
    icon: ICONS.gate,
  },
  {
    id: 'norm',
    num: '04',
    title: 'Normalise',
    detail: 'Min-max, z-score, or RRF put BM25 and cosine on one scale before they mix.',
    icon: ICONS.norm,
  },
  {
    id: 'fuse',
    num: '05',
    title: 'Fuse',
    detail: 'hybrid = α · norm_bm25 + (1 − α) · norm_vector. α is live on every request.',
    icon: ICONS.fuse,
  },
  {
    id: 'explain',
    num: '06',
    title: 'Explain',
    detail: 'Each hit carries raw, normalised, and hybrid scores plus a highlighted snippet.',
    icon: ICONS.explain,
  },
] as const

const SAMPLE_QUERIES = [
  'volcanic eruption ash plume',
  'indemnity cap on liability',
  'force majeure delay clause',
]

const FEATURES = [
  {
    title: 'Hybrid retrieval',
    body: 'BM25 and dense vectors each contribute a top-50 pool. The union is scored as α·norm_bm25 + (1−α)·norm_vector. Default α is 0.3 (lean lexical).',
    icon: ICONS.hybrid,
  },
  {
    title: 'Three normalisers',
    body: 'Min-max (default) stretches each side to 0–1. Z-score resists a single BM25 outlier. RRF ignores raw scores and uses 1/(k + rank).',
    icon: ICONS.norm,
  },
  {
    title: 'Tunable at query time',
    body: 'α, top-k (1–50), min-vector gate, and normaliser are per request. RRF needs k. No reindex.',
    icon: ICONS.knobs,
  },
  {
    title: 'Filters before fusion',
    body: 'Restrict to Wikipedia, Kearney contracts, or both. Source-path contains and created-at range shrink the candidate set first.',
    icon: ICONS.gate,
  },
  {
    title: 'Document or sentence index',
    body: 'Document mode stores one vector per file. Sentence mode packs whole sentences into chunks that fit the 512-token window so long files are fully covered.',
    icon: ICONS.layers,
  },
  {
    title: 'Explainable hits',
    body: 'Every result shows BM25 raw/norm, vector raw/norm, and hybrid. Snippets highlight lexical terms and the closest semantic word.',
    icon: ICONS.explain,
  },
]

const SURFACES: { page: Page; title: string; body: string; icon: ReactNode }[] = [
  {
    page: 'search',
    title: 'Search',
    body: 'Run a query, read the score bars, open a document, and mark relevant / not.',
    icon: ICONS.search,
  },
  {
    page: 'kpis',
    title: 'KPIs',
    body: 'p50 / p95 latency, zero-result rate, volume, and a concurrent burst probe.',
    icon: ICONS.kpis,
  },
  {
    page: 'evaluation',
    title: 'Evaluation',
    body: 'nDCG@10, Recall@10, and MRR@10 across tagged experiment runs.',
    icon: ICONS.eval,
  },
  {
    page: 'debug',
    title: 'Debug',
    body: 'Request logs by severity and time window, tied to request IDs.',
    icon: ICONS.debug,
  },
  {
    page: 'health',
    title: 'System',
    body: '/health plus a live reindex switch between document and sentence granularity.',
    icon: ICONS.health,
  },
  {
    page: 'settings',
    title: 'Call graph',
    body: 'Generated file and function graph of this repo — BFS from uncalled roots.',
    icon: ICONS.graph,
  },
]

function WorkflowPanel({ step }: { step: number }) {
  const active = WORKFLOW[step]
  const retrieveOn = step >= 1
  const mergeOn = step >= 2

  return (
    <div className="home-workflow" aria-live="polite">
      <div className="wf-head">
        <span className="wf-kicker">Live path</span>
        <span className="wf-step-count">
          {active.num} / {String(WORKFLOW.length).padStart(2, '0')}
        </span>
      </div>
      <h2 className="wf-title">What happens on a search</h2>

      <ol className="wf-rail">
        {WORKFLOW.map((s, i) => {
          const state = i < step ? 'done' : i === step ? 'active' : 'idle'
          return (
            <li key={s.id} className={`wf-node wf-node-${state}`}>
              <span className="wf-dot" aria-hidden />
              <span className="wf-node-title">{s.title}</span>
            </li>
          )
        })}
      </ol>

      <div className="wf-split" data-on={retrieveOn ? 'true' : 'false'}>
        <div className={`wf-lane ${retrieveOn ? 'is-on' : ''}`}>
          <span className="wf-lane-label">BM25</span>
          <span className="wf-lane-sub">lexical · tokens</span>
        </div>
        <div className="wf-split-join" data-on={mergeOn ? 'true' : 'false'} />
        <div className={`wf-lane ${retrieveOn ? 'is-on' : ''}`}>
          <span className="wf-lane-label">Vector</span>
          <span className="wf-lane-sub">FAISS · MiniLM</span>
        </div>
      </div>

      <div className="wf-detail" key={active.id}>
        <div className="wf-detail-title">{active.title}</div>
        <p className="wf-detail-body">{active.detail}</p>
      </div>

      <div className={`wf-hits ${step === WORKFLOW.length - 1 ? 'is-on' : ''}`}>
        <div className="wf-hit">
          <span className="wf-hit-rank">1</span>
          <span className="wf-hit-bar" style={{ width: '86%' }} />
          <span className="wf-hit-score">0.81</span>
        </div>
        <div className="wf-hit">
          <span className="wf-hit-rank">2</span>
          <span className="wf-hit-bar" style={{ width: '64%' }} />
          <span className="wf-hit-score">0.67</span>
        </div>
        <div className="wf-hit">
          <span className="wf-hit-rank">3</span>
          <span className="wf-hit-bar" style={{ width: '41%' }} />
          <span className="wf-hit-score">0.44</span>
        </div>
      </div>
    </div>
  )
}

export default function HomePage({ dark, onToggleTheme, onNavigate }: Props) {
  const [tick, setTick] = useState(0)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const step = tick % WORKFLOW.length
  const queryIdx = Math.floor(tick / WORKFLOW.length) % SAMPLE_QUERIES.length

  useEffect(() => {
    const id = window.setInterval(() => setTick(t => t + 1), 2200)
    return () => window.clearInterval(id)
  }, [])

  useEffect(() => {
    let cancelled = false
    getHealth()
      .then(h => {
        if (!cancelled) setHealth(h)
      })
      .catch(() => {
        /* chips stay empty if /health is down */
      })
    return () => {
      cancelled = true
    }
  }, [])

  const index = health?.index
  const sample = SAMPLE_QUERIES[queryIdx]

  return (
    <div className="home-page">
      <Navbar current="home" onNavigate={onNavigate} dark={dark} onToggleTheme={onToggleTheme} />

      <div className="home-hero-wrap">
        <VantaHero dark={dark} />
        <div className="home-hero-content">
          <div className="home-hero-copy">
            <div className="home-eyebrow">Kearney · Search Intelligence</div>
            <h1 className="home-title">
              Hybrid search
              <br />
              you can explain
            </h1>
            <p className="home-subtitle">
              BM25 × MiniLM fusion on Wikipedia and Kearney contracts. Every
              rank shows raw, normalised, and hybrid scores — α, top-k, and
              the normaliser change on the request, not the index.
            </p>
            <div className="home-query-chip" key={sample}>
              <span className="home-query-label">example</span>
              <span className="home-query-text">{sample}</span>
            </div>
            <div className="home-ctas">
              <button className="btn-primary" onClick={() => onNavigate('search')}>
                Open Search
              </button>
              <button className="btn-secondary" onClick={() => onNavigate('health')}>
                System Status
              </button>
            </div>
            {index && (
              <div className="home-live-chips">
                <span>
                  {index.doc_count.toLocaleString()} docs
                </span>
                <span className="footer-sep">·</span>
                <span>{index.vector_count.toLocaleString()} vectors</span>
                <span className="footer-sep">·</span>
                <span>{index.granularity}</span>
                <span className="footer-sep">·</span>
                <span>{index.model}</span>
              </div>
            )}
          </div>
          <WorkflowPanel step={step} />
        </div>
      </div>

      <div className="home-body" id="home-body">
        <section className="home-section">
          <div className="section-head">
            <div>
              <div className="section-label">Pipeline</div>
              <h2 className="section-heading">How a query is scored</h2>
            </div>
            <svg className="section-illus" viewBox="0 0 160 56" fill="none" aria-hidden>
              <circle cx="16" cy="28" r="7" stroke="var(--purple)" strokeWidth="1.5" />
              <circle cx="56" cy="16" r="7" stroke="var(--purple)" strokeWidth="1.5" />
              <circle cx="56" cy="40" r="7" stroke="var(--purple-light)" strokeWidth="1.5" />
              <circle cx="96" cy="28" r="7" stroke="var(--purple)" strokeWidth="1.5" />
              <circle cx="136" cy="28" r="7" fill="var(--purple-tint)" stroke="var(--purple)" strokeWidth="1.5" />
              <path d="M23 28h26M63 18l26 8M63 38l26-8M103 28h26" stroke="var(--c-border-strong)" strokeWidth="1.4" />
            </svg>
          </div>
          <div className="pipeline-grid">
            {WORKFLOW.map(s => (
              <article key={s.id} className="pipeline-card">
                <div className="home-icon-row">
                  <span className="home-icon-wrap">{s.icon}</span>
                  <div className="pipeline-num">{s.num}</div>
                </div>
                <h3 className="feature-title">{s.title}</h3>
                <p className="feature-body">{s.detail}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="home-section">
          <div className="section-label">Capabilities</div>
          <h2 className="section-heading">What this build actually does</h2>
          <div className="features-grid">
            {FEATURES.map(f => (
              <div key={f.title} className="feature-card">
                <span className="home-icon-wrap">{f.icon}</span>
                <h3 className="feature-title">{f.title}</h3>
                <p className="feature-body">{f.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="home-section">
          <div className="section-label">Surfaces</div>
          <h2 className="section-heading">Where to go next</h2>
          <div className="surfaces-grid">
            {SURFACES.map(s => (
              <button
                key={s.page}
                type="button"
                className="surface-card"
                onClick={() => onNavigate(s.page)}
              >
                <span className="home-icon-wrap">{s.icon}</span>
                <h3 className="feature-title">{s.title}</h3>
                <p className="feature-body">{s.body}</p>
              </button>
            ))}
          </div>
        </section>

        <section className="home-section home-cta-section">
          <div className="cta-block">
            <div className="section-label">Get started</div>
            <h2 className="section-heading">Run your first query</h2>
            <p className="cta-desc">
              Submit a natural-language query and get ranked documents with
              BM25, vector, and hybrid breakdowns. Feedback attaches to the
              request ID for later eval loops.
            </p>
            <button className="btn-primary" onClick={() => onNavigate('search')}>
              Launch Search
            </button>
          </div>
          <div className="stat-block">
            <svg className="stat-illus" viewBox="0 0 72 72" fill="none" aria-hidden>
              <circle cx="24" cy="36" r="14" stroke="var(--purple)" strokeWidth="1.6" />
              <circle cx="48" cy="36" r="14" stroke="var(--purple-light)" strokeWidth="1.6" />
              <path d="M18 36h12M42 36h12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
              <circle cx="24" cy="36" r="3" fill="var(--purple)" />
              <circle cx="48" cy="36" r="3" fill="var(--purple-light)" />
            </svg>
            <div className="stat-item">
              <div className="stat-number">0.3</div>
              <div className="stat-desc">Default α (lexical lean)</div>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <div className="stat-number">3</div>
              <div className="stat-desc">Normalisers · minmax z RRF</div>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <div className="stat-number">{index ? index.doc_count : '—'}</div>
              <div className="stat-desc">
                {index
                  ? `${index.granularity} · ${index.vector_count} vectors`
                  : 'Docs in the loaded index'}
              </div>
            </div>
          </div>
        </section>
      </div>

      <footer className="home-footer">
        <span>Kearney Search Intelligence</span>
        <span className="footer-sep">·</span>
        <span>{health?.version ?? 'Hybrid Search API'}</span>
        <span className="footer-sep">·</span>
        <span>CPU-only · Python 3.11+</span>
      </footer>
    </div>
  )
}
