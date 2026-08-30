# Research: Docker Buildx Bake feature set for #736 (3rd build leg: arm64/ubuntu-26.04)

## Premise re-verification (A1)

Re-read `.github/workflows/build-publish.yml` myself (not trusting the prior
report). A1 is CONFIRMED, with the mechanism spelled out:

- `plan` job (build-publish.yml:97-126) calls
  `uv run --project python dotfiles-setup platform-matrix` (→
  `platform_target.publish_matrix_json()`, `python/src/dotfiles_setup/platform_target.py:285-298`)
  and writes the JSON list to `steps.matrix.outputs.matrix` →
  `outputs.matrix` (build-publish.yml:103).
- Every fan-out job (`base-prep` build-publish.yml:135-144, `p2996-prep`:273-278,
  `dev-prep`:424-430, `build`:515-531, `smoke-test`:962-973) declares its OWN
  `strategy: { fail-fast: false, matrix: { target: ${{ fromJSON(needs.plan.outputs.matrix) }} } }`
  and `runs-on: ${{ matrix.target.runner }}` — a genuine GitHub Actions
  `strategy.matrix`, not a Bake construct.
- Each leg exports `PLATFORM: ${{ matrix.target.platform }}` as a job env var
  (e.g. build-publish.yml:156, 283, 436, 539, 979). `docker-bake.hcl`'s
  `variable "PLATFORM"` (line 29) reads that SAME-NAMED env var (bake's
  documented environment-variable-as-default behavior), so `target "dev"`
  (docker-bake.hcl:121, via `_common.platforms = ["${PLATFORM}"]` at line 106)
  builds exactly one platform per GHA matrix leg, on a runner NATIVE to that
  architecture (`platform_target._RUNNER_LABELS`,
  `python/src/dotfiles_setup/platform_target.py:160`: `amd64→ubuntu-latest`,
  `arm64→ubuntu-24.04-arm`).
- `docker-bake.hcl` itself has **zero** occurrences of `matrix`, `for`, or
  `dynamic` (confirmed: `grep -n "matrix\|dynamic\|for_each" docker-bake.hcl` →
  no hits outside comments). The `AGENTS.md` note "A matrix job has ONE
  `outputs` map — last leg wins" (`.github/workflows/AGENTS.md` § "Dual-
  architecture publish (#676)") documents exactly this GHA-level fan-out and
  its consequence (no job `outputs` on the prep jobs; each leg recomputes its
  own content-hash deterministically from `PLATFORM`).

So: the existing 2-leg build needs no `docker-bake.hcl` matrix/group change,
confirmed independently, not merely inherited from the earlier pass.

## Q1 — what buildx version does `docker/setup-buildx-action@v4.3.0` install?

Pinned at build-publish.yml:228,376,472,588,991,1089 (SHA
`37fe631027851001ddb9b187196cc803df7f5f0e` = `v4.3.0`). None of the 6 call
sites pass a `version:` input (confirmed: `grep -n -A3
"setup-buildx-action@37fe" .github/workflows/build-publish.yml` shows no
`with: version:` block on any of them).

Read the action's own source at that pinned SHA
(`github.com/docker/setup-buildx-action` — `action.yml`, `src/main.ts`,
`src/context.ts`):

- `action.yml` declares `version` as `required: false` with **no default**
  (`raw.githubusercontent.com/docker/setup-buildx-action/37fe631.../action.yml:11-13`).
- `src/context.ts:120-132` (`getVersion`): for the non-cloud driver (this
  repo's case — no `driver: cloud` input anywhere), `getVersion` returns
  `inputs.version` verbatim — i.e. an empty string when unset.
- `src/main.ts:47-60`: `Util.isValidRef(version)` is false for an empty
  string, so the "build buildx from source" branch is skipped; the download
  branch fires (`!(await toolkit.buildx.isAvailable()) || version`) and calls
  `toolkit.buildxInstall.download({ version: version || 'latest', ... })` —
  **`'latest'` is the literal fallback in the source**, at
  `raw.githubusercontent.com/docker/setup-buildx-action/37fe631.../src/main.ts:54`.

So: no `version:` input ⇒ the action downloads the **latest GitHub Release**
of `docker/buildx` at the time each CI run executes. Queried live
(`api.github.com/repos/docker/buildx/releases/latest`, 2026-08-29):
**`v0.36.1`** (a v0.37.0-rc1 pre-release exists but `/releases/latest` — which
is what the toolkit's "latest" resolution walks — correctly skips
pre-releases). This means the buildx version on CI runners is NOT pinned by
this repo and drifts upward on every new buildx release — the feature-set
answer below (Q2-Q4) is therefore "as of buildx ~v0.36.x, and whatever ships
next since nothing here freezes it."

## Q2 — Bake's relevant feature set, target-by-target verdict

Fetched the official Bake file reference
(`docs.docker.com/build/bake/reference/` via its `.md` mirror, current as of
2026-08-29) and read every section named below in full.

**`target.matrix`** (`docs.docker.com/build/bake/reference/#targetmatrix`):
forks ONE target into multiple targets inside a SINGLE `docker buildx bake`
invocation — a map of parameter names to lists of values, each combination
becomes a distinct generated target (name resolved via `target.name`), and
Bake assembles them into an implicit `group`. **This is the mechanism the
earlier codex-implementer pass correctly judged unnecessary**, and the
verdict extends cleanly to #736's 3rd leg: a `matrix` block still only
produces multiple targets that ONE invocation on ONE machine builds — it does
not, and cannot, cause different targets to run on different GHA runners.
Bake has no concept of "runner" or "which machine" at all; that's entirely a
GitHub Actions concern. Using `target.matrix` here would mean either (a) one
`bake` call cross-building arm64 on an amd64 runner via QEMU emulation — which
`platform_target.py:154-160`'s own comment explicitly rules out for the
~2h clang-p2996/GCC compile ("Native is the whole ruling... paid on emulated
CPU"), or (b) still needing a GHA-level fan-out to get one `bake --set
matrix.target=...` invocation per native runner, at which point the GHA
`strategy.matrix` is doing 100% of the real work and the Bake `matrix` block
adds a layer of indirection with no benefit. **Redundant.**

**HCL `for`/`dynamic` expressions**: Bake's HCL has NO Terraform-style
`dynamic` block. Full-text search of the reference doc (1533 lines) for
`dynamic` and `for_each` returns zero hits; the closest thing to
programmatic generation is precisely `target.matrix` above, plus ordinary HCL
`for` **expressions** inside a value (e.g. `[for p in PLATFORMS : "linux/${p}"]`
composing a list) — usable to build `platforms = [...]` for a single
cross-compiling target, not to fan a target across runners. **Not
applicable** to the runner-per-arch problem for the same reason as `matrix`.

**`group` blocks** (`docs.docker.com/build/bake/reference/#group`, lines
1114-1153): a `group` just names a set of targets to invoke together
(`docker buildx bake <group>` == building all its targets, still one
invocation, one machine). It's an aggregation convenience, not a
distribution mechanism — same verdict: doesn't help place a build on a
different runner. **Redundant for this use case.**

**Target inheritance** (`target.inherits`, already used in
`docker-bake.hcl:103-149` — `dev`/`base`/`p2996-cache` all `inherits =
["_common", ...]`): this is exactly the mechanism a 3rd leg would keep using —
a new `target "dev-2604"` (or similar) inheriting `_common` with a different
`BASE_IMAGE` (ubuntu 26.04 pin) would follow the SAME pattern already in the
file. No new Bake feature needed here either — it's the existing idiom,
reused.

**`--metadata-file` / `target.annotations` for multi-platform index
assembly** (`docs.docker.com/build/bake/reference/#targetannotations`, lines
284-314): `target.annotations` lets Bake attach OCI annotations at `index`
and/or `manifest` level within ONE target's output — it does not merge
outputs of separate `bake`/CI-job invocations into one index. This repo does
NOT use Bake for that step at all today: `ci.yml`'s `promote` job (lines
~440-520) builds the cross-arch `:dev`/`:latest` index with **`docker buildx
imagetools create`**, reading each per-arch digest out of the source PR's
already-published index and re-tagging (`ci.yml` promote step "Retag PR image
as :dev and :latest"). That stays true for a 3rd leg exactly as today —
`imagetools create` is the tool that assembles/republishes a manifest list
from independently-built per-arch images, regardless of how many legs fed it,
and it already lives entirely outside `docker-bake.hcl`.

## Q3 — Recommendation: does any Bake-level change earn its complexity for #736?

**No.** Add a 3rd GitHub Actions matrix entry — same `dev` Bake target,
`PLATFORM=linux/arm64/v8`, a `runs-on` for an arm64/26.04-capable runner —
exactly mirroring how the existing 2 legs work. None of Bake's `matrix`,
`group`, `for`, or `platforms`-list mechanisms solve a problem this repo
actually has, because every one of them operates WITHIN a single `bake`
invocation on a single machine, and the entire reason for the current
GHA-level `strategy.matrix` (per `platform_target.py:154-160` and
`.github/workflows/AGENTS.md` "Dual-architecture publish (#676)") is to get
each architecture onto its OWN **native** runner so the ~2h clang-p2996/GCC
compile never runs emulated. A Bake-level matrix would either reintroduce
emulation (defeating the whole reason #676 rejected it) or be a pure no-op
wrapper around a GHA matrix that's already doing all the real work.

The two things #736 actually needs — (1) manifest-**exclusion** (a
26.04-built `linux/arm64` image must NOT silently merge into the existing
`:dev` index next to the 24.04-built `linux/arm64` image, since OCI platform
tuples have no OS-version axis and two `linux/arm64` entries in one index
platform-collide) and (2) OS-qualified tagging — are BOTH handled entirely
outside Bake today, in `ci.yml`'s `promote` job via `docker buildx imagetools
create`/`inspect` (the per-arch-tag loop at ci.yml ~lines 490-520 already
demonstrates the pattern: it reads the index's own manifest list via
`imagetools inspect --raw` and creates DISTINCT per-architecture tags with
`--prefer-index=false`). The natural #736 shape is:

- a 3rd `PublishTarget`-like entry (or a parallel, EXCLUDED-from-the-main-
  matrix list) in `platform_target.py` naming its own runner and a distinct
  `tag_suffix` (e.g. `arm64-2604`) so it never collides with the existing
  `arm64` per-arch tag;
- the SAME `docker-bake.hcl` `dev` target, `PLATFORM=linux/arm64/v8`,
  `BASE_IMAGE` overridden to the 26.04 digest for that leg only (a bake
  `--set dev.args.BASE_IMAGE=...` or a distinct inheriting target, per the
  existing `inherits` idiom above — NOT a `matrix` block);
- the `manifest`/`promote` step's `docker buildx imagetools` calls simply
  never fold this leg's digest into the `:dev`/`:latest` index — it gets its
  own OS-qualified tag(s) only, same mechanism as today's `:dev-<arch>` tags.

None of that touches Bake's feature set beyond what's already in
`docker-bake.hcl`.

## Q4 — Newest Buildx/Bake releases: anything relevant to multi-OS-version image matrices or manifest-list assembly?

Queried `api.github.com/repos/docker/buildx/releases` (2026-08-29) and read
the release notes for the current latest (`v0.36.1`) and the three prior
minors (`v0.36.0`, `v0.35.0`, `v0.34.0`) in full:

- **v0.36.1**: one notable change — `BUILDX_NO_DEFAULT_OCI_ARTIFACT` env-var
  alias. Not relevant.
- **v0.36.0**: source-policy authenticity validation, bake secret-source
  overrides, `BUILDX_BAKE_FILE_RELATIVE_PATHS`, imagetools descriptor
  validation, Windows binary signing, Kubernetes-driver fixes. Nothing about
  OS-version axes or manifest-list assembly.
- **v0.35.0**: local-output `mode=delete`, source-policy exec-proxy capture,
  `--resource` CPU/memory limits for build/bake. Not relevant.
- **v0.34.0**: default source policy for `docker/dockerfile`/SBOM-scanner
  images, `bake --policy` flag, Kubernetes-driver persistent storage. Not
  relevant.

None of the last four Buildx minor releases shipped anything touching
multi-OS-version image matrices, manifest-list/index assembly, or an
OS-version-aware platform concept. The `target.platforms` attribute and OCI
platform tuple (`os/arch[/variant]`) are unchanged — there is still no
OS-version field in a platform string, which is the structural reason #736's
3rd leg cannot become a 2nd `linux/arm64` entry in the SAME manifest list and
must ship as a separately-tagged image, exactly as reasoned in Q3.

## GitHub repos touched

- [docker/setup-buildx-action](https://github.com/docker/setup-buildx-action) — read `action.yml`, `src/main.ts`, `src/context.ts` at the pinned SHA (`37fe631027851001ddb9b187196cc803df7f5f0e` = v4.3.0) to determine the default buildx version resolution (Q1)
- [docker/buildx](https://github.com/docker/buildx) — queried the Releases API (`/releases/latest`, `/releases/tags/{v0.36.0,v0.35.0,v0.34.0}`) for current version and recent release notes (Q1, Q4)
- Docker docs (`docs.docker.com/build/bake/reference/`) — full Bake file reference: `target.matrix`, `target.name`, `group`, `target.inherits`, `target.annotations`, `target.platforms` (Q2, Q3)
