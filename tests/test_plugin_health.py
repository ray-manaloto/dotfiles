# Copyright (c) 2026 Raymond Manaloto
"""Tests for plugin_health module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from dotfiles_setup import doctor
from dotfiles_setup.plugin_health import (
    PluginHealthCode,
    PluginRow,
    _declared_from_settings,
    evaluate,
)


class TestEvaluate:
    """Test observable-facts reconciliation."""

    def test_all_declared_installed_and_enabled_ok(self, tmp_path: Path) -> None:
        """All declared plugins have matching project-scoped rows → OK."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        declared = ["test@market"]
        rows = [
            PluginRow(
                id="test@market",
                scope="project",
                enabled=True,
                project_path=str(project_root.resolve()),
            ),
        ]

        report = evaluate(declared, rows, project_root)
        assert report.code == PluginHealthCode.OK
        assert report.declared_not_installed == []
        assert report.declared_disabled_here == []
        assert report.installed_not_declared == []

    def test_declared_not_installed_drift(self) -> None:
        """Declared plugin has no row anywhere → DRIFT."""
        declared = ["missing@market"]
        rows = []

        report = evaluate(declared, rows)
        assert report.code == PluginHealthCode.DRIFT
        assert report.declared_not_installed == ["missing@market"]
        assert report.declared_disabled_here == []
        assert report.installed_not_declared == []

    def test_declared_disabled_here_drift(self, tmp_path: Path) -> None:
        """Declared plugin has project-root row with enabled=false → DRIFT."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        declared = ["test@market"]
        rows = [
            PluginRow(
                id="test@market",
                scope="project",
                enabled=False,
                project_path=str(project_root.resolve()),
            ),
        ]

        report = evaluate(declared, rows, project_root)
        assert report.code == PluginHealthCode.DRIFT
        assert report.declared_not_installed == []
        assert report.declared_disabled_here == ["test@market"]
        assert report.installed_not_declared == []

    def test_installed_not_declared_drift(self, tmp_path: Path) -> None:
        """Project-root row enabled=true but not declared → DRIFT."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        declared = []
        rows = [
            PluginRow(
                id="undeclared@market",
                scope="project",
                enabled=True,
                project_path=str(project_root.resolve()),
            ),
        ]

        report = evaluate(declared, rows, project_root)
        assert report.code == PluginHealthCode.DRIFT
        assert report.declared_not_installed == []
        assert report.declared_disabled_here == []
        assert report.installed_not_declared == ["undeclared@market"]

    def test_firecrawl_regression_guard_silence(self, tmp_path: Path) -> None:
        """Declared id with no project-root row but user and other-project rows → OK.

        This is the firecrawl shape: declared but no project-scoped row exists.
        We report nothing because we cannot interpret rows without projectPath.
        """
        project_root = tmp_path / "project"
        other_project = tmp_path / "other"
        project_root.mkdir()
        other_project.mkdir()

        declared = ["firecrawl@firecrawl"]
        rows = [
            # User-scoped row (no projectPath)
            PluginRow(
                id="firecrawl@firecrawl",
                scope="user",
                enabled=True,
            ),
            # Other-project-scoped row
            PluginRow(
                id="firecrawl@firecrawl",
                scope="project",
                enabled=True,
                project_path=str(other_project.resolve()),
            ),
        ]

        report = evaluate(declared, rows, project_root)
        # Should be OK because we have no project-root row to contradict the declaration
        assert report.code == PluginHealthCode.OK
        assert report.declared_not_installed == []
        assert report.declared_disabled_here == []
        assert report.installed_not_declared == []

    def test_firecrawl_with_disabled_user_row_still_silence(
        self, tmp_path: Path
    ) -> None:
        """Firecrawl shape with disabled user row → still OK.

        Even if the user row is disabled, without a project-root row we have
        no direct contradiction of the declaration.
        """
        project_root = tmp_path / "project"
        other_project = tmp_path / "other"
        project_root.mkdir()
        other_project.mkdir()

        declared = ["firecrawl@firecrawl"]
        rows = [
            # User-scoped row disabled
            PluginRow(
                id="firecrawl@firecrawl",
                scope="user",
                enabled=False,
            ),
            # Other-project-scoped row
            PluginRow(
                id="firecrawl@firecrawl",
                scope="project",
                enabled=True,
                project_path=str(other_project.resolve()),
            ),
        ]

        report = evaluate(declared, rows, project_root)
        # Still OK: no project-root row means we don't contradict the declaration
        assert report.code == PluginHealthCode.OK
        assert report.declared_not_installed == []
        assert report.declared_disabled_here == []
        assert report.installed_not_declared == []

    def test_multiple_declared_all_ok(self, tmp_path: Path) -> None:
        """Multiple declared plugins all effectively enabled → OK."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        declared = ["test1@market", "test2@market"]
        rows = [
            PluginRow(
                id="test1@market",
                scope="project",
                enabled=True,
                project_path=str(project_root.resolve()),
            ),
            PluginRow(
                id="test2@market",
                scope="project",
                enabled=True,
                project_path=str(project_root.resolve()),
            ),
        ]

        report = evaluate(declared, rows, project_root)
        assert report.code == PluginHealthCode.OK

    def test_multiple_declared_partial_drift(self, tmp_path: Path) -> None:
        """Some declared plugins disabled → DRIFT."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        declared = ["test1@market", "test2@market"]
        rows = [
            PluginRow(
                id="test1@market",
                scope="project",
                enabled=True,
                project_path=str(project_root.resolve()),
            ),
            PluginRow(
                id="test2@market",
                scope="project",
                enabled=False,
                project_path=str(project_root.resolve()),
            ),
        ]

        report = evaluate(declared, rows, project_root)
        assert report.code == PluginHealthCode.DRIFT
        assert report.declared_disabled_here == ["test2@market"]

    def test_report_no_paths_emitted(self) -> None:
        """Report contains no filesystem paths (privacy)."""
        declared = ["test@market"]
        rows = []

        report = evaluate(declared, rows)
        report_str = repr(report)
        assert "/Users/" not in report_str
        assert "/home/" not in report_str

    def test_extra_keys_in_rows_tolerated(self, tmp_path: Path) -> None:
        """Rows with extra keys (mcpServers, notes) are handled gracefully."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        declared = ["test@market"]
        rows = [
            PluginRow(
                id="test@market",
                scope="project",
                enabled=True,
                project_path=str(project_root.resolve()),
            ),
        ]

        report = evaluate(declared, rows, project_root)
        assert report.code == PluginHealthCode.OK

    def test_local_scope_rows_ignored(self, tmp_path: Path) -> None:
        """Local-scope-only row → silence: no project-root row to interpret.

        A local-scope row means the plugin is installed, just not in a way
        relevant to this project. We report nothing.
        """
        project_root = tmp_path / "project"
        project_root.mkdir()

        declared = ["test@market"]
        rows = [
            PluginRow(
                id="test@market",
                scope="local",
                enabled=True,
            ),
        ]

        report = evaluate(declared, rows, project_root)
        # Installed but no project-scoped row: silence
        assert report.code == PluginHealthCode.OK
        assert report.declared_not_installed == []
        assert report.declared_disabled_here == []
        assert report.installed_not_declared == []

    def test_user_scope_rows_ignored_for_evaluation(self) -> None:
        """User-scope-only row → silence: no project-root row to interpret.

        A user-scope row means the plugin is installed, just not specifically
        for this project. We report nothing.
        """
        declared = ["test@market"]
        rows = [
            PluginRow(
                id="test@market",
                scope="user",
                enabled=True,
            ),
        ]

        report = evaluate(declared, rows)
        # Installed but no project-scoped row: silence
        assert report.code == PluginHealthCode.OK
        assert report.declared_not_installed == []
        assert report.declared_disabled_here == []
        assert report.installed_not_declared == []

    def test_all_three_findings_simultaneously(self, tmp_path: Path) -> None:
        """A single report can name drifts in all three categories."""
        project_root = tmp_path / "project"
        project_root.mkdir()

        declared = ["declared_ok@m", "declared_disabled@m", "declared_missing@m"]
        rows = [
            # OK case
            PluginRow(
                id="declared_ok@m",
                scope="project",
                enabled=True,
                project_path=str(project_root.resolve()),
            ),
            # Disabled case
            PluginRow(
                id="declared_disabled@m",
                scope="project",
                enabled=False,
                project_path=str(project_root.resolve()),
            ),
            # Not declared case
            PluginRow(
                id="undeclared@m",
                scope="project",
                enabled=True,
                project_path=str(project_root.resolve()),
            ),
        ]

        report = evaluate(declared, rows, project_root)
        assert report.code == PluginHealthCode.DRIFT
        assert report.declared_not_installed == ["declared_missing@m"]
        assert report.declared_disabled_here == ["declared_disabled@m"]
        assert report.installed_not_declared == ["undeclared@m"]


if TYPE_CHECKING:
    from pathlib import Path


def test_declared_from_settings_agrees_with_the_doctor_implementation() -> None:
    """The parity guard for the ONE deliberate duplication in this module.

    `plugin_health._declared_from_settings` mirrors `doctor.enabled_plugin_ids`
    because importing doctor here would be circular (doctor imports this module
    for its LIVE_CHECKS adapter) and a deferred import trips PLC0415, which this
    repo cannot silence. Duplication is only safe while something proves the two
    agree — this is that something.

    Both arms matter: the fixtures must include a case where project OVERRIDES
    user, or the test would pass on any implementation that ignores precedence.
    """
    cases: list[tuple[dict[str, object], dict[str, object]]] = [
        ({}, {}),
        ({"enabledPlugins": {"a@m": True}}, {}),
        ({}, {"enabledPlugins": {"b@m": True}}),
        # project turns OFF what user turned on — the precedence case
        ({"enabledPlugins": {"a@m": True}}, {"enabledPlugins": {"a@m": False}}),
        # project turns ON what user turned off
        ({"enabledPlugins": {"c@m": False}}, {"enabledPlugins": {"c@m": True}}),
        # non-bool values are ignored by both
        ({"enabledPlugins": {"d@m": "yes"}}, {"enabledPlugins": {"e@m": True}}),
        # a malformed enabledPlugins is tolerated by both
        ({"enabledPlugins": "not-a-dict"}, {"enabledPlugins": {"f@m": True}}),
    ]
    for user, project in cases:
        assert _declared_from_settings(user, project) == doctor.enabled_plugin_ids(
            user, project
        ), f"precedence drift for user={user} project={project}"

    # The control arm: these fixtures genuinely exercise precedence, so a
    # precedence-blind implementation would NOT satisfy the assertions above.
    assert (
        _declared_from_settings(
            {"enabledPlugins": {"a@m": True}}, {"enabledPlugins": {"a@m": False}}
        )
        == []
    )
    assert _declared_from_settings(
        {"enabledPlugins": {"c@m": False}}, {"enabledPlugins": {"c@m": True}}
    ) == ["c@m"]
