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
- **`smoke-test` is intentionally PR-skipped.** Its `if:` guard is
  `github.ref == 'refs/heads/main' || github.event_name == 'schedule'`.
  Smoke-test validates the published `:dev` image, which only exists
  after a successful main push. On PRs, expect `smoke-test` to show
  `SKIPPED` — that's not a failure. Treat the PR as green when
  `lint`/`contract-preflight`/`build`/`CodeRabbit` all pass.

## Cron schedules (`schedule:`)

- **GHA `schedule.cron` supports a sibling `timezone:` field.** Use
  `cron: "0 0 * * *"` + `timezone: "America/Chicago"` for IANA-zoned
  schedules. Verified against the GHA workflow-syntax docs 2026-04-27.
  Older AI-summarized claims of "GHA cron is UTC-only" are stale —
  the field is supported.

## Dependabot (`.github/dependabot.yml`)

- **`interval: "cron"` enforces a 24h minimum.** The schema accepts
  `interval: "cron"` + `cronjob: "<expr>"` + `timezone: "<tz>"`, but
  `dependabot-api.githubapp.com` rejects sub-daily expressions:
  *"Cronjob expression has a minimum interval of 1 hours which is less
  than the minimum allowed interval of 24 hours."* Use `0 0 * * *`
  (daily at midnight) or longer; do NOT try `0 * * * *` (hourly). The
  validation runs as a check named `.github/dependabot.yml` on every
  PR that touches the file. (PR #86 commit `b5022c0`.)

## Debugging CI failures

- Check the build job diagnostics step first (`docker buildx bake
  --print`) — it often shows known warnings without needing the full
  build log.
- `mise doctor --json` output in the lint job shows tool resolution
  issues.
- **App-installed check error detail** (dependabot, CodeRabbit, etc.)
  lives in the check-runs API, not in `gh pr checks` output. Use:
  `gh api 'repos/OWNER/REPO/commits/BRANCH/check-runs' --jq
  '.check_runs[] | select(.name | contains("NAME")) |
  .output.summary'` (substitute uppercase placeholders) to surface the
  actual rejection message.
- For Docker warning triage, see the `ci-warning-investigator` skill
  under `.claude/skills/`.
- Use `gh run watch <id> --exit-status` (or `gh pr checks <n> --watch`)
  to monitor workflows — **never sleep-poll**. See
  `feedback_gh_run_watch`. But always cross-verify with
  `gh pr checks <n> --json` because `--exit-status` has reported exit 0
  before runs were actually complete.

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
