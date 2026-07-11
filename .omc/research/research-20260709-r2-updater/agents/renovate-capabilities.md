# Renovate hosted vs self-hosted — 2026 capability split (Run C, angle 1/5)

Date: 2026-07-09. Analyst: research subagent (Run C — updater/discovery/build-trigger).
Scope: Mend-hosted Renovate app vs self-hosted Renovate as of July 2026 — job
scheduling floors, postUpgradeTasks, allowedUnsafeExecutions, mise manager
coverage + mise.lock artifact updates, git-refs cadence — grounded against
ray-manaloto/dotfiles' live config and its actual Renovate PRs of 2026-07-08.

## Findings

### F1. The Mend-hosted app DID regenerate `mise.lock` in the same PR in THIS repo (2026-07-08) — the "hosted can't do lockfiles" premise is now FALSE for the mise surface

Empirical, from this repository:

- PR #191 (`chore(deps): update dependency lefthook to v2.1.10`, created
  2026-07-08T15:17:19Z, merged 15:19:34Z) contains a **single commit authored by
  `renovate[bot]`** (sha `2aa8722`, 2026-07-08T15:17:17Z) that modifies BOTH
  `mise.toml` (version bump 2.1.9→2.1.10) AND `mise.lock` (22+/22− — new
  per-platform `sha256` checksums, release-asset URLs, `url_api` asset IDs,
  `provenance = "github-attestations"` entries). No CI autofix push — one
  renovate-authored commit. Source: https://github.com/ray-manaloto/dotfiles/pull/191
  (files + commits read via GitHub API).
- The PR body debug marker shows the hosted app ran **Renovate 43.242.2**
  (`createdInVer: 43.242.2`) on 2026-07-08.
- Mechanism: Renovate's mise manager `updateArtifacts` **executes the real
  binaries** — `mise trust <configfile>` then `mise lock [tools]` — via the exec
  layer with ToolConstraints (mise, node, npm, golang, ruby installed into the
  sidecar); it is NOT a native-TypeScript lock computation. It is gated on
  `GlobalConfig.get('allowedUnsafeExecutions')` containing `'mise'`; if absent it
  logs `"'mise lock' was requested to run, but 'mise' is not permitted in the
  allowedUnsafeExecutions"` and returns null (lock stays stale). Source:
  https://raw.githubusercontent.com/renovatebot/renovate/main/lib/modules/manager/mise/artifacts.ts
- Since the artifact update succeeded on the hosted app, **Mend has evidently
  enabled `mise` in the hosted app's global `allowedUnsafeExecutions`** (the
  global config is Mend-controlled on hosted). This is a change in effective
  hosted capability vs early June 2026: discussion #43562 (May 26 – Jun 8,
  2026) documented hosted failures (`mise trust` not run; user attempt to set
  `MISE_TRUSTED_CONFIG_PATHS` blocked by `allowedEnv`; hosted then on 43.209.4,
  predating the 43.210.1 fix from renovatebot/renovate#43606 which added the
  allowedUnsafeExecutions gate + explicit `mise trust`). Source:
  https://github.com/renovatebot/renovate/discussions/43562
- Timeline of the feature itself: mise lockfile-maintenance support was
  requested 2026-01-21 (renovatebot/renovate#40568, closed) and implemented in
  renovatebot/renovate#42591; the trust/unsafe-execution hardening followed in
  #43606 (≈43.210.1, late May 2026).

Implication for the keep/replace decision: yesterday's "self-hosted Renovate"
recommendation loses its strongest lockfile argument for `mise.lock`
specifically — the hosted app now does root `mise.lock` in-PR. (But see F5:
it does NOT cover `mise-system.lock` / `mise-runtime.lock`.)

### F2. The repo's EFFECTIVE Renovate cadence today is WEEKLY (Fridays), not daily — inherited from `github>jdx/renovate-config`

- `jdx/renovate-config` `default.json` (fetched verbatim from main,
  2026-07-09) sets top-level `"schedule": ["* * * * 5"]` with
  `"timezone": "America/Chicago"` — branch creation only on Fridays. The repo's
  `renovate.json` extends this preset (`renovate.json:3-5`) and does NOT
  override `schedule`, so the preset's Friday gate is the repo's effective
  update window. Source: https://raw.githubusercontent.com/jdx/renovate-config/main/default.json
- Confirmed live in the repo's own PR bodies: PRs #187, #188, #189, #190, #192
  all print "📅 Schedule: … Branch creation — Only on Friday (`* * * * 5`)
  (in timezone America/Chicago); Automerge — At any time". Source:
  https://github.com/ray-manaloto/dotfiles/pull/188 (and siblings).
- Consequence: the clang-p2996 digest bumps, gcc-latest deb bumps, hk/chezmoi/
  MISE_VERSION pins — everything Renovate-driven — currently discovers at most
  **weekly**, regardless of how often Mend runs the job (schedule gates branch
  creation inside each job run). "Daily-or-better discovery" is currently NOT
  met by the Renovate leg; the daily legs are refresh.yml (locks) and ci.yml
  (image republish). Fix is a one-line repo override, e.g.
  `"schedule": ["at any time"]` (repo config wins over preset).
- The preset also imposes `minimumReleaseAge: "7 days"` globally (jdx-owned
  tools exempted via two packageRules with `minimumReleaseAge: null`), and
  `lockFileMaintenance: { enabled: true, minimumReleaseAge: "7 days" }` with a
  "lockfile maintenance" group. The repo overrides `"minimumReleaseAge": null`
  at top level (`renovate.json:6`).
- Note: `vulnerabilityAlerts` (enabled, `renovate.json:105-107`) are exempt
  from `schedule` gating by design, so security updates still land off-Friday.

### F3. Hosted app job-frequency floors (2026): active repos ≈ every 4 hours (Community), hourly (Enterprise); NOT user-configurable upward

Per https://docs.renovatebot.com/mend-hosted/job-scheduling/ (read 2026-07-09):

| Scheduler | Applies to | Default frequency |
|---|---|---|
| Active ("hot") | repos with status new/activated (has merged a Renovate PR) | **4-hourly** (hourly for Renovate **Enterprise** on GitHub/Azure DevOps) |
| Inactive ("cold") | onboarded/onboarding/silent/failed | daily |
| Blocked ("capped") | timeout / resource-limit / OOM / unknown errors | weekly |
| All repos | every installed repo incl. disabled | monthly |

- "For the Mend Renovate App, the Mend maintainers control when the Renovate
  process runs" (https://docs.renovatebot.com/getting-started/running/ &
  job-scheduling page) — a repo's `schedule` config can only RESTRICT within
  those job runs, never increase job frequency. No documented user-facing knob
  to request more frequent jobs on the Community (free) app.
- So: hosted-app best-case discovery latency for this repo (which merges
  Renovate PRs, i.e. "activated"/hot) ≈ **4 hours**, provided the repo-level
  Friday `schedule` is overridden. Self-hosted (e.g. `renovatebot/github-action`
  on a GHA cron, or Mend Renovate Community Edition server with webhooks) has
  **no platform floor** — cadence is whatever the runner cron provides.
- ray-manaloto/dotfiles is on the free hosted app (PR bodies link
  developer.mend.io job log; no self-hosted runner in repo).

### F4. postUpgradeTasks: hosted = short Mend-approved command allowlist (undocumented); arbitrary commands remain self-hosted-only; Renovate 43 (2026-01-29) tightened both paths

- Hosted: "A limited set of approved `postUpgradeTasks` commands are allowed in
  the app. The commands are not documented, as they may change over time. You
  can find the allowed `postUpgradeTasks` commands in Renovate's log output,
  when searching for a log line which references `allowedCommands`." Source:
  https://docs.renovatebot.com/mend-hosted/hosted-apps-config/ (same text in
  repo docs `docs/usage/mend-hosted/hosted-apps-config.md` on main). So the
  2024-era "hosted never runs postUpgradeTasks" is outdated — but only
  Mend-blessed commands run; you cannot allowlist your own.
- Self-hosted: `allowedCommands` (renamed from `allowedPostUpgradeCommands`) is
  a global-admin regex allowlist; empty list ⇒ no tasks run. Source:
  https://docs.renovatebot.com/self-hosted-configuration/
- Renovate **43.0.0 (released 2026-01-29)** breaking changes ("secure by
  default"): implicit unsafe executions (gradle wrapper, `go generate`,
  `bazel mod deps`, mise lock) disabled by default behind the new global
  `allowedUnsafeExecutions` (values: `bazelModDeps`, `goGenerate`,
  `gradleWrapper`, `mise`); and "Commands that run through `postUpgradeTasks`
  will no longer run inside a shell" unless
  `allowShellExecutorForPostUpgradeCommands=true`. Sources:
  https://github.com/renovatebot/renovate/releases/tag/43.0.0 ,
  https://docs.renovatebot.com/self-hosted-configuration/
- `postUpgradeTasks.executionMode`: `"branch"` (run once per branch) vs
  `"update"` (run per dependency update) — per
  https://docs.renovatebot.com/configuration-options/ (postUpgradeTasks
  sub-options: commands, executionMode, fileFilters, installTools,
  workingDirTemplate, dataFileTemplate).
- Relevant preset detail: `jdx/renovate-config` itself carries a
  `postUpgradeTasks` rule (`commands: ["mise lock"]`, `executionMode: branch`,
  installTools mise/node/npm, fileFilters mise.lock + mise.*.lock) — but scoped
  to `matchManagers: ["mise"] + matchDatasources: ["npm"]` only. The lefthook
  lock update in PR #191 (aqua datasource) therefore came from the **native
  artifacts path (F1)**, not this postUpgradeTask. Whether Mend's approved
  command list includes `mise lock` for the npm-datasource rule is unverified
  (see U2).

### F5. mise manager coverage: backends and file patterns — the repo's system/runtime tiers are INVISIBLE to Renovate; the lock-refresh composite remains necessary

Per https://docs.renovatebot.com/modules/manager/mise/ (synced to mise
2026.7.0; read 2026-07-09):

- **Supported backends (verbatim): `core, asdf, aqua, cargo, gem, github, go,
  npm, pipx, spm, ubi, vfox`.** Not listed (⇒ not understood for version
  updates): **conda**, **http**, dotnet, java, gitlab, nuget. Known gaps:
  asdf/vfox plugin syntax, aqua `http`-type packages / `version_filter`, some
  ubi/github tools with regex/prefix version options. Also: only the FIRST
  (primary) version of a tool is updated, not fallbacks.
- **Default managerFilePatterns (verbatim):** `**/{,.}mise{,.*}.toml`,
  `**/{,.}mise/config{,.*}.toml`, `**/.config/mise{,.*}.toml`,
  `**/.config/mise/{mise,config}{,.*}.toml`, `**/.config/mise/conf.d/*.toml`,
  `**/.rtx{,.*}.toml`.
  - Matched in this repo: root `mise.toml`; `.config/mise/conf.d/shared.toml`
    (the 20 exact-pinned shared tools — covered ✔).
  - **NOT matched: `.devcontainer/mise-system.toml` and
    `.devcontainer/mise-runtime.toml`** (hyphenated names fit no pattern), and
    correspondingly `mise-system.lock` / `mise-runtime.lock` are not recognized
    lockfiles (docs name `mise.lock`, `mise.local.lock`, `mise.{env}.lock`
    variants only). Repo lockfiles present: `mise.lock`,
    `.config/mise/mise.lock`, `.devcontainer/mise-system.lock`,
    `.devcontainer/mise-runtime.lock` (Glob, working tree).
  - Those two tiers are all-`latest` + lock anyway, so version PRs are moot —
    but it means **Renovate (hosted OR self-hosted) cannot refresh
    mise-system.lock / mise-runtime.lock**: the daily `refresh.yml` →
    `./.github/actions/lock-refresh` composite is the only mechanism that
    regenerates all three/four locks together, and stays load-bearing under
    every Renovate topology. (One could rename tiers to `mise.system.toml` /
    `mise.{env}.toml` shapes or add `managerFilePatterns` for the toml side —
    but lock recognition for hyphenated companions would still be custom.)
- **lockFileMaintenance**: "Lock file maintenance is supported via the
  `lockFileMaintenance` option" — i.e. periodic re-resolution of `mise.lock`
  even without version bumps; jdx preset enables it (7-day minimumReleaseAge,
  grouped). Runs through the same `mise trust`+`mise lock` unsafe-execution
  path as F1, so it works on hosted now too (for the matched lockfiles only).
  Default lockFileMaintenance schedule is early-morning
  (`* 0-3 * * *`, "before 4am") unless overridden.

### F6. git-refs digest tracking (clang-p2996) works on hosted, but its cadence = job frequency × schedule gate; no event-driven trigger exists in Renovate

- The `git-refs` datasource "returns a reference from a Git repository"; branch
  HEAD tracking = named ref in `currentValue` + match on `currentDigest`
  (exactly the repo's customManager: `currentValueTemplate: "p2996"`,
  `currentDigest` from `docker-bake.hcl`/Dockerfile, `renovate.json:54-65`).
  Limitations: no versioning, no custom registry, **no release timestamps** (so
  `minimumReleaseAge` can't apply meaningfully to digests). Source:
  https://docs.renovatebot.com/modules/datasource/git-refs/
- Empirically working: PR #188 "update bloomberg/clang-p2996 digest to 7220baf"
  (2026-07-08, automerged same day). Source:
  https://github.com/ray-manaloto/dotfiles/pull/188
- Cadence: a digest bump is created only when a Renovate job runs AND the
  repo `schedule` window is open. Today: Friday-only (F2). After a schedule
  override: hosted hot cadence ≈ every 4h (F3). Renovate has no
  push/commit-webhook trigger from the UPSTREAM repo (bloomberg/clang-p2996) —
  polling at job cadence is the ceiling; sub-4h upstream-commit reaction on
  hosted requires a non-Renovate trigger (repository_dispatch etc. — angle #3's
  territory).
- Same logic applies to the gcc-latest custom HTML datasource (PR #189,
  observed working with `minimumReleaseAgeBehaviour: timestamp-optional`,
  `renovate.json:26-30`).

### F7. Version currency of the hosted app (context for trusting current-docs claims)

- Hosted app ran 43.242.2 on 2026-07-08 (repo PR debug markers) vs 43.209.4 on
  2026-06-08 (discussion #43562) — Mend tracks Renovate releases within days,
  so current docs.renovatebot.com behavior ≈ hosted behavior, with occasional
  ~days-to-weeks lag windows (exactly the lag that bit mise.lock users between
  43.210.1's release and Mend's rollout + unsafe-execution enablement).

## Uncertainties / gaps

- **U1 — Why did all 6 Renovate PRs land on Wednesday 2026-07-08 despite the
  Friday-only schedule?** Most plausible: a manual "run now" from the Mend
  developer portal and/or first full run after the renovate.json rework that
  day (PR #187 "pin dependencies" is characteristic of fresh config adoption;
  the repo's PR-#187 breakage fix landed the same day). Not resolved; does not
  change F2 (the PR bodies themselves assert the Friday gate for future branch
  creation).
- **U2 — Exact contents of Mend's hosted `allowedCommands` allowlist** are
  deliberately undocumented; whether `mise lock` (as a postUpgradeTask command,
  distinct from the native artifacts path) is on it is unverified. Discover via
  the repo job log at developer.mend.io (search "allowedCommands").
- **U3 — Formal confirmation that Mend enabled `allowedUnsafeExecutions:
  ["mise", …]` on the hosted app**: inferred from code-path analysis (F1
  gating) + the observed successful lock regeneration; no Mend changelog page
  found announcing it. A hosted job log would show the warning line if it were
  disabled.
- **U4 — PR #191's displayed schedule was `* 0-3 * * *` (daily 00:00-03:59)
  while sibling PRs showed Friday-only.** Source of that per-package schedule
  not identified (possibly a since-changed rule in jdx/renovate-config, or a
  mise-manager-scoped rule present on 2026-07-08); today's preset default.json
  has only the top-level Friday schedule. Worth re-checking the preset's git
  history before relying on exact per-surface windows.
- **U5 — Hosted webhook-reactivity**: the job-scheduling docs page describes
  only the four cron-ish schedulers; the degree to which the hosted app also
  reacts to repo events (config pushes, dashboard checkboxes) is not documented
  there and was not probed.
- **U6 — Docs summaries via WebFetch are model-condensed**; verbatim-critical
  items (backend list, file patterns, artifacts.ts commands, 43.0.0 notes,
  preset JSON) were cross-checked against raw GitHub sources, but secondary
  phrasing (e.g. executionMode semantics) rests on docs-page summaries + search
  corroboration.

## Verification addendum (second pass, 2026-07-09, GitHub API via MCP)

Re-probed the load-bearing claims independently in a second pass:

- **F1 CONFIRMED empirically.** `GET pulls/191` on ray-manaloto/dotfiles:
  author `renovate[bot]`, `commits: 1` (head `2aa8722`), `changed_files: 2`,
  created 2026-07-08T15:17:19Z, merged 15:19:34Z by `renovate[bot]`
  (automerge). `GET pulls/191/files`: `mise.toml` (+1/−1, lefthook
  2.1.9→2.1.10) and `mise.lock` (+22/−22 — per-platform `sha256` checksums,
  release URLs, `url_api` asset IDs, `provenance = "github-attestations"` all
  regenerated for v2.1.10). The Mend-hosted app therefore executed the
  `mise trust`+`mise lock` unsafe-execution artifacts path successfully —
  hosted CAN regenerate the root `mise.lock` in the same renovate commit as of
  2026-07-08. Note lefthook is `aqua:evilmartians/lefthook` backend, so this
  was the native `updateArtifacts` path, not the jdx preset's npm-scoped
  postUpgradeTask.
- **U4 partially corroborated:** PR #191's body prints "Branch creation —
  Between 12:00 AM and 03:59 AM (`* 0-3 * * *`)" (timezone America/Chicago) —
  a DAILY early-morning window for this update, not the preset's Friday-only
  top-level schedule; that `* 0-3 * * *` shape equals Renovate's default
  `lockFileMaintenance` schedule, suggesting a manager- or maintenance-scoped
  schedule rule applied. Yet the PR was *created* 10:17 AM Chicago — outside
  both windows — which supports U1's manual-trigger/config-change-job
  hypothesis for the 2026-07-08 batch.
- **Doc-based capability split re-verified this pass** (all fetched
  2026-07-09): hosted job floors 4-hourly Community / hourly Enterprise, repo
  `schedule` can only restrict (mend-hosted/job-scheduling +
  key-concepts/scheduling); hosted postUpgradeTasks = undocumented
  Mend-approved `allowedCommands` list, discoverable only in job logs
  (mend-hosted/hosted-apps-config); `allowedUnsafeExecutions` values
  `bazelModDeps|goGenerate|gradleWrapper|mise`, default `[]`, global-only
  (self-hosted-configuration); mise manager backends verbatim `core, asdf,
  aqua, cargo, gem, github, go, npm, pipx, spm, ubi, vfox` — no conda/http
  (modules/manager/mise + repo readme on main); mise lock support merged
  2026-05-19 (renovatebot/renovate#42591, v43.186.0), allowlist gate merged
  2026-06-03 (#43606, v43.210.1); jdx/renovate-config default.json verbatim
  `"schedule": ["* * * * 5"]`, `"minimumReleaseAge": "7 days"`,
  `lockFileMaintenance` enabled 7d, npm-scoped `postUpgradeTasks: {commands:
  ["mise lock"], executionMode: "branch", installTools: {mise,node,npm}}`.
- **One additive fact:** the v43 lockFileMaintenance grouping/splitting
  regression (PR #40781) was fixed in 43.20.1 (2026-02-17) — grouping of
  lock-maintenance PRs works again
  (renovatebot/renovate discussion #41204).

## GitHub repos touched

- [renovatebot/renovate](https://github.com/renovatebot/renovate) — mise manager docs/readme + artifacts.ts source, self-hosted & hosted-app docs, 43.0.0 release notes, discussions #43562, issues #40568.
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — verbatim default.json preset (Friday schedule, mise postUpgradeTasks rule, lockFileMaintenance).
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — renovate.json, lockfile Glob, and empirical Renovate PRs #187–#192 (files, commits, debug markers) via GitHub API.
- [jdx/mise](https://github.com/jdx/mise) — release notes surfaced inside PR #190 body (2026.7.1/7.2 lockfile behavior context); mise.lock docs referenced by Renovate issue #40568.
