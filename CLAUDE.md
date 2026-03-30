# Dotfiles — macOS Developer Environment

## Project
Chezmoi-managed dotfiles with devcontainer support. Two build types:
1. **Local linting** (hk + mise): `mise install && hk run pre-commit --all`
2. **Docker env image** (CI/CD → ghcr.io): `docker buildx bake dev-load`

## Quick Start
```bash
mise install                          # Install all tools
hk run pre-commit --all               # Run lint checks
docker buildx bake dev-load           # Build devcontainer locally
uv run --directory python pytest tests/ -x -q  # Run tests
```

## Architecture
- `.devcontainer/Dockerfile` — Multi-stage devcontainer (base → tools → devcontainer); APT snapshot pinning, mise bootstrap, default `devcontainer` user at UID 1000
- `.devcontainer/Dockerfile.host-user` — Host-user overlay; renames default user to match host via `DEVCONTAINER_USERNAME` build arg
- `docker-bake.hcl` — BuildKit bake config (dev, dev-load targets); `IMAGE_REF` consolidates registry+image; `docker-metadata-action` target for CI tag inheritance
- `install.sh` — Single bootstrap entry point used by Dockerfile
- `home/` — Chezmoi-managed dotfiles (shell, git, editor config)
- `python/` — Python package (`dotfiles_setup`) for orchestration
- `hk.pkl` — Git hook config (pre-commit via hk)
- `mise.toml` — Tool versions (hk, pkl, hadolint, shellcheck, actionlint, etc.)
- `.github/workflows/ci.yml` — Lint → contract-preflight → build → smoke-test
- `scripts/benchmark-docker.sh` — Docker runtime A/B benchmarking

## Docker Runtimes
Colima (VZ + Rosetta) is recommended over Docker Desktop for AMD64 devcontainers.
Use native `colima` buildx driver, not `colima-builder` (QEMU).
Benchmarks: `docs/research/trail/findings/docker-benchmarks/`

## CI Pipeline
Registry: `ghcr.io/ray-manaloto/cpp-devcontainer`
- `CONTAINER_REGISTRY` env var (not `REGISTRY` — avoids HCL collision)
- GitHub token passed via BuildKit secret mount
- `DEVCONTAINER_USERNAME=devcontainer` (UID 1000) — default user in base image; host-user overlay renames at devcontainer up time
- `updateRemoteUserUID` is a no-op on macOS (Docker Desktop VM handles UID translation); only matters on Linux hosts
- Bake targets: `dev` (CI push), `dev-load` (local)
- `IMAGE_REF` variable (`${DEFAULT_REGISTRY}/${IMAGE}`) consolidates registry+image for tags and cache refs
- `docker-metadata-action` bake target provides default tags locally; CI overrides with SHA/latest/PR tags via metadata-action bake file

## Testing
```bash
pytest tests/ -x -q                # All tests
pytest tests/test_audit.py -x -q   # Single file
```

### Smoke Test Roadmap
Current CI smoke test (inline bash) is identified as too thin (debate 2026-03-29).
Priority: adopt structured Python-driven verification with named test suites.
Cherry-pick verification patterns from cpp-playground; skip its full CI architecture.

## Phase 2 (In Progress)
Full design spec: `docs/ultrapowers/specs/2026-03-29-devcontainer-host-user-migration-design.md`
Adversarial review: `docs/research/trail/findings/devcontainer-spec-adversarial-review-2026-03-29.yaml`

**Showstoppers resolved and implemented (adversarial review 2026-03-29):**
- **RESOLVED**: `devcontainer` stage creates default `devcontainer` user at UID 1000 — `remoteUser` now points to existing user
- **RESOLVED**: `substr()` removed from docker-bake HCL — SHAs truncated in CI workflow, passed as separate `SHORT` variables
- **RESOLVED**: Compiler builds from source cut; consuming from cpp-playground published images via `COPY --from`

**Scope reduction (adversarial consensus: "scope monster"):**
- Cut multi-stage compiler builds; consume from cpp-playground published images
- Start `dotfiles-setup` CLI with 3 subcommands: `devcontainer up`, `image smoke`, `verify run`
- Defer candidate-promote CI; keep linear pipeline
- Defer 6 specialized skills to Phase 3+

**Key items (not yet implemented):**
- Host-user passthrough (`Dockerfile.host-user` overlay, dynamic `DEVCONTAINER_USERNAME`)
- Registry migration: `ghcr.io/sortakool` → `ghcr.io/ray-manaloto`, image rename to `cpp-devcontainer`
- Dynamic container naming: `{IMAGE_NAME}-{USER}-{SSH_PORT}` (default SSH port 4444)
- No-vscode enforcement: CI contract-preflight, hk pre-commit hook, Python verify suite

## Policies
See `.claude/rules/` for enforced policies:
- `zero-skip-policy.md` — Never suppress warnings without approval
- `ai-cli-invocation.md` — Correct CLI patterns for Codex/Gemini/OpenCode
