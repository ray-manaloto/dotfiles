# Cold review: `7ac2a7f3` (land smoke round 3)

- Reviewer: cold-reviewer (Opus). The review is diff-only. I edited no source file; this report is the only file I wrote in the repo.
- Subject: `git show 7ac2a7f3`. It touches `python/src/dotfiles_setup/container.py`, `tests/test_container.py`,
  `.claude/rules/persistence-gate-retry.md`, and `docs/specs/land-smoke-timeout-round3-2026-10-04.md`.
- I checked closure against `cold-review-land-smoke-r2-9241c174.md` (F1-F11).
- Probes I ran:
  - (a) An AST parse of the shipped `_SMOKE_PROCESSES_PROGRAM` via `/private/tmp/claude-r3-probe.py`.
  - (b) Direct calls to `_smoke_output` and `_smoke_process_error`.
  - (c) `0.9*3` float equality.
  - (d) After `pgrep -f devcontainer-smoke.sh` returned rc=1, a targeted run: `uv run --project python pytest tests/test_container.py -k "defpath or stderr_only or preflight or ninety or early_timeout or bounded_and_exclude or omits_command or preserves_stderr" -x -q -n 0`. Result: **37 passed, rc=0** (log `/private/tmp/claude-r3-pytest.log`).
  - I ran no docker, lint, verify or full suite.
- Status: COMPLETE (2026-10-04).

## Closure of round-2 findings

| # | Status | Evidence |
|---|---|---|
| F1 (HIGH) | **CLOSED (static). The in-container run is UNVERIFIED.** | `tests/test_container.py:218-219`: `shutil.which("git", path=os.defpath) or shutil.which("git")`. In the image, PATH git is `/usr/local/share/mise/shims/git`, per the coordinator probe the spec cites (spec lines 3-4). I checked the obvious in-container hazard: the fixture overrides `HOME` (`:215`) and puts a fake `mise` (exit 99) first on PATH (`:417-419`). It does not break the shim, because `MISE_DATA_DIR` and `MISE_SYSTEM_CONFIG_DIR` are pinned to `/usr/local/share/mise` by image ENV (`.devcontainer/Dockerfile:74-81`), not to `$HOME`. A symlink-mode mise shim also dispatches in-process by argv[0] basename `git`. The regression test `test_smoke_fixture_uses_path_when_defpath_has_no_git` (`:445-460`) monkeypatches `os.defpath` to an empty dir and asserts `which(defpath) is None` as its own control. Reverting to a defpath-only lookup errors at fixture setup, so it is a realistic fail arm, and the lane reports rc=1. The fixture was still never executed inside the devcontainer: the container mounts the main checkout, as round-2 noted. The first real smoke after merge is the true arm. |
| F2 (MEDIUM) | **CLOSED** | `container.py:269-273`: `timed_out=False` uses `(streams[0] + streams[1])` tail. Both non-timeout call sites pass it explicitly: the generic path at `:350` and the early-124/137 path at `:347`. Tests: `test_completed_failure_reports_stderr_only_cause` (`:463-472`) and the `("tier 2 starting", "mise Rust panic…")` row (`:807-811`). The lane reports the drop-stderr mutation gives rc=1. |
| F3 (LOW) | **CLOSED** | `container.py:311`, `:339-345`: `elapsed >= 0.9 * timeout`. Real inner timeouts fire at ≥T (124) or T+kill_after (137), so they always clear 0.9T. `test_inner_timeout_classification_at_ninety_percent` (`:745-770`) pins both sides with an injected clock (2.699 / 2.7). I verified `0.9*3 == 2.7` in IEEE float (`2.7 >= 0.9*3` True, `2.699 >= 0.9*3` False), so the boundary is real, not lucky. Removing the elapsed check fails the 2.699 cases. The rule text discloses the residual (≥0.9T child 124 / OOM / container stop). |
| F4 (LOW) | **CLOSED** (residual LOW, see N2) | `container.py:154-160`. **The NUL escaping is correct at runtime.** The program is a non-raw `"""…"""`, so the source text `b"\\0"` becomes `b"\0"` inside the program string. The AST of the shipped program contains the bytes constant `b'\x00'` and does **not** contain `b'\\0'` (two bytes). That second check is the control arm that would expose a raw-literal mistake. The real launch `timeout … scripts/devcontainer-smoke.sh` with shebang `#!/usr/bin/env bash` (`scripts/devcontainer-smoke.sh:1`) ends as argv `["bash","scripts/devcontainer-smoke.sh"]`, which matches. Seven mention-only negatives (`:707-726`) include `bash -c 'echo …'` and a basename lookalike; reverting to the substring match fails all seven. |
| F6 (LOW) | **CLOSED** (minor overclaim, see N3) | `container.py:200-208`: replace raw, `repr` and `json.dumps` forms **before** `strip()[:500]`. The ordering is right; the spec Result records that the strip-first order failed a test and was corrected. The `TimeoutExpired` branch builds its own message (`:243-251`), so argv and program never reach `str(exc)`. My probe: the whole program embedded in a message becomes `'[inline scanner] tail'`. |
| F10 (NIT) | **CLOSED** | `container.py:274-276`: completed failures read `smoke failed (no output)`. The test row is `("", "", "smoke failed (no output)")` (`:812`). |

## F7 / F11 acceptances

- **F7: sound.** Taking the slot before identity resolution is the round-1 F3 fix, which Q-FRESH requires. The cost is latency and visibility, not correctness, and the Result section discloses it.
- **F11: sound.** `:g` formatting at realistic T is exact. The stated hazard of fixed precision (a tiny allowed T rounding to `0s`, which `timeout` treats as "no timeout") is a real reason not to swap it in one line.

## New findings in 7ac2a7f3

| # | Severity | Claim | file:line | Failure scenario |
|---|---|---|---|---|
| N1 | LOW | `_smoke_output(..., timed_out=True)` defaults to timeout semantics. A future completed-failure call site that omits the kwarg silently reintroduces F2 (a stderr-only cause hidden) and the F10 wording. The only caller relying on the default is the host-timeout path (`:332`). | `container.py:257-258`, `:332` | Someone adds a new non-timeout return path, such as a preflight-after-exec retry, and copies the `:332` call shape. A mise panic on stderr disappears behind the stdout tail, and no test covers the new path. **Fix:** make `timed_out` a required keyword (no default), so every call site states it. |
| N2 | LOW | F4 matching misses an interpreter with options before the script (`bash -x scripts/devcontainer-smoke.sh`, `bash -e …`, `bash --noprofile …`), and non-bash/sh shells. Such a smoke is invisible to pre-flight, and a second smoke would launch beside it. | `container.py:157-159` | An operator debugs with `bash -x scripts/devcontainer-smoke.sh` in the container while `land` runs, and two suites run concurrently. No repo call site uses such a form today. The control-armed grep found only the direct invocation (`mise.toml:493`, `devcontainer.json:246`, `container.py:325`), and the rule text describes exactly argv[0]/argv[1], so this is a disclosed scope rather than a lie. **Option:** accept the first argv element after `bash`/`sh` that does not start with `-`. |
| N3 | LOW / UNVERIFIED | The rule claim "excludes the inline process-scanner program" holds only for exact whole-program echoes. A real in-container scanner crash produces a traceback. On Python ≥3.13 a `-c` traceback can include individual **source lines** of `<string>`, which no exact-match replacement removes. They stay bounded to 500 chars, so this is not a blow-up. The F6 tests emulate only whole-program echoes. | `container.py:200-208`; rule `persistence-gate-retry.md` (F6 sentence) | A PermissionError outside the handled set yields stderr containing `fd = os.pidfd_open(pid)` lines. This is harmless, but the "never echo" wording slightly overclaims. I did not measure the container's `/usr/bin/python3` version or its traceback format (docker forbidden). |
| N4 | NIT | The completed-path combined tail concatenates the streams with no separator. When stdout lacks a trailing newline, its last line fuses with stderr's first line (measured: `_smoke_output("noeol","err",timed_out=False)` → `'noeolerr'`). This is pre-round-2 behaviour restored, not new semantics. | `container.py:272` | Pytest progress dots without a newline, followed by a panic, render as `....mise panic…`. This is readable, but a fused line could theoretically hide a boundary. **Fix:** `"\n".join` the streams. |
| N5 | NIT | The new fixture default `SMOKE_INNER_DELAY = <T>` makes any future `inner*` test that forgets to override `DOTFILES_SMOKE_TIMEOUT_S` sleep the fixture's 30 s default. Every current inner test overrides it (I checked `:649,735,760,778,941,956,976,1014`). | `tests/test_container.py:398`, `:427` | This only costs suite time. |
| N6 | INFO | Early rc 124/137 (below 0.9T) is reported with no stale-base hint and with a reap. That is reasonable, because an OOM 137 or a child's own 124 is not a stale base. The behaviour is pinned by `test_early_timeout_like_exit_reports_rc_and_still_reaps` (`:729-742`). | `container.py:338-348` | — |

## Test fail-arm realism

- F1: the test reverts the lookup → fixture assertion error. This is a real regression shape, the exact round-2 bug, and it carries a built-in control (`which(defpath) is None`).
- F2: the test drops stderr on the completed path → the stderr-only assertion fails. Realistic.
- F3: the injected clock pins both sides of the boundary, and deleting the elapsed check fails it. The early-exit test uses the real clock with delay 0 and T=3, which gives ample margin.
- F4: there are 3 positives × 2 markers and 7 mention-only negatives. The negatives are what kill a substring regression.
- F6: raw, repr and json forms plus a long payload, through the public `verify_latest`; the TimeoutExpired path is driven via a `subprocess.run` wrapper. They are realistic for whole-program echoes (see N3 for the gap).

## Verdict

F1, F2, F3, F4, F6 and F10 are closed, and the F7 and F11 acceptances are sound. No new HIGH or MEDIUM defect was introduced. N1-N3 are LOW hardening items that can be fixed or ticketed. N1 is a one-line change (`timed_out` with no default), worth doing before merge if cheap. The remaining real-world uncertainty is F1 in-container, along with round-2's F9 real-signal arms. Only the first post-merge container smoke can retire that uncertainty, and it should be watched explicitly.

VERDICT: SHIP

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): the reviewed repository (local worktree, `git` and targeted pytest only).
