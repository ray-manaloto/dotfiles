# Doctor devcontainer arches — round 1 fixes + tracked arm64 profile + auto_env pin

Parent: `docs/specs/doctor-devcontainer-arches.md` (commit `7cb15346`). Respec round 1 of max 2.
Rulings: Ray 2026-09-30 — "Track mise.arm64.toml + doctor assert" and "Pin auto_env in a tracked .miserc.toml"
(AskUserQuestion). Sources: `cold-review-7cb15346-2026-09-30.md` (#1-#13), `code-review-7cb15346-2026-09-30.md`
(#1-#2), `mise-environments-multi-devcontainer-2026-09-30.md`, `findings.md` § 2026-09-30.

## 1. Objective

The doctor's restore command must be RIGHT on every clone and every context, and the check must be silent where
it cannot apply:

| id | problem | fix |
|---|---|---|
| A | `MISE_ENV=arm64 mise run up` only works when a gitignored `mise.arm64.local.toml` exists (cold #1) | tracked `mise.arm64.toml` + a doctor assertion of what each arch RESOLVES to |
| B | default arch read from the process env: outside mise it falls back to the host's arm64 (cold #2) | resolve through mise itself |
| C | inside the devcontainer: no docker CLI/socket (probed: `command -v docker` not found, no `/var/run/docker.sock`, `claude` present) → UNVERIFIABLE every session (code-review #1, cold #4) | skip unless the host is macOS |
| D | `is_linked_worktree` git call unbounded; missing git raises (code-review #2, cold #9) | 10 s timeout; OSError/timeout → "not a worktree" as the docstring says |
| E | a later arch's docker failure discards earlier definite findings (cold #5) | keep them, then add UNVERIFIABLE |
| F | `arches` entries unvalidated (cold #6) | config finding |
| G | cause-blind hint (cold #10) | per-cause text |
| H | tests: `created/paused/dead` states, `--filter` pairing, git-config isolation (cold #7, #8, #12) | tests |
| I | mise `auto_env` flips on by default in 2027.6.0, warns from 2026.12.0 | tracked `.miserc.toml` `auto_env = false` |

Out of scope → ticket (filed by the architect): cold #3 (worktree could derive the main checkout's label),
cold #13 (`sync.container_state` ignores docker rc).

## 2. Files

Create: `mise.arm64.toml`, `.miserc.toml`.
Modify: `python/src/dotfiles_setup/doctor.py`, `doctor.toml`, `tests/test_doctor.py`,
`python/src/dotfiles_setup/platform_target.py`, `tests/test_platform_target.py` (or the module's existing test file),
`mise.local.toml.example` (the arm64 paragraph only). Append-only `progress.md`/`findings.md`; report
`docs/research/kb/reports/agents/implement-doctor-arches-r1-2026-09-30.md`.
Do NOT touch: `task_plan.md`, `.claude/**`, `.agents/**`, `AGENTS.md`, `.devcontainer/**`, `mise.toml`,
`mise.local.toml`, `mise.arm64.local.toml` (the operator's files), other `docs/**`. A gate demanding more ⇒ STOP.

## 3. Behaviour

**A1 — `mise.arm64.toml`** (tracked):

```toml
# Selected by `MISE_ENV=arm64` (e.g. `MISE_ENV=arm64 mise run up`): the second devcontainer architecture in the
# same clone. The port is blank so the arm64 container derives its own and never collides with amd64's pin.
# Measured on mise 2026.9.18: this file OVERRIDES mise.local.toml under -E arm64, contrary to upstream's
# environments.md — the doctor asserts the resolved values, so a change in either direction is caught.
[env]
DOTFILES_PLATFORM = "linux/arm64/v8"
DEVCONTAINER_SSH_PORT = ""
```

**A2 — `platform_target`.** Arch-profile files `mise.<arch>.toml` (root, `<arch>` in `PUBLISHED_ARCHES`) are a
new permitted-literal class: the scan accepts a `linux/<arch>…` literal there ONLY when its arch equals the
filename's `<arch>`; any other literal in such a file is a violation (message names file, literal, expected arch).
They do NOT join the default-agreement check (`DEFAULT_LITERAL_SITES` must still agree among themselves). Tests:
the tracked file passes; `mise.arm64.toml` carrying `linux/amd64/v2` fails; a `mise.riscv.toml` with a literal is
still a violation.

**A3 / B — doctor resolution through mise.** A helper (not named `check_*`) runs
`mise env --json` (default) and `mise -E <arch> env --json` (each non-default candidate) with `cwd=repo_root`,
`timeout=20`, `check=False`, and reads `DOTFILES_PLATFORM` / `DEVCONTAINER_SSH_PORT`. The default arch =
`platform_arch(DOTFILES_PLATFORM from the plain run)`. For each configured arch that is not the default:
- resolved platform's arch ≠ that arch → finding
  `devcontainers: \`MISE_ENV=<arch>\` resolves DOTFILES_PLATFORM=<value>, so \`MISE_ENV=<arch> mise run up\` would
  bring up <other arch>; check mise.<arch>.toml`;
- resolved port non-empty AND equal to the default's non-empty port → finding naming the collision.
Any mise failure (missing, timeout, rc≠0, JSON error) → ONE `devcontainers: UNVERIFIABLE — mise env failed (…)`
finding and skip the container query for the affected arch(es). These assertions run whether or not the
containers are up.

**C.** When `platform.system() != "Darwin"` the check returns `[]` (docstring: devcontainers are brought up from
the macOS host — AGENTS.md "Two Build Types"; inside the container there is no docker, and on a Linux CI host the
concept does not apply). Inject the system name for tests.

**D.** `is_linked_worktree`: `timeout=10`; `OSError`/`TimeoutExpired`/non-zero rc → `False`.

**E.** Collect definite per-arch findings first; on a docker failure append the single UNVERIFIABLE finding and stop
querying further arches, but RETURN the earlier findings too.

**F.** `arches` must be a non-empty list of distinct strings, each normalizing (`platform_arch`) to a known arch;
otherwise one config finding naming the bad entries, no docker/mise calls.

**G.** UNVERIFIABLE detail per cause: timeout → `docker ps did not answer within 10 s`; missing binary →
`docker CLI not found on PATH`; non-zero rc → docker's first stderr line + `; is Docker Desktop running and the
context right?`; unparsable line → `unparsable docker ps line: <line>`.

**I — `.miserc.toml`** (tracked):

```toml
# Early-init mise settings (read before config discovery). Pin auto_env explicitly: mise enables platform
# environments by default from 2027.6.0 and warns from 2026.12.0 (upstream docs/configuration/environments.md
# "Rollout"). false = today's behaviour; revisit if a real host-vs-container variable difference appears.
auto_env = false
```

`doctor.toml` `[devcontainers]` comment: "for every clone of this repo" (not "this clone"), and that `arm64` is
restored via the tracked `mise.arm64.toml`.

`mise.local.toml.example`: replace the arm64 paragraph — the profile is now tracked (`mise.arm64.toml`);
`mise.arm64.local.toml` is only for per-clone overrides.

## 4. Constraints

As the parent spec. No test runs real docker or real mise env of the repo (inject the runner); ONE test may run
real `mise` against a scratch dir only if it is hermetic and bounded — otherwise inject. py3.14, ruff/ty, zero
suppressions, no bash, no platform literal outside the permitted sites.

## 5. Verification

`mise run gate -- run lint|pytest|verify` (real rcs). Live arms (quote rc + lines; never stop amd64):

1. `mise -E arm64 env --json | jq -r .DOTFILES_PLATFORM,.DEVCONTAINER_SSH_PORT` → `linux/arm64/v8`, empty — first
   with `mise.arm64.local.toml` present, then with it MOVED ASIDE to the scratchpad (restore it by byte copy and
   `cmp` after). Both must resolve arm64 + blank port.
2. `mise run doctor -- --verbose` → `PASS doctor[devcontainers]` with both containers up.
3. FAIL arm A3: temporarily edit `mise.arm64.toml` to `linux/amd64/v2` → doctor prints the resolves-to finding
   (and platform-literals fails); restore by byte copy.
4. FAIL arm C: run the doctor INSIDE the amd64 container
   (`docker exec <amd64> bash -lc 'cd /workspaces/dotfiles && mise run doctor -- --verbose'` — read-only exec) →
   no `devcontainers:` DRIFT line.
5. `mise settings get auto_env` → `false` from the repo root (control: from `/tmp` → not set).

## 6. Commit

`caller`.

## 7. PREMISES

| # | kind | claim | cite |
|---|---|---|---|
| P1 | L | mise 2026.9.18: under `-E arm64`, `mise.arm64.toml` overrides `mise.local.toml` (control-armed) | `findings.md` § 2026-09-30 PROBE |
| P2 | L | upstream docs claim the opposite order | `jdx/mise docs/configuration/environments.md:136-141` (fetched this session) |
| P3 | L | `.miserc.toml` `auto_env = false` is the documented pin; setting exists on 2026.9.18 | `environments.md:209-221`; `mise settings get auto_env` vs unknown-setting control |
| P4 | L | literal gate sites and exclusions | `platform_target.py:126`, `:139-143`, `:152-183` |
| P5 | L | `PUBLISHED_ARCHES = ("amd64", "arm64")` | `platform_target.py` (after `_SCAN_EXCLUDED_PATHS`) |
| P6 | L | in-container: no docker CLI, no socket, claude installed | `docker exec … command -v docker` (not found) / `claude` found, this session |
| P7 | L | current resolution: `mise -E arm64 env` → `linux/arm64/v8`, port `""`; default → `linux/amd64/v2`, port `26233` | this session |
| P8 | I | current check code | `doctor.py` `check_devcontainers_running` / `docker_container_rows` / `is_linked_worktree` at `7cb15346` |
| A1 | A | `mise env --json` completes well under 20 s in a SessionStart doctor | UNVERIFIED — time arm 2 and report it |
