# Deep Research — CI/CD + Devcontainer Image Pipeline Optimization

**Date:** 2026-07-11 · **Repo:** ray-manaloto/dotfiles · **Status:** proposal-only
(no GitHub issues mutated, no PRs opened — awaiting Ray's approval).

**Method:** Two parallel lanes. (1) A deep-research web harness — 6 search
angles → 28 sources fetched → 126 claims extracted → 25 adversarially verified
(3-vote, need 2/3 to refute) → **24 confirmed, 1 refuted**. (2) A read-only
repo-surface map (`agents/repo-surface-map.md`). Every external claim below
carries a citation; every repo claim carries a `file:line`.

> **Headline (read this first).** Two of Ray's explicit requests are, on the
> evidence, the *wrong* levers — and I owe him the citations rather than
> silent compliance:
> 1. **Squash + upload-both is counterproductive** and should be dropped
>    (experimental, removed from BuildKit, destroys layer sharing + cache +
>    parallel-download). §Q2.
> 2. **eStargz/SOCI lazy-pull does NOT speed up the primary consumer** — the
>    Mac's Docker Desktop `mise run sync` — because *Docker does not lazy-pull
>    eStargz*. It only helps containerd-based Linux consumers. §Q2.
>
> And one premise is already ~80% satisfied: **most of `verify-local` is
> already automated** in CI's `smoke-test` job on a Linux amd64 runner; the
> genuine Mac-only residual is the SSH-agent-forwarding R1/R2 path. §Q1.

---

## Q1 — Automating the local macOS validation via GHA

### Verified feasibility (primary-source deep-check, 2026-07-12)

Refined from the harness synthesis after Ray asked for the actual GitHub docs +
runner-image README. Precise finding — **arch matters**:

- **arm64 (Apple Silicon) hosted macOS runners — Docker cannot work.** GitHub
  docs, *Limitations for arm64 macOS runners*: *"Nested-virtualization is not
  supported due to the limitation of Apple's Virtualization Framework."* The
  `macos-26-arm64` runner-image README ships **no** Docker/colima/lima/qemu/podman
  (only Xcode + Android simulators). The `setup-docker-macos-action` README
  confirms the consequence: *"arm64 processors (M-series)… are unsupported. These
  processors do not support nested virtualization. This means Colima can't start
  the VM to run Docker… The M1 processor there is no hope."*
- **Intel (x86) hosted macOS runners — Docker CAN be installed.** `macos-15-intel`
  and `macos-26-intel` are **not** deprecated (only `macos-14` is), and the action
  supports `macos-15-intel`; on Intel, colima starts a Linux VM and `docker` works,
  so it *could* pull the amd64 image.

**But Intel-macOS is still the wrong tool** — it runs **colima, not Docker
Desktop**, so it *still* cannot do R2 (`/run/host-services/ssh-auth.sock` is a
Docker-Desktop-only socket; colima lacks it — issue #78); it costs ~10× a Linux
runner, is slower/flakier, and a **Linux runner does the identical
container-internal validation natively**. The only thing *any* macOS runner adds
over Linux is testing macOS-*host*-specific behavior (host SSH-proxy spawn) —
which doesn't need Docker, and Docker-Desktop R2 can only be faithfully tested on
the actual Mac.

→ **Decision (Ray, 2026-07-12): Linux runner.** Automate all container-internal
validation on a cheap Linux runner; R1/R2/persistence stay a local gate. No macOS
runner (hosted or self-hosted); Intel-macOS rejected on the cost/fidelity grounds
above.

Sources: [arm64 macOS limitations](https://docs.github.com/en/actions/reference/runners/github-hosted-runners#limitations-for-arm64-macos-runners),
[macos-26-arm64 README](https://github.com/actions/runner-images/blob/main/images/macos/macos-26-arm64-Readme.md),
[setup-docker-macos-action](https://github.com/douglascamata/setup-docker-macos-action),
[runner-images README](https://github.com/actions/runner-images/blob/main/README.md),
community #25777, runner-images #8104, colima #970.

### The critical reframe: most of `verify-local` is ALREADY in CI

`verify-local` (`mise.toml:543-565`) is a sequential chain of 8 Docker-dependent
steps. But **Linux GHA runners have Docker + amd64**, and CI's `smoke-test` job
(`build-publish.yml:617-706`) already builds and smoke-tests the `:sha` image on
`ubuntu-latest`. **Corrected against a direct read of CI's `build_smoke_script`
(`image.py:236-499`, verified by the devil's-advocate pass** — the two smoke
paths are genuinely different code): CI smoke runs **tool/identity/hk + the
sanitizer & reflection-compiler tier**, but does **NOT** run pytest, mount
checks, the Doppler secret-canary, R1 (`ssh -p 4444`), or R2
(`ssh -T git@github.com`). Coverage actually splits like this:

| verify-local surface | Runs in CI today? | Home |
|---|---|---|
| `lint`, `test`, `verify run`, `pin-actions`, `lint-docs` (pure-Linux gates) | **Yes** — CI `lint` + `contract-preflight` (`ci.yml:71-182`) | ubuntu-latest ✅ |
| build + tool/identity/hk + **sanitizer/reflection-compiler** checks | **Yes** — CI `smoke-test` (`image.py:236-499`) | ubuntu-latest ✅ |
| `verify-arch` / R3 (amd64) | **Yes** — CI runs on amd64 | ubuntu-latest ✅ |
| pytest-in-container, mount checks, **Doppler secret-canary** | **No** — run **nowhere** in CI | Mac-local ❌ |
| R1 (`ssh -p 4444`), **tier-3 R2** (`ssh -T git@github.com` via `/run/host-services/ssh-auth.sock`), `persistence` stop/up | **No** — needs Docker-Desktop magic socket | **Mac-only** ❌ |

**So the incremental "automate more via GHA" win is small and expensive.** The
Docker-Desktop-socket residual (R1/R2/persistence) is precisely why hosted
runners (no Docker) and even Colima (no such socket, issue #78) can't host it —
automating those needs a maintained **self-hosted macOS runner** (untrusted-PR
security surface, secrets exposure, upkeep). The *cheaper* gap is the
mount/secret-canary/pytest-in-container checks that run nowhere in CI — those
**could** move to the Linux `smoke-test` job with modest work (no magic socket
needed), which is a better first target than the runner.

### Recommendation (Q1)

1. **Do NOT stand up a self-hosted macOS runner yet.** The R1/R2/persistence
   residual is a narrow, rarely-regressing surface; the runner's security +
   maintenance cost outweighs catching those regressions marginally sooner.
   Keep R1/R2/persistence in the local `verify-local` gate (it already runs on
   `mise run land`).
2. **Close the "two smoke scripts" gap first (modularity).** Unify
   `scripts/devcontainer-smoke.sh` and `image.py`'s `build_smoke_script` behind
   one shared implementation with a tier flag, so local and CI run *identical*
   assertions (minus the DD-socket-dependent R1/R2 on Linux). This is the real
   "modular shared local↔CI scripts, no duplication" win Ray asked for — and it
   directly surfaces the coverage gaps below.
3. **Move the cheap CI gaps onto the Linux `smoke-test` job**: pytest-in-container,
   mount checks, and the Doppler **secret-canary** run *nowhere* in CI today
   (verified) yet need no magic socket. Adding them catches those regressions in
   CI without a Mac runner — a better first target than C3.
4. **Document CI-vs-local tier coverage** so the Mac-only residual is visible and
   intentional, not accidental.
5. **Revisit self-hosted Mac runner only if** the SSH path starts regressing
   often (track frequency). Decision, not default.

---

## Q2 — Image size / pull-speed optimization

**Primary objective (Ray):** faster devcontainer `mise run sync`/`dev-rebuild`
pulls AND faster event-triggered GHA workflows that pull the image.

### Where the bulk is (~38 GB uncompressed)

Base tier: `mise install` of 36 tools, **25 on the `conda:` backend** (heavy
clang/llvm toolchain + the ~20-30 min conda-solve), + cargo crates + rust
toolchains; then `/opt/clang-p2996` (from-source clang+libc++), `/opt/gcc-latest`,
+ 23 runtime tools (`repo-surface-map.md` §Q2; `build-publish.yml:632`).

### Squash: REJECT (contra Ray's explicit request — with evidence)

**CONFIRMED (high, 3-0).** Docker CLI docs (verbatim): `--squash` *"is an
experimental feature and should not be considered stable"*; a squashed image
*"can't take advantage of layer sharing with other images, and may use
significantly more space"*; *"a single layer takes longer to extract, and you
can't parallelize downloading a single layer."* 2026 sources confirm **BuildKit
removed `--squash` entirely** and recommends multi-stage instead (buildkit
[#6062](https://github.com/moby/buildkit/issues/6062), buildx
[#1287](https://github.com/docker/buildx/issues/1287),
[Docker CLI docs](https://docs.docker.com/reference/cli/docker/build-legacy/)).

For *this* pipeline squash is doubly wrong: it collapses exactly the
`base`/`p2996`/`dev` cache boundaries that make warm builds a thin pull
(~10 min vs ~2.5 h cold), and a single layer defeats parallel-stream download —
**hurting** the pull speed it was meant to help. **Uploading both squashed and
non-squashed** doubles ~38 GB of registry storage for a negative-value artifact.
→ Drop both the squash step and the dual-upload.

### Lazy-pull (eStargz/SOCI): real, OCI-compatible — but WON'T help the Mac

**CONFIRMED (high, 3-0):** eStargz is *"compatible to OCI/Docker images so this
can be pushed to standard container registries (e.g. ghcr.io) … still runnable
even on eStargz-agnostic runtimes including Docker"*
([containerd/stargz-snapshotter](https://github.com/containerd/stargz-snapshotter)).
A container can *"run without waiting for the pull completion … necessary chunks
fetched on-demand"* — image pull is ~76% of startup while only ~6.4% of data is
read at startup (Slacker, USENIX FAST '16). Benchmarks (CHEP 2024, PSI+CERN):
python:3.9 OverlayFS 375 MB/16 s vs Stargz 8 MB/2 s vs SOCI 45 MB/3 s — ~5× faster,
>8× less data
([paper](https://indico.cern.ch/event/1338689/papers/6011588/files/14858-20250227_CHEP_2024_Efficient_and_fast_container_execution_using_image_snapshotters.pdf)).

**The landmine (honest scope):** the benefit requires the *consumer* to run a
lazy-pull snapshotter (containerd stargz-snapshotter or the SOCI snapshotter).
**Docker does not lazy-pull eStargz** (confirmed in the same source). The primary
consumer — `mise run sync` on the Mac via **Docker Desktop** — will therefore
pull an eStargz image *eagerly, in full*, with **zero lazy-pull benefit**. The
benchmark numbers also come from lightweight images on a same-network registry;
**no source benchmarked a ~38 GB image over ghcr.io from a slow link**, and
read-heavy workloads erased the savings entirely. So the magnitude for *this*
pipeline is extrapolated, not measured.

Where lazy-pull *would* pay off in theory: Linux consumers running containerd +
SOCI/stargz. **But the DA pass verified this pipeline has none** — both CI
image-fetches (`build-publish.yml:663`, `image-analysis.yml:85`) use the Docker
daemon's plain `docker pull` (no lazy-pull), and Dive deliberately reads every
layer. So SOCI/eStargz help **no consumer here** — the SOCI-POC idea is killed
(see Recommendation). (`SOCI` would otherwise be the lower-risk option — a
separate index artifact, no rebuild — but "lower-risk zero" is still zero.)

### zstd / OCI media types: the ONE lever that helps every consumer

**CONFIRMED (high, 3-0, date-corrected):** BuildKit **v0.31.0 (June 17, 2025)**
makes all image results default to OCI media types (`oci-mediatypes=false` for
legacy) — the **prerequisite for zstd layer output**
([moby/buildkit releases](https://github.com/moby/buildkit/releases)). zstd
compresses better and decompresses faster than gzip, and — unlike lazy-pull —
**shrinks the bytes every consumer transfers on a normal `docker pull`.**

**Devil's-advocate correction (important):** the DA pass verified that the only
full-image fetches in the whole pipeline are **plain `docker pull`** —
`build-publish.yml:663` (smoke-test) and `image-analysis.yml:85` (Dive/Trivy) —
plus Docker Desktop on the Mac. None use a lazy-pull snapshotter. So zstd is
**universal** (Mac + both CI jobs benefit), and — the flip side — **SOCI/eStargz
help NOBODY here** (see below). This turns "two uncertain levers" into "one lever
helps everyone, delete the other." (Confirm Docker Desktop's version pulls zstd —
recent DD does; verify on Ray's machine before flipping.)

### The warm-path reality: the Mac rarely pulls real bytes at all

The DA pass reinforced a structural point: push-to-main **skips the build** and
`promote` (`ci.yml:328`) retags the PR's `:pr-NNN` → `:dev` via `imagetools
create` — a manifest retag, no new bytes — and only on **build-relevant** merges.
So on the common case `mise run sync` on a warm cache pulls **nothing new**; the
Mac transfers real bytes only when image *content* actually changes (rare). **This
means the Mac-side pull-speed "problem" is largely illusory for the common case**,
and image-optimization effort should be justified by measuring *cold /
content-change* pulls, not assumed.

### Recommendation (Q2), in priority order

1. **zstd + OCI media types** on the published targets (BuildKit ≥0.31, already
   available). Universal win (Mac + both CI jobs). Gate only on a quick
   **compatibility probe** (does DD/ghcr round-trip a zstd layer?) — *not* on #17
   metrics.
2. **Reject squash + dual-upload** (evidence above).
3. **Layer-restructuring / multi-stage pruning** as the durable size lever
   (BuildKit's recommended squash alternative). **Biggest byte target (DA-surfaced):
   the image ships THREE C++ toolchains** — conda clang/llvm + from-source
   clang-p2996 + gcc-latest — plausibly the largest single win; ties into #22
   (drop `conda:graphviz`) and #167 (mise OCI one-layer-per-tool, experimental —
   see Q5). Gate the expensive restructuring on #17 metrics.
4. ~~**POC SOCI index for Linux consumers**~~ — **KILLED by the DA pass.** Both CI
   consumers use `docker pull` (no lazy-pull), and Dive reads *every* layer by
   design — SOCI gives zero benefit on both counts. Do not POC it.
5. **Measure (#17)** to justify the *expensive* levers (rec 3) — but it does NOT
   block the cheap universal win (rec 1) or the squash rejection.

---

## Q3 — Matrix parameterization (ubuntu × arch), amd64-now / arm64-gated

**CONFIRMED (high, 3-0):** `docker-bake.hcl` supports a native `matrix`
attribute — *"a map of parameter names to lists of values"* — generating one
target per combination via name interpolation (`name = "image-${item.arch}"`),
with each target's `platforms` field driving the arch
([Docker Bake matrices](https://docs.docker.com/build/bake/matrices/)). Multiple
keys form a cross-product = exactly `(ubuntu version) × (arch)`. **CONFIRMED
(3-0):** `docker/bake-action` ships a `matrix` subaction that emits a JSON matrix
to fan out GHA jobs ([docker/bake-action](https://github.com/docker/bake-action)),
and Docker's `distribute:true` splits **one platform per runner** (mapping arm64
→ `ubuntu-24.04-arm`), which is faster than single-runner emulation
([multi-platform CI](https://docs.docker.com/build/ci/github-actions/multi-platform/)).
Native arm64 hosted runners are GA (Cobalt 100, 4 vCPU, non-emulated).

### Repo mapping (what becomes an axis)

Today `PLATFORM=linux/amd64/v2` is hardcoded in three places
(`docker-bake.hcl:19-21`, `mise.toml [tasks.up]`, `devcontainer.json`) and is a
first-class `p2996-hash`/`dev-hash` input. `BASE_IMAGE`/`BUILDER_IMAGE` carry the
ubuntu 26.04 digest. `build-publish.yml` already has a **reserved-but-unused
`platform` input** (lines 49-53) — the wiring is half-there.

**Hard arm64 blocker:** the P2996 compiler builds **X86 target only**
(`Dockerfile:280 -DLLVM_TARGETS_TO_BUILD=X86`). A real arm64 image needs
`AArch64` added (a ~2 h/arch from-source rebuild) — this is issue #166/#5's
actual gate, not the bake syntax.

### Recommendation (Q3): parameterize, one active cell

- Introduce a bake `matrix` over `{ubuntu, arch}` with a single active entry
  `{ubuntu:"26.04", arch:"amd64"}`; wire `PLATFORM`/`BASE_IMAGE` from the matrix
  item; leave arm64/24.04 as **commented/filtered axes** (documented, gated
  off).
- Thread the reserved `build-publish.yml platform` input through to bake so the
  GHA side is matrix-shaped but expands to one job today.
- **YAGNI guard + hash-pipeline hazard (DA-verified, NOT near-zero complexity):**
  `PLATFORM` is not just a build flag — it feeds **all three content hashes** via
  a shape-coupled regex (`p2996_hash.py:192-200, 328, 385, 440`). A naive bake
  refactor that moves `PLATFORM` off the top-level `variable` block **crashes the
  hash pipeline (ValueError)** or silently forces a **cold ~2.5 h rebuild**. So
  B1 is *not* free. Either **(a) defer B1 behind B3** (the p2996 AArch64 work
  that actually unblocks arm64), or **(b) ship a hash-invariance test first**
  proving the matrix refactor leaves `base/p2996/dev` hashes byte-identical for
  the amd64/26.04 cell before touching bake. Given arm64 is blocked regardless,
  **(a) defer** is the lower-risk call.

---

## Q4 — Smarter, matrix-driven validation

**CONFIRMED (high, 3-0):** `regctl`/regclient inspects manifests, lists tags,
and retrieves digests **daemonless, without privileged host access**, supports
multi-platform images and per-arch `--platform` manifest inspection
([regclient/regclient](https://github.com/regclient/regclient)). So per-variant
identity/manifest contract checks run on **cheap Linux runners with no Docker
daemon**.

### Recommendation (Q4): tiered validation

- **Cheap tier (all variants):** `regctl manifest get --platform` +
  `dotfiles-setup image identity-expected` digest/identity assertions for every
  matrix cell — daemonless, fast, no image pull.
- **Full tier (active/amd64 cell only):** the existing `smoke-test` (build →
  pull → tiers 1-2, arch). Don't run full smoke on gated-off cells (they don't
  build).
- **Unify** the two smoke code-paths (Q1 rec #2) so a future arm64 cell reuses
  the same assertions.
- Keep `ci-gate` as the single required check (`ci.yml:295-319`) — a skipped
  gated-off variant is a valid terminal state (memory:
  `feedback_skipped_check_satisfies_required`).

---

## Q5 — Parallelize the mise-task + `dotfiles_setup` automation

Concrete candidates (from `repo-surface-map.md` §Q5, with `file:line`):

1. ~~**`verify.py:489`**~~ — **KILLED by the DA pass.** The map called this the
   "top candidate"; the DA verified it is the **worst**. `suites.toml` has **90
   suites, all pure in-memory file-read/regex handlers** (57 `require_tokens`,
   16 `forbid_tokens`, …) with **no subprocess**. That work is GIL-bound → a
   `ThreadPool` runs it **slower**, and a `ProcessPool` is overhead-dominated on
   sub-millisecond file reads, while interleaved output wrecks CI error
   attribution. Do **not** parallelize it. (If `verify run` is ever slow, the fix
   is caching file reads across suites, not threads.)
2. **`pr.py:265-275`** — `run_gates` runs lint/test/verify/sync **sequentially,
   stop-on-first-fail**. These *are* real subprocesses (not GIL-bound), so
   fanning out the common all-green path is genuine wall-clock. *Tradeoff:*
   fail-fast is a *feature* — a thread pool with ordered collection + "cancel
   remaining on first failure" preserves it while overlapping green runs. The
   **best-value Q5 candidate**, but conditional on the all-green path being a
   meaningful fraction of ship time (lint alone is ~minutes).
3. **`image.py` smoke/benchmark** — one `docker run` per image; a multi-variant
   matrix would loop images serially. Parallelize **per-variant** smoke *only
   when the matrix actually grows past one cell* (Q3). Not now.

Skip: `p2996_hash.py` per-COPY-input hashing (small files), `container.py:182`
advisory loop, `image.py:157-162` in-memory dict loop, `size_report`
(`image.py:681-697`) `docker history` parse — all low-value in-memory work.

### Recommendation (Q5)

- **Do NOT parallelize `verify.py`** (GIL-bound regex, would regress).
- Parallelize `run_gates` with preserved fail-fast — **only if** a baseline shows
  the all-green ship path is a meaningful fraction of time (subprocess-bound, so
  a `ThreadPoolExecutor` *does* help here, unlike verify.py).
- Defer image/smoke parallelization until the Q3 matrix has >1 cell.
- **Net:** Q5's realistic surface is one conditional win (`run_gates`), not the
  three the map suggested. Low priority.

---

## Q6 — Reorganized backlog (proposal — no issues mutated)

Regroup the open CI/CD-and-image issues under the new goal. **Measurement is the
prerequisite gate for the optimization epics.**

### P0 — cheap universal wins (NO metrics dependency)
- **A1** zstd + OCI media types (BuildKit ≥0.31) — universal (Mac + both CI
  `docker pull` jobs). Gate only on a zstd compatibility probe.
- **C1** unify the two smoke code-paths (shared local↔CI). No metrics needed.
- **#17** build-metrics collection (image size / tool count / build time) — land
  it here too; it *gates the expensive levers* (A3/B3), not the cheap ones.

### Epic A — Image pull-speed & size (NEW; folds Q2)
- **A1** (see P0) zstd + OCI media types. *Only universal pull-speed lever.*
- **A3** layer-restructuring / multi-stage pruning (BuildKit's squash
  alternative). **Biggest target: the THREE C++ toolchains** (conda clang/llvm +
  clang-p2996 + gcc-latest); overlaps **#22** (drop `conda:graphviz`), **#167**
  (mise OCI per-tool layers — experimental, watch). *Gate on #17 metrics.*
- **A4** ~~squash + dual-upload~~ **REJECTED** (evidence in §Q2) — close the idea.
- **A5** ~~SOCI index POC~~ **KILLED** (DA-verified: no lazy-pull consumer exists;
  Dive reads every layer) — do not pursue.

### Epic B — Matrix-readiness (folds #166 #102 #5 #101; Q3/Q4)
- **B1** parameterize bake+GHA to matrix shape, amd64/26.04 active, arm64/other
  gated (Q3).
- **B2** regctl daemonless per-variant validation + unify smoke paths (Q4;
  overlaps Q1 rec #2).
- **B3 (blocked)** p2996 AArch64 target for real arm64 — the true gate on
  **#5/#102/#166**; ~2 h/arch rebuild. Depends on **#82** (ccache/sccache) to
  make per-arch rebuilds affordable.
- **#101** lint matrix `[ubuntu, macos]` — cheap; catches host-specific lint
  breakage (the agnix CI-red motivation).

### Epic C — Gate automation & modularity (NEW; folds Q1)
- **C1** unify the two smoke code-paths (shared local↔CI, tier flag). *The real
  "no duplication" win.*
- **C2** document CI-vs-local tier coverage (which R runs where).
- **C3 (deferred, decision-gated)** self-hosted macOS runner for R1/R2/persistence
  — **recommend NOT now** (small win, high cost/security). Track SSH-path
  regression frequency; revisit if it climbs.

### Epic D — Automation-library speedups (NEW; folds Q5) — LOW PRIORITY
- **D1** ~~parallelize `verify.py`~~ **KILLED** (DA-verified: 90 GIL-bound
  in-memory regex suites → pool runs slower).
- **D2** parallelize `run_gates` with fail-fast preserved — the only viable Q5
  win (subprocess-bound); conditional on the all-green ship path being slow
  enough to matter.

### Independent / housekeeping (unchanged priority)
- **#92** Trivy gate flip (after baseline cleanup); **#81** GCC version tracking
  (partially done via sha256 pin); **#104** slim lint mise install; **#20**
  restore cppclean; **#33** bun PATH warning; **#75** attestation-provenance
  fresh-clone; **#74** R1/R2/R3 doc-presence contract; **#72** drop `mise doctor
  || true`.

### Suggested sequence (DA-corrected — cheap wins do NOT wait on metrics)
**Wave 1 (parallel, no dependencies):** `A1 (zstd, after a compat probe)` ∥
`C1 (unify smoke)` ∥ `#17 (metrics)` ∥ move the pytest/mount/secret-canary CI
gaps onto Linux `smoke-test` (Q1 rec 3).
**Wave 2 (after #17 metrics exist):** `A3 (toolchain/layer restructuring —
justified by measured cold-pull cost)`.
**Wave 3 (deferred/blocked):** `B3 (p2996 AArch64)` unblocks `B1 (matrix
scaffold)` and `#5/#102/#166`; `D2 (run_gates)` only if ship-path timing warrants.
**Never:** squash+dual-upload (A4), SOCI POC (A5), verify.py parallelization (D1).

---

## Devil's advocate / adversarial review

The strongest arguments *against* this plan (pressure-test before committing):

1. **The whole macOS-automation premise may not be worth acting on.** If CI's
   `smoke-test` already covers tiers 1-2 + arch on Linux, the only thing a
   self-hosted Mac runner adds is R1/R2/persistence — a narrow surface that
   rarely regresses. Building CI infra to catch it "sooner" may never pay back.
   *Mitigation:* Epic C3 is explicitly deferred/decision-gated, not built.
2. **Q2's primary objective might be unserved by every proposed lever.** Mac
   Docker Desktop won't lazy-pull (kills SOCI/eStargz for the Mac); zstd helps
   but the warm-path sync is *already* a thin-overlay pull (the heavy base/p2996
   layers are cache-reused, not re-pulled). If sync is already fast on a warm
   cache, the real Mac win may be **near zero** and the effort belongs on the
   *Linux event-triggered* consumers instead. *This is the biggest open risk —
   #17 measurement must confirm there's a Mac-side problem at all before Epic A
   spends effort there.*
3. **Matrix scaffolding is YAGNI** while arm64 is blocked on the p2996 AArch64
   rebuild. Wiring a one-cell matrix adds config surface (and hash-input
   complexity — PLATFORM feeds the content-hash) for capability that can't ship
   until B3. *Mitigation:* keep B1 truly minimal or defer it behind B3.
4. **Parallelizing verify/gates may be a micro-optimization** that trades
   fail-fast clarity + clean logs for sub-second gains on fast file-read suites.
   *Mitigation:* D1/D2 are explicitly baseline-gated.
5. **zstd consumer-support risk:** confirm Ray's Docker Desktop version pulls
   zstd layers (and that ghcr serves them) before flipping — a mismatch could
   break `sync` for a marginal size win.
6. **Refuted claim discipline:** the assertion that mise 2026.7.1 shipped native
   OCI build normalizing apt/dpkg state (#167 territory) was **REFUTED (1-2)** —
   do NOT rely on mise OCI build for reproducible apt layers; its confirmed
   facts are limited to per-tool layering + experimental cross-platform breakage
   (§Q5, mise-oci docs).

### Independent devil's-advocate agent pass (verified against repo source)

A dedicated adversarial agent red-teamed the plan against the actual code
(`agents/devils-advocate.md`). It **killed 2 recommendations, corrected 1
misrouting, and weakened 2** — all folded into the sections above:

| Recommendation | Verdict | Why |
|---|---|---|
| A5 SOCI-POC (Linux consumers) | **KILLED** | Only image-fetches are `docker pull` (`build-publish.yml:663`, `image-analysis.yml:85`); no lazy-pull consumer; Dive reads every layer. Zero benefit. |
| D1 parallelize `verify.py:489` | **KILLED** | 90 pure in-memory regex suites, GIL-bound → pool runs *slower*, not faster. The map's "top candidate" is actually the worst. |
| A1 zstd framing ("Mac-only") | **CORRECTED** | All consumers `docker pull` → zstd helps Mac **and** both CI jobs. One universal lever; SOCI helps no one. |
| B1 one-cell matrix ("near-zero complexity") | **WEAKENED** | `PLATFORM` feeds all 3 content-hashes via shape-coupled regex (`p2996_hash.py:192-200,328,385,440`); naive refactor crashes the hash pipeline or forces a cold ~2.5 h rebuild. Defer behind B3. |
| "#17 blocks everything" sequencing | **WEAKENED** | C1 + the zstd compat-probe have zero metrics dependency; #17 gates only the *expensive* levers (A3). Cheap wins run in Wave 1. |
| Q1 coverage table | **CORRECTED** | CI smoke runs no pytest/mounts/secret-canary/R2; it *does* run sanitizers. 3 rows re-mapped; the "defer Mac runner" conclusion survives. |

**Survives intact:** squash rejection; C1 unify-smoke; the "warm sync is a
no-op / Mac pulls real bytes only on rare content changes" insight (reinforced:
`ci.yml:328` promote-retags only on build-relevant merges).

**New lever the plan under-sold:** the image ships **three C++ toolchains** —
the plausibly-largest byte win, now called out explicitly in A3.

---

## Open questions for Ray

1. **Q2 acceptance:** OK to **drop squash + dual-upload** AND **drop the SOCI
   idea** entirely (both evidenced as zero/negative value), and pivot to **zstd
   now** (universal) + toolchain/layer restructuring (metrics-gated)? (§Q2)
2. **Mac problem exists?** Is `mise run sync` on a *warm* cache actually slow
   today, or is the pull-speed pain specifically the *cold*/event-triggered
   Linux workflows? This decides whether Epic A targets the Mac or Linux. (§Q2,
   Adversarial #2)
3. **Self-hosted Mac runner:** confirm **defer** (Epic C3) vs build now?
4. **Matrix now vs after arm64 unblocks:** wire the one-cell scaffold now (B1),
   or defer until B3 (p2996 AArch64) is real? (Adversarial #3)

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under study (files + issues).
- [actions/runner-images](https://github.com/actions/runner-images) — #8104 colima/QMP breakage; macos-26-arm64 README (no Docker); README image/deprecation status.
- [douglascamata/setup-docker-macos-action](https://github.com/douglascamata/setup-docker-macos-action) — arm64-unsupported (no nested virt); Intel-only Docker-on-macOS.
- [abiosoft/colima](https://github.com/abiosoft/colima) — #970 HV_UNSUPPORTED (no nested virt on M-series runners); FAQ.
- [containerd/stargz-snapshotter](https://github.com/containerd/stargz-snapshotter) — eStargz OCI/ghcr compatibility + lazy-pull mechanics.
- [moby/buildkit](https://github.com/moby/buildkit) — v0.31.0 OCI-media-types default (zstd prerequisite); #6062 squash-not-implemented.
- [moby/moby](https://github.com/moby/moby) — #34565 squash layer-sharing loss.
- [docker/buildx](https://github.com/docker/buildx) — #1287 squash removal; default build concurrency.
- [docker/bake-action](https://github.com/docker/bake-action) — `matrix` subaction for GHA fan-out.
- [regclient/regclient](https://github.com/regclient/regclient) — daemonless per-variant manifest/digest inspection.
- [jdx/mise](https://github.com/jdx/mise) — mise OCI build docs + CHANGELOG (per-tool layering; #10731 refuted claim).
- [containers/build (docs.docker.com)](https://docs.docker.com) — Bake matrices, multi-platform CI, squash CLI legacy docs.
- [CHEP 2024 / CERN indico](https://indico.cern.ch/event/1338689/) — lazy-pull snapshotter benchmarks.
