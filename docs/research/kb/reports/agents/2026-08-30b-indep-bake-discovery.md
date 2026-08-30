# Independent Bake Research Discovery — 2026-08-30b

Question: Can Docker Bake own a build-input permutation set (container base OS
x architecture x microarch level x builder runner), give each permutation a
distinct descriptive image tag, while the GitHub Actions runner per leg is
chosen outside bake, and no leg builds under QEMU emulation?

Scope: sources NOT in the fixed list covered by other lanes (Bake docs pages,
docker/bake-action, docker/github-builder, docker/build-push-action,
crazy-max/docker-linguist).

## Findings

### 1. GitHub Changelog — arm64-hosted runner availability and labels
- **What**: GitHub Blog Changelog posts.
- **URLs**:
  - https://github.blog/changelog/2025-01-16-linux-arm64-hosted-runners-now-available-for-free-in-public-repositories-public-preview/
  - https://github.blog/changelog/2025-08-07-arm64-hosted-runners-for-public-repositories-are-now-generally-available/
  - https://github.blog/changelog/2026-01-29-arm64-standard-runners-are-now-available-in-private-repositories/
- **Claim supported**: The GitHub-hosted arm64 runner labels are `ubuntu-24.04-arm`, `ubuntu-22.04-arm`, and `windows-11-arm`. Public preview shipped Jan 2025, GA for public repos Aug 2025, and private-repo support landed Jan 2026 ("these runners are fully supported standard GitHub-hosted runners suitable for production CI workloads"). This confirms that **runner architecture selection is a `runs-on:` / job-matrix concept in GitHub Actions**, entirely outside bake's config surface — bake has no notion of "which machine runs this build," only of build inputs (context, platform, args, tags) for a builder that already exists when bake is invoked.

### 2. OCI image-spec — `image-index.md` platform object
- **What**: Primary spec (opencontainers/image-spec), the canonical schema every bake/buildx-produced multi-platform manifest list conforms to.
- **URL**: https://github.com/opencontainers/image-spec/blob/main/image-index.md
- **Claim supported/refuted**: The `platform` object's fields are `architecture` (REQUIRED, GOARCH-like), `os` (REQUIRED, GOOS-like), `os.version` (OPTIONAL — "specifies the version of the operating system targeted by the referenced blob"), `os.features` (OPTIONAL), and `variant` (OPTIONAL — "specifies the variant of the CPU"). **The Platform Variants table DOES carry a microarchitecture axis**: for amd64 it lists `v1`/`v2`/`v3`/`v4` (mirroring Go's `GOAMD64`); for arm it lists `v6`/`v7`/`v8`. So "microarch level" (the third axis in the question) has a real, spec-legal home as the image-index `platform.variant` field — a tag/manifest CAN legitimately encode base-OS x arch x microarch-variant, because the index schema already has slots for architecture, os(+os.version), and variant simultaneously. **Refutation of one possible reading of the question**: there is **no field for "which builder/runner produced this"** anywhere in the platform object — provenance/builder identity is not an image-index concept at all (it would live in build attestations / SLSA provenance, a separate OCI artifact type, not in the platform tuple). This directly answers the "give each permutation a distinct descriptive image tag" half: the tag string itself is free-form (bake's `tags` attribute), so the base/arch/microarch/runner-choice-driven distinctness is a **tagging convention bake enforces via its own `tags` templating**, not something the image-index format requires or constrains.

### 3. actuated.com blog — "The efficient way to publish multi-arch containers from GitHub Actions"
- **What**: Blog post by Alex Ellis (actuated, GitHub Actions native-arm runner vendor), discussing QEMU vs matrix-build alternatives.
- **URL**: https://actuated.com/blog/multi-arch-docker-github-actions
- **Claim supported**: The post's own recommended default is still QEMU-based (`docker/build-push-action` with a `platforms:` list on one runner) but explicitly names the escape hatch for when QEMU is too slow: "a matrix-build instead of a QEMU-based multi-arch build," pointing at actuated's own native-Arm-VM runners. It does **not** show Docker Bake as part of that matrix pattern — it stays at the `build-push-action` level. **This is evidence AGAINST the idea that bake itself owns cross-runner fan-out**: even a vendor whose entire business is "give you a real arm64 runner for GitHub Actions" describes the native/no-QEMU multi-arch pattern as a **GitHub Actions job-matrix + separate manifest-merge step**, with bake/build-push-action doing only the single-platform build inside each matrix leg.

### 4. sredevopsorg/multi-arch-docker-github-workflow (community reference repo)
- **What**: A GitHub repo demonstrating "How to build a Multi-Architecture Docker Image in Github Actions using multiple runners without QEMU."
- **URL**: https://github.com/sredevopsorg/multi-arch-docker-github-workflow
- **Claim supported**: Per search-result digest, the workflow fans out via a GHA **matrix strategy** into one job per architecture (each `runs-on` its own native runner, e.g. `ubuntu-latest` for amd64 and `ubuntu-24.04-arm` for arm64), each job builds+pushes only its own platform's image, then a separate **manifest job** merges the platform-specific images into one multi-arch tag (`docker manifest create`/`buildx imagetools create`, not bake). Same shape as finding #3: **runner selection lives in the GHA matrix (`runs-on:`), never inside a bake HCL file** — bake (where used at all) operates per-leg, after the runner is already chosen.

### 5. matthewswong.com blog — "Docker Buildx Bake: Declarative Multi-Platform Image Builds"
- **What**: Practitioner blog post walking through a real bake + GHA matrix pipeline.
- **URL**: https://www.matthewswong.com/en/blog/docker-bake-multi-platform-builds/
- **Claim supported — DIRECTLY ANSWERS THE QUESTION**: Verbatim: *"use docker buildx bake --print piped through jq in one job to emit the list of target names, feed that into a GitHub Actions matrix strategy, and run each target in its own parallel job"* — this gives *"every target an isolated runner and, crucially, its own cache scope, so a slow arm64 build never blocks the amd64 ones."* This is the exact shape asked about: **bake owns the permutation set** (targets, expanded via its `matrix` attribute, `--print`-enumerable), **GitHub Actions' job matrix chooses the runner per leg** (outside bake, driven by the enumerated target list), and each leg gets isolation. The one caveat the article itself states: it still keeps `setup-qemu-action` in the workflow because *"arm64 layers are cross-compiled via emulation on amd64 runners unless you attach a native arm64 builder"* — i.e., the "no QEMU" half of the question is satisfied only if the per-leg runner is architecture-matched (e.g., an `ubuntu-24.04-arm` runner building the arm64 leg, per finding #1's labels) rather than an amd64 runner cross-building via QEMU. This is the load-bearing missing piece connecting bake's `--print`/matrix enumeration to finding #1's native-arm64-runner labels.

### 6. containerd/containerd — Issue #9506, "Determine x86-64 micro-architecture levels"
- **What**: Issue on containerd (the OCI-adjacent runtime Docker/BuildKit sit on), closed as **not planned**.
- **URL**: https://github.com/containerd/containerd/issues/9506
- **Claim supported (caveat, not contradiction)**: A request that containerd auto-detect the host's supported amd64 microarch level (v1-v4) via `/proc/cpuinfo` and auto-select the matching image-index entry, the way it already can for arm variants. Closed as not planned. **This narrows finding #2's optimism**: while the OCI `platform.variant` field can legally encode `v1`/`v2`/`v3`/`v4` for amd64 (finding #2), there is **no runtime-side automatic selection of the right microarch variant on pull** — containerd will not pick `v3` for you at runtime. So a bake-produced "container base OS x arch x microarch level" permutation set with distinct tags is a **build-time/tagging convention the pipeline must consume explicitly** (a human or a downstream deploy step picks the tag), not something the container runtime resolves automatically the way it resolves plain `arch`/`os`. Does not contradict feasibility — narrows the "how consumers pick the microarch leg" part.

### Note on a search-engine synthesis artifact (probe hygiene)
A WebSearch summary claimed the oneuptime.com bake/matrix blog post described the `--print | jq` → GHA-matrix → isolated-runner pattern. **Direct WebFetch of that article found no such passage** — only a `bake --print | jq` *debugging* snippet with no GHA-matrix or runner-isolation claim. The real source of that pattern is finding #5 (matthewswong.com), a different URL. Recorded per this repo's `probes-need-a-control-arm.md`: a search-result digest is not itself a verified claim until the primary source is fetched and re-read.

## Which findings CONTRADICT "bake cannot select a runner"

**None do — every source strengthens, not contradicts, the assumption that bake cannot and does not select the GHA runner.** All primary evidence (findings #1, #3, #4, #5) is unanimous and consistent with the composed-diff design under study:

- Bake's job is build-input permutation (targets, `matrix`, `tags`, `platforms`) for a builder that already exists at bake-invocation time (finding #5, #2 — the image-index/platform schema itself has no builder/runner field).
- Runner selection is always external — a GitHub Actions `runs-on:`/job-matrix concern (findings #1, #3, #4), using the GA'd `ubuntu-24.04-arm`/`ubuntu-22.04-arm` labels (finding #1) to get a real native-arch machine per leg.
- The `bake --print | jq` → GHA-matrix pattern (finding #5) is the connective tissue: bake enumerates the permutation set, and a **separate** GHA `matrix:` (fed by that enumeration) is what actually varies `runs-on:` per leg — bake never expresses `runs-on:` because HCL bake files have no such attribute; `--builder`/`--set` only pick *which already-existing builder* a given bake invocation talks to (finding — `docker/buildx#320`), never spawn or select a CI runner.
- No-QEMU is achievable, but is a property of runner **choice** (arch-matched native runner per leg, finding #5's caveat + finding #1's labels), not of bake itself — bake has no emulation-avoidance knob; it just builds whatever platform the builder attached to it supports.

So the answer to the composed question is **yes, achievable, but only by splitting responsibilities exactly the way the assumption implies**: bake enumerates/tags the OS x arch x microarch permutation set (image-index `platform.variant` legally carries the microarch axis per finding #2, tempered by finding #6's caveat that runtime auto-selection doesn't exist), while the GHA workflow's job matrix — built from bake's own `--print` enumeration — is what picks the runner (and therefore avoids QEMU) per leg, entirely outside bake's HCL.

## GitHub repos touched

- [opencontainers/image-spec](https://github.com/opencontainers/image-spec) — read `image-index.md` for the platform object schema (architecture/os/os.version/variant), confirming a microarch-variant field exists but no builder/runner field
- [sredevopsorg/multi-arch-docker-github-workflow](https://github.com/sredevopsorg/multi-arch-docker-github-workflow) — read as a worked example of native-runner (no-QEMU) multi-arch builds via GHA matrix + manifest merge, outside bake
- [docker/buildx](https://github.com/docker/buildx) — read issue #320 ("bake --builder is not working") confirming `--builder`/`--set` select an *existing* builder instance, never a CI runner; searched issues #1064/#2104/#2486/#3173/#3599/#141/#1203/#3810 and discussion #2398 for any per-target runner/matrix-to-runner concept (none found)
- [containerd/containerd](https://github.com/containerd/containerd) — read issue #9506 (closed not-planned) establishing there is no runtime auto-selection of amd64 microarch variant on pull, narrowing how a microarch-tagged permutation set would actually get consumed
