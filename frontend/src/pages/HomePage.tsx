import VantaHero from '../components/VantaHero'
import Navbar from '../components/Navbar'

type Page = 'home' | 'search' | 'health'

interface Props {
  dark: boolean
  onNavigate: (p: Page) => void
}

const FEATURES = [
  {
    title: 'Hybrid Retrieval',
    body: 'Combines BM25 lexical scoring with dense vector search. Alpha-weighted fusion produces consistently better ranking than either method alone.',
  },
  {
    title: 'Explainable Scores',
    body: 'Every result surfaces its BM25 raw, vector raw, normalised, and hybrid scores — full transparency into why each document ranks where it does.',
  },
  {
    title: 'Tunable at Query Time',
    body: 'Adjust α, top-k, and normalisation strategy (min-max or z-score) per request. No reindex required.',
  },
  {
    title: 'Relevance Feedback',
    body: 'Capture thumbs-up / thumbs-down signals per result, tied to a request ID, for future model improvement loops.',
  },
  {
    title: 'Filter Support',
    body: 'Pre-ranking constraints on source, creation date range, and more — reducing candidate sets before fusion scoring.',
  },
  {
    title: 'Observable System',
    body: 'Live /health endpoint exposes version, commit, index model, corpus hash, and document count. No guesswork in production.',
  },
]

export default function HomePage({ dark, onNavigate }: Props) {
  return (
    <div className="home-page">
      <Navbar current="home" onNavigate={onNavigate} />

      <div className="home-hero-wrap">
        <VantaHero dark={dark} />
        <div className="home-hero-content">
          <div className="home-eyebrow">Kearney · Search Intelligence</div>
          <h1 className="home-title">
            Enterprise Hybrid<br />Document Retrieval
          </h1>
          <p className="home-subtitle">
            BM25 × dense vector fusion — precision retrieval with full score transparency,<br />
            built for analytical and consulting workflows.
          </p>
          <div className="home-ctas">
            <button className="btn-primary" onClick={() => onNavigate('search')}>
              Open Search
            </button>
            <button className="btn-secondary" onClick={() => onNavigate('health')}>
              System Status
            </button>
          </div>
        </div>
      </div>

      <div className="home-body">
        <section className="home-section">
          <div className="section-label">Capabilities</div>
          <h2 className="section-heading">What the system does</h2>
          <div className="features-grid">
            {FEATURES.map(f => (
              <div key={f.title} className="feature-card">
                <div className="feature-marker" />
                <h3 className="feature-title">{f.title}</h3>
                <p className="feature-body">{f.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="home-section home-cta-section">
          <div className="cta-block">
            <div className="section-label">Get started</div>
            <h2 className="section-heading">Run your first query</h2>
            <p className="cta-desc">
              Submit a natural-language query and receive ranked results with
              full BM25, vector, and hybrid score breakdowns in milliseconds.
            </p>
            <button className="btn-primary" onClick={() => onNavigate('search')}>
              Launch Search
            </button>
          </div>
          <div className="stat-block">
            <div className="stat-item">
              <div className="stat-number">α</div>
              <div className="stat-desc">Tunable fusion weight</div>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <div className="stat-number">2</div>
              <div className="stat-desc">Normalisation strategies</div>
            </div>
            <div className="stat-divider" />
            <div className="stat-item">
              <div className="stat-number">50</div>
              <div className="stat-desc">Max results per query</div>
            </div>
          </div>
        </section>
      </div>

      <footer className="home-footer">
        <span>Kearney Search Intelligence</span>
        <span className="footer-sep">·</span>
        <span>Hybrid Search API v0.1.0</span>
        <span className="footer-sep">·</span>
        <span>CPU-only · Python 3.11+</span>
      </footer>
    </div>
  )
}
