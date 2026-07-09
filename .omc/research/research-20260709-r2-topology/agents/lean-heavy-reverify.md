# Run B / Angle 4 — Re-verify "lean :ci + heavy :dev": should ci.yml jobs run in a lean container variant?

Date: 2026-07-09. Analyst: lean-heavy-reverify (Run B angle #4 of 5).
Question re-derived independently: **should the ci.yml lint / contract-preflight
(/test) jobs run inside a lean `:ci` container image instead of today's
mise-on-runner installs?**

**Verdict: NO for CI execution. mise-on-runner + mise-action cache is already
near-optimal and structurally correct for this repo; a lean `:ci` image is NOT
justified as a CI execution environment.** A lean image may still be justified
for Claude-Code-web sessions (Run A's consumer), but it should be a *sibling
consumer* of the same mise configs, not something `ci.yml` runs inside.
Yesterday's "lean :ci + heavy :dev" recommendation is therefore only half
re-confirmed: the fork seam is real, but the lean variant's justification must
come from web-session needs, not from CI speed — CI gains nothing and loses
several properties.

## Findings

### F1. What ci.yml actually needs (enumerated) — and there is NO CI test job

- **lint** (`ci.yml:71-160`): `./.github/actions/setup-mise` with **no
  `install_args`** → installs *every* tool in the merged host config
  (`ci.yml:87-92`), under `MISE_LOCKED=1` (`ci.yml:81`). Steps then use: `hk`
  (`hk validate`, `hk run check --all`, `ci.yml:97-104`), `chezmoi`
  (chezmoiignore gate, `ci.yml:113-124`), `mise outdated` / `mise reshim` /
  `mise doctor` (`ci.yml:125-140`), `agnix .` (`ci.yml:142`).
- `hk run check --all` executes the `check` hook (`hk.pkl:388-397` spreads
  `allSteps`): ruff/ruff_format/ty via `uv run --project python`
  (`hk.pkl:55-78`), plus binaries editorconfig-checker(`ec`), hadolint, taplo,
  yamllint, pkl, shellcheck, actionlint, ghalint, zizmor, gitleaks, typos,
  jq/check-jsonschema (devcontainer_json_validate), docker buildx
  (docker_bake_check), chezmoi, renovate-config-validator
  (`renovate_config_validate`, needs the ~354MB `npm:renovate` package,
  `mise.toml:16`), agnix (`hk.pkl:42-357`, `hk-common.pkl:42-74`). Roughly
  **25-30 distinct tools** across `.config/mise/conf.d/shared.toml` (20
  exact-pinned host↔image tools) + host-only `mise.toml` entries.
- **contract-preflight** (`ci.yml:161-182`): setup-mise with
  `install_args: "python uv"` only, then `uv run --project python
  dotfiles-setup verify run …`.
- **There is no pytest job in CI.** `grep pytest .github/**` → zero matches;
  the 316-test suite runs only in the hk `pre-push` hook (`hk.pkl:412-421`)
  and locally. The domain brief's "lint/test toolchain" premise is half wrong:
  any plan that says a lean `:ci` image "provides the ci.yml test toolchain"
  is providing a toolchain to a job that does not exist. (If a CI pytest job
  is *added*, its needs are exactly contract-preflight's: python + uv — a 6-7s
  runner install, see F2.)

### F2. Measured warm-path timings: the current setup is already near-floor

Real job timings from this repo (GitHub Actions API, runs of 2026-07-08/09):

| Job | Total | "Install mise" step | Run |
|---|---|---|---|
| lint (PR, docs-only) | **48s** | **22s** (all ~44 host tools, warm cache) | [run 29043090828](https://github.com/ray-manaloto/dotfiles/actions/runs/29043090828), 2026-07-09 |
| lint (nightly, main) | **45s** | **25s** | [run 29011164725](https://github.com/ray-manaloto/dotfiles/actions/runs/29011164725), 2026-07-09 |
| contract-preflight | **12-13s** | **6-7s** (python+uv subset) | both runs above |
| base-prep / p2996-prep (probe hits) | 16-18s | 5-6s | run 29011164725 |

Per-run setup-mise overhead across all short jobs is ≈45s *total*. The
dominant CI cost is elsewhere: the nightly `build-publish / build` job took
**33 min** (5m40s disk-free + 26m35s bake) in the same run — the lean:ci
question cannot move that number.

mise-action's cache restores the entire mise data dir (binary + all tools) on
hit and keys on platform + install_args_hash + config file_hash
(`docs/research/mintlify-cache/jdx/mise-action/llms-full.txt`, "Caching
overview"), so each job's subset caches independently — exactly what the
composite preserves (`.github/actions/setup-mise/action.yml:10-19`).

### F3. Measured partial-cold path: a pin-bump PR installs the delta in ~30s (and fails *in the right place*)

When `mise.lock`/`mise.toml` change, the exact cache key misses and
restore-keys hydrate an older cache; mise then installs only the delta
(documented in-repo at `ci.yml:127-135`). Observed on the
`renovate/npm-claude-flow-cli-3.x` PR: "Install mise" ran **33-37s** and
failed *on the new tool version itself* — twice, reproducibly
([run 28965970048](https://github.com/ray-manaloto/dotfiles/actions/runs/28965970048),
[run 28974425699](https://github.com/ray-manaloto/dotfiles/actions/runs/28974425699),
2026-07-08). This is the key structural property: **the PR that bumps a tool
pin exercises that pin's installability in its own lint job.** A true-cold
full install (no restorable cache at all) was not observable in the recent
run history (restore-keys make it rare); it is bounded by the job's
`timeout-minutes: 15` (`ci.yml:73`) and estimated at single-digit minutes —
see Uncertainties.

### F4. Container jobs would ADD cost to every job, with no inter-job image caching

- GHA container jobs (`jobs.<job>.container`) pull the image in an
  auto-generated "Initialize containers" step at the start of **every job**;
  GitHub states there are "no methods to reduce the time it takes" and offers
  no image caching between jobs on hosted runners (runners are ephemeral)
  ([community discussion #25975](https://github.com/orgs/community/discussions/25975)).
- GHCR pull throughput is good when healthy (runners have ~1 Gbps ≈ 125 MB/s;
  [runs-on cache benchmark](https://runs-on.com/benchmarks/github-actions-cache-performance/),
  [depot.dev cache analysis](https://depot.dev/blog/github-actions-cache) —
  ~145 MiB/s for actions/cache), but layer extraction is serialized and GHCR
  has documented degradation incidents — e.g. a 1.5GB image pull taking >8
  min while docker.io served the same image in 14s
  ([community discussion #173607](https://github.com/orgs/community/discussions/173607)).
- A lean `:ci` image carrying F1's ~25-30 tools + python venv would plausibly
  be 2-4GB → **~30s-3min pull+extract per job × 2-7 jobs per run**, versus
  today's 5-25s cache restore per job. Even in the best case it is a wash on
  the lint job and a strict regression on the four 5-7s python+uv subset jobs.
- Minor container-job frictions: default `run` shell is `sh`, `--network` /
  `--entrypoint` docker options unsupported, Linux-only
  ([GitHub docs: run jobs in a container](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/run-jobs-in-a-container)).

### F5. The chicken-and-egg problem: pins change near-daily, so a :ci image is always one PR behind

The host toolset is bumped by Renovate (minor/patch/digest automerge) plus the
daily `refresh.yml` lock regeneration (inventory report,
`.omc/research/research-20260709-r2-inventory/report.md:45-66`). If lint ran
inside `:ci`:

- a PR bumping a lint-tool pin must be linted **with the new pin** — so the
  `:ci` image would have to rebuild *before* lint on that PR's critical path
  (minutes of bake+push+pull added to the repo's most frequent PR type), OR
- CI installs the delta on top of the container with mise anyway — which
  reintroduces mise-on-runner inside a container and makes the image
  pointless, OR
- lint runs on the *previous* image — silently validating the wrong toolchain
  (violates `MISE_LOCKED` fail-fast intent, `ci.yml:76-81`, and
  `.claude/rules/ci-local-parity.md`).

Today's design has none of these: F3 shows the delta install runs (and fails
loudly) in the bump PR itself, in ~35s.

### F6. CI-on-runner is itself a test surface a container would delete

The lint job's value is not only "run hk": it verifies the **host toolchain
path** — `mise.lock` resolves and installs deterministically on linux-x64
(`MISE_LOCKED=1`, `ci.yml:76-81`), stale-shim recovery (`mise reshim`,
`ci.yml:127-135`), `mise doctor` health (`ci.yml:136-140`) — the same lock the
Mac host consumes (macOS↔CI parity, `ci.yml:77-80`). `refresh.yml`'s
auto-merging lock PRs are gated by exactly this job. Baking the tools into an
image and skipping `mise install` would stop exercising fresh lock
resolution, weakening the daily refresh gate precisely where it bites.

### F7. If CI setup time ever needs trimming, the lever is `install_args`, not an image

The lint job installs ~14-18 tools **no CI step uses** (colima, lima, aws-cli,
azure-cli, docker-cli, opencode, claude-flow, ralph-cli, agent-browser,
deepagents-cli, ctx7, skills, devcontainers-cli … `mise.toml:9-44`) — pure
cache weight inside the 22-25s install and the 10GB repo cache budget. A
`MISE_ENV`-scoped or `install_args`-scoped lint subset (mise-action keys the
cache on both — cached docs, "Cache key" section) would cut the warm restore
below 22s at zero architectural cost. This dominates any container-based
alternative and preserves F5/F6.

### F8. Delta against yesterday's recommendation

- **Re-confirmed:** the RUNTIME-tier seam (`.devcontainer/mise-runtime.toml:10-12`)
  is a real fork point, and a lean image *can* be produced cheaply from the
  existing base stage for **web sessions** (Run A's constraint: web can't
  pull 38GB).
- **Overturned:** wiring `ci.yml`'s lint/contract jobs into that lean image.
  Evidence F2-F6: warm path is already 45-48s end-to-end; containers add
  per-job pull with no caching; pin-bump PRs create a rebuild-before-lint
  cycle; and the runner install *is* the test. **mise-on-runner + mise-action
  cache remains better for CI.**
- **Recommended shape:** one source of truth (mise configs incl.
  `shared.toml`), three consumers — (a) GHA runners `mise install` per job
  (unchanged ci.yml), (b) heavy `:dev` devcontainer (unchanged), (c) optional
  lean web image forked at the documented seam, consumed only by web
  bootstrap. No `container:` keys enter ci.yml; `build-publish.yml` gains at
  most one extra bake target if (c) is adopted.

## Uncertainties / gaps

1. **True-cold full-install time is unsampled.** All observed installs were
   warm or restore-keys-hydrated. A genuinely cold install of the full ~44
   host tools (cache evicted, new `cache_key_prefix`) is estimated at 3-8 min
   (npm:renovate ~354MB, aws-cli, azure-cli among them) but was not directly
   measured; it is bounded by `timeout-minutes: 15`. This does not change the
   verdict: a cold `:ci` image *build+push+pull* would be strictly slower.
2. **restore-keys behavior is repo-documented, not upstream-documented.** The
   cached mise-action docs describe the exact-key scheme but not a
   restore-keys fallback; `ci.yml:127-135` documents the hydrate-from-older-
   cache behavior as observed. If mise-action ever drops the fallback, cold
   paths become more frequent (still cheaper than the image cycle).
3. **Lean-image size is estimated (2-4GB), not built.** If a web-oriented lean
   image is prototyped by Run A, its measured size would tighten F4's pull-
   time range but cannot invert the comparison for the 6-7s subset jobs.
4. **GHCR pull-time evidence includes incidents older/broader than 12
   months** (community discussions #25975 ≈2022-23, #173607 ≈2025). GitHub's
   "no methods to reduce Initialize containers" stance and the
   ephemeral-runner no-image-cache property are current as of the docs
   fetched 2026-07-09.
5. **Notepad MCP tools were unavailable in this session** (Bash blocked, OMC
   notepad tools not loaded); findings are persisted via this artifact per
   `agent-report-persistence.md` instead.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — ci.yml, build-publish.yml, setup-mise composite, mise.toml, shared.toml, hk.pkl/hk-common.pkl read at file:line; live job timings via Actions API (runs 29043090828, 29011164725, 28965970048, 28974425699).
- [jdx/mise-action](https://github.com/jdx/mise-action) — caching model, cache keys, install_args, platform behavior (local mintlify cache `docs/research/mintlify-cache/jdx/mise-action/llms-full.txt`).
- [github/docs](https://github.com/github/docs) — "Run jobs in a container" page (container-job mechanics and limitations).
- [orgs/community discussions](https://github.com/orgs/community/discussions/25975) — #25975 (Initialize-containers cost, no hosted-runner image cache) and #173607 (GHCR degraded pull performance).
