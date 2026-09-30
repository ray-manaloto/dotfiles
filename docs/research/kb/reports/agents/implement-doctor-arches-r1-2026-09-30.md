# implementer (Opus fallback) — doctor devcontainer arches, round 1 (2026-09-30)

Spec: `docs/specs/doctor-devcontainer-arches-r1.md`. Branch `feat/doctor-devcontainer-arches` at HEAD `7cb15346`;
no commit (COMMIT: caller). Status: DONE — every gate rc=0 and every spec behaviour implemented; TWO DISSENTS on verification probes (arm 4's command, arm 5's probe), each with a substitute arm that passes.

## Pre-implementation probes

- **A1 (timing), answered.** Both `mise env --json` and `mise -E arm64 env --json` take `real 0.07` s, rc=0, on
  mise 2026.9.18.
- **P7 re-probed; my first probe was broken.** A zsh loop `mise $e env` with `e="-E arm64"` returned
  `linux/amd64/v2 26233`. zsh does not word-split `$e`, so mise got one argument, `-E arm64`. The cross-check
  through the absolute binary `/Users/rmanaloto/.local/bin/mise` returned `linux/arm64/v8` with a blank port on
  three routes: `-E arm64 env`, `MISE_ENV=arm64 env` and `env -E arm64`. P7 holds.
  - Side fact: an env name mise does not recognise silently resolves the DEFAULT profile, which is exactly what
    the A3 assertion catches.
- **The ambient env leaks into `mise env`.** `mise.toml` templates `DOTFILES_PLATFORM` from
  `env.DOTFILES_PLATFORM`, so the child's default resolution follows whatever the parent process carries.
  - Under `MISE_ENV=arm64 mise run doctor`, the parent carries `linux/arm64/v8` plus `MISE_ENV`, and a plain
    `mise env` child would then call arm64 the default.
  - Design consequence: the doctor's mise child env drops `MISE_ENV`, `DOTFILES_PLATFORM` and
    `DEVCONTAINER_SSH_PORT`, so it gets a config-only answer, which is what a fresh shell resolves.
  - Control: `env -u DOTFILES_PLATFORM -u DEVCONTAINER_SSH_PORT mise env --json` returns `linux/amd64/v2 26233`
    (the same as ambient, as expected), and `-E arm64` returns `linux/arm64/v8` with a blank port.

## DISSENT — spec §5 arm 5 cannot pass: `mise settings get auto_env` cannot see `.miserc.toml`

The tracked `.miserc.toml` (`auto_env = false`, byte-exact per spec §3 I) IS read and honored. The probe the spec
names cannot see it.

Scratch probe (mise 2026.9.18, absolute binary). The probe dir holds a `mise.toml` plus a `mise.macos-arm64.toml`
platform file that sets `PROBE_PLAT`:

| # | condition | platform file loaded? | `mise settings get auto_env` |
|---|---|---|---|
| 1 | no `.miserc.toml` | null | — |
| 2 | `.miserc.toml` `auto_env = true` | **loaded** | `Setting [auto_env] is not set` |
| 3 | `.miserc.toml` `auto_env = false` | null | `Setting [auto_env] is not set` |
| 4 | `MISE_AUTO_ENV=true` with `.miserc.toml` set to false | loaded (the env var beats `.miserc`) | — |
| 5 | `MISE_AUTO_ENV=true` | — | `true` |

`settings get` reports "not set" even in row 2, where the setting is TRUE and in effect. It only sees the env-var
route (row 5). So it is blind to `.miserc.toml`, and the spec's arm 5 would fail however correct the file is.

**The substitute arm, run in the REPO itself.** An untracked throwaway `mise.macos-arm64.toml` sat in the root
for seconds and was then deleted:

| repo condition | `PROBE_PLAT_R1` |
|---|---|
| tracked `.miserc.toml` (`auto_env = false`) | null |
| the same file with the value flipped to `true` | **loaded** |
| no `.miserc.toml` (control) | null |

Afterwards the file was restored byte-identical (`cmp`), and the probe file is gone.

The same result holds from scratch with a byte-identical copy of the repo file: `false` gives null, and the `true`
variant loads. So the file is discovered in the repo and its value decides platform-env loading. Today `false`
equals the unset default, as the control shows; the pin only starts to matter at 2026.12.0 (warning) and
2027.6.0 (flip).

Trace logging (`MISE_LOG_LEVEL=trace`) never mentions miserc, either in the repo or in `/tmp`, so it cannot
discriminate.

## Implementation

**A1 — `mise.arm64.toml`**, created and staged with `git add`, byte-exact to spec §3.

**A2 — `platform_target.py`.**
- New `_ARCH_PROFILE_RE` `mise\.([a-z0-9_]+)\.toml`, plus a public `arch_profile(rel_path)` that returns the
  arch only when it is in `PUBLISHED_ARCHES`.
- `find_violations` skips a literal in a profile only when its `platform_arch` equals the profile's arch.
  Otherwise it emits a `PlatformLiteral` whose new `expected_arch` field makes `render()` name the file, the
  literal and the expected arch.
- `DEFAULT_LITERAL_SITES` and `find_default_drift` are untouched.
- The module docstring gains a paragraph on this class.
- Real tree: `dotfiles-setup platform-literals` rc=0 with `mise.arm64.toml` staged.

**A3/B, C–G — `doctor.py`.**
- `MiseResolution(platform, arch, ssh_port)` and `MiseEnvError`.
- `mise_env_resolution(repo_root, environ, mise_env=None)`:
  - Runs `mise [-E <arch>] env --json` with `cwd=repo_root`, `timeout=20`, `check=False`, `stdin=DEVNULL`.
  - The child env drops `MISE_ENV`, `DOTFILES_PLATFORM` and `DEVCONTAINER_SSH_PORT` (see the pre-implementation
    probes).
  - Every failure raises: timeout, missing binary, `OSError`, rc≠0 (first stderr line), bad JSON, a non-object,
    or an unrecognised platform.
- `host_system()` is a seam over `platform.system()`. The check returns `[]` unless the host is `Darwin`.
- `is_linked_worktree` gets `timeout=10`; `OSError`/`TimeoutExpired`/rc≠0 give `False`.
- `_configured_arches` handles F. Entries must be strings that normalize via `platform_arch` and are distinct
  AFTER normalization, so `x86_64` + `amd64` is a duplicate. Violations give one finding listing the bad
  entries, and no calls are made.
- `_profile_phase` handles A3.
  - For each configured arch other than the mise default, it runs `mise -E <arch>` and asserts two things: the
    arch matches, and the port does not collide (both ports non-empty and equal).
  - An arch whose run fails is excluded from the docker query and its error collected. At the end, one
    `UNVERIFIABLE — mise env failed (…)` finding is appended.
  - If the DEFAULT resolution fails, the check returns that single finding: no restore command is knowable.
- `_container_phase` handles E. A docker failure appends one UNVERIFIABLE finding and stops, keeping the
  earlier definite findings.
- `docker_container_rows` handles G, with one message per cause:
  - timeout: `docker ps did not answer within 10 s`
  - missing binary: `docker CLI not found on PATH`
  - any other `OSError`: `docker could not run: …`
  - rc≠0: `docker ps failed: <first line>; is Docker Desktop running and the context right?`
  - unparsable output: `unparsable docker ps line: <line>`
- The check was split into phase helpers to stay under C901, with no suppression.

**I — `.miserc.toml`**, created and staged, byte-exact.

**`doctor.toml`**: the comment now says "for every clone of this repo", that arm64 goes through the tracked
`mise.arm64.toml`, that the profile is asserted, and that the check runs on the macOS host only.

**`mise.local.toml.example`**: the arm64 paragraph is replaced. The profile is tracked; `mise.arm64.local.toml`
is only for per-clone overrides, e.g. a stable arm64 port. The example no longer shows a platform line.

**Tests.**
- `tests/test_platform_target.py`: +6 tests (7 cases):
  - the tracked profile names only arm64;
  - a profile's own arch passes (the control);
  - an amd64 literal in `mise.arm64.toml` fails, and its render names the file, literal and arch;
  - `mise.riscv.toml` and `mise.local.toml` are scanned as plain sites;
  - a profile does not join default-agreement.
- `tests/test_doctor.py`: the devcontainers section is rewritten. Every seam is injected: docker, mise, git
  worktree and host system. No real docker or mise runs.
  - States: `created`, `paused`, `dead` and `restarting` each give a finding.
  - The default arch comes from mise, not the process env. With an arm64 default, amd64 is the profile checked.
  - A wrong-arch profile gives both findings. A 4-way parametrized test covers port collision.
  - A failed default resolution gives one finding and no docker call. A failed profile skips only that arch.
  - A down daemon keeps earlier findings and stops further queries.
  - An unconfigured baseline (3 shapes) and unusable entries (4 shapes) make no calls. An alias normalizes.
  - Silent in a worktree, and silent off macOS (3 systems).
  - `--filter` pairing is asserted per label. Six docker cause messages are checked exactly.
  - The mise argv, cwd, timeout, stdin and stripped env are asserted, plus 7 mise failure shapes.
  - The real-git worktree test is isolated with `GIT_CONFIG_GLOBAL` → a nonexistent file and
    `GIT_CONFIG_NOSYSTEM=1`. Git missing or hung gives `False`, and `timeout=10` is asserted.
- Targeted run: ruff rc=0, ty rc=0, `pytest tests/test_doctor.py tests/test_platform_target.py` rc=0, 238 passed.
- `ruff check --select ISC004 --fix --unsafe-fixes` was used on tests only to parenthesize implicit string
  concatenations. It is a pure syntax wrap; the diff was reviewed.

## Mutation arms

Run: `pytest tests/test_doctor.py tests/test_platform_target.py`. Each mutation was restored by `cp` from a byte
copy; the final `cmp` shows both files identical, and the re-run gave rc=0 with 238 passed.

| mutation (realistic regression) | rc | caught by |
|---|---|---|
| M1 delete the macOS host gate | 1 | `…is_silent_off_the_macos_host[Linux,Windows,'']` |
| M2 `if profile.arch != arch:` → `if False:` | 1 | `…a_profile_resolving_the_wrong_arch_is_named` |
| M3 on a docker failure, `return [unverifiable]` (discarding earlier findings) | 1 | `…a_down_daemon_keeps_earlier_findings` |
| M4 catch only `CalledProcessError` in `is_linked_worktree` | 1 | `…fails_open_to_checking[git-missing,git-hung]` |
| M5 `child_env = dict(environ)` (the ambient leak) | 1 | `…asks_mise_from_config_alone[None,arm64]` |
| M6 accept any published arch in a profile | 1 | `test_an_arch_profile_naming_another_arch_is_caught` |
| M7 `profile = None` (no profile class) | 1 | the real-tree `test_repo_tree_has_no_stray_literals`, the CLI real-tree test, and 2 profile tests |
| M8 drop the CHECKS registration | 1 | `test_every_check_function_is_actually_registered` |

## Live arms (spec §5)

The amd64 container was never stopped or touched. The only exec into it was the doctor run in arm 4; see its note
on container-home writes.

1. **Resolution with and without the local profile (PASS).** Command: `mise -E arm64 env --json | jq`, absolute
   binary.
   - `mise.arm64.local.toml` present: `linux/arm64/v8`, blank port, rc=0.
   - The local file moved aside to the scratchpad, so only the tracked `mise.arm64.toml` is left:
     `linux/arm64/v8`, blank port, rc=0.
   - Controls: the default gives `linux/amd64/v2 26233`. With BOTH profile files aside, `-E arm64` falls back to
     `linux/amd64/v2 26233`, so it is the tracked file that carries arm 1b.
   - The local file was restored with `cp -p` (`cmp` identical). The tracked file was restored (`cmp` identical)
     and is still staged.
2. **Doctor with both containers up (PASS).**
   - `DOTFILES_AMBIENT_PATH="$PATH" mise -C . run doctor -- --verbose` returned rc=0 and printed
     `PASS  doctor[devcontainers]`.
   - Its 5 other DRIFT lines were already there and are unrelated: listing-budget, path-drift, graphify
     0.9.72≠0.9.65, the claude-code pin 2.1.284<2.1.285, and codex-schema.
   - **A1 timing (was UNVERIFIED):** `mise env` takes 0.07 s for the default and 0.09 s for `-E arm64`. The whole
     `check_devcontainers_running` on the real host takes 0.43 s, and the doctor's wall time is 3 s.
3. **FAIL arm for A3 (PASS, with a nuance).** `mise.arm64.toml` was temporarily set to the amd64 triple.
   - (3a) With the operator's `mise.arm64.local.toml` PRESENT, the doctor prints no devcontainers line. That is
     CORRECT: the local override wins over the tracked profile, so `MISE_ENV=arm64` really does still resolve
     arm64, and the doctor reports the resolved value, not the file.
   - (3b) With the local file moved aside, the doctor returned rc=0 and printed
     `DRIFT doctor[devcontainers]: devcontainers: \`MISE_ENV=arm64\` resolves DOTFILES_PLATFORM=linux/amd64/v2, so \`MISE_ENV=arm64 mise run up\` would bring up amd64; check mise.arm64.toml`.
   - `platform-literals` returned rc=1 with
     `mise.arm64.toml:6: platform literal 'linux/amd64/v2' in the arm64 arch profile — it may only name linux/arm64, the arch its MISE_ENV selects`.
   - Restore: the profile, the local file and the staged blob are all byte-identical (`cmp`, and
     `git show :mise.arm64.toml | cmp`). Post-restore, the doctor has no devcontainers line and
     `platform-literals` returns rc=0.
   - Moving the local file aside a second time goes beyond the letter of the brief, which named it for arm 1. It
     was the only way to make 3b discriminate, and the file was restored the same way.
   - Minor: the `platform-literals` SUMMARY line still says "outside the permitted defaults"; the per-line render
     is the specific one.
4. **FAIL arm for C, inside the amd64 container (PASS once adapted — DISSENT on the command).**
   - The command as the spec wrote it, `docker exec <amd64> bash -lc 'cd /workspaces/dotfiles && mise run doctor
     -- --verbose'`, returned **RC=1: `mise ERROR no task doctor found`**. The container's mise (2026.9.8,
     `MISE_ENV=runtime`) does not load the workspace `mise.toml` tasks; it lists only `setup:*`/`update:*`.
   - The spec's criterion, "no devcontainers line", would have been vacuously true on that failed run.
   - Adapted to the task's own body, `uv run --project python dotfiles-setup doctor --verbose`: RC=0, with
     `PASS  doctor[devcontainers]` among 8 in-container DRIFT lines that are pre-existing and container-shaped.
   - **Control (the gate is the cause):** the same in-container Python with `host_system` forced to `Darwin`
     returns `['devcontainers: UNVERIFIABLE — docker CLI not found on PATH']`. That also shows fix G's
     cause-specific text live.
   - Safety, checked first: in the container `UV_PROJECT_ENVIRONMENT=/home/rmanaloto/.venvs/dotfiles-python`
     (container home), not the bind-mounted `python/.venv`. Host `git status` is unchanged and `uv.lock` passes
     its `shasum` check.
   - This exec may have synced the container-home venv; the repo and the host were not written.
5. **auto_env pin — DISSENT (above).**
   - The literal spec probe `mise settings get auto_env` says "not set" both in the repo and in `/tmp`. It cannot
     see `.miserc.toml` at all.
   - The substitute in-repo arm (false → null, flipped true → loaded, no file → null) proves the tracked file is
     read and decides platform-env loading.

## Full gates (`mise run gate -- run …`; rc taken from `.agent/gate-results/*.json`)

| gate | rc | evidence |
|---|---|---|
| lint | 0 | `status: passed`, 21.5 s. `✔` for ruff, ruff_format, py_ty, no_lint_skip, no_platform_literals, pin_parity, mise_lock_integrity and taplo |
| pytest | 0 | `4345 passed, 11 deselected in 316.23s`, against 4306 in round 0 |
| verify | 0 | `166 passed, 0 failed, 4 skipped`. The skips are the 4 standing human-only `policy.*` suites |

## End state

- Both containers are running. amd64 was never stopped.
- The operator's `mise.arm64.local.toml` is byte-identical to its pre-arm copy.
- Staged, both new: `.miserc.toml` (+4) and `mise.arm64.toml` (+7).
- Unstaged: `doctor.toml` +8/−4; `mise.local.toml.example` +10/−7; `python/src/dotfiles_setup/doctor.py` +253/−58; `python/src/dotfiles_setup/platform_target.py` +37/−1; `tests/test_doctor.py` +461/−98; `tests/test_platform_target.py` +66/−0.
- Every file is inside the §2 allowlist. Nothing was committed.

## Dissents and judgement calls, for the architect

1. **Arm 5's probe is blind** (DISSENT). `mise settings get auto_env` cannot see `.miserc.toml`. Replace it with
   the in-repo platform-file arm above; that arm ran and passed.
2. **Arm 4's command fails in the container** (DISSENT). `mise run doctor` is not a task there (rc=1). Use
   `uv run --project python dotfiles-setup doctor --verbose`, which ran and passed, with a control. Worth knowing
   generally: the workspace `mise.toml` tasks do not load inside the devcontainer.
3. **Arm 3 depends on the operator's local override.** With `mise.arm64.local.toml` present, a broken tracked
   profile is masked, correctly. The doctor asserts what `MISE_ENV=arm64` RESOLVES to, not what the tracked file
   says; the `platform-literals` gate is the check on the file itself.
4. **The ambient env is stripped from the mise child.** `MISE_ENV`, `DOTFILES_PLATFORM` and
   `DEVCONTAINER_SSH_PORT` are dropped so the answer comes from config alone. The spec did not name the child env.
   Without this, `mise.toml`'s `env.DOTFILES_PLATFORM` template makes the "default" follow the parent process.
   Pinned by a test and by mutation M5.
5. **Profile failures skip that arch's docker query.** A `mise -E <arch>` failure removes that arch from the
   docker query, since its restore command is unknown. A DEFAULT-resolution failure returns one finding and
   queries nothing.
6. **A wrong-arch profile still gets its container queried.** When the profile resolves the wrong arch, the
   container is still checked, and its restore hint sits beside the resolves-to finding.
7. **The duplicate check runs after alias normalization,** so `["x86_64", "amd64"]` is a duplicate. Aliases are
   accepted and normalized, so `aarch64` becomes `arm64`.
8. **Out of scope, as the spec says:** cold #3 (a worktree deriving the main checkout's label) and cold #13
   (`sync.container_state` ignoring the rc) are the architect's tickets.
9. **Minor:** the `platform-literals` summary line still reads "outside the permitted defaults" for a profile
   violation. The per-literal line is specific.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — read the offline copy under `knowledge-base/sources/mise`
  (`settings.toml` `[auto_env]`, `docs/configuration/environments.md` §Rollout) to confirm the `.miserc.toml`
  format and that `auto_env` is an early-init rc setting.
