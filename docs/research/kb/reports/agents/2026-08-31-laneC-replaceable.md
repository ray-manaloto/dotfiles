# Lane C — replaceability audit of custom Claude infrastructure

Date: 2026-08-31  
Repository: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`  
Snapshot: `5f51d6922f82e0fdf476bcda59ff17730e7ddffa` (`feat/session-skills-pwf-integration`)  
Claude Code: `2.1.251`

## Executive conclusion

Real removable machinery is concentrated in three places:

1. Generic work-state persistence and common-case handoff/resume are now substantially duplicated by native session persistence, Remote Control/Desktop/Web handoff, and the already enabled Planning With Files plugin.
2. Manual copying of final subagent reports can be replaced by native `SubagentStop`/`TeammateIdle` hooks; only the repo-specific destination/naming contract needs to remain.
3. Custom plugin/skill evaluation is superseded by current first-party `claude plugin eval`.

The largest systems are not the safest deletions. Requirement closure, semantic command parsing, verification contracts, orchestration supervision, doc-reference integrity, memory-index safety, and the project doctor enforce repo-specific invariants for which no inspected plugin or native feature is equivalent.

“Replacement exists” below means a named, inspected feature performs the general job. The verdict asks whether it is actually better here. A partial alternative does not earn `REPLACE`.

## Method and counting

- Sizes are current `wc -l`/`wc -c` measurements of production/config files named in each row. Tests are excluded unless called out. Grouped rows overlap and must not be summed.
- Measured corpus: 26 rules / 2,461 lines / 131,694 bytes; 31 skills / 4,633 lines / 231,598 bytes; 4 agents / 749 lines / 64,927 bytes: **428,219 bytes**. The Python package is 69 modules / 38,690 lines / 1,545,666 bytes. There are 77 mise tasks.
- Local primary probes: `claude --version`, `--help`, `agents --help`, `doctor --help`, `plugin list --json`, `plugin details`, `plugin validate --strict`, and `plugin eval --help`.
- Plugins were judged from actual files under `~/.claude/plugins/cache/`, not marketplace summaries. Disabled/cached-only status is explicit.
- Native behavior was checked against official docs for [sessions](https://code.claude.com/docs/en/sessions), [Remote Control](https://code.claude.com/docs/en/remote-control), [web sessions](https://code.claude.com/docs/en/claude-code-on-the-web), [agents](https://code.claude.com/docs/en/agents), [hooks](https://code.claude.com/docs/en/hooks), [permissions](https://code.claude.com/docs/en/permissions), [memory](https://code.claude.com/docs/en/memory), [skills](https://code.claude.com/docs/en/skills), and [plugins](https://code.claude.com/docs/en/plugins-reference).
- Graphify could not be query authority because its health path could not write mise/uv cache state in the sandbox. Repo source is the fallback authority.

## Replacement matrix

| Custom machinery | What it does | Size (lines / bytes) | Replacement? | Named replacement | Verdict | Reason |
|---|---|---:|---|---|---|---|
| Session snapshot/handoff/resume (`session_state.py`, `handoff_check.py`; handoff/resume skills) | Captures git/PR/task state, validates citations/tasks, reconciles live state. | 1,072 / 44,900 | Strong partial | Native `--continue`, `--resume`, `/resume`, `--from-pr`, `--fork-session`; Remote Control; Desktop/Web; `--teleport`; enabled Planning With Files 3.12.0. | **REPLACE common path; KEEP thin exception** | Native sessions preserve context/agent/permissions/goals/tasks; PWF restores work after clear/compact/crash. Keep fallback for stopped machines, dirty/SSH/offline work, HEAD/PR reconciliation, audit. The skills' no-cross-device premise is stale. |
| Requirement/evidence closure (`session_ledger.py`, `session_store.py`, `session_gate.py`, requirements portion of `session_review.py`, session-review skill) | Normalizes Claude/Codex JSONL; derives requirements, promises, claims, lineage, omissions/dispositions; stores facts and bounded receipts. | 6,510 / 236,975 | No equivalent | Native task lists and PWF plans are producer-authored alternatives, not auditors. | **KEEP** | No inspected feature reconstructs cross-provider requirements/evidence or hash/nonce receipts. Plans cannot independently falsify their producer. |
| Automation/reasoning mining (`session_review.py`, `command_audit.py`, session-review skill) | Finds recurring command shapes, one-off automation candidates, manual reasoning sinks and goal-history patterns. | 2,023 / 81,931 | Partial | Skill Creator creates/evaluates proposed skills; Session Report reports usage; Hookify analyzes a short current window. | **KEEP, then measure usage** | None mines multiple sessions, goal-history revisions, reasoning sinks or coverage. Delete only as a deliberate capability cut if outputs are unused. Session Report is cached, not loaded, and covers usage—not requirements. |
| PreToolUse semantic redirect (`hook_guard.py`, `scripts/pretooluse-guard.sh`) | Parses quotes/heredocs/wrappers/separators; denies and redirects to mise with tailored reasons. | 872 / 43,875 | Partial | Native permissions/hook decisions and hook `if` prefilters; official Hookify regex rules. | **KEEP core; REPLACE trivial bans** | Native permissions suit unconditional bans. Hookify regexes raw fields, lacks shell/repo semantics, and its wrapper catches errors and exits successfully. Keep semantic parsing; migrate static rules. |
| Ask/write/branch/self-check (`ask_quality.py`, `branch_guard.py`, `hook_selfcheck.py`) | Enforces recommended questions, write constraints and hook wiring/behavior. | 973 / 41,951; ask+branch 520 / 21,969 | Partial | Plan-mode question UI; permissions; `claude plugin validate .claude --strict` for schema/frontmatter. | **INVESTIGATE decomposition** | Native validation replaces schema checks, not E2E decisions or the repo rubric. Keep behavioral fixtures and branch constraints. |
| Doc refs (`doc_refs.py`) | Validates inline-code paths, task/skill names and wikilinks with exceptions. | 465 / 19,474 | No drop-in | agnix for Claude structure/imports; rumdl/markdownlint for Markdown/real links; disabled Claude MD Improver for ad hoc review. | **KEEP; INVESTIGATE citation migration** | Nothing inspected checks arbitrary inline-code paths plus mise/skill symbols deterministically. Real Markdown links could remove only the path portion. |
| Markdown budgets (`.claude/rules/md-size-budgets.md`; shared `kb_setup.md_budget`) | Enforces byte/line ceilings by load class and eager closure. | 190 / 10,132 local | No gate | Native guidance, `/context`, `InstructionsLoaded`, auto-memory 200-line/25KB window. | **KEEP** | Native surfaces diagnose/calibrate; none enforces repo byte budgets/import closure in CI. Unscoped rules are ~88% of eager rule corpus. |
| Plugin/agent listing budget (`listing_budget.py`) | Estimates enabled listing/description cost against thresholds. | 236 / 9,350 | Substantial partial | `plugin details` gives current-model component/always-on token costs; `plugin list --json` gives loaded state. | **INVESTIGATE; likely REPLACE** | Native estimates are better, but per-plugin output lacks a stable aggregate JSON contract. Prove a bounded collector, keep only threshold. |
| Verification contracts (`python/verification/suites.toml`, `verify.py`, `token_audit.py`, token-check skill) | Runs ~123 cross-file contracts: tokens, exact lines, regex, order, reachability and uniqueness. | 3,521 / 297,946 | No drop-in | hk/mise orchestration, `TaskCompleted`/`Stop` hooks, domain linters. | **KEEP runner; INVESTIGATE per-contract retirement** | Hooks decide when to run, not policy. Native linters can shrink the 250,895-byte TOML; wholesale policy rewrite transfers maintenance. Prune narrative and assertions whose revert control does not fail. |
| Plugin/skill evals (`eval_cases.py`; shared `kb_setup.evals`) | Runs reachability and control-armed behavior fixtures. | 428 / 18,506 local | Yes for plugin/skill behavior | First-party `claude plugin eval`: graders, with/without ablation, tools, MCP mocks, judge/model, cost/time/turn limits, thresholds, JSON/HTML. | **REPLACE** | Direct native capability with real no-plugin baseline. Move reachability to doctor/verify; retain direct Python parser unit tests. |
| Notepad/report/artifact rules (`notepad-enforcement.md`, `agent-report-persistence.md`, `agent-artifact-conventions.md`) | Requires immediate findings, verbatim/incremental capture and standard destinations. | 222 / 11,641 | Yes for notes/final copy; not destination | Enabled PWF files/hooks; native `SubagentStop` gives `agent_transcript_path` + `last_assistant_message`; `TeammateIdle` can require an artifact. | **REPLACE most; KEEP thin convention** | PWF duplicates generic notepad. Lifecycle hooks remove parent transcript scraping. Keep tracked destination/brief association and incremental pre-death capture where needed. |
| Project doctor (`doctor.py`, `doctor.toml`, `path_drift.py`, `listing_budget.py`) | Checks MCP env/scope/pins/policy, fnox leaks, duplicates, currency, listings, PATH and live health. | 2,025 / 85,099 | Partial | Native doctor and `/mcp`, `/hooks`, `/permissions`, `/context`, `/memory`, `/skills`, `/agents`, `/status`, safe mode, plugin details. | **KEEP, narrowed** | Native doctor covers install/update/keychain/config/Remote Control, not fnox leakage, MCP shadowing/policy/pins, currency or PATH. Delegate generic checks only. |
| Graphify surface (`graphify.py`, hook wrapper, rule, skill/references) | Pins query behavior, checks health/receipts, guards edits, formats results and documents workflows. | 2,130 / 107,419 | Partial | Graphify's own `hook install`, `claude install`, `watch`, `query`, `hook-guard` in `.claude/skills/graphify/references/`. | **INVESTIGATE** | Wrapper already delegates to native guard; watch may replace nudges/prose. Keep project pinning, deterministic args, health/receipt provenance and fail-closed truncation until native equivalence. |
| Background watchdog/projector (`dag_tick.py`, `dag_project.py`, `codex_lane.py`, `codex_verdict.py`) | Classifies roster, respawns/stops, projects NEEDS_HUMAN, maintains lane/verdict state. | 3,629 / 159,411 | Stronger partial | Native `--bg`, `agents --json --cwd --all`, attach/logs/stop/rm/respawn/worktrees; enabled Fable 1.21.0 roles. | **INVESTIGATE with controls** | Native supervision reduces process code; custom layer adds safe projection, schemas/CAS/idempotency/rework. Probe crash, wedge, approval, completion and restart. |
| Reaping/rework (`reap.py`) | Consumes verdicts, checks stable artifacts/idempotency, applies bounded transitions. | 536 / 19,603 | Partial | Native background completion + Fable reviewer/implementer. | **KEEP pending DAG investigation** | Neither has the same stable run dir, schema, CAS receipt and bounded rework contract. |
| Auto-memory index (`memory_index.py`, memory-index-curation skill) | Audits 25KB/200-line index, index-only facts, unindexed memories and inbound refs before deletion. | 878 / 38,581 | No | Native auto memory/`/memory`; cached `claude-mem` is lossy searchable memory, not integrity checking. | **KEEP** | Protects against native memory cutoff/dangling-reference risks. Another store adds infrastructure without proving survival. |
| Whole rule/skill/agent corpus | 61 files of policy/workflows/reviews/tool doctrine; unscoped rules eager-load. | 7,843 / 428,219 | Many partials; no wholesale replacement | Path-scoped rules, on-demand supporting files/`context: fork`; enabled PWF, Matt Pocock, Fable, Skill Creator; installed Claude MD tools. | **INVESTIGATE file-by-file** | Remove generic duplication and move task material behind skills/support files. Similar titles are not equivalence; require replay/control evidence. |

## Verified replacement evidence

### Planning With Files

Installed and enabled in `.claude/settings.json`, version 3.12.0. It creates `task_plan.md`, `findings.md`, `progress.md`, supports `.planning/<task>`, records a phase ledger/plan hash, and installs six hooks including SessionStart, PreCompact and Stop:

- `/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/.claude-plugin/plugin.json`
- `/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/skills/planning-with-files/SKILL.md`
- `/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/hooks/hooks.json`
- `/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/docs/agent-forgets-plan-after-clear.md`
- `/Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0/commands/plan-doctor.md`

`plugin details` reported 14 skills, six hooks and ~735 always-on tokens. A second generic notepad protocol is hard to justify. PWF does not inspect native session stores or preserve verbatim agent evidence itself.

### Hookify

Official, installed, disabled. Actual engine supports regex/conditions over raw Bash/file/prompt/stop fields. Its PreToolUse wrapper catches errors and exits successfully:

- `/Users/rmanaloto/.claude/plugins/cache/claude-plugins-official/hookify/ed404106fcd8/.claude-plugin/plugin.json`
- `/Users/rmanaloto/.claude/plugins/cache/claude-plugins-official/hookify/ed404106fcd8/skills/writing-rules/SKILL.md`
- `/Users/rmanaloto/.claude/plugins/cache/claude-plugins-official/hookify/ed404106fcd8/hooks/pretooluse.py`
- `/Users/rmanaloto/.claude/plugins/cache/claude-plugins-official/hookify/ed404106fcd8/core/rule_engine.py`

It can absorb simple bans, not `hook_guard.py`.

### Session Report and Skill Creator

Cached Session Report emits HTML/JSON token/cache/project/subagent/skill analytics, not requirements, lineage or mining, and is not loaded:

- `/Users/rmanaloto/.claude/plugins/cache/claude-plugins-official/session-report/ed404106fcd8/skills/session-report/SKILL.md`

Skill Creator deliberately creates/evaluates proposed skills; it does not discover them across sessions.

### Native continuity, doctor and eval

Current CLI help verifies resume by ID/name/PR, forking, background launch, attach/log/stop/remove/respawn, worktrees, Remote Control/cloud flags and autocompact. Remote Control requires the local process alive; Desktop/Web has clean-tree/SSH/direction limits. Thus the no-cross-device premise in `.claude/skills/handoff/SKILL.md` and `.claude/skills/resume/SKILL.md` is false in 2.1.251, while exceptional-state reconciliation remains useful.

A live `claude doctor` checked install/update/keychain/Remote-Control health (machine not signed in), not project fnox/MCP/currency/PATH contracts.

`claude plugin eval --help` verifies graders, ablation, tool/MCP controls, model/judge selection, budgets, thresholds and JSON/HTML reporting: a direct replacement for plugin/skill eval plumbing.

## Ranked highest-value retirements

1. **Generic notepad plus common-path handoff/resume.** Use enabled PWF and native continuity. Direct surface: 56,541 bytes (44,900 + 11,641), before tests. Keep one exceptional-state reconciliation skill and tracked destination rule.
2. **Manual final report copying.** Use `SubagentStop`/`TeammateIdle`; keep path/brief association and incremental persistence. Prove missing-file and agent-death controls.
3. **Plugin/skill eval runner.** Move to `claude plugin eval`: 18,506 local bytes plus shared-runner share. Reachability becomes doctor/verify; parser fixtures remain unit tests.
4. **Trivial bans/prefilters.** Native permissions/hook `if` shrink guard and invocations without moving shell-sensitive logic to Hookify.
5. **Listing estimator after aggregate probe.** Potential 9,350 bytes plus tests; native model-specific data is better, aggregation is the gap.
6. **Path-only doc refs after Markdown-link migration.** Potential 19,474 production + 10,881 test bytes; keep task/skill symbol checks.
7. **Native-only orchestration control arm.** Watchdog/projector/lane/reap: 179,014 production + ~224,592 focused-test bytes. Largest future retirement, but crash/wedge/approval/restart/CAS/rework controls must pass.
8. **Decompose the verification surface.** 297,946 bytes: move tool-native checks, strip executable incident narrative, delete non-falsifiable assertions. Do not rewrite policy into another engine without deleting policy.
9. **Usage-audit automation mining.** No replacement, but 81,931 bytes. If it has not caused accepted automation recently, deliberate capability deletion may match operator priorities.

## Do not retire on current evidence

- Requirement/evidence closure: plans do not independently audit their producer.
- Semantic command parsing: permissions/Hookify lack repo shell/workflow semantics.
- Doc refs: no deterministic replacement covers inline paths plus tasks/skills.
- Markdown load budgets: context visibility is diagnostic, not a CI gate.
- Project doctor: native doctor is generic install/config health.
- Memory-index curation: native memory creates the cutoff/reference risks.
- Verification contracts: lifecycle hooks trigger gates but do not define invariants.

## Practical retirement boundary

A low-risk first cut leaves native continuity for ordinary sessions, PWF as the only generic notes protocol, one short exceptional-handoff skill, a lifecycle hook plus short report destination rule, native plugin eval, native permissions for unconditional bans, and the semantic guard/ledger/verifier/doc refs/budgets/memory checker/narrowed doctor unchanged.

That removes duplicated Claude-maintenance work without pretending similarly named tools implement repo-specific correctness contracts.

## GitHub repos touched

> Added by the architect at persistence time, not by the reporting lane. The
> lane did not emit this section; the entries below are the repositories its
> cited evidence demonstrably came from.

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the tree under audit.
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — the plugin whose scripts, hooks and templates the lane read.
