# Run C / Angle 5 — Same-PR companion-artifact regeneration

Research analyst report, 2026-07-09 (final; supersedes an earlier draft at
this path — see "Divergence note" at the end: the draft's two unique repo
findings were independently re-verified and kept, its hosted-app claim was
re-probed and corrected).

Question: for each candidate topology (hosted Renovate, self-hosted Renovate
with postUpgradeTasks, mise-native scheduled job, hybrid
Renovate-discovers + workflow-regenerates), how do ALL companion artifacts get
regenerated in the SAME PR — the mise lockfiles, devcontainer feature pins,
and the gcc deb pin — and which option avoids the two-PR /
broken-intermediate-state problem?

## The artifact set (what "all companions" means in this repo)

Five committed lock artifacts must move with their configs (evidence:
`tests/test_lock_coverage.py:33-143`, `.github/actions/lock-refresh/action.yml`):

| # | Artifact | Config it locks | Regen mechanism today |
|---|----------|-----------------|----------------------|
| 1 | `mise.lock` (root) | `mise.toml` host tools | `mise lock` on the runner (`lock-refresh/action.yml:26-31`) |
| 2 | `.config/mise/mise.lock` | `shared.toml` (20 exact-pinned host↔image tools) | same run — mise 2026.7.0 writes one lock PER CONFIG DIR (`test_lock_coverage.py:88-124`) |
| 3 | `.devcontainer/mise-system.lock` | image base tier | **bespoke staged pipeline**: `dotfiles-setup lock-stage` → pinned-`MISE_VERSION` installer → `MISE_ENV=runtime mise lock --platform linux-x64` ×5 convergence → `lock-collect` (coverage-validates + strips provenance) (`lock-refresh/action.yml:32-62`) |
| 4 | `.devcontainer/mise-runtime.lock` | image runtime tier | same staged pass — `collect_system_lock` writes BOTH (`python/src/dotfiles_setup/lock_refresh.py:52,143-162`) |
| 5 | `.devcontainer/devcontainer-lock.json` | devcontainer feature pins | `devcontainer upgrade --workspace-folder .` (`lock-refresh/action.yml:63-65`) |

Coupled **string pins** (ubuntu digest bake+Dockerfile, `CLANG_P2996_REF`
bake+Dockerfile, hk pkl ×3, `MISE_VERSION` ARG, gcc deb ARG) need multi-file
lockstep but NO regen step, and are already same-PR safe under hosted
Renovate: one regex customManager matching multiple `managerFilePatterns`
edits every file for the same dep in a single branch (`renovate.json:54-96`).
The gcc deb pin is a single Dockerfile ARG with no companion artifact — no
same-PR problem exists for it. The problem is confined to artifacts 1–5 and
the `MISE_VERSION` ↔ image-lock coupling.

Hard constraint shaping everything: artifacts 3–4 must be written by the
**exact pinned image mise version on linux-x64** ("lock formats are NOT
cross-version compatible", `lock-refresh/action.yml:41-44`; "macOS mise
silently omits linux-x64 conda checksums", `:12-13`) and must be
provenance-stripped (`mise install --system --locked` fail-closes on
provenance with verification off, jdx/mise#10694;
`test_lock_coverage.py:68-85`). A generic "run `mise lock` in the checkout"
can never produce artifacts 3–4.

## Findings

### F1. Renovate's mise manager gained same-PR lock updating in 2026 — and evidence shows the Mend-HOSTED app executes it

The repo's rationale comments ("the hosted app can never run `mise lock`",
`refresh.yml:12-14`, `lock-refresh/action.yml:8-10`) are now partially stale:

- The manager exports `updateArtifacts`, sets
  `supportsLockFileMaintenance: true` and `lockFileNames: ['mise.lock']`
  (<https://github.com/renovatebot/renovate/blob/main/lib/modules/manager/mise/index.ts>).
  `artifacts.ts` execs `mise trust <config>` then `mise lock <tools>` (full
  `mise lock` under lockFileMaintenance) and skips when there is no
  pre-existing lock or when `mise` is not in the global
  `allowedUnsafeExecutions` list
  (<https://github.com/renovatebot/renovate/blob/main/lib/modules/manager/mise/artifacts.ts>).
  Feature tracked in renovate#40568 (opened 2026-01); trust fix
  renovate#43606 shipped in ~43.210.1 (June 2026).
- `allowedUnsafeExecutions` is a global/admin option ("List of possibly
  unsafe executions which are permitted to run", values incl. `mise`;
  <https://docs.renovatebot.com/self-hosted-configuration/>) — repo users
  cannot set it. **But discussion #43562 (Mend-hosted app, v43.194.0,
  May 2026) shows the hosted run actually EXECUTING `mise lock`** — it
  failed with exit 1 on mise's "config files are not trusted" error, i.e.
  DURING execution, not skipped-before. Since `updateArtifacts` skips
  silently when mise is not allowed, execution on hosted implies Mend has
  `mise` in its central allow set; the blocker was the trust bug, whose fix
  (43.210.1) had not yet been deployed to the hosted platform as of
  2026-06-08 (hosted still at 43.209.4)
  (<https://github.com/renovatebot/renovate/discussions/43562>).
- `mise` was also added to the Renovate base Docker image in **43.244.0
  (2026-06-26)** after `spawn mise ENOENT` blocked lockFileMaintenance
  (`RENOVATE_BINARY_SOURCE=global`; renovatebot/base-image#3183;
  <https://github.com/renovatebot/renovate/discussions/43882>) — this is
  what makes the self-hosted path work out-of-the-box too.
- Lock-path mapping matches THIS repo exactly: `lockfile.ts` maps `conf.d/`
  configs to the parent dir's lock —
  `const lockDir = parentDirName === 'conf.d' ? upath.dirname(dirname) : dirname;`
  → `.config/mise/conf.d/shared.toml` → `.config/mise/mise.lock`, and
  `mise.toml` → `mise.lock`
  (<https://github.com/renovatebot/renovate/blob/main/lib/modules/manager/mise/lockfile.ts>).
- Additionally, the `github>jdx/renovate-config` preset this repo already
  extends (`renovate.json:3-5`) ships a belt-and-suspenders packageRule:
  `postUpgradeTasks: {commands: ["mise lock"], executionMode: "branch",
  fileFilters: ["**/mise.lock", "**/mise.*.lock"], installTools:
  {mise,node,npm}}` plus `lockFileMaintenance` automerge with a 7-day
  minimumReleaseAge
  (<https://raw.githubusercontent.com/jdx/renovate-config/main/default.json>).
  On hosted, postUpgradeTasks are limited to Mend's *undocumented* approved
  list ("A limited set of approved postUpgradeTasks commands are allowed in
  the app. The commands are not documented, as they may change over time" —
  discoverable only via `allowedCommands` log lines;
  <https://docs.renovatebot.com/mend-hosted/hosted-apps-config/>).

**Consequence:** for artifacts 1–2, hosted Renovate should now bump a pin in
`mise.toml`/`shared.toml` AND regenerate the adjacent lock **in the same
commit** — likely with zero new config, pending live verification (check the
next Renovate mise PR's diff / job log for `mise trust`+`mise lock` lines).

**Hard limits that survive:** the manager's file patterns
(`**/{,.}mise{,.*}.toml`, `**/.config/mise/conf.d/*.toml`, …;
<https://docs.renovatebot.com/modules/manager/mise/>) do NOT match the
hyphenated `.devcontainer/mise-system.toml`/`mise-runtime.toml`, and no
Renovate execution can satisfy the pinned-writer/linux-x64/provenance-strip
constraints on artifacts 3–4. Those tiers are all-`"latest"` anyway — there
is nothing for Renovate to *bump*; they are pure re-resolution, i.e.
refresh.yml's job. **The lock-refresh composite is irreplaceable for the
image tier under every topology.**

### F2. The incumbent's two-PR / broken-intermediate windows, enumerated

- (a) **`MISE_VERSION` Dockerfile bump** — the contract is
  lockstep-by-schedule, not same-PR: "Renovate bumps it, and the CI
  lock-refresh job regenerates the lock in lockstep" (`renovate.json:89`),
  i.e. up to ~24h of installer-pin ↔ lock-writer-version skew. Worse, if a
  bump lands a format-incompatible mise, the image build's `--locked`
  install rejects the old-format lock, the PR goes red, and the daily
  refresh (running main's OLD pin) cannot unblock it — a genuine ordering
  deadlock requiring a manual coupled regen. Only a same-PR regen executed
  with the NEW pinned version closes this (self-hosted postUpgradeTasks or
  the hybrid workflow, F4/F5).
- (b) **Host-tool bump with stale lock** — the per-PR coverage gate is
  deliberately NAME-only ("Freshness of the resolutions is intentionally
  NOT checked here… would false-fail whenever any upstream tool released
  since the last refresh", `test_lock_coverage.py:1-11`), so a version bump
  historically merged green with the lock still holding the old version
  until 00:00. Mostly *inert* rather than broken (mise prefers locked
  versions), and now closed in-PR by F1 if hosted artifact updating is
  live.
- (c) **Devcontainer feature tag bump** — Renovate's `devcontainer` manager
  has NO `updateArtifacts` and never touches `devcontainer-lock.json`
  (index.ts exports only `extractPackageFile` + metadata;
  <https://github.com/renovatebot/renovate/blob/main/lib/modules/manager/devcontainer/index.ts>).
  And this repo's gate DOES bite here: `_FEATURE_KEY_RE` captures the full
  key **including the tag** (`test_lock_coverage.py:26,127-143`), so a
  feature tag bump without a same-PR `devcontainer upgrade` is hard-red
  until someone pushes the regen to the branch. Rare (features pinned at
  major tags; digest-pinning disabled after PR #187, `renovate.json:15-18`)
  but structurally unsolved in the incumbent — the clearest two-PR victim.
- (d) **Daily-refresh staging gap (real, current):** `refresh.yml`'s
  `open-refresh-pr` `paths:` lists artifacts 1, 2, 3, 5 —
  **`.devcontainer/mise-runtime.lock` is missing** (`refresh.yml:107-111`)
  even though the composite regenerates it every run
  (`lock_refresh.py:52,143-162`). Path-scoped staging silently drops the
  runtime-lock diff, so runtime-tier tools (fnox, claude-code, gemini-cli,
  codex, …) never get their resolutions refreshed by the daily job — the
  all-latest intent of the runtime tier is defeated, and the header comment
  "three committed lockfiles" (`refresh.yml:2-11`) is stale against the
  5-artifact reality. Fix is one line; the lesson generalizes: **enumerated
  add-path lists are a fragility class — stage the full regen diff or derive
  the list from the same source of truth the coverage tests use.**

### F3. `lockFileMaintenance` is NOT a same-PR mechanism

Disabled by default; default schedule "before 4am on monday" (settable to
daily); runs on its own dedicated branch/PR, never grouped with version
updates (<https://docs.renovatebot.com/configuration-options/>;
<https://github.com/renovatebot/renovate/discussions/31920>). It is a batch
re-resolution mechanism — the same role as refresh.yml, in a separate PR —
and with `supportsLockFileMaintenance: true` it could at most cover
artifacts 1–2, never 3–5. Enabling it alongside refresh.yml would ADD a
duplicate PR stream, not remove one. Not a candidate.

### F4. Self-hosted Renovate + postUpgradeTasks: the only single-mechanism, same-COMMIT solve for all five artifacts

- postUpgradeTasks (`commands`, `executionMode: update|branch`,
  `fileFilters`, `installTools`) run in the branch workspace and their
  output files are committed into the update's own commit — strictly
  stronger than any second-commit pattern; gated by the admin
  `allowedCommands` regex list ("If this list is empty then no tasks will be
  executed") plus `allowedUnsafeExecutions: ["mise"]` for the native
  artifact path (<https://docs.renovatebot.com/configuration-options/>,
  <https://docs.renovatebot.com/self-hosted-configuration/>).
- Concretely: a self-hosted run (e.g. `renovatebot/github-action` on a GHA
  cron — ubuntu-latest IS the linux-x64 platform the image locks require)
  would allowlist the incumbent composite's own recipe as post-upgrade
  commands — `dotfiles-setup lock-stage` → pinned installer →
  loop → `lock-collect`, plus `devcontainer upgrade` — scoped via
  packageRules to the managers whose bumps invalidate each artifact
  (`mise`, the `MISE_VERSION` regex manager, `devcontainer`). This closes
  every window in F2 including the MISE_VERSION deadlock (the bump PR's own
  regen runs the NEW pinned mise).
- Costs, this angle only: operating Renovate; bootstrapping uv/python/
  node/@devcontainers/cli inside Renovate's exec sandbox per branch
  (untested end-to-end, U5); and the regen recipe living behind Renovate's
  config surface — mitigated by keeping all logic in the `dotfiles_setup`
  CLI (zero-bash-logic policy makes the entry points reusable verbatim).

### F5. Hybrid: hosted Renovate discovers, a workflow pushes regen to the Renovate branch — closes the gaps at second-commit grade

- Mechanics, all documented: trigger on `pull_request` where
  `startsWith(github.head_ref, 'renovate/')` and the diff touches
  mise/devcontainer surfaces; run the relevant `lock-refresh` composite
  step(s); push only when a diff exists. Push with the existing refresh
  GitHub App token, NOT `secrets.GITHUB_TOKEN` — GITHUB_TOKEN events "will
  not create a new workflow run" (GitHub recursion guard), so the regen
  commit's checks would never fire (community pattern writeups:
  <https://www.chris.qa/using-github-workflows-to-automate-adding-extra-commits-to-renovate-pull-requests/>
  (2023-10-17);
  <https://suzuki-shunsuke.github.io/guide-github-action-renovate/guide/>,
  which recommends a dedicated App + branch protection on `renovate/*`).
- Renovate must ignore the bot author: "By default, Renovate will treat any
  PR as modified if another Git author has added to the branch… add the
  other Git author(s) to `gitIgnoredAuthors`"
  (<https://github.com/renovatebot/renovate/blob/main/docs/usage/configuration-options.md>);
  otherwise "Renovate stops all updates of that branch"
  (<https://docs.renovatebot.com/updating-rebasing/>). Flip side: an
  ignored-author branch counts as unmodified, so Renovate rebases/recreates
  freely, discarding the regen commit → CI refires → workflow re-pushes.
  Converges only if the regen is idempotent + skip-on-empty-diff; failure
  modes are documented upstream (infinite force-push loops renovate#17528,
  renovate#14656/discussion#14659 — workaround `rebaseWhen: never`;
  rebase-flood renovate#9351).
- **Atomicity grade: same-PR at merge, not same-commit — and only if the
  regen job is a REQUIRED check.** With auto-merge on ci-gate, a race where
  the bump commit's checks go green before the regen push must be
  impossible; making the regen workflow a required status closes it.

### F6. mise-native scheduled job (extend refresh.yml with discovery)

Trivially atomic — one working tree, one PR carrying config bumps AND all
five artifacts (the incumbent already proves the regen half daily). But to
replace Renovate it must re-implement discovery for the non-mise surfaces
(deb HTML index, git-refs SHA, docker digests, GHA actions) — re-inventing
Renovate datasources, losing per-dep PRs/changelogs/vuln alerts (Angle 2's
territory). As a *companion-artifact* mechanism it is excellent; as a
*discovery* mechanism it is the weakest. Keep it in the refresh role.

### F7. Comparison matrix (same-PR completeness per artifact)

| Topology | 1 root lock | 2 shared lock | 3 system lock | 4 runtime lock | 5 devcontainer lock | Multi-file string pins | Atomicity grade |
|---|---|---|---|---|---|---|---|
| Hosted Renovate alone (post-F1) | in-commit¹ | in-commit¹ | n/a (nothing to bump) | n/a | **no — gap (c)** | YES (regex managers) | same-commit for mise surface¹; feature bumps hard-red |
| Incumbent (hosted + daily refresh.yml) | in-commit¹ + daily re-resolve | same | daily | **never (F2d gap — fix)** | daily; tag bumps still red until manual regen | YES | eventual ≤24h; MISE_VERSION deadlock (F2a) |
| Self-hosted Renovate + allowedUnsafeExecutions + postUpgradeTasks | native in-commit | native in-commit | postUpgradeTasks in-commit | postUpgradeTasks in-commit | postUpgradeTasks in-commit | YES | **same commit (strongest)** |
| mise-native scheduled job only | same PR | same PR | same PR | same PR | same PR | must hand-roll bumpers | same PR; discovery is the cost |
| Hybrid: hosted discovers + workflow pushes regen | Renovate in-commit¹; workflow fallback | same | stays with refresh.yml | stays with refresh.yml | **2nd commit — closes gap (c)** | YES | same PR at merge IF regen job required; loop hazards managed |

¹ pending live confirmation that the Mend hosted deployment has rolled past
43.210.1 (trust fix); it demonstrably executes `mise lock` (F1/#43562).

### F8. Recommendation (this angle's input to the domain verdict)

1. **Keep refresh.yml + the lock-refresh composite** — irreplaceable for
   artifacts 3–4 (pinned writer, linux-x64, provenance-strip) and the daily
   re-resolution of all-latest tiers. **Fix F2d now** (add
   `.devcontainer/mise-runtime.lock` to `open-refresh-pr` paths; update the
   "three lockfiles" header), and stop enumerating artifact paths in more
   than one place.
2. **Verify-and-adopt hosted Renovate's same-PR mise.lock updating** (F1):
   inspect the next mise-manager PR diff / job log; then update the stale
   "hosted can never run mise lock" comments (`refresh.yml:12-18`,
   `lock-refresh/action.yml:8-10`) per the tool-currency rule.
3. **Close gap (c)** with the hybrid micro-workflow (F5): `renovate/**`
   branches touching `devcontainer.json` → `devcontainer upgrade` → push
   with the existing App token; add the App author to `gitIgnoredAuthors`;
   make the job a required check. ~40 lines, reuses composite step 3.
   Optionally extend the same workflow to re-run the staged image-lock regen
   on `MISE_VERSION`-bump PRs, closing the F2a deadlock.
4. **Do not move to self-hosted Renovate for this reason alone** — its
   postUpgradeTasks would re-host the composite's own script inside
   Renovate's sandbox to solve gaps items 1–3 solve with infrastructure
   already in place. But if OTHER angles (scheduling floors, git-refs
   cadence) independently pick self-hosted, postUpgradeTasks then upgrades
   every window to same-commit — take it.
5. **Skip lockFileMaintenance** while refresh.yml exists (F3).

## Divergence note vs the earlier draft at this path

- CORRECTED: the draft claimed "the Mend-hosted app does not have `mise` in
  its allowedUnsafeExecutions". Re-probe of discussion #43562 shows the
  hosted run *executed* `mise lock` (failed during execution on the trust
  bug, not skipped) — execution implies allowance; the open question is only
  hosted deployment currency, not permission (F1, U1).
- RE-VERIFIED AND KEPT: (a) the jdx/renovate-config preset's
  `postUpgradeTasks: ["mise lock"]` + lockFileMaintenance rule (fetched raw
  default.json); (b) the F2d `mise-runtime.lock` add-paths omission
  (re-read `refresh.yml:107-111` against `lock_refresh.py:52,143-162`).

## Uncertainties / gaps

- **U1 — hosted currency**: whether Mend's hosted deployment has rolled past
  43.210.1/43.244.0 as of 2026-07-09 (it lagged at 43.209.4 on 2026-06-08).
  Resolve by inspecting this repo's next Renovate mise PR diff or the
  Developer-Portal job log for `mise trust`/`mise lock`/`allowedCommands`
  lines. Also whether Mend's undocumented approved postUpgradeTasks list
  matches the preset's `mise lock`.
- **U2 — writer-version skew on Renovate-regenerated host locks**: Renovate's
  container mise version may differ from the repo's pinned host mise; a
  format skew would surface as a red coverage/lint check on the Renovate PR
  (safe failure, but noisy). Unobserved.
- **U3 — rate limits inside Renovate's `mise lock`**: the composite needed a
  5-pass token-authenticated convergence loop; Renovate's exec environment
  may hit anonymous GitHub quota on large regens. Unobserved.
- **U4 — F2d intent**: the `mise-runtime.lock` omission reads as an
  oversight from the #160 T9 tier split (composite regenerates it; header
  still says "three lockfiles"), but a deliberate exclusion (e.g. deferring
  runtime refresh behind `minimum_release_age_excludes`) was not ruled out —
  one `git log -p` pass on refresh.yml would settle it.
- **U5 — self-hosted bootstrap**: running `uv run --project python
  dotfiles-setup lock-stage/collect` + `devcontainer upgrade` inside the
  Renovate sandbox (installTools/binarySource) was not probed end-to-end.
- Several doc pages were read through a summarizing fetcher; every
  load-bearing claim was cross-checked against a second source or raw file
  (one summarizer error — "lockFileMaintenance enabled by default" — was
  caught and corrected to disabled-by-default), but residual summarization
  error on peripheral details is possible.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — incumbent refresh.yml, lock-refresh composite, renovate.json, test_lock_coverage.py, lock_refresh.py read at file:line.
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — mise manager source (index/artifacts/lockfile.ts), devcontainer manager index.ts, docs (configuration-options, self-hosted-configuration, mend-hosted, updating-rebasing, modules/manager/mise), discussions #43562/#43882/#31920/#14659, issues #40568/#17528/#14656/#9351/#21004.
- [renovatebot/base-image](https://github.com/renovatebot/base-image) — PR #3183 added mise to the Renovate image (via discussion #43882).
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — the preset this repo extends: postUpgradeTasks `mise lock` + lockFileMaintenance automerge (raw default.json).
- [jdx/mise](https://github.com/jdx/mise) — local mintlify cache grepped first per rule (lockfile page absent from snapshot); jdx/mise#10694 provenance fail-close via repo test docstring.
- [suzuki-shunsuke/guide-github-action-renovate](https://github.com/suzuki-shunsuke/guide-github-action-renovate) — dedicated-App push-to-renovate-branch pattern + GITHUB_TOKEN CI-trigger caveat.
- [peter-evans/create-pull-request](https://github.com/peter-evans/create-pull-request) — add-paths stash semantics grounding the F2d gap (carried from the verified prior draft).
