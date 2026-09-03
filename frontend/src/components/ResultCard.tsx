import { useState } from 'react'
import ScoreBar from './ScoreBar'
import { submitFeedback, type SearchResult } from '../api'

interface Props {
  result: SearchResult
  requestId: string
  rank: number
}

export default function ResultCard({ result, requestId, rank }: Props) {
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null)
  const [sending, setSending] = useState(false)

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

  return (
    <div className="result-card">
      <div className="result-rank">{rank}</div>
      <div className="result-body">
        <div className="result-header">
          <span className="result-title">{result.title}</span>
          <span className="result-hybrid-score">{result.hybrid_score.toFixed(4)}</span>
        </div>
        <p className="result-snippet">{result.snippet}</p>

        <div className="score-breakdown">
          <div className="score-row">
            <span className="score-label">BM25</span>
            <ScoreBar value={result.bm25_norm} color="neutral" />
            <span className="score-num">{result.bm25_norm.toFixed(3)}</span>
          </div>
          <div className="score-row">
            <span className="score-label">Vector</span>
            <ScoreBar value={result.vector_norm} color="purple" />
            <span className="score-num">{result.vector_norm.toFixed(3)}</span>
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
                  className="feedback-btn"
                  onClick={() => handleFeedback(true)}
                  disabled={sending}
                  title="Yes"
                >
                  Yes
                </button>
                <button
                  className="feedback-btn"
                  onClick={() => handleFeedback(false)}
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
  )
}
