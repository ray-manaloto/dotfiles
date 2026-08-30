# docker/github-builder — research

Source: https://github.com/docker/github-builder

Repo API description: "Official Docker-maintained reusable GitHub Actions
workflows to securely build container images"

## What problem it solves

It is a set of **Docker-maintained reusable GitHub Actions workflows**
(`build.yml`, `bake.yml`, `verify.yml`, `setup-registry-identities.yml`) that
wrap `docker/build-push-action` / `docker/bake-action` / `docker/metadata-action`
into a single trusted, SLSA-attesting build pipeline. Consumers `uses:` the
workflow at a pinned tag (e.g. `docker/github-builder/.github/workflows/bake.yml@v1`)
instead of hand-assembling buildx/bake/metadata/cosign steps in their own
workflow. Selling points per the README: signed SLSA provenance for every
build, signed/verified GitHub Actions cache entries (Cosign-signed, tied to
workflow identity — guards against the cache-poisoning class described in
[docker/github-builder#56](https://github.com/docker/github-builder/issues/56)),
and centralized build config (buildx driver/storage/resource tuning) so
per-repo CI stops reinventing it.

It is explicitly NOT a generic CI runner product — it is a build/attest/push
pipeline wrapper. It does not touch test/deploy stages.

## Does it provide remote/managed builders?

**No.** It does not provide Docker-hosted/managed build compute of its own
(nothing like Depot or Docker Build Cloud). It runs entirely on **GitHub-hosted
runners** — the standard `ubuntu-24.04` / `ubuntu-24.04-arm` labels — selected
via the workflow's own `runner` input. There is no "Docker builder fleet";
buildx/BuildKit runs inside whichever GitHub Actions runner the workflow
schedules.

## Does it remove the need to pick a native GitHub runner per architecture?

**It automates the choice, it doesn't eliminate it as a concept — and the
choice is made OUTSIDE the Bake file, in the reusable workflow's `with:`
block.** From the README's "Runner mapping" section, verbatim:

```yaml
runner: |
  default=ubuntu-24.04
  linux/arm=ubuntu-24.04-arm
  linux/arm64=ubuntu-24.04-arm
```

> A mapping must define a `default` runner. Additional keys are platform
> prefixes, and the most specific matching prefix wins.

Combined with `distribute: true` (the default), the reusable workflow fans a
multi-platform Bake target out into **one GitHub Actions job per platform**,
each scheduled on the runner label the mapping selects for that platform —
"Native parallelization for multi-platform builds... without requiring
emulation or custom CI logic or self-managed runners" (README, Performance
section). Setting `distribute: false` collapses it back to one job building
every platform together (which — per the QEMU test job below — needs
`setup-qemu: true` to cross-build without native runners).

This is a real answer to the question's core ask: **Bake owns the
platform/target permutation set (`docker-bake.hcl`), while GH-runner-per-leg is
a workflow input the caller sets outside the HCL file**, and as long as you
don't set `setup-qemu: true`, no leg builds under QEMU — each platform gets a
runner whose native arch matches, confirmed by the `bake-qemu` test job
existing as a **separate, deliberately-opted-in** test case:

```yaml
bake-qemu:
  uses: ./.github/workflows/bake.yml
  with:
    setup-qemu: true
    artifact-upload: false
    context: test
    output: local
    sbom: true
    target: hello-cross
```

i.e. QEMU is off by default; you opt in per-workflow, not per-leg — the
workflow does not mix native and emulated legs within one call.

### Image tags per permutation

Distinct descriptive tags per permutation are the `docker/metadata-action`
integration surface (`meta-images` / `meta-tags` / `meta-flavor`), which is
config on the **workflow caller**, not on the Bake file. Real example from the
test suite (`.github/workflows/.test-bake.yml`):

```yaml
meta-images: |
  ghcr.io/docker/github-builder-test
  docker.io/dockereng/github-builder-test
meta-tags: |
  type=raw,value=${{ github.run_id }},prefix=bake-ghcr-and-dockerhub-
```

Bake-side, `set` (a newline-delimited `target.key=value` list, supports
Handlebars `{{meta.version}}` templating) is the mechanism for per-target
overrides such as build args:

```yaml
set: |
  *.args.VERSION={{meta.version}}
```

**What the project does NOT give you**: a first-class "microarch level"
(x86-64-v2/v3, cpu-feature) axis. The only platform axis it understands is the
Bake/buildx `platform` string (`linux/amd64`, `linux/arm64`, `linux/arm/v7`,
etc.) plus the runner-mapping's platform-prefix matching. A base-OS ×
arch × microarch × runner permutation set would have to be expressed as
distinct Bake **targets** (one per permutation, each with its own `platforms`
and tag-producing `docker-metadata-action` inheritance) — github-builder does
not add a native microarch dimension on top of that; it only adds signed
provenance/cache and the runner-selection-per-platform layer described above.

## Maturity, pricing, hard limits — blunt assessment

**Maturity**: young by calendar age but on a real cadence. Repo created
2025-08-18, first `v1.0.0` tag 2026-01-29, current tag `v1.17.0` released
2026-08-21 (measured via GH API). Releases have landed roughly every 1–3 weeks
since v1.0.0 (18 releases in ~7 months) — active development, not abandoned,
not stale. 81 stars, 27 open issues, not archived. Uses `v1` and `v1.x.y`
semver tags, so `@v1` floats to the latest v1.x.y — standard GitHub Actions
reusable-workflow pinning convention, same trust model as any other
`docker/*-action`.

**Is it production-ready?** For what it does — a Docker org first-party
wrapper — yes, it looks production-grade: it has its own CI matrix (dozens of
integration jobs in `.test-bake.yml`/`.test-build.yml` exercising Docker Hub
OIDC, AWS ECR public/private, GCP WIF, GHCR, local/image output, sign/nosign,
distribute/no-distribute, QEMU, named build contexts, index annotations, image
casing), a security-scan job (`crazy-max/ghaction-container-scan`), and a
`.zizmor.yml` workflow (zizmor is a GitHub Actions security linter) — i.e. the
project eats its own dogfood and lints its own Actions posture. That said it
is **only ~7 months old as of this research (2026-08-30)** and Docker itself
has not (per the README) marked it GA/stable beyond the `v1` tag convention —
treat it as "actively shipped, pre-1.0-in-spirit-but-tagged-v1" rather than a
decade-stable dependency.

**Pricing/availability**: no separate pricing — it consumes ordinary
GitHub-hosted runner minutes (billed by GitHub, same as any workflow) plus
GitHub Actions cache storage. No Docker subscription/service tier is required
to use `build.yml`/`bake.yml`. Registry auth is BYO (Docker Hub OIDC, AWS ECR
via OIDC role assumption, GCP Artifact Registry via Workload Identity
Federation, or raw `registry-auths` secret) — the `registry-identities` input
is explicitly documented as non-secret identity metadata only ("Do not put
passwords, tokens, client secrets, private keys, raw cloud credential JSON...
in this input").

**Hard limits / caveats found**:
- `runner` only accepts a **single label or platform-prefix mapping to
  GitHub-hosted Linux runner labels** — it doesn't abstract over self-hosted
  runners or other clouds; you still write real GH runner labels
  (`ubuntu-24.04-arm`, etc.) yourself.
- The `runner: amd64` shorthand form appears in the test matrix
  (`bake-set-runner-deprecated`) — named "deprecated" in the test job id,
  implying the bare-arch shorthand is being phased out in favor of the
  explicit runner-label mapping form.
- `output` only accepts `image` or `local` — narrower than
  `docker/build-push-action`'s general `outputs` passthrough.
- No microarch-level (CPU feature) axis — platform is the only build-matrix
  primitive; a microarch dimension has to be modeled as extra Bake targets.
- Signed cache/provenance depends on `id-token: write` (GitHub OIDC) being
  granted by the caller; without it those guarantees don't apply.
- Issue #56 (referenced in the README's cache section) documents the SLSA
  isolation concern the signed-cache feature exists to close — worth reading
  directly if adopting the cache exporter for a security-sensitive pipeline.

## Direct answer to the posed question

Yes — this is exactly the shape github-builder supports: Bake (`docker-bake.hcl`,
via the caller's `context`/`files`/`target` inputs) owns the build-input
permutation set and produces distinct tags per permutation through
`docker/metadata-action` (`meta-images`/`meta-tags`), while the GitHub Actions
runner per leg is chosen by the **caller's `runner:` input to the reusable
workflow** — outside the Bake file itself — and with `distribute: true`
(default) and `setup-qemu` left unset, each platform leg runs on a
GitHub-hosted runner native to that platform, with no leg going through QEMU
emulation. The one gap: it adds no first-class "microarch level" axis beyond
what you encode as extra Bake targets/platforms yourself.

## GitHub repos touched

- [docker/github-builder](https://github.com/docker/github-builder) — primary
  source: README, reusable workflows (`build.yml`, `bake.yml`, `verify.yml`),
  test fixtures (`test/docker-bake.hcl`), CI test workflow
  (`.github/workflows/.test-bake.yml`), tags/releases via the GitHub API.
