export const meta = {
  name: 'proto-interrupt-resume-probe',
  description:
    'THROWAWAY probe: when a workflow run is INTERRUPTED mid-flight, what replays from cache and what re-runs?',
  phases: [
    { title: 'Before', detail: 'one fast agent that finishes before the interrupt' },
    { title: 'Straddle', detail: 'SLOW agent (the interrupt target) + a FAST agent that finishes' },
    { title: 'After', detail: 'an agent that never starts on run 1' },
  ],
}

// Claim 1f-interrupted of prototype/RESULTS.md.
//
// The claim under test (documented, never measured here): replay stops at the FIRST
// agent that did not finish, and everything started after it re-runs EVEN IF IT COMPLETED.
//
// The fixture is built so all three outcomes are reachable:
//   * `before`  finishes before the interrupt  -> must be CACHED if any caching survives
//   * `slow`    is in flight at the interrupt  -> must RE-RUN
//   * `fast_b`  finishes before the interrupt, but its agent() call comes AFTER `slow`'s
//               -> re-runs if the cache is a prefix; stays cached if it is per-call
//   * `after`   never starts on run 1          -> must run live on resume
//
// `before` is the control arm: if IT re-runs, an interrupted run caches nothing at all
// and the fast_b reading means something different.
//
// Each agent stamps START before its work and END after, into its own witness log, so
// execution count is countable per agent instead of inferred from aggregate token totals.

const DIR =
  '/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/7e75e5ce-d559-4ea7-b601-d1cd7aa38e1d/scratchpad/irp'

const TOKEN_SCHEMA = {
  type: 'object',
  properties: {
    token: { type: 'string' },
    n: { type: 'integer' },
  },
  required: ['token', 'n'],
  additionalProperties: false,
}

// A fast agent: stamp START, stamp END, return. No file reads, no exploration.
const fastPrompt = (label, n) =>
  `Do exactly these steps and nothing else. Do NOT read any files, do NOT explore the repository, do NOT use any tool other than Bash.

Step 1 - run this exact Bash command:
printf '%s START %s\\n' ${label} "$(date +%s)" >> ${DIR}/${label}.log

Step 2 - run this exact Bash command:
printf '%s END %s\\n' ${label} "$(date +%s)" >> ${DIR}/${label}.log

Then reply with structured output only: token set to exactly ${label.toUpperCase()}-OK and n set to exactly ${n}.`

// The slow agent: same shape, but a long blocking body between START and END so the
// run can be interrupted while it is genuinely in flight.
const slowPrompt = `Do exactly these steps and nothing else. Do NOT read any files, do NOT explore the repository, do NOT use any tool other than Bash.

Step 1 - run this exact Bash command:
printf '%s START %s\\n' slow "$(date +%s)" >> ${DIR}/slow.log

Step 2 - run this exact Bash command, and pass timeout: 300000 to the Bash tool so it is not cut short:
python3 -c 'import time; time.sleep(240); print("SLOW-BODY-DONE")'

Step 3 - run this exact Bash command:
printf '%s END %s\\n' slow "$(date +%s)" >> ${DIR}/slow.log

Then reply with structured output only: token set to exactly SLOW-OK and n set to exactly 2.`

// ---- 1. Before the interrupt ----
phase('Before')
log('stage BEFORE: fast agent, finishes well before the interrupt')
const before = await agent(fastPrompt('before', 1), {
  schema: TOKEN_SCHEMA,
  label: 'before',
  phase: 'Before',
})

// ---- 2. The straddle: slow first, fast second ----
// Order matters. `slow` is dispatched first so that `fast_b` is unambiguously the
// "started after the unfinished agent" case.
phase('Straddle')
log('stage STRADDLE: slow (interrupt target) dispatched first, fast_b second')
const straddle = await parallel([
  () => agent(slowPrompt, { schema: TOKEN_SCHEMA, label: 'slow', phase: 'Straddle' }),
  () =>
    agent(fastPrompt('fast_b', 3), { schema: TOKEN_SCHEMA, label: 'fast_b', phase: 'Straddle' }),
])

const [slow, fastB] = straddle

// ---- 3. Never reached on run 1 ----
phase('After')
log('stage AFTER: never starts on run 1 - proves the resume made forward progress')
const after = await agent(fastPrompt('after', 4), {
  schema: TOKEN_SCHEMA,
  label: 'after',
  phase: 'After',
})

return {
  before,
  slow,
  fast_b: fastB,
  after,
  note: 'execution counts are in the witness logs under DIR, not in this object',
}
