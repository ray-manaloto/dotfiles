# Cold review — `git diff 7f91ace..9963e03` (smoke gcc_latest oracle)

Verdict: **SHIP.** The oracle swap is correct in every context I could enumerate, the
wrong-answer direction fails loudly rather than silently, and the test carries a real
control arm. Three doc/contract nits below, none blocking.

## Evidence gathered

- `pytest tests/test_image_arch.py -q` → `18 passed`, rc=0 (log:
  `.../scratchpad/pytest-arch.log`).
- Live containers, both arms:
  `docker exec fd86dff59441 uname -m` → `aarch64` (label `dotfiles.arch=arm64`);
  `docker exec fac33605a214 uname -m` → `x86_64` (label `dotfiles.arch=amd64`);
  host `uname -m` → `arm64`.
  **This is the load-bearing fact:** an amd64 container under Rosetta on an arm64 Mac
  reports the *target* arch, not the host's. So inside a container, `os.uname()` answers
  "what architecture is this image", which is exactly the question `ships_gcc_latest`
  asks. The docstring's "emulation is invisible from inside" is the same fact read as a
  limitation; here it is the feature.
- Only caller of `image smoke-script --tier 3` is `scripts/devcontainer-smoke.sh:84`
  (grep over `.github/`, `mise.toml`, `.devcontainer/`, `scripts/`, `python/src/`), and
  that script runs *inside* the container being smoked (`mise.toml:402` `devcontainer
  exec`, and `devcontainer.json:223` `postCreateCommand`). There is no path where the
  tier-3 generator runs on one architecture and the emitted script on another.

## Two-caller agreement

The two `ships_gcc_latest` call sites now have a clean, non-overlapping split:

| site | oracle | context |
|---|---|---|
| `image.py:763` `ImageArch.for_platform` | the platform *argument* | runs OUTSIDE the target (CI `docker run` no-mount smoke, `build_smoke_docker_cmd`) — it must be told, it cannot look |
| `image.py:1973` `smoke_script_main` | `host_platform()` / `uname` | runs INSIDE the target — looking is strictly better than being told |

Contexts checked for disagreement:
- **CI native-runner smoke via `docker run`** — per-arch legs run on native runners
  (`_RUNNER_LABELS`), generator arch == image arch, and it goes through `for_platform`
  anyway. No disagreement.
- **In-container devcontainer smoke, native arm64** → `aarch64` → `arm64` →
  `gcc_latest=False`. Correct; this is the bug being fixed.
- **amd64 container under Rosetta on arm64 Mac** → `x86_64` → `amd64` →
  `gcc_latest=True`. Correct — verified above, not assumed.
- Sibling `is_emulated`/`_is_emulated` is untouched and still asks the platform, which is
  right: emulation genuinely is *not* answerable from inside, gcc-latest presence is.

## Silent failure analysis — none found

- A wrong `False` is **not** a silent skip. `image.py:497` else-branch asserts
  `test ! -e /opt/gcc-latest/bin/g++` and fails if the compiler is present. So the only
  way this change can be wrong (emitting `False` for an image that does ship it) fails
  loudly. The reflection block at `image.py:560` has no else, but presence is already
  settled at 497.
- `host_arch()` raises `ValueError` on an unrecognised `uname -m`; that propagates out of
  `smoke_script_main`, and `tier3_core="$(…)"` under `set -euo pipefail` aborts the
  smoke. Behaviour change vs. the old code (which would have quietly used the pin) — in
  the loud direction. Fine.
- Verification contract `build.image-architecture-integrity` still binds
  `"gcc_latest=ships_gcc_latest(platform)"`, which matches `image.py:763`. Unchanged by
  this diff.

## Findings

### 1. LOW — the contract's own prose misdescribes which call site is bound
`python/verification/suites.toml:379` says *"`ships_gcc_latest` is bound at the smoke's
call site"*, and the token at `:410` is `gcc_latest=ships_gcc_latest(platform)`. That
token matches `image.py:763` (`ImageArch.for_platform`), **not** the devcontainer smoke.
It was already inaccurate before this diff, but the diff widens the gap: the smoke's call
site is now `ships_gcc_latest(host_platform())`, which no token matches. Reverting
`image.py:1973` to the `gcc_latest=True` default — the exact #698 regression — leaves the
contract green. Cheapest fix: add
`"gcc_latest=ships_gcc_latest(host_platform())"` to the `image.py` token list, or correct
the sentence.

### 2. LOW — `host_platform()`'s docstring is now wrong at this call site
`platform_target.py:~/def host_platform`: *"This host's native triple (`linux/arm64/v8`
on an M-series Mac)"*. Called from inside an amd64 Rosetta container on that same Mac it
returns `linux/amd64/v2`. The name and docstring both say "host"; the new call site means
"this machine, whatever it is". Worth one clause ("…the machine this process runs on,
which inside a container is the container's architecture, emulated or not") — otherwise
the next reader reconciles the contradiction with the `smoke_script_main` docstring three
lines above (*"emulation is invisible from inside (`os.uname` can't tell)"*) by
"fixing" the derivation back to the pin.

### 3. LOW — the new comment states the fix but not the reason it is sound
`image.py:1962-1968` explains why `resolve_platform()` was wrong (the bind-mounted
`mise.local.toml` pin wins in-container) but never states the positive fact the fix rests
on: **under emulation `uname` reports the TARGET arch**. Without that sentence, the
adjacent "`os.uname` can't tell" makes the change look self-contradictory. One line.

### 4. INFO — the test patches the stdlib `os` module globally
`tests/test_image_arch.py:451` `monkeypatch.setattr(platform_target.os, "uname", …)` —
`platform_target.os` *is* the `os` module, so `os.uname` is faked process-wide for the
test's duration (monkeypatch reverts it, so no leakage). Harmless here; note it only
because a future test in the same file that depends on real `os.uname` would be affected
if the patch were hoisted to a fixture.

The control arm in that test is genuine and is the best part of the diff: pinning
`DOTFILES_PLATFORM` to the *opposite* platform means a generator that consulted the pin
emits the wrong flag and the test fails. Confirmed by construction — the two parametrised
cases assert opposite `GCC_LATEST_PRESENT` values.

## GitHub repos touched

_None._
