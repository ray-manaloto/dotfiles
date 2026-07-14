# syntax=docker/dockerfile:1.25@sha256:0adf442eae370b6087e08edc7c50b552d80ddf261576f4ebd6421006b2461f12
# check=error=true

# ────────────────────────────────────────────────────────────────────
# File-scope ARGs (must be declared before any FROM so they can
# interpolate into FROM lines downstream — ARGs inside a stage are
# stage-local).
# ────────────────────────────────────────────────────────────────────

# Base ubuntu image for the `devcontainer-base` stage. Digest-pinned to the
# 26.04 manifest-list (multi-arch resolution preserved); Renovate bumps the
# digest via the custom `ubuntu` manager (docker datasource). Keep in lockstep
# with docker-bake.hcl's BASE_IMAGE default (the base hash reads bake).
ARG BASE_IMAGE=ubuntu:26.04@sha256:b7f48194d4d8b763a478a621cdc81c27be222ba2206ca3ca6bc42b49685f3d9e

# Builder image for the clang-p2996 compile (#160 T11). DELIBERATELY a
# separate, rarely-bumped variable (NOT Renovate-tracked): its digest is a
# first-class p2996-hash input, so a bump forces the ~2h compiler rebuild —
# decoupled from routine BASE_IMAGE bumps. The builder never ships bytes
# into the final image (only /opt/clang-p2996 is exported), so pinning it
# older than BASE_IMAGE is ABI-safe while both are the same ubuntu series.
# Keep in lockstep with docker-bake.hcl's BUILDER_IMAGE default.
ARG BUILDER_IMAGE=ubuntu:26.04@sha256:b7f48194d4d8b763a478a621cdc81c27be222ba2206ca3ca6bc42b49685f3d9e

# NOTE (#160 T11): the former ARG P2996_SOURCE / ARG DEVCONTAINER_BASE_REF
# FROM-indirection is retired. CI now injects prebuilt tiers as
# digest-pinned NAMED BUILD CONTEXTS that override the same-named local
# stages (bake `dev.contexts.devcontainer-base=docker-image://…@sha256:…`,
# `dev.contexts.p2996-export=…`); absent contexts, the local stages build
# — the native cold/warm switch with zero Dockerfile plumbing.

# ──── BASE_HASH_BEGIN ──── (sentinel for python/.../p2996_hash.py)
FROM ${BASE_IMAGE} AS devcontainer-base

ARG DEBIAN_FRONTEND=noninteractive

# Only PATH and mise directory layout stay as Docker ENV.
# All other vars (locale, platform hints, tool config) live in
# .devcontainer/mise-system.toml [env] so mise owns them.
#
# Cookbook canonical layout per https://mise.jdx.dev/mise-cookbook/docker:
#   - MISE_DATA_DIR pins installs/shims to /usr/local/share/mise. Without
#     it, build-time `mise install` (as root) writes to XDG default
#     /root/.local/share/mise — invisible to PATH and to non-root users.
#   - MISE_CONFIG_DIR tells mise WHERE to discover the system config
#     (mise reads $MISE_CONFIG_DIR/config.toml). Without it, mise has
#     no idea our COPY destination /usr/local/share/mise/config.toml is
#     a config — `mise install -y` silently no-ops because it discovers
#     zero configs. (MISE_TRUSTED_CONFIG_PATHS only AUTHORIZES a path,
#     it does not DISCOVER configs there. Trust + discovery are
#     orthogonal — both are required.)
#   - The cookbook explicitly sets BOTH vars to the same path (`/mise`)
#     and so must we.
#   - PR-2 will layer per-user overlays via named volumes at
#     ~/.local/share/mise (devcontainer feature mount), so the system
#     path remains the canonical baked location while users get mutable
#     overlays at runtime.
#
# Rust cookbook (https://mise.jdx.dev/lang/rust.html):
#   - MISE_CARGO_HOME / MISE_RUSTUP_HOME are mise-specific build-time
#     vars that isolate mise's bundled rust install from the standard
#     CARGO_HOME / RUSTUP_HOME a user might set at runtime.
#   - Standard CARGO_HOME / RUSTUP_HOME are intentionally UNSET so
#     runtime users fall back to ~/.cargo / ~/.rustup defaults; PR-2
#     mounts named volumes there for per-clone persistence and
#     cookbook shadow-priority semantics.
# MISE_SYSTEM_CONFIG_FILE is intentionally NOT set: it short-circuits
# mise's system_config_files() to that ONE file, hiding conf.d/shared.toml
# and config.runtime.toml from the system axis. The devcontainer runtime
# re-points MISE_CONFIG_DIR at the user dir (overlay tier), so system-axis
# *directory discovery* via MISE_SYSTEM_CONFIG_DIR is the only thing
# keeping the shared + runtime tiers resolvable there (probe-verified in
# :pr-169; a baked FILE pin broke `chezmoi init` onCreate — PR #169).
ENV MISE_DATA_DIR=/usr/local/share/mise \
    MISE_CONFIG_DIR=/usr/local/share/mise \
    MISE_INSTALL_PATH=/usr/local/bin/mise \
    MISE_SYSTEM_CONFIG_DIR=/usr/local/share/mise \
    MISE_TRUSTED_CONFIG_PATHS=/usr/local/share/mise:/workspaces/dotfiles \
    MISE_CARGO_HOME=/usr/local/share/cargo \
    MISE_RUSTUP_HOME=/usr/local/share/rustup \
    PATH="/usr/local/bin:/usr/local/share/mise/shims:/usr/local/share/cargo/bin:${PATH}"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Seed layer: ONLY the minimal apt set the mise installer itself needs
# (curl + ca-certificates). The full apt package set is declared in
# mise-system.toml [bootstrap.packages] and installed by
# `mise bootstrap packages apply` after the config COPY below (#160 T4,
# wagov-dtt/devcontainer-base pattern — the shadow-verify split is retired).
# The apt.conf.d drop-in disables Recommends/Suggests for EVERY apt
# invocation in this image, including the mise-driven apply (mise has no
# apt-args setting; native apt config replaces the per-command flag).
# Lists/cache live in BuildKit cache mounts, never in a layer, so no
# rm -rf cleanup is needed — and the preserved lists let the apply step
# reuse them across builds.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    export DEBIAN_FRONTEND=noninteractive && \
    printf 'APT::Install-Recommends "false";\nAPT::Install-Suggests "false";\n' \
      > /etc/apt/apt.conf.d/99no-install-recommends && \
    sed -i '/^path-exclude=\/usr\/share\/man\/\*$/d' /etc/dpkg/dpkg.cfg.d/excludes && \
    apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl

# Install mise via the official installer, pinned via MISE_VERSION (mise.run
# honors it). The pin MUST be a version that reads the committed
# mise-system.lock format — lock formats are NOT cross-version compatible
# (`mise install --locked` rejects a lock written by a different mise), and
# the lock was generated with 2026.7.0 (epic #160 T1). Renovate bumps this via
# the custom `jdx/mise` manager, which regenerates the lock in lockstep. The
# mise.run installer already chmods the binary; the explicit chmod is a
# belt-and-braces guard against permission drift on the cache mount.
# renovate: datasource=github-releases depName=jdx/mise
ARG MISE_VERSION=2026.7.5
RUN curl https://mise.run | MISE_VERSION="v${MISE_VERSION}" sh && \
    chmod +x ${MISE_INSTALL_PATH} && \
    mise --version

# System-wide mise config and data structure (cookbook canonical paths).
RUN groupadd --gid 2000 mise && \
    mkdir -p /usr/local/share/mise /usr/local/share/cargo /usr/local/share/rustup && \
    chown -R :mise /usr/local/share/mise /usr/local/share/cargo /usr/local/share/rustup && \
    chmod -R 775 /usr/local/share/mise /usr/local/share/cargo /usr/local/share/rustup

# Copy dedicated system config — no chezmoi dependency, no sed stripping
COPY .devcontainer/mise-system.toml /usr/local/share/mise/config.toml
# The native mise lockfile (rattler conda sha256 + version pins for all 109
# tools, generated for linux-x64). mise reads the lock as `mise.lock` beside
# the data dir — NOT `config.lock` (verified: config.lock is silently ignored);
# `mise install --system --locked` below consumes it. Replaces the retired
# version-only mise-system-resolved.json snapshot. See epic #160.
COPY .devcontainer/mise-system.lock /usr/local/share/mise/mise.lock
# Shared host↔image tool versions (#160 T5). mise merges $MISE_CONFIG_DIR/conf.d/
# *.toml into the system config, so these 20 exact-pinned tools are resolved the
# same on the host (which loads the repo copy at .config/mise/conf.d/) and here.
# Their versions are captured in mise-system.lock above and installed via
# `mise install --system --locked`.
COPY .config/mise/conf.d/shared.toml /usr/local/share/mise/conf.d/shared.toml

# Install the full apt set declared in mise-system.toml [bootstrap.packages]
# (#160 T4). Runs as root so mise elevates nothing (no sudo in argv); mise
# sets DEBIAN_FRONTEND=noninteractive itself; --update forces apt-get update
# against the cache-mounted lists; the experimental gate is satisfied by
# `experimental = true` in the config COPYd above (trusted via
# MISE_TRUSTED_CONFIG_PATHS). The `status --json --missing` post-condition
# is the anti-drift gate: it exits 1 if any declared package is missing or
# version-mismatched, so a silent apply no-op fails the build loudly
# (build-time self-check rule). Accepted trade-off: the config COPY above
# busts this layer on any mise-system.toml edit — mitigated by the cache
# mounts keeping .deb downloads and lists warm.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    mise bootstrap packages apply --manager apt --yes --update && \
    mise bootstrap packages status --json --missing

# graphviz 15.1.0 — pinned GitLab Ubuntu .deb (#222 PR-A, folds #22).
# WHY a manual .deb and not apt: Ubuntu 26.04 apt ships graphviz 14.1.2, and the
# retired mise `gitlab:` backend only fetched Fedora RPMs (no usable `dot`).
# Upstream's GitLab release publishes a native ubuntu_26.04 build, but both
# flavors are kitchen-sink: the -cmake.deb declares ZERO deps (its plugins can't
# load → `dot -c` registers nothing), and the split -debs pull 161 packages
# (Qt5/ghostscript/GTK). So we take the dep-less cmake .deb and add ONLY the
# libs we want — libgd3 (png/gif) + libgts (neato/fdp/circo/twopi layout); SVG,
# dot, json come from the built-in `core` plugin needing nothing extra — then
# PRUNE the exotic output plugins whose heavy deps we refuse and regenerate the
# plugin registry with `dot -c`. Net ~+21 MB over apt 14.1.2 (the lean floor for
# 15.1.0). Probe-verified formats: svg/svgz/png/json/dot/xdot.
# Pin discipline (like GCC_LATEST_DEB): the filename encodes BOTH the base
# Ubuntu release (ubuntu_26.04) and the version — bump the URL and sha256
# together. Upstream ships no checksum for the ubuntu debs, so this
# locally-computed sha256 is the .deb's only integrity handle.
# renovate: datasource=gitlab-releases depName=graphviz/graphviz
ARG GRAPHVIZ_VERSION=15.1.0
ARG GRAPHVIZ_DEB=ubuntu_26.04_graphviz-15.1.0-cmake.deb
ARG GRAPHVIZ_DEB_SHA256=f3294aeea3618044022874823344a1154ee7272857e82f248610fcaa7d2dc4c5
# Pure && chain (any failing step aborts the build loudly); explicit /tmp paths
# avoid a `cd` (hadolint DL3003). SVG/PNG/neato renders to /dev/null exercise the
# core+gd plugins and dot+neato layout engines; the trailing grep asserts v15.
# The cmake .deb declares NO deps, so we install every runtime lib explicitly:
# libltdl7/libexpat1/zlib1g are the `dot` binary's own core deps (the minimal
# devcontainer-base lacks libltdl7 once apt:graphviz is gone → dot would fail to
# start); libgd3+libcairo2 back the gd plugin (png/gif); libgts backs the neato/
# fdp/circo/twopi layout engines. Verified on a bare ubuntu:26.04 amd64 base.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    export DEBIAN_FRONTEND=noninteractive && \
    curl -fLSs -o "/tmp/${GRAPHVIZ_DEB}" "https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/${GRAPHVIZ_VERSION}/${GRAPHVIZ_DEB}" && \
    echo "${GRAPHVIZ_DEB_SHA256}  /tmp/${GRAPHVIZ_DEB}" | sha256sum -c - && \
    apt-get update && \
    apt-get install -y --no-install-recommends "/tmp/${GRAPHVIZ_DEB}" libltdl7 libexpat1 zlib1g libgd3 libgts-0.7-5t64 libcairo2 && \
    rm -f "/tmp/${GRAPHVIZ_DEB}" && \
    rm -f /usr/lib/graphviz/libgvplugin_{ascii,devil,gdk,gs,kitty,lasi,pango,poppler,rsvg,vt,webp,xlib}.so.8 && \
    rm -f /usr/lib/graphviz/config8 && \
    dot -c && \
    printf 'digraph{a->b->c;a->c}' | dot -Tsvg -o /dev/null && \
    printf 'digraph{a->b}' | dot -Tpng -o /dev/null && \
    printf 'graph{a--b--c--a}' | neato -Tsvg -o /dev/null && \
    dot -V 2>&1 | grep -q 'version 15'

# LLVM-22 C++ toolchain build-time smoke (#222 PR-C).
# The apt llvm/clang/lld/lldb/clang-tools packages (declared in mise-system.toml
# [bootstrap.packages], installed by `mise bootstrap packages apply` above) put
# their UNVERSIONED binaries under /usr/lib/llvm-22/bin (clang, clang++, clangd,
# clang-tidy, clang-format, lld, ld.lld, lldb, llvm-*) — /usr/bin holds only the
# `-22`-suffixed names. That dir is put on PATH via mise's `_.path` in
# mise-system.toml [env] (NOT /etc/profile.d: the chezmoi ~/.profile runs `mise
# activate`, which resets PATH and would drop a profile.d addition). This RUN is
# purely the loud build-time self-check (full paths, no PATH dependency): it proves
# clang++ is really v22, that the asan+ubsan sanitizer runtimes (libclang-rt-22-dev)
# link AND the binary runs, and that clangd/clang-tidy/lld/lldb/llvm-config are
# present (capability parity with the removed conda tools). TSan is not RUN here
# (build-as-root ASLR layout; the tier-3 smoke covers it on real amd64).
RUN /usr/lib/llvm-22/bin/clang++ --version | grep -q 'version 22' && \
    printf '#include <cstdio>\nint main(){printf("ok\\n");return 0;}\n' > /tmp/llvmcheck.cpp && \
    /usr/lib/llvm-22/bin/clang++ -fsanitize=address,undefined /tmp/llvmcheck.cpp -o /tmp/llvmcheck && \
    /tmp/llvmcheck | grep -q '^ok$' && \
    test -x /usr/lib/llvm-22/bin/clangd && \
    test -x /usr/lib/llvm-22/bin/clang-tidy && \
    test -x /usr/lib/llvm-22/bin/clang-format && \
    test -x /usr/lib/llvm-22/bin/lld && \
    test -x /usr/lib/llvm-22/bin/lldb && \
    /usr/lib/llvm-22/bin/llvm-config --version | grep -q '^22' && \
    rm -f /tmp/llvmcheck.cpp /tmp/llvmcheck

# Pre-install tools globally via mise
# Known cosmetic warnings during install:
# - rustup "existing settings file": rustup-init creates settings.toml then
#   check_existence_of_settings_file() warns about its own file. Fixed via
#   RUSTUP_INIT_SKIP_EXISTENCE_CHECKS=yes (undocumented env var, see
#   rust-lang/rustup/src/cli/self_update.rs). RUSTUP_INIT_SKIP_PATH_CHECK
#   in mise-system.toml [env] is a different check (PATH validation).
# - bun "add the global bin folder to $PATH": bun checks if its bin output
#   directory exists on $PATH at install time. During Docker RUN, PATH only
#   includes /usr/local/share/mise/shims — not bun's per-package bin dirs. At runtime,
#   mise shims intercept all lookups so the warning is cosmetic. No bun env
#   var (BUN_QUIET, BUN_LOG_LEVEL) suppresses this — it's hardcoded in bun's
#   install reporter. Unfixable: fundamental mismatch between bun's PATH-based
#   assumptions and mise's shim resolution model.
RUN --mount=type=cache,id=mise-cache,target=/usr/local/share/mise/cache,sharing=locked \
    --mount=type=cache,id=uv-cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=secret,id=github_token \
    export MISE_INSTALL_MODE=system && \
    export UV_LINK_MODE=copy && \
    export LANG=C.UTF-8 && \
    export LC_ALL=C.UTF-8 && \
    export RUSTUP_INIT_SKIP_EXISTENCE_CHECKS=yes && \
    if [ -f /run/secrets/github_token ]; then \
      GITHUB_TOKEN="$(cat /run/secrets/github_token)" && \
      export GITHUB_TOKEN && \
      export MISE_GITHUB_TOKEN="$GITHUB_TOKEN"; \
    fi && \
    mise install --system --locked -y && \
    test "$(mise ls --installed | wc -l)" -gt 0 || { echo "ERROR: mise installed zero tools — system config not discovered (check MISE_CONFIG_DIR points at /usr/local/share/mise containing config.toml)"; exit 1; } && \
    test -d /usr/local/share/cargo/bin || { echo "ERROR: MISE_CARGO_HOME not honored — /usr/local/share/cargo/bin missing after mise install (rust cookbook regression)"; exit 1; } && \
    test -d /usr/local/share/rustup/toolchains || { echo "ERROR: MISE_RUSTUP_HOME not honored — /usr/local/share/rustup/toolchains missing after mise install (rust cookbook regression)"; exit 1; } && \
    chmod -R 777 /usr/local/share/mise /usr/local/share/cargo /usr/local/share/rustup

# Reshim to ensure all shims are present (aqua tools may include doc-file
# shims like LICENSE, README — these are harmless and must not be deleted
# or mise doctor will report them as missing)
RUN mise reshim -f && \
    test -n "$(find /usr/local/share/mise/shims -mindepth 1 -maxdepth 1 -print -quit)" || { echo "ERROR: /usr/local/share/mise/shims empty after reshim — mise has no installed tools to shim"; exit 1; }

# Final global permissions check
RUN chmod -R 777 /usr/local/share/mise /usr/local/share/cargo /usr/local/share/rustup

# Copy image-specific hk config + shared checks for smoke-test validation.
# hk-image.pkl imports hk-common.pkl — both must be in /etc/hk/ for pkl
# relative import resolution. hk-image.pkl is renamed to hk.pkl (hk default).
COPY hk-common.pkl /etc/hk/hk-common.pkl
COPY hk-image.pkl /etc/hk/hk.pkl

# Ensure mise is activated for all users
RUN echo "eval \"\$(/usr/local/bin/mise activate bash)\"" > /etc/profile.d/mise.sh && \
    echo "eval \"\$(/usr/local/bin/mise activate zsh)\"" > /etc/profile.d/mise.zsh

WORKDIR /workspaces

# ──── BASE_HASH_END ──── (sentinel for python/.../p2996_hash.py)

# ──── P2996_HASH_BEGIN ──── (sentinel for python/.../p2996_hash.py)

# ── clang-p2996 builder (Bloomberg fork, built from source) ──────────
# Runs in parallel with devcontainer-base via BuildKit DAG — since #160
# T11 the builder is fully DECOUPLED from devcontainer-base: it starts
# from the parameterized ${BUILDER_IMAGE} and installs its own compile
# toolchain via apt, so mise/hk/base-config edits never invalidate the
# ~2h compiler build (p2996-hash no longer folds base-hash). Only the
# install prefix (/opt/clang-p2996) ships — via the scratch p2996-export
# stage (~2.8 GB uncompressed / ~0.7 GB compressed: bin + libTooling static
# libs + headers), pushed to GHCR as :p2996-<hash16> and re-consumed as a
# digest-pinned named build context on warm paths. The source checkout +
# build tree stay under /build (builder-only), excluded from the export
# since #222 PR-B.
FROM ${BUILDER_IMAGE} AS clang-builder-cold

ARG DEBIAN_FRONTEND=noninteractive
ARG CLANG_P2996_REPO=https://github.com/bloomberg/clang-p2996.git
# Reconciled to match docker-bake.hcl's CLANG_P2996_REF default (#160 T3) —
# CI's bake passes that value as a build arg (overriding this default), and
# p2996_hash.py reads it from bake, so this default was stale drift. The
# git-refs Renovate manager rewrites BOTH files in lockstep now that they
# hold the same SHA.
ARG CLANG_P2996_REF=7220baffd57ea5b0f8cf59bee494dd5b7cc2b748

# Self-contained compile toolchain (#160 T11): gcc/g++ via build-essential,
# cmake + ninja from apt (26.04 ships cmake ≥3.28, well past LLVM's 3.20
# floor), python3 (LLVM build requirement), ccache, git, and the LLVM
# optional-dep dev headers the previous base-tier build had.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      ca-certificates \
      ccache \
      cmake \
      git \
      ninja-build \
      python3 \
      zlib1g-dev \
      libedit-dev \
      libffi-dev \
      libncurses5-dev \
      libxml2-dev \
      libzstd-dev \
      swig

# Out-of-tree build (#222 PR-B): the source checkout (+ .git) and the CMake
# build tree live under /build/clang-p2996 (builder-only, NEVER shipped);
# ONLY the install prefix /opt/clang-p2996 is COPYd into p2996-export below.
# Before this, `git init .` + build + install all happened IN /opt/clang-p2996,
# so `COPY /opt/clang-p2996` grabbed the whole ~8.5 GB tree (source ~2.3 GB +
# build/ ~3.4 GB + .git ~0.25 GB) instead of the ~2.8 GB install prefix — a
# capability-preserving ~6 GB of pure packaging waste. The bloomberg/clang-p2996
# commit is still embedded in `clang --version` at build time (.git is present
# during the compile here, just excluded from the export), so the smoke ref-pin
# check (image.py) is unaffected.
WORKDIR /build/clang-p2996

RUN git init . && \
    git remote add origin "${CLANG_P2996_REPO}" && \
    git fetch --depth 1 origin "${CLANG_P2996_REF}" && \
    git checkout FETCH_HEAD

WORKDIR /build/clang-p2996/build

# cmake and ninja come from the builder's own apt toolchain (#160 T11).
# Build only X86 target to minimize compile time and binary size.
# ccache mount persists across builds — on SHA change, ~80% of objects
# are reusable, cutting rebuild time significantly vs cold cache.
# See issue #82 for further caching optimization (sccache, separate scope).
# `../llvm` resolves to /build/clang-p2996/llvm; install goes to the separate
# prefix /opt/clang-p2996 (the only thing exported).
RUN --mount=type=cache,target=/root/.cache/ccache,sharing=locked \
    cmake -G Ninja ../llvm \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/opt/clang-p2996 \
      -DCMAKE_C_COMPILER=gcc \
      -DCMAKE_CXX_COMPILER=g++ \
      -DLLVM_ENABLE_PROJECTS="clang;lld" \
      -DLLVM_ENABLE_RUNTIMES="libcxx;libcxxabi;libunwind" \
      -DLLVM_TARGETS_TO_BUILD=X86 \
      -DLLVM_CCACHE_BUILD=ON \
      -DLLVM_ENABLE_BINDINGS=OFF \
      -DLLVM_ENABLE_TERMINFO=OFF \
      -DLLVM_INCLUDE_BENCHMARKS=OFF \
      -DLLVM_INCLUDE_EXAMPLES=OFF \
      -DLLVM_INCLUDE_TESTS=OFF \
      -DCLANG_DEFAULT_CXX_STDLIB=libc++ && \
    ninja install

# Smoke test: verify clang-p2996 can parse reflection headers.
# Runs only on the cold compile path. Cached pulls skip this step —
# the cache image was built from this same stage, so its artifact was
# already validated at the time of its build.
RUN printf '#include <meta>\nint main(){return 0;}\n' >/tmp/refl.cpp && \
    /opt/clang-p2996/bin/clang++ \
      -std=c++2c \
      -freflection \
      -freflection-latest \
      -fexpansion-statements \
      -stdlib=libc++ \
      /tmp/refl.cpp \
      -fsyntax-only && \
    rm -f /tmp/refl.cpp

# ── p2996-export: scratch-based image holding ONLY the install prefix
# (~2.8 GB uncompressed). The out-of-tree build above keeps source + build/ +
# .git under /build, so this COPY genuinely grabs just the prefix (#222 PR-B).
# This is what gets pushed to GHCR as :p2996-<hash16> for cross-build reuse.
FROM scratch AS p2996-export
COPY --from=clang-builder-cold /opt/clang-p2996 /opt/clang-p2996

# ──── P2996_HASH_END ──── (sentinel for python/.../p2996_hash.py)

# ── final: combine base + reflection compilers ───────────────────────
# The published image is the devcontainer-runtime stage below (#160 T10);
# this stage stays the compiler-assembly layer it always was.
# Plain local stage names since #160 T11: on warm CI paths, bake-action
# injects `dev.contexts.devcontainer-base` / `dev.contexts.p2996-export`
# as digest-pinned docker-image:// contexts, which OVERRIDE these
# same-named local stages — no ARG indirection, no rebuild.
FROM devcontainer-base AS devcontainer

# Re-declared per stage: hadolint analyzes stages independently (DL4006 on
# the sha256sum pipe below), and the explicit SHELL also holds when CI
# substitutes the devcontainer-base named context.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# GCC-17 with P2996 reflection (precompiled .deb from jwakely trunk snapshot).
# Installs to /opt/gcc-latest/bin. kayari.org ships a rolling .deb tracking
# Ubuntu trunk; the rolling `gcc-latest.deb` 302-redirects to a dated,
# immutable filename (`gcc-latest_<ver>-<date>git<sha>.deb`). We pin that
# dated URL as the reproducibility handle — upstream publishes NO checksum or
# signature file (all 404), so the immutable dated filename IS the pin.
# Renovate bumps it via the `custom.gcc-latest` HTML datasource on the
# jwakely.github.io index (see renovate.json). Compatibility with the current
# base image is empirical; if `dpkg -i` fails, build from source.
# renovate: datasource=custom.gcc-latest depName=gcc-latest versioning=loose
ARG GCC_LATEST_DEB=gcc-latest_17.0.0-20260705git88752b86ff1a.deb
# Validation D (#160 T13): kayari publishes NO checksum or signature (all
# 404), so this locally-computed pin is the .deb's only integrity handle.
# NOT Renovate-managed (Renovate can't compute a sha): a GCC_LATEST_DEB bump
# leaves this stale, but the gcc-sha-repair workflow (#249) recomputes it from
# the newly-pinned .deb and commits the fix to the Renovate branch — the pin
# stays byte-exact without the old human-recompute friction. To repair by hand:
# `uv run --project python dotfiles-setup gcc-sha` (or `--check` to dry-run).
ARG GCC_LATEST_DEB_SHA256=2503ddace30a46c732b5a764f0d3a7cbae35666f4cc064d34485e0c10652f93a
# #222 PR-A (dev-hash only): the kayari .deb ships UNSTRIPPED backend
# executables — cc1plus 518M, cc1 480M, lto1 463M, lto-dump 463M each carry
# .debug_*+.symtab (probe-verified). `strip --strip-all` reclaims ~1.68 GB and
# keeps .dynsym (ELF stays EXEC → GCC plugins / dynamic linking unaffected).
# lib64 runtime libs are intentionally NOT stripped (keep-runtime-debug policy);
# the small hardlinked drivers (gcc/g++/cpp) and gcov* are left as-is. Stripped
# in the SAME RUN as dpkg -i, with a trivial compile (invokes the stripped
# cc1plus) as the loud post-condition — the reflection smoke below is the
# deeper functional gate.
RUN curl -fLOSs "https://kayari.org/gcc-latest/${GCC_LATEST_DEB}" && \
    echo "${GCC_LATEST_DEB_SHA256}  ${GCC_LATEST_DEB}" | sha256sum -c - && \
    dpkg -i "${GCC_LATEST_DEB}" && \
    rm -f "${GCC_LATEST_DEB}" && \
    test -x /opt/gcc-latest/bin/g++ || { echo "ERROR: gcc-latest binary missing after dpkg install"; exit 1; } && \
    find /opt/gcc-latest -type f \( -name cc1 -o -name cc1plus -o -name lto1 -o -name lto-dump \) -exec strip --strip-all {} + && \
    printf 'int main(){}\n' | /opt/gcc-latest/bin/g++ -x c++ - -o /tmp/gcc-strip-check && \
    rm -f /tmp/gcc-strip-check

# clang-p2996 (Bloomberg fork; local p2996-export stage on the cold path,
# digest-pinned :p2996-<hash16> registry context on the warm path)
COPY --from=p2996-export /opt/clang-p2996 /opt/clang-p2996

# Add reflection compilers to PATH; LD_RUN_PATH for gcc-latest runtime libs
ENV PATH="/opt/gcc-latest/bin:/opt/clang-p2996/bin:${PATH}" \
    LD_RUN_PATH="/opt/gcc-latest/lib64"

# Smoke test: GCC-16 reflection
RUN printf '#include <meta>\nint main(){return 0;}\n' >/tmp/refl-gcc.cpp && \
    /opt/gcc-latest/bin/g++ \
      -std=c++26 \
      -freflection \
      /tmp/refl-gcc.cpp \
      -fsyntax-only && \
    rm -f /tmp/refl-gcc.cpp

# Smoke test: clang-p2996 reflection
RUN printf '#include <meta>\nint main(){return 0;}\n' >/tmp/refl-clang.cpp && \
    /opt/clang-p2996/bin/clang++ \
      -std=c++2c \
      -freflection \
      -freflection-latest \
      -fexpansion-statements \
      -stdlib=libc++ \
      /tmp/refl-clang.cpp \
      -fsyntax-only && \
    rm -f /tmp/refl-clang.cpp

# ── devcontainer-runtime: the RUNTIME tool tier (#160 T9/T10) ─────────
# Locked dev tools shipped in the image but NOT needed to build it.
# MISE_ENV=runtime makes mise merge config.runtime.toml beside the base
# config.toml in $MISE_CONFIG_DIR (probe-verified additive discovery);
# the ENV persists into the final image so runtime containers keep
# loading the runtime tier. Editing mise-runtime.toml/.lock rebuilds
# only THIS thin stage — the base and p2996 caches stay warm. Both
# COPY inputs are hashed by bytes into dev-hash (COPY-input rule).
FROM devcontainer AS devcontainer-runtime

ENV MISE_ENV=runtime
COPY .devcontainer/mise-runtime.toml /usr/local/share/mise/config.runtime.toml
# Per-env lockfile (mise natively writes mise.<env>.lock beside mise.lock;
# regenerated by the lock-refresh staging under MISE_ENV=runtime).
COPY .devcontainer/mise-runtime.lock /usr/local/share/mise/mise.runtime.lock

RUN --mount=type=cache,id=mise-cache,target=/usr/local/share/mise/cache,sharing=locked \
    --mount=type=cache,id=uv-cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=secret,id=github_token \
    export MISE_INSTALL_MODE=system && \
    export UV_LINK_MODE=copy && \
    export LANG=C.UTF-8 && \
    export LC_ALL=C.UTF-8 && \
    if [ -f /run/secrets/github_token ]; then \
      GITHUB_TOKEN="$(cat /run/secrets/github_token)" && \
      export GITHUB_TOKEN && \
      export MISE_GITHUB_TOKEN="$GITHUB_TOKEN"; \
    fi && \
    mise install --system --locked -y && \
    mise reshim -f && \
    test -x "$(mise which gh)" || { echo "ERROR: runtime tier not installed — gh unresolvable, so config.runtime.toml was not discovered under MISE_ENV=runtime (check MISE_CONFIG_DIR layout + mise.runtime.lock)"; exit 1; } && \
    chmod -R 777 /usr/local/share/mise /usr/local/share/cargo /usr/local/share/rustup
