export const meta = {
  name: 'modernization-audit',
  description: 'Whole-repo audit: every custom module, rule, hk step, mise task, suite, skill, agent and script vs a native Claude Code, codex or pinned-tool feature; 3-lens adversarial verify; report + TOML',
  whenToUse: 'When a harness, CLI or pinned tool has moved and hand-written code may now be native. Pass args from .agent/kb/audit/args.json (unit lists, corpus paths, gap sources, pins, stamp); add reuseFindings:true to re-verify/re-synthesize from a previous run\'s on-disk finder output without paying for the finders again.',
  phases: [
    { title: 'Gap fetch', detail: 'live-fetch what the offline KB lacks; save verbatim to .agent/kb/raw' },
    { title: 'Find', detail: 'one finder per unit -> .agent/kb/audit/findings/<slug>.json' },
    { title: 'Verify', detail: 'coverage / risk / currency lenses per retire|refactor finding' },
    { title: 'Synthesize', detail: 'report .md + findings .toml under docs/research/kb/reports' },
    { title: 'Critique', detail: 'completeness critic; re-find uncovered units (max 2 rounds)' },
  ],
}

const A = args
if (!A || !A.modules || !A.rules || !A.groups) throw new Error('args must carry modules, rules, groups (see .agent/kb/audit/args.json)')

const slugOf = (p) => p.replace(/^python\/src\/dotfiles_setup\//, 'mod-').replace(/^\.claude\/rules\//, 'rule-').replace(/\.(py|md)$/, '').replace(/[^A-Za-z0-9_-]+/g, '-')

const GAP = { type: 'object', required: ['slug', 'saved', 'status', 'highlights'], properties: {
  slug: { type: 'string' }, saved: { type: 'string' }, status: { type: 'string' },
  highlights: { type: 'array', items: { type: 'object', required: ['capability', 'version', 'anchor'], properties: { capability: { type: 'string' }, version: { type: 'string' }, anchor: { type: 'string' } } } } } }
const FINDINGS = { type: 'object', required: ['unit', 'kind', 'saved', 'findings'], properties: {
  unit: { type: 'string' }, kind: { type: 'string' }, saved: { type: 'string' },
  findings: { type: 'array', items: { type: 'object', required: ['id', 'custom_thing', 'evidence', 'native_alternative', 'alternative_evidence', 'disposition', 'confidence', 'rationale'], properties: {
    id: { type: 'string' }, custom_thing: { type: 'string' }, evidence: { type: 'string' }, native_alternative: { type: 'string' }, alternative_evidence: { type: 'string' },
    disposition: { type: 'string', enum: ['retire', 'refactor', 'keep', 'unknown'] }, confidence: { type: 'number' }, rationale: { type: 'string' }, probe: { type: 'string' } } } } } }
const VERDICTS = { type: 'object', required: ['unit', 'lens', 'saved', 'verdicts'], properties: {
  unit: { type: 'string' }, lens: { type: 'string' }, saved: { type: 'string' },
  verdicts: { type: 'array', items: { type: 'object', required: ['id', 'refuted', 'reason', 'evidence'], properties: { id: { type: 'string' }, refuted: { type: 'boolean' }, reason: { type: 'string' }, evidence: { type: 'string' } } } } } }
const SYNTH = { type: 'object', required: ['reportMd', 'reportToml', 'counts'], properties: {
  reportMd: { type: 'string' }, reportToml: { type: 'string' },
  counts: { type: 'object', required: ['units', 'findings', 'retire', 'refactor', 'keep', 'unknown', 'refuted'], properties: { units: { type: 'number' }, findings: { type: 'number' }, retire: { type: 'number' }, refactor: { type: 'number' }, keep: { type: 'number' }, unknown: { type: 'number' }, refuted: { type: 'number' } } } } }
const CRITIQUE = { type: 'object', required: ['gaps'], properties: { gaps: { type: 'array', items: { type: 'object', required: ['kind', 'unit', 'detail'], properties: {
  kind: { type: 'string', enum: ['uncovered_unit', 'unverified_claim', 'unread_source', 'contradiction', 'other'] }, unit: { type: 'string' }, detail: { type: 'string' } } } } } }

const RULES = `REPO: ${A.repoRoot} (branch ${A.branch}). You are one stage of the ${A.stamp} whole-repo modernization audit (${A.epic}).
HARD RULES: (1) Read-only for every tracked file. You may create/overwrite files ONLY under ${A.auditDir}/ and ${A.rawDir}/ (and, for the synthesis stage only, the two report paths named in its prompt). (2) Never run a bare 'graphify' binary; read-only 'mise run graphify-query -- "<question>"' and 'mise run graphify-affected -- "<node>"' are allowed. (3) Never print or save a credential VALUE; presence flags only. (4) Every claim carries a citation: the custom side as repo-relative file:line, the native side as an absolute doc path:line under the corpus or a URL that was saved under ${A.rawDir}/. No citation => disposition 'unknown' with the probe that would settle it. (5) A 0-result grep is not an answer until a control arm has run (grep a term you KNOW is present with the same command shape). (6) Write your JSON to disk with the Write tool BEFORE you finish, then return exactly that JSON as your final answer (no prose).
HOST VERSIONS: Claude Code ${A.host.claudeCode} (the offline KB changelog stops at ${A.host.kbChangelogTop}); codex-cli ${A.host.codexCli}; plugins ${JSON.stringify(A.host.plugins)}.
REPO PINS (mise.toml + shared.toml + pyproject): ${JSON.stringify(A.pins)}.
CORPUS (offline, read FIRST): Claude Code docs ${A.corpus.claudeCodeDocs}/ (hooks.md, settings.md, sub-agents.md, workflows.md, skills.md, memory.md, plugins*.md, permissions*.md, cli-reference.md, agent-teams.md, changelog.md); codex docs ${A.corpus.codexDocs}/; per-tool source/doc trees ${JSON.stringify(A.corpus.toolTrees)}. Anything newer than the offline snapshot lives in the gap digests under ${A.rawDir}/ (files named <slug>.digest.md) — read the digests whose slug matches your unit's tools.`

// ---------- Phase 1: gap fetch (barrier — every finder needs the full digest set) ----------
phase('Gap fetch')
const gaps = (await parallel(A.gapSources.map((g) => () => agent(
`${RULES}

TASK: close the offline-corpus gap for '${g.slug}'.
1. Fetch ${g.url} (curl -sL --max-time 60; for api.github.com use 'gh api' with --paginate off). Save the VERBATIM body to ${A.rawDir}/${g.slug}.md with a 4-line header: url, fetched-at (from 'date -u'), http status, note='${g.note}'. mkdir -p first. If the URL 404s or times out, still write the file with the status and an empty body, and say so in 'status' — a missing page is a recorded miss, never a silent skip.
2. Then write ${A.rawDir}/${g.slug}.digest.md: one bullet per NEW capability that is newer than the baseline in the note (${g.note}) — capability, the version it shipped in, and an anchor (heading or line) into the saved verbatim file. Skip fixes that add no capability. For a release-list JSON, digest each release's body.
3. Return JSON: slug, saved (the verbatim path), status (http status or error text), highlights (the digest bullets as objects).`,
  { label: `gap:${g.slug}`, phase: 'Gap fetch', model: 'sonnet', effort: 'medium', schema: GAP })))).filter(Boolean)
const digestIndex = gaps.map((g) => `- ${g.slug}: ${g.status} (${g.highlights.length} new capabilities) -> ${A.rawDir}/${g.slug}.digest.md`).join('\n')
log(`Gap fetch: ${gaps.length}/${A.gapSources.length} sources answered; ${gaps.reduce((n, g) => n + g.highlights.length, 0)} new capabilities digested`)

// ---------- Units ----------
const units = [
  ...A.modules.map((p) => ({ kind: 'module', slug: slugOf(p), files: [p], members: [] })),
  ...A.rules.map((p) => ({ kind: 'rule', slug: slugOf(p), files: [p], members: [] })),
  ...A.groups.map((g) => ({ kind: g.kind, slug: g.name, files: g.files, members: g.members })),
]
log(`Units: ${units.length} (${A.modules.length} modules, ${A.rules.length} rules, ${A.groups.length} groups)`)

const KIND_HINTS = {
  module: `A python module in dotfiles_setup. Read it fully, plus its tests (tests/test_<name>.py if present) and every mise task / hk step / hook / suite that calls it (grep 'dotfiles-setup <subcommand>' and the module name across mise.toml, hk*.pkl, .claude/settings.json, python/verification/suites.toml). For EACH distinct capability the module provides, ask: does Claude Code (settings permissions/deny rules, hooks and their newer events, agent frontmatter fields, workflows, skills, memory, agent teams, output styles, CLI flags), codex-cli, mise (task options, env, lock, tool-sync, doctor, hooks, watch), hk (builtins, batch/exclusive/check_first, env), uv, gh (extensions, --watch, api), renovate (presets/managers), graphify, pytest plugins, an existing linter (agnix, claude-code-lint, cclint, agents-lint, ast-grep, zizmor, ghalint), or a marketplace plugin/skill now do this natively?`,
  rule: `A .claude/rules ADR. Read it fully. Audit THREE things: (a) every harness fact it asserts (a hook event, a settings key, a precedence claim, a doc anchor like '$CC/hooks.md:1394') — does the cited anchor still exist and say that at ${A.host.claudeCode}? (b) is the MECHANISM it prescribes (a custom guard, a grep step, a manual habit) now a native feature (a permission rule, a hook event, a settings key, an agent field, a workflow)? (c) does it forbid something a native feature has since made safe, or mandate something the harness now does by itself? Each stale fact or superseded mechanism is a finding.`,
  hk: `A group of hk steps (names listed). For each step read its definition in hk.pkl / hk-common.pkl / hk-image.pkl. Ask: is it now an hk Builtin (check the hk source tree in the corpus for builtins added since the pin)? Could an existing linter (ast-grep rule, agnix, claude-code-lint, cclint, agents-lint, zizmor, ghalint, actionlint's shellcheck integration, ruff rule) replace the inline shell body? Is the inline bash body itself the kind of logic .claude/rules/zero-bash-logic.md wants in python? Is any step redundant with another step or with a suites.toml contract?`,
  mise: `A group of mise tasks (names listed) in mise.toml. For each: read its body and description. Ask: does mise now provide this natively (task 'timeout', 'confirm', 'depends'/'depends_post', 'sources'/'outputs', 'env' templating, 'mise lock' flags, 'mise tool-sync', 'mise doctor', 'mise watch', hooks)? Is the task a thin wrapper around python (good) or inline logic (finding)? Is it dead (no caller in skills/rules/CI/hooks — grep, with a control arm)?`,
  suites: `A group of verification suites (names listed) in python/verification/suites.toml. For each: read its block. Ask: does it bind a CALL SITE or only a definition (a token prose can carry)? Is it redundant with an hk step, a test, or another suite? Could a linter or a structural check (ast-grep, a JSON schema, agnix) express it better than require_tokens substring matching? Is any contract asserting something that has since been retired (a stale path or token)?`,
  skills: `A group of skills (SKILL.md paths listed). For each: read the frontmatter and body. Ask: does a bundled Claude Code skill, a marketplace plugin, or a newer harness feature (workflows, /loop, agent memory, agent teams, Monitor) supersede it? Does its description exceed the 1,536-char truncation limit? Does it wrap a mise task + python library (the required three-layer stack) or carry procedure by hand?`,
  agents: `The saved subagents in .claude/agents/. For each: read the frontmatter and body. Compare against the current sub-agents.md field table (model, effort, tools, disallowedTools, permissionMode, maxTurns, skills, mcpServers, hooks, memory, background, isolation, color, initialPrompt) and against the fable-orchestrator plugin's own agents (${A.host.plugins['fable-orchestrator']}). Ask: does a plugin agent or a native field make this file redundant? Are the codex-* twins still needed once Claude tokens reset? Which fields would a modern definition set that this one omits?`,
  scripts: `The tracked shell scripts. For each: read it. Ask: is its logic already in python/ (a thin wrapper is fine, a logic body is a finding per .claude/rules/zero-bash-logic.md)? Could a native feature (a hook 'command' calling python directly, a mise task, devcontainer lifecycle hooks, gh, docker CLI flags) remove it? Is it still called anywhere (grep with a control arm)?`,
}

const finderPrompt = (u) => `${RULES}

GAP DIGESTS (read the relevant ones before deciding):
${digestIndex}

UNIT: ${u.slug} (kind: ${u.kind})
FILES: ${u.files.join(', ')}
${u.members.length ? `MEMBERS: ${u.members.join(', ')}` : ''}

WHAT TO DO: ${KIND_HINTS[u.kind] || KIND_HINTS.module}

DISPOSITIONS: 'retire' = a native feature fully covers it at the host's versions/pins — delete the custom thing; 'refactor' = native covers part of it, or the unit should wrap/adopt the native mechanism; 'keep' = nothing native exists — state WHY in rationale (this is a required justification, not a default); 'unknown' = a live probe is needed — put the exact command in 'probe'. Confidence 0..1. Every unit yields at least one finding: if nothing is superseded, emit ONE 'keep' finding for the unit as a whole with the justification. Ids: '${u.slug}-1', '${u.slug}-2', ...
Prefer precision over volume: a finding must name the specific native feature (doc path:line or saved URL), not 'could use a plugin'.

OUTPUT: write ${A.auditDir}/findings/${u.slug}.json (mkdir -p), then return the same JSON: {unit, kind, saved, findings:[{id, custom_thing, evidence, native_alternative, alternative_evidence, disposition, confidence, rationale, probe?}]}.`

const LENSES = {
  coverage: 'COVERAGE lens: read the custom thing at its cited file:line AND the cited native doc/URL. Does the native feature cover EVERY behaviour the custom thing provides HERE, including what its tests assert and the failure modes its comments name? A partial cover with no stated migration path is refuted. A doc anchor that does not exist or does not say what is claimed is refuted.',
  risk: 'RISK lens: enumerate what depends on the custom thing (grep callers across mise.toml, hk*.pkl, .claude/settings.json, python/verification/suites.toml, tests/, .claude/skills/, .github/; you may also run mise run graphify-affected -- "<node>"). Would retiring or refactoring it silently drop a machine-enforced invariant, a gate, a hook, or a contract without a named replacement? If yes, refuted.',
  currency: `CURRENCY lens: is the named native feature actually available at THIS host — Claude Code ${A.host.claudeCode}, codex-cli ${A.host.codexCli}, plugins ${JSON.stringify(A.host.plugins)}, repo pins ${JSON.stringify(A.pins)}? Check the version the doc names ("requires v…", release date) against the installed one and against the pin in mise.toml/shared.toml. A feature that exists only in a newer version than what is installed/pinned, or behind a flag/plugin not enabled here, is refuted (say what bump would unlock it).`,
}
const verifyPrompt = (u, contested, lens) => `${RULES}

You are an adversarial VERIFIER. Default to refuted=true when uncertain. Try to REFUTE EACH of the ${contested.length} findings below, one verdict per id, under ONE lens.
UNIT ${u.slug} (${u.kind}) FILES ${u.files.join(', ')}

${LENSES[lens]}

FINDINGS:
${contested.map((f) => `--- ${f.id}: disposition=${f.disposition} confidence=${f.confidence}
custom_thing: ${f.custom_thing}
evidence: ${f.evidence}
native_alternative: ${f.native_alternative}
alternative_evidence: ${f.alternative_evidence}
rationale: ${f.rationale}`).join('\n')}

OUTPUT: write ${A.auditDir}/verdicts/${u.slug}--${lens}.json (mkdir -p), then return the same JSON: {unit:'${u.slug}', lens:'${lens}', saved, verdicts:[{id, refuted, reason, evidence (file:line / doc:line for YOUR reason)}]} — every id above must appear exactly once.`

// Reuse-verify mode (args.existingVerdicts = ['<unit>--<lens>', ...], produced by the 'mise run audit-aggregate' step below): units whose three
// lens files exist are skipped entirely; the rest get ONLY their missing lenses, and the verifier reads the unit's
// findings file from disk itself — no loader, no verbatim re-typing of a 28 KB JSON (which is what defeated the haiku loader).
const verifyPromptDisk = (u, lens) => `${RULES}

You are an adversarial VERIFIER. Default to refuted=true when uncertain. Read ${A.auditDir}/findings/${u.slug}.json (unit ${u.slug}, kind ${u.kind}, files ${u.files.join(', ')}) and try to REFUTE EACH finding whose disposition is 'retire' or 'refactor', one verdict per id, under ONE lens.

${LENSES[lens]}

OUTPUT: write ${A.auditDir}/verdicts/${u.slug}--${lens}.json (mkdir -p), then return the same JSON: {unit:'${u.slug}', lens:'${lens}', saved, verdicts:[{id, refuted, reason, evidence (file:line / doc:line for YOUR reason)}]} — every retire/refactor id in the file must appear exactly once; keep/unknown ids are not voted on.`

// ---------- Phases 2+3 as one pipeline: an item's verify starts the moment its finder returns ----------
// Agent budget: the platform caps a run at 1000 agent() calls. Run 1 (2026-09-09) spent 121 finders and then
// tried 420 contested findings x 3 lenses = 1260 verifiers and died at the cap. So verification is 3 lens agents
// PER UNIT (each returning one verdict per contested finding) — at most 3 x units, independence per lens intact.
let nullStreak = 0
// Reuse mode (args.reuseFindings): a previous run's finder output already sits in ${auditDir}/findings/<slug>.json.
// The workflow cache is PREFIX-ordered (a changed call breaks it for everything after), so re-using disk output
// through a cheap loader agent is the only way to skip the opus finders after a script edit.
const loadPrompt = (u) => `${RULES}

TASK (reuse mode): a previous run of this audit already produced ${A.auditDir}/findings/${u.slug}.json. Read that file and return its JSON object EXACTLY as stored (same unit, kind, saved and findings — do not add, drop, reorder or reword anything; every finding keeps its id). If the file is missing or does not parse, return {unit:'${u.slug}', kind:'${u.kind}', saved:'', findings:[]} so the run can re-find it.`
const findStage = (u, suffix) => {
  const sfx = typeof suffix === 'string' ? suffix : '' // pipeline stages receive (prev, item, index); never treat those as a suffix
  return (A.reuseFindings && !sfx)
    ? agent(loadPrompt(u), { label: `load:${u.slug}`, phase: 'Find', model: 'haiku', effort: 'low', schema: FINDINGS })
    : agent(finderPrompt(u) + sfx, { label: `find:${u.slug}`, phase: 'Find', model: 'opus', effort: 'high', schema: FINDINGS })
}
const verifyStage = async (found, u) => {
  if (!found) return null
  const contested = found.findings.filter((f) => f.disposition === 'retire' || f.disposition === 'refactor')
  const lensResults = contested.length ? (await parallel(Object.keys(LENSES).map((lens) => () =>
    agent(verifyPrompt(u, contested, lens), { label: `verify:${u.slug}:${lens}`, phase: 'Verify', model: 'sonnet', effort: 'high', schema: VERDICTS })))).filter(Boolean) : []
  if (contested.length && lensResults.length < 2) { nullStreak += 1 } else { nullStreak = 0 }
  if (nullStreak >= 8) throw new Error(`verify stage: ${nullStreak} consecutive units received fewer than 2 lens verdicts — a usage limit or outage, not a content problem; stopping early so the run can be resumed (finder results are cached)`)
  const byId = {}
  for (const r of lensResults) { for (const v of r.verdicts) { (byId[v.id] = byId[v.id] || []).push({ ...v, lens: r.lens }) } }
  const findings = found.findings.map((f) => {
    const vs = byId[f.id] || []
    const refutedVotes = vs.filter((v) => v.refuted).length
    const contestedHere = f.disposition === 'retire' || f.disposition === 'refactor'
    return { ...f, unit: u.slug, kind: u.kind, verify_votes: vs.length, refuted_votes: refutedVotes, survived: contestedHere ? (vs.length >= 2 && refutedVotes < 2) : true }
  })
  return { unit: u.slug, kind: u.kind, findings }
}

const onDisk = new Set(A.existingVerdicts || [])
const missingLenses = (u) => Object.keys(LENSES).filter((lens) => !onDisk.has(`${u.slug}--${lens}`))
let results = []
if (A.existingVerdicts) {
  const todo = units.filter((u) => missingLenses(u).length)
  log(`Reuse-verify: ${units.length - todo.length} units fully verified on disk; ${todo.length} units need ${todo.reduce((n, u) => n + missingLenses(u).length, 0)} lens agents`)
  await pipeline(todo, async (u) => {
    const got = (await parallel(missingLenses(u).map((lens) => () =>
      agent(verifyPromptDisk(u, lens), { label: `verify:${u.slug}:${lens}`, phase: 'Verify', model: 'sonnet', effort: 'high', schema: VERDICTS })))).filter(Boolean)
    if (got.length < missingLenses(u).length) { nullStreak += 1 } else { nullStreak = 0 }
    if (nullStreak >= 8) throw new Error(`verify stage: ${nullStreak} consecutive units lost lens verdicts — a usage limit or outage; stop and resume later (all verdicts so far are on disk)`)
    return got
  })
} else {
  results = (await pipeline(units, (u) => findStage(u), verifyStage)).filter(Boolean)
}
const flat = () => results.flatMap((r) => r.findings)
const tally = () => {
  const fs = flat()
  const c = (d) => fs.filter((f) => f.disposition === d && f.survived).length
  return { units: results.length, findings: fs.length, retire: c('retire'), refactor: c('refactor'), keep: fs.filter((f) => f.disposition === 'keep').length, unknown: fs.filter((f) => f.disposition === 'unknown').length, refuted: fs.filter((f) => !f.survived).length }
}
log(`Find+Verify: ${JSON.stringify(tally())}`)
let missing = A.existingVerdicts ? [] : units.filter((u) => { const r = results.find((x) => x.unit === u.slug); return !r || r.findings.length === 0 }).map((u) => u.slug)
if (missing.length) {
  log(`${missing.length} units have no findings (finder dropout or empty reuse load) — re-finding now: ${missing.join(', ')}`)
  const more = (await pipeline(units.filter((u) => missing.includes(u.slug)), (u) => findStage(u, `\n\nROUND 1b (re-find): no stored findings existed for this unit; produce the complete list.`), verifyStage)).filter(Boolean)
  results = [...results.filter((r) => !missing.includes(r.unit)), ...more]
  missing = units.filter((u) => !results.some((r) => r.unit === u.slug)).map((u) => u.slug)
  if (missing.length) log(`Still no findings after the re-find (recorded as dropouts, not hidden): ${missing.join(', ')}`)
}

// ---------- Phase 4+5: synthesize, critique, re-find gaps (max 2 rounds) ----------
const synthPrompt = (round, counts) => `${RULES}

You are the SYNTHESIS stage (round ${round}). Inputs are ON DISK: every ${A.auditDir}/findings/*.json (one per unit) and every ${A.auditDir}/verdicts/*.json (one per UNIT per lens, each holding a 'verdicts' array with one entry per contested finding id; ignore ${A.auditDir}/verdicts-aborted-run1/). The script's in-memory tally is ${JSON.stringify(counts)} — it is PARTIAL in reuse mode; the disk is authoritative. Survival rule: a retire/refactor finding survives when it has >=2 lens verdicts and fewer than 2 are refuted; keep/unknown findings are not voted on. The full unit list (every one MUST appear in the Coverage table): ${units.map((u) => u.slug).join(', ')}.

STEP 0 — deterministic aggregation, ALWAYS first: run 'mise run audit-aggregate -- --audit-dir ${A.auditDir} --toml ${A.reportToml}' from the repo root. It recomputes survival from the disk files and writes ${A.reportToml} (the TOML findings file — do NOT hand-edit it), plus ${A.auditDir}/summary.json (compact rows + per-unit coverage) and ${A.auditDir}/coverage.json. Its one-line JSON stdout is your authoritative counts. summary.json is ~650 KB: NEVER cat it whole — query it with jq (e.g. jq '[.rows[]|select(.disposition=="retire" and .survived)]' …; jq '.coverage' …) and drill into individual findings/verdict files only for the rows you table.

Write ONE file (your only permitted tracked write): ${A.reportMd} — verbatim, no summarising away evidence. Sections, in order: '# Modernization audit — ${A.stamp}' (epic ${A.epic}); '## Executive summary' (counts + the five highest-value retirements); '## Method' (units, agent counts per stage, corpus paths, host versions, pins, the gap sources and their http status, survival rule); '## Confirmed: retire' (table: id, unit, custom thing, native alternative, evidence (custom), evidence (native), votes refuted/total — every SURVIVED retire row, no sampling); '## Confirmed: refactor' (same shape); '## Refuted' (id, disposition claimed, the winning lens reasons); '## Unknown — probes to run' (id, probe command); '## Keep' (one line per unit: justification); '## Coverage' (EVERY unit slug with kind, the count of findings by disposition, and contested_unverified — the completeness proof; from coverage.json); '## Rule refactors proposed' (each .claude/rules finding that survived, with the evidence and the motivating defect the rule was written for, so an adversarial critic can replay it); '## Scheduling proposal' (which confirmed findings belong to the orchestration-infra PR (#994), the #986 gate PR, the graphify refresh PR (#997), or a later epic checklist row); '## GitHub repos touched' (every owner/repo whose docs or source were read, one line each — mandatory).
The TOML at ${A.reportToml} already exists from STEP 0 (its 'schedule' field is "" by design — your '## Scheduling proposal' section is the human-readable proposal that a later PR reconciles into it).
Then return JSON {reportMd, reportToml, counts:{units, findings, retire, refactor, keep, unknown, refuted}} where counts are STEP 0's stdout numbers (retire/refactor = SURVIVED counts).`

const critiquePrompt = (synth) => `${RULES}

You are the COMPLETENESS CRITIC. Read ${synth.reportMd}, ${A.auditDir}/coverage.json, and query ${synth.reportToml} / ${A.auditDir}/summary.json with jq (never cat them whole). The audit was supposed to cover these ${units.length} units: ${units.map((u) => u.slug).join(', ')}.
Ask "what is missing?": (a) any unit absent from the Coverage table or with zero findings -> kind 'uncovered_unit' with unit=<slug>; (b) any CONFIRMED finding whose custom evidence file:line or native doc anchor does not exist or does not say what is claimed (spot-check at least 15, prioritising retire) -> 'unverified_claim'; (c) any gap digest under ${A.rawDir}/ that no finding cites although it names a capability relevant to a unit -> 'unread_source'; (d) two findings that contradict each other -> 'contradiction'; (e) anything else that would make a reader distrust the report -> 'other'. Return JSON {gaps:[{kind, unit, detail}]}; an empty list means the report is complete.`

let round = 1
const synthesize = async (label, prompt) => {
  let out = await agent(prompt, { label, phase: 'Synthesize', model: 'opus', effort: 'xhigh', schema: SYNTH })
  if (!out) { log(`${label}: no result (usage limit or outage) — retrying once`); out = await agent(prompt + '\n\n(RETRY — the previous attempt returned nothing; if the report file already exists, verify it and finish it rather than starting over.)', { label: `${label}:retry`, phase: 'Synthesize', model: 'opus', effort: 'xhigh', schema: SYNTH }) }
  if (!out) throw new Error(`${label}: synthesis returned nothing twice — resume later; every input is on disk under ${A.auditDir}/`)
  return out
}
let synth = await synthesize('synthesize', synthPrompt(round, tally()))
let critique = await agent(critiquePrompt(synth), { label: 'critique', phase: 'Critique', model: 'opus', effort: 'high', schema: CRITIQUE })
log(`Critique round ${round}: ${critique ? critique.gaps.length : 'n/a'} gaps`)
const MAX_ROUNDS = (A.maxRounds || 3)
while (critique && critique.gaps.length && round < MAX_ROUNDS) {
  round += 1
  const retry = [...new Set([...missing, ...critique.gaps.filter((g) => g.kind === 'uncovered_unit').map((g) => g.unit)])]
  const retryUnits = units.filter((u) => retry.includes(u.slug))
  if (retryUnits.length) {
    log(`Round ${round}: re-finding ${retryUnits.length} units: ${retryUnits.map((u) => u.slug).join(', ')}`)
    const detailFor = (u) => round >= 4 ? `\nCRITIC DETAIL (address it explicitly — it names the scope your previous findings missed):\n${critique.gaps.filter((g) => g.unit === u.slug).map((g) => g.detail).join('\n')}\nWhen the detail names a second root (e.g. .agents/skills/ or .codex/skills/ twins), audit BOTH roots for every member and emit one finding per diverged twin class.` : ''
    const more = (await pipeline(retryUnits, (u) => findStage(u, `\n\nROUND ${round} (re-find): the completeness critic flagged this unit as uncovered or incomplete; re-read everything and produce the complete findings list.` + detailFor(u)), verifyStage)).filter(Boolean)
    results = [...results.filter((r) => !retry.includes(r.unit)), ...more]
  }
  const otherGaps = critique.gaps.filter((g) => g.kind !== 'uncovered_unit')
  if (otherGaps.length) log(`Round ${round}: ${otherGaps.length} non-coverage gaps handed to synthesis: ${otherGaps.map((g) => `${g.kind}:${g.unit}`).join(', ')}`)
  const patchNote = round >= 4 ? `\n\nSOURCE-OF-TRUTH RULE FOR CITATION/FIELD FIXES (round ${round}): the TOML is regenerated from ${A.auditDir}/findings/*.json by mise run audit-aggregate -- --audit-dir ${A.auditDir} --toml ${A.reportToml}, so a correction made only in the .md is lost. For every citation defect, stale anchor, misplaced evidence field, or machine-local anchor named by the critic: (1) patch the finding's field IN ${A.auditDir}/findings/<unit>.json (keep the id; append 'CITATION CORRECTED <date>: <old> -> <new>' to its rationale); for machine-local anchors save a verbatim excerpt to ${A.rawDir}/<finding-id>-excerpt.md and cite that path alongside; (2) re-run 'mise run audit-aggregate -- --audit-dir ${A.auditDir} --toml ${A.reportToml}' so the TOML carries the fix; (3) then update the .md. Re-derive every count you state from that fresh aggregator output.` : ''
  synth = await synthesize(`synthesize:r${round}`, synthPrompt(round, tally()) + `\n\nCRITIC GAPS TO RESOLVE (address each explicitly in the report — fix the row, drop the claim, or record why it stands): ${JSON.stringify(otherGaps)}` + patchNote)
  critique = await agent(critiquePrompt(synth), { label: `critique:r${round}`, phase: 'Critique', model: 'opus', effort: 'high', schema: CRITIQUE })
  log(`Critique round ${round}: ${critique ? critique.gaps.length : 'n/a'} gaps`)
}

return { counts: synth ? synth.counts : tally(), reportMd: synth && synth.reportMd, reportToml: synth && synth.reportToml, rounds: round, residualGaps: critique ? critique.gaps : [], gapSources: gaps.map((g) => ({ slug: g.slug, status: g.status, highlights: g.highlights.length })), finderDropouts: missing }
