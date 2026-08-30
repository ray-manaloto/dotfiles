# syntax=docker/dockerfile:1.26@sha256:ecfaec9ed6d810b56388c508f4121597bfbba70d41a6dfeee4d8cad5f295fc32
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
ARG BASE_IMAGE=ubuntu:26.04@sha256:678c6550cc43645e08669028bc177f50be4e7c5b8cca677067b1914d4afc7a03

# Builder image for the clang-p2996 compile (#160 T11). DELIBERATELY a
# separate, rarely-bumped variable (NOT Renovate-tracked): its digest is a
# first-class p2996-hash input, so a bump forces the ~2h compiler rebuild —
# decoupled from routine BASE_IMAGE bumps. The builder never ships bytes
# into the final image (only /opt/clang-p2996 is exported), so pinning it
# older than BASE_IMAGE is ABI-safe while both are the same ubuntu series.
# Keep in lockstep with docker-bake.hcl's BUILDER_IMAGE default.
ARG BUILDER_IMAGE=ubuntu:26.04@sha256:678c6550cc43645e08669028bc177f50be4e7c5b8cca677067b1914d4afc7a03

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
ARG MISE_VERSION=2026.8.14
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
# apt.llvm.org — the LLVM 22 source (#251). Ubuntu resolute/universe froze at
# 22.1.2; this suite carries 22.1.8. Despite the site self-describing as
# "nightly", the NUMBERED suites build RELEASED TAGS: probed 2026-07-15,
# `llvmorg-22.1.8` points at commit ca7933e47d3a and the pinned versions in
# mise-system.toml embed exactly that commit. "Nightly" names the packaging
# cadence, not the source tree.
#
# Only `-22` is enabled. The UNNUMBERED suite (`llvm-toolchain-<codename>`) is
# LLVM 23 trunk and sorts HIGHER, so enabling it would silently win every
# unversioned package; `-23` does not exist (404).
#
# MUST run BEFORE the bootstrap apply below — mise resolves `[bootstrap.packages]`
# against the image's apt sources, so the repo has to exist first.
# `[bootstrap.repos]` cannot do this: that is git repos, not apt sources.
#
# Key handling: `Signed-By` scopes the key to THIS repo only (the deprecated
# `apt-key add` / `trusted.gpg.d` route trusts it for every source). The
# fingerprint is asserted BEFORE the key is trusted — a build-time self-check
# per .devcontainer/AGENTS.md, so a swapped key fails the build loudly instead
# of silently installing signed-by-someone-else packages. gnupg is declared in
# [bootstrap.packages] but installed by the apply BELOW, so it is pulled here.
# The codename is read from /etc/os-release, never hardcoded, so a BASE_IMAGE
# bump cannot silently point at the wrong dist.
#
# The candidate post-condition captures `apt-cache policy` into a VARIABLE and
# matches with `case`, NOT `... | grep -q`. Under this image's
# `SHELL [... "-o" "pipefail" ...]`, `grep -q` exits on first match and closes
# the pipe, apt-cache takes SIGPIPE (141), and pipefail propagates 141 as the
# pipeline's status — so the check FAILS *because* the match succeeded. That is
# exactly how this build broke on its first CI run (#289); probed with control
# arms: early match -> 141, pipefail off -> 0, match at end-of-stream -> 0.
ARG LLVM_APT_SIGNING_FINGERPRINT=6084F3CF814B57C1CF12EFD515CF4D18AF4F7421
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && apt-get install -y --no-install-recommends gnupg && \
    install -d -m 0755 /etc/apt/keyrings && \
    curl -fsSL https://apt.llvm.org/llvm-snapshot.gpg.key \
      -o /etc/apt/keyrings/apt-llvm-org.asc && \
    actual_fingerprint="$(gpg --show-keys --with-colons --with-fingerprint \
      /etc/apt/keyrings/apt-llvm-org.asc | awk -F: '/^fpr:/{print $10; exit}')" && \
    if [ "$actual_fingerprint" != "$LLVM_APT_SIGNING_FINGERPRINT" ]; then \
      echo "FAIL: apt.llvm.org key fingerprint $actual_fingerprint != pinned $LLVM_APT_SIGNING_FINGERPRINT" >&2; \
      exit 1; \
    fi && \
    codename="$(. /etc/os-release && echo "$VERSION_CODENAME")" && \
    printf 'Types: deb\nURIs: https://apt.llvm.org/%s/\nSuites: llvm-toolchain-%s-22\nComponents: main\nSigned-By: /etc/apt/keyrings/apt-llvm-org.asc\n' \
      "$codename" "$codename" > /etc/apt/sources.list.d/apt-llvm-org.sources && \
    apt-get update && \
    clang_policy="$(apt-cache policy clang-22)" && \
    case "$clang_policy" in \
      *apt.llvm.org*) ;; \
      *) echo "FAIL: apt.llvm.org is not a candidate source for clang-22" >&2; \
         echo "$clang_policy" >&2; exit 1 ;; \
    esac

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
# BuildKit's automatic target-architecture arg (#698). DECLARED, never defaulted:
# an automatic ARG a stage does not declare expands to the EMPTY STRING, so an
# undeclared TARGETARCH would send every architecture — amd64 included — down
# the else-branch below and silently drop graphviz from the image it works on.
# Gated by `test_every_stage_that_reads_targetarch_also_declares_it`.
ARG TARGETARCH
# Re-assert the stage shell: hadolint 2.15.x forgets a stage's SHELL after any
# mid-stage ARG (minimal repro: FROM + SHELL bash + ARG X=y + RUN with a bashism
# flags SC3011; drop the ARG and it is clean) and then wrongly lints later RUNs
# as POSIX sh. Semantically a no-op — the stage shell is already bash (line 83).
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# Pure && chain (any failing step aborts the build loudly); explicit /tmp paths
# avoid a `cd` (hadolint DL3003). SVG/PNG/neato renders to /dev/null exercise the
# core+gd plugins and dot+neato layout engines; the trailing grep asserts v15.
# The cmake .deb declares NO deps, so we install every runtime lib explicitly:
# libltdl7/libexpat1/zlib1g are the `dot` binary's own core deps (the minimal
# devcontainer-base lacks libltdl7 once apt:graphviz is gone → dot would fail to
# start); libgd3+libcairo2 back the gd plugin (png/gif); libgts backs the neato/
# fdp/circo/twopi layout engines. Verified on a bare ubuntu:26.04 amd64 base.
#
# amd64 ONLY (#698). Upstream publishes four Linux debs — ubuntu_22.04 through
# ubuntu_26.04 — and every one is amd64; the only arm64 artefact in the 15.1.0
# release is a macOS .pkg (probed 2026-08-10, GitLab package 62359347, 44 files).
# So other architectures take apt's graphviz, which is the lean floor this deb
# was chosen to beat by ~21 MB in the first place. The version assertion follows
# the branch: amd64 asserts the pinned major, apt asserts what dpkg says it just
# installed — two independent sources either way, never a restated literal.
#
# `libgvplugin-neato-layout8` is NOT optional on the apt path. Ubuntu splits the
# layout engines into separate plugin packages and `graphviz` Depends on only
# `libgvplugin-gd8` + `libgvplugin-pango8`, so `--no-install-recommends` yields
# an install where `dot` works and `neato` reports "There is no layout engine
# support" — the deb path never hits this because it installs its plugin deps
# by hand. Measured on the digest-pinned arm64 base 2026-08-10: without it the
# neato render fails and the whole RUN exits 1 (this is what reddened #703);
# with it, svg/png/neato/version all pass under `set -euo pipefail`.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    if [ "${TARGETARCH}" = "amd64" ]; then \
      curl -fLSs -o "/tmp/${GRAPHVIZ_DEB}" "https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/${GRAPHVIZ_VERSION}/${GRAPHVIZ_DEB}" && \
      echo "${GRAPHVIZ_DEB_SHA256}  /tmp/${GRAPHVIZ_DEB}" | sha256sum -c - && \
      apt-get install -y --no-install-recommends "/tmp/${GRAPHVIZ_DEB}" libltdl7 libexpat1 zlib1g libgd3 libgts-0.7-5t64 libcairo2 && \
      rm -f "/tmp/${GRAPHVIZ_DEB}" && \
      rm -f /usr/lib/graphviz/libgvplugin_{ascii,devil,gdk,gs,kitty,lasi,pango,poppler,rsvg,vt,webp,xlib}.so.8 && \
      rm -f /usr/lib/graphviz/config8 && \
      expected_major="${GRAPHVIZ_VERSION%%.*}"; \
    else \
      apt-get install -y --no-install-recommends graphviz libgvplugin-neato-layout8 && \
      expected_major="$(dpkg-query -W -f='${Version}' graphviz | sed 's/^[0-9]*://; s/\..*//')"; \
    fi && \
    dot -c && \
    printf 'digraph{a->b->c;a->c}' | dot -Tsvg -o /dev/null && \
    printf 'digraph{a->b}' | dot -Tpng -o /dev/null && \
    printf 'graph{a--b--c--a}' | neato -Tsvg -o /dev/null && \
    dot_version="$(dot -V 2>&1)" && \
    case "$dot_version" in *"version ${expected_major}."*) ;; *) echo "ERROR: dot reports '$dot_version', expected major ${expected_major}" >&2; exit 1;; esac

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
RUN clangxx_version="$(/usr/lib/llvm-22/bin/clang++ --version)" && \
    case "$clangxx_version" in *"version 22"*) ;; *) echo "ERROR: unexpected clang++ version: $clangxx_version" >&2; exit 1;; esac && \
    printf '#include <cstdio>\nint main(){printf("ok\\n");return 0;}\n' > /tmp/llvmcheck.cpp && \
    /usr/lib/llvm-22/bin/clang++ -fsanitize=address,undefined /tmp/llvmcheck.cpp -o /tmp/llvmcheck && \
    llvmcheck_out="$(/tmp/llvmcheck)" && \
    [ "$llvmcheck_out" = "ok" ] && \
    test -x /usr/lib/llvm-22/bin/clangd && \
    test -x /usr/lib/llvm-22/bin/clang-tidy && \
    test -x /usr/lib/llvm-22/bin/clang-format && \
    test -x /usr/lib/llvm-22/bin/lld && \
    test -x /usr/lib/llvm-22/bin/lldb && \
    llvm_config_version="$(/usr/lib/llvm-22/bin/llvm-config --version)" && \
    grep -q '^22' <<<"$llvm_config_version" && \
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

# Architecture EXECUTION check (#698). Every self-check above counts or stats:
# `mise ls --installed | wc -l`, `test -d`, a non-empty shims dir. None of them
# can see the defect this exists for — a tool resolved for the wrong platform
# downloads, installs, lists and stats exactly like a correct one. The only
# thing it cannot do is RUN, so this runs it.
#
# Assert the capability, never a symptom ([[probes-need-a-control-arm]] rule 9):
# no `uname -m` comparison, no ELF-header sniffing, no version string — each of
# those binds something we do not own and goes quietly dead when it changes.
# A binary that executes on this CPU is the whole claim.
#
# The names are cross-checked against `.config/mise/conf.d/shared.toml` by
# `test_every_execution_probe_is_a_tool_the_image_installs`, so a tool rename
# fails a unit test rather than a 30-minute base build. They deliberately span
# backends (aqua/ubi/github/cargo) — the backend is what resolves the platform,
# so one probe per download path is what makes this more than a spot check.
ARG ARCH_EXEC_PROBES="jq shfmt hk pkl uv chezmoi"
RUN checked=0; \
    for probe in ${ARCH_EXEC_PROBES}; do \
      bin="/usr/local/share/mise/shims/${probe}"; \
      test -x "$bin" || { echo "ERROR: expected mise shim ${probe} is missing"; exit 1; }; \
      "$bin" --version >/dev/null || { echo "ERROR: ${probe} INSTALLED but did not execute on $(uname -m) — its tool was resolved for another architecture (#698)"; exit 1; }; \
      checked=$((checked + 1)); \
    done; \
    test "$checked" -ge 3 || { echo "ERROR: architecture execution check ran only ${checked} probe(s) — ARCH_EXEC_PROBES is empty or was not expanded"; exit 1; }; \
    echo "OK: ${checked} mise-installed tools execute natively on $(uname -m)"

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
ARG CLANG_P2996_REF=060be17654102019e14810c3f948ef85a490755f

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

# BuildKit's automatic target-architecture arg — DECLARED, never defaulted, for
# the same reason as the graphviz gate above: an automatic ARG a stage does not
# declare expands to the EMPTY STRING. Here that lands in the `*)` arm below and
# fails the build loudly, which is the whole point — the alternative is a clang
# that silently cannot emit code for the machine it was built for.
ARG TARGETARCH

# cmake and ninja come from the builder's own apt toolchain (#160 T11).
# Build ONE backend — the target machine's — to minimise compile time and binary
# size; LLVM's default is every backend it knows.
#
# ⚠️ This was `=X86` unconditionally until #703, and it is #698's defect class a
# layer deeper: an architecture pinned as a literal that survived the dual-arch
# split. On the arm64 runner it built a clang that cannot emit aarch64, and the
# runtimes stage then configures USING that clang — so every compile probe fails
# (`Looking for fopen in c - not found`) and `libunwind` kills the configure.
# 52 minutes in, and nothing before that point says a word.
#
# It is invisible to `no_platform_literals`, whose pattern is a platform TRIPLE
# (`linux/amd64`); `X86` is an LLVM BACKEND name. Three vocabularies now name
# this one axis — docker's `amd64`/`arm64`, uname's `x86_64`/`aarch64`, and
# LLVM's `X86`/`AArch64` — and a gate that knows one cannot see the others.
# `tests/test_image_arch.py` gates this mapping against
# `platform_target.LLVM_TARGETS`.
#
# ccache mount persists across builds — on SHA change, ~80% of objects
# are reusable, cutting rebuild time significantly vs cold cache.
# See issue #82 for further caching optimization (sccache, separate scope).
# `../llvm` resolves to /build/clang-p2996/llvm; install goes to the separate
# prefix /opt/clang-p2996 (the only thing exported).
RUN --mount=type=cache,target=/root/.cache/ccache,sharing=locked \
    case "${TARGETARCH}" in \
      amd64) llvm_target=X86 ;; \
      arm64) llvm_target=AArch64 ;; \
      *) echo "ERROR: no LLVM backend mapped for TARGETARCH='${TARGETARCH}' — an empty value means this stage stopped declaring \`ARG TARGETARCH\`" >&2; exit 1 ;; \
    esac && \
    cmake -G Ninja ../llvm \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/opt/clang-p2996 \
      -DCMAKE_C_COMPILER=gcc \
      -DCMAKE_CXX_COMPILER=g++ \
      -DLLVM_ENABLE_PROJECTS="clang;lld" \
      -DLLVM_ENABLE_RUNTIMES="libcxx;libcxxabi;libunwind" \
      -DLLVM_TARGETS_TO_BUILD="${llvm_target}" \
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
ARG GCC_LATEST_DEB=gcc-latest_17.0.0-20260816git8df013222dff.deb
# Validation D (#160 T13): kayari publishes NO checksum or signature (all
# 404), so this locally-computed pin is the .deb's only integrity handle.
# NOT Renovate-managed (Renovate can't compute a sha): a GCC_LATEST_DEB bump
# leaves this stale, but the gcc-sha-repair workflow (#249) recomputes it from
# the newly-pinned .deb and commits the fix to the Renovate branch — the pin
# stays byte-exact without the old human-recompute friction. To repair by hand:
# `uv run --project python dotfiles-setup gcc-sha` (or `--check` to dry-run).
ARG GCC_LATEST_DEB_SHA256=a9c2f9f7d6189ccff55ccead9ae949d29d45fa32f93268de82ce319223aaa506
# amd64 ONLY, permanently (#698). This is not a gap upstream may close — the
# maintainer states the policy on the index page: "Only the C and C++ compilers
# are included, and only for x86_64, in a single large package." Probed
# 2026-08-10: one .deb, and the page's arch-token counts are x86_64=1, arm64=0.
# The named alternative (Fedora Rawhide's GCC-trunk COPR, "built for more
# architectures") ships RPMs for Rawhide and cannot serve an Ubuntu 26.04 image.
#
# Consequence, decided by Ray 2026-08-10: arm64 ships WITHOUT gcc-latest, and
# its modern-GCC slot goes to conda-forge gcc — which does publish linux-aarch64
# (204 files at 16.1.0, identical coverage to linux-64). So the "exactly 3 gcc
# compilers" invariant is ARCHITECTURE-DEPENDENT: 3 on amd64, 2 on arm64.
# amd64: distro gcc + gcc-latest .deb + (as of #841) no longer an unintended
# conda-forge gxx — conda:gxx is now pinned 16.2.0 and os=["linux/arm64"]-scoped
# in mise-system.toml, so amd64 stops picking it up as a side effect of conda
# resolving with no arch pin. arm64: distro gcc + conda-forge gxx 16.2.0.
# clang-p2996 is unaffected — it is built from source and is portable.
ARG TARGETARCH
# #222 PR-A (dev-hash only): the kayari .deb ships UNSTRIPPED backend
# executables — cc1plus 518M, cc1 480M, lto1 463M, lto-dump 463M each carry
# .debug_*+.symtab (probe-verified). `strip --strip-all` reclaims ~1.68 GB and
# keeps .dynsym (ELF stays EXEC → GCC plugins / dynamic linking unaffected).
# lib64 runtime libs are intentionally NOT stripped (keep-runtime-debug policy);
# the small hardlinked drivers (gcc/g++/cpp) and gcov* are left as-is. Stripped
# in the SAME RUN as dpkg -i, with a trivial compile (invokes the stripped
# cc1plus) as the loud post-condition — the reflection smoke below is the
# deeper functional gate.
RUN if [ "${TARGETARCH}" != "amd64" ]; then \
      echo "gcc-latest: SKIPPED on ${TARGETARCH} — kayari.org publishes x86_64 only (#698)"; \
    else \
      curl -fLOSs "https://kayari.org/gcc-latest/${GCC_LATEST_DEB}" && \
      echo "${GCC_LATEST_DEB_SHA256}  ${GCC_LATEST_DEB}" | sha256sum -c - && \
      dpkg -i "${GCC_LATEST_DEB}" && \
      rm -f "${GCC_LATEST_DEB}" && \
      { test -x /opt/gcc-latest/bin/g++ || { echo "ERROR: gcc-latest binary missing after dpkg install"; exit 1; }; } && \
      find /opt/gcc-latest -type f \( -name cc1 -o -name cc1plus -o -name lto1 -o -name lto-dump \) -exec strip --strip-all {} + && \
      printf 'int main(){}\n' | /opt/gcc-latest/bin/g++ -x c++ - -o /tmp/gcc-strip-check && \
      rm -f /tmp/gcc-strip-check; \
    fi

# clang-p2996 (Bloomberg fork; local p2996-export stage on the cold path,
# digest-pinned :p2996-<hash16> registry context on the warm path)
COPY --from=p2996-export /opt/clang-p2996 /opt/clang-p2996

# Add reflection compilers to PATH; LD_RUN_PATH for gcc-latest runtime libs
ENV PATH="/opt/gcc-latest/bin:/opt/clang-p2996/bin:${PATH}" \
    LD_RUN_PATH="/opt/gcc-latest/lib64"

# Smoke test: GCC-17 reflection. Skipped where gcc-latest itself is skipped —
# an unconditional check here would fail the arm64 build on a compiler upstream
# never shipped, which is a false accusation, not a finding (#698).
RUN if [ "${TARGETARCH}" != "amd64" ]; then \
      echo "gcc-latest reflection smoke: SKIPPED on ${TARGETARCH} (compiler not installed)"; \
    else \
      printf '#include <meta>\nint main(){return 0;}\n' >/tmp/refl-gcc.cpp && \
      /opt/gcc-latest/bin/g++ \
        -std=c++26 \
        -freflection \
        /tmp/refl-gcc.cpp \
        -fsyntax-only && \
      rm -f /tmp/refl-gcc.cpp; \
    fi

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
