# docker/bake-action research — build-input permutation, tags, runner selection, QEMU

Source: https://github.com/docker/bake-action (README.md, action.yml, subaction/matrix/README.md,
GitHub Releases — all fetched fresh at `master` / latest tags, 2026-08-30).

## The question

> Can Docker Bake own a build-input permutation set (container base OS x
> architecture x microarch level x builder runner), give each permutation a
> distinct descriptive image tag, while the GitHub Actions runner per leg is
> chosen outside bake, and no leg builds under QEMU emulation?

**Short answer: yes, and this is exactly the documented `matrix` subaction
pattern** — bake owns the target/tag permutation (via HCL `target` blocks and
`set` overrides), a `prepare` job generates a GitHub Actions matrix from that
same bake definition, and the *workflow* (not bake, not the action) maps each
matrix cell to a specific `runs-on:` runner via a plain `${{ ... }}` expression
— including picking a native arm64 runner for arm legs so nothing falls back
to QEMU. Full detail below.

## 1. `action.yml` — every input, verbatim

```yaml
name: "Docker Buildx Bake"
description: "GitHub Action to use Docker Buildx Bake as a high-level build command"
author: 'docker'
branding:
  icon: 'anchor'
  color: 'blue'

inputs:
  builder:
    description: "Builder instance"
    required: false
  allow:
    description: "Allow build to access specified resources (e.g., network.host)"
    required: false
  call:
    description: "Set method for evaluating build (e.g., check)"
    required: false
  files:
    description: "List of bake definition files"
    required: false
  no-cache:
    description: "Do not use cache when building the image"
    required: false
    default: 'false'
  pull:
    description: "Always attempt to pull a newer version of the image"
    required: false
    default: 'false'
  load:
    description: "Load is a shorthand for --set=*.output=type=docker"
    required: false
    default: 'false'
  provenance:
    description: "Provenance is a shorthand for --set=*.attest=type=provenance"
    required: false
  push:
    description: "Push is a shorthand for --set=*.output=type=registry"
    required: false
    default: 'false'
  sbom:
    description: "SBOM is a shorthand for --set=*.attest=type=sbom"
    required: false
  set:
    description: "List of targets values to override (eg. targetpattern.key=value)"
    required: false
  source:
    description: "Context to build from. Can be either local to specify the working directory or a remote bake definition"
    required: false
  targets:
    description: "List of bake targets"
    required: false
  vars:
    description: "Variables to set in the Bake definition as list of key-value pair"
    required: false
  github-token:
    description: "API token used to authenticate to a Git repository for remote definitions"
    default: ${{ github.token }}
    required: false

outputs:
  metadata:
    description: 'Build result metadata'

runs:
  using: 'node24'
  main: 'dist/index.cjs'
  post: 'dist/index.cjs'
```

**No `workdir` input on the main action.** Confirmed by the v7.0.0 release
notes (PR #365, by @crazy-max): *"The `workdir` input is now merged into
`source`; use `source` for local and remote"*. `workdir` only survives as a
separate input on the **`matrix` subaction** (see §4) — a distinct action with
its own `action.yml`, defaulting to `.`.

## 2. `set`, `push`, `load` — precedence

`set` is documented as: *"List of [targets values to override] (e.g.
`targetpattern.key=value`)"*, list-typed (newline-delimited), pattern-matched
against target names (`*.tags=...`, `foo*.args.x=...`).

`push` and `load` are literally documented as **shorthands that resolve to a
`set` override**:

- `push`: *"Push is a shorthand for `--set=*.output=type=registry`"*
- `load`: *"Load is a shorthand for `--set=*.output=type=docker`"*

Because both desugar into the *same* `--set` mechanism as a user-supplied
`set:` line, **an explicit `set` entry that also touches `.output` wins over
the `push`/`load` boolean shorthand** — they are the same override surface,
and a later/explicit `*.output=...` in `set` overrides the ones `push`/`load`
synthesize. This is exactly the trap the already-loaded
`bake-action-set-precedence-expertise` skill names: an unconditional
`set: *.output=type=cacheonly` silently defeats `push: true` on `main`,
because `set` and `push` both compile to `--set=*.output=...` and the
explicit one is not overridden by the boolean. The v6.10.0 changelog entry
("Check provenance attestation set in bake definition before overriding",
PR #359) shows Docker is aware of this override-precedence class of bug and
has patched it for `provenance` specifically — `push`/`load`/`output` are not
called out as similarly guarded, so treat `.output` overrides as
caller-owned and never emit an unconditional one on a `push`-enabled leg.

## 3. Multiple targets — what the action does with them

`targets` is List/CSV, *"List of bake targets (`default` target used if
empty)"*, e.g. `targets: default,release`. This maps 1:1 onto `docker buildx
bake <target1> <target2> ...` — bake resolves each named target (or `group`)
from the HCL/JSON bake file(s) given by `files`, and every resolved target
becomes one build. The action's only output is a single `metadata` JSON blob
(`Build result metadata`) covering the whole invocation — multiple targets in
one `bake-action` step surface as one metadata object keyed per target, not
per-step outputs. There is no first-class "give me a GITHUB_OUTPUT per target"
mechanism in the main action.

## 4. The `matrix` subaction — this is the permutation-to-runner bridge

`subaction/matrix` is a **separate action** (`docker/bake-action/subaction/matrix@v7`)
whose whole purpose, per its README, is: *"generates a multi-dimension matrix
that can be used in a GitHub matrix through the `include` property ... so you
can distribute your builds across multiple runners."*

Inputs (its own, independent of the main action's inputs):

| Name | Type | Description |
|---|---|---|
| `workdir` | String | Working directory to use (defaults to `.`) |
| `files` | List/CSV | List of bake definition files |
| `target` | String | The target to use within the bake file |
| `fields` | String | List of extra fields to include in the matrix |

Output: `matrix` (JSON) — a matrix configuration meant for
`strategy.matrix.include: ${{ fromJson(...) }}`.

### Worked example verbatim from the README — platform-per-runner, no QEMU

```hcl
# docker-bake.hcl
target "lint" {
  dockerfile = "./hack/dockerfiles/lint.Dockerfile"
  output = ["type=cacheonly"]
  platforms = [
    "darwin/amd64",
    "darwin/arm64",
    "linux/amd64",
    "linux/arm64",
    "linux/s390x",
    "linux/ppc64le",
    "linux/riscv64",
    "windows/amd64",
    "windows/arm64"
  ]
}
```

```yaml
jobs:
  prepare:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.generate.outputs.matrix }}
    steps:
      -
        name: Checkout
        uses: actions/checkout@v6
      -
        name: Generate matrix
        id: generate
        uses: docker/bake-action/subaction/matrix@v7
        with:
          target: lint
          fields: platforms

  lint:
    runs-on: ${{ startsWith(matrix.platforms, 'linux/arm') && 'ubuntu-24.04-arm' || 'ubuntu-latest' }}
    needs:
      - prepare
    strategy:
      fail-fast: false
      matrix:
        include: ${{ fromJson(needs.prepare.outputs.matrix) }}
    steps:
      -
        name: Lint
        uses: docker/bake-action@v7
        with:
          targets: ${{ matrix.target }}
          set: |
            *.platform=${{ matrix.platforms }}
```

This is the direct answer to the runner-selection question: **`runs-on:` is a
plain job-level GitHub Actions expression evaluated against `matrix.<field>`
— nothing inside `bake-action` or the `matrix` subaction chooses or
influences the runner.** The subaction only emits data (one matrix row per
bake-file permutation, carrying whatever `fields:` you asked it to include —
here `platforms`, but any target attribute works: OS, arch, a custom var).
The *workflow author* writes the `startsWith(matrix.platforms, 'linux/arm')
&& 'ubuntu-24.04-arm' || 'ubuntu-latest'` ternary that routes an arm leg to a
**native arm64 runner** (`ubuntu-24.04-arm`) instead of an amd64 runner that
would need QEMU to cross-build arm. Generalizing: a base-OS × arch ×
microarch-level permutation set expressed as one `target` per leg in the bake
file (or via `set` overrides tagged into `matrix.<field>` through `fields:`)
flows straight through to a `runs-on:` expression with the same shape — the
subaction is architecture-agnostic about what a "field" means.

### Second worked example — plain multi-target distribution (no field split)

```yaml
jobs:
  prepare:
    ...
    steps:
      - uses: docker/bake-action/subaction/matrix@v7
        with:
          target: validate   # a *group* in the bake file, e.g. targets = ["lint", "doctoc"]

  validate:
    runs-on: ubuntu-latest
    needs: [prepare]
    strategy:
      fail-fast: false
      matrix:
        include: ${{ fromJson(needs.prepare.outputs.matrix) }}
    steps:
      - uses: docker/bake-action@v7
        with:
          targets: ${{ matrix.target }}
```

Here each bake target becomes its own matrix row/job (`matrix.target`), and
`runs-on` is fixed — the same `runs-on: <expr>` per-field pattern above is
what you use once the permutation needs a *different* runner per leg.

## 5. Distinct tags per permutation

Tags are owned entirely by the bake file / `set` overrides, not by the
action. The README's canonical push example:

```yaml
      - uses: docker/bake-action@v7
        with:
          push: true
          set: |
            *.tags=user/app:latest
```

A descriptive per-permutation tag is therefore just another `set` override
(or an HCL `tags = [...]` in the matching `target` block) computed from
`matrix.<field>` values the same way `*.platform=${{ matrix.platforms }}` is
in §4 — e.g. `*.tags=registry/app:${{ matrix.os }}-${{ matrix.arch }}-${{
matrix.microarch }}`. Bake owns the tag string; the action just passes the
override through.

## 6. Runner selection — exhaustive answer

Nothing in `action.yml` (main action) or the `matrix` subaction's inputs
(`workdir`, `files`, `target`, `fields`) touches `runs-on` or any runner
selector — there is no such input on either action. Runner choice is 100%
external: a plain job-level `runs-on: ${{ <expression over matrix fields> }}`
in the caller's workflow YAML, fed by whatever `fields:` the `matrix`
subaction was told to emit. This is a hard confirmation of the target
architecture in the question: **bake (+ its bundled matrix subaction) owns
the WHAT (target/tag/platform permutation); the workflow YAML owns the WHERE
(which runner)** — a clean separation, with the native-arm-runner trick in
§4 as the documented way to guarantee no leg falls back to QEMU emulation.

## 7. Recent release notes (last 4 tagged releases, verbatim summary)

- **v7.3.0** (2026-07-01) — dependency bumps only (esbuild bundling fix,
  `@docker/actions-toolkit` 0.90→0.92, etc.). No input/behavior change.
- **v7.2.0** (2026-05-21) — added the `vars` input (Bake variables), PR #420.
  Dependency bumps otherwise.
- **v7.1.0** (2026-04-10) — added Git-context query-format support (PR #416,
  `source: {{defaultContext}}?ref=...`-style). Dependency bumps otherwise.
- **v7.0.0** (2026-03-05) — **breaking**: Node 24 runtime default (needs
  Actions Runner ≥2.327.1); **`workdir` input removed/merged into `source`**
  (PR #365); removed deprecated `DOCKER_BUILD_NO_SUMMARY` /
  `DOCKER_BUILD_EXPORT_RETENTION_DAYS` envs; **removed the deprecated
  `list-targets` subaction — replaced by `matrix`** (PR #370); ESM switch.
- **v6.10.0** (2025-11-27) — provenance-attestation override guard (PR #359,
  checks whether `provenance` is already set in the bake definition before
  the boolean shorthand overrides it) — the one precedent for Docker patching
  a `set`-vs-shorthand precedence footgun; `push`/`load`/`output` have no
  equivalent guard as of this release.

## GitHub repos touched

- [docker/bake-action](https://github.com/docker/bake-action) — README.md, action.yml,
  subaction/matrix/README.md, and the last 5 GitHub Releases (v6.10.0–v7.3.0) read to
  answer permutation/tag/runner/QEMU question.
