# build-push-action `docker-bake.hcl` at commit `2ca78c6` — structure, line 4, and matrix answer

Source: https://github.com/docker/build-push-action/blob/2ca78c6bec76527009825f31aae0532b4d40d820/docker-bake.hcl
Fetched verbatim via `gh api repos/docker/build-push-action/contents/docker-bake.hcl?ref=2ca78c6...` (raw content decoded, byte-for-byte — WebFetch's summarized version was cross-checked against this and agrees).

## Full file content (verbatim, 55 lines)

```hcl
target "_common" {
  args = {
    BUILDKIT_CONTEXT_KEEP_GIT_DIR = 1
  }
}

group "default" {
  targets = ["build"]
}

group "pre-checkin" {
  targets = ["vendor", "format", "build"]
}

group "validate" {
  targets = ["lint", "build-validate", "vendor-validate"]
}

target "build" {
  inherits = ["_common"]
  dockerfile = "dev.Dockerfile"
  target = "build-update"
  output = ["."]
}

target "build-validate" {
  inherits = ["_common"]
  dockerfile = "dev.Dockerfile"
  target = "build-validate"
  output = ["type=cacheonly"]
}

target "format" {
  inherits = ["_common"]
  dockerfile = "dev.Dockerfile"
  target = "format-update"
  output = ["."]
}

target "lint" {
  inherits = ["_common"]
  dockerfile = "dev.Dockerfile"
  target = "lint"
  output = ["type=cacheonly"]
}

target "vendor" {
  inherits = ["_common"]
  dockerfile = "dev.Dockerfile"
  target = "vendor-update"
  output = ["."]
}

target "vendor-validate" {
  inherits = ["_common"]
  dockerfile = "dev.Dockerfile"
  target = "vendor-validate"
  output = ["type=cacheonly"]
}

target "test" {
  inherits = ["_common"]
  dockerfile = "dev.Dockerfile"
  target = "test-coverage"
  output = ["./coverage"]
}
```

## What line 4 is

Line 4 is `BUILDKIT_CONTEXT_KEEP_GIT_DIR = 1`, a key inside the `args = { ... }` map of the `target "_common"` block (the file's very first target, lines 1-5). It sets the build-arg `BUILDKIT_CONTEXT_KEEP_GIT_DIR=1`, which tells BuildKit to preserve the `.git` directory when it copies the build context into the build. Every other target in the file does `inherits = ["_common"]`, so this single line is threaded into all seven real targets (`build`, `build-validate`, `format`, `lint`, `vendor`, `vendor-validate`, `test`) via bake's inheritance mechanism — the canonical "DRY common args" idiom: define once in a base target, inherit everywhere.

Why it matters here specifically: this repo's own Go tooling (their `dev.Dockerfile` targets like `build-update`, `lint`, `vendor-update`) needs git metadata inside the build (e.g. for `go generate`/version-stamping tooling that shells out to `git describe` or reads `.git`). Without `BUILDKIT_CONTEXT_KEEP_GIT_DIR=1`, BuildKit's default context transfer drops `.git`, and any in-build git command would fail or produce a wrong version string. It is NOT related to any image/architecture matrix — it's a context-transfer knob for a self-referential dev-tooling build.

## Direct answer to the framing question

**This file does not answer, and is not evidence for, the target question** (can bake own a base-OS × arch × microarch × builder-runner permutation matrix, each with a distinct tag, runner choice made outside bake, no leg under QEMU). This `docker-bake.hcl` in `docker/build-push-action` is **not an image-release bake file at all** — it is the repo's *own dev-tooling* bake file: it builds/lints/vendors/formats/tests the Action's own Go source via a `dev.Dockerfile` multi-stage build, with `output = ["."]` (writing files back to the working tree) or `output = ["type=cacheonly"]` (validation-only, no artifact). There is:

- **No `matrix` block** in the HCL itself.
- **No `platform`/`platforms` attribute** on any target.
- **No image tag logic** (`tags = [...]`) anywhere — none of these targets produce a pushed/tagged image; `build` and `vendor`/`format` output to the local filesystem (`.`), and the `*-validate`/`lint` targets output `type=cacheonly` (nothing written anywhere, pure validate-and-discard).
- **No group spanning OS/arch/microarch** — the three groups (`default`, `pre-checkin`, `validate`) just bundle dev-workflow steps (build vs. format vs. lint+validate), not deployment permutations.

So the permutation-matrix behavior the question asks about is generated **outside this HCL file**, by a companion GitHub Action: `docker/bake-action/subaction/matrix@...` (seen in `validate.yml`, see below). That subaction inspects the bake file's target/group graph and *emits a GHA `strategy.matrix` JSON* so each bake target becomes its own parallel GHA job. This is the real mechanism worth copying for a base-OS × arch × microarch × runner permutation set:

1. Bake owns the **target definitions** (one target per permutation, each an inheritance leaf off a `_common` base — mirrors this file's `_common` → 7 leaves idiom).
2. `docker/bake-action/subaction/matrix` (or an equivalent `bake --print` JSON walk) turns that target graph into a **GHA matrix output**.
3. The calling workflow's `strategy.matrix.include` then picks **`runs-on:` per leg** entirely in YAML — bake itself never selects the runner. This is exactly the separation the question wants: bake owns the permutation *definitions and tags*; GHA's matrix (fed by bake's own structure) owns the *runner-per-leg* choice, so a native-arch runner can be picked outside bake and no leg needs QEMU.
4. Per-permutation **tags** would live as a `tags = [...]` attribute on each leaf target (this file has none, since none of its targets push images) — that's the standard bake idiom elsewhere in Docker's own bake examples (each `platform`/`os` variant target carries its own descriptive tag list), just not exercised in *this* file.

## How the workflows invoke this file

`.github/workflows/validate.yml` (fetched at the same commit) is the relevant caller:

```yaml
jobs:
  prepare:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.generate.outputs.matrix }}
    steps:
      - uses: actions/checkout@...
      - name: Generate matrix
        id: generate
        uses: docker/bake-action/subaction/matrix@d3418bd... # v7.3.0
        with:
          target: validate

  validate:
    runs-on: ubuntu-latest
    needs: [prepare]
    strategy:
      fail-fast: false
      matrix:
        include: ${{ fromJson(needs.prepare.outputs.matrix) }}
    steps:
      - name: Validate
        uses: docker/bake-action@d3418bd... # v7.3.0
        with:
          targets: ${{ matrix.target }}
```

This is the two-phase pattern: a `prepare` job runs `bake-action/subaction/matrix` against the `validate` **group** (which expands to its 3 member targets: `lint`, `build-validate`, `vendor-validate`) to produce a GHA matrix JSON; a second job fans that matrix out with `runs-on: ubuntu-latest` fixed per leg (no per-leg runner variation in this particular file, since this repo's dev-tooling doesn't need multi-arch/multi-OS legs) and calls `docker/bake-action` once per matrix entry with `targets: ${{ matrix.target }}`.

`ci.yml` and `test.yml` were also fetched; they invoke this repo's actual **build-push-action itself** (dogfooding — using the Action under test to build a scratch Dockerfile) rather than `docker-bake.hcl`, so they are not additional bake-matrix evidence and are omitted from this report as out of scope for the question.

## Idioms worth copying vs. repo-specific

**Worth copying:**
- `_common` base target + `inherits = [...]` on every leaf — the DRY pattern for a shared arg/config set across many permutation targets.
- Two-phase GHA pattern: `bake-action/subaction/matrix` to derive `strategy.matrix` from bake's own target/group graph, then a second job with `runs-on:` and other per-leg GHA-level choices layered on top of what bake defines. This is the seam where "runner chosen outside bake" naturally lives.
- `output = ["type=cacheonly"]` for validate-only targets that must not produce artifacts — relevant if a leg's purpose is "verify this permutation builds" without pushing.

**Specific to this repo's layout, not to copy as-is:**
- `dev.Dockerfile` and its named stages (`build-update`, `lint`, `vendor-update`, etc.) — this is Go-tooling self-build, unrelated to shipping a runtime image.
- `BUILDKIT_CONTEXT_KEEP_GIT_DIR` itself — only relevant when an in-build step needs live git metadata (version stamping via `git describe`), not a general permutation-matrix concern.
- No `platform`/`tags`/matrix attributes exist in this file to model after directly — the OS × arch × microarch × tag pattern must be sourced from a different bake file (e.g. Docker's `buildx`/`moby` release bake files) since this one doesn't exercise that shape at all.

## GitHub repos touched

- [docker/build-push-action](https://github.com/docker/build-push-action) — read `docker-bake.hcl` and `.github/workflows/{validate,ci,test}.yml` at commit `2ca78c6bec76527009825f31aae0532b4d40d820`.
- [docker/bake-action](https://github.com/docker/bake-action) — referenced (not fetched) as the action/subaction (`docker/bake-action` and `docker/bake-action/subaction/matrix`) that `validate.yml` uses to turn bake's target graph into a GHA matrix.
