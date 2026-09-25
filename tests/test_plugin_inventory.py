# Copyright (c) 2026 Raymond Manaloto
"""Tests for exact-selector CLI and bounded repository plugin inventory."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from dotfiles_setup import plugin_inventory, plugin_remove

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
        json.dumps({"dependencies": [{"name": "dep", "marketplace": "deps"}]})
    )
    (sibling_install / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"dependencies": ["a-b"]})
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
    local = repo / ".claude" / "settings.local.json"
    local.write_text(json.dumps({"enabledPlugins": {"a-b@c": True}}))

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

    assert result.project_settings == (settings, local)
    assert result.enabling_settings == (local,)
    assert result.claude_marketplace_plugins == ("a-b@c", "beta@c")
    assert result.codex_marketplace_plugins == ("gamma@c",)
    assert result.dependent_plugins == ("beta@c",)
    assert result.enabled_dependents == ("beta@c",)
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


def test_parse_is_linear_for_a_large_grep_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N9: the old re-slicing parse took 5.2s at 40k records (O(n^2))."""
    records = 60_000
    payload = b"docs/some file.md\x0012\x00a line naming ponytail\n" * records

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del argv, kwargs
        return SimpleNamespace(stdout=payload, stderr=b"", returncode=0)

    monkeypatch.setattr(plugin_inventory.subprocess, "run", run)
    started = time.perf_counter()

    found = plugin_inventory.live_references(tmp_path, "ponytail")

    assert time.perf_counter() - started < 3
    assert len(found) == records
    assert (found[-1].path, found[-1].line, found[-1].text) == (
        "docs/some file.md",
        12,
        "a line naming ponytail",
    )


def test_grep_parse_tolerates_nul_in_text_and_rejects_truncation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payloads = [
        b"a.md\x001\x00one\nb dir/c.md\x0022\x00two\x00\x00bytes\nd.pgm\x003\x00z\n",
        b"a.md\x001\x00one\nb.md\x002\x00two",
    ]

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del argv, kwargs
        return SimpleNamespace(stdout=payloads.pop(0), stderr=b"", returncode=0)

    monkeypatch.setattr(plugin_inventory.subprocess, "run", run)

    found = plugin_inventory.live_references(tmp_path, "x")

    assert [(item.path, item.line, item.text) for item in found] == [
        ("a.md", 1, "one"),
        ("b dir/c.md", 22, "two\x00\x00bytes"),
        ("d.pgm", 3, "z"),
    ]
    with pytest.raises(RuntimeError, match="malformed"):
        plugin_inventory.live_references(tmp_path, "x")


@pytest.mark.parametrize("selector", ["honcho@", "@honcho", "a@b@c", "x@y/z"])
def test_inventory_rejects_a_malformed_selector_before_any_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selector: str
) -> None:
    calls: list[list[str]] = []

    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        calls.append(argv)
        return _result()

    monkeypatch.setattr(plugin_inventory.subprocess, "run", run)

    with pytest.raises(ValueError, match="exactly <plugin>@<marketplace>"):
        plugin_inventory.inventory(selector, home=tmp_path, root=tmp_path / "gh")
    assert calls == []


def _installed(home: Path, selector: str, dependencies: object | None) -> dict:
    name, marketplace = selector.split("@")
    install = home / ".claude" / "plugins" / "cache" / marketplace / name / "1.0.0"
    manifest: dict[str, object] = {"name": name}
    if dependencies is not None:
        manifest["dependencies"] = dependencies
    (install / ".claude-plugin").mkdir(parents=True)
    (install / ".claude-plugin" / "plugin.json").write_text(
        json.dumps(manifest, indent=2)
    )
    return {"scope": "user", "installPath": str(install)}


def _dependency_home(
    tmp_path: Path, plugins: dict[str, object | None], catalog: dict[str, object]
) -> Path:
    home = tmp_path / "home"
    registry = {
        selector: [_installed(home, selector, dependencies)]
        for selector, dependencies in plugins.items()
    }
    plugins_dir = home / ".claude" / "plugins"
    (plugins_dir / "installed_plugins.json").write_text(
        json.dumps({"version": 2, "plugins": registry})
    )
    known: dict[str, object] = {}
    for marketplace, entries in catalog.items():
        location = plugins_dir / "marketplaces" / marketplace
        (location / ".claude-plugin").mkdir(parents=True)
        (location / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps({"name": marketplace, "plugins": entries})
        )
        known[marketplace] = {"source": {}, "installLocation": str(location)}
    (plugins_dir / "known_marketplaces.json").write_text(json.dumps(known))
    return home


def _cli(enabled: dict[str, bool]) -> object:
    def run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        del kwargs
        if argv[:6] == ["mise", "exec", "--", "claude", "plugin", "list"]:
            rows = [
                {"id": key, "scope": "user", "enabled": value}
                for key, value in enabled.items()
            ]
            return _result(stdout=json.dumps(rows))
        if argv[:6] == ["mise", "exec", "--", "codex", "plugin", "list"]:
            return _result(stdout=json.dumps({"installed": []}))
        raise AssertionError(argv)

    return run


def test_the_live_dependency_shape_blocks_removal_even_when_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N8: aggregated-research's object deps; installed but disabled still blocks."""
    live = [
        {"name": "firecrawl", "marketplace": "firecrawl"},
        {"name": "exa", "marketplace": "exa"},
        {"name": "context7", "marketplace": "context7-marketplace"},
        {"name": "last30days", "marketplace": "last30days-skill"},
    ]
    home = _dependency_home(
        tmp_path,
        {"aggregated-research@ray-manaloto": live, "exa@exa": None},
        {},
    )
    monkeypatch.setattr(
        plugin_inventory.subprocess,
        "run",
        _cli({"aggregated-research@ray-manaloto": False, "exa@exa": True}),
    )

    result = plugin_inventory.inventory("exa@exa", home=home, root=tmp_path / "gh")
    removal_plan = plugin_remove.plan(result, repo_root=tmp_path, home=home)

    assert result.dependent_plugins == ("aggregated-research@ray-manaloto",)
    assert result.enabled_dependents == ()
    assert (
        "installed plugin depends on target: aggregated-research@ray-manaloto "
        "(installed but enabled nowhere; re-enabling it would break)"
    ) in removal_plan.blockers


def test_dependency_names_resolve_in_the_declaring_marketplace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare name or a marketplace-less object means the DECLARER's marketplace."""
    home = _dependency_home(
        tmp_path,
        {
            "target@market": None,
            "target@elsewhere": None,
            "bare@market": ["target"],
            "versioned@market": [{"name": "target", "version": "~1.0"}],
            "crosses@other": [{"name": "target", "marketplace": "market"}],
            "names-elsewhere@market": [{"name": "target", "marketplace": "elsewhere"}],
            "unrelated@other": ["target"],
            "catalogued@market": None,
        },
        {"market": [{"name": "catalogued", "dependencies": ["target"]}]},
    )
    monkeypatch.setattr(plugin_inventory.subprocess, "run", _cli({}))

    result = plugin_inventory.inventory(
        "target@market", home=home, root=tmp_path / "gh"
    )

    assert result.errors == ()
    assert result.dependent_plugins == (
        "bare@market",
        "catalogued@market",
        "crosses@other",
        "versioned@market",
    )


def test_an_unsupported_dependency_shape_is_a_loud_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = _dependency_home(
        tmp_path,
        {"target@market": None, "odd@market": {"target@market": "1.0.0"}},
        {},
    )
    monkeypatch.setattr(plugin_inventory.subprocess, "run", _cli({}))

    result = plugin_inventory.inventory(
        "target@market", home=home, root=tmp_path / "gh"
    )

    assert any("dependencies is not an array" in error for error in result.errors)
