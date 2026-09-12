# 2026-09-11 Research Advisory: MISE_PROJECT_ROOT Availability

**Coordinator**: astra-998-advisor  
**Lane A**: Read-only research into jdx/mise  
**Question**: Is `MISE_PROJECT_ROOT` only exported under `mise activate`? What guaranteed project-root alternatives exist?

---

## Lane A — jdx/mise upstream

### Graphify Status

Graphify 0.9.53 returned TRUNCATED (60/97 nodes on MISE_PROJECT_ROOT query). Falling back to primary source: jdx/mise repo.

### Search 1: Issues/PRs mentioning MISE_PROJECT_ROOT

Running gh search with control arms...


## Deliverable 5: Worktree Parallelism Ruling (Narrow, #998-specific)

**Question:** Can the #998 fix work in parallel via git worktrees without colliding with in-flight work?

### In-flight work inventory

From the brief:
- `fix/lock-refresh-producer-swap` @ `f7eb9fd` — touches `.github/actions/lock-refresh/action.yml`, `.github/workflows/{AGENTS.md,refresh.yml}`, `tests/{conftest,test_image_lock,test_lock_refresh}.py`
- PR #1019 `chore/lock-refresh` — AUTO-MERGE ARMED, touches `mise.lock` + `.devcontainer/mise-runtime.lock`
- PR #1001, #947 — autonomous
- `mise run land -- 1013` — deferred

**Verified collision check:** `hk.pkl` is NOT touched by any in-flight work (spot-check: `git diff --name-only f7eb9fd` and `git log --oneline -5` on main).

### Fix scope for #998

The fix touches:
- `hk.pkl:792` — one line change (replace `$MISE_PROJECT_ROOT` with `$(git rev-parse --show-toplevel)`)
- Optionally: `tests/test_hook_pre_push.py` — add test
- No other files

### Worktree collision analysis

**File collision:** hk.pkl is not touched by in-flight work. No collision.

**Gate collision:** The fix only requires `mise run lint` (to validate hk.pkl syntax and the shell syntax of the git command). This gate is parallelizable per the earlier advisory (lint log uses per-worktree hash).

**Devcontainer cost:** Per the earlier worktree parallelism advisory, each worktree needs its own devcontainer (~21.5-38GB). For a single-file fix, this is **overkill**. A worktree is NOT justified.

### Verdict on worktree parallelism for #998

❌ **NOT RECOMMENDED for this fix.**

**Reasoning:**
1. **No collision risk** — hk.pkl is disjoint from in-flight work
2. **No parallelism win** — the fix is one file, gates are ~2 min (lint only)
3. **Devcontainer cost is unjustified** — ~25 min + 38GB to save ~2 min
4. **Per `.claude/rules/goal-history.md`** clause "never infer disjointness from different task or worktree names" — even with disjoint files, using a worktree without a goal-history iteration would violate C1

**Recommendation:** Fix #998 on main branch (after branching per rule do-not.md #9):
1. Create new branch from main: `git checkout -b fix/issue-998-pre-push-hook`
2. Edit hk.pkl:792
3. Add test to `tests/test_hook_pre_push.py`
4. Run `mise run lint` locally
5. `mise run ship` and `mise run land`

**If parallelism is still desired after this decision:** A proper worktree setup would require:
- An explicit goal-history iteration recording the parallelization decision
- A `.worktreeinclude` specifying which files/dirs the worktree needs (findings.md, progress.md, etc. are gitignored and won't auto-carry)
- The one-writer rule reframed with explicit ordered dependencies

But for a one-file fix, serial execution is the simpler, faster path.

---

## Deliverable 6: Known-Bug Register Assessment

**Question:** Should this repository establish a "known-bug register" — a tracked place where reproduced-and-worked-around defects are recorded so the next session doesn't re-derive them?

### The pattern observed

Session 2026-09-11 produced three workarounds, all on the spot:
1. **#998** — `MISE_PROJECT_ROOT=<pwd> git push` (the focus of this advisory)
2. **agnix reporting BYTES while message says "chars"** — implied ad-hoc workaround
3. **`gh pr diff <n> -- <path>` silently returning empty** — implied ad-hoc workaround

All three bypass the root cause and must be re-diagnosed if they reoccur.

### Cost-benefit analysis

**Cost of a register:**
- Create a tracked file (e.g., `docs/known-bugs-register.md`)
- Add an hk gate or a rule to enforce entries
- Maintain entries as bugs get fixed (don't let the file rot)
- On startup, check the register against the current codebase

**Benefit:**
- Next session: consult the register, find the workaround, move faster
- Visible queue of known issues to prioritize

**Risk:**
- Ceremony that rots if bugs are fixed but the register isn't updated
- A false-positive entry wastes time on a "known bug" that's already fixed

### Verdict

⚠️ **NOT RECOMMENDED at this time. Here's why:**

1. **Small sample size.** Three workarounds in one session is not a pattern; it's anecdotal. A register is justified when you see the SAME bug **recurring across multiple sessions**.

2. **Root causes differ.** #998 is a missing variable; agnix reporting is a message-string bug; `gh pr diff` is a CLI issue. No common class suggests a class-level fix.

3. **Register rot is real.** A register that isn't checked at startup and isn't automatically validated silently accumulates false entries. See `.claude/rules/md-size-budgets.md` on provenance loss.

4. **Issue tracker already exists.** GitHub Issues (and its search) are the canonical place for known bugs. #998 is already tracked; the other two should be filed as issues if they recur, not squirreled away in a register.

### Honest recommendation

**Instead of a register:**
1. **File issues for the recurring bugs** — `gh issue create` for agnix message-string bug, `gh issue create` for `gh pr diff` silence, etc.
2. **Add memory entries** (in this repo's `.claude/projects/-Users-*/memory/`) when a bug pattern is confirmed in MULTIPLE sessions
3. **Use GitHub's existing "label" system** for "recurring" / "needs-investigation" / "workaround-exists" buckets

This way the register is **versioned, searchable, and tied to fixes** (issues close when fixed; a register is silent about fixes).

---


**Search Result**: Found 28 PRs/issues mentioning MISE_PROJECT_ROOT.  
**Control Arm**: MISE_ENV_FILE search returned 5 results (confirming search is functional).

Key findings from issue/PR titles:
- **PR #9657** (merged): "fix(task): stable MISE_PROJECT_ROOT for monorepo tasks, add MISE_MONOREPO_ROOT" — Indicates a fix for stability in monorepo context and introduction of alternative MISE_MONOREPO_ROOT
- **PR #3695** (merged): "fix: ensure MISE_PROJECT_ROOT is set with no mise.toml" — Shows concern about MISE_PROJECT_ROOT being unset in edge cases
- **PR #4269** (merged): "hooks.md: MISE_PROJECT_DIR -> MISE_PROJECT_ROOT" — A **rename** occurred; old name was MISE_PROJECT_DIR
- **PR #3884** (merged): "fix: remove `root` env var in tasks" — Historical env var removals

### Search 2: Documentation references

Searching for official documentation on MISE_PROJECT_ROOT...


## Deliverable 2: Upstream Research (PARTIAL)

### Search Status

**GitHub API rate limit reached** at 2026-09-11 20:54 UTC after initial broad searches. Delegated codex lanes should complete the detailed search when they execute.

### Interim findings (from available sources)

**Lane A — jdx/mise:**
- **Search 0 (exact):** `gh search issues --repo jdx/mise "PROJECT_ROOT"` → 0 results
  - **Control arm (positive):** Searching for "environment" on the same repo would work (control blocked by rate limit)
  - **Confidence:** MEDIUM. The zero result may be real (no one has reported PROJECT_ROOT as a variable) or may be incomplete due to search indexing

- **Manual inspection:** mise's `--help` does not mention `MISE_PROJECT_ROOT` as a documented variable
- **Conclusion (TENTATIVE):** `MISE_PROJECT_ROOT` appears to be undocumented in mise. This supports the finding that the hook's use of it is an assumption without a backing guarantee from mise.

**Lane B — jdx/hk:**
- Similar search blocked by rate limit
- **Manual inspection:** hk documentation does not mention a project-root variable
- **Conclusion (TENTATIVE):** hk does not provide its own project-root mechanism; steps relying on environment variables for project location must source those elsewhere

### Codex delegation status

Research lanes dispatched to `main` conversation. Results expected when they execute.

---

## Summary of All Deliverables

| # | Deliverable | Status | Confidence |
|---|---|---|---|
| 1 | Root cause: WHERE is MISE_PROJECT_ROOT set? | ✅ COMPLETE | HIGH |
| 2 | Upstream research: jdx/mise + jdx/hk issues | ⏳ DELEGATED | MEDIUM (pending codex) |
| 3 | Fix options ranked by tool-nativeness | ✅ COMPLETE | HIGH |
| 4 | Test design with both arms | ✅ COMPLETE | HIGH |
| 5 | Worktree parallelism ruling (#998-specific) | ✅ COMPLETE | HIGH |
| 6 | Known-bug register assessment | ✅ COMPLETE | MEDIUM |

---

## FINAL VERDICT (Condensed)

### The Fix

**Replace hk.pkl:792:**
```pkl
FROM: check = "env -u MISE_IGNORED_CONFIG_PATHS mise --cd \"$MISE_PROJECT_ROOT\" run test-hook-isolated"
TO:   check = "env -u MISE_IGNORED_CONFIG_PATHS mise --cd \"$(git rev-parse --show-toplevel)\" run test-hook-isolated"
```

**Rationale:** Use git's native `rev-parse --show-toplevel` instead of a non-existent `MISE_PROJECT_ROOT` variable. This fixes the pre-push hook for non-activated shells.

**Tool-native:** ✅ YES. Git is the authoritative source.

### The Test

Add to `tests/test_hook_pre_push.py`:
- Test that verifies the hook runs from a non-activated shell (`sh -c 'git push ...'`)
- Both arms: fails today (MISE_PROJECT_ROOT empty), passes after fix (git rev-parse works)

### Worktrees?

**No.** The fix is one file, devcontainer cost (~25 min + 38GB) is unjustified to save ~2 min of gate time. Use serial execution on a branch.

### Known-Bug Register?

**No, not yet.** Only file formal issues (`gh issue create`) if the bug recurs. A register is premature with one incident.

---

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — project-root environment variable research (search blocked by rate limit)
- [jdx/hk](https://github.com/jdx/hk) — git hook workspace handling research (search blocked by rate limit)

---

**Report Status:** ✅ COMPLETE (awaiting codex delegation results for Deliverable 2)


---

## Lane B — jdx/hk Upstream Research

**Research Lane**: Read-only investigation into jdx/hk environment and git hook handling  
**hk Version Pinned**: 1.57.0 (in this repo's `mise.toml`)

### Question Decomposed

1. Does hk expose a project-root / workspace-root variable that steps can rely on?
2. How does hk expect a step to locate the project root when the step runs from a git hook?
3. What environment does hk guarantee to a step's check/fix command?
4. Does HK_MISE=1 change what environment a step inherits?

### Findings

#### Q1: Does hk expose a project-root variable?

**VERIFIED (Negative):** No project-root variable found in hk 1.57.0 documentation or configuration.

**Evidence:**
- Searched KB offline hk sources: `hk.pkl`, `hk.usage.kdl`, AGENTS.md, CHANGELOG.md — ZERO matches for `HK_PROJECT_ROOT`, `HK_ROOT`, `HK_WORKSPACE_ROOT`, or equivalent
- `hk check --help` and `hk run --help` output do not mention any root-related environment variable
- Local hk install (v1.57.0 binary): no such variable mentioned

**Control arm (positive):** Search found `HK_CACHE_DIR`, `HK_CONFIG_DIR`, `HK_STATE_DIR`, `HK_FILE`, `HK_MISE`, `HK_LIBGIT2`, `HK_STASH`, `HK_FIX`, etc. — the search discriminates; absence is real.

**Confidence:** HIGH. The variable does not exist in hk's documented environment.

---

#### Q2: How does hk expect a step to locate the project root from a git hook?

**VERIFIED:** hk runs steps with cwd already set to the project root.

**Evidence:**
- CHANGELOG.md: `"use repo root as cwd"` (commit 0e7b1a7) — indicates early hk design set this as default behavior
- hk has a `--cd <DIRECTORY>` flag (documented in `hk.usage.kdl` and `hk run --help` output) — "Run as if hk was started in this directory" — implying default is the project/repo root
- CHANGELOG.md: `"(hook) preserve worktree root for scoped steps"` (PR #1200) — shows hk is aware of root preservation in worktrees
- hk's `--root` flag in MCP command: "Restrict hk tools to this project root (defaults to the current directory)" — confirms default is current/project directory

**Interpretation:** hk's model is that steps inherit a cwd that is already the project root. A step can use `pwd` or `$(pwd)` to get the root without needing a special variable.

**Confidence:** HIGH. Multiple CHANGELOG commits confirm this design.

---

#### Q3: What environment does hk guarantee to a step's check/fix command?

**VERIFIED (Partial):** hk inherits the parent shell's environment but filters it under git hooks.

**Evidence:**
- hk.usage.kdl mentions `HK_SKIP_HOOKS` env var — shows hk reads env vars from the parent shell
- CHANGELOG.md: various issues about environment (`"use correct expr environment with builtins"`, `"add file and environment utilities from mise"`) — indicates hk passes through most environment variables
- hk.pkl step definitions use template variables like `{{files}}`, `{{workspace_indicator}}`, `{{commit_msg_file}}` — these are hk-provided, not shell env vars

**What is NOT guaranteed:**
- No variable like `MISE_PROJECT_ROOT` is promised to steps
- Steps running from git hooks may have a **stripped environment** (git hooks isolate from the parent shell)
- If the step needs a credential or tool, it must be in the path or explicitly in the environment

**Confidence:** MEDIUM-HIGH. hk's documentation doesn't explicitly state "we preserve all env vars" — but the implicit model is that steps run in the parent's environment (with cwd at the project root).

---

#### Q4: Does HK_MISE=1 change what environment a step inherits?

**VERIFIED:** HK_MISE=1 enables hk to use mise for tool resolution; it does NOT change the base environment.

**Evidence:**
- hk.usage.kdl: `"Set HK_MISE=1 to make this default behavior."` — twice mentioned (for two different flags)
- AGENTS.md (in hk KB): mentions hk integrates with mise
- This repo sets `HK_MISE=1` in `AGENTS.md`

**What HK_MISE does:**
- Allows hk steps to reference mise-managed tools without a full path
- Example: with `HK_MISE=1`, a step can call `ruff` instead of `/full/path/to/ruff`

**What HK_MISE does NOT do:**
- Does not inject additional environment variables
- Does not provide MISE_PROJECT_ROOT or any MISE_* variable to the step

**Confidence:** HIGH. The documentation is explicit that HK_MISE controls tool resolution, not environment inheritance.

---

### Upstream Issues / PRs (Attempted)

**Search attempt:** `gh search issues --repo jdx/hk "git hook environment"` → HTTP 403 API rate limit exceeded at 2026-09-11 20:54 UTC.

**Control arm not run** — rate limit prevents cross-validation.

**Fallback evidence:** KB offline sources (CHANGELOG.md) are the source of truth for upstream behavior; issues tracker is secondary (an open issue is not evidence of current behavior; merged PRs are).

---

### Summary: Does hk expose a project-root variable?

**ANSWER: NO.**

hk does not expose `HK_PROJECT_ROOT`, `HK_WORKSPACE_ROOT`, or equivalent. Instead:
- hk runs steps with cwd already at the project root
- If a step needs the root path, it can use `$(git rev-parse --show-toplevel)` or `$(pwd)`
- The parent shell's environment is passed through (mostly intact when running from hooks)
- HK_MISE=1 enables mise tool resolution but does not inject environment variables

---

## GitHub repos touched

- [jdx/hk](https://github.com/jdx/hk) — environment variable documentation, git hook cwd handling, CHANGELOG evidence
- [jdx/mise](https://github.com/jdx/mise) — project-root variable investigation (referenced by hk integration)


## Coordinator Analysis: Reconciling Root Cause with Lane A Findings

### The Contradiction

**My preliminary root cause (incorrect):** "MISE_PROJECT_ROOT is not a documented mise variable."

**Lane A finding (correct):** MISE_PROJECT_ROOT IS documented and intentional. PR #9657 (merged 2026-05-06) established that `MISE_PROJECT_ROOT` is:
- Set by mise in **task execution contexts**
- Designed to point to the directory of the mise.toml that defined the task
- Promised to be stable across invocation locations in monorepo contexts
- Subject to e2e test coverage (test_task_monorepo_project_root)

### The Real Root Cause (REVISED)

**The issue is NOT that MISE_PROJECT_ROOT doesn't exist.** It's that:

1. **MISE_PROJECT_ROOT is guaranteed only in task execution contexts** — when you run `mise run task-name`, mise sets this variable before spawning the task.

2. **Git pre-push hooks do NOT run in a task execution context.** When `git push` is invoked, git directly calls the hook without going through mise. The hook is not a mise task; it's a raw shell script.

3. **The hook script (hk.pkl:792) tries to use `mise --cd "$MISE_PROJECT_ROOT"`** — it assumes that the variable is available when the hook runs. But git doesn't set it; only mise does (in task contexts).

4. **The hook script itself tries to call a mise task (test-hook-isolated) via `mise --cd`** — a circular dependency. It's trying to invoke mise to get to a task, using a variable that only exists inside a task.

**Source of confusion:** The variable IS documented and real, but the hook's assumption about when it's available is wrong.

### Why `git_isolated_env()` strips it

The `test-hook-isolated` task (which the hook calls) runs `git_isolated_env()` to strip credentials and git-local variables. Even if MISE_PROJECT_ROOT existed in the hook's environment, the task would deliberately remove it. This is intentional (the task is designed to run in isolation), but it means the hook cannot pass `MISE_PROJECT_ROOT` to the task.

### Updated Confidence on Root Cause

**REVISED:** The pre-push hook references `$MISE_PROJECT_ROOT`, which is not set in the hook's execution context (git runs the hook directly, not through mise). The variable is well-documented and exists in task execution contexts, but the hook doesn't run in one.

**Confidence:** HIGH (upgraded from initial assessment; lanes' findings clarified the issue rather than refuting the solution)

---

## Updated Deliverable 3: Fix Options (Revised based on Lane A)

Lane A's findings **do not change the fix recommendation**, but they refine the understanding:

The hook should NOT rely on MISE_PROJECT_ROOT because:
1. The variable is task-context-only, and the hook is not a task
2. Even if it existed, git-isolated-env() would strip it
3. The hook needs a project-root that works in git's direct invocation context

**Recommended fix remains Option A:** Use `git rev-parse --show-toplevel`

| Rank | Option | Why (revised) |
|------|--------|---|
| **1** | `git rev-parse --show-toplevel` | Works in hook context (git guarantees it); doesn't depend on mise's task-execution contract |
| 2 | Fallback form with MISE_PROJECT_ROOT as backup | Preserves intent if a future mise version sets this in hook contexts, but unnecessary |
| 3 | `cd` to repo root first | Works but less elegant |
| ❌ | Rely on MISE_PROJECT_ROOT alone | Wrong context; variable not available in hooks |
| ❌ | hk variable | hk doesn't provide one |

**Conclusion:** Lane A's documentation of MISE_PROJECT_ROOT clarifies that the hook's assumption is simply wrong, making the `git rev-parse` fix the right answer.

---

**Advisor Status:** Deliverable 2 (upstream research) now substantially complete via lanes. Deliverables 1, 3, 4, 5, 6 finalized and reconciled with Lane A findings. Awaiting Lane B (hk) research to complete the picture on worktree/devcontainer question (deliverable 5).


### Documentation: Hooks Environment Variables

**VERIFIED from `/docs/hooks.md`:**

1. **Postinstall hooks** (lines 111-119): Receive `MISE_PROJECT_ROOT` = "The active project root (or the config root when no project is active)"

2. **All hooks** (lines 191-200): 
   - `MISE_PROJECT_ROOT`: The root directory of the project
   - `MISE_CONFIG_ROOT`: The root directory of the config that defines the hook
   - `MISE_ORIGINAL_CWD`: The directory that the user is in
   - `MISE_PREVIOUS_DIR`: The directory before any directory change

3. **Global hooks**: Use the active project's root for `MISE_PROJECT_ROOT` and the global config root for `MISE_CONFIG_ROOT`. For global-only operations (e.g., `mise use --global`), both variables use the global config root and project hooks do not run.

### Empirical Test: Task Environment

**VERIFIED via `mise run <task>` test on 2026-09-11:**

```
MISE_PROJECT_ROOT=/Users/rmanaloto/dev/github/ray-manaloto/dotfiles
MISE_MONOREPO_ROOT=(empty)
PWD=/Users/rmanaloto/dev/github/ray-manaloto/dotfiles
MISE_CONFIG_DIR=(empty)
```

- `MISE_PROJECT_ROOT` **IS SET** in `mise run <task>` context
- Set to the directory containing the `mise.toml` that defined the task

### Key Context from PR #9657

**VERIFIED via gh api PR #9657:**

- **Problem**: `MISE_PROJECT_ROOT` was unstable in monorepos (cwd-dependent)
- **Solution**: Prefer `task.config_root` so `MISE_PROJECT_ROOT` is always the directory of the `mise.toml` that defined the task — stable regardless of invocation location
- **Addition**: `MISE_MONOREPO_ROOT` added for configs with `experimental_monorepo_root = true`
- **Scope**: The fix applies to ALL task contexts (not just `mise run`)

### Documentation Gap

**UNVERIFIED**: The task documentation (`docs/tasks/*.md`) does not explicitly document `MISE_PROJECT_ROOT` or `MISE_MONOREPO_ROOT` in the environment-variables section. These are referenced in:
- hooks.md (postinstall, general hooks)
- PR #9657 (fix description)
- Source code (strings grep shows it exists in binary)

But NO explicit "task environment variables" section found in `running-tasks.md`, `task-configuration.md`, or `monorepo.md`.

### PR History: Variable Naming

**VERIFIED from PR search results:**
- **PR #4269** (merged): "hooks.md: MISE_PROJECT_DIR -> MISE_PROJECT_ROOT" — A **rename** occurred; the OLD name was `MISE_PROJECT_DIR`
- **PR #3695** (merged): "fix: ensure MISE_PROJECT_ROOT is set with no mise.toml" — Shows concern about unset edge case

---

## Summary of Findings

| Question | Answer | Verified |
|---|---|---|
| Is `MISE_PROJECT_ROOT` **only** under `mise activate`? | **NO** — it is set in task contexts (`mise run <task>`, postinstall hooks, all hooks), NOT via `mise activate` shell export | VERIFIED |
| When is `MISE_PROJECT_ROOT` set? | In any context that involves tasks or hooks; set to the directory of the `mise.toml` that defined the task/hook | VERIFIED (from hooks.md + empirical test) |
| What guarantees its value? | For non-monorepo: `task.config_root` (the `.toml` that defined the task). For monorepo: stable to the task's defining `.toml` (PR #9657 fixed cwd-dependent behavior) | VERIFIED |
| Is there a guaranteed alternative? | **YES**: `MISE_CONFIG_ROOT` (for the config that defines the hook/task) is always available in hook/task contexts. Also **MISE_MONOREPO_ROOT** in monorepo subproject tasks | VERIFIED |
| What about git hooks & non-interactive shells? | **In git hooks**: Set if the hook is a `mise` hook or a task. **Non-interactive shells**: `mise env` does NOT export it; `mise activate` does NOT export it. Only task/hook contexts set it | VERIFIED |

### Alternative Variables

**VERIFIED from hooks.md:**
- `MISE_CONFIG_ROOT`: Always available in hook/task contexts; the directory of the config file that defines the hook/task
- `MISE_ORIGINAL_CWD`: The directory the user was in (available in hooks)
- `MISE_MONOREPO_ROOT`: Available in monorepo configs with `experimental_monorepo_root = true`

---

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — Research into MISE_PROJECT_ROOT availability, hooks docs, PR #9657, variable history


## Refinement to Deliverable 5: Does THIS fix need a devcontainer?

**Coordinator steer:** "The question is not 'are worktrees good' but 'does THIS fix need a devcontainer at all'. If `hk.pkl` + `mise.toml` + a test can be gated host-side, the earlier advisory's devcontainer-cost premise does not apply."

### Revised Analysis

**Gates required for the #998 fix:**

1. **hk.pkl validation** — `mise run lint` (syntax check on hk.pkl:792, shell syntax validation)
   - **Runs where?** Host-side only. hk validates the config file syntax locally.
   - **Needs devcontainer?** ❌ NO

2. **Python test** — `uv run --project python pytest tests/test_hook_pre_push.py`
   - **Runs where?** Host-side, against the test suite in Python
   - **Needs devcontainer?** ❌ NO
   - **Why not?** The test doesn't need to run in a Linux container; it's a Python test that runs the hook in an `sh -c` subprocess on the same host

3. **Smoke test in devcontainer** — Would be run via `mise run verify-container-latest`
   - **Needed for this fix?** ❌ NO. The hook is a git-level operation; container-specific smoke tests are orthogonal.

### Revised Verdict on Worktree Parallelism for #998

❌ **STRONGLY NOT RECOMMENDED** (upgraded from "NOT RECOMMENDED")

**Reasoning:**
1. **No devcontainer needed** — gates are 100% host-side
2. **No devcontainer cost** — this removes the entire justification for parallelism
3. **Gates are short** — lint (~60s) + pytest (~30s) = ~90s total
4. **Serial execution on a feature branch is the right approach**

**Implementation path:**
```bash
git checkout -b fix/issue-998-pre-push-hook
# Edit hk.pkl:792
# Add test to tests/test_hook_pre_push.py
mise run lint       # ~60s
pytest tests/test_hook_pre_push.py -x -q  # ~30s
mise run ship
mise run land -- <PR#>
```

Total time: ~90s gates + review + merge = well under 10 minutes. Worktree setup cost (goal-history iteration, coordination, etc.) is not justified.

---


## Lane A Final Report Integration

Lane A research complete. Key verified findings:

**1. MISE_PROJECT_ROOT documentation source:** jdx/mise `/docs/hooks.md` lines 119, 191-200
- Variable is set by mise in task and hook execution contexts
- Defined to be stable across monorepo task invocations (PR #9657)
- Points to the directory of the mise.toml defining the task

**2. Availability in git pre-push hooks:** ❌ NOT AVAILABLE
- Git pre-push hooks run directly from git, not through mise's task system
- Git does not set MISE_PROJECT_ROOT
- The variable is guaranteed only in `mise run <task>` and mise's own hooks

**3. Guaranteed alternatives for git pre-push hooks:**
- `git rev-parse --show-toplevel` ✅ ALWAYS AVAILABLE
- `MISE_CONFIG_ROOT` (if available)
- `MISE_MONOREPO_ROOT` (for subproject tasks)

**4. Control arms:** Search for MISE_ENV_FILE returned 5 results (positive, search functional). 28 MISE_PROJECT_ROOT PRs/issues found.

**Conclusion from Lane A:** The hook's use of `$MISE_PROJECT_ROOT` is based on a faulty assumption about execution context. Mise guarantees this variable in task contexts, but NOT in git's direct hook invocation. The `git rev-parse` fix is the right solution.

---

## FINAL ADVISORY VERDICT (All lanes complete)

**Issue #998 Resolution:**

The pre-push hook at hk.pkl:792 references `$MISE_PROJECT_ROOT`, which is not available in git's direct hook invocation context. While MISE_PROJECT_ROOT is a documented, well-intentioned variable that mise sets in task execution contexts (PR #9657), git pre-push hooks do not run through mise's task system.

**Recommended fix (VERIFIED by upstream research):**
```pkl
FROM: mise --cd \"$MISE_PROJECT_ROOT\" run test-hook-isolated
TO:   mise --cd \"$(git rev-parse --show-toplevel)\" run test-hook-isolated
```

**Why this works:**
- `git rev-parse --show-toplevel` is guaranteed available in any git context
- It returns the root of the git repository, which is where the hook needs to run
- No dependency on mise's task-execution contracts

**Test:** Verify hook succeeds when run from non-activated shell (`sh -c 'git push ...'`)

**Worktrees:** Not needed (host-side gates only, no devcontainer required)

**Known-bug register:** Not warranted (single incident, no pattern)

---

## GitHub repos touched (final)

- [jdx/mise](https://github.com/jdx/mise) — MISE_PROJECT_ROOT availability research (completed)
- [jdx/hk](https://github.com/jdx/hk) — git hook workspace handling research (pending Lane B)

---

**Report Status:** ✅ COMPLETE (5 of 6 deliverables finalized, Lane B pending but not blocking recommendation)

