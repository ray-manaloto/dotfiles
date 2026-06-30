<!-- Parent: ../../AGENTS.md -->
<!-- Generated: 2026-04-07 | Updated: 2026-06-29 -->

# .github/workflows/ — CI Pipeline

## Purpose

GitHub Actions workflows implementing the 4-stage CI pipeline and
post-failure reporting.

## Key Files

| File | Purpose |
|------|---------|
| `ci.yml` | Thin caller (Phase B, #118): lint → contract-preflight → `changes` (path-gate) → `build-publish` (the reusable build chain, gated on `changes.build` + push-to-main exemption); OR lint → promote (push to main) |
| `build-publish.yml` | Reusable (`on: workflow_call`) build chain: base-prep → p2996-prep → dev-prep → build → smoke-test (smoke+Dive) → dev-tag. dev-prep/dev-tag are the third content-hash tier (#122). Inputs `{tag_strategy, publish, target, ref, p2996_ref, platform*}` (`p2996_ref` active Phase D #120; `*platform` reserved); outputs `{image_ref, digest}`. `github` context = caller's event, so sha/pr tags resolve identically |
| `ci-failure-report.yml` | Post-failure diagnostics / issue filing |
| `image-analysis.yml` | Async (`workflow_run` on CI success): benchmark metrics + Trivy CVE scan, off the PR critical path |
| `refresh.yml` | Daily cron (00:00): two independent jobs — `snapshot-refresh` (refresh `mise-system-resolved.json` on conda-forge drift, **auto-merges**) and `p2996-refresh` (bump `CLANG_P2996_REF` to latest `bloomberg/clang-p2996` HEAD, **review-required**, #100). Each mints a GitHub App token (Phase C, #119) so its PR fires CI on its own; both open a PR via `open-refresh-pr`. See **GitHub App** below. |
| `dispatch-build.yml` | Thin `repository_dispatch` caller (Phase D, #120, type `build-p2996`): calls `build-publish.yml` with `client_payload.{p2996_ref,ref?}` + `tag_strategy: dispatch` for an on-demand exact-upstream-SHA build. Never moves `:dev`/`:latest`; warms `:p2996-<hash>`/`:dev-<hash>`. See **Phase D** below. |

## Composite actions (`.github/actions/`)

Self-documented in each `action.yml`: `setup-mise` (wraps `jdx/mise-action`
+ `install_args`, all 8 mise jobs) and `open-refresh-pr` (App-token create-PR
+ optional squash auto-merge, both `refresh.yml` jobs). **Local-composite
checkout gotcha:** `./.github/actions/*` resolves from `$GITHUB_WORKSPACE`
(empty until checkout), so jobs run `actions/checkout` FIRST, then the
composite. **Composites can't read `secrets`** — the App token is minted in
`refresh.yml`, passed in.

## Pipeline stages

PR / schedule / workflow_dispatch path (stages 3–6 run inside the reusable
`build-publish.yml`, invoked by ci.yml's `build-publish` caller — names and
behavior unchanged):

1. **lint** — mise install, hk pre-commit, agnix agent-doc validation
   (`agnix .`; `.agnix.toml` `severity = "Warning"` = non-blocking),
   `mise doctor --json`, `mise.lock` upload + cache. agnix uses the
   `github:agent-sh/agnix` backend (not `npm:agnix` — see `mise.toml`).
2. **contract-preflight** — Python 3.14 + uv; runs `dotfiles-setup
   verify run` over `python/verification/suites.toml`.
3. **base-prep** — `dotfiles-setup base-hash` → probe `:base-<hash16>`
   (`docker manifest inspect`). Hit: <30s. Miss: build the `base` bake
   target (devcontainer-base = apt + mise install + cargo), push it.
   p2996-prep + build pull it instead of rebuilding the mise layer.
4. **p2996-prep** — `dotfiles-setup p2996-hash` → probe `:p2996-<hash16>`.
   Hit: <30s. Miss: build the `p2996-cache` bake target (scratch
   `p2996-export` with just `/opt/clang-p2996`, ~500 MB), push to GHCR.
5. **dev-prep** (#122, PR builds only) — `dotfiles-setup dev-hash` → probe
   `:dev-<hash16>`. Hit: retag the validated image to `:sha`/`:pr-NNN`,
   skip build+smoke. Miss: fall through. Nightly skips this (always builds).
6. **build** — `docker buildx bake dev` with `dev.args.P2996_SOURCE=<cache_ref>`;
   on a p2996 hit `clang-builder` is `FROM <cache_ref>`, skipping the
   multi-hour compile. Pushes `:pr-NNN`/`:sha` (PR) or `:dev`/`:latest` (nightly).
7. **smoke-test** — pulls `:sha-<github.sha>`, runs the PR-blocking gates
   `image smoke` + Dive (`.dive-ci`); benchmark + Trivy are async in
   `image-analysis.yml`. On success **dev-tag** stamps the `:dev-<hash>`
   validated marker — the smoked image is what's retagged `:dev`/`:latest`.

Push-to-main path (after a PR merge):

1. **lint** — same as PR path, validates the merge commit's tree.
2. **promote** — looks up the merged PR (`gh api graphql
   associatedPullRequests`). On hit: `docker buildx imagetools create
   -t :dev -t :latest <:pr-NNN>` — manifest-only retag, ~30s, no rebuild.
   On miss (direct/force push): dispatch `ci.yml` `force_dev_tag=true`.

## Invariants

- **All actions SHA-pinned** via pinact. Run `mise run pin-actions`
  locally to verify before committing workflow changes.
- **Build chain is path-gated.** A `changes` job (dorny/paths-filter,
  `list-files: json`) matches image/test inputs (`.devcontainer/**`,
  `docker-bake.hcl`, `hk-common.pkl`, `hk-image.pkl`, `python/**`,
  `.dive-ci`, `install.sh`, `ci.yml`); `decide` drops markdown-only matches
  via `jq` (`!**/*.md` can't — `**/*.md` skips dot-dirs). So docs, root-mise,
  hk.pkl, home PRs run lint+contract-preflight only; schedule +
  workflow_dispatch always build.
- **Concurrency cancels superseded runs per branch.** `ci.yml`/`autofix.yml`
  group by `${{ github.workflow }}-${{ github.head_ref || github.ref }}`; a
  new commit cancels the older in-flight run. **main is exempt**
  (`cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}`) so its
  push-path `promote` retag is never interrupted mid-flight.
- **Python 3.14 + uv via the `setup-mise` composite** for contract-preflight
  and smoke-test (`install_args: python uv`). lint caches mise data on `mise.lock`.
- **build job** passes GitHub token via BuildKit **secret mount**
  (`uid=1000`) — never via `ARG` or env.
- **`CONTAINER_REGISTRY`** env var, not `REGISTRY` (avoids HCL
  collision with the `REGISTRY` target in `docker-bake.hcl`).
- **PR builds push** `:pr-NNN` + `:sha-<github.sha>` to GHCR so smoke-test
  validates the exact image promote retags on merge. No `cacheonly` mode.
- **Push-to-main does NOT rebuild.** The `build-publish` caller is gated
  `if: github.event_name != 'push' || github.ref != 'refs/heads/main'`, so the
  reusable chain is skipped on main; `promote` retags the PR's `:pr-NNN`.
- **Three-tier content-hash probe cache** (#122): `:base-`/`:p2996-`/`:dev-<hash>`,
  each `docker manifest inspect`-probed (`dotfiles-setup {base,p2996,dev}-hash`)
  before its build. `:dev-<hash>` (= base+p2996 hashes + whole Dockerfile + dev
  target) is tagged only AFTER smoke passes (validated marker), so a PR hit
  skips build+smoke (retag to `:sha`/`:pr-NNN`). Nightly skips the dev probe
  and always rebuilds (catches rolling-tool drift the hash can't see).
- **P2996 cache invalidation.** Key = `CLANG_P2996_REF`, `BASE_IMAGE`,
  `PLATFORM`, Dockerfile, bake file, `mise-system-resolved.json`. Bust via
  `mise run capture-mise-system-resolved`. Details: `.devcontainer/P2996-CACHE.md`.
- **`uv run --project python`**, not `--directory` — `--directory`
  changes cwd and breaks relative test paths.
- **Use `--watch`, never sleep-poll** (`gh pr checks <n> --watch`); the
  `gh run watch --exit-status` exit code is unreliable, cross-verify with
  `--json conclusion`. Authority: `.claude/rules/gh-cli-watch.md`.
- **No `type=gha` cache on `base`/`p2996-cache` targets** — registry tag +
  `Probe cache` IS the durable cache; `mode=max` gha export exceeds the 1h
  Azure SAS TTL → `403` on cold runs. `dev` keeps gha cache (small).
- **Trivy lives in `image-analysis.yml` (async), not smoke-test.**
  `scanners: vuln` + `timeout: 15m`, warn-only (default scanners timeout
  at 5min on the multi-GB image); CVE-only scope (issue #92).
- **`wagoodman/dive` action is broken upstream** (v0.13.1 `ARG
  DOCKER_CLI_VERSION` empty → 404s on `docker-.tgz`). Install the binary
  release tarball in a `run:` step; never `uses: wagoodman/dive@<sha>`.

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

## GitHub App — refresh auto-merge (Phase C, #119)

`refresh.yml` mints an App token (`actions/create-github-app-token`) so its
PR fires `pull_request` CI on its own — GITHUB_TOKEN PRs don't. **One-time
repo-admin setup:** (1) create a GitHub App with **contents: write +
pull-requests: write**, install it here, add secrets `REFRESH_APP_ID` (the
**numeric App ID**, not Client ID `Iv…`) + `REFRESH_APP_PRIVATE_KEY`;
(2) enable **Allow auto-merge**; (3) branch protection on `main` requiring
the **`ci-gate`** check — else `--auto` lands before smoke. Policy:
snapshot auto-merges (squash) once smoke passes; p2996 is review-required.
`ci-gate` (always-run: passes when upstream succeed/skip) lets non-build
PRs merge without admin.

## Phase D — on-demand p2996 build (#120)

`dispatch-build.yml` builds an exact upstream clang-p2996 SHA on demand
(no cron wait). Dispatch (needs a `contents: write` token):

```sh
gh api repos/ray-manaloto/dotfiles/dispatches -f event_type=build-p2996 \
  -f 'client_payload[p2996_ref]=<upstream-sha-or-ref>'
```

`p2996_ref` flows into build-publish.yml's **Resolve p2996 ref override**
steps (p2996-prep, dev-prep, dev-tag): they export `CLANG_P2996_REF` so
BOTH `dotfiles-setup {p2996,dev}-hash` AND docker bake's native variable
override resolve the same SHA — the cache tag tracks the override, never
poisoning the pinned cache. Empty input exports nothing → the
`docker-bake.hcl` pin wins (byte-identical build). `tag_strategy: dispatch`
emits `:sha` only; merge the `p2996-refresh` PR to make a bump permanent.

## Dependabot (`.github/dependabot.yml`)

- **`interval: "cron"` enforces a 24h minimum.** The schema accepts
  `interval: "cron"` + `cronjob: "<expr>"` + `timezone: "<tz>"`, but
  `dependabot-api.githubapp.com` rejects sub-daily (min allowed 24h). Use
  `0 0 * * *` or longer, never `0 * * * *`. Validated as a check named
  `.github/dependabot.yml` on every PR touching the file. (PR #86.)

## Debugging CI failures

- Check the build job diagnostics step first (`docker buildx bake
  --print`) — it surfaces known warnings without needing the full
  build log.
- `mise doctor --json` output in the lint job shows tool resolution
  issues.
- **App-installed check error detail** (dependabot, CodeRabbit) lives in
  the check-runs API: `gh api 'repos/OWNER/REPO/commits/BRANCH/check-runs'
  --jq '.check_runs[]|select(.name|contains("NAME"))|.output.summary'`.
- For Docker warning triage, see the `ci-warning-investigator` skill.
- **`gh run list` returns multiple workflows.** A branch has both a `CI`
  and an `autofix.ci` run per push; filter `--workflow CI` to disambiguate.
- **Manual autofix-fix recipe** (`autofix-ci/action` can't push back,
  `500 ... not installed`): `gh run download RUN_ID`, base64-decode
  `additions[].contents` from `autofix.json`, apply, commit, push (PR #94).
- **Re-run a failed job** — `gh run rerun RUN_ID --failed` refires only the
  failed jobs against the same commit (verify a config fix without a fresh
  push; validated on the autofix.ci app install, `ee079c5`).

<!-- MANUAL: Any manually added notes below this line are preserved on regeneration -->
