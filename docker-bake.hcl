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
# CI's base-prep + p2996-prep jobs override DEVCONTAINER_BASE_REF and
# P2996_SOURCE with published cache image refs so the dev build is a
# pull + thin layer instead of rebuilding base + clang from scratch.
target "dev" {
  inherits = ["_common", "docker-metadata-action"]
  # devcontainer-runtime = final stage + the runtime tool tier (#160 T10);
  # the published :dev image ships base + runtime tiers, the overlay tier
  # installs per-user at container create.
  target   = "devcontainer-runtime"
  args = {
    BASE_IMAGE      = BASE_IMAGE
    CLANG_P2996_REF = CLANG_P2996_REF
    # Defaults are local stage names — cold path. CI overrides these.
    DEVCONTAINER_BASE_REF = "devcontainer-base"
    P2996_SOURCE          = "p2996-export"
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
}

# Content-addressed cache for the devcontainer-base stage (apt + mise
# install + cargo crates — the heavy ~30 min layer). CI tags it
# ghcr.io/<owner>/<repo>:base-<hash16> where the hash captures
# BASE_IMAGE + Dockerfile base-section + mise-system.toml + mise-system.lock
# + hk-common.pkl/hk-image.pkl.
# Both p2996-cache and dev pull this image so neither rebuilds the
# mise install when only p2996 inputs change.
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
}

# Content-addressed cache for the clang-p2996 build artifact.
# Builds only the scratch-based p2996-export stage (~500 MB, just
# /opt/clang-p2996/). CI passes DEVCONTAINER_BASE_REF=
# ghcr.io/.../:base-<base-hash16> so the mise install layer is pulled
# (not rebuilt) before the clang compile starts. Tag pattern:
# ghcr.io/<owner>/<repo>:p2996-<p2996-hash16>.
#
# Same reasoning as `base` for omitting `type=gha` cache: registry
# tag + Probe cache covers the inter-job path; gha cache export only
# adds wall time and the 1-hour SAS expiry failure mode.
target "p2996-cache" {
  inherits = ["_common"]
  target   = "p2996-export"
  args = {
    BASE_IMAGE            = BASE_IMAGE
    CLANG_P2996_REF       = CLANG_P2996_REF
    DEVCONTAINER_BASE_REF = "devcontainer-base"
  }
  # Attestations on ALL published targets (#160 T7). Provenance on the
  # p2996 artifact directly supports T11's "provenance materials contain
  # the p2996 digest" check.
  attest = [
    "type=provenance,mode=max",
    "type=sbom",
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
