# planning-with-files 3.12.0 — findings (in progress)

Cache root `$P` = `~/.claude/plugins/cache/planning-with-files/planning-with-files/3.12.0`

## Q1 — PostToolUse output

`hooks/hooks.json` PostToolUse: matcher `Write|Edit|Bash`, timeout 10, cmd `sh $P/hooks/claude-hook.sh post-tool-use`.
(PreToolUse matcher is WIDER: `Write|Edit|Bash|Read|Glob|Grep`.)

`hooks/claude-hook.sh:103-111`:
```
    pre-tool-use)
        emit_context "PreToolUse" "pretool" ;;
    post-tool-use)
        [ -f "$RESOLVE_PLAN_DIR" ] || exit 0
        _plan_dir=$(active_plan_dir) || exit 0
        [ -n "$_plan_dir" ] && [ -f "${_plan_dir}/task_plan.md" ] || exit 0
        emit_system_message "[planning-with-files] Update progress.md with what you just did. If a phase is now complete, update task_plan.md status."
        ;;
```
- Emits a FIXED, CONSTANT string via `{"systemMessage": "..."}` (`claude-hook.sh:86-91`).
- Fires on EVERY Write, Edit and Bash tool call. No throttle, no dedupe, no state file, no
  proportionality to plan changes. It does not read the plan content at all — only checks
  that `task_plan.md` resolves.
- Silent ONLY when: `PLANNING_DISABLED=1` (`:10`), `CLAUDE_PLUGIN_ROOT` empty (`:14`),
  `scripts/resolve-plan-dir.sh` missing (`:107`), or no resolvable `task_plan.md` (`:108-109`).
- NOT load-bearing: writes nothing, no ledger append, no phase tracking, no gate state.
  Purely advisory nudge. Stop gate is a separate path (`stop` -> `scripts/gate-stop.sh`).

### Q1 — harness semantics (KB offline docs, step 00)
- `hooks.md:926` — `systemMessage`: "Warning message shown to the **user**."
- `agent-sdk__hooks.md:858` — "shows a message to the user, **not the model**. To pass context to the
  model instead, return `additionalContext`."
- `agent-sdk__typescript.md:1439` — surfaces as an informational banner "with each line prefixed by
  the hook's name, such as `PostToolUse:Bash says:`". <- that is the exact spam shape.
- => The nudge text is ADDRESSED to Claude but DELIVERED to the operator. It is not `additionalContext`,
  so it does not even reach the model. Pure operator-facing noise.
- `hooks.md:704` ("Disable or remove hooks"): "**There is no way to disable an individual hook while
  keeping it in the configuration.**" `disableAllHooks` is all-or-nothing.
- `settings-reference.md:2645` (`env`): reaches "every session and for the subprocesses Claude Code
  starts from it" — so `PLANNING_DISABLED` in settings `env` should reach the hook process. The
  ignore-list (`CLAUDE_CONFIG_DIR`, `HOME`, `XDG_*`, …) does not cover arbitrary names.

### Q1 — the two routes, and which one is live
`skills/planning-with-files/SKILL.md` frontmatter ALSO declares PostToolUse (matcher `Write|Edit`,
no Bash) but every one of its hook bodies opens with
`[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && exit 0` — self-suppressing under a plugin install.
So on this machine only `hooks/hooks.json` fires, with the WIDER `Write|Edit|Bash` matcher.

### Q1 — knob inventory
| Knob | Where | Effect on PostToolUse spam | Cost |
|---|---|---|---|
| `PLANNING_DISABLED=1` | `claude-hook.sh:10` (first line after `set -u`) | silences it | ALL 6 pwf hooks die: SessionStart recovery, UserPromptSubmit/PreToolUse injection, PreCompact flush, Stop gate |
| no resolvable `task_plan.md` | `claude-hook.sh:107-109` | silent | no plan = no plugin at all |
| delete the PostToolUse block from `hooks/hooks.json` | plugin cache | silences exactly it, keeps the other 5 | edit lives in `~/.claude/plugins/cache/...`; a plugin update overwrites it. Not tracked, not reviewable |
| narrow the matcher to `Write\|Edit` in `hooks/hooks.json` | plugin cache | drops the Bash firings (the bulk) | same cache-volatility cost |
| `disableAllHooks: true` | settings | silences it | kills THIS repo's own PreToolUse guard + branch guard. Unacceptable here |
| disable the plugin (`enabledPlugins`) | `.claude/settings.json` | silences it | loses pwf entirely |
| `PWF_INJECT`, `.mode` tokens (`autonomous`/`gate`/`inject-smart`/`plan-guard-off`), `PWF_PLAN_GUARD`, `PLAN_ID`, `PWF_SESSION_ID`, `PWF_GATE_CAP`, `PWF_MODE` | inject-plan.sh / check-complete.sh / pi runtime | **NONE** — the post-tool-use branch never calls `inject-plan.sh`; it only stats `task_plan.md` | n/a |

Control arm for "no knob exists": the same grep DOES find knobs — `PWF_` returns 15 distinct names
(724 `PWF_PLAN_ROOT`, 59 `PWF_GATE_CAP`, …) and `PLANNING_DISABLED` returns 240 hits, while a
freshly-invented token `ZQWVTX_` returns 0. The probe discriminates.

### Q1 — load-bearing? NO
`post-tool-use` writes nothing: no ledger append, no SHA cache, no `.stop_blocks`, no phase state.
`.codex/hooks/post-tool-use.sh:1-14` is the whole body (an `echo` behind an `-f` test).
Control arm: the same grep for `ledger-append` DOES return hits — but every one is a doc, the
script itself, or `sync-ide-folders.py`; `SKILL.md:431` says workers append to the ledger
themselves. No hook calls it. The Stop gate reads the ledger for its stall detector; PostToolUse
never feeds it.

---

## Q2 — Codex route

### What it places on disk (docs/codex.md, "Installation")
There is **no installer binary** — the documented path is `git clone` to /tmp + `cp -r`.
- Method 1 (recommended, workspace): writes INTO the project — `.agents/skills/planning-with-files/`,
  `.codex/hooks.json`, `.codex/hooks/`, and the doc tells you to `git add` + commit them.
- Method 2 (personal): writes OUTSIDE the project — `~/.agents/skills/planning-with-files/`,
  `~/.codex/hooks/`, `~/.codex/hooks.json` (and warns: MERGE, do not overwrite an existing one).
- Plugin package: `.codex-plugin/plugin.json` -> `"skills": "./.agents/skills/"`,
  `"hooks": "./hooks/codex-hooks.json"`, resolved via `${PLUGIN_ROOT}` (cache-safe).
  docs/codex.md: plugin mode and standalone `.codex/hooks.json` mode are ALTERNATIVES — enabling
  both duplicates every reminder, because Codex runs every matching hook from every active source.

Relative to `do-not.md` #8: nothing to run, so nothing to sandbox. Method 1 is a plain copy into
the repo (reviewable diff); Method 2 writes under `$HOME` (violates the repo's
no-user-level-file-updates preference). Neither touches `AGENTS.md` — grep of docs/codex.md for
AGENTS.md returns nothing (control arm: the same doc DOES name `.agents/skills/`, `.codex/hooks/`,
`.codex-plugin/plugin.json`).

### Hooks: codex gets SEVEN, one MORE than Claude Code
`.codex/hooks.json` declares SessionStart, UserPromptSubmit, PreToolUse, **PermissionRequest**,
PostToolUse, PreCompact, Stop. Claude Code's `hooks/hooks.json` has six (no PermissionRequest).
So the codex route is NOT skill-prose-only — it is the fuller hook surface.
- PostToolUse matcher on codex is `Bash|apply_patch|Edit|Write` — WIDER than Claude's
  `Write|Edit|Bash` (adds `apply_patch`).
- Same message, same shape: `.codex/hooks/post_tool_use.py:16-18` runs `post-tool-use.sh` and
  emits `{"systemMessage": stdout}`; `post-tool-use.sh:12` is the identical string.
  => adopting codex does not escape the spam, it widens it.
- Codex hooks are enabled by default; `[features] hooks = false` disables them, and new/changed
  hooks must be trusted via `/hooks`.
- Requires `python3` and `sh` on PATH (macOS/Linux).

### Shared state: YES, same files, and both can write
`.codex/hooks/codex_hook_adapter.py:96-116` `effective_plan_root(cwd)` returns the payload cwd
unless `PWF_PLAN_ROOT` pins it. `post-tool-use.sh:8` then calls the same `resolve-plan-dir.sh`.
So a `codex exec -C <repo>` in this checkout resolves the SAME `.planning/` / `task_plan.md` as
the Claude session. Both writing = last-write-wins clobber; that is exactly the defect the
v3.10.0 parallel-write guard (`PWF_PLAN_GUARD`) was added to *detect* (it warns, never blocks —
SKILL.md:388) .
One asymmetry: the codex adapter gates on `is_session_attached` (`codex_hook_adapter.py:131-148`)
— but `scripts/inject-plan.sh:275-385` shows the canonical Claude dispatcher honours
`PWF_SESSION_ID` + `.planning/sessions/<id>.attached` too. My initial guess that this was
codex-only was WRONG; corrected by reading inject-plan.sh.

### Version requirements / the stale-inlined-hook-body question
CHANGELOG.md:190, under the `## [3.9.0] - 2026-08-01` heading (heading at CHANGELOG.md:186):
"`PLANNING_DISABLED=1` did nothing on eleven of the thirteen hook bearing install routes …
**the reporter's `.codex` route included**, still carried the v2.43 hook body inlined in their
YAML scalars. Besides missing the opt out they lacked the symlink containment guard, the SHA
cache key fix, nonce delimiters, the v3 attestation refusal, the ledger summary and
`PWF_INJECT=smart`, and they still wrote the SHA cache to the world writable
`${TMPDIR:-/tmp}/pwf-sha` … All eleven now dispatch to the same versioned script."
=> **Fixed in v3.9.0.** Cached version is 3.12.0, so this route is fixed here.
Also 3.9.0 fixed: Codex Stop hook could never find its script; a shared-parent cwd injected the
wrong project's plan (#212).
docs/codex.md caveat: "Upgrading from v3.10.0 or earlier changes three command definitions in
`.codex/hooks.json`. Review and trust the updated definitions with `/hooks`."

### `PLANNING_DISABLED` on codex — documented and load-bearing for us
docs/codex.md, "Opting out for one-shot runs (CI, `codex exec`)":
`PLANNING_DISABLED=1 codex exec -o review.md '...'`. All seven hooks exit before reading the
plan; PreToolUse still emits its `allow` decision so tool calls proceed. Interactive sessions in
the same directory are unaffected. This is the plugin's own recommended shape for exactly our
`codex exec` lanes.

---

## Q3 — slug mode

### Is it recommended? YES for parallel work; root mode stays the default.
- `docs/attestation-locking.md`, "Recommended parallel workflow": "**Use slug-mode for parallel
  sessions**" — each slug gets its own `task_plan.md` and `.attestation`, which "avoids same-file
  contention".
- Same file, "When fallback matters": in legacy root mode "both sessions share one plan file and
  one attestation file. The atomic rename keeps the attestation file valid, **but it does not
  make the shared plan file a safe parallel workspace**."
- README.md:110 — slug dirs are for "Parallel tasks"; root mode is what `/plan` and a bare
  `init-session.sh` produce (`init-session.sh:378-388`, the `else` branch).
- `scripts/init-session.sh` with a name arg creates `.planning/YYYY-MM-DD-<slug>/` (SKILL.md:223).

### What it buys / costs
Buys: per-plan isolation of the three files + `.attestation` + `.mode` + `.stop_blocks`; auto
de-dup of slug collisions (`init-session.sh:358-362` appends `-2`, `-3`).
Costs: resolution becomes ambiguous. Order is `$PLAN_ID` -> `.planning/.active_plan` ->
**newest dir by mtime** -> legacy root (`resolve-plan-dir.sh:4-8`, `:265-267`). The mtime
fallback means an untouched-but-newer plan dir can win.

### Is `.active_plan` adequate for multiple concurrent agents in one checkout? NO — and the docs say so.
- It is ONE pointer per project, and `init-session.sh:369` writes it **unconditionally** on every
  new slug plan: creating plan B silently repoints every unpinned agent away from plan A.
- The script's own next line (`:373-374`) prints: "Pin this terminal to the plan for parallel
  sessions: `export PLAN_ID=<id>`" — i.e. the pointer is explicitly not the isolation mechanism;
  the per-process env var is.
- `docs/attestation-locking.md` likewise: "Pin a terminal to one plan when needed:
  `export PLAN_ID=...`".
- The concurrency limit is acknowledged head-on in `SKILL.md:386-390` (parallel-write guard,
  v3.10.0): "Two sessions sharing one plan directory can both write `task_plan.md` from the same
  read. The later write silently discards the earlier one's work, and nothing notices … The guard
  … never blocks … **Known ceiling: the marker is keyed on the plan path, not the session, so the
  warning reaches whichever session fires next rather than specifically the one holding the stale
  copy. Per-session keying needs `PWF_SESSION_ID`, which most hosts never set.**"
- The only real per-agent isolation is: `PLAN_ID` (cwd-relative slug), `PWF_PLAN_ROOT` (absolute
  root pin, v3.9.0), or `.planning/sessions/<id>.attached` + `PWF_SESSION_ID` — and the last one
  fails CLOSED for any session without an ID (`inject-plan.sh:385` prints an explicit notice).

### Migration path
`MIGRATION.md` covers ONLY v1->v2 and v2->v3. It contains no slug-mode section at all
(control arm: the same file DOES have "Migration Steps", "Breaking changes", "Quickstart: try
gated mode in two commands"). The slug migration is documented instead as: run
`init-session.sh <slug>`; legacy root files keep working untouched (SKILL.md:223,
`resolve-plan-dir.sh:8` falls back to root). No conversion step, no deprecation.
