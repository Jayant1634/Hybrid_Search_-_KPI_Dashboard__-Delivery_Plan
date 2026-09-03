import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import ScoreBar from './ScoreBar'
import {
  getDocument,
  submitFeedback,
  type DocumentDetail,
  type SearchResult,
} from '../api'
import { decodeSnippet, highlightContaining } from '../highlight'

interface Props {
  result: SearchResult
  requestId: string
  rank: number
  query: string
}

function Highlighted({ html, className }: { html: string; className?: string }) {
  return <span className={className} dangerouslySetInnerHTML={{ __html: html }} />
}

function looksLikeUrl(value: string): boolean {
  return /^https?:\/\//i.test(value.trim())
}

function formatCreatedAt(value: string): string {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

export default function ResultCard({ result, requestId, rank, query }: Props) {
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null)
  const [sending, setSending] = useState(false)
  const [open, setOpen] = useState(false)
  const [doc, setDoc] = useState<DocumentDetail | null>(null)
  const [docLoading, setDocLoading] = useState(false)
  const [docError, setDocError] = useState<string | null>(null)

  const handleFeedback = async (relevant: boolean) => {
    if (sending || feedback !== null) return
    setSending(true)
    try {
      await submitFeedback({ request_id: requestId, doc_id: result.doc_id, relevant })
      setFeedback(relevant ? 'up' : 'down')
    } catch {
      /* silent */
    } finally {
      setSending(false)
    }
  }

  const openModal = () => setOpen(true)
  const closeModal = () => setOpen(false)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setDocLoading(true)
    setDocError(null)
    getDocument(result.doc_id, query)
      .then(detail => {
        if (!cancelled) setDoc(detail)
      })
      .catch(err => {
        if (!cancelled) {
          setDoc(null)
          setDocError(err instanceof Error ? err.message : String(err))
        }
      })
      .finally(() => {
        if (!cancelled) setDocLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, result.doc_id, query])

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeModal()
    }
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = prev
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  const snippetHtml = highlightContaining(decodeSnippet(result.snippet), query)
  const titleHtml = highlightContaining(result.title, query)
  const fileName = doc?.title || result.title
  const source = result.source || doc?.source || ''
  const createdAt = result.created_at
  const titleIsUrl = looksLikeUrl(result.source)
  const titleNode = result.source ? (
    <a
      className="result-title"
      href={result.source}
      {...(titleIsUrl ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
      onClick={e => e.stopPropagation()}
      onKeyDown={e => e.stopPropagation()}
    >
      <Highlighted html={titleHtml} />
    </a>
  ) : (
    <Highlighted className="result-title" html={titleHtml} />
  )

  return (
    <>
      <div
        className={`result-card result-card-clickable${open ? ' is-open' : ''}`}
        role="button"
        tabIndex={0}
        onClick={openModal}
        onKeyDown={e => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            openModal()
          }
        }}
        aria-label={`Open details for ${result.title}`}
      >
        <div className="result-rank">{rank}</div>
        <div className="result-body">
          <div className="result-header">
            <div className="result-heading">
              {titleNode}
              {createdAt && (
                <time className="result-date" dateTime={createdAt}>
                  {formatCreatedAt(createdAt)}
                </time>
              )}
            </div>
            <span className="result-hybrid-score">{result.hybrid_score.toFixed(4)}</span>
          </div>
          <p className="result-snippet">
            <Highlighted html={snippetHtml} />
          </p>

          <div className="score-breakdown">
            <div className="score-row">
              <span className="score-label">BM25</span>
              <ScoreBar value={result.bm25_norm} raw={result.bm25_score} color="neutral" />
            </div>
            <div className="score-row">
              <span className="score-label">Vector</span>
              <ScoreBar value={result.vector_norm} raw={result.vector_score} color="purple" />
            </div>
            <div className="score-row">
              <span className="score-label">Hybrid</span>
              <ScoreBar value={result.hybrid_score} raw={result.hybrid_score} color="hybrid" />
            </div>
          </div>

          <div className="result-footer">
            <code className="result-doc-id">{result.doc_id}</code>
            <div className="feedback-row">
              {feedback ? (
                <span className="feedback-thanks">
                  {feedback === 'up' ? '✓ Marked relevant' : '✓ Marked irrelevant'}
                </span>
              ) : (
                <>
                  <span className="feedback-label">Relevant?</span>
                  <button
                    type="button"
                    className="feedback-btn"
                    onClick={e => {
                      e.stopPropagation()
                      void handleFeedback(true)
                    }}
                    onKeyDown={e => e.stopPropagation()}
                    disabled={sending}
                    title="Yes"
                  >
                    Yes
                  </button>
                  <button
                    type="button"
                    className="feedback-btn"
                    onClick={e => {
                      e.stopPropagation()
                      void handleFeedback(false)
                    }}
                    onKeyDown={e => e.stopPropagation()}
                    disabled={sending}
                    title="No"
                  >
                    No
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {open &&
        createPortal(
          <div className="doc-modal-overlay" onClick={closeModal} role="presentation">
            <div
              className="doc-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="doc-modal-title"
              onClick={e => e.stopPropagation()}
            >
              <header className="doc-modal-header">
                <div className="doc-modal-heading">
                  <div className="page-eyebrow">Document</div>
                  <h2 id="doc-modal-title" className="doc-modal-title">
                    <Highlighted html={highlightContaining(fileName, query)} />
                  </h2>
                  {source && <p className="doc-modal-source">{source}</p>}
                  <code className="result-doc-id">{result.doc_id}</code>
                </div>
                <button
                  type="button"
                  className="btn-ghost doc-modal-close"
                  onClick={closeModal}
                  aria-label="Close"
                >
                  Close
                </button>
              </header>

              <section className="doc-modal-section">
                <h3 className="doc-modal-label">Word occurrences</h3>
                {docLoading && !doc ? (
                  <p className="doc-modal-muted">Counting matches…</p>
                ) : doc && doc.occurrences.length > 0 ? (
                  <ul className="occur-list">
                    {doc.occurrences.map(row => (
                      <li key={row.term} className="occur-chip">
                        <em>{row.term}</em>
                        <span>{row.count}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="doc-modal-muted">No query-term matches in this file.</p>
                )}
              </section>

              <section className="doc-modal-section">
                <h3 className="doc-modal-label">Related KPIs</h3>
                <div className="kpi-grid">
                  <div className="kpi-tile">
                    <span className="kpi-tile-label">Rank</span>
                    <span className="kpi-tile-value">{rank}</span>
                  </div>
                  <div className="kpi-tile">
                    <span className="kpi-tile-label">Hybrid</span>
                    <span className="kpi-tile-value">{result.hybrid_score.toFixed(4)}</span>
                  </div>
                  <div className="kpi-tile">
                    <span className="kpi-tile-label">BM25</span>
                    <span className="kpi-tile-value">{result.bm25_score.toFixed(3)}</span>
                    <span className="kpi-tile-sub">norm {result.bm25_norm.toFixed(3)}</span>
                  </div>
                  <div className="kpi-tile">
                    <span className="kpi-tile-label">Vector</span>
                    <span className="kpi-tile-value">{result.vector_score.toFixed(3)}</span>
                    <span className="kpi-tile-sub">norm {result.vector_norm.toFixed(3)}</span>
                  </div>
                </div>
              </section>

              <section className="doc-modal-section doc-modal-body-section">
                <h3 className="doc-modal-label">What’s in the file</h3>
                {docLoading && !doc && (
                  <div className="doc-modal-muted">
                    <span className="spinner spinner-dark" /> Loading document…
                  </div>
                )}
                {docError && <div className="error-banner">{docError}</div>}
                {doc && (
                  <div
                    className="doc-body"
                    dangerouslySetInnerHTML={{ __html: doc.highlighted_text }}
                  />
                )}
              </section>
            </div>
          </div>,
          document.body,
        )}
    </>
  )
}
