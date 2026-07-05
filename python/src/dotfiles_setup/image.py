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
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dotfiles_setup import _project_root
from dotfiles_setup.p2996_hash import _extract_bake_variable

if TYPE_CHECKING:
    from collections.abc import Mapping

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


def resolve_expected_config_sha256() -> str:
    """SHA-256 of the repo's ``.devcontainer/mise-system.toml``.

    The Dockerfile COPYs this file *verbatim* to
    ``/usr/local/share/mise/config.toml`` (base stage, no transform), so its
    hash is a cheap image-identity fingerprint. If the hash of the in-image
    config differs, the smoked image was NOT built from the current
    ``mise-system.toml`` — the classic stale-cached-overlay false positive
    where ``devcontainer up`` reused a ``vsc-dotfiles-<hash>`` overlay and the
    smoke reported green against old content. Fails loud if the source file is
    missing rather than silently skipping the identity guard.
    """
    config_path = _project_root() / ".devcontainer" / "mise-system.toml"
    return hashlib.sha256(config_path.read_bytes()).hexdigest()


def resolve_expected_runtime_sha256() -> str:
    """SHA-256 of the repo's ``.devcontainer/mise-runtime.toml`` (#160 T10).

    The devcontainer-runtime stage COPYs this file verbatim to
    ``/usr/local/share/mise/config.runtime.toml`` — the second half of the
    two-tier image identity: a stale runtime stage on a current base must
    fail identity just like a stale base would.
    """
    config_path = _project_root() / ".devcontainer" / "mise-runtime.toml"
    return hashlib.sha256(config_path.read_bytes()).hexdigest()


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


def build_smoke_script(
    expected_p2996_ref: str,
    *,
    expected_config_sha256: str | None = None,
    expected_runtime_sha256: str | None = None,
    expected_tools: Mapping[str, str] | None = None,
    emulated: bool = False,
) -> str:
    """Build the inline smoke test script.

    ``expected_p2996_ref`` is injected so the script can assert the
    clang-p2996 binary baked into the image was actually built from the
    pinned ref (``resolve_expected_p2996_ref``) — closing the false-positive
    where a stale/wrong-ref reflection compiler still compiles a reflection
    program and the smoke passes green. Only a 40-hex SHA triggers the strict
    equality check; a non-SHA dispatch override still gets the
    "is-a-real-p2996-build" guard.

    ``expected_config_sha256`` (gap A — image identity) is the hash of the
    repo's ``mise-system.toml``; when set, the script asserts the in-image
    ``config.toml`` matches it, catching a stale/cached-overlay image that
    would otherwise pass smoke against old content. An empty/unset value
    leaves the guard dormant (unit-test friendly).
    ``expected_runtime_sha256`` is the runtime-tier half of the same guard
    (#160 T10): the hash of ``mise-runtime.toml``, asserted against the
    in-image ``config.runtime.toml``.

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
    expected_tool_lines = (
        _format_expected_tool_lines(expected_tools) if expected_tools else ""
    )
    header = (
        "set -euo pipefail\n"
        f"EXPECTED_P2996_REF={shlex.quote(expected_p2996_ref)}\n"
        f"P2996_REF_STRICT={shlex.quote(strict)}\n"
        f"EXPECTED_CONFIG_SHA256={shlex.quote(expected_config_sha256 or '')}\n"
        f"EXPECTED_RUNTIME_SHA256={shlex.quote(expected_runtime_sha256 or '')}\n"
        f"EXPECTED_TOOL_REQUESTS={shlex.quote(expected_tool_lines)}\n"
        f"TSAN_RUN_SKIP={shlex.quote(tsan_run_skip)}\n"
    )
    return (
        header
        + """\
# #148: the base SYSTEM config ($MISE_SYSTEM_CONFIG_FILE = the Dockerfile COPY
# target /usr/local/share/mise/config.toml), NOT ${MISE_CONFIG_DIR}/config.toml
# — MISE_CONFIG_DIR is overridden at runtime to the user config dir, a
# different (chezmoi-rendered) file that false-fails identity on a current base.
MISE_CFG="${MISE_SYSTEM_CONFIG_FILE:-/usr/local/share/mise/config.toml}"
# #160 T5: the shared conf.d fragment is merged into the system config; its
# tools are attributed to this path by `mise ls --json`, so the tool-set diff
# must count both sources.
MISE_SHARED_CFG="$(dirname "$MISE_CFG")/conf.d/shared.toml"
# #160 T9/T10: the runtime tier config, discovered via MISE_ENV=runtime
# (baked as image ENV); its tools attribute to this source path.
MISE_RUNTIME_CFG="$(dirname "$MISE_CFG")/config.runtime.toml"
echo "=== image identity (mise-system config hash) ==="
if [ -n "$EXPECTED_CONFIG_SHA256" ]; then
  actual_config_sha256=$(sha256sum "$MISE_CFG" | cut -d' ' -f1)
  if [ "$actual_config_sha256" != "$EXPECTED_CONFIG_SHA256" ]; then
    echo "FAIL: in-image mise config $actual_config_sha256 !=" \
         "repo mise-system.toml $EXPECTED_CONFIG_SHA256 (stale image — rebuild)"
    exit 1
  fi
  echo "OK: image built from current mise-system.toml ($actual_config_sha256)"
else
  echo "SKIP: no expected config hash injected (identity guard dormant)"
fi
echo "=== image identity (runtime tier config hash, #160 T10) ==="
if [ -n "$EXPECTED_RUNTIME_SHA256" ]; then
  actual_runtime_sha256=$(sha256sum "$MISE_RUNTIME_CFG" | cut -d' ' -f1)
  if [ "$actual_runtime_sha256" != "$EXPECTED_RUNTIME_SHA256" ]; then
    echo "FAIL: in-image runtime config $actual_runtime_sha256 !=" \
         "repo mise-runtime.toml $EXPECTED_RUNTIME_SHA256 (stale — rebuild)"
    exit 1
  fi
  echo "OK: image built from current mise-runtime.toml ($actual_runtime_sha256)"
else
  echo "SKIP: no expected runtime hash injected (identity guard dormant)"
fi
echo "=== hk validate ==="
HK_FILE=/etc/hk/hk.pkl hk validate
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
    expected_config_sha256: str | None = None,
    emulated: bool | None = None,
) -> list[str]:
    """Build the docker command used for smoke validation.

    The declared tool set (#143) is always resolved from the repo's
    ``mise-system.toml`` here — it has no injectable override because, unlike the
    p2996-ref / config-hash, nothing needs to smoke against a *synthetic* tool
    set; ``build_smoke_script`` remains the injection seam for unit tests.
    """
    if expected_p2996_ref is None:
        expected_p2996_ref = resolve_expected_p2996_ref()
    if expected_config_sha256 is None:
        expected_config_sha256 = resolve_expected_config_sha256()
    if emulated is None:
        emulated = _is_emulated(platform)
    script = build_smoke_script(
        expected_p2996_ref,
        expected_config_sha256=expected_config_sha256,
        expected_runtime_sha256=resolve_expected_runtime_sha256(),
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

    payload = {
        "schema_version": 1,
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


@dataclasses.dataclass(frozen=True)
class ImageCommand:
    """Parsed image CLI command parameters."""

    image_ref: str
    platform: str = "linux/amd64/v2"
    command: str = "smoke"
    output_path: Path | None = None
    baseline_path: Path | None = None
    candidate_path: Path | None = None


def verify_tools_main() -> int:
    """Assert the installed tool set matches ``.devcontainer/mise-system.toml``.

    Runs ``mise ls --json`` against the ambient mise (inside the devcontainer)
    and compares to the repo's declared ``[tools]`` — the in-container sibling of
    the ``build_smoke_script`` assertion (#143), sharing the same parse/compare
    core so the two smoke paths cannot diverge. Called by
    ``scripts/devcontainer-smoke.sh`` (keeps the diff logic in python, not bash).
    """
    declared = resolve_declared_tools()
    config_file = os.environ.get("MISE_SYSTEM_CONFIG_FILE", SYSTEM_CONFIG_FILE)
    result = subprocess.run(
        ["mise", "ls", "--json"],
        capture_output=True,
        text=True,
        check=True,
    )
    shared_file = str(Path(config_file).parent / "conf.d" / "shared.toml")
    installed = installed_tools_from_mise_ls(result.stdout, (config_file, shared_file))
    diffs = diff_tool_sets(declared, installed)
    if diffs:
        sys.stderr.write(
            "FAIL: installed tool set differs from mise-system.toml [tools]:\n"
        )
        for line in diffs:
            sys.stderr.write(f"  {line}\n")
        return 1
    sys.stdout.write(
        f"OK: installed tool set matches mise-system.toml [tools] "
        f"({len(declared)} tools)\n"
    )
    return 0


def main(cmd: ImageCommand) -> int:
    """CLI entry point for image operations."""
    if cmd.command == "verify-tools":
        return verify_tools_main()
    if cmd.command == "smoke":
        result = smoke(cmd.image_ref, platform=cmd.platform)
        if result["result"] == "FAIL":
            sys.stderr.write(f"FAIL: {cmd.image_ref}\n")
            sys.stderr.write(result.get("stderr", ""))
            return 1
        sys.stderr.write(f"PASS: {cmd.image_ref}\n")
        return 0
    if cmd.command == "size-report":
        payload = size_report(cmd.image_ref, platform=cmd.platform)
        sys.stdout.write(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
        )
        return 0
    if cmd.command == "benchmark":
        payload = benchmark(
            cmd.image_ref,
            platform=cmd.platform,
            output_path=cmd.output_path,
        )
        sys.stdout.write(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
        )
        return 0
    if cmd.command == "metrics-compare":
        if cmd.baseline_path is None or cmd.candidate_path is None:
            msg = "baseline_path and candidate_path are required"
            raise ValueError(msg)
        payload = metrics_compare(cmd.baseline_path, cmd.candidate_path)
        sys.stdout.write(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
        )
        return 0
    msg = f"Unsupported command: {cmd.command}"
    raise ValueError(msg)
