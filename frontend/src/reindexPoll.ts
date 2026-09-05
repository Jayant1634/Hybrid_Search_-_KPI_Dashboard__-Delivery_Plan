const LIVE_MS = 400
const FAIL_BACKOFF_MS = [2_000, 5_000, 15_000] as const

/** Next wait before another /reindex/progress call. null = stop. */
export function nextPollDelay(running: boolean, failCount: number): number | null {
  if (failCount > 0) {
    if (failCount > FAIL_BACKOFF_MS.length) return null
    return FAIL_BACKOFF_MS[failCount - 1]
  }
  if (running) return LIVE_MS
  return null
}
