export const meta = {
  name: 'gated-implementation',
  description: 'Run one spec-file Codex implementation, every requested gate, a cold review by ref, and an optional adversarial critique.',
  whenToUse: 'When a ratified seven-part spec should move through implementation, evidence gates, cold review, and optional proposal critique without retyping the orchestration.',
  phases: [
    { title: 'Implement', detail: 'dispatch the marked spec file and verbatim PREMISES to codex-implementer' },
    { title: 'Gates', detail: 'run every requested verification command through gate-runner' },
    { title: 'Review', detail: 'cold-review the reported commit or caller-supplied ref' },
    { title: 'Critique', detail: 'optionally replay a proposal with codex-adversarial-critic' },
  ],
}

const A = args
if (!A || typeof A.specFile !== 'string' || !A.specFile.startsWith('/')) throw new Error('args.specFile must be an absolute path')
if (typeof A.premises !== 'string' || !A.premises) throw new Error('args.premises is required')
if (!Array.isArray(A.verify)) throw new Error('args.verify must be an array of shell commands')

const GATES = {
  type: 'object',
  required: ['gates'],
  properties: {
    gates: {
      type: 'array',
      items: {
        type: 'object',
        required: ['cmd', 'rc', 'log', 'firstFailure'],
        properties: {
          cmd: { type: 'string' },
          rc: { type: 'number' },
          log: { type: 'string' },
          firstFailure: { type: 'string' },
        },
      },
    },
  },
}
const REVIEW = {
  type: 'object',
  required: ['findings', 'reportPath'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['severity', 'claim', 'file', 'line', 'cited'],
        properties: {
          severity: { type: 'string' },
          claim: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'number' },
          cited: { type: 'boolean' },
        },
      },
    },
    reportPath: { type: 'string' },
  },
}
const CRITIC = {
  type: 'object',
  required: ['verdicts', 'reportPath'],
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        required: ['proposal', 'catchesMotivatingDefect', 'evidence'],
        properties: {
          proposal: { type: 'string' },
          catchesMotivatingDefect: { type: 'boolean' },
          evidence: { type: 'string' },
        },
      },
    },
    reportPath: { type: 'string' },
  },
}

phase('Implement')
log('Implement: dispatching the ratified spec file')
const implementerLines = [
  `SPEC FILE: ${A.specFile}`,
  '(reproduced from the spec file)',
  A.premises,
  `EFFORT: ${A.effort || 'xhigh'}`,
  `TIMEOUT: ${A.timeout === undefined ? 3600 : A.timeout}`,
]
if (A.attestation) implementerLines.push(`PREMISES-VERIFIED: ${A.attestation}`)
const implementerReport = await agent(implementerLines.join('\n'), {
  label: 'codex-implementer',
  phase: 'Implement',
  agentType: 'fable-orchestrator:codex-implementer',
})
if (implementerReport === null) return { status: 'implementer-null' }
const commitMatch = /^COMMIT:\s*(\S+)\s*$/m.exec(implementerReport)
const commit = commitMatch ? commitMatch[1] : ''

phase('Gates')
log(`Gates: dispatching ${A.verify.length} verification commands`)
const gateOutput = await agent(`Run every command in this JSON array, in order, even when an earlier command fails. Capture each rc in its log file and return an object with a "gates" array holding one row per command.\n${JSON.stringify(A.verify)}`, {
  label: 'gate-runner',
  phase: 'Gates',
  agentType: 'gate-runner',
  schema: GATES,
})
const gates = gateOutput === null ? null : gateOutput.gates
if (gates === null) log('Gates: gate-runner returned null; gates are unknown, not passed')

const ref = A.reviewRef || commit
if (!ref) {
  log('Review: skipped — no reviewRef supplied and the implementer report carried no commit')
  return { status: 'implementer-no-commit', implementerReport, commit: '', gates, review: null, critic: null }
}

phase('Review')
log(`Review: dispatching a cold review for ${ref}`)
const review = await agent(`${ref}\nReview this ref cold. Resolve it yourself; the caller provides no description of intent.`, {
  label: 'cold-reviewer',
  phase: 'Review',
  agentType: 'cold-reviewer',
  schema: REVIEW,
})
if (review === null) log('Review: cold-reviewer returned null')

let critic = null
if (A.criticProposal) {
  phase('Critique')
  log('Critique: dispatching the supplied proposal')
  critic = await agent(A.criticProposal, {
    label: 'codex-adversarial-critic',
    phase: 'Critique',
    agentType: 'codex-adversarial-critic',
    schema: CRITIC,
  })
  if (critic === null) log('Critique: codex-adversarial-critic returned null')
} else {
  log('Critique: skipped because criticProposal is empty')
}

// Status vocabulary: complete | implementer-null | implementer-no-commit |
// gates-null | review-null | critic-null. Ordered by phase so each is
// reachable exactly when its own condition holds, regardless of which other
// phases also came back null (fixes the review-before-gates ordering that
// made 'gates-null' unreachable whenever review was also null).
const status = gates === null
  ? 'gates-null'
  : review === null
    ? 'review-null'
    : critic === null && A.criticProposal
      ? 'critic-null'
      : 'complete'
return { status, implementerReport, commit, gates, review, critic }
