# Initial cache for the clang-p2996 build (cmake -C). p2996 build sets P2996_SDK.
set(_sdk "$ENV{P2996_SDK}")
if(NOT IS_DIRECTORY "${_sdk}")
  message(FATAL_ERROR "Set P2996_SDK to the macOS SDK (run through mise run //p2996:build).")
endif()
set(CMAKE_OSX_SYSROOT "${_sdk}" CACHE PATH "" FORCE)
set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
set(CMAKE_OSX_ARCHITECTURES arm64 CACHE STRING "" FORCE)
set(CMAKE_OSX_DEPLOYMENT_TARGET 27.0 CACHE STRING "" FORCE)
set(CMAKE_INSTALL_RPATH "@loader_path/../lib" CACHE STRING "Relocatable tool libraries" FORCE)
# DL-756, DL-757: every LLVM project and runtime that builds on macOS; libc is the Darwin overlay
# (libllvmlibc.a beside the system libc). Skipped: libclc and offload (GPU device libraries),
# llvm-libgcc (Linux), cross-project-tests (tests). A Linux cache will differ.
set(LLVM_ENABLE_PROJECTS "clang;clang-tools-extra;lld;lldb;mlir;polly;bolt;flang" CACHE STRING "" FORCE)
set(LLVM_ENABLE_RUNTIMES "libc;libunwind;libcxxabi;libcxx;compiler-rt;openmp;flang-rt" CACHE STRING "" FORCE)
set(LLVM_TARGETS_TO_BUILD "AArch64;X86" CACHE STRING "" FORCE)
# lldb uses Xcode's signed debugserver instead of building and code-signing its own.
set(LLDB_USE_SYSTEM_DEBUGSERVER ON CACHE BOOL "" FORCE)
# DL-757: MLIR's Python bindings (nanobind, numpy from this project's uv lock, DL-758). lldb Lua and the
# OCaml bindings switch on by themselves once the global Lua and opam switch are on PATH.
set(MLIR_ENABLE_BINDINGS_PYTHON ON CACHE BOOL "" FORCE)
set(LLVM_ENABLE_ASSERTIONS ON CACHE BOOL "Diagnose experimental compiler failures" FORCE)
set(LLVM_BUILD_LLVM_DYLIB ON CACHE BOOL "" FORCE)
set(LLVM_LINK_LLVM_DYLIB ON CACHE BOOL "" FORCE)
# LLVM installs the suffixed driver names itself (replaces the default clang++;clang-cl;clang-cpp).
set(CLANG_LINKS_TO_CREATE "clang-p2996;clang++-p2996;clang-cpp-p2996" CACHE STRING "" FORCE)
set(CLANG_LINK_CLANG_DYLIB ON CACHE BOOL "Shared Clang libraries for IWYU" FORCE)
set(LLVM_INSTALL_TOOLCHAIN_ONLY OFF CACHE BOOL "Keep headers and CMake exports for IWYU" FORCE)
set(LLVM_PARALLEL_COMPILE_JOBS 4 CACHE STRING "" FORCE)
set(LLVM_PARALLEL_LINK_JOBS 1 CACHE STRING "" FORCE)
set(LLVM_PARALLEL_TABLEGEN_JOBS 1 CACHE STRING "" FORCE)
# macOS only (DL-756). zlib, zstd, libxml2, libedit and the fuzzer, xray and orc runtimes keep LLVM's
# defaults, whose own platform checks skip the Linux-only parts.
foreach(_name LLVM_INCLUDE_TESTS LLVM_INCLUDE_BENCHMARKS LLVM_INCLUDE_EXAMPLES LLVM_INCLUDE_DOCS
    LIBCXX_INCLUDE_TESTS LIBCXXABI_INCLUDE_TESTS LIBUNWIND_INCLUDE_TESTS COMPILER_RT_INCLUDE_TESTS
    COMPILER_RT_ENABLE_IOS COMPILER_RT_ENABLE_WATCHOS COMPILER_RT_ENABLE_TVOS COMPILER_RT_ENABLE_XROS)
  set(${_name} OFF CACHE BOOL "" FORCE)
endforeach()
foreach(_name LIBCXX_ENABLE_SHARED LIBCXX_ENABLE_STATIC LIBCXXABI_ENABLE_SHARED LIBCXXABI_ENABLE_STATIC
    LIBUNWIND_ENABLE_SHARED LIBUNWIND_ENABLE_STATIC LIBCXXABI_USE_LLVM_UNWINDER
    COMPILER_RT_BUILD_SANITIZERS COMPILER_RT_BUILD_PROFILE COMPILER_RT_DEFAULT_TARGET_ONLY)
  set(${_name} ON CACHE BOOL "" FORCE)
endforeach()
set(DARWIN_osx_ARCHS arm64 CACHE STRING "" FORCE)
set(DARWIN_osx_BUILTIN_ARCHS arm64 CACHE STRING "" FORCE)
set(DARWIN_macosx_CACHED_SYSROOT "${_sdk}" CACHE STRING "" FORCE)
# The runtimes and builtins sub-builds get the same platform values explicitly.
set(_runtime_args "-DCMAKE_OSX_ARCHITECTURES=arm64;-DCMAKE_OSX_DEPLOYMENT_TARGET=27.0;-DCMAKE_OSX_SYSROOT=${_sdk};-DCMAKE_INSTALL_RPATH=@loader_path/../lib")
set(RUNTIMES_CMAKE_ARGS "${_runtime_args}" CACHE STRING "" FORCE)
set(BUILTINS_CMAKE_ARGS "${_runtime_args}" CACHE STRING "" FORCE)
