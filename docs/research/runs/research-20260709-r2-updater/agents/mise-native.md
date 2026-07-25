# Run C, angle #2 — mise as its own updater engine

Analyst report, 2026-07-09 (final; merges the two research passes of this
lane). Domain: version/commit discovery + build triggering for
ray-manaloto/dotfiles. Question: could a scheduled GHA job built on
`mise outdated --json` / `mise upgrade --bump` / `mise lock` replace
Renovate for the mise-managed surface, and what would be lost?

Grounding baseline: `docs/research/runs/research-20260709-r2-inventory/report.md`
(re-verified repo inventory, main). Local mintlify cache greped first per
`research-doc-sources.md`; cache misses noted below.

## Findings

### F1. The repo ALREADY runs a mise-native updater daily — for the latest-tracking tiers only

The incumbent is not hypothetical. `refresh.yml` (cron `0 0 * * *`,
`timezone: America/Chicago` — `refresh.yml:38-40`) runs the
`./.github/actions/lock-refresh` composite (`refresh.yml:82`), which is a
pure mise-native pipeline:

1. `mise lock` with the runner mise for the root lock
   (`lock-refresh/action.yml:31`);
2. a **pinned** image-`MISE_VERSION` binary re-locking the staged merged
   image config with `MISE_ENV=runtime … lock --platform linux-x64`, run
   in a 5-iteration convergence loop because anonymous GitHub-API quota
   exhausts mid-run (`action.yml:37-62`; the comment cites mise ≥
   2026.6.13 hard-erroring on unresolvable tools — confirmed below, F5);
3. `devcontainer upgrade` for `devcontainer-lock.json` (`action.yml:63-65`).

Because tiers 3/4 (`.devcontainer/mise-system.toml`,
`mise-runtime.toml`) are **all-latest + lock** (inventory report:74-90),
for that surface "regenerate the lock" IS version discovery: a daily
`mise lock` produces a rolling 7-day-delayed latest via
`minimum_release_age = "7d"` (`mise-system.toml:141`) with
`minimum_release_age_excludes` for fast AI CLIs
(`mise-runtime.toml:33`). So the mise-native engine already owns the
image-tool surface at daily cadence; Renovate owns the *exact-pinned*
surface (root `mise.toml` + `shared.toml`) and all non-mise surfaces.

### F2. mise has every CLI primitive a scheduled updater job needs — verified current

From the canonical docs (the local mintlify cache at
`docs/research/mintlify-cache/jdx/mise/` is **partial** — it has no
`mise lock` or `mise outdated` page at all, verified by grepping its
llms.txt index; the pages below were fetched remote):

- **Detection**: `mise outdated` with `--json` (machine-consumable) and
  `--bump` (report beyond the configured range, e.g. `node = "20"` →
  show 22.x) — <https://mise.jdx.dev/cli/outdated.html>. For a pure
  exit-code detector, `mise upgrade --dry-run-code` "exits with code 1
  if there are outdated tools" (cached
  `docs/research/mintlify-cache/jdx/mise/llms-full.txt:816`).
- **Pin rewriting**: `mise upgrade --bump` upgrades to latest AND
  rewrites `mise.toml`, preserving the pin's precision (`20.0.0` →
  `22.1.0`; cache `llms-full.txt:791-865`) — this is the exact operation
  needed to bump the 20 exact-pinned tools in
  `.config/mise/conf.d/shared.toml` without Renovate. `--exclude`,
  `--local`, and `--before <DATE>` (a per-run release-age cutoff) exist.
- **Lock regeneration**: `mise lock` refreshes checksums/URLs per
  platform, `--platform linux-x64` for cross-platform locks, and has its
  own `--minimum-release-age` filter (applies to fuzzy versions only;
  explicit pins are exempt) — <https://mise.jdx.dev/cli/lock.html>.
- **Cooldown parity**: `minimum_release_age` +
  `minimum_release_age_excludes` are native settings the repo already
  uses (`mise-system.toml:139-141`), so a mise-native updater loses
  nothing vs Renovate's `minimumReleaseAge` (which the repo disables
  anyway: `renovate.json:6` sets `"minimumReleaseAge": null` — and which
  has its own timestamp-less-datasource failure mode the repo already
  patched with `minimumReleaseAgeBehaviour: timestamp-optional`,
  `renovate.json:26-30`).

**Cooldown caveat (currency check):** `minimum_release_age` **defaults
to `24h` since v2026.6.2** (jdx polled the default publicly:
<https://x.com/jdxcode/status/2059334670966243473>; perf regression from
the default fixed in v2026.6.3 —
<https://github.com/jdx/mise/releases/tag/v2026.6.3>). And the
upgrade-path honored it incorrectly as recently as June 2026: two
defects ("0s" still filtered; a too-new canonical latest fell back to
older versions without date checks), fixed via jdx PRs #10310 + #10344
(<https://github.com/jdx/mise/discussions/10303>). The feature is young
— pin the runner's mise and watch release notes
(`tool-currency-and-native-first.md`) before leaning harder on it.

### F3. Currency check: mise is releasing near-daily and actively hardening exactly this path

From <https://github.com/jdx/mise/releases> (fetched 2026-07-09): 10
releases between Jun 14 and Jul 9, 2026 (v2026.6.10 → v2026.7.4).
Directly relevant:

- **v2026.6.13** (Jun 23) "Lock resolution discipline" — `mise lock` now
  errors when active tool requests cannot be resolved (no silent
  truncated locks). Matches the `lock-refresh/action.yml:54` comment.
- **v2026.6.12** (Jun 22) — cross-platform lock checksums via
  `checksum_url`/`checksum_expr`/`checksum_algo` for more backends.
- **v2026.7.0** (Jul 2) — monorepo lockfiles (tri-state
  `[monorepo].lockfile`); richer `minimum_release_age` warnings showing
  when a version becomes eligible.
- **v2026.7.4** (Jul 9) — `mise upgrade --minimum-release-age` warning
  fix.
- **v2026.5.x line** — provenance verified and recorded during
  `mise lock` (`provenance_api_failures_fatal` setting); strict
  `locked = true` + `locked_verify_provenance` install-time verification
  (<https://mise.jdx.dev/dev-tools/mise-lock.html>).

The lockfile docs (<https://mise.jdx.dev/dev-tools/mise-lock.html>)
show per-platform checksum+size+URL coverage is backend-dependent: full
for aqua/http/github/gitlab, partial for vfox/ubi, **version-only for
asdf/npm/cargo/pipx**. So the mise-native lock is a strong supply-chain
artifact for aqua/github-backed tools but a weak one for npm-backed AI
CLIs — same weakness either way, since Renovate delegates lock content
to `mise lock` too (F4). (The docs' backend table omits `conda`; the
repo's currency rule records rattler `conda:` per-platform sha256
graduating in v2026.5.0 — docs lag the CHANGELOG, the rule's own
thesis.)

### F4. Even jdx does not use mise as the discovery engine — his preset delegates discovery to Renovate and uses `mise lock` only as artifact regen

Verbatim fetch of `jdx/renovate-config` `default.json`
(<https://raw.githubusercontent.com/jdx/renovate-config/main/default.json>,
fetched twice for confirmation):

- Discovery/PR creation: Renovate (`config:recommended`,
  `docker:pinDigests`, `helpers:pinGitHubActionDigests`,
  `abandonments:recommended`, dependencyDashboard, automerge non-major,
  `minimumReleaseAge: "7 days"` with carve-outs for jdx-owned tools).
- Lockfile: a packageRule for `matchManagers: ["mise"]` +
  `matchDatasources: ["npm"]` runs
  `postUpgradeTasks: { commands: ["mise lock"], executionMode: "branch",
  fileFilters: ["mise.lock", "mise.*.lock", …],
  installTools: {mise, node, npm} }` — i.e., the tool's own author treats
  `mise lock` as the companion-artifact regenerator inside a
  Renovate-discovered PR, not as the updater.
- **Trap inherited by this repo**: the preset sets
  `"schedule": ["* * * * 5"]` (Fridays, America/Chicago) and
  `"prHourlyLimit": 10`. `renovate.json` overrides `prHourlyLimit: 0`,
  `prConcurrentLimit: 20`, `minimumReleaseAge: null` — but **does NOT
  override `schedule`** (`renovate.json:1-108` has no `schedule` key).
  Repo config only overrides keys it sets, so the hosted app is
  currently allowed to open non-vulnerability update PRs **only on
  Fridays**. Ray's "daily-or-better" requirement is not met by the
  current Renovate surface *regardless* of hosted-app job frequency; the
  fix is a one-line `"schedule": ["at any time"]` (or `null`) in
  `renovate.json`. Vulnerability-alert PRs are the only escape hatch:
  Renovate's vulnerabilityAlerts defaults force immediate creation
  (`prCreation: 'immediate'`, empty/any-time schedule) and bypass
  `prHourlyLimit`/`prConcurrentLimit`
  (<https://docs.renovatebot.com/presets-default/>, renovatebot
  discussions #34923/#27778). The mise-native refresh.yml surface is
  unaffected.

### F5. Renovate CAN now update root `mise.lock` on the hosted app (since ~June 2026) — but not the staged image locks; the `lock-refresh` composite stays irreplaceable

The suites.toml contract text ("Renovate can never do this … mise lock is
admin-allowlisted; mise-system.lock unknown to it",
`python/verification/suites.toml:641`) and the composite header
(`lock-refresh/action.yml:8-9`) are now only **half right**:

- Renovate's mise manager supports `mise.lock` / `mise.local.lock` /
  `mise.{env}.lock` artifact updating by executing `mise lock`
  ("Renovate can update lock files when dependencies change"; lock file
  maintenance landed via renovatebot/renovate#40568, closed by PR
  #42591, opened 2026-01-21), gated as an **unsafe execution**:
  "Running `mise lock` can execute repository-defined behavior, so
  Renovate treats mise lockfile refreshes as an unsafe execution" —
  requires the global `allowedUnsafeExecutions`
  (<https://docs.renovatebot.com/modules/manager/mise/>).
- On the **Mend-hosted app**, a limited undocumented allowlist of
  postUpgradeTasks/commands exists (discoverable only from job logs via
  the `allowedCommands` log line —
  <https://docs.renovatebot.com/mend-hosted/hosted-apps-config/>), and
  renovatebot/renovate discussion #43562 (May 24 – Jun 8, 2026) shows the
  hosted app executing `mise lock` end-to-end: it initially failed on
  config trust ("Config files … are not trusted. Trust them with `mise
  trust`", v43.194.0), was fixed by PR #43606, and worked from
  v43.210.1 (~Jun 8, 2026)
  (<https://github.com/renovatebot/renovate/discussions/43562>).
- **What Renovate still cannot do**: `.devcontainer/mise-system.toml` /
  `mise-runtime.toml` do not match the mise manager's file patterns
  (`mise.toml`, `.mise.toml`, `mise.{env}.toml`, `.config/mise/…` —
  manager docs above), so those tiers and their locks are invisible to
  it; and `mise-system.lock` must be written by the **pinned image
  MISE_VERSION against a staged merged config** with a Python
  stage/collect harness around it (`lock-refresh/action.yml:37-62`) —
  lock formats are not cross-version compatible (`action.yml:41-43`),
  plus linux-x64 runner required (macOS mise silently omits linux-x64
  conda checksums, `action.yml:12-13`), npm-on-PATH required
  (`action.yml:45-49`), 5-pass rate-limit convergence, and
  `lock-collect` coverage validation before overwrite. No Renovate
  mechanism (hosted OR self-hosted postUpgradeTasks, short of embedding
  the whole recipe) reproduces that. `devcontainer upgrade` for
  `devcontainer-lock.json` is likewise outside any Renovate manager.
- Renovate's mise manager also covers backends `core, asdf, aqua, cargo,
  gem, github, go, npm, pipx, spm, ubi, vfox` — **no conda backend** —
  and documents unsupported syntaxes (asdf plugin refs, aqua `http`
  package types / `version_filter`, some ubi/github regex options)
  (manager docs above). Conda-backend image tools are updatable *only*
  by the mise-native path, and every unsupported syntax is a tool that
  silently never gets a Renovate PR — the mise-native engine, resolving
  with the same binary the image consumes, has **zero manager-parity
  gap** by construction.

### F6. What a scheduled `mise-update` GHA job loses vs Renovate (for the pinned surface)

If `refresh.yml` were extended with `mise upgrade --bump` to also bump
the 20 exact-pinned shared tools (making mise the updater for the whole
mise surface), the losses vs Renovate's mise manager are concrete:

| Capability | Renovate | mise-native job |
|---|---|---|
| Release notes / changelog in PR body | Yes (datasource changelog fetch; merge-confidence badges on Mend) | No — bare version diff; `mise outdated --json` gives versions only. PR body must be hand-templated (links to release pages scriptable; actual note mining is Run D's domain — e.g. jdx's `communique`, seen in the preset crate list) |
| CVE/vulnerability PRs that bypass schedule/cooldown | Yes (`vulnerabilityAlerts` enabled, `renovate.json:105-107`; bypasses schedule + PR limits by default) | No — mise has attestation/sigstore/provenance verification (aqua attestations, `mise-sigstore`, `osv-bloom` crates in jdx's preset list) but no CVE-alerting today. Mitigant: GH advisories barely cover the aqua/ubi CLI binaries dominating the mise tiers; the image CVE net is Trivy in `image-analysis.yml` regardless |
| Per-dependency PRs (isolation, bisectability, selective revert) | Yes | No — one bulk PR; one red check blocks every bump that day |
| Rollback when an upstream version is pulled | `rollbackPrs` | Manual git revert of the batch |
| Grouping / per-package rules / automerge policy | packageRules | Hand-rolled in workflow YAML/Python; refresh.yml's ci-gate-gated squash auto-merge is arguably a *stronger* merge gate (full build+smoke) than Renovate automerge |
| Dependency dashboard + abandonment detection | Yes (preset) | No |
| Cooldown | `minimumReleaseAge` (currently nulled repo-wide; fails on timestamp-less datasources without `timestamp-optional`) | **Parity or better**: native `minimum_release_age`(+`_excludes`, default 24h since v2026.6.2), already in use — but recently buggy on the upgrade path (F2 caveat) |
| Non-mise surfaces (GHA actions, ubuntu digest, clang-p2996 git SHA, gcc .deb, hk pkl, .chezmoiversion, npm/cargo) | Yes (native + 6 customManagers, `renovate.json:33-103`) | **Out of scope entirely** — mise cannot see any of these |

The last row is decisive: a mise-native engine can never *replace*
Renovate for this repo — the clang-p2996 branch-HEAD tracking
(git-refs datasource, `renovate.json:54-65`) and the gcc-latest HTML
datasource (`renovate.json:26-30, 98-103`) are precisely the
build-triggering upstream-commit pins Ray cares about, and they are
Renovate-only machinery. The realistic question is only which engine
owns the *pinned mise-tool* slice, and there Renovate's changelog/CVE/
per-dep-PR value is real while mise's only unique advantages (conda
backend, staged pinned-version locks, image-tier configs) are already
assigned to the mise-native refresh.yml.

**Dual-writer hazard:** whichever way the seam is drawn, exactly ONE
engine may write a given file. If Renovate's mise manager and a
`mise upgrade --bump` job both bump `shared.toml`/`mise.toml`, they race
and churn (Renovate rebases its branches; an automerged bump from one
side strands the other's open PRs). The incumbent split — Renovate
writes pins, mise writes locks — already respects this.

### F7. Cadence and trigger plumbing

- A GHA-scheduled mise job's cadence is bounded only by GHA cron
  (nominal 5-min floor, with known drift/drop behavior — angle #3's
  domain) — comfortably daily-or-better. The Mend-hosted Renovate app
  runs active repos **every 4 hours** (hourly on Enterprise)
  (<https://docs.renovatebot.com/mend-hosted/job-scheduling/>), so
  hosted Renovate is also daily-or-better **once the inherited
  Friday-only `schedule` is overridden** (F4).
- `mise outdated --json` (or `mise upgrade --dry-run-code`'s exit code)
  is a cheap pre-gate the nightly `ci.yml` 02:00 rebuild could use to
  skip no-op image republish days, or that a sub-daily cron could use to
  fire `workflow_dispatch` on `ci.yml` the moment a new tool version
  clears the 7d cooldown — the trigger plumbing exists without any new
  service. The 00:00-refresh → 02:00-publish stagger (issue #116;
  `.github/workflows/AGENTS.md` cron table) already encodes the
  merge-before-build ordering any higher-frequency variant must keep.
- Rate limits are the real cadence constraint on the mise side: the
  convergence loop exists because `mise lock`'s GitHub-backed
  resolutions exhaust anonymous quota (`lock-refresh/action.yml:17-21`);
  any frequency increase must keep `GITHUB_TOKEN`/`MISE_GITHUB_TOKEN`
  exported (jdx even ships `wait-for-gh-rate-limit` for this problem —
  preset crate list).

### F8. Bottom line for the domain recommendation

Keep the hybrid, sharpen the seams:

1. **Keep** `lock-refresh` (mise-native) as the sole owner of the
   image-tier all-latest surface + all three mise locks +
   devcontainer-lock.json — nothing else (hosted Renovate, self-hosted
   Renovate, Dependabot) can regenerate the staged pinned-version
   `mise-system.lock`/`mise-runtime.lock` or cover conda-backend tools
   (F5).
2. **Keep** Renovate for the pinned + non-mise surface; do NOT move the
   20 shared pins to `mise upgrade --bump` — the loss table (F6) is all
   cost, no unique gain, and it creates a dual-writer race on
   shared.toml.
3. **Fix the actual daily-or-better gap in one line**: override the
   inherited Friday-only `"schedule"` in `renovate.json` (F4). This is
   likely the highest-leverage finding of this angle: the current
   topology is *weekly* on the Renovate surface by silent inheritance.
4. Optionally add `mise outdated --json` / `--dry-run-code` as a change
   detector to make the nightly rebuild conditional or to add a
   sub-daily "new version cleared cooldown → dispatch build" trigger
   (F7).
5. Consider letting hosted Renovate update root `mise.lock` in-PR now
   that it can (F5) — this closes the "Renovate bumps shared.toml pin,
   root lock goes stale until 00:00 refresh" same-PR-artifact gap for
   the root lock specifically; the image locks still ride refresh.yml.
   Also update the stale absolutes in `lock-refresh/action.yml:8-9` and
   `suites.toml:641` ("Renovate can never…") to the precise residual
   claim (image locks + devcontainer lock only).

## Uncertainties / gaps

- **Mend allowlist opacity**: whether `mise lock` is on the hosted app's
  approved command list *for this repo today* is only verifiable from
  Ray's own Renovate job logs (`allowedCommands` log line) — the list is
  deliberately undocumented and mutable
  (docs.renovatebot.com/mend-hosted/hosted-apps-config/). Discussion
  #43562 shows it working for other users' dotfiles repos as of Jun 8,
  2026 (needs Renovate ≥43.210.1 for the trust fix), but it is
  Mend-changeable at any time. A self-hosted runner removes that
  dependency (angle #1's trade space).
- **Schedule-inheritance claim** (F4) is derived from Renovate config
  semantics (repo config overrides only keys it sets) + the verbatim
  preset + the verbatim repo config; I could not probe the live hosted
  app's effective config from this session. A 2-minute check of the
  repo's Renovate dashboard/log ("Repository config" section prints the
  merged config) would confirm. PR timestamps on recent Renovate PRs
  (Fridays vs weekdays) would also confirm/refute cheaply.
- **`mise outdated` vs `minimum_release_age`**: docs do not state
  whether `outdated` filters candidates by the cooldown setting or shows
  raw latest; matters for using it as a "cleared cooldown" trigger. The
  cooldown-honoring bugs fixed in PRs #10310/#10344 (June 2026) show
  this path was under-tested. Needs a local probe; also the exact
  `mise outdated --json` field schema is unverified against a live run.
- The local mintlify cache for jdx/mise is a partial mirror (38 pages;
  no lock/outdated/settings/mise-lock pages) — worth a cache refresh or
  catalog note, per `tool-currency-and-native-first.md`.
- Conda-backend presence in the image tiers is asserted from
  `lock-refresh/action.yml:12-13` ("macOS mise silently omits linux-x64
  conda checksums") and root `AGENTS.md` (rattler `conda:` lockfile
  support graduated v2026.5.0); I did not enumerate which specific tools
  use `conda:` in this session, and the mise-lock docs backend table
  omits conda entirely (docs lag).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — working-tree reads: renovate.json, refresh.yml, lock-refresh/action.yml, mise.toml, shared.toml, mise-system/runtime.toml, suites.toml, mintlify cache.
- [jdx/mise](https://github.com/jdx/mise) — CLI docs (outdated/lock/upgrade/mise-lock/settings) + releases v2026.6.2–v2026.7.4 + discussion #10303 for cooldown currency.
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — verbatim default.json preset (schedule, postUpgradeTasks mise lock rule, minimumReleaseAge carve-outs).
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — mise manager docs, postUpgradeTasks/hosted-app/job-scheduling/presets-default docs, issue #40568 + PR #42591, discussions #43562/#34923/#27778/#11206.
