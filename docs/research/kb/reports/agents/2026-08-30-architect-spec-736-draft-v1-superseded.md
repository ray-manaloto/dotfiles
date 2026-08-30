# Spec: #736 — permanent arm64/ubuntu-26.04 build leg, OS-qualified image tags

## 1. Objective

Add `arm64/ubuntu-26.04` as a 3rd, permanent build leg alongside the existing
`amd64/ubuntu-24.04` and `arm64/ubuntu-24.04` legs (issue
https://github.com/ray-manaloto/dotfiles/issues/736), and retag all 3
published images to an OS-qualified scheme (`:dev-<arch>-ubuntu<version>`).

Prevent three specific failure scenarios:

- **A Public Preview runner blocking every merge in the repo.** The new leg
  must run `continue-on-error` and be excluded from the required-checks set
  until a human flips it to blocking (see §4 "Promotion is manual, not
  automated" — do not build automatic promotion-tracking machinery).
- **A broken cross-arch manifest.** OCI image indexes have exactly one entry
  per platform tuple (`os/arch`, no OS-version axis) — a 2nd `linux/arm64`
  entry from ubuntu-26.04 MUST NOT be added to the `:dev` manifest that
  `amd64/ubuntu-24.04` + `arm64/ubuntu-24.04` publish to. This is a structural
  constraint, not a policy choice: `docker buildx imagetools inspect`/`create`
  operate on platform tuples and cannot express two entries for the same
  `linux/arm64` platform in one index.
- **A silently broken anti-drift tag guarantee for the 2 existing images.**
  `ci.yml`'s `promote` job today derives `:dev-<arch>` FROM the real published
  index digest (`docker buildx imagetools inspect "${SOURCE_REF}" --raw`, then
  `imagetools create --prefer-index=false --tag "${IMAGE}:dev-${arch}"
  "${IMAGE}@${digest}"` — ci.yml:528-541) specifically so the tag can never
  point at something other than what was actually published. The new
  OS-qualified tags for these 2 images must be added alongside this
  mechanism, not by replacing it with something that can drift from the
  published digest.

## 2. Files

- `python/src/dotfiles_setup/platform_target.py` — extend `PublishTarget`
  with an OS-version field and a `blocking: bool` field; add a 3rd entry to
  whatever replaces/extends `PUBLISHED_ARCHES` for the new
  `arm64/ubuntu-26.04` leg.
- `docker-bake.hcl` — add the Bake permutation target(s) for the 3-leg
  matrix (Buildx `matrix` block, available since buildx v0.11.0; installed
  version is v0.36.1, confirmed via the pin in `.config/mise/conf.d/shared.toml`).
- `.github/workflows/build-publish.yml` — thread the new leg (and its
  `blocking` field) through the fan-out (plan → base-prep → p2996-prep →
  dev-prep → build → smoke-test → dev-tag → manifest); the manifest job must
  filter to blocking/manifest-member legs only.
- `.github/workflows/ci.yml` — extend the `promote` job's per-arch retag
  loop (ci.yml:525-545) to add OS-qualified tags for the 2 manifest-joining
  images (still derived from the real published digest, not a static
  guess), and add a SEPARATE, independent tag/publish step for the
  non-manifest 3rd leg (it has no index entry to derive from — its digest
  comes from its own build job's output, not `imagetools inspect` on the
  shared `:dev` index).
- Any of `verify_arch_tags`, `find_lock_platform_drift`, and the lock-image
  regeneration code (grep `python/src/dotfiles_setup/` for these — they were
  not read in depth this session, so locate and read them fresh before
  editing) — these currently assume arch is a unique key
  (`_RUNNER_LABELS`, `LLVM_TARGETS` at platform_target.py:160,195 and
  `GCC_LATEST_ARCHES = ("amd64",)` at platform_target.py:173 are all
  arch-keyed dicts/tuples) and need an explicit blocking/manifest-membership
  filter now that 2 legs share `arch="arm64"`.

## 3. Interfaces

- `PublishTarget` gains at minimum: an OS/ubuntu-version field (name it
  consistently with existing `arch`/`tag_suffix` naming conventions in the
  file) and `blocking: bool`.
- The new `arm64/ubuntu-26.04` leg's `blocking` value is a single named
  constant (e.g. `UBUNTU_26_04_ARM_BLOCKING = False`) — NOT computed from a
  date, a run-count, or any other automatic tracking. Flipping it to `True`
  is a one-line follow-up PR made by a human once satisfied (whether by
  GitHub GA status or by observed reliability — that's a judgment call
  outside this spec's scope, not something this code should compute).
- Tag format for all 3 images: `dev-<arch>-ubuntu<version>`, e.g.
  `dev-amd64-ubuntu24.04`, `dev-arm64-ubuntu24.04`, `dev-arm64-ubuntu26.04`.
  Keep today's `dev-amd64`/`dev-arm64` tags too (additive, not a
  replacement) — they're the ones ci.yml:539's anti-drift mechanism
  produces; do not remove or reroute that mechanism, only add the new
  OS-qualified tags alongside it for the 2 manifest-joining images.

## 4. Constraints and invariants

- **amd64 does not get a ubuntu-26.04 variant.** #736 is ARM64-runner-OS
  scoped only (confirmed: its title names the ARM64 runner specifically).
  Building a Bake permutation mechanism that generates all 4
  arch×ubuntu-version combinations and then EXCLUDING the amd64×26.04 one
  (via `matrix.include` with an explicit permutation list, not a full
  cross-product) is the correct shape — do not build unconditional
  cross-product generation.
- **The 3rd leg's manifest exclusion is structural, not just
  `continue-on-error`.** The manifest job itself must filter to
  manifest-member legs explicitly (do not rely on `continue-on-error`
  alone to keep it out of the index — that only affects whether the job
  is required, not whether its output gets merged into the manifest).
- **Promotion is manual, not automated.** Do not build a mechanism that
  counts consecutive green runs or checks GitHub's GA announcement
  automatically. A single boolean constant, flipped by a human in a
  follow-up PR, is the entire promotion mechanism. (ponytail: this
  project's session convention is to prefer the simplest correct
  mechanism — automatic promotion tracking is out of scope until asked
  for.)
- **`GCC_LATEST_ARCHES = ("amd64",)` at platform_target.py:173 is
  precedent for arch-asymmetric tables** — it already encodes that arm64
  doesn't get the apt `gcc-latest` build (no arm64 upstream build exists).
  Follow the same pattern (an explicit tuple/set naming which legs
  participate) rather than inventing a different mechanism for the new
  OS-version asymmetry.
- **The `no_platform_literals` hk gate (`hk.pkl:268`) rejects hard-coded
  platform literals elsewhere in the codebase** — any new code identifying
  a leg by arch/OS string must route through `PublishTarget`/the tables in
  `platform_target.py`, not a fresh literal string comparison.
- **Do not touch `GCC_LATEST_ARCHES`, `LLVM_TARGETS`, or any other existing
  arch-only table's existing entries** — only add the new
  manifest-membership/blocking dimension needed for the OS-version axis;
  the arm64-asymmetry these existing tables already encode must survive
  unchanged.
- **`renovate.json`, `.devcontainer/mise-system.toml` compiler pins (GCC,
  LLVM) are OUT OF SCOPE for this spec** — a separate PR handles the GCC
  16.2 pin (`docs/specs/devcontainer-gcc162-dual-arch.md`); do not bundle a
  content-hash-busting compiler change into this diff. A CI failure on the
  new Public Preview runner must be attributable to the runner alone, not
  confounded by a simultaneous compiler change.
- **Do not modify `.devcontainer/Dockerfile:571`'s `GCC_LATEST_DEB` pin** —
  unrelated to this work (a separate apt-based GCC build, x86_64-only).

## 5. Verification

- `uv run --project python pytest python/tests/ -x -q -k "platform_target or image_manifest or verify_arch_tags or lock_platform_drift"` (adjust the `-k` filter once the actual test module names are confirmed by reading the test directory — this task does not need the full suite, only the modules touched).
- `docker buildx bake --print` (or the repo's own dry-run mechanism for `docker-bake.hcl`, if one exists — check `mise.toml` tasks) against the new Bake config, to confirm exactly 3 permutation targets are generated (not 4) and no syntax errors.
- Do NOT run `mise run build` or `docker buildx bake dev-load` locally — CI-only per this repo's `AGENTS.md` ("Build Type 2 — Docker Image... CI-only").

## 6. Commit

COMMIT: lane

## PREMISES

L1. `PUBLISHED_ARCHES = ("amd64", "arm64")` — python/src/dotfiles_setup/platform_target.py:152
L2. `_RUNNER_LABELS = {"amd64": "ubuntu-latest", "arm64": "ubuntu-24.04-arm"}` — python/src/dotfiles_setup/platform_target.py:160
I1. `PublishTarget.tag_suffix: str`, set via `tag_suffix=arch` in `_publish_target()` — python/src/dotfiles_setup/platform_target.py:252,276
L3. `GCC_LATEST_ARCHES = ("amd64",)` — python/src/dotfiles_setup/platform_target.py:173 — precedent for an arch-asymmetric table, cited in §4 as the pattern to follow.
L4. `LLVM_TARGETS = {"amd64": "X86", "arm64": "AArch64"}` — python/src/dotfiles_setup/platform_target.py:195
L5. `promote` job derives `:dev-${arch}` from the real published index digest: `raw=$(docker buildx imagetools inspect "${SOURCE_REF}" --raw)` then, per arch, `docker buildx imagetools create --prefer-index=false --tag "${IMAGE}:dev-${arch}" "${IMAGE}@${digest}"`, then re-inspects and asserts digest equality — .github/workflows/ci.yml:528-545. The surrounding comment states this is deliberate so the tag "cannot drift from the matrix that produced it."
L6. `no_platform_literals` hk gate exists — hk.pkl:268 (rejects hard-coded platform-string literals outside the sanctioned tables).
A1. The Buildx Bake version installed on the GHA runners supports the `matrix` block (available upstream since buildx v0.11.0) — this was verified by an earlier research pass in this session (codex-implementer research report, `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/10049cab-c313-4d20-98be-18409eb6daed/scratchpad/research-736-permutation-matrix.md`) but not re-read by me directly this session — re-verify the exact pinned version against `.config/mise/conf.d/shared.toml` before relying on matrix-block syntax.
A2. `verify_arch_tags`, `find_lock_platform_drift`, and lock-image regeneration exist somewhere under `python/src/dotfiles_setup/` and are currently arch-keyed — this was reported by fable-advisor's earlier review this session but I have not personally located or read these functions — locate and read them fresh before editing (per §2).
A3. Only ONE live code consumer of the literal tag strings `dev-amd64`/`dev-arm64` exists repo-wide (`ci.yml:539`) — reported by the codex research pass this session (same report file as A1) via `git grep`, not independently re-verified by me — re-run `git grep -n 'dev-amd64\|dev-arm64'` yourself before assuming this is exhaustive.
