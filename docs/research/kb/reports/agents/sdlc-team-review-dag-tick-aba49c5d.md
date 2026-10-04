## Findings

Source paths below are relative to the dotfiles checkout.

| Severity | Claim | File:line | Evidence |
|---|---|---|---|
| HIGH | A planned DEAD recovery can revive a deliberately retired coordinator. | `python/src/dotfiles_setup/dag_tick.py:1240`; `python/src/dotfiles_setup/coordinator_handoff.py:1154` | Execution rereads state but checks escalation and PID liveness without rechecking terminal status. Static replay: DEAD snapshot → handoff stops coordinator → latest stopped/idle state, dead PID → respawn requested. |
| HIGH | The code’s assumption that respawn refuses running sessions contradicts primary documentation. | `python/src/dotfiles_setup/dag_tick.py:508`; current vendor documentation | Current docs define respawn as restarting running or stopped sessions. The PID check therefore cannot rely on native refusal to close the subsequent race. Actual race behavior was not mutation-tested. [Claude command reference](https://code.claude.com/docs/en/agent-view#shell-commands) |
| HIGH | Scheduled execution follows mutable checkout contents without a branch or approved-revision guard. | `mise.toml:722`; `mise.toml:1565`; `python/src/dotfiles_setup/dag_tick.py:1383` | The installed plist runs `mise run dag-tick` from the main checkout. A later branch switch or local edit can change watchdog behavior, including restoring pre-#1644 code. |
| HIGH | `--dry-run` consumes Codex verdicts despite its read-only description. | `mise.toml:721`; `python/src/dotfiles_setup/dag_tick.py:1334`; `python/src/dotfiles_setup/codex_verdict.py:396` | Every tick invokes the reaper. It creates a lock, renames `verdict.json` to `verdict.processed.json`, and marks lane metadata `reaped`, including during dry-run. |
| MEDIUM | The outer mise invocation can install missing tools before Python checks run. | `mise.toml:132`; installed plist `:15`; upstream `src/cli/run.rs:843` | Effective `task.run_auto_install=true`; no override appears in the plist. A Python branch guard alone occurs too late to prevent these effects. [Installed-version mise source](https://github.com/jdx/mise/blob/v2026.10.1/src/cli/run.rs#L843) |
| MEDIUM | Bootstrap apply cannot reliably clear the current disabled override. | upstream `src/system/launchd.rs:328`; `/usr/share/man/man1/launchctl.1:107` | Mise writes the plist, boots out, bootstraps with failure propagation, then enables. Apple’s manual states disabled services cannot load until reenabled; bootstrap failure can prevent reaching enable. [Mise launchd source](https://github.com/jdx/mise/blob/v2026.10.1/src/system/launchd.rs#L328) |
| MEDIUM | Broad bootstrap apply can activate unrelated missing or changed agents. | upstream `src/cli/bootstrap.rs:4933`; `src/cli/system/install.rs:378` | Apply reconciles merged launchd definitions, excluding unchanged loaded agents. It is not scoped to dag-tick. [Apply implementation](https://github.com/jdx/mise/blob/v2026.10.1/src/cli/system/install.rs#L378) |
| MEDIUM | Hung census commands or reaper locks can stall recovery. | `python/src/dotfiles_setup/dag_tick.py:1008`; `:1037`; `python/src/dotfiles_setup/codex_verdict.py:440` | Census/preflight subprocesses lack timeouts; reaper flock blocks. Detached respawn children are not awaited and can outlive the tick lock. |
| CONFIRMED | #1644 removes the original direct STOP path. | `python/src/dotfiles_setup/dag_tick.py:295`; `:711`; `tests/test_dag_tick.py:2544` | Action kinds are RESPAWN and LOG. DONE plans no process action; the former stop helper is absent. |

The respawn-refusal assumption and dry-run description are **licensed-dissent findings**: the review cannot endorse those claims against the cited evidence.

## Remaining action classes

| Classification/path | Behavior |
|---|---|
| Fresh DEAD | Requests detached `claude respawn <sid>` after fresh escalation/PID checks. Output is discarded; recovery success and useful work are not verified. |
| DEAD older than 24 hours or unknown age | Log only. |
| NEEDS_HUMAN | Log only. |
| REPLY_QUEUED with live PID | Log only. |
| WEDGED | Log only. |
| DONE or ALIVE | No planned process action; quiet unless verbose. |
| Unreadable state or roster | Conservatively suppresses recovery. |
| Settled Codex lane, regardless of node classification | Consumes verdict and updates native lane metadata, including during dry-run. |
| Every tick | Census/preflight commands, tick lock creation and logging. The mise wrapper may prepare/install tools. |

There is no direct tick `stop`, `kill`, `rm`, Git checkout operation, or invocation of `dag-project --write`. Nevertheless, respawn changes session state and can restart a live session if state changes after the check. A recovered session may subsequently execute work that changes its checkout.

## Respawn versus prompted resume

**Do not replace every DEAD recovery with generic `--resume --bg`.**

The historical report’s resume arm demonstrated a new turn with the same ID and restored worktree. Its respawn control restored a stopped, done/idle throwaway without another turn. That control does **not** establish behavior for crash-mid-activity or queued-prompt recovery. Evidence: `f9b56da5:docs/research/kb/reports/agents/session-autostart-2026-10-03.md:70`.

Full-UUID resume with a prompt is the documented way to continue work, but it can fall back to a copy under a new ID. Conversation restoration also does not restore unfinished tools, background Bash commands or monitors. [Background resume semantics](https://code.claude.com/docs/en/agent-view#from-your-shell)

For deliberate coordinator recovery, first establish the current owner and absence of a successor. Reconcile the handoff, transcript, inbox, ship queue, task plan and outstanding processes before dispatching or shipping. Verify the resulting session ID, worktree, inbox and actual turn result. The existing handoff safeguards remain authoritative: `coordinator_handoff.py:698` and `:823`.

## Ranked proposals

| Rank | Proposal | PRO | CON |
|---|---|---|---|
| **1 — Recommended** | Keep disabled; correct recovery-state checks, launch provenance and dry-run consumption, then validate isolated recovery controls. | Addresses the observed defects while preserving #1644. | DEAD recovery remains supervised meanwhile. |
| 2 | Re-enable current code with explicit acceptance of its remaining behavior. | Immediately restores fresh-DEAD process recovery. | Retains retirement races, mutable executable code and unverified continuation. |
| 3 | Replace all DEAD respawns with prompted resume. | Can explicitly start a turn. | Can create duplicate ownership, awaken retired coordinators or interact incorrectly with queued replies. |

The eventual scheduler should reject unapproved checkout state on **every invocation**, with protection established before mutable project code or tool installation runs.

Before activation, meaningful isolated controls should demonstrate:

- DONE with a live PID remains untouched; reverting the STOP fix fails.
- A DEAD snapshot followed by terminal/retired state cannot respawn; still-DEAD state remains the positive control.
- Dry-run preserves settled verdict and lane bytes; normal execution consumes them.
- Unapproved branch/revision/dirty state is refused; approved state succeeds.
- Recovery preserves ownership and verifies useful continuation, including queued replies.

These checks were reviewed, not executed. The existing dry-run test creates no Codex lane and therefore misses verdict consumption.

## Conditional re-enable procedure for Ray

Current host evidence:

- `launchctl print-disabled gui/501` → **rc=0**, dag-tick disabled.
- `launchctl print gui/501/dev.mise.dotfiles-dag-tick` → **rc=113**, service absent.

**After the corrections and validation above**, enable only the reviewed plist:

```sh
launchctl enable gui/501/dev.mise.dotfiles-dag-tick
launchctl bootstrap gui/501 /Users/rmanaloto/Library/LaunchAgents/dev.mise.dotfiles-dag-tick.plist
launchctl print-disabled gui/501
launchctl print gui/501/dev.mise.dotfiles-dag-tick
```

Require enable/bootstrap **rc=0**, no disabled override, and service print **rc=0** with the reviewed program and working directory. If already loaded, inspect its definition before taking further action. The current plist has neither `RunAtLoad` nor `KeepAlive`; observe the scheduled interval and logs. Loading successfully does not prove recovery works.

Rollback:

```sh
launchctl disable gui/501/dev.mise.dotfiles-dag-tick
launchctl bootout gui/501/dev.mise.dotfiles-dag-tick
```

Rollback prevents further scheduled execution and unloads the job. It does not reverse consumed verdicts or necessarily terminate detached recovery children. None of these mutating commands were executed.

## Verification and research coverage

| Specialist | Owned review | Repository gate |
|---|---|---|
| Python | Tick actions, handoff races, tests | **NOT RUN — review instruction** |
| Config | Plist, mise bootstrap, installation effects | **NOT RUN — review instruction** |
| Documentation | Recovery semantics and historical evidence | **NOT RUN — review instruction** |

Read-only verification confirmed clean `main`, #1644 ancestry, Claude **2.1.289**, mise **2026.10.1**, and current vendor documentation. Relevant commands exited **0**, except the expected absent-service probe above.

**RESEARCH INCOMPLETE:** prescribed strict-five fanout exited **1**. Its final manifest recorded:

| Route | Result |
|---|---|
| GitHub issues/releases | Query-empty, verified; direct release retrieval additionally succeeded |
| GitHub Discussions | `empty_unverified`: **“canary returned 0 items”** |
| Exa | Successful, 10 items |
| Context7 | Successful, 5 items |
| Firecrawl developer | Successful, 10 items |
| Firecrawl search | **“exited 1: Error: Request failed with status code 402”** |
| Last30Days | Successful retry, 9 items |

Direct GitHub GraphQL confirmed Discussions are disabled on `anthropics/claude-code`; this explains the empty result but does not convert the failed strict receipt into a pass. Last30Days initially rejected an invalid planned source; correcting it allowed retrieval. All eight raw-file SHA256 values matched the final [manifest](/Users/rmanaloto/.codex/research-coverage/01a106ef-a727-7041-8271-f01d035199a8/01a106ef-b297-7802-95c0-f55f412a5286/manifest.json).

Actually used: `codex-sdlc-team` routing skill; Last30Days plugin script; Exa and Firecrawl APIs; native `fnox`, `mise`, `uv`, `gh`, `ctx7`, `firecrawl`, `curl`, Git, Python, read-only `launchctl`, and Claude version/help. No app connectors ran. Corrected supporting probe failures included a nonexistent mise path (**127**), missing stale-clone source (**2**), and malformed GitHub invocations (**1**).

## GitHub repos touched

- `ray-manaloto/dotfiles` — source/history, #1644 metadata and controlled code searches.
- `jdx/mise` — installed-version launchd/bootstrap/run source.
- `anthropics/claude-code` — provider searches, issues, releases and Discussions availability.
- `mrkhachaturov/agent-harness-docs` — existing local documentation mirror only.

No others were spawned.

