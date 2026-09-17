# codex SDLC team — Phase 7 IMPLEMENTATION run, ROUND 3 (final respec, 2026-09-16), verbatim

Brief: `mise run sdlc-team` implement mode, run `phase7-session-handoff-implement-r3-20260916`, effort xhigh, 3600 s, round-2 allowlist + renovate_validate/fnhook_gates/skills_mirror and their tests; spec appended below. Settlement in the architect dispositions. Output copied verbatim at receipt.

---

Round 3 is implemented but remains **partial failure / not commit-ready**. No files were staged or committed; the 13 pre-existing cached additions are unchanged.

Implemented:

- Caller-subtree exclusion in [session_orphans.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/session_orphans.py).
- Anchored task carriers and `unclosed_fence` detection in [handoff_check.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/handoff_check.py).
- Expanded wait-loop guarding in [hook_guard.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/hook_guard.py).
- AgentsView error handling, write detection, malformed-row census, masked commits, and list-side child inclusion in [agentsview_pass.py](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/agentsview_pass.py).
- Isolated mise state, exact Renovate pin resolution, distinct token-usage labels, mirror regression protection, and both N4c wiring contracts.

Final gate results:

| Gate | rc | Result |
|---|---:|---|
| Focused pytest matrix | 1 | 338 passed; mirror-drift test failed |
| `skills-mirror --check` | 1 | `SANDBOX:` generated `.agents` mirror remains drifted |
| `handoff-check` | 0 | Live handoff clean |
| `session-orphans` | 2 | `SANDBOX:` process-table access denied |
| Missing-skill AgentsView probe | 2 | Expected `UNVERIFIABLE`; no traceback |
| `mise run verify` | 0 | 159 passed, 0 failed, 4 skipped |
| `mise run lint` | 1 | Taplo sandbox panic, incomplete Renovate pin, mirror drift, Docker unavailable |
| Full pytest | 1 | 770 passed, 11 deselected; `/proc` sandbox failure |
| `git diff --check` | 0 | Clean |
| `mise run lint-docs` | 0 | Clean |

Fail-arm evidence:

- N0/N0b: rc=0, 12 passed.
- N1/N2 and related loop arms: rc=0, 22 passed.
- G2 host tracked-config isolation: rc=0; count stayed `168 → 168`.
- G1 synthetic exact-pin/shims arms: rc=0, 2 passed.
- G1 live Renovate suite: rc=1, 12 passed / 2 failed because pin `44.94.0` lacks the validator binary.
- N4c contract/token checks: rc=0, 40 passed.
- AgentsView focused suite: rc=0, 21 passed.

Open items:

1. Regenerate `.agents/skills/session-handoff/SKILL.md` outside this read-only sandbox.
2. Repair/reinstall Renovate `44.94.0`.
3. Resolve N4’s licensed dissent: `session list` supports `--include-children`, but `session tool-calls` does not.
4. Re-run session-orphans, lint, and full pytest with process-table, Docker, and Taplo access.

No other specialists were spawned.

Specialists spawned:

- sdlc-python-specialist — /root/phase7_r3_python
- sdlc-documentation-specialist — /root/phase7_r3_docs
- sdlc-config-specialist — /root/phase7_r3_config


---

## Appendix — the round-3 spec (verbatim)

# Spec — Phase 7 IMPLEMENTATION, ROUND 3 (final respec, 2026-09-16): last gate reds + round-2 cold-review closures

Repo `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`, branch `feat/phase7-session-handoff-sdlc-review`, base `3d03ea8`. Mode **IMPLEMENT**, `COMMIT: caller`, same allowlist as round 2 PLUS `python/src/dotfiles_setup/renovate_validate.py`, `python/src/dotfiles_setup/fnhook_gates.py`, `python/src/dotfiles_setup/skills_mirror.py`, `tests/test_renovate_validate.py`, `tests/test_fnhook_gates.py`, `tests/test_skills_mirror.py`, `tests/conftest.py`. Round-1 and round-2 specs still bind (`docs/research/kb/reports/agents/codex-sdlc-session-handoff-implement{,-r2}-2026-09-16.md`). Do not stage; `git add` nothing.

This is the LAST respec round (two-round bound). Anything you cannot close, report as OPEN with the reason — do not widen scope.

## 1. Gate reds measured by the architect outside the sandbox (`gates-r2/`)

G1 `mise run lint` → `renovate_config_validate`: `renovate_validate.run_validator` (`renovate_validate.py:105-113`) runs the bare `renovate-config-validator` from a temp cwd (`engine_rejects_lookahead`, `:124-127`); on a shims-only PATH the shim finds no config there → `mise ERROR No version is set for shim`. The repo already documents this exact trap for `claude` in `fnhook_gates.py:35-100` (resolve `<tool>@<pin>` from `mise.toml` and run through `mise exec <spec> --`). Fix `run_validator` the same way (pin read from `mise.toml`'s `npm:renovate`), or at minimum `cwd=repo_root` so the shim resolves the repo pin — with a test that passes a shims-only `PATH` fixture and still resolves. Verify: `mise run lint` green in a shell WITHOUT `mise activate` (e.g. `env -i HOME=$HOME PATH=$HOME/.local/share/mise/shims:/usr/bin:/bin mise run lint` — record rc).

G2 `pytest`: `tests/test_fnhook_gates.py:328` asserts `result.stderr == ""` on a child that runs `mise`; the host prints a `uv_venv_auto` deprecation from mise's tracked-config registry (other repos on this host), so the assertion is host-state-dependent. Architect-armed: `MISE_STATE_DIR=<tmp> mise config ls` → 0 WARN, control → 1. Fix at the seam, not the assertion: `fnhook_gates` builds `child_env` (`:178-181`) — give every mise-invoking gate child an isolated `MISE_STATE_DIR` under a temp dir (a module-level helper, parameter defaulting to a fresh `tempfile.mkdtemp()`, injectable in tests). This is also the class fix for the host pollution measured today (5,113 dangling tracked configs from tests). Add the control-arm test: after one gate run, the HOST `~/.local/state/mise/tracked-configs` count is unchanged.

G3 `session-agentsview-pass --skill /nonexistent/SKILL.md`: prints `AGENTSVIEW PASS — UNVERIFIABLE` and rc=2 but `main` uses `logger.exception` (`agentsview_pass.py:343`) so a 22-line traceback follows. Use `logger.error("AGENTSVIEW PASS — UNVERIFIABLE — %s", exc)`; test asserts no `Traceback` in stderr.

## 2. Round-2 cold review (`docs/research/kb/reports/agents/cold-review-phase7-r2-2026-09-16.md`) — architect-refuted; implement each

N0 HIGH `session_orphans.py` — `reap.snapshot`'s own `ps` (a child of the running python) is classified `BLOCK OTHER` every run, so the task can never exit 0. Exclude the caller's whole subtree (self + its descendants) from the candidate set, not only its ancestor chain. Test: a fixture table with a `ps` child of the caller pid → not in the plan; a wait loop elsewhere under the root → still in the plan.

N0b HIGH `handoff_check.py:35-36` — `_TASK_CARRIER_HEADING` fires on any heading MENTIONING "next task" (`## Where the next task lives` is a pointer, not a carrier; 48 findings over 69 historical handoffs, 6 of them mentions). Anchor: a heading is a carrier only when its text STARTS with `next task`/`next-task`/`NEXT TASK` (optionally after `#`s, emoji/punctuation, and a colon after), and a line is a carrier only when it starts with `NEXT:`/`NEXT TASK:`/`Next task:`. `## Where the next task lives` and `## What the audit says beyond the next task` → clean; `## Next task`, `## NEXT TASK — do X`, `NEXT: ship it` → `forbidden_task_carrier`. Move the positive control off the live handoff onto a fixture; `mise run handoff-check` on `.agent/plans/session-2026-09-16c.md` must then be rc=0. Also close the unclosed-fence blindness: an unclosed fence emits `unclosed_fence` (new verdict) rather than silently exempting the rest of the file.

N0c HIGH `skills_mirror.py` `PER_FILE["session-handoff"]` — the generic Claude→Codex rule rewrote "two prior Claude sessions" to "Codex" in `.agents/skills/session-handoff/SKILL.md:127`, while `agentsview_pass` hard-codes `--agent claude`. Add the reversion pair (with the one-line reason), regenerate the mirror, `--check` rc=0.

N1+N2 MEDIUM `hook_guard.py:172-204` — the condition allow-list misses `while true`/`while :`/`until false`/`while [ 1 ]` and `until <any-cmd>`. Redefine the WAIT condition as: a negated command, a file test (`-f/-e/-s/-d/-r`), a constant-true/false, OR any command invocation — EXCEPT an arithmetic/string comparison (`[ $x -lt … ]`, `[ "$a" = … ]`, `(( … ))`, `[[ … ]]` without a file test) and `read`. Keep every round-2 non-fire case green (counter loop, `while read`, `"$SLEEP"`, `timeout N sh -c`, commit-message quote, `for` loops) and add the six N1/N2 rows as fire tests.

N3 MEDIUM `agentsview_pass.py:220-224` — count a step-3c write for `Write`/`Edit`/`MultiEdit`/`NotebookEdit` whose path is under `docs/research/kb/reports/agents/`, AND for a `Bash` call whose command redirects/`tee`s/heredocs into that directory. Test both.

N4 MEDIUM `agentsview_pass.py:292-308` — pass `--include-children` to `session list` and `tool-calls` so delegate sessions are censused under their parent (aggregate child rows into the parent's block, labelled `(+N children)`); document in the skill that the census is coordinator+children.

N4b MEDIUM `hook_guard.py:178-181` — the `SECONDS` exemption is case-folded; require the exact `SECONDS` (case-sensitive) — a lowercase `seconds` in the predicate must not exempt. Keep `$deadline`/`$DEADLINE`/`$end`/`$END`.

N4c MEDIUM `suites.toml` — add wiring contracts for `plan-pointer` and `session-agentsview-pass` shaped like `workflow.bounded-wait-wiring` (task ↔ main.py dispatch ↔ module `def main(` ↔ test file ↔ the skill line naming the task); every token unique (`contract_token_uniqueness`).

N4d MEDIUM `session_ledger.py:2594-2596` — census `token_usage` and `token_usage_record` under their own labels.

N5 LOW `agentsview_pass.py:177-192` — a row with null/unparseable `input_json` is counted (`unparseable rows : k`) and skipped, not fatal; the block prints the count.

N6+N7 LOW `hook_guard.py:161-167,185` — allow `$(`/backtick substitution anywhere as a loop prefix, and match a path-qualified or parenthesised `sleep` (`/bin/sleep`, `(sleep 5)`) in the body.

N8 LOW `agentsview_pass.py:25,210-213` — run `_GIT_COMMIT` on the same masked view as the wait check.

Rulings, no change: L3 (pointer unverifiable from a clone — accepted by Ray), L5, L8, M10a (documented), N9/N10 (pre-existing `_WRAPPER` ReDoS and leading-whitespace hole → filed as a separate issue by the architect, do not touch `_CMD`/`_WRAPPER`).

## 3. Verification (config specialist; real rc; `SANDBOX:` when blocked)
```
uv run --project python pytest tests/test_hook_guard.py tests/test_handoff_check.py tests/test_session_orphans.py tests/test_agentsview_pass.py tests/test_skills_mirror.py tests/test_renovate_validate.py tests/test_fnhook_gates.py tests/test_session_ledger.py -x -q
uv run --project python dotfiles-setup skills-mirror --check
uv run --project python dotfiles-setup handoff-check            # rc=0 on the live newest handoff now
uv run --project python dotfiles-setup session-orphans           # dry run; the plan must not list the task's own ps
uv run --project python dotfiles-setup session-agentsview-pass --skill /nonexistent/SKILL.md   # rc=2, UNVERIFIABLE, no Traceback
mise run verify
mise run lint
uv run --project python pytest tests/ -x -q
```
Fail arms to show: N0b both directions; N0 fixture; N1/N2 six fire rows + the round-2 ten non-fire rows; G2 host tracked-config count unchanged after a gate run.

## 4. Commit
COMMIT: caller. Leave the tree uncommitted and unstaged.

## 5. PREMISES (fresh this session)
- L `run_validator` argv and temp cwd — `renovate_validate.py:105-127`; precedent `fnhook_gates.py:35-100,178-181`.
- L `tests/test_fnhook_gates.py:310-328` (`assert result.stderr == ""`), test added in #1038 (`34788a6`).
- L `MISE_STATE_DIR=<tmp>` → 0 mise WARN lines, control 1 — measured 2026-09-16.
- L `agentsview_pass.py:343` `logger.exception`; `:83-86` OSError conversion (round 2).
- L `session_orphans.py:63-66` own-chain protection is ancestors-only; the `ps` child pid differs per run (46921/47389/47419, cold review r2).
- L `handoff_check.py:35-36` `_TASK_CARRIER_HEADING`/`_TASK_CARRIER_LINE`; corpus sweep 48/69 (cold review r2 N0b).
- L `.agents/skills/session-handoff/SKILL.md:127` "two prior Codex sessions" (generated); `agentsview_pass` `--agent claude`.
- L `hook_guard.py:172-204` `_COMMAND_WAIT` allow-list; `:178-181` `_CONDITION_BOUND`; `:185` `_SLEEP_COMMAND`; `:161-167` prefix.
- L `suites.toml:1491-1548` bounded-wait/session-orphans wiring contracts; `grep plan-pointer suites.toml` → 0.
- L `session_ledger.py:2594-2596` single `token_usage` label.
- A `mise exec npm:renovate@<pin> -- renovate-config-validator` resolves without an activated shell (same mechanism `fnhook_gates` relies on in CI).
