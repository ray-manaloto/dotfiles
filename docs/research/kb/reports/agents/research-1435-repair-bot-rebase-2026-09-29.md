# Research #1435 — repair-bot commits vs Renovate rebase on #1063 (2026-09-29)

Lane: read-only research (writes only this report + `.agent/kb/raw/1435-*`). Base: main `efc04995`.
Status: COMPLETE (evidence log E1-E8 below the analysis was appended incrementally; analysis appended last).

## Evidence log (appended as gathered)

### E1 — gcc-sha-repair.yml trigger + commit (main efc04995)
- Trigger: `on.push.branches: ["renovate/**"]` + `paths: [".devcontainer/Dockerfile"]` (`.github/workflows/gcc-sha-repair.yml:19-24`). NOT `pull_request`.
- Concurrency `gcc-sha-repair-${{ github.ref }}`, cancel-in-progress (`:38-40`).
- Runs `uv run --project python dotfiles-setup gcc-sha` (`:77`), and only if the Dockerfile diff is non-empty commits as
  `user.name "${APP_SLUG}[bot]"`, `user.email "${APP_SLUG}[bot]@users.noreply.github.com"` (`:88-89`, NOTE: no numeric-id prefix)
  and pushes with the App token (`:92`). Self-terminating: the App push re-fires the workflow, which finds no drift (`:13-14`).
- Observed on #1063: run 34839000850 (push of Renovate commit 0d9fe029a6) produced repair commit 3abd52d964 at 11:36:29Z;
  run 34839066940 (push of 3abd52d) = `success`, no further commit (branch has exactly 2 commits). Idempotence confirmed live.

### E2 — refresh.yml `image-lock-pr` (main efc04995)
- Trigger: `on.pull_request.branches: [main]` (`refresh.yml:44-46`, default types opened/synchronize/reopened); job `if:` =
  head.ref starts `renovate/` + same repo + `pull_request.user.login == 'renovate[bot]'` (`:273-277`). A Renovate force-push
  rebase emits `synchronize`, so this job re-runs after every rebase.
- Drift check = five `tests/test_lock_coverage.py` node IDs (`:336-342`); regen = `mise run lock-image -- --no-container` (`:351`);
  containment = diff must be only `.devcontainer/mise-system.lock` + `mise-runtime.lock` else exit 1 (`:365-393`).
- Identity: `${BOT_ID}+${APP_SLUG}[bot]@users.noreply.github.com` (`:405-406`) — DIFFERENT email from gcc-sha-repair's.
- The "deliberate" comment (`:394-403`): chose this identity so Renovate's `isBranchModified` is TRUE and
  `shouldReuseExistingBranch` refuses to rebase, i.e. the freeze is the designed survival mechanism for the regenerated locks.
- Push uses `--force-with-lease=<ref>:<BASE_SHA>`; if branch moved, clean no-op exit 0 — "a newer `synchronize` run redoes the work" (`:430-470`).

### E3 — #1063 live state (gh API, 2026-09-29)
- Head `3abd52d964`; commits: `0d9fe029a6` renovate[bot] 2026-09-14T11:35:40Z, `3abd52d964` dotfiles-refresh-bot-org[bot] 11:36:29Z.
  Only 2 commits — `image-lock-pr` NEVER committed (it failed containment).
- Renovate comment 5663353711 (11:41:54Z) "Edited/Blocked Notification ... does not recognize the last commit author".
- PR `updatedAt` 2026-09-14T11:41:54Z — nothing since (15 days frozen). Auto-merge armed.
- Group content: clang-p2996 digest, bun 1.4.0→1.4.2, chezmoi 2.72.1→2.72.2, gcc-latest 20260816→20260906, hk 1.57.0→1.58.1,
  pixi 0.78.0→0.80.0, shfmt 3.14.0→3.14.1, ubuntu digest 2260313→513c074 (x3).
- Runs on 3abd52d: CI 34839072681 `failure` (lint job 103959620997 failure → ci-gate failure; build-publish SKIPPED — never reached
  a compiler build); autofix.ci 34839072436 failure; Refresh lockfiles 34839072275 → image-lock-pr 103959553575 failure.
- image-lock-pr log: drift-check failed (`hk: config 1.58.1 vs lock 1.57.0`, bun/chezmoi/pixi/shfmt likewise); after regen
  "5 passed"; containment failed: ` M .config/mise/mise.lock` (hk `1.57.0 aqua:jdx/hk` → `1.58.1 packslip:github.com/jdx/hk`)
  and ` M mise.lock` (+blake3 checksums aws-cli, docker-cli linux-x64). 2 files, 31+/29-.
  => On Renovate's branch, `.config/mise/mise.lock` still said hk 1.57.0/aqua while shared.toml said 1.58.1: Renovate's
  own lock artifact update did NOT move hk (backend aqua→packslip mismatch), which is exactly what lint reports as
  `hk@1.58.1 is not in the lockfile`.

### E4 — Renovate source (installed `mise where npm:renovate` = 44.117.2, NOT 44.117.1 — the brief's version is one patch stale)
Path `~/.local/share/mise/installs/npm-renovate/44.117.2/node_modules/renovate/dist/`.
- `util/git/index.js:682-721` `isBranchModified`: collects `%ae` AND `%ce` of EVERY commit `origin/<base>..origin/<branch>`;
  modified iff any address is not `gitAuthorEmail`, not in `ignoredAuthors` (literal or `matchRegexOrGlobList`), and not a
  platform-ignored author. So one entry per distinct email is needed.
- `workers/repository/update/branch/index.js:204-216`: if a PR exists and `branchIsModified` → `handleModifiedPr` (the
  "Edited/Blocked" comment) and RETURN `pr-edited` unless rebase checkbox / dashboard. No version updates, no rebase — the
  PR is frozen at whatever versions it had (this is #1063 since 2026-09-14).
- `update/branch/reuse.js:11-68` `shouldReuseExistingBranch`: `behind-base-branch` path rebases only if unmodified (`:24-35`);
  conflicted + modified → "Branch is not mergeable but can't be rebased" (`:38-51`) — #1063 is `DIRTY` = this state.
- `reuse.js:75-94` `determineRebaseWhenValue` converts ONLY `auto`/`automerging`; an explicit `conflicted` is kept.
- `branch/index.js:~395-410`: when reusing a branch and `getUpdatedPackageFiles`/artifacts produce changes (a NEWER version
  of any group member), "Existing branch needs updating. Restarting processBranch() with a clean branch" → rebuilt from base
  → force-push. So even under `conflicted`, a new upstream release of any group member discards foreign commits.

### E5 — jdx/renovate-config preset (raw: `.agent/kb/raw/1435-jdx-renovate-config-default.json`, HEAD 567d5c0d 2026-09-28)
- `"rebaseWhen": "conflicted"` — ADDED by jdx/renovate-config commit 73564e17 (2026-09-23T10:55Z, "group non-major updates by
  ecosystem and stop rebase churn (#22)"). Before that the preset had no `rebaseWhen` → default `auto` → `behind-base-branch`
  (because automerge=true). This repo's `renovate.json` sets neither `rebaseWhen` nor `gitIgnoredAuthors` (grep → 0 hits;
  control: `groupName` → 5 hits).
- `"gitIgnoredAuthors": ["41898282+github-actions[bot]@users.noreply.github.com"]`.
- ⚠️ This INVALIDATES the premise of the 2026-09-01 #887 analysis (`docs/research/kb/reports/agents/2026-09-01-premises-887.md`
  M-9 + Q3), which derived the gitIgnoredAuthors livelock from `rebaseWhen=auto→behind-base-branch`. That premise was true then.
- Measured cadence (gh timeline `head_ref_force_pushed`, all by renovate[bot]): #1093 and #1092 had ~5-10 force-pushes/day
  2026-09-14→09-23 (e.g. 09-16: 11 on #1093); from 09-24 onward ~0-2/day (#1093: 09-24, 09-25, 09-26, 09-27×2; #1323: one/day
  09-24→09-29). The preset change is visible in the data.
- Main branch protection: required context `ci-gate`, `strict: false` (not up-to-date-required); ruleset 19868073 has no
  merge_queue rule. So `conflicted` stays `conflicted`.

### E6 — Does gcc-sha-repair re-fire after a Renovate force-push? (docs + live history)
- GitHub docs (`.agent/kb/raw/1435-gha-paths-diff-comparisons.md`, github/docs reusable `triggering-a-workflow-paths5`):
  "Pushes to existing branches: A two-dot diff compares the head and base SHAs directly" — i.e. `before..after` of the push.
  A rebase that drops the repair reverts the `GCC_LATEST_DEB_SHA256` line, so `.devcontainer/Dockerfile` is in the diff → fires.
  (Corollary visible in the run list: a rebase diff also includes main's own Dockerfile changes, which is why the workflow
  also fires on e.g. `renovate/mise-non-major` 2026-09-29 — harmless, it finds no drift.)
- Full run history `.agent/kb/raw/1435-gcc-sha-repair-runs.txt` (180 runs; 171 on `renovate/all`; 7 repair pushes, all
  `dotfiles-refresh-bot-org[bot]`).
- LIVE ARM (in-place rebase over a repair): PR #455 — repair commit 9da9443c (2026-08-01T01:57Z); Renovate force-pushed OVER it
  at 2026-08-05T19:29:29Z (timeline `head_ref_force_pushed`, with an "Artifact update problem" comment — a rebase/retry was
  evidently requested, since the branch was modified) → gcc-sha-repair DID fire on the new head 3c412ad1 (run 31039650245) and
  again on 024c4d95 (run 31047203711) — **trigger demonstrated**. Both runs FAILED in setup-mise (`mise install` locked-mode
  error; `sh: 1: hk: not found` postinstall), i.e. a then-current setup defect, so **completion after an in-place rebase has
  never been demonstrated**. (The current job installs only `python uv`, and its 2026-09-14 run succeeded.)
- LIVE ARM (close → recreate): #236 closed 2026-07-30T23:37:38Z → #442 created 23:39:06Z → repair ac37ba05 23:39:44Z;
  #442 closed 2026-08-01T01:54:38Z → #455 created 01:56:29Z → repair 9da9443c 01:57:09Z. Renovate recreates a closed group PR
  within ~2 minutes and the repair regenerates on the new branch — **demonstrated twice**.
- Every group PR that contained a gcc bump FROZE at its first repair: #947 (40 Renovate force-pushes 2026-09-03→09-07, then
  repair 663e0803 at 09-07T10:53:41Z, "Edited/Blocked" at 10:54:34Z, never touched again, still open "abandoned") and #1063.
- gcc-latest cadence: main pins 20260816; jwakely index latest is `gcc-latest_17.0.0-20260920git549ec717abb7.deb`; both 0816 and
  0906 dated debs still HTTP 200 on kayari. A recreated group PR will therefore carry a gcc bump → repair → freeze again under
  the status quo. Upstream publishes no checksum (jwakely page: 20 `gcc-latest` hits, 0 `sha256`/`checksum` hits; repo
  jwakely/pkg-gcc-latest has one 2023 release and a Pages-only build workflow).

### E7 — Why #1063 is red: stale-branch vs independent
- `hk@1.58.1 is not in the lockfile`: Renovate's own commit 0d9fe029 rewrote `.config/mise/mise.lock` for bun/chezmoi/pixi/shfmt
  but left `[[tools.hk]] version = "1.57.0" backend = "aqua:jdx/hk"` while shared.toml said 1.58.1 (patch hunks via
  `gh api commits/0d9fe029a6`). The runner regen resolved hk as `packslip:github.com/jdx/hk`. Today main is hk `2.3.0`
  with `backend = "packslip:github.com/jdx/hk"` in both `.config/mise/mise.lock:412-414` and `mise-system.lock:4804-4806`
  (moved by human PR #1403, `42a699c8`). => This red is a STALE-BRANCH artifact: hk 1.58.1 is no longer relevant. Whether the
  hosted Renovate's mise lock update now writes a correct packslip hk entry for the next bump (hk 2.4.0, released
  2026-09-28) is UNVERIFIED — the backend mismatch that caused it is gone on main, but no Renovate hk bump in this group
  has been observed since.
- `image-lock-pr` containment: TWO parts. (a) the `.config/mise/mise.lock` hk rewrite — stale-branch consequence of the above.
  (b) root `mise.lock` +blake3 `checksum` lines for `aws-cli` and `docker-cli` `platforms.linux-x64` — **INDEPENDENT defect,
  open as #963** ("--no-container path perturbs the root mise.lock"). Reproduced AFTER #1063 froze on a different branch:
  `renovate/major-image-build-inputs` (#1093) run 36104836201 (2026-09-25) failed containment with exactly
  ` M mise.lock` +2 lines (aws-cli 2.37.1, docker-cli 29.8.1 blake3). Main today still has no `checksum` on those two
  linux-x64 entries (`mise.lock`), so it will recur.
- => A freshly recreated group PR would NOT be green: whenever it bumps a shared.toml tool (it will: bun 1.4.0→1.4.2,
  pixi 0.78.0→0.81.0, shfmt 3.14.0→3.14.1, hk 2.3.0→2.4.0 are all pending vs main), `image-lock-pr`'s drift check fails,
  the regen perturbs root `mise.lock` (#963), containment exits 1, the image locks are never pushed, and contract-preflight's
  `test_lock_coverage` keeps ci-gate red. #963 must be fixed before closing #1063 or the recreated PR is born red.

### E8 — Renovate-native alternatives
- `postUpgradeTasks` on Mend-hosted (`.agent/kb/raw/1435-renovate-mend-hosted-faq.md`, hosted-apps-config.md:106-111):
  "Community (Free) users cannot modify nor request arbitrary commands"; OSS plan may *request* allowlisting via a
  mend-hosted-request discussion, "Acceptance is at the discretion of Mend"; paid plans can set `RENOVATE_ALLOWED_COMMANDS`.
  The needed commands (`uv run --project python dotfiles-setup gcc-sha`, `mise run lock-image`) need uv/mise + network
  downloads inside Mend's sandbox; `refresh.yml:12-13` already records "the hosted app can never run `mise lock`". The plan
  tier of this installation was NOT checked (no Mend dashboard access from this lane) — UNVERIFIED, but infeasible in practice.
- Custom datasource digest: Renovate's `custom` datasource JSON schema accepts `releases[].digest` and maps it to `newDigest`
  (`dist/modules/datasource/custom/schema.js:4-20`; readme example `"digest": "c667f7..."`), and `autoReplace` rewrites
  `currentDigest`→`newDigest` (`dist/workers/repository/update/branch/auto-replace.js:142-204`). So a regex customManager
  capturing `currentValue` (GCC_LATEST_DEB) AND `currentDigest` (GCC_LATEST_DEB_SHA256) against a JSON feed of
  `{version, digest:sha256}` would make Renovate write the sha IN ITS OWN COMMIT — no foreign commit for gcc. Cost: we must
  host that feed (a scheduled producer on main that hashes each new dated deb; TOFU trust unchanged vs today). Not prototyped:
  the two ARGs are 8 lines apart (`Dockerfile:574` / `:582`), so the matchString must span them — UNVERIFIED that autoReplace
  handles that span cleanly.
- `gitIgnoredAuthors` is `type: array`, `stage: "repository"`, `patternMatch: true`, with NO `mergeable` flag
  (`dist/config/options/index.js:1267-1273`) → a repo-level value REPLACES the preset's
  `["41898282+github-actions[bot]@users.noreply.github.com"]`; re-list it. Exact strings are matched with `includes()` first
  (`util/git/index.js:720`), so the literal `[bot]` is safe as an exact string (it would be a char class as a glob).
- Identities needing entries (bot id from `gh api /users/dotfiles-refresh-bot-org%5Bbot%5D` → 298071151):
  `dotfiles-refresh-bot-org[bot]@users.noreply.github.com` (gcc-sha-repair, author+committer on all 7 repair commits) and
  `298071151+dotfiles-refresh-bot-org[bot]@users.noreply.github.com` (image-lock-pr, `refresh.yml:405-406`).

## Analysis

### Recommendation (lead)
**B′ = scoped `gitIgnoredAuthors` (the two exact repair-bot addresses + the preset's github-actions address) AND an explicit
`"rebaseWhen": "conflicted"` in `renovate.json` — landed only AFTER #963 is fixed — then close #1063 and let Renovate recreate it;
demonstrate regeneration on the recreated PR with the Renovate "rebase/retry" checkbox.** Optionally follow with E (custom
datasource digest) to delete gcc-sha-repair's foreign commit entirely.

Why this satisfies "demonstrate repair regeneration after rebases": both producers are already rebase-reactive by trigger
(gcc-sha-repair = `push` with a two-dot `before..after` paths diff, E6; image-lock-pr = `pull_request` `synchronize`, E2), the
trigger half is already live-demonstrated (#455 2026-08-05, E6), and the checkbox gives a real, repeatable, on-demand rebase to
arm the completion half. The "deliberate freeze" rationale (`refresh.yml:394-403`) and the 2026-09-01 "do not do this" verdict
(`2026-09-01-premises-887.md` Q3) were both derived from `rebaseWhen=auto→behind-base-branch` (~5-10 force-pushes/day,
measured then and re-measured here on #1092/#1093 before 09-24). jdx/renovate-config 73564e17 (2026-09-23) changed the preset to
`conflicted`; post-change cadence is ~0-2/day (E5). The premise has moved, so the verdict must be re-derived — and pinned
locally, because it currently depends on an upstream preset we do not control.

Meanwhile the status-quo freeze is empirically fatal, not protective: #947 and #1063 both froze on their FIRST repair and never
moved again (15 and 22 days); a frozen PR gets no newer versions (`branch/index.js:204-216` returns `pr-edited`), and once main
conflicts it is `DIRTY` with no path back (`reuse.js:38-51`).

### Q1 — triggers
- gcc-sha-repair: `push` to `renovate/**` touching `.devcontainer/Dockerfile` (E1). Commits the recomputed
  `GCC_LATEST_DEB_SHA256` as `dotfiles-refresh-bot-org[bot]@users.noreply.github.com`. Re-runs after a Renovate force-push:
  YES by construction (two-dot diff includes the reverted sha line) and observed firing (#455); completion after an in-place
  rebase never yet observed green (E6).
- image-lock-pr: `pull_request` on renovate[bot] same-repo `renovate/*` PRs; regenerates the two image locks when the five
  lock-coverage tests fail, containment-checks, commits as `298071151+dotfiles-refresh-bot-org[bot]@…`, pushes with
  `--force-with-lease` (E2). Re-runs on every `synchronize`, including Renovate force-pushes.
- Latent race (both today and under B′, more often under B′): gcc-sha-repair pushes with a plain `git push` (no lease, no
  retry, `gcc-sha-repair.yml:92`). If image-lock-pr's push lands first, the gcc push is rejected non-fast-forward, the job goes
  red, and image-lock-pr's push does not touch the Dockerfile so gcc-sha-repair does not re-fire → the sha stays stale. In
  practice gcc (~50 s) beats image-lock-pr (~4 min regen), but it is unguarded. Cheap fix: fetch+rebase-retry in the gcc push
  step, or also trigger gcc-sha-repair on `pull_request: synchronize`.

### Q2 — Renovate semantics (installed 44.117.2)
- Modified = ANY commit in `base..branch` whose author OR committer email is not Renovate's, not in `gitIgnoredAuthors`
  (exact/glob/regex), not platform-ignored (E4). Unknown author → `pr-edited`: no updates, no rebase, "Edited/Blocked" comment;
  only the rebase checkbox/dashboard overrides, and it discards custom commits.
- Ignored author → branch reads unmodified; with `rebaseWhen=conflicted` Renovate reuses the branch (keeps our commits) until
  (a) the branch conflicts with main, (b) any group member gets a newer version ("Restarting processBranch() with a clean
  branch"), or (c) config fingerprint changes. Each of those force-pushes a fresh branch from main — our commits are dropped —
  and each triggers both producers again. So YES, Renovate overwrites the repair on rebase; the design question is only
  whether regeneration follows, which the triggers guarantee to attempt.
- Effective `rebaseWhen`: preset `conflicted` (explicit, not converted by `determineRebaseWhenValue`); repo sets none; branch
  protection `strict:false`, no merge queue (E5).
- `postUpgradeTasks`: infeasible on Mend-hosted for these commands (E8). Native "fixup inside Renovate's commit" exists only
  for the gcc sha, via a custom-datasource `digest` (E8); there is no native path for the image locks.

### Q3 — #1063 reds
- hk@1.58.1 lockfile: stale-branch consequence (main is hk 2.3.0/packslip; E7). Next-bump behaviour UNVERIFIED.
- Lock containment: half stale-branch (hk entry), half INDEPENDENT (#963 root `mise.lock` blake3 perturbation, reproduced on
  #1093 on 2026-09-25). A recreated PR will be red on image-lock-pr → contract-preflight until #963 is fixed.

### Q4 — options

| Option | PRO | CON | Satisfies "demonstrate regeneration after rebase"? |
|---|---|---|---|
| **A** Close #1063 now; Renovate recreates; accept refreeze | Zero config change; recreate path demonstrated twice (#236→#442→#455, ~2 min) | Refreezes on the first repair almost surely (gcc 20260816→20260920 pending, E6); born red on #963 → frozen AND red = the #1063 state again within minutes | No — never exercises a rebase |
| **B′ (recommended)** exact `gitIgnoredAuthors` for both bot addresses + re-listed github-actions address; pin `rebaseWhen: "conflicted"`; land after #963; then close #1063 | Native Renovate option; removes the freeze for BOTH producers (image-lock-pr's commit freezes too); rebases now ~0-2/day, below a ~2.5h cold build; both producers already rebase-reactive; checkbox gives a real on-demand arm | Every rebase costs a fresh CI (cold-base) run; livelock returns if anyone restores `behind-base-branch` (hence the explicit pin); `conflicted`+automerge doc caveat (untested combos) — already true today with `strict:false`; gcc push race (Q1) becomes more frequent | YES — arm: tick rebase/retry on the recreated PR → expect renovate[bot] `head_ref_force_pushed`, then a gcc-sha-repair repair commit and an image-lock-pr regen commit on the new head, CI re-run, and NO "Edited/Blocked" comment on Renovate's next run. Control: the same checkbox before B′ ends in "Edited/Blocked" (observed on #455/#947/#1063) |
| **B** (brief's form) gitIgnoredAuthors scoped to the repair bot + repair re-runs on synchronize | Same as B′ | If only ONE address is listed, image-lock-pr's `298071151+…` commits still freeze the PR; if the preset array is not re-listed, github-actions commits start freezing; without the `rebaseWhen` pin the fix silently depends on jdx's preset | Yes, if both addresses are listed |
| **C** Move SHA repair into Renovate via `postUpgradeTasks` | Would remove the foreign commit entirely | Not available: Free plan cannot; OSS plan only by Mend-discretion request; commands need uv/mise + network; image locks equally blocked (`refresh.yml:12-13`) | N/A (not implementable) |
| **D** Split gcc-latest out of the group | Only the gcc PR gets gcc repair commits; group PR stops freezing on gcc | Group PR still freezes on image-lock-pr's commit whenever it bumps shared.toml (the default shape); gcc-only PR still freezes forever under status quo; adds a separate cold base build per gcc bump (contradicts the group rule's cost rationale (a)) | No |
| **E** Custom-datasource digest: host a `{version, digest}` JSON (scheduled producer on main hashes each new dated .deb), regex manager captures `currentValue`+`currentDigest` | Renovate writes version+sha in ITS commit; deletes gcc-sha-repair's branch push and its push race; no foreign author for gcc at all | New producer + hosting (data branch/Pages/release asset); matchString must span `Dockerfile:574`→`:582` (unprototyped); does NOT address image-lock-pr's commit, so B′ is still needed | Makes the question moot for gcc; image locks still need B′ |
| **E2** Use the rebase/retry checkbox on #1063 instead of closing | Keeps the PR number/history; is itself the regeneration arm today | Without B′ the PR refreezes immediately after the repair; still red on #963 | Demonstrates regeneration once, but the result freezes again |

### Suggested order (keeps the plan's "settle ownership, THEN close #1063")
1. Fix #963 (image-lock-pr `--no-container` perturbs root `mise.lock`) — otherwise every recreated group PR is born red.
2. Land B′ (renovate.json: `gitIgnoredAuthors` = three exact addresses; `rebaseWhen: "conflicted"`), updating the now-wrong
   rationale comments at `refresh.yml:394-403` and `:252-268` in the same change; optionally harden gcc-sha-repair's push (Q1 race).
3. Close #1063 (and the abandoned #947) → Renovate recreates the group PR (~2 min, E6).
4. Run the arm: after the first repair+regen commits land, tick rebase/retry; require force-push → both regenerations → CI
   re-run → no "Edited/Blocked" comment. Record run IDs as the #1435 receipt.
5. Later, if wanted: E to retire gcc-sha-repair's branch push.

### Unverified / not answered
- Mend plan tier of this installation (C feasibility rests on docs + prior repo note, not on the account).
- Whether hosted Renovate's mise artifact update writes a correct `packslip` hk entry for hk 2.3.0→2.4.0.
- Completion (green) of gcc-sha-repair after an in-place rebase — only the trigger has been observed (#455 runs failed in setup).
- E's multi-line regex autoReplace behaviour.
- Why Renovate force-pushed #455 at 2026-08-05T19:29 despite the modified branch (consistent with a checkbox rebase; body-edit
  events are not in the timeline API output I read).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — #1435, #1063, #947, #455, #442, #236, #1092, #1093, #1323, #1221, #963, #1305, #1440; workflow runs/logs of gcc-sha-repair and refresh.yml; rulesets and branch protection.
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — `default.json` (rebaseWhen, gitIgnoredAuthors) and commit 73564e17 that added `rebaseWhen: conflicted`.
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — docs `configuration-options.md`, `mend-hosted/hosted-apps-config.md`, `mend-hosted/faq.md`, `lib/modules/datasource/custom/readme.md`; source read from installed npm 44.117.2 dist.
- [github/docs](https://github.com/github/docs) — workflow-syntax paths filter "Git diff comparisons" reusable.
- [jwakely/pkg-gcc-latest](https://github.com/jwakely/pkg-gcc-latest) — checked for upstream checksums (none), releases, build workflow.
- [jdx/hk](https://github.com/jdx/hk), [oven-sh/bun](https://github.com/oven-sh/bun), [prefix-dev/pixi](https://github.com/prefix-dev/pixi), [mvdan/sh](https://github.com/mvdan/sh) — latest release tags to size a recreated group PR.
