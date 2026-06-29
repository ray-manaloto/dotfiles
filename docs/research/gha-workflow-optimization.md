# GHA Workflow Optimization — Deep Dive

Date: 2026-06-29. Scope: all six workflows under `.github/workflows/`,
plus the bake/hash machinery they drive. Goal: identify redundancy and
evaluate two specific ideas — (1) a reusable "latest p2996" action, and
(2) auto-build-and-publish when a new p2996 commit appears — without
breaking the repo's reproducibility invariants.

> Status: **analysis + recommendations**. Nothing here is implemented yet;
> it exists so we can agree a target architecture before changing CI.

## Inventory

| Workflow | Trigger(s) | Purpose |
|----------|-----------|---------|
| `ci.yml` | `pull_request`, `push:main`, `schedule` (daily 00:00 CT), `workflow_dispatch` | Main pipeline + `promote` retag |
| `autofix.yml` | `pull_request` | Auto-format, commit back |
| `ci-failure-report.yml` | `workflow_run` (CI failure) | Async failure diagnostics |
| `image-analysis.yml` | `workflow_run` (CI success, non-push) | Async benchmark + Trivy CVE scan |
| `snapshot-refresh.yml` | `schedule` (daily 00:00 CT), `workflow_dispatch` | PR on conda-forge snapshot drift |
| `p2996-refresh.yml` | `schedule` (daily 00:00 CT), `workflow_dispatch` | PR on new `clang-p2996` HEAD |

**Three workflows now fire on the same daily `0 0 * * *` cron**: `ci.yml`
(nightly build+publish on the *pinned* ref), `snapshot-refresh`, and
`p2996-refresh`.

## Current state — triggers → workflows

```mermaid
flowchart LR
  PRe[pull_request] --> CI[ci.yml]
  PRe --> AF[autofix.yml]
  PM[push: main] --> CI
  C1["cron 0 0 * * *"] --> CI
  C2["cron 0 0 * * *"] --> SR[snapshot-refresh.yml]
  C3["cron 0 0 * * *"] --> PR2[p2996-refresh.yml]
  WD[workflow_dispatch] --> CI
  WD --> SR
  WD --> PR2
  CI -- "workflow_run: success" --> IA[image-analysis.yml]
  CI -- "workflow_run: failure" --> FR[ci-failure-report.yml]
```

## Current state — ci.yml job DAG

```mermaid
flowchart TD
  lint --> cp[contract-preflight]
  lint --> ch[changes path-gate]
  cp --> bp[base-prep]
  ch --> bp
  bp --> pp[p2996-prep]
  cp --> pp
  ch --> pp
  bp --> bld[build]
  pp --> bld
  cp --> bld
  ch --> bld
  bld --> st[smoke-test]
  ch --> st
  lint --> pr[promote]
  ch --> pr
```

- **PR / schedule / dispatch path:** `lint → contract-preflight →
  changes → base-prep → p2996-prep → build → smoke-test`. The
  `base-prep…smoke-test` chain is gated `if: (not push-to-main) &&
  changes.build == true`.
- **push-to-main path:** `lint → promote` (manifest-only retag of the
  merged PR's `:pr-NNN` → `:dev`/`:latest`; ~30s, no rebuild).
- `base-prep` / `p2996-prep` are **content-hash cache probes**: compute a
  16-char hash of inputs, `docker manifest inspect` the
  `:base-<hash>` / `:p2996-<hash>` tag, build+push only on miss.

## Current state — how a new p2996 commit reaches `:dev`

```mermaid
sequenceDiagram
  participant Cron
  participant PR2 as p2996-refresh
  participant Repo
  participant CI as ci.yml (PR)
  participant Human
  participant CIm as ci.yml (push:main)
  Cron->>PR2: daily
  PR2->>PR2: git ls-remote p2996 HEAD
  PR2->>Repo: rewrite docker-bake.hcl ref (if advanced)
  PR2->>Repo: create-pull-request chore/p2996-refresh
  PR2->>CI: gh workflow run ci.yml --ref branch
  CI->>CI: p2996-prep MISS -> clang rebuild + push :p2996-<hash>
  CI->>CI: build :pr-NNN/:sha-<sha>, smoke-test
  Human->>Repo: review + merge PR
  Repo->>CIm: push:main
  CIm->>CIm: promote retag :pr-NNN -> :dev/:latest
```

Six hops, one of them a **manual merge**, plus a dependency on the
"Allow GitHub Actions to create and approve pull requests" repo setting
(currently **off** — the reason the first scheduled run pushed its branch
but failed to open the PR; #113 was opened manually instead).

## Redundancy analysis — real vs intentional

| Observation | Verdict |
|---|---|
| `snapshot-refresh` and `p2996-refresh` are ~80% identical (triggers, perms, concurrency, checkout, create-PR, ci dispatch) | **Real, low-ROI.** Differ only in detection (in-container `mise-snapshot` vs on-runner `git ls-remote`+regex). Consolidatable via a shared composite action for the create-PR tail; full merge couples two failure domains. |
| 8 jobs repeat `checkout` + `jdx/mise-action` setup | **Mostly intentional.** Subset installs cache separately (`install_args_hash`) and isolate failures. But the *boilerplate* is duplicable into one composite action with no cache penalty. |
| 3 daily crons (`ci` nightly, `snapshot-refresh`, `p2996-refresh`) | **Partly real.** `ci` nightly rebuilds+publishes on the *pinned* ref (catches base-image CVEs / floating tool drift); the two refresh crons exist to *change* the pin/snapshot. They are complementary, but the timing collision and overlapping intent are confusing and undocumented. |
| `base-prep` / `p2996-prep` cache-probe pattern duplicated | **Intentional.** Two independent cache tiers; the duplication is the design (`P2996-CACHE.md`). Leave as-is. |
| `image-analysis` + `ci-failure-report` both `workflow_run` off CI | **Intentional.** Async, off the PR critical path; correct. |

**Bottom line:** the cache-tier and async-analysis duplication is
deliberate and should stay. The genuinely reducible surface is (a) the
checkout+mise boilerplate, (b) the create-PR tail shared by the two
refresh workflows, and (c) the *manual merge* + *cron overlap* in the
p2996/snapshot publish path.

## Idea 1 — a reusable "latest p2996" action

Today the query is already one CLI call (`dotfiles-setup p2996-refresh`,
`python/src/dotfiles_setup/p2996_refresh.py`) that does ls-remote +
compare + rewrite. The reusable unit worth extracting is not the query
(already DRY) but the **workflow plumbing around it**:

- A composite action `./.github/actions/setup-mise` (inputs:
  `install_args`) wrapping `actions/checkout` + `jdx/mise-action`. Reused
  by all 8 jobs; keeps per-args caching.
- A composite action `./.github/actions/open-refresh-pr` (inputs: branch,
  title, body, paths, label) wrapping `peter-evans/create-pull-request` +
  the `gh workflow run`/auto-merge tail. Reused by both refresh
  workflows.

These are **composite actions**, not reusable workflows — composite
actions compose inside an existing job (no extra runner, no 1-level
nesting limit, no loss of cache isolation).

## Idea 2 — new p2996 commit → build → publish, automatically

The literal "skip the PR, build and push `:dev` directly on detect" is
**not recommended**: it decouples the published image from the pinned
`CLANG_P2996_REF` in `docker-bake.hcl`, which is the content-hash cache
key and the reproducibility anchor. You would lose the "what SHA is in
`:dev`?" guarantee and the audit trail.

The same outcome — *fully unattended* publish of the latest p2996 — is
achievable **without** sacrificing reproducibility by closing the one
manual hop with **auto-merge**:

```mermaid
sequenceDiagram
  participant Cron
  participant PR2 as p2996-refresh
  participant Repo
  participant CI as ci.yml (PR)
  participant CIm as ci.yml (push:main)
  Cron->>PR2: daily
  PR2->>Repo: rewrite ref + create-pull-request
  PR2->>Repo: gh pr merge --auto --squash
  PR2->>CI: dispatch ci.yml on branch
  CI->>CI: build + smoke-test (gates)
  CI-->>Repo: checks green -> auto-merge fires
  Repo->>CIm: push:main
  CIm->>CIm: promote retag -> :dev/:latest
```

This keeps the pin in the repo, keeps the CI build+smoke gate, keeps the
PR as the audit record — and removes the human step. It requires:

1. Enable **"Allow GitHub Actions to create and approve pull requests"**
   (`can_approve_pull_request_reviews: true`).
2. Add a `gh pr merge --auto --squash` step after create-PR in both
   refresh workflows (auto-merge waits for required checks).
3. Ensure branch protection requires the `smoke-test` (and lint/
   contract) checks, so auto-merge cannot land a broken image.

If you want a *review gate* for p2996 specifically (a compiler bump is
higher-risk than a snapshot refresh), keep auto-merge **on** for
`snapshot-refresh` and **off** for `p2996-refresh` (human merges the
compiler bump after eyeballing the upstream commit range). That is a
one-line policy difference, not a structural one.

## Recommendations (ranked)

| # | Change | ROI | Effort | Risk |
|---|--------|-----|--------|------|
| R1 | Enable the Actions create-PR setting + `--auto` merge on `snapshot-refresh` (and optionally `p2996-refresh`). Require smoke-test in branch protection. | **High** — delivers the "auto-publish latest" goal, preserves reproducibility | Low | Low (gated by CI) |
| R2 | Extract `./.github/actions/setup-mise` composite; adopt in all 8 jobs | Med — less drift, ~7 fewer copies | Low-Med | Low |
| R3 | Extract `./.github/actions/open-refresh-pr` composite; adopt in both refresh workflows | Med — kills the real duplication | Low-Med | Low |
| R4 | Document the 3 daily crons' distinct roles in `workflows/AGENTS.md`; consider staggering them (e.g. refresh at 00:00, nightly `ci` at 02:00) so a same-day ref bump is what the nightly publishes | Med — removes the confusion that prompted this review | Low | Low |
| R5 | Decide p2996 review policy (auto-merge vs human) and encode it; keep `docker-bake.hcl` pin as the single source of truth either way | Med | Low | Low |

**Not recommended:** merging the two refresh workflows into one file
(couples failure domains for ~80 saved lines); collapsing the base/p2996
cache tiers (the split is the optimization); build-and-push-without-PR
(breaks reproducibility).

## Suggested target state

```mermaid
flowchart TD
  subgraph daily [daily crons, staggered]
    SR[snapshot-refresh] -->|setup-mise + open-refresh-pr| PRa[PR + auto-merge]
    PR2[p2996-refresh] -->|setup-mise + open-refresh-pr| PRb[PR + auto-merge?]
    NB[ci.yml nightly] --> Pub1[rebuild on pinned ref -> :dev]
  end
  PRa --> CI[ci.yml build+smoke]
  PRb --> CI
  CI -->|merge| Prom[promote -> :dev/:latest]
```

Net: same number of workflows (each has a distinct job), but the
duplicated plumbing lives in two composite actions, the publish path is
unattended, and the cron roles are documented and staggered.

---

# v2 — Reusable-workflow target architecture (deeper rethink)

The v1 recommendations above are incremental (composite actions + auto-merge
on the existing shape). This section answers the follow-up: *is there a
fundamentally more input-driven, event-driven design?* Yes — extract the
build/publish pipeline into one **reusable workflow (`workflow_call`)** that
every trigger calls with inputs. Researched against GitHub's current docs
and six real-world repos (see sources at end).

## What this repo already does well

The real-world survey shows this repo has already adopted the strongest
patterns; the redesign should preserve them, not replace them:

- **Content-hash as the cache tag** (`:base-<hash>`, `:p2996-<hash>`) — same
  idea as `5monkeys/docker-image-context-hash-action`, but ours is finer
  (sentinel-delimited Dockerfile sections, two tiers).
- **Registry as the idempotency oracle** (`docker manifest inspect` →
  skip) — identical to the `cocallaw` and trivy patterns.
- **Pinned upstream version committed to the repo** (`CLANG_P2996_REF` in
  `docker-bake.hcl`) — the audit-trail/reproducibility pattern from
  `aquasecurity/trivy-action`'s bump workflow.

The gap is purely **structural**: that build logic is inlined in `ci.yml`
and cannot be invoked by anything other than `ci.yml`'s own triggers, so the
refresh workflows reach it only indirectly (open a PR, then
`gh workflow run ci.yml --ref <branch>`).

## The core constraint that shapes everything

`GITHUB_TOKEN`-created PRs/commits **do not trigger downstream `pull_request`/
`push` workflows** (GitHub's recursion guard). That single fact explains the
current `gh workflow run ci.yml --ref <branch>` hack in both refresh
workflows — it's a manual re-trigger because the auto-opened PR's CI won't
fire on its own. Two clean ways out:

1. **GitHub App token** (`actions/create-github-app-token`) for the refresh
   PR's push → normal `pull_request` CI fires → `gh pr merge --auto` lands
   it. Removes the dispatch hack *and* the "Allow Actions to create PRs"
   setting dependency.
2. **`repository_dispatch`/`workflow_call`** directly into the build (skip the
   PR) — faster, but loses the in-repo pin unless paired with a commit-back.

## Target shape

```mermaid
flowchart TD
  subgraph callers [thin per-trigger callers]
    A["ci.yml — pull_request / push:main"]
    B["nightly.yml — schedule (staggered)"]
    C["refresh.yml — schedule: detect p2996 + snapshot drift"]
  end
  RW["build-publish.yml (on: workflow_call)
  inputs: ref, p2996_ref, tag_strategy, publish, platform
  jobs: base-prep -> p2996-prep -> build -> smoke-test
  outputs: image_ref, digest"]
  SM["composite: setup-mise (checkout + jdx/mise-action)"]
  A -->|"with: tag=pr/sha, publish=false"| RW
  B -->|"with: tag=dev/latest, publish=true"| RW
  C -->|"App-token PR + auto-merge -> push:main"| A
  RW -. uses .-> SM
```

- **`build-publish.yml`** (`on: workflow_call`) holds the `base-prep →
  p2996-prep → build → smoke-test` chain exactly as today, parameterized by
  `inputs: { ref, p2996_ref, tag_strategy (string: pr|sha|dev|nightly),
  publish (bool), platform }` and emitting `outputs: { image_ref, digest }`.
  A `uses:` job can carry `needs`/`if`/`permissions`/`concurrency` but no
  steps — which fits, because each tier is already its own job.
- **`ci.yml`** shrinks to a caller: PR → `tag=pr, publish=false`; push:main
  keeps `promote` (manifest retag) as-is.
- **`refresh.yml`** merges the two near-identical refresh workflows into one
  file with two independent detector jobs (p2996 via `git ls-remote`,
  snapshot via in-container `mise-snapshot`), each using the shared
  `open-refresh-pr` composite with an **App token** so CI fires + auto-merge.
- **`setup-mise`** composite removes the checkout+mise block from all 8 jobs
  (composite actions keep per-args caching and let each job add its own
  steps — the right tool here, vs a reusable workflow).

## Mapping current → reusable inputs

| Current (ci.yml) | Becomes |
|---|---|
| `base-prep` job (base-hash probe/build) | `build-publish.yml` job 1 (unchanged) |
| `p2996-prep` job (p2996-hash probe/build) | job 2; `p2996_ref` overridable via input for "build this exact upstream SHA" |
| `build` job (`bake dev`, tag via metadata-action) | job 3; `tag_strategy`/`publish` inputs drive `metadata-action` + `push` |
| `smoke-test` job | job 4 (unchanged; still the required gate) |
| `promote` job | stays in `ci.yml` (push:main only) |
| `changes` path-gate | stays in `ci.yml`; callers pass `publish`/skip decisions |

## Recommended target (balances ambition vs the repo's invariants)

- **Keep** the two-tier content-hash cache, `promote` manifest-retag, and the
  pin-in-`docker-bake.hcl` reproducibility anchor. Do **not** adopt
  build-and-push-direct (Example C/E's unconditional or PR-less publish) — it
  breaks the "what SHA is in `:dev`?" guarantee that this repo deliberately
  maintains.
- **Adopt** the BretFisher "one reusable build, thin callers" structure and a
  GitHub App token so the upstream-detected bump flows
  `detect → App-token PR → CI (real) → auto-merge → promote` with zero manual
  steps, pin intact.
- **Optional** `repository_dispatch` path only if you later want sub-daily
  reaction to upstream without waiting on the cron.

## Phased migration (each phase shippable + reversible)

1. **Phase A (low risk, high clarity):** `setup-mise` composite + merge the
   two refresh workflows into `refresh.yml` (two jobs, shared composite).
   No behavior change. Document + stagger crons (v1 R4).
2. **Phase B (the unlock):** extract `build-publish.yml` (`workflow_call`);
   `ci.yml` becomes a caller. Behavior-preserving — same jobs, same gates.
3. **Phase C (automation):** App token for refresh PRs + `gh pr merge --auto`
   (policy: auto-merge snapshot; choose auto vs review for the p2996 compiler
   bump). Drops the `gh workflow run` dispatch hack and the create-PR setting.
4. **Phase D (optional):** `p2996_ref` input + a `repository_dispatch` caller
   for on-demand "build exactly this upstream SHA" without a cron wait.

## Decision points for sign-off

- **App token vs keep the dispatch hack?** App token is cleaner and the
  research-recommended path; it needs a one-time GitHub App install (org
  setting). If you'd rather not, we keep `gh workflow run` + enable the
  create-PR setting (v1 R1).
- **p2996 auto-merge or review?** Snapshot refresh → auto-merge is safe;
  the compiler bump is higher-risk — recommend human review there unless you
  want fully hands-off (smoke-test is the safety net either way).
- **Scope now:** Phase A+B are pure refactors (safe to do anytime); C is the
  behavior change that delivers "new commit → published image, unattended."

## GitHub repos touched

- [bloomberg/clang-p2996](https://github.com/bloomberg/clang-p2996) — the tracked upstream whose `p2996` HEAD drives the refresh.
- [peter-evans/create-pull-request](https://github.com/peter-evans/create-pull-request) — PR-creation action in both refresh workflows.
- [peter-evans/repository-dispatch](https://github.com/peter-evans/repository-dispatch) — reference for the optional `repository_dispatch` detect→build path.
- [jdx/mise-action](https://github.com/jdx/mise-action) — the repeated setup step analyzed for the `setup-mise` composite.
- [aquasecurity/trivy-action](https://github.com/aquasecurity/trivy-action) — image-analysis CVE scan (pin fixed in #112); also the bump-PR upstream-pin reference pattern.
- [aquasecurity/trivy-db](https://github.com/aquasecurity/trivy-db) — scheduled-rebuild reference (the unconditional-rebuild anti-pattern).
- [github/codeql-action](https://github.com/github/codeql-action) — SARIF upload in image-analysis (pin fixed in #112).
- [BretFisher/docker-build-workflow](https://github.com/BretFisher/docker-build-workflow) — canonical "one reusable build, thin multi-trigger callers" reference.
- [hassio-addons/workflows](https://github.com/hassio-addons/workflows) — two-layer reusable-workflow org pattern.
- [5monkeys/docker-image-context-hash-action](https://github.com/5monkeys/docker-image-context-hash-action) — content-hash-as-tag reference (this repo's two-tier hash is a finer version).
