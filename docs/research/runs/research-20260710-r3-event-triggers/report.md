# R3 — Event-driven trigger architecture (Renovate-PR-as-event)

Synthesis report, 2026-07-10. Domain: replace the Friday-cron update
cadence with an **event-triggered** topology where the controllable
"event" is a Renovate PR. Grounded against `renovate.json`,
`.github/workflows/refresh.yml`, `.github/workflows/ci.yml`,
`.github/workflows/AGENTS.md`, the three composites under
`.github/actions/`, R2 Run C (`docs/research/runs/research-20260709-r2-updater/report.md`),
and R2 inventory (`docs/research/runs/research-20260709-r2-inventory/report.md`).

Inputs: three angle reports in `agents/` (renovate-pr-trigger,
refresh-reusable, daily-safety-cron), each read in full; 10 load-bearing
claims adversarially verified with 3 votes each (8 CONFIRMED 3/3, 2
CONFIRMED 2/3 with a documented dissent — see "Refuted / unverified
claims").

---

## Executive summary — RECOMMENDATION: ADOPT the event-triggered topology; it is a small, safe, mostly-additive change

**Ship all four target-architecture pieces. Every one is mechanically
sound, and none requires `pull_request_target`, a new fork-facing attack
surface, or a new external service.** The change decomposes into four
independent, individually-shippable edits, plus one correctness bug that
must ship regardless:

1. **Drop the inherited Friday-only Renovate schedule.** `renovate.json`
   today (verified — no `schedule` key in all 108 lines) silently inherits
   `"schedule": ["* * * * 5"]` (America/Chicago, Friday-only) from
   `github>jdx/renovate-config`'s `default.json`. Add a top-level
   `"schedule": ["at any time"]` sibling to `extends`; repo-level raw
   config overrides the preset by documented precedence. This is the
   entire "make discovery event-frequent" lever on the Renovate side —
   it restores the hosted app's ~4-hourly "activated repo" job cadence.
   (CONFIRMED, with one nuance on the override sentinel — see Refuted.)

2. **A Renovate PR already IS the trigger — no new event type needed.**
   Renovate PRs in this repo are **same-repo branches, not forks**
   (verified live on 11 PRs: `head.repo == base.repo == ray-manaloto/dotfiles`,
   author `renovate[bot]`). `ci.yml`'s existing `pull_request:
   branches: [main]` trigger (`ci.yml:28-29`) already fires the full CI
   graph with full `GITHUB_TOKEN` + secrets on every Renovate PR (proven
   live on PR #191: `lint`/`contract-preflight`/`changes`/`ci-gate` all
   ran and passed). Scope the new refresh/build job with a **runtime
   `if:` conditional** (`github.actor == 'renovate[bot]'`), not a
   trigger-level branch filter (which can only see the PR's base branch,
   never `renovate/*` head). Do **not** use `pull_request_target`,
   `workflow_run`, or `check_suite` — each solves a problem this
   same-repo-bot setup does not have, and `pull_request_target` would add
   pwn-request risk for zero gain. (CONFIRMED 3/3 on all four claims.)

3. **`refresh.yml` becomes a reusable *workflow* (`workflow_call`), not a
   composite action.** The refresh job needs its own `permissions:`,
   `concurrency:`, and — decisively — direct `secrets` access to mint its
   GitHub App token; composite actions structurally cannot read `secrets`.
   Add `workflow_call:` alongside the existing `schedule:` +
   `workflow_dispatch:` (all three coexist in one `on:` block, no removal).
   Follow the repo's own precedent: `ci.yml` already calls
   `build-publish.yml` this exact way (`ci.yml:272-282`). The one real
   gotcha: the App-token secrets `REFRESH_APP_ID` / `REFRESH_APP_PRIVATE_KEY`
   do **not** cross the `workflow_call` boundary automatically (only
   `GITHUB_TOKEN` does) — the calling `ci.yml` job must pass `secrets:
   inherit` or an explicit mapping. (CONFIRMED 3/3.)

4. **Keep a DAILY (never Friday-only) safety-net cron** on `refresh.yml`'s
   own `schedule:`, untouched by adding `workflow_call:`. This is the
   backstop against Mend rollout-lag and against any Renovate-invisible
   drift. First-party measurement this run confirms 2026 GHA scheduled-queue
   drift is real and worsening for this repo (refresh.yml fires ~3h late on
   average), so pair the daily cron with free hygiene: move both crons off
   the `:00` top-of-hour worst-case minute.

**Ship-regardless correctness bug (unchanged from R2 Run C, re-confirmed
3/3):** `refresh.yml`'s `open-refresh-pr` `paths:` block (`refresh.yml:107-111`)
lists only 4 of the 5 committed lockfiles — it **omits
`.devcontainer/mise-runtime.lock`**, which the composite genuinely
regenerates every run and then silently discards. Runtime-tier tools
(claude-code, gemini-cli, codex, fnox) are never actually refreshed by the
daily job today. One-line fix.

### Recommended end-state wiring

```
renovate.json:  + "schedule": ["at any time"]           (drop Friday gate → ~4h discovery)
                + gitIgnoredAuthors: [refresh App]       (so App companion-pushes don't stop Renovate)

lock-refresh.yml (NEW reusable workflow):
    on: workflow_call { inputs: mode, target-branch; secrets: app-id, app-private-key }
    job: mint App token → checkout → setup-mise → lock-refresh composite
         → mode=open-pr  : open-refresh-pr composite  (cron path, unchanged)
         → mode=push-branch: idempotent App-token commit+push onto renovate branch

refresh.yml (thin caller):  on: schedule (daily, off :00) + workflow_dispatch
                            job: uses lock-refresh.yml (mode: open-pr) + secrets

ci.yml (new conditional job):
    renovate-companion-regen:
      if: pull_request && github.actor == 'renovate[bot]' && changes.build == 'true'
      uses: ./.github/workflows/lock-refresh.yml (mode: push-branch, target-branch: head_ref)
      secrets: { app-id, app-private-key }
    ci-gate: needs += renovate-companion-regen   (folds into the merge gate)
```

Cost: one Renovate config line, one new reusable-workflow file (extracted
from refresh.yml's existing job body), one new conditional `ci.yml` job,
one `secrets:` grant, one `ci-gate` `needs:` entry, plus the runtime-lock
one-liner. No new attack surface. No new external infrastructure.

---

## Q(a). Drop the inherited Friday-only Renovate schedule

**The Friday gate is real and currently in effect.** `renovate.json`
`extends: ["github>jdx/renovate-config"]` (`renovate.json:3-5`) and — verified
by reading all 108 lines — defines **no `schedule` key of its own**. The
preset's `default.json` (fetched live from
`raw.githubusercontent.com/jdx/renovate-config/main/default.json`, last
schedule edit 2026-04-04, unchanged as of today) contains verbatim:

```json
"schedule": ["* * * * 5"],
"timezone": "America/Chicago"
```

— cron day-of-week 5 = Friday, all other fields wildcarded. So the
Friday-only cadence propagates unmodified (CONFIRMED 3/3; observed
consequence in R2: the 2026-06-30 p2996 commit didn't get its bump PR
until ~2026-07-08).

**The fix:** add one top-level line to `renovate.json`:

```json
"schedule": ["at any time"]
```

Renovate's documented config-precedence rule
(https://docs.renovatebot.com/config-overview/, § Config precedence)
states verbatim: *"Presets referenced with an `extends` config are
resolved first and take lower precedence over regular/raw config in the
same file or config object."* So a raw `schedule` key written directly in
`renovate.json` overrides the preset's Friday value (`schedule` is not a
mergeable/array-concatenating key — it replaces). This removes the Friday
gate; the hosted app then creates/updates branches on each of its
underlying ~4-hourly "activated repo" job runs
(https://docs.renovatebot.com/mend-hosted/job-scheduling/). The `schedule`
option gates *branch creation within a run*, not backend scan frequency
(https://docs.renovatebot.com/key-concepts/scheduling/), so "at any time"
= no branch-creation restriction = discovery at the platform's own
~4-hourly floor.

**Two nuances to carry (both from the adversarial dissents, neither
fatal):**
- The "at any time = documented null-equivalent sentinel" phrasing is
  explicitly documented under `automergeSchedule`, and one verifier found
  Renovate's source lists `['at any time']` as `schedule`'s own literal
  default too — so a bare top-level key is very likely sufficient. **If it
  does not take**, the maintainer-recommended hard override is to wrap it:
  `"force": {"schedule": ["at any time"]}` (rarkins, renovate discussion
  #29129). Ship the bare key first; keep `force` as the fallback.
- "~4-hourly" is the hosted "activated" tier figure from Renovate's own
  job-scheduling docs; this repo qualifies (it automerges Renovate PRs).
  Treat it as the documented floor, not a contractual SLA.

This is a **pure Renovate-config change with zero interaction with the GHA
trigger side** — it only changes how often Renovate opens/updates PRs.

## Q(b). A Renovate PR triggers the refresh+build job

**Use the `pull_request` trigger that already fires today — add a runtime
`if:` guard, not a new event.** Four verified mechanics:

- **F1 — Renovate PRs are same-repo, not forks (CONFIRMED 3/3, verified on
  11 PRs #191/#207-216):** `head.repo.full_name == base.repo.full_name ==
  "ray-manaloto/dotfiles"`, author `renovate[bot]`. The hosted Mend app has
  `contents: write` and pushes `renovate/*` branches directly into the base
  repo. GitHub's fork-PR secret restriction (*"With the exception of
  `GITHUB_TOKEN`, secrets are not passed to the runner when a workflow is
  triggered from a forked repository"*) is **only** a fork restriction —
  same-repo-branch PRs get full secrets + a normally-scoped token. Proven
  live: PR #191's `pull_request` run executed the full `ci.yml` graph with
  no "awaiting approval" gate. **Therefore `pull_request_target` buys
  nothing here** and only adds the classic pwn-request surface (CONFIRMED
  3/3).

- **F3 — `on.pull_request.branches` filters the BASE branch, never the
  head (CONFIRMED 3/3):** there is no trigger-level way to scope to
  `renovate/*` head branches. Gate the job at runtime:
  ```yaml
  if: github.event_name == 'pull_request' && github.actor == 'renovate[bot]'
  ```
  `github.actor == 'renovate[bot]'` is the standard, documented Renovate
  discriminant (renovate discussion #13704). (Defense-in-depth for any
  future fork-accepting state: `&& github.event.pull_request.head.repo.full_name
  == github.repository` — near-free, moot for this repo today.)

- **F4 — `check_suite`/`workflow_run` are the wrong tools (CONFIRMED
  3/3):** `check_suite` is recursion-guarded against GitHub-Actions-created
  check suites (which is exactly what `ci-gate` is — a job inside the
  GHA-triggered CI workflow), so it can't react to this repo's own gate.
  `workflow_run` exists to hand secrets/write-token to an otherwise-
  *unprivileged* follow-up — a capability Renovate PRs don't need since
  plain `pull_request` already carries full privilege here. It would add a
  second full workflow dispatch (latency) and context re-derivation
  (indirection) for no benefit. (`workflow_run` is correctly used elsewhere
  — `image-analysis.yml` — precisely for the privilege-handoff case it's
  designed for.)

- **Alternative head-branch trigger (optional):** `on: push: branches:
  ['renovate/**']` is the one trigger-level way to see the head branch —
  it fires the instant Renovate pushes a branch, before a PR exists. Only
  useful if the job must react to every branch push (rebase/retry churn)
  rather than once per PR. Not recommended as the primary path; the
  `pull_request` + `if:` route is simpler and rides the already-firing
  trigger.

## Q(c). refresh.yml → callable reusable workflow embeddable in ci.yml

**It must become a reusable *workflow* (`on: workflow_call`), not a
composite action** — the domain brief's "reusable workflow / composite
action" phrasing conflates two distinct mechanisms:

- **Composite actions run inside an existing job's context** — they cannot
  declare `permissions:`, cannot be a `workflow_call`/`schedule` target,
  and **cannot read the `secrets` context** (github/docs issue #12705; this
  repo already encodes the limitation: `open-refresh-pr/action.yml` says
  *"Composites can't read `secrets`"*, and `.github/workflows/AGENTS.md`
  repeats it). That's why `refresh.yml` today mints its App token in the
  **job** (`refresh.yml:59-71`) and threads it into the composites as an
  input.
- **Reusable workflows (`workflow_call`) get repo/org secrets** via
  `secrets:` mapping or `secrets: inherit`, and carry their own
  `permissions:`/`concurrency:`. `refresh.yml`'s job needs all three
  capabilities, so it maps to a reusable workflow. The three existing
  composites (`setup-mise`, `lock-refresh`, `open-refresh-pr`) stay
  **unchanged** as the steps inside the new workflow's job — nesting
  composite steps inside a `workflow_call` job is already proven in-repo
  (`build-publish.yml` calls `setup-mise` from 5 jobs). (CONFIRMED 3/3.)

**Recommended shape (Shape A, thin-caller split):** a new
`.github/workflows/lock-refresh.yml` carries `on: workflow_call` with a
`mode` input (`open-pr` default = cron path; `push-branch` = Renovate-PR
companion regen) and `secrets: {app-id, app-private-key}`. `refresh.yml`
keeps its `schedule:` + `workflow_dispatch:` triggers and its job body
becomes a single `uses: ./.github/workflows/lock-refresh.yml` with `secrets:
inherit`. This mirrors the `ci.yml` → `build-publish.yml` caller/callee
split the repo already uses everywhere.

**The load-bearing gotcha (CONFIRMED 3/3):** `GITHUB_TOKEN` crosses
`workflow_call` automatically, but the **custom** App-token secrets
(`REFRESH_APP_ID`, `REFRESH_APP_PRIVATE_KEY`) do NOT. The calling `ci.yml`
job must add `secrets: inherit` (simplest) or an explicit mapping, or the
App-token mint silently fails. Note `ci.yml`'s existing `build-publish`
call shows no `secrets:` key — because it only needs the automatic
`GITHUB_TOKEN`; it is **not** a template for the App-token case.

**Design specifics carried from the angle report:**
- `workflow_call` input types are `string`/`boolean`/`number` only (no
  enum) — validate `mode` with `if:` string-equality, as `build-publish.yml`
  already does for `tag_strategy`.
- `env` context does NOT cross the call boundary — `refresh.yml`'s job-level
  `MISE_LOG_FILE`/`MISE_LOG_FILE_LEVEL` (`refresh.yml:54-57`) must be
  re-declared inside the reusable workflow (`build-publish.yml` already
  re-declares its own copies for this reason).
- **`ci-gate` wiring is what preserves auto-merge.** The new
  `renovate-companion-regen` job must be added to `ci-gate`'s `needs:` list
  (`ci.yml:296`) with the same `success|skipped` contract as
  `build-publish` — skipped on non-Renovate PRs (job `if:` false), required
  on Renovate PRs. Renovate's `automerge: true` + `platformAutomerge: true`
  (`renovate.json:19-24`) merges only once `ci-gate` passes, so this is
  what blocks a bad companion-regen from auto-merging.
- **`mode: push-branch` must be idempotent** — an App-token push re-fires
  `pull_request: synchronize` (App pushes DO trigger CI, unlike
  `GITHUB_TOKEN`), so the companion step must no-op on a clean
  `git diff --quiet` or it becomes an infinite push loop
  (renovate issues #17528/#14656/#9351). Use an App-token `git commit +
  push` onto `github.head_ref` — NOT `peter-evans/create-pull-request`,
  which always targets a new branch.
- **Renovate must ignore the App's own pushes** via `gitIgnoredAuthors` in
  `renovate.json`, else it stops rebasing/updating the branch (R2 Run C
  item 5).

## Q(d). Keep a DAILY (never Friday-only) safety-net cron

**Keep `refresh.yml`'s own `schedule:` trigger as a daily backstop** —
adding `workflow_call:` does not touch it. This is irreplaceable under
every topology: the lock-refresh composite is the ONLY writer that can
regenerate the image-tier locks (pinned image mise on linux-x64, 5-pass
rate-limit convergence, provenance strip) — Renovate structurally cannot
(CONFIRMED across R2). The daily cron also backstops Mend rollout-lag
windows (measured 1-2 weeks between a Renovate release and hosted
enablement).

**First-party GHA cron-drift measurement (new this run, resolves R2's
flagged gap):** using the GitHub Actions API on this repo's last 11
scheduled `refresh.yml` runs (2026-06-30 → 2026-07-10), **every fire was
2h23m-3h55m late, mean ≈3h09m**; `ci.yml`'s nightly (30-run sample) drifted
46m-4h23m with a worsening trend (+~25% in two weeks), matching community
discussion #196910 and GitHub staff's on-record acknowledgment of
worsening drift and >30%-growth in dropped scheduled jobs. Both this repo's
crons currently sit at the documented worst-case `:00` minute
(`refresh.yml:39` `0 0 * * *`, `ci.yml:10` `0 2 * * *`).

**Design (cheapest-first):**
1. **Move both crons off `:00`** — e.g. `17 0 * * *` / `43 2 * * *`.
   Zero-cost hygiene; implements GitHub's own documented mitigation.
   Reduces but does not eliminate multi-hour drift.
2. **Keep it DAILY, not Friday-only** — the whole point of the event-driven
   pivot is that discovery is now Renovate-PR-driven; the cron is the
   *safety net*, and a safety net that only fires weekly defeats the
   purpose. Daily is correct.
3. **Widen / stop over-promising the 00:00→02:00 stagger.** The raw
   cron-fire *order* has held (measured refresh→ci gap stayed 1h36m-2h28m —
   drifts are correlated), so this is **not** a data-loss risk
   (`refresh.yml` is idempotent re-resolution with a `lock-refresh`
   concurrency group, `cancel-in-progress: false`). But refresh's own ~3h
   typical delay + ~1.5-2h pipeline latency means "PR merged before the
   nightly" is no longer a reliable *guarantee*. Update
   `.github/workflows/AGENTS.md` § Cron schedules to describe the stagger
   as best-effort freshness, not a mechanism — a docs-only change that
   prevents a future engineer chasing "nightly published yesterday's pins"
   as a bug.
4. **Defer** an external minute-accurate dispatcher and a second same-day
   `cron:` hedge until re-measurement after step 1/3 ships (and until a
   real drifted-lock PR exists to time end-to-end — none were sampleable
   this run because no lock drifted on the measured days). Concrete revisit
   bar: refresh→ci fire-gap drops under ~30-60m, or a lock-refresh PR is
   observed merging after that day's nightly.

**Do NOT add drift hedging to `ci.yml`'s schedule path** — it always
rebuilds by design, so extra fires are ~1h GHCR-pushing builds, not a
safety net. Hedging belongs only on `refresh.yml` (the discovery workflow).

## Ship-regardless: the runtime-lock omission bug (CONFIRMED 3/3)

`refresh.yml`'s `open-refresh-pr` `paths:` block (`refresh.yml:107-111`,
read verbatim) lists exactly:
```
mise.lock
.config/mise/mise.lock
.devcontainer/mise-system.lock
.devcontainer/devcontainer-lock.json
```
`.devcontainer/mise-runtime.lock` is **absent** — but the composite
regenerates it every run (`lock-refresh/action.yml:56-58` runs
`MISE_ENV=runtime … lock`; `lock_refresh.py:52` `_RUNTIME_LOCK =
".devcontainer/mise-runtime.lock"`; `collect_system_lock` at
`lock_refresh.py:143-162` writes it to the working tree). Because
`open-refresh-pr/action.yml:74` passes `paths:` straight to
peter-evans/create-pull-request's `add-paths` (a strict allowlist — *"File
changes that do not match one of the paths will be stashed and restored
after the action has completed"*), the regenerated runtime lock is
discarded, never committed. Runtime-tier tools (claude-code, gemini-cli,
codex, fnox) are never actually refreshed by the daily job.

**Fix (one line + docs):** add `.devcontainer/mise-runtime.lock` to the
`paths:` block; correct the "three committed lockfiles" language at
`refresh.yml:2-11`/`refresh.yml:91-99` and the `lock_refresh.py` module
docstring to five (matching `tests/test_lock_coverage.py`'s coverage set).
General lesson: enumerated add-path lists are a fragility class — derive
them from the same source of truth the coverage tests use.

---

## Refuted / unverified claims

No claim in this run carried a **REFUTED verdict** — all 10 load-bearing
claims are CONFIRMED (8 unanimous, 2 at 2/3). The two split verdicts and
the genuine gaps below must NOT be over-asserted:

**Contested nuances (CONFIRMED 2/3, do not assert the strong form):**

1. **"`schedule`: [`at any time`]` is Renovate's documented no-restriction
   sentinel equivalent to null/unset."** — CONFIRMED 2/3; one REFUTE. The
   null-equivalence is explicitly documented only under `automergeSchedule`,
   not under `schedule` itself, and the cited discussion #29129 shows the
   maintainer recommending the wrapped `"force": {"schedule": "at any
   time"}` form for a *guaranteed* preset override. **Assert:** the bare
   top-level `"schedule": ["at any time"]` override is very likely
   sufficient (repo config beats preset by documented precedence; source
   lists it as `schedule`'s own default), but if it does not take, use the
   `force` wrapper. Do not present the bare key as a certainty.

2. **"The Friday cadence is inherited AND `schedule: [at any time]` unlocks
   ~4-hourly discovery"** — CONFIRMED 2/3; one REFUTE on two grounds worth
   preserving: (a) **present-tense accuracy** — `renovate.json` has NO
   `schedule` key today (I verified this directly), so the override is a
   *recommended, unapplied* change, not current state; state it as such.
   (b) The specific **"~4-hourly" figure** is the hosted "activated" tier
   documented floor, and the `schedule` option gates branch creation within
   a run, not raw backend scan frequency — so the precise effective cadence
   is "up to the hosted job floor," documented as ~4-hourly for activated
   repos, not a guaranteed interval.

**Genuine gaps (flagged, not asserted as fact):**

- **PR-merge-completion timing is inferred, not measured.** The cron-fire
  delays are measured first-party; the "stagger no longer reliably holds"
  conclusion combines that measured delay with R2's *estimated* ~1.5-2h
  pipeline latency. No `chore/lock-refresh` PR was sampleable this run (no
  lock drifted on the measured days). Re-measure once a real drift PR
  exists.
- **`workflow_dispatch`/`repository_dispatch` bypassing the degraded
  scheduled queue** is well-corroborated community consensus, but has **no
  first-party GitHub SLA source**. Treat as "very likely," not guaranteed.
- **The `mode: push-branch` companion step is scoped, not designed** — the
  App-token git-commit/push mechanics, the idempotency `git diff --quiet`
  guard, and the live-PR-head `ref:` checkout need an implementation pass.
- **Mend's enablement of `allowedUnsafeExecutions: ["mise"]`** (which lets
  hosted Renovate regen root `mise.lock` in-commit, empirically proven on
  PR #191) is an inference from that success, with no public Mend
  announcement.
- **Composite-inside-reusable-workflow nesting-limit accounting** — proven
  working in-repo (`build-publish.yml` → `setup-mise` ×5) but no normative
  doc sentence confirming composites are excluded from the 10-level cap.

---

## Contradictions with the domain-brief baseline / R2 conclusions

Flagged loudly, per the reporting requirement:

1. **"refresh.yml regenerates all committed lockfiles" is FALSE today**
   (also flagged by R2). The runtime lock is regenerated then silently
   discarded (`refresh.yml:107-111` omits it). The brief's item (d)
   ("keep a daily safety-net cron") is undermined for the runtime tier
   until this one-liner ships — fix it in the same change set.
2. **The brief says "three committed lockfiles" implicitly** (echoing the
   stale in-repo comments and the `.github/workflows/AGENTS.md` "four
   lockfiles" line); the real set is **five**. Both counts in the repo are
   wrong in different places.
3. **The brief's phrase "reusable workflow / composite action" (item c)
   conflates two mechanisms.** It must be a reusable *workflow* — a
   composite action cannot read the `secrets` needed for the App-token
   mint. Not a contradiction of intent, but a correction the implementer
   must not miss.
4. **No contradiction with R2's core conclusions** — R2 Run C already
   recommended the Friday-schedule override (its item 1), the runtime-lock
   fix (its item 2), and the ~40-line regen-push micro-workflow (its item
   5). This run operationalizes those into the event-triggered topology and
   adds the reusable-workflow mechanics + first-party cron-drift numbers.
   The one refinement to R2: R2's "the 2h stagger can easily invert" is
   softened by first-party data (raw fire-*order* has held; the risk is in
   the merge-completion tail, not the cron order).

---

## Open questions for Ray (with recommended answers)

1. **Adopt the full event-triggered topology (all four pieces)?** —
   Recommended: **YES.** Every piece is verified sound and mostly additive;
   the only irreversible-feeling piece (extracting `lock-refresh.yml`) is a
   mechanical refactor mirroring `build-publish.yml`.

2. **Add `"schedule": ["at any time"]` to renovate.json now?** —
   Recommended: **YES, ship first** (independent of the GHA work). If a
   subsequent Renovate run still shows Friday-gated branch creation, switch
   to the `"force": {"schedule": ["at any time"]}` wrapper.

3. **Extract `refresh.yml`'s job into `lock-refresh.yml` (Shape A) vs make
   `refresh.yml` self-callable (Shape B)?** — Recommended: **Shape A**
   (thin caller + callee), for consistency with the existing `ci.yml` →
   `build-publish.yml` split; Shape B is technically valid (community
   #39357) but harder to read.

4. **Gate the new ci.yml job on `github.actor == 'renovate[bot]'` or
   `startsWith(github.head_ref, 'renovate/')`?** — Recommended:
   **`github.actor == 'renovate[bot]'`** as the primary (spoof-resistant,
   standard); it's a same-repo bot so the actor is trustworthy. Optionally
   AND the same-repo head check for defense-in-depth.

5. **Should the companion-regen job also react to `push` on `renovate/**`
   (every branch push) or only PR open/synchronize?** — Recommended:
   **PR events only** (simpler, avoids doubling work on rebase/retry
   churn); revisit only if companion regen must run before a PR exists.

6. **Move both crons off `:00` and widen/soften the stagger docs now?** —
   Recommended: **YES** — free hygiene backed by first-party drift data.
   Defer the external dispatcher and second-cron hedge until re-measurement.

7. **Ship the runtime-lock one-liner regardless of the topology decision?**
   — Recommended: **YES, immediately** — it's a standalone correctness bug;
   the daily safety net is silently broken for the runtime tier today.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — read `renovate.json`, `.github/workflows/{refresh,ci,build-publish}.yml`, `.github/actions/{setup-mise,lock-refresh,open-refresh-pr}/action.yml`, `.github/workflows/AGENTS.md`, `python/src/dotfiles_setup/lock_refresh.py`, issue #116 at working-tree HEAD; live GitHub API on PRs #191/#207-216 (same-repo/non-fork head, actor identity, check-run success) and `actions_list` cron timestamps for first-party drift measurement.
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — live `default.json` confirming the inherited `"schedule": ["* * * * 5"]` / `"timezone": "America/Chicago"` Friday gate and its 2026-04-04 last-edit.
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — docs (`config-overview` config-precedence, `configuration-options`, `key-concepts/scheduling`, `mend-hosted/job-scheduling`, `security-and-permissions`, `mend-hosted/hosted-apps-config`, mise manager), source (`lib/config/options/index.ts` schedule default), discussions #13704 (`renovate[bot]` actor gating), #29129/#19599 (schedule override / force), #43562 (hosted mise rollout).
- [github/docs](https://github.com/github/docs) — Actions docs: events-that-trigger-workflows (`pull_request`/`pull_request_target`/`check_suite`/`workflow_run`/`schedule`), reusing-workflow-configurations (secrets crossing `workflow_call`), workflow-syntax (input types, multi-key `on:`), avoiding-duplication (reusable-vs-composite), triggering-a-workflow (App-token vs GITHUB_TOKEN recursion guard); issue #12705 (composite actions can't read `secrets`).
- [orgs/community discussions](https://github.com/orgs/community/discussions) — #196910 (scheduled-workflow drift magnitude + GitHub staff acknowledgment), #156282 (independent drift + dispatch-vs-schedule mitigation), #26795 (pull_request base-branch-only filter + head_ref workaround), #39357 (schedule+workflow_dispatch+workflow_call coexistence).
- [actions/runner](https://github.com/actions/runner) — issue #4468 (multi-hour scheduled-workflow drift corroboration).
- [peter-evans/create-pull-request](https://github.com/peter-evans/create-pull-request) — `add-paths` strict-allowlist / stash-and-restore semantics (runtime-lock omission mechanism).
