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
        if argv[:3] == ["claude", "plugin", "list"]:
            return _result(stdout="[]")
        if argv[:3] == ["codex", "plugin", "list"]:
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
    assert error == "claude plugin list --json exited 7: claude failed"
