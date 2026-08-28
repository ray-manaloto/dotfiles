<!-- Generated: 2026-04-07 | Updated: 2026-06-28 -->

# Dotfiles — macOS Developer Environment

Chezmoi-managed dotfiles with devcontainer support targeting AMD64 Linux
containers on macOS ARM hosts. Two build types:

1. **Local linting** (hk + mise): `mise install && mise run lint`
2. **Docker env image** (CI/CD → ghcr.io): published from `main` via GHA

Registry: `ghcr.io/ray-manaloto/dotfiles-devcontainer`. CI: `ci.yml` (thin
caller) → lint → contract-preflight → `changes` → reusable `build-publish.yml`
(plan → base-prep → p2996-prep → dev-prep → build → smoke-test → dev-tag →
manifest; the middle six fan out per architecture, #676) → `ci-gate`;
`promote` retags on main; benchmark + Trivy async in `image-analysis.yml`.

## Quick Start

```bash
mise install                                 # Install all tools
mise run lint                                # Run lint checks (hk under a hard timeout)
mise run up / down                           # Bring up / tear down devcontainer (.devcontainer/AGENTS.md)
mise run sync / ship / automerge / land -- <PR#>  # Sync + gated PR loop; automerge = bot PRs (skill: pr-workflow)
mise run verify-container-latest             # Gate: container on latest branch code + base (hard)
uv run --project python pytest tests/ -x -q  # Run tests (see python/AGENTS.md)
mise run verify                    # Run structured verification contracts
mise run pin-actions                         # Verify GHA actions are SHA-pinned
mise run lint-docs                           # Validate agent documentation (agnix)
mise run lock -- "<backend/name>"            # Re-lock ONE tool (bare form is destructive, #370)
mise run lock-image                          # Regenerate the IMAGE locks instead (#650; routes to amd64)
```

The devloop is `mise run up` → work inside the container → `mise run down`.
The legacy `dotfiles-setup docker {up,down}` wrapper has been replaced by
the official `@devcontainers/cli` (pinned in `mise.toml`).

## Key Files

| File | Purpose |
|------|---------|
| `mise.toml` + `.config/mise/conf.d/shared.toml` | Host tool versions + tasks; the tools shared with the image (hk, pkl, linters, python, uv, chezmoi, bun) live in the exact-pinned shared fragment both host and image merge (#160 T5) |
| `mise.lock` | Locked tool versions for reproducible installs |
| `mise.local.toml` | Gitignored per-clone overrides (e.g., `BASE_IMAGE`). See `mise.local.toml.example` |
| `hk.pkl` | Project git hook config; imports `hk-common.pkl`; enforces `no_lint_skip`, `require_pipefail`, `bash_logic_budget`, `claude_md_import_stub`, `claude_agents_md_pairs` |
| `hk-common.pkl` | Shared step definitions (hygiene, safety, security, typos) reused by `hk.pkl` and `hk-image.pkl` |
| `hk-image.pkl` | Image-only hook config for devcontainer validation |
| `docker-bake.hcl` | BuildKit bake config (`dev`, `dev-load` build targets + `base`/`p2996-cache` CI stages); `IMAGE_REF` consolidates registry+image |
| `renovate.json` · `currency.toml` · `parity.toml` | Declarative sets: Renovate deps; deep-tracked tools (`mise run tool-currency`); the cross-repo shared set (`mise run parity`, #354) |
| `AGENTS.md` | Agent-agnostic project instructions (this file) |
| `CLAUDE.md` | Thin `@AGENTS.md` import stub for Claude Code |

## Subdirectories

`.devcontainer/`, `.github/workflows/`, `python/` and `tests/` each carry their
own `AGENTS.md` (guaranteed by `claude_agents_md_pairs`) — read that, not a
table here. Two exceptions worth knowing: `.claude/` has its own `CLAUDE.md` and
is exempt from the stub check; `home/` (chezmoi templates) lost its `AGENTS.md`
in #80 deliberately.

## Two Build Types

- **Build Type 1 — Local Linting**: Tools managed by mise. Git hooks via hk.
  Run `mise install` then `mise run lint` before every commit.
- **Build Type 2 — Docker Image**: Multi-stage Dockerfile at `.devcontainer/Dockerfile`.
  BuildKit bake via `docker-bake.hcl`. **CI-only** — never `mise run build` or
  `docker buildx bake dev-load` locally; the base image is published to
  `ghcr.io/ray-manaloto/dotfiles-devcontainer:dev` from `main` via GHA.
  Local devcontainer flows pull `:dev` and build only the thin host-user overlay.

## Split hk Architecture

Three pkl files with a shared-import pattern:

- `hk-common.pkl` — shared step definitions exported as `Mapping<String, Config.Step>`
- `hk.pkl` — project pre-commit config; imports and spreads `hk-common.pkl` groups
- `hk-image.pkl` — Docker image checks; imports and spreads `hk-common.pkl` groups

hk 1.49's default pklr backend evaluates the import/spread config
identically to the pkl CLI (parity probe-verified #160 T12; the
`HK_PKL_BACKEND=pkl` override is retired). The pkl-eval cache is
content-hashed since hk 1.47 — no manual cache clearing after edits.

## Testing

Commands are in **Quick Start** above; append a path for a single file
(`uv run --project python pytest tests/test_audit.py -x -q`).

Structured verification via `python/verification/suites.toml` runs as CI
`contract-preflight`. The `mise run verify` gate is **distinct
from** `hk run check --all` — some contracts (e.g.,
`build.no-stderr-suppression`) only run through the verify CLI. Run both
locally before pushing Dockerfile changes.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->

## Agent Instructions

### Policies (read before working)

- **Zero-skip**: Resolve every warning/error. Suppress only with explicit user
  approval. See `.claude/rules/zero-skip-policy.md`.
- **Zero inline suppressions**: The `no_lint_skip` hk step rejects
  `noqa`/`type: ignore`/`pylint: disable`/`nosec` in Python source.
- **MCP lanes**: required by a third-party plugin/skill → allowed; our work →
  API or `mcp2cli` first. See `.claude/rules/research-doc-sources.md`.
- **CI-local parity**: Every CI lint step has a local hk equivalent; every
  hk tool is in `mise.toml`. See `.claude/rules/ci-local-parity.md`.
- **Research before fixing**: Check docs, changelogs, and issues; don't guess at CI failures.
- Follow `.claude/rules/graphify-first.md` and `.claude/rules/real-integration-evidence.md`.
- **Bound long-running commands**: Run the lint gate via `mise run lint`
  (hk under a hard timeout; hk has none) — never wait blind or capture via
  `| tail` (masks exit codes). See `.claude/rules/long-running-command-hangs.md`.
- **Clarify before acting**: On ambiguous, multi-path, or irreversible
  work, ask (with a recommended option) until sure; proceed directly on
  clear low-risk tasks. See `.claude/rules/clarify-before-acting.md`.
- **Local validation first**: Run `mise run lint`, `pytest`, AND
  `mise run verify` locally before pushing.
- **Research existing tools/services before custom code (HARD GATE)**: prefer an
  existing tool / native feature / CLI / service (`gh` auto-merge, `chezmoi.os`)
  over ANY homegrown code (last resort + justification). See `.claude/rules/use-tool-builtins.md`.
- **Chezmoi is devcontainer-only on this Mac**: `chezmoi apply`/`update`
  blocked on host (enforced by `.claude/settings.json` deny rules); read-only ok.
- **Notepad enforcement**: Agents write findings to notepad during work, not at session end. See `.claude/rules/notepad-enforcement.md`.
- **Agent artifact conventions**: Use standard `.agent/` paths, no ad-hoc
  directories. See `.claude/rules/agent-artifact-conventions.md`.
- **Zero-bash logic**: Non-trivial logic (env detection, tool config,
  validation) lives in `python/`. Bash is restricted to thin check/smoke
  wrappers in `scripts/` (the old `install.sh` bootstrap was retired).

### Validate before committing

```bash
mise run lint                                 # Lint gate (hk under a hard timeout) — then proceed
uv run --project python pytest tests/ -x -q   # All tests pass — then proceed
mise run verify                     # Verification contracts pass — then proceed
```

Commit only after all three exit 0 — validate locally, don't push to test in CI.
Before advancing to the next task or claiming done, EVERY applicable check must be green with evidence: `.claude/rules/verify-before-advancing.md`.

### Tool management

- **mise-first**: All tools declared in `mise.toml` (or the merged
  `.config/mise/conf.d/shared.toml`); use mise binaries directly, not npx.
- **uv for Python**: `uv run --project python` for all Python commands.
  **Never `uv run --directory python`** — the latter changes cwd and
  breaks relative test paths.
- **hk for hooks**: `mise run lint` for the read-only lint gate (≡ CI;
  guard redirects raw hk); `mise run fmt` to auto-fix. Always `git add`
  BEFORE `mise run fmt` — `fix=true` can strand unstaged edits when new
  files are present.

### Devcontainer success criteria (durable, do NOT silently drop)
Gated by `mise run verify-local`. Sessions touching `.devcontainer/` or `mise.toml [tasks.up]` MUST preserve all three. Mechanism: `.devcontainer/AGENTS.md`. Research: `docs/research/runs/research-20260407-ssh-devcontainer/report.md`.

| Req | Criterion | Gate |
|---|---|---|
| **R1 inbound** | `ssh ${USER}@localhost -p $(mise run ssh-port)` opens a shell, no password | `mise run verify-ssh-inbound` |
| **R2 outbound** | `ssh -T git@github.com` inside container → "successfully authenticated" | smoke tier 3 |
| **R3 amd64** | container reports `x86_64` / `amd64` on `uname -m`, `arch`, image manifest | `mise run verify-arch` |

### Environment variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `HK_MISE` | `1` | Enable mise integration for hk |
| `CONTAINER_REGISTRY` | `ghcr.io` | Docker registry (use `CONTAINER_REGISTRY`, not `REGISTRY` — avoids HCL collision) |
| `DEVCONTAINER_USER` | `${localEnv:USER}` (fallback: `devcontainer`) | Container user (UID 1000); passed through from host `USER` via `devcontainer.json`. Host-user migration is the current state — the legacy `vscode` value has been replaced. |
| `DEVCONTAINER_SSH_PORT` | derived | Host-side port for R1 inbound ssh; container-internal sshd is hardcoded on `2222` by the feature. **Unset by default (#677)** — derived per workspace+architecture into 20000-29999 so two clones and two arches never collide (`mise run ssh-port`; `mise run names` for all three). Pin per-clone via `mise.local.toml`. Volume names still exclude the port (C10/C11/C12). |
| `DOTFILES_PLATFORM` | pinned in `mise.toml` `[env]` | **The one platform parameter** (#673). Every `--platform` site resolves from it; unset, it falls back to the host's native triple. `no_platform_literals` rejects a literal elsewhere |
| `DOCKER_DEFAULT_PLATFORM` | `{{ env.DOTFILES_PLATFORM }}` | Task-scoped export of the above — what docker itself reads |
| `PLATFORM` | per-leg in CI (#676) | bake's HCL variable, overridden by the same-named env var. **All three content hashes read it too**, so a leg's build and its cache tags cannot describe different architectures |

### Docker Runtimes

**Docker Desktop is the supported runtime as of 2026-04-09** (verified
via `docker context ls` → `desktop-linux *`). It exposes
`/run/host-services/ssh-auth.sock` natively, which R2 outbound depends
on. Colima lacks an equivalent (`abiosoft/colima#1330`, `#942`) — do
NOT switch context without validating R2 on the target runtime.
Colima is a deferred alternative tracked in issue #78. Research:
`docs/research/runs/research-20260409c-dockerdesktop-ssh/report.md`.
Benchmarks: `docs/research/trail/findings/docker-benchmarks/`.

### Do not

See `.claude/rules/do-not.md` for the authoritative list of project
invariants (dock launch, local base-image builds, raw docker CLI,
stderr suppression, bulk `git add`, `gh run watch`, `claude mcp add`,
docker context switch). Machine-enforced items also live in
`hk.pkl`.
