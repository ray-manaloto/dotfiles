# Premise verify — land-smoke round 2 spec (premise-verifier, verbatim)

PREMISE REPORT: spec `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/land-smoke-timeout/docs/specs/land-smoke-timeout-round2-2026-10-04.md`. This lane is read-only and wrote no files; persisting this report is the caller's job.

ROWS: 8 checked: 4 CONFIRMED (0 provenance corrected) / 0 REFUTED / 2 UNVERIFIABLE / 1 ASSUMED (0 checkable). (P2 and P3 are CONFIRMED with line-range drift. The tally sums to 7 because P5 is counted under UNVERIFIABLE and also as provenance-mismatched. Treat P5 as UNVERIFIABLE.)

- **P1: CONFIRMED.** `_SMOKE_TIMEOUT_S = 1800.0` at worktree `python/src/dotfiles_setup/container.py:52`.
- **P2: CONFIRMED (citation drift: cited 126-140, actual 127-141).**
  - `host_lock.held(host_lock.HEAVY_GATE, f"container smoke {container_id}") as fd` is at `container.py:127-129`.
  - `_run(["docker","exec","--workdir",workspace_dest,container_id,"scripts/devcontainer-smoke.sh"], timeout=timeout, pass_fds=() if fd is None else (fd,))` is at `:130-141`.
- **P3: CONFIRMED (drift: cited 141-155, actual 142-156).** At `:145-149` the code joins `(exc.stdout, exc.stderr)` stdout first, takes the last 3 lines and caps at 2000 characters. The prefix `smoke timed out after {exc.timeout:g} seconds:` is at `:153`.
- **P4: CONFIRMED.** `monkeypatch.setenv("DOTFILES_SMOKE_TIMEOUT_S", "0.1")` at `tests/test_container.py:290`.
- **P5: UNVERIFIABLE.**
  - Provenance: the source is a past `docker exec … ps` observation, not a code location. Those processes were killed, so the condition has passed and no probe can re-read it now.
  - What I could read: `/Users/rmanaloto/.claude/jobs/a90e493a/tmp/land-1666.log:61` shows `subprocess.TimeoutExpired: Command '['docker', 'exec', '--workdir', '/workspaces/dotfiles', '0eed9addeee6', 'scripts/devcontainer-smoke.sh']' timed out after 1800.0 seconds`. That confirms the timeout half. The process tree is not settleable.
  - Non-blocking: it is motivating narrative, not something the change's correctness depends on.
- **P6: UNVERIFIABLE (provenance: a cold-review report plus an external issue I cannot read here).** The cold review cites moby/moby#9098 as OPEN (`docs/research/kb/reports/agents/cold-review-land-smoke-c14af317.md:15`).
  - Non-blocking: the incident's surviving orphans in the objective are the field evidence, and the fix (an in-container self-terminating wrapper) is correct either way.
- **P7: ASSUMED, with concrete risk.**
  - The base is `ubuntu:26.04@sha256:2260313b…` (`.devcontainer/Dockerfile:14`).
  - From my knowledge, not a code read: Ubuntu 25.10 and later ship rust-coreutils (uutils) as the default `coreutils`. On 26.04, `timeout` may therefore not be GNU, and its process-group and `--kill-after` behaviour is unproven.
  - No `procps` or `coreutils` declaration exists anywhere in `.devcontainer/`. The grep for `procps|coreutils|setsid|util-linux` returned 0. Control arm: `curl|packages` in the same tree hits 7 files.
  - Non-blocking only because §3 already requires the in-image check and the `setsid` fallback. The row should say "`timeout` (GNU or uutils — record which from `timeout --version`)".
- **P8: CONFIRMED.**
  - Main `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/container.py:108-126`: `_run_smoke` calls `_run([...], timeout=_SMOKE_TIMEOUT_S)` with no `host_lock`.
  - Main has no `host_lock` import (`:31-40`), and `_run` has no `pass_fds` (`:61-66`).
  - The `main` branch HEAD is 64c6aae8 per git status.
  - The incident log's raw `TimeoutExpired` traceback matches main's untyped path.

MISSING:

- **M1 (load-bearing): no mapping from the inner timeout's exit code.**
  - When GNU or uutils `timeout` fires, it exits 124, or 137 after `--kill-after`. The `docker exec` CLI then returns that code normally. No `TimeoutExpired` is raised.
  - That result falls into the non-timeout branch at `container.py:159-166`, which appends ``— stale base? `mise run dev-rebuild` ``. That is exactly the misdirection round 1 removed (rule `:100-102`).
  - The spec must say that rc 124/137 from the wrapper produces the `smoke timed out after <T> seconds:` detail with no rebuild hint, and whether a reap or probe runs on that path too.
- **M2 (load-bearing): F3, "keep the `_run_smoke` signature" and F8 are mutually constraining, and the spec does not say how to reconcile them.**
  - The id, mount destination and HEAD are resolved in `verify_latest` (`container.py:175-210`). `_run_smoke(container_id, workspace_dest)` takes no `workspace`, so it cannot re-resolve them without a signature change.
  - The only signature-preserving route is to take the slot in `verify_latest`. Then the inner `held()` in `_run_smoke` re-enters the same process: `_try_lock` fails on the new open file description, then holder-env == own pid == record pid, so it yields `None` (`host_lock.py:171-179`, `:186-187`).
  - With `None`, `pass_fds` becomes `()`. The outer fd is not reachable from `_run_smoke` without a new parameter or module state.
  - The spec must pin one of:
    - (a) the slot moves to `verify_latest` and the fd is threaded through, which changes the signature or adds a keyword argument;
    - (b) re-resolve inside `_run_smoke`, which needs `workspace`;
    - (c) accept a signature change.
  - It must also say what the F8 "drop pass_fds" mutation means under the chosen design.
  - Also pin that the slot is taken only when `run_smoke=True`.
- **M3 (load-bearing if the script is touched): `scripts/devcontainer-smoke.sh` has zero bash-budget headroom.**
  - It is 166 lines against `max_lines` 166 (`python/src/dotfiles_setup/bash_budget.py:92-97`).
  - Any line added to the script fails `bash_logic_budget`, and bumping the budget means editing `bash_budget.py`, which is NOT in the allowlist.
  - Either add `bash_budget.py` to the allowlist with an explicit bump rule, or state that the script must not grow and the wrapper belongs in the Python argv.
- **M4: reap identity versus "never kill a process you did not start".**
  - The reap is defined as killing "processes whose command line is the smoke script or its descendants". That cannot tell this run's smoke from a lifecycle `postCreate` smoke or a `mise run smoke` that started during the run. Both take no slot (cold review F6, `cold-review…md:19`).
  - The spec should pin an identity marker for this run's smoke: a unique env token or argv nonce, a recorded pid from the wrapper, or a pgid. Without one, the two constraints conflict.
- **M5: reap runs after the slot is released.**
  - The `except subprocess.TimeoutExpired` clause sits outside the `with host_lock.held(...)` block (`container.py:127-156`). As written, the slot is dropped before the reap and re-probe.
  - The spec should say whether the reap must run under the slot. If it does not, a waiting heavy gate starts while orphans still run, which is the F2 symptom again.
- **M6: the probe tool's presence in the image is unpinned.**
  - Neither `ps` nor `pgrep` (procps) is declared in `.devcontainer/` (grep for `procps|pgrep|\bps\b` hit only a comment at `devcontainer.json:124`).
  - Pin the probe mechanism (`ps`, `pgrep` or a `/proc` read through `python3`, and whether `python3` is in the image), or require in-image verification as for P7.
  - Also guard against the probe matching itself: a `pgrep -f devcontainer-smoke.sh` or `sh -c '…devcontainer-smoke…'` probe matches its own command line.
- **M7: the inner timeout and kill-after formula is unpinned.**
  - `DOTFILES_SMOKE_TIMEOUT_S` accepts any finite positive value (`container.py:117-123`), and tests use a few seconds.
  - The spec needs a rule that guarantees `T_inner + k < host timeout` for small values (for example a ratio, or a floor that fails closed) so the inner wrapper actually fires first in both production and tests.
- **M8: the test fixture treats every `docker exec` as the smoke (non-blocking, within the allowlist; listed so the lane plans for it).**
  - The fake `docker` handles every `exec` the same way: it writes the lock probe and sleeps 5 s in timeout mode (`tests/test_container.py:256-276`).
  - `test_smoke_invalid_timeout_uses_bounded_default` records every `docker exec` timeout and asserts `observed == [1800.0]` (`:354-363`).
  - The pre-flight probe and the reap add `docker exec` calls, so the fake must tell them apart and that assertion must be retargeted.
- **M9 (non-blocking): F5 has two possible fixes.** The cold review offers `stderr=subprocess.STDOUT` or preferring the first FAIL line (`cold-review…md:18`). The spec says "time-ordered tail, first FAIL preferred". `stderr=STDOUT` also changes the non-timeout path's `res.stderr`, which `:161` concatenates. That is harmless but should be noted.
- **Allowlist coverage:**
  - F3 does NOT need `sync.py`: `sync._verify` only calls `verify_latest` (`sync.py:841`), so the fix fits in `container.py`.
  - F9 rule rows and F7 wording are rule-file only and in scope. The rule has no `paths:` frontmatter (eager, 200-line budget) and is 147 lines now, so there is about 53 lines of headroom.
  - `rule-sync.toml:71` lists `persistence-gate-retry` by stem only (`:51-56`), so content edits do not need a matching knowledge-base change.
  - The F9 skill tables (`.claude/skills/devcontainer-sync/SKILL.md`, `.agents/skills/devcontainer-sync/SKILL.md`) are correctly out of scope and belong in a ticket.
  - The only allowlist gap is `bash_budget.py` (M3).
- **Contradictions:**
  - M2: keep the signature vs F3 vs F8 `pass_fds`.
  - M4: "never kill what you did not start" vs a reap defined by command line.
  - M1: the inner timeout's exit code vs the "no rebuild hint" invariant. This is implicit, not explicit.

VERDICT: CORRECT THE SPEC FIRST. M1 (the inner timeout's 124/137 code lands on the stale-base hint path), M2 (signature, slot and `pass_fds` cannot all hold as written) and M3 (the smoke script has 0 lines of budget, and `bash_budget.py` is outside the allowlist) are each load-bearing. M4, M5 and M7 should be pinned in the same pass.

Named non-blocking residuals:
- **P5:** narrative, and the condition has passed.
- **P6:** external issue, corroborated by the incident.
- **P7:** the spec already requires in-image verification plus the `setsid` fallback; reword "GNU".
- **M6:** in-image verification can cover it if stated.
- **M8:** a test-only change within the allowlist.
- **M9:** cosmetic.
