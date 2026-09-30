# implementer (Opus fallback for codex-sol-implementer) — doctor devcontainer arches (2026-09-30)

Spec: `docs/specs/doctor-devcontainer-arches.md`. Branch `feat/doctor-devcontainer-arches`, no commit (COMMIT: caller).
Status: DONE — every gate rc=0 and every live arm green; the arm64 container is restored and R1/R3 pass on it.

## Pre-state (measured 2026-09-30, before any edit)

- `mise run names`: `DEVCONTAINER_WORKSPACE_LABEL=dotfiles.workspace=273897ea`, `DEVCONTAINER_ARCH=amd64`,
  `DEVCONTAINER_NAME=…-amd64-26233` (the `mise.local.toml` port pin).
- `docker ps -a`: `e5aec01773f0 running dotfiles-dotfiles-rmanaloto-273897ea-amd64-26233`,
  `a91442a6161c running dotfiles-dotfiles-rmanaloto-273897ea-arm64-22975` — the arm64 name's port suffix differs
  from the computed one, confirming the spec's `{{.Names}}` rule (premise MISSING 6).

## Implementation (done)

- `doctor.toml`: `[devcontainers] arches = ["amd64", "arm64"]` (bare arch words), with the reason and the restore rule.
- `python/src/dotfiles_setup/doctor.py`:
  - `docker_container_rows(names)`: one `docker ps -a` with both label filters, `{{.ID}}\t{{.State}}\t{{.Names}}`,
    `timeout=10`, `check=False`. Every failure (timeout, `OSError`, non-zero rc, unparsable line) raises
    `DockerUnavailableError(<first line>)`. It keeps the rc, unlike `sync.container_state`.
  - `is_linked_worktree(repo_root)`: `git rev-parse --path-format=absolute --git-dir --git-common-dir`. If git
    can't answer, it returns False, so the check still runs.
  - `check_devcontainers_running(setup)`, registered as `("devcontainers", …)` last in `CHECKS`. Order: empty or
    missing `arches` gives the config finding; a linked worktree gives `[]`; otherwise it takes the default arch
    from `platform_arch(resolve_platform(None, env=dict(setup.environ)))`. Per arch it calls
    `resolve_names(workspace=repo_root, platform=arch, env=…)`. Docker failing gives ONE `UNVERIFIABLE` finding
    and returns. No rows gives a `no <arch> container` finding. Rows with none running report the first row's
    `{{.Names}}` and state.
  - The magic numbers are named constants (`_DOCKER_PS_FIELDS`, `_GIT_DIR_FLAGS`). No suppressions.
- `tests/test_doctor.py`:
  - The CHECKS count goes 15→16, with a ledger line.
  - The shipped-baseline test now asserts `arches == ["amd64", "arm64"]`.
  - 14 new tests (19 cases with parametrization). They cover the silent arm, the incident shape (docker's name
    under a port pin), a missing default arch, and a running container next to an exited sibling.
  - Default-arch comparison under 3 platform strings (`linux/amd64/v2`, `linux/arm64/v8`, `linux/amd64`).
  - A down daemon gives one finding and only one query. An unconfigured baseline (3 shapes) produces no docker
    query. A worktree gives silence with no query.
  - `docker_container_rows`: argv, labels, timeout and check; empty output means absent; 5 failure shapes each
    raise with the first line only.
  - `is_linked_worktree` runs against REAL git: main is False, a linked worktree is True, a non-repo is False.
  - The docker seam is monkeypatched. No real docker is used.

## Unit gates (targeted, before the full gates)

- `ruff format` rc=0, `ruff check` rc=0, `ty check` rc=0 on both files.
- `pytest tests/test_doctor.py`: rc=0, 129 passed.

## Mutation arms

Restored by `cp` from a byte copy; `cmp` confirmed identical. Re-run after restore: rc=0, 129 passed.

| mutation | rc | failing test |
|---|---|---|
| M1: drop the `("devcontainers", …)` CHECKS entry | 1 | `test_every_check_function_is_actually_registered` |
| M2: treat `exited` as running (`state in {"running","exited"}`) | 1 | `test_devcontainers_flags_the_incident_shape_with_dockers_own_name` |
| M3: ignore docker's rc (`if proc.returncode != 0` → `if False`) — the `sync.container_state` shape | 1 | `test_docker_container_rows_keeps_the_return_code[daemon-down]`, `[silent-nonzero]` |

## Live arms (spec §5)

1. **Both running, verbose** (`mise run doctor -- --verbose`, rc=0): prints `PASS  doctor[devcontainers]`. 5 other
   DRIFT lines are pre-existing and unrelated to this change: listing-budget (antigravity-delegate description),
   path-drift/claude-doctor BLIND (no ambient PATH under a bare `mise run`), graphify 0.9.72≠0.9.65, and the
   codex-schema 0.159.0 vs 0.159.2 mismatch.
2. **FAIL arm, the real incident shape.**
   - `docker stop dotfiles-dotfiles-rmanaloto-273897ea-arm64-22975` returned rc=0 and left the container
     `Exited (0)`, `RestartPolicy=no`. The amd64 container was untouched: `Up 21 minutes`.
   - Then the hook's exact shape, `DOTFILES_AMBIENT_PATH="$PATH" mise -C . run doctor`, returned rc=0 with:
     `DRIFT doctor[devcontainers]: devcontainers: arm64 container dotfiles-dotfiles-rmanaloto-273897ea-arm64-22975 is exited — run \`MISE_ENV=arm64 mise run up\``
   - The name is docker's `-22975`, not the computed `-26233`.
   - RESTORE: `MISE_ENV=arm64 mise run up` returned RC=0. `docker start a91442a6…` restarted the same container,
     the postStartCommand ran, and the outcome was `"outcome":"success"`.
   - `MISE_ENV=arm64 mise run verify-arch` returned RC=0: `OK: R3 container is linux/arm64/v8 aarch64 on all
     three signals`.
   - `MISE_ENV=arm64 mise run verify-ssh-inbound` returned RC=0: `OK: R1 inbound ssh rmanaloto@localhost -p 22975
     works`.
   - The doctor re-run after the restore returned RC=0 with no `devcontainers` line. Grep control: the same
     `grep -c devcontainers` finds 1 in the pre-restore log and 0 in the post-restore log.
   - Final `docker ps -a`: both running.
3. **SessionStart wiring.**
   - `.claude/settings.json` SessionStart (matcher `startup|resume`) runs
     `DOTFILES_AMBIENT_PATH="$PATH" mise -C "${CLAUDE_PROJECT_DIR:-.}" run doctor`, with no `--live`. It is
     preceded by `tool-currency-check`, and skipped when `CLAUDE_CODE_REMOTE=true`.
   - The check is in `CHECKS`, not `LIVE_CHECKS`, so it runs there. Arm 2 used that exact command shape and the
     check fired, so this is observed rather than inferred.

## Full gates (`mise run gate -- run …`, real rcs from `.agent/gate-results/*.json`)

| gate | rc | evidence |
|---|---|---|
| lint | 0 | `status: passed`, 16.9 s. `✔` for no_platform_literals, no_lint_skip, py_ty, ruff, ruff_format, bash_logic_budget, pin_parity and mise_lock_integrity |
| pytest | 0 | `4306 passed, 11 deselected in 317.26s` |
| verify | 0 | `166 passed, 0 failed, 4 skipped`. The 4 skips are the standing human-only `policy.*` suites |

## Scope

- Diff: `doctor.toml` (+13), `python/src/dotfiles_setup/doctor.py` (+155/−1), `tests/test_doctor.py` (+295/−1).
  Everything else touched is this report and appends to `progress.md`. All of it is inside the §2 allowlist.
- `devcontainer_names.py` was not touched. The helper lives in `doctor.py`, which the spec allows ("only if
  needed").
- No commit, no push, no branch switch.

## Residuals / judgement calls (for the reviewer)

1. **More than one container for an arch, none running:** the finding names the FIRST row docker lists. The spec
   template has one `<name>`, and this keeps the one-finding-per-arch invariant.
2. **Git can't answer `is_linked_worktree`:** returns False, so the check runs rather than going silent. The
   unit fixtures (`repo_root=/repo`) monkeypatch it anyway.
3. **A malformed `DEVCONTAINER_SSH_PORT` pin** makes `resolve_names` raise. That surfaces as the doctor's generic
   `check crashed` finding, not a `devcontainers:` line (premise MISSING 6, accepted).
4. **`MISE_ENV=<arch> mise run up` depends on the gitignored `mise.<arch>.local.toml`** profile (premise MISSING 7).
   It exists on this host. On a clone without it, the named command would bring up the default arch. The spec
   accepts this.
5. **One `docker ps` per arch.** Two arches means up to 2×10 s worst case. On daemon failure the check stops
   after the first query, so a down daemon costs ≤10 s.
6. **The unconfigured-baseline finding also fires for `arches = "amd64"`** (a string instead of a list): the
   value isn't a list, so it is treated as unset.

## GitHub repos touched

_None._ (Local code and local docker only.)
