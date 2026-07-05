"""Tests for `dotfiles_setup.bootstrap_packages` — parsing the declarative
`[bootstrap.packages]` apt set that `mise bootstrap packages apply` installs
in the image (#160 T4). Build-time drift is caught in the Dockerfile itself
(`mise bootstrap packages status --json --missing` exits 1); these tests
guard the parser and the declared set's load-bearing entries.
"""

from __future__ import annotations

from pathlib import Path

from dotfiles_setup.bootstrap_packages import apt_packages_from_bootstrap

_REPO_ROOT = Path(__file__).parent.parent
_MISE_SYSTEM_TOML = _REPO_ROOT / ".devcontainer" / "mise-system.toml"

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


def test_bootstrap_packages_declares_load_bearing_set() -> None:
    """`[bootstrap.packages]` is the image's ONLY apt package source (#160 T4)
    — the load-bearing entries must never be silently dropped."""
    declared = set(apt_packages_from_bootstrap(_MISE_SYSTEM_TOML))
    missing = _LOAD_BEARING_PACKAGES - declared
    assert not missing, (
        f"load-bearing apt packages missing from [bootstrap.packages]: "
        f"{sorted(missing)}"
    )
