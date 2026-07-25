# Deep Interview Spec: Devcontainer Lifecycle Restoration & Cleanup

## Metadata
- Interview ID: session-2026-04-06-k-devcontainer-lifecycle
- Rounds: 6
- Final Ambiguity Score: ~15%
- Type: brownfield
- Generated: 2026-04-07
- Threshold: 0.20
- Status: PASSED

## Clarity Breakdown
| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Goal Clarity | 0.92 | 0.35 | 0.322 |
| Constraint Clarity | 0.88 | 0.25 | 0.220 |
| Success Criteria | 0.85 | 0.25 | 0.213 |
| Context Clarity | 0.90 | 0.15 | 0.135 |
| **Total Clarity** | | | **0.890** |
| **Ambiguity** | | | **0.110** |

## Goal

Restore canonical devcontainer lifecycle wiring (per spec at containers.dev) and
unblock Mac-local devcontainer execution against the existing amd64-only ghcr base
image, while keeping the published base image and the thin host-user overlay
architecture intact.

In one sentence: **make `mise run up` succeed on this Mac, restore SSH access via
the official sshd feature, replace the install.sh script with a declarative
`onCreateCommand`, and add the small lifecycle hooks (`init`, `initializeCommand`,
smoke as `postCreateCommand`) that the current devcontainer.json is missing.**

## Constraints

1. **Container user = Mac host user** (e.g., `rmanaloto`). No `vscode` user
   anywhere. Keep the user/group rename block in `Dockerfile.host-user` —
   it stays the source of truth for in-container identity.
2. **`updateRemoteUserUID: false`** — explicit. The custom rename owns identity.
3. **amd64-only image is intentional.** Do not introduce multi-arch manifests.
   Apple Silicon emulation is via Colima VZ + Rosetta.
4. **Thin host-user overlay invariant: ≤89 lines** (`hk.pkl:dockerfile_host_user_thin_overlay`).
   Net line change in this work should be approximately zero (drops the
   `apt-get install openssh-server` block, no new RUN steps added).
5. **Base image build pipeline (`.devcontainer/Dockerfile`) is out of scope.**
   No changes to `apt-get`, mise tool list, or hk-image config.
6. **Chezmoi must run at container-create time, not at image-build time** —
   templates need runtime context (host UID, mounted home, env). This rules
   out baking chezmoi into either Dockerfile.
7. **Single PR** with logically grouped commits. Stacked PRs not used here.
8. **Keep `home/executable_run_*.sh.tmpl` files** (Session-G issue #5 footgun)
   — observe their behavior on first successful create; file follow-up issue
   if surprising. Do not delete in this session.
9. **No new top-level project directories.** Anything new lives under
   `.devcontainer/`, `scripts/`, or `.omc/`.

## Non-Goals

- Mac-host chezmoi rewire (still blocked by `.claude/settings.json`).
- Audit or refactor of `home/executable_run_*.sh.tmpl` (Session L scope).
- Multi-arch image publication.
- Migration to stock vscode user.
- Changes to `.devcontainer/Dockerfile` (the CI-built base).
- Prebuild via `devcontainer up --prebuild` (deferred until after this work).
- Replacing the architecture with `mise generate devcontainer`'s features-based pattern.
- `python/.omc/` cleanup (carryover from Session F, still deferred).

## Acceptance Criteria

- [ ] `mise run up` succeeds end-to-end on this Mac (Colima VZ+Rosetta runtime).
- [ ] `devcontainer exec --workspace-folder . bash -lc 'uname -m'` prints `x86_64`.
- [ ] `devcontainer exec --workspace-folder . bash -lc 'whoami'` prints the Mac
      host username (e.g., `rmanaloto`), not `vscode` and not `root`.
- [ ] `devcontainer exec --workspace-folder . bash -lc 'chezmoi managed | grep mise'`
      shows `dot_config/mise/config.toml` is managed (gating still works).
- [ ] `ssh ${USER}@localhost -p 4444` from the Mac host opens a shell into the
      container, authenticated by the host's existing `~/.ssh/authorized_keys`
      via the bind-mounted `~/.ssh`.
- [ ] `scripts/devcontainer-smoke.sh` runs as `postCreateCommand` and exits 0
      with no skipped checks (tier 1 / 2 / 3 all green).
- [ ] `mise run stop` tears the container down cleanly.
- [ ] `install.sh` is deleted from the repo. No references to it remain in
      `devcontainer.json`, `Dockerfile`, `Dockerfile.host-user`, or `mise.toml`.
- [ ] `Dockerfile.host-user` stays at ≤89 lines (`hk.pkl:dockerfile_host_user_thin_overlay`
      passes).
- [ ] `HK_PKL_BACKEND=pkl hk run pre-commit --all --stash none` exits 0.
- [ ] `uv run --project python pytest tests/ -x -q` passes 65/65.
- [ ] CI pipeline (lint → contract-preflight → build → smoke-test) is green on
      the PR branch.
- [ ] The findings doc `.omc/research/devcontainer-lifecycle-review-2026-04-07.md`
      is updated to retract the "install.sh runs twice" and "chezmoi never runs
      in container" errors discovered during the interview.

## Assumptions Exposed & Resolved

| Assumption | Challenge | Resolution |
|------------|-----------|------------|
| Pull failure was a docker auth issue | User said `gh auth + docker login` was already done; direct pull confirmed `no matching manifest for linux/arm64/v8` | Root cause is amd64-only image + Apple Silicon default pull arch. Fix: `DOCKER_DEFAULT_PLATFORM=linux/amd64/v2` in `mise.toml [tasks.up].env`. |
| `install.sh` runs twice (base build + postCreate) | User asked to verify before locking; grep showed `.devcontainer/Dockerfile` does NOT reference `install.sh` | install.sh runs exactly ONCE via `postCreateCommand`. Retract the duplication claim. |
| Chezmoi never runs in the container, `home/dot_config/mise/config.toml.tmpl` is dead | install.sh is the chezmoi bootstrap (`exec chezmoi init --apply --source=<script_dir>`); `.chezmoiroot` → `home`; `.chezmoiignore` gates the overlay on `chezmoi.os == "linux"` | Chezmoi DOES run, the overlay DOES land. Retract the bug claim. |
| Container user identity could be simplified to stock `vscode` | User explicit: "I don't want vscode at all, I only want 1 devcontainer user which is the mac host user" | Keep the custom rename block in `Dockerfile.host-user`. `updateRemoteUserUID: false` stays. |
| Whether to use community sshd feature (linked in prompt) or upstream | User picked option 2 = official `ghcr.io/devcontainers/features/sshd:1` | Use official feature, port 4444. |
| Whether to keep install.sh and just relocate it | Iteration frequency on chezmoi templates favors a runtime, declarative hook over a shell wrapper whose only meaningful logic (chezmoi-install fallback) is dead in this image | Delete install.sh. Replace with `onCreateCommand: chezmoi init --apply --source=/workspaces/${localWorkspaceFolderBasename} --no-tty --force`. |
| Where chezmoi should run (build time vs create time) | Frequent template updates means image-build placement would slow iteration; runtime hook also enables mid-session `devcontainer exec ... chezmoi apply` | Lifecycle hook (`onCreateCommand`), not Dockerfile RUN. |
| Whether smoke should run on every container start | Tier 1-3 checks are slow; full smoke on every start is wasteful | `postCreateCommand: scripts/devcontainer-smoke.sh` only. No `postStartCommand`. |

## Technical Context (brownfield)

### Current state (commit `611a2d6`)

**`.devcontainer/devcontainer.json`** has:
- Build via `Dockerfile.host-user` with `--platform=linux/amd64/v2` and
  `BASE_IMAGE=${localEnv:BASE_IMAGE}`.
- `remoteUser: ${localEnv:USER}`, `containerEnv` (mise paths), `forwardAgent`,
  `updateRemoteUserUID: false`.
- Mounts: workspace, `~/.ssh` (readonly), `~/.claude`, `~/.codex`, `~/.gemini`,
  `~/.local/state/dotfiles`.
- `postCreateCommand: ./install.sh`.
- VS Code customizations.

**MISSING from `devcontainer.json`** (per spec / per old `7a3ea7e`):
- `features.ghcr.io/devcontainers/features/sshd:1`
- `forwardPorts`, `appPort`
- `init: true`
- `initializeCommand`
- `onCreateCommand`
- `postStartCommand`

**`Dockerfile.host-user`** (~85 lines):
- `apt-get install openssh-server sudo` + `mkdir /run/sshd` (~5 lines, will be removed).
- Username validation.
- Group rename/create at GID 1000.
- User rename/create at UID 1000.
- Sudoers setup.
- Pre-stage home dirs for mounts.
- `ENV` block for `USER`/`HOME`/`PATH`/`MISE_TRUSTED_CONFIG_PATHS`.

**`install.sh`** (38 lines): chezmoi bootstrap + trust mise + `exec chezmoi init --apply`.
Will be DELETED.

**`mise.toml [tasks.up]`**: env scopes `BASE_IMAGE=ghcr.io/ray-manaloto/dotfiles-devcontainer:dev`.
Will gain `DOCKER_DEFAULT_PLATFORM=linux/amd64/v2`.

### Key project invariants (from CLAUDE.md / project memory)

- Thin overlay cap: 89 lines (hk-enforced).
- chezmoi multi-machine via `chezmoi.os` built-in fact (not custom env-var detection).
- chezmoi apply on Mac host blocked by `.claude/settings.json`.
- Colima VZ+Rosetta is the runtime; Docker Desktop is not used.
- `home/executable_run_*.sh.tmpl` (2 files) — Session-G issue #5 footgun, deferred.

## Implementation Outline

### Commit 1 — `fix(devcontainer): set DOCKER_DEFAULT_PLATFORM for the up task`
- Edit `mise.toml`: add `DOCKER_DEFAULT_PLATFORM = "linux/amd64/v2"` to `[tasks.up].env`.
- Commit msg explains the implicit-pull-vs-build-options gap.

### Commit 2 — `feat(devcontainer): replace install.sh with onCreateCommand chezmoi apply`
- Delete `install.sh` from repo root.
- `devcontainer.json`: replace `postCreateCommand: ./install.sh` with
  `onCreateCommand: chezmoi init --apply --source=/workspaces/${localWorkspaceFolderBasename} --no-tty --force`.
- (`postCreateCommand` slot freed for the smoke script in commit 4.)
- Update `CLAUDE.md` to remove the install.sh reference.
- Update `.omc/research/devcontainer-lifecycle-review-2026-04-07.md` to retract
  the "install.sh runs twice" + "chezmoi never runs" errors.

### Commit 3 — `feat(devcontainer): restore SSH via official sshd feature`
- `devcontainer.json`: add
  ```jsonc
  "features": {
    "ghcr.io/devcontainers/features/sshd:1": {
      "username": "${localEnv:USER}",
      "port": "4444",
      "startNow": true
    }
  },
  "appPort": ["4444:4444"],
  "forwardPorts": [4444]
  ```
- `Dockerfile.host-user`: remove the `apt-get install openssh-server sudo`
  RUN block + the `mkdir /run/sshd`. (Sudo install handled either by feature
  composition or by retaining sudo install — verify community/official sshd
  feature semantics.)
- Verify `Dockerfile.host-user` is still ≤89 lines.

### Commit 4 — `feat(devcontainer): add init, initializeCommand, postCreateCommand smoke`
- `devcontainer.json`: add
  ```jsonc
  "init": true,
  "initializeCommand": "mkdir -p ~/.ssh ~/.claude ~/.codex ~/.gemini ~/.local/state/dotfiles && touch ~/.ssh/config ~/.ssh/known_hosts ~/.ssh/authorized_keys",
  "postCreateCommand": "scripts/devcontainer-smoke.sh"
  ```
- Verify smoke script exists and is executable; if not, that becomes a sub-task
  of this commit (write or move it).
- Run full local validation: `mise run up && devcontainer exec ... uname -m && ... whoami && ssh -p 4444 ...`

### Validation gate before push
- `HK_PKL_BACKEND=pkl hk run pre-commit --all --stash none` → 0
- `uv run --project python pytest tests/ -x -q` → 65/65
- `mise run up` → success on this Mac
- `devcontainer exec --workspace-folder . scripts/devcontainer-smoke.sh` → exit 0
- `ssh ${USER}@localhost -p 4444 'echo hello'` → `hello`
- `mise run stop` → success
- `gh pr checks --watch` → all green

## Ontology (Key Entities)

| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| Devcontainer | core domain | name, build, mounts, features, lifecycle hooks | builds via Dockerfile.host-user; uses Base Image |
| Base Image | core domain | tag, registry, platform=linux/amd64/v2 | published by CI to ghcr; consumed by Dockerfile.host-user FROM |
| Host-User Overlay | core domain | line cap (89), user/group rename, sudoers, home staging | thin layer on Base Image; owned by `Dockerfile.host-user` |
| Lifecycle Hook | supporting | initializeCommand, onCreateCommand, postCreateCommand, postStartCommand | runs at specific points; declarative in `devcontainer.json` |
| Chezmoi Source | core domain | `home/`, `.chezmoiroot`, `.chezmoiignore`, templates | applied at container-create via `onCreateCommand` |
| SSH Feature | supporting | port=4444, username, startNow | installed via feature; consumes host `~/.ssh` bind mount |
| Smoke Script | supporting | tier 1/2/3 checks | runs as `postCreateCommand`, exits 0 on success |
| Mise Task | supporting | up, stop, build | wraps `devcontainer up/exec/rm`; sets task-scoped env |
| Install Script | DEPRECATED | (38-line chezmoi bootstrap) | DELETED in commit 2; replaced by `onCreateCommand` |

## Ontology Convergence

| Round | Entity Count | New | Changed | Stable | Stability Ratio |
|-------|-------------|-----|---------|--------|----------------|
| 1 | 4 | 4 | - | - | N/A (first round) |
| 2 | 5 | 1 | - | 4 | 80% |
| 3 | 6 | 1 | - | 5 | 83% |
| 4 | 7 | 1 | - | 6 | 86% |
| 5 | 8 | 1 | - | 7 | 88% |
| 6 | 9 | 1 | 1 (Install Script → DEPRECATED) | 7 | 89% |

Stable convergence — entities only added/clarified, never replaced.

## Spec Amendments (post-round-6, after user-added success criteria)

The following amendments **supersede** earlier sections where they conflict.

### Amended Goal

Restore canonical devcontainer lifecycle wiring AND adopt the mise canonical
"system tools baked + user tools on a named volume" pattern from the mise
docker cookbook, so that:

- `mise install --system` tools are baked at `/usr/local/share/mise/installs`
  (cookbook canonical, replacing the repo's custom `/opt/mise`).
- User-installed tools land at `/home/${USER}/.local/share/mise/installs` and
  **shadow** system tools per cookbook semantics.
- A named Docker volume mounted at `/home/${USER}/.local/share/mise` makes
  user-installed tools survive `mise run stop && mise run up`.
- Container and volume names are dynamic and template-friendly so multiple
  devcontainers can run side-by-side on this Mac (one per project).

### Amended Constraints

Replaces / supplements the original constraint list:

- **Constraint 5 (REVERSED):** `.devcontainer/Dockerfile` (the CI-built base
  image) is **now in scope.** It must be refactored to use cookbook-canonical
  mise paths (`/usr/local/share/mise`, `/usr/local/bin/mise`) and drop the
  custom `/opt/mise` data dir. Affects the published ghcr image — CI rebuild
  + republish required.
- **New Constraint 10:** Container name and volume names must be templated
  via `${localWorkspaceFolderBasename}`, `${localEnv:USER}`, and
  `${localEnv:DEVCONTAINER_SSH_PORT}` so multiple projects on this Mac can
  run devcontainers in parallel.
- **New Constraint 11:** SSH port is per-clone overridable via
  `mise.local.toml` (gitignored), with default `4444` set in
  `mise.toml [tasks.up].env`. No `.env.devcontainer`, no `.miserc.toml`
  multi-env overlays — those are deferred to a future "cloud environment"
  spec.
- **New Constraint 12:** Internal sshd port stays a literal `4444` in the
  `sshd` feature config and inside the container; only the host-side port
  mapping (`appPort`) is dynamic via `${localEnv:DEVCONTAINER_SSH_PORT}`.
  This is what enables port collision recovery without losing the volume
  (volume name does NOT include the port).
- **New Constraint 13:** GitHub SSH access (`ssh -T git@github.com`) inside
  the container must work using the host's existing keys via the readonly
  `~/.ssh` bind mount + `forwardAgent: true`.
- **New Non-Goal 7:** Cloud / GHA portability of the devcontainer (running
  as root in CI for C++ builds) is acknowledged as a future direction but
  is **explicitly deferred**. No `vscode`/`runner`/`USER` fallback chains
  in this spec. GHA-as-root will be a follow-up "cloud environment" spec
  that introduces `.miserc.toml` + `mise.{env}.toml` overlays.

### Amended Acceptance Criteria (additions)

- [ ] `mise install --system` is the install mode used in
  `.devcontainer/Dockerfile`. Tool installs land at
  `/usr/local/share/mise/installs/...`, not `/opt/mise/installs/...`.
- [ ] `MISE_DATA_DIR=/opt/mise` is removed from `containerEnv` in
  `devcontainer.json`. Cookbook envs (`MISE_INSTALL_PATH=/usr/local/bin/mise`,
  default mise data dir) replace it where needed.
- [ ] A named Docker volume is mounted at
  `/home/${localEnv:USER}/.local/share/mise`. Volume name follows the
  template `dotfiles-${localWorkspaceFolderBasename}-${localEnv:USER}-mise-user`.
- [ ] Inside the container, `mise install <tool>` (without `--system`)
  installs into `/home/${USER}/.local/share/mise/installs/<tool>`, the
  install survives `mise run stop && mise run up`, and `mise ls` shows
  the user-installed version taking precedence over any baked system
  version of the same tool.
- [ ] Container name resolves to
  `dotfiles-${localWorkspaceFolderBasename}-${localEnv:USER}-${localEnv:DEVCONTAINER_SSH_PORT}`
  at runtime. Verifiable via `docker ps --format '{{.Names}}'`.
- [ ] `${localEnv:DEVCONTAINER_SSH_PORT}` defaults to `4444` from
  `mise.toml [tasks.up].env`, can be overridden by `mise.local.toml`,
  and the override flows through to `appPort` and the container name.
- [ ] `mise.local.toml.example` is checked in. `mise.local.toml` and
  `mise.*.local.toml` are gitignored (add to `.gitignore` if absent).
- [ ] `ssh -T git@github.com` from inside the container returns
  `Hi rmanaloto! You've successfully authenticated, but GitHub does not
  provide shell access.` (or equivalent for the Mac host's GitHub user).
  This check is added to `scripts/devcontainer-smoke.sh` as a tier 3
  backend/lifecycle check.
- [ ] `Dockerfile.host-user`'s home-staging block creates
  `/home/${USER}/.local/share/mise` with `${USER}:${USER}` ownership so
  the named volume mounts cleanly on first create.

### Amended Implementation Outline

Replaces the 4-commit sequence in the original outline. **8 commits**, all
in one PR.

1. **`fix(devcontainer): set DOCKER_DEFAULT_PLATFORM for the up task`** —
   add `DOCKER_DEFAULT_PLATFORM = "linux/amd64/v2"` to `mise.toml [tasks.up].env`.
   Unblocks Mac-local pull immediately.
2. **`feat(devcontainer): introduce mise.local.toml for per-clone overrides`** —
   add `DEVCONTAINER_SSH_PORT = "4444"` default to `mise.toml [tasks.up].env`,
   create `mise.local.toml.example`, update `.gitignore`.
3. **`refactor(base-image): adopt mise cookbook canonical paths`** —
   `.devcontainer/Dockerfile`: drop `MISE_DATA_DIR=/opt/mise` /
   `MISE_CONFIG_DIR=/etc/mise`; set `MISE_INSTALL_PATH=/usr/local/bin/mise`;
   ensure `mise install --system` is the install mode (likely already via
   `MISE_INSTALL_MODE=system`); chmod the cookbook paths
   (`/usr/local/share/mise`) instead of `/opt/mise`. Update
   `mise-system.toml` install location if needed. Also update
   `devcontainer.json` `containerEnv` block to drop the `/opt/mise` overrides.
   This commit triggers a CI base-image republish — verify the new image is
   functional via the existing CI smoke-test job before proceeding.
4. **`feat(devcontainer): replace install.sh with onCreateCommand chezmoi apply`** —
   delete `install.sh`, replace `postCreateCommand: ./install.sh` with
   `onCreateCommand: chezmoi init --apply --source=/workspaces/${localWorkspaceFolderBasename} --no-tty --force`.
   `postCreateCommand` slot freed for the smoke script in commit 7. Update
   `CLAUDE.md` to drop the install.sh reference. Update findings doc to
   retract the "install.sh runs twice" + "chezmoi never runs" errors.
5. **`feat(devcontainer): restore SSH via official sshd feature`** — add
   `features.ghcr.io/devcontainers/features/sshd:1` (port literal `4444`,
   `username: ${localEnv:USER}`, `startNow: true`); add `appPort:
   ["${localEnv:DEVCONTAINER_SSH_PORT}:4444"]` and `forwardPorts: [4444]`;
   remove the `apt-get install openssh-server` block from
   `Dockerfile.host-user`; verify overlay still ≤89 lines.
6. **`feat(devcontainer): dynamic container + volume naming`** — add
   `name`, `runArgs --name`, and the `mise-user` volume mount, all using
   the templated form. Update `Dockerfile.host-user` home-staging block to
   pre-create `/home/${USER}/.local/share/mise` with correct ownership.
7. **`feat(devcontainer): add init, initializeCommand, postCreateCommand smoke`** —
   `init: true` (tini), `initializeCommand` for host mkdir/touch of mount
   targets including `~/.ssh/{config,known_hosts,authorized_keys}`,
   `postCreateCommand: scripts/devcontainer-smoke.sh`. If
   `scripts/devcontainer-smoke.sh` doesn't exist or doesn't cover
   tier 1/2/3 + the new `ssh -T git@github.com` AC, write/extend it
   in this commit.
8. **`docs(devcontainer): document the lifecycle, naming, and override
   model in CLAUDE.md`** — single-paragraph update to the project
   `CLAUDE.md`'s "Architecture" section pointing at the new files and
   the cookbook pattern.

### Amended Validation Gate

Before pushing the PR:

- `HK_PKL_BACKEND=pkl hk run pre-commit --all --stash none` → 0
- `uv run --project python pytest tests/ -x -q` → 65/65
- `mise run build` → success (rebuild base image locally to verify cookbook
  refactor before relying on CI republish)
- `mise run up` → success on this Mac
- `docker ps --format '{{.Names}}'` → matches templated name
- `docker volume ls --format '{{.Name}}' | grep mise-user` → volume exists
- `devcontainer exec ... whoami` → host username
- `devcontainer exec ... uname -m` → `x86_64`
- `devcontainer exec ... mise --version && mise ls` → tools listed,
  paths under `/usr/local/share/mise/installs`
- `devcontainer exec ... bash -c 'mise install --version' && mise install <some-tool>` →
  installs to `/home/${USER}/.local/share/mise/installs/<tool>`, persists
  after `mise run stop && mise run up`
- `ssh ${USER}@localhost -p ${DEVCONTAINER_SSH_PORT} 'echo hello'` → `hello`
- `devcontainer exec ... ssh -T git@github.com` → `Hi <user>! ...`
- `scripts/devcontainer-smoke.sh` (in-container) → exit 0 with no skipped checks
- `mise run stop` → success
- `gh pr checks --watch` after push → all green (CI republishes the base
  image; smoke-test job validates the cookbook refactor end-to-end)

### Amended Ontology

| Entity | Type | Fields | Relationships |
|--------|------|--------|---------------|
| Devcontainer | core | name (templated), build, mounts, features, lifecycle hooks | builds via Dockerfile.host-user; uses Base Image |
| Base Image | core | tag, registry, platform=linux/amd64/v2, mise paths (cookbook canonical) | published by CI to ghcr; consumed by Dockerfile.host-user FROM |
| Host-User Overlay | core | line cap (89), user/group rename, sudoers, home staging incl. mise dir | thin layer on Base Image; owned by `Dockerfile.host-user` |
| Lifecycle Hook | supporting | initializeCommand, onCreateCommand, postCreateCommand | declarative in `devcontainer.json` |
| Chezmoi Source | core | `home/`, `.chezmoiroot`, `.chezmoiignore` | applied via `onCreateCommand` |
| SSH Feature | supporting | port literal 4444 (internal), startNow, username | installed via feature; consumes host `~/.ssh` bind mount |
| Smoke Script | supporting | tier 1/2/3 + `ssh -T git@github.com` | runs as `postCreateCommand` |
| Mise Task | supporting | up, stop, build, env (BASE_IMAGE, DOCKER_DEFAULT_PLATFORM, DEVCONTAINER_SSH_PORT) | wraps `devcontainer up/exec/rm` |
| **Mise System Install** | core (NEW) | path: `/usr/local/share/mise/installs`, baked at base build | consumed by all users, shadowed by user installs |
| **Mise User Install** | core (NEW) | path: `/home/${USER}/.local/share/mise/installs`, on named volume | shadows system install, survives recreation |
| **Named Volume (mise-user)** | core (NEW) | name templated by project+user, target `/home/${USER}/.local/share/mise` | persists user mise installs across recreation |
| **mise.local.toml** | supporting (NEW) | gitignored, layered atop mise.toml | per-clone overrides for `DEVCONTAINER_SSH_PORT` etc. |
| Install Script | DEPRECATED | (38-line chezmoi bootstrap) | DELETED in commit 4 |

### Amended Final Ambiguity

After 7 effective interview rounds + cookbook research + naming clarification:
**~9%** (well below 20% threshold). Status: **PASSED**.

## GitHub repos touched

- [devcontainers/spec](https://github.com/devcontainers/spec) — canonical lifecycle order, `init`, `updateRemoteUserUID`, variables
- [devcontainers/cli](https://github.com/devcontainers/cli) — `up --prebuild`, no `down` verb
- [devcontainers/features](https://github.com/devcontainers/features) — official `sshd` feature
- [devcontainer-community/devcontainer-features](https://github.com/devcontainer-community/devcontainer-features) — community sshd alternative (not chosen)
- [jdx/mise](https://github.com/jdx/mise) — `mise generate devcontainer`, task env scoping
- [twpayne/chezmoi](https://github.com/twpayne/chezmoi) — `chezmoi init --apply --source`, `.chezmoiroot`, multi-machine via `chezmoi.os`
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — repo under change (`611a2d6` → target)
