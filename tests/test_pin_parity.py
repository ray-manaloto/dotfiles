# Copyright (c) 2026 Raymond Manaloto
"""Tests for the cross-site pin-parity check.

The load-bearing arm here is NOT "drift is detected" — it is "a site whose
pattern matches nothing FAILS". A rotted pattern silently drops its site out of
the comparison, leaving a check that can only pass, which is exactly the shape
``.claude/rules/probes-need-a-control-arm.md`` rule 1 rejects. Every test that
asserts a failure is paired with one asserting the passing direction, so none
of them can be satisfied by a checker that simply always fails.
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.pin_parity import (
    REGISTRY_NAME,
    check_all,
    check_tool,
    format_report,
    pin_parity_main,
    read_site,
)

if TYPE_CHECKING:
    import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_SEMVER = r"(\d+\.\d+\.\d+)"


def _write(root: Path, name: str, text: str) -> None:
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _sites(*paths: str, pattern: str = _SEMVER) -> list[dict[str, str]]:
    return [{"path": p, "pattern": pattern} for p in paths]


def test_agreeing_sites_pass(tmp_path: Path) -> None:
    _write(tmp_path, "a.txt", "tool 1.2.3\n")
    _write(tmp_path, "b.txt", "pin = 1.2.3\n")
    verdict = check_tool(tmp_path, "demo", _sites("a.txt", "b.txt"))
    assert verdict.ok
    assert verdict.distinct == ("1.2.3",)
    assert verdict.failure_reason() == ""


def test_disagreeing_sites_fail(tmp_path: Path) -> None:
    """The control arm for the test above: same shape, one value changed."""
    _write(tmp_path, "a.txt", "tool 1.2.3\n")
    _write(tmp_path, "b.txt", "pin = 1.2.4\n")
    verdict = check_tool(tmp_path, "demo", _sites("a.txt", "b.txt"))
    assert not verdict.ok
    assert verdict.distinct == ("1.2.3", "1.2.4")
    assert "pin drift" in verdict.failure_reason()


def test_pattern_matching_nothing_fails(tmp_path: Path) -> None:
    """A rotted pattern must FAIL, not silently drop the site.

    Without this, a reformatted file turns pin-parity into a check that can
    only pass — the site disappears from the comparison and the remaining
    sites trivially agree with themselves.
    """
    _write(tmp_path, "a.txt", "tool 1.2.3\n")
    _write(tmp_path, "b.txt", "this file was reformatted and no longer matches\n")
    verdict = check_tool(tmp_path, "demo", _sites("a.txt", "b.txt"))
    assert not verdict.ok
    assert verdict.unmatched == ("b.txt",)
    assert "matched nothing" in verdict.failure_reason()


def test_single_surviving_site_does_not_rescue_a_rotted_pattern(
    tmp_path: Path,
) -> None:
    """The failure above must not be rescuable by the other site agreeing.

    This is the mutation that a naive implementation passes: drop the
    unmatched site, find one distinct version left, report OK.
    """
    _write(tmp_path, "a.txt", "tool 1.2.3\n")
    _write(tmp_path, "b.txt", "nothing here\n")
    _write(tmp_path, "c.txt", "also 1.2.3\n")
    verdict = check_tool(tmp_path, "demo", _sites("a.txt", "b.txt", "c.txt"))
    assert verdict.distinct == ("1.2.3",), "surviving sites do agree"
    assert not verdict.ok, "but an unreadable site must still fail the tool"


def test_absent_file_fails(tmp_path: Path) -> None:
    _write(tmp_path, "a.txt", "tool 1.2.3\n")
    verdict = check_tool(tmp_path, "demo", _sites("a.txt", "gone.txt"))
    assert not verdict.ok
    assert verdict.missing_files == ("gone.txt",)
    assert "absent" in verdict.failure_reason()


def test_intra_file_drift_is_caught(tmp_path: Path) -> None:
    """One file carrying the pin twice is compared against itself.

    `.github/actions/setup-mise/action.yml` really does carry it twice; a
    checker reading only the first match would miss a split inside one file.
    """
    _write(tmp_path, "a.txt", "version: 1.2.3\nversion: 1.2.4\n")
    verdict = check_tool(tmp_path, "demo", _sites("a.txt"))
    assert not verdict.ok
    assert verdict.distinct == ("1.2.3", "1.2.4")


def test_read_site_returns_none_for_absent_file(tmp_path: Path) -> None:
    assert read_site(tmp_path, "nope.txt", _SEMVER) is None
    _write(tmp_path, "yes.txt", "1.2.3")
    reading = read_site(tmp_path, "yes.txt", _SEMVER)
    assert reading is not None
    assert reading.versions == ("1.2.3",)


def test_report_marks_drift_before_ok(tmp_path: Path) -> None:
    _write(tmp_path, "ok_a.txt", "1.2.3")
    _write(tmp_path, "bad_a.txt", "1.2.3")
    _write(tmp_path, "bad_b.txt", "9.9.9")
    good = check_tool(tmp_path, "good", _sites("ok_a.txt"))
    bad = check_tool(tmp_path, "bad", _sites("bad_a.txt", "bad_b.txt"))
    report = format_report([good, bad])
    assert report.index("DRIFT bad") < report.index("OK   good")


def test_main_returns_zero_only_when_every_tool_agrees(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    _write(tmp_path, "a.txt", "1.2.3")
    _write(tmp_path, "b.txt", "1.2.3")
    registry = '[meta]\nversion = "1"\n\n[tools.demo]\nsites = [\n'
    registry += '  { path = "a.txt", pattern = \'' + _SEMVER + "' },\n"
    registry += '  { path = "b.txt", pattern = \'' + _SEMVER + "' },\n]\n"
    _write(tmp_path, REGISTRY_NAME, registry)
    with caplog.at_level(logging.INFO):
        assert pin_parity_main(tmp_path) == 0
    assert "every site agrees" in caplog.text

    caplog.clear()
    _write(tmp_path, "b.txt", "9.9.9")
    with caplog.at_level(logging.INFO):
        assert pin_parity_main(tmp_path) == 1
    assert "pin-parity FAILED" in caplog.text


def test_real_registry_is_parseable_and_declares_tools() -> None:
    with (PROJECT_ROOT / REGISTRY_NAME).open("rb") as handle:
        registry = tomllib.load(handle)
    tools = registry["tools"]
    assert tools, "the registry must declare at least one tool"
    assert "graphify" in tools, "Graphify's split pin sites must stay registered"
    for name, spec in tools.items():
        assert spec["sites"], f"{name} declares no sites"
        assert len(spec["sites"]) > 1, (
            f"{name} declares one site — pin parity is meaningless for a single "
            "site, so either add the sibling sites or drop the entry"
        )


def test_graphify_registry_uses_one_lock_entry_plus_three_stamps() -> None:
    with (PROJECT_ROOT / REGISTRY_NAME).open("rb") as handle:
        sites = tomllib.load(handle)["tools"]["graphify"]["sites"]
    assert [site["path"] for site in sites] == [
        "python/uv.lock",
        ".claude/skills/graphify/.graphify_version",
        ".codex/skills/graphify/.graphify_version",
        ".agents/skills/graphify/.graphify_version",
    ]
    lock_site = sites[0]
    reading = read_site(PROJECT_ROOT, lock_site["path"], lock_site["pattern"])
    assert reading is not None
    assert reading.versions == ("0.9.65",)


def test_every_real_pattern_still_matches_its_file() -> None:
    """Guards against pattern rot in the SHIPPED registry.

    This is the test that fails when someone reformats `.chezmoiversion` or
    the Dockerfile ARG line. It deliberately asserts only that each pattern
    MATCHES — whether the versions agree is the repo's current state, not a
    property of this test.
    """
    for verdict in check_all(PROJECT_ROOT):
        assert not verdict.missing_files, (
            f"{verdict.tool}: declared site(s) absent: {verdict.missing_files}"
        )
        assert not verdict.unmatched, (
            f"{verdict.tool}: pattern matched nothing in {verdict.unmatched} — "
            "the file changed shape; fix the pattern in pin-parity.toml"
        )
