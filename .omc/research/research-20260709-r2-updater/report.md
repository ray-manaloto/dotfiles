# Run C — Version/commit discovery + build triggering (updater topology)

Synthesis report, 2026-07-09. Domain: updater/discovery/build-trigger topology
for ray-manaloto/dotfiles, evaluated against the working baseline
(`refresh.yml` daily lock refresh, `ci.yml` nightly `:dev` republish, hosted
Renovate with the jdx preset + 6 custom managers, Dependabot for GHA actions —
`.omc/research/research-20260709-r2-inventory/report.md` § Updater topology).

Inputs: five angle reports in `agents/` (renovate-capabilities, mise-native,
event-driven, git-pins, companion-artifacts), each independently re-verified;
10 load-bearing claims adversarially verified with 3 votes each (9 CONFIRMED
3/3, 1 CONFIRMED 2/3 with its absolute clause refuted — see "Refuted /
unverified claims").

---

## Executive summary — RECOMMENDATION: KEEP + EXTEND the incumbent hybrid (do NOT self-host Renovate)

**Keep the hosted-Renovate + mise-native-refresh.yml hybrid and reverse
yesterday's self-hosted-Renovate lean.** Its strongest argument is empirically
dead: on 2026-07-08 the Mend-hosted app regenerated the root `mise.lock` in
the same renovate[bot] commit as the pin bump — PR #191, single commit
`2aa8722`, `mise.toml` +1/−1 and `mise.lock` +22/−22 with fresh per-platform
sha256s (https://github.com/ray-manaloto/dotfiles/pull/191; CONFIRMED 3/3).
The unsafe-execution path shipped in renovate v43.186.0 (PR #42591,
2026-05-19), was gated behind the global `allowedUnsafeExecutions: ["mise"]`
in v43.210.1 (PR #43606, 2026-06-03), and Mend has evidently enabled it
(inference from the empirical success — no public announcement; enablement
happened between 2026-06-08 and 2026-07-08).

Meanwhile the actual "daily-or-better" gap is not a hosted-app limit at all:
it is a **silently inherited Friday-only schedule** from
`github>jdx/renovate-config` (`"schedule": ["* * * * 5"]`, America/Chicago),
which `renovate.json` never overrides (CONFIRMED 3/3 — PR #188's body prints
"Branch creation — Only on Friday"). A **one-line
`"schedule": ["at any time"]` override in renovate.json** unlocks the hosted
app's ~4-hourly "activated" cadence and is the cheapest daily-or-better win.
And a **real baseline bug** surfaced: `refresh.yml`'s `open-refresh-pr`
`paths:` list omits `.devcontainer/mise-runtime.lock`
(`refresh.yml:107-111`), so the daily refresh regenerates but never commits
the runtime lock — runtime-tier tools (claude-code, gemini-cli, codex, fnox)
are never actually refreshed by the daily job.

### The concrete change list (priority order)

1. **One-line renovate.json fix** — add `"schedule": ["at any time"]` (repo
   config overrides the preset). Converts the Renovate surface from weekly to
   the hosted app's ~4-hourly "activated" cadence — daily-or-better met with
   zero new infrastructure. (One verifier traced PR #191's daily
   `* 0-3 * * *` window to a since-removed `schedule:daily` extend at that
   PR's base commit `0ab12b0` — empirical proof that a repo-level schedule
   override beats the inherited preset gate.)
2. **One-line refresh.yml fix** — add `.devcontainer/mise-runtime.lock` to
   the `open-refresh-pr` `paths:` list (`refresh.yml:107-111`); update the
   stale "three committed lockfiles" header (the real artifact set is five).
   Stop enumerating artifact paths anywhere the coverage tests don't derive
   from.
3. **Keep refresh.yml + the lock-refresh composite unchanged in role** — it
   is irreplaceable under EVERY Renovate topology (CONFIRMED 3/3): Renovate's
   mise manager cannot see the hyphenated `.devcontainer/mise-system.toml` /
   `mise-runtime.toml` (default `managerFilePatterns` require dot-separated
   names), its `lockfile.ts` only ever derives `mise.lock` /
   `mise.local.lock` / `mise.{env}.lock` names (never `mise-system.lock` /
   `mise-runtime.lock`, and never with `MISE_ENV=runtime`), it has no
   `conda:` / `http:` backends (the image tiers' ~28 conda tools +
   `http:claude` are invisible), and no Renovate execution can reproduce the
   pinned-MISE_VERSION / linux-x64 / provenance-strip staged pipeline
   (`lock-refresh/action.yml:32-62`).
4. **Update the now-stale in-repo absolutes** per the tool-currency rule:
   "the hosted app can never run mise lock" (`refresh.yml:12-18`,
   `lock-refresh/action.yml:8-10`, `python/verification/suites.toml:641`) is
   now only half-true — narrow it to "image locks + devcontainer lock only".
5. **Close the devcontainer-feature two-PR gap** with a ~40-line hybrid
   micro-workflow: on `renovate/**` PRs touching `devcontainer.json`, run
   `devcontainer upgrade` and push with the existing refresh App token (never
   `secrets.GITHUB_TOKEN` — its pushes don't trigger CI); add the App author
   to `gitIgnoredAuthors`; make the job a required check (closes the
   automerge race). Optionally extend it to MISE_VERSION-bump PRs to close
   the format-skew deadlock (Q5, window a).
6. **p2996 pin: pick ONE writer.** Recommended: keep the git-refs
   customManager (config-only, adequate at ~4h after fix #1; upstream moves
   ~2-4 commits/month). The deterministic alternative — resurrecting the
   retired `p2996-refresh` job (module, tests, mise task all still in-tree) —
   is justified only if a guaranteed cadence bound or same-PR lock regen is
   wanted, and then the git-refs customManager must be deleted in the same
   change (dual writers race).
7. **Do NOT buy sub-daily discovery for freshness** — upstream event rates
   (p2996 ≈ weekly-in-bursts, gcc deb ≈ weekly) × ~1.5-2h pipeline latency
   make it noise. DO buy **punctuality insurance**: 2026 GHA scheduled-queue
   drift is multi-hour and worsening (staff-acknowledged), which already
   threatens the deliberate 00:00→02:00 stagger (issue #116). Free hygiene
   now: move both crons off :00 (e.g. `17 0 * * *` / `23 2 * * *`); defer an
   external minute-accurate dispatcher until local drift is measured.
8. **gcc deb: discovery is NOT the bottleneck** — PR #189 sits blocked on the
   deliberate human sha256 gate (`Dockerfile:336-347`). The only lever is a
   policy decision for Ray (see Open questions), not tooling.

---

## Q1. Hosted vs self-hosted Renovate — 2026 capability split

### Job-frequency floors
- Mend-hosted Community plan: **"activated" repos run 4-hourly** (~6
  runs/day max); hourly is Enterprise-only; inactive repos daily, blocked
  weekly; repo config can only RESTRICT cadence within a job run, never
  increase job frequency
  (https://docs.renovatebot.com/mend-hosted/job-scheduling/,
  https://docs.renovatebot.com/key-concepts/scheduling/ — "Mend decides when
  Renovate runs"; CONFIRMED 3/3 twice, independently for the floor and for
  the not-user-increasable property; maintainer confirmation in
  renovatebot/renovate#15453). This repo automerges Renovate PRs, so it sits
  in the 4-hourly tier. Minor doc nit: a secondary status table on the same
  page says "Hourly" for new/activated; the authoritative scheduler table +
  Enterprise-only footnote support the 4-hourly Community reading.
- **The binding constraint today is config, not platform** (CONFIRMED 3/3):
  the jdx preset's top-level Friday-only `schedule` gates branch creation to
  weekly (verbatim `default.json`, in place since Apr 2026;
  `renovate.json:1-108` has no `schedule` key). Observed consequence: the
  2026-06-30 p2996 commit got its bump PR on 2026-07-08 (~8 days).
  `vulnerabilityAlerts` PRs bypass the gate by default
  (`schedule: []`, `prCreation: 'immediate'`).
- Self-hosted (e.g. renovatebot/github-action on a GHA cron) has **no
  platform floor** — sub-4h polling of the clang-p2996 branch HEAD (git-refs
  has "Release timestamp support: No", so it updates only when a job runs)
  is the main remaining self-hosted advantage (CONFIRMED 3/3). Given
  upstream cadence (~0.12 events/day), sub-4h is valueless here.
- On-demand escape hatch on hosted: the Dependency Dashboard "run again"
  checkbox can in principle be ticked via an API issue-body edit (~≤10 min
  hosted provisioning) — fail-soft near-on-demand without self-hosting
  (unverified live; the checkbox was once removed upstream, discussion
  #20386).

### postUpgradeTasks and unsafe executions
- Hosted postUpgradeTasks = a **limited, intentionally-undocumented
  Mend-approved allowlist**, discoverable only via the `allowedCommands` line
  in the repo's job log on developer.mend.io (CONFIRMED 3/3). Arbitrary
  commands (this repo's lock-refresh recipe) remain self-hosted-only via
  admin `allowedCommands` regexes; Renovate 43.0.0 (2026-01-29) also disabled
  shell execution in postUpgradeTasks by default
  (`allowShellExecutorForPostUpgradeCommands`,
  https://github.com/renovatebot/renovate/releases/tag/43.0.0).
- Separately from postUpgradeTasks, the **native mise artifacts path now
  works on hosted**: `updateArtifacts` execs `mise trust` + `mise lock`,
  gated on the Mend-controlled global `allowedUnsafeExecutions: ["mise"]`,
  and PR #191 proves it end-to-end on this repo (CONFIRMED 3/3). Note
  PR #191 rode the native artifacts path (lefthook is
  `aqua:evilmartians/lefthook`), not the jdx preset's npm-scoped
  `postUpgradeTasks: ["mise lock"]` rule.
- Hosted version currency: 43.242.2 running 2026-07-08 vs 43.209.4 on
  2026-06-08 — measured lag ~5 days (June) to ~13 days (July), so treat it
  as **1-2 weeks**, not "days" (CONFIRMED 3/3 with that quantitative
  correction). Docs-current ≈ hosted behavior, with rollout-lag windows —
  exactly what broke hosted mise.lock users between 43.210.1's release and
  Mend's rollout (discussion #43562). This is the one real residual hosted
  risk; refresh.yml as lock backstop mitigates it.

### Verdict
Self-hosting would buy: arbitrary postUpgradeTasks (superseded by change-list
items 2/3/5), sub-4h polling (valueless at these upstream rates), and
independence from Mend's opaque allowlist/rollout (real but small, mitigated
by the refresh.yml backstop). It would cost: operating Renovate,
bootstrapping uv/python/node/@devcontainers-cli inside its exec sandbox
(never probed end-to-end), and losing Mend's managed runs. **Keep hosted.**

## Q2. mise-native updater alternative — and what it loses

**A mise-native GHA job cannot REPLACE Renovate — it is structurally blind to
every non-mise surface** (CONFIRMED 3/3): GHA actions, the ubuntu digest, the
clang-p2996 git-refs SHA, the gcc-latest HTML datasource, `.chezmoiversion`,
the hk pkl pins — which include exactly the upstream-commit build triggers
this run is about (`renovate.json:33-104`). Every mise update mechanism
(`mise outdated --json`, `mise upgrade --bump`, `mise lock`,
`--dry-run-code`) is scoped to tools declared in mise config files; there is
no file-rewrite facility for foreign pins. Corroborating irony: jdx/mise
itself uses Renovate for its own GHA digest bumps (jdx/mise#5957), and the
jdx preset delegates discovery to Renovate, using `mise lock` only as
artifact regen.

The repo ALREADY runs the mise-native engine daily where it is optimal: the
all-latest image tiers, where "regenerate the lock" IS discovery
(`minimum_release_age = 7d` + excludes provide native cooldown). Moving the
20 exact-pinned shared tools to `mise upgrade --bump` would lose, vs
Renovate: changelogs in PR bodies, vulnerability-alert PRs that bypass
schedule/limits, per-dependency PR isolation/bisectability, `rollbackPrs`,
grouping/packageRules, the dependency dashboard — all cost, no unique gain,
plus a dual-writer race on `shared.toml` (**one engine per file**, always).

Worth borrowing without replacing: `mise outdated --json` /
`mise upgrade --dry-run-code` as a cheap change detector — e.g. to skip
no-op nightly republishes, or dispatch a build the moment a version clears
the 7-day cooldown. Caveat: whether `outdated` filters by
`minimum_release_age` is undocumented, and the cooldown code path had bugs
fixed as recently as June 2026 (jdx/mise PRs #10310/#10344) — probe before
relying on it.

## Q3. Sub-daily / event-driven discovery — mechanics and meaningful cadence

- **GHA `schedule` reliability (2026)**: 5-min nominal floor, but
  community-measured average delays grew to **>4h by May 2026**, GitHub staff
  confirmed scheduled drops grew >30% in ~2 months with no near-term fix
  (community discussion #196910; actions/runner#4468), and the docs say
  queued scheduled jobs "may be dropped". **This already threatens the daily
  baseline**: the deliberate 00:00→02:00 refresh→publish stagger (issue
  #116) assumes ≤2h end-to-end; multi-hour drift can invert it so the
  nightly publishes yesterday's pins. Mitigations: odd-minute crons (both
  repo crons sit at :00, the documented worst window); refresh.yml is
  idempotent-catch-up, so drops delay rather than lose updates.
- **Dispatch beats cron for punctuality**: `workflow_dispatch` /
  `repository_dispatch` runs enter the normal event queue, not the degraded
  scheduled queue. An external minute-accurate scheduler (cron-job.org,
  Cloudflare cron, a Routine on an always-on box) firing
  `gh workflow run refresh.yml` (the trigger already exists,
  `refresh.yml:41`) restores punctuality with zero workflow rewrites, at the
  cost of one fine-grained credential held outside GitHub.
- **True upstream push events do not exist**: webhooks require upstream
  admin; `repository_dispatch` must be sent by something with write access
  to OUR repo — every "event-driven" topology is really our own poller plus
  a dispatch hop. Cheap poll primitives, both verified live: per-branch Atom
  feeds (`bloomberg/clang-p2996/commits/p2996.atom`, unauthenticated,
  quota-free) and ETag-conditional REST (authorized 304s don't count against
  the rate limit). Release-watch services (newreleases.io etc.) are
  release/tag-shaped and cannot see a tagless branch HEAD or a rolling deb
  on an HTML index — dismissed.
- **What cadence is meaningful given ~1h builds**: with upstream events every
  ~7-9 days and ~1.5-2h pipeline latency (build + smoke + ci-gate +
  automerge), cutting detection from 24h to 1h removes a few hours/week of
  mean staleness — invisible. Detection finer than pipeline latency (~2h)
  cannot compound: the singleton `chore/lock-refresh` branch + `lock-refresh`
  concurrency group collapse multiple detections into one effective update.
  Sub-daily's only real value is **bounding worst-case staleness when the
  daily cron drifts or drops** — reliability insurance for the daily
  contract, not fresher pins. A punctual 3-6h external dispatch dominates a
  5-min GHA cron on every axis that matters here.
- **Anti-pattern guard**: sub-daily triggers must target the DISCOVERY
  workflow (refresh.yml shape — no-drift→no-PR, path gate, content-hash
  probes, concurrency groups all already in place), never `ci.yml`, whose
  schedule path is always-build by design (each spurious fire is a ~1h
  GHCR-pushing build churning `:dev` digests).

## Q4. The clang-p2996 branch-HEAD pin and the gcc-latest rolling deb

- **clang-p2996 `p2996` HEAD**: upstream moves 2-4 commits/month in bursts;
  the pin is current (`7220baf` = `Dockerfile:233`, matches the live Atom
  feed). Best mechanism at daily-or-better: **the existing git-refs
  customManager after the schedule fix** — hosted ~4h cadence, config-only,
  proven working (PR #188 automerged 2026-07-08). The fully-deterministic
  alternative is resurrecting the retired `p2996-refresh` job
  (`python/src/dotfiles_setup/p2996_refresh.py` + `tests/test_p2996_refresh.py`
  + `mise.toml:675-677`, retired 2026-07-07 in favor of git-refs): exact cron
  control, `git ls-remote` costs nothing (git smart-HTTP, no REST quota), and
  same-PR companion regen via the proven `open-refresh-pr` pattern. If it
  returns, drop the git-refs customManager in the same change — one writer
  per pin. Atom feeds are a signal fallback only: Renovate's custom
  datasource supports no xml/atom format, and `git ls-remote` is simpler for
  a homegrown poller.
- **gcc-latest deb**: structurally weekly (GCC snapshots ~weekly per
  gcc.gnu.org/snapshots.html, published ~1 day later on the jwakely index).
  Discovery via the custom HTML datasource works (PR #189 created
  same-day-as-run; `minimumReleaseAgeBehaviour: timestamp-optional` already
  in place). The end-to-end bottleneck is the **deliberate human sha256
  gate**: `GCC_LATEST_DEB_SHA256` is "Deliberately NOT Renovate-managed …
  supply-chain friction by design" (`Dockerfile:336-347`), and PR #189 is
  empirically blocked (`mergeable_state: "blocked"`) on it. No discovery
  cadence change helps; the only lever is whether a trusted in-repo CI job
  may `curl + sha256sum + commit` hash and ARG in the same PR. The security
  delta is small — the human performs the same TOFU download over TLS with
  no independent verification channel; the dated filename remains the
  immutability handle — but it is a documented posture change (#160 T13):
  Ray's call, never silently automatable. Hosted Renovate cannot do it
  (can't run commands); only the GHA job can, slotting beside lock-refresh
  in refresh.yml.

## Q5. Same-PR companion-artifact regeneration, per topology

The real artifact set is **five**, not three (evidence:
`tests/test_lock_coverage.py:33-143`, `lock-refresh/action.yml`): root
`mise.lock`; `.config/mise/mise.lock` (shared tier — mise writes one lock per
config dir, and Renovate's `lockfile.ts` maps `conf.d/` configs to the parent
dir's lock, matching this repo exactly); `.devcontainer/mise-system.lock`;
`.devcontainer/mise-runtime.lock`; `.devcontainer/devcontainer-lock.json`.
The coupled multi-file string pins (ubuntu digest, `CLANG_P2996_REF`, hk pkl
×3, `MISE_VERSION`, gcc deb ARG) are already same-PR safe under hosted
Renovate via multi-pattern regex customManagers; the gcc deb pin has no
companion artifact at all.

| Topology | root+shared locks | system+runtime locks | devcontainer lock | Atomicity |
|---|---|---|---|---|
| Hosted Renovate alone (post-PR-#191) | **in-commit** (native mise artifacts path) | never (files invisible; pinned-writer constraint) | never (devcontainer manager exports no `updateArtifacts`) | same-commit for the mise slice; feature-tag bumps hard-red |
| Incumbent hybrid (hosted + daily refresh.yml) | in-commit + daily re-resolve | daily (runtime lock currently DROPPED — bug, fix #2) | daily; feature-tag bumps red until manual regen | eventual ≤24h |
| Self-hosted Renovate + allowedUnsafeExecutions + postUpgradeTasks | native | postUpgradeTasks re-hosting the composite recipe (bootstrap unprobed) | postUpgradeTasks | same-commit (strongest) |
| mise-native job only | same PR | same PR | same PR | same PR — but discovery must be re-invented (Q2: no) |
| Hybrid + regen-push micro-workflow | native | stays with refresh.yml | 2nd commit, same PR (required check closes the automerge race) | same-PR at merge |

Known broken-intermediate windows in the incumbent, and fixes:

- **(a) MISE_VERSION bump deadlock**: lockstep is by-schedule, not same-PR
  (`renovate.json:89`); a format-incompatible mise bump goes red under
  `--locked` and the daily refresh (running main's OLD pin) cannot unblock
  it. Only a same-PR regen with the NEW pin closes it — the micro-workflow,
  extended.
- **(b) devcontainer feature-tag bump**: hard-red until someone pushes
  `devcontainer upgrade` (the lock-coverage regex captures the full key
  including the tag, `test_lock_coverage.py:26,127-143`) — the clearest
  two-PR victim; closed by the micro-workflow. Push with the App token;
  add it to `gitIgnoredAuthors` (else Renovate stops updating the branch);
  keep the regen idempotent + skip-on-empty-diff (rebase-loop hazards:
  renovate#17528/#14656/#9351).
- **(c) runtime-lock staging omission**: `open-refresh-pr` paths omit
  `.devcontainer/mise-runtime.lock` while the composite regenerates it every
  run (`lock_refresh.py:52,143-162`) — fix now (change list #2). General
  lesson: enumerated add-path lists are a fragility class; derive them from
  the same source of truth the coverage tests use.
- `lockFileMaintenance` is NOT a same-PR mechanism (separate dedicated PR,
  never grouped with version updates, covers at most the root+shared locks)
  — skip it while refresh.yml exists; enabling it would ADD a duplicate PR
  stream.

The lock-refresh composite remains the ONLY writer capable of artifacts 3-4
(pinned image mise on linux-x64, 5-pass rate-limit convergence, provenance
strip, lock-collect coverage validation) — load-bearing under every topology
(CONFIRMED 3/3).

## Recommended trigger topology (end state)

1. **Discovery, pinned + non-mise surfaces**: hosted Renovate, ~4-hourly
   after the one-line schedule override; git-refs customManager stays the
   sole p2996 writer; custom HTML datasource stays the gcc-deb discoverer;
   root + shared mise locks regenerate in-commit via the native artifacts
   path.
2. **Discovery-by-re-resolution, image tiers**: refresh.yml daily (odd-minute
   cron), lock-refresh composite as sole writer of the five-artifact set,
   auto-merge on ci-gate — with the runtime-lock staging fix.
3. **Build triggering**: unchanged — pin-bump PRs touch build inputs, the CI
   `changes` filter runs the full build+smoke chain on the PR, `promote`
   retags `:dev` on merge; nightly ci.yml (odd-minute cron) republishes for
   layer freshness. Optional cheap upgrade: gate the nightly on
   `mise upgrade --dry-run-code` to skip no-op republish days.
4. **Gap-closers**: the ~40-line regen-push micro-workflow on `renovate/**`
   branches (feature bumps now, MISE_VERSION bumps optionally), as a
   required check.
5. **Punctuality insurance (deferred)**: external minute-accurate dispatcher
   → `workflow_dispatch` on refresh.yml, 2-4×/day, only if measured local
   cron drift shows the stagger inverting.

---

## Contradictions with the domain-brief baseline (flagged loudly)

1. **"refresh.yml regenerates all committed lockfiles" is FALSE today** —
   the runtime lock is regenerated then silently discarded by the enumerated
   add-paths list (`refresh.yml:107-111`). One-line fix, do it first.
2. **"Three committed lockfiles" undercounts** — five companion artifacts
   move together.
3. **"Hosted does NOT run postUpgradeTasks" is outdated as an absolute** —
   hosted runs a limited undocumented Mend-approved allowlist; only
   ARBITRARY commands remain self-hosted-only. Orthogonally, the native mise
   artifacts path (not postUpgradeTasks) now regenerates root mise.lock on
   hosted (PR #191).
4. **Effective Renovate cadence today is WEEKLY (Friday-only)** by silent
   preset inheritance — daily-or-better is unmet by config, not by
   hosted-app limits.
5. **Yesterday's self-hosted-Renovate recommendation is reversed** on new
   empirical evidence (PR #191) + the schedule-inheritance discovery.
6. **The 2h refresh→publish stagger (issue #116) is at risk** from 2026 GHA
   scheduled-queue drift (>4h episodes, worsening) — the baseline's implicit
   "daily crons fire near-on-time" assumption no longer holds.

## Refuted / unverified claims

**Partially refuted (do not assert the absolute):**

- "The hosted Mend app does not permit postUpgradeTasks" — verdict CONFIRMED
  2/3 with one REFUTE vote against the absolute clause: current docs state
  "A limited set of approved postUpgradeTasks commands are allowed in the
  app" (undocumented, mutable, discoverable via `allowedCommands` job-log
  lines). The surviving narrow claim: arbitrary/custom commands (this repo's
  lock-refresh recipe) require self-hosting.

**Minor verifier corrections folded in above:**

- PR #191's total diff is +23/−23 (the +22/−22 figure is mise.lock alone).
- Renovate's mise manager backend list also includes `dotnet` (omitted from
  the claim's 12-backend list; does not affect the conclusion — still no
  conda/http).
- "Hosted tracks Renovate releases within days" — directionally right, but
  measured lag is ~5-13 days; treat as 1-2 weeks.
- PR #191's daily `* 0-3 * * *` window traced by one verifier to a
  since-removed `schedule:daily` extend in renovate.json at that PR's base
  commit (`0ab12b0`, removed 2026-07-08) — resolving angle-report
  uncertainty U4 and empirically proving repo-level overrides beat the
  preset.

**Unverified — flagged, not asserted as fact:**

- Mend formally enabled `allowedUnsafeExecutions: ["mise"]` on hosted: an
  inference from PR #191's success + the code-path gating (artifacts.ts
  returns null unless allowlisted); no public Mend announcement exists.
- The exact contents of Mend's hosted `allowedCommands` allowlist (incl.
  whether the jdx preset's npm-scoped `mise lock` postUpgradeTask is on it)
  — check the repo job log at developer.mend.io.
- Why all 6 Renovate PRs landed Wednesday 2026-07-08 despite the Friday gate
  (most plausible: manual portal run / fresh-config run after the
  renovate.json rework that day).
- Dashboard-checkbox automation via API issue-edit (design fail-soft; the
  checkbox was once removed upstream, discussion #20386).
- This repo's OWN cron drift — measure `gh run list --workflow refresh.yml
  --json createdAt` deltas before treating >4h as the local number.
- Self-hosted Renovate sandbox bootstrap of uv/python/@devcontainers-cli for
  postUpgradeTasks — never probed end-to-end (moot under the
  recommendation).
- Whether `mise outdated` filters by `minimum_release_age` (matters only for
  the optional cooldown-cleared dispatch trigger); the cooldown path had
  bugs fixed June 2026 (jdx/mise #10310/#10344).
- newreleases.io's "≤30 min" detection claim (third-party copy; immaterial —
  it cannot watch the hard targets anyway).

## Open questions for Ray (with recommended answers)

1. **Override the inherited Friday schedule with `"schedule": ["at any
   time"]` in renovate.json?** — Recommended: **YES, immediately**; it is
   the entire daily-or-better gap on the Renovate surface.
2. **Automate the gcc deb sha256 recompute in a trusted in-repo CI job
   (same-PR hash + ARG)?** — Recommended: **YES**; the human gate adds TOFU
   friction, not verification (same TLS download, no independent channel),
   and the dated filename stays the immutability handle. Document the
   posture change against #160 T13. If NO, accept ~weekly human latency on
   gcc bumps and leave PR #189-style PRs blocked by design.
3. **Keep git-refs for p2996 or resurrect the in-repo p2996-refresh job?** —
   Recommended: **keep git-refs** (config-only, ~4h after fix #1); resurrect
   the job only for a guaranteed cadence bound or same-PR lock regen — and
   then remove the git-refs customManager in the same change.
4. **Add the ~40-line regen-push micro-workflow (feature bumps +
   MISE_VERSION bumps)?** — Recommended: **YES**; it upgrades the two
   remaining hard-red windows to same-PR at ~zero operating cost, reusing
   the App token and composite steps.
5. **Add an external minute-accurate dispatcher for refresh.yml (cron-drift
   insurance)?** — Recommended: **DEFER** until the repo's own measured
   drift shows the 00:00→02:00 stagger actually inverting; do the free
   hygiene now (odd-minute crons).
6. **Let hosted Renovate keep updating root mise.lock in-commit?** —
   Recommended: **YES** (it already happened; strictly better than waiting
   for 00:00) — update the stale "Renovate can never…" comments and keep
   refresh.yml as the backstop for Mend rollout-lag windows.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — baseline files (renovate.json, refresh.yml, ci.yml, lock-refresh + open-refresh-pr composites, Dockerfile, docker-bake.hcl, p2996_refresh.py, test_lock_coverage.py, lock_refresh.py, suites.toml, mise tiers) + empirical Renovate PRs #187-#192 via GitHub API.
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — mise manager source (index/artifacts/lockfile/extract.ts), devcontainer manager, git-refs + custom datasource docs, hosted-app/job-scheduling/self-hosted/scheduling/configuration docs, 43.0.0 release notes, issues #40568/#17528/#14656/#9351/#15453, PRs #42591/#43606, discussions #43562/#43882/#31920/#14659/#20386/#34923/#27778/#11206.
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — verbatim default.json preset (Friday schedule, timezone, minimumReleaseAge, mise-lock postUpgradeTask, lockFileMaintenance).
- [jdx/mise](https://github.com/jdx/mise) — CLI docs (outdated/upgrade/lock/mise-lock/settings), releases v2026.6.2-v2026.7.4, discussion #10303, PRs #10310/#10344/#5957, issue #10694; local mintlify cache grepped first (partial mirror noted).
- [bloomberg/clang-p2996](https://github.com/bloomberg/clang-p2996) — live `commits/p2996.atom` feed (HEAD SHA + commit cadence).
- [jwakely/pkg-gcc-latest](https://github.com/jwakely/pkg-gcc-latest) — gh-pages Atom feed + jwakely.github.io index (deb publication cadence, redirect behavior).
- [renovatebot/base-image](https://github.com/renovatebot/base-image) — PR #3183 (mise added to the Renovate image, 43.244.0).
- [gcc-mirror/gcc](https://github.com/gcc-mirror/gcc) — weekly snapshot cadence via gcc.gnu.org/snapshots.html.
- [actions/runner](https://github.com/actions/runner) — cron-drift issues #2977/#4468.
- [community/community](https://github.com/orgs/community/discussions) — discussions #196910/#156282/#26384 (cron drift, dispatch limits).
- [lowlydba/cron-drift](https://github.com/lowlydba/cron-drift) — drift measurement tooling.
- [peter-evans/repository-dispatch](https://github.com/peter-evans/repository-dispatch) — GHA-to-GHA dispatch action.
- [peter-evans/create-pull-request](https://github.com/peter-evans/create-pull-request) — add-paths staging semantics (runtime-lock gap grounding).
- [suzuki-shunsuke/guide-github-action-renovate](https://github.com/suzuki-shunsuke/guide-github-action-renovate) — push-to-renovate-branch App pattern.
- [newreleasesio/client-go](https://github.com/newreleasesio/client-go) — release-watch service surface check (dismissed).
- [github/roadmap](https://github.com/github/roadmap) — issue #1187 (cron `timezone:` feature, Mar 2026).
- [mend/renovate-ce-ee](https://github.com/mend/renovate-ce-ee) — CE/EE scheduling defaults, hosted checkbox support.
