# Mise Config Currency & Gaps — Advisor Report

**Session**: 2026-09-15  
**Scope**: Currency tracking machinery inventory, gap analysis, and single recommendation  
**Status**: Complete

---

## NOTE ON EARLIER SECTIONS

The following sections from earlier work are **SUPERSEDED** and left only as evidence archive. Do NOT implement:
- Deliverable 2 (Mechanism verdicts: A/B/C/D/E/F)
- Deliverable 3 (Enforcement targets: T1/T2/T3 with gates)
- All design sections on context injection, hooks, rules, and placement gates

**REASON**: The operator reframed the entire scope. The system's purpose is CURRENCY (keep everything current) and LEARNING (track what we learned from releases), not enforcement mechanisms.

---

## Deliverable 1: Mise Config Topology Map (Retained)

**Verified**: mise.toml is shared (host + GHA runners). mise-system.toml is build-time; mise-runtime.toml is runtime.

| Config | Purpose | Loaded By |
|---|---|---|
| `mise.toml` | Project tools + tasks | Host + GHA runners |
| `.config/mise/conf.d/shared.toml` | Tools shared host↔image | Host + GHA + image base stage |
| `.devcontainer/mise-system.toml` | Image build-time tools | Image base stage only |
| `.devcontainer/mise-runtime.toml` | Image runtime tools | Image runtime stage only |

---

## AI CLI Tier Inventory (Retained from tier analysis)

| CLI | Current Location | Reaches Base? | Correct? |
|---|---|---|---|
| claude-code | mise-runtime.toml + mise.toml [env] | NO | ✅ YES |
| codex | shared.toml | **YES** | ❌ **VIOLATION** |
| gemini-cli | mise-runtime.toml | NO | ✅ YES |
| antigravity-cli | mise.toml (host) | NO | ✅ YES |
| opencode | mise.toml (host) | NO | ✅ YES |

---

## NEW FOCUS: Currency Machinery Inventory

### 1. What Each Piece Is For

| Machinery | Purpose | Scope | Runs Where |
|---|---|---|---|
| **currency.toml** | Deep-track fast-movers (Doppler, graphify); enables release-note review + interview loop | Curated subset of tools | `mise run tool-currency` (daily in refresh.yml) |
| **`mise outdated`** | Broad sweep: all mise [tools] pins vs latest | Entire [tools] section | Called by `kb-setup currency daily` task |
| **pin-parity.toml** | Version parity across multiple declaration sites (chezmoi, hk, mise) | Only tools in registry | `pin_parity` hk step (pre-commit) |
| **renovate.json** | Automated version bump PRs | Managed by Renovate's backends (npm, go, python, etc.) | CI (renovate bot) |
| **rule-sync.toml** | Cross-repo shared rules sync (dotfiles ↔ knowledge-base) | Rules files only | `mise run rule-sync` |
| **dependency-currency** task | Check python/pyproject.toml dependencies vs latest | pyproject.toml only | `mise run dependency-currency` |

### 2. Coverage Analysis — What's Tracked vs Not

**TRACKED (will flag as outdated)**:
- ✅ `mise.toml [tools]` pins → `mise outdated` broad sweep
- ✅ `.config/mise/conf.d/shared.toml [tools]` → `mise outdated` merges it
- ✅ `.devcontainer/mise-system.toml [tools]` → part of merged config
- ✅ `.devcontainer/mise-runtime.toml [tools]` → part of merged config
- ✅ `pyproject.toml [project.dependencies]` → `dependency-currency` task
- ✅ Cross-environment version parity (chezmoi, hk, mise) → pin-parity.toml

**NOT TRACKED (will NOT flag as outdated)**:
- ❌ `mise.toml [env]` variables (CLAUDE_CODE_VERSION, etc.)
- ❌ `.devcontainer/Dockerfile` ARGs (MISE_VERSION, etc.)
- ❌ `.github/actions/setup-mise/action.yml` versions
- ❌ `.chezmoiversion` (chezmoi minimum floor)
- ❌ Inline-table tool pins (e.g., `{ version = "X", ... }`)

---

## Case Study: Why Claude-Code Slipped Through

**The Split**: 
- Host: `mise.toml [env] CLAUDE_CODE_VERSION = "2.1.272"`
- Image: `.devcontainer/mise-runtime.toml claude-code = "latest"` (resolves to 2.1.270 in lock)
- Latest shipped: 2.1.272

**Why Nothing Caught It**:

1. **ENV variables are invisible to `mise outdated`**
   - `mise outdated` reads the manifest and sees only `[tools]` declarations
   - `CLAUDE_CODE_VERSION` is in `[env]`, not `[tools]`
   - Result: drift is invisible

2. **currency.toml explicitly excludes claude-code**
   - Comment: "Claude Code is deliberately NOT tracked here. It has no mise owner any more: the `[tools]` pin was removed"
   - The decision was intentional (native installer owns it, not mise)
   - Result: deep-mode won't catch it

3. **pin-parity.toml never registered it**
   - Registry contains only: chezmoi, hk, mise
   - claude-code is absent
   - Result: version parity drift is invisible

4. **Combined effect**: TRIPLE coverage gap
   - Not in currency.toml (excluded by design)
   - Not in pin-parity.toml (never registered)
   - Not visible to `mise outdated` (ENV variable, not tool pin)

**Verdict**: This was a structural gap, not a broken gate. **No existing mechanism covers ENV-variable pins or floating tools that mix between [env] and [tools].**

---

## The Gap: Missing Mechanism

**What is missing**: A way to track version pins that live in `[env]` variables or appear in multiple forms (env var + tool pin + native installer).

**Concrete example**: 
- claude-code exists as: CLAUDE_CODE_VERSION (env var) + claude-code (tool pin) + native installer path
- When native installer is the source of truth, the env var can drift from the actual installed version
- No currency mechanism tracks env vars

**Scope of the gap**:
- Any tool with an `[env]` version variable (like CLAUDE_CODE_VERSION)
- Any tool with a float like "latest" in one config and an exact version in another
- Tools transitioned to native installers with version env vars left behind

---

## One Recommendation: Extend pin-parity.toml

**What to do**: Register claude-code (and future env-var pins) in pin-parity.toml.

**Why**: pin-parity.toml already has the infrastructure (regex patterns, multi-site comparison). It can capture env vars just as easily as tool pins.

**Exact entry to add**:

```toml
[tools.claude-code]
description = """
Claude Code pinned via environment variable (host) and tool pin (image).
Env vars cannot be tracked by `mise outdated` (which reads [tools] only).
pin-parity ensures they stay current."""
sites = [
  { path = "mise.toml", pattern = 'CLAUDE_CODE_VERSION = "([^"]+)"' },
  { path = ".devcontainer/mise-runtime.toml", pattern = '^claude-code = "([^"]+)"' },
]
```

**When to implement**: 
1. Convert `.devcontainer/mise-runtime.toml` line 63 from `claude-code = "latest"` to `claude-code = "2.1.272"` (exact version)
2. Add the above entry to pin-parity.toml
3. Existing `pin_parity` hk step (pre-commit gate) will then catch future divergence

**Benefit**: Single smallest change closes the structural gap. No new infrastructure needed.

---

## Summary

**Currency system works for**:
- All `[tools]` pins (broad sweep via `mise outdated`)
- Cross-site version parity (pin-parity.toml for chezmoi, hk, mise)
- Python dependencies (dependency-currency task)

**Currency system misses**:
- ENV-variable pins (like CLAUDE_CODE_VERSION)
- Floating versions that mix exact + "latest" across configs

**One fix**: Register env-var pins in pin-parity.toml. claude-code is the canonical case.

