# docker-linguist: bake + GHA build pattern

Source: https://github.com/crazy-max/docker-linguist/blob/master/.github/workflows/build.yml
Also read: https://github.com/crazy-max/docker-linguist/blob/master/docker-bake.hcl

## Question

Can Docker Bake own a build-input permutation set (base OS x arch x microarch x
builder runner), give each permutation a distinct descriptive image tag, while
the GHA runner per leg is chosen outside bake, and no leg builds under QEMU?

## Verbatim: `.github/workflows/build.yml`

```yaml
name: build

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

on:
  push:
    branches:
      - 'master'
    tags:
      - '*'
  pull_request:

jobs:
  build:
    uses: docker/github-builder/.github/workflows/bake.yml@c4a1b216d96a8c85b45a9974b37857828274c808 # v1.13.0
    permissions:
      contents: read
      id-token: write
      packages: write
    with:
      setup-qemu: true
      target: image-all
      output: image
      push: ${{ github.event_name != 'pull_request' }}
      set-meta-labels: true
      meta-images: |
        crazymax/linguist
        ghcr.io/crazy-max/linguist
      meta-tags: |
        type=match,pattern=(.*)-r,group=1
        type=ref,event=pr
        type=edge
      meta-labels: |
        org.opencontainers.image.title=Linguist
        org.opencontainers.image.description=GitHub Language Savant to detect blob languages
        org.opencontainers.image.vendor=CrazyMax
    secrets:
      registry-auths: |
        - registry: docker.io
          username: ${{ vars.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
        - registry: ghcr.io
          username: ${{ github.repository_owner }}
          password: ${{ secrets.GITHUB_TOKEN }}
```

There is **no `strategy.matrix`** anywhere in this repo's own workflow file —
the entire `build` job is a single call into a **reusable centralized
workflow** (`docker/github-builder/.github/workflows/bake.yml`, pinned by SHA
+ version comment), which crazy-max maintains separately and shares across his
repos. All the actual runner-selection / matrix-fanout logic (if any) lives
inside that external reusable workflow, not in this repo — so this repo is
NOT a self-contained example of hand-rolled matrix+bake wiring. It is an
example of *delegating* that wiring to a shared reusable workflow.

## Verbatim: `docker-bake.hcl`

```hcl
variable "DEFAULT_TAG" {
  default = "linguist:local"
}

// Special target: https://github.com/docker/metadata-action#bake-definition
target "docker-metadata-action" {
  tags = ["${DEFAULT_TAG}"]
}

// Default target if none specified
group "default" {
  targets = ["image-local"]
}

target "image" {
  inherits = ["docker-metadata-action"]
}

target "image-local" {
  inherits = ["image"]
  output = ["type=docker"]
}

target "image-all" {
  inherits = ["image"]
  platforms = [
    "linux/amd64",
    "linux/arm/v7",
    "linux/arm64"
  ]
}
```

## Findings against the question

1. **No base-OS x arch x microarch x runner permutation set, and no
   per-permutation descriptive tag.** `image-all` is a SINGLE bake target
   whose `platforms` array lists three platforms (`linux/amd64`,
   `linux/arm/v7`, `linux/arm64`). Buildx builds all three from that one
   target and assembles them into ONE multi-arch manifest list under the
   SAME tag set (produced by `docker/metadata-action`, driven by `meta-tags`
   in the workflow `with:` block, e.g. `type=edge`, `type=ref,event=pr`).
   There is no mechanism here giving arm64 vs amd64 vs armv7 *distinct* tags
   — they collapse into one manifest.

2. **QEMU IS used.** `with: setup-qemu: true` in the reusable workflow call.
   This repo builds `linux/arm/v7` and `linux/arm64` (in addition to amd64)
   from what is presumably a single (likely x86) GHA runner, via QEMU
   emulation — the opposite of "no leg builds under QEMU". Nothing in this
   repo's own files indicates a native-arm runner is used per architecture;
   `setup-qemu: true` is the tell that emulation is the mechanism.

3. **No `bake --print` → matrix idiom is visible in this repo.** Because the
   entire build is one reusable-workflow call with no local matrix, there is
   no local step here that runs `docker buildx bake target --print` and
   feeds its target list into `fromJson(...)` for a `strategy.matrix`. That
   idiom may exist *inside* `docker/github-builder`'s `bake.yml` (not
   fetched — out of scope: the task named this repo's own workflow +
   bake file as the source), but this repo's own YAML does not exhibit it.

4. **Division of labour, as actually observed:** this repo's own two files
   contribute (a) the bake file, defining `image`/`image-local`/`image-all`
   targets and the platform list, and (b) a thin workflow `with:` block
   supplying tags/labels/registries/push-condition. All runner selection,
   QEMU setup, bake invocation, and (if any) matrix fan-out is delegated
   entirely to the external reusable workflow `docker/github-builder`,
   which this report did not fetch (it's a separate repo/ref, out of the
   scope given: "that repo's docker-bake.hcl" refers to docker-linguist's
   own file, not github-builder's).

## Bottom line

**docker-linguist is NOT an example of the permutation-set-with-distinct-tags
pattern the question describes.** It's the opposite shape: one bake target
with a `platforms` array, built via QEMU emulation on (as far as this repo's
own files show) a single runner, funneled through a shared reusable workflow
that this repo does not itself define. If the goal is to find the
matrix+bake+native-runner+distinct-tag idiom, `docker/github-builder`'s own
`bake.yml` (referenced but not fetched here) or a different high-signal repo
would need to be the next source — crazy-max's *per-project* repos have
pushed that complexity out into his shared reusable workflow.

## GitHub repos touched

- [crazy-max/docker-linguist](https://github.com/crazy-max/docker-linguist) — read `.github/workflows/build.yml` and `docker-bake.hcl` (both fetched in full)
- [docker/github-builder](https://github.com/docker/github-builder) — referenced (pinned SHA) by build.yml as the reusable workflow that owns runner/QEMU/bake orchestration; NOT fetched in this pass (out of the given scope)
