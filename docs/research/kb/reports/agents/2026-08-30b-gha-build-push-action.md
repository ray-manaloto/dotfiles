# docker/build-push-action research — bake ownership of a build-input permutation set

Read-only research, no repo code modified. Primary source:
https://github.com/docker/build-push-action (README.md, action.yml, TROUBLESHOOTING.md).
Secondary sources fetched while following the README's own links (docs.docker.com,
docker/github-builder) — see "GitHub repos touched".

## Task question

Can Docker Bake own a build-input permutation set (container base OS x
architecture x microarch level x builder runner), give each permutation a
distinct descriptive image tag, while the GitHub Actions runner per leg is
chosen outside bake, and no leg builds under QEMU emulation?

**Short answer: yes, and Docker's own current guidance for exactly this shape
has moved away from `build-push-action` + a hand-rolled matrix, toward the
`docker/github-builder` reusable `bake.yml` workflow**, which reads the
permutation set from a Bake file (`docker-bake.hcl`) and lets the *caller*
supply the per-platform-runner mapping as a workflow input — i.e. runner
selection lives outside the Bake HCL, exactly as the question requires. See
"Answering the question" at the bottom.

## 1. What `docker/build-push-action` is, and how it differs from `bake-action`

`build-push-action` (README, top of file): a GitHub Action wrapping `docker
buildx build`. It builds and pushes images "using Buildx that can be used to
create multi-platform images, export cache, etc." It takes one Dockerfile +
one context and produces one build (optionally multi-platform via QEMU or a
multi-node builder) — it has **no concept of a target/permutation set**. Every
input is a single scalar or a flat list (`platforms`, `tags`, `build-args`,
etc.) — see the full `action.yml` inputs list below.

`docker/bake-action` (not in this repo's README body at all — confirmed by
grep: 0 mentions of "bake-action" in `build-push-action`'s README) is the
sibling action that instead drives `docker buildx bake` against a
`docker-bake.hcl`/`.json` file. Bake's whole reason to exist is a **named set
of targets** — each target is its own permutation (base image, platform,
args, tags, output) — resolved and built together, with the file itself
expressing group membership, target inheritance, and matrix expansion (`hcl`
`matrix` blocks). `build-push-action`'s single-build model cannot express a
permutation set at all; you'd have to fan it out yourself via a GitHub Actions
`strategy.matrix`, hand-writing what Bake already encodes declaratively.

**Docker's own current recommendation (see §3) confirms this split**: for a
single Dockerfile / single build shape, use `build-push-action` (or the new
`build.yml` reusable workflow, which mirrors `build-push-action`'s UX). For a
declared permutation set, use `bake-action` (or the new `bake.yml` reusable
workflow, which mirrors `bake-action`'s UX and reads the Bake file directly).

## 2. `build-push-action` action.yml schema (verbatim, trimmed to structure)

```yaml
name: Build and push Docker images
description: Build and push Docker images with Buildx
runs:
  using: 'node24'
  main: 'dist/index.cjs'
  post: 'dist/index.cjs'
inputs:
  add-hosts, allow, annotations, attests, build-args, build-contexts,
  builder, cache-from, cache-to, call, cgroup-parent, context, file,
  labels, load, network, no-cache, no-cache-filters, outputs, platforms,
  provenance, pull, push, sbom, secrets, secret-envs, secret-files,
  shm-size, ssh, tags, target, ulimit, github-token
outputs:
  imageid, digest, metadata
```

Every input is a scalar or a flat delimited list — there is no `matrix`,
`targets`, or `permutation` concept anywhere in the schema. `platforms` is a
single comma/newline list consumed by ONE buildx invocation; to get
per-platform outputs (e.g. distinct tags per arch, distinct runners per arch)
you must invoke the action once per leg from your own GHA `matrix:` — the
action itself does not own or express the permutation set.

## 3. Multi-platform patterns documented from `build-push-action`'s README

The README's own multi-platform example (single-node, QEMU-emulated):

```yaml
- name: Set up QEMU
  uses: docker/setup-qemu-action@v4
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v4
- name: Build and push
  uses: docker/build-push-action@v7
  with:
    platforms: linux/amd64,linux/arm64
    push: true
    tags: user/app:latest
```

This is the **emulated** path — it explicitly requires `setup-qemu-action`,
which is exactly what the task's constraint ("no leg builds under QEMU
emulation") rules out.

The README's "Guides" list links out to `docs.docker.com/build/ci/github-actions/*`
pages, including `.../multi-platform/`, but does **not** itself contain the
distribute-across-runners YAML — that content lives on docs.docker.com, not in
this repo.

## 4. What docs.docker.com's multi-platform page says NOW (fetched directly)

Fetched `https://docs.docker.com/build/ci/github-actions/multi-platform/`
directly (twice, with different extraction prompts). Result both times: **the
classic manual "digest-per-runner + `imagetools create` merge" pattern (matrix
of `runs-on` per platform, `build-push-action` with
`outputs=type=image,push-by-digest=true`, a digest-export step, `actions/upload-artifact`
+ `download-artifact`, and a merge job running `docker buildx imagetools create`)
is **no longer present on the page**. The page now states, verbatim per the
fetch:

> "If you want to split platform builds across multiple runners without
> maintaining a custom matrix and merge job, use the Docker GitHub Builder."

and directs to `docker/github-builder`'s `build.yml` (Dockerfile-shaped) and
`bake.yml` (Bake-shaped) reusable workflows, describing them as computing "the
per-platform matrix, run[ning] each platform on its own runner, and
creat[ing] the final manifest for you."

**This is a real finding, not a probe gap**: two independent fetches with
different prompts (one asking generally for the pattern, one asking
specifically to quote the legacy matrix/digest/imagetools YAML verbatim) both
came back saying that YAML is absent from the current page. Docker has
retired the manual pattern from its docs in favor of pointing at
`docker/github-builder`. (Caveat: WebFetch summarizes via a small model — the
raw page could not be fetched as clean markdown, since `docs.docker.com` is
not a mintlify site and `<url>/index.md` 404s. Treat "absent from the current
page" as the finding, not "guaranteed never mentioned anywhere on
docs.docker.com".)

## 5. `docker/github-builder` — the reusable-workflow pattern Docker now recommends

Repo: https://github.com/docker/github-builder. It wraps `build-push-action`,
`bake-action`, `metadata-action`, etc. into two reusable workflows.

### 5a. `build.yml` — Dockerfile-shaped, mirrors `build-push-action`'s UX

```yaml
name: ci
permissions:
  contents: read
on:
  push:
    branches: ['main']
    tags: ['v*']
  pull_request:
jobs:
  build:
    uses: docker/github-builder/.github/workflows/build.yml@v1
    permissions:
      contents: read
      id-token: write   # for signing attestations and cache entries with GitHub OIDC
    with:
      output: image
      push: ${{ github.event_name != 'pull_request' }}
      platforms: linux/amd64,linux/arm64
      meta-images: name/app
      meta-tags: |
        type=ref,event=branch
        type=ref,event=pr
        type=semver,pattern={{version}}
    secrets:
      registry-auths: |
        - registry: docker.io
          username: ${{ vars.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
```

`build.yml` inputs relevant to the task's constraints (from the README's
Inputs table):

| Input | Type | Default | Meaning |
|---|---|---|---|
| `runner` | String | see Runner mapping | GH-hosted Linux runner label **or a platform→runner mapping** |
| `distribute` | Bool | `true` | split the build across multiple runners, one platform per runner |
| `setup-qemu` | Bool | `false` | only runs `setup-qemu-action` if you explicitly opt in — **QEMU is off by default** |
| `platforms` | List/CSV | — | target platforms to build |
| `fail-fast` | Bool | `false` | cancel the matrix on first failure |
| `job-name-prefix` | String | — | prefix for matrix job names in the GHA UI |

Because `setup-qemu` defaults to `false` and `distribute` defaults to `true`,
the DEFAULT behavior of this workflow already satisfies "no leg builds under
QEMU emulation" — each platform gets its own native runner unless you
explicitly turn distribution off or opt into QEMU.

### 5b. `bake.yml` — Bake-shaped, mirrors `bake-action`'s UX (the one that answers the task directly)

```yaml
name: ci
permissions:
  contents: read
on:
  push:
    branches: ['main']
    tags: ['v*']
  pull_request:
jobs:
  bake:
    uses: docker/github-builder/.github/workflows/bake.yml@v1
    permissions:
      contents: read
      id-token: write
    with:
      output: image
      push: ${{ github.event_name != 'pull_request' }}
      meta-images: name/app
      meta-tags: |
        type=ref,event=branch
        type=ref,event=pr
        type=semver,pattern={{version}}
    secrets:
      registry-auths: |
        - registry: docker.io
          username: ${{ vars.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
```

`bake.yml` inputs (superset relevant to the task):

| Input | Type | Default | Meaning |
|---|---|---|---|
| `runner` | String | see Runner mapping | GH-hosted Linux runner label or **platform→runner mapping**, supplied by the CALLER, not the Bake file |
| `distribute` | Bool | `true` | one platform per runner |
| `setup-qemu` | Bool | `false` | opt-in only |
| `context` | String | `.` | build context |
| `files` | List | `{context}/docker-bake.hcl` | bake definition file(s) — **this is where the permutation set lives** |
| `target` | String | `default` | which Bake target/group to build |
| `set` | List | — | `docker buildx bake --set` overrides, e.g. `foo*.args.mybuildarg=value` |
| `vars` | List | — | Bake `variable` overrides |
| `meta-images` / `meta-tags` / `meta-labels` / `meta-annotations` | List | — | tag/label templates layered on top of what the Bake targets already declare |

Per the README's "Key Advantages → Performance" section, verbatim:

> "Native parallelization for multi-platform builds. Workflows can
> automatically distribute builds across runners based on target platform to
> be built, improving throughput for other architectures without requiring
> emulation or custom CI logic or self-managed runners."

### 5c. Runner mapping — how per-architecture native runners are selected (verbatim)

This is the mechanism that answers "the GitHub Actions runner per leg is
chosen outside bake":

```yaml
# single runner for every leg:
runner: ubuntu-24.04
```

```yaml
# platform -> runner mapping (this is the DEFAULT):
runner: |
  default=ubuntu-24.04
  linux/arm=ubuntu-24.04-arm
  linux/arm64=ubuntu-24.04-arm
```

Rules, verbatim from the README: "A mapping must define a `default` runner.
Additional keys are platform prefixes, and the most specific matching prefix
wins." Example given: `linux` matches all Linux platforms, `linux/arm`
matches variants like `linux/arm/v7`, and `linux/arm64` is a separate,
more-specific key from `linux/arm`.

**This `runner` input is a workflow-level input to `bake.yml`, not a field
inside `docker-bake.hcl`.** Bake's own file format has no `runs-on` /
runner-selection concept — Bake owns *what* to build (targets, platforms,
tags, args), the calling GHA workflow owns *where* each platform's leg runs.
That is a clean, already-productized version of "bake owns the permutation
set; the runner-per-leg choice is made outside bake."

## 6. Answering the task's question directly

> Can Docker Bake own a build-input permutation set (container base OS x
> architecture x microarch level x builder runner), give each permutation a
> distinct descriptive image tag, while the GitHub Actions runner per leg is
> chosen outside bake, and no leg builds under QEMU emulation?

**Yes**, and this is close to a first-class supported shape as of the current
`docker/github-builder@v1` reusable `bake.yml` workflow:

- **Permutation ownership**: the Bake file (`docker-bake.hcl`, referenced via
  `files:`) defines the full target matrix — base OS, arch/platform, and any
  other build-arg axis (microarch level would be a Bake `matrix`-expanded
  `args.*` value or a `target.args` override via `set:`). Bake's native
  `matrix` block (not covered in this repo, it's Bake's own HCL syntax — see
  the sibling bake-doc-* research agents' output for the exact syntax) is
  exactly the mechanism for cross-producing OS x arch x microarch as distinct
  named targets, each capable of a distinct tag via `target.tags`.
- **Distinct descriptive tags per permutation**: native to Bake — each
  target's `tags` list is independent; `meta-tags`/`meta-images` in `bake.yml`
  layer `docker/metadata-action`-style templating on top without collapsing
  targets together.
- **Runner chosen outside bake**: the `runner` input (a platform→runner
  string map) is supplied by the calling GHA workflow, not by the Bake HCL.
  Bake has no runner concept; `bake.yml` reads the target's platform and
  looks up the matching runner from the caller-supplied map.
- **No QEMU**: `setup-qemu` defaults to `false` and must be explicitly
  opted into; `distribute` defaults to `true`, so by default every declared
  platform gets its own native runner leg rather than one emulated build. The
  only way QEMU enters is if the caller sets `setup-qemu: true` or maps
  multiple non-native platforms onto one runner.

**Caveat inherited from §4/§5's "Runner mapping" quote**: the runner map keys
are **platform prefixes** (`linux/amd64`, `linux/arm64`, `linux/arm`, `linux`,
`default`) — there is no documented key axis for "microarch level" or
"builder runner identity" beyond platform. If the task's 4-axis permutation
(OS x arch x microarch x runner) needs a *distinct runner per microarch level
within the same platform* (e.g. two different `linux/amd64` legs, one
`x86-64-v2` and one `x86-64-v3`, on two different runner labels), that is
**not expressible through the `runner` input's platform-prefix map alone** —
it would need either separate Bake `target`s each pinned to a distinct
`platforms` value that doesn't collide (not possible, since platform is the
map's only key), or the caller falls back to a hand-rolled GHA `matrix:` per
microarch level wrapping `bake-action` directly (not the reusable `bake.yml`),
losing the "distribute" and "signed provenance" conveniences. This is a real
gap versus this repo's actual current CI shape (per `AGENTS.md`: "the middle
six fan out per leg — arch + a non-blocking runner-validation leg, #676/#736"
— i.e. this repo already fans out via its OWN GHA matrix + bake, not via
`github-builder`), and is worth flagging back rather than assuming
`github-builder`'s runner-mapping input covers a microarch-level axis it was
never described as covering.

## GitHub repos touched

- [docker/build-push-action](https://github.com/docker/build-push-action) — README.md, action.yml, TROUBLESHOOTING.md read for the action's schema, multi-platform example, and its (lack of) mention of bake-action or a distributed-runner pattern
- [docker/github-builder](https://github.com/docker/github-builder) — README.md read in full for `build.yml`/`bake.yml` reusable-workflow inputs, the runner-mapping mechanism, and the "distribute" / QEMU-opt-in defaults
- docs.docker.com (not a GitHub repo, but docker/docker.github.io is its likely source) — `/build/ci/github-actions/multi-platform/` fetched twice directly to confirm the legacy manual matrix+imagetools pattern is no longer documented there
