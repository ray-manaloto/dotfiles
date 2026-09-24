# Copyright (c) 2026 Raymond Manaloto
"""Tests for dry plans and guarded plugin-removal mutations."""

from __future__ import annotations

import json
import tarfile
import tomllib
from types import SimpleNamespace
from typing import TYPE_CHECKING

from dotfiles_setup import plugin_remove
from dotfiles_setup.plugin_inventory import PluginInventory, RepoReference
from dotfiles_setup.plugin_remove import RemovalPlan, RemovalStep
from dotfiles_setup.plugin_state import PluginLocation

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_PLUGIN = "example-plugin@example-plugin"


def _result(
    *, stdout: str = "", stderr: str = "", returncode: int = 0
) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def _inventory(**changes: object) -> PluginInventory:
    values: dict[str, object] = {
        "plugin": _PLUGIN,
        "locations": (),
        "claude_cli": (),
        "codex_cli": (),
        "project_settings": (),
        "worktree_settings": (),
        "stale_worktrees": (),
        "references": (),
        "errors": (),
    }
    values.update(changes)
    return PluginInventory(**values)


def _repo(tmp_path: Path, *, watched: bool = True) -> Path:
    names = '["example-plugin"]' if watched else "[]"
    (tmp_path / "doctor.toml").write_text(f"[removed_plugins]\nnames = {names}\n")
    return tmp_path


def test_plan_never_schedules_a_worktree_mutation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    worktree_setting = tmp_path / "other-worktree" / ".claude" / "settings.json"
    inv = _inventory(
        worktree_settings=(worktree_setting,),
        stale_worktrees=(tmp_path / "gone",),
    )

    removal_plan = plugin_remove.plan(inv, repo_root=repo)

    assert removal_plan.steps == ()
    assert removal_plan.blockers == ()


def test_plan_leaves_reference_judgment_to_the_wrapper_skill(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    inv = _inventory(references=(RepoReference(repo, "rules.md", 7, "example-plugin"),))

    removal_plan = plugin_remove.plan(inv, repo_root=repo)

    assert removal_plan.steps == ()
    assert removal_plan.blockers == ()


def test_project_uninstall_preserves_the_original_formatting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "repo"
    settings = project / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    original = (
        "{\n"
        '  "enabledPlugins": {\n'
        '    "keep@keep": true,\n'
        f'    "{_PLUGIN}": true\n'
        "  },\n"
        '  "other": "spacing stays"\n'
        "}\n"
    )
    cli_result = {
        "enabledPlugins": {"keep@keep": True},
        "other": "spacing stays",
    }
    settings.write_text(original)

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del argv, kwargs
        settings.write_text(json.dumps(cli_result, indent=2) + "\n")
        return _result(stdout='progress\n{"outcome":"ok"}\n')

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)

    result = plugin_remove.uninstall_project_scope(_PLUGIN, project)

    assert result.rc == 0
    assert settings.read_text() == (
        "{\n"
        '  "enabledPlugins": {\n'
        '    "keep@keep": true\n'
        "  },\n"
        '  "other": "spacing stays"\n'
        "}\n"
    )


def test_minimal_diff_fails_on_semantic_cli_result_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "repo"
    settings = project / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(
        "{\n"
        '  "enabledPlugins": {\n'
        f'    "{_PLUGIN}": true\n'
        "  },\n"
        '  "untouched": true\n'
        "}\n"
    )
    cli_text = json.dumps({"enabledPlugins": {}, "untouched": False}, indent=2)

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del argv, kwargs
        settings.write_text(cli_text)
        return _result(stdout='{"outcome":"ok"}\n')

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)

    result = plugin_remove.uninstall_project_scope(_PLUGIN, project)

    assert result.rc == 1
    assert result.detail == "minimal settings differs from CLI result"
    assert settings.read_text() == cli_text


def test_apply_stops_at_the_first_failing_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    calls: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        calls.append(argv)
        return _result(returncode=9, stderr="first failed")

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)
    removal_plan = RemovalPlan(
        _PLUGIN,
        (
            RemovalStep("remove-codex-plugin", "codex plugin remove", _PLUGIN),
            RemovalStep(
                "remove-codex-marketplace",
                "codex plugin marketplace remove",
                "example-plugin",
            ),
        ),
        (),
    )

    results = plugin_remove.apply(removal_plan, home=tmp_path, repo_root=repo)

    assert [result.rc for result in results] == [9]
    assert calls == [["codex", "plugin", "remove", _PLUGIN]]


def test_remove_orphan_cache_refuses_without_a_prior_backup(tmp_path: Path) -> None:
    cache = tmp_path / ".claude" / "plugins" / "cache" / "example-plugin"
    cache.mkdir(parents=True)

    result = plugin_remove.remove_orphan_cache("example-plugin", home=tmp_path)

    assert result.rc == 1
    assert cache.is_dir()


def test_backup_then_cache_removal_is_allowed(tmp_path: Path) -> None:
    cache = tmp_path / ".claude" / "plugins" / "cache" / "example-plugin"
    cache.mkdir(parents=True)
    (cache / "payload.txt").write_text("cache")
    archive = tmp_path / "state" / "backup.tar.gz"

    backup = plugin_remove.backup_cache("example-plugin", home=tmp_path, dest=archive)
    removed = plugin_remove.remove_orphan_cache("example-plugin", home=tmp_path)

    assert backup.rc == 0
    assert removed.rc == 0
    assert not cache.exists()
    with tarfile.open(archive, "r:gz") as saved:
        assert any(member.name.endswith("payload.txt") for member in saved.getmembers())


def test_hook_trust_removes_selector_and_plugin_cache_path_tables(
    tmp_path: Path,
) -> None:
    config = tmp_path / ".codex" / "config.toml"
    cache_hook = (
        tmp_path
        / ".codex"
        / "plugins"
        / "cache"
        / "example-plugin"
        / "example-plugin"
        / "1.0"
        / "hooks.json"
    )
    config.parent.mkdir()
    config.write_text(
        f'[hooks.state."{_PLUGIN}:hooks/hooks.json:stop:0:0"]\n'
        'trusted_hash = "one"\n'
        f'[hooks.state."{cache_hook}"]\n'
        'trusted_hash = "two"\n'
        '[hooks.state."keep@keep:hooks/hooks.json:stop:0:0"]\n'
        'trusted_hash = "three"\n'
    )

    result = plugin_remove.remove_codex_hook_trust(_PLUGIN, home=tmp_path)

    assert result.rc == 0
    changed = config.read_text()
    assert _PLUGIN not in changed
    assert str(cache_hook) not in changed
    assert "keep@keep" in changed
    tomllib.loads(changed)


def test_add_to_watchlist_changes_only_the_names_array(tmp_path: Path) -> None:
    repo = _repo(tmp_path, watched=False)
    path = repo / "doctor.toml"
    before = path.read_text()

    result = plugin_remove.add_to_watchlist("example-plugin", repo_root=repo)

    assert result.rc == 0
    assert before.replace("[]", '["example-plugin"]') == path.read_text()
    assert tomllib.loads(path.read_text())["removed_plugins"]["names"] == [
        "example-plugin"
    ]


def test_plan_orders_backup_before_cache_removal(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    location = PluginLocation(
        "claude", "cache", "~/.claude/plugins/cache/example-plugin", "example-plugin"
    )

    removal_plan = plugin_remove.plan(_inventory(locations=(location,)), repo_root=repo)

    assert [step.name for step in removal_plan.steps] == [
        "backup-cache",
        "remove-orphan-cache",
    ]
