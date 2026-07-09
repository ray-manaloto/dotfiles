# Run B / Angle 2 — The case for ONE image everywhere (evaluated, largely negative)

Date: 2026-07-09. Agent: single-image (research analyst). Bash unavailable —
evidence from Read/Grep of the working tree at `main`, GitHub Actions API job
timings (GitHub MCP), the local mintlify cache, and web fetches of official
GitHub/Anthropic docs. Sibling artifacts cross-referenced:
`agents/current-graph.md` (Run B angle 1) and
`../research-20260709-r2-web-env/agents/official-docs.md` (Run A angle 1).

**Bottom line up front:** one-image-everywhere is *blocked outright on the web
leg today* (custom base images unsupported; 30 GB disk ceiling < the ~38 GB
image), and on the CI leg it is *strictly dominated* by the existing
mise-on-runner path (measured 5-25 s tool restore vs a measured 5m27s full-image
pull per job — with $0 marginal dollar cost either way, so the fight is pure
wall-clock and reliability). The only leg where one heavy image is right is the
devcontainer — which is exactly today's topology. The honest framing: today's
architecture is already "one image for the devcontainer + mise-everywhere for
everything else," and the mise tier files (shared.toml + lockfiles) already
deliver the version-parity benefit that one-image-everywhere would exist to
provide. Conditions under which the verdict flips are enumerated in F8.

## Findings

### F1. Web leg: hard-blocked as a session base; marginal even as a sidecar

- **Custom base images are explicitly unsupported.** The official Claude Code
  docs state: "Replacing the base image with your own Docker image is not yet
  supported. Use a setup script to install what you need on top of the provided
  image, or run your image as a container alongside Claude with `docker
  compose`." (https://code.claude.com/docs/en/claude-code-on-the-web, fetched
  2026-07-09, §Setup scripts). This VERIFIES the Run A carried-in claim from
  yesterday's session — it is no longer an unverified assumption.
- **Resource ceiling kills even the sidecar path for the full image:** cloud
  sessions run at "4 vCPUs / 16 GB of RAM / 30 GB of disk" (same page,
  §Resource limits, per the Run A official-docs agent's full-page capture at
  `../research-20260709-r2-web-env/agents/official-docs.md:31`). The ~38 GB
  `:dev` image (build-publish.yml:631) cannot fit on a 30 GB disk regardless of
  mechanism.
- **The sanctioned "image-like" mechanism is setup script + filesystem
  snapshot**, not an image: "After it completes, Anthropic snapshots the
  filesystem and reuses that snapshot as the starting point for later
  sessions... New sessions start with your dependencies, tools, and Docker
  images already on disk" — with a "roughly five minutes" setup-script budget
  and ~7-day cache expiry (same page, §Environment caching / §Setup scripts).
  Docker IS available in-session ("docker, dockerd, docker compose",
  §Installed tools) and ghcr.io is on the Trusted allowlist, so a *small*
  image could ride `docker pull` in the setup script — but a sidecar container
  is not the session environment: Claude's own Bash/tools run in the outer
  Anthropic VM, so every toolchain invocation would need `docker exec`
  wrapping, which no repo tooling (hk, mise tasks, hooks) is written for.
- The web VM already ships most of the lean-CI toolchain natively: "Python 3.x
  with pip, poetry, uv, black, mypy, pytest, ruff", "GCC, Clang, cmake, ninja,
  conan", git/jq/ripgrep (§Installed tools) — i.e., the marginal install for a
  web session is mise + the 20-tool shared fragment, minutes of setup script,
  not an image at all.

### F2. CI leg: measured baseline — mise-on-runner is 5-25 s per job, effectively unbeatable

Measured from real runs via the Actions API (repo ray-manaloto/dotfiles):

| Job | "Install mise" step | Total job | Run |
|---|---|---|---|
| lint (full root mise.toml toolset, warm mise-action cache) | 25 s (10:23:37→10:24:02) | 45 s | run 29011164725 (2026-07-09, main) |
| lint (same, second sample) | 20 s | 41 s | run 28970137705 (2026-07-08, main) |
| contract-preflight (`install_args: "python uv"`) | 6 s | 12-13 s | runs 29011164725 / 28970137705 |
| promote (manifest-only retag :pr-NNN → :dev/:latest) | n/a — retag step 9 s | 24 s | run 28970137705 |

The cache mechanics behind those numbers: jdx/mise-action "restores the entire
mise data directory directly from GitHub's cache — so your workflow starts
executing tool commands almost immediately", keyed content-addressably on
`{platform}-{install_args_hash}-{file_hash}`
(docs/research/mintlify-cache/jdx/mise-action/llms-full.txt:117-170;
.github/actions/setup-mise/action.yml:9-19). `MISE_LOCKED=1` pins lint to
mise.lock (ci.yml:76-81), which is the SAME lock the Mac host consumes — CI/host
parity is already delivered *without* an image (ci.yml comment "macOS local ==
CI/CD parity principle", ci.yml:77-80; sibling F6 in `current-graph.md`).

### F3. CI leg: measured cost of putting the ONE image in the job path — ~5.5 min pull per job, plus disk games

- **Measured full-image pull on ubuntu-latest: 5m27s** — image-analysis run
  29013595948 (2026-07-09), job 86102935590, step "Pull image" 11:08:32 →
  11:13:59. This is the intra-Azure best case (Actions runner → GHCR).
- **Disk is a second tax.** GitHub's runner spec for public-repo ubuntu-latest
  is "4 vCPU / 16 GB RAM / 14 GB SSD"
  (https://docs.github.com/en/actions/reference/runners/github-hosted-runners,
  fetched 2026-07-09). The repo's own history shows the smoke-test job died
  with "no space left on device" extracting the image until
  `jlumbroso/free-disk-space` was added, which itself costs **5m40s** measured
  (build job, run 29011164725, step 2: 10:30:07→10:35:47; rationale comments
  at build-publish.yml:630-644 and :478-505).
- GHA `container:` jobs pull the job image in the "Initialize containers"
  phase on every job on every run — hosted runners are fresh VMs with **no
  cross-run layer cache**, so N jobs × M runs each pay the full pull. Today's
  ci.yml has 4-6 runner jobs per PR run (lint, contract-preflight, changes,
  ci-gate, plus 3-6 build-publish jobs when the image chain runs): converting
  even just lint + contract-preflight to run *in* the one image adds ~11 min of
  pull (2 × 5m27s) to replace 31 s of mise restores — a **>20× regression** on
  the critical path, before disk-freeing.
- **Dollar cost is zero either way; the currency is latency + reliability.**
  "GitHub Actions usage is free for... public repositories that use standard
  GitHub-hosted runners"
  (https://docs.github.com/en/billing/concepts/product-billing/github-actions);
  "Container image storage and bandwidth for the Container registry is
  currently free," and Actions-driven downloads of private packages don't
  count against the owner's transfer quota either
  (https://docs.github.com/en/billing/concepts/product-billing/github-packages).
  Larger runners (more disk/CPU) ARE billed "even when used by public
  repositories" — so a topology that *requires* larger runners converts a free
  CI into a paid one.
- Reliability tail-risk is real and registry-side: community reports of GHCR
  degradation include a 1.5 GB image pulling in 8m14s from ghcr.io vs 14 s from
  docker.io (https://github.com/orgs/community/discussions/173607; see also
  /discussions/27080). A per-job image dependency multiplies exposure to such
  incidents by job count; mise-action's GitHub-cache restore path does not
  touch GHCR at all.

### F4. The one measured fact that mildly HELPS the one-image case (and undercuts the ~38 GB doc figure)

The image-analysis `analyze` job (run 29013595948, 2026-07-09) pulled the full
`:dev` image and ran Dive + Trivy on a stock ubuntu-latest runner **with no
free-disk step at all** (job steps go login → "Pull image" directly;
image-analysis.yml:43-84 confirms no free-disk-space step) — and succeeded.
Either (a) the image has shrunk well below the ~38 GB written into
build-publish.yml:631 / mise.toml:230 / sync.py:40, or (b) current
ubuntu-latest runners provision far more free disk than the documented
"14 GB SSD". Both readings weaken doc-figure-based sizing arguments in ALL
angles of this run (the sibling current-graph.md flags the same figure as
unmeasured, its Uncertainty 1). Even in the friendliest reading, the pull is
still 5m27s — the F3 conclusion (one image loses the per-job CI race by >20×)
does not change; only the disk-freeing surcharge might.

### F5. Devcontainer leg: one image is correct here — and it is the status quo

The devcontainer is the only consumer that needs the heavy payload
(clang-p2996 + gcc-latest + conda C++ toolchain), and it already consumes
exactly one image (`:dev`) plus a thin local host-user overlay
(.devcontainer/AGENTS.md §Purpose). The Mac-side cost of that one image —
"the ~38GB buildkit pull can take hours; that is expected and fine"
(.claude/rules/verify-before-advancing.md:77) — is paid once per base refresh,
not per session, which is the correct amortization profile for a heavy image.
One-image-everywhere would not improve this leg; it would only export this
leg's weight to the two legs that can't carry it (F1, F3).

### F6. The parity benefit one-image-everywhere would buy is already ~90% delivered by the mise tiers

The strongest argument FOR one image is drift-proofing: every environment runs
byte-identical tools. But this repo already has:

- the 20-tool exact-pinned shared fragment merged by BOTH host and image
  (.config/mise/conf.d/shared.toml; Dockerfile:139; base-hash covers its bytes
  per P2996-CACHE.md:63-66);
- `MISE_LOCKED=1` CI installs against the same mise.lock the host uses
  (ci.yml:76-81);
- native mise lockfiles with rattler per-package sha256 for the image tiers
  (mise-system.lock / mise-runtime.lock; P2996-CACHE.md:51-56).

What lockfiles do NOT cover is the apt layer / glibc / distro base — bit-level
parity there genuinely requires running in the image. But no current CI job
compiles or runs C++ against those layers (lint/contract jobs are
pkl/python/shell tooling only — sibling F6), and web sessions run Anthropic's
Ubuntu 24.04 regardless (F1). So the marginal parity value of one image
everywhere, today, rounds to zero.

### F7. Warm-path / gate interaction: one-image-everywhere is the null delta on the build side

Because shape (i) keeps exactly today's single published artifact, it is the
only candidate with ZERO changes to: the three-tier content-hash probe
(base/p2996/dev hashes, P2996-CACHE.md:40-77), `promote`'s single-manifest
retag (ci.yml:326+), `dev-tag`'s smoke-validated marker, ghcr-cleanup's tag
families, and `verify-container-latest`'s tier-1 identity check
(mise.toml:446+; scripts/devcontainer-smoke.sh). All of its costs land in
ci.yml job definitions (adding `container:` or pulls) and in the web
environment (where it is blocked). This is worth stating because it means the
*build-side risk* of shape (i) is nil — the shape fails on consumption
economics, not on cache/gate engineering.

### F8. Conditions under which ONE image everywhere would win (the flip list)

1. **Anthropic ships custom base images for web** (docs say "not YET
   supported" — the only roadmap signal) AND the image fits the session disk
   ceiling (30 GB documented today) AND session provisioning amortizes the
   pull the way the setup-script snapshot does. All three are outside this
   repo's control; the first is tracked upstream (anthropics/claude-code
   issue #29515 per the Run A brief — not independently verified here).
2. **The image gets small.** If the heavy C++ payload moved out (or the lean
   stage of shape (ii)/(iii) became the CI/web artifact), a ~1-2 GB image
   pulls in ~20-60 s — competitive with mise-action's 5-25 s restore only if
   it also replaces >30 s of job work. The 2026-03-29 benchmark's 1.33 GB
   lean-core figure (docs/research/trail/findings/docker-benchmarks/
   docker-desktop-2026-03-29.json:14) is the existence proof that the
   non-C++ core is that small. Note this flip condition is precisely the
   two-image shapes — it is not a defense of shape (i).
3. **CI acquires jobs that exercise the image's unique layers** — e.g., a C++
   reflection test suite compiled with clang-p2996 in CI. Then at least THAT
   job should run in (or docker-run against) the image; today's smoke-test
   already embodies this pattern for image validation.
4. **Self-hosted or cache-warm runners.** A persistent runner with a local
   containerd/Docker layer cache makes per-job pulls ~free after the first.
   That contradicts this repo's zero-infra posture and turns free public-repo
   CI into paid/maintained infrastructure (F3, larger-runner billing note).
5. **Job-count collapse.** If CI were restructured to one long mega-job, a
   single 5.5-min pull amortizes better — but the current DAG exists for
   parallelism and path-gating (changes/ci-gate), and 5.5 min would still
   dwarf the 31 s it replaces.

None of conditions 1-5 hold today; 2 argues for the sibling shapes, not (i).

## Uncertainties / gaps

- **Image size figure.** The ~38 GB is documentation, not measurement, and F4's
  no-disk-freeing pull success suggests it (or runner disk specs) has drifted.
  The `devcontainer-metrics` artifact from image-analysis run 29013595948
  (2026-07-09) contains the registry-manifest compressed size; it could not be
  downloaded in this Bash-less session. Resolve before finalizing any
  size-based recommendation.
- **GHCR package visibility.** Anonymous fetch of the package page
  (github.com/ray-manaloto/dotfiles/pkgs/container/dotfiles-devcontainer)
  returned 404 — consistent with a private package (or a URL-shape miss). If
  private, a web-session `docker pull` additionally needs a PAT in plain-text
  environment variables (no secrets store on web — Run A F/§3), one more
  friction on any web-pulls-the-image scheme.
- **Web session pull throughput** is unmeasured; the 5m27s figure is
  Azure-runner→GHCR. Anthropic's sandbox egress goes through a security proxy
  and may be materially slower; the ~5-min setup-script budget makes this the
  deciding unknown for even a *lean*-image pull on web (setup-script docs
  recommend moving big downloads to background SessionStart hooks).
- **Whether smoke-test's free-disk step is still needed** (vs the F4
  observation) — cheap to A/B in a PR, saves ~5.7 min per image-building run
  if droppable. Not tested here.
- **`container:` job overhead beyond the pull** (extraction, container
  create, per-step exec wrapping) was not separately measured; published
  benchmarks conflate it with pull time. Direction of error: makes shape (i)
  look *better* than it is, so it does not threaten the verdict.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — working-tree reads (Dockerfile, docker-bake.hcl, ci.yml, build-publish.yml, image-analysis.yml, P2996-CACHE.md, AGENTS.md set, mise tier files, benchmark JSONs) + Actions API job timings for runs 29011164725 / 28970137705 / 28965970048 / 29013595948.
- [jdx/mise-action](https://github.com/jdx/mise-action) — cache mechanism + key template docs via the local mintlify cache (llms-full.txt).
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — official web docs (code.claude.com/docs/en/claude-code-on-the-web) for base-image/resource/setup-script/Docker-in-session facts.
- [jlumbroso/free-disk-space](https://github.com/jlumbroso/free-disk-space) — the disk-freeing action whose measured 5m40s runtime is part of the per-job image cost.
- [community/community](https://github.com/orgs/community/discussions/173607) — GHCR degraded-pull evidence (also discussion 27080).
- [actions/runner-images](https://github.com/actions/runner-images) — referenced by GitHub docs for runner disk layout (not read in depth).
