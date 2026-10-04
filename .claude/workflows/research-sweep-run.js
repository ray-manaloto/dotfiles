export const meta = {
  name: 'research-sweep-run',
  description: 'Fan a research question out to many sources via `mise run research-fanout`, deep-read the best hits cheaply, synthesize once on Opus, and refute the load-bearing claims one by one.',
  whenToUse: 'When a question needs evidence from several sources (GitHub issues/PRs/discussions/releases/code, exa, context7, firecrawl, last30days) and one context should not spend frontier tokens on fetching and reading.',
  phases: [
    { title: 'Plan', detail: 'pick sources and queries, run research-fanout plus the MANDATORY GitHub code search with its controls through one research-fanout probe (sonnet, medium)' },
    { title: 'Dependencies', detail: 'MANDATORY: github issues/discussions/releases for repo + every related repo, both directions, then one probe that reads those manifests (one sonnet/low agent per repo)' },
    { title: 'Mirror', detail: 'MANDATORY: every caller link saved offline by a research-fanout probe + a probe-written README index (one haiku agent per link)' },
    { title: 'Triage', detail: 'rank and dedup the hits, choose what to deep-read; caller links always read (Explore + sonnet, low)' },
    { title: 'Read', detail: 'caller links from their offline mirror (sonnet) + triaged URLs (haiku) in batches; optional source dive at the release tag' },
    { title: 'Synthesize', detail: 'one Opus pass writes the report (opus, high)' },
    { title: 'Verify', detail: 'one independent refuter per load-bearing claim (sonnet), a completeness critic, an Opus adjudicator for any refuted or misleading flag, then reconcile' },
    { title: 'Advise', detail: 'optional codex-sol-advisor second opinion (codex tokens, not Claude)' },
    { title: 'Retrospect', detail: 'a READ-ONLY Explore agent proposes tuning from what this run found hard; a haiku writer saves it as a PROPOSAL FILE under docs/research/kb/reports/agents/ — never applied (#1502)' },
  ],
}

// Model/effort routing — the cost reasoning lives here so it is reviewed with the code.
// 1. Every workflow agent inherits this repo's CLAUDE.md + eager rules (~150 KB, measured
//    2026-09-26 as `cat AGENTS.md .claude/CLAUDE.md .claude/rules/*.md | wc -c` = 152,855) UNLESS its agentType is a built-in that omits them (Explore). So agent
//    COUNT dominates the cost of cheap steps: bulk reading runs as Explore on haiku, in
//    batches, never one agent per item.
// 2. Fetching is not reasoning: `mise run research-fanout` does it with no model at all.
// 3. Judgment is concentrated in Synthesize (opus/high), plus an Adjudicate node (opus/high) that
//    runs ONLY when a refuter flags a claim. Fable is never used here — escalation is
//    `.claude/token-routing.md`'s. A typical run is ~11-17 agents (was ~9-15 before the 2026-10-02
//    Retrospect phase added one Explore and one haiku writer).
// 4. The advisor runs on codex (codex-sol-advisor), spending codex tokens, not Claude's.
// 5. The critic is Explore on SONNET: it reads one report and needs judgment, but still skips
//    the CLAUDE.md payload. The source dive is general-purpose because Explore may not create
//    or delete files (it clones into $TMPDIR).
// Tuning 2026-09-29b (session 5545fa41; evidence in
// docs/research/kb/reports/agents/omarchy-mise-dotfiles-crossref-sweep-2026-09-29.md and the
// superseded mise-dotfiles-omarchy-2026-09-29.md):
// 6. TRIAGE moved haiku -> sonnet/low: it decides what is ever read, so a cheap ranking miss
//    propagates to every later node; it is still ONE Explore agent.
// 7. Caller-supplied LINKS bypass triage and its READ_MAX cap — and survive a null plan/triage
//    (the run continues on the links alone) — and are read on sonnet/low: a link
//    the user named is never a ranking decision, and the one missed section that caused the
//    2026-09-29b Omarchy headline lived in a page that WAS fetched but never read closely.
// 8. REFUTE is one agent PER load-bearing claim (independence: one refuter reasoning about five
//    claims anchors on its first verdict), must cross-check an ABSENCE claim by a second,
//    independent route with a control arm (.claude/rules/probes-need-a-control-arm.md), and must
//    also judge MISLEADING-BY-OMISSION: the 2026-09-29b Omarchy headline was TRUE (of shipped
//    code) and misleading (it omitted a documented workflow), so "is it false?" alone cannot
//    catch that class. A misleading claim is flagged exactly like a refuted one.
// 9. ADJUDICATE (opus/high, one tier above the refuters) runs only when a refuter flags a claim
//    (refuted OR misleading): a refutation rewrites the report, so it is confirmed before reconcile acts on it
//    (memory feedback_refuted_research_rerun_one_tier_up). No refutation -> the node never runs.
// 10. The critic moved to medium effort and checks cross-repo directions and caller links.
// 11. Every node's routing is returned as `routing` and written to the report's Provenance, so a
//    reader can say which agent/model/effort produced which part.
// Mandatory stages 2026-09-30 (Ray's rulings; docs/specs/research-enforcement-2026-09-30.md). Three
// sweeps that day skipped GitHub because `--list-sources` called every github-* source `absent`
// without --repo, and the planner obeyed it. So these no longer depend on a planner's choice:
// 12. DEPENDENCIES: github issues/discussions/releases for REPO and every related repo, both
//    directions, one sonnet/low agent per repo (query terms need a little judgment).
// 13. MIRROR: every caller link saved by the pinned firecrawl into
//    docs/research/kb/raw/<report-slug>/links/, one haiku agent per link (pure command
//    execution; general-purpose because Explore may not create files) + one haiku README index.
//    A link that will not fetch is a NAMED gap; a mirror agent that never ran is a mandatory gap.
// 14. CODE SEARCH: the planner must run >=1 query of its own + a must-hit control + a fresh
//    known-absent control; the workflow checks the rows, so skipping it cannot read as `complete`.
//    A planner must-hit is a guess (live run wf_b74e66f5-ca3: `filename:skills.rs repo:jdx/mise`
//    returned 0 and failed the sweep), so the workflow builds its own controls for two SEPARATE
//    questions. "Is GitHub code search working?" — the first dependency agent runs
//    SEARCH_HEALTH_CONTROL, and a 0 or a failure there is a gap blamed on gh/auth/rate limit.
//    "Is this repo searchable?" — every dependency probe checks `repos/<r>` (does it exist
//    UNDER THIS NAME? a rename redirects, and a renamed repo's old name searches as 0) and
//    `repo:<r> filename:README.md` (is a README.md of it indexed?). A README of 0 for a repo that
//    exists under its own name is a NOTE, not a gap, and only when health passed: code search does
//    not index some repos (measured 2026-09-30: the 0-star fork virajp/mise returns 0 although its
//    README.md is 8569 bytes) and some have no README.md (sphinx-doc/sphinx: README.rst). The health
//    row has its own role, so only a planner or README must-hit >0 satisfies the must-hit
//    requirement; a planner must-hit of 0 is a NOTE. A 403 is recorded as rateLimited, never as 0.
// 15. A ZERO IS ONLY EVIDENCE WHEN ITS OWN SHAPE IS ARMED (#1471). The health/README controls prove
//    the endpoint answers for THEIR query shape; a planner query whose own shape is broken returns 0,
//    and so does the known-absent control. So a planner `query` row of 0 counts only beside a
//    planner must-hit >0 with the SAME qualifier set (repo:/org:/path:/filename:/language:/...);
//    otherwise it is UNARMED — a named gap, never "no results" — and cannot satisfy the
//    "planner ran a query of its own" requirement.
// Mechanical evidence 2026-10-02 (#1514, #1473). A workflow has NO filesystem or shell of its own
// (`$CC/workflows.md:355`), so every mandatory-stage number used to be TYPED by an agent: an rc, a
// count, a byte size, an HTTP status read off a header. Now each mandatory stage runs ONE
// workflow-built `mise run research-fanout -- --probe-out <path> ...` command; python runs gh /
// firecrawl itself, records real exit codes to that manifest, and prints a final `PROBE-JSON` line.
// The agent copies that line verbatim, and the workflow accepts it only when its `probe_out` is the
// exact path the workflow asked for. The dependency probe also RE-READS each fan-out manifest, so the
// query that really ran and each required source's status come from the file, not the agent:
// `research-fanout` exits 0 when ANY source answered, so a run whose github-issues search failed
// (HTTP 422) while releases answered read as success (#1473, measured on jdx/rtx). What remains
// trusted is that an agent COPIED one line; the manifests are on disk for any reader to check.
// A mandatory stage that did not run or did not succeed adds to `mandatoryGaps`. `status` is the
// highest-precedence of `statuses`, and `statuses` lists EVERY degraded state that applies, so a
// mandatory gap is never hidden behind another status (#1513).

const A = args || {}
if (typeof A.question !== 'string' || !A.question.trim()) throw new Error('args.question is required')
if (typeof A.reportPath !== 'string' || !A.reportPath.startsWith('/')) throw new Error('args.reportPath must be an absolute path')
// `/../` in the report path would move every derived path (mirrors, slug, retrospect) somewhere else.
if (A.reportPath.split('/').some(s => s === '.' || s === '..')) throw new Error(`args.reportPath must not contain a "." or ".." segment, got ${JSON.stringify(A.reportPath)}`)
// Every repo name reaches shell commands (`--repo`, `--repo-check`, `--out`), so its SHAPE is the
// guard: owner/repo characters only, never a quote, space, `;` or `$`. A segment of only dots
// (`../..`) is shell-safe but turns `repos/<r>` into another API path, so it is refused too.
const REPO_SHAPE = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/
const dotOnly = s => /^\.+$/.test(s)
const repoOk = r => REPO_SHAPE.test(r) && !r.split('/').some(dotOnly)
const REPO_RULE = 'owner/repo ([A-Za-z0-9_.-], no dot-only segment)'
const REPO = typeof A.repo === 'string' ? A.repo : ''
if (REPO && !repoOk(REPO)) throw new Error(`args.repo must be ${REPO_RULE}, got ${JSON.stringify(REPO)}`)
// Other projects the question is ABOUT, beside REPO: searched in both directions
// (REPO's tracker for each name, each repo's tracker for REPO's name).
const RELATED = Array.isArray(A.relatedRepos) ? A.relatedRepos.filter(r => typeof r === 'string' && r) : []
RELATED.forEach(r => { if (!repoOk(r)) throw new Error(`args.relatedRepos entries must be ${REPO_RULE}, got ${JSON.stringify(r)}`) })
// Search terms are project NAMES, not owner/repo slugs: `repo:jdx/mise omarchy` found 17 hits
// where `repo:jdx/mise omacom/omarchy` found 3 (cold review 94f4e161 row 8).
const nameOf = r => r.split('/').pop()
// URLs the caller names: always deep-read, never ranked away.
// Normalized (no #fragment, no trailing slash) so one page is never read twice.
const norm = u => { const [path, ...frag] = u.split('#'); return path.replace(/\/+$/, '') + (frag.length ? '#' + frag.join('#') : '') }
const LINKS = Array.isArray(A.links) ? [...new Set(A.links.filter(u => typeof u === 'string' && u).map(norm))] : []
const READ_MAX = Number.isInteger(A.readMax) ? A.readMax : 6        // triaged URLs deep-read
const READ_BATCH = 3                                                // URLs per reader agent
const VERIFY_MAX = Number.isInteger(A.verifyMax) ? A.verifyMax : 5  // claims refuted
const SOURCES = ['github-issues', 'github-discussions', 'github-releases', 'exa', 'context7',
  'firecrawl-developer', 'firecrawl-search', 'last30days']
const FAILURE_CODES = new Set(['credits-exhausted', 'prerequisite', 'http-error', 'invalid-json', 'shape-error', 'provider-failure', 'process-failed', 'timeout', 'request-failed', 'credential-invalid', 'canary-failed', 'canary-empty', 'no-canary', 'not-found', 'redirected', 'empty-output', 'io-error', 'other'])
const WORKFLOW_CODES = new Set(['probe-missing', 'invalid-probe'])
const PROVISIONAL_ROUTES = { exa: [], context7: [], 'firecrawl-developer': [], 'firecrawl-search': ['serper', 'serpapi'] }
const MIRROR_ROUTES = ['firecrawl', 'webclaw']
const MAX_PROBE_ENTRIES = 8
const REQUIRED_FAILED = new RegExp(`^(${SOURCES.join('|')}): (ok|empty_verified|empty_unverified|error|skipped|not run|invalid|no manifest|unreadable)( \\((${[...FAILURE_CODES].join('|')})\\))?$`)
const requiredFailed = value => Array.isArray(value) && value.length <= MAX_PROBE_ENTRIES
  ? value.map(entry => typeof entry === 'string' && REQUIRED_FAILED.test(entry) ? entry : 'unrecognised required_failed entry')
  : ['unrecognised required_failed entry']
// The mandatory dependency-repo stage (12): every repo the question is about, searched on GitHub.
// Every one of these must answer (ok / empty_verified) — the probe reads each from the manifest (#1473).
const DEP_SOURCES = 'github-issues,github-discussions,github-releases'
// Deduplicated case-insensitively: GitHub names and this Mac's filesystem both are, so `jdx/Mise` and
// `jdx/mise` would share one deps directory and unlink each other's files.
const DEP_REPOS = [REPO, ...RELATED].filter(Boolean)
  .filter((r, i, all) => all.findIndex(o => o.toLowerCase() === r.toLowerCase()) === i)
// Optional per-run id stamped into every dependency fan-out manifest and required by its probe, so a
// manifest left by an EARLIER run of the same report is never this run's (cold review F3). Without it,
// freshness falls back to the manifest's age.
const RUN_ID = typeof A.runId === 'string' ? A.runId : ''
if (RUN_ID && !/^[A-Za-z0-9_][A-Za-z0-9_.-]*$/.test(RUN_ID)) throw new Error(`args.runId must be [A-Za-z0-9_.-]+ not starting with - or ., got ${JSON.stringify(RUN_ID)}`)
// null = "short search terms from the QUESTION"; a name = the other side of a relationship.
const depQueries = r => (r === REPO ? [null, ...RELATED.filter(o => o.toLowerCase() !== REPO.toLowerCase()).map(nameOf)] : [REPO ? nameOf(REPO) : null])
// The repository root: explicit, else the part of reportPath before its /docs/.
const docsAt = A.reportPath.lastIndexOf('/docs/')
// Normalised like python's Path() (so an echoed probe path still matches), and refused a `.`/`..` segment
// for the same reason reportPath is.
const ROOT = (typeof A.repoRoot === 'string' && A.repoRoot.startsWith('/') ? A.repoRoot
  : docsAt > 0 ? A.reportPath.slice(0, docsAt) : '').replace(/\/+/g, '/').replace(/\/+$/, '')
if (ROOT.split('/').some(s => s === '.' || s === '..')) throw new Error(`args.repoRoot must not contain a "." or ".." segment, got ${JSON.stringify(A.repoRoot)}`)
if (LINKS.length && !ROOT) throw new Error('args.repoRoot (absolute) is required when links are given and reportPath is not under <repo>/docs/')
// The report SLUG names this run's mirror and fan-out directories, so two reports must never share it
// (#1513): every docs/research/runs/<run>/report.md had the slug `report`, and each sweep overwrote the
// last one's mirrors. Under <ROOT>/docs/ it is the whole path below docs/, `/` -> `--` (so docs/foo.md and
// docs/research/foo.md differ);
// elsewhere it is the file name.
const DOCS_PREFIX = ROOT ? `${ROOT}/docs/` : null
const underDocs = DOCS_PREFIX && A.reportPath.startsWith(DOCS_PREFIX) ? A.reportPath.slice(DOCS_PREFIX.length) : null
const REPORT_SLUG = (underDocs || A.reportPath.split('/').pop()).replace(/\.md$/, '').split('/').join('--')
if (!/^[A-Za-z0-9_.-]+$/.test(REPORT_SLUG) || dotOnly(REPORT_SLUG)) throw new Error(`args.reportPath must be a path whose report slug is [A-Za-z0-9_.-]+ and not dot-only, got ${JSON.stringify(REPORT_SLUG)}`)
const MIRROR_DIR = `${ROOT}/docs/research/kb/raw/${REPORT_SLUG}/links`
const FANOUT_DIR = `.agent/kb/raw/research-fanout/${REPORT_SLUG}`
// The roles a PLANNER row may carry. `health`/`readme` are workflow-only (they can never satisfy the
// must-hit or the planner-query requirement), so they are not offered, and a planner row tagged with
// any other role is INERT (round-4 L1: fail closed, never promoted to `query`).
const PLAN_ROLES = ['query', 'must-hit', 'known-absent']
// Two questions, two controls (14). SEARCH_HEALTH_CONTROL asks "does code search answer at all?" (a
// repo known to be indexed; 9 hits measured 2026-09-30). README_CONTROL asks "is a README.md of THIS
// repo indexed?": a 0 there is not proof the search is broken — an unindexed repo (a low-star fork), a
// repo with no README.md (README.rst) and a renamed repo's old name all return 0 — so the repos API
// settles existence and name, and only health decides "broken".
const SEARCH_HEALTH_CONTROL = 'repo:cli/cli filename:README.md'
const README_CONTROL = r => `repo:${r} filename:README.md`
// Single-quote a value for the shell: a caller URL may carry `'` (legal, common in Wikipedia URLs).
// Every shell command below interpolates only a constant, a shape-checked value (repoOk,
// REPORT_SLUG, an integer) or a shq()-quoted one — ROOT included (round-4 L2).
const shq = v => `'${v.replace(/'/g, "'\\''")}'`
const FETCH = u => `mise exec -- firecrawl scrape ${shq(u)} --format markdown --only-main-content`

// Probes (#1514): one workflow-built command, one verbatim line back.
const PROBE = { type: 'object', required: ['line'], properties: { line: { type: 'string' } } }
const probeCmd = (out, flags) => `mise run research-fanout -- --probe-out ${shq(out)} ${flags.join(' ')}`
const COPY_LINE = 'Return its LAST stdout line — it starts with `PROBE-JSON ` — VERBATIM as `line`: copy it, never retype, reformat or summarise it, and never print environment values.'
// Accepted only when it parses AND names the exact manifest this workflow asked for.
const readProbe = (got, out) => {
  if (!got || typeof got.line !== 'string') return null
  try {
    const p = JSON.parse(got.line.trim().replace(/^PROBE-JSON\s+/, ''))
    return p && p.kind === 'probe' && p.probe_out === out && Array.isArray(p.probes) ? p : null
  } catch (e) {
    return null
  }
}
const probesOf = (p, kind) => (p ? p.probes.filter(x => x && x.kind === kind) : [])
// A code-search probe row in the shape every check below reads (count -1 = no count, never a 0).
// `incomplete` (GitHub's incomplete_results: the search timed out) is carried only when set; such a row is
// never an answer, so its 0 is never evidence of absence (cold review F17).
const codeRow = (x, source) => ({ query: x.query, role: x.role, source, count: x.count, rc: x.rc, rateLimited: x.rate_limited === true,
  ...(x.incomplete_results === true ? { incomplete: true } : {}) })

// One routing table, used for dispatch AND returned as provenance, so the two cannot drift.
const ROUTE = {
  plan: { model: 'sonnet', effort: 'medium' },
  deps: { model: 'sonnet', effort: 'low' },
  mirror: { model: 'haiku' },
  mirrorIndex: { model: 'haiku' },
  planManifests: { model: 'haiku' },
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
  // READ-ONLY by construction: Explore cannot edit, so a retrospect cannot tune its own rules.
  retrospect: { agentType: 'Explore', model: 'sonnet', effort: 'low' },
  retrospectWrite: { model: 'haiku' },
}
const routing = []
const run = (key, label, phaseName, prompt, extra = {}) => {
  const r = ROUTE[key]
  routing.push({ node: label, agentType: r.agentType || 'general-purpose', model: r.model || '(codex)', effort: r.effort || '(default)' })
  return agent(prompt, { label, phase: phaseName, ...r, ...extra })
}

const PLAN = {
  type: 'object',
  required: ['runs', 'codeSearchProbe', 'sourceDive'],
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
    codeSearchProbe: PROBE,
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
  required: ['claim', 'refuted', 'misleading', 'evidence', 'controlArm'],
  properties: {
    claim: { type: 'string' }, refuted: { type: 'boolean' },
    misleading: { type: 'boolean' }, omitted: { type: 'string' },
    evidence: { type: 'string' }, controlArm: { type: 'string' },
  },
}
const CRITIC = {
  type: 'object',
  required: ['gaps'],
  properties: { gaps: { type: 'array', items: { type: 'object', required: ['gap', 'nextProbe'], properties: { gap: { type: 'string' }, nextProbe: { type: 'string' } } } } },
}
const RETRO = {
  type: 'object',
  required: ['findings', 'proposals'],
  properties: {
    findings: { type: 'array', items: { type: 'string' } },
    proposals: { type: 'array', items: { type: 'object', required: ['target', 'change', 'why'], properties: { target: { type: 'string' }, change: { type: 'string' }, why: { type: 'string' } } } },
  },
}
const RETRO_WRITE = { type: 'object', required: ['written', 'path'], properties: { written: { type: 'boolean' }, path: { type: 'string' } } }
// The tracked findings tree (#1502, agent-artifact-conventions.md), named by the unique report slug, so
// it is never one of the files it proposes changing. A report beside docs/research/runs/ would land in a
// gitignored tree. With no known ROOT it sits beside the report.
const RETRO_PATH = ROOT ? `${ROOT}/docs/research/kb/reports/agents/research-sweep-retrospect-${REPORT_SLUG}.md`
  : `${A.reportPath.replace(/\.md$/, '')}.retrospect.md`

// Retrospect (#1502): every exit — early or late — goes through finish(), so a run that stopped at
// a null stage still records what was hard. It may only ever ADD to the result: it never changes
// `status`/`statuses`, so a failed retrospect cannot turn a failed run into `complete`.
const finish = async result => {
  if (A.retrospect === false) return { ...result, retrospect: { status: 'skipped', path: null } }
  phase('Retrospect')
  const facts = Object.fromEntries(Object.entries({
    status: result.status, statuses: result.statuses, mandatoryGaps: result.mandatoryGaps,
    stageGaps: result.stageGaps, fanoutGaps: result.fanoutGaps, mirrorGaps: result.mirrorGaps,
    codeSearchGaps: result.codeSearchGaps, codeSearchNotes: result.codeSearchNotes,
    failedReads: result.failedReads, unverifiedEmpty: result.triage ? result.triage.unverifiedEmpty : undefined,
    unverifiedClaims: Array.isArray(result.verdicts) ? result.verdicts.filter(v => v.refuted === null).map(v => v.claim) : undefined,
    criticGaps: result.gaps, adjudication: result.adjudication === null ? 'did not run or returned null' : undefined,
  }).filter(([, v]) => v !== undefined))
  const retro = await run('retrospect', 'retrospect', 'Retrospect', [
    `A research sweep just ended. QUESTION: ${A.question}`,
    `REPORT: ${A.reportPath}${['complete', 'provisional'].includes(result.status) ? '' : ' (may be missing or partial: the run did not complete)'}`,
    'You are READ-ONLY. Record what this run found HARD or MISSING — empty or unverified sources, mandatory gaps, failed',
    'reads, stages that returned null, controls that could not discriminate — each as one finding grounded in the RUN',
    'FACTS below. Then PROPOSE changes to the workflow (.claude/workflows/research-sweep-run.js), its fetcher',
    '(python/src/dotfiles_setup/research_fanout.py), its skill or rules that would have prevented each. A proposal is text',
    'for a human to turn into a spec + PR: never apply, edit or write anything. Return empty lists when nothing was hard.',
    `RUN FACTS: ${JSON.stringify(facts)}`,
  ].join('\n'), { schema: RETRO })
  if (!retro || !Array.isArray(retro.findings) || !Array.isArray(retro.proposals)) {
    log('Retrospect: the retrospect agent returned nothing usable — no proposal written')
    return { ...result, retrospect: { status: 'retrospect-null', path: null } }
  }
  const cell = v => String(v).replace(/\|/g, '\\|').replace(/\n/g, ' ')
  const text = [
    `# Research-sweep retrospect — ${REPORT_SLUG} (PROPOSAL ONLY)`, '',
    `Run status: \`${result.status}\` (statuses: ${(result.statuses || []).join(', ') || 'complete'}). Report: \`${A.reportPath}\`.`, '',
    '> Nothing here has been applied. Tuning the workflow, its fetcher, rules or settings happens only through a',
    '> spec + PR (#1502); this file is the input to that, written by a read-only agent.', '',
    '## What was hard or missing', '',
    ...(retro.findings.length ? retro.findings.map(f => `- ${f}`) : ['- nothing recorded']), '',
    '## Proposals', '',
    ...(retro.proposals.length ? ['| target | change | why |', '|---|---|---|', ...retro.proposals.map(p => `| ${cell(p.target)} | ${cell(p.change)} | ${cell(p.why)} |`)] : ['None.']), '',
  ].join('\n')
  const wrote = await run('retrospectWrite', 'retrospect-write', 'Retrospect', [
    `Write the text between the two marker lines below to ${RETRO_PATH} EXACTLY (create or overwrite that ONE file).`,
    'Create, edit or delete NO other file. Do not run anything else. Return written=true and path = the exact path you',
    'wrote.',
    '<<<RETROSPECT', text, 'RETROSPECT>>>',
  ].join('\n'), { schema: RETRO_WRITE })
  // A writer that reports any other path wrote somewhere it was not asked to: the phase FAILED.
  const status = !wrote ? 'write-null' : wrote.path !== RETRO_PATH ? 'write-mismatch' : wrote.written ? 'written' : 'write-failed'
  if (status !== 'written') log(`Retrospect: proposal not saved (${status})`)
  return { ...result, retrospect: { status, path: RETRO_PATH, findings: retro.findings.length, proposals: retro.proposals.length } }
}
const withStatuses = (status, extra) => ({ status, statuses: [status,
  ...(extra.mandatoryGaps && extra.mandatoryGaps.length ? ['mandatory-gap'] : []),
  ...(extra.stageGaps && extra.stageGaps.length ? [LINKS.length ? 'links-only' : 'stage-gap'] : [])], ...extra })

phase('Plan')
const PLAN_PROBE = `${FANOUT_DIR}/plan/code-search.json`
const planPrompt = [
  `QUESTION: ${A.question}`,
  REPO ? `REPO: ${REPO}` : 'REPO: (none — do NOT pick github-* sources; if the question clearly names one project, say so in rationale so the caller can re-run with args.repo)',
  RELATED.length ? `RELATED REPOS: ${RELATED.join(', ')}` : '',
  'LOCAL CORPORA FIRST (.claude/rules/research-doc-sources.md): for Claude Code / codex / cursor behaviour grep',
  '~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/<tool>/; for a library in',
  'docs/research/mintlify-catalog.md grep docs/research/mintlify-cache/; and grep the offline mirrors under',
  'docs/research/kb/raw/. Fan out only for what those do not answer.',
  `AVAILABLE SOURCES: ${SOURCES.join(', ')} (see \`mise run research-fanout -- --list-sources\`; \`needs --repo\` means usable with --repo).`,
  'Choose only the sources that fit the question: API/library behaviour -> github-* + firecrawl-developer + context7;',
  'recent community sentiment -> last30days + exa; general web -> exa + firecrawl-search. Write 1-3 query variants',
  '(short search terms, not sentences). For each variant run exactly:',
  `  mise run research-fanout -- "<query>" ${REPO ? `--repo ${REPO} ` : ''}--sources <comma list>`,
  'and record the manifest path it prints and its real exit code.',
  DEP_REPOS.length ? `A separate MANDATORY stage already runs ${DEP_SOURCES} for ${DEP_REPOS.join(', ')} (both directions for related repos); add github-* runs only for query variants it does not cover.` : '',
  'GITHUB CODE SEARCH — MANDATORY on every run, through ONE probe that runs every search itself and records the real',
  'count, exit code and HTTP status (never run `gh api search/code` yourself). Run exactly once, never piped:',
  `  mise run research-fanout -- --probe-out ${shq(PLAN_PROBE)} --code-search 'query=<q1>' [--code-search 'query=<q2>' ...] --code-search 'must-hit=<m>' [...] --code-search 'known-absent=<k>'`,
  'with every value single-quoted as one shell word. Roles:',
  '  query: 1-3 searches of your own for the QUESTION. REST code-search syntax: `filename:`/`path:`/`repo:`/`org:`/',
  '  `language:` qualifiers, no parentheses, no `**`; one query per alternative, then union. The tokenizer drops',
  '  punctuation, so re-fetch and grep each hit before counting it.',
  '  must-hit: for EVERY query, a control with the SAME qualifiers (same repo:/org:/path:/filename:/language: set) and a',
  '  term you know matches — a query that returns 0 counts as evidence ONLY beside a same-shape must-hit that hits; one',
  '  must-hit arms every query sharing its qualifiers.',
  '  known-absent: one control built from a nonsense token you invent FRESH now (never one copied from a report or',
  '  rule — writing a control down destroys it); it must return 0.',
  `The workflow also runs \`repo:<r> filename:README.md\` per dependency repo${DEP_REPOS.length ? `: ${DEP_REPOS.join(', ')}` : ''}.`,
  `Then set codeSearchProbe.line to the probe's LAST stdout line (it starts with \`PROBE-JSON \`) copied VERBATIM.`,
  'Set sourceDive=true only when REPO is set AND the question is about what the code DOES (behaviour, a flag, a bug),',
  'where reading source at the release tag beats issues.',
].filter(Boolean).join('\n')
const depOut = (r, k) => `${FANOUT_DIR}/deps/${r.replace('/', '--')}/${k + 1}`
const depProbeOut = r => `${FANOUT_DIR}/deps/${r.replace('/', '--')}/probe.json`
const depPrompt = (r, i) => [
  `MANDATORY DEPENDENCY-REPO STAGE for ${r}: it runs whatever any planner chose. QUESTION: ${A.question}`,
  'From the repository root, run each command below exactly, in order, never piped (queries are project NAMES or',
  'short search terms, never owner/repo slugs):',
  ...depQueries(r).map((q, k) => `  mise run research-fanout -- "${q === null ? '<2-4 short search terms from the QUESTION>' : q}" --repo ${r} --sources ${DEP_SOURCES} --out ${shq(depOut(r, k))}${RUN_ID ? ` --request-id ${RUN_ID}` : ''}`),
  'Then run this probe exactly, never piped — it re-reads those manifests (which query really ran, and whether',
  `${DEP_SOURCES} each answered) and runs the code-search and repository checks itself:`,
  '  ' + probeCmd(depProbeOut(r), [
    ...depQueries(r).map((_, k) => `--fanout-manifest ${shq(`${depOut(r, k)}/manifest.json`)}`),
    `--require ${DEP_SOURCES}`,
    RUN_ID ? `--expect-request-id ${RUN_ID}` : '',
    `--code-search ${shq(`readme=${README_CONTROL(r)}`)}`,
    i === 0 ? `--code-search ${shq(`health=${SEARCH_HEALTH_CONTROL}`)}` : '',
    `--repo-check ${r}`,
  ].filter(Boolean)),
  COPY_LINE,
].join('\n')
const mirrorPath = n => `${MIRROR_DIR}/${n}.md`
const mirrorProbeOut = n => `${MIRROR_DIR}/${n}.probe.json`
const mirrorPrompt = (url, n) => [
  'MANDATORY MIRROR STAGE: save one caller link as an agent-optimized offline copy. Run exactly, never piped (the probe',
  'runs the pinned firecrawl itself and measures what landed):',
  // No `cd ROOT`: research-fanout is a task of THIS repo, and every path below is absolute and quoted.
  '  ' + probeCmd(mirrorProbeOut(n), [`--mirror-url ${shq(url)}`, `--mirror-path ${shq(mirrorPath(n))}`]),
  'Do not retry with another tool and do not edit any file.',
  COPY_LINE,
].join('\n')
const [planGot, depResults, mirrorResults] = await Promise.all([
  run('plan', 'plan+fetch', 'Plan', planPrompt, { schema: PLAN }),
  DEP_REPOS.length ? parallel(DEP_REPOS.map((r, i) => () => run('deps', `deps:${r}`, 'Dependencies', depPrompt(r, i), { schema: PROBE }))) : [],
  LINKS.length ? parallel(LINKS.map((u, i) => () => run('mirror', `mirror:${i + 1}/${LINKS.length}`, 'Mirror', mirrorPrompt(u, i + 1), { schema: PROBE }))) : [],
])
const plan = planGot && typeof planGot === 'object' && Array.isArray(planGot.runs) ? planGot : null

// Mandatory-stage bookkeeping: a stage that did not run or did not succeed is a mandatory gap, never a silent skip.
const mandatoryGaps = []
if (!DEP_REPOS.length) mandatoryGaps.push('dependency-repo stage: no args.repo or args.relatedRepos, so no dependency repo issues/PRs/discussions/releases were searched — re-run with args.repo')
// An agent may echo a query with its quotes; compare the bare terms. A slug (`other/tool`) in the
// question-terms slot is still the repo's NAME (round-4 L4).
const unquote = q => q.trim().replace(/^(["'])(.*)\1$/, '$2').trim()
const asName = q => unquote(q).toLowerCase().split('/').pop()
const REPO_NAMES = DEP_REPOS.map(r => nameOf(r).toLowerCase())
const dependencyNotes = []
const depProbes = DEP_REPOS.map((r, i) => readProbe(depResults[i], depProbeOut(r)))
const dependencyRuns = DEP_REPOS.flatMap((r, i) => {
  if (depResults[i] === null) {
    mandatoryGaps.push(`dependency-repo stage for ${r}: agent reported nothing (null)`)
    return []
  }
  const p = depProbes[i]
  if (p === null) {
    mandatoryGaps.push(`dependency-repo stage for ${r}: no PROBE-JSON line for ${depProbeOut(r)} — the probe did not run or its line was not copied`)
    return []
  }
  const rows = probesOf(p, 'fanout-manifest')
  // A tracker the repo has DISABLED is the world, not a failed search: a repo with Discussions off returns
  // empty_unverified forever (cold review F1, live: rhysd/actionlint). The repos API says which are off.
  const check = probesOf(p, 'repo-check').find(x => x.repo === r) || {}
  // github-issues searches search/issues, which also returns PULL REQUESTS: it is dead only when issues AND
  // pull requests are both off (round-2 N1, live: apache/kafka has issues off, PRs on, and answers ok).
  const disabled = [check.has_issues === false && check.has_pull_requests === false ? 'github-issues' : '',
    check.has_discussions === false ? 'github-discussions' : ''].filter(Boolean)
  disabled.forEach(d => dependencyNotes.push(`${r} has ${d.replace('github-', '')} disabled (repos API) — ${d} not searchable there; not a gap`))
  return depQueries(r).map((q, k) => {
    const want = `${depOut(r, k)}/manifest.json`
    const m = rows.find(x => typeof x.path === 'string' && x.path.endsWith(want))
    if (!m || !m.exists) {
      mandatoryGaps.push(`dependency-repo stage for ${r}: run ${k + 1} wrote no manifest (${want})`)
      return { repo: r, query: null, manifest: want, fresh: false, ok: false, requiredFailed: ['no manifest'] }
    }
    const ran = typeof m.query === 'string' ? unquote(m.query) : ''
    if (!m.fresh) mandatoryGaps.push(`dependency-repo stage for ${r}: ${want} is ${m.age_s === null ? 'undated' : `${m.age_s}s old`} — not written by this run`)
    // WHICH query ran comes from the manifest, never from the agent (F6, S3, R8).
    if (q !== null && ran !== q) mandatoryGaps.push(`dependency-repo stage for ${r}: cross-direction query "${q}" not run (got "${ran}")`)
    if (q === null && ran.startsWith('<')) mandatoryGaps.push(`dependency-repo stage for ${r}: the question-terms placeholder "${ran}" ran verbatim, so ${r} was not searched for the QUESTION`)
    else if (q === null && REPO_NAMES.includes(asName(ran))) mandatoryGaps.push(`dependency-repo stage for ${r}: question-terms query "${ran}" is a repo name, so ${r} was not searched for the QUESTION`)
    const failed = requiredFailed(m.required_failed)
      .filter(f => !disabled.some(d => f.startsWith(`${d}:`)))
    // #1473: releases answering must not hide an issues search that failed.
    if (failed.length) mandatoryGaps.push(`dependency-repo stage for ${r}: "${ran}" — ${failed.join('; ')}`)
    return { repo: r, query: ran, manifest: m.path, fresh: m.fresh === true, ok: m.fresh === true && !failed.length, requiredFailed: failed }
  })
})
const mirrorProbes = LINKS.map((u, i) => readProbe(mirrorResults[i], mirrorProbeOut(i + 1)))
const mirror = LINKS.map((url, i) => {
  const path = mirrorPath(i + 1)
  const m = probesOf(mirrorProbes[i], 'mirror').find(x => x.url === url && x.path === path)
  if (!m) {
    const why = mirrorResults[i] === null ? 'agent reported nothing (null)' : `no PROBE-JSON line for ${mirrorProbeOut(i + 1)}`
    mandatoryGaps.push(`mirror stage for ${url}: ${why}`)
    return { url, path, rc: null, bytes: 0, code: 'probe-missing' }
  }
  if (!MIRROR_ROUTES.includes(m.route) || !(m.code === '' || FAILURE_CODES.has(m.code)) ||
      !Number.isInteger(m.rc) || !Number.isInteger(m.bytes) || typeof m.provisional !== 'boolean' ||
      (m.code === '' && !(m.rc === 0 && m.bytes >= 0))) {
    mandatoryGaps.push(`mirror stage for ${url}: probe row failed validation`)
    return { url, path, rc: null, bytes: 0, code: 'invalid-probe' }
  }
  return { url, path, rc: m.rc, bytes: m.bytes, code: m.code === '' && m.bytes === 0 ? 'empty-output' : m.code,
    httpStatus: Number.isInteger(m.http_status) ? m.http_status : null,
    route: m.route, provisional: m.provisional }
})
const mirrored = m => m.rc === 0 && m.bytes > 0 && !m.code
const codeText = m => {
  const code = m.code === 'http-error' && Number.isInteger(m.httpStatus) && m.httpStatus >= 100 && m.httpStatus <= 599
    ? `http-error ${m.httpStatus}` : FAILURE_CODES.has(m.code) || WORKFLOW_CODES.has(m.code) ? m.code : 'invalid-probe'
  return m.route === 'webclaw' ? `credits-exhausted; webclaw ${code}` : code
}
// A link firecrawl could not fetch is the WORLD, not the process: a named gap, not a mandatory one.
const mirrorGaps = mirror.filter(m => m.rc !== null && m.code).map(m => `${m.url}: not mirrored (${codeText(m)})`)
// Code search = the planner's rows + the search-health control + one README control per searched repo.
const answered = c => c.rc === 0 && !c.rateLimited && !c.incomplete && c.count >= 0
const outcome = c => (c.rateLimited ? 'was RATE-LIMITED (HTTP 403/429), not 0'
  : c.incomplete ? `returned INCOMPLETE results (count=${c.count}; the search timed out)` : `returned count=${c.count} rc=${c.rc}`)
// Question 1, asked once (by the first dependency agent): does GitHub code search answer at all?
const healthProbe = depProbes.length ? probesOf(depProbes[0], 'code-search').find(x => x.role === 'health') : undefined
const healthRow = healthProbe ? codeRow(healthProbe, 'workflow') : null
const healthFailed = healthRow !== null && !(answered(healthRow) && healthRow.count > 0)
const healthOk = healthRow !== null && !healthFailed
if (healthFailed) mandatoryGaps.push(`code search: search-health control "${SEARCH_HEALTH_CONTROL}" ${outcome(healthRow)} — gh auth, rate-limit or search is broken`)
else if (depProbes.length && depProbes[0] !== null && !healthRow) mandatoryGaps.push(`code search: search-health control "${SEARCH_HEALTH_CONTROL}" was not run, so whether code search answers is unverified`)
// Question 2, per repo: does it exist under THIS name (repos API), and is a README.md of it indexed?
const RATE_LIMIT_STATUS = [403, 429]
const repoCheckGap = (r, ex) => {
  if (!ex) return `could not check ${r} via the repos API (no repo-check probe row)`
  const fullName = typeof ex.full_name === 'string' && REPO_SHAPE.test(ex.full_name.trim()) ? ex.full_name.trim() : ''
  if (ex.http_status === 404) return `dependency repo ${r} not found via the repos API (HTTP 404)`
  if (ex.http_status !== 200 || ex.rc !== 0 || !fullName) return `could not check ${r} via the repos API (HTTP ${ex.http_status}${RATE_LIMIT_STATUS.includes(ex.http_status) ? ' — rate-limited or forbidden' : ''}${ex.http_status === 200 ? `, rc=${ex.rc}, fullName "${fullName}"` : ''})`
  // The API follows a rename (jdx/rtx -> jdx/mise, rc=0) while search under the old name returns 0.
  if (fullName.toLowerCase() !== r.toLowerCase()) return `dependency repo ${r} redirects to ${fullName} — re-run with repo/relatedRepos set to ${fullName}`
  return ''
}
const readmeNotes = []
const workflowControls = DEP_REPOS.flatMap((r, i) => {
  const p = depProbes[i]
  if (p === null) return []
  const probe = probesOf(p, 'code-search').find(x => x.role === 'readme')
  const repoGap = repoCheckGap(r, probesOf(p, 'repo-check').find(x => x.repo === r))
  if (repoGap) mandatoryGaps.push(repoGap)
  if (!probe) {
    if (!repoGap) mandatoryGaps.push(`code search: README control "${README_CONTROL(r)}" was not run`)
    return []
  }
  const c = { ...codeRow(probe, 'workflow'), role: 'must-hit' }
  if (repoGap) return [c]
  if (!answered(c)) mandatoryGaps.push(`code search: README control "${c.query}" ${outcome(c)}${healthFailed ? ' — gh auth, rate-limit or search is broken' : ''}`)
  // Only a search shown to answer (health >0) can say anything about one repo's 0.
  // Health never ran (its agent returned nothing): the 0 is uninterpretable, and is said to be.
  else if (c.count === 0 && healthRow === null) readmeNotes.push(`"${c.query}" returned 0, but whether code search answers at all is unknown (no passing health control), so that 0 cannot be read either way`)
  else if (c.count === 0 && healthOk) readmeNotes.push(`"${c.query}" returned 0 although ${r} exists — either code search does not index it (e.g. a low-star fork) or it has no README.md (e.g. README.rst); not a gap`)
  return [c]
})
const planProbe = plan === null ? null : readProbe(plan.codeSearchProbe, PLAN_PROBE)
// Qualifier set = the query's SHAPE (#1471): `repo:a/b language:rust foo` -> "language:rust repo:a/b".
// Boolean operators and parentheses are part of the shape too: `foo OR bar language:toml` (the #1471
// example) is only armed by a must-hit that also uses OR.
const shapeOf = q => q.split(/\s+/).flatMap(t => (/^-?[A-Za-z_]+:\S/.test(t) ? [t.toLowerCase()]
  : /^(OR|AND|NOT)$/.test(t) ? [t] : /[()]/.test(t) ? ['()'] : [])).sort().join(' ')
const plannerRaw = probesOf(planProbe, 'code-search').map(x => {
  const row = codeRow(x, 'planner')
  // round-4 L1: an unknown planner role is INERT — recorded, never promoted to `query`.
  return PLAN_ROLES.includes(row.role) ? row : { ...row, role: 'inert', declaredRole: row.role }
})
const armingHits = plannerRaw.filter(c => c.role === 'must-hit' && answered(c) && c.count > 0)
const plannerRows = plannerRaw.map(c => (c.role !== 'query' ? c
  : { ...c, armed: answered(c) && (c.count > 0 || armingHits.some(m => shapeOf(m.query) === shapeOf(c.query))) }))
const codeSearch = plannerRows.concat(healthRow ? [healthRow] : [], workflowControls)
// An unarmed 0 is a GAP the report must name, never "no results" (#1471).
const codeSearchGaps = plannerRows.filter(c => c.role === 'query' && answered(c) && c.count === 0 && !c.armed)
  .map(c => `planner query "${c.query}" returned 0 with no same-shape must-hit (qualifiers: ${shapeOf(c.query) || 'none'}) — an unarmed negative: a gap, not evidence of absence`)
// A planner control that missed is a guess that failed, recorded for the reader, never a gap.
const codeSearchNotes = plannerRows.filter(c => c.role === 'must-hit' && !(answered(c) && c.count > 0))
  .map(c => `planner must-hit control "${c.query}" ${outcome(c)} — a guessed control, not a gap; any other must-hit >0 carries the requirement`)
  .concat(plannerRows.filter(c => c.role === 'inert').map(c => `planner row "${c.query}" declared role "${c.declaredRole}", which is workflow-only — recorded as inert, counted for nothing`))
  .concat(readmeNotes, dependencyNotes)
if (plan === null) mandatoryGaps.push('code search: planner agent reported nothing (null)')
else if (planProbe === null) mandatoryGaps.push(`code search: no PROBE-JSON line for ${PLAN_PROBE} — the planner's code-search probe did not run or its line was not copied`)
else {
  const ok = (rows, role, hit) => rows.some(c => c.role === role && answered(c) && hit(c))
  if (!ok(plannerRows, 'query', c => c.armed)) mandatoryGaps.push('code search: no planner query ran with rc=0 and produced evidence (a hit, or a 0 armed by a same-shape must-hit)')
  if (!ok(codeSearch, 'must-hit', c => c.count > 0)) mandatoryGaps.push('code search: no must-hit control returned a hit, so the search is not shown to discriminate')
  if (!ok(plannerRows, 'known-absent', c => c.count === 0)) mandatoryGaps.push('code search: no fresh known-absent control returned 0')
}

// Planner and dependency manifests are counted SEPARATELY: dependency manifests must never mask a
// planner fan-out that produced nothing (it alone carries exa/context7/firecrawl).
// Only THIS run's manifests are evidence: a stale one (an agent skipped its run) is a gap, never a hit source.
const depManifests = dependencyRuns.filter(x => x.query !== null && x.fresh).map(x => x.manifest)
const planManifests = plan === null ? [] : plan.runs.filter(r => r.manifest).map(r => r.manifest)
// A planner run that failed or wrote no manifest is a named Gap, even when its siblings succeeded.
const fanoutGaps = plan === null ? [] : plan.runs.filter(r => r.rc !== 0 || !r.manifest)
  .map(r => `planner fan-out "${r.query}" rc=${r.rc}${r.manifest ? '' : ', no manifest'}`)
if (plan === null && !LINKS.length && !depManifests.length) return await finish(withStatuses('plan-null', { mandatoryGaps, routing }))
const manifests = planManifests.concat(depManifests)
if (!manifests.length && !LINKS.length) return await finish(withStatuses('no-manifests', { plan, mandatoryGaps, fanoutGaps, routing }))
// Each failed stage carries its OWN evidence consequence, so synthesis is never handed one fixed
// sentence that is false for a different stage (round-3 review R5).
const stageGaps = []
const stageConsequences = []
const failStage = (gap, consequence) => { stageGaps.push(gap); stageConsequences.push({ stage: gap, consequence }) }
if (plan === null) failStage('planner agent reported nothing (null) — no planner fan-out manifest reached triage', 'no planner fan-out (exa/context7/firecrawl/github) result is in the evidence')
else if (!planManifests.length) failStage(`planner fan-out produced no manifests (${plan.runs.length ? plan.runs.map(r => `${r.query} rc=${r.rc}`).join(', ') : 'no runs'}) — exa/context7/firecrawl/github evidence from the planner is missing`, 'no planner fan-out (exa/context7/firecrawl/github) result is in the evidence')
if (stageGaps.length) log('Plan: no planner fanout results — continuing on the caller links and mandatory stages (a named gap)')
else log(`Plan: ${plan.runs.length} fanout run(s); ${codeSearch.length} code search(es); sourceDive=${plan.sourceDive}`)

phase('Triage')
const EMPTY_TRIAGE = { read: [], hits: [], unverifiedEmpty: [] }
// The mirror README is written by a probe from the <n>.probe.json files on disk while triage runs,
// so its rows are what the mirror probes recorded, not what an agent retyped.
const INDEX_OUT = `${MIRROR_DIR}/README.probe.json`
const indexPrompt = [
  `Write the offline-mirror index for ${A.reportPath}. Run exactly, never piped (the probe renders the README from the`,
  'mirror probes on disk; do not fetch or write anything yourself):',
  '  ' + probeCmd(INDEX_OUT, [`--mirror-index ${shq(MIRROR_DIR)}`, `--mirror-count ${LINKS.length}`]),
  COPY_LINE,
].join('\n')
const PLAN_MANIFEST_PROBE = `${FANOUT_DIR}/plan/manifests.json`
const planManifestPrompt = [
  'Read the planner manifests to record their provisional credit-exhaustion routes. Run exactly, never piped:',
  '  ' + probeCmd(PLAN_MANIFEST_PROBE, planManifests.map(m => `--fanout-manifest ${shq(m)}`)),
  COPY_LINE,
].join('\n')
const [triageOut, mirrorIndex, planManifestGot] = await Promise.all([!manifests.length ? EMPTY_TRIAGE : run('triage', 'triage', 'Triage', [
  `QUESTION: ${A.question}`,
  `Read these research-fanout manifests and every <source>.json beside them:\n${manifests.join('\n')}`,
  codeSearch.length ? `Code-search rows (recorded by research-fanout probes): ${JSON.stringify(codeSearch)}` : '',
  'Dedup hits across sources by URL (record which sources found each). Rank by likely value for the QUESTION:',
  'primary sources (source code, merged PRs, maintainer answers, release notes) above secondary ones (blogs, forums).',
  `Choose at most ${READ_MAX} URLs worth deep-reading, each with a one-line reason. Prefer a mix: at least one primary`,
  'source per project the QUESTION names. List every source whose status is empty_unverified or error in',
  'unverifiedEmpty — those are gaps, not "no results".',
  LINKS.length ? `Do NOT choose these (the caller's links, read separately): ${LINKS.join(' ')}` : '',
].filter(Boolean).join('\n'), { schema: TRIAGE }),
LINKS.length ? run('mirrorIndex', 'mirror-index', 'Mirror', indexPrompt, { schema: PROBE }) : null,
planManifests.length ? run('planManifests', 'plan-manifests', 'Triage', planManifestPrompt, { schema: PROBE }) : null,
])
const planManifestProbe = readProbe(planManifestGot, PLAN_MANIFEST_PROBE)
if (planManifests.length && planManifestProbe === null) {
  fanoutGaps.push('planner provisional check did not run')
  mandatoryGaps.push('planner provisional check did not run')
}
const manifestProvisional = p => probesOf(p, 'fanout-manifest').flatMap(m => {
  if (!Array.isArray(m.provisional) || m.provisional.length > MAX_PROBE_ENTRIES || m.provisional_invalid === true ||
      !m.provisional.every(e => e && typeof e.source === 'string' && Object.hasOwn(PROVISIONAL_ROUTES, e.source) &&
        (e.route === null || PROVISIONAL_ROUTES[e.source].includes(e.route)))) {
    mandatoryGaps.push(`${m.path}: provisional projection failed validation`)
    return []
  }
  return m.provisional.map(e => `${m.path}: ${e.source}${e.route ? ` via ${e.route}` : ' skipped'} (credits-exhausted)`)
})
const provisionalRoutes = [...new Set([
  ...mirror.filter(m => m.provisional && mirrored(m)).map(m => `${m.url}: mirrored via webclaw (credits-exhausted)`),
  ...manifestProvisional(planManifestProbe),
  ...depProbes.flatMap(manifestProvisional),
])]
const indexRow = probesOf(readProbe(mirrorIndex, INDEX_OUT), 'mirror-index')[0]
if (LINKS.length && !(indexRow && indexRow.written === true)) mandatoryGaps.push(`mirror stage: README index ${MIRROR_DIR}/README.md was not written`)
log(`Mandatory: ${dependencyRuns.length} dependency run(s) over ${DEP_REPOS.length} repo(s); ${mirror.filter(mirrored).length}/${mirror.length} link(s) mirrored; ${mandatoryGaps.length} mandatory gap(s)`)
if (triageOut === null && !LINKS.length) return await finish(withStatuses('triage-null', { plan, mandatoryGaps, fanoutGaps, stageGaps, routing }))
if (triageOut === null) {
  failStage('triage returned null — no fan-out hit was read', 'no hit from any fan-out manifest (planner or dependency-repo) was triaged or read')
  log('Triage: null — continuing on the caller links alone (a named gap)')
}
const triage = triageOut || EMPTY_TRIAGE
const linkSet = new Set(LINKS)
const triaged = triage.read.filter(u => !linkSet.has(norm(u.url)))
const toRead = triaged.slice(0, READ_MAX)
if (triaged.length > READ_MAX) log(`Triage: dropped ${triaged.length - READ_MAX} URL(s) over readMax: ${triaged.slice(READ_MAX).map(u => u.url).join(' ')}`)

phase('Read')
const READ_RULES = [
  'Read each page IN FULL, not its first screen: list its section headings, and quote every section that names an',
  'entity in the QUESTION. Extract claims that bear on the QUESTION, each with a VERBATIM quote and the URL. Record a',
  'claim of ABSENCE ("X does not do Y") only with the exact search you ran and a control term that did match.',
  'GitHub issue/PR/discussion: `gh api` (issue + comments, PR body + review comments; discussions via `gh api graphql`).',
  'Other pages: run the `fetch:` command given beside the URL EXACTLY (the URL in it is already one single-quoted',
  'shell word — never retype, re-quote or interpolate a URL into a command yourself; round-4 L6), or read the offline',
  'copy under docs/research/kb/raw/ when one exists — say which. Never print environment values.',
]
const withFetch = (u, note) => `- ${u}  (${note})\n    fetch: ${FETCH(u)}`
// Each reader keeps its identity: a reader that returns null is a GAP the report must
// name, never a silent drop (a null filtered away reads as "nothing to say").
const readers = []
for (let i = 0; i < LINKS.length; i += READ_BATCH) {
  const batch = LINKS.slice(i, i + READ_BATCH)
  const n = Math.floor(i / READ_BATCH) + 1
  readers.push({ kind: 'links', urls: batch, run: () => run('readLinks', `read-link:${n}`, 'Read', [
    `QUESTION: ${A.question}`, 'The caller named these links; every one must be read.',
    'Read each from its OFFLINE MIRROR (the firecrawl markdown the mandatory mirror stage saved), not the live page.',
    'Only a link marked NO MIRROR is read live — and say in each of its claims that the mirror failed.', ...READ_RULES,
    ...batch.map(u => {
      const m = mirror[LINKS.indexOf(u)]
      return mirrored(m) ? `- ${u}  (mirror: ${m.path}, ${m.bytes} bytes)` : withFetch(u, `NO MIRROR: ${codeText(m)}`)
    }),
  ].join('\n'), { schema: CLAIMS }) })
}
const batches = []
for (let i = 0; i < toRead.length; i += READ_BATCH) batches.push(toRead.slice(i, i + READ_BATCH))
batches.forEach((batch, i) => readers.push({ kind: 'triaged', urls: batch.map(u => u.url), run: () => run('read', `read:${i + 1}/${batches.length}`, 'Read', [
  `QUESTION: ${A.question}`, ...READ_RULES,
  ...batch.map(u => withFetch(u.url, u.why)),
].join('\n'), { schema: CLAIMS }) }))
if (plan && plan.sourceDive && REPO) {
  // general-purpose, not Explore: the dive clones into $TMPDIR and deletes it, and the
  // built-in Explore agent may not create or delete files. It pays the CLAUDE.md payload
  // only on the runs that need a clone.
  readers.push({ kind: 'dive', urls: [`${REPO} (source at the latest release tag)`], run: () => run('sourceDive', 'source-dive', 'Read', [
    `QUESTION: ${A.question}`,
    `Shallow-clone ${REPO} at its LATEST RELEASE TAG (\`gh api repos/${REPO}/releases/latest --jq .tag_name\`) into $TMPDIR,`,
    'grep for the mechanism the QUESTION is about, and extract claims about what the code does, each with file:line and a',
    'verbatim quote. Also say whether the default branch has changed that code since the tag (a merged-but-unreleased fix),',
    'and for an absence claim run `git log -S` over history so added-then-removed code is not missed. Every grep that',
    'returns nothing needs a control term that does match. Delete the clone when done.',
  ].join('\n'), { schema: CLAIMS }) })
}
const readResults = await parallel(readers.map(r => r.run))
const claims = readResults.flatMap(r => (r && Array.isArray(r.claims) ? r.claims : []))
const failedReads = readers.flatMap((r, i) => (readResults[i] === null ? r.urls : []))
log(`Read: ${claims.length} claim(s) from ${readers.length} reader(s) (${LINKS.length} caller link(s)); ${failedReads.length} unread`)

phase('Synthesize')
// What the report's evidence actually rests on, derived from what was READ — never from what was
// dispatched (round-4 L3): a null reader contributed nothing, and a code search with no answered row
// is not evidence.
const readUrls = kind => readers.reduce((n, r, i) => n + (r.kind === kind && readResults[i] !== null ? r.urls.length : 0), 0)
const evidenceBase = () => [
  readUrls('links') ? `the ${readUrls('links')} caller link(s) read` : '',
  triageOut !== null && planManifests.length ? 'hits triaged from the planner fan-out manifests' : '',
  triageOut !== null && depManifests.length ? 'hits triaged from the dependency-repo manifests' : '',
  readUrls('triaged') ? `${readUrls('triaged')} deep-read triaged URL(s)` : '',
  readUrls('dive') ? `the ${REPO} source dive` : '',
  codeSearch.some(answered) ? 'the answered code-search rows' : '',
].filter(Boolean).join(' + ') || 'nothing that was read'
const synth = await run('synthesize', 'synthesize', 'Synthesize', [
  `QUESTION: ${A.question}`,
  `Write the research report to ${A.reportPath}. Inputs: the claims JSON below, the triage hit list, the code-search`,
  `results, and the manifests (${manifests.join(', ')}). Resolve conflicts explicitly (source code and merged PRs beat`,
  'issue threads; newer beats older; say which you trusted and why). Name every gap from unverifiedEmpty as a gap,',
  'never as "nothing found". Every FAILED READ below is a gap too: the reader for it failed, so its content is unknown.',
  'Keep distinct claims distinct: what a project SHIPS in code, what its docs/discussions PROPOSE or recommend, and what',
  'a THIRD party documents about it are three different claims — never collapse them into one headline.',
  // ONE line for the whole section list, so nothing inserted later can detach its tail (#1513).
  'Sections, in this order: Answer, Evidence, Conflicts resolved, Gaps, Recommendation, Provenance (the ROUTING table below, as a table), ## GitHub repos touched (per .claude/rules/research-repo-enumeration.md).',
  'Evidence is a table (claim | URL or file:line | quote) and MUST also carry three tables, a row for EVERY input row',
  'even when its count is 0: "Code search" (query | role | source | count | rc — write RATE-LIMITED, never 0, for a',
  'rateLimited row, and UNARMED beside an unarmed 0) from CODE SEARCH, with each CODE SEARCH NOTE under it as a note',
  '(not a gap); "Dependency-repo fan-out" (repo | query | required sources failed | manifest) from DEPENDENCY RUNS;',
  '"Offline mirrors" (link | mirror file | rc | bytes | failure | route | provisional) from MIRRORS. These rows were recorded by',
  'research-fanout probes; cite the manifest paths. Every MIRROR GAP, CODE SEARCH GAP and MANDATORY GAP is a Gap; when',
  'MANDATORY GAPS is non-empty, the Answer must say the sweep is INCOMPLETE and name what did not run.',
  'Name every PROVISIONAL ROUTE below in the Answer and provenance; credit-skipped or substituted research is provisional.',
  `Return the path and the claims the Answer depends on (at most ${VERIFY_MAX}); mark absence=true on every claim`,
  'that something does NOT exist or does NOT happen — those are the easiest to get wrong.',
  LINKS.length ? `CALLER LINKS (each must be cited or named as unread): ${LINKS.join(' ')}` : '',
  `CLAIMS:\n${JSON.stringify(claims)}`,
  `TRIAGE:\n${JSON.stringify({ hits: triage.hits, unverifiedEmpty: triage.unverifiedEmpty })}`,
  `CODE SEARCH:\n${JSON.stringify(codeSearch)}`,
  codeSearchNotes.length ? `CODE SEARCH NOTES:\n${JSON.stringify(codeSearchNotes)}` : '',
  codeSearchGaps.length ? `CODE SEARCH GAPS:\n${JSON.stringify(codeSearchGaps)}` : '',
  `DEPENDENCY RUNS:\n${JSON.stringify(dependencyRuns)}`,
  `MIRRORS:\n${JSON.stringify(mirror)}`,
  mirrorGaps.length ? `MIRROR GAPS:\n${JSON.stringify(mirrorGaps)}` : '',
  provisionalRoutes.length ? `PROVISIONAL ROUTES:\n${JSON.stringify(provisionalRoutes)}` : '',
  mandatoryGaps.length ? `MANDATORY GAPS:\n${JSON.stringify(mandatoryGaps)}` : '',
  fanoutGaps.length ? `FANOUT GAPS (each is a Gap: a planner fan-out run that failed or wrote no manifest):\n${JSON.stringify(fanoutGaps)}` : '',
  `FAILED READS:\n${JSON.stringify(failedReads)}`,
  stageGaps.length ? `FAILED STAGES (each is a Gap; state its consequence, and say the evidence base is: ${evidenceBase()}): ${JSON.stringify(stageConsequences)}` : '',
  // This node's own row is added by run() only when it is called, i.e. after this prompt is built.
  `ROUTING (so far; add a row for this synthesize node — ${JSON.stringify(ROUTE.synthesize)}):\n${JSON.stringify(routing)}`,
].filter(Boolean).join('\n'), { schema: SYNTH })
const common = { stageGaps, mandatoryGaps, fanoutGaps, plan, triage, failedReads, codeSearch, codeSearchNotes, codeSearchGaps, dependencyRuns, mirror, mirrorGaps, provisionalRoutes }
if (synth === null) return await finish(withStatuses('synth-null', { ...common, claims, routing }))

phase('Verify')
const loadBearing = synth.loadBearing.slice(0, VERIFY_MAX)
if (synth.loadBearing.length > VERIFY_MAX) log(`Verify: ${synth.loadBearing.length - VERIFY_MAX} load-bearing claim(s) over verifyMax left UNVERIFIED`)
const refuteOne = (c, i) => () => run('refute', `refute:${i + 1}/${loadBearing.length}`, 'Verify', [
  'Try to REFUTE this claim by re-probing its PRIMARY source yourself (open the URL / read the file at the cited ref).',
  'Default to refuted=true if you cannot confirm it. Every negative needs a control arm',
  '(.claude/rules/probes-need-a-control-arm.md); record it in controlArm.',
  'Then judge MISLEADING-BY-OMISSION separately: even if the claim is true, would a reader draw a wrong conclusion',
  'because it omits something the sources say — e.g. it is true of shipped CODE but omits a documented or proposed',
  'workflow, or true of one project but omits what a related project documents about it? Set misleading=true and name',
  'the omission in omitted. Check the OTHER side of every relationship the claim touches (the related project\'s docs,',
  'issues and discussions), not only the source the claim cites.',
  c.absence ? 'This is an ABSENCE claim: confirm it by a SECOND route of a DIFFERENT KIND from the cited one (if it cites code, search the docs/trackers that could describe the thing; if it cites docs, search the code and its history with `git log -S`), each with its own control term.' : '',
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
const flagged = verdicts.filter(v => v.refuted === true || v.misleading === true)

// One tier up before a refutation is allowed to rewrite the report.
let refuted = flagged
let adjudication = null
if (flagged.length) {
  adjudication = await run('adjudicate', 'adjudicate', 'Verify', [
    'Independent refuters flagged the claims below as REFUTED and/or MISLEADING. Re-check each against its primary',
    'source yourself and decide: upheld (the claim really is wrong or misleading) or overturned (the refuter erred).',
    'Weigh the claim\'s own evidence against the refuter\'s; an absence verdict needs a control arm. Return EXACTLY one',
    'verdict per flagged claim, IN THE SAME ORDER, with index = its 0-based position: refuted=true upholds a',
    'falsity flag, misleading=true upholds a misleading-by-omission flag; both false = overturned.',
    `REPORT: ${synth.reportPath}`,
    `FLAGGED: ${JSON.stringify(flagged.map((v, index) => ({ index, ...v })))}`,
  ].join('\n'), { schema: { type: 'object', required: ['verdicts'], properties: { verdicts: { type: 'array', items: { ...VERDICT, required: [...VERDICT.required, 'index'], properties: { ...VERDICT.properties, index: { type: 'number' } } } } } } })
  if (adjudication === null) {
    // Fail safe: an unconfirmed flag still rewrites the report (the pre-2026-09-29b behaviour).
    log('Verify: adjudicator returned null — every flagged claim is treated as UPHELD')
  } else {
    const byIndex = new Map(adjudication.verdicts.map(v => [v.index, v]))
    // Matched back by index onto the ORIGINAL claim text; a claim the adjudicator skipped stays UPHELD.
    refuted = flagged
      .map((v, i) => ({ v, a: byIndex.get(i) }))
      .filter(({ a }) => !a || a.refuted || a.misleading)
      .map(({ v, a }) => ({ ...v, adjudicated: a ? a.evidence : 'not adjudicated — upheld by default' }))
  }
}
const gaps = critic === null ? null : critic.gaps
const overCap = synth.loadBearing.slice(VERIFY_MAX).map(c => ({ claim: c.claim, refuted: null, evidence: `over verifyMax=${VERIFY_MAX} — UNVERIFIED` }))
log(`Verify: ${flagged.length} flagged, ${refuted.length} upheld, ${unverified.length} unverified of ${verdicts.length} load-bearing claim(s)`)

// The report on disk must carry the verification outcome: a refuted claim left in the
// Answer is worse than no report. Reconcile ALWAYS runs (one sonnet call): an all-confirmed
// run still needs its Verification section and the Verify rows of the Provenance table.
let reconciled = true
{
  const reconcile = await run('reconcile', 'reconcile', 'Verify', [
    `Edit the research report at ${synth.reportPath} in place. Add a "## Verification" section listing each`,
    'load-bearing claim as confirmed, UPHELD as refuted or misleading (with the evidence), overturned by the',
    'adjudicator, or unverified. Correct or strike every UPHELD refuted claim wherever the Answer or Recommendation',
    'relies on it; QUALIFY every UPHELD misleading claim with its omission; say how the conclusion changes. Append the',
    'critic gaps to the Gaps section. If the critic or adjudicator result is null, say that step did not run. Replace',
    'the Provenance table with the full ROUTING below (every node that ran, incl. this reconcile node).',
    `VERDICTS: ${JSON.stringify(verdicts.concat(overCap))}`,
    `UPHELD: ${JSON.stringify(refuted)}`,
    `ADJUDICATION: ${JSON.stringify(adjudication)}`,
    `CRITIC GAPS: ${JSON.stringify(gaps)}`,
    `FAILED STAGES: ${JSON.stringify(stageGaps)}`,
    `MANDATORY GAPS (keep each in Gaps; if any, the Answer must say the sweep is INCOMPLETE): ${JSON.stringify(mandatoryGaps)}`,
    `ROUTING: ${JSON.stringify(routing.concat([{ node: 'reconcile', agentType: 'general-purpose', ...ROUTE.reconcile }]))}`,
  ].join('\n'))
  reconciled = reconcile !== null
  if (!reconciled) log('Verify: reconcile returned null — the report on disk does NOT reflect verification')
}

let advice = null
if (A.advisor) {
  phase('Advise')
  advice = await run('advisor', 'codex-sol-advisor', 'Advise', `Second opinion on the recommendation in ${synth.reportPath} (question: ${A.question}). Claims upheld as refuted or misleading: ${JSON.stringify(refuted)}. Return a verdict and the deciding risk.`)
  if (advice === null) log('Advise: codex-sol-advisor returned null (escalation per .claude/token-routing.md item 1)')
}

// Status (#1513): `statuses` lists EVERY degraded state that applies, highest precedence first, and
// `status` is its head (or `complete`). verify-null = EVERY refuter returned null; reconcile-null = the
// report on disk does not reflect verification; mandatory-gap = a mandatory stage (dependency repos,
// mirror, code search) did not run or did not succeed — `mandatoryGaps` names each; partial-verify =
// SOME refuters returned null; links-only / stage-gap = plan, fan-out or triage failed, so the evidence
// base is the caller links (links-only) or what the mandatory stages produced (stage-gap, no links —
// never `links-only` with zero links); provisional = a validated credit fallback or credit-skipped
// manifest source. Early exits: plan-null | no-manifests | triage-null | synth-null.
const statuses = [
  verdicts.length && unverified.length === verdicts.length ? 'verify-null' : '',
  !reconciled ? 'reconcile-null' : '',
  mandatoryGaps.length ? 'mandatory-gap' : '',
  unverified.length && unverified.length < verdicts.length ? 'partial-verify' : '',
  stageGaps.length ? (LINKS.length ? 'links-only' : 'stage-gap') : '',
  provisionalRoutes.length ? 'provisional' : '',
].filter(Boolean)
const status = statuses[0] || 'complete'
return await finish({ status, statuses, ...common, reportPath: synth.reportPath, claims: claims.length, verdicts, adjudication, refuted, gaps, advice, routing })
