# Run B / Angle 1 — Today's stage graph + size distribution (repo-grounded)

Date: 2026-07-09. Produced in the remote research container (Bash unavailable —
every fact below is from Read/Grep of the working tree at `main`; **no docker
measurement was possible**. Every size figure is doc-derived and marked as such.)

## Findings

### F1. The Dockerfile is FIVE stages in one file, with two hash-sentinel regions

`.devcontainer/Dockerfile` (single multi-stage file, `syntax=docker/dockerfile:1.7`, `check=error=true`):

| # | Stage | FROM | Contents | Evidence |
|---|-------|------|----------|----------|
| 1 | `devcontainer-base` | `${BASE_IMAGE}` = `ubuntu:26.04@sha256:b7f4…` (digest-pinned) | apt seed (curl+ca-certs only), mise installer pinned `MISE_VERSION=2026.7.2`, COPY `mise-system.toml`→`/usr/local/share/mise/config.toml` + `mise-system.lock`→`mise.lock` + `shared.toml`→`conf.d/`, `mise bootstrap packages apply` (apt set), `mise install --system --locked`, hk configs to `/etc/hk/` | Dockerfile:14,33,115-116,127-139,152-155,171-188,202-203 |
| 2 | `clang-builder-cold` | `${BUILDER_IMAGE}` (separate rarely-bumped ubuntu digest; NOT Renovate-tracked) | own apt compile toolchain, shallow-fetch bloomberg/clang-p2996 at `CLANG_P2996_REF`, cmake+ninja build to `/opt/clang-p2996` (X86 only, ccache cache mount), reflection smoke | Dockerfile:224-303 |
| 3 | `p2996-export` | `scratch` | just `COPY --from=clang-builder-cold /opt/clang-p2996` — the pushable cache artifact | Dockerfile:307-308 |
| 4 | `devcontainer` | `devcontainer-base` (stage 1) | gcc-latest .deb (jwakely trunk snapshot, sha256-pinned locally, → `/opt/gcc-latest`), `COPY --from=p2996-export`, PATH wiring, two reflection smokes | Dockerfile:319-376 |
| 5 | `devcontainer-runtime` | `devcontainer` (stage 4) | `ENV MISE_ENV=runtime`, COPY `mise-runtime.toml`→`config.runtime.toml` + `mise-runtime.lock`, second `mise install --system --locked` | Dockerfile:386-409 |

**Stage 5 is what ships**: bake `target "dev" { target = "devcontainer-runtime" }`
(docker-bake.hcl:77-87). Two sentinel regions bound the content-hash inputs:
`BASE_HASH_BEGIN/END` wraps stage 1 (Dockerfile:32,211); `P2996_HASH_BEGIN/END`
wraps stages 2-3 (Dockerfile:213,310). Stages 4-5 sit *outside* both sentinel
regions and are covered only by the dev-hash's whole-Dockerfile digest (F4).

Since #160 T11 the builder is **fully decoupled** from devcontainer-base
(Dockerfile:16-23, 224): base edits never trigger the ~2h compiler rebuild, and
`p2996-prep` runs in parallel with `base-prep` (docker-bake.hcl:35-43;
build-publish.yml:188-196).

### F2. Bake targets: 5 real targets, only `dev`/`base`/`p2996-cache` are published

`docker-bake.hcl`:

- `dev` (:77) → stage `devcontainer-runtime`; gha cache `scope=dotfiles-dev`
  mode=max; provenance mode=max + SBOM attestations (:89-102). Cold path builds
  local stages; warm CI injects named contexts (F3).
- `base` (:122) → stage `devcontainer-base`, tagged `:base-<hash16>`.
  **Deliberately NO `type=gha` cache** — a mode=max gha export of this stage's
  layers exceeded the 1-hour Azure SAS token TTL ("one layer alone took
  ~3600s") and broke base-prep; the registry tag IS the durable cache
  (docker-bake.hcl:114-121).
- `p2996-cache` (:146) → stage `p2996-export`, tagged `:p2996-<hash16>`; same
  no-gha reasoning (:143-145).
- `dev-load` (:163) — local-only `output=type=docker` variant (CI-only rule
  forbids running it locally anyway — AGENTS.md "Do not").
- `validate` (:170) — `call = "check"` dry run. Plus `help` introspection and
  a `docker-metadata-action` tag stub CI overrides (:53-57).

Variables: `IMAGE_REF` consolidates `ghcr.io/ray-manaloto/dotfiles-devcontainer`
(:11-13); `PLATFORM = linux/amd64/v2` (:19-21) — a hash input for all three
hashes; `BASE_IMAGE` and `BUILDER_IMAGE` both currently the same ubuntu:26.04
digest but deliberately separate variables with different bump cadence.

### F3. Cache strategy: three-tier content-hash probe → digest-pinned named build contexts

The warm path is **not** BuildKit layer caching for the heavy tiers — it is
registry-manifest probing plus stage substitution:

1. **base-prep** (build-publish.yml:82-187): `dotfiles-setup base-hash` →
   `docker manifest inspect ghcr.io/…:base-<hash16>`. Hit → <30s; miss → bake
   `base` target, push. Either way the job outputs a **digest**.
2. **p2996-prep** (:198-320): same with `p2996-hash` / `:p2996-<hash16>`; runs
   in PARALLEL with base-prep; cold compile budget `timeout-minutes: 240`
   (a 60-min ceiling once cancelled cold rebuilds — regression note :200-205).
3. **dev-prep** (:337-450, PR builds only): `dev-hash` → probe `:dev-<hash16>`,
   a "built AND smoke-validated" marker pushed only by `dev-tag` after smoke
   passes. Hit → `imagetools create` retag to `:sha`/`:pr-NNN` and **skip
   build + smoke entirely** ("~12m → ~2m", comment :329). Nightly
   (`tag_strategy == 'nightly'`) deliberately skips this probe so the nightly
   always rebuilds — it exists to catch rolling drift the hash can't see
   (gcc-latest rolling .deb) (:331-335).
4. **build** (:454-610): bake `dev` with
   `dev.contexts.devcontainer-base=docker-image://<ref>@<digest>` and
   `dev.contexts.p2996-export=docker-image://<ref>@<digest>` (:547-550) — the
   digest-pinned named contexts **override the same-named local stages**, so
   the heavy stages are never rebuilt here; BuildKit fails the solve on digest
   mismatch (exact-bytes guarantee). Provenance assertion closes the loop: the
   pushed image's SLSA materials must contain the p2996 digest (:572-588).
5. **smoke-test** (:617-706) pulls the exact `:sha` image and runs
   `dotfiles-setup image smoke` + the bootstrap-gap report; **dev-tag** (:717-779)
   then stamps `:dev-<hash>`. On merge, ci.yml `promote` (ci.yml:326-503) does a
   manifest-only retag of `:pr-NNN` → `:dev`/`:latest` — **push-to-main never
   rebuilds** (ci.yml:274 gate).

**Hash input coverage** (P2996-CACHE.md:40-77 + `python/src/dotfiles_setup/p2996_hash.py`):

- base-hash = BASE_IMAGE + PLATFORM + base-sentinel Dockerfile section +
  bytes of `mise-system.lock`, `mise-system.toml`, `hk-common.pkl`,
  `hk-image.pkl`, `shared.toml` (every base-stage COPY input; SCHEMA_VERSION=5,
  p2996_hash.py:47).
- p2996-hash = CLANG_P2996_REF + BUILDER_IMAGE + PLATFORM + p2996-sentinel
  section — independent of base since #160 T11.
- dev-hash = base_hash + p2996_hash + platform + **whole-Dockerfile digest** +
  dev bake-target digest + **mise-runtime.toml + mise-runtime.lock byte
  digests** (p2996_hash.py:137-148, 423-444).

⚠️ Topology-relevant consequence: because dev-hash folds the *whole* Dockerfile,
**any Dockerfile edit (e.g., adding a lean stage) busts the `:dev-<hash>` warm
path exactly once** but does NOT bust `:base-`/`:p2996-` unless it touches
their sentinel sections — the sentinel design (P2996-CACHE.md:75-77) means new
stages appended outside the sentinels leave the two heavy caches warm.

### F4. The four mise tool tiers and what each installs

| Tier | File | Installed where | Contents | Pinning |
|------|------|-----------------|----------|---------|
| BASE | `.devcontainer/mise-system.toml` | stage 1 (`devcontainer-base`) | 8 core runtimes at `latest` (node, bun, go, rust, zig, java, deno, ruby) + cargo-binstall + ~25 `conda:` C++ toolchain pkgs (llvm, clang, cmake, ninja, mold, gdb, lldb, valgrind, …) + bazel/sqlite/micromamba + `[bootstrap.packages]` 15 apt pkgs (mise-system.toml:19-115) | `mise-system.lock` (rattler conda sha256, linux-x64, `lockfile_platforms`), `minimum_release_age = "7d"` |
| SHARED | `.config/mise/conf.d/shared.toml` | merged into BOTH host and stage 1 | 20 exact-pinned tools: hk 1.50.0, pkl, chezmoi, python 3.14.6, uv, gitleaks, hadolint, shellcheck, shfmt, actionlint, ghalint, yamllint/-fmt, taplo, typos, jq, yq, pinact, pixi, check-jsonschema (shared.toml:20-40) | exact versions; Renovate bumps both sides together |
| RUNTIME | `.devcontainer/mise-runtime.toml` | stage 5 (`devcontainer-runtime`, `MISE_ENV=runtime`) | gh cli, fnox, bats, task, sccache, 8 pipx C++ eco tools (meson, conan, cpplint, …), AI CLIs (claude-code, gemini-cli, codex), turso/libsql (mise-runtime.toml:35-65) | `mise-runtime.lock`; `minimum_release_age_excludes` for fast AI CLIs |
| OVERLAY | `home/dot_config/mise/config.toml.tmpl` | per-user at container create (chezmoi, onCreateCommand) | interactive tools (fzf, starship, zellij, htop, …) — deliberately NOT image inputs | free on `latest` (.devcontainer/AGENTS.md tier table; mise-system.toml:83-85) |

**The documented fork seam**: "editing THIS file rebuilds only the thin runtime
stage, not the ~30-min base (nor p2996)" (mise-runtime.toml:10-12). The root
`mise.toml` (~30 host-only tools) is a separate host tier, not an image input
(ci.yml `changes` filter comment, ci.yml:187-189).

### F5. Where the bytes live — every figure is DOC-DERIVED, none measured here

| Component | Figure | Source (doc, not measurement) |
|-----------|--------|-------------------------------|
| Full `:dev` image | **~38 GB** | build-publish.yml:631 ("smoke-test docker pulls the full ~38 GB dev image"); same figure in mise.toml:230, sync.py:40,393, hook_guard.py:90, verify-before-advancing.md:67,77, devcontainer-sync SKILL:55. Ambiguity: none of these say compressed vs on-disk; the smoke comment context ("runs out of space extracting it" on a ~14 GB-free runner) implies **on-disk extracted** size |
| clang-p2996 artifact (`p2996-export`) | **~500 MB** | P2996-CACHE.md:17-18, docker-bake.hcl:137-138; "500 MB vs multi-GB with the toolchain" (P2996-CACHE.md:120-121) |
| clang builder intermediates | ~30 GB (never shipped) | build-publish.yml:479-480 ("clang-p2996 builds clang from source, ~30 GB of intermediate artifacts") |
| base stage build time | ~20-30 min cold | build-publish.yml:84-86 ("Cold base rebuild … ~20-30 min"); mise-runtime.toml:12 ("~30-min base") |
| clang-p2996 compile time | ~80-120 min cold / ~15-30 min warm ccache; "multi-hour (~2h+)" ceiling 240 min | P2996-CACHE.md:4-5; build-publish.yml:200-205 |
| npm:renovate exclusion | "~354MB-heavier" if added to image | shared.toml:17-19 (the one per-tool size figure in the repo) |
| 2026-03-29 benchmark image | 1.33 GB | docs/research/trail/findings/docker-benchmarks/{docker-desktop,colima}-2026-03-29.json:14 — **stale**: predates the current heavy toolchain; useless as a current-size datum but proof the lean core was ~1.3 GB before the C++ payload |

**No committed per-layer breakdown exists.** Dive layer analysis and
`dotfiles-setup image benchmark` (compressed size from the registry manifest)
run async in `image-analysis.yml` (:86-121) and land only as run artifacts —
not in the repo. `.dive-ci` enforces efficiency ≥0.85 / wasted ≤100 MB, so
gross duplication is bounded, meaning the ~38 GB is dominated by *real
content*, not layer waste.

**Inferred distribution** (inference, flagged): the delta from ~1.3 GB
(2026-03 lean image) to ~38 GB arrived with the base tier's 8 language
runtimes at latest (rust toolchain + java + go + zig are individually GB-scale)
plus the ~25 conda C++ packages (llvm/clang/gdb/valgrind + their conda-forge
dep trees), plus /opt/gcc-latest (a full trunk GCC install, plausibly several
GB), plus /opt/clang-p2996 (~0.5 GB doc'd). The RUNTIME tier (CLIs + pipx
tools) is plausibly the smallest image tier. **Ordering within the base tier
is not measurable from the repo — a dive artifact pull is needed to
apportion the ~36-37 GB across base-tier families.**

### F6. CI does NOT use the image for lint/test — mise-on-runner is the current CI toolchain

- `lint` job: `./.github/actions/setup-mise` with no `install_args` → installs
  every root-mise tool on the ubuntu runner under `MISE_LOCKED=1`, with
  jdx/mise-action caching keyed on `{platform}-{install_args_hash}-{file_hash}`
  (ci.yml:71-92). Runs `hk run check --all`, chezmoi gate, agnix.
- `contract-preflight`: setup-mise subset `install_args: "python uv"` then
  `dotfiles-setup verify run` (ci.yml:161-182).
- base-prep/p2996-prep/dev-prep/smoke-test/dev-tag likewise install only
  `python uv` via setup-mise (build-publish.yml:100-103, 219-222, 355-358,
  645-648, 731-734).
- The published image is touched by CI **only** in smoke-test (docker pull +
  `image smoke`) and async image-analysis. So the "CI toolchain image" of
  candidate shape (ii) does not exist today; its function is served by
  mise-on-runner + action cache. The 20-tool shared fragment already
  guarantees host/CI/image version parity (shared.toml header).

### F7. Gates that a topology change must preserve

- **`verify-container-latest`** (mise.toml:446-450): running container must
  bind-mount the live workspace AND pass `scripts/devcontainer-smoke.sh`, whose
  tier-1 identity check sha256-compares the in-image
  `/usr/local/share/mise/config.toml` against
  `dotfiles-setup image identity-expected .devcontainer/mise-system.toml`
  (merge-base blob on branches that change build inputs) — hard-fails a stale
  base (devcontainer-smoke.sh:21-43,59-60). Any split that relocates or renames
  `mise-system.toml`'s COPY destination breaks this check's expectations.
- **R1/R2/R3** devcontainer invariants (AGENTS.md success-criteria table) bind
  the *devcontainer* image: AMD64 (`PLATFORM=linux/amd64/v2` is an input to all
  three hashes), sshd feature, DD magic socket.
- **promote / ci-gate / changes path-gate** (ci.yml): `promote` retags exactly
  one `:pr-NNN` manifest; a second published image would need its own
  `:pr-NNN`-equivalent tag family and its own promote leg or a manifest-list.
- **ghcr-cleanup.yml** does hash-family retention on `:base-`/`:p2996-`/`:dev-`
  tag families (.github/workflows/AGENTS.md key-files table) — a new tag family
  (e.g. `:ci-<hash>`) must be added to its planner.

## Uncertainties / gaps

1. **No measured size breakdown.** All figures are documentation comments; the
   ~38 GB has no date-stamped measurement in-repo and could have drifted. The
   per-tier apportionment (base runtimes vs conda toolchain vs gcc-latest) is
   inference only. A `devcontainer-metrics` or dive artifact from a recent
   image-analysis run would resolve this (fetchable via GH API in a follow-up).
2. **Compressed vs uncompressed ~38 GB** is not stated anywhere; context
   (runner extraction failures) suggests on-disk. Registry (compressed) size is
   computed by `image benchmark` from the manifest but the number isn't
   committed.
3. **Size of the `:base-<hash16>` cache image alone** (stage 1 without
   gcc/p2996/runtime) is undocumented — it is the closest existing artifact to
   a "lean-ish" image and its size matters for shape (ii)/(iii); unknown.
4. The 2026-03-29 1.33 GB benchmark predates the current mise-tier
   architecture; I treat it only as a lower-bound hint for a lean core.
5. I could not run `docker buildx bake --print` or dive (Bash blocked);
   stage/target mapping is from file reads, which for HCL+Dockerfile is
   deterministic, so confidence there is high anyway.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — every fact read directly from the working tree at main (Dockerfile, docker-bake.hcl, P2996-CACHE.md, AGENTS.md files, ci.yml, build-publish.yml, image-analysis.yml, mise tier files, p2996_hash.py, devcontainer-smoke.sh, mise.toml, .dive-ci, benchmark JSONs).
