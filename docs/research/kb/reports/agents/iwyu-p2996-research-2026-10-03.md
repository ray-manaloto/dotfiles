# Does clang-p2996 need its own IWYU build? — primary-source research (2026-10-03, lane llvm23)

Ray's question (relayed by the coordinator): *"did you research if we need a special iwyu build for the p2996 llvm
compiler and its tools?"* The earlier answer (sweep `iwyu-prebuilt-llvm23-sweep-2026-10-03.md`, item 5) was an
INFERENCE from IWYU's README. This report replaces it with primary-source probes, each with a control arm.

Probes ran 2026-10-03 from the Mac host via `gh api` and raw.githubusercontent.com. Scripts:
`/Users/rmanaloto/.claude/jobs/6fae0fec/tmp/p2996probe{,2,3,4,5,6}.sh`. No container and no build was run, so every
behavioural claim below is from SOURCE, not execution (see "What is still unverified").

## Answer

**Yes. Analysing p2996 code needs an IWYU built against the p2996 install, specifically IWYU's `clang_21` branch.**
A stock IWYU cannot do it today, and an IWYU built on upstream LLVM 23 can do only part of it.

1. **p2996's base is LLVM 21.0.0git, an upstream `main` snapshot of 2025-07-02.**
   - At our pinned SHA `f17c8d6c7bfef5e02ccadcf33517fd2a53b51b6e` (`docker-bake.hcl:101-103`, which is also the
     current `p2996` branch head, 2026-09-24), `cmake/Modules/LLVMVersion.cmake` sets
     `LLVM_VERSION_MAJOR 21`, `MINOR 0`, `PATCH 0`. Control: the same file on `llvm/llvm-project` `release/22.x` → 22.
   - `compare main...bloomberg:clang-p2996:f17c8d6c` → merge-base `b1774222c761` (2025-07-02T15:15Z), ahead 442,
     behind 57,269. LLVM cut `release/21.x` from main on 2025-07-15 (merge-base `94b15a1ece37`). So p2996 sits 13 days
     before the 21 branch point.
   - It is stuck there. Fork issue #248 (2025-12-24): merging upstream `91cdd350` ("Improve nested name specifier AST
     representation") "is one of the major obstacles blocking us from clang 22".

2. **IWYU's `clang_21` branch matches that base.**
   - `compare <master@2025-07-03>...clang_21` → `clang_21` = master `6905bb9eb9bd` (2025-06-26) **+ 10 commits**, head
     `791e69ea4662` (2025-08-30).
   - IWYU master has **0** "clang compat" commits between 2025-07-03 and 2025-08-15. That is the window between
     p2996's base and the clang_21 branch, so IWYU needed no Clang-API adaptation across it.
   - IWYU's CMake is the same on every branch: `find_package(LLVM CONFIG REQUIRED)` + `find_package(Clang CONFIG
     REQUIRED)` (`CMakeLists.txt:19-20` on `clang_21`, `clang_23` and `master`). It builds against whatever
     `LLVMConfig`/`ClangConfig` it is pointed at.
   - IWYU's README: it "makes heavy use of Clang internals", and its version table pairs each Clang major with one
     `clang_N` branch. An IWYU from another branch is not expected to compile against p2996's Clang-21-era API.

3. **The conda IWYU we ship today (0.26, linked to libllvm22) cannot parse ANY reflection code.**
   - Upstream `release/22.x` has no `defm reflection` option, no `caretcaret` (`^^`) token and no `CXXReflectExpr` node.
     Control: `sized-deallocation` is present on every ref probed.

4. **An IWYU built on upstream LLVM 23 (our planned option (b)) understands only a SUBSET of p2996 code.**
   - `release/23.x` and `main` have `defm reflection : BoolFOption<"reflection", … "Enable C++26 reflection">`, the `^^`
     token, `CXXReflectExpr`, and expansion statements (`CXXExpansionStmtPattern`, i.e. `template for`). Upstream
     PR #164692 "[clang]: reflection operator parsing for primitive types" merged 2026-02-06.
   - Upstream 23.x and main have **no splice support**: 0 splice tokens, 0 `Splice` stmt nodes. p2996 has 4 and 2.
   - They have **no libc++ `<meta>` header**: `libcxx/include/meta` → 404 on 23.x and main, 200 at the p2996 SHA.
     Nearly all P2996 code `#include <meta>` and uses splices (`[: … :]`).
   - Upstream has **none of p2996's extra driver flags**: `-freflection-latest` (0 on main vs 1 on p2996),
     `-fexpansion-statements` (0 vs 1), and the parameter/attribute/entity-proxy reflection options.
   - Our image smoke (`.devcontainer/Dockerfile` ~:529-541) compiles reflection code with
     `-freflection -freflection-latest -fexpansion-statements`. An upstream-linked IWYU would reject those
     `compile_commands.json` entries as unknown arguments before it parsed any code.

5. **Our p2996 install already contains what an IWYU build links against (from source; the image itself was not
   inspected).**
   - The p2996 build runs a plain `ninja install` (`.devcontainer/Dockerfile` ~:510-528) into `/opt/clang-p2996`.
   - p2996's `llvm/CMakeLists.txt:390` defaults `LLVM_INSTALL_TOOLCHAIN_ONLY` to `OFF`, so libraries and CMake package
     files are installed (`:1421`), and `clang/cmake/modules/CMakeLists.txt` generates `ClangConfig.cmake`.
   - So `cmake -DCMAKE_PREFIX_PATH=/opt/clang-p2996` (or `-DIWYU_LLVM_ROOT_PATH=/opt/clang-p2996`) should resolve.

6. **No one has published this combination.**
   - IWYU's tracker has **0** issues or PRs matching `p2996` or `freflection`. Control: `clang_22` → 8. The 4
     "reflection" hits are unrelated (`__PRETTY_FUNCTION__`, MemberPointerType…).
   - The fork's tracker shows downstream Clang tools DO break on p2996 code. #275 (open, 2026-04-13): "My code compiles
     but clangd crashes" (`clangd version 21.0.0git (…clang-p2996…)`). #104 (closed): "clangd sometimes crashes parsing a
     spliced expand statement". Those tools were built FROM the fork, which is the configuration a p2996 IWYU would be
     in. Expect IWYU crashes on some reflection TUs too.

## Implications for option (b) (Ray, 2026-10-03: build IWYU from a pinned SHA in a content-hashed stage)

| Toolchain | IWYU branch | Links against | Parses p2996 code? |
|---|---|---|---|
| apt LLVM 22 (today) | `clang_22` | `/usr/lib/llvm-22` | No (no `^^`, no splices, no `<meta>`) |
| apt LLVM 23 (after the swap) | `clang_23` | `/usr/lib/llvm-23` | Partially (`^^`, `template for`). NOT splices or `<meta>`. Rejects `-freflection-latest`/`-fexpansion-statements` |
| clang-p2996 (`/opt/clang-p2996`) | `clang_21` (derived from p2996's `LLVM_VERSION_MAJOR`) | `/opt/clang-p2996` | Yes. That is the only configuration that can, with clangd-style crash risk (fork #275, #104) |

So if reflection TUs are to be analysed at all, (b) needs TWO IWYU builds. Both derive their branch from the
toolchain's own major, so no number is hardcoded. The alternative is to exclude reflection TUs from IWYU, which is
#1588's option (a).

## What is still unverified (needs a SLOT: build + run)

- That IWYU `clang_21` actually COMPILES against `/opt/clang-p2996`. p2996 adds AST nodes (`CXXSpliceExpr`, … in
  `StmtNodes.td`), and IWYU's RecursiveASTVisitor is instantiated against those headers. It should compile and
  traverse them generically, but that is unproven.
- That the result runs cleanly on a reflection TU (the image smoke's `#include <meta>` file), and that its include
  suggestions are sane for splice and `^^` uses.
- That `/opt/clang-p2996` really contains `lib/cmake/clang/ClangConfig.cmake` in the exported image. A one-line
  `ls` in the image settles it.

## GitHub repos touched

- [bloomberg/clang-p2996](https://github.com/bloomberg/clang-p2996) — LLVMVersion.cmake at the pinned SHA, Options.td, TokenKinds.def, StmtNodes.td, libcxx/include/meta, llvm/CMakeLists.txt, clang/cmake/modules, issues #248 #275 #104
- [llvm/llvm-project](https://github.com/llvm/llvm-project) — LLVMVersion.cmake on release/22.x, Options.td / TokenKinds.def / StmtNodes.td on release/22.x, release/23.x and main, compare merge-bases, PR #164692
- [include-what-you-use/include-what-you-use](https://github.com/include-what-you-use/include-what-you-use) — CMakeLists.txt on clang_21, clang_23 and master; branch list; master commit history 2025-06/08; issue search
