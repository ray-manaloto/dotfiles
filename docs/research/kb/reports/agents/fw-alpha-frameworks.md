# fw-alpha: Three Claude Code multi-agent frameworks

**Agent**: fw-alpha (research delegation)
**Date measured**: 2026-08-04
**Branch**: `research/agent-team-design`
**Method**: `gh api` + `raw.githubusercontent.com`; shallow clone into `/tmp` where the tree is large.

Repos under review:

1. [Yeachan-Heo/oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode)
2. [GarySonyak/cc-native](https://github.com/GarySonyak/cc-native)
3. [Chachamaru127/claude-code-harness](https://github.com/Chachamaru127/claude-code-harness)

## Maturity snapshot (measured 2026-08-04 via `gh api repos/<o>/<r>`)

| Repo | Stars | Forks | Open issues | Created | Last push | License | Size (KB) |
|---|---|---|---|---|---|---|---|
| Yeachan-Heo/oh-my-claudecode | 38,336 | 3,451 | 3 | 2026-01-09 | 2026-08-04T02:51:40Z | MIT | 72,328 |
| GarySonyak/cc-native | 1 | 0 | 0 | 2026-05-05 | 2026-07-21T07:07:13Z | MIT | 489 |
| Chachamaru127/claude-code-harness | 3,042 | 298 | 4 | 2025-12-12 | 2026-08-04T11:42:31Z | MIT | 589,622 |

---

# 1. Yeachan-Heo/oh-my-claudecode (OMC)

**Commit examined**: `41a4c0f77144c5beb5f5f000a89cff379c680606` (2026-07-23). Version `4.15.7` (`.claude-plugin/plugin.json:3`). Note the repo's `pushed_at` is 2026-08-04 but `main`'s HEAD is 2026-07-23 — the newer push is on another ref (branch/tag), not `main`. **Relevant context: this plugin is DISABLED in this repo** (`.claude/rules/notepad-enforcement.md` records its notepad MCP tools at 0 invocations across 941 transcripts).

## What it actually is

A **large TypeScript product** shipped as a Claude Code plugin — not a prompt pack. 5,954 blobs; `src/` alone is 1,176 files, with a compiled `dist/` checked into the repo (4,300 blobs). It is simultaneously a plugin, an npm package, a CLI (`bin/`, `src/cli/`), and an MCP server.

Concrete surfaces:

- `agents/*.md` — **19 subagent definitions** (see roster below).
- `skills/` — **41 skill directories** (`plugin.json` registers 41 paths at `.claude-plugin/plugin.json:19-59`); `commands/` — 28 slash commands.
- `hooks/hooks.json` — **13 hook events wired**, 21 hook entries, every one shelling to `node "$CLAUDE_PLUGIN_ROOT"/scripts/run.cjs <script>.mjs`: `UserPromptSubmit`, `SessionStart` (×3 matchers: `*`, `init`, `maintenance`), `PreToolUse`, `PermissionRequest`, `PostToolUse` (×3), `PostToolUseFailure`, `SubagentStart`, `SubagentStop` (×2), `PreCompact` (×3), `Stop` (×4), `SessionEnd` (×2, both `"async": true`).
- `.mcp.json` — one server, `t`, run as `node ${CLAUDE_PLUGIN_ROOT}/bridge/mcp-server.cjs`.
- `src/team/` — **70 TypeScript modules**, the orchestration core (see Parallelism).
- Plus `benchmarks/`, `missions/`, `seminar/`, `research/`, and 11 translated READMEs.

## Multi-agent roles

**19 file-backed agents**, verbatim `name` + `description` from `agents/*.md` frontmatter:

| name | model | `level` | `disallowedTools` | description (verbatim) |
|---|---|---|---|---|
| `analyst` | opus | 3 | Write, Edit | Pre-planning consultant for requirements analysis (Opus) |
| `architect` | opus | 3 | Write, Edit | Strategic Architecture & Debugging Advisor (Opus, READ-ONLY) |
| `code-reviewer` | opus | 3 | Write, Edit | Expert code review specialist with severity-rated feedback, logic defect detection, SOLID principle checks, style, performance, and quality strategy |
| `code-simplifier` | opus | 3 | — | Simplifies and refines code for clarity, consistency, and maintainability while preserving all functionality. Focuses on recently modified code unless instructed otherwise. |
| `critic` | opus | 3 | Write, Edit | Work plan and code review expert — thorough, structured, multi-perspective (Opus) |
| `debugger` | sonnet | 3 | — | Root-cause analysis, regression isolation, stack trace analysis, build/compilation error resolution |
| `designer` | sonnet | 2 | — | UI/UX Designer-Developer for stunning interfaces (Sonnet) |
| `document-specialist` | sonnet | 2 | Write, Edit | External Documentation & Reference Specialist |
| `executor` | sonnet | 2 | — | Focused task executor for implementation work (Sonnet) |
| `explore` | haiku | 3 | Write, Edit | Codebase search specialist for finding files and code patterns |
| `git-master` | sonnet | 3 | — | Git expert for atomic commits, rebasing, and history management with style detection |
| `planner` | opus | 4 | — | Strategic planning consultant with interview workflow (Opus) |
| `qa-tester` | sonnet | 3 | — | Interactive CLI testing specialist using tmux for session management |
| `scientist` | sonnet | 3 | Write, Edit | Data analysis and research execution specialist |
| `security-reviewer` | opus | 3 | Write, Edit | Security vulnerability detection specialist (OWASP Top 10, secrets, unsafe patterns) |
| `test-engineer` | sonnet | 3 | — | Test strategy, integration/e2e coverage, flaky test hardening, TDD workflows |
| `tracer` | sonnet | 3 | — | Evidence-driven causal tracing with competing hypotheses, evidence for/against, uncertainty tracking, and next-probe recommendations |
| `verifier` | sonnet | 3 | Write, Edit | Verification strategy, evidence-based completion checks, test adequacy |
| `writer` | haiku | 2 | — | Technical documentation writer for README, API docs, and comments (Haiku) |

Mapping to the canonical set — OMC covers **every** slot:

| Canonical role | OMC agent(s) |
|---|---|
| orchestrator | *no agent file* — the lead session itself, driven by `skills/team`, `skills/ultrawork`, `skills/autopilot` |
| planner | `planner`, `analyst` (pre-planning) |
| researcher | `explore` (code), `document-specialist` (external docs), `scientist` (data) |
| executor | `executor`, `designer`, `git-master` |
| qa | `qa-tester`, `test-engineer`, `verifier` |
| adversarial-review | `critic`, `code-reviewer`, `security-reviewer`, `tracer`, `debugger` |
| self-optimizer | *no agent* — `skills/self-improve` (L4) + `skills/learner` (L7) + `skills/skillify` |
| documentation | `writer` |
| suggestions | `code-simplifier` (wired to the `Stop` hook, `hooks/hooks.json`) |

**The "28 agents" in the marketplace blurb is 19 files × tier variants.** `docs/shared/agent-tiers.md` is the declared single source of truth and names variants that have no file: `architect-low`, `architect-medium`, `executor-low`, `executor-high`, `explore-high`, `designer-low`, `designer-high`, `security-reviewer-low`, `scientist-high`, plus a `vision` agent. These are synthesised in `src/agents/definitions.ts:258-274`, which builds a `Record<string, {description, prompt, tools, disallowedTools, model, defaultModel}>` by loading the markdown prompt (`loadAgentPrompt`) and re-binding a different model — **one prompt, N model bindings**.

## Per-agent configuration

Only **four** knobs appear across all 19 files: `name`, `description`, `model`, `disallowedTools` — plus a **non-native `level:` integer**.

Absent from every agent file: `effort`, `maxTurns`, `tools` (allowlist form), `permissionMode`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `isolation`, `color`, `initialPrompt`. Control arm for that absence: the same `awk` frontmatter extraction over all 19 files **did** surface `disallowedTools` on 9 of them and `model` on all 19, so the extraction is not blind.

**`level:` is undocumented.** It appears on agents (2/3/4) and skills (`skills/team/SKILL.md:6` `level: 4`, `skills/self-improve/SKILL.md:4` `level: 4`, `skills/learner/SKILL.md:4` `level: 7`). The **only** explanatory line in the tree is `skills/learner/SKILL.md:11`: *"This is a Level 7 (self-improving) skill."* Control arm: the same `grep -rn --include='*.md'` shape returns **101 hits** for `ultrawork` under `docs/`, so the near-zero result for the level taxonomy is a real absence, not a broken probe. It is also **not a Claude Code frontmatter field** — the harness will ignore it.

Model tiering therefore happens in **TypeScript, not frontmatter** (`src/agents/definitions.ts`), and at **call sites**: `skills/ultrawork/SKILL.md:72-75` instructs `Task(subagent_type="oh-my-claudecode:executor", model="haiku"|"sonnet"|"opus", ...)` — an explicit per-invocation `model` param on every delegation, with the standing rule *"Always pass the `model` parameter explicitly when delegating"* (`skills/ultrawork/SKILL.md:36`).

## Parallelism / DAG

**Yes, extensively — and via several mechanisms at once.**

- **Agent tool fan-out** is the base layer. `skills/ultrawork/SKILL.md:35` — *"Fire all independent agent calls simultaneously -- never serialize independent work"*; steps 4-8 (`:52-63`) build "Parallel Execution Waves" + a "Dependency Matrix", then fire parallel-safe tasks at once and hold dependent ones. So **dependencies are modelled explicitly, but as a prompt-level artifact the lead maintains** — not as a datastructure the runtime enforces.
- **Native agent teams** for the `/team` skill. `skills/team/SKILL.md:11` states it tracks the harness: *"Claude Code 2.1.178+ removed native `TeamCreate`/`TeamDelete`; with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, each session has one implicit team and teammates are spawned directly with the Agent/Task tool using distinct `name` values."* Task-list entries carry dependencies and pre-assigned owners (`skills/team/SKILL.md`, Architecture block).
- **tmux / CLI worker panes** as the legacy lane, preserved alongside (`src/team/tmux-session.ts`, `tmux-comm.ts`, and `skills/team/SKILL.md:11` "preserves OMC's legacy tmux/CLI worker orchestration").
- **git worktrees** — `src/team/git-worktree.ts`, `merge-coordinator.ts`, `merge-orchestrator.ts`.

The `src/team/` module list is the clearest evidence of how much machinery this needs: `dispatch-queue`, `phase-controller`, `stage-router`, `role-router`, `task-router`, `allocation-policy`, `scaling`, `heartbeat`, `worker-health`, `worker-restart`, `recovery-saga`, `sentinel-gate`, `worker-activation-gate`, `conflict-mailbox`, `inbox-outbox`, `leader-inbox`, `message-router`, `process-identity-lock`, `team-owner-epoch`, `usage-tracker`, `governance`, `audit-log`, `delegation-evidence` — **70 modules**.

`src/team/role-router.ts:10-19` does **intent-based** routing by regex over task text into 9 lane intents (`implementation`, `verification`, `review`, `debug`, `design`, `docs`, `build-fix`, `cleanup`, `unknown`), returning `{role, confidence: 'high'|'medium'|'low', reason}`.

**Mode composition** is explicit (`docs/shared/mode-hierarchy.md:7-25`):

```
autopilot (autonomous end-to-end)
├── includes: ralph (persistence)
│   └── includes: ultrawork (parallelism)
├── includes: ultraqa (QA cycling)
└── includes: plan (strategic thinking)
```

with `ultrawork` declared a **component, not a mode** — *"no persistence, no verification loop"*.

## Self-improvement

**Three distinct mechanisms, none of which use the native `memory` frontmatter field** (control arm: `memory` appears in zero agent frontmatter blocks, while `disallowedTools` appears in 9 — same extraction):

1. **`skills/self-improve` (L4)** — "Autonomous evolutionary code improvement engine with tournament selection". A full loop controller with on-disk state under `.omc/self-improve/topics/{slug}/` holding `config/{settings,goal,harness,idea}.md`, `state/agent-settings.json`, `iteration_state.json`, `research_briefs/`, `iteration_history/`. It runs **fully autonomously** — `skills/self-improve/SKILL.md:14`: *"NEVER stop or pause to ask the user during the improvement loop."* Notably it ships a **self-modification guard**: *"Sealed files: validate.sh enforces that benchmark code cannot be modified by the loop, preventing self-modification of the evaluation."* (`:29`).
2. **`skills/learner` (L7, deprecated in favour of `skillify`)** — extracts a learned skill from the conversation, and **partitions its own file** into a mutable `## Expertise` section and a stable `## Workflow` section, with only Expertise updatable by improvement cycles (`skills/learner/SKILL.md:11-13`).
3. **Session-scoped project memory via hooks** — `project-memory-session.mjs` (SessionStart), `project-memory-posttool.mjs` (PostToolUse), `project-memory-precompact.mjs` (PreCompact), plus a `wiki-*` trio on the same three events and `session-end.mjs`. This is a reinvention of memory at the hook layer.

## Cross-vendor

**Yes — the most developed of the three.** `src/team/cli-detection.ts:36-40` probes five external CLIs:

```ts
codex: detectCli('codex'),
gemini: detectCli('gemini'),
cursor: detectCli('cursor-agent'),
grok: detectCli('grok'),
antigravity: detectCli('agy'),
```

`/team` accepts them as worker types directly — `skills/team/SKILL.md` examples include `/team 2:codex "..."`, `/team 2:gemini "..."`, `/team 2:antigravity "..."`.

The genuinely interesting part is **how a non-Claude worker reports a verdict**. `src/team/cli-worker-contract.ts:1-17` documents the constraint and the workaround verbatim:

> "When a /team critic/reviewer stage is routed to an external CLI worker (codex or gemini), the worker **may not call TaskUpdate directly**. To surface a structured verdict back to the team leader, the worker writes a JSON payload to a pre-agreed file path. The leader's worker-completion handler in runtime-v2 reads the file and calls TaskUpdate with verdict metadata."

The payload is typed (`cli-worker-contract.ts:33-46`): `{role, task_id, verdict: 'approve'|'revise'|'reject', summary, findings: [{severity: 'critical'|'major'|'minor'|'nit', message, file?, line?}]}`, and applies only to `CONTRACT_ROLES = {critic, code-reviewer, security-reviewer, test-engineer}` (`:24-29`). Also noted: *"Codex team workers are launched as persistent `codex` panes, not `codex exec`"*.

## Maturity

**38,336 stars, 3,451 forks, 3 open issues**, created 2026-01-09, MIT. `main` HEAD 2026-07-23; repo `pushed_at` 2026-08-04. Measured 2026-08-04. Single primary author (Yeachan Heo, `hurrc04@gmail.com`, `marketplace.json:6`) though `plugin.json` credits "oh-my-claudecode contributors". Release cadence is high — version 4.15.7 seven months after creation. Has CI (`.github/workflows/test.yml`), `CONTRIBUTING.md`, `SECURITY.md`, benchmarks, and 11 translated READMEs. **Only 3 open issues against 38k stars is itself a signal** — either aggressive triage or issues are not the support channel.

## WORTH STEALING

1. **The external-CLI verdict file contract** — `src/team/cli-worker-contract.ts:1-46`. A codex/gemini worker cannot call `TaskUpdate`, so it writes typed JSON to a pre-agreed path and the leader reads it and calls `TaskUpdate` on its behalf. This is exactly the missing piece in our `fable-orchestrator` codex lane, where the implementer's report is currently free prose.
2. **`docs/shared/agent-tiers.md` as a single declared source of truth for model routing**, with every skill file forbidden from duplicating the table (`agent-tiers.md:3`) and `ultrawork` required to read it before its first delegation (`skills/ultrawork/SKILL.md:37`). Our `parity.toml`/`currency.toml` pattern is the same idea; we have no equivalent for *agent tiering*.
3. **One markdown prompt, N model bindings** — `src/agents/definitions.ts:258-274` generates `executor-low` / `executor` / `executor-high` from a single `agents/executor.md` by re-binding `model`. Avoids the 3× prompt-drift we would get from three near-identical agent files.
4. **The mode-composition tree stated explicitly, with a component declared NOT to be a mode** — `docs/shared/mode-hierarchy.md:7-25` plus `skills/ultrawork/SKILL.md:20-26`'s `<Do_Not_Use_When>` block routing the reader to `ralph`/`autopilot`. Skills that name their own non-applicability are rare and directly reduce mis-invocation.
5. **The self-improve loop's sealed-files guard** — `skills/self-improve/SKILL.md:29`: `validate.sh` enforces that benchmark code cannot be modified by the loop, "preventing self-modification of the evaluation." Any self-optimizing agent we build needs precisely this, and it is the one thing such systems usually omit.

## DEFICIENT

- **`level:` is dead weight** — a non-native frontmatter key on 19 agents and 41 skills, with exactly one explanatory sentence in 5,954 files. Under our `md_size_budget` / agnix regime it would fail review as an undocumented field. Do not copy the field; copy the *idea* only if you also write the taxonomy down.
- **Per-agent configuration is impoverished relative to what the harness now offers.** Zero use of `effort`, `maxTurns`, `permissionMode`, `skills`, `mcpServers`, `memory`, `isolation`, `background`, `color`. All differentiation is model + `disallowedTools` + prompt. Given cc-native's `references/agents.md:70` enumerates the full field set, OMC is leaving most of the native surface unused — and a `maxTurns`-less autonomous loop is a runaway-cost hazard.
- **70 TypeScript modules of homegrown orchestration** (heartbeat, worker-restart, recovery-saga, process-identity-lock, epochs, sentinel gates) is a direct collision with our `use-tool-builtins` hard gate and `tool-currency-and-native-first`. Much of it re-implements what native agent teams + the task tools now provide; `skills/team/SKILL.md:11` admits the harness already removed `TeamCreate`/`TeamDelete` under it. Adopting this wholesale means owning a distributed-systems layer forever.
- **21 hook entries across 13 events, all shelling `node` per call.** `PreToolUse`/`PostToolUse` fire on matcher `*` with 3s timeouts. Our own single PreToolUse guard already costs ~340ms/edit (memory `project_session_2026-08-03-f`); this would multiply that and fights `zero-bash-logic`'s spirit (logic in a real language, one thin wrapper) by having *many* wrappers.
- **`dist/` (4,300 blobs) is committed to the repo**, so the reviewable diff is swamped by build output.
- **"Autonomous, never ask the user"** (`skills/self-improve/SKILL.md:14`) is the direct inverse of our eager `clarify-before-acting` rule and its `AskUserQuestion` PreToolUse gate. The self-improve mode as written could not run here without disabling a machine-enforced policy.
- **Plugin is already disabled in this repo** for measured non-use; re-enabling it to get one mechanism would be a poor trade versus porting the mechanism.

---

# 2. GarySonyak/cc-native

**Commit examined**: `c9151748d5ad446fd5fb272d0a145fc0a4caa752` (2026-07-21, author `docs-monitor` — a bot). **Single commit in history** (`git rev-list --count HEAD` → 1; the repo is force-pushed/squashed). Version `0.2.80` (`.claude-plugin/plugin.json:3`).

## What it actually is

A **Claude Code plugin** — 41 files total, no source code beyond four Python hooks. It is emphatically **not** a multi-agent framework. Its whole thesis: *Claude Code ships features weekly and the model's training memory is stale, so force every `.claude/` edit through a freshly-downloaded reference doc.*

Concrete contents:

- `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` — plugin + single-plugin marketplace manifest.
- `agents/auditor.md` — **one** subagent definition, 85 lines.
- `hooks/hooks.json` + 4 Python hooks (`cc-native-reminder.py` 53 L, `cc-native-verify.py` 373 L, `maybe-audit.py` 201 L, `refresh-refs.py` 70 L) + `_paths.py` (shared regex set).
- `skills/feature-guide/SKILL.md` (85 L) + `references/*.md` — **9 reference files, 946 lines total**, one per CC feature area (`agents.md`, `hooks.md`, `settings.md`, `skills.md`, `modes-and-permissions.md`, `mcp-and-plugins.md`, `memory-and-context.md`, `tools-and-scheduling.md`, `changelog.md`).
- `tests/fixtures/` — good/bad agent + settings fixtures and 4 transcript `.jsonl` fixtures.

## Multi-agent roles

**One role only: `auditor`** (`agents/auditor.md:2`), verbatim description:

> "Reviews Claude Code config artifacts (.claude/ files, .mcp.json, plugin manifests) for semantic correctness against the cc-native:feature-guide skill references. Invoke after editing agents, skills, hooks, settings, commands, output-styles, schedules, or rules. Does NOT edit files — produces a per-file verdict only."

Mapping to the canonical set: **qa / adversarial-review only**, and narrowly scoped to CC config artifacts. No orchestrator, planner, researcher, executor, self-optimizer, documentation, or suggestions role exists. Control arm for that absence: `agents/` contains exactly one file (`/tmp/tree_GarySonyak_cc-native.txt` lists `agents/auditor.md` and no sibling), while the same tree does list 9 `skills/feature-guide/references/*` entries — so the listing is not blind.

## Per-agent configuration

`agents/auditor.md:1-5` sets exactly three knobs:

```yaml
name: auditor
description: <as above>
model: sonnet
tools: Read, Grep, Glob, Bash(diff:*)
```

Not set: `effort`, `maxTurns`, `disallowedTools`, `permissionMode`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `isolation`, `color`, `initialPrompt`.

Notably, `hooks/cc-native-verify.py:243-247` **actively rejects** three of those fields in plugin-scoped agents:

> `f"{path}: plugin agents cannot use permissionMode/hooks/mcpServers — these fields are ignored by the plugin loader"`

That is an `error`-severity finding, i.e. cc-native asserts plugin-provided agents silently lose `permissionMode` / `hooks` / `mcpServers`. **Relevant to us if we ever ship our agents as a plugin.** I did not independently verify the claim against the harness — labelled **UNVERIFIED** as to truth, verified only as to what cc-native asserts.

## Parallelism / DAG

**None.** No fan-out, no Workflow tool, no tmux, no dependencies. The auditor is invoked once per Stop-hook block, and `agents/auditor.md:80` forbids nesting: *"**Never** invoke other subagents (no nesting)."*

## Self-improvement

No cross-session learning, and it does **not** use the `memory` frontmatter field. What it has instead is **doc freshness**: `hooks/refresh-refs.py` is a `SessionStart` (matcher `startup`) hook that re-downloads all 9 reference files from `raw.githubusercontent.com/GarySonyak/cc-native/main` on **every** session start (`refresh-refs.py:12-23,42-51`). Its own docstring calls this out as unfinished: *"POC scope only — no TTL, no version compare, no atomic writes, no opt-out flag. Every startup re-downloads all 9 reference files. Silent on any failure."* (`refresh-refs.py:4-6`).

## Cross-vendor

**None.** No codex, gemini, or other CLI is referenced anywhere in the tree.

## Maturity

**1 star, 0 forks, 0 open issues**, created 2026-05-05, last push 2026-07-21, MIT, single author (Gary Sonyak), and the only commit is authored by a `docs-monitor` bot. Measured 2026-08-04. Effectively a personal project — **do not adopt it as a dependency**; mine it for mechanisms.

## WORTH STEALING

1. **`Stop` hook returning `{"decision": "block", "reason": ...}` to force a review subagent before a turn can end** — `hooks/maybe-audit.py:191`. Its docstring names the exact reason this shape exists: *"Stop hooks cannot spawn subagents directly — `decision: \"block\"` is the documented mechanism for steering the model to do more work before allowing the turn to end."* (`maybe-audit.py:5-8`). This is the missing enforcement layer for our `agent-report-persistence` and `verify-before-advancing` rules, which are currently prose-only at the turn boundary.
2. **Anchor the loop-guard on the last *auditor invocation*, not on the last user turn** — `maybe-audit.py:97-106`. The comment documents a real self-sustaining-loop bug: *"every hook block elicits a user relay of the block message, which counts as a new user turn, which makes the auditor look stale even though it just ran."* Any Stop-hook gate we write will hit this exact trap.
3. **Pass the reviewer an ABSOLUTE reference directory, because `Glob` from cwd cannot reach the plugin cache** — `maybe-audit.py:169-186`. Measured symptom in the comment: *"the auditor was hallucinating schema-level findings from training memory ~half the time."* Directly analogous to our `$CC` offline-doc-tree convention (`research-doc-sources.md` step 00).
4. **Citation-or-downgrade discipline enforced inside the agent prompt** — `agents/auditor.md:44`: every `block`/`warn` finding must quote `(per references/<topic>.md L<n>: "<exact phrase>")` or *"you have not actually read the reference and must downgrade the finding to `info`"*. Plus the anti-adjacent-citation self-check at `agents/auditor.md:56`: *"read the cited phrase literally — does it, by itself, state the rule the finding alleges?"* This is our `probes-need-a-control-arm` evidence discipline, expressed as reviewable agent-prompt rules.
5. **`skills/feature-guide/references/agents.md` itself** (100 lines, saved verbatim to `.agent/kb/raw/cc-native-references-agents.md`) — the densest per-version changelog of CC subagent/team behaviour I found in any of the three repos, with version tags on nearly every line: background-by-default at v2.1.198 (L44), the 200-spawn-per-session cap and `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` at v2.1.212 (L63), `Task` `mode` deprecated at v2.1.212 (L64), subagents-can-spawn-subagents with a depth-5 background cap at v2.1.172 (L24), and the agent-teams limitation that matters most for our design (L96): *"When spawning a teammate from a subagent definition, only `tools`/`model` apply and the body is appended as additional instructions — the definition's `skills`/`mcpServers` frontmatter fields are ignored."*

## DEFICIENT

- **Not a multi-agent framework at all.** If the parent task is "how should we structure an agent team", cc-native answers only "how should one reviewer agent be disciplined".
- **`refresh-refs.py` is a network fetch on every session start, silent on failure, with no TTL, no integrity check, and no opt-out** — it writes attacker-influenceable content (whatever is on `main`) straight into the path the auditor is told to trust. That would not survive this repo's review; it is a supply-chain hole dressed as a feature, and it fails `use-tool-builtins` (no caching layer) and our zero-skip posture (`except Exception: pass`).
- **`hooks.json` invokes bare `python`** (`hooks/hooks.json`, all four entries), not `python3` and not a mise-pinned interpreter. On this repo's hosts that resolves unpredictably; our own guard wrapper anchors to `$CLAUDE_PROJECT_DIR` for exactly this reason.
- **The reference docs are hand-curated prose with no provenance links** — every line is a version-tagged claim with no URL back to the release note. Under our `verify-before-advancing` provenance rule ("carry a number with its CONDITION"), each line is an inherited unverified claim. Useful as a *lead list*, never as a citation.
- **Zero release cadence signal**: one squashed commit, no tags, no CHANGELOG history to read.

---

# 3. Chachamaru127/claude-code-harness

**Version `5.6.0`** (`.claude-plugin/plugin.json:3`), HEAD fetched 2026-08-04. Examined via `gh api` + `raw.githubusercontent.com` — **not cloned**, the repo is 589,622 KB (committed cross-platform Go binaries under `bin/`).

## What it actually is

A **plugin + compiled Go binary + multi-vendor skill mirror**. Its thesis is in the repo description: *"Achieving High-Quality Development Through an Autonomous Plan→Work→Review Cycle"*. Of the three, this is the one that treats agent orchestration as a **contract system**.

Concrete structure (1,630 blobs):

- `agents/` — **4** subagent definitions (`advisor`, `reviewer`, `worker`, `test-wiring-auditor`).
- `skills/` — 79 blobs, ~20 skill dirs, each `SKILL.md` + `references/` + often `schemas/`.
- `go/` — **364 files**; the real logic (`go/internal/failurecodifier/`, etc.), compiled to `bin/harness-{darwin,linux,windows}-{amd64,arm64}` **committed to the repo**.
- `scripts/` — 215 blobs; `tests/` — 261; `benchmarks/` — 170; `docs/` — 167.
- **Vendor mirrors**: `codex/.codex/skills/` (77 blobs), `opencode/skills/` (86), `.cursor/agents/{advisor,reviewer,worker}.md` (6), `skills-codex/` (7) — the same skill set re-emitted per vendor.
- `.claude/rules/` — **24 rule files** (`commit-safety.md`, `test-quality.md`, `workflow-test-wiring.md`, `shell-scripts.md`, `versioning.md`, …) plus two YAML policy files. Structurally near-identical to this repo's `.claude/rules/`.
- `.claude/memory/archive/` — **31 archived `Plans-*.md`** files dating 2025-12-25 → 2026-07-30.
- `templates/schemas/` + per-skill `schemas/` — **29 versioned JSON schema files**.

## Multi-agent roles

**4 named roles**, verbatim `description` (originals are Japanese; English gloss mine and marked):

| name | description (verbatim) | gloss |
|---|---|---|
| `advisor` | `executor が返した advisor-request.v1 に対して方針だけ返す非実行 advisor` | non-executing advisor; answers an `advisor-request.v1` with direction only |
| `reviewer` | `sprint-contract と review artifact を基準に verdict を返す read-only reviewer` | read-only reviewer returning a verdict against the sprint contract |
| `worker` | `実装、preflight 自己点検、検証、commit 準備を 1 タスク単位で進める統合ワーカー` | integrated worker: implement → preflight self-check → verify → prepare commit, one task at a time |
| `test-wiring-auditor` | `変更差分に対してテスト網が追随しているかを fresh-context で監査する read-only auditor` | read-only auditor checking, in fresh context, that the test net kept up with the diff |

Mapping to the canonical set:

| Canonical role | Harness |
|---|---|
| orchestrator | *not an agent* — the `breezing` / `harness-loop` skills (`role: orchestrator` in frontmatter), run by the host session ("brain") |
| planner | `harness-plan` / `harness-plan-brief` skills; `advisor` returns `decision: PLAN` |
| researcher | — (no dedicated role) |
| executor | `worker` |
| qa | `test-wiring-auditor`; `harness-accept` skill |
| adversarial-review | `reviewer` + the **TeamAgent Debate** four-lens pass (below) |
| self-optimizer | `failure-codifier` skill |
| documentation | — (no dedicated role) |
| suggestions | `advisor` (`decision: PLAN | CORRECTION | STOP`) |

**TeamAgent Debate** (`skills/harness-review/references/team-debate.md`) adds four *unnamed-agent* review lenses, verbatim: `Spec Agent` (仕様正本と実装差分の矛盾を探す), `Plans Agent` (Plans.md の task / DoD / Depends と差分の対応を確認する), `Regression Agent` (既存挙動・テスト・配布 mirror・CLI/skill UX のデグレを探す), `Skeptic Agent` (合格させたい前提で見落としている major risk を探す — "looks for the major risk you missed *because you wanted it to pass*"). Minimum 2 lenses, up to 4, all read-only.

## Per-agent configuration

**This repo is the answer to the brief's frontmatter question.** It uses nearly the whole surface:

| field | advisor | reviewer | worker | test-wiring-auditor |
|---|---|---|---|---|
| `model` | `claude-opus-4-8` | `claude-sonnet-5` | `claude-sonnet-5` | `claude-sonnet-5` |
| `effort` | `xhigh` | `xhigh` | `medium` | `xhigh` |
| `maxTurns` | 20 | 50 | 100 | 50 |
| `tools` | Read, Grep, Glob | Read, Grep, Glob | Read, Write, Edit, Bash, Grep, Glob | Read, Grep, Glob, Bash |
| `disallowedTools` | Write, Edit, Bash, Agent | Write, Edit, Bash, Agent | Agent | Write, Edit, Agent |
| `color` | purple | blue | yellow | red |
| `memory` | project | project | project | — |
| `isolation` | — | — | `worktree` | — |
| `skills` | — | `harness-review` | `harness-work` | — |
| `initialPrompt` | ✅ (5 lines) | ✅ (4 lines) | ✅ (numbered preflight) | ✅ (~60 lines, full contract) |
| `permissionMode` | — | — | — | — |
| `mcpServers` / `hooks` / `background` | — | — | — | — |

Observations that matter:

- **`disallowedTools: Agent` on all four** — no agent can spawn a sub-agent. Fan-out is the orchestrator's exclusive privilege. Deliberate, and it makes the topology auditable.
- **`maxTurns` scales with role** (advisor 20 → reviewer/auditor 50 → worker 100). None of the other two repos sets `maxTurns` at all.
- **`memory: project` on the three long-lived roles, deliberately absent on `test-wiring-auditor`** — its own prompt says why: `実装セッションの会話状態・memory は引き継がない` ("does not inherit the implementation session's conversation state or memory"). This is a *designed* fresh-context guarantee, not an oversight.
- **`isolation: worktree` only on `worker`** — the sole writer gets the isolated tree.
- **Full model IDs** (`claude-opus-4-8`, `claude-sonnet-5`) rather than the `opus`/`sonnet` aliases — pinned, but they will rot.
- ⚠️ **`effort: xhigh` is suspicious.** cc-native's `references/agents.md:70` enumerates `effort (low/medium/high/max)`; `xhigh` is the *Codex* reasoning-effort spelling. Two sources disagree, so one is wrong: either cc-native's list is stale or the harness is emitting a value Claude Code silently drops. **I did not resolve this** — flagged **UNVERIFIED**, and worth a direct probe before we copy `effort: xhigh` anywhere.

## Parallelism / DAG

Yes, on several axes, and dependencies are **first-class in the plan file**:

- `breezing` exposes `--parallel N` in its `argument-hint` (`skills/breezing/SKILL.md:16`), alongside `--codex`, `--cursor`, `--reviewer-only`, `--no-commit`, `--no-discuss`, `--no-review-gate`, `--auto-mode`.
- **Dependencies live in `Plans.md`** as `task / DoD / Depends` triples — the `Plans Agent` debate lens exists specifically to check "the correspondence between `Plans.md`'s task / DoD / Depends and the diff". So the DAG is a reviewed artifact, not runtime state.
- **`harness-loop` uses `ScheduleWakeup` + `/loop`** for long-running work, re-entering with **fresh context each wake** (`skills/harness-loop/SKILL.md`). It documents the runtime clamp precisely: *"`ScheduleWakeup` の `delaySeconds` はランタイムで **[60, 3600]** に clamp される"*, with a pacing table — `worker`/`ci` 270s, `plateau` 1200s, `night` 3600s — and `--max-cycles` defaulting to 8.
- **A concurrency-control hook**: `hooks/hooks.json` wires `PreToolUse` on `Write|Edit` to `harness hook pre-tool-use-file-lease` — an actual **file-lease** mechanism, plus `hook inbox-check`.
- Not the Workflow tool; not tmux. The heavy lifting is the Go binary plus skill-level protocol.

## Self-improvement

**`failure-codifier`** — mines recurring failure patterns from the breezing orchestration ledger and a "Judgment Ledger", and emits `failure-rule.v1` proposals with confidence scores. The design constraint is the interesting part (`skills/failure-codifier/SKILL.md`, 核心契約):

> **human-approval-required**: codifier は dry-run 提案のみ。`patterns.md` / `decisions.md` への自動昇格は構造的に禁止。
> ("the codifier makes dry-run proposals only; auto-promotion to `patterns.md`/`decisions.md` is structurally forbidden")

Confidence is thresholded on occurrence count — `count ≥ 3 → medium`, `count ≥ 5 → high` — implemented in `go/internal/failurecodifier/confidence.go`, and the skill's `allowed-tools` is `["Read", "Bash", "Grep"]` so it *cannot* write the SSOT even if instructed.

It **does** use the native `memory` frontmatter field (`memory: project` on 3 of 4 agents) — the only one of the three repos that does. It supplements it with an MCP memory server: `harness-loop`'s allowed-tools include `mcp__harness__harness_mem_resume_pack` and `mcp__harness__harness_mem_record_checkpoint`.

## Cross-vendor

**The most thorough of the three — vendor support is structural, not a flag.** Parallel mirrored trees: `codex/.codex/skills/` (77 blobs), `opencode/skills/` (86), `.cursor/agents/` (3 agent defs), `skills-codex/`. `.claude/rules/` carries `codex-cli-only.md` and `cursor-cli-only.md`.

Backend selection is a documented per-run decision (`skills/breezing/SKILL.md`, "Backend 既定と per-run のフラット判断"), with the default explicitly defended:

| work type | recommended backend | stated reason |
|---|---|---|
| normal implementation/fix/test (default) | `claude` (native) | the Worker contract (`worker-report.v1` / 5 self_review items) all applies |
| large independent bulk implementation; dodging Claude rate limits | `codex` | can delegate the deep tier at `xhigh` (model resolved by `model-routing.sh`) |
| bulk UI generation, lean fast delegation | `cursor` | lean path (worktree isolation + Lead diff review) |

Two details worth carrying: *"env 直読みは引き続き禁止"* (reading the backend from env directly stays forbidden — always go through the resolver with an explicit `--backend` override), and the review gate runs a **fresh-context reviewer subagent concurrently with `codex-companion.sh review`** as a second opinion, iterating until APPROVE, **max 3 rounds**, then escalating to a human with `cc:WIP` restored.

`team-debate.md` also defines a fallback ladder when native TeamAgent is unavailable, recording `team_agent_mode` as one of `native | codex-companion | manual-pass | unavailable` — and if it is `unavailable` and manual-pass is impossible, the run **stops** as `decision_needed` rather than silently skipping the review.

## Maturity

**3,042 stars, 298 forks, 4 open issues**, created 2025-12-12, MIT, last push 2026-08-04. Measured 2026-08-04.

**Release cadence is the strongest of the three**: v5.0.0 (2026-07-09) → v5.1.0 (07-15) → v5.2.0 (07-16) → v5.3.0 (07-19) → v5.3.1 (07-20) → v5.4.0 (07-26) → v5.5.0 (07-29) → **v5.6.0 (2026-08-01)** — 8 releases in 23 days. `gh api repos/.../commits?since=2026-07-05` returned the full page (100 commits in 30 days, so ≥100).

**Effectively single-author**: `Chachamaru127` 1,129 contributions vs `claude` 46, `dependabot[bot]` 24, `github-actions[bot]` 2, `aryrabelo` 1. Has `SECURITY.md`, `scorecard.yml`, CI workflows, `VERSION`, and 261 test blobs.

## WORTH STEALING

1. **The `"type": "agent"` hook — an LLM gate wired directly into `PreToolUse`.** `hooks/hooks.json`, `Write|Edit` matcher, third entry: `{"type": "agent", "prompt": "Review the following code change for quality issues... return JSON with permissionDecision: 'deny'...", "model": "haiku", "timeout": 30}`. A haiku-tier model adjudicating every write for hardcoded secrets / TODO stubs / injection, with the authority to **deny**. Our guard layer is all deterministic Python; this is the judgment-shaped complement, and `haiku` makes it affordable.
2. **The fresh-context auditor whose prompt forbids inheriting memory, plus a bounded appeal.** `agents/test-wiring-auditor.md` omits `memory` on purpose, fixes its first three steps, and caps appeals: *"再申立ては exactly **1 回**まで"* — `appeal_round >= 2` ⇒ verdict `APPEAL_REJECTED`, no re-analysis. It also **enumerates forbidden remedies** so the agent cannot be argued into weakening the tests: test-invocation removal, `|| true` addition, `set +e` conversion, assertion-count reduction. That last list is directly portable to our `zero-skip-policy`.
3. **Versioned JSON contracts between agents** — 29 `*.v1.schema.json` / `*.v1.json` files (`advisor-request.v1`, `advisor-response.v1`, `worker-report.v1`, `test-wiring-audit.v1`, `failure-rule.v1`, `judgment-ledger.v1`, `orchestration-scorecard.v1`). Every agent's output is a **schema-validated object with a `schema_version`**, not prose. This is the generalisation of OMC's CLI-worker verdict file, and it is what makes a multi-vendor swap safe.
4. **`failure-codifier`'s structural ban on self-promotion** — the self-learning loop proposes rules with confidence thresholds (`count ≥ 3 → medium`, `≥ 5 → high`) but its `allowed-tools: ["Read","Bash","Grep"]` makes writing the SSOT *impossible*, not merely discouraged. Compare OMC's sealed-files guard: same instinct, enforced by capability rather than by a validator.
5. **The `Skeptic Agent` lens, and the trigger list that summons the debate** — *"looks for the major risk you're missing because you want this to pass"*, required when Claude and Codex verdicts diverge, when reviewers disagree across dimensions, or when **the same issue fails re-review twice in a row**. Encoding "two probes disagree ⇒ escalate" as a workflow trigger is exactly our `probes-need-a-control-arm` cross-check rule, operationalised.

Runner-up worth noting: rich **skill frontmatter taxonomy** — `kind`, `purpose`, `trigger`, `shape` (`delegate`/`wrap`), `role`, `base`, `pair`, `owner`, `since`, `user-invocable`, and negative triggers baked into `description` (*"Do NOT load for: one-shot task execution, review, release, planning"*). The `Do NOT load for` clause is a cheap, high-value addition to any skill description.

## DEFICIENT

- **Everything is in Japanese** — all four `initialPrompt`s, most `SKILL.md` bodies, all rule files. Adopting a mechanism means translating it and losing the original as the reviewable source. It also means our `typos`/agnix gates would fire on any verbatim copy.
- **~575 MB of committed cross-platform Go binaries** (`bin/harness-darwin-arm64`, `-linux-amd64`, `-windows-amd64.exe`, …). Unreviewable, unverifiable, and the hooks `exec` them. That is a supply-chain posture this repo would reject outright.
- **The hook commands are a ~600-character inline `/bin/bash -c` blob, repeated verbatim in every one of the ~10 hook entries** — a `valid_root()` function doing plugin-root discovery across five candidate paths, re-inlined each time. It head-on violates our `zero-bash-logic` rule and its `bash_logic_budget` gate, and a single fix must be applied ten times.
- **Hooks fail open and silent**: `if ! valid_root "$root"; then echo "... hook skipped" >&2; exit 0; fi`. Our `#343` incident was precisely this — a guard that is absent rather than failing loudly, with no fail-open ledger.
- **`effort: xhigh` and pinned model IDs (`claude-opus-4-8`) will rot**, and nothing in the repo validates them. cc-native's verifier would flag the first; nothing here does.
- **Single-author, 1,129 of 1,202 commits**, moving at 8 releases in 23 days. High velocity is a strength for mining and a risk for depending.
- **No `permissionMode` on any agent**, despite heavy use of everything else — so agent-level permission posture is left to the session and to the hook layer.

---

## Cross-repo synthesis

**Per-agent frontmatter coverage** (the brief's core question), measured across all three:

| field | OMC (19 agents) | cc-native (1) | harness (4) |
|---|---|---|---|
| `model` | ✅ all | ✅ | ✅ (full IDs) |
| `tools` | ❌ | ✅ | ✅ |
| `disallowedTools` | ✅ 9/19 | ❌ | ✅ all |
| `effort` | ❌ | ❌ | ✅ (`xhigh`/`medium`) |
| `maxTurns` | ❌ | ❌ | ✅ (20/50/100) |
| `memory` | ❌ | ❌ | ✅ 3/4 |
| `isolation` | ❌ | ❌ | ✅ worker only |
| `skills` | ❌ | ❌ | ✅ 2/4 |
| `initialPrompt` | ❌ | ❌ | ✅ all |
| `color` | ❌ | ❌ | ✅ all |
| `permissionMode` | ❌ | ❌ | ❌ |
| `mcpServers` | ❌ | ❌ | ❌ |
| `hooks` | ❌ | ❌ | ❌ |
| `background` | ❌ | ❌ | ❌ |

Three notes on that table. `permissionMode`/`hooks`/`mcpServers` are absent everywhere, and cc-native asserts why: `hooks/cc-native-verify.py:243-247` claims plugin-scoped agents have those fields **ignored by the loader**. Second, OMC's absences are real but partly compensated in TypeScript (`src/agents/definitions.ts`) rather than being missing capability. Third, `harness` is the only project treating an agent definition as a *contract* — and it is also the only one that sets `maxTurns`, which is the single field most relevant to bounding an autonomous loop's cost.

**The one idea all three converge on**, arrived at independently: *an agent's output should be a typed artifact, not prose.* cc-native demands a citation format with a downgrade rule; OMC defines `CliWorkerOutputPayload` so a non-Claude worker can report a verdict; the harness ships 29 versioned schemas. If only one thing is taken from this sweep, it is that.

---

## Probe methodology and control arms

Per this repo's `probes-need-a-control-arm` rule, every negative reported above ran a positive arm:

| Negative claim | Probe | Control arm | Result |
|---|---|---|---|
| OMC agents set no `effort`/`maxTurns`/`memory`/… | `awk` frontmatter extraction over all 19 `agents/*.md` | same extraction on the same files | surfaced `disallowedTools` on 9/19 and `model` on 19/19 → **probe discriminates** |
| OMC's `level:` taxonomy is undocumented | `grep -rn --include='*.md' -iE "level (1\|4\|7)\b"` over `docs/ AGENTS.md CLAUDE.md skills/` | same command shape for `ultrawork` under `docs/` | control returned **101 hits**, target returned **3** (only one explanatory) → **real absence** |
| cc-native defines exactly one agent | `git ls-tree`-derived blob list | same list for `skills/feature-guide/references/` | control returned 9 files → **listing not blind** |

One probe **failed and was corrected**: `grep -rn --include=*.md ...` returned zsh's `no matches found` because the unquoted `*.md` was glob-expanded by the shell before `grep` saw it — a zero-result that was **not** an answer. Re-run quoted. (This is the trap recorded in memory `feedback_zsh_no_word_splitting`'s neighbourhood; worth noting it bites `--include=` too.)

**Not verified** (labelled inline): whether `effort: xhigh` is accepted by Claude Code (cc-native's reference says `low/medium/high/max`); whether plugin-scoped agents really do have `permissionMode`/`hooks`/`mcpServers` ignored (cc-native asserts it, I did not test it). Both are cheap direct probes for whoever acts on this.

## GitHub repos touched

- [Yeachan-Heo/oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) — subject repo 1; read `agents/*.md`, `skills/{team,ultrawork,self-improve,learner}/SKILL.md`, `src/team/*.ts`, `src/agents/{types,definitions}.ts`, `docs/shared/{agent-tiers,mode-hierarchy}.md`, `hooks/hooks.json`, manifests.
- [GarySonyak/cc-native](https://github.com/GarySonyak/cc-native) — subject repo 2; read all 4 hooks, `agents/auditor.md`, `skills/feature-guide/references/agents.md`, manifests, `_paths.py`.
- [Chachamaru127/claude-code-harness](https://github.com/Chachamaru127/claude-code-harness) — subject repo 3; read `agents/*.md` frontmatter, `hooks/hooks.json`, `.claude-plugin/plugin.json`, `skills/{harness-loop,breezing,failure-codifier}/SKILL.md`, `skills/harness-review/references/team-debate.md`, schema inventory, releases/contributors via API.

## Raw material persisted

- `.agent/kb/raw/cc-native-references-agents.md` — verbatim 100-line CC subagent/agent-teams reference (cc-native `HEAD`, commit `c915174`).
- `.agent/kb/raw/claude-code-harness-agents.md` — verbatim YAML frontmatter of all 4 harness agent definitions (v5.6.0).
