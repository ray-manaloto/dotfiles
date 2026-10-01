export const meta = {
  name: 'research-sweep-run',
  description: 'Fan a research question out to many sources via `mise run research-fanout`, deep-read the best hits cheaply, synthesize once on Opus, and refute the load-bearing claims one by one.',
  whenToUse: 'When a question needs evidence from several sources (GitHub issues/PRs/discussions/releases/code, exa, context7, firecrawl, last30days) and one context should not spend frontier tokens on fetching and reading.',
  phases: [
    { title: 'Plan', detail: 'pick sources and queries, run research-fanout plus the MANDATORY GitHub code search with its two controls (sonnet, medium)' },
    { title: 'Dependencies', detail: 'MANDATORY: github issues/discussions/releases for repo + every related repo, both directions (one sonnet/low agent per repo)' },
    { title: 'Mirror', detail: 'MANDATORY: every caller link saved offline via `mise exec -- firecrawl scrape` + a README index (one haiku agent per link)' },
    { title: 'Triage', detail: 'rank and dedup the hits, choose what to deep-read; caller links always read (Explore + sonnet, low)' },
    { title: 'Read', detail: 'caller links from their offline mirror (sonnet) + triaged URLs (haiku) in batches; optional source dive at the release tag' },
    { title: 'Synthesize', detail: 'one Opus pass writes the report (opus, high)' },
    { title: 'Verify', detail: 'one independent refuter per load-bearing claim (sonnet), a completeness critic, an Opus adjudicator for any refuted or misleading flag, then reconcile' },
    { title: 'Advise', detail: 'optional codex-sol-advisor second opinion (codex tokens, not Claude)' },
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
//    `.claude/token-routing.md`'s. A typical run is ~9-15 agents (was ~7-10 before 2026-09-29b).
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
// 13. MIRROR: every caller link saved by `mise exec -- firecrawl scrape` (never a stale PATH copy)
//    into docs/research/kb/raw/<report-slug>/links/, one haiku agent per link (pure command
//    execution; general-purpose because Explore may not create files) + one haiku README index.
//    A link that will not fetch is a NAMED gap; a mirror agent that never ran is a mandatory gap.
// 14. CODE SEARCH: the planner must run >=1 query of its own + a must-hit control + a fresh
//    known-absent control; the workflow checks the rows, so skipping it cannot read as `complete`.
//    A planner must-hit is a guess (live run wf_b74e66f5-ca3: `filename:skills.rs repo:jdx/mise`
//    returned 0 and failed the sweep), so the workflow builds its own controls for two SEPARATE
//    questions. "Is GitHub code search working?" — the first dependency agent runs
//    SEARCH_HEALTH_CONTROL, and a 0 or a failure there is a gap blamed on gh/auth/rate limit.
//    "Is this repo searchable?" — every dependency agent runs `gh api -i repos/<r>` (does it exist
//    UNDER THIS NAME? a rename redirects, and a renamed repo's old name searches as 0) and
//    `repo:<r> filename:README.md` (is a README.md of it indexed?). A README of 0 for a repo that
//    exists under its own name is a NOTE, not a gap, and only when health passed: code search does
//    not index some repos (measured 2026-09-30: the 0-star fork virajp/mise returns 0 although its
//    README.md is 8569 bytes) and some have no README.md (sphinx-doc/sphinx: README.rst). The health
//    row has its own role, so only a planner or README must-hit >0 satisfies the must-hit
//    requirement; a planner must-hit of 0 is a NOTE. A 403 is recorded as rateLimited, never as 0.
// A mandatory stage that did not run or did not succeed adds to `mandatoryGaps`; status is
// `mandatory-gap` unless a higher-precedence degraded status applies.

const A = args || {}
if (typeof A.question !== 'string' || !A.question.trim()) throw new Error('args.question is required')
if (typeof A.reportPath !== 'string' || !A.reportPath.startsWith('/')) throw new Error('args.reportPath must be an absolute path')
// Every repo name reaches shell commands (`--repo`, `gh api repos/…`, `-f q='repo:…'`, `--out`), so its
// SHAPE is the guard: owner/repo characters only, never a quote, space, `;` or `$`.
const REPO_SHAPE = /^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/
const REPO = typeof A.repo === 'string' ? A.repo : ''
if (REPO && !REPO_SHAPE.test(REPO)) throw new Error(`args.repo must be owner/repo ([A-Za-z0-9_.-]), got ${JSON.stringify(REPO)}`)
// Other projects the question is ABOUT, beside REPO: searched in both directions
// (REPO's tracker for each name, each repo's tracker for REPO's name).
const RELATED = Array.isArray(A.relatedRepos) ? A.relatedRepos.filter(r => typeof r === 'string' && r) : []
RELATED.forEach(r => { if (!REPO_SHAPE.test(r)) throw new Error(`args.relatedRepos entries must be owner/repo ([A-Za-z0-9_.-]), got ${JSON.stringify(r)}`) })
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
// The mandatory dependency-repo stage (12): every repo the question is about, searched on GitHub.
const DEP_SOURCES = 'github-issues,github-discussions,github-releases'
const DEP_REPOS = [...new Set([REPO, ...RELATED].filter(Boolean))]
// null = "short search terms from the QUESTION"; a name = the other side of a relationship.
const depQueries = r => (r === REPO ? [null, ...RELATED.filter(o => o !== REPO).map(nameOf)] : [REPO ? nameOf(REPO) : null])
// The mandatory mirror stage (13) writes under the report's repository.
const REPORT_SLUG = A.reportPath.split('/').pop().replace(/\.md$/, '')
// The slug is unquoted in the dependency `--out` paths, so it is shape-checked like a repo name.
if (!/^[A-Za-z0-9_.-]+$/.test(REPORT_SLUG)) throw new Error(`args.reportPath file name must be [A-Za-z0-9_.-]+.md, got ${JSON.stringify(REPORT_SLUG)}`)
const docsAt = A.reportPath.lastIndexOf('/docs/')
const ROOT = typeof A.repoRoot === 'string' && A.repoRoot.startsWith('/') ? A.repoRoot.replace(/\/+$/, '')
  : docsAt > 0 ? A.reportPath.slice(0, docsAt) : ''
if (LINKS.length && !ROOT) throw new Error('args.repoRoot (absolute) is required when links are given and reportPath is not under <repo>/docs/')
const MIRROR_DIR = `${ROOT}/docs/research/kb/raw/${REPORT_SLUG}/links`
// `health` is the workflow's search-health row: its own role, so it can never satisfy the must-hit.
const CODE_ROLES = ['query', 'must-hit', 'known-absent', 'health']
// Two questions, two controls (14). SEARCH_HEALTH_CONTROL asks "does code search answer at all?" (a
// repo known to be indexed; 9 hits measured 2026-09-30). README_CONTROL asks "is a README.md of THIS
// repo indexed?": a 0 there is not proof the search is broken — an unindexed repo (a low-star fork), a
// repo with no README.md (README.rst) and a renamed repo's old name all return 0 — so the repos API
// settles existence and name, and only health decides "broken".
const SEARCH_HEALTH_CONTROL = 'repo:cli/cli filename:README.md'
const README_CONTROL = r => `repo:${r} filename:README.md`
// Single-quote a value for the shell: a caller URL may carry `'` (legal, common in Wikipedia URLs).
// Every shell command below interpolates only a constant, a shape-checked value (REPO_SHAPE,
// REPORT_SLUG, an integer) or a shq()-quoted one.
const shq = v => `'${v.replace(/'/g, "'\\''")}'`

// One routing table, used for dispatch AND returned as provenance, so the two cannot drift.
const ROUTE = {
  plan: { model: 'sonnet', effort: 'medium' },
  deps: { model: 'sonnet', effort: 'low' },
  mirror: { model: 'haiku' },
  mirrorIndex: { model: 'haiku' },
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
  required: ['runs', 'codeSearch', 'sourceDive'],
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
        required: ['query', 'role', 'count', 'rc'],
        properties: {
          query: { type: 'string' }, role: { type: 'string', enum: CODE_ROLES },
          count: { type: 'number' }, rc: { type: 'number' }, rateLimited: { type: 'boolean' },
          topUrls: { type: 'array', items: { type: 'string' } },
        },
      },
    },
    sourceDive: { type: 'boolean' },
    rationale: { type: 'string' },
  },
}
const CODE_CONTROL = {
  type: 'object',
  required: ['count', 'rc', 'rateLimited'],
  properties: { count: { type: 'number' }, rc: { type: 'number' }, rateLimited: { type: 'boolean' } },
}
const DEPS = {
  type: 'object',
  required: ['runs', 'control', 'exists'],
  properties: {
    control: CODE_CONTROL,
    exists: { type: 'object', required: ['rc', 'status', 'fullName'], properties: { rc: { type: 'number' }, status: { type: 'number' }, fullName: { type: 'string' } } },
    health: CODE_CONTROL,
    runs: {
      type: 'array',
      items: { type: 'object', required: ['query', 'manifest', 'rc'], properties: { query: { type: 'string' }, manifest: { type: 'string' }, rc: { type: 'number' } } },
    },
  },
}
const MIRROR = {
  type: 'object',
  required: ['rc', 'bytes'],
  properties: { rc: { type: 'number' }, bytes: { type: 'number' }, reason: { type: 'string' } },
}
const MIRROR_INDEX = { type: 'object', required: ['written'], properties: { written: { type: 'boolean' } } }
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

phase('Plan')
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
  'GITHUB CODE SEARCH — MANDATORY on every run: `gh api -X GET search/code -f q=\'<q>\' --jq .total_count`.',
  'REST syntax: no OR, no parentheses, no `**`; use `filename:`/`path:`/`repo:`/`org:` and run one query per',
  'alternative, then union. The bucket is 10 requests/min and a 403 is RATE LIMIT, not zero results: record such a',
  'row with rateLimited=true and count=-1, never count=0. The tokenizer',
  'drops punctuation, so re-fetch and grep each hit before counting it. Record EVERY query in codeSearch with its',
  'count and real rc — a zero-count query is still recorded — and a role:',
  '  role "query": at least one query of your own for the QUESTION;',
  '  role "must-hit": one control query you know matches (e.g. a file you know exists in REPO) — it should return >0',
  `  (the workflow also runs \`repo:<r> filename:README.md\` per dependency repo${DEP_REPOS.length ? `: ${DEP_REPOS.join(', ')}` : ''});`,
  '  role "known-absent": one control built from a nonsense token you invent FRESH now (never one copied from a report',
  '  or rule — writing a control down destroys it) — it must return 0.',
  'Set sourceDive=true only when REPO is set AND the question is about what the code DOES (behaviour, a flag, a bug),',
  'where reading source at the release tag beats issues.',
].filter(Boolean).join('\n')
const depPrompt = (r, i) => [
  `MANDATORY DEPENDENCY-REPO STAGE for ${r}: it runs whatever any planner chose. QUESTION: ${A.question}`,
  'From the repository root, run each command below exactly (queries are project NAMES or short search terms,',
  'never owner/repo slugs), never piped, and record the manifest path it prints first and its real exit code:',
  ...depQueries(r).map((q, k) => `  mise run research-fanout -- "${q === null ? '<2-4 short search terms from the QUESTION>' : q}" --repo ${r} --sources ${DEP_SOURCES} --out .agent/kb/raw/research-fanout/${REPORT_SLUG}/deps/${r.replace('/', '--')}/${k + 1}`),
  'Return exactly one run per command, in order, with the query you actually used.',
  'Then run this workflow-built code-search control once, never piped, and return it as control:',
  `  gh api -X GET search/code -f q='${README_CONTROL(r)}' --jq .total_count`,
  'control.rc = its real exit code; control.count = the number it printed, or -1 when it failed; control.rateLimited =',
  'true when gh reported HTTP 403 or a rate limit (a 403 is a RATE LIMIT, never a count of 0).',
  i === 0 ? 'Then run the search-health control once, never piped, and return it as health (same fields as control):' : '',
  i === 0 ? `  gh api -X GET search/code -f q='${SEARCH_HEALTH_CONTROL}' --jq .total_count` : '',
  'Then run, never piped, and return it as exists (rc = its real exit code; status = the HTTP status number on its',
  'FIRST line, e.g. 200 from `HTTP/2.0 200 OK`, 404, 403, 429; fullName = its LAST line when status is 200, else ""):',
  `  gh api -i repos/${r} --jq .full_name`,
  'Never print environment values.',
].filter(Boolean).join('\n')
const mirrorPrompt = (url, n) => [
  'MANDATORY MIRROR STAGE: save one caller link as an agent-optimized offline copy. Run exactly, from the repository',
  `root ${ROOT} (so mise resolves the pinned firecrawl, never a stale PATH copy), without a pipe:`,
  `  mkdir -p ${shq(MIRROR_DIR)} && mise exec -- firecrawl scrape ${shq(url)} --format markdown --only-main-content -o ${shq(`${MIRROR_DIR}/${n}.md`)}`,
  `Record its real exit code as rc, and bytes = \`wc -c < ${shq(`${MIRROR_DIR}/${n}.md`)}\` (0 if the file is missing). If rc is`,
  'not 0 or bytes is 0, set reason to the first error line firecrawl printed. Do not retry with another tool, do not',
  'edit the file, and never print environment values.',
].join('\n')
const [plan, depResults, mirrorResults] = await Promise.all([
  run('plan', 'plan+fetch', 'Plan', planPrompt, { schema: PLAN }),
  DEP_REPOS.length ? parallel(DEP_REPOS.map((r, i) => () => run('deps', `deps:${r}`, 'Dependencies', depPrompt(r, i), { schema: DEPS }))) : [],
  LINKS.length ? parallel(LINKS.map((u, i) => () => run('mirror', `mirror:${i + 1}/${LINKS.length}`, 'Mirror', mirrorPrompt(u, i + 1), { schema: MIRROR }))) : [],
])

// Mandatory-stage bookkeeping: a stage that did not run or did not succeed is a mandatory gap, never a silent skip.
const mandatoryGaps = []
if (!DEP_REPOS.length) mandatoryGaps.push('dependency-repo stage: no args.repo or args.relatedRepos, so no dependency repo issues/PRs/discussions/releases were searched — re-run with args.repo')
// An agent may echo a query with its quotes; compare the bare terms.
const unquote = q => q.trim().replace(/^(["'])(.*)\1$/, '$2').trim()
const REPO_NAMES = DEP_REPOS.map(r => nameOf(r).toLowerCase())
const dependencyRuns = DEP_REPOS.flatMap((r, i) => {
  const want = depQueries(r).length
  const got = depResults[i]
  if (got === null) {
    mandatoryGaps.push(`dependency-repo stage for ${r}: agent reported nothing (null)`)
    return []
  }
  if (got.runs.length < want) mandatoryGaps.push(`dependency-repo stage for ${r}: ${got.runs.length} of ${want} run(s) reported`)
  // The count alone cannot see an agent that swapped one slot's query for the other's, in EITHER
  // direction: a name in the question-terms slot leaves the tracker unsearched for the QUESTION.
  depQueries(r).forEach((q, k) => {
    const ran = got.runs[k] ? unquote(got.runs[k].query) : null
    if (q !== null && ran !== q) mandatoryGaps.push(`dependency-repo stage for ${r}: cross-direction query "${q}" not run (got "${ran === null ? 'missing' : ran}")`)
    if (q === null && ran !== null && REPO_NAMES.includes(ran.toLowerCase())) mandatoryGaps.push(`dependency-repo stage for ${r}: question-terms query "${ran}" is a repo name, so ${r} was not searched for the QUESTION`)
  })
  got.runs.filter(x => !x.manifest || x.rc !== 0).forEach(x => mandatoryGaps.push(`dependency-repo stage for ${r}: "${x.query}" rc=${x.rc}${x.manifest ? '' : ', no manifest'}`))
  return got.runs.map(x => ({ repo: r, ...x }))
})
const mirror = LINKS.map((url, i) => {
  const m = mirrorResults[i]
  const path = `${MIRROR_DIR}/${i + 1}.md`
  if (m === null) mandatoryGaps.push(`mirror stage for ${url}: agent reported nothing (null)`)
  return m === null ? { url, path, rc: null, bytes: 0, reason: 'mirror agent reported nothing (null)' }
    : { url, path, rc: m.rc, bytes: m.bytes, reason: m.rc === 0 && m.bytes > 0 ? '' : m.reason || `rc=${m.rc}, ${m.bytes} bytes` }
})
// A link firecrawl could not fetch is the WORLD, not the process: a named gap, not a mandatory one.
const mirrorGaps = mirror.filter(m => m.rc !== null && m.reason).map(m => `${m.url}: not mirrored (${m.reason})`)
// Code search = the planner's rows + the search-health control + one README control per searched repo.
const answered = c => c.rc === 0 && !c.rateLimited
const outcome = c => (c.rateLimited ? 'was RATE-LIMITED (HTTP 403), not 0' : `returned count=${c.count} rc=${c.rc}`)
const workflowRow = (query, c) => ({ query, role: 'must-hit', source: 'workflow', count: c.count, rc: c.rc, rateLimited: c.rateLimited === true })
// Question 1, asked once (by the first dependency agent): does GitHub code search answer at all?
const healthGot = DEP_REPOS.length && depResults[0] !== null ? depResults[0].health : undefined
const healthRow = healthGot ? { ...workflowRow(SEARCH_HEALTH_CONTROL, healthGot), role: 'health' } : null
const healthFailed = healthRow !== null && !(answered(healthRow) && healthRow.count > 0)
const healthOk = healthRow !== null && !healthFailed
if (healthFailed) mandatoryGaps.push(`code search: search-health control "${SEARCH_HEALTH_CONTROL}" ${outcome(healthRow)} — gh auth, rate-limit or search is broken`)
else if (DEP_REPOS.length && depResults[0] !== null && !healthRow) mandatoryGaps.push(`code search: search-health control "${SEARCH_HEALTH_CONTROL}" was not run, so whether code search answers is unverified`)
// Question 2, per repo: does it exist under THIS name (repos API), and is a README.md of it indexed?
const RATE_LIMIT_STATUS = [403, 429]
const repoCheckGap = (r, ex) => {
  if (ex.status === 404) return `dependency repo ${r} not found via the repos API (HTTP 404)`
  if (ex.status !== 200 || ex.rc !== 0 || !ex.fullName) return `could not check ${r} via the repos API (HTTP ${ex.status}${RATE_LIMIT_STATUS.includes(ex.status) ? ' — rate-limited or forbidden' : ''}${ex.status === 200 ? `, rc=${ex.rc}, fullName "${ex.fullName}"` : ''})`
  // The API follows a rename (jdx/rtx -> jdx/mise, rc=0) while search under the old name returns 0.
  if (ex.fullName.toLowerCase() !== r.toLowerCase()) return `dependency repo ${r} redirects to ${ex.fullName} — re-run with repo/relatedRepos set to ${ex.fullName}`
  return ''
}
const readmeNotes = []
const workflowControls = DEP_REPOS.flatMap((r, i) => {
  const got = depResults[i]
  if (got === null) return []
  const c = workflowRow(README_CONTROL(r), got.control)
  const repoGap = repoCheckGap(r, got.exists)
  if (repoGap) mandatoryGaps.push(repoGap)
  else if (!answered(c)) mandatoryGaps.push(`code search: README control "${c.query}" ${outcome(c)}${healthFailed ? ' — gh auth, rate-limit or search is broken' : ''}`)
  // Only a search shown to answer (health >0) can say anything about one repo's 0.
  else if (c.count === 0 && healthOk) readmeNotes.push(`"${c.query}" returned 0 although ${r} exists — either code search does not index it (e.g. a low-star fork) or it has no README.md (e.g. README.rst); not a gap`)
  return [c]
})
const plannerRows = plan === null ? [] : (plan.codeSearch || []).map(c => ({ ...c, source: 'planner', rateLimited: c.rateLimited === true }))
const codeSearch = plannerRows.concat(healthRow ? [healthRow] : [], workflowControls)
// A planner control that missed is a guess that failed, recorded for the reader, never a gap.
const codeSearchNotes = plannerRows.filter(c => c.role === 'must-hit' && !(answered(c) && c.count > 0))
  .map(c => `planner must-hit control "${c.query}" ${outcome(c)} — a guessed control, not a gap; any other must-hit >0 carries the requirement`)
  .concat(readmeNotes)
if (plan === null) mandatoryGaps.push('code search: planner agent reported nothing (null)')
else {
  const ok = (rows, role, hit) => rows.some(c => c.role === role && answered(c) && hit(c.count))
  if (!ok(plannerRows, 'query', () => true)) mandatoryGaps.push('code search: no planner query ran with rc=0')
  if (!ok(codeSearch, 'must-hit', n => n > 0)) mandatoryGaps.push('code search: no must-hit control returned a hit, so the search is not shown to discriminate')
  if (!ok(plannerRows, 'known-absent', n => n === 0)) mandatoryGaps.push('code search: no fresh known-absent control returned 0')
}

// Planner and dependency manifests are counted SEPARATELY: dependency manifests must never mask a
// planner fan-out that produced nothing (it alone carries exa/context7/firecrawl).
const depManifests = dependencyRuns.filter(x => x.manifest).map(x => x.manifest)
const planManifests = plan === null ? [] : plan.runs.filter(r => r.manifest).map(r => r.manifest)
// A planner run that failed or wrote no manifest is a named Gap, even when its siblings succeeded.
const fanoutGaps = plan === null ? [] : plan.runs.filter(r => r.rc !== 0 || !r.manifest)
  .map(r => `planner fan-out "${r.query}" rc=${r.rc}${r.manifest ? '' : ', no manifest'}`)
if (plan === null && !LINKS.length && !depManifests.length) return { status: 'plan-null', mandatoryGaps, routing }
const manifests = planManifests.concat(depManifests)
if (!manifests.length && !LINKS.length) return { status: 'no-manifests', plan, mandatoryGaps, fanoutGaps, routing }
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
// The mirror README is written beside the mirrors while triage runs; rows come from the workflow,
// so a link whose mirror agent never ran still gets a row naming why.
const indexPrompt = [
  `Write ${MIRROR_DIR}/README.md (create or overwrite). Content: a heading "# Offline mirrors — ${REPORT_SLUG}", a line`,
  `"Caller links for ${A.reportPath}, fetched with \`mise exec -- firecrawl scrape <url> --format markdown --only-main-content\`.",`,
  'then a markdown table with columns n | url | file | rc | bytes | failure reason — one row per entry below, in',
  'order, file as the basename. Do not fetch anything. Return written=true once the file exists.',
  `ROWS: ${JSON.stringify(mirror.map((m, i) => ({ n: i + 1, ...m })))}`,
].join('\n')
const [triageOut, mirrorIndex] = await Promise.all([!manifests.length ? EMPTY_TRIAGE : run('triage', 'triage', 'Triage', [
  `QUESTION: ${A.question}`,
  `Read these research-fanout manifests and every <source>.json beside them:\n${manifests.join('\n')}`,
  codeSearch.length ? `Code-search hits (already verified by the planner): ${JSON.stringify(codeSearch)}` : '',
  'Dedup hits across sources by URL (record which sources found each). Rank by likely value for the QUESTION:',
  'primary sources (source code, merged PRs, maintainer answers, release notes) above secondary ones (blogs, forums).',
  `Choose at most ${READ_MAX} URLs worth deep-reading, each with a one-line reason. Prefer a mix: at least one primary`,
  'source per project the QUESTION names. List every source whose status is empty_unverified or error in',
  'unverifiedEmpty — those are gaps, not "no results".',
  LINKS.length ? `Do NOT choose these (the caller's links, read separately): ${LINKS.join(' ')}` : '',
].filter(Boolean).join('\n'), { schema: TRIAGE }),
LINKS.length ? run('mirrorIndex', 'mirror-index', 'Mirror', indexPrompt, { schema: MIRROR_INDEX }) : null,
])
if (LINKS.length && !(mirrorIndex && mirrorIndex.written)) mandatoryGaps.push(`mirror stage: README index ${MIRROR_DIR}/README.md was not written`)
log(`Mandatory: ${dependencyRuns.length} dependency run(s) over ${DEP_REPOS.length} repo(s); ${mirror.filter(m => m.rc === 0 && m.bytes > 0).length}/${mirror.length} link(s) mirrored; ${mandatoryGaps.length} mandatory gap(s)`)
if (triageOut === null && !LINKS.length) return { status: 'triage-null', plan, mandatoryGaps, fanoutGaps, routing }
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
  'Other pages: `mise exec -- firecrawl scrape <url> --format markdown --only-main-content` (never a bare `firecrawl`: the',
  'PATH copy can be stale), or the offline copy under docs/research/kb/raw/ when one exists — say which. Never print',
  'environment values.',
]
// Each reader keeps its identity: a reader that returns null is a GAP the report must
// name, never a silent drop (a null filtered away reads as "nothing to say").
const readers = []
for (let i = 0; i < LINKS.length; i += READ_BATCH) {
  const batch = LINKS.slice(i, i + READ_BATCH)
  const n = Math.floor(i / READ_BATCH) + 1
  readers.push({ urls: batch, run: () => run('readLinks', `read-link:${n}`, 'Read', [
    `QUESTION: ${A.question}`, 'The caller named these links; every one must be read.',
    'Read each from its OFFLINE MIRROR (the firecrawl markdown the mandatory mirror stage saved), not the live page.',
    'Only a link marked NO MIRROR is read live — and say in each of its claims that the mirror failed.', ...READ_RULES,
    ...batch.map(u => {
      const m = mirror[LINKS.indexOf(u)]
      return m.rc === 0 && m.bytes > 0 ? `- ${u}  (mirror: ${m.path}, ${m.bytes} bytes)` : `- ${u}  (NO MIRROR: ${m.reason})`
    }),
  ].join('\n'), { schema: CLAIMS }) })
}
const batches = []
for (let i = 0; i < toRead.length; i += READ_BATCH) batches.push(toRead.slice(i, i + READ_BATCH))
batches.forEach((batch, i) => readers.push({ urls: batch.map(u => u.url), run: () => run('read', `read:${i + 1}/${batches.length}`, 'Read', [
  `QUESTION: ${A.question}`, ...READ_RULES,
  ...batch.map(u => `- ${u.url}  (${u.why})`),
].join('\n'), { schema: CLAIMS }) }))
if (plan && plan.sourceDive && REPO) {
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
// What the report's evidence actually rests on, derived from what ran — never a fixed sentence.
const evidenceBase = () => [
  LINKS.length ? `the ${LINKS.length} caller link(s)` : '',
  triageOut !== null && planManifests.length ? 'hits triaged from the planner fan-out manifests' : '',
  triageOut !== null && depManifests.length ? 'hits triaged from the dependency-repo manifests' : '',
  plan && plan.sourceDive && REPO ? `the ${REPO} source dive` : '',
  'the code-search rows',
].filter(Boolean).join(' + ')
const synth = await run('synthesize', 'synthesize', 'Synthesize', [
  `QUESTION: ${A.question}`,
  `Write the research report to ${A.reportPath}. Inputs: the claims JSON below, the triage hit list, the code-search`,
  `results, and the manifests (${manifests.join(', ')}). Resolve conflicts explicitly (source code and merged PRs beat`,
  'issue threads; newer beats older; say which you trusted and why). Name every gap from unverifiedEmpty as a gap,',
  'never as "nothing found". Every FAILED READ below is a gap too: the reader for it failed, so its content is unknown.',
  'Keep distinct claims distinct: what a project SHIPS in code, what its docs/discussions PROPOSE or recommend, and what',
  'a THIRD party documents about it are three different claims — never collapse them into one headline.',
  'Sections: Answer, Evidence (claim | URL or file:line | quote), Conflicts resolved, Gaps, Recommendation,',
  'Evidence MUST also carry three tables, a row for EVERY input row even when its count is 0: "Code search" (query |',
  'role | source | count | rc — write RATE-LIMITED, never 0, for a rateLimited row) from CODE SEARCH, with each CODE',
  'SEARCH NOTE under it as a note (not a gap); "Dependency-repo fan-out" (repo | query | rc | manifest) from DEPENDENCY RUNS;',
  '"Offline mirrors" (link | mirror file | rc | bytes | failure) from MIRRORS. Every MIRROR GAP and MANDATORY GAP is',
  'a Gap; when MANDATORY GAPS is non-empty, the Answer must say the sweep is INCOMPLETE and name what did not run.',
  'Provenance (the ROUTING table below, as a table), ## GitHub repos touched (per .claude/rules/research-repo-enumeration.md).',
  `Return the path and the claims the Answer depends on (at most ${VERIFY_MAX}); mark absence=true on every claim`,
  'that something does NOT exist or does NOT happen — those are the easiest to get wrong.',
  LINKS.length ? `CALLER LINKS (each must be cited or named as unread): ${LINKS.join(' ')}` : '',
  `CLAIMS:\n${JSON.stringify(claims)}`,
  `TRIAGE:\n${JSON.stringify({ hits: triage.hits, unverifiedEmpty: triage.unverifiedEmpty })}`,
  `CODE SEARCH:\n${JSON.stringify(codeSearch)}`,
  codeSearchNotes.length ? `CODE SEARCH NOTES:\n${JSON.stringify(codeSearchNotes)}` : '',
  `DEPENDENCY RUNS:\n${JSON.stringify(dependencyRuns)}`,
  `MIRRORS:\n${JSON.stringify(mirror)}`,
  mirrorGaps.length ? `MIRROR GAPS:\n${JSON.stringify(mirrorGaps)}` : '',
  mandatoryGaps.length ? `MANDATORY GAPS:\n${JSON.stringify(mandatoryGaps)}` : '',
  fanoutGaps.length ? `FANOUT GAPS (each is a Gap: a planner fan-out run that failed or wrote no manifest):\n${JSON.stringify(fanoutGaps)}` : '',
  `FAILED READS:\n${JSON.stringify(failedReads)}`,
  stageGaps.length ? `FAILED STAGES (each is a Gap; state its consequence, and say the evidence base is: ${evidenceBase()}): ${JSON.stringify(stageConsequences)}` : '',
  // This node's own row is added by run() only when it is called, i.e. after this prompt is built.
  `ROUTING (so far; add a row for this synthesize node — ${JSON.stringify(ROUTE.synthesize)}):\n${JSON.stringify(routing)}`,
].filter(Boolean).join('\n'), { schema: SYNTH })
if (synth === null) return { status: 'synth-null', plan, triage, claims, mandatoryGaps, fanoutGaps, routing }

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

// Status: complete | mandatory-gap | partial-verify | verify-null | reconcile-null | plan-null |
// no-manifests | triage-null | synth-null | links-only. verify-null = EVERY refuter returned null;
// partial-verify = SOME did; links-only = plan/fan-out/triage failed, so the evidence base is the caller
// links plus the mandatory stages; mandatory-gap = a mandatory stage (dependency repos, mirror, code
// search) did not run or did not succeed — `mandatoryGaps` names each, and such a run can never be `complete`.
const status = verdicts.length && unverified.length === verdicts.length ? 'verify-null'
  : !reconciled ? 'reconcile-null' : unverified.length ? 'partial-verify' : stageGaps.length ? 'links-only'
  : mandatoryGaps.length ? 'mandatory-gap' : 'complete'
return { status, stageGaps, mandatoryGaps, fanoutGaps, reportPath: synth.reportPath, plan, triage, claims: claims.length, failedReads, codeSearch, codeSearchNotes, dependencyRuns, mirror, mirrorGaps, verdicts, adjudication, refuted, gaps, advice, routing }
