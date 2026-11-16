# clang-p2996 (C++26 reflection) for arm64 macOS

The goal: this Mac always has a working C++26 reflection compiler beside its default LLVM. Every tool
from Bloomberg's clang-p2996 fork is on PATH with a `-p2996` suffix (`clang++-p2996`), so it never
replaces the default `clang++`. A new compiler goes live in one rename, only after it has verified,
and the one before it stays on disk as `ROOT/previous`.

A uv Python package (`src/p2996/`, DL-758) does this through this folder's mise tasks; layout DL-755.
From the repository root the tasks are `//p2996:<task>` (a `[monorepo.path_aliases]` entry):

```sh
mise run //p2996:source      # newest commit of P2996_BRANCH (or --commit <sha>), patches applied
mise run //p2996:build       # prepares source, then hours; a rerun resumes. --dry-run prints the cmake commands
mise run //p2996:status      # each build tree's ninja progress from its own files; runs no ninja
mise run //p2996:review-log -- <log>  # read-only Codex team reports warnings, errors, skipped parts
mise run //p2996:install     # ROOT/<id>, verify, one rename to activate; default .cfg files
mise run //p2996:verify      # compile and run src/p2996/reflection.cpp with clang++-p2996
mise run //p2996:clean       # delete the build trees; --source also the source trees
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
one `source/work` and one `build/work`), and `P2996_IWYU_REMOTE` and `P2996_IWYU_COMMIT`
(include-what-you-use, below). `<id>` is `<commit>-<12 hex>`, the hex being a digest of
`build/work/p2996-inputs.json`: what CMake found after configure, read from its file API (DL-809,
DL-811). That file holds the commit, patches, `uv.lock`, CMake version, compilers, the resolved Python
the digest of every file in the SDK, the include-what-you-use commit, and every cache entry, with outside files named by their content. It leaves out the launchers, job
counts and values inside the source, build or project folders, so a worktree does not change the id.
No lock: two builds at once are not supported.

The same `[env]` holds `SCCACHE_DIR` (`~/.cache/dotfiles/sccache`), `SCCACHE_CACHE_SIZE` and
`SCCACHE_IDLE_TIMEOUT`. Build compiles the main tree through sccache: `bootstrap.cmake` sets the CMake
launchers from `P2996_LAUNCHER` and turns precompiled headers off. The fixed folders let a new commit
reuse the cache without `SCCACHE_BASEDIRS`. The runtimes sub-builds do not use it: they compile with
the clang just built. `sccache --show-stats` reports the hits.

## Source

Always the newest commit of `refs/heads/p2996` on `https://github.com/bloomberg/clang-p2996.git`
(`git ls-remote` on each `source` run), unless `--commit` names one; build and install read the
tree of that commit. Shallow fetch into `source/work`, reset and cleaned, then the patches. Build
configures from a fresh cache, computes the id and skips the compile when `ROOT/<id>/installed` exists.
`source` also checks out include-what-you-use at `P2996_IWYU_COMMIT` into `source/iwyu`; configure builds
it in the LLVM tree as an external project (`LLVM_EXTERNAL_PROJECTS=iwyu`), so the install puts
`include-what-you-use`, `fix_includes.py`, `iwyu_tool.py` and the `.imp` mappings in the prefix and the view links
them as `include-what-you-use-p2996`, `fix_includes.py-p2996` and `iwyu_tool.py-p2996`. Its `clang_NN` branch
must match the LLVM major of the p2996 branch: when p2996 moves to a new major, the build fails until
`P2996_IWYU_COMMIT` names the matching branch. For libc++ headers pass libc++'s own mapping,
`-Xiwyu --mapping_file=ROOT/include/c++/v1/libcxx.imp`.
Install writes that mark after verify, so an interrupted or failed install is assembled again.
`build/last` names the id the build tree holds and exists only after a successful build; `source`
removes it, so a failed build or a changed tree cannot be installed. A reinstall of the active id only rewrites the `.cfg` files, which is the
repair after an SDK move. Install of an id already in ROOT reuses that prefix. Install refuses a real `ROOT/bin` folder, the layout before this
one, and changes nothing. Install verifies the new version, keeps the old one
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

`src/p2996/bootstrap.cmake` is the initial cache (`-C`); a changed value changes the id. Build passes the SDK (`xcrun --show-sdk-path`, resolved to the versioned SDK) as
`P2996_SDK`, the Command Line Tools `clang`/`clang++` as the bootstrap compilers, this project's venv
python as `Python3_EXECUTABLE` and `ROOT/current` as the configured prefix, and clears inherited
`CC CXX CFLAGS CXXFLAGS CPPFLAGS LDFLAGS SDKROOT`. Key values: Release, arm64, deployment target
27.0, `@loader_path/../lib` rpath; every LLVM project that builds on macOS (DL-756):
`clang;clang-tools-extra;lld;lldb;mlir;polly;bolt;flang`, runtimes
`libc;libunwind;libcxxabi;libcxx;compiler-rt;openmp;flang-rt` (libc is the Darwin overlay); targets
`AArch64;X86`; lldb builds its own debugserver, signed with the `lldb_codesign` certificate that `p2996 build` checks for
before configure (create it once with `lldb/scripts/macos-setup-codesign.sh` from the source tree), with Python and
Lua scripting; MLIR Python bindings and
LLVM's OCaml bindings on (DL-757). Every tool the build needs (SWIG, Lua, doxygen, opam switch `llvm`
with ocamlfind and ctypes) comes from the global mise config; the Python modules (pygments, pyyaml,
numpy, nanobind, pybind11, ml_dtypes, all uncapped) come from this project's uv lock. Assertions on; LLVM
and Clang dylibs; full install (headers and CMake exports, for IWYU); compile jobs `P2996_JOBS`, the
core count (`mise run //p2996:build --jobs N` lowers it for one run), link and tablegen jobs 1; tests,
docs, examples and the iOS, watchOS, tvOS and visionOS runtimes off;
zlib, zstd, libxml2, libedit and the compiler-rt runtimes keep LLVM's defaults, whose own checks
skip Linux-only parts. Not built on macOS: libclc, offload, llvm-libgcc, cross-project-tests.
A Linux build needs its own cache with the Linux choices.
The runtimes and builtins sub-builds get the same platform values through `RUNTIMES_CMAKE_ARGS` and
`BUILTINS_CMAKE_ARGS`. `CLANG_LINKS_TO_CREATE` is `clang++;clang-cpp;clang-p2996;clang++-p2996;clang-cpp-p2996`: LLVM installs the suffixed driver
names itself, and keeps `clang++` and `clang-cpp` because the runtimes sub-build compiles with
`build/bin/clang++` (DL-760); `install` links only the `-p2996` names into `ROOT/<id>/view/bin`, which
`ROOT/bin` reaches through `ROOT/current`.

## Nothing else runs ninja in the build folder

While a build runs, nothing else may run `ninja` in `build/work` or its sub-builds, a dry run (`ninja -n`)
included. A dry run still "finishes" each step it would run and reads that step's depfile (ninja v1.13.2
`src/build.cc:889`), then deletes it unless `-d keepdepfile` (`src/build.cc:1037-1038`). When that hits a
compile that has just written its `.o.d`, sccache can no longer open the file it stores with the object
(sccache v0.19.0 `src/cache/cache_io.rs:236-262`) and fails the compile with `failed to zip up compiler
outputs` (`src/compiler/compiler.rs:806-808`). `-d keepdepfile` is not enough: a dry run also writes each
step's response file and deletes it again (`src/build.cc:860-863`, `955-957`), and creates its output folders.

`p2996 build` runs the compile once more when its output holds that sccache message, logging a `compile
retry` warning; ninja resumes, so only the failed step runs again. A second failure fails the build.

To watch a build, read `build/work/p2996-build.log`: the compile's output (the newest run only, so a retry
starts it again), with ninja's `[done/total seconds]` lines. The builtins and runtimes sub-builds print the
same lines inside one outer step. Since the compile now writes to a pipe, ninja prints one line per step
instead of updating one line, and compiler diagnostics may lose their colour.

`mise run //p2996:status` runs no ninja. For `build/work`, `runtimes/builtins-bins` and
`runtimes/runtimes-bins`, each with a `.ninja_log`, it logs one `tree status` event: `running` (a `ninja`
process works in that folder, from `lsof`; `cmake --build` starts it there), `outputs`, `last` and `idle_s`
(seconds since ninja last wrote its log there: a step ending, or a recompaction as a run starts). The log has
one line per output, so it counts outputs, not steps; most steps have one. For a running tree, `outputs` counts
what this run has built and `last` names the output of its step that ended last: a log line's mtime is the wall
clock as its step started, or for a restat step whose outputs changed their later mtime (ninja v1.13.2
`src/build.cc:833-849`, `916-948`), so its mtime less its start (ms from the run's start) is when its run
started, and this run's lines are those at or after the process's start (`ps`, whole seconds; 1 ms plus 1000
ppm of the step's start allowed for clock slew). A run that ended within a second before this one started
would count too. For a finished tree, `outputs` counts every output its builds have logged, and `last` is
empty. Ninja recompacts the log in any order as a run starts (`src/build_log.cc:314-321`, `359-369`), so
nothing reads line order. The log holds no totals, so there is no k/N or ETA. Last comes `sccache stats`, from
the running server (`--show-stats` starts none).

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
