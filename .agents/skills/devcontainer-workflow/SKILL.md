---
name: devcontainer-workflow
description: Bring the devcontainer up/down/build, run tier 1-3 smoke checks, and respect the thin host-user overlay invariant. Use when working with .devcontainer/, mise tasks, or the @devcontainers/cli.
---

# Devcontainer Workflow

The dotfiles devcontainer has two layers:

1. **Base image** (`ghcr.io/ray-manaloto/dotfiles-devcontainer:dev`) — built by
   CI from `.devcontainer/Dockerfile` + `.devcontainer/mise-system.toml`.
   Ships every tool needed inside the container at image-build time.
2. **Host-user overlay** (`.devcontainer/Dockerfile.host-user`) — adds the host
   user (UID/GID/name) on top of the base image. **Must stay ≤ 89 lines**
   (baseline 79 + 10 cap, enforced by hk step `dockerfile_host_user_thin_overlay`).

The user-facing workflow is `mise run up` → work inside → `mise run down`.

## Tasks

```bash
mise run build   # docker buildx bake dev-load (build base image locally)
mise run up      # devcontainer up --workspace-folder . (CLI pinned in mise.toml)
mise run down    # alias of `mise run stop` — tears the container down
mise run stop    # docker rm -f filtered on devcontainer.local_folder=$PWD
                 # (the devcontainer CLI has no `down` verb)
mise run names   # this workspace+arch's container, volume and port names
mise run ssh-port # just the derived host-side SSH port (R1)
mise run test          # uv run --project python pytest tests/ -x -q (HOST tests)
mise run pre-commit    # hk run pre-commit --all
```

## Architecture — BOTH amd64 and arm64 are first-class

`PUBLISHED_ARCHES = ("amd64", "arm64")` (`platform_target.py`). Neither is a
special case, and an arm64 container is **not** a bug — a stale amd64
assumption is. Native ARM64 on the Mac is tracked by **#678** (open;
unblocked since #676 and #677 merged).

**`DOTFILES_PLATFORM` is the one selector** (#673) — no task takes an
`--arch` flag, and no other place chooses:

```bash
mise run up                                    # the pinned default (linux/amd64/v2)
DOTFILES_PLATFORM=linux/arm64/v8 mise run up   # the other architecture
DOTFILES_PLATFORM=linux/arm64/v8 mise run names  # what THAT arch owns
```

Container name, home volume and SSH port are all **arch-scoped** (#677), so
the two coexist in one clone without colliding — the port is derived from
workspace+arch, so nothing needs configuring. Both arches really have run
here; arm64 home volumes exist alongside amd64 ones.

Three things worth carrying:

1. **The container NAME is decorative; `--id-label` is the identity.** Judging
   "is a container up?" by name has produced wrong answers before. Ask for the
   labels (`dotfiles.workspace`, `dotfiles.arch`), which is what
   `resolve_names().id_labels` and every routed `devcontainer exec` use.
   Without them an arm64 `up` finds the amd64 container.
2. **Never mount one home volume into both arches.** It carries
   architecture-specific compiled output; mixing them surfaces as
   `exec format error` or a silently wrong binary. That is *why* the arch is
   a name component rather than a runtime check.
3. **A pre-#677 volume has no arch in its name.** `mise run
   migrate-home-volume` copies one into this architecture's volume; which arch
   it lands in is decided by `DOTFILES_PLATFORM`.

## Smoke checks against a running devcontainer

```bash
scripts/devcontainer-smoke.sh                # tiers 1-3 (assumes already up)
scripts/devcontainer-smoke.sh --include-up   # also runs `devcontainer up` first
```

Tiers:

- **Tier 1** — `mise ls`, `which clang++ python uv hk`, `hk run pre-commit --all`
- **Tier 2** — `pytest 190/190`, `stat ~/.ssh ~/.Codex /workspaces/dotfiles`
- **Tier 3** — `clang++ -fsanitize=address,undefined hello.cc && ./hello`

Tier 4 (CLion remote toolchain) is manual.

`mise run smoke-exec` is a complementary **containerized real-toolchain
exec gate** (`tests/test_image_smoke_exec.py`, marked `image_exec`): it runs
the python-generated tier-1/tier-3 smoke cores against the local `:dev`
image and asserts both the happy path and a tampered FAIL. It's deselected
from the default `mise run test` (root `pytest.ini`) and needs Docker + a
current `:dev` (`mise run sync`).

## Hard rules (DO NOT VIOLATE)

1. **Never grow `Dockerfile.host-user` beyond 89 lines.** Add capabilities via
   Devcontainer Features or `devcontainer.json` mounts, never new RUN steps.
   The hk step `dockerfile_host_user_thin_overlay` will block the commit.

2. **Never render the chezmoi mise overlay on the Mac host.**
   `home/dot_config/mise/config.toml.tmpl` is gated by `home/.chezmoiignore`
   on the **built-in `chezmoi.os` fact**: `{{ if ne .chezmoi.os "linux" }}`.
   This is the canonical chezmoi pattern for multi-machine differences (see
   `.Codex/rules/use-tool-builtins.md`). Do **not** reintroduce a custom
   `is_container` data variable or env-var detection — that was reverted in
   the C10 refactor. The CI lint job has an "Assert chezmoiignore mise
   overlay hard gate" step that machine-checks this on every PR — do not
   weaken it. Belt-and-suspenders: `.Codex/settings.json` blocks
   `chezmoi apply`/`chezmoi update` on the host until Mac integration ships.
   See memory `feedback_devcontainer_only_mise_overlay.md`.

3. **Tool installs go in `.devcontainer/mise-system.toml` (image build) only.**
   `home/.chezmoiscripts/` was deleted in the devcontainer-build refactor —
   chezmoi scripts must never install tools. See memory
   `feedback_chezmoi_scripts_no_tool_install.md`.

4. **Chezmoi bootstrap lives at `onCreateCommand`.**
   `.devcontainer/scripts/on-create.sh` runs `chezmoi init --apply` from the
   workspace bind-mount (it replaced the old `install.sh` postCreate
   bootstrap). `postCreateCommand` handles the SSH agent-socket chown +
   authorized keys + smoke — keep the chezmoi step at onCreate.

## Telemetry

The async `image-analysis.yml` workflow (triggered on CI success via
`workflow_run`) emits `artifacts/build/devcontainer-metrics.json` (benchmark
fields; compressed size now read from the registry manifest, not
`docker save | gzip`). The PR-blocking `smoke-test` job runs only smoke +
Dive and no longer emits metrics.

## References

- `mise.toml` — `[tasks.up]`, `[tasks.stop]`, `[tasks.build]`, alias `down`
- `hk.pkl` — `dockerfile_host_user_thin_overlay` step
- `.github/workflows/ci.yml` — hard-gate assertion (lint job) + tier 1-3 smoke + Dive (smoke-test job)
- `.github/workflows/image-analysis.yml` — async benchmark + Trivy (on CI success)
- `home/.chezmoiignore` — the gate itself
- `scripts/devcontainer-smoke.sh` — shared tier runner
