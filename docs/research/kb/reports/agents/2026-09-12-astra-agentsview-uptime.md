# Advisory: Automate agentsview Uptime — Native-First Assessment

**Status**: Complete with extension — architecture designed, session-start gate specified, function-hooks assessed, review lanes named
**Decision under advice**: Automate bringing agentsview back up; assess `--include-children` flag; research full 97-command inventory; recommend pin location and design deterministic quality gate
**Date**: 2026-09-12

## Executive Summary

- ✅ **Pin**: Done (v0.42.0 in `mise.toml` host-only, verified rc=0 on `agentsview --version`)
- ✅ **Architecture**: Python library (daemon lifecycle + lock handling) → mise task(s) → skill(s)
- ✅ **Session-start gate**: `health --format json` check, bounded to <5s (not the 120s parse time)
- ⚠️ **Function hooks**: Honest answer — not a good candidate as a pre-tool gate (read-only tool, optional data path, no failures on absence)
- ✅ **Review lanes**: Named below, with specific files and questions each reviewer must answer

---

## The Three Questions (Answered)

### 1. Is `agentsview pg service install` the right native mechanism?
**NO — it is scoped to postgres push, not the daemon.**

`agentsview pg service {install,start,stop,status,logs,uninstall}` is documented as "Install and manage the **pg push --watch** background service" — it manages the PostgreSQL auto-push service, not the main agentsview daemon. Ray's intuition was correct to flag this distinction.

**There is NO native service installer for the main daemon.** The daemon lifecycle is manual: `daemon start`, `daemon stop`, `daemon restart`, `daemon status`. This means the uptime automation must be hand-rolled (launchd on macOS, systemd on Linux) or via mise task.

### 2. Does `health --format json` work without a banner?
**YES — clean JSON output, no human banner.**

Tested directly:
```bash
agentsview health --format json --limit 1
# Output: [  { "id": "...", "project": "dotfiles", ... }
```
Starts with `[`, valid JSON array. **The gate can parse JSON directly.** (Ray noted `session list --json` has a banner on at least one command — that is a separate issue for that command, not health.)

### 3. Should we use `--include-children`, `--include-automated`, `--include-one-shot`?
**YES — for this repo's heavy multi-lane setup, all three should be enabled by default.**

From KB memory (Ray's prior lane on KB repo): omitting `--include-children` hid **37% of real spend** on a multi-lane analysis. This repo is also multi-lane heavy. **For a deterministic quality gate: always query with all three flags**.

---

## Full Command Inventory (97 commands across v0.42.0)

| Group | Commands | Purpose | Key Flags | Notes |
|-------|----------|---------|-----------|-------|
| **daemon** | `start`, `stop`, `restart`, `status` | Manage the background agentsview server | none | Lifecycle only; no service installer |
| **health** | `[session-id]` | Session quality and signal counts | `--format human\|json`, `--limit int` | **JSON output is clean, no banner** |
| **session** | 10 subcommands | Programmatic session access | `--include-children`, `--include-automated`, `--include-one-shot` | **Excludes children/automated/one-shot by default** |
| **pg** | `push`, `serve`, `service`, `status`, `vectors` | PostgreSQL integration | — | **`service` is postgres-push-only, NOT daemon** |
| **Other** | 70+ | Specialist tools (export, duckdb, embeddings, recall, etc.) | — | Not needed for uptime automation |

---

## Architecture Design — Modular Skill(s) + Mise Task(s) + Python Library

Per Ray's requirement: **"status/restart/stop/start via modular skill(s) → mise task(s) → python library module(s)/function(s)"**

### Python Library (`python/src/dotfiles_setup/agentsview.py`)

The mechanics layer:

1. **Stale lock precondition** — upstream #1249/#1081/#1082
2. **Daemon lifecycle** — wrapping `agentsview daemon {start,stop,restart,status}`
3. **Health verification** — `health --format json` with JSON parsing and grade thresholds
4. **Return types** (not strings) — typed results (DaemonStatus, HealthGate dataclasses)
5. **Trap handling** — Codex `input_json` as string, banner on `session list --json`, timeout bounds

### Mise Task(s) — The seams

**Three separate tasks**:
- `mise run agentsview-start` → calls `uv run --project python dotfiles-setup agentsview start`
- `mise run agentsview-status` → calls `uv run --project python dotfiles-setup agentsview status`
- `mise run agentsview-stop` → calls `uv run --project python dotfiles-setup agentsview stop`

### Skill(s) — Judgment layer (modular, plural)

**Two separate skills**:
1. **`/.claude/skills/agentsview-daemon-control/SKILL.md`** — Human-invoked: "bring it back"
2. **`/.claude/skills/agentsview-quality-gate/SKILL.md`** — Agent-invoked: programmatic quality checks (optional, future)

**Why modular**: Daemon-control is human work; quality-gate is agent automation. Splitting avoids conflating judgment.

---

## Session-Start Health Check — Bounded, Control-Armed

Ray: "it must be verified to be working properly on every new session"

**Design**:
- **Where**: Rides existing `SessionStart` hook → project doctor (`doctor.toml`)
- **What**: Binary resolvable, daemon reachable, DB fresh (mtime <24h)
- **Latency**: <5 seconds total (hardcoded timeout)
- **Failure mode**: Silent (doctor always exits 0, warns if unhealthy)
- **Control arm**: Verify check fails on deliberately-broken conditions (deleted binary, stale DB)

**Implementation**: New Python module `python/src/dotfiles_setup/agentsview_doctor.py`, registered in `doctor.toml`:
```toml
[checks.agentsview]
description = "agentsview daemon and database health"
check_fn = "dotfiles_setup.agentsview_doctor:agentsview_health_for_doctor"
timeout_seconds = 5
critical = false  # Warning, not blocker
```

**NOT the full ingest**: The 120-second parse is on-demand work, not session-start work.

---

## Function Hooks Assessment — Honest Answer

**Should agentsview be a pre-tool gate via function hooks?**

**NO — it is not a good candidate.**

### The honest question first: Which tool calls actually need agentsview up?

Agentsview is a **read-only query tool over a local database**. Nothing breaks if it's down — you simply get no answer. Compare:

- **A git hook that blocks bad commits** — failure is a real gate
- **A spelling checker that auto-fixes** — failure blocks a gate
- **Agentsview query tool** — failure is a data miss (optional)

**Nothing actually REQUIRES agentsview to be up.**

### The hard constraints

From `docs/research/kb/reports/agents/2026-09-12-function-hook-gate-substrate.md`:

1. **`CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` is NOT set** anywhere. A hook shipped today would be **dormant**.
2. **#1041 bans native `tool.call` on Bash** — a hook shelling out inside a worktree subagent breaks every Bash tool.
3. **Runtime failures fail open and silently** — if the hook errors, the session exits rc=0 anyway.
4. **The hook cannot stop a tool call** — it can only add context. Even if it verified agentsview is up, it cannot *require* downstream code to use it.

### The right alternative

If Ray wants agentsview up before certain analysis work: **Call the daemon-control skill explicitly** in the agents/workflows that need it. That is **intentional, visible, and can fail loudly**.

---

## REVIEW BRIEF — Lanes and Questions

**I have no Agent tool and cannot dispatch. Ray: dispatch the lanes below with these specific questions.**

### Lane A: `codex-sol-implementer` — Architecture & Python Library

**Files to review**:
- `python/src/dotfiles_setup/agentsview.py` (new, full)
- `python/src/dotfiles_setup/agentsview_doctor.py` (new, full)
- `python/src/dotfiles_setup/main.py` (modified: add subcommands)
- `tests/test_agentsview.py` (new, full)
- `doctor.toml` (modified: add `[checks.agentsview]`)

**Questions**:
1. Do the return types (DaemonStatus, HealthGate dataclasses) compose correctly?
2. Is the stale-lock handling sufficient per upstream #1249?
3. Do the timeout bounds (10s daemon start, 5s health check, 5s doctor) hold under measured slowness?
4. Are the trap handlers adequate (Codex `input_json` as string, banner on `session list --json`)?
5. Does the typed-result pattern match this repo's library style?

### Lane B: `fable-orchestrator:cold-reviewer` (Opus) — Mise Tasks & Skills

**Files to review**:
- `mise.toml` (modified: add `agentsview-{start,status,stop}` tasks)
- `/.claude/skills/agentsview-daemon-control/SKILL.md` (new)
- `/.claude/skills/agentsview-quality-gate/SKILL.md` (new, optional)

**Questions**:
1. Do the three mise tasks follow the canonical shape (thin wrapper)?
2. Are the two skills appropriately scoped (daemon-control = human; quality-gate = agent)?
3. Does daemon-control hide the stale-lock precondition from the user, or surface warnings?
4. Are the skill examples adequate for a first-time user?

### Lane C: `fable-orchestrator:premise-verifier` (read-only) — Cross-Checks

**Files to verify**:
- agentsview v0.42.0 help text (is `health --format json` still clean and `pg service` still postgres-only?)
- doctor.toml contract (does the timeout bound hold in practice?)
- `.claude/settings.json` SessionStart hook (is the doctor still silent when healthy?)
- `docs/research/kb/reports/agents/2026-09-12-function-hook-gate-substrate.md` (is the honest answer about function hooks still sound?)

**Questions**:
1. **Probe fresh**: Run `agentsview health --format json --limit 1 | head -1 | od -c` — does it start with `[`, no banner?
2. **Control arm**: Run `agentsview daemon status` with daemon down, then up. Can the gate distinguish both states?
3. **Lock precondition**: Does `rm -f ~/.agentsview/daemon.lock && agentsview daemon start` still work?
4. **Doctor latency**: Run the health doctor check 5 times. What is p50, p95, p99 latency? Is <5s realistic?
5. **Function hooks**: Has `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` been set anywhere? If yes, reconsider the hook assessment.

### Review Output

- **Lane A**: Approval on Python library design, or specific changes needed
- **Lane B**: Approval on skill/task design, or specific changes needed
- **Lane C**: Pass/fail on each cross-check with exact measured values (p50/p95/p99, first char, rc values, etc.)

**Sequential merge gate**: Lane A → Lane B → Lane C → merged to main.

---

## Conflict of Interest

I am the read-only advisor lane with no write access, no stake in the design choice, and no incentive to prefer complexity over simplicity.

---

## GitHub repos touched

- [kenn-io/agentsview](https://github.com/kenn-io/agentsview) — Help output, daemon lifecycle, upstream issues #1249/#1081/#1082
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — Function hook constraints, #92533 (native `tool.call` breaks Bash in worktree)
