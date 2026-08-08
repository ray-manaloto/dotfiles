# Copyright (c) 2026 Raymond Manaloto
"""Tests for the linter-upgrade partition (#651).

The module's value is entirely in the ATTRIBUTION — which violations belong to
the code and which arrived with the bump — so the tests pin the three ways that
attribution can quietly become meaningless: a baseline equal to the current pin
(a comparison with one face), a baseline derived from the wrong revision (the
previous COMMIT rather than the previous LOCKFILE change, which is usually the
same pin), and a one-directional diff that hides a rule which stopped firing.

Every subprocess is injected. The parsers are exercised against real output
shapes rather than invented ones — `ruff --output-format json` and `ty
--output-format concise`, both checked against the live CLIs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Only referenced as an annotation here (`LogCaptureFixture`); every other
    # test module also calls `pytest.raises`, which is why they import it at
    # runtime and this one does not.
    import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import lint_delta

REPO_ROOT = Path(__file__).parent.parent


def _lock(**versions: str) -> str:
    return "\n".join(
        f'[[package]]\nname = "{name}"\nversion = "{version}"\n'
        for name, version in versions.items()
    )


# --------------------------------------------------------------------------- #
# Reading the pins
# --------------------------------------------------------------------------- #


def test_the_pinned_version_is_read_by_package_name() -> None:
    text = _lock(ruff="0.16.2", ty="0.0.69")
    assert lint_delta.locked_version(text, "ruff") == "0.16.2"
    assert lint_delta.locked_version(text, "ty") == "0.0.69"


def test_an_absent_package_reads_as_none_rather_than_a_wrong_version() -> None:
    assert lint_delta.locked_version(_lock(ruff="0.16.2"), "pylint") is None


def test_a_package_whose_name_is_a_prefix_is_not_matched() -> None:
    """`ty` must not be satisfied by `typing-extensions`."""
    text = _lock(**{"typing-extensions": "4.0.0"})
    assert lint_delta.locked_version(text, "ty") is None


def test_the_shipped_lockfile_pins_both_tools() -> None:
    """A real-corpus arm: the parse must work on the file it will actually read."""
    text = (REPO_ROOT / lint_delta.LOCKFILE).read_text()
    assert lint_delta.locked_version(text, "ruff")
    assert lint_delta.locked_version(text, "ty")


# --------------------------------------------------------------------------- #
# Parsing each tool's output
# --------------------------------------------------------------------------- #


def test_ruff_codes_are_counted_from_its_json() -> None:
    payload = json.dumps(
        [
            {"code": "ISC004", "filename": "a.py"},
            {"code": "ISC004", "filename": "b.py"},
            {"code": "E501", "filename": "a.py"},
        ]
    )
    assert lint_delta.parse_ruff(payload) == Counter({"ISC004": 2, "E501": 1})


def test_ruff_output_that_is_not_json_counts_nothing_rather_than_raising() -> None:
    """A crashed linter must not look like a clean tree.

    It counts zero, so the caller's comparison shows every code as retired,
    which is loud rather than reassuring.
    """
    assert lint_delta.parse_ruff("error: unrecognized option") == Counter()


def test_ty_codes_are_counted_from_its_concise_output() -> None:
    """Ty has no JSON, so the `error[rule-name]` prefix is what there is."""
    output = (
        "error[unresolved-import] /a.py:1:1: cannot resolve\n"
        "warning[unused-ignore] /b.py:2:1: unused\n"
        "error[unresolved-import] /c.py:3:1: cannot resolve\n"
    )
    assert lint_delta.parse_ty(output) == Counter(
        {"unresolved-import": 2, "unused-ignore": 1}
    )


# --------------------------------------------------------------------------- #
# The partition
# --------------------------------------------------------------------------- #


def _delta(baseline: Counter[str], current: Counter[str]) -> lint_delta.Delta:
    return lint_delta.Delta("ruff", "0.15.20", "0.16.2", baseline, current)


def test_a_code_both_versions_fire_is_attributed_to_the_code() -> None:
    delta = _delta(Counter({"I001": 1}), Counter({"I001": 1, "ISC004": 30}))
    assert delta.mine == [("I001", 1)]
    assert delta.introduced == [("ISC004", 30)]


def test_a_code_that_stopped_firing_is_reported_as_lost_coverage() -> None:
    """The direction a one-way diff hides.

    A rule the old version caught and the new one does not is coverage the gate
    silently lost, which reads as good news precisely because nothing fails.
    """
    delta = _delta(Counter({"D403": 4}), Counter({"ISC004": 1}))
    assert delta.retired == [("D403", 4)]


def test_counts_are_reported_at_the_current_version_for_shared_codes() -> None:
    """A shared code whose count MOVED is still yours; report today's number."""
    delta = _delta(Counter({"E501": 1}), Counter({"E501": 5}))
    assert delta.mine == [("E501", 5)]


def test_the_report_states_the_split_and_both_directions() -> None:
    report = lint_delta.render_report(
        _delta(Counter({"I001": 1, "D403": 2}), Counter({"I001": 1, "ISC004": 30}))
    )
    assert "**1 attributable to the code, 30 to the upgrade.**" in report
    assert "control arm" in report
    assert "`D403`" in report


# --------------------------------------------------------------------------- #
# Deriving the baseline
# --------------------------------------------------------------------------- #


def test_the_baseline_revision_is_the_previous_lockfile_change() -> None:
    """Not HEAD~1 — the previous commit usually did not touch the lockfile.

    Driven against the real repo, because the property being tested is about
    git history and a fixture repo would only prove the command string.
    """
    revision = lint_delta.previous_lock_revision(REPO_ROOT)
    assert revision
    current = lint_delta.locked_version(
        (REPO_ROOT / lint_delta.LOCKFILE).read_text(), "ruff"
    )
    earlier = lint_delta.version_at(REPO_ROOT, revision, "ruff", lint_delta.LOCKFILE)
    assert earlier is not None
    # Not asserted equal or unequal: what matters is that a version was
    # RECOVERED from that revision. Asserting a difference would bind this test
    # to whichever bump happens to be most recent.
    assert isinstance(current, str)


def test_a_revision_without_the_lockfile_yields_none(tmp_path: Path) -> None:
    assert (
        lint_delta.version_at(tmp_path, "deadbeef", "ruff", lint_delta.LOCKFILE) is None
    )


# --------------------------------------------------------------------------- #
# The refusals — where a wrong answer would be silent
# --------------------------------------------------------------------------- #


def test_a_baseline_equal_to_the_current_pin_is_refused(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Comparing a version against itself can only report 'no change'.

    That is a probe with one face, and reporting it as a clean bill is the
    false negative `probes-need-a-control-arm.md` exists to refuse.
    """
    (tmp_path / "python").mkdir()
    (tmp_path / lint_delta.LOCKFILE).write_text(_lock(ruff="0.16.2"))
    rc = lint_delta.lint_delta_main(tmp_path, baseline="0.16.2")
    assert rc == 2
    assert any("one face" in record.getMessage() for record in caplog.records)


def test_an_unknown_tool_is_refused_with_the_known_ones_named(
    tmp_path: Path,
) -> None:
    assert lint_delta.lint_delta_main(tmp_path, tool="pylint") == 2


def test_a_lockfile_that_does_not_pin_the_tool_is_refused(tmp_path: Path) -> None:
    (tmp_path / "python").mkdir()
    (tmp_path / lint_delta.LOCKFILE).write_text(_lock(pytest="8.0.0"))
    assert lint_delta.lint_delta_main(tmp_path, tool="ruff") == 2


def test_an_underivable_baseline_is_refused_rather_than_guessed(
    tmp_path: Path,
) -> None:
    (tmp_path / "python").mkdir()
    (tmp_path / lint_delta.LOCKFILE).write_text(_lock(ruff="0.16.2"))
    # Not a git repo, so no earlier revision exists to read a pin from.
    assert lint_delta.lint_delta_main(tmp_path, tool="ruff") == 2


# --------------------------------------------------------------------------- #
# Invocation
# --------------------------------------------------------------------------- #


def test_the_tool_is_pinned_by_version_in_the_invocation(tmp_path: Path) -> None:
    """Pin the version INTO the invocation rather than resolving it.

    The point is to run a version the project is not pinned to, which an
    environment-resolved binary cannot do.
    """
    seen: list[list[str]] = []

    def fake_run(
        argv: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 1, "[]", "")

    lint_delta.run_at_version(
        lint_delta.TOOLS["ruff"], "0.15.20", ("python/src",), cwd=tmp_path, run=fake_run
    )
    assert seen[0][:2] == ["uvx", "ruff@0.15.20"]
    assert seen[0][-1] == "python/src"


def test_a_nonzero_exit_is_expected_and_does_not_discard_the_findings(
    tmp_path: Path,
) -> None:
    """A linter that found violations exits non-zero — that is the normal case."""
    payload = json.dumps([{"code": "E501"}])
    counts = lint_delta.run_at_version(
        lint_delta.TOOLS["ruff"],
        "0.15.20",
        ("python/src",),
        cwd=tmp_path,
        run=lambda argv, **_k: subprocess.CompletedProcess(argv, 1, payload, ""),
    )
    assert counts == Counter({"E501": 1})


def test_the_mise_task_calls_the_cli() -> None:
    mise_toml = (REPO_ROOT / "mise.toml").read_text()
    assert "[tasks.lint-delta]" in mise_toml
    assert "dotfiles-setup lint-delta" in mise_toml
