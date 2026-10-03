# Cold review: c6b8e825..227501e2 (fix/host-load)

- Base: `c6b8e82557636c4b3b2f39dcc7f80946ca97a2ac`
- Head: `227501e2217e0c8272e6a12d12991d1222e782163`
- Commits: a742d339, c224659a, 227501e2
- Reviewer: cold-reviewer (Opus). Diff-only, static reading plus a few tiny
  shell probes. I did not run pytest, lint, verify, gate or ship, in line with
  the caller's one-heavy-run-at-a-time rule.
- Memory: `.claude/agent-memory-local/cold-reviewer/` was empty at start (first run).
- Round: OPEN HUNTING (round 1). It cannot end the loop by any outcome; it
  promotes to one bounded round.

## Status

COMPLETE for round 1. Line numbers are at `227501e2`.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| 1 | MEDIUM | REGRESSION: guard bypass and code execution from the session cwd. The fast path runs `"$VENV/bin/python" -m dotfiles_setup.hook_dispatch`, and `-m` puts the cwd at `sys.path[0]`. A module-named file in the cwd (for example `json.py`) is imported on every tool call. The `uv run … python -m` fallback is also `-m`, so it shadows the same way. The wrapper then records `guard-error-rc=N` and ALLOWS a call the guard would deny. The old console-script entry (`dotfiles-setup hook pretooluse`) was immune. Fix: `python -P -m …` (or `PYTHONSAFEPATH=1`) on both lines. | scripts/pretooluse-guard.sh:33, :38 | Probe 1: the real wrapper run from a cwd with a planted `json.py` gives rc=0, 0 stdout bytes, the planted file executed 2×, and fail-open `guard-error-rc=7`. Control (clean sibling dir): deny=1, no fail-open log. Old entry point from the same shadow dir: deny=1, 0 executions. `-P` arm: deny=1, 0 executions. |
| 2 | MEDIUM | `pre_push_runs_suite` says "Any doubt answers False", but it misses two live off-switches. (a) hk's user rc (`~/.config/hk/config.pkl` / `.hkrc.pkl` `skip_steps` / `skip_hooks`), which hk unions with env and git config. (b) `HK=0`, which the INSTALLED global hook checks before it ever runs hk. In either case ship drops its own pytest gate, the push runs no suite, and ship opens the PR and arms auto-merge without any local suite. So the answer to "can ship push with NO suite run" is yes. CI `contract-preflight` still runs pytest before `ci-gate`, so this is a lost local gate, not an untested merge. Latent today: no hk rc exists on this host. | python/src/dotfiles_setup/pr.py:324-355 (switch lists at :327-328) | hk docs `docs/research/mintlify-cache/jdx/hk/llms-full.txt:2113-2124` (precedence 6 "User rc (hkrc)", list settings unioned), `:2436-2458` ("All skip sources (env var, git config, user config) are unioned"). Host `git config --global --get hook.hk-pre-push.command` returns `test "${HK:-1}" = "0" \|\| ~/.local/bin/mise x hk -- hk run pre-push --from-hook`. CI backstop: `.github/workflows/ci.yml:245` (in `contract-preflight`, which `ci-gate` needs at :359). |
| 3 | MEDIUM | `pytest.ini` addopts now force `-n auto --dist loadgroup` on every invocation, including the PAID `mise run codex-lane-e2e`. Its module-scoped fixtures exist to share ONE paid launch (`launched`, 4 tests) and ONE pair of paid calls (`rework_loop`, 2 tests). Nothing carries `xdist_group`, so LoadGroup makes each test its own work unit. The 4 workers start on 4 different tests, and each worker re-runs the module fixture. Result: ≥3 launches instead of 1, and up to 8 paid calls instead of 3. Fix: `pytestmark = [codex_exec, pytest.mark.xdist_group("codex-e2e")]`, or `-n 0` in that task. `smoke-exec` likewise now runs 4 Rosetta `docker run`s at once, outside the heavy-gate lock. | pytest.ini:22; tests/test_codex_lane_e2e.py:55, :97-113, :253-275; mise.toml:748 | `git grep xdist_group -- tests/` = 0. xdist 3.8.0 `scheduler/loadgroup.py:55-59` (an ungrouped nodeid is its own scope) and `scheduler/loadscope.py:384-398` (one unit per node initially). The fixture docstrings say "paying twice for it contradicts this file's own stated reason". UNVERIFIED by execution (costs credits). |
| 4 | LOW | The new default `-n auto` has never been run as a whole suite. The receipt says "Suite serial vs parallel: PENDING the host SLOT". It nevertheless ships as the default for every pre-push, CI (`ci.yml:245`) and `refresh.yml` pytest run. | pytest.ini:22; docs/research/kb/reports/agents/host-load-implementation-2026-10-02.md ("Suite serial vs parallel: PENDING") | Receipt text. UNVERIFIED here (heavy run not permitted). |
| 5 | LOW | Q-CLAIM: "never silently and never forever" does not hold. `DOTFILES_HEAVY_GATE_WAIT=nan` / `inf`, or `heavy-gate run --wait nan` / `inf`, parses as a float. With NaN both `budget <= 0` and `now - started >= budget` are False, and inf never expires, so `_wait_for` polls forever. There is no `math.isfinite` check. | python/src/dotfiles_setup/host_lock.py:93-99, :186-204, :231 | Static: IEEE NaN comparisons are always False. |
| 6 | LOW | The lock does not outlive its wrapper. `heavy-gate run` uses `subprocess.run`, whose `close_fds=True` default means the child does not inherit the flock fd. A SIGTERM or SIGKILL of the wrapper (a hook or tool timeout) drops the lock while the orphaned pytest keeps running, so a second suite can start. That is the "orphaned past the cap" class the review measured. `gate_result._run_declared` has the same shape. | python/src/dotfiles_setup/host_lock.py:245-246; python/src/dotfiles_setup/gate_result.py:187 | Static: flock belongs to the open file description, and Python's default SIGTERM disposition does not kill the child. UNVERIFIED whether Claude Code or hk kill the process group or only the direct child. |
| 7 | LOW | Ship holds the host-wide lock across its whole matrix, including `eval` and the conditional `sync-full` gate (`mise run sync -- --full`, minutes to hours on a base pull). Every other clone's lint/pytest/verify/pre-push queues behind it and fails `TIMED_OUT`/rc 124 after 3600 s. Separately, `run_gate`'s lock wait ignores `timeout_s`, so a gate can block for WAIT + timeout. A waiter killed by the 10-minute Bash cap writes no result, and `gate read` then serves the PREVIOUS run's typed result. | python/src/dotfiles_setup/pr.py:669-676, :407, :420-421; python/src/dotfiles_setup/gate_result.py:161-176 | Static: the `with host_lock.held(...)` wraps `run_gates(...)`, whose matrix ends with `sync-full`. `read_result` (gate_result.py) reads whatever file exists. |
| 8 | LOW | Q-CLAIM: `graphify_hook.nudge` says "Never raises for a graphify failure", but it catches only `OSError` and `TimeoutExpired`. A `UnicodeDecodeError` from the `text=True` decode propagates. The deleted wrapper's `\|\| true` used to absorb that (the old docstring said so). It now fails `hook_dispatch` (the guard had already ALLOWED), is logged as a GUARD error `guard-error-rc=1`, and costs a second full `uv run` attempt. | python/src/dotfiles_setup/graphify_hook.py:64, :129, :157-162; python/src/dotfiles_setup/hook_dispatch.py:55-58 | Removed graphify.py docstring: "It does NOT catch every exception (e.g. a UnicodeDecodeError …) The caller … wraps this call in a bash \|\| true". |
| 9 | LOW | The selfcheck's new arm, "a graphify-only tool must never deny", can only pass. Its Grep payload is `{"pattern":"x"}` with no `command`. Even if Grep were routed into the Bash guard, `decide("")` returns None and no deny appears. The unit test arms this correctly (`command=_DENIED`); the shipped `hook selfcheck` gate does not. | python/src/dotfiles_setup/hook_selfcheck.py:376-386 | Compare tests/test_hook_dispatch.py:71-78. `hook_guard.decide_payload` treats an unknown tool as Bash: `decide(str(tool_input.get("command","")))`. |
| 10 | LOW | Doc and contract drift. The eager rule `clarify-before-acting.md` still states a five-tool PreToolUse matcher, and suites.toml REQUIRES that stale string in the rule doc. The `hook_guard.py` module docstring and `scripts/web-setup.sh` still name `dotfiles-setup hook pretooluse` as the wired hook. suites.toml's `workflow.mise-tasks-enforcement` global token is satisfied by that stale docstring. `TEST-INDEX.md` rows still describe "the SessionEnd command-audit hook" and "all five guarded tools", and the rules-evidence file still says "five-tool". The pr.py module docstring still says ship runs "lint → pytest → verify". | .claude/rules/clarify-before-acting.md:65, :78; python/verification/suites.toml:1324, :1346; python/src/dotfiles_setup/hook_guard.py:4; scripts/web-setup.sh:7; tests/TEST-INDEX.md:55, :57; docs/rules-evidence/mise-tasks-only.md:126; python/src/dotfiles_setup/pr.py:53, :69 | `git grep` at 227501e2. The settings.json matcher is now `Bash\|AskUserQuestion\|Edit\|Write\|NotebookEdit\|Grep\|Read\|Glob`. |
| 11 | LOW | Q-CLAIM: "serialises every heavy run across every clone/worktree" / "one CPU budget" overstates the scope. A devcontainer suite resolves the lock under the container's own home volume (the host state dir is mounted at `/tmp/dotfiles-host-state`, not at `$XDG_STATE_HOME/dotfiles`). Container runs therefore never queue against host runs, even though both share the CPU through the Docker Desktop VM. | python/src/dotfiles_setup/host_lock.py:4-15, :75-80; .devcontainer/devcontainer.json:132 | Static. |
| 12 | LOW | The new real-uv fallback test builds and syncs a complete second project venv under `tmp_path` on EVERY suite run, including every pre-push: 184 locked packages, and the dev venv is 1.0 GB. That is added load in a change meant to cut load. | tests/test_hook_dispatch.py:132-140 | `UV_PROJECT_ENVIRONMENT=tmp_path/no-venv` plus `uv run --project`. `grep -c '^\[\[package\]\]' python/uv.lock` = 184; `du -sh python/.venv` = 1.0G. |
| 13 | LOW | The cheap `uv python find '>=3.14'` fail-open was removed. Its purpose was the cold Claude-web "web brick" window. With uv present but Python 3.14 absent, each tool call now enters `uv run`, which may download Python and sync 184 packages inside the 20 s hook timeout. A timeout-killed hook allows the call but never reaches `fail_open`, so these fail-opens go UNRECORDED (#343). suites.toml still describes the removed check. | scripts/pretooluse-guard.sh:37-39; python/verification/suites.toml (mise-tasks-enforcement description "fail open when the Python>=3.14 interpreter is absent") | Base-side wrapper text in the diff (`uv python find '>=3.14' … fail_open "interpreter-absent"`). UNVERIFIED: no web environment to probe. |
| 14 | LOW | The KB handoff misstates the hazard it warns about. It says per-gate locking from threads "would deadlock". Under the re-entry contract it hands over, a second thread in the same process finds a busy lock, its recorded pid equal to the process-global export, and RE-ENTERS. Then the first thread's exit pops the export and `LOCK_UN`s while the second is still running. The real hazard is an early release, not a deadlock. | docs/handoffs/kb-host-load-followup-2026-10-02.md:31-35; python/src/dotfiles_setup/host_lock.py:159-181 | Static: `os.environ` is process-wide, and `held()` restores and unlocks in `finally`. |

## Probes run (all tiny, none heavy)

1. **cwd shadowing (finding 1).** I planted a `json.py` (it appends to a marker,
   then exits 7) in a fresh temp dir. I then drove the REAL wrapper,
   `CLAUDE_PROJECT_DIR=<repo> /bin/bash scripts/pretooluse-guard.sh`, with
   payload `{"tool_name":"Bash","tool_input":{"command":"gh pr create --fill"}}`.
   - Shadow arm: rc=0, stdout 0 bytes, shadow_execs=2, fail-open `guard-error-rc=7`.
   - Control (sibling dir without `json.py`): rc=0, deny=1, no fail-open log.
   - Old entry (`uv run --project python dotfiles-setup hook pretooluse`) from
     the shadow dir: deny=1, shadow_execs=0. The `-m` change caused the
     regression.
   - Fix arm (`python -P -m …`): deny=1, no marker.
2. **bash 3.2 `read -r -d ''` (pretooluse-guard.sh:31).** Correct.
   - Empty stdin leaves `payload=""` set, so `set -u` does not fire (control:
     an unset var gives rc=127).
   - Trailing newlines are preserved.
   - Cost on a pipe is about 0.5 s per MB (two reads each: 100 KB 0.29 s,
     1 MB 1.09 s). That matters only for very large Write payloads.
3. **graphify 0.9.73.** Two checks, both clean, so the search skip is sound
   for the locked version and the real-binary test pins it.
   - `_run_hook_guard` search stays nudge-only "even in strict mode".
   - `hook-guard` is in `_silent_cmds` (`graphify/__main__.py:721`), so the
     real-binary test never triggers the HOME skill auto-refresh that
     do-not.md #8 forbids.
4. **hk user rc / global hook.** No `~/.config/hk/` and no `.hkrc.pkl` exist
   (finding 2 is latent). The global `hook.hk-pre-push.command` reads `HK`.

## Checked and found sound (not findings)

- **Re-entry env chain ship → push → pre-push (no deadlock found).** The chain
  holds by static reading but is not proven end to end:
  - `run_with_fnox` builds env from `os.environ` AFTER `held()` exported the
    holder pid (process_env.py:43-62).
  - `fnox exec`, git, the global hk hook (`mise x hk -- hk run pre-push`), hk,
    `mise --cd … run`, and `uv run` all inherit the environment.
  - `test-hook-isolated` takes `heavy-gate run` (mise.toml:297), which
    re-enters.
  - No link scrubs `DOTFILES_LOCK_HOLDER_*`; `git-isolated` runs after the
    lock decision.
  - **UNVERIFIED end-to-end:** only a direct child is tested
    (test_host_lock.py:122-134). If any link ever drops the variable, ship
    waits 3600 s and the push fails with rc 124. A deadlock in that sense is
    bounded, not infinite.
- **No-file pre-push.** hk docs say "If [glob is] unset, the step always runs"
  (llms-full.txt:2790). git runs pre-push even when everything is up to date.
  So docs-only and no-op pushes still run the suite.
- **truncate-after-acquire.** In `a+` mode, `seek(0)` + `truncate()` truncates
  at 0, and the O_APPEND write lands at offset 0. Waiters never truncate.
- **Stale record.** The record is never cleared on release, but re-entry needs
  the lock to be BUSY and the record pid to match the inherited value. That
  only goes wrong under pid reuse plus a stale export. Negligible.
- **In-process nesting.** A second `open()` + `flock` in the same process is a
  new OFD, so LOCK_NB fails. The record pid equals the exported pid, so the
  call re-enters, which is the intended behaviour.
- **`isolated_host_locks` under xdist.** It uses per-test `tmp_path` siblings,
  which are unique within each worker's basetemp. The inherited
  `DOTFILES_LOCK_HOLDER_*` vars are deleted. `isolated_mise_state` and
  `GIT_CONFIG_GLOBAL` isolation also hold per test.
- **`pytest_xdist_auto_num_workers`.** `tests/conftest.py` is an initial
  conftest for `pytest tests/…`. The hook is firstresult; returning None defers
  to xdist's own reading of `PYTEST_XDIST_AUTO_NUM_WORKERS`.
- **`heavy-gate` argparse.** It uses REMAINDER through both parsers. A leading
  `--` survives REMAINDER and is stripped explicitly (host_lock.py:240).
- **command-audit single instance.** `wait_s=0` raises `HostLockTimeoutError`
  before the scan, which prints "skipped" and returns rc 0.

## Q-FRESH / Q-SCOPE / Q-CLAIM

- **Q-FRESH.**
  - `suite_at_push` is decided (pr.py:662) before ship waits up to 3600 s for
    the lock (:669), and it is not re-read before the push. LOW, not tabled.
  - The graphify `was_seen` skip reads a marker that is only ever added. Fine.
  - `run_gate` writes no "started" result, so a reader during the wait sees
    the previous run's result (finding 7).
- **Q-SCOPE.** Findings 1, 2, 3, 5, 6, 7, 8, 9, 12 and 13 are in scope for
  host-load. Recommended as tickets: 4 (run the parallel suite once, in the
  slot), 10 (doc/contract sync), 11 (container lock scope), 14 (KB handoff
  wording).
  - Sibling ticket: hook_guard denies `HK_SKIP_HOOKS=` prefixes but has no
    rule for `HK=0`, the global hook's own off-switch (`git grep 'HK=0' --
    python/src` = 0 hits).
  - UNVERIFIED sibling: graphify's source says "Codex Desktop rejects
    hookSpecificOutput.additionalContext on PreToolUse". `.codex/hooks.json`
    now emits that nudge from the SAME entry as the guard, where the two used
    to be separate entries. Not probed.
- **Q-CLAIM (operator-facing strings added or changed):**
  - "pytest runs ONCE, in the hk pre-push hook … ship stops before the PR"
    (pr.py:665-667): enforced by pr.py:677-686, except under finding 2.
  - "never silently and never forever" (host_lock.py:19-22): see finding 5.
  - "A stale export cannot unlock anything" (host_lock.py:27-28): holds,
    except under pid reuse.
  - "command-audit: skipped — …" (command_audit.py:800-802): enforced by
    `wait_s=0`.
  - "Never raises for a graphify failure" (graphify_hook.py:129): see
    finding 8.
  - `FAIL  ship: git push rc=… (the pre-push hook runs the test suite; a
    failing test lands here)` (pr.py:681-685): true only when `suite_at_push`
    and the hook is not off-switched (finding 2).

## GitHub repos touched

_None._ I read only the local repo, the locked `graphifyy` 0.9.73 and
`pytest-xdist` 3.8.0 in `python/.venv`, and the local hk mintlify cache
(`docs/research/mintlify-cache/jdx/hk/`).
