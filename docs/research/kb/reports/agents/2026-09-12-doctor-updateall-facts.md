# Doctor / update-all fact-finding (2026-09-12)

Read-only fact-finding for a design discussion. Every claim below carries a
`file:line` anchor. Absences carry a named control arm.

---

## Q1 — `~/.config/mise/config.toml` `update-all` task family

The file is **682 lines**, not 304; the update-task block runs
`~/.config/mise/config.toml:329-682` (the section banner
`# --- update tasks ---` is at `:329`). Task headers:

| Task | Line |
|---|---|
| `[tasks."update:brew"]` | `~/.config/mise/config.toml:421` |
| `[tasks."update:mise"]` | `:443` |
| `[tasks."update:claude"]` | `:503` |
| `[tasks."update:check"]` | `:592` |
| `[tasks."update:all"]` | `:632` |
| `[shell_alias]` | `:657` |

### `[tasks."update:all"]` — `:632-655`

```toml
[tasks."update:all"]
description = "update all tools (brew, mise, claude) — the one command to run"
depends = ["update:brew", "update:mise", "update:claude"]
run = "mise doctor"
```

(`depends` is `:654`, `run` is `:655`; everything between `:634` and `:653` is
the DAG comment.) The DAG is a **diamond**, deduplicated by mise: `update:all`
depends on `update:brew` directly *and* on `update:mise`, which carries
`wait_for = ["update:brew"]`. Recorded measurement at `:640-652`: brew and
claude interleave from t0, mise appears only after brew ends, then `update:all`'s
own `mise doctor` closes out — `rc=0 in 57.0s`.

### The full `update:*` subtask list

Exactly five: `update:brew`, `update:mise`, `update:claude`, `update:check`,
`update:all`. Control arm: `grep -n 'tasks\.' ~/.config/mise/config.toml`
returns 6 matches — the five above plus a prose mention at `:579` ("226 plugins
would need 226 declared tasks"), i.e. the grep does return non-task lines, so a
5-task answer is a real enumeration and not a blind pattern.

### `[tasks."update:brew"]` — `:421-440`

```toml
[tasks."update:brew"]
description = "update brew tools"
run = """
set -euo pipefail
brew update
brew upgrade --yes
"""
```

A leaf: no `depends`, no `wait_for`.

### `[tasks."update:mise"]` — `:443-501`

```toml
[tasks."update:mise"]
description = "update mise tools"
wait_for = ["update:brew"]
run = """
set -euo pipefail
mise config ls
mise self-update -y
mise upgrade --bump -y -j 8
mise install --system -y
mise install -y
mise reshim -f -y
mise outdated
mise doctor
"""
```

`wait_for` (`:473`) rather than `depends` is deliberate and *measured*: the
ordering is a dylib dependency — `~/.local/share/mise/installs/python/*/bin/python3`
links `/opt/homebrew/opt/gettext/lib/libintl.8.dylib`, so a concurrent
`brew upgrade` swapping gettext produces a `dyld: Library not loaded` mid-run
(`:462-467`). Control arm recorded in the same comment: hk, typos and uv link
**zero** homebrew dylibs (static Rust), so the finding is specific, not universal.

### `[tasks."update:claude"]` — `:503-590`

**It has no `run` at all.** It is a `file =` task pointing at the Python script:

```toml
[tasks."update:claude"]
description = "update claude, marketplace and plugins"
file = ".config/mise/scripts/update_claude.py"
```

- `description` is `:519`, `file` is `:590`. Everything between is comment.
- **No `depends`, no `wait_for`** — a leaf by design (`:505-507`: "Independent
  of brew and mise by design, so under `update:all` it runs concurrently with
  brew from t0").
- `{{config_root}}` is deliberately *not* used for the path: the comment at
  `:585-588` records that for the GLOBAL config `{{config_root}}` resolves to
  `~`, not `~/.config/mise`, so the `.config/mise` segment is written out.
- Recorded measurement (`:510-511`): `rc=0 in 57.1s`, "225 checked, 0 updated,
  16 refreshed, 0 failed".

### `[tasks."update:check"]` — `:592-630`

Isolated by design (no `depends`, nothing depends on it). Three exit codes kept
distinct (`:604-607`): `0` nothing outdated, `1` something outdated, `2` a
source **could not be checked**. Body reads `brew outdated --json` and
`mise outdated --json` through `jq -e` structure tests, plus
`mise upgrade --dry-run-code`.

### The `[guard]` wrapper — `~/.config/mise/config.toml:657-682` + `mise_update_guard.py`

`update-all` is **not** `mise run update:all`. It is a `[shell_alias]` calling
the guard script directly:

```toml
[shell_alias]
update-claude = "$HOME/.config/mise/scripts/mise_update_guard.py update:claude"
update-all = "$HOME/.config/mise/scripts/mise_update_guard.py update:all"
update-check = "$HOME/.config/mise/scripts/mise_update_guard.py update:check --check-only"
```

(`:676`, `:677`, `:678`.)

The line `[guard] update:all finished rc=1` is printed at
**`~/.config/mise/scripts/mise_update_guard.py:249`**:

```python
    started = time.monotonic()
    proc = subprocess.run(["mise", "run", args.task], check=False)
    duration = time.monotonic() - started
    log_line(args.task, labels, duration, proc.returncode, note)
    print(f"[guard] {args.task} finished rc={proc.returncode} in {duration:.1f}s -> {LOG_PATH}")
    return proc.returncode
```

(`:244-250`.) So **the guard's rc is `mise run <task>`'s rc, passed through
verbatim** — an `rc=1` from `update:all` is `mise run update:all` failing, which
under the DAG almost always means `update_claude.py` returned 1 (its only
non-zero-on-success path; see Q2).

Guard states (`:199-243`): `LIVE` holder → refuse by name with pid + what it is
installing (`RC_REFUSED`, `:213`); `UNKNOWN` (markers exist, `lsof` unavailable)
→ refuse (`:224`); `--check-only` returns **before** any clearing (`:232-238` —
the comment records that the first version cleared first and "silently deleted
three real markers on its first run"); `STALE` → clear and proceed (`:241-243`).
Every run appends one audit line to `LOG_PATH` via `log_line` (`:187-196`),
which never raises.

Why the guard is a shell alias and not a mise task, verbatim
(`~/.config/mise/config.toml:668-672`): "A mise task runs INSIDE `mise run`,
which resolves tools first — so the guard would block on the very lock it exists
to detect, and report nothing."

---

## Q2 — `~/.config/mise/scripts/update_claude.py` (304 lines)

Step by step, in `main()` (`:234-300`):

1. **PATH check** — `shutil.which("claude") is None` → print to stderr and
   `return 127` (`:235-237`).
2. **Jobs** — `CLAUDE_UPDATE_JOBS`, default `DEFAULT_JOBS = 8` (`:63`, `:239`).
3. **`update_cli()`** (`:91-104`) — **strictly first, strictly alone**, because
   it replaces the binary every later step invokes:

   ```python
   print("==> claude update", flush=True)
   rc, out = _run(["claude", "update"], PRELUDE_TIMEOUT)
   if out:
       print("    " + out.replace("\n", "\n    "), flush=True)
   if rc != 0:
       print(f"    ! claude update exited {rc}", flush=True)
   return {"step": "claude update", "rc": rc}
   ```

   ⚠️ **A non-zero `claude update` does NOT fail the script.** Its rc is only
   recorded into the summary dict; nothing reads it back for the exit code.
4. **`update_marketplaces(jobs)`** (`:119-156`) — enumerates names via
   `claude plugin marketplace list --json` (`:109`), then fans out
   `claude plugin marketplace update <name>` over a `ThreadPoolExecutor`
   (`:141-155`). Falls back to the single all-marketplaces call when the list
   cannot be read (`:134-137`) so a change in that command's output can never
   silently skip the refresh. Recorded reason for the fan-out (`:122-125`): the
   single no-name call is sequential over 36 marketplaces and was "the silent
   ~2 minutes at the head of every run". Marketplace rcs are likewise recorded
   but **never gate the exit code**.
5. **`targets()`** (`:159-175`) — this is the one prelude step that CAN abort:

   ```python
   rc, out = _run(["claude", "plugin", "list", "--json"], PRELUDE_TIMEOUT)
   if rc != 0:
       print(f"claude plugin list --json failed (rc={rc}):\n{out}", file=sys.stderr, flush=True)
       raise SystemExit(rc or 1)
   try:
       rows = json.loads(out)
   except json.JSONDecodeError as exc:
       print(f"claude plugin list --json returned unparseable JSON: {exc}", file=sys.stderr, flush=True)
       raise SystemExit(1) from exc
   ```

   (`:161-169`.) Dedup is on the **(id, scope) PAIR** (`:170-175`), with **no
   `.enabled` filter** — `.enabled` is evaluated against the *current project*
   (measured, `:29-31`: 0 of 248 from `$HOME`, 9 from one repo, 0 from `/tmp`),
   so filtering on it made the task a silent no-op everywhere except inside a
   plugin-enabling repo.
6. **Group by id** (`:248-250`), then fan out `update_id` over the pool
   (`:259-267`). All scopes of ONE id run **sequentially** (`:212-231`) — a race
   fix, not an optimisation: versionless plugins share
   `cache/<marketplace>/<id>/unknown/`, and concurrent scopes produced an
   `ENOENT: copyfile` mid-copy.
7. **Per-plugin command** (`:204-209`):

   ```python
   rc, out = _run(
       ["claude", "plugin", "update", target["id"], "-s", target["scope"], "-y"],
       PLUGIN_TIMEOUT,
   )
   ```
8. **Classify** (`:188-201`) into `failed` / `current` / `refreshed` /
   `updated`, by substring match on `"already at the latest version"` (`:179`)
   and `"refreshed from source"` (`:185`).
9. **Summary JSON** written to `SUMMARY_PATH` (`:288-289`) —
   `$CLAUDE_UPDATE_JSON`, default `~/.config/mise/.update-claude.json` (`:65-68`).
   Fields: `elapsed_s`, `jobs`, `prelude`, `total`, `updated`, `refreshed`,
   `current`, `failed`, `failures[]` (each with id, scope, rc, output)
   (`:274-287`).

### What makes it exit non-zero

Three, and only three:

| Exit | Trigger | Line |
|---|---|---|
| `127` | `claude` not on PATH | `:237` |
| `rc or 1` | `claude plugin list --json` returned non-zero | `:164` |
| `1` | `json.loads` of that output failed | `:169` |
| `1` | **any** plugin update classified `failed` | `:300` — `return 1 if failed else 0` |

`failed` is `rc != 0` from `claude plugin update …` (`:196-197`), which includes
the timeout path: `_run` returns `124` on `subprocess.TimeoutExpired` (`:84-85`,
bound `PLUGIN_TIMEOUT = 180`, `:58`) and `127` on `OSError` (`:86-87`).

**So `[guard] update:all finished rc=1` means, in practice: at least one of ~225
plugin updates failed.** It does *not* mean `claude update` failed, and it does
*not* mean a marketplace refresh failed — both of those are recorded into the
JSON summary and then ignored by the exit code. `~/.config/mise/.update-claude.json`
`failures[]` is the machine-readable place to find out which plugin.

No `shell=True` anywhere in the file (`:74`, deliberate — `_run` at `:71-88`
takes an argv list).

---

## Q3 — the dotfiles project doctor

Three files:

| Piece | Path |
|---|---|
| Baseline (declared host setup) | `doctor.toml` — 265 lines |
| Implementation | `python/src/dotfiles_setup/doctor.py` — 1320 lines, 57 KB |
| Task | `mise.toml:630-…` — `[tasks.doctor]`, a thin caller |
| Hook wiring | `.claude/settings.json:108-119` — `SessionStart`, `matcher: "startup|resume"` |

### SessionStart wiring, verbatim (`.claude/settings.json:108-119`)

```json
"SessionStart": [
  {
    "matcher": "startup|resume",
    "hooks": [
      {
        "type": "command",
        "command": "if [ \"${CLAUDE_CODE_REMOTE:-}\" = \"true\" ]; then bash \"${CLAUDE_PROJECT_DIR:-.}/scripts/web-setup.sh\"; else mise -C \"${CLAUDE_PROJECT_DIR:-.}\" run tool-currency-check; DOTFILES_AMBIENT_PATH=\"$PATH\" mise -C \"${CLAUDE_PROJECT_DIR:-.}\" run doctor; fi",
        "timeout": 600
      }
    ]
  }
]
```

Two things to note. The hook runs **two** tasks — `tool-currency-check` then
`doctor`. And `DOTFILES_AMBIENT_PATH="$PATH"` is captured *by the hook*, before
mise rewrites `PATH`; without it the `path-drift` check is structurally blind
and says so as a finding rather than passing (`doctor.py:1192-1195`,
`path_drift.py:37-41`).

### The baseline schema

`doctor.toml` is **not** a list of uniform check records. It is six
purpose-built sections, each consumed by a named check:

| Section | Line | Consumed by |
|---|---|---|
| `[fnox]` | `doctor.toml:16` | `check_fnox_baseline`, `check_exec_only_not_leaked` |
| `[mcp]` | `:98` | `check_mcp_scope`, `check_mcp_pin` |
| `[mcp.mutating_tools]` | `:136` | `check_mcp_guard_coverage`, `check_live_servers` |
| `[listing]` | `:138` | `check_listing_budget` |
| `[graphify]` | `:169` | `check_graphify_skill_surface` |
| `[path_drift]` | `:203` | `check_path_drift` |

A complete real section, verbatim (`doctor.toml:169-202`):

```toml
[graphify]
# The graphify skill surface's REVIEWED, deliberate shape (issue: see the
# `graphify_skill_surface` hk step for the commit-time twin of this check).
# `.claude/skills/graphify/SKILL.md` is the full installed Claude Code
# bundle. `.agents/skills/graphify/SKILL.md` is a DELIBERATE hand-authored
# redirect stub carrying the `stub_marker` below — NOT `graphify agents
# install` output — so this check discriminates "the note was lost" from
# "the file was silently overwritten by a real install".
required_skill_files = [
    ".claude/skills/graphify/SKILL.md",
    ".agents/skills/graphify/SKILL.md",
]
stub_file = ".agents/skills/graphify/SKILL.md"
stub_marker = "DELIBERATE STUB"

# A codex-platform `graphify install` (the VENDOR installer, never ours)
# appends this literal line to the root AGENTS.md (do-not.md #8) — AGENTS.md
# IS tracked, so a landed append shows up in `git diff` too, but this check
# still needs to say so at session start, not only at the next commit.
forbidden_agents_md_marker = "use the installed graphify skill"
```

So the "schema" is **per-check, hand-shaped TOML keys**, read through
`_str_keys` / `_str_list` coercion helpers (`doctor.py:120-137`) with an absent
section degrading to `{}` (`Setup.fnox_baseline` etc., `doctor.py:224-234`).
There is no generic `[[check]]` array and no registry driven by the TOML.

### How checks are registered

A module-level tuple, `doctor.py:1216-1234`:

```python
CHECKS: tuple[tuple[str, Callable[[Setup], list[str]]], ...] = (
    ("mcp-env-opt-in", check_mcp_env_opt_in),
    ("mcp-scope", check_mcp_scope),
    ("fnox-baseline", check_fnox_baseline),
    ("fnox-exec-leak", check_exec_only_not_leaked),
    ("mcp-pin", check_mcp_pin),
    ("mcp-guard-coverage", check_mcp_guard_coverage),
    ("mcp-duplicate", check_mcp_duplicate),
    ("pin-currency-wired", check_pin_currency_wired),
    ("listing-budget", check_listing_budget),
    ("path-drift", check_path_drift),
    ("graphify-skill-surface", check_graphify_skill_surface),
)

#: Only run with ``--live``: each entry spawns subprocesses.
LIVE_CHECKS: tuple[tuple[str, Callable[[Setup], list[str]]], ...] = (
    ("mcp-live-tools", check_live_servers),
    ("mcp-health", check_mcp_health),
)
```

Contract details worth carrying into a design discussion:

- **Every check is a pure function of one `Setup` object** (`doctor.py:206-238`),
  a frozen dataclass holding `repo_root`, `baseline`, `servers`, `settings`,
  `local_settings`, `fnox`, `environ`, `listing`. Resolved once by `collect()`
  (`:377`). Tests drive a fixture without touching the real `$HOME`.
- **A check returns `list[str]` findings.** Empty list = pass.
- **Registration is asserted by a test**: `test_every_check_function_is_actually_registered`
  enumerates this module's `check_*` names and requires each to be in `CHECKS`
  — which is why `check_path_drift` is imported under the alias
  `shell_path_drift` (`doctor.py:85-90`), an imported `check_*` would be an
  unregistrable false positive.
- **Crashes are contained AND surfaced** (`run_checks`, `:1248-1279`): any
  exception is logged, appended to
  `~/.local/state/dotfiles/doctor-error.log` (`ERROR_LOG`, `:100`), and emitted
  as a finding of its own — "a doctor that quietly stops checking is worse than
  no doctor" (#343's lesson).
- **Exit code**: `doctor_main` (`:1303-1320`) returns `1` only under `--strict`
  *and* drift. On the SessionStart path it is silent when healthy and always
  exits 0.
- **Output shape** (`render`, `:1281-1301`): `DRIFT doctor[<name>]: <finding>`,
  plus `PASS doctor[<name>]` only with `--verbose`.

### Can the doctor shell out? — **Yes, and it already does, on the default path.**

Not "only inspects config/state". Three distinct classes:

1. **Default path, shells out.** `check_path_drift` → `dotfiles_setup.path_drift`,
   which runs `MISE_LS_COMMAND = ("mise", "ls", "--current", "--json")`
   (`path_drift.py:95`) via `subprocess` (`path_drift.py:74`). This is in
   `CHECKS`, so it runs on **every** SessionStart.
2. **Default path, imports rather than spawns.** `check_pin_currency_wired`
   (`doctor.py:785-812`) uses `importlib.util.find_spec("kb_setup.currency")` —
   it asserts the *delegate is runnable*, not the versions.
3. **`--live` only, spawns per server.** `probe_tools` (`doctor.py:866`) and
   `check_mcp_health` (`:1008`) each `subprocess.run(...)` with
   `_PROBE_TIMEOUT_S = 180.0` (`:101`). Explicitly held off SessionStart —
   `doctor.py:907-910`, verbatim: *"Off the SessionStart path by design (Ray,
   2026-07-29): a subprocess spawn per server every session is real latency for
   drift that changes rarely. Run it on demand with `mise run doctor -- --live`."*

**So adding a check that shells out to `claude …` is architecturally
precedented** — the only question is which tier it belongs in (default vs
`--live`), and the deciding criterion already written into the codebase is
per-session latency.

---

## Q4 — function hooks in this project

### There are NO production function hooks in this repository.

Control-armed. Absence arm:
`git ls-files | grep 'register\.ts' | grep -v '^tests/fixtures/'` returns exactly
one path — `docs/research/kb/raw/2026-09-11-anthropics-mods-sec-default-register.ts`,
a *harvested upstream source* saved as research raw material, not a registered
hook. Control arm, same command shape without the exclusion:
`git ls-files | grep -c 'register\.ts'` → **6**, so the grep does find
`register.ts` files and the narrowed result is a real enumeration.

Second arm: every tracked `.claude-plugin/plugin.json` in the repo —

```
tests/fixtures/fnhook/bad-event/.claude-plugin/plugin.json
tests/fixtures/fnhook/bad-return/.claude-plugin/plugin.json
tests/fixtures/fnhook/parse-error/.claude-plugin/plugin.json
tests/fixtures/fnhook/untyped/.claude-plugin/plugin.json
tests/fixtures/fnhook/valid/.claude-plugin/plugin.json
```

All five are **test fixtures**. `.claude/` itself has no `hooks/` directory
(`ls .claude/` → agent-memory-local, agents, CLAUDE.md, rules,
scheduled_tasks.lock, settings.json, settings.local.json, skills,
token-routing.md, types, ultrapowers-preferences.json, workflows, worktrees).

### Where a function hook WOULD live

`discover_plugin_dirs` (`python/src/dotfiles_setup/fnhook_gates.py:140-176`)
derives the set **from the tree**, not from a fixed path: any directory holding
**both** `.claude-plugin/plugin.json` and `hooks/hooks.json`. Two exclusions:
`FIXTURE_ROOT = "tests/fixtures/fnhook"` (`:28`) from the production gate, and
any plugin inside a **nested git checkout** (`_is_in_nested_checkout`, `:179-193`).
The nested-checkout rule is not hypothetical — the docstring records that CI
clones the sibling knowledge-base into `.rule-sync/`, that repo ships an
**untyped** function-hook plugin `kb-settings-guard`, and discovery on a GitHub
runner (2026-09-12) correctly flagged it, failing this repo's gate over another
repo's code.

### A registered hook, verbatim (`tests/fixtures/fnhook/valid/`)

`hooks/hooks.json`:

```json
{
  "description": "Valid typed function-hook module",
  "modules": ["./register.ts"]
}
```

`hooks/register.ts`:

```typescript
import type { Register } from "claude-code";

export const register: Register = (on) => {
  on("classic.PreToolUse", { tool: "Read" }, async (_$, e, next) => {
    const result = await next(e);
    return { ...result, additionalContext: ["fixture-valid"] };
  });
};
```

`.claude-plugin/plugin.json`:

```json
{
  "name": "fnhook-fixture-valid",
  "version": "1.0.0",
  "description": "Valid function-hook gate fixture",
  "author": { "name": "dotfiles test suite" }
}
```

### Which hook EVENTS are wired today

**Function-hook events wired: none** — there is no production module, so no
`on(...)` call exists outside fixtures. The single event any fixture names is
`"classic.PreToolUse"`.

The events wired today are all **command hooks**, in `.claude/settings.json`:

| Event | Matcher | Line |
|---|---|---|
| `PreToolUse` | `Bash\|AskUserQuestion\|Edit\|Write\|NotebookEdit` → `scripts/pretooluse-guard.sh` | `:54-64` |
| `PreToolUse` | `Bash\|Grep` → `scripts/graphify-hook-guard.sh search` | `:65-75` |
| `PreToolUse` | `Read\|Glob` → `scripts/graphify-hook-guard.sh read` | `:76-86` |
| `PostToolUse` | `Edit\|Write\|NotebookEdit` → `dotfiles-setup mise-config-context` | `:89-99` |
| `PostToolUse` | `Agent` → `hook_selfcheck subagent-contract` | `:100-110` |
| `SessionStart` | `startup\|resume` → currency-check + doctor | `:112-123` |
| `SessionEnd` | *(unscoped)* → `command-audit` | `:125-134` |
| `InstructionsLoaded` | *(unscoped)* → `instructions_observer` | `:136-145` |
| `SubagentStart` | *(unscoped)* → `hook_selfcheck subagent-contract` | `:147-156` |

(Line numbers are from the 6503-byte `.claude/settings.json` as of 2026-09-10.)

**Is there already a SessionStart function hook? No** — neither a function hook
nor any second SessionStart entry. There is exactly one SessionStart block, and
it is `"type": "command"`.

### `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` in `.claude/settings.json`

**It is not set — the key is absent from the `env` block.**

- Absence arm: `grep -n 'CLAUDE_CODE_ENABLE_FUNCTION_HOOKS' .claude/settings.json`
  → rc=1, no output.
- Control arm, same command shape, a token known present:
  `grep -n 'CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS' .claude/settings.json` →
  `6:    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",`, rc=0. The probe
  discriminates.

The `env` block (`.claude/settings.json:3-12`) holds eight keys:
`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`, `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD`,
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`,
`CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION`, `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`,
`CLAUDE_CODE_TASK_LIST_ID`, `OTEL_LOG_RAW_API_BODIES`.

The flag appears in the repo only as **documentation and research**: 
`.claude/types/README.md:8` and `:11` (the refresh recipe), and eight
`docs/research/kb/reports/agents/2026-09-11-*` files. It is also referenced in
code as a constant — `fnhook_gates.py:64`,
`_FUNCTION_HOOKS_FLAG = "CLAUDE_CODE_ENABLE_FUNCTION_HOOKS"` — which the gate
sets when it shells out to regenerate declarations, not something it reads from
settings.

### The two tasks and the types

```toml
[tasks.fnhook-gates]            # mise.toml:240
run = "uv run --project python dotfiles-setup fnhook-gates"        # :242

[tasks.fnhook-types-refresh]    # mise.toml:244
run = "uv run --project python dotfiles-setup fnhook-types-refresh" # :246
```

Outputs are `.claude/types/claude-code.d.ts` (347,960 B) and
`.claude/types/claude-code-mcp.d.ts` (439 B), plus `.claude/types/README.md`.
Generated from harness **2.1.269** on **2026-09-12** (`README.md:16-18`).

Two facts from `.claude/types/README.md:11-14` that matter for any gate design:
the flag is **mandatory** for `/plugin-types` to exist at all, and **without it
Claude Code reports an unknown command, writes nothing, and still exits zero** —
so the refresh task verifies the outputs exist and are non-empty rather than
trusting the process status. The declarations are also **session-dependent**
(`README.md:20-25`): `/plugin-types` includes the built-in tools available in
the generating session, so the drift gate normalizes only the bodies of
`BuiltinToolInputs` and `BuiltinToolResults` (`fnhook_gates.py:69-75`,
`normalize_claude_code_declarations` at `:345`).

The gates themselves (`fnhook_gates.py`, module docstring `:2-10`): Claude Code's
`claude plugin validate --strict` (`:195-214`) checks syntax and event names;
`tsc` checks handler return shapes; and an explicit typed-register assertion
(`_TYPED_REGISTER_RE`, `:66-68`, matching `export const register: Register`)
bridges them, because without it TypeScript accepts an `any`-typed module and
the second gate proves nothing. Both binaries are invoked as
`mise exec <tool>@<version> --` with the version read from `mise.toml` at
runtime (`tool_spec`, `:50-62`) — the comment at `:32-38` records that a bare
`mise exec -- claude` died on a GitHub runner with
`mise ERROR No version is set for shim: claude` while passing locally, i.e. the
host is not a control arm for CI.

---

## Q5 — machine-readable `claude` surfaces

Probed against the **installed** binary: `claude --version` → `2.1.269 (Claude Code)`.

### `claude doctor` — confirmed, no JSON

`claude doctor --help` in full:

```
Usage: claude doctor [options]

Check the health of your Claude Code installation. Reads settings files in the
current directory without a trust prompt. For a full checkup that can also fix
issues, run /doctor in a session.

Options:
  -h, --help  Display help for command
```

`-h` is the only option. Confirmed.

### Every subcommand that emits JSON

Enumerated by running `--help` on all 17 top-level commands and on the nested
`plugin` / `mcp` / `auth` / `auto-mode` / `project` subcommands, grepping each
for `json`.

| Command | Flag | Notes |
|---|---|---|
| `claude agents` | `--json` | "Print active sessions (interactive and background) as a JSON array and exit". `--all` adds completed sessions — **only meaningful with `--json`**. Verified live: rc=0, array of `{id, cwd, kind, startedAt, sessionId, name, …}` |
| `claude auth status` | `--json` | **"Output as JSON (default)"** — it is already the default format. Verified live: rc=0, `{loggedIn, authMethod, apiProvider, analyticsDisabled, projectsDirectory, configDirectory, email, orgId, orgName, subscriptionType}` |
| `claude plugin list` | `--json` | "Output as JSON". `--available` (include marketplace plugins) **requires `--json`**. Verified live: rc=0, 270 rows, each `{id, version, scope, enabled, installPath, installedAt, …}` in 0.40s |
| `claude plugin marketplace list` | `--json` | "Output as JSON" |
| `claude plugin validate` | `--json` | "Output the validation report as JSON (**same exit codes**)" |
| `claude plugin eval` | `--json [path]` | "Print the full run result (prompts, graders, per-run scores) as JSON to stdout, or write it to this .json"; separately `--output-dir <dir>` for `aggregate-result.json` |
| `claude ultrareview` | `--json` | "Print the raw bugs.json payload instead of formatted …" |
| `claude auto-mode config` | *(no flag)* | The subcommand itself "Print[s] the effective auto mode config as JSON: your settings where set, defaults …" — JSON is the only output |
| `claude auto-mode <rules sub>` | *(no flag)* | "… and hard_deny rules as JSON" |
| `claude` (main, with `-p`) | `--output-format json` | Choices: `text` (default), `json` (single result), `stream-json`. Only works with `--print`. Also `--input-format {text,stream-json}` and `--json-schema <schema>` for structured-output validation |

**No `--format json` spelling exists anywhere** — every surface uses `--json`
or `--output-format json`.

Subcommands with **zero** JSON output: `auth` (parent), `doctor`, `gateway`,
`import`, `install`, `logs`, `project`/`project purge`, `respawn`, `rm`,
`setup-token`, `stop`, `update`, `attach`, `plugin details`.

⚠️ **`claude mcp list` has NO `--json`.** Its `--help` mentions `.mcp.json` only
as a filename. Nor does `claude mcp get`. `claude mcp add-json` takes JSON as
*input*, it does not emit it. This matters: `doctor.py:986-1053`'s
`check_mcp_health` therefore **parses `claude mcp list`'s human text**
(`parse_mcp_list`, `:962`) — that is a text parser by necessity, not by choice.

### `~/.claude/daemon.json` — does not exist

Absence arm: `ls -la ~/.claude/daemon.json` → `No such file or directory`, rc=1.
Control arm, same command shape: `ls -la ~/.claude.json` → present, 172,160 B.
The probe discriminates.

### State files that DO carry version / health info

| File | Content (read live) |
|---|---|
| **`~/.claude/.last-update-result.json`** | `{"timestamp":"2026-09-12T20:17:53.243Z","path":"npm-global","outcome":"success","status":"success","version_from":"2.1.269","version_to":"2.1.270","error_code":null}` — **the CLI self-update's own machine-readable receipt**, with both versions and an error code slot |
| `~/.claude/daemon.status.json` | `{"supervisorPid":35334,"supervisorProcStart":"Sat Sep 12 20:18:22 2026","writtenAt":1789244302281,"workers":{}}` |
| `~/.claude/daemon-auth-status.json` | `{"status":"auth_required","since":1785719604586}` |
| `~/.claude/mcp-needs-auth-cache.json` | `{}` |
| `~/.claude/policy-limits.json` | 214 B, mode 0600 |
| `~/.claude/remote-settings.json` | `{}` (2 B) |
| `~/.claude/stats-cache.json` | 26,461 B |
| `~/.claude/gh-pr-status-cache.json` | 488 B |
| `~/.claude.json` | 172,160 B — the big one; `doctor.py:334-355` already reads its user-global **and** per-project MCP blocks |
| `~/.claude/mcp_servers.json` | 23 B, mode 0600 |

**`~/.claude/.last-update-result.json` is the surface worth knowing about**: it
answers "did the CLI update, from what to what, and did it fail" without
parsing any text, and it is written by `claude update` itself.

---

## Bonus: what `rc=1` actually was today (measured)

The guard's audit log, `~/.config/mise/update-runs.log`, tail:

```
2026-09-12T19:34:00+00:00 | update:all | tools=- | 65.7s | rc=0 | clean
2026-09-12T19:48:16+00:00 | update:all | tools=- | 66.1s | rc=0 | clean
2026-09-12T19:57:26+00:00 | update:all | tools=- |  0.5s | rc=1 | clean
2026-09-12T20:10:02+00:00 | update:all | tools=- |  0.6s | rc=1 | clean
2026-09-12T20:11:14+00:00 | update:all | tools=- |  0.4s | rc=1 | clean
2026-09-12T20:12:37+00:00 | update:all | tools=- |  0.5s | rc=1 | clean
```

Every recent `rc=1` completed in **0.4-0.6 s**. A plugin-fan-out failure cannot
look like that: a healthy run is 62-107 s, and `claude plugin list --json` alone
takes 0.40 s (measured just now, rc=0, 270 rows). Corroborating:
`~/.config/mise/.update-claude.json` carries `elapsed_s: 65.7`, which matches
the **19:34** entry exactly — so no run after 19:48 ever reached the summary
write at `update_claude.py:288-289`.

Also note `note=clean` on every line: the guard did **not** refuse
(a refusal logs `refused: live holder` and returns `RC_REFUSED`, not 1). So
`mise run update:all` itself returned 1, almost immediately.

The last successful state, from that summary: `total: 238, updated: 0,
refreshed: 0, current: 238, failed: 0`, `failures: []`, and every prelude step
rc=0.

**Not resolved here**: which of the three parallel `depends` entries fast-fails.
The candidate fast-exit-1 paths are `update_claude.py:164`
(`claude plugin list --json` non-zero → `SystemExit(rc or 1)`), `update:brew`'s
`set -euo pipefail` on `brew update`, or `update:mise`'s `mise config ls`.
`~/.local/state/mise/mise.log` cannot settle it — its mtime is 16:15, four hours
before the first fast failure, so it was not written by those runs. Naming the
task requires one instrumented run, which this read-only lane did not do.

---

## GitHub repos touched

_None._ Every source read was local: `~/.config/mise/**`, `~/.claude/**`, and
this repository's working tree.
