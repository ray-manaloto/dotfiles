export const meta = {
  name: 'graphify-refresh',
  description: 'Inventory installed Graphify features, execute an ordered data-defined mise task list, and optionally audit stale prose.',
  whenToUse: 'When Graphify changes and research, repository-owned refresh tasks, and staleness checks must run in a repeatable verified order.',
  phases: [
    { title: 'Research', detail: 'optionally inventory installed features against a supplied brief' },
    { title: 'Operate', detail: 'run the ordered task data through graphify-operator' },
    { title: 'Audit', detail: 'optionally audit named stale terms after the refresh' },
  ],
}

const A = args
if (!A || !Array.isArray(A.tasks)) throw new Error('args.tasks must be an array')
if (!Array.isArray(A.staleTerms)) throw new Error('args.staleTerms must be an array')

const RESEARCH = {
  type: 'object',
  required: ['reportPath', 'summary'],
  properties: {
    reportPath: { type: 'string' },
    summary: { type: 'string' },
  },
}
const TASK_RESULTS = {
  type: 'object',
  required: ['tasks'],
  properties: {
    tasks: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name', 'rc', 'log', 'delta'],
        properties: {
          name: { type: 'string' },
          rc: { type: 'number' },
          log: { type: 'string' },
          delta: { type: 'string' },
        },
      },
    },
  },
}
const AUDIT = {
  type: 'object',
  required: ['findings', 'reportPath'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'file', 'line', 'evidence'],
        properties: {
          claim: { type: 'string' },
          file: { type: 'string' },
          line: { type: 'number' },
          evidence: { type: 'string' },
        },
      },
    },
    reportPath: { type: 'string' },
  },
}

let research = null
phase('Research')
if (A.researchBrief) {
  log('Research: dispatching the installed-feature inventory')
  research = await agent(A.researchBrief, {
    label: 'graphify-researcher',
    phase: 'Research',
    agentType: 'graphify-researcher',
    schema: RESEARCH,
  })
  if (research === null) log('Research: graphify-researcher returned null')
} else {
  log('Research: skipped because researchBrief is empty')
}

phase('Operate')
log(`Operate: dispatching ${A.tasks.length} ordered tasks`)
const taskOutput = await agent(`Run exactly this ordered JSON task list. Stop at the first rc that differs from expectRc (default 0), and return an object with a "tasks" array holding rows only for attempted tasks.\n${JSON.stringify(A.tasks)}`, {
  label: 'graphify-operator',
  phase: 'Operate',
  agentType: 'graphify-operator',
  schema: TASK_RESULTS,
})
const tasks = taskOutput === null ? null : taskOutput.tasks
if (tasks === null) {
  log('Operate: graphify-operator returned null; the task list stopped')
  return { research, tasks: null, audit: null }
}

let audit = null
phase('Audit')
if (A.staleTerms.length) {
  log(`Audit: dispatching ${A.staleTerms.length} stale terms`)
  audit = await agent(`Audit repository prose for these stale terms and report every claim with evidence:\n${A.staleTerms.join('\n')}`, {
    label: 'codex-staleness-auditor',
    phase: 'Audit',
    agentType: 'codex-staleness-auditor',
    schema: AUDIT,
  })
  if (audit === null) log('Audit: codex-staleness-auditor returned null')
} else {
  log('Audit: skipped because staleTerms is empty')
}

return { research, tasks, audit }
