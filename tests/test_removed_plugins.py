# Copyright (c) 2026 Raymond Manaloto
"""Tests for dotfiles_setup.removed_plugins and the doctor check wiring it (#1317).

Every fixture is a throwaway home directory, never the operator's: the codex
config it imitates can hold credentials. Each FAIL arm plants one realistic
reappearance; the clean fixture is the same shape with nothing planted.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from dotfiles_setup import doctor, removed_plugins

if TYPE_CHECKING:
    from pathlib import Path

_NAMES = ("fable-orchestrator", "claudex-loop")


def _home(tmp_path: Path) -> Path:
    (tmp_path / ".claude" / "plugins").mkdir(parents=True)
    (tmp_path / ".codex").mkdir()
    return tmp_path


def _find(home: Path, settings: dict[str, object] | None = None) -> list[str]:
    return removed_plugins.find_reappearances(
        _NAMES, home=home, settings_sources={"project": settings or {}}
    )


def test_a_clean_home_has_no_findings(tmp_path: Path) -> None:
    home = _home(tmp_path)
    (home / ".codex" / "config.toml").write_text(
        '[plugins."exa@exa"]\nenabled = true\n[marketplaces.exa]\nsource = "x"\n'
    )
    (home / ".claude" / "plugins" / "installed_plugins.json").write_text(
        json.dumps({"plugins": {"exa@exa": [{"scope": "user"}]}})
    )
    assert _find(home, {"enabledPlugins": {"exa@exa": True}}) == []


def test_a_settings_enable_is_a_finding(tmp_path: Path) -> None:
    found = _find(
        _home(tmp_path),
        {"enabledPlugins": {"fable-orchestrator@fable-orchestrator": True}},
    )
    assert found == ["project enables `fable-orchestrator@fable-orchestrator`"]


def test_a_disabled_settings_key_is_not_a_finding(tmp_path: Path) -> None:
    found = _find(
        _home(tmp_path),
        {"enabledPlugins": {"fable-orchestrator@fable-orchestrator": False}},
    )
    assert found == []


def test_a_claude_install_and_marketplace_are_findings(tmp_path: Path) -> None:
    home = _home(tmp_path)
    plugins = home / ".claude" / "plugins"
    (plugins / "installed_plugins.json").write_text(
        json.dumps(
            {
                "plugins": {
                    "fable-orchestrator@fable-orchestrator": [{"projectPath": "/r"}]
                }
            }
        )
    )
    (plugins / "known_marketplaces.json").write_text(
        json.dumps({"fable-orchestrator": {"source": {}}})
    )
    found = _find(home)
    assert len(found) == 2
    assert "installs `fable-orchestrator@fable-orchestrator` (/r)" in found[0]
    assert "registers marketplace `fable-orchestrator`" in found[1]


def test_codex_plugin_hook_and_marketplace_are_findings(tmp_path: Path) -> None:
    home = _home(tmp_path)
    (home / ".codex" / "config.toml").write_text(
        'secret_like = "must-never-be-printed"\n'
        '[plugins."claudex-loop@claudex-loop"]\nenabled = true\n'
        '[hooks.state."fable-orchestrator@fable-orchestrator:hooks/hooks.json:pre_tool_use:0:0"]\n'
        'trusted_hash = "sha256:abc"\n'
        '[marketplaces.claudex-loop]\nsource = "x"\n'
    )
    found = _find(home)
    assert found == [
        "~/.codex/config.toml enables plugin `claudex-loop@claudex-loop`",
        (
            "~/.codex/config.toml trusts hook "
            "`fable-orchestrator@fable-orchestrator:hooks/hooks.json:pre_tool_use:0:0`"
        ),
        "~/.codex/config.toml registers marketplace `claudex-loop`",
    ]
    assert not any("must-never-be-printed" in f or "sha256:abc" in f for f in found)


def test_a_codex_plugin_marked_disabled_is_not_a_finding(tmp_path: Path) -> None:
    """The ruled "disable" for claudex-loop: plugin off, marketplace may remain."""
    home = _home(tmp_path)
    (home / ".codex" / "config.toml").write_text(
        '[plugins."claudex-loop@claudex-loop"]\nenabled = false\n'
        '[marketplaces.claudex-loop]\nsource = "x"\n'
    )
    assert _find(home) == []


def test_a_marketplace_without_a_disabled_plugin_is_a_finding(tmp_path: Path) -> None:
    """Control for the test above: the same marketplace alone still reports."""
    home = _home(tmp_path)
    (home / ".codex" / "config.toml").write_text(
        '[marketplaces.claudex-loop]\nsource = "x"\n'
    )
    assert _find(home) == ["~/.codex/config.toml registers marketplace `claudex-loop`"]


def test_the_doctor_check_reads_names_from_the_baseline(tmp_path: Path) -> None:
    """Wiring: the doctor check reports via the baseline, and is silent without it."""
    home = _home(tmp_path)
    (home / ".codex" / "config.toml").write_text(
        '[plugins."claudex-loop@claudex-loop"]\nenabled = true\n'
    )
    setup = doctor.Setup(
        repo_root=tmp_path,
        baseline={"removed_plugins": {"names": list(_NAMES)}},
        servers=(),
        settings={},
        local_settings={},
        fnox=doctor.FnoxState(exists=False),
        environ={},
        home=home,
    )
    assert len(doctor.check_removed_plugins(setup)) == 1
    assert ("removed-plugins", doctor.check_removed_plugins) in doctor.CHECKS
    bare = doctor.Setup(
        repo_root=tmp_path,
        baseline={},
        servers=(),
        settings={},
        local_settings={},
        fnox=doctor.FnoxState(exists=False),
        environ={},
        home=home,
    )
    assert doctor.check_removed_plugins(bare) == []
