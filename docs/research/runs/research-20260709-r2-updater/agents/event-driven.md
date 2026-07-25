# Run C / Angle 3 — Sub-daily and event-driven discovery mechanics

Agent report, 2026-07-09. Scope: mechanics + reliability of sub-daily discovery on
GitHub Actions (cron floor/drift/drops), external triggering
(`repository_dispatch`/`workflow_dispatch`), Atom feeds, release-watch services,
what cadence is meaningful given a ~1h image build, anti-patterns, and
dedup/idempotency patterns. Baseline grounding:
`docs/research/runs/research-20260709-r2-inventory/report.md`.

## Findings

### 1. GHA `schedule` cron: 5-min nominal floor, but 2026 punctuality is bad and worsening

- Documented floor: "The shortest interval you can run scheduled workflows is once
  every 5 minutes." The same docs page warns "The `schedule` event can be delayed
  during periods of high loads … In periods of sufficiently high load, some queued
  jobs may be dropped," names "the start of every hour" as a high-load window,
  requires the workflow to live on the default branch, and auto-disables scheduled
  workflows in public repos after 60 days of no repository activity.
  Source: <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows>
  (§ schedule). (The 60-day disable is a non-issue here: refresh.yml itself generates
  daily activity.)
- Real-world 2025–2026 drift is far worse than "minutes". Community discussion
  [#196910](https://github.com/orgs/community/discussions/196910) (data May 2025 →
  June 2026): average delay ~1h40m in mid-2025, **>4h by May 2026**; a 15-min
  schedule effectively ran every ~90 min for another user. A GitHub staff member
  (nebuk89) confirmed "scheduled drops have grown >30% in 2ish months" due to
  platform load-balancing, with **no near-term fix**. Mirrored at
  [actions/runner#4468](https://github.com/actions/runner/issues/4468) and
  [discussion #156282](https://github.com/orgs/community/discussions/156282).
- Independent measurement (crontap.com blog, 2025–26,
  <https://crontap.com/blog/github-actions-cron-drift-problem>): ~1 in 10 top-of-hour
  runs 5+ min late, ~1 in 50 runs 15+ min late, worst Mondays ~14:00 UTC; community
  consensus "5-minute drift routine, 15-minute common around top-of-hour, 30+ on busy
  days". Measurement tooling exists
  ([lowlydba/cron-drift](https://github.com/lowlydba/cron-drift)).
- **Direct consequence for this repo**: the deliberate 2h stagger between
  `refresh.yml` 00:00 and `ci.yml` nightly 02:00 America/Chicago (issue #116;
  `.github/workflows/AGENTS.md` § Cron schedules; `refresh.yml:38-40`,
  `ci.yml:3-11`) assumes ≤2h total for refresh cron fire + lock PR + ci-gate +
  automerge. At 2026 drift levels (hours), the 00:00 refresh can fire *after* the
  02:00 nightly, silently inverting the "nightly publishes today's pins" invariant.
  Drift is not just a sub-daily concern — it already threatens the daily topology.
- The `timezone:` sibling key both workflows use shipped in GitHub's **late-March
  2026** Actions update (IANA zones, DST-aware skipped-hour advance):
  <https://github.blog/changelog/2026-03-19-github-actions-late-march-2026-updates/>,
  roadmap [github/roadmap#1187](https://github.com/github/roadmap/issues/1187).
  Repo usage at `refresh.yml:39-40` and `ci.yml:10-11` is current best practice.

### 2. Punctual sub-daily triggering = external scheduler → dispatch API (bypasses the scheduled queue)

- `repository_dispatch`: POST `/repos/{owner}/{repo}/dispatches`; requires
  `event_type` (≤100 chars); `client_payload` ≤10 top-level properties and <64KB
  total; 204 on success; classic PAT needs `repo` scope (fine-grained: Contents
  write; an App installation token also works). Workflow must exist on the default
  branch. Sources:
  <https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event>,
  events docs above. GHA-to-GHA helper:
  [peter-evans/repository-dispatch](https://github.com/peter-evans/repository-dispatch).
- `workflow_dispatch`: same external-API triggerability (`gh workflow run` /
  REST), ≤25 inputs / 65,535-char payload, default-branch file requirement (same
  docs page). This is the shape `refresh.yml` already exposes (`refresh.yml:41`).
- Dispatch-triggered runs enter the normal event queue, not the degraded scheduled
  queue — the workaround GitHub's own community threads converge on is "external
  cron service (e.g. cron-job.org) calling `workflow_dispatch`"
  ([#196910](https://github.com/orgs/community/discussions/196910), crontap blog).
  Minute-accurate external schedulers (cron-job.org, Crontap, Cloudflare Workers
  cron, a Routine on any always-on box) + one `gh workflow run refresh.yml` API
  call restore punctuality with zero workflow rewrites, at the cost of one
  fine-grained PAT/App credential held outside GitHub.

### 3. True push-style events from third-party upstreams do not exist — "event-driven" means a watcher converting detection into a dispatch

- Webhooks are configured by a repo's admins; you cannot subscribe your workflow to
  push events on `bloomberg/clang-p2996` or jwakely's pages repo. GitHub's docs
  are explicit that no webhook initiates `repository_dispatch` — an authenticated
  API call must (events docs above; community discussion
  [#26384](https://github.com/orgs/community/discussions/26384)). So every
  "event-driven" topology for these upstreams is really *someone else's poller* +
  a dispatch into this repo.
- Cheap polling primitives (both verified live):
  - **Atom feeds, no auth, no API quota**: `releases.atom`, `tags.atom`, and —
    key for this repo — per-branch `commits/<branch>.atom`. Verified:
    <https://github.com/bloomberg/clang-p2996/commits/p2996.atom> returns the
    branch-HEAD history. Feed-URL surface:
    <https://www.locked.de/how-to-get-rss-feeds-for-releases-tags-on-github/>.
  - **REST conditional requests are quota-free when unchanged**: "Making a
    conditional request does not count against your primary rate limit if a `304`
    response is returned and the request was made while correctly authorized"
    (<https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api>).
    An ETag poll of `GET /repos/bloomberg/clang-p2996/commits/p2996` every 15 min
    is effectively free; same pattern works for the jwakely index page via plain
    HTTP `If-None-Match`/`If-Modified-Since`.
- **Third-party watch services cover the wrong surface for this repo's hard
  targets.** newreleases.io watches GitHub *releases/tags* (plus GitLab, PyPI, npm,
  Docker Hub, …), claims notification "no longer than 30 mins after the new version
  is released" (third-party summary; exact SLA not on the homepage), and offers
  custom webhooks + an API/CLI (<https://newreleases.io/>,
  [newreleasesio/client-go](https://github.com/newreleasesio/client-go)). But the
  two upstreams Ray most wants sub-daily — clang-p2996 **branch HEAD** (no releases,
  no per-bump tags) and the gcc-latest **rolling dated .deb on a plain HTML index**
  — are not release-shaped, so newreleases.io/Anitya-class services cannot watch
  them. They only duplicate the surface Renovate/mise/Dependabot already handle.
  A newreleases.io custom webhook could in principle POST the GitHub dispatches
  API for release-shaped deps, but that puts a repo-write-capable token in a third
  party's hands for marginal gain.

### 4. Upstream signal rates make sub-daily discovery nearly valueless for freshness — its real value is punctuality insurance

- **clang-p2996 `p2996` branch cadence** (from the live atom feed, fetched
  2026-07-09): 20 most recent commits span 2026-01-13 → 2026-06-30 ≈ 168 days →
  mean interarrival ≈ **8–9 days**, arriving in clusters (e.g. 4 commits
  2026-06-12→06-30, then quiet). ~0.12 events/day.
- **gcc-latest deb**: current artifact `gcc-latest_17.0.0-20260705git….deb`
  (fetched 2026-07-09); the page itself warns builds "might not get updated" —
  irregular, empirically ~weekly (GCC snapshot rhythm). Source:
  <https://jwakely.github.io/pkg-gcc-latest/>.
- Arithmetic: with a ~1h image build (+ smoke + ci-gate + automerge ≈ 1.5–2h
  pipeline latency) and events every ~7–9 days, cutting detection latency from
  24h to 1h improves *mean* pin freshness by ~23h on ~0.1–0.25 events/day ≈ a few
  hours/week of staleness removed — invisible to a human who reviews automerged
  PRs at most daily. Detection cadences finer than the pipeline latency (~2h)
  cannot compound: two detections inside one in-flight build/merge cycle collapse
  into one effective update anyway (refresh PR branch `chore/lock-refresh` is a
  singleton, `refresh.yml:106`; concurrency group `lock-refresh`,
  cancel-in-progress:false, `refresh.yml:51-53`).
- **What sub-daily actually buys**: bounded worst-case staleness when the daily
  cron drifts hours or drops entirely (finding 1) — i.e., *reliability of the
  daily contract*, not meaningfully fresher pins. A 3–6h cadence from a punctual
  external trigger dominates a 5-min GHA cron on every axis that matters here.

### 5. Anti-patterns

- **Top-of-hour / midnight-UTC cron storms**: both docs and measurements say :00
  schedules queue worst (docs § schedule; crontap data). Both repo crons sit at
  :00 (00:00 and 02:00 America/Chicago = 05:00/06:00 or 06:00/07:00 UTC). Cheap
  hygiene regardless of topology: move to odd minutes (e.g. `17 0 * * *` /
  `23 2 * * *`).
- **Wiring high-frequency triggers into an always-build path**: `ci.yml` treats
  `schedule`/`workflow_dispatch` as *always build* by design (`ci.yml:198-200`,
  `:245`, "nightly full rebuild is intentional; do NOT gate it"). A sub-daily
  trigger pointed at ci.yml would burn a ~1h GHCR-pushing build per fire and churn
  `:dev` digests (invalidating local `verify-container-latest` state) with no new
  pins. Sub-daily triggers must target the *discovery* workflow (refresh.yml
  shape), never the publish workflow.
- **Hand-rolled poll loops / sleep-watching** — already banned in-repo for agents
  (`.claude/rules/gh-cli-watch.md`); the same logic applies to workflow design:
  prefer a dispatch that fires when there is something to do.
- **Third party holding write-capable tokens** for dispatch (newreleases.io custom
  webhook → dispatches API): works, but the blast radius of a leaked fine-grained
  PAT with Contents:write exceeds the value given finding 4.
- **Dropped-run denial**: GitHub documents that queued scheduled jobs "may be
  dropped" — a topology whose correctness depends on *every* cron firing (e.g. the
  00:00→02:00 stagger) needs either an external punctual trigger or an idempotent
  catch-up property (refresh.yml has the latter: the next successful run
  re-resolves everything; nothing is lost, only delayed).

### 6. Dedup / idempotency: the incumbent design already has the right skeleton — reuse it for any frequency increase

The "skip build when resolved pins unchanged" property is already implemented at
four layers, which means *trigger frequency and build count are decoupled*:

1. **No-drift → no PR**: `open-refresh-pr` outputs are "empty when no change"
   (`.github/actions/open-refresh-pr/action.yml:52-55,81`) — a refresh fire that
   resolves identical lockfiles produces zero PRs, zero builds. This makes
   arbitrarily frequent refresh fires build-idempotent.
2. **Path gate**: `changes` job via dorny/paths-filter drops non-image and
   markdown-only diffs before the build chain (`ci.yml:204-274`).
3. **Three-tier content-hash probe**: `:base-`/`:p2996-`/`:dev-<hash16>` manifest
   probes skip rebuild/smoke on identical build inputs
   (`.github/workflows/AGENTS.md` § Pipeline stages / invariants).
4. **Concurrency**: ci.yml cancels superseded per-branch runs, main exempt
   (`ci.yml:47-49`); refresh serializes on group `lock-refresh` without
   cancellation (`refresh.yml:51-53`) so overlapping fires queue instead of
   racing the singleton PR branch.

The only always-build hole is deliberate (nightly, layer-freshness). Any new
trigger plumbing should enter through layer 1 (refresh-shaped) and inherit 2–4
for free. A clang-p2996/gcc-deb watcher should additionally carry its own
"detected ref == pinned ref → exit 0" pre-check before invoking lock-refresh, so
a 15-min ETag poll costs seconds, not runner-hours.

### 7. Bottom line for the domain recommendation (this angle's input)

- Sub-daily *freshness* is not worth buying: upstream event rates (~weekly) and
  pipeline latency (~1.5–2h) cap the benefit at noise level.
- Sub-daily/event-driven *mechanics* ARE worth adopting for **punctuality
  insurance**: 2026 GHA cron drift (hours, worsening, staff-acknowledged) already
  endangers the daily 00:00→02:00 stagger. The cheapest robust fix is an external
  minute-accurate scheduler firing `workflow_dispatch` on refresh.yml (trigger
  already exists) — optionally 2–4×/day — while keeping the GHA crons as
  fallback. All dedup layers needed to make extra fires free already exist in the
  incumbent design.
- For clang-p2996 HEAD and the gcc deb specifically: quota-free polling (branch
  atom feed / ETag REST / HTTP conditional GET on the jwakely index) inside the
  refresh-shaped workflow beats any third-party watcher, since those upstreams
  are not release-shaped and watch services cannot see them.

## Uncertainties / gaps

- The ">4h drift" figures are from one well-instrumented reporter plus staff
  acknowledgment; drift varies by time-of-day and possibly repo/plan. This repo's
  own historical delta (cron `created_at` vs scheduled time on past refresh.yml
  runs) should be measured before treating 4h as the local number. (Bash was
  unavailable in this session; `gh run list --workflow refresh.yml --json
  createdAt` would settle it in minutes.)
- newreleases.io's "≤30 min" detection claim comes from third-party directory
  copy, not a first-party SLA page; unverified. Immaterial given finding 3 (it
  cannot watch the hard targets anyway).
- gcc-latest deb cadence is inferred (dated 20260705 artifact + GCC weekly
  snapshot convention); the page publishes no schedule and disclaims continuity.
- Whether dispatch-queued runs are fully immune to the load-shedding affecting
  the scheduled queue is asserted by community workarounds and consistent with
  the docs (the delay language is specific to `schedule`), but GitHub publishes
  no formal queue-class SLA.
- Renovate hosted-app job-frequency floors and git-refs bump cadence are angle
  1's remit; not re-verified here.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — baseline: refresh.yml, ci.yml, open-refresh-pr composite, workflows AGENTS.md (file:line cites).
- [bloomberg/clang-p2996](https://github.com/bloomberg/clang-p2996) — fetched `commits/p2996.atom` live to measure branch commit cadence.
- [community/community](https://github.com/orgs/community/discussions) — discussions #196910, #156282, #26384 (cron drift evidence, external-webhook limits).
- [actions/runner](https://github.com/actions/runner) — issue #4468 (drift mirror).
- [lowlydba/cron-drift](https://github.com/lowlydba/cron-drift) — drift-measurement tooling (search-level, README summary only).
- [peter-evans/repository-dispatch](https://github.com/peter-evans/repository-dispatch) — canonical GHA-to-GHA dispatch action.
- [newreleasesio/client-go](https://github.com/newreleasesio/client-go) — newreleases.io API client (automation-surface existence check).
- [github/roadmap](https://github.com/github/roadmap) — issue #1187 (cron timezone feature shipped Mar 2026).
