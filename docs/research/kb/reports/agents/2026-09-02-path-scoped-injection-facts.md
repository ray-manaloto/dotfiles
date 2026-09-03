# Path-scoped rule injection & enforcement — harness facts (2026-09-02)

STATUS: IN PROGRESS — version being audited recorded below.

Corpora: installed binary, `claude --help`, offline vendor docs
(`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/`), live probes.

**Version audited: `claude --version` -> `2.1.258 (Claude Code)`** (NOT 2.1.222 — every
prior ledger row in the claude-code-expert agent definition is version-stale by 36 patches).
Doc tree: 192 pages under `.../agent-harness-docs/docs/claude-code/`.

---

## 1. Path-scoped rules — CONFIRMED, REAL, shipped

Key: **`paths:`** — a YAML frontmatter list of globs in `.claude/rules/*.md`.

- `$CC/memory.md:209` — the canonical example and the "Path-specific rules" section.
- `$CC/memory.md:~203` — "Rules without `paths` frontmatter are loaded at launch with the
  same priority as `.claude/CLAUDE.md`."
- `$CC/memory.md` — "Path-scoped rules trigger when Claude **reads files matching the
  pattern, not on every tool use**."
- `$CC/claude-directory.md:169` — "Rules without `paths:` load at session start. Rules with
  `paths:` load when a matching file enters context."
- `$CC/glossary.md:251` — same, in the glossary definition of Rules.

Glob semantics (all `$CC/memory.md`, "Path-specific rules"):

| Pattern | Matches |
|---|---|
| `**/*.ts` | all .ts in any dir |
| `src/**/*` | everything under `src/` |
| `*.md` | markdown in the project ROOT only |
| `src/components/*.tsx` | one directory, no recursion |

- Brace expansion IS supported: `src/**/*.{ts,tsx}`.
- **Budget: 1,000 expanded patterns / 4 MiB per rule's whole `paths` list.** Over budget the
  pattern is used UNEXPANDED and its literal braces match nothing — a SILENT no-op.
  Before v2.1.217 an over-budget list stalled or crashed the CLI at startup.
- `[` starts a bracket expression. `photos [2024/**` is invalid and matches NOTHING (other
  patterns in the same rule keep working). Escape as `photos \[2024/**`.
  Before v2.1.207 one invalid pattern made Read FAIL for every file the rule was evaluated
  against.
- Symlinked paths DO match as of v2.1.198 (`$CC/memory.md`); `changelog.md:1529` records the fix.
- Nested dirs (`.claude/rules/frontend/react.md`) are discovered recursively.
- Project rules skipped if `project` excluded from `--setting-sources`. **Before v2.1.211
  path-scoped and nested rules loaded even when `project` was excluded** — a leak, now fixed.
- User-level `~/.claude/rules/` loads BEFORE project rules (project wins on priority).
- ⚠️ `$CC/claude-directory.md:169` states the limit explicitly: "rules are guidance Claude
  reads, **not configuration Claude Code enforces**. For guaranteed behavior use hooks or
  permissions."

---

## 5. `FileChanged` — EXISTS, but is the WRONG event for injection

`$CC/hooks.md:2787` (full reference), `:60`, `:876`, `:1025`, `:321`.

- **Trigger**: a *filesystem watcher*, NOT tool-call inspection — "it runs the hook no matter
  what changed the file: an `Edit` or `Write` tool call, a script Claude runs with `Bash`, or a
  process outside Claude Code entirely" (`hooks.md:2789`).
- **Payload** (`hooks.md:2832`): common fields + **`file_path`** (absolute path of the changed
  file) + **`event`** (`"change"` | `"add"` | `"unlink"`).
- **Matcher is NOT a glob and NOT a regex.** It is split on `|` into **literal filenames in the
  working directory**. `"^\.env"` would watch a file literally named `^\.env`
  (`hooks.md:2793`). `hooks.md:301`: FileChanged (with StopFailure) uses a narrower exact-match
  set — letters, digits, `_`, `|` only; a hyphen/space/comma keeps it on the regex path.
- **`watchPaths`** (array of absolute paths) can be returned from FileChanged, SessionStart or
  CwdChanged to update the dynamic watch list. The watcher does not start until something names
  a file (`hooks.md:2852`).
- ⚠️ **DECISIVE NEGATIVE — FileChanged has NO decision control and CANNOT inject context.**
  `hooks.md:1025` groups it with Setup/WorktreeRemove/Notification/SessionEnd/PostCompact/
  InstructionsLoaded/StopFailure/CwdChanged/DirectoryAdded: "**None** — No decision control.
  Used for side effects like logging or cleanup." `hooks.md:876`: exit code 2 → "Shows stderr
  to **user** only." `hooks.md:2860`: "Claude Code reads `watchPaths` and `systemMessage` from
  their JSON output and **discards `continue`**... shows the `systemMessage` as a brief terminal
  notification. **The message doesn't reach the SDK message stream.**"
- `hooks.md:1544`: "Unlike PreToolUse, Claude Code runs FileChanged hooks **after** the change,
  and they have no decision control, so they can't block the write."

**Verdict: FileChanged is a side-effect event (reformat, reload env), not an injection event.**
It is the right tool for "this path was touched, DO something on disk"; it is the wrong tool
for "inject its rule into the model's context".

⚠️ **Loop hazard, documented**: `perl -i` rewrites a file even when it substitutes nothing, and
Claude Code re-fires the hook after every rewrite — a FileChanged hook that writes must guard on
exactly what it changes or it loops forever (`hooks.md:2820`).

---

## 5b. `InstructionsLoaded` — the native observability channel for path-scoped rules

`$CC/hooks.md:1261`. Added in `changelog.md:4130`.

Fires when a `CLAUDE.md` or `.claude/rules/*.md` file is loaded into context — **at session
start for eager files AND later when conditional `paths:` rules match**.

Input fields (`hooks.md:1267`):

| Field | Value |
|---|---|
| `file_path` | absolute path of the *instruction file* that loaded |
| `memory_type` | `"User"` / `"Project"` / `"Local"` / `"Managed"` |
| `load_reason` | `"session_start"` / `"nested_traversal"` / **`"path_glob_match"`** / `"include"` / `"compact"` |
| `globs` | the rule's own `paths:` patterns — **present only for `path_glob_match`** |
| `trigger_file_path` | **the path Claude accessed that caused the lazy load** |

**The `matcher` runs against `load_reason`** — e.g. `"matcher": "path_glob_match"` fires only on
path-scoped lazy loads (`hooks.md:1263`).

⚠️ **No decision control, and its JSON output is DISCARDED** including `systemMessage`
(`hooks.md:1292`). "Use this event for audit logging, compliance tracking, or observability."
So it can *observe* every path-scoped rule load, and it can write to disk — but it cannot
itself inject.

Note `load_reason: "compact"` — instruction files are **re-loaded after compaction**, which is
the event any "already injected this session" bookkeeping must account for.

---

## 2. Hook-driven injection into the MODEL's context

The field is **`hookSpecificOutput.additionalContext`** (a string). `$CC/hooks.md:970`
"Add context for Claude":

> "Claude Code wraps the string in a **system reminder** and inserts it into the conversation
> at the point where the hook fired. Claude reads the reminder on the next model request, but
> it doesn't appear as a chat message in the interface."

⚠️ `$CC/hooks-guide.md`: "`additionalContext` **inside `hookSpecificOutput`**; if you place it
at the top level of the JSON, Claude Code **silently ignores it**."

`systemMessage` is the OPPOSITE field: it renders in the user's terminal, not the model's
context. Do not confuse them.

### Which events accept `additionalContext` (enumerated from `hooks.md:970` + the
### decision-control table at `hooks.md:1025`, not from an expected list)

| Event | Injects into model context? | Where the reminder lands |
|---|---|---|
| `SessionStart` | YES | start of conversation, before first prompt |
| `SubagentStart` | YES | start of the subagent's conversation |
| `UserPromptSubmit` | YES | alongside the submitted prompt |
| `UserPromptExpansion` | YES | alongside the expanded prompt |
| **`PreToolUse`** | **YES** | next to the tool result. ⚠️ **Ignored when `permissionDecision` is `"defer"`** |
| **`PostToolUse`** | **YES** | next to the tool result |
| `PostToolUseFailure` | YES | next to the tool result |
| `PostToolBatch` | YES | next to the tool result |
| `Stop` / `SubagentStop` | YES | end of turn; conversation continues |
| `PostModelSwitch` | YES | with the next request after the switch |
| **`FileChanged`** | **NO** | no decision control at all (see §5) |
| **`InstructionsLoaded`** | **NO** | JSON output discarded (see §5b) |
| `CwdChanged`, `DirectoryAdded`, `Setup`, `SessionEnd`, `PostCompact`, `Notification`, `WorktreeRemove`, `StopFailure` | NO | `hooks.md:1025` "None" |

Cap: `additionalContext`, `systemMessage` and plain stdout are each capped at **10,000
characters**; overflow is written to a file in the session directory and Claude gets a preview
plus the path (`hooks.md`, JSON output section). Multiple hooks returning `additionalContext`
for one event: **Claude receives all of the values**.

⚠️ **Style constraint, documented**: write injected text as *factual statements*, not
imperatives — "Text framed as out-of-band system commands can trigger Claude's
prompt-injection defenses, which causes Claude to surface the text to you instead of treating
it as context" (`hooks.md:~1000`).

⚠️ **Resume replays stale text**: for mid-session events (`PostToolUse`, `UserPromptSubmit`),
`--continue`/`--resume` **replays the saved injected text rather than re-running the hook**, so
timestamps/SHAs go stale. Only `SessionStart` re-runs (with `source: "resume"` or `"fork"`).

### Which events see a file path

| Event | Field | Notes |
|---|---|---|
| `PreToolUse` | `tool_input.file_path` | **Always ABSOLUTE for `Write`, `Edit`, `Read`** — `~` and relative paths are expanded *before* hooks run, "so a hook that matches on paths **can't be bypassed** via `~` or a relative spelling" (`hooks.md:1558`) |
| `PostToolUse` | `tool_input.file_path` + `tool_response` | same absolute format (`hooks.md:1928`) |
| `PostToolUseFailure` | `tool_input.file_path` | same |
| `FileChanged` | top-level `file_path` | absolute; plus `event` |
| `InstructionsLoaded` | `file_path`, `trigger_file_path` | the *instruction* file and the file that triggered it |
| **`UserPromptSubmit`** | **NONE** | payload is `prompt` only (`hooks.md:1308`). It cannot path-filter. |

⚠️ **Windows**: `tool_input.file_path` arrives with **backslashes**, even under Git Bash. A
`/src/` check never matches and "the tool call proceeds as if the hook had nothing to block"
(`hooks.md:1560`). Normalize before comparing. (Not a hazard on this darwin host, but it is a
silent-no-op class worth knowing.)

### ⭐ NATIVE PATH FILTERING EXISTS — the `if` field

`$CC/hooks.md:424` (common hook fields). This was NOT in the caller's question and changes the
design:

> `if` — "Permission rule syntax to filter when this hook runs, such as `"Bash(git *)"` or
> **`"Edit(*.ts)"`**. The hook command **only runs if the tool call matches the pattern**.
> Only evaluated on tool events: **`PreToolUse`, `PostToolUse`, `PostToolUseFailure`,
> `PermissionRequest`, `PermissionDenied`**. On other events, a hook with `if` set **never
> runs**."

So a path-scoped injection hook does NOT need to spawn a script and self-filter: `if` gates the
spawn itself. Constraints:

- **Exactly one rule.** "There is no `&&`, `||`, or list syntax for combining rules; to apply
  multiple conditions, define a separate hook handler for each."
- `"Edit(src/**)"` matches only `src` **in the working directory**; use `"Edit(**/src/**)"` for
  any depth. Before v2.1.214 the single-segment form matched any depth — a semantics change
  inside the current minor.
- ⚠️ **Best-effort, by the docs' own words**: "Because the `if` filter is best-effort, use the
  permission system rather than a hook to enforce a hard allow or deny" (`hooks.md:~446`).
  Fine for *injection*; not for *enforcement*.
- For Bash, `if` inspects subcommands, `$()` and backticks; when it cannot tell what a command
  expands to it **runs the hook anyway** (fail-open toward running).

---

## 3. Once-only injection — NO general harness-native de-duplication

**There is no de-duplication of `additionalContext`.** The docs say the opposite: "When several
hooks return `additionalContext` for the same event, **Claude receives all of the values**"
(`$CC/hooks.md:993`). A `PostToolUse` hook that injects rule text will re-inject it on every
matching tool call unless the hook itself keeps state.

**The one native once-only mechanism is `once: true`** (`$CC/hooks.md:430`):

> "If `true`, Claude Code removes the hook after its first successful run. A run that fails,
> blocks with exit code 2, or times out leaves the hook in place... **Only honored for hooks
> declared in skill frontmatter; IGNORED in settings files and agent frontmatter.**"

⚠️ So `once: true` is **useless for a `.claude/settings.json` hook** — silently ignored. A
settings-declared hook MUST implement its own bookkeeping.

**Session-scoped key available to every hook** (`$CC/hooks.md:~726`, "Common input fields"):

| Field | Use |
|---|---|
| **`session_id`** | current session identifier — the natural dedup key |
| `prompt_id` | UUID of the prompt being processed (v2.1.196+); correlates with OTel `prompt.id`. **Absent until first user input** |
| `transcript_path` | path to the session JSONL — ⚠️ "written asynchronously and may **lag** the in-memory conversation" |
| `cwd`, `permission_mode`, `effort`, `hook_event_name` | |
| `agent_id`, `agent_type` | **present only inside a subagent** — so a subagent's injections can be keyed separately from the main thread |

Env available to a command hook: `CLAUDE_PROJECT_DIR` (project root where the session started —
**stays put even if Claude enters a worktree**), `CLAUDE_PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`,
`$CLAUDE_EFFORT`. `CLAUDE_ENV_FILE` is available **only** to `SessionStart`, `Setup`,
`CwdChanged`, `FileChanged`.

**Where to persist**: the docs name no convention. This repo's own convention applies —
`.agent/state/` (gitignored), per `.claude/rules/agent-artifact-conventions.md`. Keying on
`session_id` is the documented-field answer; **this is INFERRED for the storage location, not
documented.**

⚠️ **Two events that break naive session-keyed dedup:**
1. `InstructionsLoaded` fires again with `load_reason: "compact"` after compaction — instruction
   files are re-loaded, so anything you injected in place of a rule is arguably due again.
2. On `--continue`/`--resume`, mid-session injected text is **replayed from the transcript, not
   re-derived** — so a resumed session sees the OLD text and your state file is out of sync with
   what the model actually has.

---

## 4. Deny rules vs PreToolUse hook deny — the repo's belief is CONFIRMED, with a correction

**`permissions.deny` is authoritative. The hook is not.**

- `$CC/permission-modes.md:30` — "**Deny rules block in every mode, including
  `bypassPermissions`.** Allow rules have no effect in `bypassPermissions`."
- `$CC/permissions.md:64` — "Rules are evaluated in order: **deny, then ask, then allow.** The
  first match in that order determines the outcome, and **rule specificity doesn't change the
  order**." A broad deny "can't carry allowlist exceptions".
- `$CC/permissions.md:495` — "**Hook decisions don't bypass permission rules.** Claude Code
  evaluates deny and ask rules regardless of what a PreToolUse hook returns: a matching deny
  rule blocks the call, and a matching ask rule still prompts even when the hook returned
  `"allow"` or `"ask"`."
- `$CC/permissions.md:68` — a **bare tool name** in deny (`"Bash"`) *removes the tool from
  Claude's context entirely*; a **scoped** rule (`"Bash(rm *)"`) leaves the tool and blocks
  matching calls.

**The hook fails OPEN — confirmed, and the doc names this exact failure:**

`$CC/hooks.md:820` ("Other exit codes"): "A hook that can't start lands in the same non-blocking
bucket. When the script path doesn't exist or isn't executable, the shell exits with a code like
127 and you see the same notice... For most hook events, **the action proceeds**. When you set
up a policy hook, watch for this notice on its first run: **a mistyped path in `settings.json`
leaves the gate silently disabled.**"

That is #343's exact shape, documented by the vendor. Further fail-open surfaces:

- ⚠️ **Exit code 1 does NOT block.** `hooks.md` Warning: "Claude Code treats exit code 1 as a
  non-blocking error and proceeds with the action, even though 1 is the conventional Unix
  failure code. If your hook is meant to enforce a policy, use `exit 2`."
- ⚠️ **A timed-out PreToolUse command/http/mcp_tool hook does NOT block** — "the call continues
  through the normal permission flow, so **don't count on a stalled hook to act as a gate**"
  (`hooks.md:839`). (An Agent-SDK *callback* hook that times out DOES block — opposite behavior.)
- A parse failure or schema-validation failure on stdout is a **non-blocking** error on every
  exit code except 2.

### Corrections to this repo's stated beliefs

1. **"the deny is deterministic — it applies even in bypassPermissions mode"**
   (`.claude/rules/clarify-before-acting.md`, `mise-tasks-only.md`) — the vendor docs make this
   claim for **permission `deny` RULES** (`permission-modes.md:30`), not for a PreToolUse hook's
   `permissionDecision: "deny"`. I found **no doc statement** that a PreToolUse hook still runs
   and can deny under `bypassPermissions`. `permission_mode` is passed to the hook *as a value it
   can read*, which implies hooks do run in that mode — but "hooks run in bypass mode" is
   **UNVERIFIED**; only "deny RULES block in every mode" is documented. Given the repo's guards
   (`hook_guard`, `branch_guard`, `ask_quality`) are all PreToolUse hooks, this distinction is
   load-bearing and worth a live probe before relying on it.
2. **Circuit breaker**: `permission-modes.md:567` — "Claude Code **never** lets a
   `permissions.allow` rule **or a `PreToolUse` hook that returns `"allow"`** approve an `rm` or
   `rmdir` targeting a critical path, even in modes that skip other prompts."
3. `permissions.md:316` — ⚠️ **file path rules are only consulted for `Edit(path)` and
   `Read(path)`.** A rule written for `Write`, `NotebookEdit`, `Glob` or `MultiEdit` is
   *accepted and never consulted* (with a startup warning). Use `Edit(docs/**)`, not
   `Write(docs/**)`. A `Read` deny also blocks Edit and Write on that path (v2.1.208 / v2.1.228),
   **but not NotebookEdit**.

---

## 6-7. Codex

Corpus: `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/`
(`$CX` below). Codex version NOT probed live — findings are DOCUMENTED, not probed.

### Events (10, enumerated from `$CX/hooks.md:25`, not from the repo's file)

| When | Events |
|---|---|
| During a turn | `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStop`, `Stop` |
| Session/subagent start | `SessionStart`, `SubagentStart` |
| Main thread ends | `SessionEnd` (does NOT run for subagents) |

Sources: `~/.codex/hooks.json`, `~/.codex/config.toml` inline `[hooks]`,
`<repo>/.codex/hooks.json`, `<repo>/.codex/config.toml`, plus plugin-bundled.
**All matching hooks from all layers run — higher layers do not replace lower ones.**
Project-local hooks load only when the project `.codex/` layer is trusted, and
**non-managed command hooks must be reviewed and trusted before they run.**

### Context injection — Codex DOES support `hookSpecificOutput.additionalContext`

Same field name as Claude Code (`$CX/hooks.md:496, 570, 625, 753, 844`). Supported on at least
`SessionStart`, `SubagentStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`. Text is added
as "extra **developer** context".

⚠️ **Codex-only knob with no Claude Code equivalent: `additionalContextLimit`**
(`$CX/hooks.md:185, 452`) — a per-handler approximate token cap, **default 2,500 tokens**
(Claude Code's is a fixed 10,000 *characters*). Overflow is written to
`<temp_dir>/hook_outputs/<session_id>/<uuid>.txt`. Docs warn: without a strict cap "a single
hook can consume the entire context".

Also: **plain stdout is added as developer context** on SessionStart/SubagentStart/PostToolUse/
UserPromptSubmit — but on `PreToolUse`, `$CX/hooks.md:598`: "**Plain text on `stdout` is
ignored.**"

### ⚠️ Codex has NO native path/glob filtering — CONFIRMED with control arms

`$CX/hooks.md:320` "Matcher patterns": `matcher` is a **regex over the TOOL NAME** (or the
compaction trigger / session source / subagent type). There is no path dimension.

| Probe (`$CX/hooks.md`) | Count |
|---|---|
| `file_path` | **0** |
| `if` field (Claude Code's native path filter) | **0** |
| control, known present: `tool_input` | 5 |
| control, freshly invented: `zzvraknil5522` | 0 |

So **the Codex hook script MUST filter paths itself**, and it has a harder job than in Claude
Code: there is no `file_path` field at all. `$CX/hooks.md:595` — `Bash` and `apply_patch` both
put their payload in **`tool_input.command`**, so a path filter must *parse the apply_patch
body*. Claude Code hands you a pre-resolved absolute `file_path`; Codex does not.

Tool coverage (`$CX/hooks.md:~360`): `apply_patch` matches as `apply_patch`, `Edit`, OR `Write`.
⚠️ **Hosted tools such as `WebSearch` do NOT go through the hook path at all**, and "Some
specialized tool paths can opt out... Treat tool hooks as a useful guardrail, **not a complete
enforcement boundary**."

### Q7: Codex DOES have a `permissions.deny` equivalent — and it is NOT the hook

`$CX/agent-configuration__rules.md`. Codex "**Rules**" are **not** instruction files (do not
confuse them with `.claude/rules/`): they are a `.rules` file of `prefix_rule()` entries
controlling which commands may run outside the sandbox.

```python
prefix_rule(pattern = ["gh","pr","view"], decision = "prompt",
            justification = "...", match = [...], not_match = [...])
```

- `decision` ∈ `allow` (default) | `prompt` | **`forbidden`** ("Block the request without
  prompting"). **"Codex applies the most restrictive decision when more than one rule matches
  (`forbidden` > `prompt` > `allow`)"** — the same deny-first precedence as Claude Code.
- Located at `rules/*.rules` next to any active config layer: `~/.codex/rules/default.rules`,
  Team Config locations, and `<repo>/.codex/rules/` (**trusted projects only**).
- Admins can enforce `prefix_rule` entries from `requirements.toml`.
- Marked **experimental and may change**.
- Requires a **restart** to pick up.
- ⚠️ It is **command-prefix** scoped, not path scoped. There is no Codex equivalent of
  `Read(./secrets/**)` / `Edit(docs/**)` in this mechanism.

Codex `PreToolUse` deny shape (`$CX/hooks.md:600`): `hookSpecificOutput.permissionDecision:
"deny"` + `permissionDecisionReason`; the older `{"decision":"block","reason":...}` is also
accepted; `exit 2` + stderr also works. ⚠️ `permissionDecision: "ask"`, `continue:false`,
`stopReason`, `suppressOutput` are **parsed but NOT supported** on PreToolUse — Codex marks the
hook run failed, reports the error, **and continues the tool call** (fail-open).

### Codex instruction files: directory-walk, NOT glob — no path-scoped rules exist

`$CX/agent-configuration__agents-md.md:12`: Codex "walks down" from the project root to your
**current working directory**, taking at most one file per directory
(`AGENTS.override.md` → `AGENTS.md` → `project_doc_fallback_filenames`). Combined size capped by
`project_doc_max_bytes`, **32 KiB default**, and files are dropped once the cap is reached.

That is **cwd-determined at launch**, not lazily triggered by reading a file. Control-armed
probe over the 118-page Codex tree: no `paths:` instruction frontmatter exists
(the only `paths:` hit is a GitHub Actions snippet in `security__plugin__code-changes.md:262`;
control `AGENTS.md` → 24 files, fresh control `qxvthrum7741` → 0).

**Conclusion: Claude Code's `paths:` mechanism has NO Codex equivalent. On Codex, path-scoped
injection must be built out of a `PreToolUse`/`PostToolUse` hook that parses
`tool_input.command` itself.**

---

## 8. What this repo already has

⚠️ `mise run graphify-query` returned `[!] TRUNCATED: showing 49 of 223 nodes` — per
`.claude/rules/graphify-first.md` that is an "unavailable" state, so this inventory is read from
source, not from the graph.

### `.claude/settings.json` hooks (5 handlers, 4 events)

| Event | matcher | Command | What it does |
|---|---|---|---|
| `PreToolUse` | `Bash\|AskUserQuestion\|Edit\|Write\|NotebookEdit` | `scripts/pretooluse-guard.sh` (t=20) | `hook_guard` command redirects + `branch_guard` default-branch write deny + `ask_quality` question gate |
| `PreToolUse` | `Bash\|Grep` | `scripts/graphify-hook-guard.sh search` (t=15) | the graphify-first nudge on searches |
| `PreToolUse` | `Read\|Glob` | `scripts/graphify-hook-guard.sh read` (t=15) | same, on reads |
| **`PostToolUse`** | **`Edit\|Write\|NotebookEdit`** | **`dotfiles-setup mise-config-context` (t=20)** | ⭐ **path-scoped injection — see below** |
| `SessionStart` | `startup\|resume` | `web-setup.sh` (remote) else `tool-currency-check` + `doctor` (t=600) | currency drift + project doctor |
| `SessionEnd` | (none) | `command-audit` → `.agent/command-audit.md` (t=120) | mines the transcript for one-off commands |

**No `if` field is used on any handler** — all four PreToolUse handlers filter by tool name only
and re-implement path logic in the script. The native `if` filter (`hooks.md:424`) is unused.

### ⭐ `mise_config_context.py` — this repo ALREADY does path-scoped injection, with dedup

`python/src/dotfiles_setup/mise_config_context.py` is a working implementation of exactly the
mechanism being designed. Before designing anything new, read it:

- **Path filter**: `MISE_CONFIG_GLOBS` (7 globs), `fnmatch` against the **repo-relative resolved**
  path; anything outside the repo root returns False.
- **Injection**: `hookSpecificOutput.additionalContext` on `PostToolUse`.
- **Once-per-session dedup, hand-rolled** (because `once: true` is ignored in settings files):
  marker file at `.agent/state/mise-config-context/<key>.seen`, pruned at a 7-day age floor.
- ⭐ **The dedup key is `f"{session_id}--{agent_id}"`, not `session_id`** — its docstring records
  the measured defect: "Keyed on session alone, the first agent to touch a mise config consumed
  the reminder for every sibling subagent in the same session — confirmed by replay in a cold
  review (agent A got 1,240 bytes, agent B zero)." **Any new injector must key the same way.**
- **Fail-open on purpose**, in both directions: no `session_id` ⇒ emit; marker unwritable ⇒ emit
  ("a repeating reminder is visible and fixable; a gate that quietly stopped firing is neither").
- **Injection-defense-aware phrasing**: every line is a factual statement, per `hooks.md`'s
  prompt-injection warning.
- **Security detail worth copying**: the path is `json.dumps`-escaped into the message because
  `fnmatch`'s `*` matches a newline, so a crafted filename could otherwise carry
  newline-separated instruction text.
- Its docstring also states the design reason the caller will need:
  **"A `Write` that replaces `mise.toml` wholesale never READS it, so a `paths:`-scoped rule
  would be absent in exactly the case it exists for. The hook fires on the edit itself."**

### `.claude/rules/` — 2 of 26 are path-scoped; 24 are eager

Only two files carry ANY frontmatter, and both use `paths:`:

- `ci-local-parity.md` → `.github/workflows/*.yml`, `hk.pkl`, `mise.toml`,
  `.devcontainer/mise-system.toml`
- `md-size-budgets.md` → `hk.pkl`, `**/CLAUDE.md`, `**/AGENTS.md`, `.claude/rules/*.md`,
  `.claude/skills/**/SKILL.md`

The other 24 have no frontmatter at all and therefore load **every session, unconditionally**.
That is the measured eager-corpus mass from `project_session_2026-08-31.md`.

⚠️ Note `ci-local-parity.md`'s `.github/workflows/*.yml` — a single-segment pattern. Per
`$CC/memory.md` it matches that directory only, which is correct here. But `mise.toml` and
`hk.pkl` are root-relative bare names; per the `*.md` row in the pattern table those match the
project root only, which is also what is wanted. Both rules look correctly written.

### `.codex/hooks.json` — a byte-level mirror of the Claude hooks, minus PostToolUse

3 `PreToolUse` handlers + `SessionStart` + `SessionEnd`, identical commands.
**It does NOT carry the `PostToolUse` mise-config-context injector** — so the one piece of
path-scoped injection this repo has is **Claude-only**; Codex sessions get nothing.

⚠️ **REAL DEFECT (control-armed): `.codex/hooks.json` interpolates `${CLAUDE_PROJECT_DIR:-.}`,
and Codex does not set that variable.**

| Probe over the 118-page Codex doc tree | Files |
|---|---|
| `CLAUDE_PROJECT_DIR` | **0** |
| control, known present: `CODEX_HOME` | 22 |

`$CX/hooks.md:307` lists the env Codex gives hook commands: `PLUGIN_ROOT`, `PLUGIN_DATA`, and
`CLAUDE_PLUGIN_ROOT`/`CLAUDE_PLUGIN_DATA` "for compatibility" — **`CLAUDE_PROJECT_DIR` is not
among them, and those three are documented for PLUGIN hooks only.** So every command in
`.codex/hooks.json` silently falls back to `.` (the cwd). It works only while Codex's cwd is the
repo root. This is the *exact* shape of #343 (a relative hook path meaning the guard never ran
off-root), on the Codex side, unfixed. **SUSPECT rather than CONFIRMED for the runtime
consequence** — I did not run a live Codex probe; what is confirmed is that the variable is
undocumented in Codex and that the fallback is `.`.

---

## Verdict table

| # | Verdict | Claim | Corpus + control arm |
|---|---|---|---|
| 1 | CONFIRMED | `paths:` frontmatter in `.claude/rules/*.md` is real, shipped, glob-based, brace-expanding | `$CC/memory.md`, `claude-directory.md:169`, `glossary.md:251`; repo has 2 live users |
| 1b | CONFIRMED | It triggers when Claude **READS** a matching file — so a blind `Write` never fires it | `$CC/memory.md` "trigger when Claude reads files matching the pattern, not on every tool use"; repo's own `mise_config_context.py` docstring reaches the same conclusion independently |
| 2 | CONFIRMED | `hookSpecificOutput.additionalContext` is the model-context field; top-level placement is silently ignored | `$CC/hooks.md:970`, `hooks-guide.md` |
| 2b | CONFIRMED | PreToolUse/PostToolUse/PostToolUseFailure carry `tool_input.file_path`, **always absolute**; UserPromptSubmit carries **no path at all** | `$CC/hooks.md:1558`, `:1928`, `:1308` |
| 2c | CONFIRMED | ⭐ Hooks have a **native `if` path filter** using permission-rule syntax (`"Edit(*.ts)"`), on tool events only, one rule each, best-effort | `$CC/hooks.md:424` |
| 3 | CONFIRMED | **No** harness dedup of `additionalContext` — all values from all hooks are delivered | `$CC/hooks.md:993` |
| 3b | CONFIRMED | `once: true` exists but is **ignored in settings files** (skill frontmatter only) | `$CC/hooks.md:430` |
| 3c | CONFIRMED | `session_id` (+ `agent_id` inside subagents) is the available dedup key | `$CC/hooks.md` common input fields; repo's measured agent-A/agent-B defect |
| 4 | CONFIRMED | `permissions.deny` **blocks in every mode including `bypassPermissions`**; hook decisions never override it | `$CC/permission-modes.md:30`, `permissions.md:64`, `:495` |
| 4b | CONFIRMED | The PreToolUse hook **fails open** — bad path (127), exit 1, timeout, parse failure all proceed | `$CC/hooks.md:820`, `:839`, Warning box |
| 4c | **UNVERIFIED** | "the hook deny applies even in bypassPermissions mode" (this repo's claim) — the docs make that claim for deny **RULES**, not for hooks | no doc statement found either way; needs a live probe |
| 5 | CONFIRMED | `FileChanged` exists, is filesystem-watcher-driven, carries `file_path`+`event`, and **cannot inject context or block** | `$CC/hooks.md:2787`, `:876`, `:1025` |
| 5b | CONFIRMED | `InstructionsLoaded` observes every path-scoped rule load (`load_reason:"path_glob_match"`, `globs`, `trigger_file_path`) but its output is discarded | `$CC/hooks.md:1261` |
| 6 | CONFIRMED | Codex has 11 hook events; `additionalContext` works; **matcher is tool-name regex only, no path dimension, no `file_path` field, no `if`** | `$CX/hooks.md:25,320,595`; controls `tool_input`→5, `zzvraknil5522`→0 |
| 7 | CONFIRMED | Codex's deny equivalent is `prefix_rule(decision="forbidden")` in `.rules` — command-prefix scoped, experimental, `forbidden`>`prompt`>`allow` | `$CX/agent-configuration__rules.md:60-64` |
| 7b | CONFIRMED | Codex has **no** path-scoped instruction files; AGENTS.md is a cwd directory-walk capped at 32 KiB | `$CX/agent-configuration__agents-md.md:12`; controls `AGENTS.md`→24, `qxvthrum7741`→0 |
| 8 | CONFIRMED | This repo **already ships** path-scoped injection: `mise_config_context.py` on PostToolUse, with per-`session--agent` marker dedup | source read |
| 8b | SUSPECT | `.codex/hooks.json` uses `${CLAUDE_PROJECT_DIR:-.}`, which Codex does not set ⇒ silent fallback to cwd | `CLAUDE_PROJECT_DIR`→0 files vs `CODEX_HOME`→22; no live Codex probe run |

## GitHub repos touched

- [anthropics/claude-code](https://github.com/anthropics/claude-code) — offline vendor doc tree
  (`agent-harness-docs/docs/claude-code`, 192 pages) for rules, hooks, permissions.
- [openai/codex](https://github.com/openai/codex) — offline vendor doc tree
  (`agent-harness-docs/docs/codex`, 118 pages) for hooks, rules, AGENTS.md discovery.
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo audited.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — host of the
  offline doc corpus.
