# Premise re-verify — land-smoke round 2 @10e2a180 (premise-verifier, verbatim)

PREMISE REPORT (re-verify, round 2) — spec `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/land-smoke-timeout/docs/specs/land-smoke-timeout-round2-2026-10-04.md` @10e2a180. Scope: §3a design pins, rows P7/P9/P10/P11, and the narrowed allowlist. This lane is read-only and wrote no files, so you need to persist this report.

**Verdict: correct the spec first.** The design pins close M1–M7, but stale wording in §3 and §4 contradicts them. That wording is cheap to fix, and one part of it is load-bearing: §4:91-92 still defines the reap by command line.

ROWS: 4 checked — 3 CONFIRMED (0 provenance corrected) / 0 REFUTED / 0 UNVERIFIABLE / 1 ASSUMED (0 checkable)
- **P7 — ASSUMED.** The base is `ubuntu:26.04` (`.devcontainer/Dockerfile:14`), and nothing in `.devcontainer/` declares coreutils (round-1 grep). Settling it needs the in-image `timeout --version` probe; reading the repo cannot settle it. See N1 for the evidence gap in how P7 is pinned.
- **P9 — CONFIRMED.**
  - `host_lock.py:171-179`: `_try_lock` fails on the new file handle, then `inherited == _holder_pid(record)` and the call does `yield None`.
  - `:186-187` sets the holder env to `os.getpid()`. So a nested `held()` in the same pid gets `None`.
  - Grep: the only caller of `_run_smoke` is `container.py:224`, so the new keyword-only `lock_fd` breaks no other caller.
- **P10 — CONFIRMED.**
  - `scripts/devcontainer-smoke.sh` ends at line 166 (`echo "[devcontainer-smoke][end]"`).
  - Its budget is `bash_budget.py:92-97` `BashAllowance(166, …)`.
- **P11 — CONFIRMED.**
  - The fake's `exec` branch is at `tests/test_container.py:256-276`. Every exec writes the lock probe and, in timeout mode, `time.sleep(5)` (`:272`).
  - The recorder at `:354` matches every `["docker","exec"]`, and `:363` asserts `observed == [1800.0]`.
  - Under the new formula with the default T: kill_after=30, grace=60, so the host timeout is 1890. The pre-flight and reap execs also match `:354`, so retarget the assertion to the smoke exec only.

**M1–M7 status**
- **M1 — RESOLVED** (spec:72-74). The code to change is `container.py:159-166`, which currently appends `stale base? mise run dev-rebuild` for any non-zero rc.
- **M2 — RESOLVED** (spec:52-57; see P9).
  - The existing contention test `test_container.py:379-429` still fits: its child re-enters, gets `None`, so `pass_fds=()`.
  - The F8 fd-held test must therefore run without an outer holder. Otherwise the mutation cannot show up.
- **M3 — RESOLVED** (spec:34-35; P10).
- **M4 — STILL OPEN (contradiction).**
  - §3a:58-60 pins a marker-only reap (`DOTFILES_SMOKE_RUN_ID` in `/proc/<pid>/environ`).
  - §4:91-92 still says "Kill only processes whose command line is the smoke script or its descendants" — the original M4 defect.
  - §4:88-90 and §3a:59 also define the pre-flight match differently: "smoke or pytest whose parent chain is the smoke" against "any process running `devcontainer-smoke.sh`".
  - Nothing says §3a wins. This is load-bearing: a lane that follows §4 reintroduces killing processes it did not start.
  - The marker holds as far as I can see: `devcontainer-smoke.sh` contains no `env -i`, `setsid`, `nohup` or `timeout` (grep returned 0; the control `tier|pytest` returned 22). Descendants deeper than the script that scrub env were not checked.
- **M5 — RESOLVED** (spec:56-57). The slot sits in `verify_latest` around the whole `_run_smoke`, so the probe and the reap run under it.
- **M6 — RESOLVED with a caveat (N4).**
- **M7 — RESOLVED.**
  - grace ≥ 2 means host = T + kill_after + grace is always more than T + kill_after.
  - For T ≤ 10 the host timeout is T+3 (T=0.1 gives 3.1; T=2 gives 5). For T=1800 it is 1890.

**New contradictions and issues the pins introduce**
- **N1 — P7 vs §3:45-48 and the real-integration-evidence rule.**
  - §3 requires verifying in the image that `timeout` signals the whole process group, with a fallback to `setsid` plus a group kill.
  - §3a:75-77 downgrades that to "prove group kill with a test that the fake honours it" plus a version string.
  - A fake honouring group kill proves nothing about the real `timeout`, so that test only confirms itself. A version string does not show group-kill behaviour either.
  - Mitigation: the marker reap also runs on the rc 124/137 path (spec:73), which backstops it. Even so, the spec should either allow a harmless in-image arm (for example `timeout -k1 1 sh -c 'sleep 30 & sleep 30 & wait'`, then a `/proc` check) or state that in-image group kill stays unverified and the reap is the backstop.
- **N2 — where `HostLockTimeoutError` is caught is unpinned.**
  - Once the slot moves into `verify_latest`, the error is raised there. `sync._verify` (`sync.py:841-845`) has no `except`, so it would escape as a traceback.
  - `test_container.py:421-426` requires `smoke host heavy-slot wait timed out` and `fixture-holder` in the sync output, with no lock probe.
  - The spec should say that `verify_latest` catches it and returns a `smoke-tiers-1-3` Check. The fix fits in `container.py`, so the allowlist is fine.
- **N3 — test timing.**
  - The fake's fixed `time.sleep(5)` (`test_container.py:272`) must be longer than the host timeout to reach the host-`TimeoutExpired` path. At T ≥ 2 the host timeout is ≥ 5, so the race goes silent and the run exits normally.
  - Host-timeout tests cost at least T+3 s each, and four tests use it (`:296` ×3, `:366`).
  - The fake never runs `timeout`. The inner-timeout path needs the fake to emit rc 124/137, and the "delete the wrapper" mutation needs an assertion on the argv.
  - Covered by F1's ready-file handshake, but it should be stated.
- **N4 — `python3` on the image PATH is the mise shim, not `/usr/bin/python3`.**
  - `.devcontainer/mise-system.toml:217-219`: "the default `python3` here is the mise shim … use /usr/bin/python3".
  - `.config/mise/conf.d/shared.toml:43` sets `python = "3.14.7"`.
  - The shim adds mise config resolution and trust in the exec's workdir to the probe path.
  - Recommend pinning `/usr/bin/python3`. The final image has it according to that comment; the apt `python3` at `Dockerfile:444` is in the `clang-builder-cold` stage only.
  - The version probe should check whichever path the code uses.
- **N5 — rc 137 is ambiguous.** A smoke child that is OOM- or SIGKILL-ed returns 137 through `timeout` too, and would be reported as "timed out" with no rebuild hint. Name it as a residual, or tell them apart by elapsed time ≥ T.
- **N6 — which number goes in the message is ambiguous.**
  - The current host path formats `exc.timeout:g` (`container.py:153`), which would now print T+k+g (3.1 for T=0.1).
  - `test_container.py:315` asserts `after 0.1 seconds`.
  - The spec says `<T>` on the inner path, and "keeps its prefix" on the host path. Pin `<T>` on both.

**Allowlist (narrowed):** consistent. F3 and N2 both fit in `container.py`, and `sync._verify` only calls `verify_latest` (`sync.py:841`). `bash_budget.py` is correctly excluded because the script is not touched.

MISSING: N1–N6 above.

VERDICT: **correct the spec first.** Blocking:
- **M4 / §4:88-92** contradicts the §3a marker reap and pre-flight. Add "§3a overrides §3/§4", or rewrite §4:88-92.
- **N1:** reconcile how group kill is verified, P7 against §3:45-48.

Non-blocking residuals, each needs your accept-on-record:
- **P7:** an assumption the lane settles by the read-only probe, and it STOPs if `--kill-after` is missing.
- **N2:** the existing test at `:421-426` forces correct handling.
- **N3:** F1's handshake covers it.
- **N4:** a one-word path pin.
- **N5:** a rare misclassification.
- **N6:** the existing test at `:315` forces T.

Relevant files:
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/land-smoke-timeout/python/src/dotfiles_setup/container.py`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/land-smoke-timeout/python/src/dotfiles_setup/host_lock.py`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/land-smoke-timeout/python/src/dotfiles_setup/sync.py`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/land-smoke-timeout/tests/test_container.py`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/land-smoke-timeout/.devcontainer/mise-system.toml`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/land-smoke-timeout/scripts/devcontainer-smoke.sh`
