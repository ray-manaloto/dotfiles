<!-- Parent: ../../AGENTS.md -->
<!-- Generated: 2026-04-07 | Updated: 2026-04-07 -->

# .github/workflows/ — CI Pipeline

## Purpose

GitHub Actions workflows implementing the 4-stage CI pipeline and
post-failure reporting.

## Key Files

| File | Purpose |
|------|---------|
| `ci.yml` | Main pipeline: lint → contract-preflight → build → smoke-test |
| `ci-failure-report.yml` | Post-failure diagnostics / issue filing |

## Pipeline stages

1. **lint** — mise install, hk pre-commit, agnix agent-doc validation
   (`agnix --target claude-code --strict .`), `mise doctor --json`
   health check, `mise.lock` artifact upload, mise data cache keyed on
   `mise.lock`.
2. **contract-preflight** — Python 3.14 + uv; runs `dotfiles-setup
   verify run` over `python/verification/suites.toml`.
3. **build** — `docker buildx bake` for the published base image;
   includes diagnostics step (`docker buildx bake --print` + known
   warnings table); publishes to
   `ghcr.io/ray-manaloto/dotfiles-devcontainer` on `main`.
4. **smoke-test** — validates clang, AI CLIs, sanitizers, backend
   policies on the built image; no host mount (see
   `feedback_docker_ci_workarounds`).

## Invariants

- **All actions SHA-pinned** via pinact. Run `mise run pin-actions`
  locally to verify before committing workflow changes.
- **Python 3.14** for contract-preflight and smoke-test jobs
  (`actions/setup-python@v6`, `astral-sh/setup-uv@v8`).
- **lint job** caches mise data directory keyed on `mise.lock`.
- **build job** passes GitHub token via BuildKit **secret mount**
  (`uid=1000` for vscode user) — never via `ARG` or env.
- **`CONTAINER_REGISTRY`** env var, not `REGISTRY` (avoids HCL
  collision with the `REGISTRY` target in `docker-bake.hcl`).
- **`cacheonly` conditional** on PR builds — see
  `feedback_docker_ci_workarounds`.
- **`uv run --project python`**, not `--directory` — `--directory`
  changes cwd and breaks relative test paths.
- **`gh run watch --exit-status` is unreliable** — always verify
  workflow completion with `gh pr checks <n> --json` or
  `gh run list --json conclusion`.

## Debugging CI failures

- Check the build job diagnostics step first (`docker buildx bake
  --print`) — it often shows known warnings without needing the full
  build log.
- `mise doctor --json` output in the lint job shows tool resolution
  issues.
- For Docker warning triage, see the `ci-warning-investigator` skill
  under `.claude/skills/`.
- Use `gh run watch <id> --exit-status` (or `gh pr checks <n> --watch`)
  to monitor workflows — **never sleep-poll**. See
  `feedback_gh_run_watch`. But always cross-verify with
  `gh pr checks <n> --json` because `--exit-status` has reported exit 0
  before runs were actually complete.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
