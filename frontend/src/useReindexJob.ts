import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getReindexProgress,
  reindex,
  type IndexGranularity,
  type ReindexProgress,
} from './api'

const IDLE_MS = 1500
const LIVE_MS = 400

export function useReindexJob() {
  const [progress, setProgress] = useState<ReindexProgress | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState<string | null>(null)
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
    let cancelled = false
    let timer = 0
    const tick = async () => {
      try {
        const next = await refresh()
        if (cancelled) return
        timer = window.setTimeout(tick, next.running ? LIVE_MS : IDLE_MS)
      } catch {
        if (!cancelled) timer = window.setTimeout(tick, IDLE_MS)
      }
    }
    void tick()
    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [refresh])

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
