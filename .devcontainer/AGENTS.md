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
| `mise-system.toml` | BASE tool tier (#160 T9) → `/usr/local/share/mise/config.toml`. `[bootstrap.packages]` declares the apt set installed by `mise bootstrap packages apply` (#160 T4); the 20 host↔image shared tools come from the repo `.config/mise/conf.d/shared.toml` COPYd to `conf.d/` and merged (#160 T5) |
| `mise-runtime.toml` | RUNTIME tool tier (#160 T9/T10) → `config.runtime.toml`, installed in the `devcontainer-runtime` stage under `MISE_ENV=runtime` (baked ENV). The interactive OVERLAY tier lives in `home/dot_config/mise/config.toml.tmpl`, eager-installed per-user by `on-create.sh` |
| `mise-system.lock` + `mise-runtime.lock` + `P2996-CACHE.md` | Native mise lockfiles (rattler conda sha256 + version pins, linux-x64) per tier; COPYd to `mise.lock` / `mise.runtime.lock` beside the configs, consumed by `mise install --system --locked`; base lock digest feeds the base content-hash, runtime pair feeds dev-hash. Regenerate via the CI `lock-refresh` job |

## Devcontainer Lifecycle

The devcontainer uses **declarative lifecycle hooks** (containers.dev
spec), not a bootstrap shell wrapper:

- `initializeCommand` (host): pre-creates `~/.local/state/dotfiles`,
  downloads Doppler secrets to `doppler.env` (KEY=VALUE for
  `--env-file`), then runs `dotfiles-setup docker initialize-host`.
- `onCreateCommand` (in container, once): `chezmoi init --apply`
  against `/workspaces/${localWorkspaceFolderBasename}`, chowns
  named-volume mountpoints to `${USER}:${USER}`.
- `postCreateCommand` (once): chowns the magic SSH socket, installs
  `authorized_keys` from `/tmp/dotfiles-host-state/` for R1, seeds
  `~/.ssh/known_hosts`, runs `scripts/devcontainer-smoke.sh` tier 1/2/3
  (exit 0 required). `postStartCommand` re-chowns the socket on EVERY
  start (it reverts to root:root on DD restart) — R2's durable fix.

## Secrets Injection (Doppler)

`initializeCommand` (host-side) runs `doppler secrets download
--format docker` → `~/.local/state/dotfiles/doppler.env` →
`runArgs --env-file` → container env vars. No doppler CLI, fnox, or
service token needed inside the container.

Doppler project/config defaults (`dotfiles`/`dev_personal`) come from
`mise.toml [tasks.up].env` (`:251`, `:277`, `:771`). Override per-clone via
`mise.local.toml`: `[tasks.up] env = { DOPPLER_CONFIG = "dev" }`.

**Aligned onto `dev_personal` 2026-08-03.** `dev` (43) was a strict subset of
`dev_personal` (49) — measured, 0 names in `dev` absent from `dev_personal`. The
6 extras all have host-side consumers (fnox's age key, the mise/renovate token
aliases, an NVIDIA benchmark key), so the container never used them; what the
split cost was a second name set that **nothing asserts** — `doctor.toml` models
`dev_personal` only, and `build.doppler-secrets-wired` names no config at all.
The accepted trade-off is that `AGE_PRIVATE_KEY` — the key that decrypts the
fnox age cache — now reaches the container's `--env-file`.

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
after the v5→v6 change orphans the old volumes; runtime-installed
tools/crates/toolchains must be re-installed. `mise run prune` cleans
orphans. (See `.agent/plans/home-volume-consolidation-draft.md`.)

**Reset-on-recreate:** `onCreateCommand` runs `chezmoi init --apply
--force` on every container creation; chezmoi-managed files (`.bashrc`,
`.zshrc`, `.profile`, `.config/mise/config.toml`) are wiped and
re-rendered from `home/`. The home volume protects unmanaged state
(caches, history, TMPDIR) — to change managed files, edit `home/`.

SSH-agent forwarding uses Docker Desktop's native magic socket at `/run/host-services/ssh-auth.sock`. No host-side proxy. See `docs/research/runs/research-20260409c-dockerdesktop-ssh/`.

## Override Model

- `mise.toml [tasks.up].env` holds the defaults: `BASE_IMAGE`,
  `DOCKER_DEFAULT_PLATFORM=linux/amd64/v2`.
- `mise.local.toml` (gitignored, see `mise.local.toml.example`) overrides
  per-clone. Typical use: pin `BASE_IMAGE` to a specific SHA tag.
- No `.env.devcontainer` layering; per-clone overrides via `mise.local.toml` only.

**Platform tag must match in BOTH places.** Update both
`mise.toml [tasks.up].env.DOCKER_DEFAULT_PLATFORM` AND
`devcontainer.json build.options[]` (e.g.
`["--platform=linux/amd64/v2"]`). The `build.amd64-platform-wired`
contract checks the latter; missing it fails `contract-preflight`.

## IDE Workflow

Bringing the container up is **always a terminal action**: `mise run
up` (start) / `mise run down` (stop). Both spawn / tear down the host
SSH-agent proxy via `initializeCommand`.

Attaching an IDE to the running container:

- **VS Code:** Command Palette → `Dev Containers: Attach to Running
  Container…` → pick the templated container name.
- **CLion:** `Remote Development` → `Dev Containers` → `Connect to Dev
  Container` → select the running container. **CLion caveat:** the
  first attach invokes `initializeCommand`, so launch CLion from a
  terminal so it inherits `mise`, `uv`, and `$SSH_AUTH_SOCK`.

> ⚠️ **Never `Reopen in Container` (VS Code) or "create new dev
> container" (CLion) from a dock-launched IDE.** macOS GUI processes
> don't inherit terminal env; `initializeCommand` then fails to spawn
> the host-side SSH agent proxy.

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
| mise tools | `/usr/local/share/mise/installs/` | `~/.local/share/mise/installs/` | `mise-system.toml` (base) / `mise-runtime.toml` (runtime) + image PR; overlay tier: `home/dot_config/mise/config.toml.tmpl` |
| cargo crates | `/usr/local/share/cargo/{bin,registry}` | `~/.cargo/{bin,registry}` | base image PR; runtime `cargo install` |
| rust toolchains | `/usr/local/share/rustup/toolchains/` | `~/.rustup/toolchains/` | `mise-system.toml` `rust = "..."`; runtime `rustup install` |
| pipx tools | `/usr/local/share/mise/installs/pipx-*` | shadowed by mise overlay | `"pipx:<name>"` in `mise-system.toml` |
| apt packages | `/usr/{bin,lib,share}/...` | **none — not persistable** | `mise-system.toml [bootstrap.packages]` + base image PR |

**Apt packages have no runtime persistence.** Add system packages to
`mise-system.toml [bootstrap.packages]` and ship via a base-image PR.
`sudo apt install` at runtime works but is lost on container recreate.

## Build-time self-checks

Tools that exit 0 on no-op (mise install, apt, pip) need post-condition
`test` assertions in the same `RUN` block. Learned via 3 hotfix cycles
(PRs #59/#60/#61; PR-2 commit F, issue #63). Current assertions:

- `mise bootstrap packages status --json --missing` after `apply` (#160 T4)
- `mise ls --installed | wc -l > 0` after `mise install`
- Non-empty shims dir after `mise reshim -f`

Always let these checks fail loudly — the `build.no-stderr-suppression`
contract rejects stderr suppression, so do not add `2>/dev/null`.

## Mise installer & system-config gotchas

- **Don't set `MISE_INSTALL_ARCH=x86_64`** — `curl https://mise.run | sh`
  maps `uname -m == x86_64` → suffix `linux-x64` (not `linux-x86_64`);
  setting the var to `x86_64` makes the installer 404. Omit it or use
  `x64`. (PR #86 commit `11d1b11`.)
- **Don't re-run `mise install --system` in `Dockerfile.host-user`** —
  it writes to `/usr/local/share/mise` (owned `mise:mise`); after the
  `USER` switch the non-root user isn't in the `mise` group, so the
  install either fails on perms or silent no-ops. Base stage already
  baked the system tools. (PR #86 commit `1fab490`.)
- **Avoid `conda:imagemagick`** — pulls a heavy GUI dep chain
  (adwaita-icon-theme) with duplicate-record solve failures in
  conda-forge. Use apt's `imagemagick` package instead. (PR #86 commit
  `d116918`.)

<!-- PR blast radius reference: PR-1 (#58+hotfixes), PR-2 (#65).
     Only PR-2 commit F mutates the :dev base image. See git log. -->

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->

## SSH Agent Forwarding (Docker Desktop only)

**Runtime as of 2026-04-09:** Docker Desktop 29.3.1+. Verify
`docker context ls` → `desktop-linux *`. Do NOT switch context —
the magic socket path is Docker-Desktop-only and silently breaks on
Colima (`abiosoft/colima#1330`, `#942`; tracked in issue #78).

DD exposes the macOS launchd SSH agent at
`/run/host-services/ssh-auth.sock`. Bind-mount it and set
`SSH_AUTH_SOCK` via `containerEnv` (not `remoteEnv`). Authority:
`devcontainers/cli#441`. Research:
`docs/research/runs/research-20260409c-dockerdesktop-ssh/`.

**R1 inbound**: `ghcr.io/devcontainers/features/sshd@1.1.0` on internal
port 2222 → 4444 via `appPort`. Schema only honors `version` +
`gatewayPorts`.
