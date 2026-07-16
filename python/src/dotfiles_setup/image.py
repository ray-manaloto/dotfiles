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

# Leading MAJOR.MINOR.PATCH of a Debian apt version, past an optional epoch
# (``1:22.1.8~++2026...`` -> ``22.1.8``). Anchored: the release is always the
# first token after the epoch, never inside the ``~++<snapshot>`` suffix.
_LLVM_VERSION_RE = re.compile(r"(?:\d+:)?(\d+\.\d+\.\d+)")


def _parse_apt_llvm_version(config_text: str) -> str:
    """Extract the LLVM release (``MAJOR.MINOR.PATCH``) from ``apt:clang-22``.

    The whole apt.llvm.org suite shares one version string, so the pinned
    ``clang-22`` package in ``[bootstrap.packages]`` is the natural anchor for
    "what LLVM release is this image". Fails loud if the pin is absent or
    unparsable — a silently-empty version would leave the runtime version
    guard dormant, reintroducing the false-positive it exists to catch.
    """
    data = tomllib.loads(config_text)
    packages = data.get("bootstrap", {}).get("packages", {})
    pin = packages.get("apt:clang-22")
    if not isinstance(pin, str):
        msg = "mise-system.toml [bootstrap.packages] lacks a string 'apt:clang-22' pin"
        raise TypeError(msg)
    match = _LLVM_VERSION_RE.match(pin)
    if match is None:
        msg = f"could not parse an LLVM release from apt:clang-22 pin {pin!r}"
        raise ValueError(msg)
    return match.group(1)


def resolve_expected_llvm_version() -> str:
    """The apt LLVM release the image is expected to ship (HEAD).

    Reads the committed ``mise-system.toml`` pin — feeds ``build_smoke_script``,
    since CI builds the image FROM branch HEAD. The merge-base sibling
    (:func:`resolve_expected_llvm_version_at_base`) feeds the devcontainer smoke,
    whose local base predates a branch's pin bump.
    """
    root = _project_root()
    return _parse_apt_llvm_version(
        (root / ".devcontainer" / "mise-system.toml").read_text()
    )


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
# #251: the default `python3` must BE mise's declared interpreter, not the
# distro's. The image ships two 3.14s — mise's (python-build-standalone, pinned
# in the shared fragment) and Ubuntu's /usr/bin/python3 — and NOTHING else
# pins which one bare `python3` resolves to: the tool-set diff proves only that
# mise *knows about* python; `which python` proves only that a path exists
# (protective solely because Debian ships no bare `python`); and tier-2's
# `uv run --project python pytest` resolves the project venv's interpreter,
# which uv provisions, so it stays green through a shim regression. Asserts
# both halves — resolution (sys.executable under mise's installs, which is what
# separates 3.14.6 from the distro's 3.14.4 at the same minor) and the exact
# declared version. Dormant when the var is unset, like the guards above.
_TIER1_PYTHON_DEFAULT = """\
if [ -n "$EXPECTED_PYTHON_VERSION" ]; then
  command -v python3 >/dev/null \
    || { echo "FAIL: python3 not on PATH"; exit 1; }
  py_exe=$(python3 -c 'import sys; print(sys.executable)')
  case "$py_exe" in
    "$MISE_DIR"/installs/python/*) ;;
    *)
      echo "FAIL: default python3 is $py_exe, not a mise install under" \
           "$MISE_DIR/installs/python — the distro python has taken the PATH"
      exit 1
      ;;
  esac
  py_ver=$(python3 -c 'import platform; print(platform.python_version())')
  if [ "$py_ver" != "$EXPECTED_PYTHON_VERSION" ]; then
    echo "FAIL: default python3 is $py_ver, declared $EXPECTED_PYTHON_VERSION"
    exit 1
  fi
  echo "OK: default python3 is mise's $py_ver ($py_exe)"
else
  echo "SKIP: no expected python version injected (python guard dormant)"
fi
"""


_TIER1_CORE_BODY = (
    _TIER1_MISE_PATHS
    + _TIER1_IDENTITY_BLOCK
    + _TIER1_MISE_LS_TOOLSET
    + _TIER1_PYTHON_DEFAULT
)


# The tier-3 COMPILER substrate: sanitizer compile checks + reflection compiler
# presence/ref-pin + reflection functional compile+run. This is mount-INDEPENDENT
# (self-contained /tmp + /opt paths, no repo files), so it is shared VERBATIM by
# the CI no-mount smoke (:func:`build_smoke_script`) and the devcontainer smoke's
# tier 3 (:func:`build_tier3_script`, emitted by ``image smoke-script --tier 3``)
# — closing the sanitizer/reflection duplication that previously drifted between
# the two paths (#223). The genuinely mount/SSH-dependent tier-3 checks
# (home-volume ownership + seed survivors, TMPDIR, R2 github SSH) can never run
# in the CI no-mount smoke and stay bash-only in scripts/devcontainer-smoke.sh.
# Reads injected data: $TSAN_RUN_SKIP (skip the emulation-incompatible TSan RUN),
# $EXPECTED_P2996_REF / $P2996_REF_STRICT (the pinned clang-p2996 ref). Only the
# injected DATA differs by caller (HEAD ref for CI; merge-base for the
# devcontainer, whose local base was built from the merge-base pin).
# #294: the default-clang identity + version gate. Extracted as its own
# constant (like _TIER1_PYTHON_DEFAULT) so its FAIL direction is control-armable
# in a unit test with a stubbed clang++ — a version guard verified only on a
# right answer is a probe that can only pass. The image ships several clang++
# (apt LLVM-22 at /usr/lib/llvm-22/bin, the clang-p2996 reflection build at
# /opt/clang-p2996/bin, plus conda's); the sanitizer + openmp + lld probes below
# all invoke BARE clang++, so pin which one that resolves to (the apt LLVM
# build) and — when the release is injected — that its --version reports it.
_TIER3_DEFAULT_CLANG = """\
echo "=== default clang toolchain identity (#294) ==="
clang_bin=$(command -v clang++ 2>/dev/null || true)
[ -n "$clang_bin" ] || { echo "FAIL: clang++ not on PATH"; exit 1; }
clang_real=$(readlink -f "$clang_bin")
case "$clang_real" in
  /usr/lib/llvm-*/*) echo "OK: default clang++ -> $clang_real (apt LLVM)" ;;
  *)
    echo "FAIL: default clang++ resolves to $clang_real, not apt /usr/lib/llvm-*"
    exit 1
    ;;
esac
if [ -n "$EXPECTED_LLVM_VERSION" ]; then
  clang_ver=$(clang++ --version 2>&1 || true)
  case "$clang_ver" in
    *"clang version $EXPECTED_LLVM_VERSION"*)
      echo "OK: default clang++ is LLVM $EXPECTED_LLVM_VERSION" ;;
    *)
      echo "FAIL: default clang++ is not LLVM $EXPECTED_LLVM_VERSION"
      echo "$clang_ver"
      exit 1
      ;;
  esac
else
  echo "SKIP: no expected LLVM version injected (clang version guard dormant)"
fi
"""


_TIER3_COMPILER_BODY = (
    _TIER3_DEFAULT_CLANG
    + """\
echo "=== clang driver presence (#294: moved from CI-only tail) ==="
# Presence of the apt LLVM driver entrypoints, in the SHARED substrate so the
# devcontainer smoke (verify-container-latest) runs it too — not just the CI
# no-mount smoke where it used to live.
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
echo "=== openmp compile+link+run (#294: libomp-22-dev) ==="
# Proves the OpenMP runtime is actually linkable+runnable, not merely that the
# libomp package installed. Runs even under emulation (like asan/ubsan): OpenMP
# threading works under Rosetta/QEMU; only TSan's shadow memory does not.
cat >/tmp/omp.cpp <<'CPP'
#include <omp.h>
#include <cstdio>
int main() {
  int n = 0;
#pragma omp parallel reduction(+ : n)
  n += 1;
  std::printf("openmp threads=%d\\n", n);
  return n >= 1 ? 0 : 1;
}
CPP
clang++ -fopenmp /tmp/omp.cpp -o /tmp/omp \
  || { echo "FAIL: clang++ -fopenmp link failed (libomp-22-dev missing?)"; exit 1; }
/tmp/omp >/dev/null || { echo "FAIL: openmp binary did not run"; exit 1; }
echo "OK: openmp -fopenmp compiles, links, runs"
echo "=== lld linker (#294: -fuse-ld=lld) ==="
# lld presence is asserted above; this proves it actually LINKS. Reuses the
# sanitizer source (still on disk — never removed).
clang++ -fuse-ld=lld /tmp/sanitizer.cpp -o /tmp/lld-linked \
  || { echo "FAIL: clang++ -fuse-ld=lld link failed"; exit 1; }
/tmp/lld-linked >/dev/null || { echo "FAIL: lld-linked binary did not run"; exit 1; }
echo "OK: lld links (-fuse-ld=lld) + binary runs"
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
echo "=== llvm utility version smoke (#294) ==="
# The core LLVM binaries all embed the release in --version. opt/llc/llvm-cov/
# llvm-profdata/llvm-symbolizer ship in the `llvm-22` package (verified from the
# .deb: /usr/lib/llvm-22/bin/*); llvm-bolt in `bolt-22`; mlir-opt in
# `mlir-22-tools`. Match the bare release substring (format-robust across all
# banners). `case` glob, never `cmd | grep -q` — the latter SIGPIPEs (141) under
# pipefail (hk no_grep_q_under_pipefail).
if [ -n "$EXPECTED_LLVM_VERSION" ]; then
  for util in opt llc llvm-cov llvm-profdata llvm-symbolizer llvm-bolt mlir-opt; do
    ubin=$(command -v "$util" 2>/dev/null || true)
    [ -n "$ubin" ] || { echo "FAIL: $util not on PATH"; exit 1; }
    uver=$("$ubin" --version 2>&1 || true)
    case "$uver" in
      *"$EXPECTED_LLVM_VERSION"*) echo "OK: $util reports $EXPECTED_LLVM_VERSION" ;;
      *)
        echo "FAIL: $util --version missing $EXPECTED_LLVM_VERSION"
        echo "$uver"
        exit 1
        ;;
    esac
  done
else
  echo "SKIP: no expected LLVM version injected (utility version guard dormant)"
fi
echo "=== flang fortran compile+run (#294: flang-22) ==="
# Binary name varies across LLVM releases (flang | flang-new); accept either.
flang_bin=$(command -v flang 2>/dev/null || command -v flang-new 2>/dev/null || true)
[ -n "$flang_bin" ] || { echo "FAIL: flang/flang-new not on PATH"; exit 1; }
if [ -n "$EXPECTED_LLVM_VERSION" ]; then
  fver=$("$flang_bin" --version 2>&1 || true)
  case "$fver" in
    *"$EXPECTED_LLVM_VERSION"*) echo "OK: flang reports $EXPECTED_LLVM_VERSION" ;;
    *)
      echo "FAIL: flang --version missing $EXPECTED_LLVM_VERSION"
      echo "$fver"
      exit 1
      ;;
  esac
fi
cat >/tmp/hello.f90 <<'F90'
program hello
  implicit none
  print *, "flang ok"
end program hello
F90
"$flang_bin" /tmp/hello.f90 -o /tmp/flang-hello \
  || { echo "FAIL: flang compile/link failed"; exit 1; }
/tmp/flang-hello >/dev/null || { echo "FAIL: flang binary did not run"; exit 1; }
echo "OK: flang compiles + runs a Fortran program"
echo "=== libclc bitcode presence (#294: libclc-22) ==="
# libclc-22 ships its OpenCL *.bc bitcode under /usr/lib/clc (verified from the
# .deb); the extra roots tolerate a future relocation. The trailing `|| true` is
# load-bearing: `find` exits NON-ZERO if any start dir is absent, and under
# `set -e` a bare `var=$(find ...)` would then abort the script BEFORE this
# check runs (a probe that dies at its own setup — probes-need-a-control-arm).
clc_bc=$(find /usr/lib/clc /usr/lib/clang /usr/lib/llvm-22 \
  -name '*.bc' 2>/dev/null | head -n1 || true)
[ -n "$clc_bc" ] || { echo "FAIL: no libclc bitcode (*.bc) found in image"; exit 1; }
echo "OK: libclc bitcode present ($clc_bc)"
rm -f /tmp/refl-func.cpp /tmp/refl-gcc /tmp/refl-clang \
  /tmp/omp.cpp /tmp/omp /tmp/lld-linked /tmp/hello.f90 /tmp/flang-hello
"""
)


def _tier1_var_lines(
    expected_identity: Mapping[str, str] | None,
    expected_tools: Mapping[str, str] | None,
    expected_python: str | None = None,
) -> str:
    """Injected-data header lines the tier-1 core reads ($EXPECTED_*)."""
    identity_blob = (
        _format_identity_lines(expected_identity) if expected_identity else ""
    )
    tool_lines = _format_expected_tool_lines(expected_tools) if expected_tools else ""
    return (
        f"EXPECTED_IDENTITY={shlex.quote(identity_blob)}\n"
        f"EXPECTED_TOOL_REQUESTS={shlex.quote(tool_lines)}\n"
        f"EXPECTED_PYTHON_VERSION={shlex.quote(expected_python or '')}\n"
    )


def _tier3_var_lines(
    expected_p2996_ref: str,
    *,
    emulated: bool,
    expected_llvm_version: str | None = None,
) -> str:
    """Injected-data header lines the tier-3 substrate reads.

    ``P2996_REF_STRICT`` is set only for a 40-hex SHA (a non-SHA dispatch
    override keeps the "is-a-real-p2996-build" guard but not strict equality).
    ``TSAN_RUN_SKIP`` gates the ThreadSanitizer RUN — the compile always fires
    (it proves the toolchain), but the RUN is skipped under emulation, where
    TSan's shadow-memory ASLR layout is incompatible with Rosetta/QEMU.
    ``EXPECTED_LLVM_VERSION`` is the apt LLVM release (#294) the default-clang
    and utility ``--version`` guards assert; empty leaves those guards dormant
    (unit-test friendly), like the tier-1 guards.
    """
    strict = "1" if _SHA_RE.match(expected_p2996_ref) else ""
    tsan_run_skip = "1" if emulated else ""
    return (
        f"EXPECTED_P2996_REF={shlex.quote(expected_p2996_ref)}\n"
        f"P2996_REF_STRICT={shlex.quote(strict)}\n"
        f"TSAN_RUN_SKIP={shlex.quote(tsan_run_skip)}\n"
        f"EXPECTED_LLVM_VERSION={shlex.quote(expected_llvm_version or '')}\n"
    )


def build_tier3_script(
    *,
    expected_p2996_ref: str,
    emulated: bool,
    expected_llvm_version: str | None = None,
) -> str:
    """Standalone tier-3 compiler smoke script: sanitizers + reflection.

    Emitted by ``image smoke-script --tier 3`` for ``scripts/devcontainer-smoke``
    to run in-container, and reused VERBATIM (the same :data:`_TIER3_COMPILER_BODY`)
    by :func:`build_smoke_script` for the CI no-mount smoke — the #223 single
    source of truth for the tier-3 compiler substrate. The mount/SSH-dependent
    tier-3 checks (home-volume, TMPDIR, R2 SSH) stay bash-only and are NOT part
    of this substrate. ``emulated`` skips the TSan RUN (the compile still runs).
    ``expected_llvm_version`` (#294) drives the apt-suite default-clang + utility
    ``--version`` guards; unset leaves them dormant.
    """
    return (
        "set -euo pipefail\n"
        + _tier3_var_lines(
            expected_p2996_ref,
            emulated=emulated,
            expected_llvm_version=expected_llvm_version,
        )
        + _TIER3_COMPILER_BODY
    )


def build_tier1_script(
    *,
    expected_identity: Mapping[str, str] | None = None,
    expected_tools: Mapping[str, str] | None = None,
    expected_python: str | None = None,
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
        + _tier1_var_lines(expected_identity, expected_tools, expected_python)
        + _TIER1_CORE_BODY
    )


def build_smoke_script(
    expected_p2996_ref: str,
    *,
    expected_identity: Mapping[str, str] | None = None,
    expected_tools: Mapping[str, str] | None = None,
    emulated: bool = False,
    expected_llvm_version: str | None = None,
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

    ``expected_llvm_version`` (#294 — apt LLVM-22 runtime coverage) is the
    release the default-clang identity gate and the ``opt``/``llvm-bolt``/
    ``mlir-opt``/``flang`` ``--version`` guards assert. Unset leaves those
    guards dormant (unit-test friendly).
    """
    header = (
        "set -euo pipefail\n"
        + _tier1_var_lines(expected_identity, expected_tools)
        + _tier3_var_lines(
            expected_p2996_ref,
            emulated=emulated,
            expected_llvm_version=expected_llvm_version,
        )
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
"""
        + _TIER3_COMPILER_BODY
        + """\
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
        expected_llvm_version=resolve_expected_llvm_version(),
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


# Layer→source attribution (#231 scope-(b)(a)). A fat layer's `created_by` is
# the raw Dockerfile command, which does not by itself say *which toolchain /
# stage* produced it — the datum #222 needs to decide what to thin/drop. This
# ordered keyword map coarsely classifies a layer command into a source bucket
# so the two fat layers (the report measured 3.80 GB + 2.28 GB compressed =
# 83.4% of the pull) map to a cause. Order matters: the most specific toolchain
# markers (clang-p2996, gcc-latest) are checked before the generic ones (mise,
# apt) so a `mise install` line that also mentions gcc is not misfiled.
_LAYER_SOURCE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("clang-p2996", ("clang-p2996", "/opt/clang-p2996", "p2996")),
    ("gcc-latest", ("gcc-latest", "/opt/gcc-latest")),
    ("cargo", ("cargo install", "cargo-binstall", "cargo_home", "cargo ")),
    ("node/npm", ("npm install", "npm ci", "bun install", "bun add", "corepack")),
    ("mise-tools", ("mise install", "mise use", "mise-system", "mise ")),
    ("apt", ("apt-get", "apt install", "dpkg", "add-apt-repository")),
)


def classify_layer_source(created_by: str) -> str:
    """Coarse source bucket for a layer's ``created_by`` Dockerfile command.

    Pure keyword classifier (#231 scope-(b)(a)): maps a fat layer to the
    toolchain/stage that produced it so #222 can group pull-cost by cause
    instead of eyeballing verbose ``RUN`` strings. Returns ``"other"`` when no
    marker matches — never guesses. The buckets are intentionally coarse; the
    goal is "which of base-apt / mise / the 3 C++ toolchains", not per-package
    accounting.
    """
    low = created_by.lower()
    for label, needles in _LAYER_SOURCE_PATTERNS:
        if any(needle in low for needle in needles):
            return label
    return "other"


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
        created_by = entry.get("CreatedBy", "")
        layers.append(
            {
                "created_by": created_by,
                "source": classify_layer_source(created_by),
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


# Modeled pull-time defaults (#231 scope-(b)(c)). Compressed size drives the
# network download; uncompressed size drives zstd decompression. Both are
# already captured by the benchmark, so a modeled wall-time is the user-facing
# metric the whole "measure before optimize" program is about. Defaults are
# deliberately conservative round numbers (a mid-tier connection + zstd's
# level-independent decompress throughput) and are overridable so a caller can
# model a specific link. This is an ESTIMATE, labeled as such in the summary —
# not a measured pull.
_DEFAULT_BANDWIDTH_MBPS = 200.0
_ZSTD_DECOMPRESS_MB_S = 500.0
_MEGABIT_BYTES_PER_S = 125_000.0  # 1 Mbps = 1e6 bits/s = 125_000 bytes/s
_MIB = 1024.0 * 1024.0


def estimate_pull_time_s(
    compressed_size_bytes: int,
    uncompressed_size_bytes: int,
    *,
    bandwidth_mbps: float = _DEFAULT_BANDWIDTH_MBPS,
    decompress_mb_s: float = _ZSTD_DECOMPRESS_MB_S,
) -> dict[str, float]:
    """Model image pull wall-time from compressed + uncompressed sizes.

    Pure (#231 scope-(b)(c)): ``download_s`` = compressed bytes ÷ bandwidth,
    ``decompress_s`` = uncompressed bytes ÷ zstd throughput, ``total_s`` their
    sum. The two assumptions are echoed back in the payload so a reader knows
    the model behind the number. Zero/negative bandwidth would divide by zero;
    callers pass the positive defaults, and the guard keeps a hostile override
    from raising inside the benchmark.
    """
    bandwidth = bandwidth_mbps if bandwidth_mbps > 0 else _DEFAULT_BANDWIDTH_MBPS
    decompress = decompress_mb_s if decompress_mb_s > 0 else _ZSTD_DECOMPRESS_MB_S
    download_s = compressed_size_bytes / (bandwidth * _MEGABIT_BYTES_PER_S)
    decompress_s = uncompressed_size_bytes / (decompress * _MIB)
    return {
        "download_s": round(download_s, 2),
        "decompress_s": round(decompress_s, 2),
        "total_s": round(download_s + decompress_s, 2),
        "bandwidth_mbps": bandwidth,
        "decompress_mb_s": decompress,
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
        # schema 3 (#231): per-layer `source` attribution + modeled pull-time.
        "schema_version": 3,
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
        "pull_time_estimate": estimate_pull_time_s(
            report["compressed_size_bytes"], report["image_size_bytes"]
        ),
        "tool_count": tool_count,
        "top_layers": report["top_layers"],
        "result": smoke_result["result"].lower(),
    }
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def _pull_time_total(payload: Mapping[str, Any]) -> float:
    """Modeled total pull-time from a payload, tolerating pre-schema-3 JSON.

    A baseline written before #231 has no ``pull_time_estimate`` key; treat its
    modeled pull-time as 0 so a delta against it degrades gracefully rather than
    KeyError-ing the whole summary.
    """
    estimate = payload.get("pull_time_estimate") or {}
    return float(estimate.get("total_s", 0.0))


def compare_payloads(
    baseline: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, float]:
    """Pure metric deltas (candidate - baseline) between two benchmark payloads.

    Split out of :func:`metrics_compare` (which does the file IO) so the trend
    section in the step summary (#231 scope-(b)(b)) can render a delta from
    in-memory payloads without a second file read. Positive ⇒ candidate is
    larger/slower (a regression for size/pull-time).
    """
    return {
        "image_size_delta": candidate["image_size_bytes"]
        - baseline["image_size_bytes"],
        "compressed_size_delta": candidate["compressed_size_bytes"]
        - baseline["compressed_size_bytes"],
        "pull_time_total_delta": round(
            _pull_time_total(candidate) - _pull_time_total(baseline), 2
        ),
        "smoke_wall_delta": candidate["timings_s"]["smoke_wall"]
        - baseline["timings_s"]["smoke_wall"],
        "total_wall_delta": candidate["timings_s"]["total_wall"]
        - baseline["timings_s"]["total_wall"],
    }


def metrics_compare(baseline_path: Path, candidate_path: Path) -> dict[str, Any]:
    """Compare two benchmark payloads."""
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    return {
        "baseline": str(baseline_path),
        "candidate": str(candidate_path),
        **compare_payloads(baseline, candidate),
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


def _format_signed_bytes(delta: int) -> str:
    """Signed byte delta (``+1.20 GB`` / ``-512 MB`` / ``±0 B``) for the trend."""
    if delta == 0:
        return "±0 B"
    return f"{'+' if delta > 0 else '-'}{_format_bytes(abs(delta))}"


def _format_signed_seconds(delta: float) -> str:
    """Signed second delta (``+3.20s`` / ``-1.10s`` / ``±0.00s``) for the trend."""
    if delta == 0:
        return "±0.00s"
    return f"{'+' if delta > 0 else '-'}{abs(delta):.2f}s"


def render_metrics_summary(
    payload: Mapping[str, Any],
    timing: Mapping[str, Any] | None,
    comparison: Mapping[str, Any] | None = None,
) -> str:
    """Render benchmark ``payload`` (+ optional CI ``timing``/trend) as markdown.

    GitHub-flavored markdown for ``$GITHUB_STEP_SUMMARY``. Pure — no IO.
    ``comparison`` (candidate - baseline deltas from :func:`compare_payloads`,
    #231 scope-(b)(b)) renders a trend section when supplied; the durable
    cross-run baseline store is a deferred follow-up, so the workflow leaves it
    unset for now and the section stays dormant.
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
    pull_estimate = payload.get("pull_time_estimate")
    if pull_estimate:
        bandwidth = pull_estimate.get("bandwidth_mbps", _DEFAULT_BANDWIDTH_MBPS)
        pull_total = _format_duration(pull_estimate.get("total_s", 0))
        lines.append(
            f"| Modeled pull time | ~{pull_total} "
            f"(down {bandwidth:g} Mbps + zstd decompress) |"
        )
    if "tool_count" in payload:
        lines.append(f"| Installed tools | {payload['tool_count']} |")
    lines.append(f"| Smoke result | {payload.get('result', '?').upper()} |")
    if timing is not None:
        lines.append(
            f"| CI build time (wall) | {_format_duration(timing['total_wall_s'])} |"
        )
    lines.append("")

    if comparison is not None:
        compressed_delta = _format_signed_bytes(comparison["compressed_size_delta"])
        uncompressed_delta = _format_signed_bytes(comparison["image_size_delta"])
        pull_delta = _format_signed_seconds(comparison["pull_time_total_delta"])
        lines += [
            "### Trend vs baseline",
            "",
            "| Metric | Delta (candidate - baseline) |",
            "| --- | --- |",
            f"| Compressed size | {compressed_delta} |",
            f"| Uncompressed size | {uncompressed_delta} |",
            f"| Modeled pull time | {pull_delta} |",
            "",
        ]

    top_layers = payload.get("top_layers") or []
    if top_layers:
        lines += [
            "### Largest layers",
            "",
            "| Size | Source | Created by |",
            "| --- | --- | --- |",
        ]
        lines.extend(
            f"| {_format_bytes(layer.get('size_bytes', 0))} "
            f"| {layer.get('source', 'other')} "
            f"| `{layer.get('created_by', '').replace('|', '\\|')}` |"
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
    baseline_path: Path | None = None,
) -> str:
    """Read a benchmark JSON, render a step summary, return the markdown.

    Optionally fetches upstream CI timings (when ``run_id``/``repo`` given) and
    appends the rendered markdown to ``summary_path``. When ``baseline_path`` is
    given and readable, renders a trend section (#231 scope-(b)(b)) with deltas
    vs that baseline; a missing/unreadable baseline degrades to no trend section
    rather than failing the summary (the durable baseline store is deferred).
    """
    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
    timing = fetch_build_timing(run_id, repo) if run_id and repo else None
    comparison: dict[str, float] | None = None
    if baseline_path is not None and baseline_path.is_file():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        comparison = compare_payloads(baseline, payload)
    markdown = render_metrics_summary(payload, timing, comparison)
    if summary_path is not None:
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write(markdown)
    return markdown


# --------------------------------------------------------------------------
# image-analysis tag resolution (#231)
#
# ``image-analysis.yml`` runs via ``workflow_run`` and must find the image the
# upstream CI run pushed. The pre-#231 code sought ``:<workflow_run.head_sha>``
# = the PR HEAD commit, but ``build-publish`` tags the PR image ``:<github.sha>``
# = the ephemeral ``refs/pull/N/merge`` commit (head ≠ merge for every PR), so
# the lookup missed on every PR build → ``present=false`` → all analysis steps
# skipped → job silently green. Fix (Option A): analyze ``:pr-NNN`` (which
# ``build-publish`` reliably pushes via ``type=ref,event=pr``), resolving the PR
# number from the head sha via ``commits/<sha>/pulls`` — NOT
# ``workflow_run.pull_requests[]``, which is EMPTY on same-repo PR CI runs
# (verified #231). schedule/dispatch runs keep the bare ``:<head_sha>`` tag,
# which works there because ``github.sha == head_sha ==`` a real main tip.
_PULL_REQUEST_EVENT = "pull_request"


@dataclasses.dataclass(frozen=True)
class AnalysisTarget:
    """Outcome of resolving the analyzable image for an image-analysis run."""

    ref: str | None
    present: bool
    fail: bool
    reason: str


def decide_analysis_target(
    *,
    event: str,
    head_sha: str,
    pr_number: int | None,
    image_base: str,
    tag_exists: Callable[[str], bool],
) -> AnalysisTarget:
    """Pure decision: which image ref (if any) an image-analysis run analyzes.

    ``image_base`` is the untagged ``registry/name``; ``tag_exists`` probes a
    full ref in the registry (injected so this is unit-testable without docker).

    - **pull_request** with no ``pr_number`` → FAIL. A PR CI run whose head sha
      resolves to no PR is the #231 silent-lookup signature (the empty
      ``pull_requests[]`` trap); failing loud is the zero-skip guard Ray locked,
      rather than silently skipping analysis again.
    - **pull_request** with ``pr_number`` → analyze ``:pr-NNN`` when present;
      when absent, the build was path-gated off (docs/root-mise PR) so there is
      genuinely no image — a correct, quiet green skip.
    - **schedule / workflow_dispatch** → the bare ``:<head_sha 7-char>`` tag,
      which those triggers push (``github.sha == head_sha``); quiet-skip if
      absent (no build for this run).
    """
    if event == _PULL_REQUEST_EVENT:
        if pr_number is None:
            return AnalysisTarget(
                ref=None,
                present=False,
                fail=True,
                reason=(
                    "FAIL: pull_request CI run but commits/"
                    f"{head_sha}/pulls resolved no PR number — the analyzable "
                    ":pr-NNN tag cannot be derived (#231 silent-lookup "
                    "regression); failing loud instead of skipping analysis."
                ),
            )
        tag = f"pr-{pr_number}"
        ref = f"{image_base}:{tag}"
        if tag_exists(ref):
            return AnalysisTarget(
                ref=ref,
                present=True,
                fail=False,
                reason=f"analyzing per-PR image {tag}",
            )
        return AnalysisTarget(
            ref=None,
            present=False,
            fail=False,
            reason=(
                f"{tag} absent — no image built for this PR "
                "(docs/path-gated build skipped); nothing to analyze."
            ),
        )
    tag = head_sha[:7]
    ref = f"{image_base}:{tag}"
    if tag_exists(ref):
        return AnalysisTarget(
            ref=ref, present=True, fail=False, reason=f"analyzing {event} image {tag}"
        )
    return AnalysisTarget(
        ref=None,
        present=False,
        fail=False,
        reason=f"{tag} absent (no build for this {event} run); nothing to analyze.",
    )


def _lookup_pr_number(repo: str, head_sha: str) -> int | None:
    """PR number associated with ``head_sha`` via ``gh api commits/<sha>/pulls``.

    This is the resolution the #231 verifier proved works
    (``commits/24a68c8/pulls → [{237}]``) where ``workflow_run.pull_requests[]``
    was empty. Returns ``None`` when no PR is associated or the field is absent
    — the caller turns that into the loud FAIL for a pull_request run.
    """
    result = _run(
        ["gh", "api", f"repos/{repo}/commits/{head_sha}/pulls", "--jq", ".[0].number"],
        check=False,
    )
    number = result.stdout.strip()
    return int(number) if number.isdigit() else None


def _image_tag_exists(ref: str) -> bool:
    """True when ``ref`` resolves in the registry (``imagetools inspect``)."""
    result = subprocess.run(
        ["docker", "buildx", "imagetools", "inspect", ref],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def resolve_analysis_target(
    *, event: str, head_sha: str, repo: str, image_base: str
) -> AnalysisTarget:
    """Resolve the analyzable image ref (IO wrapper over the pure decision).

    Looks the PR number up only for a pull_request event (schedule/dispatch use
    the head sha directly), then defers to :func:`decide_analysis_target` with
    the real registry probe.
    """
    pr_number = (
        _lookup_pr_number(repo, head_sha) if event == _PULL_REQUEST_EVENT else None
    )
    return decide_analysis_target(
        event=event,
        head_sha=head_sha,
        pr_number=pr_number,
        image_base=image_base,
        tag_exists=_image_tag_exists,
    )


def resolve_analysis_ref_main(
    *, event: str, head_sha: str, repo: str, image_base: str
) -> int:
    """CLI: emit ``present``/``ref`` GitHub outputs; exit 1 on the loud FAIL.

    stdout carries ONLY ``key=value`` lines (the workflow redirects it to
    ``$GITHUB_OUTPUT``); the human-readable reason goes to stderr (the run log).
    A FAIL writes the reason to stderr and returns 1 so the step (``set -e``)
    reddens the async, non-gating analyze job — visible, without blocking merge.
    """
    target = resolve_analysis_target(
        event=event, head_sha=head_sha, repo=repo, image_base=image_base
    )
    sys.stderr.write(target.reason + "\n")
    if target.fail:
        return 1
    sys.stdout.write(f"present={'true' if target.present else 'false'}\n")
    if target.ref is not None:
        sys.stdout.write(f"ref={target.ref}\n")
    return 0


@dataclasses.dataclass(frozen=True)
class ImageCommand:
    """Parsed image CLI command parameters."""

    image_ref: str
    platform: str = "linux/amd64/v2"
    command: str = "smoke"
    output_path: Path | None = None
    baseline_path: Path | None = None
    candidate_path: Path | None = None
    metrics_path: Path | None = None
    run_id: str | None = None
    repo: str | None = None
    summary_path: Path | None = None
    tier: int | None = None
    event: str | None = None
    head_sha: str | None = None
    image_base: str | None = None


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


def resolve_expected_p2996_ref_at_base() -> str:
    """The clang-p2996 ref the CURRENT local base was built from (merge-base).

    Merge-base-aware sibling of :func:`resolve_expected_p2996_ref` (which reads
    HEAD and feeds ``build_smoke_script`` — CI builds the image FROM the branch
    ``docker-bake.hcl`` pin). The local devcontainer's base predates a branch's
    ``CLANG_P2996_REF`` bump (the branch's base is built by its own PR CI, never
    locally), so the devcontainer tier-3 ref-pin (injected by
    :func:`build_tier3_script` / ``smoke-script --tier 3``) must expect the
    MERGE-BASE pin — reading HEAD would false-FAIL on a branch that bumps the
    ref. A Phase D ``CLANG_P2996_REF`` env override still wins (dispatch parity).
    Fixes the latent HEAD-read the pre-#223 bash tier-3 had (it grepped the
    mounted HEAD ``docker-bake.hcl``).
    """
    override = os.environ.get("CLANG_P2996_REF")
    if override:
        return override
    blob = base_currency_blob(_project_root(), "docker-bake.hcl")
    return _extract_bake_variable(blob.decode(), "CLANG_P2996_REF")


def resolve_expected_llvm_version_at_base() -> str:
    """The apt LLVM release the CURRENT local base was built from (merge-base).

    Merge-base-aware sibling of :func:`resolve_expected_llvm_version`. The local
    devcontainer's base predates a branch's ``mise-system.toml`` pin bump (the
    branch's base is built by its own PR CI, never locally), so the devcontainer
    tier-3 version guard (injected by :func:`build_tier3_script` / ``smoke-script
    --tier 3``) must expect the MERGE-BASE pin — reading HEAD would false-FAIL on
    a branch that bumps the LLVM version. On main, merge-base == HEAD.
    """
    blob = base_currency_blob(_project_root(), ".devcontainer/mise-system.toml")
    return _parse_apt_llvm_version(blob.decode())


_SMOKE_SCRIPT_TIER1 = 1
_SMOKE_SCRIPT_TIER3 = 3


def smoke_script_main(tier: int | None) -> int:
    """CLI: print a shared smoke core for the devcontainer smoke (#223).

    ``scripts/devcontainer-smoke.sh`` evaluates this so its in-container checks
    are byte-identical to the CI no-mount smoke — the two paths run the SAME
    python-generated bodies (:data:`_TIER1_CORE_BODY` for tier 1,
    :data:`_TIER3_COMPILER_BODY` for tier 3), so they cannot diverge. The
    injected DATA is merge-base aware (the local base predates a branch's
    image-input bump, which is validated by the branch's own PR CI build+smoke):

    - **tier 1** — image identity + exact tool-set
      (:func:`resolve_expected_identity_at_base` /
      :func:`resolve_declared_tools_at_base`).
    - **tier 3** — sanitizer + reflection compiler substrate
      (:func:`resolve_expected_p2996_ref_at_base`). ``emulated=True`` is forced:
      the amd64 container reports ``x86_64`` even under Rosetta on the arm64 Mac
      dev host, so emulation is invisible from inside (``os.uname`` can't tell) —
      and CI's native-runner smoke already exercises the TSan RUN, so the
      devcontainer always skips it (the compile still runs, proving the
      toolchain). asan/ubsan + reflection RUN fine under Rosetta and stay.

    Tier 2 (pytest + mounts + doppler secrets) has NO python-generated core —
    every tier-2 check is mount/env-dependent and has no CI no-mount counterpart,
    so there is nothing to unify; it stays entirely bash. The mount/SSH-dependent
    tier-3 checks (home-volume, TMPDIR, R2 SSH) likewise stay bash-only.
    """
    root = _project_root()
    if tier == _SMOKE_SCRIPT_TIER1:
        # The python pin comes from the SAME merge-base tool set the diff uses
        # (#140 Gap A base-currency), never a second resolution — a branch that
        # bumps python is validated by its own CI-built base, not against a
        # local base that predates the bump.
        base_tools = resolve_declared_tools_at_base(root)
        script = build_tier1_script(
            expected_identity=resolve_expected_identity_at_base(),
            expected_tools=base_tools,
            expected_python=base_tools.get("python"),
        )
    elif tier == _SMOKE_SCRIPT_TIER3:
        script = build_tier3_script(
            expected_p2996_ref=resolve_expected_p2996_ref_at_base(),
            emulated=True,
            expected_llvm_version=resolve_expected_llvm_version_at_base(),
        )
    else:
        sys.stderr.write(
            f"smoke-script: unsupported tier {tier!r} (only --tier 1 or 3)\n"
        )
        return 2
    sys.stdout.write(script)
    return 0


def _handle_smoke_script(cmd: ImageCommand) -> int:
    return smoke_script_main(cmd.tier)


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
        baseline_path=cmd.baseline_path,
    )
    sys.stdout.write(markdown)
    return 0


def _handle_resolve_analysis_ref(cmd: ImageCommand) -> int:
    if cmd.event is None or cmd.head_sha is None or cmd.image_base is None:
        sys.stderr.write("resolve-analysis-ref requires --event, --head-sha, --image\n")
        return 2
    if cmd.repo is None:
        sys.stderr.write("resolve-analysis-ref requires --repo\n")
        return 2
    return resolve_analysis_ref_main(
        event=cmd.event,
        head_sha=cmd.head_sha,
        repo=cmd.repo,
        image_base=cmd.image_base,
    )


def main(cmd: ImageCommand) -> int:
    """CLI entry point for image operations (command → handler dispatch)."""
    handlers: dict[str, Callable[[ImageCommand], int]] = {
        "smoke-script": _handle_smoke_script,
        "smoke": _handle_smoke,
        "size-report": _handle_size_report,
        "benchmark": _handle_benchmark,
        "metrics-compare": _handle_metrics_compare,
        "metrics-summary": _handle_metrics_summary,
        "resolve-analysis-ref": _handle_resolve_analysis_ref,
    }
    handler = handlers.get(cmd.command)
    if handler is None:
        msg = f"Unsupported command: {cmd.command}"
        raise ValueError(msg)
    return handler(cmd)
