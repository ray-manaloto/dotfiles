# Copyright (c) 2026 Raymond Manaloto
"""Tests for the contract-token pre-flight (#652).

The pre-flight and the whole-suite audit are deliberately the SAME predicate at
different scopes, so the tests that matter most are the ones pinning that they
cannot drift apart — a pre-flight that says "binds once" while the gate later
says "matches twice" would be worse than no pre-flight, because it would be
trusted.

Fixtures are written into ``tmp_path`` rather than pointed at repo files. That
is not only isolation: the absent-token arm needs a string that is genuinely
absent, and a literal written into a tracked test file is thereafter present in
the corpus — the contamination
``.claude/rules/probes-need-a-control-arm.md`` rule 3 warns about. Building the
haystack means absence is a property of the fixture, not a hope about the repo.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import token_audit

REPO_ROOT = Path(__file__).parent.parent

_HAYSTACK = """\
def wire_it(handler):
    return handler

REGISTRY = {"a": wire_it, "b": wire_it}
"""


@pytest.fixture
def haystack(tmp_path: Path) -> Path:
    (tmp_path / "mod.py").write_text(_HAYSTACK)
    return tmp_path


# --------------------------------------------------------------------------- #
# The predicate
# --------------------------------------------------------------------------- #


def test_a_token_binding_one_site_is_ok(haystack: Path) -> None:
    (counted,) = token_audit.count_tokens(haystack, "mod.py", ["def wire_it("])
    assert (counted.count, counted.ok) == (1, True)


def test_a_token_binding_several_sites_is_not_ok(haystack: Path) -> None:
    """The #394 shape: either registry entry can stand in for the other."""
    (counted,) = token_audit.count_tokens(haystack, "mod.py", ["wire_it"])
    assert counted.count == 3
    assert not counted.ok
    assert "AMBIGUOUS" in counted.render()


def test_an_absent_token_is_reported_as_missing_not_as_ambiguous(
    haystack: Path,
) -> None:
    """Zero and many are different defects and deserve different words.

    Many means the contract asserts less than it claims; zero means the path
    or the spelling is wrong and it would fail the moment it ran.
    """
    (counted,) = token_audit.count_tokens(haystack, "mod.py", ["def unwire_it("])
    assert counted.count == 0
    assert not counted.ok
    assert "MISSING" in counted.render()


def test_a_path_that_does_not_exist_counts_zero_rather_than_raising(
    haystack: Path,
) -> None:
    """A wrong path and an absent token are the same finding to the caller."""
    (counted,) = token_audit.count_tokens(haystack, "nope.py", ["def wire_it("])
    assert counted.count == 0


def test_expected_multiplicity_is_a_parameter(haystack: Path) -> None:
    """Deliberate multiplicity exists — AMBIGUITY_ALLOWED documents 18 of them."""
    (counted,) = token_audit.count_tokens(haystack, "mod.py", ["wire_it"], expected=3)
    assert counted.ok


# --------------------------------------------------------------------------- #
# The pre-flight entry point
# --------------------------------------------------------------------------- #


def test_all_unique_tokens_exit_zero(haystack: Path) -> None:
    assert (
        token_audit.preflight_main(haystack, "mod.py", ["def wire_it(", "REGISTRY = {"])
        == 0
    )


def test_one_bad_token_among_good_ones_exits_one(haystack: Path) -> None:
    assert (
        token_audit.preflight_main(haystack, "mod.py", ["def wire_it(", "wire_it"]) == 1
    )


def test_the_passing_arm_is_reported_too(
    haystack: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A silent success is indistinguishable from a probe that never ran.

    The reassurance is half the point of a pre-flight: the caller is about to
    commit these tokens into a contract, so "I checked and they bind" has to be
    visible, not inferred from the absence of an error.
    """
    with caplog.at_level(logging.INFO, logger=token_audit.logger.name):
        token_audit.preflight_main(haystack, "mod.py", ["def wire_it("])
    assert any("matches 1x" in record.message for record in caplog.records)


def test_the_failure_names_the_stand_in_hazard(
    haystack: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR, logger=token_audit.logger.name):
        token_audit.preflight_main(haystack, "mod.py", ["wire_it"])
    assert any("stand-in" in record.getMessage() for record in caplog.records)


# --------------------------------------------------------------------------- #
# One predicate, two scopes — the property that makes the pre-flight trustworthy
# --------------------------------------------------------------------------- #


def test_the_suite_audit_and_the_preflight_agree_on_the_same_input(
    tmp_path: Path,
) -> None:
    """Drive both scopes over one manifest and require the same verdict.

    If these two ever answered differently, the pre-flight would be giving
    permission the gate then refuses — the worst outcome, since its whole value
    is being believed before the contract is written.
    """
    manifest = tmp_path / token_audit.MANIFEST
    manifest.parent.mkdir(parents=True)
    (tmp_path / "mod.py").write_text(_HAYSTACK)
    manifest.write_text(
        "[[suite]]\n"
        'name = "x.y"\n'
        'description = "d"\n'
        'category = "workflow"\n'
        'check_type = "static"\n'
        'handler = "require_tokens"\n'
        'paths = ["mod.py", "other.md"]\n'
        'per_path_tokens = { "mod.py" = ["wire_it", "def wire_it("] }\n'
        'tokens = ["wire_it"]\n'
    )
    (tmp_path / "other.md").write_text("filler\n")

    ambiguous = {(a.token, a.count) for a in token_audit.find_ambiguous(tmp_path)}
    preflighted = {
        (c.token, c.count)
        for c in token_audit.count_tokens(
            tmp_path, "mod.py", ["wire_it", "def wire_it("]
        )
        if not c.ok
    }
    assert ambiguous == preflighted == {("wire_it", 3)}


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #


def test_the_mise_task_calls_the_cli_flag_rather_than_a_second_implementation() -> None:
    mise_toml = (REPO_ROOT / "mise.toml").read_text()
    assert "[tasks.token-check]" in mise_toml
    assert "dotfiles-setup token-audit --check" in mise_toml


def test_the_shipped_manifest_still_passes_the_whole_suite_audit() -> None:
    """The regression arm for the refactor: same answer on the real corpus."""
    assert token_audit.find_violations(REPO_ROOT) == []
