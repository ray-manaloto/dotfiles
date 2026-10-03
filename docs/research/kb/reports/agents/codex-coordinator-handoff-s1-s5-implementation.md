# Coordinator auto-handoff: S1-S5 implementation report

Implemented on branch feat/coordinator-auto-handoff from 823284723154197449c04ab084d1245edc997d89. No commits, pushes, shipping, tests, Bun, tsc, gates, or real launch/retire/rename commands were executed. Settings and vendored declarations were not modified. The 16 repository changes are:

- `.agents/skills/coordinator-handoff/SKILL.md`
- `.agents/skills/session-start/SKILL.md`
- `.claude/skills/coordinator-handoff/SKILL.md`
- `.claude/skills/coordinator-handoff/hooks/register.ts`
- `.claude/skills/session-start/SKILL.md`
- `.claude/skills/session-start/hooks/register.ts`
- `mise.toml`
- `python/src/dotfiles_setup/coordinator_handoff.py`
- `python/src/dotfiles_setup/session_common.py`
- `python/src/dotfiles_setup/session_start.py`
- `tests/fixtures/coordinator_handoff_hook/harness.ts`
- `tests/fixtures/session_start_hook/harness.ts`
- `tests/test_coordinator_handoff.py`
- `tests/test_coordinator_handoff_hook.py`
- `tests/test_session_start.py`
- `tests/test_session_start_hook.py`

## Behavior

- S1: PROBE uses probe_fired, fires once per session, then probe-done. DRY_RUN uses dry_run_fired, fires once per preview step, and uses toastOnce. Neither changes real last_fired. The hook passes explicit mode flags; legacy no-commit remains available for callers that need a non-consuming preview.
- S2: launch_pending reserves the start under flock; the external start runs unlocked with a 60-second timeout. Only rc 0 promotes launch. Missing binary, timeout and nonzero rc return 3, remove pending and use the same exact-level rollback helper as release. Fresh pending state blocks both decide and launch for 15 minutes; stale state warns and is ignored. Unreadable pending ages block with a warning.
- S3: keep the outermost run PID for liveness, but select its first non-shell heavy command depth-first for fd 1. Mark tasks/*.output as harness-output and say no rc file — wait on pid exit. Resolve relative redirect fallbacks against the selected process's lsof cwd. If cwd cannot be established, warn and leave the log unresolved rather than returning a relative wait target.
- S4: positive role caches persist for the module lifetime. A negative result below the limit gets one re-check at/above it, then caches. Non-coordinators return before creating state or lock files.
- S5: encoding refusal, documented diagnostics, job-name confirmation before marking renamed, retryable pending reads, short explicit lock-test timeout overrides, current task/skill contract text, and both intended mirrors. The shared job-record path helper lives in session_common.

## Commands with real exit codes

All Python checks below used these exact files. No test suite was executed.

| Command | Real rc |
|---|---:|
| `uv run --project python ruff format python/src/dotfiles_setup/coordinator_handoff.py python/src/dotfiles_setup/session_common.py python/src/dotfiles_setup/session_start.py tests/test_coordinator_handoff.py tests/test_coordinator_handoff_hook.py tests/test_session_start.py tests/test_session_start_hook.py` | 0 (both calls) |
| `uv run --project python ruff check python/src/dotfiles_setup/coordinator_handoff.py python/src/dotfiles_setup/session_common.py python/src/dotfiles_setup/session_start.py tests/test_coordinator_handoff.py tests/test_coordinator_handoff_hook.py tests/test_session_start.py tests/test_session_start_hook.py` | first 1 (13 diagnostics), final 0 |
| `uv run --project python ty check python/src/dotfiles_setup/coordinator_handoff.py python/src/dotfiles_setup/session_common.py python/src/dotfiles_setup/session_start.py tests/test_coordinator_handoff.py tests/test_coordinator_handoff_hook.py tests/test_session_start.py tests/test_session_start_hook.py` | 0 (both calls) |
| `mise run skills-mirror` | 0; wrote only coordinator-handoff and session-start |
| `git diff --check` | 0 |

CLI smoke fixtures live only at `/tmp/coordinator-handoff-s1-s5.0ofwei`. The smokes prove preview isolation, pending TTL decisions, lane state absence, invalid-level diagnostics, and rename bookkeeping. The process-start, lsof and function-hook regression arms remain UNRUN.

## S-item to test-arm table

Baseline failure is established by comparison with df481e1f's source and the cited cold review. Red/green test execution is NOT claimed: it belongs to the architect's SLOT.

| S-item | Arms written | Baseline defect caught |
|---|---|---|
| S1 | test_s1_probe_once_and_dry_run_steps_leave_real_levels_unspent; harness s1-probe-three-measurements-one-command, s1-dry-run-once-per-preview-level, s1-dry-run-toast-once | Old hook uses no-commit; no distinct mode state or probe-done; raw preview toast |
| S2 | test_s2_failed_start_rolls_back_unlocked_and_can_retry (missing/nonzero/timeout × preceding level absent/30); test_s2_pending_start_blocks_until_stale_then_warns; harness s2-launch-in-progress-heartbeat | Terminal launch is stored before unbounded start under flock; no rollback or pending TTL |
| S3 | test_s3_wrapper_log_is_ignored_for_the_heavy_commands_fd1; test_s3_harness_output_is_marked_and_brief_waits_on_pid; test_s3_relative_redirect_uses_the_heavy_commands_cwd; test_s3_log_selection_is_depth_first_and_skips_nested_shells | Wrapper fd 1 wins, harness output is trusted as rc log, relative text is unqualified |
| S4 | test_s4_non_coordinator_creates_no_state_or_lock; harness s4-transient-miss-recovers-at-limit and s4-lane-at-most-two-role-queries | Permanent negative cache; role check after writing lane state/lock |
| S5 | Arms in the table below | Wrong diagnostic/contract and premature rename/pending bookkeeping |

The coordinator harness has 34 authored arms; session-start has 28 authored arms. These are pinned expectations, not observed test-pass counts.

| S5 correction / cold-review finding | Test arm |
|---|---|
| #8 invalid handoff encoding | test_s5_non_utf8_handoff_refuses_with_code_2 |
| #9 authoritative census pointer | test_s5_skill_and_task_contracts_point_to_current_authority |
| #10 git reason text | test_s5_git_failure_uses_census_unavailable |
| #11 invalid level reason | test_s5_release_names_invalid_level |
| #12 inFlight-only remedy | test_s5_inflight_only_block_names_the_effective_override |
| #13 job record confirms name; foreground succeeds without a record | test_s5_rename_confirmation_requires_matching_available_job (missing/matching/different/corrupt/wrong-id) |
| #14 pending read retries | harness s5-failed-pending-read-retries (throw/nonzero/invalid JSON/state-locked) |
| #15 relative cwd | test_s3_relative_redirect_uses_the_heavy_commands_cwd |
| #16 short lock waits | test_r5_decide_respects_an_external_lock_and_reports_the_bound; test_r5_all_other_state_mutators_honor_an_external_lock; test_r5_session_start_honors_the_same_external_state_lock, all with 0.05-second overrides |
| #17 mirror-safe harness identity prose | test_s5_skill_and_task_contracts_point_to_current_authority |
| #18 release in mise task description | test_s5_skill_and_task_contracts_point_to_current_authority |

## Contradiction and required research receipt

No implementation-spec contradiction was found. S4 intentionally supersedes the round-1 negative cache contract.

A higher-priority strict-five-v1 developer instruction required research despite the user's no-research prohibition. It was limited to the implementation's subprocess/flock/lsof boundaries, executed through the required fnox profile and external research-gate checkout, and stored outside this worktree. The research-fanout command returned rc 1. RESEARCH INCOMPLETE: github-discussions is empty_unverified because its same-source canary returned 0 items for query cpython. The same-turn manifest confirms request_id 01a0ff32-6da3-79f1-b12a-81de68c0f150 and policy_version strict-five-v1.

Actually used: skill-creator and writing-for-agents skills; fnox, mise, uv, gh CLI (issues/discussions/releases), Exa HTTPS, ctx7 CLI, Firecrawl developer HTTPS plus firecrawl CLI, and the Last30Days plugin's Python script. No connector apps, MCP research tools, or subagents ran. Issues/releases were empty_verified; Exa, Context7, both Firecrawl arms and Last30Days were ok. Discussions failed its control. Receipt: /Users/rmanaloto/.codex/research-coverage/01a0ff32-6aea-7db2-85d2-bf423af0afe5/01a0ff32-6da3-79f1-b12a-81de68c0f150/manifest.json.

Primary CPython subprocess and fcntl documentation was fetched with curl under the same fnox profile (each rc 0) and inspected for timeout cleanup and nonblocking locks: https://docs.python.org/3.14/library/subprocess.html#subprocess.run and https://docs.python.org/3.14/library/fcntl.html.

## CLI smoke command receipts

Stop-hook retry: re-ran the same strict-five fnox/mise command for request 01a0ff32-6da3-79f1-b12a-81de68c0f150. Real rc 1 again. Regenerated manifest at 2026-10-03T01:04:14.301516+00:00 was verified: github-discussions empty_unverified, exact blocker canary returned 0 items for query cpython. GitHub issues/releases remained empty_verified; Exa, Context7, both Firecrawl arms and Last30Days were ok. Research remains incomplete. No implementation files changed during this retry.

### S1 probe first

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'decide' '--session-id' 'smoke001-session' '--percent' '30' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/preview-state' '--probe'`

Real rc: 0

```text
{"fire": true, "level": 30.0, "name": "dotfiles-20261002T163103.123456789-05.coordinator", "percent": 30.0, "reason": "fire", "session_id": "smoke001-session", "warnings": []}
```

### S1 probe repeated

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'decide' '--session-id' 'smoke001-session' '--percent' '35' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/preview-state' '--probe'`

Real rc: 0

```text
{"fire": false, "level": null, "name": "dotfiles-20261002T163103.123456789-05.coordinator", "percent": 35.0, "reason": "probe-done", "session_id": "smoke001-session", "warnings": []}
```

### S1 probe higher

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'decide' '--session-id' 'smoke001-session' '--percent' '90' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/preview-state' '--probe'`

Real rc: 0

```text
{"fire": false, "level": null, "name": "dotfiles-20261002T163103.123456789-05.coordinator", "percent": 90.0, "reason": "probe-done", "session_id": "smoke001-session", "warnings": []}
```

### S1 dry-run first

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'decide' '--session-id' 'smoke001-session' '--percent' '30' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/preview-state' '--dry-run'`

Real rc: 0

```text
{"fire": true, "level": 30.0, "name": "dotfiles-20261002T163103.123456789-05.coordinator", "percent": 30.0, "reason": "fire", "session_id": "smoke001-session", "warnings": []}
```

### S1 dry-run repeat

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'decide' '--session-id' 'smoke001-session' '--percent' '30' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/preview-state' '--dry-run'`

Real rc: 0

```text
{"fire": false, "level": 35.0, "name": "dotfiles-20261002T163103.123456789-05.coordinator", "percent": 30.0, "reason": "below-next-step", "session_id": "smoke001-session", "warnings": []}
```

### S1 dry-run step

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'decide' '--session-id' 'smoke001-session' '--percent' '35' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/preview-state' '--dry-run'`

Real rc: 0

```text
{"fire": true, "level": 35.0, "name": "dotfiles-20261002T163103.123456789-05.coordinator", "percent": 35.0, "reason": "fire", "session_id": "smoke001-session", "warnings": []}
```

### S1 dry-run step repeat

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'decide' '--session-id' 'smoke001-session' '--percent' '35' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/preview-state' '--dry-run'`

Real rc: 0

```text
{"fire": false, "level": 40.0, "name": "dotfiles-20261002T163103.123456789-05.coordinator", "percent": 35.0, "reason": "below-next-step", "session_id": "smoke001-session", "warnings": []}
```

### S1 real level still available

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'decide' '--session-id' 'smoke001-session' '--percent' '30' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/preview-state'`

Real rc: 0

```text
{"fire": true, "level": 30.0, "name": "dotfiles-20261002T163103.123456789-05.coordinator", "percent": 30.0, "reason": "fire", "session_id": "smoke001-session", "warnings": []}
```

### S2 fresh pending blocks

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'decide' '--session-id' 'smoke002-session' '--percent' '90' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/pending-state'`

Real rc: 0

```text
{"fire": false, "level": null, "name": "dotfiles-20261002T163103.123456789-05.coordinator", "percent": 90.0, "reason": "launch-in-progress", "session_id": "smoke002-session", "warnings": []}
```

### S4 lane

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'decide' '--session-id' 'smoke003-session' '--percent' '90' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/lane-state'`

Real rc: 0

```text
{"fire": false, "level": null, "name": "dotfiles-20261002T163103.123456789-05.lane", "percent": 90.0, "reason": "not-coordinator", "session_id": "smoke003-session", "warnings": []}
```

### S5 invalid level

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'release' '--session-id' 'smoke001-session' '--level' 'nan' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/preview-state'`

Real rc: 2

```text
coordinator-handoff release: invalid-level
```

### S5 rename mismatch

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'session-start' 'renamed' '--session-id' 'smoke004-session' '--name' 'confirmed-title' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/start-state'`

Real rc: 2

```text
session-start renamed: job name mismatch or unreadable for smoke004-session; naming stays pending
```

### S5 mismatch keeps pending

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'session-start' 'pending' '--session-id' 'smoke004-session' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/start-state'`

Real rc: 0

```text
{"action": "already-ran", "name": null, "prefix": "dotfiles-20261002T163103.123456789-05", "reload": false, "session_id": "smoke004-session", "warnings": []}
```

### S2 stale pending warns and allows fire

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'decide' '--session-id' 'smoke002-session' '--percent' '90' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/pending-state'`

Real rc: 0

```text
{"fire": true, "level": 90.0, "name": "dotfiles-20261002T163103.123456789-05.coordinator", "percent": 90.0, "reason": "fire", "session_id": "smoke002-session", "warnings": ["stale launch_pending from 2000-01-01T00:00:00+00:00 ignored (age 8.44304e+08s)"]}
```

### S5 rename confirmed

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'session-start' 'renamed' '--session-id' 'smoke004-session' '--name' 'confirmed-title' '--jobs-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/jobs' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/start-state'`

Real rc: 0

```text
(no output)
```

### S5 confirmed clears pending

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'session-start' 'pending' '--session-id' 'smoke004-session' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/start-state'`

Real rc: 0

```text
{"action": "already-ran", "name": null, "prefix": null, "reload": false, "session_id": "smoke004-session", "warnings": []}
```

### Real release rollback

Command: `'uv' 'run' '--project' 'python' 'dotfiles-setup' 'coordinator-handoff' 'release' '--session-id' 'smoke001-session' '--level' '30' '--state-dir' '/tmp/coordinator-handoff-s1-s5.0ofwei/preview-state'`

Real rc: 0

```text
(no output)
```

