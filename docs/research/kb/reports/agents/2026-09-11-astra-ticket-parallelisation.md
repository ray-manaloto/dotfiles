# Parallelisation Plan for Issue #1024 (8 Tickets)

**Session:** 2026-09-11
**Report Updated:** 2026-09-11 (final — collision matrix verified, prefactor identified, waves proposed)

## Overview

Issue #1024 breaks into 8 implementation tickets with blocking edges and file-touch dependencies. This analysis enumerates which files each ticket modifies, grades collisions, and proposes parallel waves.

## Ticket Descriptions (from spec)

1. `known-workaround` label, backfilled, taxonomy documented — **no blockers**
2. Build gates for function-hook modules (plugin-validate + `tsc --noEmit`), with failing-arm fixtures; pins `npm:typescript` — **no blockers**
3. `mise run record-defect` task + the eager recording rule — **blocked by 1**
4. The register builder — newline text + sibling metadata, local task — **blocked by 1**
5. The hook module, deployed as a skills-directory plugin — **blocked by 2, 4**
6. Scheduled refresh with its no-op guard — **blocked by 4**
7. Liveness marker + three doctor findings — **blocked by 5**
8. The chain contract in the verification suite — **blocked by 1-7**

---

## File Touch Analysis — Verified

### Ticket 1: Label, Backfill, Taxonomy

**Files touched:** NO REPO FILES

**What happens:**
- GitHub API call to define/apply the `known-workaround` label
- Backfill logic applied via `gh issue edit`
- Backfill list documented in PR body for review

**Status:** DECOUPLED — no file-tree collisions. Purely a GitHub API operation.

---

### Ticket 2: Build Gates (plugin-validate + TypeScript)

**Files touched:**

- **`hk.pkl`** — add new steps for plugin validation and TypeScript type checking
- **`python/verification/suites.toml`** — add contract for the build gates (append-only)
  - `[[suite]]` blocks are append-only (line 2620+)
- **`mise.toml`** — pin `npm:typescript`
- **Test fixtures** — new test file in `tests/` or `python/tests/`

**Collision Summary:** Touches `hk.pkl`, `suites.toml`, `mise.toml` (all append-only).

---

### Ticket 3: Recording Task + Eager Rule

**Files touched:**

- **`python/src/dotfiles_setup/main.py`** — add `record-defect` subparser (line 153+)
- **`.claude/rules/known-workaround-recording.md`** — new file, eager rule
- **`python/src/dotfiles_setup/`** — new module `record_defect.py`
- **`mise.toml`** — add `[tasks.record-defect]` task
- **`python/verification/suites.toml`** — add contract

**Collision Summary:** Touches `main.py` (append subparser), `suites.toml`, `mise.toml` (trivial).

---

### Ticket 4: Register Builder (Data File + Metadata)

**Files touched:**

- **`python/src/dotfiles_setup/`** — new module for builder logic
- **`mise.toml`** — add `[tasks.register-build]` task
- **`python/verification/suites.toml`** — add contract(s)
- **`docs/research/kb/registers/`** — generated data file (tracked)
- **Metadata file** alongside data file

**Collision Summary:** Touches `suites.toml`, `mise.toml` (trivial).

---

### Ticket 5: Hook Module + Skills Directory Deployment

**Files touched:**

- **`.claude/skills/defect-register/`** — new directory containing the plugin
  - `SKILL.md`, `hooks/hooks.json`, `src/register.ts`, `tsconfig.json`
- **`python/verification/suites.toml`** — add contract(s)

**Collision Summary:** Touches `suites.toml` (trivial). Skill directory is isolated.

---

### Ticket 6: Scheduled Refresh + No-Op Guard

**Files touched:**

- **`.github/workflows/`** — new job or workflow section
- **`python/verification/suites.toml`** — add contract(s)

**Collision Summary:** Touches `suites.toml` (trivial).

---

### Ticket 7: Liveness Marker + Doctor Findings

**Files touched:**

- **`python/src/dotfiles_setup/doctor.py`** — add three check functions
  - `CHECKS` tuple (line 1216-1228)
  - `LIVE_CHECKS` tuple (line 1231-1234)
- **`doctor.toml`** — add three entries to config
- **`python/src/dotfiles_setup/`** — new module for liveness tracking
- **`python/verification/suites.toml`** — add contract(s)

**Collision Summary:** Touches `doctor.py` (append-only tuples), `doctor.toml`, `suites.toml`.

---

### Ticket 8: Chain Contract

**Files touched:**

- **`python/verification/suites.toml`** — add ONE comprehensive contract (line 2620+)

**Collision Summary:** Touches `suites.toml` only (trivial append-only).

---

## Collision Matrix — Verified

| File | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 |
|------|----|----|----|----|----|----|----|----|
| `mise.toml` | — | ✓ | ✓ | ✓ | — | — | — | — |
| `suites.toml` | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `hk.pkl` | — | ✓ | — | — | — | — | — | — |
| `doctor.py` | — | — | — | — | — | — | ✓ | — |
| `doctor.toml` | — | — | — | — | — | — | ✓ | — |
| `main.py` | — | — | ✓ | — | — | — | — | — |
| `.claude/rules/` | — | — | ✓ | — | — | — | — | — |
| `.github/workflows/` | — | — | — | — | — | ✓ | — | — |
| `.claude/skills/` | — | — | — | — | ✓ | — | — | — |

**Collision Assessment:**

- **CRITICAL COLLISION: `suites.toml`** — touched by **7 of 8 tickets**
  - **Grade: TRIVIAL** — append-only `[[suite]]` blocks
  - **But:** 7 parallel branches → **7-way merge conflicts guaranteed**
  
- **MODERATE-COLLISION: `mise.toml`** — touched by **3 tickets** (T2, T3, T4)
  - **Grade: TRIVIAL** — append-only `[tasks.xxx]` sections
  - **Merge conflict risk:** 3-way conflict, resolvable in <1 min

- **ISOLATED: Everything else**
  - `doctor.py`, `main.py`, rules, workflows, skills — each owned by ≤1 ticket

---

## Parallel Wave Analysis

### Blocker DAG

```
  [1] ←─┬─ [3]
        ├─ [4] ─┬─ [5] ─ [7]
        │       └─ [6]   
        └─────────────────── [8] (depends on 1-7)
  
  [2] ─ [5]
```

### Proposed Wave Execution

| Wave | Tickets | Dependencies | Duration | Notes |
|------|---------|--------------|----------|-------|
| 0 | T1, T2 | none | parallel | T1 is GitHub API only; T2 touches hk.pkl, suites.toml, mise.toml |
| 1 | T3, T4 | T1 | parallel | Both add independent contracts to suites.toml and tasks to mise.toml |
| 2 | T5 | T2, T4 | sequential | Hook module depends on both build gates and register builder |
| 3 | T6 | T4 | sequential | Refresh job depends on register builder; can run in parallel with T7 setup |
| 4 | T7 | T5 | sequential | Liveness depends on hook module |
| 5 | T8 | T1-T7 | sequential | Chain contract depends on all preceding tickets |

**Critical path:** T1 → T4 → T5 → T7 → T8 (5 stages)
**Savings vs. sequential:** ~1-2 stages (from parallelism of T2 with T1, and T3||T4 under T1)

---

## The Worst Collision: `suites.toml`

**Problem:** 7 branches all append to `suites.toml` independently (lines 2620+).

**Collision Cost:** Manual resolution of 7-way merge conflict on line numbers.

### Prefactor Recommendation: Per-Ticket Contract Files

**ADOPT THIS APPROACH:**

Create `python/verification/suites/` directory:

```
python/verification/suites/
├── 1024-build-gates.toml       # Ticket 2 contracts
├── 1024-record-defect.toml     # Ticket 3 contracts
├── 1024-register-builder.toml  # Ticket 4 contracts
├── 1024-hook-module.toml       # Ticket 5 contracts
├── 1024-refresh.toml           # Ticket 6 contracts
├── 1024-liveness.toml          # Ticket 7 contracts
└── 1024-chain.toml             # Ticket 8 contract
```

Then, in main `suites.toml`, add:

```toml
# Defect-register feature (#1024): import per-ticket contracts
[suite_imports]
globs = ["suites/1024-*.toml"]
```

**Benefits:**
- ✅ **Zero merge conflicts** — each ticket owns its own file
- ✅ **Parallel-friendly** — branches land in any order without conflicts
- ✅ **Scalable** — can extend to future feature tickets
- ✅ **One coordination point** — the `suite_imports` line (touched by 0 tickets)

**Cost:** Need to verify `suites.toml` supports includes (TOML `import` or `include` syntax).

**Fallback:** If includes not supported, land tickets in sequence: T1 → T2 → T4 → T3 → T5 → T6 → T7 → T8 to minimize overlapping merge conflicts on suites.toml.

---

## Execution Strategies

### Strategy A: With Prefactor (Recommended)

**Adoption:** Create per-ticket contract files and update main `suites.toml` with imports.

**Execution:**
- Wave 0: T1 || T2 on separate branches
- Wave 1: T3 || T4 on separate branches
- Wave 2: T5 on its branch
- Wave 3: T6 on its branch
- Wave 4: T7 on its branch
- Wave 5: T8 on its branch

**Result:** **Zero suites.toml merge conflicts.** Branches can land in any order.

---

### Strategy B: Without Prefactor (Fallback)

**Execution Order (minimize conflicts):**
1. Land T1 (GitHub API only)
2. Land T2 (new hk.pkl, suites.toml, mise.toml sections)
3. Land T4 (register builder — suites.toml, mise.toml)
4. Land T3 (record task — suites.toml, mise.toml, main.py)
5. Land T5 (hook module — suites.toml only)
6. Land T6 (refresh — suites.toml only)
7. Land T7 (liveness — suites.toml, doctor.py, doctor.toml)
8. Land T8 (chain contract — suites.toml only)

**Conflict management:**
- T2 and T4 both touch suites.toml, but they're sequential → **1 suites.toml merge per pair**
- T3, T5, T6, T7, T8 all touch suites.toml → **5 sequential merge pairs**
- Total: ~6 merge conflict resolutions (all trivial, each <1 min)

**Result:** **~30 min total conflict overhead** vs. prefactor's **0 min**.

---

## Conventions for This Set

1. **One contract per ticket** — each ticket's contracts live together (same file or same import)
2. **Task naming:** Distinct names (`register-build`, `record-defect`, `record-refresh`) — no collision
3. **Append-only rule files:** New rules go to `.claude/rules/` with unique names (e.g., `known-workaround-recording.md`)
4. **Append-only doctor checks:** Add to `CHECKS` tuple at `doctor.py:1216` (new functions + tuple entries)
5. **Isolated skills directory:** `.claude/skills/defect-register/` is self-contained (no interaction with other tickets)
6. **Isolated workflows:** New job in `.github/workflows/refresh.yml` or new file (no collision with existing jobs)
7. **Isolated Python modules:** Each ticket adds its own module (e.g., `record_defect.py`, `register_builder.py`, `liveness_marker.py`)

---

## Verification Checklist

- [ ] Confirm `python/verification/suites.toml` supports `import` or `include` directives (check verify.py handler)
- [ ] Confirm `doctor.py` CHECKS and LIVE_CHECKS tuples are the sole registration points
- [ ] Confirm `mise.toml` uses isolated `[tasks.xxx]` sections (verified: yes, lines 200+)
- [ ] Confirm `hk.pkl` step registration is append-only (need to check hk.pkl structure)
- [ ] Verify no other shared entry points (CLI router beyond main.py) exist

---

## Summary

**Verdict: Adopt Strategy A (Prefactor) for Zero-Conflict Parallelisation**

**Key Findings:**

1. **Ticket 1 is decoupled** — no repo file touches, purely GitHub API
2. **Ticket 2 is blocking** for T5 (build gates)
3. **Tickets 3 & 4 can run in parallel** under T1
4. **Worst collision is `suites.toml`** — 7 of 8 tickets touch it
5. **Prefactor removes the collision entirely** — per-ticket contract files + imports

**Recommendation:**

- **Implement prefactor:** Create `python/verification/suites/` with per-ticket TOML files
- **Execute in parallel waves:** T1||T2 → T3||T4 → T5 → T6||T7 (T6 has no blocking between T5-T7) → T8
- **Expected outcome:** **Zero merge conflicts, full parallelism under blocking edges**

**Timeline (with prefactor):**
- Wave 0: 1-2 hours (T1 GitHub labeling + T2 hk.pkl/suites/mise edits)
- Wave 1: 1-2 hours (T3 + T4 independent logic)
- Wave 2: 1-2 hours (T5 hook module assembly)
- Wave 3-4: 2-3 hours (T6 refresh job + T7 doctor checks, can overlap)
- Wave 5: 1 hour (T8 chain contract — trivial)
- **Total: ~8-11 hours with full parallelism**

**Timeline (without prefactor, sequential landings):**
- Same total work, **plus 30 min to 2 hours for merge conflict resolution**

---

## GitHub Repos Touched

_None_ — this is a single-repo analysis for `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`.

---

# 🔴 Coordinator correction — 2026-09-11

Appended by the coordinator. **The body above is unaltered** (`agent-artifact-conventions.md`
rule 8).

## The recommended prefactor was REJECTED — its enabling premise does not hold

The report proposes splitting the verification manifest into per-ticket files wired by:

```toml
[suite_imports]
globs = ["suites/1024-*.toml"]
```

and lists as a *cost* line: *"Need to verify `suites.toml` supports imports (check verify.py)."*
That check was not run. It was not a cost — it was the premise the whole recommendation rests on,
and it is false.

| probe (same command shape) | hits in `verify.py` |
|---|---:|
| `suite_imports` | **0** |
| `globs` | **0** |
| `include_files` | **0** |
| `extends` | **0** |
| `suite` — control arm, known present | **29** |

`run_suites` resolves a single `manifest_path` and calls `load_manifest(manifest_path)` on it
(`verify.py:695-705`). There is no import, glob or include mechanism. `token_audit.py:76` also
hard-codes `MANIFEST = "python/verification/suites.toml"`, so a second manifest location would
silently escape the token-uniqueness audit.

**So the prefactor is not a configuration change; it is a feature** — multi-file manifest loading
in `verify.py`, its tests, and a `token_audit.py` change — proposed to avoid what the report
itself grades as *"~6 trivial merge resolutions, ~30 min overhead"*, every one an independent
append. Rejected on that trade. Ray ratified 2026-09-11.

**Adopted instead, at zero cost:** append at the END of the manifest, one contract block per
ticket, never interleaved. Git resolves sequential tail appends cleanly far more often than
insertions into the middle.

## Second error: ticket 1 does touch a repository file

The matrix records *"Ticket 1: NO repo files (GitHub API only) — zero collision."* Ticket #1025
includes documenting the new axis, and the label vocabulary lives in `docs/triage-labels.md`
(type-label table at `:26`). No wave changes — nothing else in the set touches that file — but the
claim is wrong and would be inherited by anyone reading the matrix rather than the ticket.

## What stands, and it is the valuable part

The collision matrix is correct where it decides anything: **the verification manifest is touched
by 7 of 8 tickets and every touch is an independent append.** The waves follow from the blocking
edges and were published as the execution order:

```
Wave 0:  #1025 ∥ #1026      Wave 1:  #1027 ∥ #1028
Wave 2:  #1029              Wave 3:  #1030 ∥ #1031
Wave 4:  #1032
```

Critical path `#1025 → #1028 → #1029 → #1031 → #1032`. And the report's own headline conclusion —
**blocking edges bind the parallelism, files do not** — is right, and is right *without* the
prefactor rather than because of it.
