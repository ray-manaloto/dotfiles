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
