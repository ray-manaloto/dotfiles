# Research: CPU microarchitecture levels on GitHub-hosted runners

Status: COMPLETE (written incrementally as evidence arrived)
Started: 2026-08-30 · read-only research · facts only, no design recommendation.

Local raw copies of every fetched source live beside this file in `raw/`.

---

## Q2/Q5 — runner-images READMEs: fetch receipts

All four fetched via `curl` from `raw.githubusercontent.com/actions/runner-images/main/images/...`
(2026-08-30), HTTP 200 each:

| README | HTTP | bytes | Image Version stated |
|---|---|---|---|
| `images/ubuntu/Ubuntu2404-Readme.md` | 200 | 15740 | `20260823.283.1`, OS 24.04.4 LTS, kernel `6.17.0-1022-azure` |
| `images/ubuntu/Ubuntu2604-Arm64-Readme.md` | 200 | 8784 | `20260824.102.3`, OS 26.04 LTS, kernel `7.0.0-1012-azure` |
| `images/macos/macos-26-arm64-Readme.md` | 200 | 16207 | `20260728.0273.1`, macOS 26.5.2 (25F84), Darwin 25.5.0 |
| `images/macos/xcode-27-arm64-Readme.md` | 200 | 11258 | `20260810.0090.1`, macOS 26.5.2 (25F84), Darwin 25.5.0 |

### FINDING (Q2): none of the four READMEs states a CPU model or instruction set

Probe: `grep -niE 'cpu|processor|xeon|epyc|neoverse|ampere|graviton|cobalt|apple m[0-9]|architecture|instruction|avx|core count|ram|memory'` over each file → **0 matching lines in all four**.

**Control arm** (same grep shape, tokens known to be present in the same corpus):
`installed` → 3/3/4/4 hits, `image` → 4/4/4/4, `version` → 7/7/8/7 across the four
files. The probe discriminates, so the zero above is a real negative, not a blind
probe.

Consequence: the runner-images READMEs enumerate *installed software* only. They
do **not** publish the host CPU model, the vendor, the µarch generation, or any
ISA feature list. Anything about AVX2/AVX-512/Neoverse level from these files
would be inference, not citation.

### FINDING (Q5, control-armed): "docker" occurrence counts

Case-insensitive `grep -oi docker | wc -l` per file:

| README | "docker" occurrences |
|---|---|
| `Ubuntu2404-Readme.md` (x64) | **5** |
| `Ubuntu2604-Arm64-Readme.md` (arm64 Linux) | **5** |
| `macos-26-arm64-Readme.md` | **0** |
| `xcode-27-arm64-Readme.md` | **0** |

The two Ubuntu READMEs are the control arm: the same command shape over the same
corpus returns 5 on Linux images, so **0 on both macOS READMEs is a real
negative**, not a broken probe.

(Detail of the 5 Linux hits and the macOS container-adjacent sweep: below.)

---

## Q1 — what the platform spec actually defines

### OCI image-spec: the `variant` field and the Platform Variants table

`variant` is OPTIONAL and free-form; the spec only says implementations SHOULD
understand the listed values.

> **`variant`** *string* — This OPTIONAL property specifies the variant of the CPU.
> Image indexes SHOULD use, and implementations SHOULD understand, `variant`
> values listed in the [Platform Variants](#platform-variants) table.
>
> — `opencontainers/image-spec` `image-index.md:82-85`
> <https://github.com/opencontainers/image-spec/blob/main/image-index.md>

> When the variant of the CPU is not listed in the table, values are
> implementation-defined and SHOULD be submitted to this specification for
> standardization. These values SHOULD match (or be similar to) their analog
> listed in the Go Language document.
>
> | ISA/ABI    | `architecture` | `variant`             | Go analog   |
> |------------|----------------|-----------------------|-------------|
> | ARM 32-bit | `arm`          | `v6`, `v7`, `v8`      | `GOARM`     |
> | ARM 64-bit | `arm64`        | `v8`, `v8.1`, …       | `GOARM64`   |
> | POWER8+    | `ppc64le`      | `power8`, `power9`, … | `GOPPC64`   |
> | RISC-V     | `riscv64`      | `rva20u64`, …         | `GORISCV64` |
> | x86-64     | `amd64`        | `v1`, `v2`, `v3`, …   | `GOAMD64`   |
>
> — `image-index.md:105-116`

Same wording is repeated for the image *config* in
`opencontainers/image-spec` `config.md:126-129`.

Note what the spec does **not** do: it never enumerates the CPU *features* a
variant requires. It defers to the Go `GOAMD64`/`GOARM64` environment variables,
which in turn track the x86-64 psABI levels (see below). `v4` is not literally in
the table (it ends "`v1`, `v2`, `v3`, …"), and `v9` is not literally in the arm64
row either ("`v8`, `v8.1`, …").

### containerd `platforms` — what is enforced vs. erased

Source: `containerd/platforms` (the module Docker/BuildKit/containerd all use for
platform parsing and matching). <https://github.com/containerd/platforms>

**(a) `v8` on arm64 and `v1` on amd64 are ERASED during normalization** —
i.e. `linux/arm64/v8` ≡ `linux/arm64`, and `linux/amd64/v1` ≡ `linux/amd64`:

```go
case "x86_64", "x86-64", "amd64":
    arch = "amd64"
    if variant == "v1" {
        variant = ""
    }
case "aarch64", "arm64":
    arch = "arm64"
    switch variant {
    case "8", "v8", "v8.0":
        variant = ""
    case "9", "9.0", "v9.0":
        variant = "v9"
    }
```
— `containerd/platforms` `database.go:82-94`
<https://github.com/containerd/platforms/blob/main/database.go#L76-L111>

The package doc states this explicitly:

> Similarly, the most common arm64 version v8, and most common amd64 version v1
> are represented without the variant.
> While these normalizations are provided, their support on arm platforms has
> not yet been fully implemented and tested.
>
> — `platforms.go:105-109`

**So specifying `arm64/v8` is a NO-OP** — it normalizes away to the empty
variant. It is not wrong, it is simply erased. (`v9`/`v9.0` normalize to `v9`,
which is *not* erased.)

**(b) arm64 variant handling beyond v8 IS modeled, not cosmetic.** `compare.go`
carries a real version lattice and a documented downgrade-match order:

```go
var arm64variantToVersion = map[string]platformVersions{
    "v8": {[]int{8}, []int{0}}, "v8.0": …, "v8.1": … "v8.9": …,
    "v9": {[]int{9, 8}, []int{0, 5}}, "v9.0": …, … "v9.7": {[]int{9,8}, []int{7,9}},
}
```
— `compare.go:39-60` <https://github.com/containerd/platforms/blob/main/compare.go#L39-L60>

> // For arm64/v9.x, will also match arm64/v9.{0..x-1} and arm64/v8.{0..x+5}
> // For arm64/v8.x, will also match arm64/v8.{0..x-1}
> // For arm/v8, will also match arm/v7, arm/v6 and arm/v5
> // For amd64, will also match 386
>
> — `compare.go:145-150` (doc comment on `func Only`)

For amd64 the same file builds a descending vector: a request for `amd64/vN`
also matches `amd64/v{N-1}` … `amd64/v1` (`compare.go:67-85`). Note the direction:
a **higher requested** level matches **lower-level images**, never the reverse.

**(c) ⚠️ containerd never DETECTS an x86-64 microarch level from the host.**
`cpuVariant()` is guarded by `isArmArch`:

```go
func cpuVariant() string {
    cpuVariantOnce.Do(func() {
        if isArmArch(runtime.GOARCH) { … getCPUVariant() … }
    })
    return cpuVariantValue
}
```
— `cpuinfo.go:32-43` <https://github.com/containerd/platforms/blob/main/cpuinfo.go#L32-L43>

and `DefaultSpec()` fills `Variant` from exactly that call, with the comment
"The Variant field will be empty if arch != ARM" — `defaults_unix.go:28-35`
<https://github.com/containerd/platforms/blob/main/defaults_unix.go>

Also: on arm64, `getCPUVariant()` can only ever return `v3`–`v8` — the switch has
no `v9` and no `v8.x` arm — so a detected arm64 host is always `v8`, which
normalization then erases. `cpuinfo_linux.go:76-157`
<https://github.com/containerd/platforms/blob/main/cpuinfo_linux.go>

**Consequence (analysis of the cited code, flagged as such):** on an amd64 host
the default matcher is `Only({linux, amd64, ""})`, whose match test is exact
equality on the normalized variant (`platforms.go:190-194`). An image index whose
*only* amd64 entry is `linux/amd64/v2` therefore does **not** match a default
amd64 host — the vector for `""` is `[amd64, 386]` and never includes `v2`.
The compatibility direction is one-way: v3-requesting runtimes accept v1 images,
not the other way round. I have **not** yet found a Docker/BuildKit doc page
stating this in prose; treat the "does not match" conclusion as *derived from the
cited source*, and see the verification note added below if/when one is found.

### x86-64 microarchitecture levels — the actual feature sets

Authoritative source: the **x86-64 psABI**, `x86-64-ABI/low-level-sys-info.tex`,
table "Micro-Architecture Levels" (`\label{features}`).
<https://gitlab.com/x86-psABIs/x86-64-ABI/-/blob/master/x86-64-ABI/low-level-sys-info.tex>
(fetched raw, 105138 bytes; table at lines 14-57, prose at 59-109).

| Level | CPU features it adds (verbatim from the table) |
|---|---|
| **(baseline)** = `v1` | CMOV, CX8, FPU, FXSR, MMX, OSFXSR, SCE, SSE, SSE2 — `:21-30` |
| **x86-64-v2** | CMPXCHG16B, LAHF-SAHF, POPCNT, SSE3, SSE4_1, SSE4_2, SSSE3 — `:31-38` |
| **x86-64-v3** | AVX, **AVX2**, BMI1, BMI2, F16C, FMA, LZCNT, MOVBE, OSXSAVE — `:39-48` |
| **x86-64-v4** | AVX512F, AVX512BW, AVX512CD, AVX512DQ, AVX512VL — `:49-54` |

Note the table's own naming: the baseline row is literally labelled
`(baseline)`, and the named levels start at `x86-64-v2`. "v1" is the
OCI/Go spelling of that baseline.

> In addition to the x86-64 baseline architecture, several micro-architecture
> levels implemented by later CPU modules have been defined, starting at level
> `x86-64-v2`. These levels are intended to support loading of optimized
> implementations on those systems that are compatible with them. **The levels
> are cumulative in the sense that features from previous levels are implicitly
> included in later levels.**
>
> Levels `x86-64-v3` and `x86-64-v4` are only available if the corresponding
> features have been fully enabled. This means that the system must pass the full
> sequence of checks in the processor manual for these features, including
> verification of the XCR0 feature flags obtained using `xgetbv`.
>
> — `low-level-sys-info.tex:59-71`

> If this guideline is not followed, **loading the library will fail on systems
> that do not support the level for which the optimized shared object was
> built.**
>
> — `low-level-sys-info.tex:91-94`

So the levels are an ISA contract with a hard failure mode: run a `v3` binary on
a host lacking AVX2 and it faults (SIGILL) rather than degrading.

⚠️ **These are COMPILER/loader levels; a Docker platform variant string is not
one.** The psABI level is what `-march=x86-64-v3` and glibc's
`glibc-hwcaps/x86-64-v3` directory select (`:81-98`). The OCI `variant` field is
metadata for *manifest selection* (Q1 above) — nothing in the OCI spec or the
containerd source read here makes `--platform linux/amd64/v3` change a compiler
flag. That coupling, if wanted, is the image author's job.

### Q1 continued — what Docker/BuildKit actually does with the variant

BuildKit surfaces the variant only as a **build argument**:

> The following `ARG` variables are set automatically:
> - `TARGETPLATFORM` - platform of the build result. Eg `linux/amd64`, `linux/arm/v7`, `windows/amd64`.
> - `TARGETOS` … `TARGETARCH` … **`TARGETVARIANT` - variant component of TARGETPLATFORM**
> - `BUILDPLATFORM` … `BUILDVARIANT` - variant component of BUILDPLATFORM
>
> — `moby/buildkit` `frontend/dockerfile/docs/reference.md:2723-2732`
> <https://github.com/moby/buildkit/blob/master/frontend/dockerfile/docs/reference.md>
> (same list at `docker/docs` `content/manuals/build/building/variables.md:243-256`,
> <https://github.com/docker/docs/blob/main/content/manuals/build/building/variables.md>)

Neither page says the variant changes compiler flags, base-image selection
semantics, or codegen. It is a string handed to the Dockerfile plus a field
written into the output manifest.

**UNVERIFIED / not found:** no Docker or BuildKit *documentation* page was found
stating what happens when a runtime whose default variant is empty pulls an image
whose only amd64 entry carries `v2`/`v3`. The "does not match" conclusion in (c)
above is derived from `containerd/platforms` source, not from prose docs. If that
behaviour is load-bearing for the decision, the settling probe is a real one:
push a two-entry vs. `v2`-only index and `docker pull` it on a plain amd64 host.

### Summary answer to "is arm64 variant handling meaningfully enforced?"

Split it in two, because the honest answer differs by value:

- **`arm64/v8` specifically: cosmetic.** It is erased to the empty variant by
  `normalizeArch` (`database.go:87-94`), so `linux/arm64/v8` and `linux/arm64`
  are the same platform after normalization. Docker's own docs and the OCI table
  still list `v8`, and BuildKit will still hand it to you in `TARGETVARIANT`, but
  matching cannot distinguish them.
- **`arm64/v8.x` and `arm64/v9.x`: modelled and enforced.** `compare.go` carries
  an explicit version lattice and asymmetric downgrade matching
  (`compare.go:39-60`, `:98-136`, doc at `:145-150`). These are *not* erased.
- **Host detection is the weak link on both arches.** containerd's arm64 detector
  can only ever return `v3`–`v8` (`cpuinfo_linux.go:140-155`) and its amd64
  detector does not exist at all (`cpuinfo.go:32-43`). So a host will never
  *advertise* a level above the erased baseline by itself.

---

## Q5 — macOS runners and container runtimes

Beyond the "docker" counts above, a wider container-runtime sweep over all four
READMEs (`colima|podman|lima|qemu|virtualbox|parallels|container|buildx|buildkit|nerdctl|runc|skopeo|virtualization|hypervisor`, case-insensitive):

| README | hits |
|---|---|
| `macos-26-arm64-Readme.md` | **0** |
| `xcode-27-arm64-Readme.md` | **0** |
| `Ubuntu2404-Readme.md` | 3 — `Docker-Buildx 0.36.1` (L74), `Podman 5.8.4` (L95), `Skopeo 1.13.3` (L97) |
| `Ubuntu2604-Arm64-Readme.md` | 3 — `Docker-Buildx 0.36.1` (L68), `Podman 5.7.0` (L83), `Skopeo 1.21.0-dev` (L84) |

Control arm: the identical command over the Ubuntu files returns hits, so the
macOS zeros are real negatives.

Full docker lines on the Linux images:

- `Ubuntu2404-Readme.md:72-76` — Docker Amazon ECR Credential Helper 0.12.0,
  Docker Compose 2.38.2, Docker-Buildx 0.36.1, **Docker Client 28.0.4**,
  **Docker Server 28.0.4**
- `Ubuntu2604-Arm64-Readme.md:66-70` — Docker Amazon ECR Credential Helper 0.12.0,
  Docker Compose 5.1.3, Docker-Buildx 0.36.1, **Docker Client 29.4.2**,
  **Docker Server 29.4.2**

**Verdict on the prior session's claim** ("macOS GitHub runners ship no container
runtime and cannot build Linux images"): the *first half* is **CONFIRMED as far as
these two READMEs go** — neither macOS README lists Docker, Podman, Colima, Lima,
QEMU, or any other container/VM runtime, while both Ubuntu READMEs list a Docker
client *and server*. The *second half* ("cannot build Linux images") is a
**stronger claim these READMEs do not settle** — absence from the pre-installed
software list is not the same as "cannot be installed in a job". Label it
UNVERIFIED unless a GitHub docs statement is found.

---

## Q4 — does `ubuntu-latest` resolve to 24.04 or 26.04?

**24.04.** GitHub's own docs source, `github/docs`
`data/reusables/actions/supported-github-runners.md` (included into
`content/actions/reference/runners/github-hosted-runners.md` at line 42 as
`{% data reusables.actions.supported-github-runners %}`):

```html
<td>Linux</td><td>4</td><td>16 GB</td><td>14 GB</td><td> x64 </td>
<td>
  <code><a href=".../images/ubuntu/Ubuntu2404-Readme.md">ubuntu-latest</a></code>,
  <code><a href=".../images/ubuntu/Ubuntu2404-Readme.md">ubuntu-24.04</a></code>,
  <code><a href=".../images/ubuntu/Ubuntu2204-Readme.md">ubuntu-22.04</a></code>,
  <code><a href=".../images/ubuntu/Ubuntu2604-Readme.md">ubuntu-26.04</a></code> ({% data variables.release-phases.public_preview_caps %})
</td>
```
— `supported-github-runners.md:18-30` (public repos) and `:113-125` (private repos)
<https://github.com/github/docs/blob/main/data/reusables/actions/supported-github-runners.md>
rendered at <https://docs.github.com/en/actions/reference/runners/github-hosted-runners>

Both `ubuntu-latest` and `ubuntu-24.04` point at the **same** README
(`Ubuntu2404-Readme.md`). `ubuntu-26.04` and `ubuntu-26.04-arm` are marked
**Public preview**. There is no `ubuntu-latest-arm`; the arm64 row lists only
`ubuntu-24.04-arm`, `ubuntu-22.04-arm`, `ubuntu-26.04-arm` (preview) —
`supported-github-runners.md:44-55`.

The same page carries the standing caveat:

> The `-latest` runner images are the latest stable images that GitHub provides,
> and might not be the most recent version of the operating system available
> from the operating system vendor.
>
> — `github-hosted-runners.md:35`

**Migration date:** the runner-images READMEs carry an announcement banner
linking <https://github.com/actions/runner-images/issues/14226> ("[Ubuntu] Ubuntu
26.04 and Ubuntu 26.04 Arm is now available as a public preview"). No
`ubuntu-latest` cut-over date is stated in the docs table or the README banners
read here — see the issue check below.

### What the docs table does and does NOT say about hardware

The table's **"Processor (CPU)"** column holds a **vCPU count**, not a model:
`4` for public-repo Linux x64/arm64, `2` for private-repo Linux, `3 (M1)` for
arm64 macOS, `4` for Intel macOS. The **"Architecture"** column holds only
`x64` / `arm64` / `Intel`. Neither column names a CPU model, generation, or
instruction-set level. (`supported-github-runners.md:8-13`, rows at `:18-91`.)

So: **no GitHub-published source read here states the host CPU model or its
supported ISA level for any Linux runner.**

---

## Q5 supplement — GitHub's own statement on macOS virtualization

`github/docs` `data/reusables/actions/macos-runner-limitations.md` (included at
`github-hosted-runners.md:48`, "Limitations for arm64 macOS runners"):

> * Nested-virtualization is not supported due to the limitation of Apple's
>   Virtualization Framework.
>
> — <https://github.com/github/docs/blob/main/data/reusables/actions/macos-runner-limitations.md>

This is the mechanism behind the README absence: a Linux container runtime on
macOS (Docker Desktop, Colima, Lima, Podman machine) needs a Linux VM, and the
arm64 macOS runner is itself a VM, so that VM would be nested. The docs statement
is scoped to **arm64** macOS runners; it says nothing about `macos-*-intel`.

---

(remaining sections in progress)

---

## Q3 — highest microarch level each runner can *safely* target

### The READMEs do not settle it. At all.

Six runner-images READMEs were fetched and probed with the same CPU-token grep
(`cpu|processor|xeon|epyc|neoverse|ampere|avx|architecture`, case-insensitive):

| README | matching lines | control (`version`) | docker occurrences |
|---|---|---|---|
| `Ubuntu2404-Readme.md` (`ubuntu-latest`, `ubuntu-24.04`) | **0** | 8 | 5 |
| `Ubuntu2604-Readme.md` (`ubuntu-26.04`) | **0** | 8 | 5 |
| `Ubuntu2404-Arm64-Readme.md` (`ubuntu-24.04-arm`) | **0** | 7 | 5 |
| `Ubuntu2604-Arm64-Readme.md` (`ubuntu-26.04-arm`) | **0** | 7 | 5 |
| `macos-26-arm64-Readme.md` | **0** | 7 | 0 |
| `xcode-27-arm64-Readme.md` | **0** | 7 | 0 |

Control arm present in every row (`version` hits, and `docker` hits on the four
Linux images), so every zero is a real negative.

GitHub's docs table is no better: its "Processor (CPU)" column is a vCPU **count**
and its "Architecture" column is `x64` / `arm64` / `Intel`
(`supported-github-runners.md:8-13, 18-91`).

**Therefore: no cited source answers "highest safe level" for any of
`ubuntu-latest`, `ubuntu-24.04`, `ubuntu-26.04`, `ubuntu-24.04-arm`,
`ubuntu-26.04-arm`.** Any number stated here for those labels would be inference,
and the brief forbids that.

### What WOULD settle it (per runner, empirically)

Run these in a job on each label. Each is a real probe with an unambiguous
answer, and the third is the one that answers the *level* question directly:

1. `cat /proc/cpuinfo` → `model name` and the full `flags` list. Presence of
   `avx2` + `bmi2` + `fma` + `f16c` + `movbe` + `lzcnt` + `xsave` ⇒ v3-capable;
   `avx512f avx512bw avx512cd avx512dq avx512vl` ⇒ v4-capable. (Feature lists per
   the psABI table above.) On arm64 the analogous field is `Features` /
   `CPU architecture` — which is exactly the field containerd parses
   (`cpuinfo_linux.go:112-138`).
2. `ld.so --list-diagnostics` (glibc ≥ 2.33) or `ld.so --help`, whose tail prints
   the glibc-hwcaps subdirectories the running CPU qualifies for:

   > The dynamic linker loads optimized implementations of shared objects from
   > subdirectories under the `glibc-hwcaps` directory … Initially supported
   > subdirectories include … **"x86-64-v2", "x86-64-v3", "x86-64-v4" for
   > x86_64-linux-gnu**. In the x86_64-linux-gnu case, the subdirectory names
   > correspond to the vendor-independent x86-64 microarchitecture levels defined
   > in the x86-64 psABI supplement.
   >
   > — glibc 2.33 `NEWS`, "Major new features" (`:87-95`)
   > <https://sourceware.org/git/?p=glibc.git;a=blob_plain;f=NEWS;hb=refs/heads/release/2.33/master>

   Ubuntu 24.04 ships glibc 2.39 and 26.04 later still, so this is available on
   both. (UNVERIFIED: exact glibc version per image — the READMEs do not list it;
   the probe itself would report it.)
3. `gcc -march=native -Q --help=target | grep -E '^\s+-march='` → the exact
   `-march` GCC picks for that host, which is the compiler's own verdict.

Run it across **many** jobs, not one — see the heterogeneity evidence next.

### Durability risk: the hardware is explicitly not guaranteed

This is the part a source *does* address, and it addresses it against you.

**(a) GitHub maintainer, on AVX-512 (i.e. exactly `v4`):**

> Unfortunately, at this time our agents are not guaranteed to have AVX-512, and
> only the way to enable the feature for you on permanent basis is to use
> self-hosted agents (where it is possible to control the underlying hardware).
>
> — Darleev (maintainer), 2021-05-17, `actions/runner-images` issue #3389
> <https://github.com/actions/runner-images/issues/3389> (CLOSED)
> ⚠️ Dated 2021. Treat as the stated *policy* posture, not a current hardware
> inventory.

**(b) Measured heterogeneity WITHIN one label, 2026:** `ubuntu-24.04` jobs
occasionally land on a machine advertising **AVX10.1**, which most do not:

> I'm not setting any AVX specific flags in these builds; only `-march=native`.
> But I'm getting `error: invalid feature combination: +avx10.1-256; will be
> promoted to avx10.1-512`. This failure has occurred infrequently (maybe ~5
> times total) in the past months so it's probably due to the specific machine
> that a runner is assigned to.
>
> — `actions/runner-images` issue #14296, opened 2026-06-27, still OPEN
> <https://github.com/actions/runner-images/issues/14296>
> (image `ubuntu-24.04` version `20260622.220.1`)

⚠️ **Provenance:** (b) is a *user report* filed in the official repo, not a
GitHub statement. Its "~5 times in the past months" is the reporter's own count,
not a measurement I reproduced — **inherited number, unverified.** What it does
establish, and what a single-job `/proc/cpuinfo` probe cannot, is that one label
maps to **more than one CPU model**, so a probe run once is a sample of size one.

**(c) The `-latest` labels are explicitly a moving target:**

> The `-latest` runner images are the latest stable images that GitHub provides,
> and might not be the most recent version of the operating system available from
> the operating system vendor.
>
> — `github-hosted-runners.md:35`

That statement is about the OS, not the CPU; **no source found states any SLA,
notice period, or guarantee about the runner CPU generation.** The absence is the
finding: pinning a level above the guaranteed floor is uninsured by any published
commitment.

**(d) Quantification:** no source read here quantifies the risk (no percentage of
fleet at a given level, no rollout schedule, no deprecation notice for a CPU
generation). The only quantitative datum found is the unverified "~5 times" in
(b). If a number is needed, it has to be measured, not cited.

### `ubuntu-latest` → 26.04 migration date

Not announced, as far as this search reaches. `gh search issues --repo
actions/runner-images "ubuntu-latest"` (20 results) returned no migration
announcement; the 26.04 announcement (#14226, opened 2026-06-11, still OPEN) says
only:

> The image is marked as "preview" for now. It means some software can be
> unstable on the new platform. Also, there could be queueing issues as the
> capacity will be balanced only throughout the next weeks.

**Control arm for the negative:** the same search *did* return the two
announcement issues that exist — #14226 (26.04 preview) and #14254 ("[Ubuntu] The
Ubuntu 22 based runner images will begin deprecation on September 17th and will
be fully unsupported by April 17th"). So the search finds announcement issues
when they exist; the absence of a `ubuntu-latest` cut-over announcement is a real
negative for this query, bounded by: GitHub's changelog blog was not searched.

### Extra fact worth knowing for a build matrix

`ubuntu-slim` is **not a VM** and cannot run Docker-in-Docker:

> `ubuntu-slim` runners execute Actions workflows in Ubuntu Linux, **inside a
> container rather than a full VM instance** … Each container provides hypervisor
> level 2 isolation.
>
> The container for `ubuntu-slim` runners runs in unprivileged mode. This means
> that some operations requiring elevated privileges—such as mounting file
> systems, **using Docker-in-Docker**, or accessing low-level kernel features—are
> not supported.
>
> — `github-hosted-runners.md:54, 57`

---

## Summary table (what is cited vs. what is not)

| Question | Answer | Status |
|---|---|---|
| x86-64 level feature sets | v1 baseline / v2 SSE3-4.2+POPCNT+CX16 / v3 AVX+AVX2+BMI1/2+FMA+F16C+LZCNT+MOVBE / v4 AVX-512{F,BW,CD,DQ,VL} | CITED (psABI) |
| Levels cumulative, hard failure if unsupported | yes | CITED (psABI `:59-71`, `:91-94`) |
| OCI-recognised variants | `amd64`: `v1,v2,v3,…`; `arm64`: `v8, v8.1, …`; `arm`: `v6,v7,v8` | CITED (image-index.md:110-116) |
| `arm64/v8` meaningful? | **No — normalized away to empty** | CITED (database.go:87-94) |
| `arm64/v8.x`, `v9.x` meaningful? | **Yes — real version lattice + downgrade matching** | CITED (compare.go:39-60,145-150) |
| amd64 `v1` meaningful? | No — normalized away | CITED (database.go:82-86) |
| amd64 `v2/v3/v4` meaningful? | Preserved; `Only(vN)` matches vN..v1, not the reverse | CITED (compare.go:67-85,150) |
| Host µarch auto-detection on amd64 | **None — containerd never detects it** | CITED (cpuinfo.go:32-43, defaults_unix.go:28-35) |
| `v2`-only index vs. plain-amd64 host | would not match | DERIVED from cited source; no doc prose found |
| Does `/vN` change the build? | Only exposed as `TARGETVARIANT` ARG | CITED (buildkit reference.md:2723-2732) |
| Runner CPU model, any Linux label | **not stated in any README or GitHub doc read** | CITED NEGATIVE (control-armed) |
| Highest safe level per label | **unresolved by any source; must be measured** | NOT SETTLED |
| `ubuntu-latest` → | 24.04 | CITED (supported-github-runners.md:25-26) |
| `ubuntu-26.04` / `-arm` status | Public preview | CITED (same file :28, :53) |
| `ubuntu-latest` migration date | none announced | CITED NEGATIVE (control-armed search) |
| AVX-512 guaranteed on runners? | **explicitly not guaranteed** | CITED (issue #3389, 2021) |
| One label = one CPU model? | no — AVX10.1 machines appear occasionally | USER REPORT (issue #14296), count unverified |
| macOS runners ship a container runtime? | **no** — 0 hits for docker/podman/colima/lima/qemu/buildx/skopeo | CITED NEGATIVE (control-armed vs. Ubuntu READMEs) |
| macOS runners *cannot* build Linux images? | mechanism cited (no nested virtualization, arm64 macOS), but "cannot" not stated by any source | PARTLY VERIFIED |
| `ubuntu-slim` docker-in-docker | not supported | CITED (`github-hosted-runners.md:57`) |

---

## Probe hygiene notes (so a later reader can re-run these)

- Every README/spec/source was fetched with `curl` and saved under `raw/` next to
  this file; every grep quoted above was run against those local copies, so the
  line numbers cited are reproducible.
- Every negative result in this report is paired with a control arm run with the
  same command shape over the same corpus. The two that matter most:
  the macOS "no container runtime" zero (control: Ubuntu READMEs → 5 docker hits,
  3 container-tool hits) and the "no CPU model stated" zero (control:
  `version` → 7-8 hits in every file).
- Not probed, and therefore not claimed: GitHub's changelog blog, Azure VM SKU
  documentation, larger/hosted-runner hardware pages, `macos-*-intel` READMEs,
  and any live `/proc/cpuinfo` from an actual runner job.

---

## GitHub repos touched

- [actions/runner-images](https://github.com/actions/runner-images) — the six
  runner READMEs (Ubuntu 24.04/26.04 x64+arm64, macOS 26 arm64, Xcode 27 arm64)
  and issues #3389, #14226, #14254, #14296.
- [github/docs](https://github.com/github/docs) — `github-hosted-runners.md`,
  `data/reusables/actions/supported-github-runners.md`,
  `data/reusables/actions/macos-runner-limitations.md` (the source of
  docs.github.com's runner spec page).
- [opencontainers/image-spec](https://github.com/opencontainers/image-spec) —
  `image-index.md` Platform Variants table, `config.md` variant field.
- [containerd/platforms](https://github.com/containerd/platforms) — `database.go`,
  `platforms.go`, `compare.go`, `cpuinfo.go`, `cpuinfo_linux.go`,
  `defaults_unix.go`; the normalization/matching behaviour Docker and BuildKit
  inherit.
- [moby/buildkit](https://github.com/moby/buildkit) —
  `frontend/dockerfile/docs/reference.md` for `TARGETVARIANT`.
- [docker/docs](https://github.com/docker/docs) —
  `content/manuals/build/building/variables.md` (same build-arg list).
- [golang/go](https://github.com/golang/go) — `doc/godebug.md` fetched while
  chasing the `GOAMD64` analog; **not cited in the end** (no level table there).

Non-GitHub sources consulted:

- [gitlab.com/x86-psABIs/x86-64-ABI](https://gitlab.com/x86-psABIs/x86-64-ABI) —
  `x86-64-ABI/low-level-sys-info.tex`, the Micro-Architecture Levels table.
- [sourceware.org glibc](https://sourceware.org/git/?p=glibc.git) — 2.33 `NEWS`,
  glibc-hwcaps subdirectory list.
