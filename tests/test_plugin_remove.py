# Copyright (c) 2026 Raymond Manaloto
"""Tests for dry plans and guarded plugin-removal mutations."""

from __future__ import annotations

import json
import tarfile
import tomllib
from dataclasses import replace
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
_EMPTY_INVENTORY = PluginInventory(
    plugin=_PLUGIN,
    locations=(),
    claude_cli=(),
    codex_cli=(),
    project_settings=(),
    worktree_settings=(),
    stale_worktrees=(),
    references=(),
    errors=(),
)


def _result(
    *, stdout: str = "", stderr: str = "", returncode: int = 0
) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def _inventory(**changes: object) -> PluginInventory:
    return replace(_EMPTY_INVENTORY, **changes)


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
    assert result.detail.endswith("changed beyond the requested key")
    assert settings.read_text().endswith('  "untouched": true\n}\n')


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
    assert calls == [["mise", "exec", "--", "codex", "plugin", "remove", _PLUGIN]]


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
    cache = PluginLocation(
        "claude",
        "cache",
        "/home/test/.claude/plugins/cache/market/alpha",
        "alpha@market",
        marketplace="market",
    )
    data = PluginLocation(
        "claude",
        "data",
        "/home/test/.claude/plugins/data/alpha-market",
        "alpha@market",
        marketplace="market",
    )

    removal_plan = plugin_remove.plan(
        _inventory(plugin="alpha@market", locations=(cache, data)), repo_root=repo
    )

    assert [step.name for step in removal_plan.steps] == [
        "backup-cache",
        "remove-orphan-cache",
        "add-to-watchlist",
    ]
    orphan = next(
        step for step in removal_plan.steps if step.name == "remove-orphan-cache"
    )
    assert orphan.target == (
        "/home/test/.claude/plugins/cache/market/alpha, "
        "/home/test/.claude/plugins/data/alpha-market"
    )


def test_plan_covers_user_project_and_local_entries(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    locations = (
        PluginLocation(
            "claude",
            "installed",
            "registry",
            "alpha@market",
            "",
            "market",
            "user",
        ),
        PluginLocation(
            "claude",
            "installed",
            "registry",
            "alpha@market",
            str(project),
            "market",
            "project",
        ),
        PluginLocation(
            "claude",
            "installed",
            "registry",
            "alpha@market",
            str(project),
            "market",
            "local",
        ),
    )

    removal_plan = plugin_remove.plan(
        _inventory(plugin="alpha@market", locations=locations), repo_root=repo
    )

    assert [step.name for step in removal_plan.steps] == [
        "uninstall-user-scope",
        "uninstall-project-scope",
        "uninstall-local-scope",
        "add-to-watchlist",
    ]


def test_plan_blocks_missing_project_path_and_dependencies_and_data_collision(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    location = PluginLocation(
        "claude",
        "installed",
        "registry",
        "alpha@market",
        str(tmp_path / "gone"),
        "market",
        "local",
    )

    removal_plan = plugin_remove.plan(
        _inventory(
            plugin="alpha@market",
            locations=(location,),
            dependent_plugins=("beta@market",),
            auto_dependencies=("dep@deps",),
            data_collisions=("alpha-market@other",),
        ),
        repo_root=repo,
    )

    assert any("projectPath is unusable" in item for item in removal_plan.blockers)
    assert any("beta@market" in item for item in removal_plan.blockers)
    assert any("alpha-market@other" in item for item in removal_plan.blockers)
    assert removal_plan.notes == ("auto-installed dependency kept: dep@deps",)


def test_plan_keeps_a_marketplace_with_siblings_and_names_them(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    known = PluginLocation(
        "claude",
        "known-marketplace",
        "known",
        "market",
        marketplace="market",
    )
    codex = PluginLocation(
        "codex",
        "codex-marketplace",
        "config",
        "market",
        marketplace="market",
    )

    removal_plan = plugin_remove.plan(
        _inventory(
            plugin="alpha@market",
            locations=(known, codex),
            claude_marketplace_plugins=("alpha@market", "beta@market"),
            codex_marketplace_plugins=("alpha@market", "gamma@market"),
        ),
        repo_root=repo,
    )

    assert not any("marketplace" in step.name for step in removal_plan.steps)
    assert "marketplace kept: still used by beta@market" in removal_plan.notes
    assert "codex marketplace kept: still used by gamma@market" in removal_plan.notes


def test_project_uninstall_removes_surviving_key_and_added_local_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "repo"
    settings = project / ".claude" / "settings.json"
    local = project / ".claude" / "settings.local.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(
        "{\n"
        '  "enabledPlugins": {\n'
        f'    "{_PLUGIN}": true,\n'
        '    "keep@keep": true\n'
        "  }\n"
        "}\n"
    )
    local.write_text('{\n  "other": true\n}\n')

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        assert argv[:4] == ["mise", "exec", "--", "claude"]
        assert "--keep-data" in argv
        local.write_text(
            json.dumps(
                {
                    "other": True,
                    "enabledPlugins": {_PLUGIN: False},
                },
                indent=2,
            )
        )
        return _result(stdout='{"outcome":"ok"}\n')

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)

    result = plugin_remove.uninstall_project_scope(_PLUGIN, project)

    assert result.rc == 0
    assert _PLUGIN not in settings.read_text()
    assert local.read_text() == '{\n  "other": true\n}\n'


def test_failed_backup_write_aborts_before_cli_and_keeps_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "repo"
    settings = project / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({"enabledPlugins": {_PLUGIN: True}}))
    original = settings.read_bytes()
    calls: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        calls.append(argv)
        return _result(stdout='{"outcome":"ok"}\n')

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)
    settings.parent.chmod(0o500)
    try:
        result = plugin_remove.uninstall_project_scope(_PLUGIN, project)
    finally:
        settings.parent.chmod(0o700)

    assert result.rc == 1
    assert "backup failed before edit" in result.detail
    assert calls == []
    assert settings.read_bytes() == original


def test_cache_backup_is_exact_manifested_and_requires_uninstall(
    tmp_path: Path,
) -> None:
    selector = "exa@exa"
    exact = tmp_path / ".codex" / "plugins" / "cache" / "exa" / "exa"
    other = (
        tmp_path / ".codex" / "plugins" / "cache" / "claude-plugins-official" / "exa"
    )
    exact.mkdir(parents=True)
    other.mkdir(parents=True)
    (exact / "payload.txt").write_text("exact")
    (other / "payload.txt").write_text("other")
    registry = tmp_path / ".claude" / "plugins" / "installed_plugins.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"plugins": {selector: [{"scope": "user"}]}}))
    archive = tmp_path / "state" / "backup.tar.gz"

    backup = plugin_remove.backup_cache(selector, home=tmp_path, dest=archive)
    refused = plugin_remove.remove_orphan_cache(selector, home=tmp_path)
    registry.write_text(json.dumps({"plugins": {}}))
    removed = plugin_remove.remove_orphan_cache(selector, home=tmp_path)

    assert backup.rc == 0
    assert refused.rc == 1
    assert "while plugin is installed" in refused.detail
    assert removed.rc == 0
    assert not exact.exists()
    assert other.is_dir()
    with tarfile.open(archive, "r:gz") as saved:
        names = saved.getnames()
        assert "plugin-removal-manifest.json" in names
        assert not any("claude-plugins-official" in name for name in names)


def test_cache_removal_refuses_a_freshly_malformed_registry(tmp_path: Path) -> None:
    selector = "alpha@market"
    cache = tmp_path / ".claude" / "plugins" / "cache" / "market" / "alpha"
    cache.mkdir(parents=True)
    (cache / "payload.txt").write_text("cache")
    archive = tmp_path / "state" / "backup.tar.gz"

    backup = plugin_remove.backup_cache(selector, home=tmp_path, dest=archive)
    registry = tmp_path / ".claude" / "plugins" / "installed_plugins.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps({"plugins": {selector: {"scope": "user"}}}))

    removed = plugin_remove.remove_orphan_cache(selector, home=tmp_path)

    assert backup.rc == 0
    assert removed.rc == 1
    assert "invalid shape" in removed.detail
    assert cache.is_dir()


def test_persistent_data_is_backed_up_before_it_is_removed(tmp_path: Path) -> None:
    selector = "alpha@market"
    data = tmp_path / ".claude" / "plugins" / "data" / "alpha-market"
    data.mkdir(parents=True)
    (data / "state.json").write_text('{"kept":"in archive"}')
    archive = tmp_path / "state" / "backup.tar.gz"

    backup = plugin_remove.backup_cache(selector, home=tmp_path, dest=archive)
    removed = plugin_remove.remove_orphan_cache(selector, home=tmp_path)

    assert backup.rc == 0
    assert removed.rc == 0
    assert not data.exists()
    with tarfile.open(archive, "r:gz") as saved:
        assert any(
            member.name.endswith(".claude/plugins/data/alpha-market/state.json")
            for member in saved.getmembers()
        )


def test_symlinked_cache_is_dereferenced_but_only_the_link_is_deleted(
    tmp_path: Path,
) -> None:
    selector = "alpha@market"
    external = tmp_path / "external"
    external.mkdir()
    (external / "payload.txt").write_text("linked content")
    cache = tmp_path / ".claude" / "plugins" / "cache" / "market" / "alpha"
    cache.parent.mkdir(parents=True)
    cache.symlink_to(external, target_is_directory=True)
    archive = tmp_path / "state" / "backup.tar.gz"

    backup = plugin_remove.backup_cache(selector, home=tmp_path, dest=archive)
    removed = plugin_remove.remove_orphan_cache(selector, home=tmp_path)

    assert backup.rc == 0
    assert removed.rc == 0
    assert not cache.is_symlink()
    assert (external / "payload.txt").read_text() == "linked content"
    with tarfile.open(archive, "r:gz") as saved:
        assert any(member.name.endswith("payload.txt") for member in saved.getmembers())


def test_hook_trust_handles_inline_and_subtable_forms(tmp_path: Path) -> None:
    variants = (
        (
            (
                "[hooks.state]\n"
                f'"{_PLUGIN}:hooks/a.json:stop:0:0" = {{ trusted = true }}\n'
            ),
            "inline",
        ),
        (
            (
                f'[hooks.state."{_PLUGIN}:hooks/a.json:stop:0:0".metadata]\n'
                "trusted = true\n"
            ),
            "subtable",
        ),
        (
            f'hooks.state."{_PLUGIN}:hooks/a.json:stop:0:0" = {{ trusted = true }}\n',
            "dotted",
        ),
    )
    for source, label in variants:
        home = tmp_path / label
        config = home / ".codex" / "config.toml"
        config.parent.mkdir(parents=True)
        config.write_text(source + '[hooks.state."keep@keep:x"]\ntrusted = true\n')

        result = plugin_remove.remove_codex_hook_trust(_PLUGIN, home=home)

        assert result.rc == 0, label
        parsed = tomllib.loads(config.read_text())
        assert list(parsed["hooks"]["state"]) == ["keep@keep:x"]


def test_hook_trust_refuses_an_unhandled_multiline_form_and_rolls_back(
    tmp_path: Path,
) -> None:
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir()
    original = (
        "[hooks.state]\n"
        f'"{_PLUGIN}:hooks/a.json:stop:0:0" = [\n'
        "  { trusted = true },\n"
        "]\n"
    )
    config.write_text(original)

    result = plugin_remove.remove_codex_hook_trust(_PLUGIN, home=tmp_path)

    assert result.rc == 1
    assert "rolled back" in result.detail
    assert config.read_text() == original


def test_failed_hook_backup_never_restores_a_stale_backup(tmp_path: Path) -> None:
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir()
    original = (
        'model = "current"\n'
        f'[hooks.state."{_PLUGIN}:hooks/a.json:stop:0:0"]\n'
        "trusted = true\n"
    )
    config.write_text(original)
    stale = config.with_name("config.toml.plugin-remove.bak")
    stale.write_text('model = "stale"\n')
    stale.chmod(0o444)
    config.parent.chmod(0o500)
    try:
        result = plugin_remove.remove_codex_hook_trust(_PLUGIN, home=tmp_path)
    finally:
        config.parent.chmod(0o700)
        stale.chmod(0o600)

    assert result.rc == 1
    assert "backup failed" in result.detail
    assert config.read_text() == original


def test_watchlist_multiline_comment_cannot_hide_a_false_success(
    tmp_path: Path,
) -> None:
    path = tmp_path / "doctor.toml"
    path.write_text(
        "[removed_plugins]\n"
        "names = [\n"
        '  "ponytail", # historical ] bracket\n'
        '  "claudex-loop",\n'
        "]\n"
    )

    result = plugin_remove.add_to_watchlist("alpha", repo_root=tmp_path)

    assert result.rc == 0
    assert "alpha" in tomllib.loads(path.read_text())["removed_plugins"]["names"]


def test_dry_run_with_a_blocker_exits_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    home = tmp_path / "home"
    repo = tmp_path / "repo"
    home.mkdir()
    repo.mkdir()
    (repo / "doctor.toml").write_text("[removed_plugins\n")

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        if argv[:4] == ["mise", "exec", "--", "claude"]:
            return _result(stdout="[]")
        if argv[:4] == ["mise", "exec", "--", "codex"]:
            return _result(stdout=json.dumps({"installed": []}))
        raise AssertionError(argv)

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo)

    rc = plugin_remove.plugin_remove_main(["alpha@market"])

    assert rc == 1
    assert "blockers: 1" in capsys.readouterr().out


def test_apply_refuses_marketplace_removal_while_target_is_still_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    registry = tmp_path / ".claude" / "plugins" / "installed_plugins.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({"plugins": {"alpha@market": [{"scope": "user"}]}}))
    calls: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        calls.append(argv)
        if argv[:6] == ["mise", "exec", "--", "claude", "plugin", "list"]:
            return _result(
                stdout=json.dumps(
                    [{"id": "alpha@market", "scope": "user", "enabled": True}]
                )
            )
        if argv[:6] == ["mise", "exec", "--", "codex", "plugin", "list"]:
            return _result(stdout=json.dumps({"installed": []}))
        raise AssertionError(argv)

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)
    removal_plan = RemovalPlan(
        "alpha@market",
        (
            RemovalStep(
                "remove-claude-marketplace",
                "claude plugin marketplace remove market",
                "market",
            ),
        ),
        (),
    )

    results = plugin_remove.apply(removal_plan, home=tmp_path, repo_root=repo)

    assert len(results) == 1
    assert results[0].rc == 1
    assert "alpha@market" in results[0].detail
    assert not any("marketplace" in argv for argv in calls)
