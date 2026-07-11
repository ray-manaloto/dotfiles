# R2 Step 0 — Repo inventory (re-verified, remote session 2026-07-09)

Provenance: the original Explore-agent inventory from the planning session
lives on Ray's Mac (plan-mode forbade the write there). This report is a
**re-verified reconstruction** produced in the remote execution container
from the fresh clone at branch `main`, with file:line evidence read
directly. It is the grounding input for research runs A–G
(`research-20260709-r2-*`).

## Secrets (baseline for Run E)

- Doppler is the live devcontainer secrets path:
  `.devcontainer/devcontainer.json:198` `initializeCommand` runs
  `doppler secrets download --format docker --no-file --project
  "${DOPPLER_PROJECT:-dotfiles}" --config "${DOPPLER_CONFIG:-dev}"` →
  `~/.local/state/dotfiles/doppler.env`; `runArgs --env-file` at
  `devcontainer.json:84-88` injects it into the container. No doppler CLI
  inside the container.
- Enforcement: contract `build.doppler-secrets-wired`
  (`python/verification/suites.toml:443-452`); smoke tier-2 canaries
  (`scripts/devcontainer-smoke.sh:91-104`, expects ≥3 of
  DOPPLER_PROJECT/DOPPLER_CONFIG/DOPPLER_ENVIRONMENT/EXA_API_KEY/
  GITHUB_TOKEN/BRAVE_API_KEY/GEMINI_API_KEY); mise `verify-secrets` S1
  (`mise.toml:519-540`). Defaults `DOPPLER_PROJECT=dotfiles`,
  `DOPPLER_CONFIG=dev` come from `mise.toml [tasks.up].env`
  (`mise.toml:186,212`).
- fnox already ships in the image runtime tier
  (`.devcontainer/mise-runtime.toml:41`, `"fnox" = "latest"`).
- Issue #83 already tracks "migrate to mise-env-fnox with doppler provider
  inside the container for runtime secret resolution"
  (`.devcontainer/AGENTS.md` § Secrets Injection).
- R2 SSH outbound: Docker Desktop magic socket
  `/run/host-services/ssh-auth.sock` bind-mount (`devcontainer.json:96`),
  `SSH_AUTH_SOCK` via containerEnv (`devcontainer.json:189`), chown in BOTH
  `postCreateCommand` (`:200`) and `postStartCommand` (`:207`) because the
  socket reverts to root:root on DD restart. Docker-Desktop-only
  (Colima gap: issue #78, abiosoft/colima#1330/#942).
- CI secrets: least-privilege GITHUB_TOKEN blocks; `refresh.yml` mints a
  GitHub App token (REFRESH_APP_ID + REFRESH_APP_PRIVATE_KEY,
  `persist-credentials: false` pattern) so its PRs fire `pull_request` CI;
  bake `secret id=github_token`. No 1Password/Vault/Infisical anywhere.

## Updater topology (baseline for Run C)

- `refresh.yml`: daily cron 00:00 America/Chicago
  (`refresh.yml:38-39`), one `lock-refresh` job regenerating the committed
  lockfiles via the `./.github/actions/lock-refresh` composite
  (`refresh.yml:82`), PR branch `chore/lock-refresh` (`:106`) via App token,
  **auto-merges** (squash) once `ci-gate` passes
  (`.github/workflows/AGENTS.md:145-155`).
- `ci.yml`: nightly cron 02:00 (`ci.yml:10`) republishes `:dev`/`:latest`
  on the current pins. Two staggered crons are deliberate — do NOT collapse
  (issue #116; `.github/workflows/AGENTS.md:131-143`).
- Hosted Renovate (`renovate.json`): extends `github>jdx/renovate-config`;
  native managers npm/cargo/mise/dockerfile/docker-compose/devcontainer/
  github-actions; minor/patch/digest **automerge**; 6 surviving
  customManagers — hk pkl schema pin, `.chezmoiversion`, clang-p2996 git
  SHA (git-refs datasource), gcc-latest dated .deb (custom HTML datasource
  on jwakely index, `minimumReleaseAgeBehaviour: timestamp-optional`),
  ubuntu digest in bake+Dockerfile lockstep, MISE_VERSION installer pin.
  Devcontainer features deliberately NOT digest-pinned (PR #187 breakage,
  `renovate.json:15-18`).
- Dependabot: `interval: "cron"` enforces a **24h minimum**
  (`.github/workflows/AGENTS.md:165-171`).
- Retired: Phase D on-demand p2996 dispatch build (zero lifetime runs,
  retired 2026-07-07; resurrectable from git history).

## Image / build (baseline for Run B)

- `docker-bake.hcl` targets: `dev` (:77), `base` (:122), `p2996-cache`
  (:146), `dev-load` (:163), `validate` (:170), plus `_common`/metadata.
  Variables include IMAGE_REF consolidation, PLATFORM
  (linux/amd64/v2), CLANG_P2996_REF (:47).
- Four mise tool tiers:
  1. root `mise.toml` — ~30 host tools (renovate npm, agnix, ast-grep,
     docker-cli, opencode, claude-flow, …);
  2. `.config/mise/conf.d/shared.toml` — 20 exact-pinned tools shared
     host↔image (#160 T5);
  3. `.devcontainer/mise-system.toml` — image BASE tier, all-latest +
     `mise-system.lock`, `[bootstrap.packages]` apt set (#160 T4), 7d
     `minimum_release_age`;
  4. `.devcontainer/mise-runtime.toml` — image RUNTIME tier
     (`config.runtime.toml`, MISE_ENV=runtime), all-latest +
     `mise-runtime.lock`; carries fnox, gh cli, claude-code, gemini-cli,
     codex, sccache, conan, meson, turso/libsql;
     `minimum_release_age_excludes` for the fast AI CLIs
     (`mise-runtime.toml:33`).
  Tier split rationale: editing runtime tier rebuilds only the thin runtime
  stage, not the ~30-min base (`mise-runtime.toml:10-12`) — the natural
  fork seam for a two-image topology.
- Interactive overlay tier (5th, per-user): `home/dot_config/mise/config.toml.tmpl`,
  chezmoi-rendered, free on latest.
- CI pipeline: ci.yml (thin caller) → lint → contract-preflight → changes →
  reusable build-publish.yml (base-prep → p2996-prep → dev-prep → build →
  smoke-test → dev-tag) → ci-gate; promote retags on main; benchmark +
  Trivy async in image-analysis.yml.

## Research infrastructure (baseline for Runs D/E/G)

- Mintlify cache at `docs/research/mintlify-cache/` (llms.txt +
  llms-full.txt per repo): jdx/{mise,hk,fnox,mise-env-fnox,pitchfork,pklr,
  mise-action}, twpayne/chezmoi, starship/starship,
  devcontainers/{cli,spec,features,images}, wagoodman/dive,
  knowsuchagency/mcp2cli, yeachan-heo/oh-my-claudecode. Catalog:
  `docs/research/mintlify-catalog.md` (queue: lima-vm/lima,
  abiosoft/colima).
- NOT cached: astral (uv/ruff/ty), Doppler, Renovate, graphify,
  anthropics/* — remote fetch required; queue catalog additions.
- `/graphify` skill is a **user-level** skill on Ray's Mac
  (`~/.claude/skills/graphify/SKILL.md`) — absent in the remote container
  (verified); KB pilot must run locally.
- `.omc/**` is NOT in the repo `.gitignore` (only `.omc/state/` is,
  `.gitignore:41`); research/plans artifacts are committable to a branch.
  On Ray's Mac they are excluded per-clone (rule
  `research-repo-enumeration.md`), which does not block checkout of
  tracked files.

## Environment constraints of this execution session (remote container)

- Bash entirely blocked: the PreToolUse hook
  (`.claude/settings.json:9-20`, `uv run --project python dotfiles-setup
  hook pretooluse`) cannot start — no Python ≥3.14 in the container — and
  the harness fails closed. All research runs use
  WebSearch/WebFetch/Read/Grep/Write; git delivery via GitHub MCP.
- `.omc/` from Ray's Mac (yesterday's
  `research-20260709-unified-image/` run, 104 agents) is not present;
  its load-bearing claims are carried into Runs A/B as claims to
  RE-verify from scratch, per the approved plan.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — all facts above read directly from the working tree at main.
