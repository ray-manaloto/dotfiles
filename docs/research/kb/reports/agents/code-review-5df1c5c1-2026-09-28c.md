# /code-review medium 5df1c5c1~1..5df1c5c1 (session dcb0b106, 2026-09-28c)

Verbatim final message.

---

I found one real issue in `5df1c5c1`. The `ReportFindings` tool isn't available in this session, so the finding is only reported here.

**Finding 1 (medium)** — `python/src/dotfiles_setup/handoff_check.py:42` (`ATTESTATION_PATH = ".plan-attestation"`, used at lines 238–256)

`handoff-check` always compares `./task_plan.md` against `./.plan-attestation`. `mise run plan-attest` doesn't always write there. The plugin's `attest-plan.sh` (3.21.0) picks the plan in this order:
1. `--target`
2. `$PLAN_ID`
3. `.planning/.active_plan`
4. the newest `.planning/<slug>/`
5. only then the root `task_plan.md`

For a slug plan it writes `.planning/<slug>/.attestation`, not the root file (see `attestation_path_for`).

This repo already has a `.planning/` directory with two slug folders. It works today only because both hold `task_plan.archived.md`, not `task_plan.md`. I ran `mise run plan-attest -- --show`, and it currently resolves to `./task_plan.md` and `./.plan-attestation`.

How it breaks: suppose `PLAN_ID` is set, or a codex lane writes `.planning/.active_plan` (the 2026-09-22c wrong-plan incident), or a new slug plan exists. Then:
- `plan-attest` attests the slug plan, while `handoff-check` keeps reading a stale or missing root `.plan-attestation`.
- `handoff-check` then reports `unattested_plan` on every run. The session-handoff skill's §5 loop ("fix and restart at step 1 → run `plan-attest`") can never converge, so `Run /session-resume` is never printed.
- It can also go the other way: the gate checks the root plan while the plugin's hook is actually injecting a different one.

Suggested fix: resolve the attestation path the way the plugin does — call its resolver or parse `plan-attest --show` output — or fail with a clear message when slug mode is active.

**Checked and fine:**
- No `plan-pointer` / `plan_pointer` references remain outside the append-only `docs/agents/goal-history.md`.
- The `main.py` registration and dispatch are both removed.
- The `suites.toml` contract is removed along with its target files.
- The hash comparison (stripped file content vs. `hexdigest()`) matches the lowercase `sha256sum`/`shasum` output the plugin writes.
- The `.agents` ↔ `.claude` skill differences are only the expected path rewrites.

Summary:
- `python/src/dotfiles_setup/handoff_check.py:42` — the attestation path is hard-coded to the root `.plan-attestation`, but `plan-attest` writes `.planning/<slug>/.attestation` whenever `PLAN_ID`, `.active_plan` or a slug plan is active. `handoff-check` then reports `unattested_plan` indefinitely (or checks the wrong plan), and the session-handoff §5 loop never ends.

## GitHub repos touched

_None._
