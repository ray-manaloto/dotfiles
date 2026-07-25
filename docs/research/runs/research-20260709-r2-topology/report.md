# Run B — Image topology: one image vs two forked from a common base

Date: 2026-07-09. Synthesis of five angle reports
(`agents/{current-graph,single-image,two-image-fork,lean-heavy-reverify,industry-patterns}.md`)
plus 10 adversarially verified claims (3 votes each; 8 CONFIRMED, 2 REFUTED —
verdicts from the Run B verification stage). Repo baseline:
`docs/research/runs/research-20260709-r2-inventory/report.md`. Produced in the
remote research container (Bash blocked; no docker measurement possible —
size figures carry their provenance inline). Sibling constraint set: Run A
(web env) verified that custom base images are NOT supported on Claude Code
web, sessions get ~4 vCPU / 16 GB / **30 GB disk** with docker+compose and
ghcr.io allowlisted, and the setup script (~5-min budget) + ~7-day filesystem
snapshot is the de-facto custom-image mechanism.

## Executive summary — recommendation

**Recommendation: keep ONE published heavy image (`:dev`) today, and land the
"fork-ready" refactor now: split the base tier's mise config into `core`
(20 shared pinned tools + python/uv) and `cpp` (8 language runtimes + ~25
conda C++ packages) and materialize a `devcontainer-core` stage inside the
existing single multi-stage Dockerfile — but do NOT publish a second lean
image until a confirmed consumer exists.** Concretely:

1. **Not one-image-everywhere.** CONFIRMED hard-blocked on web (custom base
   images unsupported; ~37.6 GB measured-by-inference `:dev` > 30 GB session
   disk, even as a compose sidecar) and strictly dominated in CI (measured
   5m27s image pull vs 5-25 s mise-action restore per job).
2. **Not a lean `:ci` image for ci.yml either.** The claim "container jobs
   are faster than cached mise-on-runner" was **REFUTED** by the repo's own
   telemetry (lint: 45-48 s total, 20-25 s install, warm). Hosted runners
   re-pull job containers every run with no cross-run cache; pin-bump PRs
   would need the image rebuilt *before* lint; and the runner install is
   itself the test surface that gates the daily lock-refresh auto-merge.
   mise-on-runner is already near-floor and structurally correct.
3. **The two-image fork is the right *shape* when a consumer appears** — it
   is the industry-canonical pattern (one Dockerfile, multiple bake targets,
   lean variant for ephemeral consumers, heavy for the persistent
   devcontainer) — but its only plausible consumer today is a web-session
   docker-compose sidecar, which Run A shows is second-fiddle to the
   sanctioned setup-script + snapshot path (web's marginal need is mise +
   shared.toml, minutes of setup script, not an image at all).
4. **Do the seam surgery now because it is cheap, reversible, and valuable
   regardless:** the split improves base-cache granularity (a conda toolchain
   bump stops busting the lean core), makes the future `:ci` leaf a one-PR
   flip, and costs exactly one ~20-30 min cold base rebuild and zero compiler
   rebuilds. The documented runtime-tier seam is the WRONG seam — the lean
   and heavy toolchains live together in stage 1; the true seam cuts through
   the BASE tier.

## Q1 — Where the size lives in today's 5-stage graph

Today's graph (current-graph F1/F2, verdict CONFIRMED with 3/3 votes):

| # | Stage | Published as | Contents |
|---|-------|--------------|----------|
| 1 | `devcontainer-base` | `:base-<hash16>` (bake `base`) | apt seed + mise + **BOTH** the lean toolchain (20 shared pinned tools, python/uv via `shared.toml`) **AND** the heavy payload (8 language runtimes at latest + ~25 `conda:` C++ packages) — one `mise install --system --locked` RUN (Dockerfile:171-188) |
| 2 | `clang-builder-cold` | — | clang-p2996 compile (~30 GB intermediates, never shipped; decoupled from base since #160 T11) |
| 3 | `p2996-export` | `:p2996-<hash16>` (bake `p2996-cache`) | ~500 MB `/opt/clang-p2996` artifact |
| 4 | `devcontainer` | — | gcc-latest trunk .deb → `/opt/gcc-latest` + COPY p2996 |
| 5 | `devcontainer-runtime` | `:dev` etc. (bake `dev`) | thin RUNTIME tier (gh, fnox, bats, AI CLIs, pipx C++ linters) via `MISE_ENV=runtime` |

Size facts, with provenance discipline (CONFIRMED: *every* in-repo figure is
doc-derived, none measured):

- Full `:dev` ≈ **37.6 GB** — the best current estimate, derived by a
  verifier from the 2026-07-09 image-analysis run 29013595948 Dive log
  (efficiency 99.9905%, wastedBytes 3,570,443 ⇒ total ≈ 3.57 MB / 0.000095),
  consistent with the ubiquitous "~38 GB" doc figure (build-publish.yml:631,
  mise.toml:230, sync.py:40).
- p2996 artifact ~500 MB (P2996-CACHE.md:17-18); builder intermediates
  ~30 GB never ship; pre-C++-payload lean core measured **1.33 GB** on
  2026-03-29 (stale benchmark, docs/research/trail/findings/docker-benchmarks/).
- `.dive-ci` bounds waste (efficiency ≥0.85 enforced; measured 99.99%), so
  the ~37.6 GB is real content, not layer duplication.
- **The per-tier apportionment is NOT measured.** A specific split ("base
  toolset = 4.83 GB of a 5.06 GB compressed image") was **REFUTED** — the
  numbers appear nowhere in the repo or in accessible CI artifacts (see
  Refuted section). Directionally, base tier (runtimes + conda toolchain) +
  gcc-latest plausibly dominate and the ~500 MB p2996 payload does not, but
  no load-bearing decision should rest on an apportionment until the
  `devcontainer-metrics` artifact from run 29013595948 (expires 2026-10-07)
  is pulled in a shell-enabled session.

Key structural fact for any delta: the lean web/CI toolchain and the heavy
C++ payload are installed in the SAME stage-1 layer (two-image-fork F1). The
documented "natural fork seam" at the runtime tier (mise-runtime.toml:10-12)
would fork *above* ~30+ GB of base — useless for a lean leaf.

## Q2 — Can a thin image serve the ci.yml toolchain (and web), or is mise-on-runner optimal?

**mise-on-runner is already optimal for CI; a thin image loses on every
axis** (lean-heavy-reverify F1-F7 + single-image F2-F3; the pro-container
claim was REFUTED 0/3):

- Measured warm path (Actions API, runs 29043090828 / 29011164725 /
  28970137705): lint **45-48 s total** with a 20-25 s "Install mise" step for
  the full ~44-tool host set; contract-preflight **12-13 s** (python+uv in
  6-7 s). Per-run setup overhead across all short jobs ≈45 s total.
- Measured image cost: full-image pull **5m27s** on ubuntu-latest (run
  29013595948, job 86102935590) plus a 5m40s free-disk step where extraction
  needs room — an order-of-magnitude regression per job (13-27× depending on
  comparison), CONFIRMED. Hosted runners pull `container:` images fresh
  every job — no cross-run layer cache (community discussions #25975,
  #47550), and GHCR has documented degradation incidents (#173607: 1.5 GB in
  8m14s vs 14 s from docker.io).
- Even a lean 2-4 GB `:ci` image (~30 s-3 min pull+extract per job) is a wash
  at best on lint and a strict regression on the 6-7 s python+uv jobs.
- **Chicken-and-egg:** pins change near-daily (Renovate automerge + daily
  lock-refresh). A PR bumping a lint tool must lint *with the new pin* —
  containerized lint either rebuilds the image on the PR critical path,
  reinstalls the delta via mise anyway (making the image pointless), or
  silently lints the wrong toolchain (violates MISE_LOCKED intent +
  ci-local-parity).
- **The runner install IS a test.** lint exercises fresh mise.lock resolution
  on linux-x64, `mise reshim`, `mise doctor` — the gate that the auto-merging
  daily lock-refresh PRs depend on. Baking tools into an image deletes that
  surface (lean-heavy-reverify F6).
- **There is no CI pytest job** (grep of `.github/**` — zero matches; the
  316-test suite runs in the hk pre-push hook and locally), so "the ci.yml
  test toolchain" a lean image would serve does not exist; if added, its
  needs are python+uv — a 6-7 s runner install.
- Upstream alignment: mise's own docs recommend mise-action + lockfile-keyed
  cache on GHA; their "image with mise preinstalled" recipe is the GitLab
  pattern (industry-patterns F4).
- If CI setup time ever needs trimming, the lever is `install_args`/
  `MISE_ENV` scoping (lint installs ~14-18 tools no CI step uses —
  colima, aws-cli, azure-cli, opencode…), not an image (lean-heavy-reverify F7).

**For web sessions** the same logic lands differently but at the same
conclusion: the web VM already ships python/uv/pytest/ruff, GCC/Clang/cmake,
git/jq/ripgrep natively; the marginal web install is mise + the 20-tool
shared fragment inside the ~5-min setup-script budget, then snapshot-cached
~7 days. A sidecar image is not the session environment (Claude's tools run
in the outer VM; everything would need `docker exec` wrapping that no repo
tooling supports). So the shared **mise configs** — not an image layer — are
the artifact CI, web, and host all consume. Version parity is already ~90%
delivered by shared.toml + MISE_LOCKED + rattler-sha256 lockfiles
(single-image F6); the residual (apt/glibc parity) matters to no current CI
job and cannot apply to web anyway.

## Q3 — Applicable industry common-base fork patterns

(industry-patterns F1-F5)

1. **Fork inside one Dockerfile, publish per-stage bake targets** — Docker's
   own bake docs: "In most cases you should just use a single multi-stage
   Dockerfile with multiple targets" (https://docs.docker.com/build/bake/contexts/);
   BuildKit dedups shared stages within one bake invocation
   (https://depot.dev/blog/buildx-bake-deep-dive). This repo already does
   exactly this for dev/base/p2996-cache; a lean variant is +1 stage, +1
   target, not a second Dockerfile.
2. **Small variant count, one refresh pipeline** — Uber Devpod ships six
   per-audience flavors from one maintained base with nightly channels
   (https://www.uber.com/blog/devpod-improving-developer-productivity-at-uber/);
   devcontainers/images publishes base/language/universal families with one
   version stamping all variants' tags, and explicitly steers users AWAY
   from the one-giant-image `universal` (x86-64-only, "largest image in this
   set"). Two variants is well inside norms; both should ride the same
   promote/nightly lifecycle.
3. **Nobody delivers a ~38-50 GB toolchain by registry pull at session
   start.** GHA's >50 GB toolchain arrives as a VM disk image; Codespaces
   prebuilds are stored container snapshots restored per session (pay
   storage to make start O(snapshot-restore)); hyperscaler lazy-pull
   (eStargz/SOCI/Nydus) requires snapshotter control unavailable on web
   sandboxes or stock runners. The heavy image's audience is only the
   persistent local devcontainer — which already amortizes via `mise run
   sync` + the content-addressed registry cache. Notably, Run A's finding
   that Anthropic web snapshots the filesystem (including pulled Docker
   images) is the Codespaces-prebuild economics arriving on web.
4. **Byte-level sharing requires engineering layer boundaries** (nix layered
   images lesson): both leaves must consume the SAME built core stage as a
   digest-pinned context so shared layers are digest-identical — precisely
   this repo's existing probe + named-context mechanism (F5).
5. **Multi-config devcontainers are first-class** — Codespaces prebuilds are
   scoped per devcontainer.json config; devcontainers/ci selects via
   `configFile` with per-config `imageName`. If a lean leaf is ever consumed
   *as* a devcontainer, it is a second config pointing at `:ci`, not a fork
   of lifecycle scripts (two-image-fork F5).

## Q4 — Incremental migration path; what changes in ci.yml / build-publish.yml

**Phase 0 (now, recommended): fork-ready refactor, still one published image.**

- Split `.devcontainer/mise-system.toml` → `mise-core.toml` (COPY as
  `config.toml`: shared 20 + python/uv) + a `config.cpp.toml` env config
  (runtimes + conda toolchain), with per-env lock `mise.cpp.lock` (native
  mise mechanism, same as the existing `mise.runtime.lock`; MISE_ENV accepts
  comma lists, so the heavy chain runs `MISE_ENV=cpp` then `cpp,runtime`).
- Insert stage `devcontainer-core` before `devcontainer-base`; re-root
  `devcontainer-base` on it (`FROM devcontainer-core`). Core stays an
  **internal, unpublished** stage — zero registry/lifecycle cost.
- Optional in the same PR: a `CORE_HASH_BEGIN/END` sentinel + `core-hash`
  tier so the future `:core-<hash16>` probe is pre-wired (base-hash then
  folds core-hash, exactly as dev-hash folds base+p2996 today).
- Cost (CONFIRMED mechanics): splitting mise-system.toml busts base-hash →
  **one ~20-30 min cold base build**; **zero compiler rebuild** (p2996-hash
  independent since #160 T11); one `:dev-<hash>` marker miss (dev-hash folds
  the whole Dockerfile). The smoke tier-1 `identity-expected` merge-base
  logic absorbs the transition PR natively.
- ci.yml / build-publish.yml changes in Phase 0: `changes` path-filter gains
  the new file names (precedent: the shared.toml filter gap found landing
  #178); smoke tier-1 identity expected-source list points at the new
  core/cpp configs; lock-refresh composite regenerates the third lock.
  **No `container:` keys enter ci.yml — ever, per Q2.**

**Phase 1 (deferred, gated on a confirmed consumer): publish the lean leaf.**

- Add stage `devcontainer-ci` (FROM `devcontainer-core`; + gh CLI, little
  else) and bake targets `core` + `ci` (each `inherits = ["_common"]`, own
  `type=gha` cache scope `dotfiles-ci`, same provenance/SBOM `attest`
  block), plus `group "leaves" { targets = ["dev", "ci"] }`.
- build-publish.yml: new `core-prep` probe job (<30 s warm) feeding its
  digest to base-prep's miss build and to the ci leaf as
  `*.contexts.devcontainer-core=docker-image://…@sha256:…`; the ci leaf is
  cheap enough to build inside the existing `build` job as `targets: dev ci`
  (single-invocation BuildKit dedup builds core once); a `ci-hash` validated
  marker `:ci-<hash16>` stamped after a fast lean smoke, mirroring
  `:dev-<hash>` semantics.
- ci.yml `promote`: one job body performs BOTH manifest retags
  (`:pr-NNN`→`:dev`, `:ci-pr-NNN`→`:ci`), both-or-fail, so the rolling tags
  can never diverge across commits for longer than one red promote. Same
  package (`IMAGE_REF`), prefixed tag families — mirrors devcontainers/images'
  one-version-all-variants discipline.
- `ghcr_cleanup.py:29` `PRUNABLE_FAMILIES` gains `"core-"` and `"ci-"` in
  the same change (else the families accrete forever).

**Rollback:** delete the `ci` target + tag legs + probe; `devcontainer-core`
remains as a free internal stage. The only one-way door is the
mise-system.toml split — itself a cache-granularity win worth keeping in a
one-image world (two-image-fork F7).

## Q5 — Does a two-image split break the content-hash warm path + verify-container-latest?

**No — the preservation properties are CONFIRMED, provided six gates are
handled in the same change** (two-image-fork F3/F8; current-graph F3/F7;
both underlying mechanics claims verified 3/3):

- **Sentinel design protects the heavy caches.** base/p2996 hashes cover only
  sentinel-delimited Dockerfile sections + their COPY-input file bytes; a new
  stage added outside the sentinels busts NEITHER `:base-` nor `:p2996-`.
  dev-hash folds the whole Dockerfile, so any Dockerfile edit busts the
  `:dev-<hash>` marker exactly once — a bounded, expected cost.
- **The warm path is probe + digest-pinned named contexts, not layer cache**
  — it *extends* naturally: a fourth `core-hash` tier follows the identical
  probe/miss/context pattern; hash composition (base folds core) follows the
  existing dev-folds-base+p2996 precedent in `p2996_hash.py:432-444`.

| Gate | Impact | Preserve by |
|---|---|---|
| smoke tier-1 identity (devcontainer-smoke.sh:39-67; hard gate of `verify-container-latest`, mise.toml:446-454) | file split changes expected sources | point `identity-expected` at core (+cpp) configs; merge-base logic absorbs the transition PR. Both leaves share the identical core `config.toml`, so ONE identity check covers both — a free lockstep verifier |
| `verify-container-latest` itself | none — gates the heavy devcontainer only | no change |
| PLATFORM (linux/amd64/v2) feeding all three hashes; R1/R2/R3 | none — heavy leaf unchanged | core/ci hashes include PLATFORM like the others |
| `changes` path-gate (ci.yml) | new COPY inputs must be filtered | add mise-core/cpp toml+lock files |
| promote / ci-gate | two rolling tags on merge | single promote job, both retags, both-or-fail |
| ghcr-cleanup retention (`ghcr_cleanup.py:29`) | new tag families accrete | add `"core-"`, `"ci-"` to `PRUNABLE_FAMILIES` |
| provenance/SBOM (#160 T7) | two new published targets | inherit `attest`; extend the materials assertion (ci leaf's provenance contains the core digest) |

## Recommended stage/tag graph — delta vs today's bake targets

```
                       TODAY                     →    RECOMMENDED (Phase 0 solid, Phase 1 dashed)

ubuntu:26.04 (digest-pinned)                          ubuntu:26.04 (digest-pinned)
  └─ devcontainer-base ──────► :base-<hash16>           └─ devcontainer-core            [NEW, internal]
     └─ devcontainer                                       │   apt seed + mise + shared.toml
        └─ devcontainer-runtime ► :dev, :dev-<h>,          │   + mise-core.toml/.lock (python/uv + shared 20)
                                  :pr-NNN, :sha            │   (Phase 1: ► :core-<hash16>)
                                                           ├╬ devcontainer-ci           [Phase 1, LEAN LEAF]
BUILDER_IMAGE (decoupled)                                  │╬   +gh cli ► :ci, :ci-<sha>, :ci-pr-NNN, :ci-<hash16>
  └─ clang-builder-cold                                    └─ devcontainer-base         [CHANGED: FROM core;
     └─ p2996-export ────────► :p2996-<hash16>                │  installs config.cpp.toml under MISE_ENV=cpp]
                                                              │                        ► :base-<hash16>
bake targets: dev / base /                                    └─ devcontainer          [unchanged]
  p2996-cache / dev-load / validate                              └─ devcontainer-runtime [unchanged] ► :dev …

                                                      clang-builder-cold / p2996-export  [unchanged]
```

| Bake target | Today | Phase 0 delta | Phase 1 delta |
|---|---|---|---|
| `dev` | stage `devcontainer-runtime` | unchanged (chain now passes through core) | joins `group "leaves"` |
| `base` | stage `devcontainer-base` | FROM re-rooted on core; base-hash folds core-hash | consumes `:core` digest as named context |
| `p2996-cache` | stage `p2996-export` | unchanged | unchanged |
| `dev-load` / `validate` | local-only / dry-run | unchanged | unchanged |
| `core` | — | (optional) defined, unpublished | published `:core-<hash16>`; `core-prep` probe job |
| `ci` | — | — | published `:ci` families; built via `targets: dev ci` dedup |

Mise tiers: 4 → 5. BASE splits into **CORE** (`mise-core.toml` → `config.toml`)
+ **CPP** (`config.cpp.toml`, `MISE_ENV=cpp`); SHARED, RUNTIME, OVERLAY
unchanged; heavy chain runs `MISE_ENV=cpp` (stage: base) then `cpp,runtime`
(stage: runtime). Probe the three-tier `[settings]`/`[env]` merge order
empirically before committing (use-tool-builtins rule 4).

## Refuted / unverified claims

Judged by 3-vote adversarial verification; these must NOT be asserted as true:

1. **REFUTED (0/3): "The base toolset layer accounts for ~4.83 GB of a
   5.06 GB (compressed) image — the mise base tier dominates rather than the
   p2996 payload."** The figures appear nowhere in the repo; the same-day
   angle work confirms no committed per-layer breakdown exists; the 5.06 GB
   compressed total conflicts with the ~38 GB doc figure with no source for
   the implied ~7.5× ratio; and the arithmetic strains (leaves ~230 MB for
   gcc-latest + p2996 + the runtime tier). The *directional* half (p2996's
   ~500 MB does not dominate) is plausible but unquantified. Resolve by
   pulling the `devcontainer-metrics` / dive artifact from image-analysis run
   29013595948 (artifact 8197088598, expires 2026-10-07).
2. **REFUTED (0/3): "Running CI lint/test jobs inside a prebuilt container
   image is faster end-to-end than cached mise-on-runner installs."**
   Contradicted by the repo's own telemetry (lint 45-48 s total incl. 20-25 s
   install) vs per-job container pulls with no hosted-runner image caching;
   at best the claim could hold on a cold cache miss, not steady state.
3. **Unverified/unmeasured (flagged, not refuted):** the ~1-2.5 GB lean-leaf
   size estimate (rests on the stale 2026-03 1.33 GB benchmark + tool-count
   reasoning); true-cold full mise install time (est. 3-8 min, bounded by
   `timeout-minutes: 15`); web-session GHCR pull throughput (the deciding
   unknown for even a lean sidecar within the ~5-min setup budget); whether
   smoke-test's 5m40s free-disk step is still needed (the analyze job pulled
   ~37.6 GB with no free-disk step and succeeded — cheap to A/B); GHCR
   package visibility (anonymous fetch 404/401 → likely private; a web
   `docker pull` would need a PAT in plain-text env, one more friction).

## Open questions for Ray (with recommended answers)

1. **Adopt the Phase 0 core/cpp split now, before any second image?**
   *Recommended: yes.* One ~25-min cold base build buys cache granularity
   (conda/runtime bumps stop busting the lean core layers), a pre-wired fork
   seam, and full reversibility. It is the only part of the topology work
   that is valuable under every future (one image, two images, or web-only
   setup scripts).
2. **What trigger publishes the `:ci` leaf (Phase 1)?** *Recommended:
   publish only when a concrete consumer lands* — either (a) you adopt a web
   docker-compose sidecar workflow that demonstrably beats the setup-script
   + mise path for your sessions, or (b) Anthropic ships custom base images
   for web (docs say "not yet supported"; watch anthropics/claude-code
   #29515 — carried from the Run A brief, not independently verified). Until
   then the leaf has no load-bearing consumer: CI is settled by Q2, and web
   is served by setup script + snapshot.
3. **Web bootstrap: setup script installing mise + shared.toml, or a lean
   sidecar image?** *Recommended: setup script + SessionStart background
   warm, snapshot-cached.* The web VM already carries most of the lean
   toolchain; a sidecar isn't the session environment (docker-exec wrapping
   nothing in the repo supports). This is Run A's domain — align the final
   call with its report.
4. **Should the ~38 GB doc figure be replaced with a measured, dated
   number?** *Recommended: yes, cheap follow-up.* Pull the run-29013595948
   metrics artifact in a shell-enabled session; record compressed +
   extracted sizes and the per-tier breakdown (also settles refuted claim 1
   properly, and informs whether smoke-test's free-disk step can go).
5. **Trim lint's runner install?** *Recommended: optional micro-win, not
   now.* An `install_args`/`MISE_ENV`-scoped lint subset would shave part of
   a 22-25 s step; defer unless CI latency starts to matter.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — all repo-grounded facts (Dockerfile, docker-bake.hcl, mise tiers, P2996-CACHE.md, ci.yml, build-publish.yml, image-analysis.yml, p2996_hash.py, ghcr_cleanup.py, smoke script, rules) + Actions API timings (runs 29043090828, 29011164725, 29013595948, 28970137705, 28965970048, 28974425699).
- [jdx/mise](https://github.com/jdx/mise) — config environments / MISE_ENV lists / per-env locks; CI + Docker cookbook guidance (local mintlify cache).
- [jdx/mise-action](https://github.com/jdx/mise-action) — cache mechanism, key template, install_args behavior (local mintlify cache).
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — official web docs (code.claude.com/docs/en/claude-code-on-the-web): base-image, resource ceilings, setup script/snapshot, in-session Docker.
- [devcontainers/images](https://github.com/devcontainers/images) — image-family layout, base/language/universal decision guide, manifest.json parent/versioning, tag discipline.
- [devcontainers/cli](https://github.com/devcontainers/cli) — `--prebuild` semantics (local mintlify cache).
- [devcontainers/spec](https://github.com/devcontainers/spec) — onCreateCommand prebuild semantics (local mintlify cache).
- [devcontainers/ci](https://github.com/devcontainers/ci) — configFile/imageName/cacheFrom/push action inputs.
- [docker/buildx](https://github.com/docker/buildx) — bake target dedup / shared-stage attribution (issues #3312, #1064, #1377).
- [docker/docs](https://github.com/docker/docs) — bake targets/contexts pages; gha cache backend scope (docs.docker.com).
- [github/docs](https://github.com/github/docs) — runner specs, container-job mechanics, Codespaces prebuilds, Actions/Packages billing (docs.github.com).
- [actions/runner-images](https://github.com/actions/runner-images) — >50 GB preinstalled VM-image delivery model.
- [jlumbroso/free-disk-space](https://github.com/jlumbroso/free-disk-space) — measured 5m40s disk-freeing cost in the build job.
- [community/community](https://github.com/orgs/community/discussions/173607) — GHCR degradation evidence; also discussions #27080, #25975, #47550 (Initialize-containers cost, no hosted-runner image cache).
- [NixOS/nixpkgs](https://github.com/NixOS/nixpkgs) — dockerTools layered-image byte-sharing mechanics (grahamc post; PRs #47411, #91084).
- [containerd/stargz-snapshotter](https://github.com/containerd/stargz-snapshotter) — lazy-pull background for the giant-image delivery survey.
