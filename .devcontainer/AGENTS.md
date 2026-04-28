<!-- Parent: ../AGENTS.md -->
<!-- Generated: 2026-04-07 | Updated: 2026-04-07 -->

# .devcontainer/ — Devcontainer Spec, Dockerfile, System-Wide mise Config

## Purpose

Defines the devcontainer image and runtime lifecycle. Two layers:

1. **Base image** — multi-stage `Dockerfile` published to
   `ghcr.io/ray-manaloto/dotfiles-devcontainer:dev` via GHA.
2. **Host-user overlay** — thin `Dockerfile.host-user` never published,
   builds locally on `mise run up` (Phase 2 work, currently minimal).

## Key Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage base image (mise bootstrap, cargo/rustup cookbook paths, build-time self-checks); known cosmetic warnings documented in comment block |
| `Dockerfile.host-user` | Thin overlay that adds the host UID/GID (low-priority Phase 2 work) |
| `devcontainer.json` | Devcontainer spec (containers.dev) — lifecycle hooks, features, volumes, dynamic naming |
| `mise-system.toml` | Dedicated Docker system-wide mise config; installed to `/usr/local/share/mise/config.toml`; includes postinstall hook for Claude Code CLI |

## Devcontainer Lifecycle

The devcontainer uses **declarative lifecycle hooks** (per containers.dev
spec), not a bootstrap shell wrapper:

- `initializeCommand` (host side): pre-creates
  `~/.local/state/dotfiles`, downloads Doppler secrets to
  `~/.local/state/dotfiles/doppler.env` (KEY=VALUE format for
  `--env-file`), then runs `dotfiles-setup docker initialize-host`.
- `onCreateCommand` (inside container, once): runs `chezmoi init --apply`
  against `/workspaces/${localWorkspaceFolderBasename}`, then chowns the
  mise-user, cargo-user, and rustup-user named volume mountpoints to
  `${USER}:${USER}`.
- `postCreateCommand` (inside container, once): chowns the Docker
  Desktop magic SSH agent socket at `/run/host-services/ssh-auth.sock`
  to the container user (needed because the socket comes in as
  `root:root 0660`), installs `authorized_keys` from the
  `/tmp/dotfiles-host-state/` bind mount for R1, seeds
  `~/.ssh/known_hosts`, and runs `scripts/devcontainer-smoke.sh` tier
  1/2/3 checks. Exit 0 required.

## Secrets Injection (Doppler)

Secrets from Doppler are injected into the container as environment
variables via Docker's `--env-file` flag. The flow:

1. `initializeCommand` (host-side) runs `doppler secrets download
   --format docker` → writes `~/.local/state/dotfiles/doppler.env`
2. `runArgs --env-file` passes the file to `docker run` → all secrets
   become container env vars at creation time
3. No doppler CLI, fnox, or service token needed inside the container

Doppler project/config defaults (`dotfiles`/`dev`) come from
`mise.toml [tasks.up].env`. Override per-clone via `mise.local.toml`:

```toml
[tasks.up]
env = { DOPPLER_CONFIG = "dev_personal" }
```

Future: migrate to mise-env-fnox with doppler provider inside the
container for runtime secret resolution (#83).

## Dynamic Naming (v6 single home volume)

Container name and home volume are templated with a workspace-path
hash so multiple clones of `dotfiles` on the same Mac get distinct
resources. `mise run up` computes `DEVCONTAINER_WORKSPACE_HASH` in the
task body via portable `sha256sum`/`shasum` detection.

- **Container:** `dotfiles-<basename>-<user>-<hash>-<ssh-port>`
- **Home volume:** `dotfiles-<basename>-<user>-<hash>-home` → `/home/${USER}`

The single home volume replaces the v5 per-directory volumes
(`mise-user`, `cargo-user`, `rustup-user`). It covers the entire user
home, so `~/.cache/mise`, `~/.cache/uv`, `~/.bash_history`,
`~/.ssh/known_hosts`, and TMPDIR all persist across `stop/up`.

**TMPDIR persistence:** `Dockerfile.host-user` sets
`ENV TMPDIR=/home/${USER}/.local/tmp` on the home volume.
`on-create.sh` sweeps files older than 30 days (atime) and prunes
empty directories per container create to bound growth.

**Accepted trade-off — data loss on rollout:** First `mise run up`
after this change orphans the old 3 volumes; runtime-installed
tools/crates/toolchains must be re-installed. `mise run prune` cleans
orphans. Explicitly accepted during initial setup; migration script
declined (see `.omc/plans/home-volume-consolidation-draft.md`).

**Reset-on-recreate:** `onCreateCommand` runs
`chezmoi init --apply --force` via `.devcontainer/scripts/on-create.sh`
on every container creation. Local edits to chezmoi-managed files
(`.bashrc`, `.zshrc`, `.profile`, `.config/mise/config.toml`) are
wiped and re-rendered from `home/`. The home volume protects
**unmanaged** state (caches, history, TMPDIR) — to change managed
files, edit the `home/` source tree instead.

SSH-agent forwarding uses Docker Desktop's native magic socket at `/run/host-services/ssh-auth.sock`. No host-side proxy. See `.omc/research/research-20260409c-dockerdesktop-ssh/`.

## Override Model

- `mise.toml [tasks.up].env` holds the defaults: `BASE_IMAGE`,
  `DOCKER_DEFAULT_PLATFORM=linux/amd64/v2`.
- `mise.local.toml` (gitignored, see `mise.local.toml.example`) overrides
  per-clone. Typical use: pin `BASE_IMAGE` to a specific SHA tag.
- No `.env.devcontainer`, no `.miserc.toml` multi-env layering. Cloud/GHA
  portability is an explicitly deferred future spec.

## IDE Workflow

Bringing the container up is **always a terminal action**:

```bash
mise run up     # start (spawns host SSH-agent proxy via initializeCommand)
mise run down   # stop (also tears down host SSH-agent proxy)
```

Attaching an IDE to the running container:

- **VS Code:** Command Palette → `Dev Containers: Attach to Running
  Container…` → pick the templated container name.
- **CLion:** `Remote Development` → `Dev Containers` → `Connect to Dev
  Container` → select the running container. **CLion caveat:** the first
  attach invokes `initializeCommand`, so launch CLion from a terminal
  (`open -a CLion` from shell, or `clion .` via the JetBrains Toolbox
  shell wrapper) to ensure it inherits `mise`, `uv`, and `$SSH_AUTH_SOCK`.

> ⚠️ **Never use `Reopen in Container` (VS Code) or the "create new dev
> container" CLion flow from a dock-launched IDE.** macOS GUI processes
> don't inherit terminal env, so `mise`, `uv`, and `$SSH_AUTH_SOCK` are
> not available to `initializeCommand`, which then fails to spawn the
> host-side SSH agent proxy.

## Mise Cookbook Paths

Base image follows the [mise docker cookbook](https://mise.jdx.dev/mise-cookbook/docker):
`MISE_DATA_DIR=/usr/local/share/mise`, `MISE_CARGO_HOME=/usr/local/share/cargo`,
`MISE_RUSTUP_HOME=/usr/local/share/rustup` (baked at image build time).
User overlays at `~/.local/share/mise`, `~/.cargo`, `~/.rustup` shadow
the system install at runtime. No custom `/opt/*` paths.

## Tool Persistence Matrix

User-overlay paths live on the single home volume
(`dotfiles-<basename>-<user>-<hash>-home`); `mise run stop && mise run up`
preserves all state. New in v6: `~/.cache/uv`, `~/.local/tmp` (TMPDIR,
30-day atime sweep in `on-create.sh`), `~/.bash_history`.

| Tool family | System install (baked) | User overlay | How to add system |
|---|---|---|---|
| mise tools | `/usr/local/share/mise/installs/` | `~/.local/share/mise/installs/` | `mise-system.toml [tools]` + base image PR |
| cargo crates | `/usr/local/share/cargo/{bin,registry}` | `~/.cargo/{bin,registry}` | base image PR; runtime `cargo install` |
| rust toolchains | `/usr/local/share/rustup/toolchains/` | `~/.rustup/toolchains/` | `mise-system.toml` `rust = "..."`; runtime `rustup install` |
| pipx tools | `/usr/local/share/mise/installs/pipx-*` | shadowed by mise overlay | `"pipx:<name>"` in `mise-system.toml` |
| apt packages | `/usr/{bin,lib,share}/...` | **none — not persistable** | `Dockerfile` apt list + base image PR |

**Apt packages have no runtime persistence story.** If a system package
is needed, it must be added to the base `Dockerfile` apt list and shipped
via a base-image PR. Do NOT rely on `sudo apt install` at runtime — it
works but the install is lost on container recreate. This is the standard
devcontainer idiom, not a project-specific gap.

## Build-time self-checks

Tools that exit 0 on no-op (mise install, apt, pip) need post-condition
`test` assertions in the same `RUN` block. Learned via 3 hotfix cycles
(PRs #59/#60/#61), validated empirically by PR-2 commit F and issue #63.
Current assertions:

- `mise ls --installed | wc -l > 0` after `mise install`
- Non-empty shims dir after `mise reshim -f`

Do NOT add `2>/dev/null` to any of these — the `build.no-stderr-suppression`
contract rejects stderr suppression. Let errors be loud.

<!-- PR blast radius reference: PR-1 (#58+hotfixes), PR-2 (#65).
     Only PR-2 commit F mutates the :dev base image. See git log. -->

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->

## SSH Agent Forwarding (Docker Desktop only)

**Runtime as of 2026-04-09:** Docker Desktop 29.3.1+. Verify
`docker context ls` → `desktop-linux *`. Do NOT switch context —
the path below is Docker-Desktop-only and silently breaks on Colima
(`abiosoft/colima#1330`, `#942`). Colima is a deferred alternative
tracked in issue #78.

Docker Desktop exposes the macOS launchd SSH agent at
`/run/host-services/ssh-auth.sock` inside every container. Bind-mount
it and set `SSH_AUTH_SOCK` via `containerEnv` (not `remoteEnv`).
Authority: `devcontainers/cli#441` (@chrmarti). Live-probe verified
2026-04-09. Research: `.omc/research/research-20260409c-dockerdesktop-ssh/`.

**R1 inbound**: `ghcr.io/devcontainers/features/sshd@1.1.0` on
internal port 2222 mapped to 4444 via `appPort`. Schema only honors
`version` + `gatewayPorts`.
