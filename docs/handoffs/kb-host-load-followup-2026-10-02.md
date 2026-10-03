# KB follow-up: host-load items 2 and 3 (heavy-gate lock, xdist cap)

Drafted 2026-10-02 by the dotfiles host-load lane (branch `fix/host-load`) for a
knowledge-base lane. Source review:
`docs/research/kb/reports/agents/host-load-review-2026-10-02.md`.

Not "trivially shareable": `kb_setup` is a SHA-pinned dependency of dotfiles, so
moving `host_lock` into `kb_setup` would need a KB PR first and a pin bump here.
What follows is a wire-compatible KB implementation, so the two repos serialise
against each other today without sharing code.

## 1. Heavy-gate lock in `kb_setup.gates` (the #838 class)

**Why.** `kb_setup/gates.py:277` runs `CONCURRENT_SAFE = {"lint", "test",
"brain-audit", "graph-size"}` concurrently, and nothing serialises a KB gate run
against a dotfiles one; the 2026-10-02 KB `test` went 57 s -> ~13 min and timed out
twice (#838) while a dotfiles ship ran.

**Contract (must match dotfiles `python/src/dotfiles_setup/host_lock.py`):**

| item | value |
|---|---|
| lock file | `${DOTFILES_LOCK_DIR:-${XDG_STATE_HOME:-~/.local/state}/dotfiles}/heavy-gate.lock` |
| primitive | `fcntl.flock(fd, LOCK_EX \| LOCK_NB)` polled each 1 s; open with `"a+"`, never `"w"` |
| holder record | file content `"<pid>\t<label>\t<UTC ISO since>\n"`, written after acquiring |
| re-entry | holder exports `DOTFILES_LOCK_HOLDER_HEAVY_GATE=<pid>`; a busy lock whose recorded pid equals the inherited value is re-entered |
| bound | `DOTFILES_HEAVY_GATE_WAIT` seconds (default 3600); expiry = a typed timeout, never a silent pass |
| notice | `==> waiting for heavy-gate lock held by pid N (label, since T) (up to Ss; path)`, reminder every 60 s |

**Where.** Take it ONCE around the whole `kb_setup.gates` run (the concurrent
`CONCURRENT_SAFE` batch is one heavy run, not four), and in the KB `test` task
when invoked directly. Do not take it per gate inside the batch: the batch's
workers are threads of ONE process, so under the re-entry rule a second thread
sees its own pid recorded and re-enters — then the thread that ACQUIRED it
releases the lock when it finishes, while the others still run (an early release, not a deadlock;
cold review 2026-10-02, finding 14). Also pass the locked descriptor to each gate
child (`pass_fds`) so a killed parent does not free the lock while its child
still runs (dotfiles `gate_result._run_declared`).

**Arms to reproduce (dotfiles measured all four, `tests/test_host_lock.py`):**
A holds, B prints "waiting … held by A" and runs after A releases; `kill -9` of
a holder with no child sharing the fd releases at once (a child handed the fd
via `pass_fds` keeps it held — armed both ways in dotfiles); a busy lock with a 0.3 s bound times out without
running the block; a child WITH the holder export re-enters (rc 0) while the same
child with it stripped times out (rc 124). Add one cross-repo arm: hold via
`dotfiles-setup heavy-gate run -- sleep 30` and show a KB gate run waits.

## 2. xdist worker cap in the KB `test` task

**Why.** KB `mise.toml` `[tasks.test]` runs `pytest tests/ -x -q -n auto`; xdist
3.8.0 without psutil resolves `auto` to `os.cpu_count()` = 12 on this host
(`xdist/plugin.py:16-55`), and graph tests each load the 756 MB `graph.json`.

**Change (same shape as dotfiles):** keep `-n auto`; add to `tests/conftest.py`

```python
DEFAULT_TEST_WORKERS = 4

@pytest.hookimpl(optionalhook=True)
def pytest_xdist_auto_num_workers(config: pytest.Config) -> int | None:
    _ = config
    if os.environ.get("PYTEST_XDIST_AUTO_NUM_WORKERS"):
        return None  # xdist's own impl reads the native knob
    return DEFAULT_TEST_WORKERS
```

and `--dist loadgroup` with `@pytest.mark.xdist_group(name="graph")` on the
`graph.json`-loading tests, so they share one worker. ONE knob, xdist's own
`PYTEST_XDIST_AUTO_NUM_WORKERS`; a clone raises it in `mise.local.toml [env]`.

**Arm:** `pytest --collect-only -q` is not enough — run the suite and read xdist's
`created: 4/4 workers` line with the variable unset, and `created: 8/8` with
`PYTEST_XDIST_AUTO_NUM_WORKERS=8` (the control). Mind the 25 m task bound in the
same block: fewer workers lengthens the run.

## 3. Also KB: SessionEnd scans

KB wires SessionEnd `brain-transcript-audit` + `kb-session-reflect` (both
`mise run`, timeout 60). Dotfiles removed its SessionEnd `command-audit` for the
same reason (seven concurrent ~814 MB scans, four orphaned past SessionEnd's 60 s
cap). Measure KB's chain count during a burst of session ends before deciding;
if they recur concurrently, give them a single-instance `flock` (dotfiles:
`host_lock.held(COMMAND_AUDIT, ..., wait_s=0)`) or take them off SessionEnd.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — `host_lock.py`, `tests/conftest.py`, `pytest.ini` (the reference implementation)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — `mise.toml [tasks.test]`, `python/src/kb_setup/gates.py:277`, #838
- [pytest-dev/pytest-xdist](https://github.com/pytest-dev/pytest-xdist) — 3.8.0 `plugin.py` `pytest_xdist_auto_num_workers`, `newhooks.py` firstresult hookspec
