export const meta = {
  name: 'research-sweep-run',
  description: 'Fan a research question out to many sources via `mise run research-fanout`, deep-read the best hits cheaply, synthesize once on Opus, and refute the load-bearing claims.',
  whenToUse: 'When a question needs evidence from several sources (GitHub issues/PRs/discussions/releases, exa, context7, firecrawl, last30days) and one context should not spend frontier tokens on fetching and reading.',
  phases: [
    { title: 'Plan', detail: 'pick sources and queries, then run research-fanout (sonnet, medium)' },
    { title: 'Triage', detail: 'rank and dedup the trimmed hits, choose what to deep-read (Explore + haiku)' },
    { title: 'Read', detail: 'deep-read the chosen URLs in batches; optional source dive at the release tag' },
    { title: 'Synthesize', detail: 'one Opus pass writes the report (opus, high)' },
    { title: 'Verify', detail: 'refute the load-bearing claims + a completeness critic (sonnet), then reconcile them into the report' },
    { title: 'Advise', detail: 'optional codex-sol-advisor second opinion (codex tokens, not Claude)' },
  ],
}

// Model/effort routing — the cost reasoning lives here so it is reviewed with the code.
// 1. Every workflow agent inherits this repo's CLAUDE.md + eager rules (~150 KB, measured
//    2026-09-26 as `cat AGENTS.md .claude/CLAUDE.md .claude/rules/*.md | wc -c` = 152,855) UNLESS its agentType is a built-in that omits them (Explore). So agent
//    COUNT dominates the cost of cheap steps: bulk reading runs as Explore on haiku, in
//    batches, never one agent per item.
// 2. Fetching is not reasoning: `mise run research-fanout` does it with no model at all.
// 3. Judgment is concentrated in ONE node (Synthesize, opus/high). Verification needs care
//    but not breadth: sonnet. Fable is never used here — escalation is `.claude/token-routing.md`'s.
// 4. The advisor runs on codex (codex-sol-advisor), spending codex tokens, not Claude's.
// 5. The critic is Explore on SONNET, not haiku: it reads one report and needs judgment, but
//    still skips the CLAUDE.md payload. The source dive is general-purpose because Explore may
//    not create or delete files (it clones into $TMPDIR).

const A = args || {}
if (typeof A.question !== 'string' || !A.question.trim()) throw new Error('args.question is required')
if (typeof A.reportPath !== 'string' || !A.reportPath.startsWith('/')) throw new Error('args.reportPath must be an absolute path')
const REPO = typeof A.repo === 'string' ? A.repo : ''
const READ_MAX = Number.isInteger(A.readMax) ? A.readMax : 6        // URLs deep-read
const READ_BATCH = 3                                                // URLs per Explore agent
const VERIFY_MAX = Number.isInteger(A.verifyMax) ? A.verifyMax : 5  // claims refuted
const SOURCES = ['github-issues', 'github-discussions', 'github-releases', 'exa', 'context7',
  'firecrawl-developer', 'firecrawl-search', 'last30days']

const PLAN = {
  type: 'object',
  required: ['runs', 'sourceDive'],
  properties: {
    runs: {
      type: 'array',
      items: {
        type: 'object',
        required: ['query', 'sources', 'manifest', 'rc'],
        properties: {
          query: { type: 'string' },
          sources: { type: 'array', items: { type: 'string' } },
          manifest: { type: 'string' },
          rc: { type: 'number' },
        },
      },
    },
    sourceDive: { type: 'boolean' },
    rationale: { type: 'string' },
  },
}
const TRIAGE = {
  type: 'object',
  required: ['read', 'hits', 'unverifiedEmpty'],
  properties: {
    read: { type: 'array', items: { type: 'object', required: ['url', 'why'], properties: { url: { type: 'string' }, why: { type: 'string' } } } },
    hits: { type: 'array', items: { type: 'object', required: ['url', 'title', 'sources'], properties: { url: { type: 'string' }, title: { type: 'string' }, sources: { type: 'array', items: { type: 'string' } } } } },
    unverifiedEmpty: { type: 'array', items: { type: 'string' } },
  },
}
const CLAIMS = {
  type: 'object',
  required: ['claims'],
  properties: {
    claims: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'url', 'quote'],
        properties: { claim: { type: 'string' }, url: { type: 'string' }, quote: { type: 'string' }, date: { type: 'string' } },
      },
    },
  },
}
const SYNTH = {
  type: 'object',
  required: ['reportPath', 'loadBearing'],
  properties: {
    reportPath: { type: 'string' },
    loadBearing: { type: 'array', items: { type: 'object', required: ['claim', 'source'], properties: { claim: { type: 'string' }, source: { type: 'string' } } } },
  },
}
const VERDICTS = {
  type: 'object',
  required: ['verdicts'],
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'refuted', 'evidence'],
        properties: { claim: { type: 'string' }, refuted: { type: 'boolean' }, evidence: { type: 'string' } },
      },
    },
  },
}
const CRITIC = {
  type: 'object',
  required: ['gaps'],
  properties: { gaps: { type: 'array', items: { type: 'object', required: ['gap', 'nextProbe'], properties: { gap: { type: 'string' }, nextProbe: { type: 'string' } } } } },
}

phase('Plan')
const plan = await agent([
  `QUESTION: ${A.question}`,
  REPO ? `REPO: ${REPO}` : 'REPO: (none — do NOT pick github-* sources; if the question clearly names one project, say so in rationale so the caller can re-run with args.repo)',
  'LOCAL CORPORA FIRST (.claude/rules/research-doc-sources.md): for Claude Code / codex / cursor behaviour grep',
  '~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/<tool>/; for a library in',
  'docs/research/mintlify-catalog.md grep docs/research/mintlify-cache/. Fan out only for what those do not answer.',
  `AVAILABLE SOURCES: ${SOURCES.join(', ')} (see \`mise run research-fanout -- --list-sources\`).`,
  'Choose only the sources that fit the question: API/library behaviour -> github-* + firecrawl-developer + context7;',
  'recent community sentiment -> last30days + exa; general web -> exa + firecrawl-search. Write 1-3 query variants',
  '(short search terms, not sentences). For each variant run exactly:',
  `  mise run research-fanout -- "<query>" ${REPO ? `--repo ${REPO} ` : ''}--sources <comma list>`,
  'and record the manifest path it prints and its real exit code. Set sourceDive=true only when REPO is set AND the',
  'question is about what the code DOES (behaviour, a flag, a bug), where reading source at the release tag beats issues.',
].join('\n'), { label: 'plan+fetch', phase: 'Plan', model: 'sonnet', effort: 'medium', schema: PLAN })
if (plan === null) return { status: 'plan-null' }
const manifests = plan.runs.filter(r => r.manifest).map(r => r.manifest)
if (!manifests.length) return { status: 'no-manifests', plan }
log(`Plan: ${plan.runs.length} fanout run(s); sourceDive=${plan.sourceDive}`)

phase('Triage')
const triage = await agent([
  `QUESTION: ${A.question}`,
  `Read these research-fanout manifests and every <source>.json beside them:\n${manifests.join('\n')}`,
  'Dedup hits across sources by URL (record which sources found each). Rank by likely value for the QUESTION:',
  'primary sources (source code, merged PRs, maintainer answers, release notes) above secondary ones (blogs, forums).',
  `Choose at most ${READ_MAX} URLs worth deep-reading, each with a one-line reason. List every source whose status is`,
  'empty_unverified or error in unverifiedEmpty — those are gaps, not "no results".',
].join('\n'), { label: 'triage', phase: 'Triage', agentType: 'Explore', model: 'haiku', schema: TRIAGE })
if (triage === null) return { status: 'triage-null', plan }
const toRead = triage.read.slice(0, READ_MAX)
if (triage.read.length > READ_MAX) log(`Triage: dropped ${triage.read.length - READ_MAX} URL(s) over readMax`)

phase('Read')
const batches = []
for (let i = 0; i < toRead.length; i += READ_BATCH) batches.push(toRead.slice(i, i + READ_BATCH))
// Each reader keeps its identity: a reader that returns null is a GAP the report must
// name, never a silent drop (a null filtered away reads as "nothing to say").
const readers = batches.map((batch, i) => ({ urls: batch.map(u => u.url), run: () => agent([
  `QUESTION: ${A.question}`,
  'Deep-read each URL below and extract claims that bear on the QUESTION, each with a VERBATIM quote and the URL.',
  'GitHub issue/PR/discussion: `gh api` (issue + comments, PR body + review comments; discussions via `gh api graphql`).',
  'Other pages: `firecrawl scrape <url> --format markdown`. Never print environment values.',
  ...batch.map(u => `- ${u.url}  (${u.why})`),
].join('\n'), { label: `read:${i + 1}/${batches.length}`, phase: 'Read', agentType: 'Explore', model: 'haiku', schema: CLAIMS }) }))
if (plan.sourceDive && REPO) {
  // general-purpose, not Explore: the dive clones into $TMPDIR and deletes it, and the
  // built-in Explore agent may not create or delete files. It pays the CLAUDE.md payload
  // only on the runs that need a clone.
  readers.push({ urls: [`${REPO} (source at the latest release tag)`], run: () => agent([
    `QUESTION: ${A.question}`,
    `Shallow-clone ${REPO} at its LATEST RELEASE TAG (\`gh api repos/${REPO}/releases/latest --jq .tag_name\`) into $TMPDIR,`,
    'grep for the mechanism the QUESTION is about, and extract claims about what the code does, each with file:line and a',
    'verbatim quote. Also say whether the default branch has changed that code since the tag (a merged-but-unreleased fix).',
    'Delete the clone when done.',
  ].join('\n'), { label: 'source-dive', phase: 'Read', model: 'sonnet', effort: 'medium', schema: CLAIMS }) })
}
const readResults = await parallel(readers.map(r => r.run))
const claims = readResults.flatMap(r => (r === null ? [] : r.claims))
const failedReads = readers.flatMap((r, i) => (readResults[i] === null ? r.urls : []))
log(`Read: ${claims.length} claim(s) from ${readers.length} reader(s); ${failedReads.length} unread`)

phase('Synthesize')
const synth = await agent([
  `QUESTION: ${A.question}`,
  `Write the research report to ${A.reportPath}. Inputs: the claims JSON below, the triage hit list, and the manifests`,
  `(${manifests.join(', ')}). Resolve conflicts explicitly (source code and merged PRs beat issue threads; newer beats`,
  'older; say which you trusted and why). Name every gap from unverifiedEmpty as a gap, never as "nothing found".',
  'Every FAILED READ below is a gap too: the reader for it failed, so its content is unknown.',
  'Sections: Answer, Evidence (claim | URL or file:line | quote), Conflicts resolved, Gaps, Recommendation,',
  '## GitHub repos touched (per .claude/rules/research-repo-enumeration.md). Return the path and the claims the',
  `Answer depends on (at most ${VERIFY_MAX}).`,
  `CLAIMS:\n${JSON.stringify(claims)}`,
  `TRIAGE:\n${JSON.stringify({ hits: triage.hits, unverifiedEmpty: triage.unverifiedEmpty })}`,
  `FAILED READS:\n${JSON.stringify(failedReads)}`,
].join('\n'), { label: 'synthesize', phase: 'Synthesize', model: 'opus', effort: 'high', schema: SYNTH })
if (synth === null) return { status: 'synth-null', plan, triage, claims }

phase('Verify')
const loadBearing = synth.loadBearing.slice(0, VERIFY_MAX)
const [verdicts, critic] = await parallel([
  () => agent([
    'Try to REFUTE each claim below by re-probing its PRIMARY source yourself (open the URL / read the file at the',
    'cited ref). Default to refuted=true if you cannot confirm it. Every negative needs a control arm',
    '(.claude/rules/probes-need-a-control-arm.md). Claims:',
    ...loadBearing.map(c => `- ${c.claim}  [${c.source}]`),
  ].join('\n'), { label: 'refute', phase: 'Verify', model: 'sonnet', effort: 'medium', schema: VERDICTS }),
  () => agent([
    `Read the report at ${synth.reportPath} for the QUESTION: ${A.question}`,
    'What is missing — a source never queried, a claim never checked, a primary source never read, a version or',
    'release never confirmed? Give each gap with the concrete next probe. Return an empty list if there is none.',
  ].join('\n'), { label: 'critic', phase: 'Verify', agentType: 'Explore', model: 'sonnet', effort: 'low', schema: CRITIC }),
])
const refuted = verdicts === null ? null : verdicts.verdicts.filter(v => v.refuted)
const gaps = critic === null ? null : critic.gaps
if (verdicts === null) log('Verify: refuter returned null — claims are UNVERIFIED, not confirmed')
else log(`Verify: ${refuted.length}/${verdicts.verdicts.length} load-bearing claim(s) refuted`)

// The report on disk must carry the verification outcome: a refuted claim left in the
// Answer is worse than no report. Reconcile only when there is something to write
// (a small edit to an existing file: sonnet at low effort).
let reconciled = true
if (verdicts === null || critic === null || refuted.length || gaps.length) {
  const reconcile = await agent([
    `Edit the research report at ${synth.reportPath} in place. Add a "## Verification" section listing each`,
    'load-bearing claim as confirmed, refuted (with the evidence) or unverified. Correct or strike every refuted',
    'claim wherever the Answer or Recommendation relies on it, and say how the conclusion changes. Append the',
    'critic gaps to the Gaps section. If the refuter or critic result is null, say that verification did not run.',
    `VERDICTS: ${JSON.stringify(verdicts)}`,
    `CRITIC GAPS: ${JSON.stringify(gaps)}`,
  ].join('\n'), { label: 'reconcile', phase: 'Verify', model: 'sonnet', effort: 'low' })
  reconciled = reconcile !== null
  if (!reconciled) log('Verify: reconcile returned null — the report on disk does NOT reflect verification')
}

let advice = null
if (A.advisor) {
  phase('Advise')
  advice = await agent(`Second opinion on the recommendation in ${synth.reportPath} (question: ${A.question}). Refuted claims: ${JSON.stringify(refuted)}. Return a verdict and the deciding risk.`, {
    label: 'codex-sol-advisor', phase: 'Advise', agentType: 'codex-sol-advisor',
  })
  if (advice === null) log('Advise: codex-sol-advisor returned null (escalation per .claude/token-routing.md item 1)')
}

// Status: complete | verify-null | reconcile-null | plan-null | no-manifests | triage-null | synth-null.
const status = verdicts === null ? 'verify-null' : !reconciled ? 'reconcile-null' : 'complete'
return { status, reportPath: synth.reportPath, plan, triage, claims: claims.length, failedReads, verdicts, refuted, gaps, advice }
