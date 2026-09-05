import assert from 'node:assert/strict'
import { nextPollDelay } from './src/reindexPoll.ts'

assert.equal(nextPollDelay(false, 0), null)
assert.equal(nextPollDelay(true, 0), 400)
assert.equal(nextPollDelay(false, 1), 2_000)
assert.equal(nextPollDelay(true, 1), 2_000)
assert.equal(nextPollDelay(false, 2), 5_000)
assert.equal(nextPollDelay(false, 3), 15_000)
assert.equal(nextPollDelay(false, 4), null)
assert.equal(nextPollDelay(true, 4), null)

console.log('reindexPoll.nextPollDelay: ok')
