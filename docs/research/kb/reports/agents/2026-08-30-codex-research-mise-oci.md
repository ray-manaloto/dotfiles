# Research: mise OCI features vs this repo's devcontainer caching (for #736)

## Sources read

- **Primary (offline, read in full):**
  `~/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/dev-tools/mise-oci.md`
  `~/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/oci.md`
  These fully answered every research question below — no fallback to
  `bootstrap/` docs, live web, or WebSearch was needed.
- **This repo's caching context (read in full):**
  `.devcontainer/P2996-CACHE.md`, `.github/workflows/AGENTS.md`,
  `docker-bake.hcl`, `.devcontainer/mise-system.toml`.

## Q1 — What does mise's OCI backend/feature actually do?

`mise oci` (three subcommands: `build`, `run`, `push`) turns a `mise.toml`
into a **container image where each installed tool is its own OCI layer**.
It is not a tool-download cache and not an artifact-caching mechanism for
arbitrary build outputs — it's a Dockerfile *replacement* for producing an
image whose tool set is declared in `mise.toml`.

> "`mise oci build` turns a `mise.toml` into a container image, with one
> OCI layer per installed tool... mise's on-disk layout (every tool
> installed in an isolated `$MISE_DATA_DIR/installs/<plugin>/<version>/`
> directory) makes layer ordering semantically irrelevant, so swapping a
> tool's version swaps a single layer and everything else... is reused
> unchanged."

Layer order (from the doc): base image layers → mise binary → one
`[bootstrap.packages]` layer (apt OR apk, not both) → one layer **per
tool** (rooted at `/mise/installs/<plugin>/<version>/`) → `[dotfiles]`
layer → synthesized `/etc/mise/config.toml`.

`mise oci push` has its own layer-reuse cache: a tool layer is reused from
the registry (skipping local install + tar/gzip) when its cache key
(tool, version, in-image prefix, file owner) matches what's already
published under the destination ref (or `--cache-from` another tag in the
same repo).

**Explicitly marked experimental** — requires
`mise settings experimental=true` / `MISE_EXPERIMENTAL=1`; "Flags, output
layout, and defaults may change in future releases."

## Q2 — Could it replace/simplify the P2996 cache or the base/dev content-hash tiers?

**No — it's the wrong shape of tool for both, and adopting it would be a
rewrite, not a simplification.**

**P2996 compiler cache:** the clang-p2996 fork is built from source via
`cmake`/`ninja` inside a Dockerfile stage (`clang-builder-cold`), not
installed through any mise backend. `mise oci build`'s entire value
proposition is "one layer per *mise-managed tool install directory*" —
there is no mise-backend equivalent of "compile this git ref with these
build flags and export `/opt/clang-p2996`". The only way to fold it into
`mise oci build` would be `--copy HOST_PATH:IMAGE_PATH` (copy an
already-built prefix into the image as an extra layer) — but that still
requires the existing Dockerfile-based cmake/ninja build to happen first,
so it wouldn't delete any of `p2996_hash.py`, the `p2996-prep` CI job, or
the `docker manifest inspect` probe; it would just add a second packaging
tool on top of the one already doing the job (`docker-bake.hcl`'s
`p2996-cache` target + `FROM scratch` export). Net: more moving parts, not
fewer.

**Base/dev content-hash tiers:** the base stage installs ~58 pinned
apt LLVM packages plus a `[bootstrap.packages]` set, and 20+ conda-forge
tools, all via a multi-stage `Dockerfile` consumed by `docker-bake.hcl`.
`mise oci build` does support `[bootstrap.packages]` `apt:` entries for
OCI images ("For image builds... OCI builds support `apt:` entries with a
Debian/Ubuntu base image... emits the filesystem changes as **one** OCI
layer") — but that collapses the whole apt set into one layer, which is
strictly coarser than what this repo already has today (an entire
Dockerfile *stage*, hash-gated as one unit, is roughly equivalent
granularity — no gain). Migrating the base/dev build to be `mise.toml`-native
would mean giving up: the two-stage `p2996-cache`/`p2996-export`
`FROM scratch` split, the digest-pinned named-build-context injection
(`dev.contexts.*=docker-image://…@sha256:…`) that skips rebuilds entirely
on a hash hit, the zstd/OCI compression + `force-compression` tuning in
`docker-bake.hcl`, and the SBOM/provenance attestations already wired via
`attest = ["type=provenance,mode=max", "type=sbom"]` on every published
target. None of that has a `mise oci` equivalent in the docs read. This
would be a from-scratch reimplementation of `#160`/`#222`'s work, not a
deletion of custom code.

## Q3 — Per-architecture/platform awareness relevant to #736's arm64 leg-identity gap?

**Yes, and this is the one genuinely relevant finding.** `mise oci push
--update-index` supports assembling a **multi-arch image index from
separate per-architecture pushes**, explicitly sequenced to avoid a
read-modify-write race:

```yaml
jobs:
  push-amd64: # runs-on: ubuntu-24.04
    run: mise oci push --update-index ghcr.io/me/dev:latest
  push-arm64: # runs-on: ubuntu-24.04-arm
    needs: push-amd64 # sequence to avoid a read-modify-write race
    run: mise oci push --update-index ghcr.io/me/dev:latest
```

> "Re-pushing the same platform replaces its entry (no duplicates)...
> Note the index update is read-modify-write (the Distribution API has no
> conditional writes), so concurrent pushes to the same tag from
> different runners can race — sequence them as above."

This confirms the *pattern* #736 needs (per-runner leg → per-platform
manifest → sequenced index assembly) is a known, documented shape — but
it's a capability of `mise oci push`'s own index-management code, not a
generic caching primitive that plugs into `docker-bake.hcl`'s existing
GHCR-tag probe cache. It does **not** natively key cache entries by
*runner identity* (only by platform), so it would not by itself
distinguish "two arm64 legs on different runners" any better than the
current content-hash scheme — `mise oci`'s per-arch model still assumes
one push per (tag, platform) pair, same granularity gap. The value here
is as a **design reference for the sequencing discipline**, not as an
adoptable mechanism — `.github/workflows/AGENTS.md`'s `manifest` job
already does the equivalent (assembles the index from per-leg
`:<sha>-<arch>` pushes and asserts every architecture resolves to a
distinct image).

## Q4 — Maturity/stability

**Experimental, explicitly and prominently.** The doc's first substantive
section is a warning block:

> "::: warning Experimental
> `mise oci build` is experimental. Enable it with:
> `mise settings experimental=true`... Flags, output layout, and defaults
> may change in future releases. :::"

Also v1 known limitations relevant here: `asdf`/`vfox` backends rejected
outright ("Using them errors out with a clear message" — not applicable,
this repo doesn't use them, but flags the tool's overall newness);
cross-platform builds produce broken images (must build on the target
Linux arch, same constraint this repo already works around for
`arm64`/`amd64`); Alpine/musl base images break most tools (irrelevant,
this repo uses Ubuntu/glibc).

No version number is given in either doc for when `oci` shipped or what
mise version introduced it — its own docs simply flag it as experimental
throughout, with no stability timeline stated.

## Q5 — Recommendation

**Not a good fit for #736, and not worth a dedicated future exploration
either — pass, for three concrete reasons from the docs above:**

1. **Experimental flag on production CI.** Every command in this repo's
   3-tier cache sits on the PR-blocking critical path
   (`base-prep`/`p2996-prep`/`dev-prep`/`build`/`smoke-test`). Building
   any of that around a feature whose own docs say "flags, output layout,
   and defaults may change in future releases" is the wrong risk profile
   for a gate the whole pipeline depends on.
2. **Category mismatch for the expensive part.** The P2996 compiler is a
   from-source cmake/ninja build, not a mise-backend tool install —
   `mise oci`'s entire mechanism (one layer per `$MISE_DATA_DIR/installs/`
   directory) doesn't reach it. `--copy` could staple the artifact in
   after the fact, but that adds a second packaging tool instead of
   replacing the existing GHCR-tag + `docker manifest inspect` probe
   (`p2996_hash.py`) — no code gets deleted.
3. **Base/dev image is already Dockerfile/bake-tuned beyond what `mise
   oci build` expresses.** The digest-pinned named-build-context
   injection, the `FROM scratch` P2996 export, the zstd compression +
   `force-compression` recompression logic, and the provenance/SBOM
   attestations on every published target are all bake/BuildKit features
   with no stated `mise oci` equivalent. Migrating would be a rewrite
   that discards #160/#222's tuning, not a simplification.

The one thing worth carrying forward *as an idea, not as a dependency*:
`mise oci push --update-index`'s documented sequencing pattern
(`needs: push-amd64` before `push-arm64`, same tag) is independent
confirmation that per-arch-then-assembled-index is the right shape for
#736's multi-runner arm64 problem — which is exactly what this repo's
`manifest` job already does. No action item beyond noting the docs agree
with the existing design.

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — source referenced by the offline docs for `mise oci build/run/push` (`src/cli/oci/mod.rs`); not fetched live, cited only via the vendored doc pages read above.
