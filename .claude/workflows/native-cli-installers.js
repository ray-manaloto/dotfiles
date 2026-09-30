export const meta = {
  name: 'native-cli-installers',
  description: 'Move vendor AI CLIs (agy, codex, claude) off mise pins onto their native installers: plan (discover, research, blast radius, spec, critique) then, after approval, execute (implement, sweep, QA, review, docs, verify).',
  whenToUse: 'When a vendor CLI with its own native installer/updater should stop being mise-managed across this Mac: run mode "plan" first, read the returned spec, then run mode "execute" with the approved spec path.',
  phases: [
    { title: 'Discover', detail: 'read-only sweep of every mise config on this Mac for the tool families' },
    { title: 'Research', detail: 'native installers, GitHub examples, consumer blast radius (graphify affected/prs)' },
    { title: 'Design', detail: 'seven-part spec with per-file edit plan and machine checks' },
    { title: 'Critique', detail: 'improvements critic + security lens + premise check' },
    { title: 'Implement', detail: 'repo change on the named worktree branch' },
    { title: 'Sweep', detail: 'one agent per external mise config (global, repos, worktrees)' },
    { title: 'QA', detail: 'gates with file-captured exit codes' },
    { title: 'Review', detail: 'cold review + security review of the diff' },
    { title: 'Docs', detail: 'rules, skills, and CLAUDE.md prose synced to the new install channel' },
    { title: 'Verify', detail: 'live arms: which binary runs, versions, update path, doctor, latency' },
  ],
}

// Two modes, one script (Ray 2026-09-30: "Two modes: plan, then execute"). A workflow cannot pause to
// ask, so the approval gate lives BETWEEN the two runs: plan RETURNS a spec, execute consumes it.
// Shipping (`mise run ship` / `mise run kb-ship`) stays a human step after execute returns.
const A = args || {}
const MODE = A.mode || 'plan'
if (MODE !== 'plan' && MODE !== 'execute') throw new Error('args.mode must be "plan" or "execute"')
const REPO = A.repoRoot
if (typeof REPO !== 'string' || !REPO.startsWith('/')) throw new Error('args.repoRoot must be an absolute path')
const OUT = A.reportDir || `${REPO}/docs/research/kb/reports/agents`
const STAMP = A.stamp || 'undated'
// Tool families to move. Each names its native install/update entrypoint as far as the CALLER knows it;
// the research phase must re-derive and correct these, never trust them.
const TOOLS = Array.isArray(A.tools) && A.tools.length ? A.tools : [
  { family: 'agy', misePatterns: ['antigravity-cli', 'aqua:google-antigravity/antigravity-cli'], binary: 'agy', nativeHint: '~/.local/bin/agy (stale 1.1.12); `agy update`' },
  { family: 'codex', misePatterns: ['codex', 'npm:@openai/codex', 'aqua:openai/codex'], binary: 'codex', nativeHint: '~/.codex/packages/standalone; host disable_tools precedent' },
  { family: 'claude', misePatterns: ['claude', 'npm:@anthropic-ai/claude-code', 'claude-code'], binary: 'claude', nativeHint: '~/.local/share/claude/versions' },
]
const TOOL_LIST = TOOLS.map(t => `${t.family} (mise: ${t.misePatterns.join(', ')}; native: ${t.nativeHint})`).join('; ')
// Standing constraints every stage inherits (the repo rules still load; these are task-specific).
const RULES = [
  'Edits outside a file allowlist are forbidden; a gate that demands more means STOP and report.',
  'Never run a bare mutating vendor installer during PLAN mode; plan mode is read-only everywhere.',
  'Print presence of credentials, never values.',
  'Every negative claim ("not used", "absent") needs a control arm that could have found it.',
  'Classify every mise hit as HOST (Mac), IMAGE (.devcontainer/*), or CI (.github/*): only HOST pins are removed without a replacement plan; IMAGE/CI pins need a native install path proven inside that environment first.',
].join('\n- ')

const INVENTORY = {
  type: 'object',
  required: ['files', 'controlArm'],
  properties: {
    controlArm: { type: 'string' },
    files: {
      type: 'array',
      items: {
        type: 'object',
        required: ['path', 'kind', 'lines', 'scope'],
        properties: {
          path: { type: 'string' },
          kind: { type: 'string' },   // global | repo | worktree | backup | other
          scope: { type: 'string' },  // HOST | IMAGE | CI
          repo: { type: 'string' },
          branch: { type: 'string' },
          dirty: { type: 'boolean' },
          liveWriter: { type: 'boolean' },
          lines: { type: 'array', items: { type: 'string' } },
        },
      },
    },
  },
}
const REPORT = {
  type: 'object',
  required: ['summary', 'reportPath', 'citations'],
  properties: {
    summary: { type: 'string' },
    reportPath: { type: 'string' },
    citations: { type: 'array', items: { type: 'string' } },
    gaps: { type: 'array', items: { type: 'string' } },
  },
}
const SPEC = {
  type: 'object',
  required: ['specPath', 'editPlan', 'openQuestions'],
  properties: {
    specPath: { type: 'string' },
    editPlan: { type: 'array', items: { type: 'object', required: ['path', 'action'], properties: { path: { type: 'string' }, action: { type: 'string' }, reason: { type: 'string' } } } },
    openQuestions: { type: 'array', items: { type: 'string' } },
  },
}
const CRITIQUE = {
  type: 'object',
  required: ['verdicts', 'improvements', 'reportPath'],
  properties: {
    verdicts: { type: 'array', items: { type: 'string' } },
    improvements: { type: 'array', items: { type: 'object', required: ['suggestion', 'citation'], properties: { suggestion: { type: 'string' }, citation: { type: 'string' }, risk: { type: 'string' } } } },
    reportPath: { type: 'string' },
  },
}
const GATES = {
  type: 'object',
  required: ['gates'],
  properties: { gates: { type: 'array', items: { type: 'object', required: ['cmd', 'rc', 'log'], properties: { cmd: { type: 'string' }, rc: { type: 'number' }, log: { type: 'string' }, firstFailure: { type: 'string' } } } } },
}
const FINDINGS = {
  type: 'object',
  required: ['findings', 'reportPath'],
  properties: {
    findings: { type: 'array', items: { type: 'object', required: ['severity', 'claim', 'file'], properties: { severity: { type: 'string' }, claim: { type: 'string' }, file: { type: 'string' }, line: { type: 'number' } } } },
    reportPath: { type: 'string' },
  },
}
const SWEEP = {
  type: 'object',
  required: ['path', 'outcome'],
  properties: { path: { type: 'string' }, outcome: { type: 'string' }, backup: { type: 'string' }, commit: { type: 'string' }, detail: { type: 'string' } },
}

if (MODE === 'plan') {
  phase('Discover')
  const inventory = await agent(
    `READ-ONLY. Inventory every mise config file on this Mac that pins any of these tool families: ${TOOL_LIST}.\n` +
    'Search at least: ~/.config/mise (and conf.d), every git repo and worktree under ~/dev, ~/.codex, ~/ (maxdepth 3), ' +
    'mise.toml / .mise.toml / mise.*.toml / .config/mise/conf.d/*.toml / .devcontainer/mise-*.toml / .tool-versions. ' +
    'For each hit record the exact lines, kind (global|repo|worktree|backup|other), scope (HOST|IMAGE|CI — IMAGE for ' +
    '.devcontainer/*, CI for files a workflow in .github/ installs from), the git branch, whether the tree is dirty, and ' +
    'whether a live process has its cwd inside it (`lsof +D` is too slow — use `ps -axo pid,command` + per-pid cwd via ' +
    '`lsof -a -d cwd -p <pid>`). Also list `which -a` for each binary with each resolved version. ' +
    `controlArm: name a term you KNOW is present and show the same search finds it.\n- ${RULES}`,
    { label: 'discover:mise-configs', phase: 'Discover', agentType: 'general-purpose', effort: 'medium', schema: INVENTORY },
  )
  if (!inventory) throw new Error('discovery returned null — nothing to plan from')
  log(`${inventory.files.length} mise config hits across the Mac`)

  phase('Research')
  const research = await parallel([
    () => agent(
      `Research the OFFICIAL native install + update channel for each of: ${TOOL_LIST}. For each: install command, ` +
      'update command and whether it self-updates, install location, macOS AND linux (amd64/arm64) support, checksum or ' +
      'signature verification (compare with mise aqua/npm backends, which verify against mise.lock), how to pin or roll ' +
      'back a version, and env vars that disable self-update. Use this repo\'s research-sweep skill IN-LANE steps ' +
      '(local corpora first; `mise run research-fanout` with github-*, firecrawl-developer, context7; deep-read release ' +
      'notes and installer source). Latest versions only: check `mise latest` / GitHub releases before citing behaviour. ' +
      `Write the report incrementally to ${OUT}/native-installers-${STAMP}.md with a "GitHub repos touched" section.\n- ${RULES}`,
      { label: 'research:native-installers', phase: 'Research', agentType: 'general-purpose', schema: REPORT },
    ),
    () => agent(
      'GitHub code search for real-world patterns (gh api -X GET search/code; one query per alternative, no OR; re-fetch ' +
      'and grep every hit; arm with a query that must hit): dotfiles that install codex / claude / agy natively from a ' +
      'mise task or bootstrap, mise `disable_tools` usage, mise tasks named update:codex / update:claude / install:agy, ' +
      'devcontainers installing these CLIs natively (Dockerfile / postCreateCommand). Record every query, its hit count and ' +
      `rc. Write incrementally to ${OUT}/native-installers-github-examples-${STAMP}.md.\n- ${RULES}`,
      { label: 'research:github-examples', phase: 'Research', agentType: 'general-purpose', effort: 'medium', schema: REPORT },
    ),
    () => agent(
      `Blast radius of moving ${TOOLS.map(t => t.family).join(', ')} off mise, in this repo (${REPO}) and knowledge-base. ` +
      `(1) From ${A.graphRoot || REPO} (the checkout with a built graph), run \`mise run graphify-health\`, then \`mise run graphify-affected -- "<node>"\` for the modules that invoke these ` +
      'CLIs (codex_lane, sdlc_team, research_fanout, doctor, pin_parity, workflow_claude_code, antigravity plugin wrapper) ' +
      'and `mise run graphify-prs` for open PRs touching them. (2) Grep consumers: `mise exec -- agy|codex|claude`, ' +
      'disable_tools, pin-parity.toml, renovate.json, currency.toml, .github/actions/setup-*, .devcontainer/*, ' +
      '.claude/rules/ai-cli-invocation.md, .claude/CLAUDE.md. (3) Review the repo\'s blast-radius skill and graphify\'s ' +
      '`prs` command against the installed graphify version: what each does, what it misses, how to improve the skill. ' +
      `Write incrementally to ${OUT}/native-installers-blast-radius-${STAMP}.md.\n- ${RULES}`,
      { label: 'research:blast-radius', phase: 'Research', agentType: 'graphify-researcher', schema: REPORT },
    ),
  ])
  const researched = research.filter(Boolean)
  if (researched.length < research.length) log(`${research.length - researched.length} research lane(s) returned null — carried as gaps`)

  phase('Design')
  const spec = await agent(
    `Write a seven-part spec (objective, files, interfaces, constraints, verification, commit, PREMISES with file:line ` +
    `provenance) at ${REPO}/docs/specs/native-cli-installers-${STAMP}.md for moving ${TOOL_LIST} to native installers.\n` +
    `Inventory (JSON): ${JSON.stringify(inventory)}\nResearch reports: ${researched.map(r => r.reportPath).join(', ')}\n` +
    'Requirements (Ray 2026-09-30): remove these tools from EVERY mise config incl. worktrees (commit on each worktree\'s own ' +
    'branch; skip-and-report a dirty tree or one with a live writer); add native install/update mise tasks to ' +
    '~/.config/mise/config.toml with a timestamped backup first, AND keep their tracked source + python module in this repo ' +
    '(skill -> mise task -> python library; S29-M bootstrap will own the global file later); host keeps disable_tools-style ' +
    'guards where the image/CI still needs a pin. Add a MACHINE CHECK (doctor or lint) that fails when a native-managed ' +
    'tool reappears as a mise pin, or when `which` resolves a stale copy; arm it both ways. Include a rollback section ' +
    'and the security posture of each native channel versus the checksummed mise backend.',
    { label: 'design:spec', phase: 'Design', model: 'opus', effort: 'high', schema: SPEC },
  )
  if (!spec) throw new Error('design returned null')

  phase('Critique')
  const critique = await parallel([
    () => agent(
      `Attack the proposal at ${spec.specPath} against its motivating goal (native installers for ${TOOLS.map(t => t.family).join(', ')}). ` +
      'Replay whether each step catches its failure; overturn by name what does not. Then SUGGEST IMPROVEMENTS beyond the ' +
      'user\'s direction — each must cite a researched source (the reports under the research lanes, a GitHub search hit, ' +
      'vendor docs, or file:line). Unsupported suggestions are dropped. ' +
      `Write to ${OUT}/native-installers-critique-${STAMP}.md.`,
      { label: 'critique:improvements', phase: 'Critique', agentType: 'adversarial-critic', schema: CRITIQUE },
    ),
    () => agent(
      `Security lens on ${spec.specPath}: supply-chain of each native installer (curl|sh, signature, checksum, update ` +
      'channel, auto-update without review), versus mise backends pinned in mise.lock; credential exposure; what a ' +
      'compromised update could reach on this host. Findings with severity and cited source. ' +
      `Write to ${OUT}/native-installers-security-${STAMP}.md.`,
      { label: 'critique:security', phase: 'Critique', agentType: 'general-purpose', schema: FINDINGS },
    ),
    () => agent(
      `SPEC FILE: ${spec.specPath}\nVerify every PREMISES row (CONFIRMED / REFUTED / UNVERIFIABLE / ASSUMED with file:line) ` +
      'and list unstated premises. Return the full report as your final message.',
      { label: 'critique:premises', phase: 'Critique', agentType: 'premise-verifier' },
    ),
  ])
  return {
    mode: 'plan',
    inventory,
    research: researched,
    spec,
    critique: critique[0],
    security: critique[1],
    premises: critique[2],
    next: `Review ${spec.specPath}, the critique and the security report; then re-run with mode "execute", specFile set to the approved spec.`,
  }
}

// ---------------- execute ----------------
const SPEC_FILE = A.specFile
if (typeof SPEC_FILE !== 'string' || !SPEC_FILE.startsWith('/')) throw new Error('execute mode needs args.specFile (absolute, approved)')
const WORKTREE = A.worktree || REPO
const IMPLEMENTER = A.implementer || 'general-purpose' // codex-sol-implementer when codex is available
const SWEEP_TARGETS = Array.isArray(A.sweepTargets) ? A.sweepTargets : []

phase('Implement')
const impl = await agent(
  `Implement the approved SPEC FILE ${SPEC_FILE} in ${WORKTREE} (its branch is already checked out). Repo-side only: ` +
  'the python module + mise task + skill, the machine check, pin removals in THIS repo\'s mise files, and tests. Do not ' +
  'commit; report changed paths, every gate rc, and any dissent. Licensed dissent: a spec/code contradiction stops you.',
  { label: 'implement:repo', phase: 'Implement', agentType: IMPLEMENTER, effort: 'xhigh' },
)
if (!impl) throw new Error('implementer returned null — nothing to verify')

phase('Sweep')
// One agent per external config (global file, other repos, every worktree). Each backs up, edits, verifies
// resolution, and commits on its own branch — or skips with a reason (dirty tree, live writer, default branch).
const swept = await pipeline(
  SWEEP_TARGETS,
  target => agent(
    `Per the approved spec ${SPEC_FILE}, remove the ${TOOLS.map(t => t.family).join('/')} mise pins from ${target.path} ` +
    `(kind ${target.kind}, scope ${target.scope}). Rules: copy the file to a timestamped backup first; never edit a file on ` +
    'a default branch (main/master) — use or create a branch; skip and report a dirty tree or one with a live writer; ' +
    'for the global config also add the spec\'s native install/update tasks; after the edit run `mise config ls` and ' +
    '`mise ls` from that directory to prove the tool no longer resolves through mise; commit only in a worktree/branch ' +
    'the spec names. Report backup path, commit sha or skip reason.',
    { label: `sweep:${target.kind}`, phase: 'Sweep', agentType: 'general-purpose', effort: 'medium', schema: SWEEP },
  ),
)
const sweepDone = swept.filter(Boolean)
if (sweepDone.length < SWEEP_TARGETS.length) log(`${SWEEP_TARGETS.length - sweepDone.length} sweep target(s) returned null — re-run them`)

phase('QA')
const gates = await agent(
  `In ${WORKTREE}, run each gate as \`mise run gate -- run <name>\` for lint, pytest, verify, lint-docs (and pin-actions ` +
  'if .github changed) and report cmd, rc, log path and first failure. Never pipe to head/tail.',
  { label: 'qa:gates', phase: 'QA', agentType: 'gate-runner', effort: 'low', schema: GATES },
)

phase('Review')
const reviews = await parallel([
  () => agent(
    `Cold review BY REF of the working tree in ${WORKTREE} against origin/main (author family: ${IMPLEMENTER === 'codex-sol-implementer' ? 'codex' : 'Anthropic — same-family fallback, say so'}). ` +
    'Cite severity / claim / file:line / failure scenario. Write the report incrementally under ' + OUT + '.',
    { label: 'cold-reviewer:diff', phase: 'Review', agentType: 'cold-reviewer', schema: FINDINGS },
  ),
  () => agent(
    `Security review of the diff in ${WORKTREE} and of the swept external configs (${sweepDone.map(s => s.path).join(', ')}): ` +
    'installer provenance, update channels, removed checksum verification, credential reach. Cite file:line.',
    { label: 'review:security', phase: 'Review', agentType: 'general-purpose', schema: FINDINGS },
  ),
])

phase('Docs')
const docs = await agent(
  `Sync prose to the new install channel in ${WORKTREE}: .claude/rules/ai-cli-invocation.md (the "mise exec -- agy/codex" ` +
  'contract), .claude/CLAUDE.md (antigravity/codex install paragraph), any skill naming the old mise pins, and ' +
  'mise.local.toml.example. Respect md-size budgets; regenerate the .agents mirror with `mise run skills-mirror`. ' +
  'Report changed paths; do not commit.',
  { label: 'docs:sync', phase: 'Docs', agentType: 'general-purpose', effort: 'medium' },
)

phase('Verify')
const verify = await agent(
  'Live verification, each with a control arm: for each binary, `which -a` shows the native path first and its version ' +
  'equals the vendor latest; `mise ls` no longer lists the tool in any swept directory; the native update command runs ' +
  '(dry/--help if a real update would mutate); `mise run doctor` shows the new machine check PASS, and FAILs when a pin ' +
  'is temporarily re-added (restore by byte copy); the antigravity plugin\'s setup check still finds agy; latency: ' +
  'median of 5 `<binary> --version` runs, native versus the old mise shim where it still exists.',
  { label: 'verify:live', phase: 'Verify', agentType: 'general-purpose', schema: REPORT },
)
return { mode: 'execute', impl, swept: sweepDone, gates, reviews, docs, verify }
