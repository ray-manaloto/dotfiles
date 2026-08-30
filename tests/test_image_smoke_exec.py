# Copyright (c) 2026 Raymond Manaloto
"""Containerized real-toolchain execution tests for the #223 smoke cores.

Backlog item 2 (#231 follow-up). The tier-1 tool-set jq/diff block and the
tier-3 clang-p2996 compiler substrate are golden/substring-tested in
``test_image_smoke.py`` — but that never *executes* them against a real
toolchain. These tests generate the tier-1/tier-3 smoke cores exactly as
``image smoke-script --tier {1,3}`` does (merge-base-aware) and run them against
the real local ``:dev`` image, asserting both the happy path and a tampered
FAIL so a silently-non-running check can't pass green.

**Gated, not silently skipped.** Every test is marked ``image_exec``, which the
root ``pytest.ini`` deselects by default (``addopts = -m 'not image_exec'``), so
``mise run test`` and CI ``contract-preflight`` (no Docker, no ``:dev``) never
run them. Invoke explicitly via ``mise run smoke-exec`` (``pytest -m
image_exec`` re-selects — last ``-m`` wins). If Docker or the image is absent
under that explicit run, the module skips with a loud reason rather than
erroring — an honest gate, never a false green.

The devcontainer path forces ``emulated=True`` (the amd64 container reports
``x86_64`` even under Rosetta on the arm64 Mac dev host, invisible from inside),
so the ThreadSanitizer RUN is skipped while the compile still proves the
toolchain; asan/ubsan + reflection RUN fine under Rosetta.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import _project_root
from dotfiles_setup.image import (
    build_tier1_script,
    build_tier3_script,
    resolve_declared_tools_at_base,
    resolve_expected_identity_at_base,
    resolve_expected_p2996_ref_at_base,
)
from dotfiles_setup.platform_target import platform_arch, resolve_platform

pytestmark = pytest.mark.image_exec

# The local devcontainer base — the same tag `mise run sync` converges onto and
# `scripts/devcontainer-smoke.sh` runs against.
_DEV_IMAGE = "ghcr.io/ray-manaloto/dotfiles-devcontainer:dev"

# A syntactically valid but WRONG 40-hex clang-p2996 ref, to force the tier-3
# ref-pin guard's strict-equality FAIL against the real in-image binary.
_WRONG_P2996_REF = "dead" * 10

# tier-3 compiles asan/ubsan + reflection with clang-p2996 under Rosetta on the
# arm64 dev host — minutes, not seconds. Bound it generously so a genuine hang
# is still caught, but a slow-but-honest emulated compile is not.
_TIER3_TIMEOUT_S = 900
_TIER1_TIMEOUT_S = 180


def _docker_available() -> bool:
    """True iff a Docker daemon answers — the gate for the whole module."""
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        return False
    return result.returncode == 0


def _image_present(image: str) -> bool:
    """True iff the image is pulled locally (no network round-trip)."""
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


@pytest.fixture(scope="module")
def dev_image() -> str:
    """The local ``:dev`` image, or a loud skip when the gate can't run.

    A missing Docker daemon or un-pulled image is an environment gap, not a
    defect — skip with an actionable reason instead of erroring (this only runs
    under the explicit ``mise run smoke-exec``, never in the default suite).
    """
    if not _docker_available():
        pytest.skip("docker daemon unavailable — image_exec needs a running Docker")
    if not _image_present(_DEV_IMAGE):
        pytest.skip(f"{_DEV_IMAGE} not pulled locally — run `mise run sync` first")
    return _DEV_IMAGE


def _run_in_image(
    image: str, script: str, *, timeout: int
) -> subprocess.CompletedProcess[str]:
    """Execute a generated smoke core inside ``image`` via a login shell.

    ``bash -l`` sources the image's mise activation so jq / clang++ / mise
    resolve exactly as they do under ``scripts/devcontainer-smoke.sh``; the
    script arrives on stdin (``-i``), so no host mount is needed.
    """
    return subprocess.run(
        ["docker", "run", "--rm", "-i", image, "bash", "-l"],
        input=script,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def test_tier1_core_passes_against_dev(dev_image: str) -> None:
    """The merge-base tier-1 core runs GREEN against the current ``:dev``.

    Exercises what the golden/substring tests can't: the identity hashes and the
    jq/diff tool-set block actually executed against a real ``mise ls --json``.
    A red here means the local ``:dev`` drifted from the branch source — which is
    exactly the stale-base condition the gate exists to catch.
    """
    # `_DEV_IMAGE` is the amd64 image (DOTFILES_PLATFORM pin), run under Rosetta
    # on this arm64 Mac host — so the expected set must be resolved for amd64,
    # not the host's own `uname` (#841; that derivation is for code running
    # INSIDE the container, e.g. ``smoke_script_main``, not this host-side test).
    script = build_tier1_script(
        expected_identity=resolve_expected_identity_at_base(),
        expected_tools=resolve_declared_tools_at_base(
            _project_root(), arch=platform_arch(resolve_platform())
        ),
    )

    result = _run_in_image(dev_image, script, timeout=_TIER1_TIMEOUT_S)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "image built from current" in result.stdout
    assert "OK: installed tool set matches mise-system.toml [tools]" in result.stdout


def test_tier1_toolset_block_fails_on_declared_not_installed(dev_image: str) -> None:
    """The jq/diff tool-set block FAILs when a declared tool isn't installed.

    Identity stays correct (real hashes) so the failure isolates to the tool-set
    block: an injected declared-but-absent tool must surface as a ``<`` diff and
    exit 1 — proving the block runs its set-diff, not merely that it's present.
    """
    tampered_tools = dict(
        resolve_declared_tools_at_base(
            _project_root(), arch=platform_arch(resolve_platform())
        )
    )
    tampered_tools["zzz-not-a-real-tool"] = "9.9.9"
    script = build_tier1_script(
        expected_identity=resolve_expected_identity_at_base(),
        expected_tools=tampered_tools,
    )

    result = _run_in_image(dev_image, script, timeout=_TIER1_TIMEOUT_S)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "installed tool set differs from mise-system.toml [tools]" in result.stdout


def test_tier3_compiler_substrate_compiles_against_dev(dev_image: str) -> None:
    """The tier-3 substrate compiles asan/ubsan + reflection on the real image.

    The heavy, high-value assertion: the clang-p2996 toolchain baked into
    ``:dev`` actually compiles the sanitizer + reflection programs (the TSan RUN
    is skipped under emulation; the compile still proves the toolchain) and the
    in-image ref matches the merge-base pin.
    """
    script = build_tier3_script(
        expected_p2996_ref=resolve_expected_p2996_ref_at_base(),
        emulated=True,
    )

    result = _run_in_image(dev_image, script, timeout=_TIER3_TIMEOUT_S)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "matches pinned CLANG_P2996_REF" in result.stdout


def test_tier3_ref_pin_fails_on_wrong_ref(dev_image: str) -> None:
    """The tier-3 ref-pin guard FAILs when the expected ref is wrong.

    The substrate compiles fine (a stale/wrong-ref reflection compiler still
    compiles reflection code — the exact false-positive the pin closes), so only
    the strict-equality ref check against the real in-image binary catches it.
    """
    script = build_tier3_script(
        expected_p2996_ref=_WRONG_P2996_REF,
        emulated=True,
    )

    result = _run_in_image(dev_image, script, timeout=_TIER3_TIMEOUT_S)

    assert result.returncode == 1, result.stdout + result.stderr
    assert _WRONG_P2996_REF in result.stdout
