"""Tests for the local Renovate dry-run (dotfiles_setup.renovate_dryrun).

The report fixtures below are trimmed from a REAL ``reportType=file`` payload
produced by npm:renovate 43.260.2 against this repo on 2026-07-15, so the
shape asserted here is renovate's own, not an invented one.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import renovate_dryrun
from dotfiles_setup.renovate_dryrun import DryRunResult, PendingUpdate

# Not a credential: an opaque sentinel whose only job is to survive being
# carried from one env name to another. Named for that role, not for what it
# imitates — it is neither a token nor a secret.
_SENTINEL = "ghp_not-a-real-value"

# An LLVM pin that resolved cleanly and is already current (updates: []), and
# an npm tool with a real pending bump — the same two shapes the live run
# produced. Keeping both in one fixture is the control arm: a parser that
# reported "nothing pending" for everything would still pass a fixture that
# only ever contained current pins.
_REPORT = {
    "problems": [],
    "repositories": {
        "local": {
            "problems": [],
            "packageFiles": {
                "regex": [
                    {
                        "packageFile": ".devcontainer/mise-system.toml",
                        "deps": [
                            {
                                "depName": "clang-22",
                                "currentValue": "1:22.1.8~++20260714015917",
                                "datasource": "deb",
                                "updates": [],
                            }
                        ],
                    }
                ],
                "mise": [
                    {
                        "packageFile": "mise.toml",
                        "deps": [
                            {
                                "depName": "npm:renovate",
                                "currentValue": "43.260.2",
                                "datasource": "npm",
                                "updates": [{"newValue": "43.264.2"}],
                            }
                        ],
                    }
                ],
            },
        }
    },
}


def test_parse_report_counts_every_dep() -> None:
    result = renovate_dryrun.parse_report(json.dumps(_REPORT))
    assert result.total_deps == 2


def test_parse_report_extracts_only_pending_updates() -> None:
    result = renovate_dryrun.parse_report(json.dumps(_REPORT))
    assert len(result.updates) == 1
    upd = result.updates[0]
    assert upd.dep_name == "npm:renovate"
    assert upd.current_value == "43.260.2"
    assert upd.new_value == "43.264.2"
    assert upd.manager == "mise"
    assert upd.package_file == "mise.toml"


def test_parse_report_ignores_current_pins() -> None:
    # clang-22 resolved with updates: [] — it must NOT appear as pending.
    result = renovate_dryrun.parse_report(json.dumps(_REPORT))
    assert all(u.dep_name != "clang-22" for u in result.updates)


def test_parse_report_empty_repo() -> None:
    result = renovate_dryrun.parse_report(json.dumps({"repositories": {}}))
    assert result.total_deps == 0
    assert result.updates == []


def test_exit_code_bare_run_is_always_zero() -> None:
    result = renovate_dryrun.parse_report(json.dumps(_REPORT))
    assert result.updates, "fixture must carry drift for this test to mean anything"
    assert renovate_dryrun.decide_exit_code(result, check=False) == 0


def test_exit_code_check_fails_on_pending_update() -> None:
    result = renovate_dryrun.parse_report(json.dumps(_REPORT))
    assert renovate_dryrun.decide_exit_code(result, check=True) == 1


def test_exit_code_check_passes_when_current() -> None:
    clean = DryRunResult(total_deps=2, updates=[], problems=[])
    assert renovate_dryrun.decide_exit_code(clean, check=True) == 0


def test_force_disables_clone_submodules() -> None:
    """The #290 fix: the preset's cloneSubmodules=true must be forced off.

    RENOVATE_FORCE is the only layer applied after repo config, so this env
    var — not RENOVATE_CLONE_SUBMODULES — is what keeps syncGit() unreached.
    """
    report = Path(tempfile.gettempdir()) / "report.json"
    env = renovate_dryrun.renovate_env(report)
    assert json.loads(env["RENOVATE_FORCE"]) == {"cloneSubmodules": False}
    assert env["RENOVATE_REPORT_TYPE"] == "file"
    assert env["RENOVATE_REPORT_PATH"] == str(report)


def test_dry_run_mode_is_lookup_not_full() -> None:
    """platform=local coerces every non-extract mode to lookup anyway.

    Asking for `full` made the task claim something renovate never did; the
    args must stay honest about the mode that actually runs.
    """
    assert "--dry-run=lookup" in renovate_dryrun.RENOVATE_ARGS
    assert "--platform=local" in renovate_dryrun.RENOVATE_ARGS
    assert not any("full" in a for a in renovate_dryrun.RENOVATE_ARGS)


def test_token_resolution_prefers_the_explicit_renovate_name() -> None:
    env = {"GITHUB_TOKEN": "ghp_conventional", "GITHUB_COM_TOKEN": "ghp_explicit"}
    assert renovate_dryrun.resolve_github_token(env) == "ghp_explicit"


def test_token_resolution_falls_back_to_conventional_env() -> None:
    # The real shell on this Mac exports GITHUB_TOKEN but not GITHUB_COM_TOKEN;
    # renovate DELETES the former from its own env, so the fallback is what
    # makes an already-present credential usable at all.
    assert renovate_dryrun.resolve_github_token({"GITHUB_TOKEN": "ghp_x"}) == "ghp_x"
    assert (
        renovate_dryrun.resolve_github_token({"MISE_GITHUB_TOKEN": "ghp_m"}) == "ghp_m"
    )


def test_token_resolution_ignores_the_mcp_pat() -> None:
    # GITHUB_MCP_PAT is scoped to the MCP server; it is not ours to spend here.
    assert renovate_dryrun.resolve_github_token({"GITHUB_MCP_PAT": "ghp_mcp"}) is None


def test_token_resolution_treats_empty_as_absent() -> None:
    assert renovate_dryrun.resolve_github_token({"GITHUB_TOKEN": ""}) is None
    assert renovate_dryrun.resolve_github_token({}) is None


def test_env_promotes_token_to_the_name_renovate_reads() -> None:
    report = Path(tempfile.gettempdir()) / "r.json"
    env = renovate_dryrun.renovate_env(report, {"GITHUB_TOKEN": _SENTINEL})
    assert env["GITHUB_COM_TOKEN"] == _SENTINEL


def test_env_omits_token_when_none_available() -> None:
    report = Path(tempfile.gettempdir()) / "r.json"
    env = renovate_dryrun.renovate_env(report, {"PATH": "/usr/bin"})
    assert "GITHUB_COM_TOKEN" not in env


def test_incomplete_run_is_labelled_a_floor_not_a_total() -> None:
    """An untokened run must never print a bare authoritative total.

    Control arm: the same result rendered as complete says "8 would be
    updated"; as incomplete it must say INCOMPLETE and "at least". A renderer
    that ignored `complete` would pass the first assertion alone.
    """
    result = renovate_dryrun.parse_report(json.dumps(_REPORT), complete=False)
    out = renovate_dryrun.render_report(result)
    assert "INCOMPLETE" in out
    assert "FLOOR, not a total" in out
    assert "at least 1 would be updated" in out
    assert "GITHUB_COM_TOKEN" in out


def test_complete_run_has_no_incomplete_warning() -> None:
    result = renovate_dryrun.parse_report(json.dumps(_REPORT), complete=True)
    out = renovate_dryrun.render_report(result)
    assert "INCOMPLETE" not in out
    assert "at least" not in out
    assert "Scanned 2 deps; 1 would be updated." in out


def test_render_report_lists_the_change() -> None:
    result = renovate_dryrun.parse_report(json.dumps(_REPORT))
    out = renovate_dryrun.render_report(result)
    assert "Scanned 2 deps; 1 would be updated." in out
    assert "npm:renovate: 43.260.2 -> 43.264.2" in out


def test_render_report_when_nothing_pending() -> None:
    clean = DryRunResult(total_deps=217, updates=[], problems=[])
    out = renovate_dryrun.render_report(clean)
    assert "Scanned 217 deps; 0 would be updated." in out


def test_pending_update_render_includes_manager_and_file() -> None:
    upd = PendingUpdate(
        manager="regex",
        package_file=".devcontainer/Dockerfile",
        dep_name="gcc-latest",
        current_value="17.0.0-20260705",
        new_value="17.0.0-20260712",
    )
    row = upd.render()
    assert "[regex]" in row
    assert "gcc-latest: 17.0.0-20260705 -> 17.0.0-20260712" in row
    assert ".devcontainer/Dockerfile" in row
