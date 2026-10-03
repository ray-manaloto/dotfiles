# Cold review round 2: 227501e2..a8f606bb (fix/host-load)

- Base (round-1 head): `227501e217e0c8272e6a12d12991d1222e782163`
- Head: `a8f606bb824d392058b1c4e1600f89c9032e8f17`. The worktree HEAD equals this, and the tree is clean apart from this report.
- Commits: 6d588856, a8f606bb
- Round 1 report: `docs/research/kb/reports/agents/host-load-cold-review-2026-10-02.md`
- Reviewer: cold-reviewer (Opus).
  - Read-only and host-quiet: static reading plus sub-second shell probes.
  - Not run: pytest, lint, verify, gate, ship, push, or any GitHub write.
- Memory: consulted `.claude/agent-memory-local/cold-reviewer/`, which held one entry from round 1.
- Round: BOUNDED.
  - The domain is 13 items: round-1 findings 1, 2, 3, 5, 6, 7, 8, 9, 10, 12, 13, 14, plus Q-FRESH.
  - Each item gets FIXED, NOT FIXED or REGRESSED.
  - New defects are limited to lines that the fix diff added or changed.

## Status

COMPLETE. Line numbers are at `a8f606bb`.

## Verdicts

| Item | Verdict | Evidence (file:line at a8f606bb) |
|---|---|---|
| 1 (MEDIUM, cwd shadowing via `-m`) | **FIXED** | Both interpreter lines now run `python -P -m`: `scripts/pretooluse-guard.sh:35` and `:40`. suites.toml tokens pin both lines (`python/verification/suites.toml:1344`). New test: `tests/test_hook_dispatch.py:173-188`. It cannot pass vacuously: `git grep PYTHONSAFEPATH` finds no config that sets it. Live probe P1, both arms. |
| 2 (MEDIUM, missed hk off-switches) | **FIXED** for the two switches round 1 named. Residual: N2. | `HK=0` is checked at `python/src/dotfiles_setup/pr.py:360`. hkrc skip lists are checked at `pr.py:330-344` and called at `:362`. The key names and the three paths match the hk docs (`docs/research/mintlify-cache/jdx/hk/llms-full.txt:2051-2053`, `:2445`, `:2458`). Tests: `tests/test_pr.py:138-155`, with the HK=1 control at `:145-146`. |
| 3 (MEDIUM, xdist re-runs paid module fixtures) | **FIXED** | Each exec module is pinned to one worker: `tests/test_codex_lane_e2e.py:59` and `tests/test_image_smoke_exec.py:49`. The installed xdist reads the mark via `iter_markers("xdist_group")` (`xdist/remote.py:245-251`), and loadgroup routes `nodeid@group` as one scope (`scheduler/loadgroup.py:55-59`). These are the only `codex_exec`/`image_exec` modules. They also hold the only exec-test module fixtures (`test_codex_lane_e2e.py:101`, `:257`; `test_image_smoke_exec.py:92`). |
| 5 (LOW, NaN/inf wait unbounded) | **FIXED** | `host_lock.py:102-106` covers the env value. `:164-165` covers `held()`, which handles both the CLI `--wait` and `run_gate`'s `wait_s`. Test: `tests/test_host_lock.py:171-176`. Nit: `-inf` now means "wait 3600 s" while `-1` means "do not wait" (`_wait_for` `budget <= 0`). The result is bounded, so this is not a defect. |
| 6 (LOW, lock dies with the wrapper) | **FIXED** at both call sites round 1 named. | `held()` yields the fd (`host_lock.py:189`). `heavy-gate run` passes it on (`host_lock.py:259-261`), and so does `gate_result._run_declared` (`gate_result.py:206`). Live probe P2, both arms. The `gate run` half has no test arm (N4). Residual (LOW, same class, outside round 1's two sites): ship's own lock (`pr.py:682`) is never passed to its children. If ship is SIGKILLed during `git push`, the pre-push suite re-enters with no fd of its own (`yield None`, `host_lock.py:178`) and keeps running unlocked. |
| 7 (LOW, lock scope / wait bound / stale result) | **NOT FIXED** (two of three parts fixed) | (b) FIXED: the lock wait is bounded by `timeout_s` (`gate_result.py:168-170`), and suites.toml pins it (`:3118`). The worst case is now 2×timeout. (c) FIXED: the previous result is deleted before the wait (`gate_result.py:162-164`), so `gate read` returns rc 2 "no stored result" (`:279-281`) rather than stale data. (a) NOT FIXED: ship still holds the host-wide lock across the whole matrix, including `eval` (`pr.py:426`) and `sync-full` (`pr.py:440`). The `with` at `pr.py:682` wraps `run_gates` at `:699`. The commit message does not mention it, so it has not been dispositioned. |
| 8 (LOW, nudge raises UnicodeDecodeError) | **FIXED** | The handler is `except OSError, subprocess.TimeoutExpired, UnicodeDecodeError` at `graphify_hook.py:161` (PEP 758 form, catches all three). Live probe P3, both arms. There is no regression test (N4). |
| 9 (LOW, selfcheck Grep arm can only pass) | **FIXED** | The payload now carries `"command": _DENIED_SAMPLE` (`hook_selfcheck.py:378-386`), where `_DENIED_SAMPLE = "gh pr create --fill"` (`:52`). Probe P4: a misrouted Grep that carries the command is denied (True). The round-1 payload without the command was not denied (False). The arm can now fail. |
| 10 (LOW, doc/contract drift) | **FIXED** at every location round 1 enumerated. Residual (LOW): see the note after this table. | The eight-tool matcher now appears at `.claude/rules/clarify-before-acting.md:65` and `:78`. The suites token is updated (`suites.toml:1324`). The `hook_guard.py:3-7` docstring is updated; its `dotfiles-setup hook pretooluse` mention ("remains as a standalone entry") is now true, and it alone satisfies the `suites.toml:1346` token. Also updated: `scripts/web-setup.sh:7`, `tests/TEST-INDEX.md:55` and `:57`, `docs/rules-evidence/mise-tasks-only.md:125-126`, and `pr.py:53-55` and `:70-71`. |
| 12 (LOW, real-uv test builds a 1 GB venv) | **FIXED** | A stub `uv` records argv and execs the real interpreter (`tests/test_hook_dispatch.py:133-170`). The deny still comes from the real guard. The exact `uv run … python -P -m` argv is asserted at `:161-170`. |
| 13 (LOW, cheap interpreter fail-open removed) | **FIXED** | `scripts/pretooluse-guard.sh:39` brings back `uv python find '>=3.14'` → `fail_open "interpreter-absent"`. This behaves the same as the base wrapper (`c6b8e825:scripts/pretooluse-guard.sh:36-37`), and the suites.toml description is accurate again. Gap: the uv-present / Python-absent branch has no test arm. `tests/test_hook_dispatch.py:190-201` covers only the no-uv case. |
| 14 (LOW, KB handoff "deadlock") | **FIXED** (wording nit) | The handoff now describes an early release instead of a deadlock (`docs/handoffs/kb-host-load-followup-2026-10-02.md:32-38`). Two nits. (i) `:34` says "the first thread to finish RELEASES". It is the ACQUIRING thread that releases, whenever it finishes; a re-entrant thread's exit releases nothing (`host_lock.py:176-179` vs `:190-195`). (ii) `:41-42` still says "`kill -9` of the holder releases at once". That is true only for a holder with no fd-inheriting child, which is exactly what the new `:36-38` advice creates. |
| Q-FRESH (`suite_at_push` stale before push) | **NOT FIXED** (the lock-wait window is closed; the gate window remains) | `suite_at_push` is now decided after the lock is acquired (`pr.py:693`). It still precedes the whole gate matrix, including `eval` and `sync-full`, which can run for hours. It is not re-read before the push at `pr.py:701`. The comment at `pr.py:691-692` says the decision "describes the hook state at push time"; no line enforces that (Q-CLAIM). Closing it would take a re-read just before `:701`, falling back to the pytest gate when the answer flips to False. CI `contract-preflight` still backstops this, so it stays LOW. |

Finding 10 residual, outside round 1's enumerated lines:

- `docs/rules-evidence/mise-tasks-only.md:119-120` still says settings.json "wires every Bash call through `dotfiles-setup hook pretooluse`".
- `hook_selfcheck.py:105` says "All five matcher tools". The matcher is now eight tools; the comment is accurate only for the guarded subset.

## New defects introduced by the fix diff

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| N1 | LOW | The tests that expect `pre_push_runs_suite` to return True now depend on the developer's HOME and shell. The fix makes the function read the real `~/.hkrc.pkl`, the real `~/.config/hk/config.pkl` and the ambient `HK`. No fixture isolates HOME or `HK`. On any host with an hkrc that mentions `skip_steps`/`skip_hooks`, or a shell that exports `HK=0`, the True-expecting tests fail. | tests/test_pr.py:121-122, :145-146; python/src/dotfiles_setup/pr.py:330, :334-344, :360 | The autouse fixtures isolate only git config, mise state and locks (`tests/conftest.py:27-96`). `grep HOME tests/test_pr.py` finds 0 hits. Latent here: no hkrc exists (ls rc≠0 on all three paths), and `HK` is ABSENT (presence probe; control `HK_MISE`=SET). |
| N2 | LOW | The fixed function's own claims still overstate its coverage. It answers True while hk can be off-switched by two sources it never reads. (a) `hk.local.pkl` or `.config/hk.local.pkl`, which REPLACE `hk.pkl` and can drop the pre-push `test` step or set `skip_steps`. (b) `HK_FILE`, which points hk at another config. The overstated claims are the docstring ("none of hk's skip switches is set — environment, git config, or an hk user rc") and "Any doubt answers False". | python/src/dotfiles_setup/pr.py:347-374 (claims at :352-353, :358) | hk docs `llms-full.txt:1886-1887` (local override files), `:1894` (`HK_FILE`), `:1945-1947` ("If `hk.local.pkl` exists it is used instead of `hk.pkl`"). Latent: neither file exists, `.gitignore` has no `hk.local` entry, and `HK_FILE` is ABSENT. The CI backstop is unchanged (round 1: `ci.yml:245`). |
| N3 | LOW | The new fix arm cannot spot a misplaced reader: `_hkrc_may_skip` hard-codes `~/.config/hk/config.pkl`. If hk resolves the XDG location from `$XDG_CONFIG_HOME`, a host with a non-default value would be read at the wrong path. | python/src/dotfiles_setup/pr.py:330 | UNVERIFIED whether hk 2.3.0 honours `XDG_CONFIG_HOME`; the docs only say "XDG config directory" (`llms-full.txt:2053`). Harmless on this host: `XDG_CONFIG_HOME` = `$HOME/.config`. |
| N4 | LOW | Several fixes ship with no regression arm. Deleting any of these lines fails no test: `pass_fds` in `gate_result._run_declared`, the stale-result `unlink`, and the `UnicodeDecodeError` catch in the nudge. The 6d588856 commit message says the fd inheritance was "armed both ways" for "(heavy-gate run, gate run)". Only heavy-gate run has an arm. | python/src/dotfiles_setup/gate_result.py:162-164, :206; python/src/dotfiles_setup/graphify_hook.py:161 | `git diff 227501e2..a8f606bb --stat -- tests/test_gate_result.py` is empty. The only kill arm is `tests/test_host_lock.py:179-219`, which goes through `host_lock_main`. `git grep 'pass_fds\|lock_fd' -- tests/` gives 1 hit, the heavy-gate test's docstring. None of these lines is pinned by a suites.toml token; only `wait_s=timeout_s` is (`suites.toml:3118`). I probed the behaviour live (P2, P3), so the code works today; what is missing is the gate. |

No item REGRESSED. I found no new MEDIUM or HIGH defect in the fix diff.

Residual risk (UNVERIFIED, not tabled): after a SIGKILLed wrapper, the lock now lives as long as any descendant that inherited the non-CLOEXEC fd and did not close it. A daemonising grandchild would hold the host-wide lock indefinitely, while the record names a dead pid. This is not reachable in the paths I checked:

- `process git-isolated` respawns via `subprocess.run`, which closes the fd (`process_env.py:108`).
- `core.fsmonitor` is unset (rc=1; control `user.name`=SET).

## Probes run (all sub-second; host-quiet)

- **P1: cwd `json.py` shadowing.** I planted a `json.py` in a temp dir. It appends a marker and then exits 7. Payload: `gh pr create --fill`.
  - Fix arm: the real wrapper at HEAD from that dir gave rc=0, deny=1, marker=0, no fail-open log.
  - Control arm: `python/.venv/bin/python -m dotfiles_setup.hook_dispatch` (no `-P`) from the same dir gave rc=7, deny=0, marker=1.
  - The planted module is live, so the probe discriminates.
  - My first attempt wrote a malformed `json.py` (zsh `printf %r`), and its control produced no marker. I discarded that run.
- **P2: lock survives a SIGKILLed wrapper.** I used `DOTFILES_LOCK_DIR` set to a temp dir.
  - Fix arm: `host_lock_main(['run','--',child])`, wrapper SIGKILLed, then `held(wait_s=0.3)` reported BUSY.
  - Control arm: `held()` plus `subprocess.run(child)` with no `pass_fds`, wrapper SIGKILLed, reported ACQUIRED.
- **P3: nudge with non-UTF-8 graphify output.** A stub `graphify` prints `\377\376`.
  - Fix arm: `nudge(..., 'read', '{}')` returned `''`.
  - Control arm: a raw `subprocess.run(text=True)` of the same stub raised `UnicodeDecodeError`.
- **P4: selfcheck Grep arm.** `decide_payload("Grep", {pattern, command: "gh pr create --fill"})` denies (True). `decide_payload("Grep", {pattern})`, the round-1 payload, does not deny (False).
- **P5: hk config sources.**
  - Installed hk is `hk 2.3.0`.
  - `~/.config/hk`, `~/.hkrc.pkl`, `.hkrc.pkl`, `hk.local.pkl` and `.config/hk.local.pkl` are all absent. The control `git ls-files | grep -c hk.pkl` = 2.
  - `HK`, `HK_FILE` and `PYTHONSAFEPATH` are ABSENT (control `HK_MISE`=SET).
  - `XDG_CONFIG_HOME` = `$HOME/.config`.

## Verdict

**SHIP-READY.**

- All three round-1 MEDIUMs (1, 2, 3) are FIXED, two of them with live both-arm probes.
- No item REGRESSED, and the fix diff introduces no MEDIUM or HIGH defect.
- Two in-scope items are NOT FIXED (partial): 7(a), ship's lock spanning `sync-full`, and Q-FRESH, `suite_at_push` not re-read before the push. Both were LOW in round 1. 7(a) fails toward queued or timed-out runs in other clones. Q-FRESH can, in a narrow window, lose the LOCAL suite. Neither can produce an untested merge, because CI `contract-preflight` runs pytest before `ci-gate`. Neither is blocking.
- Recommended dispositions (ticket or fix in this unit, caller's choice), none blocking:
  - 7(a) and Q-FRESH: one ticket ("ship lock scope + re-read suite_at_push before push").
  - N1: isolate HOME and `HK` in the `pre_push_runs_suite` tests.
  - N2: add `hk.local.pkl`, `.config/hk.local.pkl` and `HK_FILE` to the conservative check.
  - N4: add kill and unlink arms for `gate run` and a non-UTF-8 arm for the nudge.
  - The KB handoff wording nits (item 14).

Stop condition: this round was BOUNDED (13 enumerated items), and all 13 are answered. Dispositioning N1-N4 does not change the enumeration, so no further round is needed unless a fix for N2 or Q-FRESH adds a new decision→action pair. A round for that would cover only the new pair.

## GitHub repos touched

_None._ I read only the local repo, the installed `pytest-xdist` in `python/.venv`, and the local hk mintlify cache (`docs/research/mintlify-cache/jdx/hk/`).
