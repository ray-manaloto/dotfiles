# codex-advisor: promote staleness guard design (#1007)

Status: DELIVERED — codex (gpt-5.6-sol, xhigh) verdict below, relayed verbatim.

Prompt sent to codex: `.agent/kb/raw/codex-advisor-promote-prompt.md`
Raw codex stdout log: `.agent/kb/raw/codex-advisor-promote-run.log`

## Recommendation

Ranked:

1. Enable `required_status_checks.strict: true` now. This structurally closes the stale-base merge race for protected PR merges.
2. Add a small in-repo defense using existing `:dev-<dev-hash>` smoke-validated marker tags. Compare each candidate `:pr-N` child digest with the marker derived from the actual `github.sha` checkout.
3. On mismatch, do not retag. Hard-fail initially. Only route automatically to fallback after making fallback rebuilds exact-SHA-bound and newest-wins.
4. Consider merge queue later if strict mode’s rebase/rerun churn is materially painful. It is not a drop-in change for this workflow.
5. Do not use revision labels or layer extraction as the primary guard.

`★ Insight ─────────────────────────────────────`
The repository already has the provenance primitive this guard needs: `dev-hash → post-smoke marker tag → OCI child digest`. Promotion can prove candidate eligibility transitively, using only registry metadata, without adding a second provenance system.
`─────────────────────────────────────────────────`

## 1. Signal choice

| Design | Assessment |
|---|---|
| (a) Read the three files | Semantically exact for those three files, but requires layer traversal or a full platform pull and covers fewer inputs than the existing dev hash. Keep as a diagnostic, not the primary gate. |
| (b) `org.opencontainers.image.revision` | Reject. The PR’s `GITHUB_SHA` is a synthetic merge-ref commit, not generally an ancestor of the later squash commit. Cache hits also reuse an older image/config, so a revision label is expected to be historically “wrong” even when content is correct. |
| (c) Compare against existing `:dev-<hash>` marker digests | Recommended. Registry-only, no new label/build input/tool, architecture-aware, and already tied to successful smoke validation. |

The repository’s exact identity set is centralized at [image.py:282](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image.py:282). Those files are already inputs to `dev-hash`:

- `mise-system.toml` and `shared.toml` feed the base hash at [p2996_hash.py:354](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/p2996_hash.py:354) and [p2996_hash.py:361](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/p2996_hash.py:361).
- `mise-runtime.toml` feeds the dev hash at [p2996_hash.py:502](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/p2996_hash.py:502).
- The final hash folds in the base hash, platform, whole Dockerfile, dev target, and runtime inputs at [p2996_hash.py:511](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/p2996_hash.py:511).

After smoke succeeds, CI binds `:dev-<hash>` to the validated per-architecture image at [build-publish.yml:1045](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:1045) and verifies the retag at [build-publish.yml:1124](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:1124). The PR index is assembled only after that marker stage succeeds at [build-publish.yml:1165](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:1165).

The guard algorithm should therefore be:

```text
source = OCI index for :pr-N
for target in published_targets():
    expected_hash = compute_repo_dev_hash(
        checkout_of_github_sha,
        platform=target.platform,
    )
    expected_marker = IMAGE:dev-<expected_hash>

    candidate_digest = source's unique linux/<target.arch> child digest
    marker_digest = resolve_arch_tag(expected_marker).inner_digest

    require marker platform == linux/<target.arch>
    require marker_digest == candidate_digest
```

Use `published_targets()` rather than a YAML or Python architecture literal; it deliberately excludes the duplicate validation runner at [platform_target.py:346](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/platform_target.py:346).

Critically, compare inner platform manifests. The existing resolver already handles bare manifests versus Buildx-created wrapper indexes and ignores attestation entries at [image_manifest.py:190](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image_manifest.py:190). Comparing outer `Manifest.Digest` values would recreate #703’s “check that can only fail” defect documented at [image_manifest.py:8](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/image_manifest.py:8).

Why not the revision label:

- GitHub documents that `pull_request` workflows use the synthetic `refs/pull/N/merge` commit as `GITHUB_SHA`; squash merging creates a new commit on the base. [GitHub Actions event documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- A dev-cache hit manifest-retags an already-validated image instead of rebuilding it at [build-publish.yml:492](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:492). Its old config label would remain.
- Making revision labels accurate would require every commit to produce a distinct image config and digest, undermining cross-commit content-cache reuse. Passing a dynamic label outside `dev-hash` would instead under-hash the image.

One caveat: describe design (c) as protecting the `dev-hash` trust root, including all three identity files—not yet as a formal proof of every possible bake input. `gather_dev_inputs()` hashes the `dev` target block, not the fully resolved inherited Bake model at [p2996_hash.py:492](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/p2996_hash.py:492); `_common` and `COMPRESSION_OUTPUT` live outside that block at [docker-bake.hcl:72](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docker-bake.hcl:72) and [docker-bake.hcl:112](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/docker-bake.hcl:112). The three requested identity files are definitely covered, but a separate dev-hash coverage audit would be needed before claiming exhaustive Bake-input coverage.

Confidence: High for the three-file defect class; medium-high for a broader “all build inputs” claim because of that Bake dependency caveat.

## 2. Reading image bytes cheaply

It is possible to avoid pulling the whole image, but `imagetools inspect --format '{{json .Image}}'` cannot return arbitrary files.

OCI separates:

- The small image configuration: runtime settings, labels, history, and uncompressed layer DiffIDs.
- The manifest: ordered descriptors for compressed layer blobs.
- The filesystem bytes: tar changesets in those layer blobs.

See the [OCI configuration specification](https://github.com/opencontainers/image-spec/blob/main/config.md) and [OCI manifest specification](https://github.com/opencontainers/image-spec/blob/main/manifest.md). Docker’s `.Image` format exposes only the first category. [Docker Buildx inspect documentation](https://docs.docker.com/reference/cli/docker/buildx/imagetools/inspect/)

Selective possibilities:

- `regctl image get-file IMAGE PATH` is the closest native solution. Its documented purpose is to traverse image layers looking for one file, without a Docker daemon. [regctl documentation](https://regclient.org/cli/regctl/image/get-file/)
- `crane blob` and `oras blob fetch` can fetch one exact layer blob once its digest is known. [crane blob](https://github.com/google/go-containerregistry/blob/main/cmd/crane/doc/crane_blob.md), [ORAS blob fetch](https://oras.land/docs/commands/oras_blob_fetch/)
- `skopeo inspect --config` reads configuration metadata; `skopeo copy` copies manifests and filesystem layers and is not a single-file extractor. [Skopeo documentation](https://github.com/containers/skopeo)

The three files are added by three separate `COPY` instructions at [Dockerfile:127](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:127), [Dockerfile:139](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:139), and [Dockerfile:666](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.devcontainer/Dockerfile:666). That strongly suggests each can be obtained from a small COPY layer instead of downloading the large compiler/tool layers. A robust extractor still needs to account for later replacement and OCI whiteouts; the existing byte-identity smoke provides good evidence that these paths survive unchanged.

A fresh `docker run`, however, does not selectively pull only the layer containing the requested file. It resolves and downloads every missing layer needed for that platform. Thus design 1(a)’s Docker fallback should be treated as a full-image-pull path.

No `crane`, `skopeo`, `oras`, or `regctl` pin exists in the inspected mise configurations/locks. The control search found the existing Docker CLI pin at [mise.toml:72](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:72) and `jq` at [shared.toml:38](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.config/mise/conf.d/shared.toml:38), confirming the searched corpus was correct.

Confidence: High on OCI/Docker mechanics and tool availability; medium on actual transfer cost. I could not inspect live GHCR layer descriptors, so the exact compressed sizes remain unverified.

## 3. Placement and failure mode

Place the new guard after “Probe source PR image exists” and before “Retag PR image as :dev and :latest”:

```text
Find associated PR
    ↓
Probe :pr-N and capture index digest
    ↓
Checkout exactly github.sha
Install python + uv
Plan candidate eligibility       ← new
    ↓
Eligible: retag
Not eligible: leave moving tags untouched
```

The source probe at [ci.yml:453](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/ci.yml:453) should remain first because there is nothing meaningful to compare when the source tag is absent. The retag begins at [ci.yml:488](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/ci.yml:488), so the guard must complete before that step.

Failure classification should be:

- Candidate child digest differs from current expected marker: stale correctness breach; never retag.
- Expected marker missing: eligibility cannot be proved; never retag.
- Malformed OCI shape, wrong platform, registry authentication/network failure, or Buildx failure: hard failure; do not reinterpret as staleness or a cache miss.
- Candidate and all markers match: retag.

For the first patch, I recommend hard-failing a mismatch and leaving the prior `:dev`/`:latest` untouched. That gives a red main run, activates the existing failure-report job at [ci.yml:595](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/ci.yml:595), and preserves the last known-good publication.

I would not silently route mismatches into the existing fallback yet. It only proves that a dispatch run appeared—not that it completed—at [ci.yml:557](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/ci.yml:557). Meanwhile main runs are explicitly exempt from cancellation at [ci.yml:41](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/ci.yml:41). Two long fallback builds can therefore finish out of order and let an older run overwrite a newer `:dev`.

The preferred eventual third mode is “fail closed, queue repair, remain loud”:

1. Add a dispatch input carrying the exact stale-promote `github.sha`.
2. Pass it into the reusable workflow’s existing `ref` input.
3. Build and publish immutable SHA tags for that exact commit.
4. Immediately before moving `:dev`, `:latest`, and `:dev-<arch>`, confirm the SHA is still the protected branch head. If not, skip moving tags because a newer main run owns publication.
5. After the recovery run is observed, mark the original stale promotion red rather than presenting the incident as an ordinary green retag.

Do not retag stale content under any “best effort” mode. A warning cannot compensate for deliberately recreating the measured regression. I also would not auto-open an issue; the red run, digest-rich step summary, and failure artifact are sufficient and avoid issue spam.

Confidence: High.

## 4. Concrete control arm

Put the decision logic beside the existing injected registry reader—either extend `image_manifest.py` or add a focused `image_promote.py` that imports its `Inspector`, `real_platform_entries()`, and `resolve_arch_tag()`.

The decisive test fixture should use real hash computation and fake only the registry boundary:

```python
repo = seed_minimal_hash_repo(tmp_path)

shared = repo / ".config/mise/conf.d/shared.toml"
shared.write_text('codex = "0.152.1"\n')
stale_hash = compute_repo_dev_hash(repo, platform=AMD64_PLATFORM)

shared.write_text(
    'codex = "0.154.0"\nminimum_release_age = "0s"\n'
)
fresh_hash = compute_repo_dev_hash(repo, platform=AMD64_PLATFORM)
assert fresh_hash != stale_hash
```

Then construct an index-shaped fake registry:

```text
:pr-1005
  linux/amd64 → STALE_DIGEST

:dev-<stale_hash>
  index wrapper → linux/amd64 → STALE_DIGEST

:dev-<fresh_hash>
  index wrapper → linux/amd64 → FRESH_DIGEST
```

Run the guard against the fresh worktree:

- Failure arm: candidate `:pr-1005` resolves to `STALE_DIGEST`; expected marker resolves to `FRESH_DIGEST`. Require a stale verdict naming the platform, expected hash, marker ref, candidate digest, and expected digest.
- Passing control: change only the candidate index entry to `FRESH_DIGEST`; require an eligible verdict.
- Shape control: make the fresh marker a bare manifest rather than an index; it must still pass through `resolve_arch_tag()`.
- Multi-arch arm: amd64 matches while arm64 is stale; the whole candidate must be rejected.
- Missing-marker arm: raise the typed “manifest not found” result; classify as unprovable/rebuild, never current.
- Operational-error arm: authentication/network error must propagate as hard failure, not be converted into a stale/missing decision.

Also add two wiring tests:

- CLI parse/dispatch reaches the public verifier, matching the pattern at [test_image_manifest.py:377](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/tests/test_image_manifest.py:377).
- Parsed workflow YAML proves the retag step requires `eligible == true` and that the guard is textually before retag. This prevents a perfect but unreachable Python verifier.

Required mutation evidence:

- Delete or invert the marker-digest comparison: the stale arm must fail.
- Remove the eligibility condition from the retag step: the workflow-wiring test must fail.
- Replace the fresh expected marker with the stale marker: the stale-file fixture must fail.

After implementation, run a real registry control through the public CLI:

- Pass arm: a retained PR image whose children equal the current merge commit’s expected marker digests.
- Fail arm: retained `:pr-1005`, if still present, against current main.
- Verify that neither arm mutates any tag.

That last live pair matters because repo policy explicitly treats mocked registries as supplemental, not final integration evidence at [real-integration-evidence.md:3](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/rules/real-integration-evidence.md:3).

Confidence: High.

## 5. Native-first alternative

Enable `strict: true`.

GitHub’s documented contract is that strict required checks require the branch to be current with the base before merging; after another PR moves `main`, a second PR must be updated and checked again. Loose checks intentionally allow the opposite. [GitHub protected-branch documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

Under that contract and the confirmed no-bypass setting, the #1004/#1005 race becomes structurally impossible:

1. #1004 advances main.
2. #1005 is no longer current.
3. #1005 cannot merge on its old successful check.
4. Its updated merge result must obtain the required check, causing PR CI to produce or retag an image for the current combined content.

A “simultaneous double merge” is not intended to be a loophole: one protected ref update wins first; the second is then evaluated against the advanced base. I did not live-race GitHub to experimentally verify this atomicity, but it is the platform contract described by the strict setting.

Practical cost in this repository:

- The existing automerge implementation explicitly assumes a behind-main branch is acceptable at [pr.py:690](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/pr.py:690), and [mise.toml:906](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/mise.toml:906) advertises that behavior. Those comments, skill prose, and tests must be revised.
- Strict does not update branches by itself; it blocks them until something updates them.
- Renovate has `platformAutomerge: true` for minor/patch/digest updates at [renovate.json:32](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/renovate.json:32). Renovate documents that `rebaseWhen=auto` detects strict protection and rebases behind branches, but each rebase causes another CI run and frequent main changes can repeatedly defer merging. [Renovate configuration](https://docs.renovatebot.com/configuration-options/)
- Human `ship` PRs may need updating and re-arming because the current workflow pins auto-merge to a specific head SHA.
- The content cache should make many reruns inexpensive when intervening changes do not alter image inputs, but lint/contract-preflight still rerun.

Merge queue provides the same current-base guarantee while also testing against PRs already ahead in the queue. [GitHub merge-queue documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue) It is better for sustained high merge volume, but it is not a settings-only change here:

- `ci.yml` lacks a `merge_group` trigger; GitHub says required Actions checks will otherwise never report.
- `build-publish.yml` derives `PR_NUMBER` from `github.event.pull_request.number` at [build-publish.yml:1212](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/build-publish.yml:1212).
- Promotion chooses only the first associated PR at [ci.yml:409](/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.github/workflows/ci.yml:409), while a merge group may represent several queued PRs.

Therefore:

- Adopt strict mode now.
- Keep merge queue as a separately designed throughput improvement.
- Still build the inexpensive dev-marker guard. Strict protection prevents stale-base merging, but it does not detect external setting drift, a misbound/mutated `:pr-N` tag, or future promotion regressions. The guard is worthwhile defense-in-depth precisely because design (c) avoids labels, layer pulls, and new dependencies.

Confidence: High on GitHub’s structural guarantee and workflow incompatibilities; medium on the exact bot latency until one real Renovate, refresh-bot, and Dependabot PR has been observed under strict mode.

## Verification gaps

I could not verify:

- Current live branch protection/rulesets: `gh api` was blocked by network access, so I accepted your measured `strict:false` and no-bypass facts.
- Live GHCR manifests or layer sizes: both Buildx probes failed at DNS resolution in this sandbox.
- `regctl image get-file` transfer volume and GHCR authentication behavior against this specific image.
- The fully resolved inherited `github>jdx/renovate-config` preset; the repo has no explicit `rebaseWhen`, so the cost assessment uses Renovate’s documented default behavior.
- Graphify evidence: both required project tasks were attempted but `mise` could not create its temp/log state under the read-only sandbox. Source was used as fallback authority.
- No tests were run because this was advisory-only and no files were changed.

