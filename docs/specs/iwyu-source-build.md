# Spec — IWYU built from source in content-hashed stages, incl. a p2996-linked IWYU

> **RULED (Ray, 2026-10-03, relayed by coordinator dotfiles-20261003T113006.726261000-05.coordinator): all four §0
> recommendations ACCEPTED.**
> - Q1: build the p2996-linked IWYU (`clang_21`, against `/opt/clang-p2996`, in its own step in the p2996-hash section;
>   branch derived from `LLVMVersion.cmake`; fail loud on mismatch).
> - Q2: the apt-linked IWYU at `/opt/iwyu/bin` goes first on PATH; the p2996 one is used by full path.
> - Q3: retire the conda IWYU and fix2's conda pin/lock parity in that PR; readiness = `gh api branches/clang_<M>` 200.
> - Q4: a SEPARATE PR after the detector PR, which keeps its conda gate until then.
>
> Next: the SLOT-gated configure-only cmake probe on the published `:p2996-<hash>` export (§5.2, queued by the
> coordinator), then §6/§7 and a premise-verifier pass before dispatch.

Ruling: Ray, 2026-10-03, IWYU option (b): "build IWYU from source, from a pinned clang_23 SHA, in a
content-hashed image stage". Then: "did you research if we need a special iwyu build for the p2996 llvm compiler and
its tools?" Research: `docs/research/kb/reports/agents/iwyu-p2996-research-2026-10-03.md` (primary-source).
Prior sweep: `iwyu-prebuilt-llvm23-sweep-2026-10-03.md`. Lane llvm23. Not dispatchable until the design questions in §0
are ruled; then it gets a premise-verifier pass.

## 0. Design questions for Ray (each with a recommendation)

1. **p2996 IWYU: build it, or exclude reflection TUs (#1588)?** RECOMMEND: build it. Research: only an IWYU linked
   against `/opt/clang-p2996` can parse p2996 code (splices, `<meta>`, `-freflection-latest`). An apt-LLVM-23 IWYU
   handles only `^^` and `template for`, and upstream has no splices or `<meta>`. Cost: a few minutes inside the ~2h
   p2996 cold build, and its IWYU SHA becomes a p2996-hash input. Risk: fork-built Clang tools crash on some reflection
   code (fork #275, #104 for clangd).
2. **Which IWYU is `include-what-you-use` on PATH?** RECOMMEND: the apt-LLVM one, at `/opt/iwyu/bin`, prepended via
   mise `_.path` beside `/usr/lib/llvm-<P>/bin`. That mirrors bare `clang++` resolving to apt LLVM (`image.py` ~:535-545).
   The p2996 one stays with its toolchain at `/opt/clang-p2996/bin/include-what-you-use`, reached by full path, like
   the p2996 `clang++`.
3. **Retire the conda IWYU and fix2's conda machinery?** RECOMMEND: yes, in the same PR (`tool-currency-and-native-first`
   rule 3: retire superseded code). Remove `"conda:include-what-you-use"` (`mise-system.toml:70`) and its lock entries
   (via `mise run lock-image`). Remove `llvm_major`'s conda IWYU pin/lock parity (`_IWYU_URL`, `iwyu_versions_for`,
   `iwyu_pin_for`, `iwyu_lock_state`, `_iwyu_pin_violations`, `_iwyu_lock_violations`, ~:35-36, :283-360, :588-623)
   and the IWYU-rewrite step in `plan_bump`.
4. **Ship order?** RECOMMEND: as its OWN PR after the llvm23 detector PR, because it touches the Dockerfile base and
   p2996 stages and needs two cold image builds. The detector PR ships as-is, with its conda IWYU gate (correct until
   this lands).

## 1. Objective

Make IWYU match the compiler it analyses, with no dependence on conda-forge release timing:
- **IWYU-apt**: IWYU branch `clang_<P>`, where P is the apt LLVM major from the pins, built against `/usr/lib/llvm-<P>`.
- **IWYU-p2996**: IWYU branch `clang_<N>`, where N is `LLVM_VERSION_MAJOR` of the p2996 source tree (21 today), built
  against `/opt/clang-p2996`.
Both are pinned to exact IWYU commit SHAs, and both are content-hashed: IWYU-apt lives in the base-hash section,
IWYU-p2996 in the p2996-hash section. No LLVM major is hardcoded outside parity-checked sites.

## 2. Files (expected)

- `.devcontainer/Dockerfile`:
  - a new stage `iwyu-apt-builder` inside `BASE_HASH_BEGIN…END` (after the apt LLVM install, ~:212), which installs
    to `/opt/iwyu` and is COPYd into `devcontainer-base`;
  - a build step in `clang-builder-cold` after `ninja install` (~:528), inside `P2996_HASH_BEGIN…END`, which installs
    into `/opt/clang-p2996` so `p2996-export` carries it unchanged.
- `docker-bake.hcl`: two single-literal variables, `IWYU_APT_REF` and `IWYU_P2996_REF` (40-hex SHAs), plus
  `IWYU_APT_BRANCH = "clang_<P>"` and `IWYU_P2996_BRANCH = "clang_<N>"`. Precedent: `CLANG_P2996_REF`
  (`docker-bake.hcl:101-103`, the single-literal rule, `tests/test_p2996_single_literal.py`).
- `renovate.json`: two git-refs customManagers that bump the SHAs on their branch, each with its own packageRule.
  Precedent: clang-p2996 (`renovate.json` ~:130, ~:176-185).
- `python/src/dotfiles_setup/p2996_hash.py` / base hash: confirm the new ARGs and bake variables are hash inputs
  (`feedback_content_hash_must_cover_copy_inputs`).
- `python/src/dotfiles_setup/llvm_major.py`:
  - `iwyu_ready(M)` → `gh api repos/include-what-you-use/include-what-you-use/branches/clang_<M>` returns 200 (404 →
    False; other statuses raise);
  - parity: `IWYU_APT_BRANCH == clang_<P>`;
  - `plan_bump(T)` rewrites `IWYU_APT_BRANCH` and resolves `IWYU_APT_REF` to that branch's head SHA;
  - retire the conda pieces (§0.3).
- `.devcontainer/mise-system.toml`: drop the conda IWYU; `_.path` gains `/opt/iwyu/bin`.
- `python/src/dotfiles_setup/image.py` smoke: both binaries present; each runs `--version`, which reports its own Clang
  major; IWYU-p2996 is run on the existing reflection probe TU (`#include <meta>`, p2996 flags) and must not exit with a
  parse error.
- Tests: the matching unit tests, the single-literal tests for the new bake variables, `EXPECTED_JOBS` unchanged.

## 3. Required behaviour

- **IWYU-p2996 branch derivation (no literal trust):** the Dockerfile reads `LLVM_VERSION_MAJOR` from
  `/build/clang-p2996/cmake/Modules/LLVMVersion.cmake` and FAILS LOUD unless `IWYU_P2996_BRANCH == clang_<that>`.
  A p2996 rebase onto LLVM 22 then forces a visible IWYU branch bump instead of a confusing compile error.
- **IWYU-apt branch derivation:** the Dockerfile asserts `IWYU_APT_BRANCH == clang_${LLVM_MAJOR}`, the existing ARG.
- Each IWYU stage runs `git fetch --depth 1 origin <REF>`, checks that `git merge-base --is-ancestor <REF>
  origin/<BRANCH>` holds (the SHA is on the claimed branch), then builds with `cmake -G Ninja
  -DCMAKE_PREFIX_PATH=<llvm root>` and installs to its prefix. `IWYU_RESOURCE_RELATIVE_TO=clang` (the default), so each
  binary finds its own Clang's builtin headers.
- Build-time self-check in the same RUN (`feedback_build_time_self_check`): `<prefix>/bin/include-what-you-use
  --version` prints the expected Clang major. For p2996, also run the reflection TU.
- Renovate: each IWYU SHA bumps within its branch. A branch change (`clang_22` → `clang_23`) comes only from
  `llvm-bump`, or a p2996 major change, both of which are gated.

## 4. Constraints

- CI builds only (`do-not.md` #2). Local verification uses SLOT-granted container probes only.
- No new `.sh`; logic stays in Dockerfile RUN chains (existing pattern) plus python for parity and detection.
- The p2996 IWYU build must not lengthen the warm path: it sits inside the p2996-hash section, so it only reruns on a
  p2996 or IWYU-p2996 SHA change.

## 5. Verification (sketch; finalised after the ruling)

1. Static: lint, pytest, verify, pin-parity, single-literal tests, renovate-validate.
2. A SLOT-granted throwaway container on the published `:p2996-<hash>` export: confirm
   `/opt/clang-p2996/lib/cmake/clang/ClangConfig.cmake` exists, then configure-only `cmake` of IWYU `clang_21` against
   it. That is the cheap control arm for "compiles against p2996", before spending a CI cold build.
3. CI: both cold builds green, plus the smoke (both `--version` checks and the p2996 reflection TU).

## 6. Commit / 7. PREMISES

Written after the ruling. The research report's probe results are the premise table seed.
