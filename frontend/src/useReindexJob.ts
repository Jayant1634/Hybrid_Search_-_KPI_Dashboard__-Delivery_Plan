import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getReindexProgress,
  reindex,
  type IndexGranularity,
  type ReindexProgress,
} from './api'
import { nextPollDelay } from './reindexPoll'

export function useReindexJob(enabled = true) {
  const [progress, setProgress] = useState<ReindexProgress | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState<string | null>(null)
  const [lease, setLease] = useState(0)
  const wasRunning = useRef(false)

  const refresh = useCallback(async () => {
    const next = await getReindexProgress()
    setProgress(next)
    if (next.running) {
      wasRunning.current = true
      setError(null)
    } else if (wasRunning.current) {
      wasRunning.current = false
      if (next.error) {
        setError(next.error)
        setNote(null)
      } else if (next.granularity) {
        setNote(`Rebuilt as ${next.granularity}.`)
      }
    }
    return next
  }, [])

  useEffect(() => {
    // Homepage stays quiet. lease === 0 means nobody started a rebuild this
    // session, so do not probe /reindex/progress at all (avoids Vite proxy
    // spam while the API is still coming up).
    if (!enabled || lease === 0) return
    let cancelled = false
    let timer = 0
    let failCount = 0

    const tick = async () => {
      try {
        const next = await refresh()
        if (cancelled) return
        failCount = 0
        const wait = nextPollDelay(next.running, 0)
        if (wait !== null) timer = window.setTimeout(() => void tick(), wait)
      } catch {
        if (cancelled) return
        failCount += 1
        const wait = nextPollDelay(false, failCount)
        if (wait !== null) timer = window.setTimeout(() => void tick(), wait)
      }
    }

    void tick()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [refresh, enabled, lease])

  const start = useCallback(async (granularity: IndexGranularity) => {
    setError(null)
    setNote(null)
    setProgress({
      running: true,
      granularity,
      done: 0,
      total: 0,
      percent: 0,
      phase: 'embedding',
      error: null,
    })
    wasRunning.current = true
    try {
      const accepted = await reindex(granularity)
      setProgress(accepted.progress)
      setLease((n) => n + 1)
    } catch (e) {
      wasRunning.current = false
      setError(e instanceof Error ? e.message : String(e))
      setProgress(null)
    }
  }, [])

  return {
    progress,
    running: Boolean(progress?.running),
    error,
    note,
    start,
    refresh,
  }
}
