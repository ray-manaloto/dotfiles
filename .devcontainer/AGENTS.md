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
`mise.toml [tasks.up].env` (`:251`, `:277`, `:771`), templated
`{{ env.DOPPLER_CONFIG | default(value='dev_personal') }}`. Override per-clone
via a top-level `[env]` block in `mise.local.toml` — `DOPPLER_CONFIG = "dev"` —
**never** by redefining `[tasks.up]`, which replaces the whole task and strips
its `run` body (`mise.local.toml.example:9-13`).

**Aligned onto `dev_personal` 2026-08-03** (`dev` was a strict subset; its 6
extras are all host-side). ⚠️ Accepted cost: `AGE_PRIVATE_KEY`, which decrypts
the fnox age cache, now reaches the container's `--env-file`. Rationale,
measurements and the still-open contract gap:
`docs/secrets-doppler-fnox-keychain.md` § "One config".

Future: migrate to mise-env-fnox with doppler provider inside the
container for runtime secret resolution (#83).

## Dynamic Naming (v7 architecture-scoped, #677)

Names are **resolved, never composed in config**: `mise run up` evals
`dotfiles-setup devcontainer env` (`python/src/dotfiles_setup/devcontainer_names.py`)
and `devcontainer.json` interpolates whole values. The hash separates clones;
the **arch** separates amd64 from arm64.

- **Container:** `dotfiles-<basename>-<user>-<hash>-<arch>-<ssh-port>`
- **Home volume:** `dotfiles-<basename>-<user>-<hash>-<arch>-home` → `/home/${USER}`
- **SSH port:** derived from workspace **and** arch into 20000-29999 (below the
  49152+ ephemeral range); `DEVCONTAINER_SSH_PORT` still pins one per clone.
  `mise run ssh-port` / `mise run names` print them.

**Why the arch is in the NAME, not in a check:** the home volume carries
compiled output (`~/.local/share/mise/installs`, `~/.cargo`, `~/.rustup`), and
docker reuses a named volume on mount without a word — so a shared volume
interleaves two architectures' binaries and fails far from its cause. Distinct
names let docker's own uniqueness enforce it.

**Migrating a pre-#677 volume:** `mise run migrate-home-volume` (dry-run;
`-- --apply` executes) copies `…-<hash>-home` into `…-<hash>-<arch>-home` and
**never deletes the source** — `mise run prune` does, once the new container is
known good. Run it via mise: a bare CLI call *refuses*, because the old name
records no arch and an unpinned resolve would take one from the host.

It covers the whole user home, so `~/.cache/mise`, `~/.cache/uv`,
`~/.bash_history`, `~/.ssh/known_hosts` and TMPDIR persist across `stop/up`.
The v5 per-directory volumes (`mise-user`, `cargo-user`, `rustup-user`) it
replaced are orphans; `mise run prune` cleans them.

**TMPDIR persistence:** `Dockerfile.host-user` sets
`ENV TMPDIR=/home/${USER}/.local/tmp` on the home volume.
`on-create.sh` sweeps files older than 30 days (atime) and prunes
empty directories per container create to bound growth.

**Reset-on-recreate:** `onCreateCommand` runs `chezmoi init --apply
--force` on every container creation; chezmoi-managed files (`.bashrc`,
`.zshrc`, `.profile`, `.config/mise/config.toml`) are wiped and
re-rendered from `home/`. The home volume protects unmanaged state
(caches, history, TMPDIR) — to change managed files, edit `home/`.

SSH-agent forwarding uses Docker Desktop's native magic socket at `/run/host-services/ssh-auth.sock`. No host-side proxy. See `docs/research/runs/research-20260409c-dockerdesktop-ssh/`.

## Override Model

- `mise.toml [tasks.up].env` holds `BASE_IMAGE`; its **global** `[env]` holds
  `DOTFILES_PLATFORM`, the one place the target architecture is chosen (#673).
- `mise.local.toml` (gitignored, see `mise.local.toml.example`) overrides
  per-clone. Typical use: pin `BASE_IMAGE` to a specific SHA tag, or
  `DOTFILES_PLATFORM` to build for the other architecture.
- No `.env.devcontainer` layering; per-clone overrides via `mise.local.toml` only.

**The platform is ONE parameter — do not restate it** (#673). Tasks export
`DOCKER_DEFAULT_PLATFORM = "{{ env.DOTFILES_PLATFORM }}"`; `devcontainer.json`
interpolates `${localEnv:DOTFILES_PLATFORM}` at **both** `--platform` sites
(`build.options` and `runArgs`), with no `:default` fallback — a fallback would
be a second place choosing. The value lives in `mise.toml`'s global `[env]`,
mirrored for CI by `docker-bake.hcl`'s `PLATFORM` (bake jobs skip mise).

A literal anywhere else fails `mise run lint`'s `no_platform_literals`, which
also holds those two defaults equal; `build.amd64-platform-wired*` binds the
interpolations. Machine-enforced because the failure is silent: an image built
for one arch and started as another is a **false pass**, not a crash — PR #86
shipped exactly that split-brain.

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

Which paths are baked into the image, which live on the home volume, and how
to promote a tool from one to the other: **`.devcontainer/TOOL-PERSISTENCE.md`**
(a linked sibling, not an import — AGM-003 caps this file at 12,000 chars).
Headline: **apt packages have no runtime persistence** — add them to
`mise-system.toml [bootstrap.packages]` and ship a base-image PR.

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
port 2222 → `mise run ssh-port` via `appPort`. Schema only honors `version` +
`gatewayPorts`.
