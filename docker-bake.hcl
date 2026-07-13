variable "DEFAULT_REGISTRY" {
  default = "ghcr.io/ray-manaloto"
}

variable "IMAGE" {
  default = "dotfiles-devcontainer"
}

# Full image reference used for tags and cache refs
# In CI, metadata-action overrides tags; this controls cache and local builds
variable "IMAGE_REF" {
  default = "${DEFAULT_REGISTRY}/${IMAGE}"
}

variable "TAG" {
  default = "dev"
}

variable "PLATFORM" {
  default = "linux/amd64/v2"
}

# Whether the published targets push to the registry. Defaults false so a
# stray local `docker buildx bake dev/base/p2996-cache` builds without
# pushing to GHCR (those targets are CI-only — see AGENTS.md "Do not").
# CI flips it per job via a `PUSH` step env var (bake reads same-named env
# vars into variables): base/p2996-prep set it "true"; the dev build sets it
# to the reusable workflow's `publish` input. This lives in a variable — not
# the bake-action `push:` shorthand — because `push: true` injects
# `--set *.output=type=registry`, and a bake `--set` on `output` REPLACES the
# whole list (docs.docker.com/build/bake/reference "overridden by last
# occurrence"), which would silently drop the zstd/OCI compression flags below.
variable "PUSH" {
  default = "false"
}

# Layer compression for the published image (#222). zstd compresses better and
# decompresses faster than gzip, and — unlike a lazy-pull snapshotter — shrinks
# the bytes EVERY consumer transfers on a normal `docker pull` (the Mac's
# `mise run sync` plus both CI pull jobs). `oci-mediatypes=true` is the
# prerequisite media-type framing. `force-compression=true` is load-bearing on
# the `dev` target: the two largest layers (~82% of the pull) arrive from the
# gzip `devcontainer-base`/`p2996-export` named contexts, whose content-hash
# tags are NOT busted by this attribute (base-hash/p2996-hash read file bytes,
# not the bake output) — so they stay warm gzip cache-hits and force-compression
# is what recompresses them to zstd in the final manifest, no cold rebuild.
# compression-level is left at the buildkit zstd default for this first flip
# (single-variable size measurement vs the 9.26 GB gzip baseline); tune later.
variable "COMPRESSION_OUTPUT" {
  default = "compression=zstd,oci-mediatypes=true,force-compression=true"
}

# Digest-pinned to the ubuntu:26.04 manifest-list (multi-arch resolution
# preserved). This value feeds the base content-hash (p2996_hash.py reads it),
# so a digest bump busts the base cache. Renovate bumps it via the custom
# `ubuntu` manager; keep in lockstep with the Dockerfile BASE_IMAGE ARG.
variable "BASE_IMAGE" {
  default = "ubuntu:26.04@sha256:b7f48194d4d8b763a478a621cdc81c27be222ba2206ca3ca6bc42b49685f3d9e"
}

variable "DEVCONTAINER_USERNAME" {
  default = "devcontainer"
}

# Builder image for the clang-p2996 compile (#160 T11). A first-class
# p2996-hash input (with PLATFORM): bumping it forces the ~2h compiler
# rebuild, so it is DELIBERATELY separate from BASE_IMAGE and NOT
# Renovate-tracked — bump manually and rarely. The builder never ships
# bytes into the final image. Keep in lockstep with the Dockerfile
# BUILDER_IMAGE ARG default.
variable "BUILDER_IMAGE" {
  default = "ubuntu:26.04@sha256:b7f48194d4d8b763a478a621cdc81c27be222ba2206ca3ca6bc42b49685f3d9e"
}

# Pinned commit SHA for Bloomberg's clang-p2996 fork (C++ P2996 reflection).
# Changing this value invalidates the BuildKit cache for the clang-builder stage.
variable "CLANG_P2996_REF" {
  default = "a56e7036fc1dcc8d4325f79230809b6ee678e5f2"
}

// Default tags for local builds; overridden by docker/metadata-action
// bake files in CI to inject SHA, latest, and PR tags.
target "docker-metadata-action" {
  tags = [
    "${IMAGE_REF}:${TAG}",
  ]
}

target "_common" {
  context    = "."
  dockerfile = ".devcontainer/Dockerfile"
  platforms  = ["${PLATFORM}"]
  args = {
    DEVCONTAINER_USERNAME = DEVCONTAINER_USERNAME
  }
  secret = [
    "id=github_token,env=GITHUB_TOKEN",
  ]
}

# Default dev environment on ubuntu base.
# Warm CI paths inject `dev.contexts.devcontainer-base` and
# `dev.contexts.p2996-export` as digest-pinned docker-image:// refs via
# bake-action `set:` (#160 T11) — the contexts override the same-named
# local stages so the dev build is a pull + thin layer. No contexts
# here: the committed default is the cold path (local stages build).
target "dev" {
  inherits = ["_common", "docker-metadata-action"]
  # devcontainer-runtime = final stage + the runtime tool tier (#160 T10);
  # the published :dev image ships base + runtime tiers, the overlay tier
  # installs per-user at container create.
  target   = "devcontainer-runtime"
  args = {
    BASE_IMAGE      = BASE_IMAGE
    BUILDER_IMAGE   = BUILDER_IMAGE
    CLANG_P2996_REF = CLANG_P2996_REF
  }
  # Tags inherited from docker-metadata-action (CI overrides with SHA/latest/PR tags)
  cache-from = [
    "type=gha,scope=dotfiles-dev",
  ]
  cache-to = [
    "type=gha,scope=dotfiles-dev,mode=max",
  ]
  # mode=max records the full build graph (materials, args, steps) so the
  # published provenance can answer "what exactly went into this image"
  # (#160 T7). All three published targets attest identically — see base /
  # p2996-cache below.
  attest = [
    "type=provenance,mode=max",
    "type=sbom",
  ]
  # zstd + OCI media types + force-compression (#222). Editing this block is
  # deliberate: `dev_target_digest` (p2996_hash.py) hashes the whole `dev`
  # target, so adding this output BUSTS dev-hash — the dev-prep probe MISSES
  # and CI actually rebuilds, applying zstd. Without a block edit the existing
  # gzip `:dev-<hash>` would be a cache-hit and the flip a silent no-op.
  output = [
    "type=image,push=${PUSH},${COMPRESSION_OUTPUT}",
  ]
}

# Content-addressed cache for the devcontainer-base stage (apt + mise
# install + cargo crates — the heavy ~30 min layer). CI tags it
# ghcr.io/<owner>/<repo>:base-<hash16> where the hash captures
# BASE_IMAGE + Dockerfile base-section + mise-system.toml + mise-system.lock
# + hk-common.pkl/hk-image.pkl.
# The dev build consumes it as the digest-pinned `devcontainer-base`
# named context on warm paths (#160 T11); p2996-cache no longer touches
# it at all (builder decoupled).
#
# NOTE: deliberately NO `type=gha` cache-from/cache-to. The registry
# tag IS the durable cache: CI's `Probe cache` step short-circuits
# this target via `docker manifest inspect :base-<hash>` before the
# bake even runs. A `mode=max` gha export of this image's layers
# exceeded the 1-hour Azure SAS token TTL on cold-cache runs (one
# layer alone took ~3600s) and broke base-prep. Rely on the registry
# manifest probe instead — that's the cache for inter-job/inter-PR
# reuse, with no SAS token in the path.
target "base" {
  inherits = ["_common"]
  target   = "devcontainer-base"
  args = {
    BASE_IMAGE = BASE_IMAGE
  }
  # Attestations on ALL published targets (#160 T7): the base cache image
  # gets the same provenance/SBOM guarantees as the dev image it feeds.
  attest = [
    "type=provenance,mode=max",
    "type=sbom",
  ]
  # zstd + OCI media types (#222). This block is NOT a base-hash input, so
  # adding it does NOT bust `:base-<hash>` — the warm gzip base cache stays a
  # hit (no ~30 min cold rebuild) and the `dev` target's force-compression
  # recompresses its layers to zstd anyway. This output only takes effect on a
  # genuine base rebuild (BASE_IMAGE/mise-system bump), keeping the internal
  # cache image zstd for consistency.
  output = [
    "type=image,push=${PUSH},${COMPRESSION_OUTPUT}",
  ]
}

# Content-addressed cache for the clang-p2996 build artifact.
# Builds only the scratch-based p2996-export stage (~500 MB, just
# /opt/clang-p2996/). Since #160 T11 the builder is fully decoupled
# from devcontainer-base (FROM ${BUILDER_IMAGE} + own apt toolchain),
# so this target needs NO base ref and p2996-prep runs in PARALLEL
# with base-prep. Tag pattern: ghcr.io/<owner>/<repo>:p2996-<hash16>.
#
# Same reasoning as `base` for omitting `type=gha` cache: registry
# tag + Probe cache covers the inter-job path; gha cache export only
# adds wall time and the 1-hour SAS expiry failure mode.
target "p2996-cache" {
  inherits = ["_common"]
  target   = "p2996-export"
  args = {
    BUILDER_IMAGE   = BUILDER_IMAGE
    CLANG_P2996_REF = CLANG_P2996_REF
  }
  # Attestations on ALL published targets (#160 T7). Provenance on the
  # p2996 artifact directly supports T11's "provenance materials contain
  # the p2996 digest" check.
  attest = [
    "type=provenance,mode=max",
    "type=sbom",
  ]
  # zstd + OCI media types (#222). Like `base`, this block is NOT a p2996-hash
  # input, so it does NOT bust `:p2996-<hash>` — the warm cache stays a hit (no
  # ~2 h cold clang rebuild) and only takes effect on a genuine p2996 rebuild
  # (CLANG_P2996_REF/BUILDER_IMAGE bump).
  output = [
    "type=image,push=${PUSH},${COMPRESSION_OUTPUT}",
  ]
}

# Local-load variant (outputs to docker instead of registry)
target "dev-load" {
  inherits = ["dev"]
  output   = ["type=docker"]
  tags     = ["${IMAGE_REF}:${TAG}"]
}

# Validation target (dry-run mode)
target "validate" {
  inherits = ["dev"]
  call     = "check"
}

# Introspection target (lists all targets)
target "help" {
  call = "targets"
}

group "default" {
  targets = ["dev"]
}

group "all" {
  targets = ["dev"]
}
