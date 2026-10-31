# clang-p2996 (C++26 reflection) for arm64 macOS

A uv Python package (`src/p2996/`, DL-758) run through this folder's mise tasks; layout DL-755.
From the repository root the tasks are `//p2996:<task>` (a `[monorepo.path_aliases]` entry):

```sh
mise run //p2996:source      # newest commit of P2996_BRANCH (or --commit <sha>), patches applied
mise run //p2996:build       # prepares source, then hours; a rerun resumes. --dry-run prints the cmake commands
mise run //p2996:review-log -- <log>  # read-only Codex team reports warnings, errors, skipped parts
mise run //p2996:install     # ROOT/<id>, verify, one rename to activate; default .cfg files
mise run //p2996:verify      # compile and run src/p2996/reflection.cpp with clang++-p2996
mise doctor project          # (in this folder) SDK, cmake, ninja, SWIG, Lua, doxygen, ocamlfind, venv, codex
```

Every step reports as JSON lines (structlog through stdlib handlers): info on stdout, errors on
stderr, exit 1 on failure; nothing prints. Child processes run through AnyIO. The stack is DL-762:

- `schema/p2996.schema.json` holds `Config`, the `Command` enum and one model per command;
  `codegen` writes them to `src/p2996/models.py` as frozen pydantic v2 models.
- `p2996 <command>` parses the rest of argv into that command's model with pydantic-settings
  `CliApp` (kebab-case flags, `--flag/--no-flag` booleans).
- Each task's `usage` spec in `mise.toml` is checked against its model by `tests/test_usage.py`: the
  real `usage explain` binds a full argv, bash expands the task's `run` line, and the CLI must parse
  every value into the model.

Development: `mise run //p2996:check` runs `lint` (ruff check, ruff format --check, ty, and
`models.py` matching the schema) and `test` (pytest with the AnyIO plugin, 100% line and branch
coverage, real git, cmake, ninja, mise, usage and Apple clang; stand-in executables only for
clang++-p2996 and codex). `lock` re-resolves every dependency to its latest release; `sync` installs
the lock. uv runs only through these tasks, with this folder's `.venv` (`_.python.venv`).

## Settings

`mise.toml` `[env]` holds every value the package reads (the generated `Config`, field `<name>` from
`P2996_<NAME>`): `P2996_REMOTE`, `P2996_BRANCH`, `P2996_ROOT` (default `~/.local/share/p2996`;
prefix `ROOT/<id>`, only `ROOT/bin` on PATH) and `P2996_CACHE` (`~/.cache/dotfiles/p2996`, holding
`source/<id>` and `build/<id>`). `<id>` is `<commit>-<recipe digest>`, the digest covering the patches,
`bootstrap.cmake`, `build.py` and the Python version. No lock: each id has its own folders; two runs of one id at once are not supported.

## Source

Always the newest commit of `refs/heads/p2996` on `https://github.com/bloomberg/clang-p2996.git`
(`git ls-remote` on each `source` run), unless `--commit` names one; build and install read the
tree of that commit, so a new upstream commit means a new prefix and a full rebuild. Shallow fetch
into a temporary folder, patches applied there, then one rename to `source/<id>`: a tree never
changes after that, and a commit whose patch failed has no tree. Any change to the recipe
means a new id, so a full rebuild and a normal install. A reinstall of the active id only rewrites the
`.cfg` files, which is the repair after an SDK move. `build/last` links to the newest
successful build, which is what install takes; `build/started` links to the newest build that began,
which is the source tree review-log names. Install verifies the new version, keeps the old one
as `ROOT/previous`, and swaps `ROOT/current` in one rename; `ROOT/bin`, `include`, `lib`, `libexec`
and `share` are fixed links through it.

## Patches (`src/p2996/patches/`, applied with `git apply --unidiff-zero`)

A patch that no longer applies stops `source` with its name, so
delete it (upstream fixed it) or rebase it.

- `sdk-rdf-comparator.patch`: the macOS 27 SDK libc++ that compiles LLVM rejects the stateful
  `std::less<RegisterRef>` specialization; RDF code gets a named `llvm::rdf::RegisterRefLess` (5 files).
- `sdk-float-math.patch`: clang's and libc++'s `float.h` answer a partial
  `__need_infinity_nan` include, which the macOS 27 SDK headers make (2 files).
- `asan-macos27-dyld.patch`: on macOS 27, ASan startup finds the dyld header through
  `TASK_DYLD_INFO` instead of shared-cache enumeration, which allocates too early.
- `lldb-base-specifier-derived.patch` (DL-759): P2996 replaced `CXXBaseSpecifier`'s base-of-class
  flag with the derived record, and lldb's `TypeSystemClang` no longer compiled; the specifier now
  starts without one and `TransferBaseClasses` sets it, as Sema does. Upstream PR
  bloomberg/clang-p2996#242 (closed unmerged) passed the base class instead.

## CMake

`src/p2996/bootstrap.cmake` is the initial cache (`-C`); an edit changes the id, so it takes effect
as a new build, and `clean` deletes the build folder (`--source` also the
checkout). Build passes the SDK (`xcrun --show-sdk-path`, resolved to the versioned SDK) as `P2996_SDK`, the Command Line Tools `clang`/`clang++` as the
bootstrap compilers, this project's venv python as `Python3_EXECUTABLE` and `ROOT/<id>` as the configured prefix, and clears inherited
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
`clang++;clang-cpp;clang-p2996;clang++-p2996;clang-cpp-p2996`: LLVM installs the suffixed driver
names itself, and keeps `clang++` and `clang-cpp` because the runtimes sub-build compiles with
`build/bin/clang++` (DL-760); `install` links only the `-p2996` names into `ROOT/bin`.

## Prefix layout

```text
ROOT/<id>/                       cmake --install of build, runtimes/builtins-bins, runtimes/runtimes-bins
ROOT/<id>/bin/arm64-apple-darwin.cfg           -isysroot <xcrun SDK>
ROOT/<id>/bin/arm64-apple-darwin-clang++.cfg   @arm64-apple-darwin.cfg plus link-only
                              -L and -rpath ROOT/<id>/lib and -lunwind
ROOT/<id>/view/bin/<tool>-p2996 -> ../../bin/<tool>   every other tool; skipped when LLVM made <tool>-p2996
ROOT/<id>/view/bin/*-p2996, *.cfg -> ../../bin/<same name>
ROOT/<id>/view/{include,lib,libexec,share} -> ../<same name>
ROOT/current -> <id>/view        ROOT/previous -> the view before it
ROOT/{bin,include,lib,libexec,share} -> current/<same name>
```

Clang reads `<triple>.cfg`, then `arm64-apple-darwin<N>.cfg`, then `arm64-apple-darwin.cfg` from
its own resolved bin dir (`ROOT/<id>/bin`), so only the unversioned names exist and a macOS
bump never shadows them.
