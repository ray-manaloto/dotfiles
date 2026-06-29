<!-- Parent: ../../AGENTS.md -->
<!-- Generated: 2026-04-07 | Updated: 2026-06-28 -->

# .github/workflows/ — CI Pipeline

## Purpose

GitHub Actions workflows implementing the 4-stage CI pipeline and
post-failure reporting.

## Key Files

| File | Purpose |
|------|---------|
| `ci.yml` | Main pipeline: lint → contract-preflight → `changes` (path-gate) → base-prep → p2996-prep → build → smoke-test (smoke+Dive), build chain gated on `changes.build`; OR lint → promote (push to main) |
| `ci-failure-report.yml` | Post-failure diagnostics / issue filing |
| `image-analysis.yml` | Async (`workflow_run` on CI success): benchmark metrics + Trivy CVE scan, off the PR critical path |
| `refresh.yml` | Daily cron (00:00): two independent jobs — `snapshot-refresh` (refresh `mise-system-resolved.json` on conda-forge drift) and `p2996-refresh` (bump `CLANG_P2996_REF` to latest `bloomberg/clang-p2996` `p2996`-branch HEAD, issue #100). Both open a PR on change via the shared `open-refresh-pr` composite. |

## Composite actions (`.github/actions/`)

Self-documented in each `action.yml`: `setup-mise` (wraps `jdx/mise-action`
+ `install_args`, all 8 mise jobs) and `open-refresh-pr` (create-PR +
ci.yml dispatch tail, both `refresh.yml` jobs). **Local-composite checkout
gotcha:** a `./.github/actions/*` action resolves from `$GITHUB_WORKSPACE`
(empty until checkout), so jobs run `actions/checkout` FIRST, then the
composite — neither wraps checkout.

## Pipeline stages

PR / schedule / workflow_dispatch path:

1. **lint** — mise install, hk pre-commit, agnix agent-doc validation
   (`agnix .`; `.agnix.toml` sets `severity = "Warning"` so warnings
   don't fail), `mise doctor --json`, `mise.lock` artifact upload, mise
   cache keyed on `mise.lock`. agnix uses the `github:agent-sh/agnix`
   backend (NOT `npm:agnix`; bun skips its postinstall — see `mise.toml`).
2. **contract-preflight** — Python 3.14 + uv; runs `dotfiles-setup
   verify run` over `python/verification/suites.toml`.
3. **base-prep** — computes content-hash of base inputs via
   `dotfiles-setup base-hash`. Probes
   `ghcr.io/<owner>/<repo>:base-<hash16>` with `docker manifest
   inspect`. On hit, exits in <30s. On miss, builds the `base` bake
   target (devcontainer-base stage = apt + mise install + cargo) and
   pushes it. p2996-prep and build both pull this image so neither
   rebuilds the heavy mise install when only p2996 inputs change.
4. **p2996-prep** — computes content-hash of P2996 inputs via
   `dotfiles-setup p2996-hash`. Probes
   `ghcr.io/<owner>/<repo>:p2996-<hash16>` with `docker manifest
   inspect`. On hit, exits in <30s. On miss, builds the `p2996-cache`
   bake target (the scratch-based `p2996-export` stage holding just
   `/opt/clang-p2996`, ~500 MB) and pushes it to GHCR.
5. **build** — `docker buildx bake dev` with
   `dev.args.P2996_SOURCE=<cache_ref>` from p2996-prep. On cache hit
   the Dockerfile's `clang-builder` stage is `FROM <cache_ref>` instead
   of `FROM p2996-export`, skipping the multi-hour clang compile (see
   `.devcontainer/P2996-CACHE.md` for the current baseline).
   Always pushes (`:pr-NNN` or `:sha-<sha>` for PRs; `:dev`/`:latest`
   for schedule and `force_dev_tag=true` workflow_dispatch).
6. **smoke-test** — pulls `:sha-<github.sha>` and runs the PR-blocking
   image gates only: `image smoke` (functional) + Dive (`.dive-ci` layer
   thresholds). The non-gating benchmark metrics + Trivy CVE scan moved to
   the async `image-analysis.yml` (on CI success) to keep them off the PR
   critical path. The smoked image is the one retagged `:dev`/`:latest` on
   merge.

Push-to-main path (after a PR merge):

1. **lint** — same as PR path, validates the merge commit's tree.
2. **promote** — looks up the merged PR via `gh api graphql
   associatedPullRequests`. On hit, runs `docker buildx imagetools
   create -t :dev -t :latest <:pr-NNN>` — a manifest-only retag,
   ~30 sec, no rebuild. On miss (direct push, force-push), dispatches
   `ci.yml` with `force_dev_tag=true` to fall back to a full build.

## Invariants

- **All actions SHA-pinned** via pinact. Run `mise run pin-actions`
  locally to verify before committing workflow changes.
- **Build chain is path-gated.** A `changes` job (dorny/paths-filter,
  `list-files: json`) matches image/test inputs (`.devcontainer/**`,
  `docker-bake.hcl`, `hk-common.pkl`, `hk-image.pkl`, `python/**`,
  `.dive-ci`, `install.sh`, `ci.yml`); the `decide` step drops markdown-only
  matches via `jq` (a `!**/*.md` pattern can't — `**/*.md` skips dot-dirs).
  base-prep→smoke-test AND `promote` gate on the result. So docs (incl. under
  `.devcontainer/`/`python/`), root-mise, hk.pkl, home PRs run
  lint+contract-preflight only; schedule + workflow_dispatch always build.
- **Concurrency cancels superseded runs per branch.** `ci.yml` and
  `autofix.yml` group by
  `${{ github.workflow }}-${{ github.head_ref || github.ref }}` so all
  events for one source branch share a group; pushing a new commit
  cancels the older in-flight run. `head_ref` is the PR source branch;
  `ref` covers push/schedule/dispatch. **main is exempt**
  (`cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}`) so its
  push-path `promote` manifest-retag is never interrupted mid-flight.
- **Python 3.14** for contract-preflight and smoke-test jobs
  (`actions/setup-python@v6`, `astral-sh/setup-uv@v8`).
- **lint job** caches mise data directory keyed on `mise.lock`.
- **build job** passes GitHub token via BuildKit **secret mount**
  (`uid=1000` for vscode user) — never via `ARG` or env.
- **`CONTAINER_REGISTRY`** env var, not `REGISTRY` (avoids HCL
  collision with the `REGISTRY` target in `docker-bake.hcl`).
- **PR builds push** `:pr-NNN` + `:sha-<github.sha>` to GHCR so smoke-test
  validates the exact image promote retags on merge. No `cacheonly` mode
  (removed in the cache+promote rework).
- **Push-to-main does NOT rebuild.** `build`, `p2996-prep`, and
  `smoke-test` are all gated `if: github.event_name != 'push' ||
  github.ref != 'refs/heads/main'`. The merge commit is published
  via `promote`'s manifest-retag of the PR's `:pr-NNN`.
- **P2996 cache invalidation.** Key = `CLANG_P2996_REF`, `BASE_IMAGE`,
  `PLATFORM`, Dockerfile, bake file, `mise-system-resolved.json`. Bust via
  `mise run capture-mise-system-resolved` in the devcontainer on conda-forge
  drift. Details: `.devcontainer/P2996-CACHE.md`.
- **`uv run --project python`**, not `--directory` — `--directory`
  changes cwd and breaks relative test paths.
- **Use `--watch`, never sleep-poll** (`gh pr checks <n> --watch`); the
  `gh run watch --exit-status` exit code is unreliable, cross-verify with
  `--json conclusion`. Authority: `.claude/rules/gh-cli-watch.md`.
- **No `type=gha` cache on `base`/`p2996-cache` targets** — registry tag +
  `Probe cache` (`docker manifest inspect`) IS the durable cache;
  `mode=max` gha export exceeds the 1h Azure SAS TTL → `403` on cold runs.
  Documented in `docker-bake.hcl`. `dev` target keeps gha cache (small).
- **Trivy lives in `image-analysis.yml` (async), not ci.yml smoke-test.**
  `scanners: vuln` + `timeout: 15m`, warn-only: default scanners timeout
  at 5min exporting the multi-GB image; scope is CVE-only (issue #92).
- **`wagoodman/dive` action is broken upstream** (v0.13.1 `ARG
  DOCKER_CLI_VERSION` has no default → fetches `docker-.tgz`, 404s). Use
  the binary release tarball in a `run:` step; do NOT use
  `uses: wagoodman/dive@<sha>`.

## Cron schedules (`schedule:`)

GHA `schedule.cron` honors a sibling `timezone:` field (IANA zone), e.g.
`timezone: "America/Chicago"` — NOT UTC-only (a stale claim). Two staggered
daily crons, **distinct, complementary** roles:

| Time | Workflow | Role |
|------|----------|------|
| 00:00 | `refresh.yml` | **Changes the pins.** `snapshot-refresh` + `p2996-refresh` jobs detect upstream drift (conda-forge snapshot / `clang-p2996` HEAD) and open PRs — no build. |
| 02:00 | `ci.yml` nightly | **Publishes on the pinned ref.** Rebuilds `:dev`/`:latest` on the *current* pins (catches base-image CVEs / floating-tool drift the pins don't move). |

The 2h gap lets a 00:00 refresh PR, merged before 02:00, be what the
nightly publishes. Do NOT collapse onto one cron (issue #116).

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
  --print`) — it surfaces known warnings without needing the full
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
- **`gh run list` returns multiple workflows.** A branch with both
  `ci.yml` and `autofix.yml` has a `CI` run AND an `autofix.ci` run
  per push; `gh run list --limit 1` may surface the wrong one. Filter
  with `--workflow CI` (or `--workflow autofix.ci`) to disambiguate.
- **Manual autofix-fix recipe** — if `autofix-ci/action` can't push
  back (e.g. app uninstalled, `500 autofix.ci app is not installed`),
  the diff is in the run's `autofix.ci.zip` artifact (substitute
  uppercase RUN_ID and FILE placeholders):
  ```bash
  gh run download RUN_ID -D /tmp/autofix
  jq -r '.changes.additions[] | select(.path=="FILE") | .contents' \
    /tmp/autofix/autofix.ci/autofix.json | base64 -d > /tmp/FILE
  cp /tmp/FILE FILE
  ```
  Apply locally, commit, push. Validated on PR #94 commit `cb186ac`
  (mise.lock linux-x64 blake3 checksum drift).
- **Re-run a failed job to verify a fix** — `gh run rerun RUN_ID --failed`
  refires only the failed jobs against the same commit. Useful for
  verifying that a config change (e.g. installing a GitHub app)
  actually fixes the failure mode without forcing a fresh push. Used
  to verify the autofix.ci app install in session 2026-05-01 (run
  `25201532504` failed on first run, succeeded on rerun against the
  same commit `ee079c5`).

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
