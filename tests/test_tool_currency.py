"""Tests for the daily tool-currency signal (dotfiles_setup.tool_currency)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import tool_currency


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("github:ast-grep/ast-grep", "https://github.com/ast-grep/ast-grep/releases"),
        ("aqua:jackchuka/mdschema", "https://github.com/jackchuka/mdschema/releases"),
        ("npm:@devcontainers/cli", "npmjs.com/package/@devcontainers/cli"),
        ("pipx:mcp2cli", "pypi.org/project/mcp2cli"),
        ("cargo:rtk", "crates.io/crates/rtk"),
        ("hk", "mise.jdx.dev/registry.html"),
    ],
)
def test_release_link_per_backend(key: str, expected: str) -> None:
    assert expected in tool_currency.release_link(key)


def test_render_report_empty_is_all_current() -> None:
    report = tool_currency.render_report({})
    assert "current" in report
    assert "|" not in report


def test_render_report_rows_and_links() -> None:
    outdated = {
        "hk": {"current": "1.49.0", "latest": "1.50.1"},
        "github:agent-sh/agnix": {"current": "0.36.2", "latest": "0.37.0"},
    }
    report = tool_currency.render_report(outdated)
    assert "| `hk` | 1.49.0 | 1.50.1 |" in report
    assert "https://github.com/agent-sh/agnix/releases" in report
    assert "2 tool(s)" in report
    assert "tool-currency-check" in report


def test_render_report_tolerates_missing_fields() -> None:
    report = tool_currency.render_report({"x": {}})
    assert "| `x` | ? | ? |" in report
