# Run C / Angle #4 — Tracking upstream branch HEADs and rolling artifacts

Agent: git-pins (research analyst). Date: 2026-07-09. Scope: best mechanism to
track (a) `bloomberg/clang-p2996` `p2996` branch HEAD (moving 40-char SHA pin,
today a Renovate git-refs custom manager) and (b) the jwakely gcc-latest
rolling `.deb` (today a Renovate custom HTML datasource), at daily-or-better
cadence, feeding image builds. Compares Renovate polling, a scheduled GHA
`git ls-remote` + PR job, upstream webhooks, and GitHub Atom commit feeds.

Sibling reports consulted (same research dir): `renovate-capabilities.md`
(hosted-app cadence facts F2/F3/F6), `mise-native.md`.

## Findings

### F1. Upstream cadence reality: both pins move weekly-or-slower — daily discovery already saturates the value curve

- **clang-p2996 `p2996` branch**: the unauthenticated Atom commit feed
  (`https://github.com/bloomberg/clang-p2996/commits/p2996.atom`, fetched
  2026-07-09) shows the last three commits at **2026-06-30** (`7220baf`),
  **2026-06-16** (`a56e703`), **2026-06-16** (`7f0f89c`) — roughly **2-4
  commits/month**, in bursts. Current HEAD `7220baf` is exactly what the tree
  pins (`.devcontainer/Dockerfile:233`), i.e. the pin is current today.
- **gcc-latest deb**: the jwakely index
  (`https://jwakely.github.io/pkg-gcc-latest/`, fetched 2026-07-09) lists one
  dated deb, `gcc-latest_17.0.0-20260705git88752b86ff1a.deb`, plus a rolling
  redirect (`kayari.org/gcc-latest/gcc-latest.deb`). The gh-pages publication
  feed (`https://github.com/jwakely/pkg-gcc-latest/commits/gh-pages.atom`)
  shows automated "Regenerate index.html for `<ver>`" commits at **~7-day
  intervals** (20260705→published 2026-07-06 10:34Z, 20260621→2026-06-22,
  20260614, 20260607, 20260531) — GCC weekly snapshots, published ~1 day
  after the snapshot date. The weekly cadence is upstream-anchored:
  gcc.gnu.org states snapshots are made "about once a week"
  (<https://gcc.gnu.org/snapshots.html>, fetched 2026-07-09), so the deb
  cannot structurally move faster than that.
- Consequence: with a **daily** poll, worst-case discovery staleness is 24h on
  inputs that move every 7-30 days; mean added latency ≈ 12h. Sub-daily
  polling shaves at most those hours off a pipeline whose build takes ~1h and
  whose deb path is human-gated anyway (F5). Sub-daily buys essentially
  nothing here.

### F2. Upstream webhooks are structurally unavailable — every mechanism is polling

- GitHub docs: "You must be a repository owner or have admin access in the
  repository to create webhooks in that repository"
  (<https://docs.github.com/en/webhooks/using-webhooks/creating-webhooks>).
  We control neither `bloomberg/clang-p2996` nor `jwakely/pkg-gcc-latest`, so
  no push/commit webhook can originate upstream. `repository_dispatch` into
  our repo requires a sender with write access to *our* repo — upstream will
  never send it; it is only glue for a poller we would run ourselves, adding
  a hop without removing the poll
  (<https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows>).
- Release-watching services (e.g. newreleases.io) are modeled on
  releases/tags/registry versions (<https://newreleases.io/>); a tagless
  branch HEAD and a rolling deb on a GitHub Pages index do not fit that
  model, and adopting one would add a third-party dependency plus webhook
  glue for zero cadence gain over an in-repo daily poll. Dismissed.
- So the design space collapses to: **who polls, how often, and how good is
  the resulting PR** (companion-artifact regeneration, automerge, CI wiring).

### F3. Incumbent Renovate git-refs manager: works, but cadence is job-frequency × schedule gate; observed 8-day latency under the Friday-only preset

- The manager (`renovate.json:54-65`: `git-refs` datasource,
  `currentValueTemplate: "p2996"`, digest match in `docker-bake.hcl` +
  Dockerfile) works empirically: PR #188 "update bloomberg/clang-p2996 digest
  to 7220baf" was created and automerged 2026-07-08 (sibling report F6,
  <https://github.com/ray-manaloto/dotfiles/pull/188>).
- Latency data point: the commit landed upstream **2026-06-30** (F1 feed);
  the bump PR appeared **2026-07-08** — **8 days**. Root cause is not the
  datasource but the schedule: PR #189's body (fetched via GitHub API
  2026-07-09) states "Branch creation — Only on Friday (`* * * * 5`)" — the
  `github>jdx/renovate-config` preset's gate. The git-refs datasource itself
  has no release timestamps and default-15-min soft package-cache TTL
  (<https://docs.renovatebot.com/modules/datasource/git-refs/>,
  <https://docs.mend.io/wsk/renovate-soft-and-hard-package-cache-behavior>,
  `cacheTtlOverride` in
  <https://docs.renovatebot.com/self-hosted-configuration/>) — cache freshness
  is never the bottleneck; hosted job frequency (~4h hot ceiling, sibling F3)
  and the repo `schedule` window are.
- Fix is config-only: a `packageRules` schedule override for the two custom
  datasources (`"schedule": ["at any time"]` or daily) drops worst-case
  latency from ~7 days to the hosted job cadence (≤ ~24h guaranteed, ~4h
  typical when hot). Renovate has no event-driven trigger from upstream
  (sibling F6) — its ceiling is polling cadence, same as everything else (F2).
- Hosted cadence, pinned to the current Mend doc
  (<https://docs.renovatebot.com/mend-hosted/job-scheduling/>, fetched
  2026-07-09): repos with Renovate Status **activated are scheduled
  4-hourly**; inactive (onboarded/silent/failed) daily; blocked weekly;
  Enterprise runs hourly on GitHub. This repo automerges Renovate PRs
  regularly, so it should sit in the 4-hourly "activated" tier — i.e. after
  a schedule override, discovery is ~4h worst-case, well inside
  daily-or-better. The doc lists no user-facing override to run *more*
  often on the Community cloud.
- **On-demand escape hatch (no cron job needed)**: the Dependency Dashboard
  issue carries a "Check this box to trigger a request for Renovate to run
  again on this repository" checkbox, supported on the hosted GitHub app
  (<https://docs.renovatebot.com/key-concepts/dashboard/>;
  renovatebot/renovate#7035; hosted runs provision in ≤ ~10 min). Ticking it
  is an issue-body edit, which automation can perform via the GitHub API —
  so a trivial poller that detects an upstream change and ticks the box
  turns hosted Renovate near-on-demand while keeping it the sole PR author.
  Caveat: the checkbox was once removed and later restored
  (renovatebot/renovate discussion #20386) — any automation against it must
  fail soft to the scheduled run.

### F4. The scheduled `git ls-remote` + PR job is already fully built in this repo — the retired incumbent, resurrectable at near-zero cost

- `python/src/dotfiles_setup/p2996_refresh.py` (docstring lines 1-20;
  `fetch_latest_ref` at :98-121 runs
  `git ls-remote <repo> refs/heads/p2996`) rewrites `CLANG_P2996_REF` in
  `docker-bake.hcl` only on change; tests exist
  (`tests/test_p2996_refresh.py`); the mise task survives
  (`mise.toml:675-677` `[tasks.p2996-refresh]`). The workflow job was retired
  2026-07-07 "in favor of the Renovate git-refs manager"
  (`.github/workflows/refresh.yml:20-23`); re-adding it is one job in
  `refresh.yml` reusing the existing `open-refresh-pr` composite (App token →
  PR fires CI → auto-merge on ci-gate, the proven `lock-refresh` pattern,
  `refresh.yml:59-114`).
- Poll cost is negligible at any cadence: `git ls-remote` rides the git
  smart-HTTP endpoint (no REST rate-limit consumption), and if the REST API
  is used instead, an ETag-conditional `GET /repos/.../commits?sha=p2996`
  returning 304 "does not count against your primary rate limit" when
  authorized
  (<https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api>).
  The deb side polls even cheaper: the index states the unversioned
  `gcc-latest.deb` URL "will redirect to the latest .deb file", so a HEAD
  request's `Location` header reveals the current dated filename without a
  download.
- Cadence control is total: its own cron can be daily or hourly. GHA cron
  reliability bounds it: 5-min nominal floor ("The shortest interval you can
  run scheduled workflows is once every 5 minutes"), "can be delayed during periods
  of high loads… High load times include the start of every hour"
  (<https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows>);
  community measurements show minutes of routine drift, 30+ min on busy days,
  and pathological multi-hour drift episodes
  (<https://github.com/orgs/community/discussions/156282>,
  <https://github.com/orgs/community/discussions/196910>,
  <https://github.com/actions/runner/issues/2977>,
  <https://github.com/lowlydba/cron-drift>). Drift is irrelevant at daily
  granularity, disqualifying only for sub-hourly SLOs (which F1 shows are
  pointless here). Note the 60-day public-repo inactivity auto-disable for
  scheduled workflows (same docs page) — moot while refresh.yml merges PRs
  daily.
- Decisive structural advantage over hosted Renovate: the job runs arbitrary
  repo code, so it can regenerate **every companion artifact in the same
  PR** — the three mise lockfiles via the existing `lock-refresh` composite,
  and (if policy allows, F5) the deb sha256. Hosted Renovate cannot run
  `mise lock` or `sha256sum` (refresh.yml:12-14; sibling F1/U2 on hosted
  postUpgradeTasks/allowlisting).

### F5. The deb's binding constraint is not discovery — it's the deliberate human sha256 gate; PR #189 is empirically stuck on it

- Upstream publishes **no checksum or signature** ("all 404"), so the repo
  computes its own: `ARG GCC_LATEST_DEB_SHA256=…` is "Deliberately NOT
  Renovate-managed: a GCC_LATEST_DEB bump fails this check until a human
  recomputes the hash … supply-chain friction by design"
  (`.devcontainer/Dockerfile:336-347`).
- Empirical proof: Renovate PR #189 (created 2026-07-08 15:17Z, 1 file,
  +1/-1 — bumps only the ARG to 20260705) is **open,
  `mergeable_state: "blocked"`** as of 2026-07-09 — CI fails the
  `sha256sum -c` until a human pushes the recomputed hash
  (<https://github.com/ray-manaloto/dotfiles/pull/189>, GitHub API).
- Therefore NO discovery mechanism shortens deb end-to-end latency today;
  weekly upstream + human-in-loop dwarfs any polling improvement. The only
  lever is a **policy decision**: let a trusted CI job `curl + sha256sum` the
  dated deb and commit hash+ARG in the same PR. Security delta is small —
  the human recomputing the hash downloads from the same kayari.org over TLS
  with no independent verification channel (TOFU either way); the dated
  filename remains the immutability handle. But it *is* a documented posture
  change (#160 T13) — surface to Ray, do not silently automate. If approved,
  only the in-repo GHA job can do it (hosted Renovate can't run commands);
  it slots naturally beside `lock-refresh` in refresh.yml.

### F6. Atom feeds are excellent *signals* but can't drive Renovate, and don't beat `git ls-remote` for a homegrown poller

- Both signals have clean, unauthenticated Atom feeds:
  `github.com/bloomberg/clang-p2996/commits/p2996.atom` (20 entries, entry id
  = full SHA) and `github.com/jwakely/pkg-gcc-latest/commits/gh-pages.atom`,
  whose commit titles literally carry the deb version string ("Regenerate
  index.html for 20260705git88752b86ff1a") — arguably a cleaner deb signal
  than scraping the HTML index (both fetched 2026-07-09).
- But Renovate's custom datasource supports only `json`/`plain`/`yaml`/
  `toml`/`html` — **no xml/rss/atom format**
  (<https://docs.renovatebot.com/modules/datasource/custom/>), so feeds are
  unusable by the incumbent HTML-datasource path. And for a homegrown GHA
  poller, one `git ls-remote <url> refs/heads/p2996` returns exactly the SHA
  with zero parsing — strictly simpler than fetching+parsing XML. Atom adds
  value only for third-party feed-to-notification services or an RSS reader;
  it is a fallback signal, not the trigger mechanism of choice.

### F7. Comparison — which triggers a build fastest with least machinery

Context: a pin-bump PR touches `docker-bake.hcl`/`.devcontainer/Dockerfile`,
both on the CI `changes` build filter, so the PR itself runs the full
build+smoke chain and `promote` retags `:dev` on merge
(`.github/workflows/AGENTS.md`, Pipeline stages + path-gate invariant). So
"trigger a build" = "open an auto-merging PR"; end-to-end = discovery latency
+ ~1h build + automerge.

| Mechanism | Worst-case discovery latency | New machinery | Same-PR companions (lockfiles / deb sha) | Verdict |
|---|---|---|---|---|
| Renovate git-refs, today (Friday gate) | ~7 d (observed 8 d, F3) | none | no / no | too slow as-is |
| Renovate git-refs + schedule override | hosted job cadence: ≤ ~24 h, ~4 h "activated" tier (Mend doc, F3) | **1-line config** | no / no | cheapest daily-or-better for p2996 |
| Renovate + dashboard-checkbox poker | poller cron (~1 h honest) + ≤10 min hosted provisioning | ~20-line fail-soft job (F3) | no / no | near-on-demand while Renovate stays sole PR author |
| GHA cron + `git ls-remote` + PR (resurrect `p2996-refresh`) | your cron + drift: daily guaranteed; hourly realistic | ~1 workflow job (module/tests/task/composites all in-tree, F4) | **yes / yes (policy-gated)** | most deterministic; only option that closes the deb sha gap |
| Upstream webhooks / repository_dispatch | n/a — impossible without upstream admin (F2) | — | — | dismissed |
| Atom feeds + third-party watcher | poll cadence of the watcher | external service + glue | no | signal only (F6) |
| Release-watch services (newreleases.io etc.) | n/a for tagless branches/rolling debs | external | no | dismissed (F2) |

**Bottom line for the domain recommendation:** for the p2996 SHA, the
*cheapest* adequate fix is a Renovate schedule override (config-only,
≤ ~24 h); the *most deterministic* and only-fully-general fix is
resurrecting the in-repo `p2996-refresh` job (near-zero cost, exact cron
control, same-PR companion regen, no dependence on Mend's opaque scheduler).
If both run, they race to the same pin — pick ONE writer per pin to avoid
duplicate/conflicting PRs (if the GHA job returns, drop the git-refs
customManager in the same change). For the deb, discovery is already
adequate at any daily cadence; the real decision is whether to automate the
sha256 recompute (in-repo job only), which is a security-posture call for
Ray, not a tooling gap.

## Uncertainties / gaps

- **U1 — Hosted Renovate effective cadence after a schedule override** is
  inherited from sibling report F3 (~4h hot, activity-dependent); Mend does
  not contractually guarantee it. If Ray needs a *guaranteed* ≤24h bound,
  only the in-repo cron provides it.
- **U2 — PR #188's 8-day latency is confounded**: the 2026-07-08 run may have
  been a manual portal trigger after the renovate.json rework (sibling U1),
  so 8 days is an upper-bound observation consistent with, not proof of, the
  Friday gate; the PR-body schedule text is the stronger evidence.
- **U3 — newreleases.io commit-tracking**: dismissed on its release-centric
  model (landing page + <https://systhoughts.com/posts/tracking-software-releases-across-forges>);
  I did not exhaustively probe whether it has an undocumented branch-commit
  tracker. Does not change the conclusion (third-party + glue for no cadence
  gain).
- **U4 — WebFetch summaries are model-condensed**; verbatim-critical items
  (feed SHAs/dates, PR #189 state, Dockerfile/renovate.json/refresh.yml
  contents) were read from raw feeds/API/files, but Renovate docs phrasing
  rests on fetched-page summaries cross-checked by search results.
- **U5 — GHA cron drift magnitude** varies by period; the multi-hour-drift
  reports (discussions #196910, runner #4468) are worst-case episodes, not
  steady state. At daily granularity this is noise; quantify before ever
  promising sub-hourly reaction.
- **U6 — "Activated = 4-hourly" tier assignment is Mend policy, not
  contract** (job-scheduling doc, re-verified 2026-07-09): tier assignment
  depends on Mend's Renovate Status for the repo, which we cannot read from
  this container. If a *guaranteed* ≤24h bound is required, only the in-repo
  cron provides it.
- **U7 — Dashboard-checkbox automation is inferred, not probed**: the docs
  describe UI ticking; I did not verify the hosted app reacts identically to
  an API-driven issue-body edit. A 5-minute live probe settles it; design
  fail-soft regardless (checkbox was removed once, discussion #20386).

## Re-verification stamp (second pass, 2026-07-09)

Independent re-research confirmed the load-bearing claims of this report
from primary sources: p2996 atom feed HEAD `7220baf` (2026-06-30) matches
`Dockerfile:233`; sha256 human gate verbatim at `Dockerfile:336-347` with
the committed deb pin (20260621) one snapshot behind upstream (20260705) —
consistent with PR #189 blocked on the hash; `p2996_refresh.py`
ls-remote implementation and `mise.toml:675-677` task present in-tree;
webhook admin requirement, repository_dispatch repo-scope requirement,
GHA 5-min floor/delay/drop language, Mend 4-hourly activated tier, and
GCC weekly snapshot cadence all re-confirmed against the cited pages.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — renovate.json, refresh.yml, Dockerfile, docker-bake.hcl, p2996_refresh.py, mise.toml read from tree; PR #189 state via GitHub API.
- [bloomberg/clang-p2996](https://github.com/bloomberg/clang-p2996) — `p2996` branch Atom commit feed (HEAD SHA + commit cadence).
- [jwakely/pkg-gcc-latest](https://github.com/jwakely/pkg-gcc-latest) — master + gh-pages Atom feeds (deb publication cadence + signal quality); jwakely.github.io index page.
- [renovatebot/renovate](https://github.com/renovatebot/renovate) — git-refs datasource docs, custom-datasource format list, self-hosted cacheTtlOverride docs, cache-TTL discussions #36290/#24214, issue #13798.
- [jdx/renovate-config](https://github.com/jdx/renovate-config) — Friday-only schedule preset (via PR #188/#189 bodies + sibling report F2).
- [actions/runner](https://github.com/actions/runner) — cron-drift issues #2977/#4468.
- [lowlydba/cron-drift](https://github.com/lowlydba/cron-drift) — GHA cron drift measurement tooling.
- [newreleasesio (org)](https://github.com/newreleasesio) — release-watcher service model check (dismissal).
- [mend/renovate-ce-ee](https://github.com/mend/renovate-ce-ee) — CE/EE scheduling defaults + hosted checkbox support issue #187 (second-pass verification).
- [gcc-mirror/gcc](https://github.com/gcc-mirror/gcc) — upstream weekly snapshot cadence via gcc.gnu.org/snapshots.html (second-pass verification).
