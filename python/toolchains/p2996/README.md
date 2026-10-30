# clang-p2996 (C++26 reflection) for arm64 macOS

A uv Python package (`src/p2996/`, DL-758) run through this folder's mise tasks; layout DL-755.
From the repository root the tasks are `//p2996:<task>` (a `[monorepo.path_aliases]` entry):

```sh
mise run //p2996:source      # newest commit of P2996_BRANCH (or --commit <sha>), patches applied (idempotent)
mise run //p2996:build       # hours; a rerun resumes the build dir. --dry-run prints the cmake commands
mise run //p2996:review-log -- <log>  # read-only Codex team reports warnings, errors, skipped parts
mise run //p2996:install     # ROOT/<commit>, ROOT/bin links, default .cfg files
mise run //p2996:verify      # compile and run src/p2996/reflection.cpp with clang++-p2996
mise doctor project          # (in this folder) SDK, cmake, ninja, SWIG, Lua, doxygen, ocamlfind, venv, codex
```

Development: `mise run //p2996:check` runs `lint` (ruff check, ruff format --check, ty, and
`models.py` matching the schema) and `test` (pytest, 100% line and branch coverage, real git, cmake,
ninja and Apple clang; stand-in executables only for clang++-p2996 and codex). `codegen` writes
`src/p2996/models.py` from `schema/p2996.schema.json`; `lock` re-resolves every dependency to its
latest release; `sync` installs the lock. uv runs only through these tasks.

## Settings

`mise.toml` `[env]` holds every value the package reads (the generated `Config`, field `<name>` from
`P2996_<NAME>`): `P2996_REMOTE`, `P2996_BRANCH`, `P2996_ROOT` (default `~/.local/share/p2996`;
prefix `ROOT/<commit>`, only `ROOT/bin` on PATH), `P2996_CACHE` (`~/.cache/dotfiles/p2996`, holding
`source` and `build`) and `P2996_LOCK` (the heavy-build gate the legacy `host_lock.py` uses; build
takes it without waiting, so one heavy build runs at a time).

## Source

Always the newest commit of `refs/heads/p2996` on `https://github.com/bloomberg/clang-p2996.git`
(`git ls-remote` on each `source` run), unless `--commit` names one; build and install read the
commit checked out in the cache, so a new upstream commit means a new prefix and a full rebuild.
Shallow fetch of that commit; a commit change force-checks-out over the previous patches.

## Patches (`src/p2996/patches/`, applied with `git apply --unidiff-zero`)

An already-applied patch is skipped; one that no longer applies stops `source` with its name, so
delete it (upstream fixed it) or rebase it.

- `sdk-rdf-comparator.patch`: the macOS 27 SDK libc++ that compiles LLVM rejects the stateful
  `std::less<RegisterRef>` specialization; RDF code gets a named `llvm::rdf::RegisterRefLess` (5 files).
- `sdk-float-math.patch`: clang's and libc++'s `float.h` answer a partial
  `__need_infinity_nan` include, which the macOS 27 SDK headers make (2 files).
- `asan-macos27-dyld.patch`: on macOS 27, ASan startup finds the dyld header through
  `TASK_DYLD_INFO` instead of shared-cache enumeration, which allocates too early.

## CMake

`src/p2996/bootstrap.cmake` is the initial cache (`-C`); `build` reconfigures on every run, so an edit
takes effect on the next build, and `clean` deletes the build folder (`--source` also the
checkout). Build passes the SDK (`xcrun --show-sdk-path`, resolved to the versioned SDK) as `P2996_SDK`, the Command Line Tools `clang`/`clang++` as the
bootstrap compilers, this project's venv python as `Python3_EXECUTABLE` and `ROOT/<commit>` as the configured prefix, and clears inherited
`CC CXX CFLAGS CXXFLAGS CPPFLAGS LDFLAGS SDKROOT`. Key values: Release, arm64, deployment target
27.0, `@loader_path/../lib` rpath; every LLVM project that builds on macOS (DL-756):
`clang;clang-tools-extra;lld;lldb;mlir;polly;bolt;flang`, runtimes
`libc;libunwind;libcxxabi;libcxx;compiler-rt;openmp;flang-rt` (libc is the Darwin overlay); targets
`AArch64;X86`; lldb uses Xcode's debugserver, with Python and Lua scripting; MLIR Python bindings and
LLVM's OCaml bindings on (DL-757). Every tool the build needs (SWIG, Lua, doxygen, opam switch `llvm`
with ocamlfind and ctypes) comes from the global mise config; the Python modules (pygments, pyyaml,
numpy, nanobind, pybind11, ml_dtypes, all uncapped) come from this project's uv lock. Assertions on; LLVM
and Clang dylibs; full install (headers and CMake exports, for IWYU); compile jobs 4, link and
tablegen jobs 1; tests, docs, examples and the iOS, watchOS, tvOS and visionOS runtimes off;
zlib, zstd, libxml2, libedit and the compiler-rt runtimes keep LLVM's defaults, whose own checks
skip Linux-only parts. Not built on macOS: libclc, offload, llvm-libgcc, cross-project-tests.
A Linux build needs its own cache with the Linux choices.
The runtimes and builtins sub-builds get the same platform values through `RUNTIMES_CMAKE_ARGS` and `BUILTINS_CMAKE_ARGS`. `CLANG_LINKS_TO_CREATE` is
`clang-p2996;clang++-p2996;clang-cpp-p2996`, so LLVM installs the suffixed driver names itself
(and no unsuffixed `clang++`, `clang-cl` or `clang-cpp`).

## Prefix layout

```text
ROOT/<commit>/                   cmake --install of build, runtimes/builtins-bins, runtimes/runtimes-bins
ROOT/<commit>/bin/arm64-apple-darwin.cfg           -isysroot <xcrun SDK>
ROOT/<commit>/bin/arm64-apple-darwin-clang++.cfg   @arm64-apple-darwin.cfg plus link-only
                              -L and -rpath ROOT/<commit>/lib and -lunwind
ROOT/bin/<tool>-p2996 -> ../<commit>/bin/<tool>     every other tool; skipped when LLVM made <tool>-p2996
ROOT/bin/*-p2996, *.cfg -> ../<commit>/bin/<same name>
```

Clang reads `<triple>.cfg`, then `arm64-apple-darwin<N>.cfg`, then `arm64-apple-darwin.cfg` from
its own resolved bin dir (`ROOT/<commit>/bin`), so only the unversioned names exist and a macOS
bump never shadows them.
