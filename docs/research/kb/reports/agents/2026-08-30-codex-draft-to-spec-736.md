# Spec: Validate `ubuntu-26.04-arm` as a non-blocking CI runner (#736)

## Problem Statement

The devcontainer image build pipeline currently builds its `arm64` leg on
`ubuntu-24.04-arm`, the only GA arm64-hosted GitHub Actions runner today.
GitHub has published `ubuntu-26.04-arm` as a Public Preview arm64 runner
image, and issue #736 asks the repo to start validating that runner before
depending on it.

This is scoped entirely to the **GitHub Actions runner VM's OS** — the
machine that *builds* the image — not to the container's own base OS.
`.devcontainer/Dockerfile` already pins `ubuntu:26.04` as `BASE_IMAGE`
uniformly for both `amd64` and `arm64`, today, regardless of which runner
built the layer. There is no "ubuntu-24.04 container" vs "ubuntu-26.04
container" split in this repo, and this work must not create one. The new
leg is expected to produce a container **identical in content** to the
existing `arm64` image; the only thing being validated is whether the new,
still-preview runner VM can build that same content correctly.

A second, unrelated defect surfaces the moment a second leg shares a
platform value: the GitHub Actions cache scope Buildx Bake uses for the
`dev` target is keyed only on `PLATFORM` (e.g. `linux/arm64`), with no
per-runner or per-leg disambiguation. Two `linux/arm64` legs built on two
different runners would collide on that scope and silently share/corrupt
each other's build cache. This is the same bug class already fixed once
under issue #676 (the scope string exists at all because #676 required
disambiguating per-leg caches); #736 reopens it on a new axis.

More broadly, the repo's build-matrix mechanism (`PublishTarget` /
`platform_target.py`) needs to keep being cheap to extend: the maintainer
wants to eventually support more CPU-architecture and runner-OS
permutations for devcontainer images without repeated re-architecture work
each time a new permutation shows up.

## Solution

Add `ubuntu-26.04-arm` as a **third, non-blocking** build leg alongside the
two existing legs (`amd64` on its current runner, `arm64` on
`ubuntu-24.04-arm`). The new leg:

- builds the same `arm64` platform target, on the new runner, to the same
  content-hash-gated pipeline the other legs already go through;
- is marked non-blocking at the CI job level, so a Public Preview runner
  failure never blocks a merge;
- publishes its own tag independently, and is explicitly excluded from the
  cross-arch `:dev` manifest, since an OCI image index cannot hold two
  entries for the same platform tuple;
- gets a cache scope disambiguated by which leg produced it, not just by
  platform, fixing the #676-class collision before it can bite a second
  time.

The permutation table that drives all of this stays a small, explicit,
Python-side enumeration (`PublishTarget` rows), extended with two new
fields (a runner identity, already partially present, and a `blocking`
flag) rather than any new HCL-level matrix construct. This keeps the
"add a permutation = add a row" property the maintainer asked for, while
avoiding a second, parallel permutation mechanism living in
`docker-bake.hcl` that could drift out of sync with the Python table (the
same split-brain the `no_platform_literals` gate already guards against
elsewhere).

## User Stories

**As the repo maintainer**, I want a real, low-risk trial run of
`ubuntu-26.04-arm` so I can decide, with actual evidence, when to promote it
to the required `arm64` runner — without gambling every merge on a Public
Preview runner in the meantime.

**As the repo maintainer**, I want the new leg's failures to be visible (not
silently swallowed) but never merge-blocking, so a flaky or broken preview
runner doesn't become an on-call problem for unrelated PRs.

**As the repo maintainer**, I want to flip a single, explicit boolean when
I'm satisfied the new runner is trustworthy, rather than build or depend on
any automatic promotion-tracking machinery (green-run counters, GA-status
polling) I didn't ask for.

**As the CI pipeline**, I need to keep publishing a correct two-platform
`:dev` manifest (`amd64` + `arm64`) with zero behavior change for existing
consumers, even while a third, non-manifest-joining leg is building
alongside it — because an OCI index has exactly one slot per platform
tuple and cannot represent "two ways to build arm64."

**As the CI pipeline**, I need the new leg's build cache to never collide
with the existing `arm64` leg's cache, since they share the same
`PLATFORM` value and only differ in which runner built them.

**As a future contributor** adding the next runner or architecture
permutation (say, a future `ubuntu-28.04-arm`, or a new architecture
entirely), I want to add one row to the `PublishTarget` table and get correct
tagging, correct cache scoping, and correct manifest membership for free,
without touching `docker-bake.hcl`'s cache-scope logic or re-deriving the
non-blocking/manifest-exclusion wiring by hand.

**As a downstream consumer** of `ghcr.io/ray-manaloto/dotfiles-devcontainer`
tags (`:dev`, `:dev-amd64`, `:dev-arm64`), I want to see zero change in the
content, digests, or publishing behavior of the two existing legs as a
result of this work landing.

**As a reviewer of a future PR that promotes the new runner to required**, I
want the leg's identity, tag suffix, and blocking flag to already read
clearly as "this was the validation leg for the preview runner," so
flipping it to required (or deleting the old `ubuntu-24.04-arm` leg) is an
obvious, well-labeled follow-up change rather than an archaeology exercise.

## Implementation Decisions

**Cache-scope fix (standalone, land regardless of the rest).** Introduce a
generic Bake-level variable representing "which leg is building" that
defaults to the existing platform-derived value when unset, so any manual
or local `docker buildx bake` invocation is unaffected. Change the `dev`
target's GitHub Actions cache-scope expression to key on that leg identity
instead of keying on `PLATFORM` directly. CI supplies the leg identity per
matrix entry, sourced from that entry's tag suffix (already guaranteed
distinct by construction in the Python permutation table). This is the
entire Bake-file change required — no HCL-side matrix, group, or `for`
construct is added, so a future axis added on the Python side automatically
gets its own disambiguated cache scope with no further Bake edits.

**Where the new axis lives.** The runner-OS axis is expressed as fields on
the existing `PublishTarget` dataclass (a runner-identity field, already
partially present, plus a new `blocking` boolean), not as a Bake-level
construct. Permutations stay an explicit, enumerated list of concrete rows
— never a computed cross-product of independent axis values — so
"buildable" is always exactly the rows an author listed, and adding a new
axis value never silently starts building every combination against it.

**No container-base-OS field.** Deliberately do not add any field
representing a different container base image / OS version. The Dockerfile
and Bake file both currently express one Renovate-pinned base shared by
every leg, on purpose. Runner OS and container base OS are independent
concerns that happen to both be "Ubuntu version numbers" right now; this
spec only exercises the runner-OS axis, and inventing a base-OS axis before
a second real base image exists would be guessing at a distinction that
isn't there yet.

**Naming.** The new leg's tag suffix should name what actually varies —
which runner built it — rather than implying a different container OS.
Follow the existing `tag_suffix` convention used by the other rows (which
today denotes architecture); extend it in a way that reads as "arm64,
built on the alternate/preview runner" rather than anything resembling an
OS-version tag, since that would misleadingly suggest the container itself
differs.

**Non-blocking mechanism.** Gate the new leg's job with `continue-on-error`
driven by a single named constant on the `blocking` field for that row (a
human-flipped boolean, not computed). No consecutive-green-run counting, no
polling GitHub's own GA/preview status — promotion to blocking is a manual,
reviewed follow-up PR once the maintainer is satisfied.

**Manifest exclusion is structural, not just non-blocking.** The
manifest-assembly step must filter to only the legs designated as
manifest members (today: the `amd64` leg and the existing `arm64`-on-
`ubuntu-24.04-arm` leg) — this is a hard constraint independent of the
blocking flag, since an OCI image index physically cannot carry two entries
for one platform tuple. The existing per-arch retag logic that derives
`:dev-<arch>` tags from the real published index digest, and re-verifies
digest equality after retagging, stays completely unchanged for the two
manifest-joining legs.

**Independent publish path for the new leg.** Because the new leg has no
index entry to derive a tag from, it needs its own tag/publish step whose
digest comes straight from its own build job's output, separate from the
index-derived retag loop the two manifest legs use.

**Scope boundary.** This work is `arm64`-runner-OS-only, matching #736's own
title and text. `amd64` gets no equivalent new leg or treatment here.

## Testing Decisions

**Primary seam: pure-Python unit tests.** Extend the existing
`tests/test_platform_target.py` parametrized-pytest pattern (the same style
already used by tests like `test_repo_tree_has_no_stray_literals`,
`test_default_drift_between_the_two_permitted_sites`, `test_normalize_arch`)
to cover the new `PublishTarget` row: correct tag suffix, correct
`blocking` value, correct manifest-membership classification, and that the
enumerated-list nature of the permutation table is preserved (no accidental
cross-product behavior). Tests live at the repo root `tests/`, matching
where this file already lives, not under `python/tests/`.

**Secondary seam: Bake structural/dry-run validation.** Add a
`docker buildx bake --print`-style check against the changed Bake
configuration to confirm the new cache-scope variable and target wiring
parse and resolve correctly, without triggering a real build. This is
constrained by the repo's standing rule against local base-image or `dev-load`
builds (CI-only) — so this seam is strictly a print/dry-run syntax check,
never a real local build, and cannot substitute for the primary Python
test seam.

## Out of Scope

- The GCC 16.2 pin (`"conda:gxx"` currently `"latest"` in
  `.devcontainer/mise-system.toml`) — tracked separately by
  `docs/specs/devcontainer-gcc162-dual-arch.md`, which supersedes issue
  #243. That work ships as its own follow-up PR, deliberately *after* this
  one, so a content-hash-busting compiler change never lands on the same CI
  run as the new preview runner's first real test — confounding failure
  attribution otherwise.
- LLVM/clang bump to 23.1.0 — `llvm-toolchain-resolute-23` does not yet
  exist on apt.llvm.org (suite 22 is current max at time of writing), so it
  cannot be pinned regardless of intent. Deferred until upstream publishes
  it.
- Any equivalent `ubuntu-26.04`-class runner validation for `amd64` — out of
  scope; #736 is arm64-runner-OS-specific.
- Full adoption of Docker's `docker/github-builder` reusable workflow as a
  pipeline replacement — investigated and explicitly rejected in favor of
  extending the existing custom `PublishTarget` mechanism (see Further
  Notes).
- Automatic promotion-tracking machinery (consecutive-green-run counting,
  polling GitHub's own runner-GA-status signal) — promotion is a
  manually-flipped constant by design.
- Any new field or axis representing a distinct container base-OS version —
  not introduced until a second real base image actually exists to justify
  it.

## Further Notes

This design followed a real research and review investment worth
preserving for future readers, so these decisions don't read as arbitrary:

- Docker's official `docker/github-builder` reusable workflow was evaluated
  as a possible full-pipeline replacement. Its own `runner` input
  (platform-prefix-matched, e.g. mapping `linux/arm64` to a specific runner
  label) turned out to be architecturally the same idea as this repo's
  existing `PublishTarget` table — which reads as validation of the
  existing approach rather than a reason to replace it. A live check of
  real-world adopters (via `gh search code` across projects including
  moby/moby, docker/compose, docker/cli, moby/buildkit, zizmorcore/zizmor,
  oxipng/oxipng, luanti-org/luanti, and asterinas/asterinas) found every one
  of them uses it only for the platform-fanout core, keeping custom jobs
  around it for anything more involved — none route a pipeline with this
  repo's complexity (content-hash-gated job skipping, a compiler-cache
  build stage, post-build manifest retagging, index-correctness assertions)
  fully through it. The decision was to extend the existing custom
  mechanism rather than adopt the reusable workflow.
- Docker Buildx Bake's own `matrix` attribute (a way to generate a
  cross-product of named targets within one Bake invocation) was also
  evaluated and found not to help: it operates entirely within a single
  `bake` call on one machine and has no notion of "which GitHub Actions
  runner should build this," so it cannot substitute for the
  GitHub-Actions-level matrix that currently drives per-leg parallelism
  across separate, natively-different runners. This was re-traced through
  the existing `plan` job → Python matrix-JSON generation →
  GitHub Actions `fromJSON` matrix path independently more than once during
  design review, arriving at the same conclusion each time.
- An architecture review at a commitment boundary recommended against
  adding any HCL-level permutation/matrix mechanism, on the grounds that
  the permutation table already lives correctly in the Python layer, and an
  HCL-side matrix would duplicate it and risk drifting out of sync — the
  same class of split-brain risk the repo already guards against elsewhere
  with its no-platform-literals gate.
- The cache-scope fix (keying on leg identity instead of raw platform) is
  itself an independently valuable bugfix — a recurrence of the #676 bug
  class on a new axis — and is worth landing even if the broader #736
  runner-validation effort were somehow deprioritized.
