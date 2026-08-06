# Gemini (agy) cold review — #578 combined diff (b7dea52..67a3127)

- Date: 2026-08-05
- Commits: d04c8a7 (feat: launchd watchdog tick), 67a3127 (fix: respawn precondition pid-liveness only)
- Method: git object reads only (no working tree); inputs in review-input/; reviewer: agy-delegate --tier pro, agy 1.1.8
- Status: agy run COMPLETE (SUCCESS, 110340 tokens total). Reconciliation follows the verbatim output.

## agy output (verbatim)

### Section 1: FINDINGS DIGEST
critical | The respawned node inherits the minimal launchd PATH instead of the user's interactive shell PATH, breaking execution of background tools | python/src/dotfiles_setup/dag_tick.py:540
major | Stale-PID hazard: process liveness checks ignore the roster's procStart value, allowing PID reuse to falsely classify a dead node as alive | python/src/dotfiles_setup/dag_tick.py:362
major | Subprocess invocations lack exception handling for missing binaries, which crashes the tick with a FileNotFoundError | python/src/dotfiles_setup/dag_tick.py:413
major | `read_census` swallows non-zero exit codes and JSON decode errors, returning an empty list that silently masks fleet-wide failures | python/src/dotfiles_setup/dag_tick.py:438
major | The launchd plist configuration hardcodes the username `rmanaloto` in the PATH, breaking execution for any other user | mise.toml:1034
minor | The launchd plist configures stdout/stderr files without log rotation, leading to unbounded disk usage | mise.toml:1029
minor | TOCTOU race: `execute_stop` does not verify process liveness before running, potentially stopping a node that just exited naturally | python/src/dotfiles_setup/dag_tick.py:549
minor | `try_acquire_lock` uses `open("w")`, which unnecessarily truncates the file even when another process holds the flock | python/src/dotfiles_setup/dag_tick.py:396
minor | The `run_tick` orchestrator tests completely omit the end-to-end wiring for `ActionKind.STOP` and `ActionKind.LOG` | UNCITED

### Section 2: DETAILED FINDINGS

**The respawned node inherits the minimal launchd PATH instead of the user's interactive shell PATH, breaking execution of background tools**
Evidence:
```python
        env=strip_respawn_env(),
```
Why it is a defect: `strip_respawn_env` preserves the caller's `os.environ` (minus Claude-specific vars). Because the caller is a launchd agent with a severely restricted `PATH` (defined in `mise.toml` as `/Users/rmanaloto/.local/bin:/opt/homebrew/bin:/usr/bin:/bin`), the respawned node inherits this barebones PATH rather than a full user interactive environment.
Concrete failure scenario: `dag-tick` respawns a `DEAD` agent. When the agent attempts to run a background build using standard tools like `npm`, `cargo`, or `go` (typically installed in `~/.nvm` or `~/.cargo/bin`), the command fails entirely because those paths are missing from the launchd-inherited environment.

**Stale-PID hazard: process liveness checks ignore the roster's procStart value, allowing PID reuse to falsely classify a dead node as alive**
Evidence:
```python
    return pid_is_alive(entry.pid)
```
Why it is a defect: The `RosterWorker` correctly captures `procStart`, but the liveness check completely drops it, relying exclusively on `os.kill(pid, 0)`. On POSIX systems, PIDs are routinely recycled.
Concrete failure scenario: A background Claude node crashes, and the OS reassigns its PID to a newly launched, unrelated user application (e.g., a browser worker). The tick checks `os.kill(pid, 0)`, which succeeds. The node is falsely classified as `ALIVE` and is never respawned, permanently deadlocking the background work.

**Subprocess invocations lack exception handling for missing binaries, which crashes the tick with a FileNotFoundError**
Evidence:
```python
    result = subprocess.run(
        [claude_bin, "logs", bogus_id],
```
Why it is a defect: The `check=False` argument only prevents `CalledProcessError` on non-zero exits. If `claude_bin` does not exist on disk, `subprocess.run` (and `Popen`) raises a `FileNotFoundError`, which goes uncaught and crashes the script.
Concrete failure scenario: If the Claude binary is uninstalled or `DEFAULT_CLAUDE_BIN` points to a non-existent path on a fresh system, the launchd agent crashes with a Python traceback on every tick instead of gracefully degrading, violating the contract that every failure mode "degrades to 'do nothing this tick'".

**`read_census` swallows non-zero exit codes and JSON decode errors, returning an empty list that silently masks fleet-wide failures**
Evidence:
```python
    if result.returncode != 0:
        return []
```
Why it is a defect: It throws away the error evidence (like stderr output) and returns a success-shaped empty list. A failure to read the fleet is silently misinterpreted as an empty fleet. 
Concrete failure scenario: If the `claude agents` command repeatedly crashes or times out (e.g., due to a corrupted global configuration or missing dependencies), the watchdog silently processes 0 nodes and exits successfully. The user receives no logs or alerts, and all dead nodes remain dead indefinitely.

**The launchd plist configuration hardcodes the username `rmanaloto` in the PATH, breaking execution for any other user**
Evidence:
```toml
environment = { PATH = "/Users/rmanaloto/.local/bin:/opt/homebrew/bin:/usr/bin:/bin" }
```
Why it is a defect: Using an absolute path containing a specific username destroys portability across different developer machines and CI runners.
Concrete failure scenario: A collaborator named "alice" clones the dotfiles repo and runs `mise bootstrap macos launchd-agents apply`. The launchd agent fails to execute ticks because it looks for `uv` in `/Users/rmanaloto/.local/bin`, which does not exist on her filesystem.

**The launchd plist configures stdout/stderr files without log rotation, leading to unbounded disk usage**
Evidence:
```toml
stdout_path = "~/Library/Logs/dotfiles-dag-tick.log"
```
Why it is a defect: Launchd natively appends to stdout/stderr files indefinitely without providing any built-in log rotation mechanism.
Concrete failure scenario: Because the task fires every 60 seconds, these log files will continuously append text forever, eventually consuming gigabytes of disk space and becoming too large to open in standard text editors.

**TOCTOU race: `execute_stop` does not verify process liveness before running, potentially stopping a node that just exited naturally**
Evidence:
```python
    result = subprocess.run(
        [claude_bin, "stop", node_id],
```
Why it is a defect: There is a TOCTOU window between classifying the process as `DONE` with a lingering PID (during the roster read) and executing the stop command. It lacks the fresh PID re-check that `execute_respawn` implements.
Concrete failure scenario: A background node finishes its work and is classified as `DONE` with `pid_alive=True`. Moments before `execute_stop` actually runs, the process cleanly exits natively. `claude stop` is then unnecessarily invoked on a fully settled, dead session.

**`try_acquire_lock` uses `open("w")`, which unnecessarily truncates the file even when another process holds the flock**
Evidence:
```python
    handle = lock_path.open("w")
```
Why it is a defect: While `flock` correctly enforces mutual exclusion on the file descriptor, opening with `"w"` forces an immediate filesystem truncation before the lock is even requested. (Using `"a"` avoids this).
Concrete failure scenario: A user manually runs `mise run dag-tick` while the launchd background tick is active. The manual run successfully opens and truncates the lockfile, mutating the file structure out from under the active tick before correctly blocking on the lock.

**The `run_tick` orchestrator tests completely omit the end-to-end wiring for `ActionKind.STOP` and `ActionKind.LOG`**
Evidence:
```python
# UNCITED (No test verifies run_tick processing a DONE node with pid_alive=True)
```
Why it is a defect: The test suite verifies the `RESPAWN` logic end-to-end through `run_tick` (via `test_run_tick_respawns_a_dead_node`), but fails to verify that `run_tick` actually executes `STOP` or logs `WEDGED` nodes via `_execute_or_preview`.
Concrete failure scenario: A future refactoring accidentally drops the `STOP` handling branch inside `_execute_or_preview`. The unit tests for `execute_stop` will still pass, but the orchestrator will silently leak lingering processes in production without failing any CI gates.

## agy run metadata

```
AGY_USAGE {"status": "SUCCESS", "error": "", "usage": {"input": 83485, "output": 26855, "thinking": 24889, "cache_read": 0, "total": 110340}, "conversation_id": "a4691292-6b08-49f8-a0bc-8a95893ee0db"}
```

## Reconciliation (Claude, final judge — each finding corroborated against the 67a3127 blobs)

| # | agy severity | verdict | reconciled severity | evidence |
|---|---|---|---|---|
| 1 | critical | CONFIRMED, severity reduced | major | `execute_respawn` passes `strip_respawn_env()` (= launchd-agent `os.environ` minus denylist) at dag_tick.py:540; the launchd env is the minimal `PATH` at mise.toml:1034 (no mise shims, no interactive activation). A watchdog-respawned node runs in a poorer env than one spawned from a terminal. Not critical: `~/.local/bin` (mise, claude) and homebrew ARE present, and the config self-declares host-personal. |
| 2 | major | CONFIRMED | major | `read_roster` captures `procStart` (dag_tick.py:332) but `background_pid_alive` uses only `pid_is_alive(entry.pid)` (:362). PID reuse ⇒ false ALIVE ⇒ node never respawned. Compounding: `pid_is_alive` returns True on `PermissionError` (:342-343), so a recycled PID owned by another user also reads alive. |
| 3 | major | CONFIRMED | major | `subprocess.run(..., check=False)` does not catch `FileNotFoundError` for a missing `claude_bin` (gate_preflight :413, first subprocess in the tick; also read_census :431, Popen :535, execute_stop :549). Contradicts run_tick's own "always returns 0 / every failure degrades to do-nothing" contract (:598-601). `DEFAULT_CLAUDE_BIN` (:96) is an unchecked personal path fallback. |
| 4 | major | CONFIRMED | major | read_census returns `[]` on rc!=0 (:437-438), JSONDecodeError (:441-442), and non-list (:443-444) with NO log line — contrast the gate!=on branch which `logger.warning`s (:612). A failed fleet read is output-indistinguishable from an empty fleet, forever. Docstring declares the degradation deliberate, but the zero-evidence swallow is the defect. |
| 5 | major | CONFIRMED, severity reduced | minor | mise.toml:1034 hardcodes `/Users/rmanaloto/...` in `environment.PATH`. Factually breaks any other user; however the adjacent comment (:1031-1033) documents launchd `environment` values are not ~-expanded (why it is literal) and the block is declared host-personal (dag_tick.py:92-96). Portability knowingly traded, not overlooked. |
| 6 | minor | CONFIRMED | minor | mise.toml:1029-1030 stdout/stderr logs with 60s cadence and no rotation; launchd appends unboundedly. Slow growth (quiet ticks print nothing) but unbounded. |
| 7 | minor | CONFIRMED | minor | execute_stop (:549) lacks the fresh liveness re-check execute_respawn performs (:533). Window = up to one tick. Consequence mild: a stop against an already-settled node produces a false "FAILED rc=…" log line or a harmless no-op. |
| 8 | minor | PARTIALLY REFUTED, downgraded | nit | `lock_path.open("w")` (:396) does truncate before flock — but nothing ever reads the lock file's contents and flock is inode-based, so the second opener's truncation cannot disturb the holder's lock. agy's "mutating the file out from under the active tick" scenario has no correctness consequence. `open("a")` would still be cleaner. |
| 9 | minor (UNCITED) | CONFIRMED, now cited | minor | run_tick-level tests cover lock-held (:591), gate-off (:611), dry-run (:641), respawn (:668) only. No test drives `_execute_or_preview`'s `ActionKind.STOP` branch (dag_tick.py:590) end-to-end — STOP is pinned only at the plan() level (test :195) and execute_stop unit level (:553/:563), so deleting the `elif` at :590 would pass the whole suite. Same for a run_tick-level WEDGED/LOG pass-through. |

Verdict: 8 of 9 findings real (1 partially refuted → nit). The load-bearing ones are #2 (PID-reuse false-ALIVE defeats the watchdog's core purpose), #3 (a missing binary crash-loops the launchd agent in direct contradiction of the module's own degradation contract), and #4 (a fleet-read failure is silently indistinguishable from an empty fleet).

## GitHub repos touched

_None._ (Review inputs were local git object reads only.)
