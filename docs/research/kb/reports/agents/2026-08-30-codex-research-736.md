# Research: #736 permutation-matrix design (arm64/ubuntu-26.04 3rd build leg)

## 1. Docker Bake permutation/matrix targets

Buildx Bake supports a native `matrix` block on a `target`, introduced in **buildx v0.11.0** (`docker/buildx` release notes). This repo's pinned tool is `docker-cli = "29.7.2"` in `mise.toml:71` (no separate buildx pin — buildx ships as the docker CLI plugin); the actually-installed local buildx is **v0.36.1** (`docker buildx version`). Both are far past v0.11.0, so the matrix feature is available with no tool bump.

Syntax (confirmed via docs.docker.com/build/bake/reference/):

```hcl
target "app" {
  name = "app-${tgt}-${replace(version, ".", "-")}"
  matrix = {
    tgt     = ["foo", "bar"]
    version = ["1.0", "2.0"]
  }
  target = tgt
  args = {
    VERSION = version
  }
}
```

Each key in `matrix` is a list; Bake generates one target per element of the **cross product** of all keys (2×2 = 4 targets in the example). `name` must reference every matrix variable (directly or via a derived local) so the generated target names are unique — Bake errors if two permutations resolve to the same name.

**Applied to #736's 3-leg (not full cross-product) matrix**: the acceptance criteria explicitly want amd64 pinned to ubuntu-24.04 only (2 of the 3 legs share one axis value), so a literal 2×2 `matrix = { arch = [...], ubuntu = [...] }` cross product would generate a 4th `amd64×ubuntu-26.04` target that must never build. Two implementation options, both compatible with the existing bake file's `dev`/`base`/`p2996-cache` structure:

- **Option A — explicit permutation list, not `matrix`.** Keep three separate `target` blocks (or a `group` naming three targets), each inheriting from `_common`/`dev` and setting its own `PLATFORM`/`BASE_IMAGE`/tag args. This is closer to the current one-target-per-CI-matrix-leg shape (`PLATFORM` is already resolved per-CI-job via env, not per-Bake-target) and avoids Bake ever being asked to enumerate a permutation that must not exist.
- **Option B — `matrix` with a pre-filtered permutation list.** Bake also supports feeding `matrix` a **list of objects** rather than independent lists per key, e.g. `matrix = { include = [{arch="amd64",ubuntu="24.04"},{arch="arm64",ubuntu="24.04"},{arch="arm64",ubuntu="26.04"}] }` (mirrors GitHub Actions' `matrix.include` idiom) — this generates exactly 3 targets, no forbidden 4th permutation, no post-filtering needed. This is the closer match to the issue's "generalized … Bake permutation scheme" language and avoids hand-duplicating 3 near-identical target blocks.

Given today's CI shape (`python/src/dotfiles_setup/platform_target.py`'s `PublishTarget`/`published_targets()` already drives the CI-side fan-out, and `PLATFORM` is a bake **variable**, not a matrix axis, read from the environment per-job — see docker-bake.hcl:19-31), the CI workflow is *already* doing the fan-out at the GitHub Actions matrix level, one `docker/bake-action` invocation per (arch × ubuntu-version) leg with `PLATFORM`/a new `UBUNTU_VERSION`-equivalent env var set per job. In that shape Bake itself never needs its own `matrix` block — each CI job bakes exactly one target (`dev`) with variables resolved from that job's leg. **Bake-native `matrix` only becomes relevant if the intent is to also let a human run `docker buildx bake dev-load` locally and get all 3 (or a chosen subset) images in one invocation** — worth clarifying with Ray before choosing between "keep bake single-target, extend the Python-side `PublishTarget` table to 3 legs and 3 CI jobs" (matches the issue's own instruction to add the axis to `platform_target.py`, not to `docker-bake.hcl`) vs. "add a real Bake `matrix`/`group`". The issue's own rollout step 1 ("via an OS+blocking dimension added to `PublishTarget`") points at the Python-side table, not a Bake-native matrix — Bake's per-job `PLATFORM`/`BASE_IMAGE` variables stay exactly as they are today, and the 3rd leg is just a 3rd CI matrix entry.

## 2. Every repo-wide consumer of `:dev-amd64` / `:dev-arm64`

`git grep -n 'dev-amd64\|dev-arm64' -- .` (excluding `docs/research/`, which is out of scope per `agent-artifact-conventions.md`):

- `.github/workflows/ci.yml:539` — comment inside the `promote` job's per-arch retag loop: `# also what the tag should mean: :dev-amd64 IS the amd64 image,`. The **actual code** producing the tags is at ci.yml around line 520-545 (see §3 below) — it derives the arch list from the published index's manifest platforms and does `docker buildx imagetools create --prefer-index=false --tag "${IMAGE}:dev-${arch}" "${IMAGE}@${digest}"` per architecture.
- `docs/specs/devcontainer-gcc162-dual-arch.md` — five hits (lines 111, 202-203, 206-207, 874, 998), all **historical spec prose** describing the design that shipped the current 2-tag scheme (D1: `:dev` manifest + `:dev-amd64`/`:dev-arm64` per-arch tags). Per `agent-artifact-conventions.md`, `docs/specs/` content is durable design history, not live code — it should **not** be edited in place to match the new `:dev-<arch>-ubuntu<version>` scheme (that would falsify a design record of what was actually decided/built at the time); #736's own spec should instead record the *supersession* explicitly (a new spec or an addendum noting D1 is superseded by the new tag scheme), consistent with how `docs/rules-evidence/` and spec files elsewhere in this repo treat prior decisions as append-only.

**No other repo-wide consumer was found** — `mise run sync`, `dev-rebuild`, and the devcontainer's pin machinery (`python/src/dotfiles_setup/platform_target.py`, `mise.toml`) do **not** reference `:dev-amd64`/`:dev-arm64` literally; they resolve architecture through `PublishTarget.tag_suffix` (`platform_target.py:252,276`, currently `tag_suffix=arch`, i.e. exactly `"amd64"`/`"arm64"`) and the `mise.local.toml` pin documented in the spec (`mise.local.toml pin → :dev-arm64`). This means **the tag_suffix field is the one true generalization point**: today `tag_suffix=arch` (`platform_target.py:276`); for #736 it needs to become something like `tag_suffix=f"{arch}-ubuntu{ubuntu_version}"` once `PublishTarget` grows an `os_version` (or similar) field, and every reader of `tag_suffix` (only `promote`'s retag loop and any doc/spec prose) inherits the new scheme automatically without further code changes. **This is a materially smaller blast radius than the issue text's phrasing ("every existing consumer … updated") suggests** — there is exactly one live code consumer (ci.yml's `promote` job) plus one historical doc that should be left alone (superseded, not rewritten).

## 3. `ci.yml`'s `promote` job — current logic and what changes

Read in full at `.github/workflows/ci.yml:381-560` (see the "Retag PR image as :dev and :latest" step, ~477-548). Current flow:

1. GraphQL-resolve the merge commit's source PR number (fallback to a rebuild-dispatch if none).
2. Probe `docker buildx imagetools inspect "${IMAGE}:pr-${PR_NUMBER}"` for the PR-built manifest-list digest (`source_digest`).
3. `docker buildx imagetools create --tag :dev --tag :latest "${SOURCE_REF}"` — a **tag-only** retag (no rebuild) of the multi-arch **index** onto `:dev`/`:latest`.
4. Verify both new tags resolve to `source_digest`.
5. **Per-arch retag loop** (the part #736 changes): `raw=$(docker buildx imagetools inspect "${SOURCE_REF}" --raw)`, then
   ```bash
   while read -r arch digest; do
     docker buildx imagetools create --prefer-index=false \
       --tag "${IMAGE}:dev-${arch}" "${IMAGE}@${digest}"
     ...
   done < <(printf '%s' "${raw}" | jq -r \
     '.manifests[] | select(.platform.os != "unknown") | "\(.platform.architecture) \(.digest)"')
   ```
   This derives the tag list **from the real published OCI index** (self-describing, anti-drift by construction — the code comment at ci.yml:531-539 explains exactly why: `--prefer-index=false` is load-bearing, and the loop iterates whatever architectures the index actually contains, filtering out `os=="unknown"` attestation entries).

**What #736 needs, precisely stated**: the issue's rollout step 4 says tags should be "derived from a **static/Bake-matrix permutation table** rather than introspecting the published index — this intentionally trades the index's built-in anti-drift tag derivation for permutation flexibility." That is a deliberate, named trade-off, because **the index's manifest list has no OS-version axis** (an OCI image index's `platform` object is `{os, architecture, variant, os.version, os.features}` — Docker's own manifest-list producer only ever sets `os`/`architecture`/`variant`, not `os.version`, for these builds) — so introspecting the index can produce `arch` (`amd64`/`arm64`) but **cannot** recover which Ubuntu version a given manifest was built from. Concretely:

- The `jq` selector `.manifests[] | select(.platform.os != "unknown") | "\(.platform.architecture) \(.digest)"` must become a **3-row static table** (or one sourced from `python/src/dotfiles_setup/platform_target.py`'s generalized `PublishTarget`, e.g. `publish_matrix_json()` extended with an `os_version`/`tag_suffix` field) mapping `{arch, ubuntu_version} → tag_suffix`, with each row's digest resolved separately — because **only 2 of the 3 legs join the published `:dev` index** (issue rollout step 2: `arm64/ubuntu-26.04` is excluded from the manifest while non-blocking), the loop can no longer assume every tag it emits comes from the same `${SOURCE_REF}` index inspection.
- Concretely this likely means: for the 2 manifest-joining legs (`amd64/ubuntu-24.04`, `arm64/ubuntu-24.04`), keep deriving `{arch, digest}` from the real index exactly as today (this is the "still tag the 2 manifest-joining images correctly from the real published index digest" the issue's own research-question wording anticipates) — but resolve the tag **suffix** for each from the static table instead of the bare `${arch}` string (`dev-amd64` → `dev-amd64-ubuntu24.04`, `dev-arm64` → `dev-arm64-ubuntu24.04`). For the 3rd leg (`arm64/ubuntu-26.04`, non-manifest-member), the promote job needs an **independent digest source** — most likely its own PR-build tag (e.g. `:pr-<NNN>-arm64-ubuntu26.04`, produced by that leg's own `continue-on-error` CI job) probed and retagged separately, since it is by design absent from `${SOURCE_REF}`'s index.
- The `verify_arch_tags` reference (issue AC row 8) and `find_lock_platform_drift`/lock-image regeneration (`platform_target.py:606-639`, keyed on bare `PUBLISHED_ARCHES` today) both need the same blocking/manifest-membership filter described in the issue: `PUBLISHED_ARCHES = ("amd64", "arm64")` (`platform_target.py:152`) currently conflates "published in the index" with "every architecture this repo builds" — #736 needs a **new** notion (e.g. a `manifest_member: bool` or `blocking: bool` field on `PublishTarget`, or a second tuple like `MANIFEST_ARCHES`/`BLOCKING_TARGETS` distinct from `PUBLISHED_ARCHES`/`ALL_TARGETS`) so `mise_lock_platforms()`, `find_lock_platform_drift()`, and any `_RUNNER_LABELS`/`GCC_LATEST_ARCHES`/`LLVM_TARGETS`/`_MISE_LOCK_PLATFORM` table keyed by bare arch string can still express "arm64 has 2 rows now" without arch remaining a unique key.

## 4. LLVM/clang Renovate coverage — suite-23 status

**Confirmed, both premises correct as stated:**

- `renovate.json:56` pins `https://apt.llvm.org/resolute?suite=llvm-toolchain-resolute-22&components=main&binaryArch=amd64` — a **hardcoded suite number** ("22") inside the `apt-ubuntu-pockets` registryUrls list.
- `renovate.json:175`'s `customType: regex` manager (`managerFilePatterns: .devcontainer/mise-system.toml`) matches `"apt:(?<depName>...)" = "(?<currentValue>[0-9]...)"` entries and resolves them via the `deb` datasource — it tracks **patch/version bumps of packages already pinned inside whatever suite the registryUrl above points at**. It has no mechanism to change *which* suite (`-22` → `-23`) is queried; that string is a plain literal in the registryUrl, invisible to the regex manager entirely.

**Is `llvm-toolchain-resolute-23` published yet?** **No, not at the time of this research (2026-08-29).** Live-fetched `https://apt.llvm.org/` lists only `llvm-toolchain-resolute` (dev/trunk), `llvm-toolchain-resolute-21`, and `llvm-toolchain-resolute-22` for the resolute (26.04) distribution; the site states apt.llvm.org's policy is to carry "the last 2 LLVM releases" per distro, so **22 is currently the highest packaged LLVM for resolute**. A `discourse.llvm.org` thread titled "Why llvm 23 still not downloadable from apt.llvm.org?" (found via search, not independently fetched — treat as a corroborating signal, not primary evidence) is consistent with this. LLVM 23.1.0 (the release the user named, https://github.com/llvm/llvm-project/releases#release-llvmorg-23.1.0) is out upstream, but apt.llvm.org has not yet cut a `-23` Debian/Ubuntu suite for it as of this research.

**Pending Renovate PRs**: `gh pr list --search "llvm OR clang" --state open` returned **zero matches**. The only two open PRs in the repo are `#822` (`chore(deps): update all dependencies`, branch `renovate/all`) and `#821` (`chore: refresh lockfiles`, branch `chore/lock-refresh`) — neither is LLVM/clang-specific by title, and neither can be an "advance the suite" PR regardless, since the regex manager (§ above) is structurally incapable of producing one.

**What edit is needed:** none *yet*, because there is nothing at `-23` to point at. When apt.llvm.org does publish `llvm-toolchain-resolute-23`, the fix is a **manual one-line edit** to `renovate.json:56` (and its three sibling Ubuntu-pocket URLs stay unaffected, they don't encode an LLVM suite number) bumping `-22` → `-23` — this is exactly the kind of edit `renovate.json:56`'s own inline comment structure anticipates (a hardcoded suite baked into a registryUrl, not managed by the tool). Recommend tracking this as a follow-up ticket gated on the suite's actual publication, not bundled into #736's build-matrix work (the issue's own "Notes" section already says compiler currency is tracked separately, citing #243 for GCC — an equivalent LLVM-currency ticket, gated on `apt.llvm.org` publishing `-23`, is the natural sibling; #736 itself should not touch `renovate.json:56`).

## 5. conda-forge GCC 16.2 availability

**Confirmed available.** Live-fetched `anaconda.org/conda-forge/gxx` and `anaconda.org/conda-forge/gxx_linux-aarch64`:

- `gxx` (noarch activation package) latest version: **16.2.0**, published **2026-08-25**. Recent version history: 16.2.0, 16.1.0, 15.3.0, 15.2.0, 15.1.0.
- `gxx_linux-aarch64` (the actual aarch64 build) also latest: **16.2.0**, same publish date. `linux-64`, `linux-aarch64`, `linux-ppc64le`, `linux-riscv64`, `win-64`, `osx-64`, `osx-arm64` are all listed as supported platforms (linux-s390x dropped as of 14.2.0 — not relevant here).

This directly matches the code comment already in `.devcontainer/mise-system.toml:56-59` (`#698/D31: conda-forge gxx fills arm64's modern-GCC slot … 204 files at 16.1.0, identical coverage to linux-64` — that comment is now stale by one minor version; 16.2.0 supersedes the 16.1.0 the comment cites, and coverage remains identical across linux-64/linux-aarch64).

**Correct mise TOML value**: since `mise-system.toml:59` currently pins `"conda:gxx" = "latest"` (floating), and the user wants an explicit pin, the correct literal is:

```toml
"conda:gxx" = "16.2.0"
```

(conda-forge's own version strings for this package are plain `MAJOR.MINOR.PATCH`, e.g. `16.2.0` — not a fuller build-string form; mise's conda backend resolves `"gxx" = "16.2.0"` against the same conda-forge channel index this fetch queried.) Confirm mise's conda backend accepts a bare `MAJOR.MINOR.PATCH` for this package name specifically (not independently re-verified here beyond the general mise-conda pin pattern already used elsewhere in this file) before merging — a quick `mise install` dry run against the pin is the local control-arm per `local-devcontainer-first.md`.

**Not in scope for #736 per the dispatch's own explicit premise L3/L4**: `.devcontainer/Dockerfile:571`'s `GCC_LATEST_DEB` (kayari.org rolling snapshot, amd64-only, Renovate-managed via a custom HTML datasource) is a **separate GCC installation** from the conda-forge one and is untouched by this change.

## 6. ubuntu-26.04-arm known issues (`actions/runner-images`)

Live-fetched the readme (`images/ubuntu/Ubuntu2604-Arm64-Readme.md`) plus `gh issue list --repo actions/runner-images --search "26.04 arm64"` / `"ubuntu-26.04-arm"` (`--state all`):

- **Docker/BuildKit versions on the runner itself**: Docker Client/Server **29.4.2**, Docker Compose **5.1.3**, **Docker-Buildx 0.36.1** — comfortably past the v0.11.0 matrix-feature floor from §1, and the exact same buildx version this Mac's local `docker buildx version` reports, so no version-skew risk for anything Bake-matrix-related.
- The readme itself carries **no explicit ARM64-specific caveats** and does not enumerate mise/uv/hk/Pkl (those are installed by this repo's own devcontainer bootstrap, not preinstalled on the GitHub runner, so their absence from the readme is expected, not a gap).
- **Runner status**: GitHub currently lists `ubuntu-26.04-arm` as issue **#14226** ("[Ubuntu] Ubuntu 26.04 and Ubuntu 26.04 Arm is now available as a public preview", OPEN, still receiving comment activity as of 2026-08-30) — consistent with the issue body's own "Public preview" framing and its non-blocking rollout requirement (step 2/3).
- **One CLOSED issue specific to this runner**: **#14549**, "[ubuntu-26.04-arm] /dev/kvm device node missing on Ubuntu 26.04 ARM runner" (closed 2026-08-12). `/dev/kvm` is relevant to *nested virtualization* (e.g. Android emulator, QEMU-KVM acceleration) — **not** to a Docker/BuildKit image build, and it's already closed/fixed, so it does not block #736's rollout. No open issue found naming Docker, BuildKit, mise, uv, hk, or Pkl incompatibilities on `ubuntu-26.04-arm` specifically.
- **One OPEN issue on Ubuntu 26.04 (not arm-specific)**: **#14647**, "Ubuntu 26.04 image build fails in install-azure-cli.sh: azure-cli package not found for resolute" (OPEN, filed 2026-08-30, `needs triage`) — Azure CLI install step, unrelated to this repo's own image build (this repo never installs azure-cli in the devcontainer Dockerfile per the files read for this research), so it is not expected to block #736 either, but worth a one-line note in the ticket in case GitHub's `ubuntu-26.04-arm` runner image itself is affected by whatever produces this failure (unclear from the issue title alone whether it is amd64-only).
- No other open/closed issue matched a Docker/BuildKit/mise/uv/hk/Pkl compatibility problem specific to `ubuntu-26.04`/`ubuntu-26.04-arm` at the time of this research.

**Overall assessment**: nothing found in the runner-images tracker blocks #736's rollout; the one closed issue (`/dev/kvm`) is irrelevant to image builds, and the one open non-arm-specific issue (`azure-cli`/resolute) is unrelated to this repo's toolchain. Re-run this search closer to promoting the leg to blocking (per the issue's own gate: "only once GitHub marks the runner generally available"), since Public Preview runners are actively being patched (issue #14226's own comment velocity suggests ongoing changes).

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue #736 body, `platform_target.py`, `docker-bake.hcl`, `ci.yml` promote job, `renovate.json`, `.devcontainer/mise-system.toml`, `.devcontainer/Dockerfile`, open PR list (#821/#822)
- [docker/buildx](https://github.com/docker/buildx) — matrix feature introduction (v0.11.0 release notes, via search) and installed local version (`docker buildx version` → v0.36.1)
- [llvm/llvm-project](https://github.com/llvm/llvm-project) — release 23.1.0 tag referenced by the user; issue #188999 (apt.llvm.org resolute enablement) surfaced via search, not independently fetched
- [actions/runner-images](https://github.com/actions/runner-images) — `Ubuntu2604-Arm64-Readme.md` (fetched), issue search for ubuntu-26.04/-arm compatibility (issues #14226, #14549, #14647, #14647 read via `gh issue list`)
- [conda-forge/ctng-compiler-activation-feedstock](https://github.com/conda-forge/ctng-compiler-activation-feedstock) — surfaced via search as the feedstock behind `gxx`/`gxx_linux-aarch64`; not independently fetched (anaconda.org package pages were fetched directly instead and are the primary evidence for §5)

## Unresolved / needs a follow-up read before spec-writing

- Whether Bake should get a real `matrix`/`group` block (§1 Option B) or stay single-target with the 3-leg fan-out entirely at the GitHub Actions matrix + `platform_target.py` level (§1's closing paragraph) — the issue text is compatible with both; recommend confirming with Ray before the spec commits to one, since it changes how much of `docker-bake.hcl` vs. `platform_target.py` gets edited.
- The exact mechanism for retagging the non-manifest-member 3rd leg in `promote` (§3) — whether its source digest comes from a per-leg PR tag, a separate workflow output, or something else — depends on how the base-prep/p2996-prep/build/smoke-test/dev-tag steps for the new leg are wired into `build-publish.yml`'s existing 6-step-per-architecture fan-out (#676), which this research did not read in full (only `ci.yml`'s `promote` job was read in depth per the dispatch's file list; `build-publish.yml`'s per-leg step sequence needs a dedicated read before the spec finalizes the promote-job rewrite).
- mise's conda backend's acceptance of a bare `16.2.0` pin for `gxx` was not verified with an actual `mise install`/`mise lock` dry run in this session (read-only research task) — flag this as the first thing to control-arm once implementation starts.
