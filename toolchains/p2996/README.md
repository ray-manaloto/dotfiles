# clang-p2996 (C++26 reflection) for arm64 macOS

What a rebuild needs, moved from the marketplace recipe (DL-754). Run in order:

```sh
mise run p2996:source    # fetch the pin into the cache, apply patches/ (idempotent)
mise run p2996:build     # hours; a rerun resumes the build dir. --dry-run prints the cmake commands
mise run p2996:install   # dated prefix, current link, suffixed/bin, default .cfg files
mise run p2996:verify    # compile and run a reflection sample with clang++-p2996
```

## Paths

- Install root: `ROOT` in `common.sh`, one line (or set `P2996_ROOT`); default `~/.local/state/dotfiles/p2996`.
- Source and build: `~/.cache/dotfiles/p2996/{source,build}` (`P2996_CACHE`), outside the repo.
- Lock: build takes a non-blocking `flock` on `~/.local/state/dotfiles/heavy-gate.lock`, the
  gate the legacy `host_lock.py` uses, so one heavy build runs at a time.

## Source pin

- Remote `https://github.com/bloomberg/clang-p2996.git`, commit
  `f17c8d6c7bfef5e02ccadcf33517fd2a53b51b6e`, tree `9899759f9004a7df8442ec57000a17e53e6ad5f6`.
- Shallow fetch of that commit; the tree hash is checked before patching.

## Patches (applied with `git apply --unidiff-zero`)

- `sdk-rdf-comparator.patch`: the macOS 27 SDK libc++ that compiles LLVM rejects the stateful
  `std::less<RegisterRef>` specialization; RDF code gets a named `llvm::rdf::RegisterRefLess` (5 files).
- `sdk-float-math.patch`: clang's and libc++'s `float.h` answer a partial
  `__need_infinity_nan` include, which the macOS 27 SDK headers make (2 files).
- `asan-macos27-dyld.patch`: on macOS 27, ASan startup finds the dyld header through
  `TASK_DYLD_INFO` instead of shared-cache enumeration, which allocates too early.

## CMake

`bootstrap.cmake` is the initial cache (`-C`). Build passes the SDK (`xcrun --show-sdk-path`,
resolved to the versioned SDK) as `P2996_SDK`, the Command Line Tools `clang`/`clang++` as the
bootstrap compilers and `ROOT/current` as the configured prefix, and clears inherited
`CC CXX CFLAGS CXXFLAGS CPPFLAGS LDFLAGS SDKROOT`. Key values: Release, arm64, deployment target
27.0, `@loader_path/../lib` rpath; projects `clang;clang-tools-extra`; runtimes
`libunwind;libcxxabi;libcxx;compiler-rt`; AArch64 only; assertions on; LLVM and Clang dylibs;
full install (headers and CMake exports, for IWYU); compile jobs 4, link and tablegen jobs 1;
tests, docs, examples, optional libraries and non-macOS compiler-rt parts off; shared and static
runtimes, sanitizers and profile on. The runtimes and builtins sub-builds get the same platform
values through `RUNTIMES_CMAKE_ARGS` and `BUILTINS_CMAKE_ARGS`.

## Prefix layout

```text
ROOT/<UTC stamp>/             cmake --install of build, runtimes/builtins-bins, runtimes/runtimes-bins
ROOT/<UTC stamp>/bin/arm64-apple-darwin.cfg           -isysroot <xcrun SDK>
ROOT/<UTC stamp>/bin/arm64-apple-darwin-clang++.cfg   @arm64-apple-darwin.cfg plus link-only
                              -L and -rpath ROOT/current/lib and -lunwind
ROOT/current -> <UTC stamp>
ROOT/suffixed/bin/<tool>-p2996 -> ../../current/bin/<tool>   (cfg files keep their names)
```

Clang reads `<triple>.cfg`, then `arm64-apple-darwin<N>.cfg`, then `arm64-apple-darwin.cfg` from
its own bin dir, so only the unversioned names exist and a macOS bump never shadows them.
