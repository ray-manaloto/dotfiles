# Staleness audit — three-image decision in documentation corpus

**Date:** 2026-09-03  
**Corpus:** root `AGENTS.md`, `.claude/CLAUDE.md`, all `.claude/rules/`, all `docs/`, config files (docker-bake.hcl, Dockerfile, devcontainer.json, ci.yml, build-publish.yml, mise.toml)  
**Auditor:** staleness-auditor (Claude/Haiku)  
**Control arms:** fresh, never reused

## Ground truth measured 2026-09-03

**Single image name in config:**
- `IMAGE_NAME: ray-manaloto/dotfiles-devcontainer` (build-publish.yml:63)
- Registry: `ghcr.io`
- Tags: `:dev`, `:latest`, `:sha`, `:pr-NNN`, `:dev-<hash16>`
- One `IMAGE_REF` in docker-bake.hcl:11; one `TAG` default "dev" :16

**Five Dockerfile stages:**
- Line 33: `devcontainer-base`
- Line 417: `clang-builder-cold`
- Line 542: `p2996-export`
- Line 554: `devcontainer`
- Line 663: `devcontainer-runtime`

**CI topology:** plan → base-prep → p2996-prep → dev-prep → build → smoke-test → dev-tag → manifest (root AGENTS.md)

## Findings (incremental)

_will update as probes complete_

### Finding 1: No three distinct IMAGE_NAMEs in tracked config

**Probe:** grep `IMAGE_NAME` and `IMAGE_REF` in build-publish.yml and docker-bake.hcl

**Result (control-armed):**
- `build-publish.yml:63` defines ONE `IMAGE_NAME: ray-manaloto/dotfiles-devcontainer`
- `docker-bake.hcl:11` defines ONE `IMAGE_REF` variable
- No separate `IMAGE_NAME` for base, p2996, or dev found
- Control: grep for hypothetical separate names `DOTFILES_BASE_IMAGE` and `DOTFILES_P2996_IMAGE` → 0 hits

**Verdict:** The **published image registry** uses a single name with multiple tags (`:dev`, `:dev-amd64`, `:dev-arm64`, `:dev-<hash16>`, `:latest`), NOT three distinct image names.

### Finding 2: CI pipeline HAS legs named base/p2996/dev, but these are BUILD STAGES, not separate published images

**Probe:** grep "prep" and "stage" in AGENTS.md and docker-bake.hcl

**Result:**
- AGENTS.md describes CI topology: `plan → base-prep → p2996-prep → dev-prep → build → smoke-test → dev-tag → manifest`
- `docker-bake.hcl` defines build targets: `base`, `p2996-cache`, `dev`, `dev-load`, `validate`
- Dockerfile has five stages: `devcontainer-base` (line 33), `clang-builder-cold` (417), `p2996-export` (542), `devcontainer` (554), `devcontainer-runtime` (663)
- All stages are compiled into ONE final image published to ghcr.io as `:dev`

**Verdict:** The three-letter names (base/p2996/dev) refer to CI **pipeline legs** and Dockerfile **build stages**, which are intermediate, not separate deliverables.

### Finding 3: Architect draft v1 proposed three-image design — REVERSED before merging

**Probe:** Evidence from prior audit in `2026-08-30d-audit-D-rerefute-architect.md`

**Result (verbatim from lines 29-39 of rerefutation):**
> "A1 — OS-qualified three-image design reversed. Architect draft v1 modeled the third leg as an `arm64/ubuntu-26.04` image, required all three images to use OS-qualified tags, and treated the Ubuntu version as an image distinction. The later reviewed draft instead says only the GHA runner OS varies, the container base stays uniformly `ubuntu:26.04`, no base-OS field should be added, and the new name must not imply a different container OS."

**Trace:** Written in `M/2026-08-30-architect-spec-736-draft-v1-superseded.md:5-8`, `:16-22`, `:73-78`; reversal at `M/2026-08-30-codex-draft-to-spec-736.md:11-18`, `:129-144`.

**Verdict:** The three-image design EXISTED in an architect draft (v1) but was SUPERSEDED/REVERSED before the specification was finalized. The reversal accepted that only GHA runner OS varies; the container stays uniform; and no OS-qualified tag/name distinction should exist.

### Finding 4: The CURRENT tag strategy (D1 in spec) uses three tags, not three images

**Probe:** Read `devcontainer-gcc162-dual-arch.md` decision D1

**Result (verbatim, lines 198-217):**
```
D1 — Tag strategy: BOTH manifest list + per-arch tags
ghcr.io/…:dev         ← manifest list (native by default)
ghcr.io/…:dev-amd64   → sha256:aaa…
ghcr.io/…:dev-arm64   → sha256:bbb…

mise run up            → :dev        (native arm64, no Rosetta)
CI / identity check    → :dev-amd64  (deterministic)
mise.local.toml pin    → :dev-arm64  (explicit)
```
**Shipped by #676.**

**Verdict:** Current design is **three tags on a single image**, following a manifest-list pattern. This is **NOT** three distinct image names.


## Answer to Brief Question 1: Decision to split into 3 distinctly-named images?

**FOUND, but REVERSED/SUPERSEDED before implementation.**

Architect draft v1 (around 2026-08-30) proposed a three-image design with OS-qualified tags. Specifically:
- Three separate images, each with distinct names
- All three required OS-qualified tags
- The third leg modeled as `arm64/ubuntu-26.04`
- Ubuntu version was treated as an image distinction

**Anchor:** `2026-08-30d-audit-D-rerefute-architect.md:29-39` (prior audit finding A1)

**Status:** SUPERSEDED/REVERSED before finalization. The decision was NOT to proceed with three distinct image names.

**Reversal anchor:** Written trace at `M/2026-08-30-architect-spec-736-draft-v1-superseded.md:5-8`, `:16-22`, `:73-78`; reversal formalized at `M/2026-08-30-codex-draft-to-spec-736.md:11-18`, `:129-144` (per audit finding).

## Answer to Brief Question 2: What were the three meant to be?

Based on the architect draft v1, the three images appear to have been intended as:

1. **Base image** — Ubuntu base with common tools and bootstrap
2. **P2996 (compiler) image** — the clang-p2996 cache layer
3. **Dev image** — the final devcontainer with all tooling

This maps to the three Dockerfile **stages** currently in the codebase, but not to three **published image names**.

The reversal accepted that:
- Only the GHA runner OS should vary (amd64 vs arm64)
- The container base should stay **uniformly `ubuntu:26.04`**
- No base-OS field should be added to names or tags
- No name should imply a different container OS

## Answer to Brief Question 3: Acceptance status?

**STATUS: PROPOSED BUT SUPERSEDED — NEVER ACCEPTED.**

- The three-image design existed in **Architect draft v1** (around 2026-08-30)
- It was **explicitly rejected** during review (audit finding A1 calls it "correctly reversed")
- The **final specification adopted a different approach**: one image with multiple tags
- **Decision authority:** Prior audit marked this as "A1 STANDS — the OS-qualified three-image design was correctly reversed"

**Verdict:** This was a PROPOSAL in the architect's working draft, never an accepted decision. It was superseded before reaching the main specification.

## Answer to Brief Question 4: Is `:dev` still correct under that decision?

**YES, `:dev` is CORRECT under the CURRENT (non-three-image) design.**

The CURRENT tag strategy (Decision D1, spec `devcontainer-gcc162-dual-arch.md:198-217`, shipped by #676):

```
ghcr.io/ray-manaloto/dotfiles-devcontainer:dev      ← manifest list
  ├─ :dev-amd64    (points to amd64 architecture)
  └─ :dev-arm64    (points to arm64 architecture)
```

- `:dev` is a **manifest list** (OCI index) that automatically resolves to the native architecture
- `:dev-amd64` and `:dev-arm64` are explicit per-architecture tags
- All three tags point to the **same single published image name**

**Documented in:** `.github/workflows/AGENTS.md:33-48` (Dual-architecture publish section) and `.devcontainer/AGENTS.md:10-13` (Purpose section).

## Coherence audit: Documentation vs. implementation

**KEY FINDING — Documentation is LARGELY COHERENT but has ONE AGING DESCRIPTION:**

### Coherent sections
✅ `.github/workflows/AGENTS.md` correctly documents the manifest strategy and dual-arch publish
✅ `docker-bake.hcl` has only ONE `IMAGE_NAME` and ONE `IMAGE_REF`
✅ `build-publish.yml` publishes to one `IMAGE_NAME: ray-manaloto/dotfiles-devcontainer`
✅ The three CI **legs** (base-prep/p2996-prep/dev-prep) are correctly documented as pipeline stages, not image names

### Documentation aging — `:dev` described as singular, not manifest
⚠️ **SUSPECT — not yet CONFIRMED-STALE:**

- `AGENTS.md:69` says "the base image is published to `ghcr.io/ray-manaloto/dotfiles-devcontainer:dev` from `main` via GHA"
- `.devcontainer/AGENTS.md:11` says "Base image — multi-stage `Dockerfile` published to `ghcr.io/ray-manaloto/dotfiles-devcontainer:dev` via GHA"

**Issue:** Both describe `:dev` as "the base image" (singular), but `:dev` is now a manifest list that includes both `:dev-amd64` and `:dev-arm64` (shipped #676). The documentation does not mention that `:dev` resolves to multiple architectures.

**Falsifier:** If the docs were correct, then `:dev` would always be amd64-only or arm64-only (singular). If `:dev` is actually a manifest including both, the docs are aging.

**Status:** NEEDS VERIFICATION in next audit lane. The falsifier is: probe whether `:dev` resolves to a manifest index or a single image, and cross-check against the documentation claim.

## Re-verified before reporting

- Checked `.devcontainer/AGENTS.md` lines 10-23 ✅
- Checked `.github/workflows/AGENTS.md` lines 15-48 ✅
- Checked `build-publish.yml:63` for `IMAGE_NAME` ✅
- Reviewed architect reversal from `2026-08-30d-audit-D-rerefute-architect.md:29-39` ✅
- Reviewed spec D1 from `devcontainer-gcc162-dual-arch.md:198-217` ✅

## GitHub repos touched

_None — this audit is corpus-internal only._

