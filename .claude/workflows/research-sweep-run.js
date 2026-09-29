export const meta = {
  name: 'research-sweep-run',
  description: 'Fan a research question out to many sources via `mise run research-fanout`, deep-read the best hits cheaply, synthesize once on Opus, and refute the load-bearing claims one by one.',
  whenToUse: 'When a question needs evidence from several sources (GitHub issues/PRs/discussions/releases/code, exa, context7, firecrawl, last30days) and one context should not spend frontier tokens on fetching and reading.',
  phases: [
    { title: 'Plan', detail: 'pick sources and queries (incl. cross-repo both directions), then run research-fanout (sonnet, medium)' },
    { title: 'Triage', detail: 'rank and dedup the hits, choose what to deep-read; caller links always read (Explore + sonnet, low)' },
    { title: 'Read', detail: 'caller links (sonnet) + triaged URLs (haiku) in batches; optional source dive at the release tag' },
    { title: 'Synthesize', detail: 'one Opus pass writes the report (opus, high)' },
    { title: 'Verify', detail: 'one independent refuter per load-bearing claim (sonnet), a completeness critic, an Opus adjudicator for any refutation, then reconcile' },
    { title: 'Advise', detail: 'optional codex-sol-advisor second opinion (codex tokens, not Claude)' },
  ],
}

// Model/effort routing — the cost reasoning lives here so it is reviewed with the code.
// 1. Every workflow agent inherits this repo's CLAUDE.md + eager rules (~150 KB, measured
//    2026-09-26 as `cat AGENTS.md .claude/CLAUDE.md .claude/rules/*.md | wc -c` = 152,855) UNLESS its agentType is a built-in that omits them (Explore). So agent
//    COUNT dominates the cost of cheap steps: bulk reading runs as Explore on haiku, in
//    batches, never one agent per item.
// 2. Fetching is not reasoning: `mise run research-fanout` does it with no model at all.
// 3. Judgment is concentrated in ONE node (Synthesize, opus/high). Fable is never used here —
//    escalation is `.claude/token-routing.md`'s.
// 4. The advisor runs on codex (codex-sol-advisor), spending codex tokens, not Claude's.
// 5. The critic is Explore on SONNET: it reads one report and needs judgment, but still skips
//    the CLAUDE.md payload. The source dive is general-purpose because Explore may not create
//    or delete files (it clones into $TMPDIR).
// Tuning 2026-09-29b (session 5545fa41; evidence in
// docs/research/kb/reports/agents/omarchy-mise-dotfiles-crossref-sweep-2026-09-29.md and the
// superseded mise-dotfiles-omarchy-2026-09-29.md):
// 6. TRIAGE moved haiku -> sonnet/low: it decides what is ever read, so a cheap ranking miss
//    propagates to every later node; it is still ONE Explore agent.
// 7. Caller-supplied LINKS bypass triage and its READ_MAX cap and are read on sonnet/low: a link
//    the user named is never a ranking decision, and the one missed section that caused the
//    2026-09-29b Omarchy headline lived in a page that WAS fetched but never read closely.
// 8. REFUTE is one agent PER load-bearing claim (independence: one refuter reasoning about five
//    claims anchors on its first verdict) and must cross-check an ABSENCE claim by a second,
//    independent route with a control arm (.claude/rules/probes-need-a-control-arm.md).
// 9. ADJUDICATE (opus/high, one tier above the refuters) runs only when a refuter says
//    "refuted": a refutation rewrites the report, so it is confirmed before reconcile acts on it
//    (memory feedback_refuted_research_rerun_one_tier_up). No refutation -> the node never runs.
// 10. The critic moved to medium effort and checks cross-repo directions and caller links.
// 11. Every node's routing is returned as `routing` and written to the report's Provenance, so a
//    reader can say which agent/model/effort produced which part.

const A = args || {}
if (typeof A.question !== 'string' || !A.question.trim()) throw new Error('args.question is required')
if (typeof A.reportPath !== 'string' || !A.reportPath.startsWith('/')) throw new Error('args.reportPath must be an absolute path')
const REPO = typeof A.repo === 'string' ? A.repo : ''
// Other projects the question is ABOUT, beside REPO: searched in both directions
// (REPO's tracker for each name, each repo's tracker for REPO's name).
const RELATED = Array.isArray(A.relatedRepos) ? A.relatedRepos.filter(r => typeof r === 'string' && r) : []
// URLs the caller names: always deep-read, never ranked away.
const LINKS = Array.isArray(A.links) ? A.links.filter(u => typeof u === 'string' && u) : []
const READ_MAX = Number.isInteger(A.readMax) ? A.readMax : 6        // triaged URLs deep-read
const READ_BATCH = 3                                                // URLs per reader agent
const VERIFY_MAX = Number.isInteger(A.verifyMax) ? A.verifyMax : 5  // claims refuted
const SOURCES = ['github-issues', 'github-discussions', 'github-releases', 'exa', 'context7',
  'firecrawl-developer', 'firecrawl-search', 'last30days']

// One routing table, used for dispatch AND returned as provenance, so the two cannot drift.
const ROUTE = {
  plan: { model: 'sonnet', effort: 'medium' },
  triage: { agentType: 'Explore', model: 'sonnet', effort: 'low' },
  readLinks: { agentType: 'Explore', model: 'sonnet', effort: 'low' },
  read: { agentType: 'Explore', model: 'haiku' },
  sourceDive: { model: 'sonnet', effort: 'medium' },
  synthesize: { model: 'opus', effort: 'high' },
  refute: { model: 'sonnet', effort: 'medium' },
  critic: { agentType: 'Explore', model: 'sonnet', effort: 'medium' },
  adjudicate: { model: 'opus', effort: 'high' },
  reconcile: { model: 'sonnet', effort: 'medium' },
  advisor: { agentType: 'codex-sol-advisor' },
}
const routing = []
const run = (key, label, phaseName, prompt, extra = {}) => {
  const r = ROUTE[key]
  routing.push({ node: label, agentType: r.agentType || 'general-purpose', model: r.model || '(codex)', effort: r.effort || '(default)' })
  return agent(prompt, { label, phase: phaseName, ...r, ...extra })
}

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
    codeSearch: {
      type: 'array',
      items: {
        type: 'object',
        required: ['query', 'count', 'rc'],
        properties: { query: { type: 'string' }, count: { type: 'number' }, rc: { type: 'number' }, topUrls: { type: 'array', items: { type: 'string' } } },
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
    loadBearing: {
      type: 'array',
      items: {
        type: 'object',
        required: ['claim', 'source'],
        properties: { claim: { type: 'string' }, source: { type: 'string' }, absence: { type: 'boolean' } },
      },
    },
  },
}
const VERDICT = {
  type: 'object',
  required: ['claim', 'refuted', 'evidence'],
  properties: { claim: { type: 'string' }, refuted: { type: 'boolean' }, evidence: { type: 'string' }, controlArm: { type: 'string' } },
}
const CRITIC = {
  type: 'object',
  required: ['gaps'],
  properties: { gaps: { type: 'array', items: { type: 'object', required: ['gap', 'nextProbe'], properties: { gap: { type: 'string' }, nextProbe: { type: 'string' } } } } },
}

phase('Plan')
const plan = await run('plan', 'plan+fetch', 'Plan', [
  `QUESTION: ${A.question}`,
  REPO ? `REPO: ${REPO}` : 'REPO: (none — do NOT pick github-* sources; if the question clearly names one project, say so in rationale so the caller can re-run with args.repo)',
  RELATED.length ? `RELATED REPOS: ${RELATED.join(', ')}` : '',
  'LOCAL CORPORA FIRST (.claude/rules/research-doc-sources.md): for Claude Code / codex / cursor behaviour grep',
  '~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/<tool>/; for a library in',
  'docs/research/mintlify-catalog.md grep docs/research/mintlify-cache/; and grep the offline mirrors under',
  'docs/research/kb/raw/. Fan out only for what those do not answer.',
  `AVAILABLE SOURCES: ${SOURCES.join(', ')} (see \`mise run research-fanout -- --list-sources\`).`,
  'Choose only the sources that fit the question: API/library behaviour -> github-* + firecrawl-developer + context7;',
  'recent community sentiment -> last30days + exa; general web -> exa + firecrawl-search. Write 1-3 query variants',
  '(short search terms, not sentences). For each variant run exactly:',
  `  mise run research-fanout -- "<query>" ${REPO ? `--repo ${REPO} ` : ''}--sources <comma list>`,
  'and record the manifest path it prints and its real exit code.',
  RELATED.length ? [
    'CROSS-REFERENCE BOTH DIRECTIONS: for each related repo R, also run research-fanout with `--repo R` and a query',
    `naming ${REPO || 'the main project'}, and one with ${REPO ? `\`--repo ${REPO}\`` : 'the main repo'} naming R. A relationship`,
    'searched from one side only is a gap, not a finding.',
  ].join('\n') : '',
  'GITHUB CODE SEARCH (for "how do real projects configure X" questions only): `gh api -X GET search/code -f q=\'<q>\'`.',
  'REST syntax: no OR, no parentheses, no `**`; use `filename:`/`path:`/`repo:`/`org:` and run one query per',
  'alternative, then union. The bucket is 10 requests/min and a 403 is RATE LIMIT, not zero results. The tokenizer',
  'drops punctuation, so re-fetch and grep each hit before counting it. Record every query with its count and rc in',
  'codeSearch, plus one control query that must hit.',
  'Set sourceDive=true only when REPO is set AND the question is about what the code DOES (behaviour, a flag, a bug),',
  'where reading source at the release tag beats issues.',
].filter(Boolean).join('\n'), { schema: PLAN })
if (plan === null) return { status: 'plan-null', routing }
const manifests = plan.runs.filter(r => r.manifest).map(r => r.manifest)
if (!manifests.length) return { status: 'no-manifests', plan, routing }
log(`Plan: ${plan.runs.length} fanout run(s); ${(plan.codeSearch || []).length} code search(es); sourceDive=${plan.sourceDive}`)

phase('Triage')
const triage = await run('triage', 'triage', 'Triage', [
  `QUESTION: ${A.question}`,
  `Read these research-fanout manifests and every <source>.json beside them:\n${manifests.join('\n')}`,
  plan.codeSearch && plan.codeSearch.length ? `Code-search hits (already verified by the planner): ${JSON.stringify(plan.codeSearch)}` : '',
  'Dedup hits across sources by URL (record which sources found each). Rank by likely value for the QUESTION:',
  'primary sources (source code, merged PRs, maintainer answers, release notes) above secondary ones (blogs, forums).',
  `Choose at most ${READ_MAX} URLs worth deep-reading, each with a one-line reason. Prefer a mix: at least one primary`,
  'source per project the QUESTION names. List every source whose status is empty_unverified or error in',
  'unverifiedEmpty — those are gaps, not "no results".',
  LINKS.length ? `Do NOT choose these (the caller's links, read separately): ${LINKS.join(' ')}` : '',
].filter(Boolean).join('\n'), { schema: TRIAGE })
if (triage === null) return { status: 'triage-null', plan, routing }
const linkSet = new Set(LINKS)
const triaged = triage.read.filter(u => !linkSet.has(u.url))
const toRead = triaged.slice(0, READ_MAX)
if (triaged.length > READ_MAX) log(`Triage: dropped ${triaged.length - READ_MAX} URL(s) over readMax: ${triaged.slice(READ_MAX).map(u => u.url).join(' ')}`)

phase('Read')
const READ_RULES = [
  'Read each page IN FULL, not its first screen: list its section headings, and quote every section that names an',
  'entity in the QUESTION. Extract claims that bear on the QUESTION, each with a VERBATIM quote and the URL. Record a',
  'claim of ABSENCE ("X does not do Y") only with the exact search you ran and a control term that did match.',
  'GitHub issue/PR/discussion: `gh api` (issue + comments, PR body + review comments; discussions via `gh api graphql`).',
  'Other pages: `firecrawl scrape <url> --format markdown` (or the offline copy under docs/research/kb/raw/ when one',
  'exists — say which). Never print environment values.',
]
// Each reader keeps its identity: a reader that returns null is a GAP the report must
// name, never a silent drop (a null filtered away reads as "nothing to say").
const readers = []
for (let i = 0; i < LINKS.length; i += READ_BATCH) {
  const batch = LINKS.slice(i, i + READ_BATCH)
  const n = Math.floor(i / READ_BATCH) + 1
  readers.push({ urls: batch, run: () => run('readLinks', `read-link:${n}`, 'Read', [
    `QUESTION: ${A.question}`, 'The caller named these links; every one must be read.', ...READ_RULES,
    ...batch.map(u => `- ${u}`),
  ].join('\n'), { schema: CLAIMS }) })
}
const batches = []
for (let i = 0; i < toRead.length; i += READ_BATCH) batches.push(toRead.slice(i, i + READ_BATCH))
batches.forEach((batch, i) => readers.push({ urls: batch.map(u => u.url), run: () => run('read', `read:${i + 1}/${batches.length}`, 'Read', [
  `QUESTION: ${A.question}`, ...READ_RULES,
  ...batch.map(u => `- ${u.url}  (${u.why})`),
].join('\n'), { schema: CLAIMS }) }))
if (plan.sourceDive && REPO) {
  // general-purpose, not Explore: the dive clones into $TMPDIR and deletes it, and the
  // built-in Explore agent may not create or delete files. It pays the CLAUDE.md payload
  // only on the runs that need a clone.
  readers.push({ urls: [`${REPO} (source at the latest release tag)`], run: () => run('sourceDive', 'source-dive', 'Read', [
    `QUESTION: ${A.question}`,
    `Shallow-clone ${REPO} at its LATEST RELEASE TAG (\`gh api repos/${REPO}/releases/latest --jq .tag_name\`) into $TMPDIR,`,
    'grep for the mechanism the QUESTION is about, and extract claims about what the code does, each with file:line and a',
    'verbatim quote. Also say whether the default branch has changed that code since the tag (a merged-but-unreleased fix),',
    'and for an absence claim run `git log -S` over history so added-then-removed code is not missed. Every grep that',
    'returns nothing needs a control term that does match. Delete the clone when done.',
  ].join('\n'), { schema: CLAIMS }) })
}
const readResults = await parallel(readers.map(r => r.run))
const claims = readResults.flatMap(r => (r === null ? [] : r.claims))
const failedReads = readers.flatMap((r, i) => (readResults[i] === null ? r.urls : []))
log(`Read: ${claims.length} claim(s) from ${readers.length} reader(s) (${LINKS.length} caller link(s)); ${failedReads.length} unread`)

phase('Synthesize')
const synth = await run('synthesize', 'synthesize', 'Synthesize', [
  `QUESTION: ${A.question}`,
  `Write the research report to ${A.reportPath}. Inputs: the claims JSON below, the triage hit list, the code-search`,
  `results, and the manifests (${manifests.join(', ')}). Resolve conflicts explicitly (source code and merged PRs beat`,
  'issue threads; newer beats older; say which you trusted and why). Name every gap from unverifiedEmpty as a gap,',
  'never as "nothing found". Every FAILED READ below is a gap too: the reader for it failed, so its content is unknown.',
  'Keep distinct claims distinct: what a project SHIPS in code, what its docs/discussions PROPOSE or recommend, and what',
  'a THIRD party documents about it are three different claims — never collapse them into one headline.',
  'Sections: Answer, Evidence (claim | URL or file:line | quote), Conflicts resolved, Gaps, Recommendation,',
  'Provenance (the ROUTING table below, as a table), ## GitHub repos touched (per .claude/rules/research-repo-enumeration.md).',
  `Return the path and the claims the Answer depends on (at most ${VERIFY_MAX}); mark absence=true on every claim`,
  'that something does NOT exist or does NOT happen — those are the easiest to get wrong.',
  LINKS.length ? `CALLER LINKS (each must be cited or named as unread): ${LINKS.join(' ')}` : '',
  `CLAIMS:\n${JSON.stringify(claims)}`,
  `TRIAGE:\n${JSON.stringify({ hits: triage.hits, unverifiedEmpty: triage.unverifiedEmpty })}`,
  `CODE SEARCH:\n${JSON.stringify(plan.codeSearch || [])}`,
  `FAILED READS:\n${JSON.stringify(failedReads)}`,
  `ROUTING:\n${JSON.stringify(routing)}`,
].filter(Boolean).join('\n'), { schema: SYNTH })
if (synth === null) return { status: 'synth-null', plan, triage, claims, routing }

phase('Verify')
const loadBearing = synth.loadBearing.slice(0, VERIFY_MAX)
if (synth.loadBearing.length > VERIFY_MAX) log(`Verify: ${synth.loadBearing.length - VERIFY_MAX} load-bearing claim(s) over verifyMax left UNVERIFIED`)
const refuteOne = (c, i) => () => run('refute', `refute:${i + 1}/${loadBearing.length}`, 'Verify', [
  'Try to REFUTE this claim by re-probing its PRIMARY source yourself (open the URL / read the file at the cited ref).',
  'Default to refuted=true if you cannot confirm it. Every negative needs a control arm',
  '(.claude/rules/probes-need-a-control-arm.md); record it in controlArm.',
  c.absence ? 'This is an ABSENCE claim: confirm it by a SECOND, independent route (e.g. code search AND a clone grep AND `git log -S`, or the other project\'s tracker), each with its own control term.' : '',
  `CLAIM: ${c.claim}`, `SOURCE: ${c.source}`,
].filter(Boolean).join('\n'), { schema: VERDICT })
const [verdictList, critic] = await Promise.all([
  parallel(loadBearing.map(refuteOne)),
  parallel([() => run('critic', 'critic', 'Verify', [
    `Read the report at ${synth.reportPath} for the QUESTION: ${A.question}`,
    'What is missing — a source never queried, a claim never checked, a primary source never read, a version or',
    'release never confirmed, a related project searched from only one side, a caller link never cited, or two',
    'distinct claims (shipped vs proposed vs documented-by-others) merged into one? Give each gap with the concrete',
    'next probe. Return an empty list if there is none.',
  ].join('\n'), { schema: CRITIC })]).then(r => r[0]),
])
// A refuter that returned null leaves its claim UNVERIFIED, never confirmed.
const verdicts = loadBearing.map((c, i) => verdictList[i] || { claim: c.claim, refuted: null, evidence: 'refuter returned null — UNVERIFIED' })
const unverified = verdicts.filter(v => v.refuted === null)
const flagged = verdicts.filter(v => v.refuted === true)

// One tier up before a refutation is allowed to rewrite the report.
let refuted = flagged
let adjudication = null
if (flagged.length) {
  adjudication = await run('adjudicate', 'adjudicate', 'Verify', [
    'Independent refuters flagged the claims below as REFUTED. Re-check each against its primary source yourself and',
    'decide: upheld (the claim really is wrong) or overturned (the refuter erred). Weigh the claim\'s own evidence against',
    'the refuter\'s; an absence verdict needs a control arm. Return one verdict per claim: refuted=true means UPHELD.',
    `REPORT: ${synth.reportPath}`,
    `FLAGGED: ${JSON.stringify(flagged)}`,
  ].join('\n'), { schema: { type: 'object', required: ['verdicts'], properties: { verdicts: { type: 'array', items: VERDICT } } } })
  if (adjudication === null) log('Verify: adjudicator returned null — refutations stand UNCONFIRMED')
  else refuted = adjudication.verdicts.filter(v => v.refuted)
}
const gaps = critic === null ? null : critic.gaps
log(`Verify: ${flagged.length} flagged, ${refuted.length} upheld, ${unverified.length} unverified of ${verdicts.length} load-bearing claim(s)`)

// The report on disk must carry the verification outcome: a refuted claim left in the
// Answer is worse than no report. Reconcile only when there is something to write.
let reconciled = true
if (critic === null || unverified.length || flagged.length || gaps.length) {
  const reconcile = await run('reconcile', 'reconcile', 'Verify', [
    `Edit the research report at ${synth.reportPath} in place. Add a "## Verification" section listing each`,
    'load-bearing claim as confirmed, refuted-and-upheld (with the evidence), refuted-but-overturned by the adjudicator,',
    'or unverified. Correct or strike every UPHELD refuted claim wherever the Answer or Recommendation relies on it, and',
    'say how the conclusion changes. Append the critic gaps to the Gaps section. If the critic or adjudicator result is',
    'null, say that step did not run. Keep the Provenance table and add the Verify nodes to it.',
    `VERDICTS: ${JSON.stringify(verdicts)}`,
    `ADJUDICATION: ${JSON.stringify(adjudication)}`,
    `CRITIC GAPS: ${JSON.stringify(gaps)}`,
    `ROUTING: ${JSON.stringify(routing)}`,
  ].join('\n'))
  reconciled = reconcile !== null
  if (!reconciled) log('Verify: reconcile returned null — the report on disk does NOT reflect verification')
}

let advice = null
if (A.advisor) {
  phase('Advise')
  advice = await run('advisor', 'codex-sol-advisor', 'Advise', `Second opinion on the recommendation in ${synth.reportPath} (question: ${A.question}). Refuted claims: ${JSON.stringify(refuted)}. Return a verdict and the deciding risk.`)
  if (advice === null) log('Advise: codex-sol-advisor returned null (escalation per .claude/token-routing.md item 1)')
}

// Status: complete | verify-null | reconcile-null | plan-null | no-manifests | triage-null | synth-null.
// verify-null now means EVERY refuter returned null (nothing was verified at all).
const status = verdicts.length && unverified.length === verdicts.length ? 'verify-null' : !reconciled ? 'reconcile-null' : 'complete'
return { status, reportPath: synth.reportPath, plan, triage, claims: claims.length, failedReads, verdicts, adjudication, refuted, gaps, advice, routing }
