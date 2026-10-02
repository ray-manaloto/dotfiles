# Doctor check: every expected devcontainer arch is running

Ruling: Ray, 2026-09-30 (AskUserQuestion "Restore arm64 + add a doctor check").
Incident: `findings.md` § "2026-09-30 — arm64 devcontainer silently down ~24h".

## 1. Objective

Docker Desktop quit on 2026-09-29T17:12:06Z. Both workspace containers stopped (`RestartPolicy=no` by design:
a docker-level restart skips `postStartCommand`, so R2's ssh-auth chown would be lost —
`.devcontainer/devcontainer.json:46-51`). `land`/`sync` later re-created only the default amd64; the arm64
container sat `Exited (0)` for ~24 h and nothing said so. Add a SessionStart doctor check that reports, at the
start of every session, any expected architecture whose workspace container is not running, naming the exact
command that brings it back.

## 2. Files

- `doctor.toml` — new `[devcontainers]` section.
- `python/src/dotfiles_setup/doctor.py` — `check_devcontainers_running`, registered in `CHECKS` as
  `("devcontainers", check_devcontainers_running)`.
- `python/src/dotfiles_setup/devcontainer_names.py` — only if a small public helper is needed (e.g. a bounded
  `docker ps` returning id+state for label filters); reuse `resolve_names`, `workspace_label`, `arch_label`.
- `tests/test_doctor.py` (or the existing doctor test module — find it), plus devcontainer_names tests if a
  helper is added.
- Append-only `progress.md` / `findings.md`; report `docs/research/kb/reports/agents/implement-doctor-devcontainer-arches-2026-09-30.md`.

Do NOT touch `task_plan.md`, `.claude/**`, `.agents/**`, `.devcontainer/**`, `mise.toml`, other `docs/**`.
If `classifier_axes` or another gate demands an out-of-list edit, STOP and report.

## 3. Interfaces

```toml
[devcontainers]
# Bare arch words, never platform triples (the `no_platform_literals` gate rejects
# `linux/<arch>` outside its allowed sites). Architectures whose workspace container must be RUNNING for this clone. A stopped one
# (Docker Desktop quit, reboot) is reported with the command that restores it. Reviewed diff.
arches = ["amd64", "arm64"]
```

```python
def check_devcontainers_running(setup: Setup) -> list[str]:
```

For each arch: `names = devcontainer_names.resolve_names(workspace=setup.repo_root, platform=arch, env=dict(setup.environ))`
(`platform_arch` accepts a bare arch word; pass `env` so tests are hermetic — `resolve_names(env=None)` reads
`os.environ`); query
`docker ps -a --filter label=<names.workspace_label> --filter label=<names.arch_label> --format '{{.ID}}\t{{.State}}\t{{.Names}}'`
with a hard `timeout=10` and `check=False`.

Findings (prefix `devcontainers:`), exactly one per platform at most:

| observation | finding text must contain |
|---|---|
| `docker` missing / timeout / non-zero rc (daemon down) | `devcontainers: UNVERIFIABLE — docker ps failed (<first line>); is Docker Desktop running?` — ONE finding total, stop checking further platforms |
| no container for the arch | `devcontainers: no <arch> container for this clone — run \`<restore>\`` |
| container(s) present, none `running` | `devcontainers: <arch> container <name> is <state> — run \`<restore>\`` |
| `[devcontainers].arches` missing/empty | `devcontainers: doctor.toml has no [devcontainers].arches, so no container is being checked` |

`<name>` is docker's `{{.Names}}`, NEVER `names.container` (a pinned `DEVCONTAINER_SSH_PORT` changes the computed
suffix; the real arm64 container is `…-arm64-22975`). Linked git worktree (`git rev-parse --git-dir` ≠
`--git-common-dir`): the check returns no finding — devcontainers belong to the main checkout; say so in the
docstring.

Not reusing `sync.container_state` (`sync.py:529-547`, same query) on purpose: it ignores the return code, so a
down daemon reads as `absent` — exactly the conflation the first row forbids. Write a helper that keeps rc.
(Superseded by #1478: `sync.container_state` now derives its state from that helper, `docker_container_rows`.)

`<restore>`: `mise run up` for the arch equal to
`platform_arch(resolve_platform(None, env=dict(setup.environ)))` — compare ARCH words, never triples (the pinned
default is `linux/amd64/v2`, and outside mise the fallback is the host's `linux/arm64/v8`); otherwise `MISE_ENV=<arch> mise run up` (arm64 → `MISE_ENV=arm64 mise run up`,
matching `.devcontainer/AGENTS.md` / root AGENTS.md R3 row).

## 4. Constraints

- The doctor's contract: exits 0, silent when healthy (`.claude/CLAUDE.md` § graphify + project doctor). A finding
  is a line, not a crash; every exception path becomes a finding.
- Bounded: one `docker ps` per platform, 10 s each; no network; no docker mutations (read-only).
- Tests inject the docker answer (keyword parameter or monkeypatched helper) — no real docker in unit tests;
  follow the existing doctor test idiom. py3.14, ruff/ty, zero suppressions, no bash.

## 5. Verification

`mise run gate -- run lint|pytest|verify` (real rcs). Live arms (quote rc + lines):

1. Both containers running now → `mise run doctor` prints no `devcontainers:` line.
2. FAIL arm on the REAL incident shape: `docker stop <arm64 container>` (graceful, same as the DD quit's Exit 0),
   `mise run doctor` → `devcontainers: arm64 container … is exited — run \`MISE_ENV=arm64 mise run up\``; then
   RESTORE with exactly that command, and re-run `MISE_ENV=arm64 mise run verify-arch` (rc=0) and
   `MISE_ENV=arm64 mise run verify-ssh-inbound` (rc=0). `docker stop` here is an ephemeral probe of the doctor, and
   the restore goes through the devcontainer CLI (`do-not.md` #3 governs lifecycle, and `up` is the lifecycle path).
3. Report which command the SessionStart hook runs for the doctor and confirm the check runs in it (not only under
   `--live`).

## 6. Commit

`caller`.

## 7. PREMISES

| # | kind | claim | cite |
|---|---|---|---|
| P1 | I | `CHECKS` table of `(name, fn(Setup) -> list[str])`; `check_hk_hooks` reads its baseline section via `_str_keys(setup.baseline.get(...))` | `doctor.py:1363-1395`, `:1397-1412` |
| P2 | I | `resolve_names(*, workspace, user, platform, …) -> DevcontainerNames` with `workspace_label`/`arch_label` | `devcontainer_names.py:278-307` |
| P3 | P | arch-scoped container lookup = workspace label AND arch label | `devcontainer_names.py:594-640` (`teardown_container_ids`) |
| P4 | L | live labels: `dotfiles.workspace=273897ea`, `dotfiles.arch=amd64`; arm64 container `…-arm64-22975` | `mise run names`, `docker ps -a`, this session |
| P5 | L | the incident container: Finished 2026-09-29T17:12:08Z, ExitCode 0, RestartPolicy no | `docker inspect`, this session |
| P6 | L | restart policy `no` is deliberate: postStartCommand re-chowns ssh-auth.sock on every start | `.devcontainer/devcontainer.json:46-51`, `:241-243` |
| P7 | I | `test_every_check_function_is_actually_registered` requires each `check_*` in CHECKS | `doctor.py:88-92` comment |
| P8 | L | SessionStart runs `mise run doctor` without `--live`; `CHECKS` always run | `.claude/settings.json:125-129`, `mise.toml:695`, `doctor.py:1454` |
| P9 | L | `no_platform_literals` rejects `linux/<arch>` in doctor.toml/doctor.py | `platform_target.py:139-143`, `hk.pkl:281-283` |
| P10 | L | pinned default platform `linux/amd64/v2`; host fallback `linux/arm64/v8` | `mise.toml:203`, `platform_target.py:428-456` |
| P11 | L | `tests/test_doctor.py:1202` asserts `len(doctor.CHECKS) == 15` → becomes 16, ledger comment at `:1171-1201` | premise report |
| P12 | P | `Setup.environ` is the injected env; fixtures use `environ={}` — tests must set `DOTFILES_PLATFORM` | `doctor.py:246`, `:416`; `tests/test_doctor.py:87` |
