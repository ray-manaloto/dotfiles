# Requirements — devcontainer gcc 16.2 + multi-arch + build optimisation

**Captured VERBATIM 2026-08-08, session dotfiles-20260808.02, at Ray's explicit
instruction: _"dont lose all of my requirements so we dont forget them in the
implementation"_.**

**This file is the SOURCE OF TRUTH FOR SCOPE.** Promoted from the session's
working notes (`.agent/`) to `docs/specs/` on Ray's instruction, because
`.agent/` is swept by `git clean -xdf` and absent from a fresh clone — and R4
hands this to a **`/goal` session** that must be able to read it anywhere.

**Read this before implementing anything.** It carries Ray's requirements
**verbatim** (four messages), the derived ledger R1–R20, and decisions D1–D33
with their evidence.

Two conventions that make it useful rather than merely long:

- **Do NOT paraphrase or "tidy" the verbatim blocks** — annotate below them.
  Ray's wording is the requirement; my summary of it is not.
- **Corrections are kept as corrections, not silently rewritten.** Several
  claims here were overturned mid-session — by Ray, by measurement, or by
  research. Each is marked ⚠️ with what was believed and what replaced it, so a
  later reader can tell a *contested* conclusion from an uncontested one and
  need not re-derive the argument.

**Companion evidence:** `docs/research/runs/research-20260808-devcontainer-lifecycle-spec/report.md`
(committed `09a2e9a`) — the devcontainer lifecycle/schema/CLI research this
ledger cites throughout.

---

## VERBATIM — Ray, 2026-08-08

> /grilling
> we need to update the devcontainer to support the following:
> 1. add gcc 16.2 to the image
>    - it should work like the p2996 compiler build where its cache and its binaries are stored as ghcr packages or a tar/zipped file so we dont have to keep rebuilding it
>    - the 16.2 version should be a docker bake/dockerfile/github environment variable so we can keep updating it as new releases are released and we dont have to pay for its expensive build all the time
>    - and verify there are only 3 gcc compilers on the final docker image
>      1. latest available from the ubuntu version the docker image is on
>         - we eventually need to remove this and other binaries that are duplicates to reduce docker image size
>      2. the 16.2 version
>      3. the gcc latest build we have already
> 2. update the permutations we are building to include both amd64 and arm64 so we can run the devcontainer natively on this mac vs rosetta virtualization
> 3. review latest mise features that could help optimize this build
>    - offline repo is here: /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise
>      - bootstrap
>        - /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/bootstrap
>        - /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/bootstrap
>      - oci
>        - /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/dev-tools/mise-oci.md
>        - /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/cli/oci.md
>      - can we use homebrew's integration in addition to conda
>        - right now i see conda has gcc 16.1 only (gcc 16.2 was released)
>          - we can try conda's 16.1 to get it to the docker image as the first step and then once that's stable the next phase would be to try to build it via ci/cd to get the latest 16.2 version
>            - https://anaconda.org/channels/conda-forge/packages/gcc/overview
>            - but worth researching when homebrew or conda will support 16.2
>          - /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/bootstrap/packages/brew.md
>          - /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/mise/docs/dev-tools/backends/conda.md
>    - going forward use the offline repo to research mise instead first of online websearch
> 4. run this as a /goal on a new session
>    - /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/goal.md
> 5. the docker image size is very large and i think we can get it to be smaller but we have not optimized it so we need to get more diagnostics and metrics to help find places to optimize and shrink the size
>    - but we can make that a subsequent task once we get the docker image working and we've validated the ship and land steps are working properly and ssh works properly
>
> feel free to research the offline docs to do more research and use use skills:
> - /research
> - /deep-research
>   - /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/workflows.md
>
> we should utilize these skills (note some might be user triggered) in the process to make sure there are not bugs:
> - /mattpocock-skills:code-review
> - /code-review:code-review
>
> once you have completed and fully tested i will then run /verify
> - /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/commands.md
>
> dont lose all of my requirements so we dont forget them in the implementation

---

## VERBATIM — Ray, 2026-08-08, SECOND message (reusability + lifecycle + docker ban)

> these devcontainers should be re-usable across other projects/repos
> another github repo should be to just pull these docker images and startup these devcontainers with a .devcontainer/ subdirectory in their repo/projects
> - we still need to enforce that there are zero bash scripts
> - so we might need to break up the python library to its own library which just gets imported into this project
> - the devcontainer focused python library will be used throughout all the devcontainer lifecycle methods
>   - https://containers.dev/implementors/json_reference/#lifecycle-scripts
>   - https://oneuptime.com/blog/post/2026-01-25-dev-containers-team-development/view#lifecycle-scripts
>   - https://containers.dev/implementors/spec/#lifecycle
>   - https://tenthirtyam.org/dispatches/2026/07/01/development-containers-consistent-environments-for-every-contributor/#lifecycle-hooks
>   - https://blog.projectasuras.com/DevContainers/3
>   - https://fabiorehm.com/blog/2025/11/11/devpod-ssh-devcontainers/
>   - https://docs.docker.com/compose/how-tos/lifecycle/
> make sure to also not lose this note and the sources i provided
>
> create a markdown document explaining all the lifecycle hooks and fully understand them instead of guessing what they do
> and bringing up a devcontainer should only use the devcontainer cli
> - NEVER run the docker command
>   - this needs to be enforced via progressive disclosure CLAUDE.md markdown at all the files and directories involving the devcontainer
>   - and maybe via claude rules and hooks
>     - /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/memory.md
>     - /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code/hooks.md

---

## VERBATIM — Ray, 2026-08-08, THIRD message (SDK / async / structured logging)

> D1 is wrong
> - thought we were going to have both a :dev-amd64 and :dev-arm64 tag also in addition to the manifest
>
> D10 - i dont understand, why are you calling docker cli
>
>  and all the python code should be using a modern asynchronous library that supports structured logging of different formats via sinks
>   - there should be no direct stdout/stderror calls and only via the logging library
>     - if it output needs to be in stdout/stderr it should be its own dedicated sink
>     - we should enforce this via hk/ruff/graphify's tree-sitter/ty lsp to block stdout/stderror from ever writing out
>
>   the python library should be treated as an sdk with proper error codes via enums
>
>   i think we've also drifted away from only having models and code generated from https://github.com/koxudaxi/datamodel-code-generator
>   with modern efficient message formats that the loggign library can offload to the the logging thread
>
>   the logging library can be a rust/c++ library if it is more efficient if it provides python bindings
>
> and our verification process needs to review the logs for warnings/errors that might be silently skipped
> - can be found faster via structured logging
>
> we need to support different ssh ports if the devcontainer is started from another repo/directory

---

## Derived requirement ledger — every item gets an ID and a disposition

Nothing may be dropped silently. If an item is deferred, it says so, with who
decided and when.

| ID | Requirement | Phase | Status |
|---|---|---|---|
| **R1.1** | Add **gcc 16.2** to the devcontainer image | 1 | OPEN |
| **R1.2** | Cache it like the **p2996 compiler build** — binaries/cache stored as **ghcr packages or a tar/zip**, so it is not rebuilt every time | 1 | OPEN |
| **R1.3** | The **16.2 version string is a variable** (docker bake / Dockerfile ARG / GitHub env) so new releases are a version bump, not a re-architecture | 1 | OPEN |
| **R1.4** | **Verify exactly 3 gcc compilers** on the final image: (a) ubuntu-latest-for-the-base, (b) 16.2, (c) the gcc-latest build we already have | 1 | OPEN — **now RESOLVED to concrete artifacts**, below |
| **R1.5** | *Eventually* remove the ubuntu one + other duplicate binaries to shrink the image | later | DEFERRED by Ray ("eventually") |
| **R2** | Build **both amd64 AND arm64** so the devcontainer runs **natively on this Mac**, not under Rosetta | 1 | OPEN — see R2.1 |
| **R2.1** | ⭐ **CLARIFIED by Ray 2026-08-08:** *"we might need to test amd64 functionality locally so we will need to run both amd64 and arm64 locally and ci/cd on both also"* ⇒ **both arches must be runnable LOCALLY and both must be built in CI/CD.** This is NOT "native only" and NOT "amd64 only" — it is **both, everywhere**. arm64 native for speed; amd64 (Rosetta locally) retained for testing amd64 functionality. | 1 | OPEN |
| **R3.1** | Review **latest mise features** that could optimise this build — `bootstrap`, `oci` | 1 | OPEN |
| **R3.2** | Evaluate **homebrew backend in addition to conda** | 1 | OPEN |
| **R3.3** | **Phase A:** conda's gcc **16.1** into the image first (it is what conda has today); **Phase B:** CI/CD build for **16.2** once 16.1 is stable | 1→2 | OPEN |
| **R3.4** | Research **when homebrew/conda will support 16.2** | 1 | OPEN |
| **R3.5** | ⭐ **STANDING PROCESS RULE:** research mise via the **offline repo FIRST**, before any web search | standing | ADOPTED |
| **R4** | Run the implementation as a **`/goal` on a NEW session** | handoff | OPEN |
| **R5** | Image is **very large**; gather **diagnostics + metrics** to find shrink targets | **subsequent** | DEFERRED by Ray — explicitly gated behind "docker image working + ship/land validated + ssh working" |
| **P1** | Use `/research` and `/deep-research` for the research legwork | process | OPEN |
| **P2** | Use `/mattpocock-skills:code-review` **and** `/code-review:code-review` to catch bugs | process | OPEN |
| **P3** | **Ray runs `/verify`** once implementation is complete and fully tested | final gate | RAY-OWNED |
| **R6** | ⭐ **Devcontainers must be REUSABLE ACROSS OTHER PROJECTS/REPOS.** Another GitHub repo should just **pull these docker images** and start the devcontainer with its own `.devcontainer/` subdirectory. | **architecture** | OPEN — reframes everything |
| **R7** | **Zero bash scripts** still enforced (existing [[zero-bash-logic]]) — and it must hold in the *consuming* repos too, not just here | standing | OPEN |
| **R8** | **Split the python library into its own standalone library**, imported into this project. A **devcontainer-focused** library used throughout **all devcontainer lifecycle methods**. | **architecture** | OPEN |
| **R9** | **Write a markdown document explaining ALL the lifecycle hooks** — *"fully understand them instead of guessing what they do"* | 1 (do early) | OPEN |
| **R10** | **Bringing up a devcontainer uses ONLY the devcontainer CLI. NEVER the `docker` command.** | standing | OPEN — partially exists |
| **R10.1** | Enforce R10 via **progressive-disclosure `CLAUDE.md`** at *all* files and directories involving the devcontainer | standing | OPEN |
| **R10.2** | Enforce R10 *"maybe"* via **Claude rules and hooks** (`memory.md`, `hooks.md`) | standing | OPEN — Ray said "maybe" |
| **R13** | All python uses a **modern ASYNCHRONOUS** library | **architecture** | OPEN |
| **R14** | **Structured logging**, multiple formats, via **SINKS** | **architecture** | OPEN |
| **R14.1** | **NO direct stdout/stderr calls anywhere** — only through the logging library | **architecture** | OPEN |
| **R14.2** | Output that must reach stdout/stderr gets its **own dedicated SINK** | **architecture** | OPEN |
| **R14.3** | **Machine-enforce** the stdout/stderr ban via **hk / ruff / graphify tree-sitter / ty LSP** | gate | OPEN |
| **R14.4** | **Efficient message format** the logging library can **offload to the logging thread** | perf | OPEN |
| **R14.5** | The logging library **may be Rust/C++** with python bindings if more efficient | perf | OPEN |
| **R15** | The python library is an **SDK**, with **proper error codes via ENUMS** | **architecture** | OPEN |
| **R16** | ⚠️ **We DRIFTED** — models must be **code-generated** from [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator), *only* generated | **architecture** | OPEN — drift called out by Ray |
| **R17** | **Verification must review logs** for warnings/errors that might be silently skipped — *"can be found faster via structured logging"* | gate | OPEN — extends R12 |
| **R18** | **Support different SSH ports** when the devcontainer is started **from another repo/directory** | 1 | OPEN — interacts with D4 + D16 |

### R3.5 is a standing rule, not a task

*"going forward use the offline repo to research mise instead first of online
websearch"* — this outlives this project. It belongs in
`.claude/rules/research-doc-sources.md` as a mise-specific step alongside the
existing step 00 (agent-harness-docs). **File it there so it survives.**

## DECISIONS — Ray-owned, recorded as they land (grilling 2026-08-08)

### Established facts (looked up, not assumed)

| Fact | Evidence | Consequence |
|---|---|---|
| **The cache is ALREADY arch-keyed** | `PLATFORM` feeds *both* content hashes — `P2996-CACHE.md:51` (base) and `:73` (p2996) | Dual-arch forks `:p2996-<hash16>` into two cache images **automatically**. **R1.2 needs NO hash redesign.** |
| `platforms` is **singular** | `docker-bake.hcl:96` — `platforms = ["${PLATFORM}"]`, in `_common`, inherited by all targets | The single choke point for multi-arch. |
| ~~`verify-arch` asserts **literal `x86_64`**~~ ✅ **RESOLVED by #673** (PR #694, merged 2026-08-09) | It now derives both expected values from `dotfiles-setup platform`; measured in-container: `OK: R3 container is linux/amd64/v2 x86_64 on all three signals` | The invariant was redefined as "the container is the architecture we ASKED for", not "the container is amd64". |
| ⚠️ **CORRECTED** — there IS a deliberate gcc | `Dockerfile:477-494` — **GCC-17 with P2996 reflection**, precompiled `.deb` from kayari.org/jwakely trunk, installed to **`/opt/gcc-latest/bin`**, pinned as `ARG GCC_LATEST_DEB=gcc-latest_17.0.0-20260719git6d5d980f76c3.deb` | **My earlier "no deliberate gcc" claim was FALSE** — I had grepped only `mise-system.toml`, not the `Dockerfile`. This IS Ray's "the gcc latest build we have already". |
| ⭐ **R1.3's pattern already exists in-repo** | Same block: Renovate bumps it via the `custom.gcc-latest` HTML datasource; a `gcc-sha-repair` workflow (#249) recomputes the sha; `dotfiles-setup gcc-sha [--check]` | **R1.3 has TWO proven precedents**, not one: the p2996 content-hash cache AND this pinned-filename `.deb`. Prefer the cheaper one that fits. |
| LLVM/clang is a separate deliberate tier | `mise-system.toml:115-134` — moved OUT of conda to apt (#222 PR-C), clang-22, exact-pinned | Not a gcc; do not conflate when counting. |
| p2996 clang is a **third** compiler family | `Dockerfile:444` — `/opt/clang-p2996/bin/clang++` | Also not a gcc. |

### D1 — Tag strategy: **BOTH manifest list + per-arch tags** ✅

```
ghcr.io/…:dev         ← manifest list (native by default)
ghcr.io/…:dev-amd64   → sha256:aaa…
ghcr.io/…:dev-arm64   → sha256:bbb…

mise run up            → :dev        (native arm64, no Rosetta)
CI / identity check    → :dev-amd64  (deterministic)
mise.local.toml pin    → :dev-arm64  (explicit)
```

Rationale: callers that want native use `:dev` and keep working unchanged;
anything needing determinism names the exact arch. buildx emits all three in
one push.

⚠️ **Accepted risk, must be designed against:** a stale per-arch tag sitting
beside a fresh manifest is a confusing failure mode. The identity check must
resolve *through* the arch it asked for, never through `:dev` alone.

✅ **SHIPPED by #676.** As built, with three deviations from the sketch above
and one defect the sketch could not have anticipated:

- **"buildx emits all three in one push" is not what happens.** Ray ruled a
  **native runner matrix** over one bake emitting two platforms, because the
  arm64 half would compile GCC 16.2 and clang-p2996 under QEMU. So each leg
  pushes `:<sha>-<arch>` and *only* that; a `manifest` job then assembles the
  moving tags with `imagetools create`, which references the existing manifests
  rather than re-uploading bytes. The arm runner label was **measured** before
  the matrix was built on it (`ubuntu-24.04-arm` → `uname -m` = `aarch64`,
  run 31355665422, with an amd64 control arm).
- **Per-commit tags carry the suffix too** (`:<sha>-amd64`), not just the moving
  ones — smoke-test needs a per-architecture handle at the commit, and the
  moving tags do not exist until the manifest job runs.
- **`:dev-<arch>` is safe beside `:dev-<hash16>`**, checked rather than assumed:
  `ghcr_cleanup`'s planner matches `^(base|p2996|dev)-[0-9a-f]{16}$`, so an
  architecture word is never a hash-family member.
- ⚠️ **KNOWN OPEN at merge — the image's mise config is amd64-only.**
  `.devcontainer/mise-system.toml:281` pins `arch = "x86_64"` and `:293`
  `lockfile_platforms = ["linux-x64"]`; both locks carry **zero** arm64 entries
  (131/0 and 35/0, measured 2026-08-10). So an arm64 leg resolves x86_64
  downloads into an arm64 image, and the build-time self-checks *count* tools
  rather than executing them, so it survives the build and surfaces at smoke.
  ⭐ **Ray's ruling, 2026-08-10: publish both architectures anyway and let CI
  establish the real failure**, over the recommended alternative of shipping the
  plumbing amd64-only behind a one-line `PUBLISHED_ARCHES` flip. Recorded so the
  first red arm64 leg is recognised rather than re-diagnosed. The fix, when it
  comes: derive `arch`, add `linux-arm64` to `lockfile_platforms`, regenerate
  BOTH locks for two platforms (#650's trap — regenerating on macOS truncates
  **silently** while the tool count holds), and re-verify the apt.llvm.org
  `[bootstrap.packages]` pins on arm64.
- ⚠️ **The blocking defect was in the content hashes, not the tags.**
  `gather_{base,p2996,dev}_inputs` read `PLATFORM` from the HCL *default* only,
  while bake reads a same-named **environment variable** — so both matrix legs
  would have computed ONE `:base-`/`:p2996-`/`:dev-<hash>` tag. The arm64 leg
  would have probe-HIT the amd64 cache and consumed an amd64 named context into
  an arm64 build, and `:dev-<hash>` — the marker meaning "this passed smoke" —
  would have pointed at whichever leg pushed last. `resolve_bake_platform`
  makes python resolve it exactly as bake does. AC3 was unreachable without it.

### D2 — Arch selector: **explicit per-arch mise tasks over ONE parameterised library** ✅

Ray, verbatim: *"option 3 / make sure this follows the mandate of: modular skill
→ modular mise task → modular python library module/function — make re-usable
via arguments/parameters"*.

**This is a synthesis, not plain option 3.** The call site is explicit
(`mise run up-amd64` / `up-arm64`); the *implementation* is a single
parameterised function, so there is **no duplicated task body**.

```
skill  (judgement: when to use which arch, the non-obvious traps)
  └── mise task   up / up-amd64 / up-arm64   ← thin, passes an ARGUMENT
        └── python library   up(platform=...)  ← ONE implementation
```

⚠️ **The whole benefit is conditional on the library being genuinely
parameterised.** If `up_amd64()` and `up_arm64()` become two functions, this
decision has bought the duplication it was chosen to avoid.
[[agent-artifact-conventions]] rule 6: *"make each layer reusable by PARAMETER,
not by copy — a library function that hard-codes this repo's case cannot serve
the next caller; make that case the parameter's DEFAULT instead."*

So: **`platform` is a parameter with a host-native default**, and the twelve
hard-coded `linux/amd64/v2` literals collapse into that one default.

⭐ **Ray's ruling, 2026-08-09 — this sentence and #673's "behaviour unchanged"
are in direct conflict on an arm64 Mac**, where a host-native default would
target `linux/arm64/v8` and no arm64 `:dev` exists until #676. Resolution:
**host-native is the FALLBACK; the repo carries ONE explicit pin.**
`resolve_platform()` = explicit override → `DOTFILES_PLATFORM` → host native,
and `mise.toml`'s global `[env]` supplies the pin. Every existing flow resolves
to what it always did, and **deleting that pin is what flips the default to
native** once #676 publishes both arches and #678 brings up a native container
— no other site changes.

#### ⚠️ Concrete bug this must fix — `image.py:943`

The identity check **already** recurses into manifest lists, hard-coded to the
`linux/amd64` entry. Under D1's manifest `:dev`, it would resolve, silently
select amd64, and compare that hash to an **arm64** container. Not a crash — a
**false pass**. Manifest selection must take the same `platform` parameter.

✅ **Parameterised by #673**; the recursion now selects `platform_arch(...)`.
✅ **CLOSED by #674**, across the two surfaces Ray scoped on 2026-08-09:

- **(a) the AC2 control arm — built.** The mismatch path did not merely go
  unverified, it could not fail: an index with no entry for the requested
  architecture fell through to `_gzip_size_for_image`, which measures the
  *local* image whatever architecture that is. It now raises, and the
  local-gzip fallback is narrowed to a genuinely unreadable document. Four
  FAIL arms are pinned in `tests/test_image_smoke.py` (absent arch, index of
  attestations only, `windows/amd64` against a `linux/amd64` request, empty
  index); both mutations — restoring the fall-through, and dropping the `os`
  check — are caught.
- **(b) `sync.py` — probed, and NO change was needed.** Measured both arms
  against a real multi-architecture tag: `imagetools inspect --format '{{json
  .Manifest.Digest}}'` and, after a `--platform`-scoped pull of *either*
  architecture, `image inspect --format '{{json .RepoDigests}}'` return the
  **same index digest**. A `--platform` pull selects which manifest is
  materialised, not which digest is recorded, so `SyncStatus.stale` compares
  like-for-like as written. Recorded in `registry_digest`'s docstring so it is
  not re-opened. ⚠️ `sync.py:127`'s "can never converge" is about a **buildkit
  re-export** minting a new local digest; do NOT cite it as multi-arch evidence
  (this spec did, briefly, and it was wrong).

One fact found while doing it contradicts the framing above: `:dev` is
**already** an OCI index (an `amd64/v2` entry plus an `unknown/unknown`
attestation entry), so the recursion runs today rather than lying dormant until
D1. The (a) defect was therefore **reachable** before dual-arch publication, not
merely prospective — `dotfiles-setup image size-report --platform linux/arm64/v8`
against the real `:dev` took the fall-through, and now exits 1 naming
`available: linux/amd64`. It was not *exercised*, because the repo pin resolves
to amd64 and every caller inherits it. AC3's "passes on both architectures" is
satisfied by **synthetic manifest fixtures**; the real two-architecture run is
deferred to #676.

✅ **The deferred run LANDED in #676** as the `manifest` job's "Assert each
architecture resolves to its own image" step: `size-report --platform <triple>`
against the freshly-published index, once per published architecture, requiring
the measurements to **differ**. Identical measurements mean the index points
both entries at one image — the failure a "did the pull succeed" check cannot
see. A fixture is not the registry, and now the registry is checked.

#### The 12+ hard-coded sites (the real risk is PARTIAL threading)

✅ **SHIPPED by #673** (PR #694, merged 2026-08-09). The site list below is kept
as the point-in-time survey it was; do not treat it as current.

`docker-bake.hcl:20` · `mise.toml:251,277,303` · `devcontainer.json:81,92` ·
`docker.py:164,178` · `image.py:840,881,943,1042` · `apt_pins.py:156,164` ·
`mise.toml:765,795` (verify-arch) · `hook_guard.py:297`

⚠️ **The survey was INCOMPLETE, and that is the finding.** `hook_guard.py:297`
was never a platform literal (it names the *variable*), while
`scripts/benchmark-docker.sh` (ten sites), `main.py`'s three argparse defaults,
`sync.py:76`, `image.py:1128,1233,1635`, `token_audit.py:190` and
`image_lock.py`'s `REQUIRED_MACHINE` were all missing from it. A hand-built list
of "the places to change" is exactly the artifact this failure mode defeats.

**Proposed gate — APPROVED and shipped as the `no_platform_literals` hk step**
(`dotfiles-setup platform-literals`, logic in
`python/src/dotfiles_setup/platform_target.py`, pinned by
`tests/test_platform_target.py`). It is glob-less and enumerates the tracked
tree. It **failed on its first real run and named eight sites the change had
missed** — the completeness argument, demonstrated rather than asserted.

Two deviations from "exactly one default", both deliberate:

1. **Two files carry the literal**, `mise.toml` (the pin every mise-run flow
   reads) and `docker-bake.hcl` (CI's bake jobs do not run under mise, and HCL
   cannot read TOML). No single value is readable from HCL + TOML + JSON +
   Python without codegen — **that is #680's job**. `find_default_drift` holds
   the two byte-equal, so the duplication cannot diverge silently.
2. **`platform_target.py` is exempt from its own scan.** It composes every
   triple from `_MICROARCH_LEVEL` and hard-codes none, but its docstring and
   scan pattern must be able to NAME them, and it issues no `--platform`.

Note the string is `linux/amd64/**v2**` — a *microarchitecture level*. arm64's
analogue is `linux/arm64/v8`. **The parameter carries a full platform triple,
not an arch word.**

### D3 — R10 scope: **lifecycle-event integrity is the reason**, not docker-avoidance ✅

Ray, verbatim: *"we need to enforce following the devcontainer best practices
regarding: start / stop / restart / status. **running raw docker commands
bypasses the lifecycle events**"*.

**This gives the rule its principle, which the old wording lacked.** `do-not.md`
#3 said "use the CLI so lifecycle hooks run" but framed it as a tool-choice
preference. The real invariant is:

> **Any operation that SHOULD fire a lifecycle event must go through the
> devcontainer CLI. Raw docker silently skips the event.**

That predicts the boundary instead of enumerating it:

| Operation | Fires a lifecycle event? | Verdict |
|---|---|---|
| start / stop / **restart** / **status** | **YES** | **CLI ONLY** — `docker start` skips `postStartCommand` |
| create / build / up | YES (`onCreate`, `postCreate`) | CLI ONLY |
| `ps`, `inspect`, `history`, `imagetools`, size | **NO** — read-only, no state transition | allowed |
| `docker run --rm` ephemeral probe on a *pinned base* | NO — not a devcontainer at all | allowed ([[local-devcontainer-first]]) |

⚠️ **`restart` and `status` are NEW in this list** and are the sharp end.
`docker restart` skips `postStartCommand`, which is where the **SSH socket
re-chown** happens — the documented R2 durable fix
(`.devcontainer/AGENTS.md`). So a raw `docker restart` produces a container
whose outbound SSH is broken, with no error. That is the concrete harm, and it
is worth naming in the rule.

### D4 — Coexistence: **ALL THREE modes; arch-scope everything** ✅

Ray, verbatim: *"1 2 and 3 — i want flexibility on how to code/build/test"*.

So the design must support, simultaneously:

1. **Full amd64 devcontainer** with persistent home volume (run C++ under x86-64)
2. **Ephemeral `--rm` amd64 checks** (verify the image builds/smokes) —
   the pattern [[local-devcontainer-first]] already blesses
3. **Switching freely** between arm64 and amd64 without teardown

⇒ **Arch must be scoped into the container name, the home volume AND the SSH
port**, because mode 3 means both can be up at once:

```
arm64 (native)              amd64 (Rosetta)
────────────────            ───────────────
dotfiles-…-<hash>-arm64-4444   dotfiles-…-<hash>-amd64-4445
volume …-arm64-home            volume …-amd64-home
ssh -p 4444                    ssh -p 4445
```

⚠️ **Consequences that must not be lost:**

- **R1's success criterion changes.** `ssh ${USER}@localhost -p 4444` becomes
  **port-per-arch**; `verify-ssh-inbound` must take the arch/port as a
  PARAMETER (consistent with D2's mandate), not assume 4444.
- **Two home volumes = real disk.** Acceptable per Ray's flexibility ruling.
  Mitigate by creating the second **lazily** — it should not exist until the
  arch is first used. ⚠️ A half-created volume from an interrupted first run is
  a nasty state; design for it explicitly.
- **`mise run prune`** must learn about arch-scoped volumes or it will orphan
  them.
- Volume names currently do **not** include the port (C10/C11/C12) — keep that
  property; add **arch** only, or a port change would orphan the home volume.

### R1.4 resolved — the three gccs map to REAL artifacts

Ray's three-compiler list was **exactly right**; my model of the repo was wrong.

| # | Ray's words | The actual artifact | Path | Managed by |
|---|---|---|---|---|
| 1 | *"latest available from the ubuntu version"* | apt **gcc-16**, arriving as a **transitive** dep — not declared | `/usr/bin/gcc` | nothing (implicit) |
| 2 | *"the 16.2 version"* | **NEW — this project** | TBD | TBD (R1.3) |
| 3 | *"the gcc latest build we have already"* | **GCC-17 + P2996 reflection**, precompiled `.deb` (kayari.org / jwakely trunk) | **`/opt/gcc-latest/bin`** | Renovate `custom.gcc-latest` + `gcc-sha-repair` (#249) |

**NOT gccs — do not count them:** apt **clang-22** (`/usr/lib/llvm-22/bin`) and
**clang-p2996** (`/opt/clang-p2996/bin`). Three *gcc* compilers, three *clang*
families; six toolchains total on the image.

Note the version ordering is deliberate and coherent: **distro 16** (stable,
old) → **16.2** (stable, current) → **17.0.0 trunk** (dev snapshot). #2 is the
current *stable release*; #3 is a *trunk* build. They are not redundant.

⭐ **R1.3 therefore has TWO in-repo precedents, and the cheaper one may fit:**

| Pattern | Cost | Fits R1.2/R1.3? |
|---|---|---|
| **p2996 content-hash GHCR cache** — build from source, publish `:p2996-<hash16>` | ~80–120 min cold build; needs a builder stage | Yes, but expensive — this is what Ray *asked* for |
| **`GCC_LATEST_DEB` pinned filename** — download a prebuilt `.deb`, pin by name, Renovate-bump | **No build at all** | Yes — **IF** a prebuilt 16.2 `.deb` exists |

⇒ **Open question for the research/design phase:** does a prebuilt gcc-16.2
`.deb` (or conda-forge 16.2) exist? If yes, R1.1 costs almost nothing and R1.2's
"don't keep rebuilding it" is satisfied *by not building it at all*. Ray already
noted conda has only **16.1** today — hence his own phased plan (R3.3).

### R11 — RESEARCH MANDATE (Ray, 2026-08-08)

Run `/research` **and** `/deep-research` on devcontainer best practices, and
**validate against the devcontainer SCHEMA**:

- <https://github.com/devcontainers/spec/tree/main/schemas>
- <https://raw.githubusercontent.com/devcontainers/spec/main/schemas/devContainer.schema.json>
- <https://github.com/devcontainers/cli>

> *"there might be modern tools/apis/sdks/libraries and/or a python sdk we can
> use to make programatic development of this easier and type checked/linted/
> static analysis run"*

**This directly serves R8** — if a typed Python SDK for the devcontainer spec
exists, the extracted library should build on it rather than hand-roll JSON
handling. [[use-tool-builtins]] is a HARD GATE here: research before building.

⚠️ Our `devcontainer.json` already declares `$schema` (line 76), so schema
validation is *available* but **nothing in `hk.pkl` currently validates against
it** — to be confirmed, and a likely quick win.

### D5 — R10 REFINED by research: the CLI **has no stop/restart/status** ✅ FACT

Report: `docs/research/runs/research-20260808-devcontainer-lifecycle-spec/report.md`
(persisted verbatim; the agent's own `Write` was hook-denied).

**`devcontainer` 0.88.0 subcommands:** `up · set-up · build · run-user-commands ·
read-configuration · outdated · upgrade · features · templates · exec`.
**There is NO `stop`, `down`, `restart`, `status` or `ps`.**

⚠️ **A cross-check caught a near-miss.** A WebFetch summary of the CLI README
listed `devcontainer stop`/`down` as available. The raw markdown shows them as
**unchecked roadmap boxes** (`- [ ] devcontainer stop`). The summarizer read the
roadmap as the command list. **Do not build on them.**

⇒ **R10 as literally worded is IMPOSSIBLE**, and the research says exactly where
the line goes:

| Operation | Implementation | Why |
|---|---|---|
| up / create / start | **`devcontainer up`** | carries the hooks |
| exec | **`devcontainer exec`** | also applies `userEnvProbe`, `remoteUser`, `remoteEnv`, cwd — `docker exec` applies **none** |
| build | **`devcontainer build`** (has `--platform`!) | |
| re-run hooks on a live container | **`devcontainer run-user-commands`** | the escape hatch |
| status | **`devcontainer up --expect-existing-container`** | exits 1 if absent — the only status primitive |
| **stop / down / rm** | **raw docker — NO ALTERNATIVE EXISTS** | |
| **restart** | **`docker stop` + `devcontainer up`** — NEVER `docker restart` | |

**The rule to write is therefore:** *raw docker is banned for
**hook-bearing** operations (start / restart / exec / create); it remains the
only implementation for stop/rm and for read-only inspection.* That is D3's
principle, now with the exact boundary the research supplies.

### D6 — Lifecycle facts that change the design (R9 is largely ANSWERED)

- **SIX hooks, and Ray's list was complete** — enumerated from
  `injectHeadless.ts:128`, not from the prompt. `waitFor`/`userEnvProbe` are
  *controls*, not hooks. `postAttachCommand` is **not** a legal `waitFor` value.
- ⚠️ **FEATURES CONTRIBUTE LIFECYCLE HOOKS** and they are **invisible in
  `devcontainer.json`**. Only `read-configuration
  --include-merged-configuration` reveals them. **We use the sshd feature** — so
  our real hook set is larger than our file shows. Any R8 library that reads
  `devcontainer.json` alone **under-reports what runs**.
- **Idempotency is marker-file based**, not state-machine based: create-hooks
  compare against docker `Created`, `postStart` against `State.StartedAt`.
  `postAttachCommand` has **no marker — it runs unconditionally, every attach**.
- **Hooks are orchestrator-run over an exec channel — NOT the container
  ENTRYPOINT.** That is *why* docker cannot run them: there is nothing for it to
  run. This is the precise justification R10 needed.
- **Concrete harm, confirmed against our own config:** our `postStartCommand` is
  the `ssh-auth.sock` chown ⇒ **a raw `docker start` silently breaks R2 outbound
  SSH**, presenting later as "git push hangs".

### D7 — R8 library shape: **subprocess the CLI + CODEGEN the models** ✅ FACT-BASED

- **No typed Python SDK for the devcontainer spec exists.** Control-armed: PyPI
  control `requests` → 200, eight candidate names → **404 all**; GitHub
  `devcontainer language:Python` → 872 hits (control 3,972) but **zero** model
  the spec. ⚠️ PyPI *full-text search* was **blind** (challenge page) — that null
  is explicitly NOT relied upon.
- **The CLI has no library API even from Node** (`main/exports/types: null`).
  **Subprocess is the only contract.**
- ⚠️ **The trap a wrapper must handle:** `up` reports errors **in-band on
  stdout** with an `{"outcome":"error"}` envelope; `read-configuration` reports
  failure by **emitting nothing at all**, and its *success* has **no envelope**.
  **Branch on returncode FIRST, always.** Two different stdout shapes.
- `--log-format json` affects **stderr only**, as NDJSON. Exit codes are only
  `0`/`1` — **no taxonomy**. Do **not** parse `--help` (yargs, no `--json`).
- **Recommendation adopted:** drive lifecycle via `subprocess` on the
  **version-pinned** CLI; generate typed models with `datamodel-codegen` from
  `devContainer.base.schema.json` **pinned to a commit SHA** (the schema is
  **unversioned** — no `$id`, no `version`, a moving `main` file); hand-write the
  narrowing for the `string|array|object` lifecycle union, which codegen cannot
  express. Prior art for the exact move: `compose-pydantic`.

### D8 — Multi-arch is NOT in the schema (affects D1/D2)

Control-armed grep on `devContainer.base.schema.json`:
`platform|architecture|arch"` → **0** hits (control `runArgs` → 1, `docker` → 4).
**There is no `platform` field anywhere in the schema.**

⇒ Multi-arch has exactly two homes, both already in use here:

1. **`devcontainer build --platform`** — a real CLI flag ("Set target
   platforms"), alongside `--push`, `--output`, `--cache-to`, `--image-name`.
   **This is the R2 build surface.**
2. **Free-form escape hatches in config** — `runArgs` and `build.options` are
   `array<string>`, unconstrained. That is exactly where our
   `--platform=linux/amd64/v2` already lives (`devcontainer.json:81,92`).

⚠️ **Consequence for R11's "validate against the schema":** schema validation
**cannot** catch a wrong platform string — the field it would validate does not
exist. Our arch correctness must be enforced by our **own** contract, not by
`check-jsonschema`.

### D9 — Q4 ANSWERED: **GCC 16.2.0 released 2026-08-07 (one day ago)** ✅ FACT

⭐ **This reframes R1.1 entirely.** The question is not *"does a prebuilt exist"*
but *"how long until one does, and from whom"* — and vendors differ by ~8–11 weeks.

**No prebuilt 16.2 exists anywhere today** (conda-forge 16.1.0 · Homebrew 16.1.0
· Docker Hub 16.1.0 · jwakely trunk-only x86_64-only · Ubuntu/PPA are *March
trunk snapshots*).

| Vendor | 16.2 ETA | Basis |
|---|---|---|
| **Homebrew** | **~2026-08-18** | PR **#297625** opened on release day; 16.1.0's PR took **11 days** |
| conda-forge | mid-Sep → early Nov | 16.1.0 took **89 days**; no 16.2 work started (armed: `16.2`→0, `16.1`→3) |

⭐ **Homebrew ships `arm64_linux` AND `x86_64_linux` bottles** → serves **R2
directly, zero cross-compilation**. conda-forge covers both arches too, so
**arch coverage is not the discriminator — release latency is.**

⇒ **R3.2 ANSWERED: YES, add the Homebrew backend alongside conda**, specifically
because of the latency gap.

**Revised phasing** (Ray's staging kept; vendor flipped):

1. **Phase 1 — conda-forge 16.1.0 today.** De-risks R1.2/R1.3 packaging without waiting.
2. **Phase 2 — 16.2 from Homebrew (~10 days), NOT conda-forge.** Likely
   **eliminates the CI source build entirely** — Ray's stated goal.
3. Build from source only if 16.2 is needed before ~2026-08-18.
4. **Recheck `formulae.brew.sh/api/formula/gcc.json` → `versions.stable` on
   ~2026-08-18.** One armed call; if it reads `16.2.0`, the source build is dead work.

⚠️ **R1.4 CORRECTION — the distro compiler is NOT a released GCC.** Ubuntu
resolute's `gcc-16` is **`16-20260322-1ubuntu1`, a trunk snapshot from
2026-03-22 that PREDATES 16.1**. The "exactly 3 compilers" check must not assume
it is 16.1/16.2 or it will misidentify them.

### D10 — `docker restart` proven EMPIRICALLY, with a nuance that must not be flattened

Probed the **running container** (`4b9b9ef700b1`), not the docs:

- `Cmd` = `["-c","echo Container started\ntrap … /usr/local/share/ssh-init.sh\nexec \"$@\" …","-"]`
- Control-armed grep for the chown: **0** hits in `Entrypoint`+`Cmd`, **6** in
  the full `docker inspect`. Probe discriminates.
- The string lives only in the `devcontainer.metadata` label, **with
  `${localEnv:USER}` UNSUBSTITUTED** — docker has no executor for it *and* could
  not resolve it (a host value the container cannot see). **Two independent
  reasons.**

⚠️ **THE NUANCE:** feature **entrypoints DO survive `docker restart`** —
`ssh-init.sh` is in `Cmd` and runs every start. So:

> A raw `docker restart` re-runs image/feature **entrypoints** but **none of the
> six lifecycle hooks**.

Someone who tests `docker restart`, sees `ssh-init.sh` fire, and concludes
"restart works" is **wrong** — the chown is what's missing, surfacing later as
an agent-socket permission failure, not a startup error. **Silent and
time-delayed** — the strongest justification for the ban.

### D11 — the `stop`/`down` question, SETTLED (five routes)

Ray challenged the "no stop verb" finding with the CLI README's status list.
**Raw markdown resolves it:** lines 13–21 are **`- [x]`** (shipped), lines 22–23
are **`- [ ]`** — `devcontainer stop` and `devcontainer down` are the only
**unchecked** entries in a roadmap headed *"Current status"*.

⚠️ **Durable lesson: copy-pasting a rendered GitHub checklist STRIPS checkbox
state.** `[x]` and `[ ]` both render as boxed bullets and flatten to identical
plain text. A WebFetch summary hit the same trap. **Read the raw markdown when a
checklist is load-bearing.**

Five agreeing routes: raw README checkboxes · the README's own `--help`
transcript (lines 75–81, no stop/down) · Ray's screenshot · a live control-armed
`devcontainer --help` (`up`/`exec`/`build`→1, `stop`/`restart`/`status`/`down`/`ps`→0)
· `mise.toml:929`, where Ray recorded the same finding on **2026-04-06** and
`mise run stop` has used `docker rm -f` ever since.

### D12 — Rule shape: hook-bearing ban + **adopt `shutdownAction` explicitly** ✅

Ray chose the D3/D5 boundary **plus** setting `shutdownAction` in
`devcontainer.json` rather than leaving it on the spec default.

**The rule to write:**

> Raw `docker` is banned for **hook-bearing** operations — start, restart, exec,
> create. It remains the **only** implementation for stop/rm (the CLI's `stop`
> and `down` are unshipped roadmap items) and for read-only inspection. Those
> calls live **inside the devcontainer library** and nowhere else.
> **`restart` = `docker stop` + `devcontainer up`, never `docker restart`.**

Justification to embed (all proven, not asserted): hooks are dispatched by the
orchestrator over an exec channel and are **not** the container ENTRYPOINT; the
stored `postStartCommand` carries an **unresolved `${localEnv:USER}`** that the
container cannot resolve; and **feature entrypoints DO still run**, so a
`docker restart` *looks* healthy while the chown is silently skipped.

⚠️ **`restart` must become a NAMED VERB** (`mise run restart` → library) or
people will reach for `docker restart` regardless — a two-step nobody guesses is
not a usable substitute.

### D13 — `shutdownAction = "stopContainer"` — RAY'S CALL, risk acknowledged ✅

Ray chose **`stopContainer`** (the spec default, made explicit) over `none`,
having been shown the downside. **This is his decision; do not re-litigate it.**

⚠️ **But VERIFY the behaviour empirically before trusting it** — it was picked
against a stated risk, so the risk deserves a measurement rather than an
assumption:

1. **Does detaching CLion/VS Code actually stop the container?** If yes,
   `ssh -p 4444` dies with it and **R1 inbound breaks on IDE close**. The spec
   says the container stops when "the tool window is closed / connection ends",
   but *which* tool owns the lifecycle is ambiguous here: we bring the container
   up from a **terminal** (`mise run up`) and attach IDEs afterwards. A
   CLI-initiated `up` may not be owned by the IDE at all.
2. **Does it fight D4?** Both arches are meant to stay up simultaneously.
3. **Interaction with `mise run stop`** (`docker rm -f`) — belt and braces, or
   conflicting owners?

**If measurement shows IDE-detach kills the container, bring this back to Ray**
with the evidence — that is new information, not a re-argument.

### D14 — ⚠️ SUPERSEDED by D14b. Kept for provenance.

<details><summary>Original (new standalone repo) — REVERSED by Ray, same session</summary>

Ray first chose extraction to its own GitHub repo, with dotfiles and other
projects depending on it as a SHA-pinned `uv` git dependency, following the
`kb_setup.currency` precedent.

</details>

### D14b — Distribution: **library stays IN dotfiles; consumers depend ON dotfiles** ✅

Ray, verbatim (correcting himself immediately):

> *"i think i misunderstood — this dotfiles repos should still be responsible
> for building/managing the docker images as it needs to keep in sync w this mac
> as we are trying to get a dev environment that is as close/similar to a native
> mac experience. we still need to break up the python library and some code so
> that it can be re-used. how we test it is by creating a new repo that has
> .devcontainer/ subdirectory and just downloads its dependencies from the
> dotfiles github repo"*

**Three consequences, all different from D14:**

1. **NO third repo.** `dotfiles` remains the **owner** of the images and of the
   library. Image build/publish stays here — it must track this Mac.
2. **The library is still broken up** — modularised *within* `python/` so it is
   importable and reusable, but it ships **from the dotfiles GitHub repo**
   (a `uv` git dep pointing at `ray-manaloto/dotfiles`).
3. **A new repo is the TEST, not the home.** Its `.devcontainer/` pulls the
   published images and takes a dependency on dotfiles. It exists to **prove
   reusability**, i.e. to make the seam real rather than asserted.

⭐ **The stated goal, worth keeping in front of every decision:** *"a dev
environment that is as close/similar to a native mac experience."* That is the
**why** behind R2 — native arm64 is not a nice-to-have, it is the point.
Rosetta amd64 is the compatibility lane (D4), not the target.

⚠️ **The new repo is a control arm for reusability.** A library called reusable
by its own author, inside its own repo, is untested. A consuming repo that can
only work by reaching into dotfiles' internals proves the seam is wrong. Judge
the extraction by **what the test repo has to import**, not by how the modules
look from here.

⚠️ **R7 still bites the same way:** the consuming repo gets no `scripts/`
directory and no bash allowlist, so anything on the reused path must be
**genuinely zero-bash** — `ensure-docker-up.sh` and
`validate-devcontainer-json.sh` (`hk.pkl:137,151`) must become python.

⚠️ **Carry the lesson that pattern already taught us:** cross-repo shared code
**drifts**, which is why `mise run parity` and `parity.toml` exist (#354). The
new repo needs the same treatment from day one — a declared shared set and a
gate — or it will diverge silently.

⚠️ **R7 lands hardest here.** Allowlisted `scripts/*.sh` wrappers do **not**
travel to a consuming repo. So the extracted library must be **genuinely
zero-bash**, not "bash that happens to be allowlisted locally". Today
`hk.pkl:137,151` call `scripts/ensure-docker-up.sh` and
`scripts/validate-devcontainer-json.sh` — **both must become python** before or
during extraction.

### R12 — LOG REVIEW (Ray, 2026-08-08, verbatim)

> *"also the logs need to be reviewed for warnings/errors instead of skipping
> them"*

This is [[zero-skip-policy]] applied to **build and lifecycle logs**, which are
currently the least-scrutinised surface: a `devcontainer up` emits a large log
that nobody reads unless it exits non-zero.

**Scope it explicitly — every log this system produces:**

**MEASURED 2026-08-08, control-armed** (arms fired 6 / 4 / 1 / 7, so the empty
results below are real absences, not blind probes):

| Log | Today | Evidence |
|---|---|---|
| **mise output inside the smoke** | ✅ **A zero-warning gate EXISTS** — `FAIL: mise produced warnings (zero-warning policy)` | `image.py:825-828` |
| Docker/BuildKit **base image build** (CI) | ❌ **unscanned** | no `log_scan`/`scan_log`/`build_log` module; no warning grep in `.github/workflows/` |
| `devcontainer up` / lifecycle hook output | ❌ **unscanned** | same |
| `--log-format json` NDJSON | ❌ **never passed anywhere** | `git grep 'log-format'` → **0** outside docs |
| smoke tier 1/2/3 overall | exit-code gated only | |
| `mise run lint` / gate logs | rc-gated only | |

⇒ **R12 is neither greenfield nor done.** One narrow warning gate exists on
*mise* output in the smoke tier; the **build log and the entire lifecycle log
surface are unscanned**, and the free structural mechanism
(`--log-format json`) is unused.

Related but different: the `build.no-stderr-suppression` contract
(`suites.toml:96`) stops us *hiding* stderr — it does not *read* it.

⭐ **The CLI hands us the mechanism for free:** `--log-format json` turns
**stderr** into NDJSON `{"type","level","timestamp","text"}` records, with
`level: 2` carrying errors (D7). So a wrapper that *always* passes
`--log-format json` can classify warnings/errors **structurally** instead of
grepping prose. That is a strong argument for routing every CLI call through
the library.

⚠️ **A non-zero exit is NOT the same as a clean log** — that is the entire point
of this requirement, and it is the same trap as
[[probes-need-a-control-arm]]: a check that only looks at rc can only ever see
failures loud enough to abort.

⚠️ **Prior art to find, not reinvent:** `missions/docker-mise-system-config/mission.md`
already names *"build log scanning for warnings/errors (zero-skip policy)"* as a
goal. **Verify whether that shipped** before building anything —
[[use-tool-builtins]].

### D15 — Log policy: **warnings FAIL the gate, with a reviewed allowlist** ✅

Ray chose blocking-from-the-start over report-first.

Shape it like the mechanisms this repo already trusts — `bash_budget`'s
ALLOWLIST and `doctor.toml`'s baseline: **a declared set of known-benign
warnings, each with a one-line reason, so every exception is a reviewable diff
rather than silent drift.** Matches [[zero-skip-policy]].

⚠️ **Expect a wall on first run.** The initial scan will surface every
pre-existing warning at once, and they all need triaging before the gate can go
green — the same shape as a linter bump, where newly-enabled checks read as
regressions ([[lint-delta]] exists for exactly that confusion). **Budget for the
burn-down; do not let it become a reason to weaken the gate.**

⚠️ **Ray REJECTED report-first, and the repo's own history says he was right:**
**#92** ("flip Trivy CVE scan to gate after baseline cleanup") has been open
since **2026-04-30** — a live example of the "we'll turn it on later" flip never
happening.

⭐ **Classify structurally, not by grepping prose:** `--log-format json` gives
NDJSON with `level: 2` = error (D7). Prefer that over regexing human text
wherever the CLI produces the log.

### D16 — Seam test: the test repo drives the **FULL lifecycle** through the library ✅

up · stop · restart · exec · status — and it **never touches `docker` or the
`devcontainer` CLI directly**.

Why this is the right bar: it exercises R8's own wording (*"used throughout all
the devcontainer lifecycle methods"*), and it is the **only** version that proves
D12's no-raw-docker rule holds for a *consumer*. A consumer with no library path
for `stop` will simply call docker — and `stop`/`restart` are exactly where raw
docker is unavoidable, so omitting them would leave the rule untested precisely
where it is most likely to break.

⇒ **Forcing consequence, and a good one:** the arch/port/volume parameters
(D2/D4) must be **genuinely parameterised on day one**, not defaulted to our
case. The test repo has a different workspace path, probably a different SSH
port, and no p2996. If those are hard-coded, the test cannot pass — which is
[[agent-artifact-conventions]] rule 6 enforced by construction rather than by
review.

⇒ **`restart` and `status` must exist as library verbs** (D12 already flagged
`restart` needs a named verb). `status` maps to
`devcontainer up --expect-existing-container`; `restart` to
`docker stop` + `devcontainer up`.

---

## SHARED UNDERSTANDING — the 16 decisions, consolidated

| # | Decision |
|---|---|
| **D1** | `:dev` manifest list **+** `:dev-amd64` / `:dev-arm64` per-arch tags |
| **D2** | Per-arch mise tasks over **ONE parameterised** python function (skill → task → library) |
| **D3** | Docker ban's principle = **lifecycle-event integrity**, not tool preference |
| **D4** | All three amd64 modes; arch scoped into container name, home volume **and** SSH port |
| **D5** | CLI has **no stop/down/restart/status** → raw docker for stop/rm; `restart` = `docker stop` + `devcontainer up` |
| **D6** | SIX hooks; **features contribute hooks invisibly**; marker-file idempotency; postAttach has no marker |
| **D7** | **No Python SDK exists** → subprocess the pinned CLI + `datamodel-codegen` from the SHA-pinned schema |
| **D8** | Schema has **no `platform` field** → arch correctness needs OUR contract, not `check-jsonschema` |
| **D9** | **GCC 16.2.0 released 2026-08-07**; Homebrew ~10 days (ships `arm64_linux`), conda-forge ~2-3 months |
| **D10** | `docker restart` skips all hooks — **proven**; but feature entrypoints DO survive, so it *looks* healthy |
| **D11** | `stop`/`down` are **unchecked roadmap boxes**; five routes agree |
| **D12** | Rule = ban raw docker for **hook-bearing** ops; stop/rm confined to the library; adopt `shutdownAction` |
| **D13** | `shutdownAction = "stopContainer"` — Ray's call; **verify IDE-detach behaviour empirically** |
| **D14b** | Library stays **IN dotfiles**; a new repo is the **TEST**, not the home |
| **D15** | Log warnings **FAIL the gate**, with a reviewed allowlist |
| **D16** | Test repo drives the **full lifecycle** through the library, touching neither docker nor the CLI |

### Still OPEN after grilling

| Item | Status |
|---|---|
| **R9** — the lifecycle markdown document | Research **done** (D6/D10); the document itself is **unwritten** |
| **R1.2/R1.3** — detailed 16.2 packaging design | Blocked on the ~2026-08-18 Homebrew recheck (D9) |
| **R12** burn-down | Size unknown until the scanner runs once |
| **R4** — run as a `/goal` in a new session | **Ray-invoked**; cannot be started by an agent |
| **R5** — image-size diagnostics | **DEFERRED by Ray**, explicitly gated behind "image working + ship/land validated + ssh working" |
| **P2** — `/mattpocock-skills:code-review` + `/code-review` | For the implementation phase |
| **P3** — `/verify` | **Ray-owned**, final gate |

### D17 — R13/R14 stack: **RESEARCH FIRST** (Ray's call) ⏳

Ray chose research over adopting a stack from familiarity — correct under
[[use-tool-builtins]]'s HARD GATE, since R13/R14/R14.5 are literally
"does an existing tool do this" questions.

Research agent `logging-stack-research` covers: sink-based structured logging
(structlog vs loguru vs stdlib+QueueHandler), Rust/C++ cores with python
bindings, efficient offloadable message formats, **how to machine-enforce the
stdout ban**, `datamodel-code-generator` practice, and async subprocess for a
library that must not impose an event loop on sync callers.

### R14 baseline — MEASURED 2026-08-08 (the burn-down is 126, not 2)

| Surface | Count | Note |
|---|---|---|
| `print()` | **2** | `image.py` only; ruff `select = ["ALL"]` already enables **T20 un-ignored** |
| **`sys.stdout` / `sys.stderr`** | **126** | `pr.py` 30 · `sync.py` 15 · `image.py` 15 · `main.py` 11 · `verify.py` 8 · … |
| stdlib `logging` | **~40 modules** | already in use — the codebase is **hybrid** today |

### ✅ D18 — R14.3 SOLVED by **ruff `TID251`**. My "ruff can't do it" claim was WRONG.

⚠️ **CORRECTION.** I told Ray *"ruff CANNOT enforce R14.3 … R14.3 needs a custom
AST / tree-sitter check"*. **False.** True premise (no rule *named* for
`sys.stdout` — all **968** rules in pinned ruff 0.16.2 enumerated; `stdout`
matches only `UP022` and `RUF030`), wrong conclusion.

**`TID251` (flake8-tidy-imports `banned-api`) bans arbitrary DOTTED PATHS,
resolving attribute access and aliases — not just imports.**

```toml
[lint.flake8-tidy-imports.banned-api]
"sys.stdout" = { msg = "write via the logging sink, not sys.stdout" }
"sys.stderr" = { msg = "write via the logging sink, not sys.stderr" }
```

Measured on a fixture (`ruff check --no-cache`):

| Form | Result |
|---|---|
| `sys.stdout.write("x")` | **TID251 flagged** |
| `sys.stderr.write("y")` | **TID251 flagged** |
| `from sys import stdout, stderr` | **flagged at the import** |
| `import sys as s` → `s.stdout.write(…)` | **flagged — alias resolved** |
| `from sys import stdout as out` | **flagged — alias resolved** |
| `print("hello")` | **T201 flagged** |
| `sys.exit(1)` | **clean** ← control arm |
| `io.StringIO().write("ok")` | **clean** ← control arm |
| `getattr(s, "stdout").write("z")` | ⚠️ **MISS** |

Both control arms clean ⇒ it discriminates rather than flagging every dotted call.

⭐ **`select = ["ALL"]` already enables TID251 — it currently bans NOTHING.** The
`banned-api` table is what gives it teeth. **No new tool, no new CI step, no
homegrown AST.** (semgrep = new binary; pylint = a second linter for one check;
tree-sitter = homegrown, which [[use-tool-builtins]] would reject.)

**Escape hatch for the one sink module — verified working:**
`[lint.per-file-ignores] "…/_sink.py" = ["TID251", "T20"]` → 0 findings in
`_sink.py`, 2 still in a sibling. Per-file and in a **reviewed diff** — unlike a
`# noqa`, which `no_lint_skip` rejects anyway.

⚠️ **Known gap — it is a REDIRECT GUARD, not a sandbox** (same posture as
`hook_guard`): `getattr(sys,"stdout")`, `os.write(1,…)`, `os.fdopen(1)` and
fd-inheriting subprocesses are not caught. **Recommend also banning `os.write`
and `os.fdopen`** — one line each, and we drive subprocesses anyway.

### ✅ D19 — R14.5 ANSWERED: **no Rust/C++ logging core. Don't.**

Control-armed (`zzqq-nonexistent-control-pkg-8f3a` → 404, every real name → 200,
so the 404s are real absences):

| Candidate | Latest release | Verdict |
|---|---|---|
| `picologging` (Microsoft, C++) | 0.9.3, **2023-09-29** | **no release in ~2.8 yrs**; still self-described beta; and it is a *stdlib drop-in*, not structured-events-with-sinks — **wrong shape** |
| `spdlog-python` | 2.0.6, **2023-04-19** | upstream `gabime/spdlog` is alive (29.5k★) but the **binding** is 76★, unmaintained ~2 yrs |
| `tracing-py` | 0.1.0 | **single release, empty summary, no URLs** — a name-squat |
| `pyo3-log` | **404 on PyPI** | a *Rust crate* routing Rust records INTO python logging — **opposite direction** |
| `rust-logging`, `pyspdlog` | **404** | do not exist |
| `logbook` | 1.10.1, **2026-08-05** | ⭐ **alive**, real handler-stack model — under-considered, folded into Q1 |

⭐ **The judgment that settles it: the throughput ceiling is a subprocess
round-trip to a Node CLI** — thousands of records per *build*, not millions per
second. A binary core optimises the free part, while charging every R6 consumer
a compiled dependency: a wheel matrix per platform/python version, manylinux/musl,
and — on this stack specifically — **the amd64-on-arm64 split**. Wrong trade for
a library other repos import.

⚠️ **R16 drift acknowledged.** D7 recorded `datamodel-codegen`, but every
discussion since assumed hand-written models. Ray's framing is stricter —
**ONLY generated models**. Hold that line.

### Clarifications Ray asked for

- **D1 was already "both".** Recorded as three tags from one buildx push:
  `:dev` (manifest list) **plus** `:dev-amd64` **plus** `:dev-arm64`. The
  one-line summary compressed it misleadingly; the decision never changed.
- **D10 is a FINDING, not a plan.** It is the *evidence* that `docker restart`
  skips lifecycle hooks — the proof supporting the ban. The agent ran
  `docker inspect` (read-only) to establish it. **Nothing in the design calls
  docker for lifecycle**; the only surviving docker calls are `stop`/`rm`
  (CLI verbs unshipped, D5/D11), confined inside the library.

### ✅ D20 — R13/R14 stack: **structlog + stdlib `ProcessorFormatter` + `QueueHandler`/`QueueListener`**

⚠️ **Framing correction first: "structlog vs loguru" is NOT the axis.** structlog
is an *event layer* (a processor pipeline producing an event dict, then handing
off); loguru is a *complete logging system with its own sinks*. **The sink layer
is a separate decision, and stdlib already owns it.**

**Maintenance (measured):** structlog **26.1.0, 2026-06-06** (repo pushed
2026-08-06) vs loguru **0.7.3, 2024-12-06 — ~20 months, 265 open issues**.
structlog is the healthier dependency despite 5× fewer stars.

⭐ **THE DECIDING ARGUMENT — loguru's own docs disqualify it for OUR case.**
Under *"Configuring Loguru to be used by a library or an application"*: a library
*"usually should not add any handler"* and should call
**`logger.disable("mylib")` unconditionally in `__init__.py`**. So loguru's
headline advantage — owning the sinks — is **exactly what loguru tells you not to
do from a library**. We would take a hard dependency on a **global singleton
logger we are then instructed to disable**, and every R6 consumer inherits it.

structlog takes the opposite posture: it renders **into stdlib `logging`** via
`structlog.stdlib.ProcessorFormatter`, so the **consuming application keeps
control** of handlers, levels and config. It also preserves our existing
investment (stdlib `logging` in ~40 modules), is **pure-python** (no wheel
matrix — cf. D19 and the amd64/arm64 split), and its processor chain is the
natural place to map the CLI's `{"type","level","timestamp","text"}` records and
our R15 error enums into structured fields. `structlog.contextvars` binds
build-scoped context across the async subprocess code.

**The sink layer = stdlib `QueueHandler` + `QueueListener`.** One `QueueHandler`
returns immediately; a `QueueListener` on a background thread fans one record to
**N handlers, each with its own formatter** — literally "JSON to a file, human
text to console, NDJSON to a scanner" (R14.2). `respect_handler_level=True` lets
each sink filter independently. ⭐ **We pin `requires-python = ">=3.14"`, so
`QueueListener` is a CONTEXT MANAGER** (`with QueueListener(q, *handlers):`) —
removing the ugliest part of the pattern.

⚠️ **`ainfo` is NOT fire-and-forget.** Source (`structlog/stdlib.py:447-471`):
`_dispatch_to_sync` does `run_in_executor(None, …)` — the event loop stays
unblocked but **the coroutine still awaits the write**. It is *offload*, not
fire-and-forget. ⇒ **Get non-blocking from `QueueHandler`, NOT from `ainfo`**,
and prefer plain sync `log.info()` inside async code once the queue is in place.
Simpler *and* faster.

**Trade-off accepted:** we give up loguru's one-liner ergonomics and per-sink
`enqueue=True`, and assemble ~15 lines of queue wiring ourselves.

⚠️ **Migration sizing — do NOT big-bang it.** The D18 ban would fire across
**23 files / 126 references**. **Land the ban on the NEW SDK package first**
via `per-file-ignores` on the legacy modules, then burn those down.

### ✅ D21 — R14.4 REFRAMED: **NDJSON. The format is not the bottleneck.**

⚠️ **This partly reframes Ray's R14.4** (*"modern efficient message formats that
the logging library can offload to the logging thread"*). The research agrees
with the **offload** half and contradicts the **format** half — with arithmetic:

A devcontainer build emits **10²–10⁴ records per run**, over a process whose
wall-clock is **seconds to tens of minutes**. Serialization at that volume is
single-digit **milliseconds in total**, against a subprocess round-trip and a
container build. protobuf over NDJSON optimises ~0.001% of runtime while adding
a `.proto`, a codegen step, a binary dependency and an unreadable log.

**Three reasons NDJSON is *correct*, not merely adequate:**

1. **It is already on the wire** — the CLI emits NDJSON; re-encoding to msgpack
   means decode-then-re-encode for no consumer's benefit.
2. **Our third sink is a SCANNER** (R12/R17). NDJSON is the lingua franca of
   every log shipper (Vector, Fluent Bit, Loki, `jq`). Binary ⇒ write an adapter.
3. **Debuggability** — a log you cannot `tail | jq` costs human minutes on every
   incident, paid far more often than the microseconds saved.

⭐ **The decisive point: offload is ORTHOGONAL to format.** Moving emission to
the `QueueListener` thread takes the **entire** serialization cost off the
caller's path *regardless of encoding* — so once queued, a 3× faster encoder
changes caller latency by **zero**. **Fix the concurrency, not the codec.**

**Encoder:** `orjson` (3.11.9) or `msgspec.json` (0.21.1) if we want the speed
free — both are a **one-line swap** behind structlog's
`JSONRenderer(serializer=…)`, so this stays reversible. **Do NOT** adopt
protobuf / Cap'n Proto / FlatBuffers; revisit only if serialization ever measures
above ~5% of runtime.

⚠️ **Picklability caveat:** loguru's `enqueue` uses a
`multiprocessing.SimpleQueue`, so records must be **picklable**. stdlib
`QueueHandler` + `queue.Queue` (same process) removes that constraint — another
point for the stdlib path.

### ✅ D22 — Ray's constraint RESOLVES R14.4: **`msgspec.Struct` via datamodel-codegen**

Ray: *"it needs to be a format that datamodel-code-generator supports"*.

**PROBED DIRECTLY** — `uvx --from datamodel-code-generator datamodel-codegen --help`,
rc=0, 41,079 bytes (control arm: 2 `usage` lines, so the help really rendered).
⚠️ First attempt returned empty at rc=1 because the **package** is
`datamodel-code-generator` while the **command** is `datamodel-codegen`; the
control arm caught that the "empty" was blindness, not an answer.

**`--input-file-type`:**
`{auto, openapi, asyncapi, jsonschema, mcp-tools, xmlschema, protobuf, avro, json, yaml, dict, csv, graphql}`

⚠️ **CORRECTION to my own reasoning:** I was about to conclude Ray's constraint
*eliminated* binary formats. **It does not — `protobuf` and `avro` are supported
inputs.** Caught before publishing; a correction was also sent to the research
agent so it would not inherit the wrong premise.

**`--output-model-type`:**
`{pydantic_v2.BaseModel, pydantic_v2.dataclass, dataclasses.dataclass, typing.TypedDict, msgspec.Struct}`
(**pydantic v1 is gone — v2 only.**)

⭐ **`msgspec.Struct` IS supported, and it dissolves the D21 tension.** msgspec
encodes to **both JSON and MessagePack from one typed Struct**. So:

| Layer | Choice | Why |
|---|---|---|
| **input** | `jsonschema` | not a choice — the devcontainer spec **is** JSON Schema |
| **output** | **`msgspec.Struct`** | generated per R16; satisfies Ray's codegen constraint |
| **wire** | **NDJSON** | readable, `jq`-able, already what the CLI emits, what the R12/R17 scanner sink wants |
| **available** | MessagePack | free from the same structs if ever needed |

⇒ **Ray's efficiency requirement (R14.4) and the debuggability argument (D21)
are no longer in tension.** The constraint is what made this visible — the
default path would have been pydantic + orjson, and msgspec would never have
been considered.

⭐ **Also found — `--preset`, PYTHON-VERSION-PINNED:**
`standard-py{310..314}-20260619`, `practical-py{310..314}-20260619`. We pin
`requires-python = ">=3.14"`, so **generated syntax can be pinned to the target
version** instead of floating with whatever Python runs the generator. Directly
relevant to R16 reproducibility — and needed at BOTH ends, since the devcontainer
schema itself is **unversioned and moving** (D7).

### ✅ D23 — R16 codegen: `--check` is NATIVE; config in `pyproject.toml`

**datamodel-code-generator 0.72.2 (2026-08-06), 4,000★ — healthy.**
Draft **2019-09 is first-class** (`enums.py:300`, `Auto` default).

⚠️ **Caveat for a MOVING schema:** the project's conformance suite
(`docs/conformance.md`) runs JSON-Schema-Test-Suite against **draft7 and
draft2020-12 only** (640 groups / 2,226 tests). **2019-09 is a supported enum
value but is NOT in the continuously-verified set.** ⇒ pin the generator version
and treat **our generated output** as the thing under test.

⭐ **`--check` is NATIVE** — regenerates in memory, diffs against disk, prints a
unified diff, **exits 1 on drift**, 0 silently when in sync. **No homegrown
generate-to-tmp-and-diff wrapper** ([[use-tool-builtins]] would have pushed us to
write one).

⚠️ **`--disable-timestamp` is NON-OPTIONAL.** Without it the generator stamps a
timestamp header, so **every** regeneration diffs and `--check` **can only
fail** — the mirror image of a check that can only pass
([[probes-need-a-control-arm]]).

**Config lives in `pyproject.toml`, not the command line** (documented best
practice — keeps local and CI identical); both `datamodel-codegen` and
`datamodel-codegen --check` then take **zero arguments**:

```toml
[tool.datamodel-codegen]
input = "…"; output = "…"; input-file-type = "jsonschema"
output-model-type = "pydantic_v2.BaseModel"; disable-timestamp = true
```

Named profiles (`[tool.datamodel-codegen.profiles.<name>]` + `--profile`) handle
multiple schemas.

⚠️ **Do NOT use the pre-commit hook or the official GitHub Action** the docs lead
with — we use **hk**, not pre-commit, and a CI-only Action breaks
[[ci-local-parity]]. Shape it as `mise run codegen` / `codegen-check` wrapping a
`python/` module, wired as an hk step ([[mise-tasks-only]]).

**Unions codegen can't express:** add a **`discriminator`** where we control the
schema (pydantic v2 tagged unions generate cleanly); **never hand-edit generated
output** — keep `_models.py` machine-owned and put fixups in a hand-written
**adapter module** beside it. A hand-edit makes `--check` fail forever.

### ⚠️ D22 CHALLENGED — research recommends `pydantic_v2.BaseModel`, not `msgspec.Struct`

**Ray's constraint permits BOTH**, so it never forced msgspec. The research
argues pydantic, and the argument is strong:

| | `pydantic_v2.BaseModel` | `msgspec.Struct` |
|---|---|---|
| Dependency | **already in `python/pyproject.toml` (`pydantic>=2.13.4`)** — adds nothing | **new BINARY wheel** |
| Runtime validation | **yes** — a moving-schema shape change surfaces as `ValidationError` mappable to an R15 error enum | minimal |
| Speed | slower | faster — **but Q3 established speed is NOT the constraint** |
| MessagePack | no | yes — **but we chose NDJSON, so it is UNUSED** |

⭐ **Consistency argument:** D19 rejected a binary logging core partly because a
compiled dependency charges every R6 consumer a wheel matrix across the
**amd64/arm64 split**. **msgspec is also a binary wheel.** Applying that reasoning
consistently points at pydantic. `TypedDict` gives no runtime check at all —
wrong for an untrusted boundary.

### ✅ D22-FINAL — Ray ruled: **`msgspec.Struct`, UNIVERSAL and ENFORCED**

Ray, verbatim: *"option 2 and it needs to be universal throughout the project to
avoid drift/mismatch and enforced"*.

**D22 stands; the research recommendation above is OVERRULED by Ray**, who added
two requirements beyond the codegen target:

- **R19 — msgspec is UNIVERSAL project-wide** (not just for generated models),
  so there is no second model system to drift against.
- **R20 — ENFORCED**, machine-checked, not a convention.

**Migration scope MEASURED — far smaller than feared:**

| | count | evidence |
|---|---|---|
| files using pydantic | **1** — `config.py` (60 lines) | control arm: 27 files `import json`, so the probe discriminates |
| files using msgspec | **0** | not yet a dependency |

⚠️ **BUT that one file is the awkward case, and it is NOT about models.**
`config.py` uses **`pydantic-settings`** — `BaseSettings` +
`SettingsConfigDict(env_prefix="MISE_"/"DOTFILES_")` — i.e. **environment-variable
settings loading**, across three classes (`MiseConfig`, `ContainerConfig`,
`DotfilesConfig`).

**msgspec has NO `BaseSettings` equivalent.** It is a serialization/validation
library, not a settings library. So "universal msgspec" meets a boundary that is
about a *different concern*:

| Concern | Library | Universal msgspec? |
|---|---|---|
| **Models / serialization** (devcontainer schema, CLI records) | msgspec | ✅ yes — this is R19 |
| **Env-var settings** (`MISE_*`, `DOTFILES_*` prefixes) | `pydantic-settings` | ❓ no msgspec equivalent exists |

**Three ways out — needs Ray's ruling (Q15):** keep `pydantic-settings` for
settings only and enforce msgspec for *models* (the narrow, honest reading);
find a msgspec-native settings library; or hand-roll env loading — which
[[use-tool-builtins]] rejects for 60 lines of working code.

⚠️ **Enforcement (R20) shape:** the D18 `TID251` `banned-api` mechanism handles
this directly — ban `pydantic.BaseModel` while leaving
`pydantic_settings.BaseSettings` allowed, if that is the ruling. **Same tool,
same table, no new machinery.**

### ✅ D24 — R13 async: stdlib `asyncio`, ONE chokepoint — and a DISSENT worth hearing

**Measured on the real interpreter (Python 3.14.0), not cited:**

- `async for raw in p.stderr:` yields NDJSON **line-by-line as it arrives** —
  3 records, 3 lines, rc=0. `p.stderr` is a `StreamReader`, directly
  async-iterable. **No chunk buffer or manual `readline()` loop needed.**
- ⚠️ **Sync-caller trap CONFIRMED:** nested `asyncio.run` →
  `RuntimeError: asyncio.run() cannot be called from a running event loop`.
  A facade built as `def run(): return asyncio.run(_arun())` **works for sync
  callers and breaks for every async caller** — the worst failure mode, because
  **it passes our tests and explodes in the consumer that matters** (R6!).
- ⭐ **3.14 makes the fix clean:** `hasattr(asyncio,"get_child_watcher")` →
  **False** (watchers gone), and `create_subprocess_exec` **works from a
  non-main thread** (measured, rc=0). Historically the fragile spot for exactly
  this pattern.

⇒ **Async core as the ONLY implementation** (no duplicated sync codepath to
drift — the mistake httpx pays for), plus a **thread-hosted-loop sync facade**
(~20 lines, or anyio's **`BlockingPortalProvider`**, which anyio's docs
recommend by name for this case).

**anyio vs stdlib:** start **stdlib**; its value is not forcing asyncio on a
*trio* consumer, and **none of our repos use trio**. Keep subprocess spawning
behind **ONE internal chokepoint function** so the swap stays contained; adopt
anyio the day a trio consumer actually exists. Using anyio for *just the portal*
is a legitimate middle position.

⚠️ **DISSENT — we may not need async at all.** One subprocess, one stderr
stream, line-oriented: `subprocess.Popen` + a reader thread does this with fewer
moving parts, imposes **no event loop on anyone**, and needs **no sync facade**
because it was never async. Async earns its place only when driving **several
containers concurrently**.

⭐ **But D4/D16 say we DO** — both arches up simultaneously, and a test repo
driving its own container. **So concurrent lifecycle is real, not hypothetical.**
That tips it to async — but decide it deliberately, not by defaulting to async
because the CLI is I/O-shaped.

### D25 — two build-time flags from the research

1. **Scope the stdout burn-down NOW.** `sys.stdout`/`sys.stderr` spans **23
   files** (126 refs). Turning `banned-api` on globally turns the gate red
   immediately. **Land on the new SDK package; `per-file-ignores` the 23 legacy
   modules; burn down separately.**
2. ⭐ **"Errors as enums" (R15) and pydantic validation want ONE meeting place.**
   The CLI's `level:2` records and `ValidationError`s from a moving schema are
   both *"the outside world surprised us"*. **One translation module owning
   both** — CLI record → enum, `ValidationError` → enum — keeps the generated
   models machine-owned and stops enum mapping leaking into codegen output.

⚠️ **Evidence bound stated by the agent:** ruff behaviour, Python 3.14 behaviour
and package recency were **measured directly**; the structlog/loguru/anyio
**design** claims come from reading source and docs, **not benchmarked in our
stack**. If the queue design turns out to matter, **measure it in place**.

### ✅ D26 — msgspec VINDICATED by execution. My counter-argument was FALSE.

⚠️ **CORRECTION — the "new binary dependency" objection I used against Ray's
choice does not survive contact with reality:**

```
pydantic_core  compiled extensions: ['_pydantic_core.cpython-314-darwin.so']
msgspec        compiled extensions: ['_core.cpython-314-darwin.so']
```

**pydantic v2 ALREADY ships a compiled Rust core.** Both are compiled; both have
broad wheel coverage. **"Avoid a binary dep" never distinguished them**, so my
D22-challenge consistency argument was wrong. (The D19 argument against binary
*logging cores* still stands — but on **maintenance** grounds, not "binary".)

⚠️ **Second correction, to my own protobuf reasoning:**
`--input-file-type protobuf` means the generator can **READ a `.proto` as a
schema** to emit Python models — **not** that generated models speak protobuf on
the wire. Different axes. And the devcontainer spec **is JSON Schema**, so the
input is *fixed*; **`--output-model-type` is the only real lever**, which is
exactly why Ray's constraint lands on the model target.

**Measured end-to-end on a real draft-2019-09 schema (rc=0 both targets):**

- ⭐ **Dual codec CONFIRMED BY RUNNING IT** — one Struct, both encoders:
  `json 53 bytes` / `msgpack 39 bytes` (**26% smaller**), msgpack round-trip
  returns the original. **Buy it for the OPTION, not the bytes** — nothing here
  is serialization-bound; the value is that a compact frame later is a one-line
  encoder swap on the same type, not a modelling project.
- ⭐ **msgspec DOES validate:** `"level": "NOT_AN_INT"` →
  `ValidationError: Expected int, got str - at $.level`. Its error carries a
  **JSON-pointer path natively** — *better* than pydantic for mapping onto R15
  error enums.
- ✅ **Union worry RETRACTED.** The `string|array|object` lifecycle union
  generates and decodes correctly in **both** targets. The caveat survives only
  for unions **of Structs**, which need a discriminator
  (`model/msgspec.py:121`, `REQUIRES_TAGGED_UNION_DISCRIMINATOR = True`) — our
  `{"type": …}` field is a natural one if we ever model log records that way.

### ⚠️ D27 — REAL DEFECT: msgspec output silently DROPS schema strictness

`unevaluatedProperties: false` → pydantic emits `ConfigDict(extra='forbid')`;
**msgspec emits nothing.** Runtime: pydantic **REJECTS** an unknown field,
msgspec **ACCEPTS** it. All three recovery levers fail
(`unevaluatedProperties`, `additionalProperties`, **`--extra-fields forbid`**).

**Attribution control arm:** `--extra-fields forbid` on a schema with *no*
strictness keyword still produced `extra='forbid'` for pydantic ⇒ **the flag
works and is silently ignored for msgspec output.** Not a msgspec limitation
either — `msgspec.Struct(forbid_unknown_fields=True)` works, and the generator
even *has* the mapping at `model/msgspec.py:127`. It just isn't reached.
**Worth an upstream issue.**

⭐ **THE TWIST — this may flip in our favour.** Our schema is **unversioned and
moving**. Under `extra='forbid'`, **every field the devcontainer spec adds
upstream breaks the SDK at runtime** — a strict model against a moving schema is
a *scheduled outage*. So msgspec's lenient default is arguably what we want, and
pydantic's inherited `forbid` is the liability we would deliberately override.

⇒ **DECIDE strictness explicitly (`extra-fields = "ignore"`), never inherit
whatever the target happens to emit.**

### ⚠️ D28 — `--preset` is NOT a reproducibility pin; it changes the PUBLIC API

Measured diff, plain vs `--preset practical-py314-20260619`:

```diff
-    forwardPorts: list[int | str] | UnsetType = UNSET
+    forward_ports: list[int | str] | UnsetType = field(name='forwardPorts', default=UNSET)
-from __future__ import annotations
```

It **renames every field to snake_case** with wire aliases and drops the
`__future__` import. That is a change to our generated models' **public API**.
Presets are immutable and date-stamped, so they pin *style* — not the generator.

**Three levers, three jobs:**

| Lever | Pins |
|---|---|
| **`uv add --dev datamodel-code-generator==0.72.2`** | the generator — **the primary reproducibility control** |
| `--disable-timestamp` | removes the header; without it `--check` can **only fail** |
| `--preset practical-py314-…` | generated **style/naming** only — decide snake_case on API grounds |

⚠️ **REPRODUCIBILITY LANDMINE, emitted on every run:**
`FutureWarning: The default external formatters (black, isort) will become
opt-in in a future version.` On the version bump that flips it, **every
generated file reformats and `--check` goes red repo-wide** for no semantic
reason. **Set `formatters` explicitly NOW.**

✅ **`--check` both arms verified:** in-sync → **rc=0**; after a hand-edit →
**rc=1**. The gate discriminates.

**Recommended config:**

```toml
[tool.datamodel-codegen]
input = "schemas/devcontainer.json"
input-file-type = "jsonschema"
output = "python/src/<sdk>/_models.py"
output-model-type = "msgspec.Struct"
disable-timestamp = true
formatters = ["black", "isort"]   # freeze the CHANGING default
extra-fields = "ignore"            # DECIDE it, don't inherit it
```

⚠️ **`UNSET` vs `None` ergonomics:** msgspec emits `str | UnsetType = UNSET`,
distinguishing **absent** from **explicit null** — more correct for a moving
schema, but `UnsetType` **leaks into our public type signatures** and consumers
would write `if rec.image is not UNSET`. **Normalize at the adapter boundary;
do not export `UNSET` to callers.**

### ✅ D29 — Settings: **no adoptable msgspec-native library exists**

Control-armed (`zzqq-absent-control-a1b2c3` → 404, `requests` → 200):

| | `msgspec-settings` | `msgspec-config` | `pydantic-settings` |
|---|---|---|---|
| **Total commits** | **1** | 20 | — |
| Stars | **1** | **0** | — |
| **Downloads/month** | **16** | 32 | **455,058,300** |
| Extra deps | msgspec | msgspec + pyyaml + **rich + rich-click** | — |

Both are *real* libraries (READMEs read, not dismissed on stars) — and neither
clears a bus-factor bar for something other repos import. **~28-million-fold
download gap.** ⇒ **Option (b) is OUT.**

Also 404: `msgspec-env`, `msgspec-configs`, `msgspec-toolbelt`, `pyconfz`.
Mature-but-**not-msgspec-compatible**: `typed-settings` (attrs/cattrs/pydantic
only), `environs` (marshmallow), `dynaconf`, `goodconf`, `environ-config`,
`everett`, `confz`, `python-decouple`.

**msgspec has NO env/config API** — full top-level enumeration on 0.21.1, with a
known-present control (`convert`, `inspect`, `structs`, `to_builtins`) proving
the enumeration works. But it ships the primitives: `convert(..., strict=False)`,
`structs.fields()`, plus `toml`/`yaml` codecs.

### D30 — the hand-roll: **BUILT AND MEASURED at 22 lines**

Not estimated — run against a faithful port of the real `config.py`. Every field
correct: prefixes, nesting, defaults preserved when unset, `str→int`, `str→bool`,
`Path` via `dec_hook`. **Failure arm armed:** `DOTFILES_SSH_PORT=not_a_port` →
`ValidationError`.

**Measured LOSSES vs `pydantic-settings`:**

| Feature | pydantic-settings | 22-line loader |
|---|---|---|
| **Case-insensitive env names** | ✅ | ❌ **latent** — all our vars (`MISE_*`, `DOTFILES_*`, `DEVCONTAINER`) are uppercase, so **not a live regression** |
| Nested delimiter `X__Y` | ✅ | ❌ unused here |
| `.env` / secrets dir | ✅ | ❌ unused here |
| **Error names the FIELD** | ✅ | ❌ **REAL regression** — `Expected int, got str` with no field name. **~3 lines to fix. Do not ship without it.** |

### 🆕 The sharpest framing — `pydantic-settings` ships **14 sources**; we use **ONE**

Enumerated, not recalled:

```
EnvSettingsSource · DotEnvSettingsSource · SecretsSettingsSource · NestedSecretsSettingsSource
CliSettingsSource · InitSettingsSource
JsonConfigSettingsSource · TomlConfigSettingsSource · YamlConfigSettingsSource · PyprojectTomlConfigSettingsSource
AWSSecretsManagerSettingsSource · AzureKeyVaultSettingsSource · GoogleSecretManagerSettingsSource
```

**`config.py` uses exactly one — `EnvSettingsSource`.** ⇒ **The trade is: give up
13 sources we don't use, to keep the 1 we do.**

⭐ **TOML/YAML stay cheap to add later** — msgspec ships `msgspec.toml` and
`msgspec.yaml`, so a file source becomes decode → merge → `convert`, not a rebuild.

🆕 **`starlette.config` probed and RULED OUT on capability, not maintenance:**
`Config(env_file, environ, env_prefix, encoding)` with **`get` as its only public
method** — a **per-key getter** (`config('DEBUG', cast=bool, default=False)`),
**no nesting, no Struct binding**. It would mean hand-writing every field.

⭐ **The prize for (c):** it drops **`pydantic` AND `pydantic-settings` from the
SDK's dependency tree entirely** — two fewer transitive deps for every R6
consumer. And the migration is **source-compatible**: `audit.py`/`docker.py` take
`DotfilesConfig` by DI and use attribute access, identical on a Struct. Only
`config.py` + `tests/test_config.py` change.

⚠️ **The honest case for (a), which Ray must hear:** the drift risk R19 guards
against is a property of **serialization models** — two schemas describing one
wire format, diverging. **`config.py` is not that.** It is a process-boundary env
reader that never serializes anything: no schema, no wire format, **nothing to
drift**. Under that reading, keeping `pydantic-settings` for settings only costs
one dependency and *zero* drift risk, and it is battle-tested where 22 fresh
lines are not.

**(a) is enforceable with the SAME D18 mechanism — no new tooling:**

```toml
[lint.flake8-tidy-imports.banned-api]
"pydantic.BaseModel" = { msg = "models are codegen'd msgspec Structs" }
[lint.per-file-ignores]
"python/src/dotfiles_setup/config.py" = ["TID251"]   # settings only
```

### ⚠️ D31 — msgspec has NO `pathlib.Path` support. Reaches BEYOND settings.

```
json decode {"p":"/a/b"} -> ValidationError: Expected `Path`, got `str`
json encode S(Path(...)) -> TypeError: Encoding objects of type PosixPath is unsupported
convert("/x", Path, strict=False)                 -> ValidationError   ← control
convert("/x", Path, strict=False, dec_hook=hook)  -> PosixPath('/x')   ← rescued
```

**Both directions fail natively.** pydantic handles `Path` out of the box;
msgspec needs a **`dec_hook` AND an `enc_hook`**, and **those are NOT global —
they must be threaded through every encode/decode call site.** `config.py` uses
`Path` on **three** fields.

⭐ **Generalises to the whole SDK:** the same tax applies to `datetime`,
`Decimal`, and any custom scalar. Codegen emits `str` for JSON-Schema strings so
generated models are fine as-is — but the moment an adapter promotes `str → Path`
or adds a custom type, we own hook management across the SDK.

⇒ **Centralise `dec_hook`/`enc_hook` in ONE module from day one and route every
codec call through it.** Retrofitting is the ugly version. This is a genuine
ergonomic cost of msgspec-universal that must be adopted knowingly — it does not
reverse Ray's ruling, but he should have it.

### ✅ D32 — Agent SDK structured outputs: **NO CONFLICT with msgspec**

Ray asked whether the msgspec ruling conflicts with
`agent-harness-docs/docs/claude-code/agent-sdk__structured-outputs.md`
(step-00 offline corpus — read directly, not delegated).

**Measured, two arms:**

1. **This project does NOT use the Agent SDK.** `claude_agent_sdk` /
   `output_format` / `structured_output` → **0 hits** in `python/`; no dependency
   declared. Control arm: 37 files mention `subprocess`. **The question is
   hypothetical today.**
2. **If it did, msgspec works.** The SDK contract is
   `output_format={"type":"json_schema","schema": <plain JSON Schema dict>}`.
   Pydantic's `.model_json_schema()` is a **convenience for producing that
   dict**, not a requirement. msgspec's equivalent is **`msgspec.json.schema()`**,
   which emits `$ref` + `$defs` + plain types — and the doc explicitly lists
   `$ref` definitions among supported features.

⭐ **The draft-version trap does NOT bite msgspec.** The doc: the SDK validates
against **draft-07** and *"schemas that declare a newer version are rejected"* —
which is why **Zod** needs `target: "draft-7"` (it defaults to 2020-12).

**Probed: `msgspec.json.schema()` emits NO `$schema` key** (`declares $schema?
False`). **There is no version declaration to reject.**

⚠️ **Honest nuance, untested:** `$defs` is draft-2019-09+ terminology (draft-07
used `definitions`). Not verified against the SDK's validator. **But pydantic v2
emits `$defs` too**, so both libraries are in the identical position — msgspec is
not worse.

⇒ **Does not constrain the `config.py` decision.** Producing a schema for an
*agent's output* is a third axis, distinct from the devcontainer models and from
the env-var settings reader. **Q16 stands, unblocked.**

### ✅ D33 — `config.py`: **hand-roll the 22-line msgspec loader. Fully universal.** ✅

Ray's call. `pydantic` and `pydantic-settings` leave the dependency tree
entirely — the real prize for every R6 consumer.

**Ship conditions (non-negotiable):**

1. ⚠️ **Add the field name to the error before shipping.** ~3 lines (catch,
   re-raise with `f.name`). Without it a misconfigured env var reports
   `Expected int, got str` with no clue which variable — a real diagnostic
   regression against `pydantic-settings`, which names `ssh_port`.
2. ⚠️ **Centralise `dec_hook`/`enc_hook` in ONE module** (D31) and route every
   codec call through it. `config.py` uses `Path` on three fields, msgspec
   supports `Path` in **neither** direction, and the hooks are **per-call, not
   global**. Retrofitting this across the SDK later is the ugly version.
3. **Write the `use-tool-builtins` justification in the commit body** — the rule
   demands *research then justification*, and the research came back genuinely
   empty (two msgspec-native libs at 1 and 20 total commits; nine mature
   alternatives none of which bind msgspec Structs; msgspec has no env API).
4. **Accepted, latent:** case-insensitive env names go away. Every var in use
   (`MISE_*`, `DOTFILES_*`, `DEVCONTAINER`, `SSH_AUTH_SOCK`, `EXPECTED_*`) is
   uppercase, so this is a behaviour change, **not a live regression**.

**Blast radius measured:** only `config.py` and `tests/test_config.py` change —
`audit.py`/`docker.py` take `DotfilesConfig` by DI and use attribute access,
identical on a Struct. **22 lines replace 60: a net reduction.**

---

## ✅ Promoted to `docs/specs/` — tracked, survives a clone

Done 2026-08-08 on Ray's instruction (Q17). The working copy remains at
`.agent/requirements-devcontainer-gcc162.md`; **this tracked file is
authoritative.** If they diverge, this one wins.

Rationale, per [[agent-artifact-conventions]]: *"Anything that should survive a
clone is tracked… Promoting is the default for anything a future session will
cite."* R4 hands this to a `/goal` session, which will cite it constantly.

### NEW — two side findings worth tickets

- ⚠️ **`shutdownAction` is UNSET in our `devcontainer.json`** (spec default
  `stopContainer`). It is a **declarative, non-docker** stop mechanism we are
  not using. Fires on tool-disconnect, so it does not replace `mise run stop`,
  but it is real and currently left on default.
- ⚠️ **Guard false positive:** the PreToolUse guard denied
  `devcontainer up --help`, matching `devcontainer up` regardless of `--help`.
  Same class as #265. Narrow the pattern.

### OPEN — verify before Q3

- Can `devcontainer.json` interpolate `${localEnv:…}` inside `build.options`?
  It is JSON and cannot compute host arch. If not, the selector needs a
  different mechanism there (the task can template the file, or pass
  `--build-arg`).

## Named source paths (Ray-supplied — verify each exists before citing)

| Topic | Path |
|---|---|
| mise root | `~/dev/github/ray-manaloto/knowledge-base/sources/mise` |
| mise bootstrap | `…/mise/docs/bootstrap`, `…/mise/docs/cli/bootstrap` |
| mise OCI | `…/mise/docs/dev-tools/mise-oci.md`, `…/mise/docs/cli/oci.md` |
| mise brew backend | `…/mise/docs/bootstrap/packages/brew.md` |
| mise conda backend | `…/mise/docs/dev-tools/backends/conda.md` |
| Claude Code `/goal` | `…/sources/agent-harness-docs/docs/claude-code/goal.md` |
| Claude Code memory (R10.2) | `…/sources/agent-harness-docs/docs/claude-code/memory.md` |
| Claude Code hooks (R10.2) | `…/sources/agent-harness-docs/docs/claude-code/hooks.md` |

### R9 lifecycle sources — Ray-supplied, ALL must be read (do not guess)

1. <https://containers.dev/implementors/json_reference/#lifecycle-scripts> — **spec, normative**
2. <https://containers.dev/implementors/spec/#lifecycle> — **spec, normative**
3. <https://oneuptime.com/blog/post/2026-01-25-dev-containers-team-development/view#lifecycle-scripts>
4. <https://tenthirtyam.org/dispatches/2026/07/01/development-containers-consistent-environments-for-every-contributor/#lifecycle-hooks>
5. <https://blog.projectasuras.com/DevContainers/3>
6. <https://fabiorehm.com/blog/2025/11/11/devpod-ssh-devcontainers/> — devpod + SSH, relevant to R1/R2
7. <https://docs.docker.com/compose/how-tos/lifecycle/> — compose lifecycle (different model; compare, don't conflate)

⚠️ 1 and 2 are the **normative spec**; 3–6 are blog posts and 7 is a *different
product's* lifecycle. Where they disagree, **the spec wins** — and say so in the
document rather than averaging them.
| Claude Code workflows | `…/sources/agent-harness-docs/docs/claude-code/workflows.md` |
| Claude Code commands | `…/sources/agent-harness-docs/docs/claude-code/commands.md` |
| conda-forge gcc | <https://anaconda.org/channels/conda-forge/packages/gcc/overview> |

## Existing repo context this must not fight

- **#243** — *"Add GCC 16.1 (latest stable release) to the devcontainer image"*,
  open and **unlabelled**, sitting in the triage backlog. This request
  **supersedes and extends** it. Link them; do not open a duplicate.
- **R3 amd64 invariant** — `AGENTS.md` currently makes `x86_64/amd64` a
  **success criterion** gated by `mise run verify-arch`. Per **R2.1** the
  contract becomes *"the arch you asked for is the arch you got"*, over a set of
  **two**, rather than a single hard-coded `x86_64`. ⚠️ Highest-risk part of the
  whole ask. Everything below encodes the single-arch assumption and must be
  re-examined:
  - `mise run verify-arch` — asserts literal `x86_64`
  - smoke **tier-1 image identity** — one expected config hash, now one per arch
  - `DOCKER_DEFAULT_PLATFORM=linux/amd64/v2` — a global default, now a per-run choice
  - `docker-bake.hcl` targets, and the `:dev` tag — **one tag cannot name two
    arches** unless it becomes a multi-arch manifest list
  - **volume names** (C10/C11/C12) — an arm64 and an amd64 container sharing one
    home volume would cross-contaminate installed binaries. **Likely needs an
    arch-scoped volume name; this is a real, concrete failure mode, not theory.**
  - `mise-system.lock` / `mise-runtime.lock` — **platform coverage per arch**;
    `mise_lock_integrity` already guards truncation, and `lock-image` currently
    "routes to amd64" (#650)
- **do-not.md #2** — base images are **CI-only**; never build locally.
- **P2996-CACHE.md** — the existing cache tier R1.2 is asked to imitate. Read it
  before designing anything new.
