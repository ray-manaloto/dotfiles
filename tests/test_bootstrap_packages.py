# Copyright (c) 2026 Raymond Manaloto
"""Tests for `dotfiles_setup.bootstrap_packages`.

Parses the declarative `[bootstrap.packages]` apt set that `mise bootstrap
packages apply` installs in the image (#160 T4). Build-time drift is caught in
the Dockerfile itself (`mise bootstrap packages status --json --missing` exits
1); these tests guard the parser and the declared set's load-bearing entries.
"""

from __future__ import annotations

import json
from pathlib import Path

from dotfiles_setup.bootstrap_packages import (
    apt_packages_from_bootstrap,
    gap_report_failures,
)

_REPO_ROOT = Path(__file__).parent.parent
_MISE_SYSTEM_TOML = _REPO_ROOT / ".devcontainer" / "mise-system.toml"


def _toml_declaring(tmp_path: Path, *names: str) -> Path:
    toml = tmp_path / "mise-system.toml"
    lines = [f'"apt:{name}" = "latest"' for name in names]
    toml.write_text("[bootstrap.packages]\n" + "\n".join(lines) + "\n")
    return toml


def _status_json(*entries: tuple[str, str]) -> str:
    return json.dumps(
        {
            "apt": {
                "available": True,
                "packages": [
                    {
                        "package": name,
                        "requested_version": "latest",
                        "state": state,
                        "installed_version": "1.0",
                    }
                    for name, state in entries
                ],
            }
        }
    )


# Packages whose absence breaks the build or a documented invariant:
# curl/ca-certificates must stay declared even though the Dockerfile seed
# layer installs them (the status gate reports the full declarative set);
# build-essential backs rust/cargo/conda toolchain installs; gnupg backs
# mise signature verification (build.gnupg-installed contract); sudo/zsh
# back the devcontainer user experience.
_LOAD_BEARING_PACKAGES = frozenset(
    {"build-essential", "ca-certificates", "curl", "gnupg", "sudo", "zsh"}
)


def test_apt_packages_from_bootstrap_strips_prefix(tmp_path: Path) -> None:
    toml = tmp_path / "mise-system.toml"
    toml.write_text(
        "[bootstrap.packages]\n"
        '"apt:curl" = "latest"\n'
        '"apt:zsh" = "latest"\n'
        '"brew:jq" = "latest"\n'
    )
    assert apt_packages_from_bootstrap(toml) == ["curl", "zsh"]


def test_gap_report_clean(tmp_path: Path) -> None:
    toml = _toml_declaring(tmp_path, "curl", "zsh")
    report = _status_json(("curl", "installed"), ("zsh", "installed"))
    assert gap_report_failures(report, toml) == []


def test_gap_report_flags_missing_and_mismatch(tmp_path: Path) -> None:
    toml = _toml_declaring(tmp_path, "curl", "zsh")
    report = _status_json(("curl", "missing"), ("zsh", "version_mismatch"))
    failures = gap_report_failures(report, toml)
    assert any("curl: missing" in failure for failure in failures)
    assert any("zsh: version_mismatch" in failure for failure in failures)


def test_gap_report_flags_unavailable_manager(tmp_path: Path) -> None:
    """`status --missing` does NOT exit 1 on an unavailable manager.

    It emits state "skipped", so the gap report must catch it instead.
    """
    toml = _toml_declaring(tmp_path, "curl")
    report = json.dumps({"apt": {"available": False, "reason": "apt-get not found"}})
    failures = gap_report_failures(report, toml)
    assert any("unexpectedly unavailable" in failure for failure in failures)


def test_gap_report_flags_set_drift_both_directions(tmp_path: Path) -> None:
    """An empty/partial report must fail loudly, as must undeclared extras.

    An empty/partial report can mean config discovery failed in the image.
    """
    toml = _toml_declaring(tmp_path, "curl", "zsh")
    report = _status_json(("curl", "installed"), ("jq", "installed"))
    failures = gap_report_failures(report, toml)
    assert any("zsh: declared" in failure for failure in failures)
    assert any("jq: reported" in failure for failure in failures)


def test_gap_report_flags_absent_apt_manager(tmp_path: Path) -> None:
    toml = _toml_declaring(tmp_path, "curl")
    failures = gap_report_failures(json.dumps({"brew": {"available": True}}), toml)
    assert failures == ["no 'apt' manager in status report (managers: ['brew'])"]


def test_bootstrap_packages_declares_load_bearing_set() -> None:
    """`[bootstrap.packages]` is the image's ONLY apt package source (#160 T4).

    The load-bearing entries must never be silently dropped.
    """
    declared = set(apt_packages_from_bootstrap(_MISE_SYSTEM_TOML))
    missing = _LOAD_BEARING_PACKAGES - declared
    assert not missing, (
        f"load-bearing apt packages missing from [bootstrap.packages]: "
        f"{sorted(missing)}"
    )
