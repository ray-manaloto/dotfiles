# Copyright (c) 2026 Raymond Manaloto
"""Tests for dry plans and guarded plugin-removal mutations.

Every fixture keeps the plugin and marketplace halves DIFFERENT (``alpha@market``)
so a path joined on the wrong half cannot pass by coincidence, and every
mutation runs against a ``tmp_path`` home and repo root, never the real ones.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import tarfile
import tomllib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from dotfiles_setup import plugin_remove
from dotfiles_setup.plugin_inventory import PluginInventory, RepoReference
from dotfiles_setup.plugin_remove import RemovalPlan, RemovalStep
from dotfiles_setup.plugin_state import PluginLocation

_PLUGIN = "alpha@market"
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


@pytest.fixture(autouse=True)
def _isolated_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No test may reach the real home or write backups into the real repo."""
    fake_home = tmp_path / "unused-home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.chdir(tmp_path)


def _result(
    *, stdout: str = "", stderr: str = "", returncode: int = 0
) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def _inventory(**changes: object) -> PluginInventory:
    return replace(_EMPTY_INVENTORY, **changes)


def _repo(tmp_path: Path, *, watched: bool = True) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    names = '["alpha"]' if watched else "[]"
    (repo / "doctor.toml").write_text(f"[removed_plugins]\nnames = {names}\n")
    return repo


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _registry(home: Path, plugins: dict[str, object]) -> Path:
    return _write(
        home / ".claude" / "plugins" / "installed_plugins.json",
        json.dumps({"version": 2, "plugins": plugins}, indent=2),
    )


def _backups(repo: Path) -> list[Path]:
    root = repo / ".agent" / "state" / "plugin-remove"
    return sorted(path for path in root.rglob("*") if path.is_file())


# ---------------------------------------------------------------------------
# Planning.
# ---------------------------------------------------------------------------


def test_plan_never_schedules_a_worktree_mutation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    worktree_setting = tmp_path / "other-worktree" / ".claude" / "settings.json"
    inv = _inventory(
        worktree_settings=(worktree_setting,),
        stale_worktrees=(tmp_path / "gone",),
    )

    removal_plan = plugin_remove.plan(inv, repo_root=repo, home=tmp_path)

    assert removal_plan.steps == ()
    assert removal_plan.blockers == ()


def test_plan_leaves_reference_judgment_to_the_wrapper_skill(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    inv = _inventory(references=(RepoReference(repo, "rules.md", 7, "alpha"),))

    removal_plan = plugin_remove.plan(inv, repo_root=repo, home=tmp_path)

    assert removal_plan.steps == ()
    assert removal_plan.blockers == ()


@pytest.mark.parametrize("selector", ["honcho@", "@honcho", "a@b@c", "../x@y"])
def test_plan_rejects_a_malformed_selector_before_building_a_path(
    tmp_path: Path, selector: str
) -> None:
    with pytest.raises(ValueError, match="exactly <plugin>@<marketplace>"):
        plugin_remove.plan(
            _inventory(plugin=selector), repo_root=_repo(tmp_path), home=tmp_path
        )


def test_plugin_remove_main_exits_two_on_an_empty_selector_half(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        calls.append(argv)
        return _result()

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)

    with pytest.raises(SystemExit) as exited:
        plugin_remove.plugin_remove_main(["honcho@"])

    assert exited.value.code == 2
    assert "exactly <plugin>@<marketplace>" in capsys.readouterr().err
    assert calls == []


def test_plan_orders_backup_before_cache_removal(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    home = tmp_path / "home"
    cache_path = home / ".claude" / "plugins" / "cache" / "market" / "alpha"
    data_path = home / ".claude" / "plugins" / "data" / "alpha-market"
    cache = PluginLocation(
        "claude", "cache", str(cache_path), _PLUGIN, marketplace="market"
    )
    data = PluginLocation(
        "claude", "data", str(data_path), _PLUGIN, marketplace="market"
    )

    removal_plan = plugin_remove.plan(
        _inventory(locations=(cache, data)), repo_root=repo, home=home
    )

    assert [step.name for step in removal_plan.steps] == [
        "backup-cache",
        "remove-orphan-cache",
    ]
    assert removal_plan.blockers == ()
    orphan = removal_plan.steps[-1]
    assert orphan.target == f"{cache_path}, {data_path}"
    archive = Path(removal_plan.steps[0].target)
    assert archive.parent.parent == repo / ".agent" / "state" / "plugin-remove"


def test_plan_blocks_a_removal_target_outside_the_plugin_roots(tmp_path: Path) -> None:
    home = tmp_path / "home"
    marketplace_dir = home / ".claude" / "plugins" / "cache" / "market"
    escaped = PluginLocation(
        "claude", "cache", str(marketplace_dir), _PLUGIN, marketplace="market"
    )

    removal_plan = plugin_remove.plan(
        _inventory(locations=(escaped,)), repo_root=_repo(tmp_path), home=home
    )

    assert removal_plan.blockers == (
        f"removal target escapes the plugin's cache/data roots: {marketplace_dir}",
    )


def test_plan_covers_user_project_and_local_entries(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    locations = (
        PluginLocation(
            "claude", "installed", "registry", _PLUGIN, "", "market", "user"
        ),
        PluginLocation(
            "claude",
            "installed",
            "registry",
            _PLUGIN,
            str(project),
            "market",
            "project",
        ),
        PluginLocation(
            "claude", "installed", "registry", _PLUGIN, str(project), "market", "local"
        ),
    )

    removal_plan = plugin_remove.plan(
        _inventory(locations=locations), repo_root=repo, home=tmp_path
    )

    assert [step.name for step in removal_plan.steps] == [
        "uninstall-user-scope",
        "uninstall-project-scope",
        "uninstall-local-scope",
    ]


def test_plan_blocks_missing_project_path_and_dependencies_and_data_collision(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    location = PluginLocation(
        "claude",
        "installed",
        "registry",
        _PLUGIN,
        str(tmp_path / "gone"),
        "market",
        "local",
    )

    removal_plan = plugin_remove.plan(
        _inventory(
            locations=(location,),
            dependent_plugins=("beta@market", "gamma@other"),
            enabled_dependents=("gamma@other",),
            auto_dependencies=("dep@deps",),
            data_collisions=("alpha-market@other",),
        ),
        repo_root=repo,
        home=tmp_path,
    )

    assert any("projectPath is unusable" in item for item in removal_plan.blockers)
    assert (
        "installed plugin depends on target: beta@market (installed but enabled "
        "nowhere; re-enabling it would break)"
    ) in removal_plan.blockers
    assert (
        "installed plugin depends on target: gamma@other "
        "(enabled in at least one scope)"
    ) in removal_plan.blockers
    assert any("alpha-market@other" in item for item in removal_plan.blockers)
    assert removal_plan.notes == ("auto-installed dependency kept: dep@deps",)


def test_plan_keeps_a_marketplace_with_siblings_and_names_them(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    known = PluginLocation(
        "claude", "known-marketplace", "known", "market", marketplace="market"
    )
    codex = PluginLocation(
        "codex", "codex-marketplace", "config", "market", marketplace="market"
    )

    removal_plan = plugin_remove.plan(
        _inventory(
            locations=(known, codex),
            claude_marketplace_plugins=(_PLUGIN, "beta@market"),
            codex_marketplace_plugins=(_PLUGIN, "gamma@market"),
        ),
        repo_root=repo,
        home=tmp_path,
    )

    assert not any("marketplace" in step.name for step in removal_plan.steps)
    assert "marketplace kept: still used by beta@market" in removal_plan.notes
    assert "codex marketplace kept: still used by gamma@market" in removal_plan.notes


def test_plan_removes_an_enabled_key_that_has_no_install_record(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    project_settings = project / ".claude" / "settings.json"
    installed_elsewhere = tmp_path / "installed-project"
    enabled = PluginLocation(
        "claude", "enabled", "~/.claude/settings.json", _PLUGIN, marketplace="market"
    )
    installed = PluginLocation(
        "claude",
        "installed",
        "registry",
        _PLUGIN,
        str(installed_elsewhere),
        "market",
        "project",
    )
    installed_elsewhere.mkdir()

    removal_plan = plugin_remove.plan(
        _inventory(
            locations=(enabled, installed),
            enabling_settings=(
                project_settings,
                installed_elsewhere / ".claude" / "settings.json",
            ),
        ),
        repo_root=_repo(tmp_path),
        home=home,
    )

    assert [(step.name, step.target) for step in removal_plan.steps] == [
        ("uninstall-project-scope", str(installed_elsewhere)),
        ("remove-settings-key", str(home / ".claude" / "settings.json")),
        ("remove-settings-key", str(project_settings)),
    ]


def test_plan_removes_a_codex_config_plugin_the_cli_does_not_list(
    tmp_path: Path,
) -> None:
    configured = PluginLocation(
        "codex",
        "codex-plugin",
        "~/.codex/config.toml",
        _PLUGIN,
        "enabled=true",
        "market",
    )

    removal_plan = plugin_remove.plan(
        _inventory(locations=(configured,)), repo_root=_repo(tmp_path), home=tmp_path
    )

    assert [step.name for step in removal_plan.steps] == ["remove-codex-config-plugin"]


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

    rc = plugin_remove.plugin_remove_main([_PLUGIN])

    assert rc == 1
    assert "blockers: 1" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Uninstall and settings goal state.
# ---------------------------------------------------------------------------


def test_project_uninstall_preserves_the_original_formatting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    project = tmp_path / "project"
    settings = _write(
        project / ".claude" / "settings.json",
        "{\n"
        '  "enabledPlugins": {\n'
        '    "keep@keep": true,\n'
        f'    "{_PLUGIN}": true\n'
        "  },\n"
        '  "other": "spacing stays"\n'
        "}\n",
    )
    cli_result = {"enabledPlugins": {"keep@keep": True}, "other": "spacing stays"}

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del argv, kwargs
        settings.write_text(json.dumps(cli_result, indent=4) + "\n")
        return _result(stdout='progress\n{"outcome":"ok"}\n')

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)

    result = plugin_remove.uninstall_project_scope(
        _PLUGIN, project, home=home, repo_root=_repo(tmp_path)
    )

    assert result.rc == 0, result.detail
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
    project = tmp_path / "project"
    settings = _write(
        project / ".claude" / "settings.json",
        "{\n"
        '  "enabledPlugins": {\n'
        f'    "{_PLUGIN}": true\n'
        "  },\n"
        '  "untouched": true\n'
        "}\n",
    )
    cli_text = json.dumps({"enabledPlugins": {}, "untouched": False}, indent=2)

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del argv, kwargs
        settings.write_text(cli_text)
        return _result(stdout='{"outcome":"ok"}\n')

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)

    result = plugin_remove.uninstall_project_scope(
        _PLUGIN, project, home=tmp_path / "home", repo_root=_repo(tmp_path)
    )

    assert result.rc == 1
    assert result.detail.endswith("changed beyond the requested key")
    assert settings.read_text().endswith('  "untouched": true\n}\n')


def test_project_uninstall_removes_surviving_key_and_added_local_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    settings = _write(
        project / ".claude" / "settings.json",
        "{\n"
        '  "enabledPlugins": {\n'
        f'    "{_PLUGIN}": true,\n'
        '    "keep@keep": true\n'
        "  }\n"
        "}\n",
    )
    local = _write(
        project / ".claude" / "settings.local.json", '{\n  "other": true\n}\n'
    )

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        assert argv[:4] == ["mise", "exec", "--", "claude"]
        assert "--keep-data" in argv
        local.write_text(
            json.dumps({"other": True, "enabledPlugins": {_PLUGIN: False}}, indent=2)
        )
        return _result(stdout='{"outcome":"ok"}\n')

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)

    result = plugin_remove.uninstall_project_scope(
        _PLUGIN, project, home=tmp_path / "home", repo_root=_repo(tmp_path)
    )

    assert result.rc == 0, result.detail
    assert settings.read_text() == (
        '{\n  "enabledPlugins": {\n    "keep@keep": true\n  }\n}\n'
    )
    assert local.read_text() == '{\n  "other": true\n}\n'


def test_uninstall_post_condition_reads_the_real_home_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N5: a project has no registry, so the check must read the home's one."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    _write(project / ".claude" / "settings.json", "{}\n")
    registry = _registry(
        home, {_PLUGIN: [{"scope": "project", "projectPath": str(project)}]}
    )
    before = registry.read_bytes()

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del argv, kwargs
        return _result(stdout='{"outcome":"ok"}\n')

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)

    result = plugin_remove.uninstall_project_scope(
        _PLUGIN, project, home=home, repo_root=_repo(tmp_path)
    )

    assert result.rc == 1
    assert "installed scope survived uninstall" in result.detail
    assert registry.read_bytes() == before


def test_user_uninstall_post_condition_fails_when_the_registry_keeps_the_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    repo = _repo(tmp_path)
    _registry(home, {_PLUGIN: [{"scope": "user"}]})

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del argv, kwargs
        return _result(stdout='{"outcome":"ok"}\n')

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)
    step = RemovalStep("uninstall-user-scope", "claude plugin uninstall", "user")

    results = plugin_remove.apply(
        RemovalPlan(_PLUGIN, (step,), ()), home=home, repo_root=repo
    )

    assert [result.rc for result in results] == [1]
    assert "installed scope survived uninstall" in results[0].detail


def test_failed_backup_write_aborts_before_cli_and_keeps_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "project"
    settings = _write(
        project / ".claude" / "settings.json",
        json.dumps({"enabledPlugins": {_PLUGIN: True}}),
    )
    original = settings.read_bytes()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".agent").write_text("a file where the backup directory must go")
    calls: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        calls.append(argv)
        return _result(stdout='{"outcome":"ok"}\n')

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)

    result = plugin_remove.uninstall_project_scope(
        _PLUGIN, project, home=tmp_path / "home", repo_root=repo
    )

    assert result.rc == 1
    assert "backup failed before edit" in result.detail
    assert calls == []
    assert settings.read_bytes() == original


def test_backups_land_under_agent_state_never_beside_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N3: a backup beside a gitignored file is itself an un-ignored copy."""
    project = tmp_path / "project"
    original = '{\n  "enabledPlugins": {\n    "alpha@market": true\n  }\n}\n'
    local = _write(project / ".claude" / "settings.local.json", original)
    repo = _repo(tmp_path)

    monkeypatch.setattr(
        plugin_remove.subprocess,
        "run",
        lambda *_args, **_kwargs: _result(stdout='{"outcome":"ok"}\n'),
    )
    result = plugin_remove.uninstall_project_scope(
        _PLUGIN, project, home=tmp_path / "home", repo_root=repo
    )

    assert result.rc == 0, result.detail
    assert sorted(path.name for path in local.parent.iterdir()) == [
        "settings.local.json"
    ]
    mirrored = [path for path in _backups(repo) if path.name == "settings.local.json"]
    assert len(mirrored) == 1
    assert mirrored[0].read_text() == original
    assert str(local.absolute()).lstrip("/") in str(mirrored[0])


def test_settings_edit_preserves_mode_bits(tmp_path: Path) -> None:
    """N7: mkstemp's 0600 must not leak onto an edited 0644 file."""
    settings = _write(
        tmp_path / "p" / ".claude" / "settings.json",
        '{\n  "enabledPlugins": {\n    "alpha@market": true\n  }\n}\n',
    )
    settings.chmod(0o644)

    result = plugin_remove.remove_settings_key(
        _PLUGIN, settings, backup_root=tmp_path / "backups"
    )

    assert result.rc == 0, result.detail
    assert stat.S_IMODE(settings.stat().st_mode) == 0o644
    assert settings.read_text() == '{\n  "enabledPlugins": {}\n}\n'


def test_settings_edit_keeps_a_symlinked_file_a_link(tmp_path: Path) -> None:
    real = _write(
        tmp_path / "dotfiles" / "settings.json",
        (
            '{\n  "enabledPlugins": {\n    "alpha@market": true,\n'
            '    "k@k": true\n  }\n}\n'
        ),
    )
    link = tmp_path / "p" / ".claude" / "settings.json"
    link.parent.mkdir(parents=True)
    link.symlink_to(real)

    result = plugin_remove.remove_settings_key(
        _PLUGIN, link, backup_root=tmp_path / "backups"
    )

    assert result.rc == 0, result.detail
    assert link.is_symlink()
    assert link.resolve() == real.resolve()
    assert real.read_text() == '{\n  "enabledPlugins": {\n    "k@k": true\n  }\n}\n'


def test_a_crash_before_the_new_bytes_are_durable_leaves_the_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Row 20: the new content is staged aside, so dying mid-write loses nothing."""
    original = '{\n  "enabledPlugins": {\n    "alpha@market": true\n  }\n}\n'
    settings = _write(tmp_path / "p" / ".claude" / "settings.json", original)
    new_size = len('{\n  "enabledPlugins": {}\n}\n')
    real_fsync = os.fsync

    def crash_when_new_content_is_complete(descriptor: int) -> None:
        if os.fstat(descriptor).st_size == new_size:
            raise KeyboardInterrupt
        real_fsync(descriptor)

    monkeypatch.setattr(plugin_remove.os, "fsync", crash_when_new_content_is_complete)

    with pytest.raises(KeyboardInterrupt):
        plugin_remove.remove_settings_key(
            _PLUGIN, settings, backup_root=tmp_path / "backups"
        )

    assert settings.read_text() == original
    assert sorted(path.name for path in settings.parent.iterdir()) == ["settings.json"]


# ---------------------------------------------------------------------------
# Cache and data backup / removal.
# ---------------------------------------------------------------------------


def test_remove_orphan_cache_refuses_without_a_prior_backup(tmp_path: Path) -> None:
    cache = tmp_path / ".claude" / "plugins" / "cache" / "market" / "alpha"
    cache.mkdir(parents=True)

    result = plugin_remove.remove_orphan_cache(_PLUGIN, home=tmp_path)

    assert result.rc == 1
    assert cache.is_dir()


def test_backup_then_cache_removal_is_allowed(tmp_path: Path) -> None:
    cache = tmp_path / ".claude" / "plugins" / "cache" / "market" / "alpha"
    sibling = tmp_path / ".claude" / "plugins" / "cache" / "market" / "beta"
    _write(cache / "1.0.0" / "payload.txt", "cache")
    _write(sibling / "1.0.0" / "payload.txt", "sibling")
    archive = tmp_path / "state" / "backup.tar.gz"

    backup = plugin_remove.backup_cache(_PLUGIN, home=tmp_path, dest=archive)
    removed = plugin_remove.remove_orphan_cache(_PLUGIN, home=tmp_path)

    assert backup.rc == 0
    assert removed.rc == 0
    assert not cache.exists()
    assert (sibling / "1.0.0" / "payload.txt").read_text() == "sibling"
    with tarfile.open(archive, "r:gz") as saved:
        assert any(member.name.endswith("payload.txt") for member in saved.getmembers())
    assert stat.S_IMODE(archive.stat().st_mode) == 0o600


def test_cache_backup_is_exact_manifested_and_requires_uninstall(
    tmp_path: Path,
) -> None:
    selector = "exa@exa"
    exact = tmp_path / ".codex" / "plugins" / "cache" / "exa" / "exa"
    other = (
        tmp_path / ".codex" / "plugins" / "cache" / "claude-plugins-official" / "exa"
    )
    _write(exact / "payload.txt", "exact")
    _write(other / "payload.txt", "other")
    registry = _registry(tmp_path, {selector: [{"scope": "user"}]})
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


def test_backup_refuses_a_registry_install_path_outside_the_plugin_root(
    tmp_path: Path,
) -> None:
    plugins = tmp_path / ".claude" / "plugins"
    sibling_version = plugins / "cache" / "market" / "beta" / "1.0.0"
    _write(sibling_version / "payload.txt", "sibling")
    _registry(
        tmp_path, {_PLUGIN: [{"scope": "user", "installPath": str(sibling_version)}]}
    )

    backup = plugin_remove.backup_cache(
        _PLUGIN, home=tmp_path, dest=tmp_path / "state" / "b.tar.gz"
    )

    assert backup.rc == 1
    assert "escapes the plugin's roots" in backup.detail
    assert (sibling_version / "payload.txt").read_text() == "sibling"


def test_removal_rechecks_containment_immediately_before_delete(
    tmp_path: Path,
) -> None:
    """TOCTOU: a marketplace dir swapped for a link after backup is refused."""
    cache_root = tmp_path / ".claude" / "plugins" / "cache"
    _write(cache_root / "market" / "alpha" / "payload.txt", "cache")
    backup = plugin_remove.backup_cache(
        _PLUGIN, home=tmp_path, dest=tmp_path / "state" / "b.tar.gz"
    )
    external = tmp_path / "external"
    _write(external / "alpha" / "keep.txt", "not plugin cache")
    (cache_root / "market").rename(tmp_path / "moved-market")
    (cache_root / "market").symlink_to(external, target_is_directory=True)

    removed = plugin_remove.remove_orphan_cache(_PLUGIN, home=tmp_path)

    assert backup.rc == 0
    assert removed.rc == 1
    assert "escaped the plugin's roots before delete" in removed.detail
    assert (external / "alpha" / "keep.txt").read_text() == "not plugin cache"


def test_removal_deletes_only_the_backed_up_set(tmp_path: Path) -> None:
    """Row 18: a path that appears after the backup was never archived."""
    plugins = tmp_path / ".claude" / "plugins"
    cache = _write(plugins / "cache" / "market" / "alpha" / "payload.txt", "cache")
    backup = plugin_remove.backup_cache(
        _PLUGIN, home=tmp_path, dest=tmp_path / "state" / "b.tar.gz"
    )
    late_data = _write(plugins / "data" / "alpha-market" / "late.json", "{}")

    removed = plugin_remove.remove_orphan_cache(_PLUGIN, home=tmp_path)

    assert backup.rc == 0
    assert removed.rc == 0
    assert not cache.exists()
    assert late_data.read_text() == "{}"


def test_cache_removal_refuses_a_freshly_malformed_registry(tmp_path: Path) -> None:
    cache = _write(
        tmp_path / ".claude" / "plugins" / "cache" / "market" / "alpha" / "p.txt",
        "cache",
    )
    backup = plugin_remove.backup_cache(
        _PLUGIN, home=tmp_path, dest=tmp_path / "state" / "backup.tar.gz"
    )
    _registry(tmp_path, {_PLUGIN: {"scope": "user"}})

    removed = plugin_remove.remove_orphan_cache(_PLUGIN, home=tmp_path)

    assert backup.rc == 0
    assert removed.rc == 1
    assert "invalid shape" in removed.detail
    assert cache.exists()


def test_persistent_data_is_backed_up_before_it_is_removed(tmp_path: Path) -> None:
    data = tmp_path / ".claude" / "plugins" / "data" / "alpha-market"
    _write(data / "state.json", '{"kept":"in archive"}')
    archive = tmp_path / "state" / "backup.tar.gz"

    backup = plugin_remove.backup_cache(_PLUGIN, home=tmp_path, dest=archive)
    removed = plugin_remove.remove_orphan_cache(_PLUGIN, home=tmp_path)

    assert backup.rc == 0
    assert removed.rc == 0
    assert not data.exists()
    with tarfile.open(archive, "r:gz") as saved:
        assert any(
            member.name.endswith(".claude/plugins/data/alpha-market/state.json")
            for member in saved.getmembers()
        )


def test_symlinked_cache_is_archived_as_a_link_and_only_the_link_is_deleted(
    tmp_path: Path,
) -> None:
    external = tmp_path / "external"
    _write(external / "payload.txt", "linked content")
    cache = tmp_path / ".claude" / "plugins" / "cache" / "market" / "alpha"
    cache.parent.mkdir(parents=True)
    cache.symlink_to(external, target_is_directory=True)
    archive = tmp_path / "state" / "backup.tar.gz"

    backup = plugin_remove.backup_cache(_PLUGIN, home=tmp_path, dest=archive)
    removed = plugin_remove.remove_orphan_cache(_PLUGIN, home=tmp_path)

    assert backup.rc == 0
    assert removed.rc == 0
    assert not cache.is_symlink()
    assert (external / "payload.txt").read_text() == "linked content"
    with tarfile.open(archive, "r:gz") as saved:
        link = saved.getmember(".claude/plugins/cache/market/alpha")
        assert link.issym()
        assert link.linkname == str(external)
        assert not any(name.endswith("payload.txt") for name in saved.getnames())
        manifest_file = saved.extractfile("plugin-removal-manifest.json")
        assert manifest_file is not None
        manifest = json.loads(manifest_file.read())
    assert manifest["paths"][0]["symlinkTarget"] == str(external)


# ---------------------------------------------------------------------------
# codex config text edits.
# ---------------------------------------------------------------------------


def test_hook_trust_removes_selector_and_plugin_cache_path_tables(
    tmp_path: Path,
) -> None:
    config = tmp_path / ".codex" / "config.toml"
    cache_hook = (
        tmp_path / ".codex" / "plugins" / "cache" / "market" / "alpha" / "1.0"
    ) / "hooks.json"
    _write(
        config,
        f'[hooks.state."{_PLUGIN}:hooks/hooks.json:stop:0:0"]\n'
        'trusted_hash = "one"\n'
        f'[hooks.state."{cache_hook}"]\n'
        'trusted_hash = "two"\n'
        '[hooks.state."keep@keep:hooks/hooks.json:stop:0:0"]\n'
        'trusted_hash = "three"\n',
    )

    result = plugin_remove.remove_codex_hook_trust(
        _PLUGIN, home=tmp_path, repo_root=_repo(tmp_path)
    )

    assert result.rc == 0
    changed = config.read_text()
    assert _PLUGIN not in changed
    assert str(cache_hook) not in changed
    assert "keep@keep" in changed
    tomllib.loads(changed)


def test_hook_trust_handles_inline_and_subtable_forms(tmp_path: Path) -> None:
    key = f'"{_PLUGIN}:hooks/a.json:stop:0:0"'
    variants = (
        (f"[hooks.state]\n{key} = {{ trusted = true }}\n", "inline"),
        (f"[hooks.state.{key}.metadata]\ntrusted = true\n", "subtable"),
        (f"hooks.state.{key} = {{ trusted = true }}\n", "dotted"),
        (f"[hooks]\nstate.{key} = {{ trusted = true }}\n", "hooks-table-dotted"),
    )
    for source, label in variants:
        home = tmp_path / label
        config = _write(
            home / ".codex" / "config.toml",
            source + '[hooks.state."keep@keep:x"]\ntrusted = true\n',
        )

        result = plugin_remove.remove_codex_hook_trust(
            _PLUGIN, home=home, repo_root=_repo(tmp_path)
        )

        assert result.rc == 0, (label, result.detail)
        parsed = tomllib.loads(config.read_text())
        assert list(parsed["hooks"]["state"]) == ["keep@keep:x"], label


def test_hook_trust_refuses_an_unhandled_multiline_form_and_rolls_back(
    tmp_path: Path,
) -> None:
    original = (
        "[hooks.state]\n"
        f'"{_PLUGIN}:hooks/a.json:stop:0:0" = [\n'
        "  { trusted = true },\n"
        "]\n"
    )
    config = _write(tmp_path / ".codex" / "config.toml", original)

    result = plugin_remove.remove_codex_hook_trust(
        _PLUGIN, home=tmp_path, repo_root=_repo(tmp_path)
    )

    assert result.rc == 1
    assert "rolled back" in result.detail
    assert config.read_text() == original


def test_hook_trust_post_condition_catches_a_form_the_editor_leaves_behind(
    tmp_path: Path,
) -> None:
    """Row 17: a valid-TOML edit that leaves trust behind must not report success."""
    original = (
        f'[hooks.state."{_PLUGIN}:hooks/a.json:stop:0:0"]\n'
        "trusted = true\n"
        "[hooks.state]\n"
        f'"{_PLUGIN}:hooks/b#c.json:stop:0:0" = {{ trusted = true }}\n'
    )
    config = _write(tmp_path / ".codex" / "config.toml", original)

    result = plugin_remove.remove_codex_hook_trust(
        _PLUGIN, home=tmp_path, repo_root=_repo(tmp_path)
    )

    assert result.rc == 1
    assert "matching entries remain" in result.detail
    assert config.read_text() == original


def test_hook_trust_that_no_line_matches_is_a_failure_not_success(
    tmp_path: Path,
) -> None:
    original = f'hooks = {{ state = {{ "{_PLUGIN}:x" = {{ trusted = true }} }} }}\n'
    config = _write(tmp_path / ".codex" / "config.toml", original)

    result = plugin_remove.remove_codex_hook_trust(
        _PLUGIN, home=tmp_path, repo_root=_repo(tmp_path)
    )

    assert result.rc == 1
    assert "cannot remove" in result.detail
    assert config.read_text() == original


def test_failed_hook_backup_aborts_before_any_edit(tmp_path: Path) -> None:
    original = (
        'model = "current"\n'
        f'[hooks.state."{_PLUGIN}:hooks/a.json:stop:0:0"]\n'
        "trusted = true\n"
    )
    config = _write(tmp_path / ".codex" / "config.toml", original)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".agent").write_text("blocks the backup directory")

    result = plugin_remove.remove_codex_hook_trust(
        _PLUGIN, home=tmp_path, repo_root=repo
    )

    assert result.rc == 1
    assert "backup failed" in result.detail
    assert config.read_text() == original


def test_codex_config_plugin_table_is_removed_by_text_edit(tmp_path: Path) -> None:
    config = _write(
        tmp_path / ".codex" / "config.toml",
        'model = "m"\n'
        f'[plugins."{_PLUGIN}"]\n'
        "enabled = true\n"
        '[plugins."keep@keep"]\n'
        "enabled = true\n",
    )
    step = RemovalStep("remove-codex-config-plugin", "text edit", _PLUGIN)

    results = plugin_remove.apply(
        RemovalPlan(_PLUGIN, (step,), ()), home=tmp_path, repo_root=_repo(tmp_path)
    )

    assert [result.rc for result in results] == [0]
    assert config.read_text() == 'model = "m"\n[plugins."keep@keep"]\nenabled = true\n'


# ---------------------------------------------------------------------------
# doctor.toml watchlist.
# ---------------------------------------------------------------------------


def test_add_to_watchlist_changes_only_the_names_array(tmp_path: Path) -> None:
    repo = _repo(tmp_path, watched=False)
    path = repo / "doctor.toml"
    before = path.read_text()

    result = plugin_remove.add_to_watchlist("alpha", repo_root=repo)

    assert result.rc == 0
    assert before.replace("[]", '["alpha"]') == path.read_text()


def test_watchlist_insert_keeps_comments_and_layout(tmp_path: Path) -> None:
    """N6: the tracked doctor.toml keeps its provenance comments."""
    shapes = (
        (
            (
                "names = [\n"
                '  "ponytail",  # removed in [#1363]\n'
                '  "claudex-loop",  # disabled, see #1310\n'
                "]\n"
            ),
            (
                "names = [\n"
                '  "ponytail",  # removed in [#1363]\n'
                '  "claudex-loop",  # disabled, see #1310\n'
                '  "alpha",\n'
                "]\n"
            ),
        ),
        (
            'names = [\n    "ponytail"  # no trailing comma\n]\n',
            'names = [\n    "ponytail",  # no trailing comma\n    "alpha"\n]\n',
        ),
        (
            'names = ["ponytail", "claudex-loop"]\n',
            'names = ["ponytail", "claudex-loop", "alpha"]\n',
        ),
    )
    for index, (array, expected) in enumerate(shapes):
        repo = tmp_path / f"repo{index}"
        header = "# watched plugins\n[removed_plugins]\n"
        _write(repo / "doctor.toml", header + array + "\n[other]\nx = 1\n")

        result = plugin_remove.add_to_watchlist("alpha", repo_root=repo)

        assert result.rc == 0, result.detail
        assert (repo / "doctor.toml").read_text() == (
            header + expected + "\n[other]\nx = 1\n"
        )


def test_watchlist_multiline_comment_cannot_hide_a_false_success(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path / "doctor.toml",
        "[removed_plugins]\n"
        "names = [\n"
        '  "ponytail", # historical ] bracket\n'
        '  "claudex-loop",\n'
        "]\n",
    )

    result = plugin_remove.add_to_watchlist("alpha", repo_root=tmp_path)

    assert result.rc == 0
    assert tomllib.loads(path.read_text())["removed_plugins"]["names"] == [
        "ponytail",
        "claudex-loop",
        "alpha",
    ]


def test_watchlist_verification_rejects_an_edit_of_a_decoy_array(
    tmp_path: Path,
) -> None:
    """Row 14: a ``names = [`` inside a string must not yield a false success."""
    original = (
        '[removed_plugins]\nnote = """\nnames = ["decoy"]\n"""\nnames = ["ponytail"]\n'
    )
    path = _write(tmp_path / "doctor.toml", original)

    result = plugin_remove.add_to_watchlist("alpha", repo_root=tmp_path)

    assert result.rc == 1
    assert "verification" in result.detail
    assert path.read_text() == original


# ---------------------------------------------------------------------------
# Apply ordering and the marketplace guard.
# ---------------------------------------------------------------------------


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
                "remove-codex-marketplace", "codex plugin marketplace remove", "market"
            ),
        ),
        (),
    )

    results = plugin_remove.apply(removal_plan, home=tmp_path, repo_root=repo)

    assert [result.rc for result in results] == [9]
    assert calls == [["mise", "exec", "--", "codex", "plugin", "remove", _PLUGIN]]


def test_apply_refuses_marketplace_removal_while_target_is_still_installed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    _registry(tmp_path, {_PLUGIN: [{"scope": "user"}]})
    calls: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        calls.append(argv)
        if argv[:6] == ["mise", "exec", "--", "claude", "plugin", "list"]:
            return _result(
                stdout=json.dumps([{"id": _PLUGIN, "scope": "user", "enabled": True}])
            )
        if argv[:6] == ["mise", "exec", "--", "codex", "plugin", "list"]:
            return _result(stdout=json.dumps({"installed": []}))
        raise AssertionError(argv)

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)
    removal_plan = RemovalPlan(
        _PLUGIN,
        (RemovalStep("remove-claude-marketplace", "remove", "market"),),
        (),
    )

    results = plugin_remove.apply(removal_plan, home=tmp_path, repo_root=repo)

    assert len(results) == 1
    assert results[0].rc == 1
    assert _PLUGIN in results[0].detail
    assert not any("marketplace" in argv for argv in calls)


# ---------------------------------------------------------------------------
# A fake native harness that behaves as the vendor documents.
# ---------------------------------------------------------------------------


class _FakeHarness:
    """``claude``/``codex``/``git`` stand-ins that mutate a scratch home.

    Every settings rewrite re-serializes the WHOLE file with a different
    indentation, as the real CLI does, so only a minimal-diff restore can
    reproduce the original formatting.
    """

    def __init__(self, home: Path, repos: tuple[Path, ...] = ()) -> None:
        self.home = home
        self.repos = repos
        self.calls: list[tuple[tuple[str, ...], str | None]] = []
        self.keep_known = False

    @property
    def registry(self) -> Path:
        return self.home / ".claude" / "plugins" / "installed_plugins.json"

    @property
    def known(self) -> Path:
        return self.home / ".claude" / "plugins" / "known_marketplaces.json"

    def _rewrite(self, path: Path, section: str, key: str) -> None:
        if not path.exists():
            return
        value = json.loads(path.read_text())
        table = value.get(section)
        if isinstance(table, dict) and key in table:
            del table[key]
            path.write_text(json.dumps(value, indent=4) + "\n")

    def _list(self) -> SimpleNamespace:
        loaded = json.loads(self.registry.read_text()) if self.registry.exists() else {}
        rows = [
            {"id": key, "scope": entry.get("scope"), "enabled": True}
            for key, entries in loaded.get("plugins", {}).items()
            for entry in entries
        ]
        return _result(stdout=json.dumps(rows))

    def _uninstall(self, selector: str, scope: str, cwd: str | None) -> SimpleNamespace:
        loaded = json.loads(self.registry.read_text())
        entries = loaded["plugins"].get(selector, [])
        kept = [
            entry
            for entry in entries
            if not (
                entry.get("scope") == scope
                and (scope == "user" or entry.get("projectPath") == cwd)
            )
        ]
        if kept:
            loaded["plugins"][selector] = kept
        else:
            loaded["plugins"].pop(selector, None)
        self.registry.write_text(json.dumps(loaded, indent=4))
        settings = (
            self.home / ".claude" / "settings.json"
            if scope == "user"
            else Path(str(cwd)) / ".claude" / "settings.json"
        )
        self._rewrite(settings, "enabledPlugins", selector)
        return _result(stdout='{"outcome":"ok"}\n')

    def _marketplace_remove(
        self, marketplace: str, scope: str, cwd: str | None
    ) -> SimpleNamespace:
        files = {
            "user": self.home / ".claude" / "settings.json",
            "project": Path(str(cwd)) / ".claude" / "settings.json",
            "local": Path(str(cwd)) / ".claude" / "settings.local.json",
        }
        self._rewrite(files[scope], "extraKnownMarketplaces", marketplace)
        if scope == "user" and not self.keep_known:
            known = json.loads(self.known.read_text())
            location = Path(known.pop(marketplace)["installLocation"])
            self.known.write_text(json.dumps(known))
            shutil.rmtree(location, ignore_errors=True)
        return _result()

    def __call__(self, argv: list[str], **kwargs: object) -> SimpleNamespace:
        cwd = kwargs.get("cwd")
        cwd_text = None if cwd is None else str(cwd)
        self.calls.append((tuple(argv), cwd_text))
        if argv[:2] == ["git", "-C"] and argv[3] == "worktree":
            return _result(stdout=f"worktree {argv[2]}\nHEAD abc\n")
        if argv[:2] == ["git", "-C"] and argv[3] == "grep":
            return _result(returncode=1)
        tool, command = argv[3], argv[4:]
        if tool == "codex":
            return _result(stdout=json.dumps({"installed": []}))
        if command[:2] == ["plugin", "list"]:
            return self._list()
        if command[:2] == ["plugin", "uninstall"]:
            return self._uninstall(command[2], command[4], cwd_text)
        if command[:3] == ["plugin", "marketplace", "remove"]:
            return self._marketplace_remove(command[3], command[5], cwd_text)
        raise AssertionError(argv)


_SOURCE = (
    '{\n      "source": {\n        "source": "github",\n'
    '        "repo": "o/%s"\n      }\n    }'
)


def _declaration(name: str) -> str:
    return f'    "{name}": ' + (_SOURCE % name)


def _settings_text(enabled: dict[str, bool], marketplaces: tuple[str, ...]) -> str:
    enabled_lines = ",\n".join(
        f'    "{key}": {json.dumps(value)}' for key, value in enabled.items()
    )
    declared = ",\n".join(_declaration(name) for name in marketplaces)
    return (
        "{\n"
        f'  "enabledPlugins": {{\n{enabled_lines}\n  }},\n'
        f'  "extraKnownMarketplaces": {{\n{declared}\n  }},\n'
        '  "permissions": { "allow": [] }\n'
        "}\n"
    )


def _known_text(home: Path, names: tuple[str, ...]) -> str:
    entries = []
    for name in names:
        location = home / ".claude" / "plugins" / "marketplaces" / name
        (location / ".claude-plugin").mkdir(parents=True, exist_ok=True)
        entries.append(
            f'  "{name}": {{\n'
            '    "source": {\n      "source": "github",\n'
            f'      "repo": "o/{name}"\n    }},\n'
            f'    "installLocation": "{location}",\n'
            '    "lastUpdated": "2026-09-24T00:00:00.000Z"\n'
            "  }"
        )
    return "{\n" + ",\n".join(entries) + "\n}\n"


def test_marketplace_removal_calls_each_declared_scope_and_keeps_minimal_diffs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N2: one native call per declared scope; settings restored minus the span."""
    home = tmp_path / "home"
    repo = _repo(tmp_path)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_settings = _write(
        first / ".claude" / "settings.json",
        _settings_text({"keep@else": True}, ("else", "tools")),
    )
    second_local = _write(
        second / ".claude" / "settings.local.json",
        _settings_text({"keep@else": True}, ("tools",)),
    )
    user_settings = _write(
        home / ".claude" / "settings.json",
        _settings_text({"keep@else": True}, ("tools", "else")),
    )
    known = _write(
        home / ".claude" / "plugins" / "known_marketplaces.json",
        _known_text(home, ("else", "tools")),
    )
    _registry(home, {})
    harness = _FakeHarness(home)
    monkeypatch.setattr(plugin_remove.subprocess, "run", harness)
    step = RemovalStep(
        "remove-claude-marketplace", "remove", "tools", (str(first), str(second))
    )

    results = plugin_remove.apply(
        RemovalPlan("solo@tools", (step,), ()), home=home, repo_root=repo
    )

    assert [result.rc for result in results] == [0], results
    removals = [(argv[4:], cwd) for argv, cwd in harness.calls if "marketplace" in argv]
    assert removals == [
        (
            ("plugin", "marketplace", "remove", "tools", "--scope", "project"),
            str(first),
        ),
        (("plugin", "marketplace", "remove", "tools", "--scope", "local"), str(second)),
        (("plugin", "marketplace", "remove", "tools", "--scope", "user"), str(repo)),
    ]
    assert first_settings.read_text() == _settings_text({"keep@else": True}, ("else",))
    assert user_settings.read_text() == _settings_text({"keep@else": True}, ("else",))
    assert second_local.read_text() == (
        "{\n"
        '  "enabledPlugins": {\n    "keep@else": true\n  },\n'
        '  "extraKnownMarketplaces": {},\n'
        '  "permissions": { "allow": [] }\n'
        "}\n"
    )
    assert json.loads(known.read_text()).keys() == {"else"}
    assert "\n" not in known.read_text()
    assert not list(first_settings.parent.glob("*.bak"))


def test_marketplace_removal_never_restores_the_harness_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N2(a): a failed goal is reported; the CLI-owned file keeps the CLI's bytes."""
    home = tmp_path / "home"
    repo = _repo(tmp_path)
    _write(home / ".claude" / "settings.json", _settings_text({}, ("tools",)))
    known = _write(
        home / ".claude" / "plugins" / "known_marketplaces.json",
        _known_text(home, ("tools",)),
    )
    _registry(home, {})
    harness = _FakeHarness(home)
    harness.keep_known = True

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        result = harness(argv, **kwargs)
        if "marketplace" in argv:
            known.write_text(known.read_text().replace("2026-09-24", "2026-09-25"))
        return result

    monkeypatch.setattr(plugin_remove.subprocess, "run", run)
    step = RemovalStep("remove-claude-marketplace", "remove", "tools", ())

    results = plugin_remove.apply(
        RemovalPlan("solo@tools", (step,), ()), home=home, repo_root=repo
    )

    assert [result.rc for result in results] == [1]
    assert "still registers tools" in results[0].detail
    assert "2026-09-25" in known.read_text()
    snapshot = [
        path for path in _backups(repo) if path.name == "known_marketplaces.json"
    ]
    assert snapshot
    assert "2026-09-24" in snapshot[0].read_text()


# ---------------------------------------------------------------------------
# End to end: scratch home, real inventory -> plan -> apply through the CLI.
# ---------------------------------------------------------------------------


def _install(home: Path, selector: str, version: str) -> Path:
    name, marketplace = selector.split("@")
    install = home / ".claude" / "plugins" / "cache" / marketplace / name / version
    _write(install / ".claude-plugin" / "plugin.json", json.dumps({"name": name}))
    _write(install / "payload.txt", f"{selector} payload")
    return install


def test_end_to_end_apply_removes_one_plugin_and_leaves_its_sibling_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    repo = _repo(tmp_path, watched=False)
    project = home / "dev" / "github" / "owner" / "project"
    (project / ".git").mkdir(parents=True)
    alpha = _install(home, _PLUGIN, "1.0.0")
    beta = _install(home, "beta@market", "2.0.0")
    plugins_dir = home / ".claude" / "plugins"
    _write(plugins_dir / "data" / "alpha-market" / "state.json", '{"a": 1}')
    _write(plugins_dir / "data" / "beta-market" / "state.json", '{"b": 2}')
    beta_entry = [{"scope": "user", "installPath": str(beta), "version": "2.0.0"}]
    registry = _registry(
        home,
        {
            _PLUGIN: [
                {"scope": "user", "installPath": str(alpha)},
                {
                    "scope": "project",
                    "projectPath": str(project),
                    "installPath": str(alpha),
                },
            ],
            "beta@market": beta_entry,
        },
    )
    settings = _write(
        project / ".claude" / "settings.json",
        _settings_text({_PLUGIN: True, "beta@market": True}, ("market",)),
    )
    known = _write(
        plugins_dir / "known_marketplaces.json", _known_text(home, ("market",))
    )
    known_before = known.read_bytes()
    beta_cache_before = _tree(beta.parent)
    beta_data_before = _tree(plugins_dir / "data" / "beta-market")
    harness = _FakeHarness(home)
    monkeypatch.setattr(plugin_remove.subprocess, "run", harness)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo)

    rc = plugin_remove.plugin_remove_main([_PLUGIN, "--apply"])

    assert rc == 0
    assert not alpha.parent.exists()
    assert not (plugins_dir / "data" / "alpha-market").exists()
    assert _tree(beta.parent) == beta_cache_before
    assert _tree(plugins_dir / "data" / "beta-market") == beta_data_before
    assert json.loads(registry.read_text())["plugins"] == {"beta@market": beta_entry}
    assert known.read_bytes() == known_before
    assert settings.read_text() == _settings_text({"beta@market": True}, ("market",))
    assert tomllib.loads((repo / "doctor.toml").read_text())["removed_plugins"] == {
        "names": ["alpha"]
    }
    archives = [path for path in _backups(repo) if path.suffix == ".gz"]
    assert len(archives) == 1
    assert not any("marketplace" in argv for argv, _cwd in harness.calls)


def test_end_to_end_apply_removes_the_last_plugin_and_its_marketplace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    repo = _repo(tmp_path, watched=False)
    project = home / "dev" / "github" / "owner" / "project"
    (project / ".git").mkdir(parents=True)
    solo = _install(home, "solo@tools", "1.0.0")
    plugins_dir = home / ".claude" / "plugins"
    _registry(home, {"solo@tools": [{"scope": "user", "installPath": str(solo)}]})
    project_settings = _write(
        project / ".claude" / "settings.json",
        _settings_text({"keep@else": True}, ("else", "tools")),
    )
    user_settings = _write(
        home / ".claude" / "settings.json",
        _settings_text({"solo@tools": True, "keep@else": True}, ("tools",)),
    )
    known = _write(
        plugins_dir / "known_marketplaces.json", _known_text(home, ("else", "tools"))
    )
    harness = _FakeHarness(home)
    monkeypatch.setattr(plugin_remove.subprocess, "run", harness)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(repo)

    rc = plugin_remove.plugin_remove_main(["solo@tools", "--apply"])

    assert rc == 0
    assert project_settings.read_text() == _settings_text(
        {"keep@else": True}, ("else",)
    )
    assert user_settings.read_text() == (
        "{\n"
        '  "enabledPlugins": {\n    "keep@else": true\n  },\n'
        '  "extraKnownMarketplaces": {},\n'
        '  "permissions": { "allow": [] }\n'
        "}\n"
    )
    assert set(json.loads(known.read_text())) == {"else"}
    assert not (plugins_dir / "cache" / "tools").exists()
    assert (
        "solo"
        in tomllib.loads((repo / "doctor.toml").read_text())["removed_plugins"]["names"]
    )
