# Adversarial review: mise per-tool OCI layering + declarative platform conditionality (#736)

Scope: narrower than the prior `mise oci` wholesale-pipeline verdict
(`research-mise-oci-features.md`, not re-litigated). This reviews two specific
questions for `.devcontainer/mise-system.toml`'s individually mise-managed
tools (not the P2996/GCC from-source builds).

## Q1 — Docker image layer advantage from mise features

**What mise supports, cited:**

> "`mise oci build` turns a `mise.toml` into a container image, with one OCI
> layer per installed tool... bumping any single tool version only
> invalidates one content-addressable blob."
> — `knowledge-base/sources/mise/docs/dev-tools/mise-oci.md`

> "**One layer per tool**, each rooted at `/mise/installs/<plugin>/<version>/`."
> — same file, "How layering works"

> "**Not supported in v1:** `asdf` and `vfox` plugins... Their install
> scripts can write outside the per-version directory, breaking the
> one-layer-per-tool invariant. Using them errors out with a clear message."
> — same file, "Supported backends"

> "[experimental] Build OCI container images from a mise.toml... requires
> `mise settings experimental=true`."
> — `knowledge-base/sources/mise/docs/cli/oci.md`

**This repo's current baseline (self-read this session):**

`.devcontainer/Dockerfile:347` and `:678`:
```
mise install --system --locked -y && \
test "$(mise ls --installed | wc -l)" -gt 0 || …
```
This is a single `RUN` — one Docker layer installs the **entire**
`mise-system.toml` tool set (`node`, `go`, `rust`, `zig`, `java`, `deno`,
`ruby`, `cargo-binstall`, all `conda:*` tools, `bazel`, `sqlite`,
`micromamba`) at once. Docker's own layer-cache semantics already apply here
the way they always do: bumping the `mise-system.toml`/`mise-system.lock`
COPY (`Dockerfile:127,133`) invalidates the content hash for that COPY layer,
which invalidates every downstream `RUN`, including this single combined
install — so today, bumping **any one** tool (e.g. `node = "latest"` →
pinned) busts the whole install layer, reinstalling every other tool too.

**Verdict: real, narrow win — but a moderate rework, not a drop-in.**

`mise oci build`'s one-layer-per-tool model is a genuine improvement over
"one RUN installs everything" for this exact pain point (`node` bump forces a
`bazel`/`rust`/all-conda reinstall). But adopting it is not "flip a flag":

1. **It replaces the install step, not the whole pipeline.** `mise oci build`
   produces its own image (base + mise binary + apt/bootstrap layer + one
   layer per tool + dotfiles + synthesized `/etc/mise/config.toml`), a
   different shape from this repo's multi-stage
   `base → devcontainer-runtime → dev/dev-host-user` pipeline
   (`docker-bake.hcl` targets, `.devcontainer/Dockerfile` stages). It is not
   a "COPY this in" primitive for an existing Dockerfile — it IS a Dockerfile
   alternative for the tool-install portion.
2. **Backend coverage gap hits this repo directly.** `conda:*` isn't in the
   documented supported-backend list (`core, aqua, cargo, npm, go, pipx,
   github, gitlab, forgejo, ubi, spm, http, s3, gem, conda, dotnet` — actually
   `conda` IS listed). Re-checking: `conda` **is** in the supported list, so
   `conda:gxx`, `conda:cmake`, `conda:ninja`, etc. would layer individually.
   The real gap is **`[bootstrap.packages]` (`apt:*`)** — supported only via
   a separate "one apt layer, still combined" mechanism (see below), so the
   58-package LLVM-22 apt block stays one layer regardless; it was never a
   `[tools]` entry and OCI's per-tool granularity doesn't apply to it.
3. **`[bootstrap.packages]` apt/apk support exists but is still COARSE, not
   per-package:**
   > "For packages, OCI builds support `apt:` entries with a Debian/Ubuntu
   > base image... mise unpacks the base image into a temporary rootfs,
   > calls the matching host package manager to install into that rootfs,
   > then emits the filesystem changes as **one OCI layer** annotated with
   > `dev.mise.system.packages=apt`."
   > — `mise-oci.md`, "[bootstrap] and [dotfiles] in OCI images"

   So the 58-package LLVM apt block and the 14-package base apt block would
   still each collapse to one shared layer under OCI too — no improvement
   over the status quo for that surface, which is most of this repo's build
   time-sensitive packages.
4. **Experimental, and pinned to a target this repo explicitly avoids
   locally.** `mise oci build` needs `MISE_EXPERIMENTAL=1`. This repo's own
   `mise-system.toml` already sets `[settings] experimental = true` for
   *other* reasons, so that specific gate isn't new friction — but shipping
   production image builds on a documented-experimental subsystem, with
   "Flags, output layout, and defaults may change in future releases," cuts
   against `do-not.md` #2/#4's spirit of CI-only, stable, loud-failure image
   builds.
5. **It doesn't replace what Dockerfile+bake give for free today that this
   repo relies on:** `docker-bake.hcl` multi-arch fan-out via BuildKit's
   `platforms = ["${PLATFORM}"]` per matrix leg (`docker-bake.hcl:106`),
   GHA layer caching (`type=gha,scope=...`, `docker-bake.hcl:145-148`), the
   multi-stage `base`/`p2996-cache`/`devcontainer-runtime`/`dev`/`dev-load`
   targets, and the from-source P2996/GCC compiler stage this repo's whole
   pipeline exists to support (out of scope here, per the prior verdict).
   `mise oci push --update-index` (multi-arch via one job per arch,
   `mise-oci.md` "Multi-arch images") is real, but it's a parallel multi-arch
   mechanism this repo would have to re-plumb alongside/instead of bake's,
   not use in combination with it.

**Concrete scope, if pursued:** a genuine per-tool layer win applies **only**
to the `[tools]` block of `mise-system.toml` — `node`, `go`, `rust`, `zig`,
`java`, `deno`, `ruby`, `cargo-binstall`, the ~14 `conda:*` entries, `bazel`,
`sqlite`, `micromamba` (all listed backends `core`/`conda` are OCI-supported
per the doc). It does **not** help the apt/LLVM block (still one layer either
way) and does not replace the P2996 build stage or bake's multi-arch/caching
machinery. Net: a real but bounded win, gated behind adopting an experimental
mise subsystem as a parallel/replacement image-build path for one segment of
one stage — not a drop-in Dockerfile optimization. **Verdict: complexity
trade, not a clear net win for this repo today**, given the experimental
status, the apt-layer non-improvement, and the need to re-architect around a
second build mechanism rather than extend the existing bake pipeline.

## Q2 — Declarative per-tool platform conditionality in `mise.toml`

**What mise supports, cited (this IS real and directly usable):**

> "## OS-Specific Tools
>
> You can restrict tools to specific operating systems using the `os` field:
>
> ```toml
> [tools]
> # Only install on Linux and macOS
> ripgrep = { version = "latest", os = ["linux", "macos"] }
>
> # Only install on Windows
> "npm:windows-terminal" = { version = "latest", os = ["windows"] }
> ```
>
> The `os` field accepts an array of operating system identifiers:
> - `"linux"` - All Linux distributions
> - `"macos"` - macOS (Darwin). `"darwin"` is also accepted as an alias.
> - `"windows"` - Windows. `"win"` is also accepted as an alias.
>
> ### OS/Architecture Combinations
>
> You can also restrict tools to specific OS and architecture combinations
> using the `os/arch` syntax:
>
> ```toml
> [tools]
> # Only install on macOS ARM64 and all Linux (skips macOS x86_64)
> hk = { version = "latest", os = ["linux", "macos/arm64"] }
>
> # Only install on Linux x86_64
> mytool = { version = "latest", os = ["linux/x64"] }
> ```
>
> Supported architecture identifiers:
> - `"arm64"` (or `"aarch64"`)
> - `"x64"` (or `"x86_64"` or `"amd64"`)
>
> When an entry contains `/`, both the OS and architecture must match. When
> an entry is just an OS name, it matches any architecture on that OS.
>
> If a tool specifies an `os` restriction and the current operating system is
> not in the list, mise will skip installing and using that tool."
> — `knowledge-base/sources/mise/docs/dev-tools/index.md`, "OS-Specific Tools"

This is a **native, declarative, per-tool `os`/`os-arch` gate**, expressible
as data in the same `[tools]` table entry — exactly the shape question 2
asked about. It also composes with other tool options in the same entry
(`os = [...], locked = false`, shown in the doc's own third example).

Separately, mise supports **whole-file** platform conditionality (not
per-tool, but worth citing since it's the same "declare platform
applicability as data" family):

> "Platform-specific environments like `mise.windows.toml` or
> `mise.macos-arm64.toml` can be enabled automatically with the `auto_env`
> setting."
> — `knowledge-base/sources/mise/docs/configuration.md:26`

**This repo's ACTUAL current baseline (self-read this session, per the
dispatch's A1):**

`.devcontainer/mise-system.toml` has **zero** per-tool `os`/`os-arch` usage.
Every entry in `[tools]` is a bare `"latest"` or `{ version = "latest",
postinstall = ... }` — no conditionality expressed in TOML at all. The one
place platform-specific behavior is handled today is:

1. **Removed, not branched** — the arch pin was deleted outright rather than
   conditioned:
   > "NO `arch` PIN (#698)... Each matrix leg builds inside a container of
   > its own architecture, so mise's native detection already IS the build
   > target; a literal can only disagree with it."
   > — `.devcontainer/mise-system.toml`, `[settings]` comment block
2. **A real per-tool platform asymmetry exists TODAY and is handled by
   accepting the asymmetry, not by conditioning it:**
   > "#698/D31: conda-forge gxx fills arm64's modern-GCC slot because kayari
   > gcc-latest is permanently x86_64-only. amd64 gains it too because mise
   > resolves conda packages natively with no arch pin."
   > — `.devcontainer/mise-system.toml:59` comment, directly above
     `"conda:gxx" = "latest"`

   This is the sharpest concrete case for question 2: `gxx` is meant to fill
   an **arm64-specific** gap (`kayari gcc-latest` is x64-only), but today it
   installs on **both** arches (self-described as an accepted side effect,
   not a deliberate choice), because nothing in the TOML restricts it. The
   native `os = ["linux/arm64"]` syntax above would express the ACTUAL intent
   ("gxx exists to backfill arm64") as one line of data, instead of the
   current state where it silently also runs on amd64 and that's noted as
   tolerated rather than intended.
3. **All architecture selection instead happens at the Docker/bake layer**
   (`docker-bake.hcl:106` `platforms = ["${PLATFORM}"]`, one job per arch in
   CI, #676) and via **Python branching**, not TOML: `platform_target.py`
   (referenced in the `mise-system.toml` `[settings]` comment: "must cover
   every arch in `platform_target.PUBLISHED_ARCHES`") holds the
   `PUBLISHED_ARCHES` list and any per-arch logic that governs lock
   generation, CI matrix legs, and drift checks
   (`find_lock_platform_drift`/`find_pinned_image_arch`).

**Verdict: real, low-risk, narrowly-scoped win — worth adopting for one
line.**

Unlike Q1, this doesn't require restructuring the build pipeline: `os`/`arch`
tool-entry keys are read by the *same* `mise install --system --locked -y`
invocation already in `Dockerfile:347/678` — no new build mechanism, no
experimental flag (this feature isn't flagged experimental in the docs,
unlike `oci`), no change to bake or the Dockerfile stages. It's additive TOML
syntax mise already evaluates during normal tool resolution ("mise will skip
installing and using that tool").

Concrete scope: the one identified fit is `"conda:gxx" = "latest"` →
`"conda:gxx" = { version = "latest", os = ["linux/arm64"] }` if the intent
really is "arm64-only GCC backfill" (per the #698/D31 comment). This is a
genuine *behavior change*, not a no-op — it would stop installing `gxx` on
amd64, which the current comment frames as an accepted-but-unintended
side effect. **This is a scope decision for the repo owner** (does amd64
gaining a modern GCC via conda hurt or help?), not something this review
resolves — but the *mechanism* to express either choice declaratively exists
and is unused today. Scanning the rest of `[tools]`: no other entry has a
documented or commented platform-specific intent (the LLVM/apt block is
`[bootstrap.packages]`, a different table not covered by this per-`[tools]`-
entry `os` field at all — need to check separately whether
`[bootstrap.packages]` entries support the same `os` key; **not found in the
docs read this session** — the "OS-Specific Tools" section documents `[tools]`
only, and `mise-oci.md`'s bootstrap-packages section documents `apt:`/`apk:`
base-image selection, not per-package OS conditionals within one apt run).
No other `[tools]` entry in this repo's `mise-system.toml` carries a comment
suggesting it's meant to be platform-restricted.

## Summary

| Question | Mise supports it? | Net win for THIS repo? |
|---|---|---|
| Q1: per-tool Docker layers | Yes, via experimental `mise oci build` (cited) — but apt/bootstrap packages stay one combined layer even under OCI, and it's a parallel/replacement build mechanism, not an addition to the existing Dockerfile+bake pipeline | **No** — complexity trade; the one clear beneficiary segment (`[tools]`, not `[bootstrap.packages]`) doesn't justify replacing/duplicating the multi-arch bake pipeline for an experimental subsystem |
| Q2: declarative per-tool OS/arch conditionality | Yes, native `os`/`os-arch` field on any `[tools]` entry (cited, non-experimental) | **Yes, narrowly** — zero pipeline changes required; one concrete candidate exists today (`conda:gxx`, #698/D31) where current behavior (installs on both arches) contradicts its own stated arm64-only intent; adopting it is a one-line, low-risk TOML change **once the repo owner confirms amd64 gxx should actually be dropped** |

## GitHub repos touched

- [jdx/mise](https://github.com/jdx/mise) — read `mise-oci.md`/`oci.md` (OCI
  per-tool layering, bootstrap-packages layer granularity, experimental
  status) and `configuration.md`/`dev-tools/index.md` (OS-specific tools
  syntax, platform-specific config files) via the offline knowledge-base
  mirror; no live fetch needed, offline corpus was sufficient for both
  questions.
