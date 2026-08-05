export const meta = {
  name: 'proto-workflow-mechanism-probe',
  description: 'THROWAWAY probe: does agent({schema}), pipeline() fan-out, and per-stage model routing actually work?',
  phases: [
    { title: 'Schema', detail: 'one agent forced through a strict JSON Schema' },
    { title: 'Fanout', detail: 'pipeline() over 3 items' },
    { title: 'Routing', detail: 'same prompt, two different model routes' },
  ],
}

// Claim 1 of prototype/RESULTS.md. Throwaway — the artifact is the return value,
// which gets pasted into RESULTS.md as evidence.

const TOKEN_SCHEMA = {
  type: 'object',
  properties: {
    token: { type: 'string' },
    n: { type: 'integer' },
  },
  required: ['token', 'n'],
  additionalProperties: false,
}

const MODEL_SCHEMA = {
  type: 'object',
  properties: {
    model_self_report: { type: 'string' },
    certainty: { type: 'string' },
  },
  required: ['model_self_report', 'certainty'],
  additionalProperties: false,
}

// ---- 1. Does `schema:` actually force validated structured output? ----
phase('Schema')
log('probe 1: strict schema — expecting a validated object, not prose')
const schemaProbe = await agent(
  'Reply with structured output only. Set token to exactly WORKFLOW-SCHEMA-OK and n to exactly 7. Do not do anything else, do not read any files.',
  { schema: TOKEN_SCHEMA, label: 'schema-probe' }
)

// ---- 2. Does pipeline() fan out one agent per item? ----
phase('Fanout')
log('probe 2: pipeline() over 3 items')
const items = ['alpha', 'beta', 'gamma']
const fanned = await pipeline(
  items,
  (item, _orig, i) =>
    agent(
      `Reply with structured output only. Set token to exactly FAN-${item} and n to exactly ${i}. Do not read any files.`,
      { schema: TOKEN_SCHEMA, label: `fan:${item}`, phase: 'Fanout' }
    )
)

// ---- 3. Does a per-stage `model` route reach a different model? ----
// Weak signal by construction: a model's self-report is not authoritative.
// Recorded as such; the run journal is the corroborating source.
phase('Routing')
log('probe 3: same prompt, two routes — haiku vs session default')
const ASK =
  'Reply with structured output only. In model_self_report put the exact model name you are running as. In certainty put one of: certain, inferred, guess. Do not read any files and do not run any commands.'

const routed = await parallel([
  () => agent(ASK, { schema: MODEL_SCHEMA, model: 'haiku', label: 'route:haiku', phase: 'Routing' }),
  () => agent(ASK, { schema: MODEL_SCHEMA, label: 'route:session-default', phase: 'Routing' }),
])

const [haikuRoute, defaultRoute] = routed

// ---- 4. RESUME PROBE (appended after run wf_c18255a9-2ea completed) ----
// Everything above is byte-identical to the original run, so on resume it must
// replay from cache. Only this stage is new and should run live. The control arm
// is the contrast: if the six above re-run, caching does not work.
phase('Resume')
log('probe 4: this stage is NEW — the six above must replay from cache')
const resumeProbe = await agent(
  'Reply with structured output only. Set token to exactly RESUME-STAGE-RAN and n to exactly 99. Do not read any files.',
  { schema: TOKEN_SCHEMA, label: 'resume-new-stage', phase: 'Resume' }
)

return {
  probe1_schema: {
    returned: schemaProbe,
    is_object: schemaProbe !== null && typeof schemaProbe === 'object',
    token_matches: schemaProbe && schemaProbe.token === 'WORKFLOW-SCHEMA-OK',
    n_is_number: schemaProbe && typeof schemaProbe.n === 'number',
  },
  probe2_pipeline: {
    items_in: items.length,
    results_out: fanned.length,
    nulls: fanned.filter((r) => r === null).length,
    tokens: fanned.map((r) => (r ? r.token : null)),
    indices: fanned.map((r) => (r ? r.n : null)),
  },
  probe4_resume: {
    new_stage: resumeProbe,
    ran_live: resumeProbe && resumeProbe.token === 'RESUME-STAGE-RAN',
  },
  probe3_routing: {
    haiku_route: haikuRoute,
    default_route: defaultRoute,
    self_reports_differ:
      haikuRoute && defaultRoute
        ? haikuRoute.model_self_report !== defaultRoute.model_self_report
        : null,
    caveat: 'a model self-report is weak evidence; corroborate against the run journal',
  },
}
