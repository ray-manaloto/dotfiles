# Copyright (c) 2026 Raymond Manaloto
"""The operator's attestation path, and the ban on every other one.

The boundary these guard is a HUMAN one, and it has now been crossed twice by
agents on this host: once by a session self-attesting through a plain Bash call
(2026-09-02), and once by the session BUILDING the ban, which smoke-tested the
new wrapper with no arguments and locked a tampered plan over the operator's
hash. Both times `/plan-attest`'s `disable-model-invocation: true` was set and
irrelevant — it stops the command, never the script.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from dotfiles_setup.hook_selfcheck import (
    _ATTEST_DENY_BASES,
    check_plan_attest_deny,
)
from dotfiles_setup.plan_attest import (
    ATTEST_SCRIPT,
    PLUGIN_ID,
    PluginNotInstalledError,
    resolve_attest_script,
)

PROJECT_ROOT = Path(__file__).parent.parent
SETTINGS = PROJECT_ROOT / ".claude" / "settings.json"


def _fake_plugin(home: Path, version: str = "3.14.0") -> Path:
    name, _, marketplace = PLUGIN_ID.partition("@")
    root = home / ".claude" / "plugins" / "cache" / marketplace / name / version
    (root / ATTEST_SCRIPT.parent).mkdir(parents=True, exist_ok=True)
    (root / ATTEST_SCRIPT).write_text("#!/bin/sh\nexit 0\n")
    return root


def test_the_script_resolves_out_of_the_plugin_cache(tmp_path: Path) -> None:
    """Through the shared resolver, so there is one version rule, not two."""
    root = _fake_plugin(tmp_path)
    assert resolve_attest_script(tmp_path) == root / ATTEST_SCRIPT


def test_the_highest_version_wins_not_the_newest_mtime(tmp_path: Path) -> None:
    """The cache keeps every version installed side by side.

    `listing_budget.plugin_root` records that an mtime heuristic picked the
    wrong one on the first try and an edit went to a dead file. This asserts
    this module inherits that rule rather than re-deriving it — 3.9.0 sorts
    above 3.14.0 as a STRING, so a lexicographic resolver fails here.
    """
    _fake_plugin(tmp_path, "3.9.0")
    newest = _fake_plugin(tmp_path, "3.14.0")
    assert resolve_attest_script(tmp_path) == newest / ATTEST_SCRIPT


def test_an_absent_plugin_is_a_legible_error_not_a_silent_miss(
    tmp_path: Path,
) -> None:
    """Naming what was looked for: disabled plugin and renamed script differ."""
    with pytest.raises(PluginNotInstalledError, match=PLUGIN_ID):
        resolve_attest_script(tmp_path)


def test_a_present_plugin_missing_its_script_says_so_differently(
    tmp_path: Path,
) -> None:
    """The other half of the arm above — the two failures need different fixes."""
    root = _fake_plugin(tmp_path)
    (root / ATTEST_SCRIPT).unlink()
    with pytest.raises(PluginNotInstalledError, match="upstream may have renamed"):
        resolve_attest_script(tmp_path)


# --------------------------------------------------- the deny rules themselves


def test_the_live_settings_deny_every_attestation_route() -> None:
    """The real file, not a fixture: this is the gate, so it must hold HERE."""
    assert check_plan_attest_deny(SETTINGS) == []


@pytest.mark.parametrize("base", _ATTEST_DENY_BASES)
def test_both_forms_are_denied_for_every_route(base: str) -> None:
    """The bare form is the one that WRITES, and it needs its own rule.

    A trailing `*` also matches the bare command only when it is the rule's
    sole wildcard (`$CC/permissions.md` wildcard table: `Bash(* --help *)`
    matches `npm --help x` but NOT `npm --help`). Every rule here carries a
    leading `*` or is a bare-command prefix, so `Bash(<base> *)` alone would
    leave the argument-less invocation allowed while the ban looked complete.
    """
    deny = set(json.loads(SETTINGS.read_text())["permissions"]["deny"])
    assert f"Bash({base})" in deny
    assert f"Bash({base} *)" in deny


def test_the_deny_check_notices_a_half_written_ban(tmp_path: Path) -> None:
    """The control arm: dropping ONLY the bare form must fail the check.

    That is the realistic regression — someone tidying the rules who believes a
    trailing `*` subsumes the bare command. A mutation that removed both forms
    would prove far less, since any presence check catches that
    (`probes-need-a-control-arm.md` rule 2: mutate realistically).
    """
    settings = json.loads(SETTINGS.read_text())
    settings["permissions"]["deny"].remove("Bash(*attest-plan.sh)")
    half = tmp_path / "settings.json"
    half.write_text(json.dumps(settings))
    failures = check_plan_attest_deny(half)
    assert len(failures) == 1
    assert "Bash(*attest-plan.sh)" in failures[0]


def test_an_unreadable_settings_file_fails_rather_than_passing(
    tmp_path: Path,
) -> None:
    """A check that returns clean when it cannot read is a check that can only pass."""
    missing = tmp_path / "nope.json"
    assert check_plan_attest_deny(missing) != []
