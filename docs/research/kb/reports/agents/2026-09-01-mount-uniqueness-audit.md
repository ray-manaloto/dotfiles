# Devcontainer mount & volume uniqueness audit — 2026-09-01

**Lane:** codex-advisor (running in-process, task delegated from team-lead)
**Question:** Are the devcontainer's bind mounts/volumes uniquely scoped per
(workspace × architecture), or can two concurrent containers (or the host)
write the same bytes and corrupt them?

Status: IN PROGRESS — writing incrementally.

## Mount inventory (from `.devcontainer/devcontainer.json` lines ~104-120)

| # | Declaration | Source | Target | Type | Scope |
|---|---|---|---|---|---|
| 1 | `workspaceMount` | `${localWorkspaceFolder}` | `/workspaces/<basename>` | bind, `consistency=cached` | workspace path (inherently unique per clone dir) |
| 2 | `mounts[0]` | `${HOME}/.local/state/dotfiles` | `/tmp/dotfiles-host-state` | bind | **NOT scoped** — literal `$HOME` path, identical for every workspace and every arch on this Mac |
| 3 | `mounts[1]` | `/run/host-services/ssh-auth.sock` | `/run/host-services/ssh-auth.sock` | bind | **NOT scoped** — Docker Desktop's single host-wide magic socket; identical for every workspace and arch |
| 4 | `mounts[2]` (home volume) | `${DEVCONTAINER_HOME_VOLUME}` | `/home/${USER}` | named volume | **Scoped** — name embeds workspace SHA-256[:8] hash + arch (`python/src/dotfiles_setup/devcontainer_names.py:231`) |

## Finding 1 — home volume: correctly scoped (CONTROL-ARMED, negative confirmed)

`DevcontainerNames.home_volume` = `dotfiles-<basename>-<user>-<hash>-<arch>-home`
(`devcontainer_names.py:231`). `resolve_names()` derives `hash` from
`workspace_hash()` (SHA-256[:8] of the **resolved** workspace path,
`devcontainer_names.py:153-171`) and `arch` from `platform_arch(resolve_platform(...))`.

Control arm — ran the real resolver against 4 distinct (workspace, arch) inputs
(no ambient env overrides beyond `USER`):

```
/Users/.../dotfiles            linux/amd64 -> home=dotfiles-dotfiles-rmanaloto-273897ea-amd64-home
/Users/.../dotfiles            linux/arm64 -> home=dotfiles-dotfiles-rmanaloto-273897ea-arm64-home
/Users/.../dotfiles-worktree2  linux/amd64 -> home=dotfiles-dotfiles-worktree2-rmanaloto-758cc58b-amd64-home
/tmp/some-other-clone          linux/amd64 -> home=dotfiles-some-other-clone-rmanaloto-9f9a78c0-amd64-home
```

All four values differ — one bit (arch) or the workspace hash changes the name
every time. **Verdict: home volume is uniquely scoped to (workspace × arch).
No collision.** This matches the design comment at
`devcontainer.json:110-113` ("sharing one across architectures interleaves
binaries silently").

**Self-correction during this control arm**: an earlier pass of the same test
appeared to show `ssh_port` collapsing to the same value (26233) for both
amd64 and arm64 on the same workspace. Root cause: the probe script copied
`os.environ` into the resolver's `env=`, and the CURRENT shell already has
`DEVCONTAINER_SSH_PORT=26233` set (this session's own devcontainer). That env
var is the documented per-clone **override** (`ssh_port()`,
`devcontainer_names.py:174-206`) and wins over derivation by design — so the
identical port was the probe leaking ambient state, not a defect. Re-ran
`ssh_port()` directly (no env dict) and got amd64=26233, arm64=22975 — correctly
differentiated. Recorded per `probes-need-a-control-arm.md`: the surprising
result was in my probe, not the resolver.

## Finding 2 — `~/.local/state/dotfiles` bind mount: UNSCOPED, real collision (Sev: HIGH)

`mounts[0]`: `source=${localEnv:HOME}/.local/state/dotfiles,target=/tmp/dotfiles-host-state,type=bind`
carries **no workspace hash and no arch** — it is the literal `$HOME` path,
identical across every clone and every architecture on one Mac.

What writes/reads it (traced via `python/src/dotfiles_setup/docker.py`,
`config.py:42`, `devcontainer.json` `initializeCommand`/`postCreateCommand`):

- `initializeCommand` (host-side, runs BEFORE the container exists, on every
  `devcontainer up`): `doppler secrets download ... > ~/.local/state/dotfiles/doppler.env`,
  then `dotfiles-setup docker initialize-host` writes
  `~/.local/state/dotfiles/authorized_keys` (`docker.py:101` `_write_host_authorized_keys`).
- `runArgs --env-file ${HOME}/.local/state/dotfiles/doppler.env` — read by the
  Docker daemon at container-create time, directly off the host path (not
  through the bind mount, since the container doesn't exist yet).
- `postCreateCommand` (container-side, in-container): reads
  `/tmp/dotfiles-host-state/authorized_keys` via the bind mount to seed
  `~/.ssh/authorized_keys`.

**`doppler.env` content is workspace-specific by design** — `DOPPLER_PROJECT`/
`DOPPLER_CONFIG` are documented as overridable **per-clone** via
`mise.local.toml` (`devcontainer.json:69-72`, `AGENTS.md` "Override per-clone
via `mise.local.toml`"). So the file this shared path holds is not a constant —
it is "whichever clone's `up` ran `initializeCommand` most recently."

### Concrete corruption interleaving

1. Operator runs `mise run up` in clone A (project=`dotfiles`, config=`dev_personal`).
2. `initializeCommand` starts: `doppler secrets download ... > ~/.local/state/dotfiles/doppler.env`
   (a **truncate-then-write**, i.e. `>` redirection — not atomic, not append).
3. Before A's `devcontainer up` reaches the `docker create`/`run` step that
   consumes `--env-file`, the operator (or CI, or a second terminal) runs
   `mise run up` in clone B — a different clone with a different
   `mise.local.toml` `DOPPLER_PROJECT`/`DOPPLER_CONFIG` (or the same project,
   different config, e.g. `dev_ci`).
4. B's `initializeCommand` also does `doppler secrets download ... > ~/.local/state/dotfiles/doppler.env`,
   overwriting A's freshly-downloaded file with B's secrets — or, if B's
   download is slower/interleaved at the OS write-buffer level with A's, the
   file can end up holding an interleaved/partial mix of two Doppler
   responses (both are shell `>` redirects to the SAME path — no locking, no
   temp-file+rename).
5. If A's `docker create --env-file` step runs strictly after step 4, **A's
   container is created with B's secrets** (wrong project's credentials
   injected into A's environment) — silent, no error, since the file is
   non-empty and well-formed KEY=VALUE either way (`initializeCommand`'s own
   `[ -s ... ]` check only verifies non-empty, not "belongs to this clone").
   If the writes genuinely interleave at the byte level, the file can be
   **malformed** (a truncated line, a value split mid-write), and `--env-file`
   parsing then either drops secrets or errors out — a real corruption, not
   just a mix-up.
6. `authorized_keys` collision is a narrower case: content is derived from
   `ssh-add -L` (the host user's current SSH agent identities), which is
   normally identical regardless of which clone triggered the write, so two
   concurrent `initialize-host` calls overwriting each other does not by
   itself corrupt data (same content wins either way) — this file is
   unscoped but not currently a corruption vector unless a future change
   makes it workspace-specific.

**Verdict: unscoped shared path + a `>`-truncate writer with no lock, mounted
into potentially-concurrent containers.** The realistic trigger is two
terminals bringing up two different clones (or two arches of the same clone)
within the same few seconds — not a contrived scenario; `mise run up` for a
second arch of the SAME workspace is an explicitly supported flow (#677), and
both arches share this one host path.

**Severity: HIGH for secrets correctness** (wrong-project secrets silently
injected, or a malformed env file), **LOW for `authorized_keys`** (idempotent
content in the current design, but still unscoped and worth fixing alongside).

No existing lock guards `initializeCommand`'s writes to this path — checked
`mise.toml [tasks.up]` (lines 239+) for a lockfile/flock wrapper: none found.
The only sibling lock mentioned in the repo (`~/.local/state/dotfiles/dag-tick.lock`,
`mise.toml:629`) guards an unrelated periodic-tick mechanism, not `up`.

## Live confirmation (read-only `docker inspect`, 2026-09-01)

Two containers are running RIGHT NOW for this exact workspace, one per arch:

```
dotfiles-dotfiles-rmanaloto-273897ea-amd64-26233
dotfiles-dotfiles-rmanaloto-273897ea-arm64-22975
```

Both simultaneously bind-mount the SAME two unscoped host paths:

```
/Users/rmanaloto/.local/state/dotfiles -> /tmp/dotfiles-host-state   (both containers)
/run/host-services/ssh-auth.sock       -> /run/host-services/ssh-auth.sock (both containers)
/Users/rmanaloto/dev/github/ray-manaloto/dotfiles -> /workspaces/dotfiles (both containers — same workspace, expected)
```

This is not a hypothetical — the exact concurrency window described in
Finding 2 exists on this Mac at this moment for two arches of one workspace,
and `docker volume ls` shows **15 other dotfiles clones/worktrees** with
their own home volumes, each a candidate for a concurrent `mise run up` that
would hit the same shared `/tmp/dotfiles-host-state` path.

`docker volume ls` also confirms the home-volume uniqueness claim empirically:
every one of the 15+ real volumes has a distinct hash/arch suffix (e.g.
`dotfiles-dotfiles-arm64-main-rmanaloto-019ae7b8-arm64-home`,
`dotfiles-repo-rmanaloto-8ca71197-amd64-home` — five different `dotfiles-repo-*`
clones, five different hashes). The pre-#677 legacy volume
`dotfiles-dotfiles-rmanaloto-273897ea-home` (no arch suffix) is present but
**not mounted by either running container** — confirms the #677 migration to
arch-suffixed volumes is in effect and the legacy volume is inert, not double-mounted.

## Finding 3 — `ssh-auth.sock` bind: unscoped but not a corruption vector (Sev: LOW / informational)

`mounts[1]`: `source=/run/host-services/ssh-auth.sock,target=/run/host-services/ssh-auth.sock,type=bind`
is Docker Desktop's single host-wide magic socket — inherently one instance
per Mac, cannot be workspace/arch-scoped (it isn't a resource this project
creates). Both live containers mount it, confirmed above.

`postCreateCommand`/`postStartCommand` in each container run
`sudo chown ${localEnv:USER}:${localEnv:USER} /run/host-services/ssh-auth.sock`
(`devcontainer.json:223` and the postStartCommand referenced at
`devcontainer.json` comment lines 44-52). Two containers chowning the same
socket concurrently is a race, but `remoteUser` is `${localEnv:USER}` for
every container on this Mac (one host user), so both chowns target the
identical owner:group — the race is idempotent, not corrupting. Docker
Desktop itself resets the socket to `root:root` independently on restart, so
this is already a known re-chown-every-start design, not a data path.
**No corruption; flag only because it is unscoped by necessity, not because
it needs a fix.**

## Finding 4 — `workspaceMount`: intentionally shared, one known collision already fixed, watch for new ones (Sev: informational)

`workspaceMount` binds the literal working tree
(`source=${localWorkspaceFolder}`) into every container for that workspace,
by design — this is the standard "edit host files from the container" model,
not a scoping defect. It is deliberately the SAME source for both arch
containers of one workspace (confirmed live above) — that is required for
the devloop (both arches should see the same source edits), not a bug.

The known instance of two writers colliding on this shared tree was already
found and fixed: `UV_PROJECT_ENVIRONMENT` (`devcontainer.json` containerEnv,
review finding [33], 2026-07-07) redirects the python venv out of the bind
mount onto the (per-arch-scoped) home volume, because host macOS Python and
container Linux Python interpreters are ABI-incompatible and a concurrent
`uv sync` from both sides was observed corrupting `dist-info` (ENOENT rename
race). That fix is in place and confirmed above (home volumes are correctly
per-arch).

**Residual risk, not yet observed as a defect**: any FUTURE build artifact
written under `/workspaces/dotfiles` by both a `amd64` and an `arm64`
container concurrently (or by the host and a container) without a similar
redirect would reproduce the same class of bug the venv fix already
addressed once. This audit found no second instance of it in the current
tree (searched for other `.venv`/`node_modules`/build-cache-shaped paths
under the workspace — `python/.venv` is the only one referenced by
`containerEnv`, and it is now redirected). Recommend: any new per-arch build
artifact under the workspace tree gets the same treatment (redirect to the
home volume) proactively, before it is observed as corruption rather than
after.

## Summary table

| Mount | Scoped to workspace×arch? | Concurrent writers? | Verdict | Severity |
|---|---|---|---|---|
| `workspaceMount` (git tree) | N/A — intentionally shared per workspace | host + N containers (by design) | OK; one prior collision (python venv) already fixed; watch for new build-artifact paths | Informational |
| `~/.local/state/dotfiles` → `/tmp/dotfiles-host-state` | **No** — host-wide, no hash/arch | `initializeCommand` (host, `>`-truncate, no lock) from every concurrent `mise run up` across every clone/arch | **Real collision**: concurrent `up`s can overwrite each other's `doppler.env` before it's consumed, injecting wrong-project secrets or a malformed env file | **HIGH** (secrets file); LOW (authorized_keys, idempotent content) |
| `/run/host-services/ssh-auth.sock` | No — single host-wide socket (not project-created) | every running container chowns it | Idempotent race (same owning user for every container on this Mac); no corruption | LOW / informational |
| Home volume (`DEVCONTAINER_HOME_VOLUME`) | **Yes** — SHA-256[:8] workspace hash + arch, control-armed against 4 inputs + confirmed live against 15+ real volumes | N/A | No collision | — |

## Recommendation (not implemented — read-only audit)

Fix Finding 2 by either (a) scoping `mounts[0]`'s host-side path per workspace
(e.g. `~/.local/state/dotfiles/<workspace-hash>`, mirroring the home-volume
pattern already in `devcontainer_names.py`), or (b) serializing
`initializeCommand`'s `doppler.env` write with a lock file plus a
temp-file+atomic-rename instead of `>` truncation, or (c) both — (a) removes
the collision class entirely, (b) hardens the write itself if any other
process still touches the shared file. Given `workspace_hash()` and
`resolve_names()` already exist and are exercised by
`tests/test_devcontainer_names.py`, (a) is the smaller change and reuses
tested code rather than adding new locking logic
(`.claude/rules/use-tool-builtins.md`).

## GitHub repos touched

_None._ This audit read only files inside the local `dotfiles` repository
working tree and local `docker`/`mise` state; no external repo, doc site, or
API was consulted.

---
Status: COMPLETE.

---

# Round 2 — full enumeration of `~/.local/state/dotfiles/` (9 remaining files)

`ls -la ~/.local/state/dotfiles/` (re-run fresh for this round):

```
authorized_keys        104 B   (covered in Round 1)
dag-tick.lock             0 B
doppler.env          3,478 B   (covered in Round 1)
guard-fail-open.log   9,418 B
hk-lint.log         304,027 B
host-ssh-proxy.log        0 B
ssh-agent-port             6 B
ssh-agent-proxy.pid        6 B
ssh-agent.target          48 B
sync-ghcr.io_ray-manaloto_dotfiles-devcontainer_dev.json  288 B
```

## Finding 5 — `hk-lint.log`: unscoped, evidence-integrity risk, HOST-side only (Sev: MEDIUM)

`DEFAULT_LOG_FILE = Path.home() / ".local" / "state" / "dotfiles" / "hk-lint.log"`
(`python/src/dotfiles_setup/lint.py:48`). `run_guarded()` **truncates it up
front** (`log_file.write_text("")`, line 118) on every `mise run lint`
invocation, then points `HK_LOG_FILE` at it for the hk subprocess to append
debug output during the run (line ~120).

**Where it physically lands depends on which `HOME` resolved it — and that
splits this from Finding 2 rather than merging with it.** Confirmed
`.devcontainer/Dockerfile.host-user:71`: `HOME=/home/${DEVCONTAINER_USER}` is
a **build-time, static** ENV, baked into the image for both arch overlays.
Inside EITHER container, `Path.home()` resolves to `/home/<user>`, which is
the **home volume mount target** — already confirmed scoped per (workspace ×
arch) in Finding 1. So a `mise run lint` executed *inside* a container never
touches the shared `/tmp/dotfiles-host-state` bind-mount path at all; it
writes to that container's own scoped home volume.

**The real collision is HOST-side, across CLONES, not container-side.** On
the Mac, `Path.home()` is the same `/Users/rmanaloto` for every terminal
regardless of which clone's directory it's running `mise run lint` from
(this repo's "Build Type 1 — Local Linting" is the documented host-run path,
`AGENTS.md`). Two terminals running `mise run lint` concurrently — for the
SAME clone (two windows) or for TWO DIFFERENT clones on the same Mac — both
resolve `DEFAULT_LOG_FILE` to the identical
`~/.local/state/dotfiles/hk-lint.log`.

### Concrete interleaving

1. Terminal 1 (clone A) runs `mise run lint`; `run_guarded()` truncates
   `hk-lint.log` and starts `hk` with `HK_LOG_FILE` pointed at it.
2. Before terminal 1's `hk` run finishes, terminal 2 (clone B, or a second
   window on the SAME clone) runs `mise run lint` too; its `run_guarded()`
   ALSO truncates the same file and starts its own `hk` writing to it.
3. Both `hk` processes now append DEBUG lines to the same inode
   concurrently — the file becomes an interleaved mix of two unrelated lint
   runs' output, and whichever truncation happened last wins the "start of
   this run" boundary for both.
4. Per `.claude/rules/long-running-command-hangs.md` rule 2, `hk-lint.log`
   is the file an agent or human is told to read for "what happened" —
   **the process's own `rc` (from `proc.wait()`, printed as `rc=N` by the
   CLI) is still correct for its own run** (that value never crosses
   processes), but if you go read the log body to diagnose a failure or
   confirm a timeout tail (`_print_log_tail`, line ~140), **you can read the
   OTHER run's content**, or a spliced mix of both. This is exactly the
   evidence-integrity failure `.claude/rules/verify-before-advancing.md`
   warns against ("read a file-based `rc`... never a piped tail") — the
   file itself, not just a pipe, can now lie about which run it describes.
5. On a *timeout*, `_print_log_tail()` reads whatever is currently on disk
   — if the other run truncated first, the printed "diagnosis" tail can be
   **entirely the other run's debug output**, misattributed to the timeout.

**Control arm — is this really plausible, or a one-in-a-thousand race?**
`hk run check --all` on this repo took ~58s wall-clock for the 304,027-byte
log observed (Sep 1 00:58 timestamp on a repo with a `land -- 892` in flight
around the same window per Finding 3's sync file below) — that is a wide
concurrency window, and running `mise run lint` from two clones/two windows
during active multi-branch work (confirmed common in this session's own git
log — 15+ live worktree home volumes) is a completely ordinary devloop
pattern, not a contrived edge case.

**Severity: MEDIUM.** Not disk corruption of a durable artifact (the file is
disposable/regenerated every run and never a `.git` or source file), and the
"done" signal (`rc`) is unaffected — but it *does* poison the diagnostic
artifact the project's own rules tell you to trust, at exactly the moment
(a hang or failure) you most need it to be reliable.

## Finding 6 — `dag-tick.lock`: correctly scoped for what it protects (Sev: none — false alarm, control-armed)

`LOCK_PATH = Path.home() / ".local" / "state" / "dotfiles" / "dag-tick.lock"`
(`python/src/dotfiles_setup/dag_tick.py:231`), with the comment: *"One tick
at a time — a second tick that finds the lock held exits 0 silently rather
than racing a respawn/stop against the first."*

Tracing what `dag_tick` actually is (`dag_tick.py` module + `mise.toml:624`
comment "Fired every 60s by the [LaunchAgent]"): it is a **host-only,
per-Mac** background-job reaper for Claude Code's own background nodes
(`JOBS_DIR = Path.home() / ".claude" / "jobs"`, `DAEMON_DIR = Path.home() /
".claude" / "daemon"`), invoked via a macOS LaunchAgent running
`~/.local/bin/mise` directly (not through any devcontainer). **It has no
relationship to devcontainers, workspaces, or architectures at all** — it is
one global process managing one global job roster for this Mac.

So "a lock in an unscoped directory" here is not a scoping defect: the
directory being host-wide, unscoped by workspace/arch, is *correct* for a
mechanism whose own domain is host-wide. It happens to share the same
parent directory (`~/.local/state/dotfiles/`) purely as a convention for
"host state this project owns" — not because it needs devcontainer-level
scoping. **Verdict: not a devcontainer mount-uniqueness issue; false alarm
by association with the shared directory, not by its own design.**

## Finding 7 — `sync-ghcr.io_..._dev.json`: real cross-workspace state pollution, confirmed by both code and live data (Sev: MEDIUM-HIGH)

`_state_file(image_ref)` (`python/src/dotfiles_setup/sync.py:228-229`) keys
the filename **only on the base image ref**
(`ghcr.io/ray-manaloto/dotfiles-devcontainer:dev`), not on workspace or arch.
The module docstring defends this explicitly for `local_image_id`/
`registry_digest`: those describe the ONE shared base image on this Mac's
Docker daemon, and correctly-shared state is not a bug — sharing them is the
whole point (avoids every clone re-detecting a base-image pull redundantly).

**But the `containers` dict inside that same shared record is
workspace-specific data being stored in a workspace-unaware key.**
`container_image_id(names)` (`sync.py:436-456`) filters `docker ps` by
**both** `names.workspace_label` AND `names.arch_label` — i.e. it resolves
"the overlay image ID for THIS workspace's THIS-arch container" — genuinely
per-(workspace × arch) data. `write_sync_record()` then stores it as
`containers[names.arch] = cid` (`sync.py:306-308`) — **keyed by arch alone**,
inside a file that is itself keyed by image_ref alone. There is no
workspace dimension anywhere in the storage path for a value that is
workspace-specific by construction.

**Live confirmation**: this Mac has 15+ distinct dotfiles clones/worktrees
(Round 1's `docker volume ls` enumeration — `checkout`, `arm64-main`,
`codex-task-orchestration-v2`, `goal-history`, `issue-753-writer-lease`,
`issue-763`, `pr671`, five `repo-*` variants, plus this workspace), every one
of which is capable of running `mise run sync` against the SAME shared base
image ref. Yet exactly **one** `sync-ghcr.io_...json` file exists on this
Mac, holding exactly one `containers` entry per arch
(`{"amd64": "sha256:670921fd..."}`) — there is no per-workspace fan-out at
all. Whichever workspace synced last for a given arch is the only one whose
convergence state survives.

### Concrete interleaving

1. Workspace A (this clone, `273897ea`) runs `mise run sync`;
   `write_sync_record` reads the current record (`containers={}` or stale),
   computes `container_image_id` for A's amd64 overlay
   (`vsc-dotfiles-273897ea-amd64`), writes `containers["amd64"] = A_cid`.
2. Workspace B (e.g. `dotfiles-repo-...-8ca71197`) runs `mise run sync` for
   its own amd64 overlay shortly after. Its `write_sync_record` call does
   its own `read_sync_record` → sees A's record (same `registry_digest`/
   `local_image_id`, since both point at the identical base image) → merges
   in `containers["amd64"] = B_cid`, **overwriting A's entry** (same dict
   key, no workspace disambiguation).
3. `write_text()` (`sync.py:320`) is a **plain, non-atomic write** — no
   temp-file+rename, no lock — so this is also a live TOCTOU race if A and B
   sync concurrently: whichever `write_text()` call lands last wins outright,
   independent of which read happened first.
4. Workspace A next runs `mise run sync` (or any command consulting
   `SyncStatus.container_current`) and reads `containers["amd64"] = B_cid` —
   **B's overlay image id, attributed to A's workspace**. Compared against
   A's *actual* current overlay id, this reads as `stale=True`
   (`container_current` returns `self.container_image_id == recorded`, and
   A's real id ≠ B's id) even when A's own overlay is genuinely current.

**Direction of the defect is fail-safe, not fail-silent**: a mismatch reads
as "stale," triggering an unnecessary rebuild rather than skipping a needed
one — so this is not the "silently serve stale/wrong container" failure mode,
it's "spurious rebuild storms across every clone that shares this Mac,"
because each clone's sync run keeps clobbering every other clone's arch
entry. That still directly matches what was asked to check: **"a second
clone can read a verdict that was computed for a different workspace" — yes,
confirmed by code path and by the live single-entry file. The filename's
registry-ref scoping is NOT sufficient**, because the value it protects
(`containers[arch]`) needs a workspace dimension the filename doesn't carry.

**Fix shape** (not implemented — read-only audit): key `containers` by
`f"{names.hash}:{names.arch}"` instead of `names.arch` alone, reusing the
already-tested `workspace_hash` (same "reuse the tested helper" recommendation
as Finding 2).

## Finding 8 — `ssh-agent-port` / `ssh-agent-proxy.pid` / `ssh-agent.target`: DEAD residue, confirmed (Sev: none — cleanup only)

Content: `ssh-agent-port` = `63597`, `ssh-agent-proxy.pid` = `81264`,
`ssh-agent.target` = `/var/run/com.apple.launchd.NlopaSJTzb/Listeners`. All
three carry the **same mtime, Apr 9 2026**, alongside `host-ssh-proxy.log`
(0 bytes, also Apr 9).

Verified — not assumed from mtime alone, per the brief's instruction:

- **No runtime code references any of the three filenames.**
  `grep -rlnE "ssh-agent-port|ssh-agent-proxy|ssh-agent.target|host-ssh-proxy"`
  across every `.py`/`.json`/`.toml` in the repo returns **zero matches**.
  `.md` files are deliberately outside the claim: this audit and the
  historical research docs narrating the deleted mechanism necessarily
  contain the names, and a document match is not a runtime reader or
  writer.
- **`ps -p 81264`** (the PID recorded in `ssh-agent-proxy.pid`) returns no
  matching process — the process is not running.
- **Git history confirms the mechanism was deliberately deleted**, not
  merely superseded silently: `git log -S"ssh-agent-proxy"` surfaces
  `8cba29b refactor(devcontainer): delete dead Python SSH proxy code (#77
  stage 2)` and `5a9de96 fix(devcontainer): bound ssh-bridge failure path to
  ≤3.5s` — the custom host-TCP↔container-socket proxy that these files were
  runtime state for. It predates the Docker-Desktop-native
  `/run/host-services/ssh-auth.sock` migration this audit's Finding 3 covers
  (`docs/research/runs/research-20260409c-dockerdesktop-ssh/report.md`,
  cited directly in `devcontainer.json`'s R2 comment block) — the Apr 9 mtime
  lines up exactly with that migration date.

**Verdict: confirmed dead residue from the pre-migration SSH proxy, never
cleaned up from disk when the code was deleted.** Not a corruption risk
(nothing reads or writes them anymore), but worth a housekeeping delete —
their presence is misleading to a future reader of this directory (this
audit itself initially had to verify liveness rather than assume it from the
mechanism's obvious age).

## `guard-fail-open.log` — out of scope for this audit, not re-litigated

Not named in the round-2 brief's priority list and not a devcontainer mount
concern — it is the `hook_guard` fail-open audit log referenced in
`.claude/rules/mise-tasks-only.md` ("the hook fails OPEN on its own errors
and records every one"), a host-side Claude-Code-hook artifact unrelated to
container mounts. Flagging only that it shares the same unscoped directory,
same class of risk as Finding 5 if two hook-guard-invoking sessions ever
truncate-and-append it concurrently, but not traced further here since it
wasn't asked for and would need its own writer-code read to do justice.

## Round 2 summary table addendum

| File | Scoped? | Real collision? | Verdict | Severity |
|---|---|---|---|---|
| `hk-lint.log` | No — host-wide `Path.home()`, but container lint runs land on the (already-scoped) home volume instead, so this is HOST-clone-to-HOST-clone, not container-to-container | Yes — concurrent host-side `mise run lint` across clones/windows interleaves or clobbers the diagnostic log | Evidence-integrity risk, not disk corruption | MEDIUM |
| `dag-tick.lock` | No, and correctly so — the mechanism it guards is genuinely host-wide, unrelated to devcontainers | No | Not a devcontainer scoping issue | None |
| `sync-ghcr.io_..._dev.json` | Partially — base-image fields correctly shared; per-workspace `containers[arch]` entries are NOT, despite holding workspace-specific data | Yes — confirmed by code path AND by live single-entry file across 15+ clones | Cross-workspace state pollution → spurious rebuilds (fail-safe direction) | MEDIUM-HIGH |
| `ssh-agent-port`/`-proxy.pid`/`.target`/`host-ssh-proxy.log` | N/A — dead | No — confirmed dead, no writer/reader exists | Cleanup candidate only | None |
| `authorized_keys` | No, but idempotent content (Round 1 Finding 2) | No corruption | — | LOW |
| `doppler.env` | No (Round 1 Finding 2) | Yes — confirmed HIGH | — | HIGH |
| `guard-fail-open.log` | No (same directory) | Not traced this round — out of brief scope | Flagged only | Untraced |

---
Status: ROUND 2 COMPLETE.
