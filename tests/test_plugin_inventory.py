# Copyright (c) 2026 Raymond Manaloto
"""Tests for exact-selector CLI and bounded repository plugin inventory."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

from dotfiles_setup import plugin_inventory

if TYPE_CHECKING:
    import pytest

_PLUGIN = "ponytail@ponytail"


def _result(
    *, stdout: str = "", stderr: str = "", returncode: int = 0
) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_codex_rows_require_both_exact_selector_halves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "installed": [
            {
                "pluginId": "engineering-suite-ponytail@openai-curated-remote",
                "name": "engineering-suite-ponytail",
                "marketplaceName": "openai-curated-remote",
                "installed": True,
                "enabled": True,
            },
            {
                "pluginId": _PLUGIN,
                "name": "ponytail",
                "marketplaceName": "ponytail",
                "installed": False,
                "enabled": False,
            },
        ],
        "available": [],
    }
    monkeypatch.setattr(
        plugin_inventory.subprocess,
        "run",
        lambda *_args, **_kwargs: _result(stdout=json.dumps(payload)),
    )

    rows, error = plugin_inventory.codex_cli_rows(_PLUGIN, timeout=1)

    assert rows == []
    assert error is None


def test_codex_rows_report_an_inconsistent_plugin_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "installed": [
            {
                "pluginId": "wrong@wrong",
                "name": "ponytail",
                "marketplaceName": "ponytail",
                "installed": True,
                "enabled": True,
            }
        ]
    }
    monkeypatch.setattr(
        plugin_inventory.subprocess,
        "run",
        lambda *_args, **_kwargs: _result(stdout=json.dumps(payload)),
    )

    rows, error = plugin_inventory.codex_cli_rows(_PLUGIN, timeout=1)

    assert rows == []
    assert error == "codex plugin list --json pluginId mismatch for ponytail@ponytail"


def test_claude_rows_match_the_full_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = [
        {"id": "not-ponytail@ponytail", "scope": "user", "enabled": True},
        {"id": _PLUGIN, "scope": "project", "enabled": True},
    ]
    monkeypatch.setattr(
        plugin_inventory.subprocess,
        "run",
        lambda *_args, **_kwargs: _result(stdout=json.dumps(payload)),
    )

    rows, error = plugin_inventory.claude_cli_rows(_PLUGIN, timeout=1)

    assert rows == [f"{_PLUGIN} scope=project enabled=True"]
    assert error is None


def test_discover_repos_adds_existing_worktrees_and_skips_prunable_ones(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "github"
    repo = root / "owner" / "repo"
    worktree = tmp_path / "worktree"
    stale = tmp_path / "gone"
    (repo / ".git").mkdir(parents=True)
    worktree.mkdir()
    output = (
        f"worktree {repo}\nHEAD abc\nbranch refs/heads/main\n\n"
        f"worktree {worktree}\nHEAD def\nbranch refs/heads/feature\n\n"
        f"worktree {stale}\nHEAD 000\n"
        "prunable gitdir file points to non-existent location\n"
    )
    settings = worktree / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"enabledPlugins": {_PLUGIN: True}}))
    grepped: list[Path] = []

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        if argv[:4] == ["git", "-C", str(repo), "worktree"]:
            return _result(stdout=output)
        if argv[:6] == ["mise", "exec", "--", "claude", "plugin", "list"]:
            return _result(stdout="[]")
        if argv[:6] == ["mise", "exec", "--", "codex", "plugin", "list"]:
            return _result(stdout=json.dumps({"installed": [], "available": []}))
        if len(argv) > 3 and argv[3] == "grep":
            grepped.append(Path(argv[2]))
            return _result(returncode=1)
        raise AssertionError(argv)

    monkeypatch.setattr(plugin_inventory.subprocess, "run", run)

    assert plugin_inventory.discover_repos(root) == [repo, worktree]
    result = plugin_inventory.inventory(_PLUGIN, home=tmp_path, root=root)
    assert result.worktree_settings == (settings,)
    assert result.stale_worktrees == (stale,)
    assert grepped == [repo]


def _git(*argv: str, cwd: Path) -> None:
    subprocess.run(
        ["git", *argv],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_live_references_excludes_historical_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "docs" / "research").mkdir(parents=True)
    (repo / "src" / "live.txt").write_text("ponytail\n")
    (repo / "docs" / "research" / "history.md").write_text("ponytail\n")
    _git("init", "-q", cwd=repo)
    _git("add", "src/live.txt", "docs/research/history.md", cwd=repo)

    found = plugin_inventory.live_references(repo, "ponytail")

    assert [(item.path, item.line, item.text) for item in found] == [
        ("src/live.txt", 1, "ponytail")
    ]


def test_cli_probe_errors_are_not_reported_as_absence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        return _result(returncode=7, stderr=f"{argv[0]} failed")

    monkeypatch.setattr(plugin_inventory.subprocess, "run", fail)

    rows, error = plugin_inventory.claude_cli_rows(_PLUGIN, timeout=1)

    assert rows == []
    assert error == "mise exec -- claude plugin list --json exited 7: mise failed"


def test_inventory_reads_marketplace_declarations_and_planning_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    plugins_dir = home / ".claude" / "plugins"
    target_install = plugins_dir / "cache" / "c" / "a-b" / "1.0.0"
    sibling_install = plugins_dir / "cache" / "c" / "beta" / "1.0.0"
    dependency_install = plugins_dir / "cache" / "deps" / "dep" / "1.0.0"
    collision_install = plugins_dir / "cache" / "b-c" / "a" / "1.0.0"
    for install in (
        target_install,
        sibling_install,
        dependency_install,
        collision_install,
    ):
        (install / ".claude-plugin").mkdir(parents=True)
    (target_install / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"dependencies": {"dep@deps": "1.0.0"}})
    )
    (sibling_install / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"dependencies": {"a-b@c": "1.0.0"}})
    )
    (dependency_install / ".claude-plugin" / "plugin.json").write_text("{}")
    (collision_install / ".claude-plugin" / "plugin.json").write_text("{}")
    (plugins_dir / "installed_plugins.json").write_text(
        json.dumps(
            {
                "plugins": {
                    "a-b@c": [
                        {
                            "scope": "user",
                            "installPath": str(target_install),
                        }
                    ],
                    "beta@c": [
                        {
                            "scope": "user",
                            "installPath": str(sibling_install),
                        }
                    ],
                    "dep@deps": [
                        {
                            "scope": "user",
                            "auto": True,
                            "installPath": str(dependency_install),
                        }
                    ],
                    "a@b-c": [
                        {
                            "scope": "user",
                            "installPath": str(collision_install),
                        }
                    ],
                    "ghost@c": [],
                }
            }
        )
    )
    root = tmp_path / "github"
    repo = root / "owner" / "repo"
    (repo / ".git").mkdir(parents=True)
    settings = repo / ".claude" / "settings.json"
    settings.parent.mkdir()
    settings.write_text(json.dumps({"extraKnownMarketplaces": {"c": {"source": {}}}}))

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        if argv[:4] == ["git", "-C", str(repo), "worktree"]:
            return _result(stdout=f"worktree {repo}\nHEAD abc\n")
        if argv[:6] == ["mise", "exec", "--", "claude", "plugin", "list"]:
            return _result(
                stdout=json.dumps(
                    [
                        {"id": "a-b@c", "scope": "user", "enabled": True},
                        {"id": "beta@c", "scope": "user", "enabled": True},
                    ]
                )
            )
        if argv[:6] == ["mise", "exec", "--", "codex", "plugin", "list"]:
            return _result(
                stdout=json.dumps(
                    {
                        "installed": [
                            {
                                "pluginId": "gamma@c",
                                "name": "gamma",
                                "marketplaceName": "c",
                                "installed": True,
                                "enabled": False,
                            }
                        ]
                    }
                )
            )
        if len(argv) > 3 and argv[3] == "grep":
            return _result(returncode=1)
        raise AssertionError(argv)

    monkeypatch.setattr(plugin_inventory.subprocess, "run", run)

    result = plugin_inventory.inventory("a-b@c", home=home, root=root)

    assert result.project_settings == (settings,)
    assert result.claude_marketplace_plugins == ("a-b@c", "beta@c")
    assert result.codex_marketplace_plugins == ("gamma@c",)
    assert result.dependent_plugins == ("beta@c",)
    assert result.auto_dependencies == ("dep@deps",)
    assert result.data_collisions == ("a@b-c",)


def test_live_references_uses_binary_exclusion_and_replacement_decode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        seen.append(argv)
        return SimpleNamespace(
            stdout=b"note.md\x004\x00\xffponytail\x0b\x0cpayload\n",
            stderr=b"",
            returncode=0,
        )

    monkeypatch.setattr(plugin_inventory.subprocess, "run", run)

    found = plugin_inventory.live_references(tmp_path, "ponytail")

    assert "-I" in seen[0]
    assert "-z" in seen[0]
    assert len(found) == 1
    assert found[0].text == "�ponytail\x0b\x0cpayload"
