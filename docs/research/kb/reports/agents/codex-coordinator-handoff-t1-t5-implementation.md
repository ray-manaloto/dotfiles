# Coordinator handoff T1-T5 implementation

Base: dd871ef74fb44a05ad2f4626c9beede94576dead, branch feat/coordinator-auto-handoff.
Scope: spec section 11; cold review bdedf8d1 read, including measured eval wrapper.

## Constraints and contradictions

- Tests and host gates are NOT RUN by user instruction. Regression arms are authored; baseline/current pass status remains UNVERIFIED until the coordinator runs them under its SLOT.
- No commit, push, ship, actual launch/retire/rename, settings edit, or declaration edit.
- User forbids research fanout; higher-priority strict-five-v1 hook requires it. Only the hook-required handoff research receipt is run.
- Graphify tasks and root findings.md are outside the user's command/file scope. Source/spec are the authority; incremental findings live in this requested report and .agent/notepad.md.

## Findings at the base commit

- T1: _start_successor rolls back last_fired on failed start, allowing immediate re-fire.
- T2: finalisation failure reports rc 3 despite a successful start and leaves retirement without a launch record.
- T3: redirect fallback searches the whole wrapper and can select its prelude /dev/null redirect.
- T4: probe consumption occurs at decide, and failed delivery cannot release it.
- T5: refusal labels, negative-role cache TTL, unknown pending age, and pending-read cap need correction.

## Verification

No tests executed. File-scoped formatting, lint/type checks and inert CLI smoke results are recorded below.

- Initial file-scoped Ruff format: rc 0 (2 reformatted, 3 unchanged). Ruff check: rc 1, eight findings (argument/return/statement counts and fixture path literals); fixed through small helpers and fixture grouping, with no suppressions. Initial ty: rc 0.
- Second Ruff format: rc 0 (1 reformatted, 4 unchanged). Final Ruff check and ty check on the two changed source files and three changed Python test drivers: both rc 0.
- `mise run skills-mirror`: rc 0, wrote only coordinator-handoff and session-start SKILL.md mirrors.
- `git diff --check`: rc 0. HEAD remains dd871ef7; 13 tracked paths changed, all in the allowlist.
- Strict-five native fnox research fanout: rc 1; manifest request ID is correct. GitHub issues ok (10), discussions empty_unverified (canary 0), releases empty_verified (same-source control); Exa ok (10), Context7 ok (5), Firecrawl developer/search ok (10 each), Last30Days error (CLI rc 2, missing required plan field intent). RESEARCH INCOMPLETE. No external claim used to change the ratified design.

## Implementation notes

- T2 uses an atomic per-session .started.json receipt under an independent native flock. This is necessary because a main-lock timeout prevents editing the main JSON at all. Reads fold it into launch_pending with started true; retirement accepts it before recovery. Under the main lock, confirmation is persisted before the separate promotion write.
- If both independent receipt persistence and main-state persistence fail, a process cannot promise a durable confirmation. rc 4 still reports the actual started outcome; this fundamental storage limitation is reported, not called a successful record. Tests cover promotion, main marker-write, lock reacquisition, and changed-claim failures.
- The cold review includes the measured prelude excerpt, not the full 1657-character argv. The T3 fixture preserves its literal unalias /dev/null / eval shape and ellipsis, adds the requested placeholder snapshot path, and never executes that shell text.
- Found a pre-existing contradictory test expecting lane last_seen state, although round-2 S4 already forbids all lane state. Updated it to assert no lane state and a coordinator heartbeat control.
- A patch application failed validation once (invalid empty hunk); no files were changed by that failed call. Corrected the patch and reran allowed formatting/checks.

## Final status and files

Implemented T1-T5 on dd871ef7 without committing. These 13 tracked files changed:

- python/src/dotfiles_setup/coordinator_handoff.py
- python/src/dotfiles_setup/session_common.py
- .claude/skills/coordinator-handoff/hooks/register.ts
- .claude/skills/session-start/hooks/register.ts
- .claude/skills/coordinator-handoff/SKILL.md
- .claude/skills/session-start/SKILL.md
- .agents/skills/coordinator-handoff/SKILL.md (generated)
- .agents/skills/session-start/SKILL.md (generated)
- tests/test_coordinator_handoff.py
- tests/test_coordinator_handoff_hook.py
- tests/test_session_start_hook.py
- tests/fixtures/coordinator_handoff_hook/harness.ts
- tests/fixtures/session_start_hook/harness.ts

Local records: this report, .agent/notepad.md, .agent/logs/coordinator-handoff-t1-t5-cli-smokes.json, .agent/logs/coordinator-handoff-round3-last30days-plan.json. Temporary smoke fixtures: /tmp/coordinator-handoff-t1-t5.S4yIjq. No protected settings/declaration edits.

## T-item to regression arm

All arms below are AUTHORED, NOT RUN. The failure-on-bdedf8d1 explanations come from source/cold-review replay, not execution. Current baseline/current pass status remains UNVERIFIED, as required by the host SLOT prohibition. Coordinator hook driver expects 40 arms; session-start driver expects 33 (authored expectations, not measured executed counts).

| Item | Named arm | Why it would fail on bdedf8d1 / intended corrected behavior |
|---|---|---|
| T1 | test_t1_failed_start_keeps_level_and_retries_only_at_next_step | Six cases: prior level absent/30 crossed to 45, each nonzero/missing/timeout start. Baseline restores the previous level and fires again at 45 (F1/E1). Now 45 remains consumed, 49.9 is quiet, 50 fires. Verifies flock is released across dispatch. Replaces the immediate-refire assertion located by content near original line 1274. |
| T2 | test_t2_started_promotion_failure_blocks_relaunch_and_allows_retire | Five actual filesystem/lock boundary failures after injected successful dispatch: promotion replace, main marker replace, finalisation lock, changed pending claim, unreadable main state. Baseline returns 3 (F3/E5), lacks started confirmation and refuses retire. Corrected rc 4; no relaunch at 90/100; retire eligible using original census. Independent receipt covers inability to reacquire/write/read main state. |
| T2 | test_t2_started_pending_without_receipt_is_terminal_and_retirable | Missing-age and 2000-era started pending records without any sidecar. Baseline ignores started and refuses retire. Corrected already-launched regardless of age; dry retirement eligible with valid census/inFlight. |
| T3 | test_t3_measured_eval_wrapper_skips_prelude_redirect | Six measured-prelude payloads: variable, variable/space path, absolute file, /dev/null, no redirect, nested last eval. Baseline returns the prelude /dev/null (F2/E3). Corrected fallback reads only final eval payload, keeps unresolved variables labelled, and represents /dev/null/no redirect as no log; brief says wait on pid exit. |
| T4 | test_t4_probe_is_pending_until_delivery_and_rejection_releases_it | Baseline immediately writes probe_fired and cannot release a probe (F4/E6). Corrected probe_pending before delivery; release allows retry; delivered confirmation sets probe_fired; real level remains unspent. |
| T4 | t4-failed-probe-releases-and-reports-failure | Production hook harness: rejection, missing skill, throwing listing all call release --probe, show exact delivery ERROR, then successful retry confirms done. Baseline omits release under PROBE. |
| T4 | t4-probe-done-only-after-command-resolution | Delayed command resolution plus an intervening measurement: pending throughout, no confirm until resolved. Baseline lacks pending status and post-resolution confirmation. |
| T4 | t4-release-failure-never-reports-probe-done | Failed rollback never overwrites delivery ERROR with a done heartbeat. |
| T4 | t4-confirmation-failure-keeps-accurate-error | Delivered command with failed state confirmation stays confirmation ERROR through the next measurement, queues no second command, never displays done. |
| T5/F6 | test_t5_git_failure_uses_worktree_unavailable; test_t5_launch_state_refusals_are_distinct_from_census | Baseline calls git, corrupt state and lock failures census-unavailable (F6/E8). Corrected worktree-unavailable, state-unreadable, state-locked. Handoff encoding is separately handoff-unreadable; process snapshot/tree failures remain census-unavailable. |
| T5/F7 | t5-negative-role-cache-expires-at-ten-minutes | At/above-limit miss cached at time 0, no new process at 599999 ms, recovery at 600000 using $.clock.now. Positive coordinator cache remains valid after another ten minutes. Baseline's negative cache never expires (F7/E9). |
| T5/F8 | test_t5_unknown_pending_age_is_stale_with_warning | Non-dict, missing, malformed and timezone-naive ages: baseline blocks forever. Corrected decision fires with stale warning; launch dry-run can proceed. Fresh valid pending-start blocking control remains in test_s2_pending_start_blocks_until_stale_then_warns. |
| T5/F9 | t5-pending-recovery-stops-after-three-failures; t5-third-pending-read-can-succeed | Four failure shapes: throwing process, nonzero rc, non-JSON, state failure. At most three reads, exactly one terminal ERROR status, no more reads/statuses. Success on third read still renames/confirms/caches. Baseline issues a fourth read (F9). |

Python arms are in tests/test_coordinator_handoff.py. Hook names are pinned by tests/test_coordinator_handoff_hook.py and tests/test_session_start_hook.py, which drive the real register modules through their TS fixtures when the coordinator executes them.

## Commands and observed return codes

File set for Python checks: python/src/dotfiles_setup/coordinator_handoff.py python/src/dotfiles_setup/session_common.py tests/test_coordinator_handoff.py tests/test_coordinator_handoff_hook.py tests/test_session_start_hook.py.

| Command | Real rc / result |
|---|---|
| uv run --project python ruff format (above five paths) | First rc 0 (2 reformatted), second rc 0 (1 reformatted). |
| uv run --project python ruff format python/src/dotfiles_setup/coordinator_handoff.py tests/test_coordinator_handoff.py | Extension rc 0 (2 reformatted), corrective pass rc 0 (2 unchanged). |
| uv run --project python ruff check (above five paths) | Observed sequence 1, 0, 1, 0, 0. Initial eight findings fixed; later 52-statement test split/simplified to the allowed budget. Final rc 0, All checks passed. |
| uv run --project python ty check (above five paths) | All five observed runs rc 0, including final source/test bytes. |
| mise run skills-mirror | rc 0; regenerated only the two changed SKILL.md mirrors. |
| git diff --check | Final standalone rc 0. |
| git diff --name-only -- .claude/settings.json .claude/types | rc 0, empty output. |
| git rev-parse HEAD | rc 0, dd871ef74fb44a05ad2f4626c9beede94576dead. |
| mktemp -d /tmp/coordinator-handoff-t1-t5.XXXXXX | rc 0, created the inert smoke fixture directory. |

All CLI smoke commands are below with real rc. Full captured output/chunk IDs are in .agent/logs/coordinator-handoff-t1-t5-cli-smokes.json. These are CLI smokes against temp directories, not an execution of the regression tests. Launch/retire commands always use --dry-run; no harness binary was executed.

| Smoke | Exact command | Real rc |
|---|---|---|
| step-before | `uv run --project python dotfiles-setup coordinator-handoff decide --session-id abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --percent 49.9 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/steps` | 0 |
| started-terminal | `uv run --project python dotfiles-setup coordinator-handoff decide --session-id abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --percent 100 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/started` | 0 |
| receipt-retire | `uv run --project python dotfiles-setup coordinator-handoff retire --old-session abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/receipt --dry-run` | 0 |
| unknown-age | `uv run --project python dotfiles-setup coordinator-handoff decide --session-id abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --percent 35 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/stale` | 0 |
| corrupt-decision | `uv run --project python dotfiles-setup coordinator-handoff decide --session-id abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --percent 35 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/corrupt` | 0 |
| corrupt-pending | `uv run --project python dotfiles-setup session-start pending --session-id abcdef12-0000-4000-8000-000000000001 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/corrupt` | 0 |
| corrupt-launch | `uv run --project python dotfiles-setup coordinator-handoff launch --old-session abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/corrupt --handoff /tmp/coordinator-handoff-t1-t5.S4yIjq/handoff.md --dry-run` | 2 |
| session-noninteractive | `uv run --project python dotfiles-setup session-start decide --session-id abcdef12-0000-4000-8000-000000000001 --cwd /tmp/coordinator-handoff-t1-t5.S4yIjq --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/session --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --non-interactive` | 0 |
| step-at | `uv run --project python dotfiles-setup coordinator-handoff decide --session-id abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --percent 50 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/steps` | 0 |
| probe-first | `uv run --project python dotfiles-setup coordinator-handoff decide --session-id abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --percent 30 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/probe --probe` | 0 |
| probe-pending | `uv run --project python dotfiles-setup coordinator-handoff decide --session-id abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --percent 35 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/probe --probe` | 0 |
| probe-release | `uv run --project python dotfiles-setup coordinator-handoff release --session-id abcdef12-0000-4000-8000-000000000001 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/probe --probe` | 0 |
| probe-retry | `uv run --project python dotfiles-setup coordinator-handoff decide --session-id abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --percent 35 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/probe --probe` | 0 |
| probe-confirm | `uv run --project python dotfiles-setup coordinator-handoff release --session-id abcdef12-0000-4000-8000-000000000001 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/probe --probe --delivered` | 0 |
| probe-done | `uv run --project python dotfiles-setup coordinator-handoff decide --session-id abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --percent 100 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/probe --probe` | 0 |
| probe-real-unspent | `uv run --project python dotfiles-setup coordinator-handoff decide --session-id abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --percent 30 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/probe` | 0 |
| started-retire | `uv run --project python dotfiles-setup coordinator-handoff retire --old-session abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/started --dry-run` | 0 |
| started-launch-refusal | `uv run --project python dotfiles-setup coordinator-handoff launch --old-session abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/started --handoff /tmp/coordinator-handoff-t1-t5.S4yIjq/handoff.md --dry-run` | 2 |
| receipt-terminal | `uv run --project python dotfiles-setup coordinator-handoff decide --session-id abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --percent 100 --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/receipt` | 0 |
| receipt-corrupt-retire | `uv run --project python dotfiles-setup coordinator-handoff retire --old-session abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/receipt-corrupt --dry-run` | 0 |
| receipt-corrupt-recovery | `uv run --project python dotfiles-setup coordinator-handoff decide --session-id abcdef12-0000-4000-8000-000000000001 --jobs-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/jobs --state-dir /tmp/coordinator-handoff-t1-t5.S4yIjq/receipt-corrupt --percent 100` | 0 |

The two rc-2 smoke outcomes are intentional refusal controls: corrupt state and an already-started successor. Other smoke commands returned 0. Corrupt main-state recovery is visible as a warning and uses the original census in the independent started receipt.

## Research hook receipt and actual routes

Initial required command (real rc 1; same command rerun below):

```text
fnox --config ~/.config/fnox/config.toml --profile codex_research --no-defaults --no-daemon --non-interactive exec -- mise -C /Users/rmanaloto/.codex/tools/dotfiles-research-gate run research-fanout -- 'Claude Code background sessions command hooks handoff' --repo anthropics/claude-code --strict-five --request-id 01a0ff59-2223-7723-a108-bef8294f32f9 --last30days-plan /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002/.agent/logs/coordinator-handoff-round3-last30days-plan.json --out /Users/rmanaloto/.codex/research-coverage/01a0ff59-1f4b-7333-9928-a82956530853/01a0ff59-2223-7723-a108-bef8294f32f9
```

Initial manifest read and verified: correct policy/request ID, all eight route entries present, generated_at 2026-10-03T01:22:16.649649+00:00. GitHub releases empty_verified includes its same-source control. The current rerun receipt is recorded below.

- CLIs actually invoked: fnox, mise, uv, gh for GitHub issues/discussions/releases, ctx7 for library/docs, firecrawl for web search, python3 for the installed Last30Days 3.26.0 plugin script (/Users/rmanaloto/.claude/plugins/cache/last30days-skill/last30days/3.26.0/skills/last30days/scripts/last30days.py). Exa and Firecrawl developer searches use direct HTTP API routes within the fanout.
- No connector app or MCP app was invoked. No standalone research skill was invoked. Spec and relevant SKILL.md files were read for implementation contracts; skills-mirror regenerated the two maintained surfaces.
- GitHub issues ok (10), releases empty_verified; discussions empty_unverified: canary returned 0 items.
- Exa ok (10), Context7 ok (5), Firecrawl developer and search ok (10 each).
- Last30Days plugin script executed and rejected plan with rc 2: missing required field intent. It did not successfully fetch evidence.
- RESEARCH INCOMPLETE: GitHub discussions did not complete (canary returned 0 items); Last30Days failed plan validation (missing required field intent). No five-provider success claimed.
- Primary implementation evidence: current local source and the measured cold-review sample. Checked bundled primary EngineInterface declarations at .claude/types/claude-code.d.ts:2893-2901: $.clock.now resolves epoch milliseconds. No fetched third-party claim was used to override the ratified spec. No web search tool was separately invoked; required research routed only through native fnox.

## Contradictions and remaining validation

- Section 11 supersedes section 10 S2's rollback promise: failed starts KEEP last_fired; only undelivered skill submission releases real levels. Section 11 T4 supersedes decide-time probe consumption with pending/confirmed state.
- User hard prohibitions supersede spec sections 5-6/local-validation/commit requirements for this implementer. Pytest, Bun, tsc, lint/verify/fnhook-gates/gate, Claude/agy, live hook probes, stop/rename, commits, pushes and shipping are NOT RUN.
- Higher-priority strict-five hook overrides the user's no-fanout clause; receipt failure is recorded, not counted as a successful audit. No unrelated implementation/research was done.
- Graphify commands and root findings.md were excluded by the user's allowed-command/file scope; incremental findings were recorded in the requested report and .agent/notepad.md.
- State-lock failure means the locked main JSON cannot itself be updated at that instant. The independent started receipt supplies the logical started pending record until normal state access resumes. Main marker is written before promotion when writable. Receipt includes the census so retirement can recover a main JSON that became unreadable after dispatch. If both receipt and main persistence remain unavailable, durable success cannot be guaranteed; rc 4 still accurately warns do not relaunch. This storage limit is explicit.
- The review provides the prelude excerpt and an ellipsis rather than full measured argv. T3 preserves that exact sampled segment, adds only placeholder snapshot location, and exercises parsing without executing the string.
- Corrected the inherited lane-heartbeat test conflicting with section 10 S4; no lane state is created. No other scope expansion.
- No additional user-authored logic was requested: section 11 already ratifies the retry, cache, recovery and outcome choices.
- Patch application validation failed three times during editing, without modifying files on those failed calls; the intended edits were subsequently written successfully. No failed execution/test result hidden.
- Required coordinator validation remains: execute the named baseline/current arms under the HOST SLOT, production Bun harnesses, typed function-hook gates, full repo gates and review cycle. Actual harness behavior, vendored-type currency and cold-review F5's supervisor/timeout uncertainty remain UNVERIFIED here. No declarations/settings changed.

Implementation is ready for coordinator review; no claim that forbidden regression tests passed.

## Stop-hook receipt retry (same request ID)

- Stop hook requested a strict-five rerun for 01a0ff59-2223-7723-a108-bef8294f32f9. Read the installed Last30Days 3.26.0 primary planner schema: required intent/freshness_mode/cluster_mode and search_query/ranking_query/sources. Corrected the local plan and reran the exact native fnox command above. Implementation/test files are unchanged during this retry.
- Native fnox/mise strict-five rerun real rc 1 (exec session 11586, final chunk bd6b35). Last30Days schema failure is resolved: this route now returned 5 items successfully.
- Verified current manifest with `jq '{request_id,policy_version,generated_at,strict_five,sources:[.sources[]|{source,status,reason,items:(.items|length),control}]}' /Users/rmanaloto/.codex/research-coverage/01a0ff59-1f4b-7333-9928-a82956530853/01a0ff59-2223-7723-a108-bef8294f32f9/manifest.json`: real rc 0. Request ID correct; strict_five true; generated_at 2026-10-03T01:45:07.324483+00:00; all eight routes present.

| Provider group | Verified rerun evidence | Result |
|---|---|---|
| GitHub | issues ok: 10; releases empty_verified: 0 with repo control count 1; discussions empty_unverified: 0, canary query claude-code control count 0 | INCOMPLETE |
| Exa | ok: 10 | Complete |
| Context7 | ok: 5 | Complete |
| Firecrawl | developer ok: 10; search ok: 10 | Complete |
| Last30Days | ok: 5 | Complete |

- RESEARCH INCOMPLETE: github-discussions did not complete; exact manifest blocker: canary returned 0 items (control query claude-code, count 0). This is not evidence that the user lacks credentials. No five-provider success is claimed.
- Read primary fetcher source research_fanout.py:603-643 to verify discussions actually uses gh api graphql; primary Last30Days planner validation source checked before correcting the plan. No research claim altered the T1-T5 implementation.
- Rerun invoked the same native CLIs/API routes as the initial attempt; the installed Last30Days plugin now completed its fetch. No connector app, MCP app or separate research skill was invoked.
- Read-only git status/rev-parse confirmed the same 13 tracked paths and HEAD dd871ef74fb44a05ad2f4626c9beede94576dead. Tests, gates and all real harness operations remain NOT RUN; no commit/push/ship.
