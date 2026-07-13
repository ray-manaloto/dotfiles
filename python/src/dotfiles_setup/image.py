"""Image smoke test and metrics logic for devcontainer validation."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import os
import re
import shlex
import subprocess
import sys
import time
import tomllib
import zlib
from datetime import datetime
from typing import TYPE_CHECKING, Any

from dotfiles_setup import _project_root
from dotfiles_setup.p2996_hash import _extract_bake_variable

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

logger = logging.getLogger(__name__)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def resolve_expected_p2996_ref() -> str:
    """Resolve the clang-p2996 ref the image is expected to be built from.

    Mirrors the hash-command resolution (main.py ``_hash_command_handlers``):
    a Phase D (#120) ``CLANG_P2996_REF`` env override wins; otherwise the
    committed ``docker-bake.hcl`` pin is authoritative. Fails loud if neither
    is available — a silently-skipped ref check would reintroduce exactly the
    false-positive this guard exists to prevent.
    """
    override = os.environ.get("CLANG_P2996_REF")
    if override:
        return override
    bake_path = _project_root() / "docker-bake.hcl"
    return _extract_bake_variable(bake_path.read_text(), "CLANG_P2996_REF")


# The per-file HEAD/merge-base identity resolvers now live with the tier-1
# identity block (``resolve_expected_identity_head`` /
# ``resolve_expected_identity_at_base``, below ``resolve_declared_tools``): the
# Dockerfile COPYs each build input verbatim into the image, so its sha256 is a
# cheap image-identity fingerprint that catches a stale/cached overlay smoked
# against old content (#223 folded the config/runtime scalar resolvers into the
# three-file map ``IDENTITY_IMAGE_PATHS``).

# System mise config inside the image — the Dockerfile COPY target and the
# ``source.path`` that ``mise ls --json`` attributes system tools to.
SYSTEM_CONFIG_FILE = "/usr/local/share/mise/config.toml"
# The shared conf.d fragment (#160 T5) is COPYd alongside and merged into the
# system config; mise attributes its 20 tools to THIS source path, so the
# declared/installed comparison must count both files.
SHARED_CONFIG_FILE = "/usr/local/share/mise/conf.d/shared.toml"
# The runtime tier config (#160 T9/T10) — discovered beside config.toml when
# MISE_ENV=runtime (baked as ENV in the final image); its tools are attributed
# to this source path.
RUNTIME_CONFIG_FILE = "/usr/local/share/mise/config.runtime.toml"


def _tool_requested_version(spec: str | dict[str, Any]) -> str:
    """Requested version string from a mise ``[tools]`` entry value.

    Handles both the bare form (``tool = "latest"``) and the table form
    (``tool = { version = "latest", depends = [...] }``).
    """
    if isinstance(spec, str):
        return spec
    version = spec.get("version")
    if not isinstance(version, str):
        msg = f"mise [tools] entry lacks a string 'version': {spec!r}"
        raise TypeError(msg)
    return version


def parse_declared_tools(config_text: str) -> dict[str, str]:
    """Parse ``[tools]`` from a mise-system.toml document.

    Returns ``{tool_key: requested_version}``. Keys preserve the backend prefix
    verbatim (``conda:llvm``, ``npm:renovate``, bare ``python``) so they line up
    1:1 with ``mise ls --json`` keys — that is what makes the (tool, backend,
    version) comparison exact rather than name-only.
    """
    data = tomllib.loads(config_text)
    tools = data.get("tools", {})
    return {key: _tool_requested_version(spec) for key, spec in tools.items()}


def resolve_declared_tools() -> dict[str, str]:
    """Declared image tool set (base + shared fragment + runtime tier).

    All three files are COPYd into the image and merged by mise (#160
    T5/T9): the shared fragment supplies the 20 exact-pinned host↔image
    tools, mise-system.toml the base tier, mise-runtime.toml the runtime
    tier (loaded via MISE_ENV=runtime). The declared set is their union.
    """
    root = _project_root()
    declared = parse_declared_tools(
        (root / ".devcontainer" / "mise-system.toml").read_text()
    )
    declared.update(
        parse_declared_tools(
            (root / ".config" / "mise" / "conf.d" / "shared.toml").read_text()
        )
    )
    declared.update(
        parse_declared_tools((root / ".devcontainer" / "mise-runtime.toml").read_text())
    )
    return declared


# Image build-input files whose in-image copy is byte-identical to the repo
# file (verbatim Dockerfile COPY), keyed by repo-relative path -> the in-image
# location expressed RELATIVE to the mise config dir. The system config uses the
# ``@SYS@`` sentinel so the smoke reads ``$MISE_SYSTEM_CONFIG_FILE`` directly
# (#148) rather than a reconstructed path. This map is the single source of
# truth for the tier-1 identity block, shared by the CI no-mount smoke and the
# devcontainer smoke (#223) so both assert the SAME three build inputs.
IDENTITY_IMAGE_PATHS: dict[str, str] = {
    ".devcontainer/mise-system.toml": "@SYS@",
    ".config/mise/conf.d/shared.toml": "conf.d/shared.toml",
    ".devcontainer/mise-runtime.toml": "config.runtime.toml",
}


def resolve_expected_identity_head() -> dict[str, str]:
    """Expected in-image hashes for the CI smoke (image built from branch HEAD).

    CI smokes the image it JUST built from the branch, so the in-image build
    inputs are the branch-HEAD files — the expectation is a raw sha256 of the
    worktree file (identical to origin/main on main). The devcontainer path
    uses :func:`resolve_expected_identity_at_base` instead (merge-base aware),
    because a local base predates a branch's image-input bump.
    """
    root = _project_root()
    return {
        rel: hashlib.sha256((root / rel).read_bytes()).hexdigest()
        for rel in IDENTITY_IMAGE_PATHS
    }


def resolve_expected_identity_at_base() -> dict[str, str]:
    """Expected in-image hashes for the devcontainer smoke (merge-base base).

    The local base predates a branch's image-input bump (the branch's base is
    built by its own PR CI, never locally), so tier-1 identity must expect the
    MERGE-BASE blob for a branch-modified input and the committed file otherwise
    — exactly :func:`identity_expected_hash`. Branch identity is validated by the
    PR CI build+smoke, which builds from HEAD
    (:func:`resolve_expected_identity_head`).
    """
    root = _project_root()
    return {rel: identity_expected_hash(root, rel) for rel in IDENTITY_IMAGE_PATHS}


def _format_identity_lines(expected_identity: Mapping[str, str]) -> str:
    """Tab-separated ``repo_rel``/``img_rel``/``hash`` lines for the smoke block.

    ``img_rel`` comes from :data:`IDENTITY_IMAGE_PATHS`; all three fields are
    non-empty (the system file uses the ``@SYS@`` sentinel) so the in-script
    ``IFS=<tab> read`` never collapses adjacent tabs. An unknown build-input key
    is a hard error, never a silent drop — a dropped identity line would be an
    invisible false-green.
    """
    unknown = set(expected_identity) - set(IDENTITY_IMAGE_PATHS)
    if unknown:
        msg = f"unknown identity build-input(s): {sorted(unknown)}"
        raise ValueError(msg)
    return "\n".join(
        f"{rel}\t{IDENTITY_IMAGE_PATHS[rel]}\t{expected_identity[rel]}"
        for rel in sorted(expected_identity)
    )


def installed_tools_from_mise_ls(
    mise_ls_json: str,
    config_paths: tuple[str, ...] = (
        SYSTEM_CONFIG_FILE,
        SHARED_CONFIG_FILE,
        RUNTIME_CONFIG_FILE,
    ),
) -> dict[str, str]:
    """Extract ``{tool_key: requested_version}`` from ``mise ls --json`` output.

    Filters to entries that are (a) sourced from one of ``config_paths`` (the
    system config + the shared conf.d fragment, so a user/global overlay's tools
    don't pollute the comparison) and (b) actually ``installed`` — a declared-
    but-failed install therefore shows up as a *missing* tool in the diff
    instead of silently passing.
    """
    doc = json.loads(mise_ls_json)
    result: dict[str, str] = {}
    for key, entries in doc.items():
        for entry in entries:
            source = entry.get("source") or {}
            if source.get("path") in config_paths and entry.get("installed"):
                result[key] = entry.get("requested_version", "")
    return result


def diff_tool_sets(
    declared: Mapping[str, str],
    installed: Mapping[str, str],
) -> list[str]:
    """Human-readable diff lines; empty ⇔ exact (tool, backend, version) match.

    Compares against the *requested* version (deterministic, equal to the
    declared string) rather than the resolved version, because ``latest`` tools
    drift by design — asserting the resolved version would false-fail on every
    upstream release.
    """
    lines: list[str] = []
    for key in sorted(set(declared) | set(installed)):
        want = declared.get(key)
        have = installed.get(key)
        if want is None:
            lines.append(f"+ {key}: installed ({have!r}) but NOT declared")
        elif have is None:
            lines.append(f"- {key}: declared ({want!r}) but NOT installed")
        elif want != have:
            lines.append(f"~ {key}: declared {want!r} but installed {have!r}")
    return lines


def _format_expected_tool_lines(declared: Mapping[str, str]) -> str:
    """Tab-separated ``key``/``version`` lines for the injected smoke assertion.

    One line per tool, tab-joined, sorted with Python's default (code-point)
    order so it matches an in-script ``LC_ALL=C sort`` byte comparison — all
    tool keys are ASCII.
    """
    return "\n".join(sorted(f"{key}\t{ver}" for key, ver in declared.items()))


def _is_emulated(target_platform: str) -> bool:
    """True when the host CPU cannot *natively* execute ``target_platform``.

    ThreadSanitizer's shadow-memory layout requires a native x86_64 process;
    under Rosetta/QEMU emulation (arm64 host running an amd64 image) the TSan
    RUN aborts with an ASLR/"unexpected memory mapping" fatal. We detect the
    host↔target arch mismatch in Python — which knows the host arch via
    ``os.uname()`` — rather than probing ``binfmt_misc`` in-container, because
    the emulator marker is not reliably visible inside the container.
    """
    host = os.uname().machine.lower()
    host_amd64 = host in {"x86_64", "amd64"}
    host_arm = host in {"arm64", "aarch64"}
    platform_lc = target_platform.lower()
    target_amd64 = "amd64" in platform_lc or "x86_64" in platform_lc
    target_arm = "arm64" in platform_lc or "aarch64" in platform_lc
    if target_amd64:
        return not host_amd64
    if target_arm:
        return not host_arm
    return False


def _run(
    cmd: list[str],
    *,
    capture: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
    )


_TIER1_MISE_PATHS = """\
# #148: the base SYSTEM config ($MISE_SYSTEM_CONFIG_FILE = the Dockerfile COPY
# target /usr/local/share/mise/config.toml), NOT ${MISE_CONFIG_DIR}/config.toml
# — MISE_CONFIG_DIR is overridden at runtime to the user config dir, a
# different (chezmoi-rendered) file that false-fails identity on a current base.
MISE_CFG="${MISE_SYSTEM_CONFIG_FILE:-/usr/local/share/mise/config.toml}"
MISE_DIR="$(dirname "$MISE_CFG")"
# #160 T5: the shared conf.d fragment is merged into the system config; its
# tools are attributed to this path by `mise ls --json`, so the tool-set diff
# must count both sources.
MISE_SHARED_CFG="$MISE_DIR/conf.d/shared.toml"
# #160 T9/T10: the runtime tier config, discovered via MISE_ENV=runtime
# (baked as image ENV); its tools attribute to this source path.
MISE_RUNTIME_CFG="$MISE_DIR/config.runtime.toml"
"""

# #223: ONE identity loop over every verbatim-COPYd build input (mise-system,
# the shared conf.d fragment, mise-runtime), replacing the two per-file scalar
# checks. Expected hashes are injected as data ($EXPECTED_IDENTITY:
# repo_rel<TAB>img_rel<TAB>hash lines); the @SYS@ sentinel reads
# $MISE_SYSTEM_CONFIG_FILE directly (#148). A stale/cached overlay smoked
# against old content fails here. Raw string: `\\t`/backslashes stay literal.
_TIER1_IDENTITY_BLOCK = r"""echo "=== image identity (build-input hashes) ==="
if [ -n "$EXPECTED_IDENTITY" ]; then
  while IFS="$(printf '\t')" read -r repo_rel img_rel want; do
    [ -n "$repo_rel" ] || continue
    if [ "$img_rel" = "@SYS@" ]; then
      img_file="$MISE_CFG"
    else
      img_file="$MISE_DIR/$img_rel"
    fi
    if [ ! -f "$img_file" ]; then
      echo "FAIL: in-image build input $img_file missing (from $repo_rel)"
      exit 1
    fi
    actual_identity_sha256=$(sha256sum "$img_file" | cut -d' ' -f1)
    if [ "$actual_identity_sha256" != "$want" ]; then
      echo "FAIL: in-image $img_file $actual_identity_sha256 !=" \
           "$repo_rel $want (stale image — rebuild)"
      exit 1
    fi
    echo "OK: image built from current $repo_rel ($actual_identity_sha256)"
  done <<< "$EXPECTED_IDENTITY"
else
  echo "SKIP: no expected identity injected (identity guard dormant)"
fi
"""

_TIER1_MISE_LS_TOOLSET = """\
echo "=== mise ls (check no missing — system config only) ==="
mise_output=$(mise ls 2>&1)
missing=$(echo "$mise_output" | grep -c "(missing)" || true)
echo "Missing tools: $missing"
if [ "$missing" -gt 0 ]; then
  echo "$mise_output" | grep "(missing)"
  exit 1
fi
echo "=== exact tool-set assertion (declared vs installed, system config) ==="
# #143: assert the EXACT (tool, backend, requested-version) set declared in
# mise-system.toml is what's installed from the system config — not merely that
# mise reports zero (missing). The declared set is injected as data
# ($EXPECTED_TOOL_REQUESTS, computed in python: parse_declared_tools); this
# block only does a mechanical set diff (zero-bash-logic). Comparison is on the
# requested version (deterministic == declared) not the resolved version, which
# drifts for `latest` by design. LC_ALL=C sort => byte order matching python's.
if [ -n "$EXPECTED_TOOL_REQUESTS" ]; then
  installed_tool_requests=$(mise ls --json \
    | jq -r --arg cfg "$MISE_CFG" --arg shared "$MISE_SHARED_CFG" \
         --arg runtime "$MISE_RUNTIME_CFG" '
    to_entries[] | .key as $k | .value[]
    | select((.source.path == $cfg or .source.path == $shared
              or .source.path == $runtime) and .installed == true)
    | "\\($k)\\t\\(.requested_version)"' | LC_ALL=C sort -u)
  if ! diff <(printf '%s\n' "$EXPECTED_TOOL_REQUESTS") \
            <(printf '%s\n' "$installed_tool_requests"); then
    echo "FAIL: installed tool set differs from mise-system.toml [tools]" \
         "('<' declared-not-installed; '>' installed-not-declared/version-drift)"
    exit 1
  fi
  echo "OK: installed tool set matches mise-system.toml [tools]"
else
  echo "SKIP: no expected tool set injected (tool-set guard dormant)"
fi
"""

# The tier-1 CORE: image identity + no-missing + exact tool-set. This is the
# single source of truth shared VERBATIM by the CI no-mount smoke
# (:func:`build_smoke_script`) and the devcontainer smoke
# (:func:`build_tier1_script`, emitted by ``image smoke-script --tier 1``) so
# the two paths cannot diverge (#223). Only the injected DATA differs by caller
# (HEAD hashes/tools for CI; merge-base for the devcontainer).
_TIER1_CORE_BODY = _TIER1_MISE_PATHS + _TIER1_IDENTITY_BLOCK + _TIER1_MISE_LS_TOOLSET


def _tier1_var_lines(
    expected_identity: Mapping[str, str] | None,
    expected_tools: Mapping[str, str] | None,
) -> str:
    """Injected-data header lines the tier-1 core reads ($EXPECTED_*)."""
    identity_blob = (
        _format_identity_lines(expected_identity) if expected_identity else ""
    )
    tool_lines = _format_expected_tool_lines(expected_tools) if expected_tools else ""
    return (
        f"EXPECTED_IDENTITY={shlex.quote(identity_blob)}\n"
        f"EXPECTED_TOOL_REQUESTS={shlex.quote(tool_lines)}\n"
    )


def build_tier1_script(
    *,
    expected_identity: Mapping[str, str] | None = None,
    expected_tools: Mapping[str, str] | None = None,
) -> str:
    """Standalone tier-1 core smoke script: image identity + exact tool-set.

    Emitted by ``image smoke-script --tier 1`` for ``scripts/devcontainer-smoke``
    to run in-container, and reused VERBATIM (the same :data:`_TIER1_CORE_BODY`)
    by :func:`build_smoke_script` for the CI no-mount smoke — the #223 single
    source of truth for tier-1 logic. Both guards are dormant (empty injected
    var) when their data is unset, so an unpopulated call is a no-op, never a
    false green.
    """
    return (
        "set -euo pipefail\n"
        + _tier1_var_lines(expected_identity, expected_tools)
        + _TIER1_CORE_BODY
    )


def build_smoke_script(
    expected_p2996_ref: str,
    *,
    expected_identity: Mapping[str, str] | None = None,
    expected_tools: Mapping[str, str] | None = None,
    emulated: bool = False,
) -> str:
    """Build the inline CI (no-mount) smoke test script.

    Composes the shared tier-1 core (:data:`_TIER1_CORE_BODY` — image identity
    + exact tool-set, #223) with the CI-only tail (hk validate, sanitizers,
    reflection compilers, AI CLIs, zero-warning). The devcontainer smoke runs
    the SAME core via :func:`build_tier1_script`.

    ``expected_p2996_ref`` is injected so the script can assert the clang-p2996
    binary baked into the image was actually built from the pinned ref
    (``resolve_expected_p2996_ref``) — closing the false-positive where a
    stale/wrong-ref reflection compiler still compiles a reflection program and
    the smoke passes green. Only a 40-hex SHA triggers the strict equality
    check; a non-SHA dispatch override still gets the "is-a-real-p2996-build"
    guard.

    ``expected_identity`` (gap A — image identity) maps each verbatim-COPYd
    build input (:data:`IDENTITY_IMAGE_PATHS`) to its expected in-image sha256;
    the tier-1 core asserts each in-image copy matches, catching a stale/cached
    overlay smoked against old content. An empty/unset map leaves the guard
    dormant (unit-test friendly).

    ``expected_tools`` (#143 — exact tool-set assertion) maps declared tool keys
    to requested versions (``resolve_declared_tools``). When set, the script
    asserts the installed set sourced from the system config matches it exactly
    — catching a tool silently dropped/added or a requested-version drift that
    the ``(missing)``-count check alone passes green. An empty/unset value
    leaves the guard dormant (unit-test friendly).

    ``emulated`` (gap B — TSan under Rosetta) controls whether the
    ThreadSanitizer binary is RUN after it is compiled. The compile always
    runs (it proves the toolchain); the RUN is skipped under emulation, where
    TSan's shadow-memory layout is incompatible with Rosetta/QEMU.
    """
    strict = "1" if _SHA_RE.match(expected_p2996_ref) else ""
    tsan_run_skip = "1" if emulated else ""
    header = (
        "set -euo pipefail\n"
        + _tier1_var_lines(expected_identity, expected_tools)
        + f"EXPECTED_P2996_REF={shlex.quote(expected_p2996_ref)}\n"
        + f"P2996_REF_STRICT={shlex.quote(strict)}\n"
        + f"TSAN_RUN_SKIP={shlex.quote(tsan_run_skip)}\n"
    )
    return (
        header
        + _TIER1_CORE_BODY
        + """\
echo "=== hk validate ==="
HK_FILE=/etc/hk/hk.pkl hk validate
echo "=== shell integration ==="
command -v zsh || { echo "FAIL: zsh not found"; exit 1; }
command -v git || { echo "FAIL: git not found"; exit 1; }
echo "=== identity constraints ==="
if getent passwd vscode >/dev/null 2>&1; then
  echo "FAIL: vscode user exists in image"; exit 1
fi
if getent group vscode >/dev/null 2>&1; then
  echo "FAIL: vscode group exists in image"; exit 1
fi
if [ -d /home/vscode ]; then
  echo "FAIL: /home/vscode directory exists"; exit 1
fi
if env | grep -qi vscode; then
  echo "FAIL: vscode found in environment variables"; exit 1
fi
echo "=== path constraints ==="
if [ ! -x /usr/local/bin/mise ]; then
  echo "FAIL: /usr/local/bin/mise missing"; exit 1
fi
if [ ! -d /usr/local/share/mise/installs ]; then
  echo "FAIL: /usr/local/share/mise/installs missing"; exit 1
fi
echo "=== backend policy checks ==="
grep -q 'npm.package_manager = "bun"' "$MISE_CFG" || {
  echo "FAIL: bun package manager policy missing"; exit 1;
}
grep -q 'pipx.uvx = true' "$MISE_CFG" || {
  echo "FAIL: uvx policy missing"; exit 1;
}
grep -q 'cargo.binstall = true' "$MISE_CFG" || {
  echo "FAIL: cargo-binstall policy missing"; exit 1;
}
grep -q 'python.uv_venv_auto = "source"' "$MISE_CFG" || {
  echo "FAIL: python uv venv policy missing"; exit 1;
}
echo "=== clang tooling checks ==="
for tool in clang clang++ clangd clang-tidy clang-format lld lldb; do
  command -v "$tool" >/dev/null 2>&1 || { echo "FAIL: missing $tool"; exit 1; }
done
echo "=== sanitizer compile checks ==="
cat >/tmp/sanitizer.cpp <<'CPP'
#include <iostream>
int main() { std::cout << "ok\\n"; return 0; }
CPP
clang++ -fsanitize=address,undefined /tmp/sanitizer.cpp -o /tmp/san-au
/tmp/san-au >/dev/null
clang++ -fsanitize=thread /tmp/sanitizer.cpp -o /tmp/san-tsan
if [ -n "$TSAN_RUN_SKIP" ]; then
  echo "SKIP: ThreadSanitizer RUN skipped under emulation (compiled OK;" \
       "TSan shadow-memory ASLR layout is incompatible with Rosetta/QEMU)"
else
  /tmp/san-tsan >/dev/null
fi
clang++ -fsanitize=fuzzer-no-link -c /tmp/sanitizer.cpp -o /tmp/san-fuzz.o
echo "=== reflection compiler checks ==="
test -x /opt/gcc-latest/bin/g++ \
  || { echo "FAIL: gcc-latest binary missing"; exit 1; }
test -x /opt/clang-p2996/bin/clang++ \
  || { echo "FAIL: clang-p2996 missing"; exit 1; }
echo "=== clang-p2996 ref pin check ==="
# The clang-p2996 build embeds its bloomberg/clang-p2996 source commit in
# `--version`. Assert (a) it really IS a p2996 build (not conda clang on
# PATH) and (b) the embedded SHA matches the pinned CLANG_P2996_REF. Without
# this, a stale/wrong-ref reflection compiler still passes the functional
# compile below — a silent false positive.
P2996_VERSION=$(/opt/clang-p2996/bin/clang --version)
if ! echo "$P2996_VERSION" | grep -q 'bloomberg/clang-p2996'; then
  echo "FAIL: /opt/clang-p2996 is not a bloomberg/clang-p2996 build"; exit 1
fi
ACTUAL_P2996_REF=$(echo "$P2996_VERSION" | grep -oiE '[0-9a-f]{40}' | head -1)
if [ -z "$ACTUAL_P2996_REF" ]; then
  echo "FAIL: could not parse clang-p2996 git ref from --version"; exit 1
fi
if [ -n "$P2996_REF_STRICT" ]; then
  if [ "$ACTUAL_P2996_REF" != "$EXPECTED_P2996_REF" ]; then
    echo "FAIL: clang-p2996 ref $ACTUAL_P2996_REF != pinned $EXPECTED_P2996_REF"
    exit 1
  fi
  echo "OK: clang-p2996 ref $ACTUAL_P2996_REF matches pinned CLANG_P2996_REF"
else
  echo "OK: clang-p2996 real build @ $ACTUAL_P2996_REF (non-SHA override; skip)"
fi
cat >/tmp/refl-func.cpp <<'CPP'
#include <meta>
#include <iostream>
enum class Color { Red, Green, Blue };
consteval int count_enumerators() {
  return static_cast<int>(enumerators_of(^^Color).size());
}
static_assert(count_enumerators() == 3);
int main() {
  int n = count_enumerators();
  std::cout << "reflection enumerators=" << n << std::endl;
  return n == 3 ? 0 : 1;
}
CPP
# Gap C (#141): link + RUN, not merely a syntax check. The static_assert
# still forces enumerators_of(^^Color) evaluation at COMPILE time (a broken
# reflection front-end fails the build); the RUN then materializes that
# consteval result into a runtime value and asserts on it via the exit code,
# proving the emitted binary actually executes. clang-p2996's -stdlib=libc++
# binary needs libc++.so.1 at runtime, which is off the default loader path,
# so we bake an rpath pointing at the in-image libc++ dir — discovered, not
# hard-coded, so a triple change can't silently break it. Link-flag-only fix:
# no Dockerfile change, hence no cold base rebuild. A p2996 libc++ binary runs
# under Rosetta/QEMU (verified #141), so unlike TSan the RUN needs no
# emulation gate.
P2996_LIBCXX_SO=$(find /opt/clang-p2996/lib -name 'libc++.so.1' 2>/dev/null | head -n1)
if [ -z "$P2996_LIBCXX_SO" ]; then
  echo "FAIL: clang-p2996 libc++.so.1 not found in image"; exit 1
fi
P2996_LIBCXX_DIR=$(dirname "$P2996_LIBCXX_SO")
/opt/gcc-latest/bin/g++ -std=c++26 -freflection /tmp/refl-func.cpp -o /tmp/refl-gcc \
  || { echo "FAIL: gcc-latest reflection link failed"; exit 1; }
/tmp/refl-gcc || { echo "FAIL: gcc-latest reflection binary did not run"; exit 1; }
/opt/clang-p2996/bin/clang++ -std=c++2c -freflection -freflection-latest \
  -fexpansion-statements -stdlib=libc++ -Wl,-rpath,"$P2996_LIBCXX_DIR" \
  /tmp/refl-func.cpp -o /tmp/refl-clang \
  || { echo "FAIL: clang-p2996 reflection link failed"; exit 1; }
/tmp/refl-clang || { echo "FAIL: clang-p2996 reflection binary did not run"; exit 1; }
rm -f /tmp/refl-func.cpp /tmp/refl-gcc /tmp/refl-clang
echo "=== AI CLI checks ==="
for tool in claude codex gemini; do
  command -v "$tool" >/dev/null 2>&1 || { echo "FAIL: missing $tool"; exit 1; }
done
echo "=== zero-warning check ==="
warn_count=$(echo "$mise_output" | grep -ci "WARN" || true)
if [ "$warn_count" -gt 0 ]; then
  echo "FAIL: mise produced warnings (zero-warning policy)"
  echo "$mise_output" | grep -i "WARN"
  exit 1
fi
echo "=== All smoke checks passed ==="
"""
    )


def build_smoke_docker_cmd(
    image_ref: str,
    *,
    platform: str = "linux/amd64/v2",
    expected_p2996_ref: str | None = None,
    expected_identity: Mapping[str, str] | None = None,
    emulated: bool | None = None,
) -> list[str]:
    """Build the docker command used for smoke validation.

    CI smokes the image it just built from branch HEAD, so identity + tool-set
    resolve to the HEAD content (:func:`resolve_expected_identity_head` /
    :func:`resolve_declared_tools`) — the devcontainer path injects merge-base
    data instead (:func:`build_tier1_script`). The declared tool set has no
    injectable override (nothing smokes a *synthetic* set); ``build_smoke_script``
    remains the injection seam for unit tests.
    """
    if expected_p2996_ref is None:
        expected_p2996_ref = resolve_expected_p2996_ref()
    if expected_identity is None:
        expected_identity = resolve_expected_identity_head()
    if emulated is None:
        emulated = _is_emulated(platform)
    script = build_smoke_script(
        expected_p2996_ref,
        expected_identity=expected_identity,
        expected_tools=resolve_declared_tools(),
        emulated=emulated,
    )
    return [
        "docker",
        "run",
        "--rm",
        "--platform",
        platform,
        "--entrypoint",
        "/bin/bash",
        image_ref,
        "-lc",
        script,
    ]


def smoke(image_ref: str, *, platform: str = "linux/amd64/v2") -> dict[str, Any]:
    """Run smoke tests against a container image."""
    logger.info("Smoking image: %s", image_ref)
    cmd = build_smoke_docker_cmd(image_ref, platform=platform)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.error("Smoke test FAILED:\n%s\n%s", result.stdout, result.stderr)
        return {
            "image_ref": image_ref,
            "platform": platform,
            "result": "FAIL",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    logger.info("Smoke test PASSED")
    return {
        "image_ref": image_ref,
        "platform": platform,
        "result": "PASS",
    }


def _gzip_size_for_image(image_ref: str) -> int:
    save_proc = subprocess.Popen(
        ["docker", "image", "save", image_ref],
        cwd=_project_root(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if save_proc.stdout is None:
        msg = "docker image save returned no stdout"
        raise RuntimeError(msg)
    compressor = zlib.compressobj(wbits=31)
    compressed_size = 0
    while chunk := save_proc.stdout.read(1024 * 1024):
        compressed_size += len(compressor.compress(chunk))
    compressed_size += len(compressor.flush())
    stderr = save_proc.stderr.read().decode("utf-8") if save_proc.stderr else ""
    returncode = save_proc.wait()
    if returncode != 0:
        msg = f"docker image save failed for {image_ref}: {stderr}".strip()
        raise RuntimeError(msg)
    return compressed_size


def _repo_without_tag(image_ref: str) -> str:
    """Strip a ``:tag`` suffix, preserving a registry ``:port`` and ``@digest``."""
    if "@" in image_ref:
        return image_ref.split("@", 1)[0]
    last_slash = image_ref.rfind("/")
    last_colon = image_ref.rfind(":")
    if last_colon > last_slash:
        return image_ref[:last_colon]
    return image_ref


def _sum_manifest_layer_sizes(raw: str, image_ref: str) -> int:
    """Sum compressed layer sizes from an OCI/Docker manifest JSON.

    Registry manifests record each layer's *compressed* (download) size, so
    summing them yields the compressed image size without a ``docker save``.
    Handles a single-platform manifest (``layers``) directly and a manifest
    list / OCI index (``manifests``) by recursing into the linux/amd64 entry.
    """
    doc = json.loads(raw)
    layers = doc.get("layers")
    if layers is not None:
        return sum(int(layer.get("size", 0)) for layer in layers)
    for entry in doc.get("manifests", []):
        platform = entry.get("platform", {})
        if platform.get("os") == "linux" and platform.get("architecture") == "amd64":
            digest = entry.get("digest")
            sub = _run(
                [
                    "docker",
                    "buildx",
                    "imagetools",
                    "inspect",
                    f"{_repo_without_tag(image_ref)}@{digest}",
                    "--raw",
                ],
            ).stdout
            return _sum_manifest_layer_sizes(sub, image_ref)
    # Not a recognized manifest shape — fall back to the local gzip measure.
    return _gzip_size_for_image(image_ref)


def _compressed_size_for_image(image_ref: str) -> int:
    """Compressed (download) size of an image.

    Prefers the registry manifest (``docker buildx imagetools inspect --raw``),
    whose layer sizes are already gzip-compressed — instant and exact for a
    pushed image. Falls back to streaming ``docker image save`` through gzip
    when the ref is not resolvable in a registry (e.g. a local-only image).
    """
    try:
        raw = _run(
            ["docker", "buildx", "imagetools", "inspect", image_ref, "--raw"],
        ).stdout
    except subprocess.CalledProcessError, FileNotFoundError:
        return _gzip_size_for_image(image_ref)
    return _sum_manifest_layer_sizes(raw, image_ref)


def _parse_human_size(size: str) -> int:
    cleaned = size.strip()
    match = re.fullmatch(r"(?i)\s*([0-9]+(?:\.[0-9]+)?)\s*([kmgt]?b)\s*", cleaned)
    if match:
        number = float(match.group(1))
        unit = match.group(2).upper()
        scales = {
            "B": 1,
            "KB": 1024,
            "MB": 1024**2,
            "GB": 1024**3,
            "TB": 1024**4,
        }
        return int(number * scales[unit])
    if cleaned.isdigit():
        return int(cleaned)
    return 0


def size_report(
    image_ref: str,
    *,
    platform: str = "linux/amd64/v2",
    top_layers: int = 10,
) -> dict[str, Any]:
    """Report image size and large-layer metrics."""
    image_size_bytes = int(
        _run(
            ["docker", "image", "inspect", "--format", "{{.Size}}", image_ref],
        ).stdout.strip()
    )
    compressed_size_bytes = _compressed_size_for_image(image_ref)

    history_lines = _run(
        ["docker", "history", "--no-trunc", "--format", "{{json .}}", image_ref],
    ).stdout.splitlines()
    layers: list[dict[str, Any]] = []
    for line in history_lines:
        if not line.strip():
            continue
        entry = json.loads(line)
        size_bytes = _parse_human_size(entry.get("Size", "0B"))
        layers.append(
            {
                "created_by": entry.get("CreatedBy", ""),
                "size": entry.get("Size", "0B"),
                "size_bytes": size_bytes,
            }
        )
    layers.sort(key=lambda item: item["size_bytes"], reverse=True)

    return {
        "image_ref": image_ref,
        "platform": platform,
        "image_size_bytes": image_size_bytes,
        "compressed_size_bytes": compressed_size_bytes,
        "top_layers": layers[:top_layers],
    }


def benchmark(
    image_ref: str,
    *,
    platform: str = "linux/amd64/v2",
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Benchmark smoke and size-report timings for an image."""
    if output_path is None:
        output_path = (
            _project_root() / "artifacts" / "build" / "devcontainer-metrics.json"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    started = time.time()
    smoke_result = smoke(image_ref, platform=platform)
    smoke_finished = time.time()
    report = size_report(image_ref, platform=platform)
    finished = time.time()
    tool_count = count_installed_tools(image_ref, platform=platform)

    payload = {
        "schema_version": 2,
        "image_ref": image_ref,
        "platform": platform,
        "smoke": smoke_result,
        "timings_s": {
            "smoke_wall": round(smoke_finished - started, 6),
            "report_wall": round(finished - smoke_finished, 6),
            "total_wall": round(finished - started, 6),
        },
        "image_size_bytes": report["image_size_bytes"],
        "compressed_size_bytes": report["compressed_size_bytes"],
        "tool_count": tool_count,
        "top_layers": report["top_layers"],
        "result": smoke_result["result"].lower(),
    }
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def metrics_compare(baseline_path: Path, candidate_path: Path) -> dict[str, Any]:
    """Compare two benchmark payloads."""
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    return {
        "baseline": str(baseline_path),
        "candidate": str(candidate_path),
        "image_size_delta": candidate["image_size_bytes"]
        - baseline["image_size_bytes"],
        "compressed_size_delta": candidate["compressed_size_bytes"]
        - baseline["compressed_size_bytes"],
        "smoke_wall_delta": candidate["timings_s"]["smoke_wall"]
        - baseline["timings_s"]["smoke_wall"],
        "total_wall_delta": candidate["timings_s"]["total_wall"]
        - baseline["timings_s"]["total_wall"],
    }


def _count_tools_from_mise_ls(raw: str) -> int:
    """Count installed tool entries from ``mise ls --json`` output.

    ``mise ls --json`` maps each tool key to a list of its installed version
    objects, so summing those list lengths counts every installed
    (tool, version) entry — the JSON-robust equivalent of ``mise ls | wc -l``
    (one line per tool-version) without depending on the plain-text columns.
    """
    data = json.loads(raw)
    total = 0
    for versions in data.values():
        total += len(versions) if isinstance(versions, list) else 1
    return total


def count_installed_tools(image_ref: str, *, platform: str = "linux/amd64/v2") -> int:
    """Installed tool count inside ``image_ref`` via ``mise ls --json``.

    Runs mise in a login shell (``-lc``) so the image's mise activation and
    PATH are in effect, mirroring :func:`build_smoke_docker_cmd`.
    """
    raw = _run(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            platform,
            "--entrypoint",
            "/bin/bash",
            image_ref,
            "-lc",
            "mise ls --json",
        ],
    ).stdout
    return _count_tools_from_mise_ls(raw)


def _parse_build_timing(jobs_json: str) -> dict[str, Any]:
    """Reduce a ``/actions/runs/<id>/jobs`` payload to timing metrics.

    Jobs in the reusable build chain run partly in parallel, so the honest
    "total build time" is wall-clock: the span from the earliest job start to
    the latest job completion. Per-job durations are kept for a visibility
    breakdown. Jobs still running (null ``completed_at``) are skipped — this
    runs after CI has completed, so that is only a defensive guard.
    """
    doc = json.loads(jobs_json)
    per_job: list[dict[str, Any]] = []
    starts: list[datetime] = []
    ends: list[datetime] = []
    for job in doc.get("jobs", []):
        started = job.get("started_at")
        completed = job.get("completed_at")
        if not started or not completed:
            continue
        start_dt = datetime.fromisoformat(started)
        end_dt = datetime.fromisoformat(completed)
        starts.append(start_dt)
        ends.append(end_dt)
        per_job.append(
            {
                "name": job.get("name", "?"),
                "conclusion": job.get("conclusion"),
                "duration_s": round((end_dt - start_dt).total_seconds(), 3),
            }
        )
    total_wall_s = (
        round((max(ends) - min(starts)).total_seconds(), 3) if starts else 0.0
    )
    return {"total_wall_s": total_wall_s, "jobs": per_job}


def fetch_build_timing(run_id: str, repo: str) -> dict[str, Any]:
    """Fetch upstream CI-run job timings via ``gh api`` (needs actions:read).

    ``run_id`` is the source CI run exposed by the ``workflow_run`` trigger
    (``github.event.workflow_run.id``); ``repo`` is ``owner/name``. Uses the
    native jobs endpoint — no build-job instrumentation needed. No
    ``--paginate``: the object-wrapped list endpoint would emit one JSON doc
    per page (unparsable), and the build chain has far fewer than 100 jobs.
    """
    raw = _run(
        ["gh", "api", f"repos/{repo}/actions/runs/{run_id}/jobs"],
    ).stdout
    return _parse_build_timing(raw)


_BYTE_STEP = 1024.0


def _format_bytes(num_bytes: int) -> str:
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if abs(value) < _BYTE_STEP:
            return f"{int(value)} {unit}" if unit == "B" else f"{value:.2f} {unit}"
        value /= _BYTE_STEP
    return f"{value:.2f} TB"


def _format_duration(seconds: float) -> str:
    total = round(seconds)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def render_metrics_summary(
    payload: Mapping[str, Any], timing: Mapping[str, Any] | None
) -> str:
    """Render benchmark ``payload`` (+ optional CI ``timing``) as markdown.

    GitHub-flavored markdown for ``$GITHUB_STEP_SUMMARY``. Pure — no IO.
    """
    compressed = _format_bytes(payload.get("compressed_size_bytes", 0))
    uncompressed = _format_bytes(payload.get("image_size_bytes", 0))
    lines: list[str] = [
        "## \U0001f433 Devcontainer image metrics",
        "",
        f"**Image:** `{payload.get('image_ref', '?')}`",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Compressed size | {compressed} |",
        f"| Uncompressed size | {uncompressed} |",
    ]
    if "tool_count" in payload:
        lines.append(f"| Installed tools | {payload['tool_count']} |")
    lines.append(f"| Smoke result | {payload.get('result', '?').upper()} |")
    if timing is not None:
        lines.append(
            f"| CI build time (wall) | {_format_duration(timing['total_wall_s'])} |"
        )
    lines.append("")

    top_layers = payload.get("top_layers") or []
    if top_layers:
        lines += ["### Largest layers", "", "| Size | Created by |", "| --- | --- |"]
        lines.extend(
            f"| {_format_bytes(layer.get('size_bytes', 0))} | "
            f"`{layer.get('created_by', '').replace('|', '\\|')}` |"
            for layer in top_layers[:5]
        )
        lines.append("")

    jobs = (timing or {}).get("jobs") or []
    if jobs:
        lines += [
            "### CI job timings",
            "",
            "| Job | Duration | Conclusion |",
            "| --- | --- | --- |",
        ]
        lines.extend(
            f"| {job.get('name', '?')} "
            f"| {_format_duration(job.get('duration_s', 0))} "
            f"| {job.get('conclusion') or '?'} |"
            for job in jobs
        )
        lines.append("")

    return "\n".join(lines) + "\n"


def metrics_summary(
    metrics_path: Path,
    *,
    run_id: str | None = None,
    repo: str | None = None,
    summary_path: Path | None = None,
) -> str:
    """Read a benchmark JSON, render a step summary, return the markdown.

    Optionally fetches upstream CI timings (when ``run_id``/``repo`` given)
    and appends the rendered markdown to ``summary_path``.
    """
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    timing = fetch_build_timing(run_id, repo) if run_id and repo else None
    markdown = render_metrics_summary(payload, timing)
    if summary_path is not None:
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write(markdown)
    return markdown


@dataclasses.dataclass(frozen=True)
class ImageCommand:
    """Parsed image CLI command parameters."""

    image_ref: str
    platform: str = "linux/amd64/v2"
    command: str = "smoke"
    output_path: Path | None = None
    baseline_path: Path | None = None
    candidate_path: Path | None = None
    identity_path: str | None = None
    metrics_path: Path | None = None
    run_id: str | None = None
    repo: str | None = None
    summary_path: Path | None = None
    tier: int | None = None


def base_currency_blob(repo_root: Path, rel_path: str) -> bytes:
    """Bytes of an image build input as the CURRENT local base was built from it.

    A branch that CHANGES an image build input can never have a local base
    built from it — the new base is built by that branch's own PR CI — so
    the local smoke tier-1 base-currency checks compare against the
    MERGE-BASE blob ("is the base current w.r.t. what is already integrated
    on main") and defer branch-config validation to the PR CI build+smoke.
    On main, merge-base == HEAD, so this is byte-identical to the committed
    file.

    Falls back to the worktree bytes when the merge-base or blob cannot be
    resolved (checkout without origin/main, path not yet tracked).
    """
    merge_base = subprocess.run(
        ["git", "-C", str(repo_root), "merge-base", "HEAD", "origin/main"],
        capture_output=True,
        text=True,
        check=False,
    )
    if merge_base.returncode == 0:
        blob = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "show",
                f"{merge_base.stdout.strip()}:{rel_path}",
            ],
            capture_output=True,
            check=False,
        )
        if blob.returncode == 0:
            return blob.stdout
    return (repo_root / rel_path).read_bytes()


def identity_expected_hash(repo_root: Path, rel_path: str) -> str:
    """Expected sha256 for the in-image copy of an image build input.

    Base-currency hash: the merge-base blob for a branch-modified input,
    the committed file otherwise (see :func:`base_currency_blob`).
    """
    return hashlib.sha256(base_currency_blob(repo_root, rel_path)).hexdigest()


def identity_expected_main(rel_path: str) -> int:
    """CLI: print the tier-1 expected hash for ``rel_path`` (see above).

    Standalone debug/inspection command. As of #223 the devcontainer smoke no
    longer calls this per-file — tier-1 identity is generated by
    :func:`build_tier1_script` (``image smoke-script --tier 1``), which injects
    :func:`resolve_expected_identity_at_base` in one shot. Retirement of this
    thin wrapper is a #223 follow-up candidate.
    """
    sys.stdout.write(identity_expected_hash(_project_root(), rel_path) + "\n")
    return 0


def resolve_declared_tools_at_base(repo_root: Path) -> dict[str, str]:
    """Declared image tools as the CURRENT local base was built from them.

    Merge-base-aware sibling of :func:`resolve_declared_tools` (which reads
    HEAD and feeds ``build_smoke_script`` — CI builds the image FROM the
    branch config, so it must compare against HEAD). The local devcontainer's
    base predates a branch's image-input bump, so the devcontainer smoke's
    tier-1 tool-set (injected by :func:`build_tier1_script` / ``smoke-script
    --tier 1``) compares installed tools against this merge-base declaration;
    branch tool bumps are validated by the PR CI build+smoke.
    """
    declared: dict[str, str] = {}
    for rel_path in (
        ".devcontainer/mise-system.toml",
        ".config/mise/conf.d/shared.toml",
        ".devcontainer/mise-runtime.toml",
    ):
        declared.update(
            parse_declared_tools(base_currency_blob(repo_root, rel_path).decode())
        )
    return declared


def verify_tools_main() -> int:
    """Assert the installed tool set matches the base-declared ``[tools]``.

    Runs ``mise ls --json`` against the ambient mise (inside the devcontainer)
    and compares to the MERGE-BASE declared ``[tools]``. Standalone
    debug/inspection command: as of #223 the devcontainer smoke asserts the
    tool-set through the shared tier-1 core (:func:`build_tier1_script`, the
    same bash jq/diff the CI no-mount smoke runs) rather than this python diff,
    so the two smoke paths cannot diverge. Retirement of this now-off-path
    wrapper (and its ``installed_tools_from_mise_ls`` / ``diff_tool_sets``
    helpers) is a #223 follow-up candidate.

    Uses :func:`resolve_declared_tools_at_base`, not
    :func:`resolve_declared_tools`: the local base predates a branch's
    image-input bump, so a HEAD comparison would false-fail on the bumped
    tools (#178 follow-up). Branch tool bumps are validated by the PR CI
    build+smoke, which builds the image from HEAD.
    """
    declared = resolve_declared_tools_at_base(_project_root())
    result = subprocess.run(
        ["mise", "ls", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    # Default source tuple = system + shared + runtime configs. The runtime
    # tier was missing here (a 2-tuple derived from MISE_SYSTEM_CONFIG_FILE,
    # itself retired — build.no-system-config-file-pin), so all 23 runtime
    # tools diffed as declared-but-not-installed in the devcontainer (PR #169).
    installed = installed_tools_from_mise_ls(result.stdout)
    diffs = diff_tool_sets(declared, installed)
    if diffs:
        sys.stderr.write(
            "FAIL: installed tool set differs from base-declared [tools] "
            "(merge-base):\n"
        )
        for line in diffs:
            sys.stderr.write(f"  {line}\n")
        return 1
    sys.stdout.write(
        f"OK: installed tool set matches base-declared [tools] "
        f"({len(declared)} tools)\n"
    )
    return 0


_SMOKE_SCRIPT_TIER1 = 1


def smoke_script_main(tier: int | None) -> int:
    """CLI: print the shared tier-1 smoke core for the devcontainer smoke (#223).

    ``scripts/devcontainer-smoke.sh`` evaluates this so its in-container tier-1
    (image identity + exact tool-set) is byte-identical to the CI no-mount smoke
    — the two paths run the SAME :data:`_TIER1_CORE_BODY`. The injected DATA is
    merge-base aware (:func:`resolve_expected_identity_at_base` /
    :func:`resolve_declared_tools_at_base`): the local base predates a branch's
    image-input bump, which is validated by the branch's own PR CI build+smoke.
    Only tier 1 is migrated to python; tiers 2/3 stay in bash for now.
    """
    if tier != _SMOKE_SCRIPT_TIER1:
        sys.stderr.write(f"smoke-script: unsupported tier {tier!r} (only --tier 1)\n")
        return 2
    root = _project_root()
    script = build_tier1_script(
        expected_identity=resolve_expected_identity_at_base(),
        expected_tools=resolve_declared_tools_at_base(root),
    )
    sys.stdout.write(script)
    return 0


def _handle_smoke_script(cmd: ImageCommand) -> int:
    return smoke_script_main(cmd.tier)


def _handle_verify_tools(_cmd: ImageCommand) -> int:
    return verify_tools_main()


def _handle_identity_expected(cmd: ImageCommand) -> int:
    if cmd.identity_path is None:
        sys.stderr.write("identity-expected requires a path\n")
        return 2
    return identity_expected_main(cmd.identity_path)


def _handle_smoke(cmd: ImageCommand) -> int:
    result = smoke(cmd.image_ref, platform=cmd.platform)
    if result["result"] == "FAIL":
        sys.stderr.write(f"FAIL: {cmd.image_ref}\n")
        sys.stderr.write(result.get("stderr", ""))
        return 1
    sys.stderr.write(f"PASS: {cmd.image_ref}\n")
    return 0


def _handle_size_report(cmd: ImageCommand) -> int:
    payload = size_report(cmd.image_ref, platform=cmd.platform)
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _handle_benchmark(cmd: ImageCommand) -> int:
    payload = benchmark(
        cmd.image_ref, platform=cmd.platform, output_path=cmd.output_path
    )
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _handle_metrics_compare(cmd: ImageCommand) -> int:
    if cmd.baseline_path is None or cmd.candidate_path is None:
        msg = "baseline_path and candidate_path are required"
        raise ValueError(msg)
    payload = metrics_compare(cmd.baseline_path, cmd.candidate_path)
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _handle_metrics_summary(cmd: ImageCommand) -> int:
    if cmd.metrics_path is None:
        sys.stderr.write("metrics-summary requires --metrics-path\n")
        return 2
    markdown = metrics_summary(
        cmd.metrics_path,
        run_id=cmd.run_id,
        repo=cmd.repo,
        summary_path=cmd.summary_path,
    )
    sys.stdout.write(markdown)
    return 0


def main(cmd: ImageCommand) -> int:
    """CLI entry point for image operations (command → handler dispatch)."""
    handlers: dict[str, Callable[[ImageCommand], int]] = {
        "verify-tools": _handle_verify_tools,
        "identity-expected": _handle_identity_expected,
        "smoke-script": _handle_smoke_script,
        "smoke": _handle_smoke,
        "size-report": _handle_size_report,
        "benchmark": _handle_benchmark,
        "metrics-compare": _handle_metrics_compare,
        "metrics-summary": _handle_metrics_summary,
    }
    handler = handlers.get(cmd.command)
    if handler is None:
        msg = f"Unsupported command: {cmd.command}"
        raise ValueError(msg)
    return handler(cmd)
