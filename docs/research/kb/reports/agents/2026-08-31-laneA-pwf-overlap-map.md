# Planning-with-files overlap map

Decision report for the dotfiles session, planning, and workflow machinery versus planning-with-files 3.12.0.

## Executive decision

The plugin can replace this repository's basic same-clone working-memory layer: a task plan, accumulated findings, progress log, lifecycle injection, active-plan selection, and a syntactic phase-completion reminder. It does not replace the capabilities that make most of the custom stack large: Git and GitHub state reconciliation, checked handoff citations, tracked cross-surface transfer, memory-index safety, native transcript analysis, requirement and promise coverage, mutation receipts, or command-audit classification.

The evidence-backed deletion boundary is therefore:

1. High confidence: consolidate .agent/notepad.md into the plugin's findings.md and progress.md, then delete the dedicated notepad rule and its evidence mirror after rewiring any remaining reader.
2. Medium confidence, if the operator deliberately accepts the listed losses: delete the same-clone session-handoff/session-resume layer and its two small Python helpers. This is the custom layer closest to the plugin, but the overlap is only partial.
3. Keep the cross-surface handoff pair, memory index, command audit, and session-review/ledger/store/gate stack unless the operator is explicitly abandoning their unique outcomes. The plugin has no executable substitute for them.

There is no evidence-based basis for deleting all seven named Python modules merely because the plugin calls itself session-aware. Its normal SessionStart path explicitly avoids host transcript history and only injects planning files (PWF/hooks/claude-hook.sh:60-83; PWF/scripts/session-catchup.py:669-681).

## Method and verdict standard

OUR means /Users/rmanaloto/dev/github/ray-manaloto/dotfiles. PWF means /Users/rmanaloto/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0. Sizes are physical wc line and byte counts measured from those trees. For a stanza or fragment, the size is only the cited span.

Only shipped executable sources were treated as capability: PWF/scripts, PWF/hooks, PWF/commands, PWF/templates, and PWF/skills/planning-with-files/SKILL.md. README claims were not used. DUPLICATED means the plugin executes substantially the same outcome; PARTIAL means it covers only a narrower part; UNIQUE means no executable equivalent was found. Generic repository gates that happen to run during handoff are not separately inventoried unless they exist specifically to implement session state.

## Inventory and overlap verdicts

### Skills and protocol

| Our machinery | Size | What it actually does | Verdict | Plugin feature that covers it |
|---|---:|---|---|---|
| .claude/skills/session-handoff/SKILL.md | 297 lines / 16,899 B | Builds a same-clone handoff with repo/runtime state, planning-path inventory, doc and memory sync, agent-report coverage, gates, citation checks, and a resume prompt (OUR/.claude/skills/session-handoff/SKILL.md:39-90,92-199,201-276). | PARTIAL | Project planning files and lifecycle injection preserve basic plan/findings/progress context (PWF/skills/planning-with-files/SKILL.md:65-126; PWF/hooks/claude-hook.sh:60-83). They do not perform the other checks. |
| .claude/skills/session-resume/SKILL.md | 114 lines / 4,291 B | Selects the newest local handoff, compares live Git/PR state, verifies handoff citations, and reports discrepancies, next work, owed items, and traps before mutation (OUR/.claude/skills/session-resume/SKILL.md:22-45,47-99). | PARTIAL | SessionStart and prompt hooks resolve and inject an active plan (PWF/scripts/resolve-plan-dir.sh:207-267; PWF/scripts/inject-plan.sh:1174-1229), but do not reconcile Git/PR state or validate citations. |
| .claude/skills/session-review/SKILL.md | 244 lines / 14,349 B | Runs transcript and narrative review, builds normalized requirement coverage and goal history, and requires prevention receipts before declaring a missed requirement closed (OUR/.claude/skills/session-review/SKILL.md:24-50,52-106,108-190,207-237). | UNIQUE | Plugin ledgers record explicit phase events and summarize counts (PWF/scripts/ledger-append.sh:215-336; PWF/scripts/ledger-summary.sh:1-39), not native transcript requirements, promises, omissions, or prevention evidence. |
| .claude/skills/handoff/SKILL.md | 83 lines / 4,368 B | Creates a tracked cross-surface handoff, validates it, commits it with repository state, and pushes the branch (OUR/.claude/skills/handoff/SKILL.md:8-19,23-57). | UNIQUE | Plugin planning artifacts are local ignored state in this repo; no plugin command commits or pushes them. |
| .claude/skills/resume/SKILL.md | 74 lines / 2,998 B | Fetches/checks out/pulls a handoff branch, reads tracked context, restates decisions, runs gates, and continues on another surface (OUR/.claude/skills/resume/SKILL.md:17-68). | UNIQUE | Active-plan injection is same-working-tree continuity only (PWF/scripts/resolve-plan-dir.sh:207-267). |
| docs/handoffs/README.md | 86 lines / 3,121 B | Defines the tracked branch-plus-handoff protocol and distinguishes it from gitignored same-machine session handoffs (OUR/docs/handoffs/README.md:1-13,15-42,44-80). | UNIQUE | The plugin creates root or .planning local files and a local active-plan selector (PWF/scripts/init-session.sh:310-370); it has no Git transport. |

### Python implementation

| Our machinery | Size | What it actually does | Verdict | Plugin feature that covers it |
|---|---:|---|---|---|
| python/src/dotfiles_setup/handoff_check.py | 201 lines / 6,791 B | Finds the newest local handoff and validates every repo path, line range, and cited mise task against the live tree (OUR/python/src/dotfiles_setup/handoff_check.py:51-101,104-152,172-201). | UNIQUE | plan-doctor checks plugin installation and injection health, not handoff citations (PWF/scripts/plan-doctor.sh:1-20,49-100). |
| python/src/dotfiles_setup/memory_index.py | 664 lines / 27,026 B | Enforces MEMORY.md line/byte budgets and detects facts that would be lost by index-only compaction (OUR/python/src/dotfiles_setup/memory_index.py:2-45,61-74,230-317,390-455). | UNIQUE | Plugin findings are working notes; no plugin script audits Claude memory budgets or fact retention. |
| python/src/dotfiles_setup/session_gate.py | 510 lines / 18,605 B | Registers prevention runners, stores run receipts, validates command/GitHub evidence and mutation sentinels, and finalizes only with live checks (OUR/python/src/dotfiles_setup/session_gate.py:22-88,110-153,173-323,344-456). | UNIQUE | Plugin Stop gating checks phase syntax and whether its own ledger advanced (PWF/scripts/check-complete.sh:69-108,134-215,247-252); it does not execute or validate prevention runners. |
| python/src/dotfiles_setup/session_ledger.py | 4,336 lines / 151,127 B | Models provider events, authority and coverage; discovers Claude/Codex transcripts; derives requirement coverage, semantic dispositions, iteration state, and bounded reports (OUR/python/src/dotfiles_setup/session_ledger.py:75-200,1305-1511,3446-3506,3751-3855,4022-4186,4215-4336). | UNIQUE | Plugin ledgers accept user/agent-supplied phase event names and summarize them (PWF/scripts/ledger-append.sh:215-336; PWF/scripts/ledger-summary.sh:1-39). They do not parse host transcripts or infer requirement coverage. |
| python/src/dotfiles_setup/session_review.py | 965 lines / 36,443 B | Mines transcript facts plus bounded notepad, handoff, and goal-history narratives, then builds review and requirements artifacts (OUR/python/src/dotfiles_setup/session_review.py:2-49,71-179,265-374,694-761,788-965). | UNIQUE | Explicit session-catchup replay emits bounded excerpts only (PWF/scripts/session-catchup.py:184-203,495-512,684-783); it does not build review artifacts or coverage. |
| python/src/dotfiles_setup/session_state.py | 303 lines / 9,553 B | Produces a bounded branch, dirty-tree, commit, and optionally fail-closed GitHub PR snapshot (OUR/python/src/dotfiles_setup/session_state.py:37-141,144-229,232-303). | UNIQUE | Plugin status is plan and phase state, not repository or PR state (PWF/commands/status.md:5-13,39-45; PWF/scripts/phase-status.sh:75-201). |
| python/src/dotfiles_setup/session_store.py | 455 lines / 16,451 B | Implements a content-addressed single-writer store with immutable objects, manifests, fingerprints, reuse/rebuild decisions, and atomic publication (OUR/python/src/dotfiles_setup/session_store.py:132-301,316-455). | UNIQUE | Plugin writes Markdown planning artifacts and append-only per-agent event logs; it has no content-addressed cache or manifest validation (PWF/scripts/ledger-append.sh:14-33,215-336). |
| python/src/dotfiles_setup/command_audit.py | 814 lines / 31,139 B | Pairs native Claude tool uses/results, classifies commands, groups repetitions, and writes a SessionEnd command-audit report (OUR/python/src/dotfiles_setup/command_audit.py:2-61,480-578). | UNIQUE | Plugin lifecycle code does not parse or classify commands; PostToolUse only emits planning reminders (PWF/hooks/claude-hook.sh:93-127). |

### Mise task surface

| Our machinery | Size | What it actually does | Verdict | Plugin feature that covers it |
|---|---:|---|---|---|
| tasks.command-audit | 12 lines / 717 B | Thin task invoking the command-audit CLI with optional limit/output (OUR/mise.toml:700-711). | UNIQUE | None; see command_audit.py row. |
| tasks.memory-index | 11 lines / 705 B | Thin task invoking the memory-index audit (OUR/mise.toml:712-722). | UNIQUE | None; see memory_index.py row. |
| tasks.session-state | 5 lines / 249 B | Invokes the Git/PR session snapshot (OUR/mise.toml:864-868). | UNIQUE | None; plugin status is plan-only. |
| tasks.handoff-check | 5 lines / 264 B | Invokes live handoff citation validation (OUR/mise.toml:869-873). | UNIQUE | None; plan-doctor has a different contract. |
| tasks.session-review | 17 lines / 1,003 B | Selects review lanes and emits the session-review artifact (OUR/mise.toml:1383-1399). | UNIQUE | None; plugin catchup does not review requirements. |
| tasks.session-requirements | 11 lines / 785 B | Builds the requirements-coverage artifact (OUR/mise.toml:1400-1410). | UNIQUE | None. |
| tasks.session-review-gate | 4 lines / 193 B | Finalizes prevention evidence for a session review (OUR/mise.toml:1411-1414). | UNIQUE | Plugin phase Stop gate is not evidence validation. |
| tasks.session-review-mutation-credential-launcher | 4 lines / 289 B | Runs a named mutation credential launcher for review evidence (OUR/mise.toml:1415-1418). | UNIQUE | None. |
| tasks.session-review-mutation-git-hook-contamination | 4 lines / 298 B | Runs a named Git-hook contamination mutation check (OUR/mise.toml:1419-1422). | UNIQUE | None. |
| tasks.session-review-focused-gate | 4 lines / 211 B | Runs the bounded focused review gate (OUR/mise.toml:1427-1430). | UNIQUE | None. |

### Hooks and policy

| Our machinery | Size | What it actually does | Verdict | Plugin feature that covers it |
|---|---:|---|---|---|
| settings PreToolUse guard | 11 lines / 302 B | Runs the repository tool guard before Bash, Write, Edit, and NotebookEdit (OUR/.claude/settings.json:40-50). | UNIQUE | Plugin also uses PreToolUse but only to inject/remind about plans (PWF/hooks/hooks.json:34-67; PWF/hooks/claude-hook.sh:93-127). |
| settings PreToolUse Graphify search | 10 lines / 257 B | Enforces Graphify-first behavior before broad Search calls (OUR/.claude/settings.json:51-60). | UNIQUE | No plugin graph or research gate. |
| settings PreToolUse Graphify read | 10 lines / 254 B | Enforces Graphify-first behavior before broad Read calls (OUR/.claude/settings.json:61-70). | UNIQUE | No plugin graph or research gate. |
| settings SessionStart setup | 12 lines / 478 B | Runs web setup, tool-currency check, and doctor at startup (OUR/.claude/settings.json:72-83). | UNIQUE | Plugin also has SessionStart but injects planning context (PWF/hooks/hooks.json:4-32; PWF/hooks/claude-hook.sh:60-83). Shared event does not mean shared behavior. |
| settings SessionEnd command audit | 11 lines / 299 B | Refreshes .agent/command-audit.md when the session actually ends (OUR/.claude/settings.json:84-94). | UNIQUE | Plugin has a Stop hook, not SessionEnd command classification (PWF/hooks/hooks.json:88-98). |
| .claude/rules/notepad-enforcement.md | 44 lines / 1,867 B | Makes .agent/notepad.md the immediate as-you-go findings sink and requires verification before advancing (OUR/.claude/rules/notepad-enforcement.md:1-38). | DUPLICATED | findings.md stores discoveries and progress.md stores actions; the skill requires updates after roughly two view operations and after phase changes/errors (PWF/skills/planning-with-files/SKILL.md:96-126). |
| .claude/rules/agent-artifact-conventions.md | 103 lines / 5,745 B | Defines the .agent taxonomy, tracked exceptions, prohibition on ad-hoc artifacts, and skill-to-mise-to-Python layering (OUR/.claude/rules/agent-artifact-conventions.md:3-35,61-85). | PARTIAL | Plugin defines its own root or .planning plan taxonomy (PWF/skills/planning-with-files/SKILL.md:65-103), but not this repo's durable report, handoff, or receipt conventions. |
| .claude/rules/agent-report-persistence.md | 75 lines / 4,029 B | Requires findings-bearing subagent reports to be persisted verbatim and referenced from notepad/handoff coverage (OUR/.claude/rules/agent-report-persistence.md:1-7,20-36,45-59). | UNIQUE | Plugin records plan events, not verbatim subagent reports. |
| .claude/rules/goal-history.md | 29 lines / 1,619 B | Requires append-only tracked goal iterations and handoff integration from a fixed origin/main baseline (OUR/.claude/rules/goal-history.md:1-29). | UNIQUE | Plugin phase ledgers are local planning events and do not enforce tracked goal history or Git baseline. |
| .claude/rules/research-repo-enumeration.md | 69 lines / 2,602 B | Requires every research artifact to enumerate repositories consulted and makes reviewers enforce it (OUR/.claude/rules/research-repo-enumeration.md:1-6,17-60). | UNIQUE | No plugin equivalent. |
| session fragment of .claude/rules/mise-tasks-only.md | 17 lines / 1,357 B | Defines the command-audit task and SessionEnd transcript-mining contract (OUR/.claude/rules/mise-tasks-only.md:70-86). | UNIQUE | No plugin command classifier or SessionEnd audit. |
| session-state fragment of .claude/rules/do-not.md | 2 lines / 137 B | Prevents bulk staging of volatile .agent/state cache data (OUR/.claude/rules/do-not.md:23-24). | UNIQUE | Independent repository safety rule. |
| .gitignore planning-with-files block | 11 lines / 522 B | Ignores task_plan.md, findings.md, progress.md, .active_plan, and .planning root-anchored (OUR/.gitignore:89-99). | DUPLICATED | This is required local integration for the plugin artifacts created by init-session (PWF/scripts/init-session.sh:310-370), not a competing custom tracker. Keep it while the plugin is used. |
| docs/rules-evidence mirrors for artifact, report, notepad rules | 175 lines / 8,332 B | Stores evidence copies for the three named policy files; these are supporting artifacts, not runtime behavior (OUR/docs/rules-evidence/agent-artifact-conventions.md:1-74; OUR/docs/rules-evidence/agent-report-persistence.md:1-49; OUR/docs/rules-evidence/notepad-enforcement.md:1-52). | PARTIAL | Only the notepad evidence mirror becomes redundant with notepad retirement; the other two document unique policy. |

### Dedicated tests and fixtures

Tests are included because deleting a maintained implementation without its dedicated regression surface would understate the maintenance reduction.

| Our machinery | Size | What it actually does | Verdict | Plugin feature that covers it |
|---|---:|---|---|---|
| tests/test_handoff_check.py | 349 lines / 10,293 B | Regression tests for the scoped handoff citation checker (OUR/tests/test_handoff_check.py:1-17). | UNIQUE | No corresponding plugin behavior. |
| tests/test_session_state.py | 353 lines / 10,558 B | Regression tests for the read-only Git/PR snapshot (OUR/tests/test_session_state.py:1-16). | UNIQUE | No corresponding plugin behavior. |
| tests/test_memory_index.py | 572 lines / 22,969 B | Covers discovery, parsing, distinctive-fact retention, inbound references, budgets, rendering, and exit status (OUR/tests/test_memory_index.py:1-20). | UNIQUE | No corresponding plugin behavior. |
| tests/test_session_review.py | 1,294 lines / 44,416 B | Pins the two review lanes' noise rejection and disjointness (OUR/tests/test_session_review.py:1-15). | UNIQUE | No corresponding plugin behavior. |
| tests/test_session_ledger.py | 2,915 lines / 103,135 B | Tests the lossless requirement/promise ledger against provider fixtures (OUR/tests/test_session_ledger.py:1-23). | UNIQUE | No corresponding plugin behavior. |
| tests/test_session_store.py | 314 lines / 10,450 B | Controls the content-addressed session-review store (OUR/tests/test_session_store.py:1-22). | UNIQUE | No corresponding plugin behavior. |
| tests/test_session_gate.py | 359 lines / 12,380 B | Mutation/control tests for the trusted receipt runner (OUR/tests/test_session_gate.py:1-23). | UNIQUE | No corresponding plugin behavior. |
| tests/test_command_audit.py | 642 lines / 24,153 B | Covers discovery, defensive parsing, call/result pairing, classification, grouping, rendering, and SessionEnd output (OUR/tests/test_command_audit.py:1-23). | UNIQUE | No corresponding plugin behavior. |
| tests/fixtures/session_review/* | 21 lines / 8,408 B | Claude/Codex transcript fixtures imported by the ledger tests (OUR/tests/test_session_ledger.py:15-23). | UNIQUE | Plugin ships no equivalent requirement-review test corpus. |

The tests' behavior claims follow the implementation contracts cited in the corresponding module rows; they are not counted as plugin capability merely because the plugin has its own unrelated tests.

## CONFLICTS

### 1. Two working-memory sinks create drift and double work

The repo requires discoveries to be written immediately to .agent/notepad.md (OUR/.claude/rules/notepad-enforcement.md:3-30). The plugin separately instructs the agent to put discoveries in findings.md, actions/results in progress.md, and to update after roughly two view operations (PWF/skills/planning-with-files/SKILL.md:96-126). An agent obeying both must duplicate each fact or choose one source. Duplicating creates divergent copies; choosing one violates the other instruction. session_review.py also treats the repo notepad as a narrative input (OUR/python/src/dotfiles_setup/session_review.py:320-374,694-750), so moving to plugin files without changing that reader silently removes evidence from review.

### 2. The artifact-location rules contradict the plugin's default layout

The repo says local agent artifacts belong under .agent and prohibits ad-hoc locations (OUR/.claude/rules/agent-artifact-conventions.md:3-24,61-73). The plugin creates task_plan.md, findings.md, and progress.md at the root or under .planning/<slug> (PWF/skills/planning-with-files/SKILL.md:65-85; PWF/scripts/init-session.sh:310-370). The .gitignore exception proves this repo intentionally permits those five plugin artifacts (OUR/.gitignore:89-99), but the prose rules do not identify that exception. Agents can therefore receive contradictory placement instructions even when the filesystem setup is correct.

### 3. Both stacks claim the authoritative next task

The repo's resume skill explicitly says planning-file content does not establish the next task and instead derives next/owed/traps from the handoff plus live discrepancies (OUR/.claude/skills/session-resume/SKILL.md:42-45,67-99). The plugin treats the plan's Current Phase and Next Step as the compact recovery state (PWF/skills/planning-with-files/SKILL.md:184-195; PWF/templates/task_plan.md:11-20). If a handoff and task_plan.md drift, the same startup can tell the agent two different next actions.

### 4. A process-global active-plan selector can cross-wire concurrent sessions

init-session overwrites a single .active_plan selector when a slug plan is created (PWF/scripts/init-session.sh:350-374), and resolution follows that selector unless an explicit plan root/session attachment wins (PWF/scripts/resolve-plan-dir.sh:218-267; PWF/scripts/inject-plan.sh:224-256). The repo handoff only inventories plugin paths and deliberately does not copy their contents into the handoff (OUR/.claude/skills/session-handoff/SKILL.md:77-90). Two sessions in one clone can therefore resume from different custom handoffs while both receive the most recently selected plugin plan.

The plugin has a .planning/sessions attachment reader (PWF/scripts/inject-plan.sh:272-390), but no creator of .attached sentinels was found anywhere in the shipped scripts, commands, hooks, templates, or skill. An external adapter may create them; that cannot be determined from this plugin tree. Without such an adapter, the isolation mechanism is not a usable automatic replacement.

### 5. Overlapping hook events compound context and make ordering observable

The repo already runs three PreToolUse commands and one SessionStart command (OUR/.claude/settings.json:40-83). The plugin registers SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PreCompact, and Stop hooks (PWF/hooks/hooks.json:4-99) and injects plan excerpts on several of those fires (PWF/hooks/claude-hook.sh:60-127; PWF/scripts/inject-plan.sh:1003-1026,1174-1229). These do not duplicate the repo guards, but they compete for latency and context. Hook ordering is not specified in either inspected tree, so the exact order of guard diagnostics, Graphify directions, doctor output, and plan instructions cannot be determined.

### 6. Plugin Stop gating can delay the repo's SessionEnd audit

In gated mode, the plugin can block Stop while a phase remains in progress and its ledger conditions allow a block (PWF/scripts/check-complete.sh:134-215,247-252). The repo command audit runs only at SessionEnd (OUR/.claude/settings.json:84-94; OUR/.claude/rules/mise-tasks-only.md:78-83). A blocked Stop is not SessionEnd, so command-audit refresh can be delayed until the agent finally terminates. This is lifecycle interference, not equivalent enforcement.

### 7. Plugin completion can be mistaken for repository completion

check-complete counts Markdown phase markers and, in gated mode, checks its own event ledger (PWF/scripts/check-complete.sh:69-108,134-215). The repo's session gate validates named runner results, GitHub receipts, mutation sentinels, and live final state (OUR/python/src/dotfiles_setup/session_gate.py:173-323,344-456). Calling both mechanisms a gate risks an agent treating a syntactically complete plan as proof that tests, remote state, or prevention evidence passed. The plugin does not execute acceptance commands found in Markdown.

### 8. The two ledgers can double-count one action without sharing authority

Plugin ledger events are explicitly appended per agent and summarized as event/phase counts (PWF/scripts/ledger-append.sh:14-33,215-336; PWF/scripts/ledger-summary.sh:1-39). The repo ledger derives authoritative events and requirement coverage from native Claude/Codex transcripts (OUR/python/src/dotfiles_setup/session_ledger.py:1305-1511,3446-3506,3751-3855). Recording an action in progress.md, a plugin ledger event, .agent/notepad.md, and a native transcript creates four representations. The repo review can see the transcript and selected narrative files but does not ingest plugin ledger authority, so counts and completion labels are not interchangeable.

### 9. Normal plan maintenance can invalidate optional attestation

V3 initialization writes .nonce/.mode metadata and attests the initial plan template (PWF/scripts/init-session.sh:151-183). The skill then requires the plan to be updated as work advances (PWF/skills/planning-with-files/SKILL.md:117-126). Attestation validates a content hash (PWF/scripts/attest-plan.sh:40-48,74-108,147-202), and injection can refuse or warn on a mismatched attestation (PWF/scripts/inject-plan.sh:964-1038). Unless the agent re-attests after legitimate edits, the plugin can suppress the very plan the repo handoff expects to coexist with it.

### 10. Plugin root commands and active-plan hooks do not always inspect the same files

The status command reads root task_plan.md/findings.md/progress.md directly (PWF/commands/status.md:5-13,39-45). The hooks resolve .active_plan and slug directories (PWF/scripts/resolve-plan-dir.sh:207-267). In a slug workflow, /status can report absent or stale root files while hooks inject the active slug plan. That ambiguity becomes worse when a custom handoff inventories all planning paths but names a separate authoritative next action.

### 11. Automatic catchup is much narrower than its name suggests

The Claude hook always invokes the root session-catchup.py with --no-history (PWF/hooks/claude-hook.sh:16-20,68-71). That mode returns before opening a host session store (PWF/scripts/session-catchup.py:669-681). Metadata and bounded replay are explicit-only modes (PWF/scripts/session-catchup.py:495-512,684-783). It therefore cannot replace automatic native-transcript review, and presenting both as session recovery would create a false sense that custom evidence was captured.

There is also shipped-source drift: the hook-selected root script is 787 lines, while PWF/skills/planning-with-files/scripts/session-catchup.py is 983 lines and contains additional runtime routing (PWF/skills/planning-with-files/scripts/session-catchup.py:393-395). Which copy a manual command reaches depends on the path used. The Claude lifecycle route is determinate: it uses the shorter root copy.

## DELETE CANDIDATES

Counts below are direct whole-file or whole-stanza removals. Discontiguous imports, CLI dispatch, documentation references, and generated index edits are called out but excluded rather than estimated.

### 1. High confidence: retire the dedicated .agent/notepad policy

Direct removal:

| Item | Lines | Bytes |
|---|---:|---:|
| .claude/rules/notepad-enforcement.md | 44 | 1,867 |
| docs/rules-evidence/notepad-enforcement.md | 52 | 2,221 |
| Total | 96 | 4,088 |

Why: findings.md and progress.md cover the intended working-memory behavior, and the plugin has lifecycle reminders to keep them current (PWF/skills/planning-with-files/SKILL.md:96-126; PWF/hooks/claude-hook.sh:93-127).

Lost or required migration: the exact .agent/notepad.md convention and its verification wording disappear. Before deleting, either teach session_review.py to read the resolved plugin findings/progress files or retire that narrative lane; today it explicitly searches repo narrative paths (OUR/python/src/dotfiles_setup/session_review.py:320-374). References in agent-artifact-conventions.md and agent-report-persistence.md also need surgical edits; those embedded lines are not counted.

### 2. Medium confidence: retire the same-clone handoff/resume layer

Direct removal:

| Item | Lines | Bytes |
|---|---:|---:|
| .claude/skills/session-handoff/SKILL.md | 297 | 16,899 |
| .claude/skills/session-resume/SKILL.md | 114 | 4,291 |
| python/src/dotfiles_setup/handoff_check.py | 201 | 6,791 |
| python/src/dotfiles_setup/session_state.py | 303 | 9,553 |
| mise tasks session-state + handoff-check | 10 | 513 |
| tests/test_handoff_check.py + tests/test_session_state.py | 702 | 20,851 |
| Total | 1,627 | 58,898 |

Why only medium: the plugin replaces persistent plan/findings/progress injection, which is the operator's desired core. It does not replace the custom layer's Git/PR snapshot, citation validation, documentation/memory synchronization, agent-report coverage, exact next/owed/traps contract, or captured gate evidence (OUR/.claude/skills/session-handoff/SKILL.md:39-90,92-246; OUR/.claude/skills/session-resume/SKILL.md:47-99). If those extras are precisely the behavior the operator no longer wants, their loss is intentional and this candidate becomes high confidence.

Additional cleanup not counted: imports, parser registration, and dispatch in main.py (OUR/python/src/dotfiles_setup/main.py:70,116,1145-1168,1542,2152-2159), skill indexes, and references from artifact policies.

### 3. Low confidence: retire the native command-audit stack

Direct removal:

| Item | Lines | Bytes |
|---|---:|---:|
| python/src/dotfiles_setup/command_audit.py | 814 | 31,139 |
| tests/test_command_audit.py | 642 | 24,153 |
| mise task command-audit | 12 | 717 |
| settings SessionEnd hook | 11 | 299 |
| Total | 1,479 | 56,308 |

Lost capability: automatic pairing and classification of native tool commands and the end-of-session repetition report (OUR/python/src/dotfiles_setup/command_audit.py:2-61,480-578). The plugin has no replacement. The only rationale for deletion is an explicit decision to stop auditing command behavior, not overlap.

Additional cleanup not counted: the 17-line command-audit fragment in mise-tasks-only.md, CLI wiring, and references to .agent/command-audit.md.

### 4. Low confidence: retire the memory-index stack

Direct removal:

| Item | Lines | Bytes |
|---|---:|---:|
| python/src/dotfiles_setup/memory_index.py | 664 | 27,026 |
| tests/test_memory_index.py | 572 | 22,969 |
| mise task memory-index | 11 | 705 |
| Total | 1,247 | 50,700 |

Lost capability: measured Claude-memory budget enforcement and detection of facts lost by index-only compaction (OUR/python/src/dotfiles_setup/memory_index.py:2-45,230-317,390-455). Plugin findings persist task notes but do not audit the Claude memory system.

### 5. Very low confidence: retire the cross-surface handoff protocol

Direct removal:

| Item | Lines | Bytes |
|---|---:|---:|
| .claude/skills/handoff/SKILL.md | 83 | 4,368 |
| .claude/skills/resume/SKILL.md | 74 | 2,998 |
| docs/handoffs/README.md | 86 | 3,121 |
| Total | 243 | 10,487 |

Lost capability: tracked, committed, pushed transfer between clones/surfaces (OUR/docs/handoffs/README.md:1-13,15-42). Because plugin artifacts are ignored here (OUR/.gitignore:95-99), deleting this is a deliberate abandonment of cross-device continuity. Existing handoff data under docs/handoffs should not be bulk-deleted as though it were implementation.

### 6. Very low confidence: retire the transcript review/ledger/store/gate stack

Direct removal:

| Item group | Lines | Bytes |
|---|---:|---:|
| .claude/skills/session-review/SKILL.md | 244 | 14,349 |
| session_review.py + session_ledger.py + session_store.py + session_gate.py | 6,266 | 222,626 |
| Six session-review mise task stanzas | 44 | 2,779 |
| Four dedicated test files | 4,882 | 170,381 |
| tests/fixtures/session_review/* | 21 | 8,408 |
| Total | 11,457 | 418,543 |

Lost capability: the entire provider-aware transcript evidence model, requirements and promises coverage, content-addressed review cache, goal-iteration accounting, and prevention/mutation receipts (OUR/python/src/dotfiles_setup/session_ledger.py:75-200,1305-1511,3446-3506,3751-3855; OUR/python/src/dotfiles_setup/session_gate.py:173-456). Plugin phase ledgers are voluntary local event logs, not a substitute. This candidate belongs on a minimization list only if the operator wants the outcome gone, not because of duplication.

## KEEP

### Keep cross-surface handoff/resume

The plugin's planning state is root-ignored in this repo (OUR/.gitignore:95-99), while the custom protocol deliberately commits and pushes a self-sufficient handoff (OUR/.claude/skills/handoff/SKILL.md:29-57; OUR/docs/handoffs/README.md:10-13). The plugin cannot carry state into another clone by itself.

### Keep session review, ledger, store, and gate

These modules recover evidence from native Claude/Codex transcripts, assign authority and coverage, cache normalized facts, and require falsifiable prevention receipts (OUR/python/src/dotfiles_setup/session_ledger.py:1305-1511,3446-3506,3751-3855; OUR/python/src/dotfiles_setup/session_store.py:132-360; OUR/python/src/dotfiles_setup/session_gate.py:173-456). The plugin's ledger records only explicitly appended planning events and its Stop gate checks plan syntax/ledger movement (PWF/scripts/ledger-append.sh:215-336; PWF/scripts/check-complete.sh:69-108,134-215).

### Keep memory-index

It protects a separate persistent-memory format with measured size constraints and fact-retention analysis (OUR/python/src/dotfiles_setup/memory_index.py:2-45,230-317). findings.md is useful working memory but has no budget, backlink, or loss audit.

### Keep command audit unless command analytics are intentionally retired

It consumes the native transcript at SessionEnd and classifies command behavior (OUR/python/src/dotfiles_setup/command_audit.py:2-61,480-578; OUR/.claude/settings.json:84-94). Plugin hooks do not inspect native tool histories.

### Keep the five existing custom hooks

The five command hooks implement guarding, Graphify enforcement, environment health, and command auditing (OUR/.claude/settings.json:40-94). They share lifecycle events with the plugin but not outcomes. Remove or merge them only on their own merits; none is duplicated by planning-file injection.

### Keep unique policy, but reconcile its wording

agent-report-persistence, goal-history, research-repo-enumeration, and the durable portions of agent-artifact-conventions govern evidence the plugin never stores (OUR/.claude/rules/agent-report-persistence.md:1-59; OUR/.claude/rules/goal-history.md:1-29; OUR/.claude/rules/research-repo-enumeration.md:1-60). Keep them, but edit agent-artifact-conventions to explicitly permit the plugin's root/.planning artifacts so agents do not receive contradictory location rules.

## Plugin capability boundary and unresolved facts

- Confirmed automatic behavior: SessionStart/prompt/tool/compact hooks inject selected project planning files and reminders; Stop performs advisory or bounded gated phase checks (PWF/hooks/hooks.json:4-99; PWF/hooks/claude-hook.sh:60-127; PWF/scripts/check-complete.sh:69-252).
- Confirmed non-automatic behavior: lifecycle hooks do not call ledger-append.sh or phase-status.sh. Those are separate explicit writers (PWF/scripts/ledger-append.sh:215-336; PWF/scripts/phase-status.sh:1-23,75-201). Therefore the plugin does not independently observe and persist every agent action.
- Confirmed catchup boundary: the normal Claude hook uses --no-history and returns before host-store access; metadata/replay require an explicit invocation (PWF/hooks/claude-hook.sh:68-71; PWF/scripts/session-catchup.py:495-512,669-681,684-783).
- Unresolved external dependency: inject-plan can consume .planning/sessions/*.attached, but no creator exists in the inspected plugin tree (PWF/scripts/inject-plan.sh:272-390). An adapter outside this tree may supply it.
- Source inconsistency: init-session creates a .nonce file (PWF/scripts/init-session.sh:165-173), while inject-plan assigns NONCE_FILE but its injection delimiter is derived from payload bytes rather than reading that file (PWF/scripts/inject-plan.sh:449-463,927-947). The inspected code does not establish that .nonce protects hook injection.
- Source inconsistency: the skill and doctor mention a pwf-sha injection cache (PWF/skills/planning-with-files/SKILL.md:467-477; PWF/scripts/plan-doctor.sh:1-20), while current inject-plan hashes on each fire and uses a separate pwf-prog regression marker (PWF/scripts/inject-plan.sh:964-975,1134-1156). Do not base a deletion decision on claimed cache behavior.
- Host hook order is unresolved: neither the repo settings nor plugin hook manifest specifies cross-plugin ordering. The existence of overlapping lifecycle hooks is proven, but a deterministic execution order is not.

## Recommended removal sequence

1. Declare the plugin's resolved findings.md/progress.md pair the only live working-memory sink.
2. Rewire or intentionally retire session_review.py's .agent/notepad narrative input.
3. Delete the notepad rule/evidence pair and clean their embedded references.
4. Run the plugin in normal advisory mode through real clear/compact/resume cases before deleting the same-clone handoff pair.
5. If the observed continuity is acceptable and the operator confirms that Git/PR snapshots, citation checks, next/owed/traps, doc/memory sync, and agent-report coverage are unwanted, delete the 1,627-line same-clone stack.
6. Leave cross-surface, memory, command-audit, and transcript-review systems independent; deleting them is a scope decision, not plugin deduplication.

## GitHub repos touched

- https://github.com/ray-manaloto/dotfiles — custom session, workflow, rules, hooks, tasks, tests, and handoff protocol inspected from the caller's working tree.
- https://github.com/OthmanAdi/planning-with-files — plugin 3.12.0 inspected from the installed marketplace cache.
