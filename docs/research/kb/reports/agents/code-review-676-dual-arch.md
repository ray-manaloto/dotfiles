# Agent report — `/code-review high` on `feat/676-dual-arch-publish` (2026-08-10)

Persisted verbatim per `.claude/rules/agent-report-persistence.md`. The
disposition table at the end was added by the parent session; everything under
"Report (verbatim)" is the agent's own text, unedited.

## Brief

Invoked as the `code-review` skill with argument `high`, as the
`mattpocock-skills:implement` skill directs ("Once done, use /code-review to
review the work"). The skill composes its own brief from that level; the parent
supplied no additional prompt text.

⚠️ **Recorded limitation:** the skill-composed brief is not visible to the
parent, so unlike a hand-written delegation this brief cannot be reproduced
verbatim here. What IS reproducible: the target (the working tree at commit
`a5a8882`, i.e. `git diff main...HEAD`) and the effort level (`high`). #601's
lesson — that seven review briefs were lost while their reports survived —
applies to hand-authored briefs; for a skill invocation the invocation line
above is the whole of what the parent controlled.

## Report (verbatim)

The `ReportFindings` tool is not available in this session (searched, no match), so findings are reported directly below.

## Review of `feat/676-dual-arch-publish` (dual-architecture publish)

I read the full diff (`git diff main...HEAD`), then the resulting `build-publish.yml`, the new composite, `docker-bake.hcl`, `platform_target.py`, `p2996_hash.py`, `image.py:size_report`, `ci.yml:promote`, and the image lockfiles. Working tree is clean, so the range diff is the whole scope.

### Findings

**1. `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:595` — HIGH: the nightly path now breaks, and stops rebuilding.**
`build` probes the dev cache unconditionally (no `if:`), and every build/push step is gated `if: steps.probe.outputs.hit != 'true'`. On the nightly path `dev-prep` is skipped (`if: inputs.tag_strategy == 'pr'`), so nothing retags `:<sha>-<arch>`. Concretely: nightly runs on main's sha, content is unchanged since the last merged PR, so `:dev-<hash>` exists → build's probe HITs → every push step is skipped → no `:<short-sha>-<arch>` tag is created for main's sha. `smoke-test` then also HITs and skips, reporting `success`, so `dev-tag` runs and executes `docker buildx imagetools create --tag "${IMAGE}:dev-${hash}" "${IMAGE}:${short_sha}-${TAG_SUFFIX}"` against a tag that does not exist → hard failure; `manifest` is then skipped, so `:dev` / `:latest` are never republished. This also silently defeats the documented nightly invariant (`build-publish.yml:417-421`, "nightly … always rebuilds — it exists to catch rolling-tool drift the content hash cannot see"), which the old `if:` (`needs.dev-prep.outputs.hit != 'true'` only when dev-prep succeeded) preserved. The same shape can bite a PR run as a narrow race: if a concurrent run's `dev-tag` stamps the marker between `dev-prep`'s probe (miss) and `build`'s probe (hit), no leg ever writes `:<sha>-<arch>`.

**2. `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:1120` — HIGH: the AC2 assertion cannot run; the `manifest` job never pulls the image.**
`dotfiles-setup image size-report` calls `docker image inspect --format {{.Size}} <ref>` and `docker history <ref>` (`python/src/dotfiles_setup/image.py:1140-1149`) via `_run(..., check=True)` (`image.py:239-250`) — both read the **local** daemon store. The `manifest` job's steps are checkout → setup-mise → buildx → login → `imagetools create` → assertions; `imagetools create` does not pull, and there is no `docker pull` anywhere in the job. So the first loop iteration raises `CalledProcessError` and the step exits non-zero on every run, failing `manifest` and therefore the workflow.

**3. `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:1128` — MEDIUM: the "each architecture resolves to its own image" check can only pass.**
`sums` are sha256 of the `size-report` JSON, and that payload embeds `"platform": platform` (`image.py:1167-1173`), which differs by construction on every iteration. So `sort -u | wc -l` always equals `${#sums[@]}` and the `FAIL` branch is unreachable — even if the index pointed both entries at one image. Compounding it, `image_size_bytes` and `top_layers` come from the local daemon and are not platform-selected at all; only `compressed_size_bytes` is genuinely arch-derived. The check needs to compare something arch-discriminating (e.g. the per-entry manifest digests from `imagetools inspect --raw`), and should be armed against a deliberately duplicated index.

**4. `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/mise-system.toml:281` — HIGH: the new arm64 leg builds an image full of x86_64 binaries.**
The image's system mise config pins `[settings] arch = "x86_64"` (line 281) and `lockfile_platforms = ["linux-x64"]` (line 293), and the committed locks contain **zero** arm64 entries (`mise-system.lock`: 131 `linux-x64` / 0 `linux-arm64`; `mise-runtime.lock`: 35 / 0). Adding `"arm64"` to `PUBLISHED_ARCHES` (`platform_target.py:143-147`) makes `base-prep`/`build` actually run on arm64, where `mise install --system --locked` will resolve x86_64 downloads into an arm64 image. The build-time self-checks (`mise ls --installed | wc -l`) do not execute the binaries, so this survives the image build and only surfaces at smoke — after a multi-hour native arm64 clang-p2996 compile. Nothing in this PR regenerates the locks for `linux-arm64` or makes `arch`/`lockfile_platforms` platform-derived.

**5. `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:1065` — MEDIUM: `:dev-<arch>` is only ever written on the nightly path.**
The `if [ "${NIGHTLY}" = "true" ]` block is the sole producer of `:dev-amd64` / `:dev-arm64`, but the primary publish path is `promote` in `ci.yml:468` (push-to-main), which only does `imagetools create -t :dev -t :latest <:pr-NNN>` and never writes the per-arch moving tags. The comment right above (lines 1054-1058) states these are what "a cross-architecture identity check and a `mise.local.toml` pin both need". So after a normal merge, `:dev` advances while `:dev-<arch>` stays at the last nightly (or never exists at all until the first nightly runs) — a consumer pinning `:dev-arm64` silently gets a stale image.

**6. `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:797` — LOW: `smoke-test` computes `dev-hash` without the `p2996_ref` override.**
`dev-prep`, `build` and `dev-tag` all carry a "Resolve p2996 ref override" step before anything calls `dev-hash`; `smoke-test` does not, yet it now runs `dev-cache-probe` (which shells `dotfiles-setup dev-hash`). With `inputs.p2996_ref` set, smoke-test's probe computes the pinned-ref hash rather than the overridden one. It fails in the safe direction (a spurious MISS just re-smokes), and the Phase D dispatch caller is retired, but the four call sites are no longer consistent.

### Things I checked that are fine
- `BASE_IMAGE` / `BUILDER_IMAGE` are digest-pinned to **manifest lists**, so arm64 resolution is preserved; the Dockerfile has no hard-coded arch tokens.
- The `PLATFORM` resolution order in `resolve_bake_platform` matches bake's, and `test_repo_hashes_unchanged_when_env_repeats_the_default` correctly pins that no published amd64 cache tag is orphaned.
- `find_unpublished_pin` agrees with `mise.toml:150` (`linux/amd64/v2` ∈ published set); the `mapfile`/`sort -u` AC1 comparison and the `unknown/unknown` attestation filter are sound.
- Dropping the `ci.dev-prep-gate-exists` / `dev-hash` entry from `AMBIGUITY_ALLOWED` is right — that token now appears exactly once per path after the probe moved into the composite.
- `ci.yml` does not consume `build-publish`'s `image_ref`/`digest`, so re-sourcing them from `manifest` (which is gated on `inputs.publish`) breaks no caller.

## Disposition (added by the parent, 2026-08-10)

Every finding was **independently confirmed by the parent before acting** — the
review's claims were re-derived from the source, not taken at face value.

| # | Sev | Verdict | Disposition |
|---|---|---|---|
| 1 | HIGH | CONFIRMED | **Fixed** in `2c29366`. `build` now asks whether dev-prep published *this leg's tag* (no race window — `needs` guarantees dev-prep finished), and both `build` and `smoke-test` guard their probe with `if: inputs.tag_strategy == 'pr'`. The guard is now bound by `ci.build-publish-matrix` with a deliberate multiplicity of two, so dropping it from EITHER job fails `contract_token_uniqueness` — mutation-verified. |
| 2 | HIGH | CONFIRMED | **Fixed** in `2c29366`. Read `image.py:1140-1149` directly: `docker image inspect` + `docker history` are local-daemon reads and the job never pulls. Replaced with a registry-only comparison via `imagetools inspect --raw`. |
| 3 | MEDIUM | CONFIRMED | **Fixed** in `2c29366`, and the most serious of the six despite its severity label — a check that could only pass, in a repo whose `probes-need-a-control-arm.md` exists for exactly that. Now compares the per-entry manifest **digests** and asserts each per-architecture tag resolves to its own entry. #674's deferred `size-report` run moved to `smoke-test`, where the image is already local and the architecture native. |
| 4 | HIGH | CONFIRMED | **Deferred by Ray's explicit ruling, 2026-08-10.** Measurements re-taken independently (locks 131/0 and 35/0). The parent recommended shipping the plumbing amd64-only behind a one-line `PUBLISHED_ARCHES` flip; Ray chose to publish both and let CI establish the real failure. Filed as **#698** and recorded in `docs/specs/devcontainer-gcc162-dual-arch.md` § D1 so the expected red arm64 leg is recognised rather than re-diagnosed. |
| 5 | MEDIUM | CONFIRMED | **Fixed** in `2c29366`. `promote` now splits the published index into `:dev-<arch>` by digest, reading the architecture list *from the index* so it cannot drift from the matrix that produced it. |
| 6 | LOW | CONFIRMED | **Fixed** in `2c29366` — `smoke-test` gained the "Resolve p2996 ref override" step. |

One defect the review did **not** find, caught while fixing the above: an
unquoted `#676` in a YAML step name starts a comment and would have silently
truncated the name. Now quoted, with the reason in a comment above it.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review; no external sources were consulted.
