# Copyright (c) 2026 Raymond Manaloto
"""Tests for the removed-plugin doctor guard and its delegated readers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from dotfiles_setup import doctor, removed_plugins

if TYPE_CHECKING:
    from pathlib import Path

_NAMES = ("example-plugin", "claudex-loop")
_EXAMPLE = "example-plugin@other-market"


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
    found = _find(_home(tmp_path), {"enabledPlugins": {_EXAMPLE: True}})
    assert found == [f"project enables `{_EXAMPLE}`"]


def test_a_disabled_settings_key_is_not_a_finding(tmp_path: Path) -> None:
    found = _find(_home(tmp_path), {"enabledPlugins": {_EXAMPLE: False}})
    assert found == []


def test_a_claude_install_and_marketplace_are_findings(tmp_path: Path) -> None:
    home = _home(tmp_path)
    plugins = home / ".claude" / "plugins"
    (plugins / "installed_plugins.json").write_text(
        json.dumps({"plugins": {_EXAMPLE: [{"projectPath": "/r"}]}})
    )
    (plugins / "known_marketplaces.json").write_text(
        json.dumps({"example-plugin": {"source": {}}, "other-market": {"source": {}}})
    )
    found = _find(home)
    assert found == [
        f"~/.claude/plugins/installed_plugins.json installs `{_EXAMPLE}` (/r)",
        (
            "~/.claude/plugins/known_marketplaces.json registers marketplace "
            "`example-plugin`"
        ),
    ]


def test_codex_plugin_hook_and_marketplace_are_findings(tmp_path: Path) -> None:
    home = _home(tmp_path)
    (home / ".codex" / "config.toml").write_text(
        'secret_like = "must-never-be-printed"\n'
        '[plugins."claudex-loop@claudex-loop"]\nenabled = true\n'
        f'[hooks.state."{_EXAMPLE}:hooks/hooks.json:pre_tool_use:0:0"]\n'
        'trusted_hash = "sha256:abc"\n'
        '[marketplaces.claudex-loop]\nsource = "x"\n'
    )
    found = _find(home)
    assert found == [
        "~/.codex/config.toml enables plugin `claudex-loop@claudex-loop`",
        (
            "~/.codex/config.toml trusts hook "
            f"`{_EXAMPLE}:hooks/hooks.json:pre_tool_use:0:0`"
        ),
        "~/.codex/config.toml registers marketplace `claudex-loop`",
    ]
    assert not any(
        "must-never-be-printed" in item or "sha256:abc" in item for item in found
    )


def test_a_codex_plugin_marked_disabled_is_not_a_finding(tmp_path: Path) -> None:
    home = _home(tmp_path)
    (home / ".codex" / "config.toml").write_text(
        '[plugins."claudex-loop@claudex-loop"]\nenabled = false\n'
        '[marketplaces.claudex-loop]\nsource = "x"\n'
    )
    assert _find(home) == []


def test_a_marketplace_without_a_disabled_plugin_is_a_finding(tmp_path: Path) -> None:
    home = _home(tmp_path)
    (home / ".codex" / "config.toml").write_text(
        '[marketplaces.claudex-loop]\nsource = "x"\n'
    )
    assert _find(home) == ["~/.codex/config.toml registers marketplace `claudex-loop`"]


def test_the_doctor_check_reads_names_from_the_baseline(tmp_path: Path) -> None:
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
    assert doctor.check_removed_plugins(bare) == [
        (
            "removed-plugins: `doctor.toml` has no [removed_plugins].names, so no "
            "removed plugin is being watched"
        )
    ]


def test_a_corrupt_registry_is_unchecked_not_clean(tmp_path: Path) -> None:
    home = _home(tmp_path)
    (home / ".claude" / "plugins" / "installed_plugins.json").write_text("{trunc")
    found = _find(home)
    assert found == [
        (
            "~/.claude/plugins/installed_plugins.json is unreadable "
            "(JSONDecodeError), so claudex-loop, example-plugin went unchecked"
        )
    ]


def test_a_settings_marketplace_declaration_is_a_finding(tmp_path: Path) -> None:
    found = _find(
        _home(tmp_path),
        {"extraKnownMarketplaces": {"example-plugin": {"source": {}}}},
    )
    assert found == ["project declares marketplace `example-plugin`"]


def test_a_surviving_cache_copy_is_a_finding(tmp_path: Path) -> None:
    home = _home(tmp_path)
    cache = home / ".claude" / "plugins" / "cache" / "other-market" / "example-plugin"
    cache.mkdir(parents=True)
    assert _find(home) == [f"{cache} still holds a cached copy"]


def test_a_surviving_data_directory_is_a_finding(tmp_path: Path) -> None:
    """A bare watched name is checked at its exact id in each recorded marketplace."""
    home = _home(tmp_path)
    plugins = home / ".claude" / "plugins"
    (plugins / "known_marketplaces.json").write_text(
        json.dumps({"other-market": {"source": {}}})
    )
    data = plugins / "data" / "example-plugin-other-market"
    data.mkdir(parents=True)
    (plugins / "data" / "example-plugin-extra-other-market").mkdir()

    assert _find(home) == [f"{data} still holds plugin data"]


def test_hook_trust_of_a_disabled_codex_plugin_is_not_a_finding(
    tmp_path: Path,
) -> None:
    home = _home(tmp_path)
    (home / ".codex" / "config.toml").write_text(
        '[plugins."claudex-loop@claudex-loop"]\nenabled = false\n'
        '[hooks.state."claudex-loop@claudex-loop:hooks/hooks.json:stop:0:0"]\n'
        'trusted_hash = "sha256:abc"\n'
    )
    assert _find(home) == []


def test_the_doctor_check_skips_when_home_is_unavailable(tmp_path: Path) -> None:
    setup = doctor.Setup(
        repo_root=tmp_path,
        baseline={"removed_plugins": {"names": list(_NAMES)}},
        servers=(),
        settings={},
        local_settings={},
        fnox=doctor.FnoxState(exists=False),
        environ={},
        home=None,
    )
    assert doctor.check_removed_plugins(setup) == []


def test_the_doctor_labels_unreadable_state_as_could_not_check(tmp_path: Path) -> None:
    home = _home(tmp_path)
    (home / ".claude" / "plugins" / "installed_plugins.json").write_text("{trunc")
    setup = doctor.Setup(
        repo_root=tmp_path,
        baseline={"removed_plugins": {"names": ["example-plugin"]}},
        servers=(),
        settings={},
        local_settings={},
        fnox=doctor.FnoxState(exists=False),
        environ={},
        home=home,
    )

    found = doctor.check_removed_plugins(setup)

    assert len(found) == 1
    assert found[0].startswith("removed plugin could not check:")
    assert "reappeared" not in found[0]
