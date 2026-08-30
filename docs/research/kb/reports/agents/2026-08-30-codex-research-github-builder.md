# `docker/github-builder` adoption fit — dotfiles devcontainer CI

## 1. What it is

`docker/github-builder` ships two `workflow_call` reusable workflows —
`bake.yml` (buildx bake driven) and `build.yml` (build-push-action driven,
simpler single-target case). Both wrap Docker's own build actions
(`build-push-action`, `metadata-action`, `bake-action`) behind a
Docker-org-controlled, org-trusted pipeline: signed SLSA provenance, signed
GHA-cache entries (verified via GitHub OIDC before reuse), and "the consumer
cannot alter build logic" isolation. Its stated value proposition (README
"Key Advantages") is Performance (native per-platform parallel runners, no
custom distribution logic), Security (org-trusted build steps, signed
provenance/cache), and Isolation/Reliability (uniform behavior, less
per-repo CI scripting drift).

`updatedAt: 2026-08-24`, not archived — actively maintained, current major
tag `v1` (pinned SHAs seen in the wild go up to `v1.17.0`).

## 2. `bake.yml` — input/output schema (the relevant one for this repo)

Read `.github/workflows/bake.yml` directly (1415 lines; the `workflow_call`
header is lines 3–193, jobs start at 194). Full `inputs:` list:

- `runner` (string, multiline `pattern=runner` mapping, default maps
  `default`→`ubuntu-24.04`, `linux/arm`/`linux/arm64`→`ubuntu-24.04-arm`)
- `distribute` (bool, default `true`) — one platform per runner vs. one job
  building everything
- `fail-fast` (bool, default `false`) — **maps directly onto GHA's own
  `strategy.fail-fast`**, wired straight through to the `build` job's
  `strategy: fail-fast: ${{ inputs.fail-fast }}` (bake.yml:611)
- `job-name-prefix`, `setup-qemu`, `artifact-name`/`artifact-upload`/
  `artifact-retention-days` (local-output path)
- `cache` (bool), `cache-scope` (string, **defaults to target name but is
  fully caller-settable per invocation**), `cache-mode` (`min`/`max`)
- `context`, `files` (bake file list), `output` (`image`|`local`), `push`
  (bool), `sbom` (bool), `set` (raw bake `--set` overrides), `sign`
  (`auto`|`true`|`false`), `target` (bake target name, default `default`),
  `vars`, `registry-identities`
- `set-meta-*` / `meta-*` — `docker/metadata-action` passthrough (images,
  tags, flavor, labels, annotations, bake-target-name)
- `secrets`: `registry-auths` (YAML, multi-registry), `github-token`
- `outputs`: `meta-json`, `cosign-version`, `cosign-verify-commands`,
  `artifact-name`, `digest`, `output-type`, `signed`

Jobs: `registry-identities` → `prepare` (resolves the runner-mapping JS,
computes the per-platform job matrix `includes` from the bake file's declared
`platforms`) → `build` (`strategy.matrix.include = fromJson(prepare
.outputs.includes)`, `runs-on: ${{ matrix.runner }}`, `fail-fast: ${{
inputs.fail-fast }}`) → `finalize` (merges per-platform results into the
final manifest/output).

### Runner-per-platform mapping IS overridable (directly answers #736)

`prepare`'s embedded `actions/github-script` step (bake.yml:104-246) parses
the `runner` input as a **multiline `pattern=runner` list** with prefix
matching on the platform string (`matchesPlatformPrefix`, most-specific rule
wins) plus a mandatory `default=` entry. This is exactly the shape needed to
route one arm64 leg to `ubuntu-26.04-arm` while the rest stay on
`ubuntu-24.04-arm`/`ubuntu-24.04`: e.g.

```yaml
runner: |
  default=ubuntu-24.04
  linux/arm64=ubuntu-26.04-arm
```

The default `runner` value literally documents this exact pattern
(`linux/arm64=ubuntu-24.04-arm`) — this repo's #736 ask (arch × runner-OS
permutation) is the documented, first-class use case, not an edge case
requiring workarounds. A previous "auto"/"amd64"/"arm64" shorthand form is
deprecated in favor of this explicit mapping (deprecation warnings emitted
if used), confirming the mapping syntax is the maintained path forward.

### Cache scope IS per-leg overridable (directly answers the cache-scope collision bug)

`cache-scope` is a plain string input, "defaults to target name" if unset —
but the caller can set it to anything, including something that folds in the
platform. `docker/compose`'s real workflow (below) sets a static
`cache-scope: binary` for a single-platform job and ALSO uses raw `set:`
overrides (`*.cache-from=type=gha,scope=test`) for a different job in the
same file — i.e. callers freely override cache-from/cache-to per bake target
via `set:` even beyond the `cache-scope` input, which is strictly more
flexible than this repo's current single hardcoded HCL string
(`docker-bake.hcl:145`, `"type=gha,scope=dotfiles-dev-${replace(PLATFORM,
"/", "-")}"`). Nothing here is a limitation the current repo doesn't already
have to solve itself — the actual #676-recurrence collision this repo found
was caused by NOT parameterizing the scope by platform, and `bake.yml`
doesn't force that mistake; it makes scope-per-leg the natural path since
each matrix leg is a normal `runs-on: ${{ matrix.runner }}` job that can set
its own `cache-scope`/`set:` value the same way the repo's own `PLATFORM`
substitution does today.

### Non-blocking / best-effort leg support

There is no literal "allow-failure" input, but the primitive is `fail-fast`
(bool) wired straight to GHA's native `strategy.fail-fast`. Combined with
each matrix leg being an ordinary job, a caller wanting one leg to be
"advisory" would do what any GHA matrix does — a separate low-priority
`continue-on-error` wrapper job or a second bake.yml call outside the
gating strategy — the workflow does not itself special-case "best effort,"
but it doesn't prevent composing one either. `fail-fast: false` already
matches this repo's own `base-prep`/`p2996-prep`/`build`/`smoke-test`
matrices (all explicitly `fail-fast: false`, e.g.
`build-publish.yml:141,275,528,784`), for the same stated reason ("one
architecture failing must not cancel the other").

## 3. This repo's repo-specific behaviors — what a switch to `bake.yml` would need to accommodate or lose

Read in full: `docker-bake.hcl`, `build-publish.yml` (1226 lines),
`ci.yml` `promote` job (~380-560), `platform_target.py`.

1. **Three-tier content-hash probe cache** (`base-hash`/`p2996-hash`/
   `dev-hash`, each `docker manifest inspect`-probed via `dotfiles-setup
   {base,p2996,dev}-hash`, `build-publish.yml` `base-prep`/`p2996-prep`/
   `dev-prep` jobs). `bake.yml`'s only cache primitive is GHA's `type=gha`
   backend (`cache`/`cache-scope`/`cache-mode` inputs) — a layer cache, not
   a manifest-existence probe that can SKIP an entire job (base-prep exits
   in <30s on hit; `dev-prep` skips build+smoke-test entirely on hit). None
   of this maps onto `bake.yml`'s inputs; it would have to remain
   repo-owned custom job logic wrapping (or replacing) the reusable
   workflow's `build` job, not something `bake.yml` provides or could be
   configured to provide.
2. **P2996 compiler cache / prep stage** — `p2996-prep` builds a *separate*
   bake target (`p2996-cache`) from a *different* base image
   (`BUILDER_IMAGE`) fully decoupled from the main `base` target, pushes it
   under a content-hash tag, and the `dev` target consumes it as a
   digest-pinned named build context. `bake.yml` builds ONE bake file/target
   per invocation via its `files`/`target`/`vars`/`set` inputs — nothing
   about a second independently-cached prerequisite target feeding the
   first as a named context is expressible as reusable-workflow inputs.
   This would need to stay a separate, repo-owned job (or a second
   `bake.yml` call) exactly as today.
3. **Anti-drift `:dev-<arch>` manifest retagging in `promote`**
   (`ci.yml:381-560`) — on push-to-main, looks up the merged PR via GraphQL
   `associatedPullRequests`, then `docker buildx imagetools create -t :dev
   -t :latest <:pr-NNN>` (manifest-only retag, no rebuild). This is
   entirely post-build registry manipulation outside anything `bake.yml`'s
   `finalize` job does (its outputs are `meta-json`/`digest`/`signed` for
   the run just executed, not cross-run promotion logic). Stays custom.
4. **`GCC_LATEST_ARCHES`/`LLVM_TARGETS` arch-asymmetric tables**
   (`platform_target.py:162-195`) — these feed Dockerfile `ARG`/build args
   (`vars`/`set` in bake terms) and downstream smoke assertions; `bake.yml`
   passes through `vars`/`set` freely, so this specific piece is
   compatible (nothing bake-specific blocks it) but the *assertion* logic
   (`ships_gcc_latest`, the smoke-test step that skips gcc-latest checks on
   arm64) is entirely this repo's own Python — unaffected either way.
5. **The `PLATFORM` single-source-of-truth discipline** (`no_platform_literals`
   gate, `platform_target.py` docstring) — the repo's `PUBLISHED_ARCHES`
   plan is generated at runtime (`dotfiles-setup platform-matrix`) into
   `plan.outputs.matrix`, consumed via `fromJSON` by every downstream job.
   `bake.yml`'s own `prepare` job does the equivalent (derive an `includes`
   matrix from the bake file's declared `platforms` + the `runner` mapping)
   but is driven by the bake FILE's `platforms` list, not by this repo's
   Python-owned `PUBLISHED_ARCHES` tuple — adopting bake.yml would mean the
   plan's source of truth moves from `platform_target.py` into
   `docker-bake.hcl`'s `dev` target's `platforms = ["${PLATFORM}"]"` (today
   single-valued, resolved via the `PLATFORM` env var per CI leg) unless
   restructured to declare BOTH platforms in one bake target and let
   `bake.yml`'s own matrix distribution replace the repo's hand-rolled
   `plan`/matrix-fan-out job. That is the crux of what "adopt bake.yml"
   would actually mean structurally (see §5).
6. **`dev-tag`/`manifest` job's own AC1/AC2 verification steps**
   (`build-publish.yml:1151-1225`) — assert the index lists every expected
   architecture and that each per-arch tag resolves to a distinct image,
   written as `dotfiles-setup image verify-arch-tags`. `bake.yml`'s
   `finalize` produces a `digest`/`signed` output but doesn't run
   repo-specific correctness assertions like this — would remain custom,
   layered after the reusable workflow call.
7. **Force-compression/zstd output flags via `PUSH` variable indirection**
   (`docker-bake.hcl:33-45`, the comment explaining why `push: true` is
   deliberately NOT used because it clobbers `output` list) — `bake.yml`'s
   own `push` input has the identical documented risk since it too likely
   sets an `output`/`--set` equivalent under the hood; this repo already
   worked around the analogous problem in `docker/bake-action` (the
   underlying action `bake.yml` itself wraps) by routing push through a
   bake-native variable instead of the action's `push:` shorthand. Whether
   `bake.yml`'s `push` input has the same clobbering behavior is unverified
   from the input schema alone (would require reading the `build` job's
   `docker/bake-action` invocation options, out of scope for this schema
   read) — **flag this as an integration risk to verify before any adoption**,
   since it is exactly the kind of repo-specific landmine this repo already
   hit once (#222) and `bake.yml`'s abstraction is one layer further removed
   from bake's native flags.

## 4. Real-world adopters — found via `gh search code`

Zero doubt about maturity: this is **not** an unproven zero-adopter project.
Confirmed real production adopters (not just docs mentions) via
`gh search code "docker/github-builder/.github/workflows"`:

- **`moby/moby`** — `.github/workflows/bin-image.yml` uses `bake.yml@v1.17.0`
- **`docker/compose`** — `.github/workflows/ci.yml` AND `merge.yml` use
  `bake.yml@v1.16.0`
- **`docker/cli`** — `.github/workflows/build.yml` uses `bake.yml@v1.17.0`
- **`moby/buildkit`** — `.github/workflows/buildkit.yml` AND
  `frontend.yml` use `bake.yml@v1.17.0`
- **`zizmorcore/zizmor`** — `.github/workflows/release-docker.yml` uses
  `build.yml@v1.17.0` (also has zizmor's own test fixtures that lint-check
  usages of this exact reusable workflow — i.e. the popular GHA security
  linter has first-class awareness of it)
- **`oxipng/oxipng`** — `.github/workflows/docker.yml` uses `build.yml@v1`
- **`luanti-org/luanti`** (formerly Minetest) — `docker_image.yml` uses
  `build.yml@v1`
- **`asterinas/asterinas`** — `publish_docker_images.yml` uses `build.yml@v1`
- **`OpenDroneMap/ODM`** — references it in `RELEASE.md` (build.yml)
- **`AFCMS/voxelibre-test`** — a Forgejo workflow referencing it via full URL

Notably, **Docker's own flagship projects** (buildkit, cli, compose,
moby itself) are the primary adopters — this is Docker dogfooding its own
reusable workflow on its highest-profile repos, which is a stronger
maturity signal than third-party adoption would be.

### How real adopters actually use it (read in detail)

**`docker/compose`** (`.github/workflows/ci.yml`) — TWO separate
`bake.yml` calls in one file:
- `binary` job: `cache: true`, `cache-scope: binary`, `target: release` —
  simple single-purpose cache scope, no platform suffix needed (compose's
  binary target apparently doesn't hit the same collision this repo's dual
  amd64/arm64 matrix does, or they simply haven't needed per-platform
  scoping yet).
- `bin-image-test` job: `target: image-cross`, `cache: true`,
  `cache-scope: bin-image-test`, PLUS a raw `set:` block overriding
  `*.cache-from=type=gha,scope=test` / `*.cache-to=type=gha,scope=test,
  mode=max` for a nested e2e matrix (`matrix.mode`/`matrix.channel`/
  `matrix.store`) that reuses `docker/bake-action` directly (not via
  `bake.yml`) for its own per-variant builds — i.e. compose mixes
  `bake.yml` for the main image build with a **direct** `bake-action` call
  for a large parametrized e2e test matrix, showing the reusable workflow
  is NOT treated as mandatory for every build in the pipeline; it's adopted
  selectively.

**`moby/buildkit`** (`.github/workflows/buildkit.yml`) — a `binaries-platforms`
job first computes a JSON platform matrix via `docker/bake-action/subaction/
matrix@…` (a small helper subaction, NOT `bake.yml` itself), THEN calls
`bake.yml` with `runner: ubuntu-24.04` (single static runner, no
per-platform mapping used here — they don't need arch-specific runners for
this target), `cache-scope: binaries`, `target: release`. A second
`bake.yml` call for `image-cross` builds against a JS-computed matrix
(`base`/`target` combos, e.g. rootless variants) with `cache-scope: image`
and per-leg `set:` overrides passing `IMAGE_TARGET`/`EXPORT_BASE`/
`BUILDKITD_TAGS` as bake vars through `${{ matrix.target }}` interpolation
— i.e. buildkit layers a CUSTOM JS-driven matrix (not `bake.yml`'s built-in
`runner` mapping) on top of the reusable workflow for its more complex
multi-variant image build, again proving partial/selective adoption is the
norm even among Docker's own repos, not "swap the whole pipeline."

## 5. Verdict

**Partial adoption fits; full replacement does not.**

- **The permutation-table problem `bake.yml` genuinely solves well**: the
  `runner` input's platform-prefix-matching mapping syntax is exactly the
  durable "add a new arch/OS-runner permutation without re-architecting"
  mechanism this repo is looking for (#736's actual ask), and it's the
  *documented, maintained, first-class* path (the default value literally
  demonstrates the arm64→specific-runner pattern). If this repo's own
  hand-rolled `PublishTarget`/`_RUNNER_LABELS` table
  (`platform_target.py:150-277`) were the only thing being replaced, this
  is a clean win — less code to maintain, same expressiveness, and a
  design Docker's own flagship repos already lean on.

- **But that table isn't the only thing doing work here.** This repo's real
  complexity — the three-tier content-hash probe cache that SKIPS entire
  jobs on a hit, the fully decoupled P2996 compiler-cache prerequisite
  stage, the post-build manifest-promotion logic in `ci.yml`'s `promote`
  job, and the AC1/AC2 index-correctness assertions — has **no counterpart**
  in `bake.yml`'s input schema. None of it is a gap in `bake.yml` (it's not
  trying to be a generic CI-caching framework); it's simply orthogonal to
  what a "build this bake target across N platforms, securely" reusable
  workflow does. Every real adopter examined (`compose`, `buildkit`)
  confirms this by NOT routing 100% of their build logic through it —
  they use it for the platform-fan-out + secure-build core and keep custom
  jobs/matrices around it for anything domain-specific.

- **Recommended shape, if adopted at all**: replace ONLY the runner-mapping
  table (`_RUNNER_LABELS` and the manual per-arch matrix job) with
  `bake.yml`'s `runner` input for the FINAL `build` job (the one bake-action
  call producing the published `dev` image), while keeping `base-prep`,
  `p2996-prep`, `dev-prep`, `promote`, and the AC1/AC2 assertions exactly as
  hand-rolled custom jobs feeding it prebuilt digest-pinned contexts via
  `set:` (which `bake.yml` passes through natively, same as
  `docker/bake-action` does today). This buys the maintained runner-mapping
  syntax for #736's ask without discarding any of the content-hash
  skip-logic that is this pipeline's actual competitive advantage (2m PR
  builds on a cache hit vs. a 20-30min cold rebuild). A full swap trades a
  system this repo deeply understands and controls (every failure mode
  documented in `AGENTS.md`) for a black-box "cannot be altered by user
  configuration" pipeline (README's own "Isolation & Reliability" framing —
  a stated SECURITY feature, but a genuine LOSS of the fine-grained control
  this repo's probe-cache logic depends on) whose cache/skip primitives
  don't reach the level of granularity (`docker manifest inspect`-probed,
  per-tier, job-skipping) this repo already built and relies on for its
  build-time budget.

- **Do not adopt for #736 alone via a big-bang migration.** The cheapest,
  lowest-risk path to #736's actual ask (route one arm64 leg to
  `ubuntu-26.04-arm`) is extending `_RUNNER_LABELS`/`PublishTarget` in
  `platform_target.py` directly (a few lines, matches the existing
  measured-not-assumed discipline already documented there) — not a
  dependency on an external reusable workflow whose adoption would touch
  every job in `build-publish.yml`.

## GitHub repos touched

- [docker/github-builder](https://github.com/docker/github-builder) — the subject: README + `bake.yml`/`build.yml` workflow_call schemas
- [docker/compose](https://github.com/docker/compose) — real-world adopter, read `.github/workflows/ci.yml` for actual bake.yml usage patterns (per-job cache-scope, mixed direct-bake-action + bake.yml usage)
- [moby/buildkit](https://github.com/moby/buildkit) — real-world adopter, read `.github/workflows/buildkit.yml` for JS-driven matrix layered on top of bake.yml
- [moby/moby](https://github.com/moby/moby) — confirmed adopter via code search (`bin-image.yml`), not read in depth
- [docker/cli](https://github.com/docker/cli) — confirmed adopter via code search (`build.yml`), not read in depth
- [zizmorcore/zizmor](https://github.com/zizmorcore/zizmor) — confirmed adopter (`release-docker.yml`) + ships test fixtures asserting against this exact reusable workflow's pinned-ref conventions
- [oxipng/oxipng](https://github.com/oxipng/oxipng), [luanti-org/luanti](https://github.com/luanti-org/luanti), [asterinas/asterinas](https://github.com/asterinas/asterinas) — confirmed adopters via code search, not read in depth
- ray-manaloto/dotfiles (this repo) — read `docker-bake.hcl`, `.github/workflows/build-publish.yml`, `.github/workflows/ci.yml` (promote job), `python/src/dotfiles_setup/platform_target.py`, `.github/workflows/AGENTS.md` for comparison baseline
