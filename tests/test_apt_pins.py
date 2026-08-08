# Copyright (c) 2026 Raymond Manaloto
"""Tests for the local-first apt-pin gate (dotfiles_setup.apt_pins).

Two layers: isolated logic tests (a fixture mise-system.toml / Dockerfile, so
parsing and script generation are exercised without docker or the network) and
real-repo guards (the tree's own declarations must parse, and the probe must be
pointed at the image the Dockerfile actually builds).

The probe's own two arms — a clean tree PASSES, a corrupted pin FAILS with
`E: Version '...' was not found` — are NOT reproducible here: they need docker,
amd64 emulation, and the network. They were run by hand against the real base
(2026-07-16) and are the reason `mise run verify-apt-pins` is believed. What is
tested here is everything that decides WHAT the probe asks.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import apt_pins

REPO_ROOT = Path(__file__).parent.parent

_FIXTURE_TOML = """\
[tools]
node = "latest"

[bootstrap.packages]
"apt:curl" = "8.18.0-1ubuntu2.3"
"apt:zlib1g-dev" = "1:1.3.dfsg+really1.3.1-1ubuntu3"
"apt:sudo" = "latest"
"pipx:ruff" = "1.2.3"
"""

_FIXTURE_DOCKERFILE = """\
# comment
ARG BASE_IMAGE=ubuntu:26.04@sha256:abc123
ARG LLVM_APT_SIGNING_FINGERPRINT=DEADBEEF
RUN echo ARG BASE_IMAGE=not-a-real-arg-line
"""


@pytest.fixture
def fixture_toml(tmp_path: Path) -> Path:
    """A mise-system.toml with pinned, unpinned, and non-apt entries."""
    path = tmp_path / "mise-system.toml"
    path.write_text(_FIXTURE_TOML)
    return path


def test_pinned_excludes_latest_and_non_apt(fixture_toml: Path) -> None:
    """Only pinned `apt:` entries are returned, prefix stripped."""
    assert apt_pins.pinned_apt_packages(fixture_toml) == {
        "curl": "8.18.0-1ubuntu2.3",
        "zlib1g-dev": "1:1.3.dfsg+really1.3.1-1ubuntu3",
    }


def test_unpinned_lists_only_latest_apt_entries(fixture_toml: Path) -> None:
    """`"latest"` apt entries are reported; `pipx:` is out of scope."""
    assert apt_pins.unpinned_apt_packages(fixture_toml) == ["sudo"]


def test_dockerfile_arg_reads_top_level_arg_only() -> None:
    """A top-level `ARG x=y` is read; the same text inside RUN is not.

    The probe must test the image the build starts FROM, so a stray mention
    must never win over the real ARG.
    """
    assert (
        apt_pins.dockerfile_arg(_FIXTURE_DOCKERFILE, "BASE_IMAGE")
        == "ubuntu:26.04@sha256:abc123"
    )
    assert (
        apt_pins.dockerfile_arg(_FIXTURE_DOCKERFILE, "LLVM_APT_SIGNING_FINGERPRINT")
        == "DEADBEEF"
    )


def test_dockerfile_arg_missing_raises() -> None:
    """A missing ARG is loud — never a silently-empty probe target."""
    with pytest.raises(ValueError, match=re.escape("no top-level `ARG NOPE=...`")):
        apt_pins.dockerfile_arg(_FIXTURE_DOCKERFILE, "NOPE")


def test_probe_script_simulates_every_pin_in_one_transaction() -> None:
    """All pins land in ONE `--simulate`, which is how mise applies them.

    A per-package loop would pass on a set that conflicts as a group, so the
    single transaction is the point, not an optimisation.
    """
    script = apt_pins.probe_script({"curl": "1.0", "zsh": "2.0"}, "ABCD1234")
    assert script.count("apt-get install --simulate") == 1
    assert "curl=1.0 zsh=2.0" in script
    assert "APT_PINS_OK" in script


def test_probe_script_pins_the_signing_fingerprint() -> None:
    """The apt.llvm.org key is fingerprint-checked, as the Dockerfile does."""
    script = apt_pins.probe_script({"clang-22": "1:22"}, "CAFEBABE")
    assert 'if [ "$actual" != "CAFEBABE" ]; then' in script
    assert script.startswith("set -euo pipefail\n")


def test_docker_command_forces_amd64() -> None:
    """The pins resolve for the image's arch, not this ARM Mac's (R3)."""
    argv = apt_pins.docker_command("ubuntu:26.04@sha256:abc", "echo hi")
    assert argv[:6] == [
        "docker",
        "run",
        "--rm",
        "--platform",
        "linux/amd64",
        "ubuntu:26.04@sha256:abc",
    ]
    assert argv[-2:] == ["-c", "echo hi"]


def test_real_tree_declares_every_apt_package_pinned() -> None:
    """#288's acceptance: no `apt:` entry is left on `"latest"`.

    The rationale for each pin lives in the `[bootstrap.packages]` header; this
    asserts the state that rationale describes, so a future "latest" needs a
    deliberate diff here too.
    """
    mise_system = REPO_ROOT / apt_pins.MISE_SYSTEM_TOML
    assert apt_pins.unpinned_apt_packages(mise_system) == []
    assert len(apt_pins.pinned_apt_packages(mise_system)) > 60


def test_real_tree_ubuntu_pins_are_not_release_pocket_versions() -> None:
    """Guard the finding that made #288's proposed config non-functional.

    Ubuntu freezes the LTS release pocket at release day, so a `resolute`-only
    pin is both security-stale AND uninstallable (`curl` hard-depends on its
    co-versioned `libcurl4t64`, which apt will not drag below its candidate).
    These four are the packages measured to differ across pockets on
    2026-07-16; if one is ever reverted to its release-pocket value, the base
    build breaks in CI — fail here instead, where it costs 60 seconds.
    """
    pins = apt_pins.pinned_apt_packages(REPO_ROOT / apt_pins.MISE_SYSTEM_TOML)
    release_pocket_traps = {
        "curl": "8.18.0-1ubuntu2",
        "libssl-dev": "3.5.5-1ubuntu3",
        "libsqlite3-dev": "3.46.1-9",
        "ca-certificates": "20260223",
    }
    for name, frozen in release_pocket_traps.items():
        assert pins[name] != frozen, (
            f"{name} is pinned to the frozen resolute release-pocket version "
            f"{frozen}; it needs the newer -updates/-security version"
        )
