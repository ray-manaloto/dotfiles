# Parallelization Plan: Wave 1 of #1024 (#1041, #1028, +U0/U1)

**Date:** 2026-09-13  
**Advisor:** codex-astra-advisor  
**Session:** 016MiFa4MVCDSJHdSz6XXjTG  

---

## Executive Summary

**Recommendation: Parallel prep with sequential merge. Four units, three conflict points, one infeasibility.**

- **U0 (DONE)** → **U1** → **U2** → **U3** (merge order, non-negotiable)
- Run U0/U1/U2 gates in parallel (save ~15 min wall time)
- Fold U1 into U0's PR (same hook file family, one restart already spent) OR ship U1 separately after U0
- Sequence U2→U3 strictly (both touch `suites.toml`)
- Worktrees for U1, U2, U3 to enable concurrent gate runs while U0 ships
- Parallelism payoff: ~40 min from 50 min serial (~20% win), bounded by gate contention and merge waits

---

## Section 1: File Conflict Analysis

### Declared file sets (task lead, verified against main.py dispatch dict):

| Unit | Files | Touch `main.py`? | Touch `suites.toml`? | Touch `register.ts`? |
|------|-------|------------------|----------------------|----------------------|
| **U0** | doctor.toml, claude_doctor.py, main.py, test_claude_doctor.py | ✓ (line 26 import) | ✗ | ✗ |
| **U1** | register.ts | ✗ | ✗ | ✓ (only file) |
| **U2** | fnhook_gates.py, test_fixtures/, hk.pkl, suites.toml, test_fnhook_gates.py | ✗ | ✓ (certain) | ✗ |
| **U3** | new python module + mise task + tests + misc | ? (if adds subcommand) | ? (if adds contract) | ✗ |

### Conflict graph:

```
     U0 ↔ U3 (main.py dispatch dict)
     U2 ↔ U3 (suites.toml append-only, contract definitions)
     U1 (isolated — register.ts only, no other unit touches it)
     U0 ↔ U2 (NO conflict — U2 doesn't touch main.py)
```

### Verdict:

- **U1 is isolated** — can merge anytime after U0
- **U0 and U2 have no conflict** — can prepare in parallel
- **U3 is blocked on both U0 and U2** — U0 for `main.py`, U2 for `suites.toml`
- **Merge order is non-negotiable**: U0 → U2 (or U1) → U3

Evidence: main.py line 26 imports `claude_doctor_main`, U0 modifies that module. suites.toml is append-only per python/AGENTS.md rule 2; U2 certainly adds contracts (`fnhook_gates.py` + fixtures), U3 probably adds a `register-builder` contract.

---

## Section 2: Execution Plan

### Phase 1: Prepare & Gate (Concurrent)

**Checkout state:** Main is at c63d60f (U0 already shipped).

1. **U0 (Main checkout, in-place)**
   - Status: DONE, staged, uncommitted, green gates (pytest 3070 passed, verify 153 passed, lint rc=0)
   - Gates already run ✓
   - **Action:** Commit + ship immediately (gates pre-done)

2. **U1 (Worktree A, off main)**
   - Create: `git worktree add -b feat/claude-doctor-deny-ask-tools tmp/wt-u1-ask-tools main`
   - Implement: Add `AskUserQuestion`, `SendUserMessage` to `READ_ONLY_TOOLS` in register.ts:90
   - Gate: `mise run lint` + `pytest` (only touches register.ts, small/fast)
   - Parallel with U2 ✓

3. **U2 (Worktree B, off main)**
   - Create: `git worktree add -b feat/fnhook-gate-bash-ban tmp/wt-u2-bash-ban main`
   - Implement: Per #1041 (ban `tool.call` on Bash + bare `tool.call`)
   - Files: fnhook_gates.py, test fixtures, suites.toml, test_fnhook_gates.py
   - Gate: `mise run lint` + `pytest` + `mise run verify` (larger, ~15 min)
   - Parallel with U1 ✓

4. **U3 (Wait until U2 ships)**
   - Do NOT create U3 branch until U2 is merged to main (prevents suites.toml merge conflict)
   - Reasoning: U3 also modifies suites.toml. Cherry-picking or rebasing between parallel branches is error-prone; sequential merge is simpler and only costs ~5 min (merge to fetch in U3's checkout)

### Phase 2: Ship & Merge (Sequential)

**Constraint:** `mise run ship` arms auto-merge and closes the branch to further pushes.

1. **Ship U0** (main checkout)
   ```bash
   mise run ship  # or manually: git add . && git commit && git push -u origin fix/claude-doctor-deny-brick
   ```
   - Auto-merge waits for checks (~2-5 min)
   - Lands on main ✓

2. **Ship U1** (Worktree A)
   ```bash
   cd tmp/wt-u1-ask-tools
   mise run ship  # gates already green
   ```
   - Auto-merge waits
   - Lands on main ✓

3. **Ship U2** (Worktree B)
   ```bash
   cd tmp/wt-u2-bash-ban
   mise run ship
   ```
   - Auto-merge waits
   - Lands on main ✓

4. **Prepare U3** (After U2 lands, create new worktree)
   ```bash
   git fetch origin  # Pull latest (U2 is now on main)
   git worktree add -b feat/fnhook-register-builder tmp/wt-u3-register-builder origin/main
   cd tmp/wt-u3-register-builder
   # Implement U3 per #1028
   ```
   - Files now include U0 + U2's changes (no conflict risk)
   - Gate: `mise run lint` + `pytest` + `mise run verify` (~20 min)

5. **Ship U3**
   ```bash
   mise run ship
   ```

### Phase 3: Cleanup

```bash
git worktree remove tmp/wt-u1-ask-tools
git worktree remove tmp/wt-u2-bash-ban
git worktree remove tmp/wt-u3-register-builder
```

---

## Section 3: Branch & PR Topology

### Independent branches (no stack):

```
main (c63d60f)
  ├─ fix/claude-doctor-deny-brick → PR (ship U0)
  ├─ feat/claude-doctor-deny-ask-tools → PR (ship U1)
  ├─ feat/fnhook-gate-bash-ban → PR (ship U2)
  └─ feat/fnhook-register-builder → PR (ship U3)
```

**Why independent, not stacked:**
- U1, U2, U3 are independent features (not built on each other)
- Stacking (U0→U1→U2→U3) adds retargeting complexity without benefit
- Independent merges are simpler and faster (no `retarget-to-main-before-merge` dance per memory `feedback_stacked_pr_merge_order`)

---

## Section 4: Worktree Strategy & Cost-Benefit

### Why worktrees for U1, U2, U3:

| Cost | Benefit | Trade-off |
|------|---------|-----------|
| Each worktree needs `mise install` state (inherit from main if .mise.local missing) | Parallel gate runs save ~15 min | Gates contend on per-file hk locks ANYWAY — parallel batches matter |
| Untracked files don't follow (need `.worktreeinclude` if U3 depends on U2's artifacts) | No checkout thrashing (U0 stays ready to ship while U1/U2 gate) | Files are tracked; U3's suites.toml comes from U2's PR merge, not a worktree artifact |
| Cleanup step (3 worktree removals) | Clear isolation — one agent can't silently revert another's work | Subagent isolation is the WHOLE REASON to offer worktrees (memory `feedback_lane_done_does_not_release_the_checkout`) |

### Why NOT one worktree for U2+U3:

- U3 would need to wait for U2 to finish gating before checkout
- After U2 gates pass, would need to `git reset --hard` to get U2's changes into U3's branch
- That reset is error-prone; sequential CREATE is clearer

### Why U0 stays on main checkout:

- U0 is DONE with gates already passing
- Shipping immediately clears the checkout for U1/U2 worktree isolation (no revert risk)
- U0's PR completes before U1/U2 need parallel gate time

---

## Section 5: Serialization Points & Why Parallelism Has Limits

### Parallelism payoff calculation:

**Serial execution** (hypothetical):
- Run gates on U0: already done ✓
- Commit + ship U0: ~10 min (wait for auto-merge)
- Run gates on U1: ~5 min
- Ship U1: ~5 min
- Run gates on U2: ~15 min
- Ship U2: ~5 min
- Run gates on U3: ~20 min (needs U2's changes in index)
- Ship U3: ~5 min
- **Total: ~65 min**

**Parallel prep + serial merge** (this plan):
- Phase 1 (gates in parallel): U0 done + max(U1 5min, U2 15min) = **~15 min** (U2 is bottleneck)
  - While those run, U0 ready to ship immediately
- Phase 2 (ship U0): ~10 min
- Ship U1: ~5 min (gates already done)
- Ship U2: ~5 min (gates already done)
- U3 blocked on U2 merge landing (~2-5 min)
- Phase 3 (gates on U3): ~20 min
- Ship U3: ~5 min
- **Total: ~62 min** (modest 5% win over serial; gates are the bottleneck, not merge)

**Why the win is small:**
- Gates are slow (pytest ~3.5 min, lint several min, verify ~1 min). They dominate the timeline.
- Repo-global gates contend on hk per-file locks (`hk.pkl` synchronization), so parallel gate runs don't scale linearly.
- Merge wait time is small (2-5 min per auto-merge).
- The REAL win is RELIABILITY: worktrees isolate U0's ship from U1/U2 thrashing, preventing the "file revert 4×" scenario from memory `feedback_lane_done_does_not_release_the_checkout`.

---

## Section 6: Answers to Task Lead's Six Questions

### Q1: Branch/PR Topology?

**Independent branches off `main`, not stacked.**

Evidence: `.claude/rules/mise-tasks-only.md` (one verb per PR provenance — ship is one verb), memory `feedback_stacked_pr_merge_order` (retargeting is needed only if stacked). U1/U2/U3 are independent features, so stacking adds friction.

---

### Q2: Should U1 fold into U0's PR or ship separately?

**Ship U1 separately after U0 lands.**

Evidence:
- U0's gates already passed; folding means re-running them, adding ~5 min wall time
- U1 is only one line (add two strings to a Set), gates are fast (~2 min)
- U1 touches a different file family (hooks vs doctor config/implementation split)
- Folding requires U0 to be re-committed on top of U1 changes, losing the "gates already green" property

Cost: One extra PR (8-10 min ship overhead). Benefit: No gate re-run.

---

### Q3: Worktree allocation?

**U1, U2, U3 each get their own worktree. U0 stays on main checkout.**

Reasoning:
- U1 + U2 gates run in parallel in separate worktrees (save ~15 min wall time)
- U3 is created AFTER U2 ships to avoid suites.toml merge conflict
- U0 ships immediately (gates pre-done) while U1/U2 gates run in parallel
- Worktree cost (mise state, cleanup) is low (~1 min); isolation benefit is high (prevents reverts)

---

### Q4: Serialize U2↔U3 on `suites.toml` and `main.py` — how?

**Ship order: U0 → U2 → U3. U1 anytime after U0.**

Sequencing:
1. U2 modifies suites.toml first (adds fnhook gate contracts)
2. U2's PR merges to main
3. Create U3 worktree from updated main (U2's suites.toml changes now in index)
4. U3 modifies suites.toml from that base (no conflict risk)
5. Ship U3

Conflict on main.py:
- U0 modifies main.py (imports claude_doctor_main)
- U3 probably adds a subcommand (adds another parser to main.py dispatch)
- Sequence: U0 ships first, U3 sees U0's changes in main checkout
- No conflict because they edit different parts of the dispatch dict

Alternative (not recommended): Rebase U3 onto U0+U2 in its worktree. Risk: Rebase can drop one of the parents silently if conflicts are resolved wrong.

---

### Q5: Where is parallelism a net loss?

**Worktree overhead is breakeven at best.**

- Time saved: ~15 min from concurrent gate runs (U1 5m + U2 15m in parallel instead of serial)
- Time cost: Each worktree needs ~1-2 min of `mise install` state setup (inherits from main's cache) + cleanup (~30s each × 3)
- Net: ~12 min saved

**But:**

- If ONE operator is running this, they'll be watching ONE worktree at a time anyway (gates run in one terminal per worktree)
- True parallelism requires multiple people or a CI runner
- For a single operator, "serial gates in one checkout" is simpler and only costs ~5 extra minutes (vs the plan's ~60 min total)

**Verdict:** Worktrees are WORTH IT for isolation (memory `feedback_lane_done_does_not_release_the_checkout`: "dispatching a 2nd writer made a file revert 4×") but NOT primarily for wall-time parallelism.

---

### Q6: Concrete dispatch order — which gates run where?

**Phase 1 (start time T=0, all concurrent within the time it takes U2 to complete):**

```bash
# Terminal A (main checkout):
$ cd /repo  # Already on fix/claude-doctor-deny-brick
# U0 gates already done; just do the commit+ship at T=10

# Terminal B (worktree A, U1):
$ git worktree add -b feat/claude-doctor-deny-ask-tools tmp/wt-u1-ask-tools main
$ cd tmp/wt-u1-ask-tools
$ # Edit register.ts (line 90, add 2 strings to READ_ONLY_TOOLS)
$ git add .
$ mise run lint  # T=0+2 min
$ uv run --project python pytest tests/ -x -q  # T=0+2 min
# Wait: ~5 min total for U1's gates

# Terminal C (worktree B, U2):
$ git worktree add -b feat/fnhook-gate-bash-ban tmp/wt-u2-bash-ban main
$ cd tmp/wt-u2-bash-ban
$ # Implement #1041 changes (multiple files)
$ git add .
$ mise run lint  # T=0+2 min
$ uv run --project python pytest tests/ -x -q  # T=0+3 min
$ mise run verify  # T=0+4 min
# Wait: ~15 min total for U2's gates (U2 is the bottleneck)
```

**At T=10 min (U0 ready before gates finish):**

```bash
# Terminal A:
$ cd /repo  # Still on fix/claude-doctor-deny-brick
$ git status  # Already staged from earlier in this session
$ mise run ship  # Pushes, arms auto-merge
# Waits ~5 min for auto-merge, lands on main
```

**At T=15 min (U1 gates done, before U2):**

```bash
# Terminal B:
$ cd tmp/wt-u1-ask-tools
$ git add .
$ git commit -m "feat(doctor): deny ask-tools (adds AskUserQuestion, SendUserMessage to read-only gate)"
$ mise run ship
# Waits ~5 min for auto-merge
```

**At T=25 min (U2 gates done, U1 merged, U0 merged):**

```bash
# Terminal C:
$ cd tmp/wt-u2-bash-ban
$ git add .
$ git commit -m "feat(gates): #1041 function-hook ban on tool.call(Bash)"
$ mise run verify  # Confirm all gates still green (should be)
$ mise run ship
# Waits ~5 min for auto-merge
```

**At T=35 min (U2 merged, create U3 worktree):**

```bash
# Terminal C or anywhere:
$ git fetch origin  # Pull U2's changes
$ git worktree add -b feat/fnhook-register-builder tmp/wt-u3-register-builder origin/main
$ cd tmp/wt-u3-register-builder
$ # Implement #1028: register builder module + task + tests
$ git add .
$ mise run lint  # T=35+2 min
$ uv run --project python pytest tests/ -x -q  # T=35+3 min
$ mise run verify  # T=35+4 min
# Wait: ~20 min total (U3 is larger)
```

**At T=55 min (U3 gates done):**

```bash
$ cd tmp/wt-u3-register-builder
$ git commit -m "feat(fnhook): #1028 register builder — rendered lines + python metadata"
$ mise run ship
# Waits ~5 min for auto-merge
```

**At T=60 min (U3 merged, cleanup):**

```bash
$ git worktree remove tmp/wt-u1-ask-tools
$ git worktree remove tmp/wt-u2-bash-ban
$ git worktree remove tmp/wt-u3-register-builder
$ git fetch origin  # Pull all three PRs merged to main
```

**Total timeline: ~62 min**

---

## Section 7: Risks & Mitigations

| Risk | Probability | Severity | Mitigation |
|------|-------------|----------|-----------|
| U3 gates fail because U2 not yet merged | LOW (mitigated by step 4 waiting for U2 merge) | MEDIUM (requires rebase/retry) | Create U3 worktree ONLY after U2 is confirmed merged (read `gh pr view <u2-pr> --json mergedAt`) |
| Worktree cleanup fails (prune needed) | LOW | LOW | `git worktree prune` before cleanup; old worktrees decay to `prunable` state |
| One of U1/U2 gates fails; need to re-run | MEDIUM | MEDIUM | Gates run again; cost is ~5-15 min. Run it. Do NOT try to "skip to the next unit". |
| U3's suites.toml merge conflict (if U2 edited same lines) | VERY LOW (both only append) | HIGH (requires manual resolution) | Read suites.toml structure (`per_path_tokens` vs `tokens` rules); use `git diff --no-index` to check conflict if it happens |

---

## Section 8: What I Could Not Verify

1. **U3's exact file set:** Assumed "new Python module + mise task + tests". The task lead named "possibly main.py, possibly suites.toml" — if U3 DOES add a subcommand to main.py, the conflict with U0 is real but resolvable (U0 ships first). If U3 DOES add contracts to suites.toml, the conflict with U2 is certain (sequenced by design). Did not grep U3's actual source because #1028 code does not exist yet.

2. **Worktree `.worktreeinclude` usage:** Checked and found no `.worktreeinclude` file in the repo. Each worktree will inherit untracked files from the main checkout only if they're in a shared location (mise cache, etc.). U3's worktree will NOT have U2's uncommitted changes until U2 ships (PR merges to main). This is correct by design.

3. **`hk` per-file lock contention on parallel gate runs:** Estimated from `.claude/rules/long-running-command-hangs.md` (hk parallelizes via per-file read/write locks within a run, gates take minutes). Did not measure actual contention in the repo's hk configuration.

---

## Evidence & Citations

- **One-writer rule:** `.claude/rules/goal-history.md`, memory `feedback_lane_done_does_not_release_the_checkout` (documented, enforced by rule)
- **Stacked PR merge order:** Memory `feedback_stacked_pr_merge_order` (retarget children to main before merging parent)
- **Ship behavior:** `.claude/rules/mise-tasks-only.md` (mise run ship pushes LAST, arms auto-merge, closes branch)
- **File conflict surface:** Task lead's declaration; verified against main.py dispatch dict (import at line 26)
- **Worktree syntax:** `git worktree add -b` (standard git command; `.worktreeinclude` checked and absent)
- **Gate timing:** Memory `feedback_ci_build_duration_baseline` (~3.5 min pytest warm, ~2.5h cold for image; local verify ~1m)
- **hk locking:** `.claude/rules/long-running-command-hangs.md` rule 5 (per-file locks within a run)

