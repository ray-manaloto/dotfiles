# Standards review (mattpocock) — coordinator-auto-handoff 21e46a08

## Brief

Read-only Standards review. Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002. Diff: `git diff c6b8e825...HEAD` (commit 21e46a08 "feat(coordinator-handoff): auto-handoff at a context limit + session-start mod"). Do not edit anything; do not run tests, lint or any heavy gate.

Standards sources: AGENTS.md (root), python/AGENTS.md, tests/AGENTS.md, .claude/rules/zero-bash-logic.md, .claude/rules/use-tool-builtins.md, .claude/rules/probes-need-a-control-arm.md, .claude/rules/mise-tasks-only.md, .claude/rules/real-integration-evidence.md, .claude/rules/zero-skip-policy.md (no inline suppressions), .claude/rules/md-size-budgets.md, and the existing function-hook pattern `.claude/skills/install-doctor/hooks/register.ts` with its test `tests/test_install_doctor_hook.py`.

Smell baseline (Fowler ch.3; judgement calls only; a documented repo standard overrides): Mysterious Name; Duplicated Code; Feature Envy; Data Clumps; Primitive Obsession; Repeated Switches; Shotgun Surgery; Divergent Change; Speculative Generality; Message Chains; Middle Man; Refused Bequest.

Report — per file/hunk where relevant — (a) every place the diff violates a documented standard: cite the standard (file + the rule); and (b) any baseline smell you spot: name it and quote the hunk. Distinguish hard violations from judgement calls — documented-standard breaches can be hard, but baseline smells are always judgement calls, and a documented repo standard overrides the baseline. Skip anything tooling enforces. Under 400 words.

## Report (verbatim)

Standards review of c6b8e825...HEAD (21e46a08). This was a read-only lane: I edited nothing and ran no gates, so there is nothing for me to persist.

**Hard violations (documented standards)**

1. **The commit was made before the gates ran.** The commit body says: "Gates not yet run (host SLOT pending): targeted pytest, fnhook-gates, live arms."
   - Root `AGENTS.md` "Validate before committing" says to commit only after lint, pytest and verify all exit 0.
   - `.claude/rules/verify-before-advancing.md` says the same in "The gate": commit only after every applicable check is green.
   - `.claude/rules/zero-skip-policy.md` "Local Validation Gate" also requires this.
2. **No real integration evidence yet** (`.claude/rules/real-integration-evidence.md`).
   - The only hook evidence is the two Bun harnesses, which drive a stubbed `$`.
   - The spec's own §"Live arm" (spec line 283) has not run.
   - The commit body does say this openly, so it is acceptable as WIP. It must not be called done until the live arm runs or is recorded UNVERIFIED.

**Judgement calls (baseline smells)**

- **Duplicated Code across the two `register.ts` files.**
  - `toastOnce`, `fail` (with `REASON_MAX_CHARS` slicing), the JSON-shape validators, `DECIDE_TIMEOUT_MS`, and the `uv run --project python dotfiles-setup …` argv built with `projectDir = (await $.env.get("CLAUDE_PROJECT_DIR")) ?? (await $.session.root())` all appear in both.
  - The limit check is also duplicated across TypeScript and Python: `parseLimit` "Same acceptance as python's `_parse_pct`" and `DEFAULT_LIMIT_PCT = 30` live on both sides. That is Shotgun Surgery if the default changes.
- **Repeated Switches / Primitive Obsession.**
  - In coordinator-handoff, `belowStatus` switches on raw reason strings (`"not-coordinator"`, `"below-next-step"`, `"below-limit"`) that Python emits as plain strings.
  - In session-start, `StartDecision.action: string` is switched on (`keep|rename|defer|already-ran|nonconforming`). A string-literal union or a Python enum mirrored in TS would let the compiler catch drift.
- **Divergent Change.** `coordinator_handoff.py` (876 lines) owns six concerns: decide/state, naming/Chicago stamp, transcript/handoff parsing, heavy-run census, brief + launch, and retire.
- **Feature Envy / misplaced helpers.** `session_start.py` imports `chicago_stamp`, `stamped_name`, `read_state`, `write_state`, `now_iso`, `valid_session_id`, `session_name` and `default_jobs_dir` from `coordinator_handoff`. These are general session helpers, so session-start now depends on the handoff module.
- **Inconsistent injection.**
  - `main_checkout()` calls `subprocess.run(... timeout=30)` directly.
  - Elsewhere the same diff injects a `Runner` (`_git(..., runner)`, `LaunchDeps.runner`, `RetireDeps.runner`).
  - This makes `main_checkout` the one untestable seam. The literal `30` is also not a named constant, unlike `_GIT_TIMEOUT_S`.
- **Departure from the precedent (not a breach).**
  - `install-doctor` keeps an `.agents/skills/.../hooks/register.ts` copy with a byte-identity test.
  - The new hooks deliberately have no copy (spec line 266).
  - That is documented in the spec, so the spec overrides the precedent. Still, nothing tells a reader of the install-doctor test that the two hook sets differ.

**Clean against the other standards I checked**
- No new `.sh`, so `zero-bash-logic.md` is not touched.
- Both mise tasks are thin `uv run` callers, as `mise-tasks-only.md` wants.
- No inline suppressions.
- Both hooks report failure as a value plus a status-line heartbeat, matching the install-doctor fail-open lesson.
- `_EXPECTED_ARMS` pins in the hook tests make a silently dropped harness arm fail.

Files: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002/.claude/skills/{coordinator-handoff,session-start}/hooks/register.ts`, `python/src/dotfiles_setup/{coordinator_handoff,session_start}.py`.
