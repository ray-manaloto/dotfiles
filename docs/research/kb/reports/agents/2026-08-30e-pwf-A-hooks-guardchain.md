# Planning-with-files v3.12.0 — hooks and guard-chain adoption review

## Scope and source map

Unprefixed citations are relative to the read-only plugin root (`pwf/`). Citations beginning `dotfiles/` are relative to the target repository root. This is a static pre-adoption review: no plugin/helper script was executed and neither source tree was modified.

This is a static audit of the checked-out plugin implementation. The plugin identifies itself as `planning-with-files` version `3.12.0`; its manifest describes lifecycle context injection and an optional gated continuation mode. (`.claude-plugin/plugin.json:2-4`)

The Claude plugin lifecycle declaration is `hooks/hooks.json`; it sends every declared event through `sh ${CLAUDE_PLUGIN_ROOT}/hooks/claude-hook.sh <event-name>` with a ten-second timeout. (`hooks/hooks.json:3-99`) The repository contains no `.claude/` directory. The related standalone-skill hook wiring is instead embedded in `skills/planning-with-files/SKILL.md`; every such command exits immediately when `CLAUDE_PLUGIN_ROOT` is nonempty, preventing the standalone route from duplicating plugin hooks. (`skills/planning-with-files/SKILL.md:6-29`)

The dispatcher derives payload scripts exclusively from `${CLAUDE_PLUGIN_ROOT}/scripts`, including `inject-plan.sh`, `gate-stop.sh`, `resolve-plan-dir.sh`, and `session-catchup.py`. (`hooks/claude-hook.sh:12-20`) The root `scripts/gate-stop.sh`, `scripts/inject-plan.sh`, `scripts/check-complete.sh`, and `scripts/resolve-plan-dir.sh` are byte-identical to their copies under `skills/planning-with-files/scripts/` in this checkout (SHA-256 control recorded under “Static commands and controls”).

## Executive result

- **BLOCKER against the stated adoption goal:** the hooks re-inject existing planning files but do not persist submitted prompts, tool results, or findings-bearing agent reports; automatic catch-up explicitly returns before reading history. (`hooks/claude-hook.sh:100-110`; `scripts/session-catchup.py:669-690`; `dotfiles/.claude/rules/agent-report-persistence.md:20-44`)
- **SERIOUS:** with an active plan, default legacy mode can add 98,304 bytes of project payload plus framing per prompt and 65,536 bytes plus framing before every matched tool call. (`hooks/hooks.json:21-50`; `scripts/inject-plan.sh:826-847`; `scripts/inject-plan.sh:993-1025`; `scripts/inject-plan.sh:1174-1229`)
- **SERIOUS only if gated mode is enabled:** `Stop` can block continuation and directly write `.stop_blocks` / `.gate_last_ledger` outside the target's PreToolUse branch guard. (`scripts/check-complete.sh:132-169`; `scripts/check-complete.sh:183-215`; `scripts/check-complete.sh:247-252`; `dotfiles/.claude/settings.json:39-50`)
- **NON-ISSUE:** plugin and project hooks merge rather than shadow; the plugin PreToolUse output is context-only and has no normal non-zero or `permissionDecision` path, so it does not make the existing deny guard fail open. (`dotfiles/.claude/agents/claude-code-expert.md:266-270`; `hooks/claude-hook.sh:37-46`; `hooks/claude-hook.sh:128-133`)

## Plugin hook inventory and observable behavior

| Claude event | Matcher | Command argument | Stdout seen by Claude | Exit behavior |
|---|---|---|---|---|
| `SessionStart` | `startup\|resume\|clear\|compact` | `session-start` | When an active plan exists and the composed context is nonempty, one JSON object with `hookSpecificOutput.hookEventName="SessionStart"` and `additionalContext`; otherwise nothing. (`hooks/hooks.json:4-19`; `hooks/claude-hook.sh:60-84`) | Dispatcher exits 0 on missing prerequisites, empty helper output, helper failure, and normal completion. (`hooks/claude-hook.sh:60-63`; `hooks/claude-hook.sh:70-72`; `hooks/claude-hook.sh:81-84`; `hooks/claude-hook.sh:133`)
| `UserPromptSubmit` | none | `user-prompt-submit` | Nonempty `inject-plan.sh --context=userprompt` stdout becomes JSON `hookSpecificOutput.additionalContext` for `UserPromptSubmit`; empty or failed injection is silent. (`hooks/hooks.json:21-34`; `hooks/claude-hook.sh:37-46`; `hooks/claude-hook.sh:100-102`) | Exit 0, including missing injector, failed injector, or empty output. (`hooks/claude-hook.sh:40-42`; `hooks/claude-hook.sh:133`)
| `PreToolUse` | `Write\|Edit\|Bash\|Read\|Glob\|Grep` | `pre-tool-use` | Nonempty `inject-plan.sh --context=pretool` stdout becomes JSON `hookSpecificOutput.additionalContext` for `PreToolUse`; empty or failed injection is silent. (`hooks/hooks.json:36-50`; `hooks/claude-hook.sh:37-46`; `hooks/claude-hook.sh:103-105`) | Exit 0; there is no dispatcher deny/permission branch. (`hooks/claude-hook.sh:40-46`; `hooks/claude-hook.sh:103-105`; `hooks/claude-hook.sh:133`)
| `PostToolUse` | `Write\|Edit\|Bash` | `post-tool-use` | If an active `task_plan.md` resolves, one JSON `systemMessage`: `[planning-with-files] Update progress.md with what you just did. If a phase is now complete, update task_plan.md status.` Otherwise nothing. (`hooks/hooks.json:52-67`; `hooks/claude-hook.sh:86-91`; `hooks/claude-hook.sh:106-111`) | Exit 0 on missing resolver, no active plan, or normal completion. (`hooks/claude-hook.sh:107-110`; `hooks/claude-hook.sh:133`)
| `PreCompact` | `*` | `pre-compact` | Nonempty `inject-plan.sh --context=precompact` stdout becomes one JSON `systemMessage`; injector failure is silent. (`hooks/hooks.json:68-83`; `hooks/claude-hook.sh:112-116`) | Exit 0 on missing/failed injector and normal completion. (`hooks/claude-hook.sh:113-115`; `hooks/claude-hook.sh:133`)
| `Stop` | none | `stop` | A helper result beginning exactly `{"decision":"block"` is relayed verbatim; any other nonempty helper output becomes a JSON `systemMessage`; empty or failed helper output is silent. (`hooks/hooks.json:84-99`; `hooks/claude-hook.sh:117-126`) | The dispatcher ultimately exits 0, including the blocking case; blocking is requested by stdout JSON, not the process status. (`hooks/claude-hook.sh:121-126`; `hooks/claude-hook.sh:133`; `scripts/check-complete.sh:247-253`)

All events are globally inert when `PLANNING_DISABLED=1`, and all plugin events are also inert when `CLAUDE_PLUGIN_ROOT` is empty. (`hooks/claude-hook.sh:8-14`) The dispatcher JSON-escapes backslashes and quotes, replaces forbidden control bytes except newline, and encodes line boundaries as `\\n` before placing helper text in `additionalContext` or `systemMessage`. (`hooks/claude-hook.sh:22-35`; `hooks/claude-hook.sh:43-45`; `hooks/claude-hook.sh:86-90`)

## Stop gate: exact executable decision table

`gate-stop.sh` honors `PLANNING_DISABLED=1`, chooses a sibling `check-complete.sh` first, falls back to two `$HOME/.claude/...` locations only if the sibling is absent, exits 0 if no target exists, and otherwise runs the target as `sh "$TARGET" --gate` while leaving Stop stdin available to it. (`scripts/gate-stop.sh:13-17`; `scripts/gate-stop.sh:19-32`) `check-complete.sh` resolves an explicit plan argument first, otherwise uses its sibling resolver and finally `./task_plan.md`. (`scripts/check-complete.sh:37-67`)

A Stop is blocked only when all of these executable conditions hold:

1. A resolved `task_plan.md` exists and contains at least one line matching `### Phase`; no plan prints a no-session advisory, while zero phase headings returns silently. (`scripts/check-complete.sh:69-75`; `scripts/check-complete.sh:104-109`)
2. The plan directory has a `.mode` path satisfying `[ -f ]` for which `grep -q "gate"` succeeds. This is a substring test, not a token parser. (`scripts/check-complete.sh:132-140`)
3. On non-TTY stdin, the payload does not contain a `"stop_hook_active"` key followed by optional whitespace, `:`, optional whitespace, and `true`; a match produces advisory output and permits stopping. TTY stdin is not read, and empty stdin is treated as false. (`scripts/check-complete.sh:142-162`)
4. At least one in-progress marker exists. Counts are the per-field maximum of fixed-string `**Status:** in_progress` occurrences and regex `\[in_progress\]` occurrences, so merely having fewer complete phases than total phases does not block. (`scripts/check-complete.sh:77-96`; `scripts/check-complete.sh:164-169`)
5. The parsed `.stop_blocks` integer is strictly below `PWF_GATE_CAP`, whose default and invalid-value fallback are 20. At or above cap, the helper emits its advisory plus a cap-reached line and permits stopping. (`scripts/check-complete.sh:183-205`)
6. If `.stop_blocks` is greater than zero, the current total line count across `ledger-*.jsonl` paths satisfying `[ -f ]` is not equal to `.gate_last_ledger`. Equality emits its advisory plus a no-progress line and permits stopping. (`scripts/check-complete.sh:171-180`; `scripts/check-complete.sh:188-215`)

When all conditions pass, the helper increments and best-effort writes `.stop_blocks`, best-effort writes the current ledger count to `.gate_last_ledger`, and prints one single-line `{"decision":"block","reason":"..."}` object naming the first in-progress phase and the counts. Both state writes explicitly ignore failure, so stdout can still request a block if either marker was not persisted. (`scripts/check-complete.sh:217-227`; `scripts/check-complete.sh:229-252`)

Finding: the comments specify that the ledger must have “advanced,” but the executable guard tests only equality. A lower current line count is unequal and therefore passes this guard; the actual condition is “changed since the last block,” not “advanced.” (`scripts/check-complete.sh:16-24`; `scripts/check-complete.sh:208-215`)

The helper's block output and every advisory path exit 0. The Claude plugin dispatcher recognizes the block by its stdout prefix and passes it through, while it converts advisories to `systemMessage`. (`scripts/check-complete.sh:23-25`; `scripts/check-complete.sh:251-253`; `hooks/claude-hook.sh:121-126`)

No inspected Claude hook path emits `permissionDecision`. The only permission-like decision is Stop's top-level `{"decision":"block"...}` object. (`hooks/claude-hook.sh:123-125`; `scripts/check-complete.sh:251-252`) This negative was checked with a same-file-set `rg permissionDecision` miss and an `rg '"decision"'` positive control; commands and exit statuses are below.

## `inject-plan.sh`: what is injected, where, and when

The script's default context is `userprompt`; a `--context=<value>` argument replaces it. It exits without injection when `PLANNING_DISABLED=1`. (`scripts/inject-plan.sh:26-28`; `scripts/inject-plan.sh:61-63`; `scripts/inject-plan.sh:92-97`) It selects an absolute executable Python at version 3.8 or newer from the explicit trust variables or `PATH`; because the safe snapshot function refuses to run without that interpreter, every plan-body/reminder injection path is silent when no candidate works. (`scripts/inject-plan.sh:30-59`; `scripts/inject-plan.sh:259-270`; `scripts/inject-plan.sh:517-519`; `scripts/inject-plan.sh:803-811`)

Before emitting plan data, it resolves in this order: a valid `PLAN_ID`, a valid `.planning/.active_plan`, the newest valid scoped plan by directory mtime, then root `task_plan.md`. No resolution is silent. (`scripts/inject-plan.sh:224-257`) An explicit invalid `PWF_PLAN_ROOT` emits a one-line refusal and exits; a session-isolation directory without a valid attachment emits a refusal only for `userprompt`; and an ambiguous guessed parent/nested plan emits a refusal only for `userprompt`. (`scripts/inject-plan.sh:65-89`; `scripts/inject-plan.sh:272-388`; `scripts/inject-plan.sh:392-440`) Symlinked or uncontained plan files are refused before injection. (`scripts/inject-plan.sh:262-270`; `scripts/inject-plan.sh:442-467`)

The plan is accepted only when its regular-file size is at most 4,194,304 bytes and is then copied into a private snapshot; oversize or unsafe snapshot input makes the injection exit silently, and subsequent plan-derived output reads the snapshot. (`scripts/inject-plan.sh:469-473`; `scripts/inject-plan.sh:517-543`; `scripts/inject-plan.sh:803-811`) A `.mode` containing `gate` selects gated mode, otherwise one containing `autonomous` selects autonomous mode; in either mode, `pretool` exits silently. (`scripts/inject-plan.sh:826-847`)

The plan payload is data-framed with a SHA-256 digest, a 24-hex-character content-derived nonce, the exact byte count, and a truncation flag. (`scripts/inject-plan.sh:927-947`) The size control is byte-based: `bounded_view` measures with `wc -c` and truncates with `head -c`. (`scripts/inject-plan.sh:949-962`)

### Session start and user-prompt target

On `SessionStart` for startup, resume, clear, or compact, the dispatcher requires an active plan, invokes `session-catchup.py --no-history "$PWD"` if an interpreter is available, and then invokes `inject-plan.sh --context=userprompt`; any catch-up text would precede the plan text in `hookSpecificOutput.additionalContext`. (`hooks/hooks.json:4-19`; `hooks/claude-hook.sh:60-83`) In this checkout the called `--no-history` branch returns before IDE detection or host-history discovery and prints nothing, so the actual successful SessionStart payload is the user-prompt injection alone. (`scripts/session-catchup.py:669-676`; `hooks/claude-hook.sh:72-83`)

On each `UserPromptSubmit`, the same `userprompt` injection is targeted directly to `hookSpecificOutput.additionalContext`. (`hooks/hooks.json:21-34`; `hooks/claude-hook.sh:37-46`; `hooks/claude-hook.sh:100-102`)

For `userprompt`, an unattested autonomous/gated plan emits only `v3 mode requires attested plan`; an attestation mismatch emits the tamper line, expected and actual digests, and remediation, with no plan body. (`scripts/inject-plan.sh:964-991`; `scripts/inject-plan.sh:1028-1039`) Otherwise it emits, in order:

1. An optional plan-regression advisory if previously observed checked-item or completed-phase counts decreased. (`scripts/inject-plan.sh:1129-1172`)
2. The active-plan warning, optional attestation hash, and a `kind=plan` frame. The classic view is the first 50 lines, capped at 65,536 bytes. (`scripts/inject-plan.sh:1174-1189`)
3. A `kind=progress` frame capped at 32,768 bytes. Legacy mode uses the last 20 lines of the progress snapshot with timestamps normalized; autonomous/gated mode uses the sibling ledger summary when available, otherwise the same bounded tail form. (`scripts/inject-plan.sh:1192-1229`)
4. A final instruction to read `findings.md`; the contents of `findings.md` are not emitted by this script. (`scripts/inject-plan.sh:1231-1233`)

When smart injection is opted in by `PWF_INJECT=smart` or `inject-smart` in `.mode`, the plan view instead contains the title, Goal/Next Step/Current Phase sections, phase completion count, the full first in-progress phase, and the last three Decisions rows; a plan without phase headings falls back to the classic head view. (`scripts/inject-plan.sh:849-865`; `scripts/inject-plan.sh:866-925`)

### Pre-tool target

For each matched `Write`, `Edit`, `Bash`, `Read`, `Glob`, or `Grep` call, legacy mode targets `hookSpecificOutput.additionalContext` with `--context=pretool`; autonomous and gated modes suppress the per-tool payload entirely. (`hooks/hooks.json:36-50`; `hooks/claude-hook.sh:37-46`; `hooks/claude-hook.sh:103-105`; `scripts/inject-plan.sh:840-847`)

When not suppressed, a tampered legacy plan emits a one-line refusal rather than plan data; otherwise `pretool` emits only a `kind=plan` frame, using the smart shape when enabled or the first 30 lines, capped at 65,536 bytes, and never appends progress. (`scripts/inject-plan.sh:1003-1026`) Although the later branch contains an unattested autonomous/gated refusal, it is unreachable through normal `pretool` flow because those modes exit earlier. (`scripts/inject-plan.sh:840-847`; `scripts/inject-plan.sh:986-991`; `scripts/inject-plan.sh:1003-1007`)

### Pre-compact target

For every `PreCompact`, the dispatcher targets a JSON `systemMessage` with `--context=precompact`. (`hooks/hooks.json:68-83`; `hooks/claude-hook.sh:112-116`) Once a plan has resolved and passed the earlier path/session guards, the script emits three fixed reminder lines and optionally a stored attestation hash; it emits no plan or progress body, and neither missing required attestation nor an attestation mismatch alters this branch. (`scripts/inject-plan.sh:964-1001`)

### Measurement

There is no token-counting implementation in `inject-plan.sh`; the enforceable measurements are classic-view line selection and byte caps. The classic user-prompt plan view is 50 lines before a 65,536-byte bound, classic pre-tool is 30 lines before the same bound, and progress is 20 lines or a ledger summary before a 32,768-byte bound. Smart plan views replace the plan line limit but retain the 65,536-byte bound. (`scripts/inject-plan.sh:914-925`; `scripts/inject-plan.sh:1010-1024`; `scripts/inject-plan.sh:1176-1189`; `scripts/inject-plan.sh:1192-1227`) This negative was checked by an `rg` miss for common token-counter identifiers and `wc -w`, with the same-file positive control finding `wc -c` and `head -c` byte measurement.

## Standalone Claude skill wiring (duplicate-suppressed under plugin install)

The standalone skill frontmatter declares `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, and `PreCompact`, but no `SessionStart`; each declared command begins by exiting 0 when `CLAUDE_PLUGIN_ROOT` is set. (`skills/planning-with-files/SKILL.md:6-29`) Its `PreToolUse` matcher equals the plugin match set, while standalone `PostToolUse` matches only `Write|Edit`, not the plugin's additional `Bash`. (`skills/planning-with-files/SKILL.md:11-20`; `hooks/hooks.json:36-67`) The standalone Stop command prefers PowerShell on MINGW/MSYS/CYGWIN and the shell gate elsewhere, has opposite-language fallback, suppresses helper stderr, and ends with `exit 0`. (`skills/planning-with-files/SKILL.md:21-24`)

## Rated adoption findings

### BLOCKER — the hook layer does not durably capture the information this adoption is meant to save

The plugin's `UserPromptSubmit` handler does not consume or persist the submitted prompt; it calls `inject-plan.sh --context=userprompt` and returns existing planning-file content as `additionalContext`. Its `PostToolUse` handler likewise does not persist the tool input, result, or a report: it emits a fixed reminder asking the model to update two planning files. (`hooks/claude-hook.sh:37-46`; `hooks/claude-hook.sh:100-110`)

Automatic `SessionStart` recovery does not recover omitted instructions or lost lane output from Claude history. It invokes `session-catchup.py --no-history`, whose executable branch returns before IDE detection, transcript-store discovery, or output, and then injects the already-existing plan/progress files. (`hooks/claude-hook.sh:60-83`; `scripts/session-catchup.py:669-690`)

The six-event plugin descriptor has no `SessionEnd`, `SubagentStop`, or `TaskCompleted` hook that could enforce report receipt. The same-shape control found all six known-present event names and zero instances of those three absent names. (`hooks/hooks.json:3-100`) That is materially below the target's existing standard: findings-bearing subagent reports must be persisted verbatim at receipt, and handoff must map every findings-bearing launch to both its brief and report. (`dotfiles/.claude/rules/agent-report-persistence.md:1-7`; `dotfiles/.claude/rules/agent-report-persistence.md:20-36`; `dotfiles/.claude/rules/agent-report-persistence.md:56-65`)

**Plain answer:** these hooks can rehydrate information only after an agent has written it to the plugin's files. They do not close the motivating capture gap; adoption would still rely on model compliance for prompt capture and lane-report persistence. (`hooks/claude-hook.sh:100-110`; `scripts/session-catchup.py:669-690`; `dotfiles/.claude/rules/agent-report-persistence.md:31-44`)

### SERIOUS — default legacy mode adds high-amplification context exactly where this repo chose not to

With no `.mode` file, mode is empty/legacy, so the plugin injects before every matched `Write`, `Edit`, `Bash`, `Read`, `Glob`, and `Grep`; only explicit autonomous/gated modes suppress per-tool injection. (`hooks/hooks.json:36-50`; `scripts/inject-plan.sh:826-847`) The target explicitly chose not to re-inject per-turn reminders because its hard gate has no behavioral decay and repeated reminders consume instruction budget. (`dotfiles/.claude/rules/mise-tasks-only.md:88-95`)

The source permits exact byte ceilings, not exact token counts. One `UserPromptSubmit` or successful plan-bearing `SessionStart` can contribute up to 65,536 bytes of plan data plus 32,768 bytes of progress/ledger data — **98,304 bytes of project payload plus framing**. One legacy `PreToolUse` can contribute up to **65,536 bytes of plan payload plus framing**. `PreCompact` emits only three fixed lines plus an optional hash. (`scripts/inject-plan.sh:993-1025`; `scripts/inject-plan.sh:1174-1189`; `scripts/inject-plan.sh:1192-1233`) There is no tokenizer in the injector, so a model-token figure would be content/model-dependent rather than source-derived; the same-file negative/positive control is recorded below. (`scripts/inject-plan.sh:949-962`)

The context cost compounds within a turn: the full payload is added on `UserPromptSubmit`, then the short payload is eligible again for every matched tool call in legacy mode. (`hooks/hooks.json:21-50`; `hooks/claude-hook.sh:100-105`) This does not weaken the deny chain, but it is a silent context/latency change on the repo's hottest tool path. (`dotfiles/.claude/settings.json:40-70`)

### SERIOUS when gated mode is enabled — Stop blocks and writes around the branch guard

The only blocking plugin hook is `Stop`, and it blocks through stdout `{"decision":"block"}` at process exit 0, not through `permissionDecision` or exit 2. Its exact six executable predicates and escape paths are listed above. (`hooks/claude-hook.sh:117-126`; `scripts/check-complete.sh:132-169`; `scripts/check-complete.sh:183-215`; `scripts/check-complete.sh:247-253`) In the default no-`.mode` case, it is advisory and does not block, which is fine. (`scripts/check-complete.sh:126-140`)

On each actual block it best-effort writes `.stop_blocks` and `.gate_last_ledger` inside the resolved plan directory, ignoring write failures. (`scripts/check-complete.sh:188-199`; `scripts/check-complete.sh:247-252`) Those writes occur inside a `Stop` hook, whereas the target's branch guard is attached to pending `PreToolUse` calls and dispatches file-path policy for `Edit`, `Write`, and `NotebookEdit`; it therefore never evaluates the Stop helper's own filesystem writes. (`dotfiles/.claude/settings.json:39-50`; `dotfiles/python/src/dotfiles_setup/hook_guard.py:788-805`; `dotfiles/python/src/dotfiles_setup/branch_guard.py:17-30`; `dotfiles/python/src/dotfiles_setup/branch_guard.py:274-293`)

The target requires agent working state under `.agent/` or tracked durable material under `docs/`, with “No ad-hoc directories” as rule 1. (`dotfiles/.claude/rules/agent-artifact-conventions.md:1-5`; `dotfiles/.claude/rules/agent-artifact-conventions.md:13-35`; `dotfiles/.claude/rules/agent-artifact-conventions.md:61-69`) The target `.gitignore` has explicit `.agent/` controls but no plugin plan/marker paths; the same-command-shape negative/positive grep is recorded below. (`dotfiles/.gitignore:39-50`; `dotfiles/.gitignore:75-87`) Thus gated mode can create project state not covered by the committed ignore policy without traversing the default-branch edit guard.

This is bounded rather than an unconditional deadlock: `stop_hook_active=true` allows recursive continuation to stop, unchanged ledger count after a prior block allows stop, and the default cap permits stop at 20 recorded blocks. (`scripts/check-complete.sh:142-162`; `scripts/check-complete.sh:183-215`) However, the marker writes ignore failure; if the host did not supply the recursion flag and markers could not persist, the code's cap/stall protections would not advance. That is a conditional robustness risk, not a demonstrated Claude deadlock. (`scripts/check-complete.sh:247-252`)

### MINOR — the gate's “ledger advanced” comment is stricter than its code

The gate says the ledger must have advanced, but its executable check permits any unequal line count. A decrease in total ledger lines therefore passes the “progress” guard and can request another block. (`scripts/check-complete.sh:16-24`; `scripts/check-complete.sh:171-180`; `scripts/check-complete.sh:208-215`)

### NON-ISSUE — plugin hooks add to the project hooks; they do not shadow them

The target's locally maintained Claude behavior ledger records that hooks merge across settings sources rather than override, so the plugin and project hooks both fire. (`dotfiles/.claude/agents/claude-code-expert.md:266-270`) The resulting overlap is:

| Trigger | Target project hooks | Plugin hook | Combined result |
|---|---|---|---|
| `Bash` PreToolUse | hard guard + Graphify search | plan injection | three matching hooks (`dotfiles/.claude/settings.json:40-59`; `hooks/hooks.json:36-50`) |
| `Edit` / `Write` PreToolUse | hard guard | plan injection | two matching hooks (`dotfiles/.claude/settings.json:40-50`; `hooks/hooks.json:36-50`) |
| `Read` / `Glob` PreToolUse | Graphify read | plan injection | two matching hooks (`dotfiles/.claude/settings.json:61-70`; `hooks/hooks.json:36-50`) |
| `Grep` PreToolUse | Graphify search | plan injection | two matching hooks (`dotfiles/.claude/settings.json:51-60`; `hooks/hooks.json:36-50`) |
| `AskUserQuestion` / `NotebookEdit` PreToolUse | hard guard | none | target guard only (`dotfiles/.claude/settings.json:40-50`; `hooks/hooks.json:36-50`) |
| `SessionStart` `startup` / `resume` | tool-currency + doctor chain | plan restoration | two matching hooks; plugin alone also matches `clear` / `compact` (`dotfiles/.claude/settings.json:72-82`; `hooks/hooks.json:4-19`) |
| `SessionEnd` | command-audit | none | target audit remains the only registered SessionEnd route (`dotfiles/.claude/settings.json:84-94`; `hooks/hooks.json:3-100`) |
| `UserPromptSubmit`, `PostToolUse`, `PreCompact`, `Stop` | none in project settings | plugin lifecycle hooks | additive plugin-only events (`dotfiles/.claude/settings.json:39-94`; `hooks/hooks.json:21-99`) |

No cross-source execution-order promise appears in either tree. The same-shape search found the explicit merge guarantee as its positive control and no plugin-versus-project ordering guarantee, so order must be treated as undefined rather than inferred from JSON/file order. (`dotfiles/.claude/agents/claude-code-expert.md:266-270`) This is operationally minor because the plugin's overlapping PreToolUse output is context-only; no design should depend on whether it appears before or after the project's deny result. (`hooks/claude-hook.sh:37-46`; `dotfiles/python/src/dotfiles_setup/hook_guard.py:808-830`)

The plugin also avoids duplicating its own Claude hooks: the manifest omits an explicit hook key in favor of the conventional `hooks/hooks.json`, and the five standalone skill-frontmatter hooks immediately exit in plugin context. (`.claude-plugin/plugin.json:1-47`; `tests/test_claude_plugin_operations.py:65-68`; `tests/test_claude_plugin_operations.py:198-220`) That part is correctly composed.

### NON-ISSUE — the plugin cannot make the existing guard fail open on a normal code path

The target guard's denial travels as `permissionDecision:"deny"` at exit 0; a crash would fail open, and its wrapper deliberately converts interpreter absence or a guard error to recorded exit 0. (`dotfiles/python/src/dotfiles_setup/hook_guard.py:808-830`; `dotfiles/scripts/pretooluse-guard.sh:24-42`) The recorded incident was a non-zero, non-2 PreToolUse error, which the target documents as non-blocking. (`dotfiles/.claude/rules/mise-tasks-only.md:112-116`)

The plugin's separate PreToolUse route emits only `hookSpecificOutput.additionalContext`. Missing scripts, failed injection, and empty injection all exit 0, and the dispatcher ends at exit 0; it has no `permissionDecision` branch. (`hooks/claude-hook.sh:37-46`; `hooks/claude-hook.sh:103-105`; `hooks/claude-hook.sh:128-133`) Because sources merge rather than shadow, a plugin-helper failure can make the plugin's own context injection disappear, but it does not change the project guard subprocess or its deny JSON. (`dotfiles/.claude/agents/claude-code-expert.md:266-270`; `dotfiles/python/src/dotfiles_setup/hook_guard.py:808-830`)

The ten-second timeout could still surface a plugin hook timeout/error, but that would be the plugin hook's non-blocking failure, not the target guard returning the historical non-zero/non-2 condition. (`hooks/hooks.json:36-48`; `dotfiles/.claude/rules/mise-tasks-only.md:112-116`) **Plain answer:** no normal plugin code path makes the repository guard fail open; the existing guard retains its own documented fail-open paths.

### MINOR — lifecycle duplication adds work but leaves SessionEnd intact

On `startup` and `resume`, the project still runs tool currency plus doctor while the plugin independently restores planning context; neither declaration replaces the other. (`dotfiles/.claude/settings.json:72-82`; `hooks/hooks.json:4-19`; `dotfiles/.claude/agents/claude-code-expert.md:266-270`) The target doctor is deliberately silent and exit 0 when healthy, while the plugin is silent without an active plan, so the overlap is latency/work rather than a new permission conflict. (`dotfiles/.claude/CLAUDE.md:50-61`; `hooks/claude-hook.sh:60-84`)

The plugin does not register `SessionEnd`, so the target's once-per-session command-audit remains in place; the plugin instead adds per-turn `Stop`, which can block only in the opt-in gate mode. (`dotfiles/.claude/settings.json:84-94`; `dotfiles/.claude/rules/mise-tasks-only.md:78-83`; `hooks/hooks.json:84-99`; `scripts/check-complete.sh:126-140`)

## Adoption answer on this axis

Installing the plugin as-is is **not an evidence-backed fix for the target's loss problem**: it has no automatic submitted-prompt capture or findings-bearing-agent receipt gate, while default legacy mode adds large repeated context and optional gated mode writes outside the existing branch guard. (`hooks/claude-hook.sh:100-110`; `scripts/session-catchup.py:669-690`; `scripts/inject-plan.sh:826-847`; `scripts/check-complete.sh:247-252`; `dotfiles/.claude/rules/agent-report-persistence.md:20-44`)

What is fine: hook merging preserves the existing deny-capable PreToolUse guard, the plugin emits no competing allow/deny decision, its own plugin/standalone routes are duplicate-suppressed, and the existing SessionEnd command-audit is not shadowed. (`dotfiles/.claude/agents/claude-code-expert.md:266-270`; `hooks/claude-hook.sh:37-46`; `tests/test_claude_plugin_operations.py:198-220`; `dotfiles/.claude/settings.json:84-94`)

## Static commands and controls

No plugin or helper script was executed. Inspection used line-numbered reads and static searches.

1. Primary-source reads:

   ```sh
   nl -ba hooks/hooks.json
   nl -ba hooks/claude-hook.sh
   nl -ba scripts/gate-stop.sh
   nl -ba scripts/check-complete.sh
   nl -ba scripts/inject-plan.sh
   nl -ba .claude-plugin/plugin.json
   nl -ba skills/planning-with-files/SKILL.md
   ```

2. Canonical/copy identity control:

   ```sh
   for f in gate-stop.sh inject-plan.sh check-complete.sh resolve-plan-dir.sh; do
     shasum -a 256 "scripts/$f" "skills/planning-with-files/scripts/$f"
   done
   ```

   Each pair returned the same SHA-256: `ed4f138c...` for `gate-stop.sh`, `b9900baa...` for `inject-plan.sh`, `4fb617e8...` for `check-complete.sh`, and `eb1d3a25...` for `resolve-plan-dir.sh`.

3. `permissionDecision` negative with same-command-shape positive control over the same source set:

   ```sh
   rg -n -S 'permissionDecision' hooks/hooks.json hooks/claude-hook.sh scripts/gate-stop.sh scripts/check-complete.sh scripts/inject-plan.sh .claude-plugin/plugin.json skills/planning-with-files/SKILL.md
   # exit 1, no matches
   rg -n -S '"decision"' hooks/hooks.json hooks/claude-hook.sh scripts/gate-stop.sh scripts/check-complete.sh scripts/inject-plan.sh .claude-plugin/plugin.json skills/planning-with-files/SKILL.md
   # exit 0; hooks/claude-hook.sh:124, scripts/check-complete.sh:251, and skill documentation
   ```

4. Token-measurement negative with same-command-shape positive control in the injector:

   ```sh
   rg -n -S 'tiktoken|token_count|count_tokens|wc -w' scripts/inject-plan.sh
   # exit 1, no matches
   rg -n -S 'wc -c|head -c' scripts/inject-plan.sh
   # exit 0; byte accounting/bounds at lines 940, 954, 961, 1012, 1178, 1204, 1206, and 1219
   ```

5. Local Claude-layout existence check, using the same predicate for negative and positive controls:

   ```sh
   for p in .claude .claude-plugin .codex; do
     if [ -d "$p" ]; then printf 'FOUND_DIR %s\n' "$p"; else printf 'MISSING_DIR %s\n' "$p"; fi
   done
   # MISSING_DIR .claude
   # FOUND_DIR .claude-plugin
   # FOUND_DIR .codex
   ```

6. Plugin-manifest hook-key negative with same-command-shape positive control against the hook manifest:

   ```sh
   rg -n -S '"hooks"[[:space:]]*:' .claude-plugin/plugin.json
   # exit 1, no matches
   rg -n -S '"hooks"[[:space:]]*:' hooks/hooks.json
   # exit 0; lines 3, 7, 23, 39, 55, 71, and 86
   ```

The plugin metadata file itself therefore does not contain a hook key; the checked-in hook declaration is the separate `hooks/hooks.json` file. (`.claude-plugin/plugin.json:1-47`; `hooks/hooks.json:1-101`)

7. Plugin lifecycle-event negative with a known-present event control, both against the same descriptor:

   ```sh
   rg -n -S '"(SessionStart|UserPromptSubmit|PreToolUse|PostToolUse|PreCompact|Stop)"' hooks/hooks.json
   # exit 0; six event keys at lines 4, 21, 36, 52, 68, and 84
   rg -n -S '"(SessionEnd|SubagentStop|TaskCompleted)"' hooks/hooks.json
   # exit 1, no matches
   ```

8. Target hook-event negative with known-present project-event control, both against the same settings file:

   ```sh
   rg -n -S '"(PreToolUse|SessionStart|SessionEnd)"' .claude/settings.json
   # exit 0; lines 40, 72, and 84
   rg -n -S '"(UserPromptSubmit|PostToolUse|PreCompact|Stop)"' .claude/settings.json
   # exit 1, no matches
   ```

9. Target ignore-path negative with a known-present artifact-root control, both against `.gitignore`:

   ```sh
   rg -n -S '^/?(\.planning|\.active_plan|task_plan\.md|findings\.md|progress\.md|\.stop_blocks|\.gate_last_ledger)' .gitignore
   # exit 1, no matches
   rg -n -S '^/?\.agent' .gitignore
   # exit 0; lines 41, 45, 50, 81, and 87
   ```

10. Cross-source ordering negative with the known-present merge statement as control over the same relevant source set:

   ```sh
   rg -n -i -S 'hooks merge across sources|plugin.*project.*order|project.*plugin.*order|cross-source.*order' \
     dotfiles/.claude/agents/claude-code-expert.md pwf/hooks pwf/.claude-plugin \
     pwf/skills/planning-with-files/SKILL.md
   # exit 0 only for the merge statement at dotfiles/.claude/agents/claude-code-expert.md:268;
   # no inter-source ordering guarantee matched
   ```

## GitHub repos touched

- `OthmanAdi/planning-with-files` — read-only local inspection. (`.git/config:8-10`; `.claude-plugin/plugin.json:5-10`)
- `ray-manaloto/dotfiles` — read-only local inspection. (`dotfiles/.git/config:8-10`)
