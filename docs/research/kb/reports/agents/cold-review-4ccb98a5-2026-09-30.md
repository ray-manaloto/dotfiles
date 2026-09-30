# Cold review — 4ccb98a5 (round 2, bounded)

- **Subject:** `4ccb98a55e8ab53f4b26bcb8ad86e401ec5bdbff` ("feat(doctor): tracked arm64 profile, resolved-value assertion, auto_env pin").
- **Base:** `7cb15346f50a1ea75c2c5d62368c134f7152898f`.
- **Reviewer:** cold-reviewer, Claude Opus. This is a same-family fallback: the author family is Anthropic (Opus), and codex is unavailable until 2026-10-03. Read it as a degraded lens, not the full cross-family gate.
- **Memory:** consulted (`doctor_docker_restore_review.md`, `mutation_harness.md`, `shell_comment_continuation_review.md`).
- **Constraints honoured:** no container was stopped or started. The only docker calls were `docker ps` (read-only). `mise.arm64.local.toml` was never moved, and it was read only for its two non-secret keys. Every mise experiment that needed files ran in the scratchpad (a local clone, or synthetic projects). The real repo was only read, and `MISE_STATE_DIR` pointed at the scratchpad for every cache arm, so the operator's env cache and trust DB were untouched.
- **Status:** COMPLETE. This round is BOUNDED (exactly four questions), and all four are answered below.

## Domain (bounded: exactly 4 questions)

1. Does any path let the doctor's `mise env` resolution, or its docker query, read a broken state as healthy? Covered: mise missing, a timeout, rc≠0, bad JSON, an unknown `MISE_ENV` silently resolving the default, and an ambient `MISE_ENV`/`DOTFILES_PLATFORM` leak.
2. Is the printed restore command correct for amd64 and arm64 on a fresh clone with no local profiles?
3. Does the arch-profile class of the platform-literal gate accept exactly `mise.<arch>.toml` carrying its own arch, and reject everything else?
4. Is `.miserc.toml` `auto_env = false` actually honoured? (Scratch dir.)

## Verdict

**SHIP-WITH-FIXES.** One MEDIUM and four LOW findings are new; all are listed below. None makes a broken state read as HEALTHY today:

- Every mise-failure and docker-failure branch yields a visible UNVERIFIABLE, armed live.
- The profile assertion catches an unknown or missing profile.

The MEDIUM falsifies the check's own "answers from config alone" contract, nondeterministically. It changes which restore command the doctor prints and emits a spurious DRIFT line. The fix is one environment variable, and it is mise's documented switch.

## Findings

| # | Sev | Claim | file:line | Failure scenario | Evidence |
|---|---|---|---|---|---|
| 1 | **MEDIUM** | mise's **env cache defeats the ambient stripping**. `mise env --json` is served from `env_cache`, which is on by default, `mise.toml:161`. The cache key covers config paths+mtimes, tool versions, settings, base `PATH` and the mise version, but **not caller env values and not `MISE_ENV`**. So a `DOTFILES_PLATFORM` templated from the ambient value (`mise.toml:203`) and cached by an unstripped mise process comes back to the doctor's stripped child. The child inherits `__MISE_ENV_CACHE_KEY` (`doctor.py:422` uses `os.environ`; `:1525` strips only three names). Profile-less `-E amd64` / `-E <unknown>` share the default's config set, so they share its entry. | `python/src/dotfiles_setup/doctor.py:1525` (child env, no `MISE_ENV_CACHE=0`); seeders: `codex_schema.py:25-32` (`mise exec -- codex --version`, no `env=`/`cwd=`, called at `doctor.py:1326`, check #14 at `:1757`, before `devcontainers` #17 at `:1760`), and the SessionStart parent `mise -C … run doctor` itself | Trigger: an operator uses the DOCUMENTED shell-export override (`mise.toml:196` "or a shell export") `DOTFILES_PLATFORM=linux/arm64/v8` on any clone without a literal pin in `mise.local.toml` (every fresh clone). The SessionStart doctor then resolves the "default" as **arm64**. It prints ``devcontainers: `MISE_ENV=amd64` resolves DOTFILES_PLATFORM=linux/arm64/v8 … check mise.amd64.toml``, a DRIFT line naming a file that does not exist. It also gives arm64's restore as bare ``run `mise run up` ``. With the cache off, the same clone prints ``run `MISE_ENV=arm64 mise run up` `` and no DRIFT line. Which answer appears depends on cache state and check order, so it flips between sessions. It is masked on this host only because `mise.local.toml` pins amd64 literally. | **Mechanism, scratch (`q1c`, real 2026.9.18):** seed `PROBE_P=AMBIENT` with key K1 → `AMBIENT`; stripped with K1 → **`AMBIENT`**; stripped with no key → `DEFAULT`; stripped with `MISE_ENV_CACHE=0` → `DEFAULT`. **Real repo, committed module (`q1e`, `mise.local.toml` ignored, scratch state):** A, `codex-schema` first (CHECKS order), cache on → **`linux/arm64/v8`**; B, the same with `MISE_ENV_CACHE=0` → `linux/amd64/v2`; C, devcontainers first → `amd64`, then after the codex `mise exec` → still `amd64` (first writer wins). **`q1f`:** seeded → default/`-E amd64`/`-E zz-unknown` all `arm64`, `-E arm64` `arm64`; unseeded → `amd64`/`amd64`/`amd64`/`arm64`. **Genuine fresh clone, exact SessionStart shape (`mise -C <clone> run <task>` → `uv run … python` → the check, docker stubbed with arm64 absent):** the task sees `KEY-SET`; cache on → the spurious `mise.amd64.toml` finding plus ``run `mise run up` ``; cache off → ``run `MISE_ENV=arm64 mise run up` `` only. Upstream: `docs/cache-behavior.md:43-70` ("set `MISE_ENV_CACHE=0` … must recompute"), and `src/toolset/env_cache.rs:152-193` (key composition; offline corpus 2026.9.4, behaviour re-measured on 2026.9.18). No test can see it: every `mise_env_resolution` test stubs `subprocess.run` (`tests/test_doctor.py:1852-1928`). |
| 2 | LOW | `_MISE_AMBIENT_VARS` strips `MISE_ENV` but not its two live aliases, `MISE_PROFILE` and `MISE_ENVIRONMENT`. mise 2026.9.18 honours both as `MISE_ENV`. | `python/src/dotfiles_setup/doctor.py:1418-1422` (list), `:1525` (filter) | The doctor inherits `MISE_PROFILE=arm64`, a legacy spelling, e.g. from the shell Claude was launched from. The default resolves arm64, so a stopped arm64 container is reported with ``run `mise run up` ``. In a clean shell that command targets `linux/amd64/v2`: it re-ups the running amd64 container, and the finding repeats every session. This is exactly the failure the list's own comment says it prevents. | Scratch alias arm: `MISE_ENV`, `MISE_PROFILE` and `MISE_ENVIRONMENT=arm64` each load `mise.arm64.toml`; no variable → not loaded; bogus `MISE_ENV_NAME=arm64` → not loaded (the control). Live repo (`q1.py`): R6 (`MISE_ENV` + `DOTFILES_PLATFORM` + port) is stripped correctly → amd64; R7 `MISE_PROFILE` and R7b `MISE_ENVIRONMENT` → default **arm64**. `q1b.py` (docker stubbed, mise real): clean → ``MISE_ENV=arm64 mise run up``; each alias → ``mise run up``. In a clean shell, `mise env` → `linux/amd64/v2`. |
| 3 | LOW | The new arch-profile class compares only the **arch word**, so `mise.arm64.toml` may carry `linux/arm64`, `linux/aarch64`, `linux/arm64/v9` or `linux/aarch64/v2`, and `mise.amd64.toml` may carry `linux/x86_64/v3` or `linux/x64`. That re-admits the "dropped level" split-brain the module says the gate exists to catch (`platform_target.py:134-136`). The doctor's profile assertion also compares only the arch (`doctor.py:1635`), so both gates pass such a file. | `python/src/dotfiles_setup/platform_target.py:603`; `python/src/dotfiles_setup/doctor.py:1635` | Someone writes mise's own os-filter spelling, `DOTFILES_PLATFORM = "linux/arm64"`, into `mise.arm64.toml`. lint, pytest and the doctor all stay green. On a host whose local `:dev` lacks the arm64 platform, `MISE_ENV=arm64 mise run sync` then fails with `'linux/arm64' is not a published platform; refresh cannot target it` (`sync.py:689-694` matches the exact published triple). `mise run up` still works (it needs only the arch), so the doctor's restore stays correct; the damage is downstream. | `q3.py`, committed `find_violations` over 27 one-file scratch repos: `linux/arm64`, `linux/aarch64`, `linux/arm64/v9` and `linux/aarch64/v2` are ACCEPTED in `mise.arm64.toml`; `linux/x86_64/v3` and `linux/x64` are ACCEPTED in `mise.amd64.toml`; wrong-arch literals are REJECTED. `q3b.py`: `published_targets()` = `['linux/amd64/v2','linux/arm64/v8']`, and all four accepted arm64 variants except `/v8` are `in published_targets = False`. Control: the real tree → `[]`. The spec (§3 A2) asked for arch equality, so the enumeration is the gap, not the implementation. Fix: compare against the arch's published triple. |
| 4 | LOW | The project `.miserc.toml` pin is **not read under `mise -C <repo>`** when the process cwd is outside the repo. mise discovers early-init `miserc` from the PROCESS cwd, not the `-C` target. On that route a global `auto_env = true` (or the 2027.6.0 default) wins, and it is the route SessionStart uses. | `.miserc.toml:4`; the consumer route `mise -C "${CLAUDE_PROJECT_DIR}" run …` at `.claude/settings.json:129`, `:140` and `.codex/hooks.json:41`, `:52` | Latent today. No platform-env file exists: `git ls-files` shows only `mise.arm64.toml` and `.miserc.toml`, and `~/.config/mise` has no `config.{unix,macos,macos-arm64}.toml`, so nothing extra loads. The pin fails the day such a file appears under mise ≥ 2027.6.0 or a global `auto_env = true`: SessionStart's `mise -C` runs load it while in-repo `mise run` does not, which is the host split-brain the pin exists to prevent. | `q4.py` (absolute binary, isolated `MISE_CONFIG_DIR`/`MISE_STATE_DIR`; platform files `mise.{unix,macos,macos-arm64}.toml` plus a bare `mise.arm64.toml`). **B** `.miserc` true, cwd=proj → loaded (the file is read). **I** the SAME file under `mise -C proj` from outside → NOT loaded. **E** the repo's bytes plus global miserc true, cwd=proj → not loaded (the pin wins). **J** the same pair under `-C` → **loaded** (the pin loses). **G/H** a subdirectory cwd → the parent `.miserc` is found and honoured. |
| 5 | LOW | On rc≠0 the doctor quotes only the FIRST stderr line. For mise's untrusted-config error that line is `error parsing config file: …/mise.toml`, and the cause (`Config files in … are not trusted.`) is on line 2 and dropped. | `python/src/dotfiles_setup/doctor.py:1547-1549` | The doctor runs outside `mise run` on an untrusted clone (e.g. `uv run --project python dotfiles-setup doctor` on a second Mac, or mise paranoid mode, where `mise run` auto-trust does not cover `mise.arm64.toml`). The operator reads that `mise.toml` fails to parse and debugs TOML that is fine. It is visible UNVERIFIABLE, never healthy. | Fresh local clone with an empty global config and a scratch state (`q2.py` T0): raw `mise env` rc=1, line 1 `error parsing config file: …/mise.toml`, line 2 `… are not trusted.`; doctor → ``UNVERIFIABLE — mise env failed (`mise env` exited 1: mise ERROR error parsing config file: …/mise.toml)``. |

## Answers

### Q1 — Can a broken state read as healthy? **No path found. Two leaks (#1, #2) make the answer nondeterministic or wrong-shell.**

The live arms below all ran through the committed `check_devcontainers_running`, in the real repo, with real mise and real docker (`q1.py`, `q1k.py`). The control R0, with the real env and both containers running, gave `[]`.

| Arm | Result |
|---|---|
| mise missing (`PATH=/usr/bin:/bin`) | `UNVERIFIABLE — mise env failed (mise not found on PATH)` |
| timeout (fake `mise` sleeping 25 s) | `… did not answer within 20 s`; the check returned in 20.2 s (one bound, not three) |
| rc≠0 (fake, rc=3, empty stderr) | `… exited 3: no stderr` |
| bad JSON (fake, rc=0) | `… printed unparsable JSON (Expecting value)` |
| unknown/missing profile (`MISE_IGNORED_CONFIG_PATHS` = tracked + local arm64) | two DRIFT findings: the resolves-amd64 line and the port collision. mise itself gives NO signal: `-E zz-unknown` → rc=0, default, 0 stderr lines, so only the doctor's arch comparison catches it |
| ambient `MISE_ENV`/`DOTFILES_PLATFORM`/port | stripped correctly, default amd64 |
| ambient `MISE_PROFILE` / `MISE_ENVIRONMENT` | **leaks** (#2) |
| ambient `DOTFILES_PLATFORM` via env cache | **leaks** (#1) |
| ambient `MISE_AUTO_ENV=true` | no effect today (no platform-env files) |
| docker down (`DOCKER_HOST` bogus / `DOCKER_CONTEXT` bogus, with the control `docker ps` rc=1 under the same env) | `UNVERIFIABLE — docker ps failed: …` for both |

Neither leak produces a false HEALTHY with today's files. With arches `[amd64, arm64]` and no `mise.amd64.toml`, a leaked arm64 default always makes `-E amd64` disagree, so some finding always appears. It becomes a silent-healthy path only if a tracked `mise.amd64.toml` is ever added: `-E amd64` would then get its own cache key and resolve cleanly, and the arm64 profile, now "the default", is never asserted (`doctor.py:1662`).

Probed and cleared: the gitignored `mise.arm64.local.toml` masks a deleted tracked profile on this host (R5b → `[]`). But `tests/test_platform_target.py:294-298` pins the tracked file's platform line, so pytest catches the deletion. Not a finding.

### Q2 — Is the restore command correct on a fresh clone? **Yes, in a clean shell.**

A local clone of 4ccb98a5 has no `mise*.local.toml` and uses an empty global mise config.

- **Trust:** `mise run` auto-trusts the directory. `trust --show` → `<clone>: trusted`. After that, `-E arm64` resolves `linux/arm64/v8` with a blank port.
- **Doctor output:** ``no amd64 … run `mise run up` `` and ``no arm64 … run `MISE_ENV=arm64 mise run up` ``.
- **Task layer:** `mise run names` → `amd64`, port 21301. `MISE_ENV=arm64 mise run names` → `arm64`, port 23466. Labels and volume differ by arch.
- **Image pull:** `up` pulls inside `devcontainer up`, so no prior `sync` is needed.

Two caveats. #1 and #2 can swap the printed strings. #5 is a misleading UNVERIFIABLE when the doctor runs outside `mise run` on an untrusted clone. The operator-shell ambient `DOTFILES_PLATFORM` case is round-1 #1's mirror, not new.

### Q3 — Does the arch-profile class accept exactly `mise.<arch>.toml` with its own arch? **Filename axis exact; literal axis too loose (#3).**

The filename axis was driven over 27 cells through the committed `find_violations`. Only a root `mise.amd64.toml` / `mise.arm64.toml` gets the class. These are all rejected when they carry a literal:

- `.mise.arm64.toml`
- `.config/mise.arm64.toml`
- `mise/config.arm64.toml`
- `.config/mise/config.arm64.toml`
- `conf.d/x.arm64.toml`
- `sub/mise.arm64.toml`
- `mise.arm64.local.toml`
- `mise.local.toml`
- `mise.riscv.toml`
- `mise.ARM64.toml`
- `mise.aarch64.toml`
- `mise.x86_64.toml`
- `mise.x64.toml`
- `mise.arm64.json`

(`mise.arm64.toml.bak` passes only because `.bak` was never a scanned suffix, which predates this diff.) `platform_arch()` cannot raise inside the filter: every `_LITERAL_RE` match contains an alias. Pytest: `tests/test_doctor.py` plus `tests/test_platform_target.py` → 238 passed at HEAD.

### Q4 — Is `.miserc.toml` `auto_env = false` honoured? **Yes at a repo cwd, including subdirectories. No under `mise -C` from outside (#4).**

- **Honoured:** at the repo cwd, and it beats a global `miserc` `auto_env = true`.
- **Beaten by `MISE_AUTO_ENV`:** documented, and already in the implementer's report, so not new.
- **Bypassed under `mise -C` from outside:** #4.
- **Inert today:** on 2026.9.18, `false` equals the unset default, and the repo has no platform-env files.
- **The profile name cannot collide.** mise's platform envs are `unix`, `{os}` and `{os}-{arch}` (`environments.md:147-156`), so the flip can never auto-load the tracked `mise.arm64.toml`. Arm K confirms that only an explicit `-E arm64` loads it.

## Q-SCOPE

- **#1, #2:** in scope. One line in `mise_env_resolution`'s child env: add `MISE_ENV_CACHE=0`, plus the two alias names. The `test_mise_env_resolution_asks_mise_from_config_alone` equality assertion must change with it.
- **#3:** in scope. Compare against the arch's published triple in both `find_violations` and `_profile_findings`.
- **#4:** recommend a ticket. It is an upstream discovery behaviour; mitigate by running the SessionStart hooks from the project dir instead of via `-C`, or with `MISE_AUTO_ENV=false` in `.claude/settings.json` `env`.
- **#5:** in scope, cosmetic. Quote the `not trusted` line when present, or join the first two lines.

## Evidence log and probe self-corrections

- **Harness.** The working tree was `4ccb98a5`, clean except this report. Every arm imported `dotfiles_setup` from `<repo>/python/src`, asserted by `doctor.__file__`. Scripts are in the scratchpad: `q1*.py`, `q2.py`, `q3*.py`, `q4.py`.
- **Probe self-correction 1: zsh `$E`.** A zsh `for E in "" "-E arm64"` loop passed ONE argv `"-E arm64"` (zsh does not word-split). That gave `-E " arm64"` → default amd64 at rc=0. I discarded it and re-ran with literal argv. The accident incidentally confirmed that an unknown env resolves the default silently.
- **Probe self-correction 2: `setup.environ` vs the process env.** `DOCKER_HOST`/`DOCKER_CONTEXT` set only in `setup.environ` → `[]`. `docker_container_rows` passes no `env=` (`doctor.py:1453-1468`), so docker never saw them. A zsh `VAR=x eval …` prefix also did not reach the grandchild. Re-armed in-process with a direct `docker ps` control (rc=1) → UNVERIFIABLE. The two blind `[]` results are void.
- **Probe self-correction 3: a stray shell.** A stray `$=0` spawned an interactive `/bin/zsh` (pid 3807, my own child); I terminated it. A `printf` left an invalid `\&` in scratch TOML; I rewrote it with Python literal strings. The scratch clone was restored with `git checkout HEAD -- mise.toml` (0 dirty).
- **Not re-derived:** the full lint/verify gates. The implementer reports rc=0 for both; that is inherited and UNVERIFIED here.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — the offline corpus at `knowledge-base/sources/mise` (2026.9.4): `docs/configuration/environments.md` (miserc discovery, platform envs, auto_env rollout), `docs/cache-behavior.md` and `src/toolset/env_cache.rs`/`toolset_env.rs`/`cli/env.rs` (env-cache key and the `mise env` code path). Behaviour was re-measured on the installed 2026.9.18.
