# Agent report: codex-implementer — draft to-tickets breakdown for #831

Session: 2026-08-29h.

## Brief

Drafting/analysis task, no files created or modified, no mutating gh/git
commands. Decompose the approved spec at issue #831 into tracer-bullet
tickets per the `to-tickets` skill's vertical-slice rules. Read the skill
definition and the real source (`session_state.py`, `handoff_check.py`,
their tests) so the breakdown reflects real code structure. Report each
ticket as Title/Blocked by/What it delivers/Acceptance criteria, in
dependency order — the exact "quiz the user" presentation format.

## Report (verbatim)

CODEX REPORT
STATUS: complete
OBJECTIVE: Decompose the approved feature spec at GitHub issue #831 into tracer-bullet tickets per the `to-tickets` skill's vertical-slice rules, as a draft-only text deliverable (no files/commits/mutating gh calls).
CHANGES: none (working tree confirmed clean before and after the run; `git status --porcelain` empty, `git diff --stat` against baseline `7822751` empty)
VERIFIED: not applicable — the spec's own Verification section says "N/A, no tests to run"; codex's self-check was reading its own draft back against the skill's vertical-slice criteria (each ticket independently verifiable, sized for one context window, correct blocking edges) — this is a judgment call, not a machine-checkable command, so there is no captured/claim-only grade to assign here. `gh issue view 831` (CLI) failed in-sandbox with `error connecting to api.github.com`; codex fell back to a read-only MCP GitHub connector (`MCP_DOCKER/issue_read`) to fetch the real issue #831 body/comments, then read all four named source/test files directly (`nl -ba` on each) before drafting.
COMMIT: none — nothing to commit; spec said caller commits, tree left uncommitted (confirmed clean)
CODEX SAID: three tracer-bullet tickets, all "None — can start immediately" (no blocking edges, only "possible merge coordination" from shared source areas); no conflict found between issue #831 and current source/tests, no prefactor/expand-contract needed.
PROCESS: REAPED: 55009 (group dead)
FAST MODE: off (standard tier — no FAST MODE line)
EFFORT: applied: high (default — no EFFORT line in the dispatch)
GAPS: none

---

Codex's proposed ticket breakdown (verbatim from its final message, in dependency order — all three have no genuine blocking edges and can proceed in parallel):

**1. Bind session-state snapshots to the requested repository**
- **Blocked by:** None — can start immediately
- **What it delivers:** `session-state` produces the target repository's branch, tree, commits, and open-PR state even when the calling environment contains Git repository-redirection variables pointing at a decoy repository.
- **Acceptance criteria:**
  - With all six specified redirection variables set — `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_COMMON_DIR` — the snapshot still describes the target repository.
  - Both git and GitHub reads receive an environment without those variables while preserving unrelated environment values.
  - Verification uses real target and decoy git repositories under isolated temporary paths; only the GitHub subprocess boundary is substituted.
  - Existing session-state snapshot, rendering, and three-way PR-state behavior remains unchanged.

**2. Validate scoped extensionless citations in session handoffs**
- **Blocked by:** None — can start immediately
- **What it delivers:** `handoff-check` validates citations to `Makefile`, `Dockerfile`, and extensionless files beneath a subdirectory, producing the existing `Verdict`/`Finding` outcomes for missing paths and stale line ranges without admitting unrelated colon-delimited text.
- **Acceptance criteria:**
  - Valid allowlisted and subdirectory extensionless citations resolve without findings.
  - Missing files produce `MISSING_PATH`; invalid or out-of-range lines produce `BAD_LINE_RANGE`, preserving the exact citation text.
  - Bare, slash-free extensionless names outside the allowlist, such as `LICENSE:1`, remain ignored.
  - Numeric ratios, clock times, host-port pairs, mise flags, and documented cross-repository tasks remain ignored.
  - Verification exercises the public citation-checking behavior against real temporary files without mocking the citation matcher.

**3. Report handoff-check file-read failures without tracebacks**
- **Blocked by:** None — can start immediately
- **What it delivers:** When a handoff or cited file becomes unreadable after discovery, the `handoff-check` CLI returns its normal clean failure result instead of crashing with a Python traceback.
- **Acceptance criteria:**
  - An `OSError` while reading the handoff returns exit code 1, emits one actionable `handoff-check:` stderr line, and emits no traceback.
  - An `OSError` while reading a cited file follows the same failure path.
  - Existing missing-handoff, `RuntimeError`, successful-check, and finding-rendering behavior remains unchanged.
  - Tests use isolated temporary files and substitute only the filesystem read boundary; they do not mock internal collaborators or depend on permissions, timers, or production paths.

Codex's closing note: all three tickets are independently verifiable, fit a fresh context window, and have no genuine blocking edges — their only interaction is possible merge coordination from touching the same two source/test file pairs, not implementation dependencies.

## Outcome

User approved as-is (AskUserQuestion). Architect published all 3 as GitHub
issues #832/#833/#834, each tagged `ready-for-agent`, parent #831.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — read issue #831 via MCP GitHub connector fallback
