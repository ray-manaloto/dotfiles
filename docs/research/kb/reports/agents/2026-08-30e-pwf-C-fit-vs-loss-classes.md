# Adoption fit: `planning-with-files` versus dotfiles persistence

## Scope and method

This is a read-only pre-adoption review of plugin version 3.12.0; the version is declared in the executable skill frontmatter (`pwf/skills/planning-with-files/SKILL.md:30-32`). No plugin script was executed and neither source tree was modified. Findings below distinguish a place where an agent *can* write from a mechanism that makes the write happen.

Severity means:

- **BLOCKER** — unmodified adoption contradicts a mandatory repository rule or gate.
- **SERIOUS** — material mismatch with the measured loss class or a competing source of truth.
- **MINOR** — real operational friction with bounded impact.
- **NON-ISSUE** — compatible or useful behavior with no conflict found on this axis.

## Bottom line

**SERIOUS — it is a useful working-memory scaffold, but it does not close either measured loss class by itself.** It offers durable fields for requirements and decisions, but its every-turn hook only *reads and injects* the existing plan; writes still happen when the model follows prose or a reminder (`pwf/hooks/claude-hook.sh:37-46`, `pwf/hooks/claude-hook.sh:100-110`). For delegated work it records a worker-selected summary capped at 200 characters, not the final report (`pwf/scripts/ledger-append.sh:14-29`, `pwf/scripts/ledger-append.sh:270-278`).

**SERIOUS — gated progress is not wired to the production Claude hook path.** The Stop oracle measures only `ledger-*.jsonl`, while PostToolUse tells the model to update `progress.md`/`task_plan.md` and never calls the ledger appender (`pwf/scripts/check-complete.sh:171-215`, `pwf/hooks/claude-hook.sh:93-126`). Gated mode therefore cannot be treated as an unattended persistence guarantee.

**BLOCKER — its default artifact locations directly contradict this repository's artifact contract.** The plugin directs project-root `task_plan.md`, `findings.md`, and `progress.md` (`pwf/skills/planning-with-files/SKILL.md:65-85`) and named-plan `.planning/` directories (`pwf/skills/planning-with-files/SKILL.md:219-225`), while the repo requires working artifacts under gitignored `.agent/` or tracked `docs/` and forbids ad-hoc directories (`.claude/rules/agent-artifact-conventions.md:1-5`, `.claude/rules/agent-artifact-conventions.md:61-69`). This is a blocker to *unmodified runtime use*, not evidence that the plugin has no useful mechanics.

## 1. Capability overlap

| Capability | Plugin | Existing repo | Fit / severity |
|---|---|---|---|
| Running discoveries | `findings.md`; write after any discovery and after every two view/browser/search operations (`pwf/skills/planning-with-files/SKILL.md:98-110`). | `.agent/notepad.md`; append after each significant discovery, never batch at session end (`.claude/rules/notepad-enforcement.md:17-30`). | **Both / SERIOUS duplication.** Two live findings journals create competing “current” records with different paths and slightly different cadence. |
| Requirements and decisions | Templates provide `Requirements`, `Technical Decisions`, `Key Questions`, and `Decisions Made` fields (`pwf/skills/planning-with-files/templates/findings.md:5-23`, `pwf/skills/planning-with-files/templates/task_plan.md:62-75`). | The notepad requires design decisions and next-agent context; handoff requires decisions and open questions to be recoverable (`.claude/rules/notepad-enforcement.md:19-27`, `.claude/skills/session-handoff/SKILL.md:31-37`). | **Both / SERIOUS duplication.** The schemas overlap, but neither location is automatically written when the operator speaks. |
| Phase plan, next action, errors, chronological work | `task_plan.md` owns goal, next step, phases, decisions and errors; `progress.md` owns actions, changed files, validation and errors (`pwf/skills/planning-with-files/templates/task_plan.md:5-25`, `pwf/skills/planning-with-files/templates/task_plan.md:69-89`, `pwf/skills/planning-with-files/templates/progress.md:1-18`, `pwf/skills/planning-with-files/templates/progress.md:28-42`). | `.agent/plans/` owns plans and local handoffs; `.agent/logs/` owns execution logs (`.claude/rules/agent-artifact-conventions.md:13-24`). | **Both / SERIOUS duplication.** The plugin adds a more prescriptive phase schema, but at forbidden root/`.planning` paths. |
| Automatic re-orientation | SessionStart and UserPromptSubmit hooks inject existing plan context; PreCompact reminds the model to flush progress (`pwf/hooks/hooks.json:4-34`, `pwf/hooks/hooks.json:68-81`, `pwf/scripts/inject-plan.sh:993-1000`). | `/session-resume` explicitly reads the newest handoff and reconciles it against current repo/PR state (`.claude/skills/session-resume/SKILL.md:20-60`, `.claude/skills/session-resume/SKILL.md:62-91`). | **Plugin-only mechanic / NON-ISSUE.** Automatic turn/compaction re-injection is genuinely new. The repo's resume path is semantically stronger because it checks live state rather than trusting the artifact. |
| Named parallel task state | Named initialization creates isolated `.planning/YYYY-MM-DD-slug/` plans and `.active_plan` selects one (`pwf/skills/planning-with-files/SKILL.md:219-254`). | The repo defines per-session state and plans under `.agent/`, but no active-plan selector in this convention (`.claude/rules/agent-artifact-conventions.md:13-24`). | **Plugin-only / MINOR benefit, BLOCKER location.** Useful isolation, incompatible namespace. |
| Per-worker machine status | Workers append one JSONL event with event, summary, phase and files; the summary is truncated to 200 characters (`pwf/scripts/ledger-append.sh:14-33`, `pwf/scripts/ledger-append.sh:270-278`). | The repo requires a full findings-bearing report verbatim at receipt and an incremental report during research (`.claude/rules/agent-report-persistence.md:20-36`). | **Different layers / NON-ISSUE as coordination, SERIOUS if treated as report persistence.** A ledger can show that a lane moved; it cannot preserve the lane's evidence. |
| Full delegated-report retention | The autonomous template tells workers to report through ledgers or findings, while the orchestrator owns the plan (`pwf/skills/planning-with-files/templates/task_plan_autonomous.md:5-11`). | Persist verbatim in the same turn before acting; handoff audits every findings-bearing lane's brief and report (`.claude/rules/agent-report-persistence.md:20-36`, `.claude/rules/agent-report-persistence.md:45-59`). | **Repo-only / SERIOUS gap in plugin.** The existing rule is the capability aimed at the actual loss class. |
| Handoff completeness and live reconciliation | Planning files support a five-question reboot from their current contents (`pwf/skills/planning-with-files/templates/progress.md:44-54`). | Handoff first resolves next-task ambiguity, checks that decisions/reports are on disk, then resume checks branch/SHA/PR drift and stale citations (`.claude/skills/session-handoff/SKILL.md:19-37`, `.claude/skills/session-resume/SKILL.md:42-86`). | **Repo-only depth / NON-ISSUE.** The plugin's reboot view is useful but is not a substitute for the existing send/receive protocol. |
| Clone durability and artifact promotion | Plugin planning files are placed in the project directory (`pwf/skills/planning-with-files/SKILL.md:65-85`). | `.agent/` is explicitly same-clone/gitignored; durable artifacts live under `docs/` and verbatim reports are protected from normalizers (`.claude/rules/agent-artifact-conventions.md:13-35`, `.claude/rules/agent-artifact-conventions.md:50-59`). | **Repo-only / SERIOUS.** The repo has the explicit local-versus-clone-durable promotion model needed for audit evidence. |

### Artifact-location control arm

The same read-only check was run against a known-positive and the proposed paths:

```text
git check-ignore -v .agent/notepad.md
# positive: .gitignore:87:.agent/

git check-ignore -v task_plan.md findings.md progress.md .planning/placeholder .active_plan
# zero output
```

The positive is supported by the repo's explicit `.agent/` ignore (`.gitignore:75-87`). The zero therefore means the plugin's root files and `.planning/` state are not currently ignored, not that `git check-ignore` was blind. **SERIOUS:** using those paths would introduce a second artifact convention and visible worktree state until an approved adaptation changes the placement/ignore contract.

Two narrower controls support the “plugin-only” cells above:

```text
rg -n '"(SessionStart|UserPromptSubmit|PreCompact|SessionEnd)"' .claude/settings.json
# positive: SessionStart at line 72; SessionEnd at line 84
# zero: UserPromptSubmit and PreCompact

rg -n 'plans?|handoffs?|state' .claude/rules/agent-artifact-conventions.md
# positive: documented state/plan/handoff paths at lines 17-23 and 33

rg -n 'active.?plan|select.{0,20}plan|switch.{0,20}plan' \
  .claude/rules/agent-artifact-conventions.md
# zero
```

The first control shows that the repo's existing hook file is discoverable and currently wires startup and termination, but not per-prompt or pre-compaction hooks (`.claude/settings.json:72-94`). The second finds the repo's plan namespace before testing the same file for an active-plan selector (`.claude/rules/agent-artifact-conventions.md:13-24`).

## 2. Loss class (a): operator rulings given mid-session

**SERIOUS — representable, but not reliably captured.** A ruling has sensible destinations: a request can become a verifiable requirement (`pwf/skills/planning-with-files/templates/findings.md:5-9`), a resolved choice can enter `Technical Decisions` or `Decisions Made` (`pwf/skills/planning-with-files/templates/findings.md:17-23`, `pwf/skills/planning-with-files/templates/task_plan.md:69-75`), and an answered uncertainty can replace a key question (`pwf/skills/planning-with-files/templates/task_plan.md:62-67`).

The actual write cadence is agent-driven:

1. **Every user turn:** no write. `UserPromptSubmit` calls `emit_context`, which runs the injector and returns `additionalContext`; the dispatcher contains no planning-file write in that path (`pwf/hooks/claude-hook.sh:37-46`, `pwf/hooks/claude-hook.sh:100-104`).
2. **During discovery:** prose tells the model to update `findings.md` after any discovery and applies a two-view/search-action rule (`pwf/skills/planning-with-files/SKILL.md:98-112`). That may catch a ruling the model classifies as a requirement or decision, but “operator ruling received” is not itself a hook trigger.
3. **On phase transition:** the model is told to update phase status, errors, modified files, and `Next Step` after a phase completes (`pwf/skills/planning-with-files/SKILL.md:117-126`). The progress template separately asks for updates after a phase, validation, or error (`pwf/skills/planning-with-files/templates/progress.md:56-58`).
4. **After tool use:** the plugin emits only a reminder to update `progress.md` and, if applicable, phase status (`pwf/hooks/claude-hook.sh:106-110`). A reminder after `Write|Edit|Bash` does not journal the operator message that preceded the tool.
5. **Before compaction:** the hook again says “ensure” that recent actions and phase state have been captured, then exits (`pwf/scripts/inject-plan.sh:993-1000`). It does not perform the flush.
6. **Optional recurring loop:** only after the user invokes `/plan-loop`, the default tick runs every 10 minutes, writes a current-state entry when `progress.md` has not advanced, updates a finished phase, and continues remaining work (`pwf/commands/plan-loop.md:7-25`, `pwf/commands/plan-loop.md:29-37`). That is an opt-in periodic progress write, not a per-operator-message journal.

The existing repo has the same compliance-versus-enforcement weakness during ordinary turns: its stronger prose says to persist design decisions immediately and never batch (`.claude/rules/notepad-enforcement.md:17-30`), while the handoff later requires every decision and open question to be recoverable (`.claude/skills/session-handoff/SKILL.md:31-37`). The plugin adds more frequent reminders and structured fields, but it does **not** add a deterministic operator-instruction journal. On this loss class it is incremental defense-in-depth, not a fix.

**MINOR recovery benefit:** explicit `--replay` can surface some missed instructions from a prior main session. The script finds the last planning-file write, parses later messages, and prints up to the last 100, with each user message clipped to 300 characters (`pwf/scripts/session-catchup.py:698-742`, `pwf/scripts/session-catchup.py:744-783`). This can help repair a gap after the fact, but it is explicit, bounded, truncated, and does not itself update a durable artifact (`pwf/scripts/session-catchup.py:495-512`, `pwf/scripts/session-catchup.py:771-783`). It is recovery assistance rather than prevention.

Negative control arm for the per-prompt write:

```text
sed -n '37,46p;93,111p' hooks/claude-hook.sh | \
  rg -n 'emit_context|emit_system_message|printf'
# positive: context/message emission and JSON stdout

sed -n '37,46p;93,111p' hooks/claude-hook.sh | \
  rg -n '(task_plan|findings|progress).*([>]{1,2}|tee|sed -i)|(operator|user).*(append|write)'
# zero
```

This scopes both arms to the `emit_context` implementation and the `UserPromptSubmit`/PostToolUse dispatcher branches (`pwf/hooks/claude-hook.sh:37-46`, `pwf/hooks/claude-hook.sh:93-111`). The positive proves the selected code exists; the zero corroborates the direct code reading that those branches emit context/reminders rather than append the prompt or a ruling to a planning file.

## 3. Loss class (b): delegated lanes whose reports never reach disk

**SERIOUS — the plugin does not solve this loss class.** It supplies a worker ledger, but the contract is one caller-supplied event and a free-text summary truncated to 200 characters (`pwf/scripts/ledger-append.sh:14-29`, `pwf/scripts/ledger-append.sh:270-278`). The synthesized view retains total entries, phase counts, and only each agent's last event type (`pwf/scripts/ledger-summary.sh:134-161`). That can expose lane activity or stalling; it cannot reconstruct a report, evidence table, commands, or file:line anchors.

The autonomous template is also advisory: workers “should report” through their ledgers or findings (`pwf/skills/planning-with-files/templates/task_plan_autonomous.md:7-11`). No cited hook receives a subagent final response; the plugin hook matchers are lifecycle and ordinary tool events (`pwf/hooks/hooks.json:4-99`). By contrast, the repo requires the full report verbatim in the same turn before its contents are used, tells research agents to write incrementally, and audits brief/report coverage at handoff (`.claude/rules/agent-report-persistence.md:20-44`, `.claude/rules/agent-report-persistence.md:56-65`).

Negative control arm (same scope and command shape):

```text
rg -n -i --glob '*.md' --glob '*.sh' --glob '*.py' \
  'workers?|subagents?|sub-agents?|ledger-[^ ]*agent|agent id' \
  skills/planning-with-files scripts commands hooks
# positive hits: ledger-append.sh, task_plan_autonomous.md, SKILL.md, reference.md

rg -n -i --glob '*.md' --glob '*.sh' --glob '*.py' \
  'persist.{0,30}(agent|worker).{0,30}report|(agent|worker).{0,30}report.{0,30}persist|verbatim.{0,30}(agent|worker).{0,30}report|at receipt' \
  skills/planning-with-files scripts commands hooks
# zero hits
```

The positive arm is grounded by the actual worker-ledger contract (`pwf/scripts/ledger-append.sh:4-29`) and worker coordination template (`pwf/skills/planning-with-files/templates/task_plan_autonomous.md:7-11`). The zero is therefore a meaningful absence of a report-persistence contract in the searched implementation surface. It does not stand alone: the hook and ledger code above independently show what is actually captured.

## 4. Autonomous and gated modes

### `--autonomous`: NON-ISSUE for human decision points; BLOCKER path issue remains

`--autonomous` writes mode/nonce/counter state and auto-attests the plan (`pwf/scripts/init-session.sh:151-183`). At injection time it suppresses per-tool plan recitation but retains turn-level plan context (`pwf/scripts/inject-plan.sh:826-847`); because its `.mode` lacks `gate`, the Stop checker falls back to an advisory report (`pwf/scripts/init-session.sh:168-173`, `pwf/scripts/check-complete.sh:132-140`). It therefore does **not** force work past a human decision point. Its project-root or `.planning/` writes remain subject to the artifact-location blocker already reported (`pwf/scripts/init-session.sh:310-370`, `.claude/rules/agent-artifact-conventions.md:1-5`).

### `--gated`: SERIOUS human-pause mismatch, not a direct authorization bypass

`--gated` writes `autonomous gate` into `.mode` (`pwf/scripts/init-session.sh:165-173`). On Stop, the implementation blocks only when the mode contains `gate`, an `in_progress` phase exists, this is not already a forced continuation, the cap is not reached, and the ledger advanced (`pwf/scripts/check-complete.sh:132-169`, `pwf/scripts/check-complete.sh:171-215`). When those predicates pass it updates `.stop_blocks` and `.gate_last_ledger`, then emits `{"decision":"block"}` telling the model to finish or update the phase (`pwf/scripts/check-complete.sh:241-252`).

The good news is concrete: the gate counts phase markers and ledger lines; it does not execute commands written in Markdown (`pwf/scripts/check-complete.sh:74-96`, `pwf/scripts/check-complete.sh:171-180`, `pwf/scripts/check-complete.sh:217-252`). It also does not remove the repo's PreToolUse chain, which still matches `Bash|AskUserQuestion|Edit|Write|NotebookEdit` (`.claude/settings.json:39-49`). **NON-ISSUE:** neither mode grants permission for a forbidden Bash/edit or turns descriptive plan text into executable work.

The policy mismatch is what the oracle omits. This repo requires the agent to ask before ambiguous, multi-path, irreversible, or outward-facing work and to stop/reconfirm when a chosen path becomes infeasible (`.claude/rules/clarify-before-acting.md:24-66`). The repo explicitly acknowledges that its guard cannot detect the missing-question case (`.claude/rules/clarify-before-acting.md:68-93`). The plugin's gate likewise has no ambiguity, approval, irreversible-action, or waiting-for-human predicate; its plan status vocabulary is only `pending`, `in_progress`, and `complete` (`pwf/skills/planning-with-files/templates/task_plan_autonomous.md:31-40`, `pwf/skills/planning-with-files/templates/task_plan_autonomous.md:93-98`). A correct human pause can therefore meet every gate predicate and receive at least one forced continuation unless the agent first moves the phase out of `in_progress`, reaches the cap, or leaves the ledger stalled (`pwf/scripts/check-complete.sh:164-215`). **SERIOUS:** gated mode does not waive the clarification requirement, but its completion oracle is unaware of it and can oppose the safe stopping state.

Negative control arm for that omission:

```text
rg -n 'in_progress|stop_hook_active|PWF_GATE_CAP|ledger' \
  scripts/check-complete.sh scripts/gate-stop.sh
# positive: all implemented gate predicates

rg -n -i 'AskUserQuestion|ambigu|irrevers|human|approval|await|pause|blocked' \
  scripts/check-complete.sh scripts/gate-stop.sh
# zero
```

The first arm is grounded in the executable decision path (`pwf/scripts/check-complete.sh:132-215`); the zero is therefore a real absence from the gate implementation, not a search against the wrong files.

### Gated progress signal: SERIOUS unwired path

The gate's stall test counts lines only in `ledger-*.jsonl` (`pwf/scripts/check-complete.sh:171-215`). The ledger writer is a separate explicitly invoked script (`pwf/scripts/ledger-append.sh:14-33`), while Claude PostToolUse only reminds the model to update `progress.md` and phase status (`pwf/hooks/claude-hook.sh:93-110`). Consequently, the first eligible Stop can block with a zero-line ledger; if the model then makes ordinary progress only in the two files named by the hook, the next Stop sees the unchanged zero ledger and allows stopping as “no progress” (`pwf/scripts/check-complete.sh:188-215`). **SERIOUS:** `--gated` does not continuously enforce completion on the production path unless some separate workflow appends ledger events.

Same-shape production-wiring control:

```text
rg -n 'inject-plan|session-catchup|gate-stop' hooks/claude-hook.sh
# positive: all three sibling runtime scripts are invoked

rg -n 'ledger-append' hooks/claude-hook.sh
# zero
```

The positive calls are in the dispatcher (`pwf/hooks/claude-hook.sh:16-20`, `pwf/hooks/claude-hook.sh:37-83`, `pwf/hooks/claude-hook.sh:112-126`); the negative arm tests the same production hook file for the ledger writer the Stop oracle depends on.

## 5. `session-catchup.py`

For the plugin install route, both the lifecycle dispatcher and the SKILL command resolve the **root** `pwf/scripts/session-catchup.py`, not a translated/platform copy (`pwf/hooks/claude-hook.sh:16-20`, `pwf/hooks/claude-hook.sh:65-70`, `pwf/skills/planning-with-files/SKILL.md:45-55`).

### Automatic path: NON-ISSUE

SessionStart invokes the script with `--no-history` and `$PWD` (`pwf/hooks/claude-hook.sh:60-83`). Argument parsing also defaults bare invocation to `no-history`, and `main()` returns before IDE detection, home-directory probing, or transcript discovery (`pwf/scripts/session-catchup.py:495-512`, `pwf/scripts/session-catchup.py:669-688`). Automatic catchup therefore emits nothing and reads no host session record.

### Explicit `--metadata`: reads outside the project, emits aggregates only

On Claude Code, explicit metadata resolves the user-level `~/.claude/projects/<sanitized-project>/` store, enumerates its JSONL files, and keeps only main-session files (`pwf/scripts/session-catchup.py:105-120`, `pwf/scripts/session-catchup.py:141-145`). It then reads recorded `cwd` values and accepts only exact same-project sessions; missing-cwd records are quarantined and folded-name collisions are rejected (`pwf/scripts/session-catchup.py:148-181`, `pwf/scripts/session-catchup.py:226-274`). Within prior sessions it locates the most recent `Write`/`Edit` to one of the three planning filenames and parses subsequent user/assistant messages to calculate the unsynced count (`pwf/scripts/session-catchup.py:312-353`, `pwf/scripts/session-catchup.py:356-437`, `pwf/scripts/session-catchup.py:698-742`).

On OpenCode, it resolves `${XDG_DATA_HOME}/opencode/opencode.db`, `OPENCODE_DATA_DIR`, or `~/.local/share/opencode/opencode.db`, opens SQLite with `mode=ro`, and selects sessions whose `directory` exactly equals the resolved project path (`pwf/scripts/session-catchup.py:443-459`, `pwf/scripts/session-catchup.py:515-565`). It finds planning-file tool events and counts later parts (`pwf/scripts/session-catchup.py:567-638`).

Metadata output is five fixed-shape lines on stdout: catchup available, runtime name, unsynced-entry count, an explicit exclusion of transcript excerpts, and direction to use `--replay` (`pwf/scripts/session-catchup.py:486-492`). **NON-ISSUE for `no_env_dump`:** it reads user-level records outside the project, but it neither emits the transcript/tool/path bytes in metadata mode nor writes them into a tracked file.

### Explicit `--replay`: bounded excerpts, with a wider disclosure boundary than “inside project”

For Claude records, replay prints at most the last 100 messages. User and assistant text are clipped to 300 characters; at most four tool summaries are emitted, but `Write`/`Edit` paths are retained and Bash commands retain their first 80 characters (`pwf/scripts/session-catchup.py:400-433`, `pwf/scripts/session-catchup.py:744-783`). OpenCode similarly limits to 100 parts and emits text, tool paths, and command prefixes (`pwf/scripts/session-catchup.py:462-483`, `pwf/scripts/session-catchup.py:641-666`). Every excerpt is bounded, SHA-labelled, nonce-framed, and marked untrusted data (`pwf/scripts/session-catchup.py:184-203`). Session and project labels are hashes rather than raw IDs/paths (`pwf/scripts/session-catchup.py:206-222`).

The same-project check applies to the transcript's recorded `cwd`, not each path inside a tool call (`pwf/scripts/session-catchup.py:226-274`, `pwf/scripts/session-catchup.py:400-424`). Thus replay can emit a path or command referring outside the project if an accepted same-project session contained one; the script does not open that referenced path. **MINOR privacy exposure, user-approved:** replay requires an explicit flag and the skill says to use it only after explicit approval (`pwf/skills/planning-with-files/SKILL.md:45-63`).

Replay also clips and frames arbitrary user/assistant text but does not redact it (`pwf/scripts/session-catchup.py:184-203`, `pwf/scripts/session-catchup.py:378-433`, `pwf/scripts/session-catchup.py:771-777`). **MINOR:** if a same-project transcript already contains an environment value or other secret in the emitted slice, replay can print it; nonce framing is an integrity/context boundary, not confidentiality. The script still does not write that output to a tracked file, so this is not itself the tracked-file violation forbidden by `no_env_dump` (`.claude/rules/do-not.md:68-74`, `hk.pkl:300-309`).

For the measured delegated-report loss, the Claude path is especially decisive: enumeration explicitly excludes every transcript whose filename starts `agent-` (`pwf/scripts/session-catchup.py:141-145`). Catchup can recover unsynced text from prior *main* sessions, but it is not a fallback archive for a subagent report left only in an agent transcript. **SERIOUS:** this reinforces the loss-class (b) finding rather than mitigating it.

### Filesystem, environment, and network control arms

```text
rg -n "open\\(|sqlite3\\.connect|\\.glob\\(" scripts/session-catchup.py
# positive: read opens/globs and the read-only SQLite connection

rg -n 'write_text|write_bytes|\\.mkdir\\(|\\.unlink\\(|\\.rename\\(|os\\.remove|shutil\\.' \
  scripts/session-catchup.py
rg -n "open\\([^\\n]*,[[:space:]]*['\"][wax]" scripts/session-catchup.py
# both zero

rg -n 'os\\.environ\\.get|os\\.environ\\[' scripts/session-catchup.py
# positive: named OPENCODE_DATA_DIR and XDG_DATA_HOME lookups

rg -n 'os\\.environ\\.(items|keys|values)|for .* in os\\.environ|printenv|export -p' \
  scripts/session-catchup.py
# zero

rg -n "glob\\('\\*\\.jsonl'\\)|startswith\\('agent-'\\)" scripts/session-catchup.py
# positive: the JSONL enumeration and explicit agent-file exclusion

rg -n '^(import|from)[[:space:]]+(requests|urllib|socket|subprocess)|^[[:space:]]*(requests|urllib|socket|subprocess)\\.' \
  scripts/session-catchup.py
# zero
```

The read/write result matches the code's `open(..., 'r')` calls and `mode=ro` database URI (`pwf/scripts/session-catchup.py:141-151`, `pwf/scripts/session-catchup.py:312-365`, `pwf/scripts/session-catchup.py:530-539`). The environment result shows named routing lookups, not enumeration or a dump (`pwf/scripts/session-catchup.py:30-47`, `pwf/scripts/session-catchup.py:443-459`). The repo's gate scans every tracked file for environment dumps (`hk.pkl:300-309`, `python/src/dotfiles_setup/env_blob_scan.py:202-230`), but this script only prints to stdout and contains no file-writing API. No network client import/call is present in the same implementation surface; a code-shaped control (`^(import|from) ...` or an indented client call for `requests|urllib|socket|subprocess`) returned zero, while the read-open arm above returned known positives.

## GitHub repos touched

- None. Only the two local trees named in the review scope were read.
