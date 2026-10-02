# Copyright (c) 2026 Raymond Manaloto
"""Tests for the project doctor (dotfiles_setup.doctor, #418).

**Every check is armed in both directions.** A doctor check that has only ever
passed is decoration (`probes-need-a-control-arm.md`), and a doctor is
particularly exposed to that failure: it reads the operator's live host state, so
the tempting way to "verify" it is to run it once against a healthy machine and
believe the silence. That proves nothing. Each check here gets a fixture it must
flag and a fixture it must stay silent on.

The fixtures are synthetic ``Setup`` objects, never the real ``$HOME``. That is
not only hygiene: half the doctor's inputs are the operator's credential config,
and a test that read it would pass or fail depending on whose machine ran it.
"""

from __future__ import annotations

import dataclasses
import json
import re
import subprocess
import sys
from fnmatch import fnmatchcase
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import doctor
from dotfiles_setup import path_drift as doctor_path_drift
from dotfiles_setup.graphify_currency import Drift

REPO_ROOT = Path(__file__).parent.parent

#: Raised by the fail-open fixtures; a literal in a `raise` trips EM101.
_CRASH_MESSAGE = "kaboom"
_SPAWN_ERROR_MESSAGE = "cannot spawn"


@pytest.fixture(autouse=True)
def healthy_graphify_currency(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep unrelated doctor checks independent of host Graphify state."""
    monkeypatch.setattr(
        doctor,
        "graphify_currency_check",
        lambda _root, *, offline: () if offline else pytest.fail("doctor went online"),
    )


# A baseline mirroring the shipped doctor.toml closely enough that a check
# reading it behaves as it does in production.
_BASELINE: dict[str, object] = {
    "fnox": {"env": "exec", "env_true": ["EXA_API_KEY"]},
    "mcp": {
        "scope_servers": ["filesystem"],
        "mutating_tools": {"filesystem": ["write_file"]},
    },
}


def _fnox(
    *,
    env_mode: object = "exec",
    per_secret: dict[str, object] | None = None,
    sync_blocks: int = 1,
) -> doctor.FnoxState:
    return doctor.FnoxState(
        exists=True,
        env_mode=env_mode,
        per_secret=per_secret if per_secret is not None else {"EXA_API_KEY": True},
        sync_blocks=sync_blocks,
    )


def _setup(**overrides: object) -> doctor.Setup:
    """A default-healthy ``Setup`` with the named fields replaced.

    Built by ``dataclasses.replace`` rather than a long keyword list so a test
    states only the field it is about — the rest stay at a shape that passes.
    """
    base = doctor.Setup(
        repo_root=Path("/repo"),
        baseline=_BASELINE,
        servers=(),
        settings={},
        local_settings={},
        fnox=_fnox(),
        environ={},
    )
    return dataclasses.replace(base, **overrides)


def _server(
    name: str = "srv",
    origin: str = "project",
    **config: object,
) -> doctor.Server:
    return doctor.Server(name=name, origin=origin, config=config)


# --------------------------------------------------------------------------- #
# check 1 — mcp-env-opt-in
# --------------------------------------------------------------------------- #


def test_env_opt_in_flags_an_interpolation_that_resolves_empty() -> None:
    """The context7 class: declared in fnox, exec-only, so the header is empty."""
    setup = _setup(
        servers=(_server("context7", headers={"Authorization": "${C7_KEY:-}"}),),
        fnox=_fnox(per_secret={"C7_KEY": None}),
        environ={},
    )
    findings = doctor.check_mcp_env_opt_in(setup)
    assert len(findings) == 1
    assert "C7_KEY" in findings[0]
    assert "exec-only" in findings[0]


def test_env_opt_in_is_silent_when_the_variable_is_set() -> None:
    """The control arm: the same config, with the variable actually present."""
    setup = _setup(
        servers=(_server("context7", headers={"Authorization": "${C7_KEY:-}"}),),
        fnox=_fnox(per_secret={"C7_KEY": True}),
        environ={"C7_KEY": "sk-whatever"},
    )
    assert doctor.check_mcp_env_opt_in(setup) == []


def test_env_opt_in_flags_an_empty_string_as_absent() -> None:
    """An exported-but-empty variable is the same silent downgrade as unset."""
    setup = _setup(
        servers=(_server("context7", headers={"Authorization": "${C7_KEY:-}"}),),
        environ={"C7_KEY": ""},
    )
    assert len(doctor.check_mcp_env_opt_in(setup)) == 1


def test_env_opt_in_explains_a_variable_fnox_never_heard_of() -> None:
    """The two absences need different fixes, so they must read differently."""
    setup = _setup(
        servers=(_server("s", env={"NOPE": "${NOPE}"}),),
        fnox=_fnox(per_secret={}),
        environ={},
    )
    assert "does not declare NOPE at all" in doctor.check_mcp_env_opt_in(setup)[0]


def test_env_opt_in_exempts_harness_substituted_path_placeholders() -> None:
    """Claude Code resolves these itself, so the doctor's env cannot speak to them.

    The live shape: context7's `.mcp.json` headersHelper is
    `node "${CLAUDE_PLUGIN_ROOT}/scripts/headers.mjs"`. Before the exemption,
    enabling that plugin produced permanent drift from a `mise run doctor`
    child, which no plugin provides and which therefore never has the variable.
    """
    setup = _setup(
        servers=(
            _server(
                "context7",
                headersHelper='node "${CLAUDE_PLUGIN_ROOT}/scripts/headers.mjs"',
            ),
        ),
        fnox=_fnox(per_secret={}),
        environ={},
    )
    assert doctor.check_mcp_env_opt_in(setup) == []


def test_env_opt_in_still_flags_a_credential_beside_a_placeholder() -> None:
    """The FAIL arm: exempting paths must not exempt the secret next to them.

    Same server, same absent environment. If this ever returns [] the exemption
    has widened past paths and the check has become one that can only pass.
    """
    setup = _setup(
        servers=(
            _server(
                "context7",
                headersHelper='node "${CLAUDE_PLUGIN_ROOT}/scripts/headers.mjs"',
                headers={"Authorization": "${C7_KEY:-}"},
            ),
        ),
        fnox=_fnox(per_secret={}),
        environ={},
    )
    findings = doctor.check_mcp_env_opt_in(setup)
    assert len(findings) == 1
    assert "C7_KEY" in findings[0]
    assert "CLAUDE_PLUGIN_ROOT" not in findings[0]


def test_interpolations_finds_both_plain_and_defaulted_forms() -> None:
    config = {"env": {"A": "${A}", "B": "${B:-fallback}"}, "url": "https://x/${C}"}
    assert doctor.interpolations(config) == {"A", "B", "C"}


# --------------------------------------------------------------------------- #
# check 2 — mcp-scope
# --------------------------------------------------------------------------- #


def test_scope_flags_a_declaration_the_roots_replace() -> None:
    """The filesystem class: one declared directory, two effective roots."""
    setup = _setup(
        repo_root=Path("/repo"),
        servers=(_server("filesystem", args=["-y", "pkg", "/repo"]),),
        local_settings={"permissions": {"additionalDirectories": ["/other"]}},
    )
    findings = doctor.check_mcp_scope(setup)
    assert len(findings) == 1
    assert "roots REPLACE" in findings[0]
    assert "/other" in findings[0]


def test_scope_is_silent_when_the_declaration_matches_the_roots() -> None:
    setup = _setup(
        repo_root=Path("/repo"),
        servers=(_server("filesystem", args=["-y", "pkg", "/repo", "/other"]),),
        local_settings={"permissions": {"additionalDirectories": ["/other"]}},
    )
    assert doctor.check_mcp_scope(setup) == []


def test_scope_flags_a_baseline_entry_for_an_unregistered_server() -> None:
    """A stale baseline is drift too — otherwise the check silently covers nothing."""
    findings = doctor.check_mcp_scope(_setup(servers=()))
    assert len(findings) == 1
    assert "stale" in findings[0]


def test_scope_ignores_a_server_the_baseline_does_not_name() -> None:
    """Only scope-bearing servers are compared — a plain one declares no scope."""
    setup = _setup(
        servers=(
            _server("filesystem", args=["-y", "pkg", "/repo"]),
            _server("memory", args=["-y", "mem"]),
        ),
    )
    assert doctor.check_mcp_scope(setup) == []


# --------------------------------------------------------------------------- #
# check 3 — fnox-baseline
# --------------------------------------------------------------------------- #


def test_fnox_baseline_flags_a_wiped_env_mode() -> None:
    """`bootstrap-config` drops the global mode; that is the whole tripwire."""
    setup = _setup(fnox=_fnox(env_mode=True))
    findings = doctor.check_fnox_baseline(setup)
    assert any("bootstrap-config" in f for f in findings)


def test_fnox_baseline_is_silent_on_the_sanctioned_state() -> None:
    assert doctor.check_fnox_baseline(_setup()) == []


def test_fnox_baseline_flags_an_unsanctioned_opt_in() -> None:
    """A credential newly visible to every child process is drift, not a detail."""
    setup = _setup(fnox=_fnox(per_secret={"EXA_API_KEY": True, "AWS_SECRET": True}))
    findings = doctor.check_fnox_baseline(setup)
    assert any("AWS_SECRET" in f and "does not sanction" in f for f in findings)


def test_fnox_baseline_flags_a_lost_opt_in() -> None:
    """The reverse: something reads it from the env and will now degrade silently."""
    setup = _setup(fnox=_fnox(per_secret={"EXA_API_KEY": "exec"}))
    findings = doctor.check_fnox_baseline(setup)
    assert any("EXA_API_KEY" in f and "SILENT" in f for f in findings)


def test_fnox_baseline_flags_a_config_with_no_sync_blocks() -> None:
    """A swap keeps the opt-in set; the missing sync blocks are the other signature."""
    setup = _setup(fnox=_fnox(sync_blocks=0))
    findings = doctor.check_fnox_baseline(setup)
    assert any("not one `sync` block" in f for f in findings)


def test_fnox_baseline_reports_an_unreadable_config_rather_than_passing() -> None:
    setup = _setup(fnox=doctor.FnoxState(exists=True, error="boom"))
    assert doctor.check_fnox_baseline(setup) == ["fnox config unreadable: boom"]


def test_fnox_baseline_flags_a_missing_baseline_section() -> None:
    """No baseline must not read as "nothing to check"."""
    findings = doctor.check_fnox_baseline(_setup(baseline={}))
    assert findings == ["doctor.toml has no [fnox] section to check against"]


# --------------------------------------------------------------------------- #
# check — fnox-exec-leak (2026-08-29c)
# --------------------------------------------------------------------------- #


def test_exec_leak_flags_an_exec_only_secret_present_in_the_live_environ() -> None:
    """The CLAUDE_CODE_OAUTH_TOKEN class: env="exec", but a stale process kept it."""
    setup = _setup(
        fnox=_fnox(per_secret={"EXA_API_KEY": True, "CLAUDE_CODE_OAUTH_TOKEN": "exec"}),
        environ={"CLAUDE_CODE_OAUTH_TOKEN": "sk-stale"},
    )
    findings = doctor.check_exec_only_not_leaked(setup)
    assert len(findings) == 1
    assert "CLAUDE_CODE_OAUTH_TOKEN" in findings[0]
    assert "exec" in findings[0]


def test_exec_leak_is_silent_when_the_exec_only_secret_is_absent() -> None:
    """The control arm: same config, but the variable genuinely absent."""
    setup = _setup(
        fnox=_fnox(per_secret={"EXA_API_KEY": True, "CLAUDE_CODE_OAUTH_TOKEN": "exec"}),
        environ={},
    )
    assert doctor.check_exec_only_not_leaked(setup) == []


def test_exec_leak_ignores_a_shell_true_secret_present_in_the_environ() -> None:
    """A `env = true` secret is SUPPOSED to be ambient — not this check's concern."""
    setup = _setup(
        fnox=_fnox(per_secret={"EXA_API_KEY": True}),
        environ={"EXA_API_KEY": "sk-fine"},
    )
    assert doctor.check_exec_only_not_leaked(setup) == []


@pytest.mark.parametrize(
    ("env_mode", "per_secret", "expected"),
    [
        # No per-secret field: the global mode decides. ⚠️ `{}` is a shape
        # `read_fnox` NEVER produces — it stores `fields.get("env")`, so a
        # declaration without the field arrives as an explicit `None`. These
        # rows passed while that real shape was broken; the `None` rows below
        # are the ones with teeth.
        (True, {}, True),
        ("exec", {}, False),
        (False, {}, False),
        # The REAL shape from `read_fnox`: key present, value None => inherit.
        (True, {"V": None}, True),
        ("exec", {"V": None}, False),
        (False, {"V": None}, False),
        # A per-secret field overrides the global mode, in both directions.
        ("exec", {"V": True}, True),
        (True, {"V": "exec"}, False),
        (True, {"V": False}, False),
    ],
)
def test_shell_visible_covers_every_tri_state_combination(
    env_mode: object, per_secret: dict[str, object], *, expected: bool
) -> None:
    """The `env` field is tri-state, and per-secret overrides global."""
    state = doctor.FnoxState(exists=True, env_mode=env_mode, per_secret=per_secret)
    assert state.shell_visible("V") is expected


def test_read_fnox_parses_env_fields_and_sync_coverage(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        'env = "exec"\n'
        "[secrets]\n"
        'A = { provider = "p", value = "A", sync = { provider = "age" } }\n'
        'B = { provider = "p", value = "B", env = true }\n'
    )
    state = doctor.read_fnox(config)
    assert state.exists
    assert state.env_mode == "exec"
    assert state.sync_blocks == 1
    assert state.shell_visible("B")
    assert not state.shell_visible("A")


def test_read_fnox_reports_a_missing_file_rather_than_inventing_a_default(
    tmp_path: Path,
) -> None:
    state = doctor.read_fnox(tmp_path / "absent.toml")
    assert not state.exists
    assert state.error is not None


def test_read_fnox_never_retains_a_secret_value(tmp_path: Path) -> None:
    """The state object must be safe to print; only names may appear in findings."""
    config = tmp_path / "config.toml"
    config.write_text(
        '[secrets]\nA = { provider = "p", value = "super-secret-material" }\n'
    )
    state = doctor.read_fnox(config)
    assert "super-secret-material" not in repr(state)


# --------------------------------------------------------------------------- #
# check 4 — mcp-pin
# --------------------------------------------------------------------------- #


def test_pin_flags_an_unpinned_npx_spec() -> None:
    setup = _setup(servers=(_server("exa", command="npx", args=["-y", "exa-mcp"]),))
    findings = doctor.check_mcp_pin(setup)
    assert len(findings) == 1
    assert "exa-mcp@<version>" in findings[0]


def test_pin_is_silent_on_a_pinned_spec() -> None:
    setup = _setup(
        servers=(_server("exa", command="npx", args=["-y", "exa-mcp@3.2.1"]),)
    )
    assert doctor.check_mcp_pin(setup) == []


def test_pin_is_silent_on_a_pinned_scoped_spec() -> None:
    """`@scope/pkg` has a leading `@` that must not read as a version."""
    setup = _setup(
        servers=(_server("fs", command="npx", args=["-y", "@mcp/server-fs@2026.7.10"]),)
    )
    assert doctor.check_mcp_pin(setup) == []


def test_pin_flags_an_unpinned_scoped_spec() -> None:
    setup = _setup(
        servers=(_server("fs", command="npx", args=["-y", "@mcp/server-fs"]),)
    )
    assert len(doctor.check_mcp_pin(setup)) == 1


def test_pin_ignores_directory_arguments_and_flags() -> None:
    """A path argument is not a package spec; flagging it would be noise."""
    setup = _setup(
        servers=(
            _server("fs", command="npx", args=["-y", "@mcp/server-fs@1.0.0", "/repo"]),
        )
    )
    assert doctor.check_mcp_pin(setup) == []


def test_pin_ignores_a_server_that_is_not_run_through_a_package_runner() -> None:
    """A pinned binary on PATH has no dist-tag to drift."""
    setup = _setup(servers=(_server("local", command="/usr/local/bin/srv", args=[]),))
    assert doctor.check_mcp_pin(setup) == []


def test_pin_ignores_an_http_server() -> None:
    """An HTTP server has no command to pin at all."""
    setup = _setup(servers=(_server("c7", type="http", url="https://x/mcp"),))
    assert doctor.check_mcp_pin(setup) == []


# --------------------------------------------------------------------------- #
# check 5 — mcp-guard-coverage
# --------------------------------------------------------------------------- #


def test_guard_coverage_flags_a_tool_with_no_decision_anywhere() -> None:
    setup = _setup(servers=(_server("filesystem"),))
    findings = doctor.check_mcp_guard_coverage(setup)
    assert len(findings) == 1
    assert "mcp__filesystem__write_file" in findings[0]
    assert "no permission rule" in findings[0]


def test_guard_coverage_is_silent_on_a_tracked_rule() -> None:
    setup = _setup(
        servers=(_server("filesystem"),),
        settings={"permissions": {"allow": ["mcp__filesystem__write_file"]}},
    )
    assert doctor.check_mcp_guard_coverage(setup) == []


def test_guard_coverage_accepts_a_deny_as_a_reviewed_decision() -> None:
    """The check is about the decision existing, not about it being permissive."""
    setup = _setup(
        servers=(_server("filesystem"),),
        settings={"permissions": {"deny": ["mcp__filesystem__write_file"]}},
    )
    assert doctor.check_mcp_guard_coverage(setup) == []


def test_guard_coverage_accepts_a_whole_server_rule() -> None:
    setup = _setup(
        servers=(_server("filesystem"),),
        settings={"permissions": {"ask": ["mcp__filesystem"]}},
    )
    assert doctor.check_mcp_guard_coverage(setup) == []


def test_guard_coverage_accepts_a_pretooluse_matcher_that_reaches_the_tool() -> None:
    setup = _setup(
        servers=(_server("filesystem"),),
        settings={"hooks": {"PreToolUse": [{"matcher": "mcp__filesystem__.*"}]}},
    )
    assert doctor.check_mcp_guard_coverage(setup) == []


def test_guard_coverage_rejects_a_matcher_that_does_not_reach_the_tool() -> None:
    """`Bash` is a real matcher in this repo and must not read as coverage."""
    setup = _setup(
        servers=(_server("filesystem"),),
        settings={"hooks": {"PreToolUse": [{"matcher": "Bash|Grep"}]}},
    )
    assert len(doctor.check_mcp_guard_coverage(setup)) == 1


def test_guard_coverage_survives_an_uncompilable_matcher() -> None:
    """A malformed regex must not crash the check into a fail-open."""
    setup = _setup(
        servers=(_server("filesystem"),),
        settings={"hooks": {"PreToolUse": [{"matcher": "([unclosed"}]}},
    )
    assert len(doctor.check_mcp_guard_coverage(setup)) == 1


def test_guard_coverage_distinguishes_a_local_only_rule() -> None:
    """A gitignored allow is standing policy nobody reviews — say so explicitly."""
    setup = _setup(
        servers=(_server("filesystem"),),
        local_settings={"permissions": {"allow": ["mcp__filesystem__write_file"]}},
    )
    findings = doctor.check_mcp_guard_coverage(setup)
    assert len(findings) == 1
    assert "gitignored" in findings[0]


def test_guard_coverage_flags_a_stale_baseline_server() -> None:
    findings = doctor.check_mcp_guard_coverage(_setup(servers=()))
    assert findings == [
        (
            "doctor.toml declares mutating tools for 'filesystem', which is not a "
            "registered MCP server — the entry is stale"
        )
    ]


# --------------------------------------------------------------------------- #
# check 6 — mcp-duplicate
# --------------------------------------------------------------------------- #


def test_duplicate_flags_a_name_registered_twice() -> None:
    setup = _setup(
        servers=(
            _server("context7", origin="project"),
            _server("context7", origin="plugin:context7@mkt"),
        )
    )
    findings = doctor.check_mcp_duplicate(setup)
    assert len(findings) == 1
    assert "registered 2 times" in findings[0]


def test_duplicate_is_silent_on_distinct_names() -> None:
    setup = _setup(
        servers=(_server("a", origin="project"), _server("b", origin="plugin:x@y"))
    )
    assert doctor.check_mcp_duplicate(setup) == []


# --------------------------------------------------------------------------- #
# check 7 — pin-currency-wired
# --------------------------------------------------------------------------- #


def test_pin_currency_flags_a_missing_sessionstart_hook() -> None:
    findings = doctor.check_pin_currency_wired(_setup(settings={}))
    assert any("tool-currency-check" in f for f in findings)


def test_pin_currency_is_silent_when_the_hook_is_wired() -> None:
    """Armed against the real dep being importable, which it is in this venv."""
    setup = _setup(
        settings={
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"command": "mise run tool-currency-check"}]}
                ]
            }
        }
    )
    assert doctor.check_pin_currency_wired(setup) == []


def test_pin_currency_notices_an_unimportable_delegate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The gap the existing text-grep contract cannot see: wired but unrunnable."""
    monkeypatch.setattr(doctor, "_CURRENCY_MODULE", "definitely_not_a_module")
    setup = _setup(
        settings={
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"command": "mise run tool-currency-check"}]}
                ]
            }
        }
    )
    findings = doctor.check_pin_currency_wired(setup)
    assert any("not importable" in f for f in findings)


# --------------------------------------------------------------------------- #
# The live arm
# --------------------------------------------------------------------------- #


_LIST_OUTPUT = """Secure MCP Filesystem Server running on stdio

Available tools:
  read-text-file        Read the complete contents...
  write-file            Create a new file...
  list-allowed-directories  Returns the list of directories...
"""


def test_parse_tool_list_unhyphenates_and_ignores_the_preamble() -> None:
    assert doctor.parse_tool_list(_LIST_OUTPUT) == {
        "read_text_file",
        "write_file",
        "list_allowed_directories",
    }


def test_looks_mutating_discriminates() -> None:
    assert doctor.looks_mutating("write_file")
    assert doctor.looks_mutating("delete_entities")
    assert not doctor.looks_mutating("read_text_file")
    assert not doctor.looks_mutating("list_allowed_directories")


def test_stdio_command_joins_the_spawn_line() -> None:
    server = _server("fs", command="npx", args=["-y", "pkg", "/repo"])
    assert doctor.stdio_command(server) == "npx -y pkg /repo"


def test_stdio_command_skips_an_http_server() -> None:
    assert doctor.stdio_command(_server("c7", type="http", url="https://x")) is None


def test_live_flags_an_undeclared_mutating_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The drift an unpinned `npx -y` makes possible: a new mutating tool appears."""
    monkeypatch.setattr(
        doctor, "probe_tools", lambda _cmd: ({"write_file", "delete_file"}, None)
    )
    setup = _setup(servers=(_server("filesystem", command="npx", args=["pkg"]),))
    findings = doctor.check_live_servers(setup)
    assert len(findings) == 1
    assert "delete_file" in findings[0]


def test_live_is_silent_when_the_tool_set_matches_the_baseline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        doctor, "probe_tools", lambda _cmd: ({"write_file", "read_text_file"}, None)
    )
    setup = _setup(servers=(_server("filesystem", command="npx", args=["pkg"]),))
    assert doctor.check_live_servers(setup) == []


def test_live_flags_a_baseline_tool_the_server_no_longer_offers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "probe_tools", lambda _cmd: ({"read_text_file"}, None))
    setup = _setup(servers=(_server("filesystem", command="npx", args=["pkg"]),))
    findings = doctor.check_live_servers(setup)
    assert any("no longer offers" in f for f in findings)


def test_live_surfaces_a_probe_failure_instead_of_reading_it_as_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A probe that never answered must not be mistaken for a probe that said no."""
    monkeypatch.setattr(doctor, "probe_tools", lambda _cmd: (set(), "probe timed out"))
    setup = _setup(servers=(_server("filesystem", command="npx", args=["pkg"]),))
    assert doctor.check_live_servers(setup) == [
        "live probe of MCP server 'filesystem': probe timed out"
    ]


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #


def test_enabled_plugin_ids_returns_only_enabled_and_lets_project_win() -> None:
    user = {"enabledPlugins": {"a@m": True, "b@m": True}}
    project = {"enabledPlugins": {"b@m": False, "c@m": True}}
    assert doctor.enabled_plugin_ids(user, project) == ["a@m", "c@m"]


def test_plugin_mcp_path_resolves_through_the_marketplace_manifest(
    tmp_path: Path,
) -> None:
    """A marketplace clone carries variants for other agents; only one is loaded."""
    root = tmp_path / ".claude" / "plugins" / "marketplaces" / "mkt"
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"plugins": [{"name": "c7", "source": "./plugins/claude/c7"}]})
    )
    wanted = root / "plugins" / "claude" / "c7"
    wanted.mkdir(parents=True)
    (wanted / ".mcp.json").write_text("{}")
    decoy = root / "plugins" / "codex" / "c7"
    decoy.mkdir(parents=True)
    (decoy / ".mcp.json").write_text("{}")
    assert doctor.plugin_mcp_path(tmp_path, "c7@mkt") == wanted / ".mcp.json"


def test_plugin_mcp_path_is_none_for_a_plugin_without_a_server(tmp_path: Path) -> None:
    assert doctor.plugin_mcp_path(tmp_path, "nothing@nowhere") is None


def test_servers_from_records_provenance() -> None:
    config = {"mcpServers": {"a": {"command": "x"}, "b": {"command": "y"}}}
    servers = doctor.servers_from(config, "project")
    assert [s.name for s in servers] == ["a", "b"]
    assert {s.origin for s in servers} == {"project"}


def test_load_json_tolerates_a_malformed_file(tmp_path: Path) -> None:
    """Externally-authored config must never crash collection into a fail-open."""
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert doctor.load_json(bad) == {}


# --------------------------------------------------------------------------- #
# Runner: fail-open, exit codes, rendering
# --------------------------------------------------------------------------- #


def test_a_crashed_check_is_recorded_and_surfaced_not_raised(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail open, but LOUDLY — a doctor that quietly stops checking is worse."""

    def _boom(_setup: doctor.Setup) -> list[str]:
        raise RuntimeError(_CRASH_MESSAGE)

    log = tmp_path / "doctor-error.log"
    monkeypatch.setattr(doctor, "CHECKS", (("exploder", _boom),))
    results = doctor.run_checks(_setup(), log_path=log)
    assert results == [
        ("exploder", [f"check crashed (RuntimeError: kaboom) — see {log}"])
    ]
    assert "exploder" in log.read_text()
    assert "kaboom" in log.read_text()


def test_a_crash_survives_an_unwritable_log(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bookkeeping failure must not turn a fail-open into a crash."""

    def _boom(_setup: doctor.Setup) -> list[str]:
        raise RuntimeError(_CRASH_MESSAGE)

    monkeypatch.setattr(doctor, "CHECKS", (("exploder", _boom),))
    results = doctor.run_checks(_setup(), log_path=Path("/proc/nope/doctor.log"))
    assert len(results) == 1


def test_live_checks_only_run_when_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    """A subprocess spawn per server must stay off the per-session path."""
    monkeypatch.setattr(doctor, "CHECKS", ())
    monkeypatch.setattr(doctor, "LIVE_CHECKS", (("live", lambda _s: ["found"]),))
    assert doctor.run_checks(_setup()) == []
    assert doctor.run_checks(_setup(), live=True) == [("live", ["found"])]


def test_render_is_completely_silent_when_healthy() -> None:
    """Silent when healthy is the contract: no news, not a reassuring line."""
    assert doctor.render([("a", []), ("b", [])]) == []


def test_render_prints_pass_lines_only_when_verbose() -> None:
    lines = doctor.render([("a", [])], verbose=True)
    assert lines == [
        "PASS  doctor[a]",
        "doctor: OK — the declared setup matches this host",
    ]


def test_render_tags_every_finding_with_its_check_name() -> None:
    lines = doctor.render([("a", ["x", "y"])])
    assert lines[0] == "DRIFT doctor[a]: x"
    assert lines[1] == "DRIFT doctor[a]: y"
    assert "2 finding(s)" in lines[2]


def test_doctor_main_exits_zero_on_findings_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The SessionStart hook must never be able to disrupt a session."""
    monkeypatch.setattr(doctor, "CHECKS", (("a", lambda _s: ["drift"]),))
    assert doctor.doctor_main(REPO_ROOT) == 0


def test_doctor_main_exits_one_on_findings_under_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "CHECKS", (("a", lambda _s: ["drift"]),))
    assert doctor.doctor_main(REPO_ROOT, strict=True) == 1


def test_doctor_main_exits_zero_when_clean_under_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "CHECKS", (("a", lambda _s: []),))
    assert doctor.doctor_main(REPO_ROOT, strict=True) == 0


# --------------------------------------------------------------------------- #
# The shipped baseline and wiring
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# The full registration surface + health (the #418 follow-up)
# --------------------------------------------------------------------------- #


def test_claude_json_servers_reads_user_global_and_per_project(tmp_path: Path) -> None:
    """The surface the first version missed, which cost it its own defect class."""
    (tmp_path / ".claude.json").write_text(
        json.dumps(
            {
                "mcpServers": {"context7": {"command": "/bin/mde-mcp-context7"}},
                "projects": {
                    "/repo": {"mcpServers": {"pkgsearch": {"url": "https://x/mcp"}}},
                    "/elsewhere": {"mcpServers": {"nope": {"command": "x"}}},
                },
            }
        )
    )
    servers = doctor.claude_json_servers(tmp_path, Path("/repo"))
    assert {(s.name, s.origin) for s in servers} == {
        ("context7", "user"),
        ("pkgsearch", "project-local"),
    }


def test_claude_json_servers_is_empty_without_the_file(tmp_path: Path) -> None:
    assert doctor.claude_json_servers(tmp_path, Path("/repo")) == []


def test_collect_servers_actually_includes_the_claude_json_source(
    tmp_path: Path,
) -> None:
    """Binds the CALL SITE, because the function alone is not the wiring.

    Found by mutation: deleting the ``claude_json_servers`` call from
    ``collect_servers`` left the whole suite green — every other test injects
    ``servers`` into a synthetic ``Setup``, so nothing exercised collection. Only
    the contract caught it, and a contract is not a test. This is the same
    stand-in shape as `test_every_check_function_is_actually_registered`.
    """
    (tmp_path / ".claude.json").write_text(
        json.dumps({"mcpServers": {"stale-wrapper": {"command": "/bin/mde-mcp-x"}}})
    )
    servers = doctor.collect_servers(REPO_ROOT, tmp_path)
    assert "stale-wrapper" in {s.name for s in servers}
    assert {s.origin for s in servers if s.name == "stale-wrapper"} == {"user"}


def test_duplicate_now_sees_a_user_global_shadow() -> None:
    """The live miss: a same-name user entry SHADOWS the project one, and won."""
    setup = _setup(
        servers=(
            _server("filesystem", origin="project"),
            _server("filesystem", origin="user"),
        )
    )
    findings = doctor.check_mcp_duplicate(setup)
    assert len(findings) == 1
    assert "project, user" in findings[0]


@pytest.mark.parametrize(
    ("origin", "owned"),
    [
        ("project", True),
        ("plugin:context7@context7-marketplace", True),
        ("user", False),
        ("project-local", False),
    ],
)
def test_repo_owned_splits_by_origin(origin: str, *, owned: bool) -> None:
    """The boundary that keeps output readable — both directions."""
    assert _server("s", origin=origin).repo_owned is owned


def test_pin_ignores_a_user_global_registration() -> None:
    """Not this repo's pin to fix; flagging it is noise it cannot act on."""
    setup = _setup(
        servers=(_server("x", origin="user", command="npx", args=["-y", "unpinned"]),)
    )
    assert doctor.check_mcp_pin(setup) == []


def test_pin_still_flags_the_same_server_when_the_project_owns_it() -> None:
    """The control arm for the line above — the scoping must not disable the check."""
    setup = _setup(
        servers=(
            _server("x", origin="project", command="npx", args=["-y", "unpinned"]),
        )
    )
    assert len(doctor.check_mcp_pin(setup)) == 1


def test_live_tools_ignores_a_user_global_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The MCP_DOCKER flood: 32 findings about a gateway the repo cannot fix."""
    monkeypatch.setattr(
        doctor, "probe_tools", lambda _cmd: ({"create_repository"}, None)
    )
    setup = _setup(
        servers=(_server("MCP_DOCKER", origin="user", command="/bin/x", args=[]),)
    )
    assert doctor.check_live_servers(setup) == []


def test_scope_reports_a_server_that_declares_no_scope_distinctly() -> None:
    """A wrapper taking no path argument is unbounded, not wrongly declared."""
    setup = _setup(servers=(_server("filesystem", origin="project", args=["-y", "p"]),))
    findings = doctor.check_mcp_scope(setup)
    assert len(findings) == 1
    assert "declares no scope at all" in findings[0]


#: Real captured `claude mcp list` output (2026-07-30), one row of each status
#: kind. Pinned verbatim: the command has NO `--json`, so the parser is only as
#: trustworthy as this fixture.
_MCP_LIST_OUTPUT = """Checking MCP server health…

claude.ai Google Drive: https://drivemcp.googleapis.com/mcp/v1 - ✔ Connected
claude.ai Asana: https://mcp.asana.com/sse - ! Needs authentication
plugin:context7:context7: https://mcp.context7.com/mcp (HTTP) - ✔ Connected
context7: /Users/x/.local/bin/mde-mcp-context7  - ✘ Failed to connect \
— -32000: MCP error -32000: Connection closed
exa: npx -y exa-mcp-server@3.2.1 - ⏸ Pending approval (run `claude` to approve)
"""


def test_parse_mcp_list_reads_every_status_kind() -> None:
    rows = doctor.parse_mcp_list(_MCP_LIST_OUTPUT)
    by_name = {r.name: r for r in rows}
    assert by_name["claude.ai Google Drive"].healthy
    assert by_name["plugin:context7:context7"].healthy
    assert not by_name["claude.ai Asana"].healthy
    assert not by_name["context7"].healthy
    assert not by_name["exa"].healthy
    assert by_name["exa"].target == "npx -y exa-mcp-server@3.2.1"


def test_parse_mcp_list_ignores_the_preamble() -> None:
    """A banner line must not become a phantom server."""
    names = {r.name for r in doctor.parse_mcp_list(_MCP_LIST_OUTPUT)}
    assert not any("Checking MCP server health" in n for n in names)


def test_health_reports_a_failure_and_names_repo_ownership(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda _c: "/usr/bin/claude")
    monkeypatch.setattr(
        doctor,
        "parse_mcp_list",
        lambda _s: [
            doctor.ServerHealth(
                "context7", "x", "Failed to connect — closed", healthy=False
            )
        ],
    )
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess([], 0, _MCP_LIST_OUTPUT, ""),
    )
    setup = _setup(servers=(_server("context7", origin="project"),))
    findings = doctor.check_mcp_health(setup)
    assert len(findings) == 1
    assert "does not connect" in findings[0]
    assert "This repo registers it." in findings[0]


def test_health_is_silent_when_everything_connects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda _c: "/usr/bin/claude")
    monkeypatch.setattr(
        doctor,
        "parse_mcp_list",
        lambda _s: [doctor.ServerHealth("a", "x", "Connected", healthy=True)],
    )
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess([], 0, "out", ""),
    )
    assert doctor.check_mcp_health(_setup()) == []


@pytest.mark.parametrize(
    "status", ["Pending approval (run `claude` to approve)", "Needs authentication"]
)
def test_health_words_a_consent_state_as_waiting_not_broken(status: str) -> None:
    """Sending you to debug something that needs a click is how a doctor loses trust."""
    row = doctor.ServerHealth("exa", "x", status, healthy=False)
    finding = doctor.health_finding(row, owned=True)
    assert "waiting on you, not broken" in finding
    assert "`/mcp`" in finding


def test_health_says_so_when_the_output_stops_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A report the parser cannot read must not come out as "all healthy"."""
    monkeypatch.setattr(doctor.shutil, "which", lambda _c: "/usr/bin/claude")
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess([], 0, "totally new format", ""),
    )
    findings = doctor.check_mcp_health(_setup())
    assert len(findings) == 1
    assert "output format" in findings[0]


def test_health_reports_a_missing_claude_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor.shutil, "which", lambda _c: None)
    assert doctor.check_mcp_health(_setup()) == [
        "`claude` is not on PATH, so server health cannot be checked"
    ]


# --------------------------------------------------------------------------- #
# check 11 — graphify-skill-surface
# --------------------------------------------------------------------------- #

_GRAPHIFY_BASELINE: dict[str, object] = {
    "required_skill_files": [
        ".claude/skills/graphify/SKILL.md",
        ".agents/skills/graphify/SKILL.md",
    ],
    "stub_file": ".agents/skills/graphify/SKILL.md",
    "stub_marker": "DELIBERATE STUB",
    "forbidden_agents_md_marker": "use the installed graphify skill",
}


def _write_healthy_graphify_surface(repo_root: Path) -> None:
    claude_skill = repo_root / ".claude" / "skills" / "graphify" / "SKILL.md"
    claude_skill.parent.mkdir(parents=True)
    claude_skill.write_text("full installed bundle")
    agents_skill = repo_root / ".agents" / "skills" / "graphify" / "SKILL.md"
    agents_skill.parent.mkdir(parents=True)
    agents_skill.write_text("<!-- DELIBERATE STUB: hand-authored redirect -->")
    (repo_root / "AGENTS.md").write_text("ordinary project instructions\n")


def test_graphify_skill_surface_flags_a_missing_required_file(tmp_path: Path) -> None:
    (tmp_path / ".agents" / "skills" / "graphify").mkdir(parents=True)
    (tmp_path / ".agents" / "skills" / "graphify" / "SKILL.md").write_text(
        "DELIBERATE STUB"
    )
    setup = _setup(repo_root=tmp_path, baseline={"graphify": _GRAPHIFY_BASELINE})
    findings = doctor.check_graphify_skill_surface(setup)
    assert len(findings) == 1
    assert ".claude/skills/graphify/SKILL.md" in findings[0]


def test_graphify_skill_surface_is_silent_on_the_reviewed_shape(
    tmp_path: Path,
) -> None:
    _write_healthy_graphify_surface(tmp_path)
    setup = _setup(repo_root=tmp_path, baseline={"graphify": _GRAPHIFY_BASELINE})
    assert doctor.check_graphify_skill_surface(setup) == []


def test_graphify_skill_surface_flags_a_stub_that_lost_its_marker(
    tmp_path: Path,
) -> None:
    _write_healthy_graphify_surface(tmp_path)
    (tmp_path / ".agents" / "skills" / "graphify" / "SKILL.md").write_text(
        "no marker here"
    )
    setup = _setup(repo_root=tmp_path, baseline={"graphify": _GRAPHIFY_BASELINE})
    findings = doctor.check_graphify_skill_surface(setup)
    assert len(findings) == 1
    assert "DELIBERATE STUB" in findings[0]


def test_graphify_skill_surface_is_silent_on_an_adopted_codex_install(
    tmp_path: Path,
) -> None:
    """`.codex/skills/graphify` is adopted (2026-08-31) — presence is fine.

    Until 2026-08-31 this path was `forbidden_paths` and its presence was a
    finding. The ban guarded against the VENDOR installer's AGENTS.md append
    (do-not.md #8), which this repo's own `graphify_skill.install_skill`
    structurally cannot cause. Presence alone is no longer a signal — see
    `test_graphify_skill_surface_flags_a_landed_vendor_install_marker` below
    for the check that still catches the real hazard.
    """
    _write_healthy_graphify_surface(tmp_path)
    (tmp_path / ".codex" / "skills" / "graphify").mkdir(parents=True)
    (tmp_path / ".codex" / "skills" / "graphify" / "SKILL.md").write_text(
        "managed via mise run graphify-update"
    )
    setup = _setup(repo_root=tmp_path, baseline={"graphify": _GRAPHIFY_BASELINE})
    assert doctor.check_graphify_skill_surface(setup) == []


def test_graphify_skill_surface_flags_a_landed_vendor_install_marker(
    tmp_path: Path,
) -> None:
    """The real hazard: a vendor `graphify install` append to AGENTS.md."""
    _write_healthy_graphify_surface(tmp_path)
    (tmp_path / "AGENTS.md").write_text(
        "When the user types `/graphify`, use the installed graphify skill instead.\n"
    )
    setup = _setup(repo_root=tmp_path, baseline={"graphify": _GRAPHIFY_BASELINE})
    findings = doctor.check_graphify_skill_surface(setup)
    assert len(findings) == 1
    assert "AGENTS.md" in findings[0]
    assert "do-not.md #8" in findings[0]


def test_graphify_skill_surface_is_silent_without_a_baseline_section(
    tmp_path: Path,
) -> None:
    """An absent `[graphify]` section covers nothing — the same seam #535 named."""
    setup = _setup(repo_root=tmp_path, baseline={})
    assert doctor.check_graphify_skill_surface(setup) == []


def test_graphify_skill_surface_delegates_currency_checks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _write_healthy_graphify_surface(tmp_path)
    monkeypatch.setattr(
        doctor,
        "graphify_currency_check",
        lambda root, *, offline: (
            Drift(
                "stamp",
                f"{root}/.codex stamp drift — run graphify-update (offline={offline})",
            ),
        ),
    )
    setup = _setup(repo_root=tmp_path, baseline={"graphify": _GRAPHIFY_BASELINE})
    assert doctor.check_graphify_skill_surface(setup) == [
        f"{tmp_path}/.codex stamp drift — run graphify-update (offline=True)"
    ]


def test_every_check_function_is_actually_registered() -> None:
    """Binds the CALL SITE, not the definition.

    Every other test in this file calls a ``check_*`` function directly, so a
    check that got dropped from :data:`doctor.CHECKS` would keep every one of
    them green while the doctor silently stopped running it. That is the
    stand-in failure `feedback_forbid_tokens_substring_fragile` names: assert
    the wiring, not just the thing being wired.
    """
    registered = {fn for _, fn in doctor.CHECKS + doctor.LIVE_CHECKS}
    defined = {
        getattr(doctor, name)
        for name in dir(doctor)
        if name.startswith("check_") and callable(getattr(doctor, name))
    }
    assert defined - registered == set(), "a check_* function is not wired into CHECKS"
    # 7 from #418, + `listing-budget` (2026-08-07): the skill/agent listing is
    # standing context every turn and nothing measured it. + `path-drift`
    # (2026-08-08, #596): whether THIS shell resolves the tools mise pins — a
    # cached activation keeps the old install dir on PATH, so gates run a stale
    # binary while `mise which` reports the new one. + `fnox-exec-leak`
    # (2026-08-29c): an `env = "exec"` secret present in the live ambient
    # environ anyway — a stale-process leak, not a config defect. Raise this
    # ONLY alongside a new entry in CHECKS — the count is what catches a check
    # that was defined and never registered, which the set-difference above
    # cannot see once the function is also removed. + `graphify-skill-surface`
    # (2026-08-31): the graphify skill surface's reviewed, DELIBERATE shape —
    # the deliberate-stub marker, and the forbidden vendor-install AGENTS.md
    # marker — the commit-time twin of hk's `graphify_skill_surface` step.
    # + `install-doctor` (2026-09-13): is the `claude` THIS shell runs the newest
    # published build, and does `claude doctor` itself report clean. Host state,
    # like `path-drift`, and blind for the same reason unless the SessionStart
    # hook captured PATH first. It exists because the repo's own
    # claude pin (added by #1038 so `fnhook_gates` can name an exact version)
    # puts a competing `claude` on PATH. #1043 moved it off the npm backend, so
    # it can no longer produce a broken launcher — but it is still not the
    # operator's install, and that is what this check asserts.
    # + `codex-schema` (2026-09-14): is the vendored codex app-server JSON schema
    # bundle still the one the INSTALLED codex emits. It exists because an agent or
    # config authored against a stale schema validates clean and then fails at
    # runtime — and codex drops an invalid `.codex/agents/*.toml` SILENTLY, with no
    # error, which is how six specialist agents existed on disk and none loaded.
    # + `removed-plugins` (2026-09-24): a deliberate removal must stay removed
    # across settings, harness state, caches, marketplaces and trusted hooks.
    # + `hk-hooks` (2026-09-27): every hk hook event hk.pkl defines is installed
    # for this checkout from some scope — the repo stopped installing hooks from
    # mise's postinstall (jdx/hk#1376), so a fresh clone otherwise has none.
    # + `devcontainers` (2026-09-30): every architecture in doctor.toml's
    # [devcontainers].arches has a RUNNING workspace container. Docker Desktop
    # quit on 2026-09-29, `land`/`sync` brought back only amd64, and the arm64
    # container sat exited ~24 h with nothing saying so.
    # + `native-only` (2026-10-01): agy/codex/claude resolve ONLY to their native
    # installs on the host (Ray's ruling); a mise copy first on PATH, or none
    # native at all, fails. Blind without the captured ambient PATH, like
    # `path-drift`, whose ambient-PATH seam it reuses.
    assert len(doctor.CHECKS) == 17, "every specified check must be wired"


def test_the_shipped_baseline_parses_and_declares_what_the_checks_read() -> None:
    """A baseline missing a section makes its check silently cover nothing.

    The ``env`` value is pinned deliberately, so flipping the host's posture
    cannot happen without a reviewed diff here as well. It was ``"exec"`` until
    **2026-08-02**, when Ray reversed it to ``True`` — all credentials available
    to every terminal and agent. See
    ``.claude/rules/secrets-out-of-the-shell-env.md``.
    """
    setup = doctor.collect(REPO_ROOT)
    fnox = setup.fnox_baseline()
    assert fnox.get("env") is True
    opt_in = fnox.get("env_true")
    assert isinstance(opt_in, list)
    # Under ``env = true`` this list is the FULL shell-visible set, not a short
    # opt-in list, and ``_opt_in_findings`` compares it as a SET in both
    # directions. A duplicate would silently shrink what is actually compared.
    assert opt_in, "env_true must not be empty — an empty set sanctions nothing"
    assert len(opt_in) == len(set(opt_in)), "env_true has duplicate names"
    mcp = setup.mcp_baseline()
    # KEY PRESENCE, not truthiness (#535). The arm's job is to distinguish "the
    # shipped doctor.toml was parsed" from "the parse returned {}" — and an empty
    # dict has no key at all, so presence still discriminates. Truthiness ALSO
    # pinned the value non-empty, which made a legitimately-empty declaration
    # (no MCP server is scoped on this host) unrepresentable, and kept a stale
    # `filesystem` entry alive purely to satisfy a test.
    assert "scope_servers" in mcp
    assert isinstance(mcp.get("mutating_tools"), dict)
    # KEY PRESENCE again, for the same reason: a missing [claude] section makes
    # `check_install_doctor` fall back to its module default silently, so the
    # reviewed decision about which install method is expected would live
    # nowhere a reviewer looks.
    claude = setup.baseline.get("claude")
    assert isinstance(claude, dict)
    assert "expected_install_method" in claude
    assert "enabled" in claude
    # Bare arch words: `check_devcontainers_running` resolves each through
    # `platform_arch`, and `no_platform_literals` rejects a triple in this file.
    devcontainers = setup.baseline.get("devcontainers")
    assert isinstance(devcontainers, dict)
    assert devcontainers.get("arches") == ["amd64", "arm64"]


def test_the_baseline_seam_still_discriminates_when_the_file_is_missing(
    tmp_path: Path,
) -> None:
    """The control arm for the assertions above (#535).

    Weakening `scope_servers` from truthiness to key presence is only safe if
    presence still tells a real parse apart from a failed one. The REALISTIC
    failure is not a renamed key — it is `collect()` finding no readable
    `doctor.toml` and falling back to `{}`, which is what it does on any OSError
    or TOMLDecodeError. Reproduce exactly that, and confirm the seam fails.
    """
    setup = doctor.collect(tmp_path, home=tmp_path, environ={})

    assert setup.baseline == {}, "no doctor.toml must yield an empty baseline"
    # Both forms of the seam fail on the empty parse — so presence is not weaker
    # than truthiness at the thing the arm actually guards.
    assert "scope_servers" not in setup.mcp_baseline()
    assert setup.fnox_baseline().get("env") is not True


def test_the_sessionstart_hook_runs_the_doctor() -> None:
    """The only place the doctor is wired; hook_selfcheck gates it in ship/land."""
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text())
    commands = doctor.hook_commands(settings, "SessionStart")
    assert any("run doctor" in command for command in commands)
    assert all("CLAUDE_PROJECT_DIR" in command for command in commands)


def test_claude_denies_the_label_command_even_inside_a_grep() -> None:
    """The exact double-quoted grep accident shape must hit the deny glob.

    ``hook_selfcheck`` drives the PreToolUse hook, not Claude's permission
    engine. The whole-command ``Bash`` glob semantics come from the local
    ``$CC/permissions.md`` corpus; this pins the live rule and both string arms.
    """
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text())
    rule = "Bash(*graphify label*)"
    deny = set(settings["permissions"]["deny"])
    assert rule in deny

    pattern = rule.removeprefix("Bash(").removesuffix(")")
    accident = 'grep -rn "Run `graphify label` to refresh" .'
    safe_control = 'grep -rn "Run the skill refresh task" .'
    assert fnmatchcase(accident, pattern)
    assert not fnmatchcase(safe_control, pattern)


def test_collect_reads_the_real_repo_without_touching_the_real_home(
    tmp_path: Path,
) -> None:
    """The `home` seam is what keeps this suite machine-independent.

    This used to assert the repo's server set was ``{exa, memory, filesystem}``,
    which doubled as the proof that ``collect`` had really read ``REPO_ROOT``.
    ``.mcp.json`` was emptied on 2026-07-30 (all three servers measured at 1-2
    calls across 179 transcripts), so that assertion would now be ``== set()``
    — a check that can only pass, and indistinguishable from ``collect``
    reading nothing at all. See ``tests/AGENTS.md`` on probes without a control
    arm.

    The repo-was-read proof therefore moves to ``doctor.toml``, which is
    non-empty and unambiguously sourced from ``REPO_ROOT``.
    """
    setup = doctor.collect(REPO_ROOT, home=tmp_path, environ={})

    # The home seam, and it genuinely discriminates: this machine HAS a real
    # ~/.config/fnox, so a broken seam flips this to True.
    assert not setup.fnox.exists

    # The repo seam — positive evidence that REPO_ROOT was read.
    assert setup.fnox_baseline().get("env") is True
    assert "scope_servers" in setup.mcp_baseline()

    # Current declared state, pinned deliberately so a future reader does not
    # "restore" the stale expectation above. The parsing path itself is covered
    # by the fixtures in test_collect_servers_* — not by this test.
    #
    # 2026-09-13: back to ONE server. `exa` was re-added when the `exa@exa`
    # plugin was enabled, because plugin 3.4.1 ships `mcp.json` (no leading dot,
    # `agent-plugins.org` schema) and declares no `mcpServers` in plugin.json —
    # so Claude Code, which reads `.mcp.json` or an inline `plugin.json` key
    # (`$CC/plugins-reference.md:166`), registers nothing for it and the
    # `/exa:search` skill's server would be absent. This also un-vacuums the four
    # doctor checks that iterate `setup.servers`, and restores this assertion's
    # control arm: a non-empty expectation fails if `collect` reads nothing,
    # which `== []` could not.
    assert [s.name for s in setup.servers] == ["exa"]


# --------------------------------------------------------------------------- #
# check — devcontainers (every expected architecture has a RUNNING container)
# --------------------------------------------------------------------------- #

_ARCHES_BASELINE: dict[str, object] = {"devcontainers": {"arches": ["amd64", "arm64"]}}
_ARM64_NAME = "dotfiles-dotfiles-u-273897ea-arm64-22975"
_AMD64_NAME = "dotfiles-dotfiles-u-273897ea-amd64-26233"
#: Raised by the down-daemon fixtures; a literal in a `raise` trips EM101.
_DAEMON_DOWN = "docker ps failed: Cannot connect to the Docker daemon"
_MISE_DOWN = "`mise -E arm64 env` exited 1: boom"
_AMD64_PLATFORM = "linux/amd64/v2"
_ARM64_PLATFORM = "linux/arm64/v8"
#: What this host resolves today: default amd64 on the pinned port, the arm64
#: profile on a blank one (P7 of the round-1 spec, re-probed 2026-09-30).
Rows = list[tuple[str, str, str]]
#: An arch's docker answer: its rows, or the DockerUnavailableError text.
DockerAnswers = dict[str, "Rows | str"]
Profiles = dict[str | None, "doctor.MiseResolution | Exception"]
_HEALTHY_PROFILES: Profiles = {
    None: doctor.MiseResolution(_AMD64_PLATFORM, "amd64", "26233"),
    "arm64": doctor.MiseResolution(_ARM64_PLATFORM, "arm64", ""),
}
_BOTH_RUNNING: DockerAnswers = {
    "amd64": [("e5ae", "running", _AMD64_NAME)],
    "arm64": [("a914", "running", _ARM64_NAME)],
}


@dataclasses.dataclass
class _Calls:
    """What the check asked of each injected seam, in order."""

    docker: list[str] = dataclasses.field(default_factory=list)
    mise: list[str | None] = dataclasses.field(default_factory=list)


def _inject(
    monkeypatch: pytest.MonkeyPatch,
    rows_by_arch: DockerAnswers | None = None,
    *,
    profiles: Profiles | None = None,
    worktree: bool = False,
    system: str = "Darwin",
) -> _Calls:
    """Replace every subprocess seam the check has; return the calls it made."""
    calls = _Calls()
    docker: DockerAnswers = _BOTH_RUNNING if rows_by_arch is None else rows_by_arch
    answers: Profiles = _HEALTHY_PROFILES if profiles is None else profiles

    def rows(names: doctor.devcontainer_names.DevcontainerNames) -> Rows:
        calls.docker.append(names.arch)
        answer = docker.get(names.arch, [])
        if isinstance(answer, str):
            raise doctor.DockerUnavailableError(answer)
        return answer

    def resolution(
        _root: Path, _environ: object, mise_env: str | None = None
    ) -> doctor.MiseResolution:
        calls.mise.append(mise_env)
        answer = answers[mise_env]
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(doctor, "docker_container_rows", rows)
    monkeypatch.setattr(doctor, "mise_env_resolution", resolution)
    monkeypatch.setattr(doctor, "is_linked_worktree", lambda _root: worktree)
    monkeypatch.setattr(doctor, "host_system", lambda: system)
    return calls


def _arches_setup(baseline: dict[str, object] | None = None) -> doctor.Setup:
    return _setup(baseline=_ARCHES_BASELINE if baseline is None else baseline)


def test_devcontainers_is_silent_when_every_arch_is_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The control arm: both up, profiles right — and every seam was asked."""
    calls = _inject(monkeypatch)
    assert doctor.check_devcontainers_running(_arches_setup()) == []
    assert calls.docker == ["amd64", "arm64"]
    assert calls.mise == [None, "arm64"]


def test_devcontainers_flags_the_incident_shape_with_dockers_own_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2026-09-29: arm64 exited after a Docker Desktop quit, amd64 re-created."""
    _inject(
        monkeypatch,
        {
            "amd64": [("e5ae", "running", _AMD64_NAME)],
            "arm64": [("a914", "exited", _ARM64_NAME)],
        },
    )
    assert doctor.check_devcontainers_running(_arches_setup()) == [
        (
            f"devcontainers: arm64 container {_ARM64_NAME} is exited — run "
            "`MISE_ENV=arm64 mise run up`"
        )
    ]


@pytest.mark.parametrize("state", ["created", "paused", "dead", "restarting"])
def test_devcontainers_every_non_running_state_is_a_finding(
    monkeypatch: pytest.MonkeyPatch, state: str
) -> None:
    """Only `running` counts; docker's other states all need the restore."""
    _inject(
        monkeypatch,
        {"amd64": [("e5ae", state, _AMD64_NAME)], "arm64": _BOTH_RUNNING["arm64"]},
    )
    assert doctor.check_devcontainers_running(_arches_setup()) == [
        f"devcontainers: amd64 container {_AMD64_NAME} is {state} — run `mise run up`"
    ]


def test_devcontainers_flags_a_missing_default_arch_with_plain_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No container at all for the default arch restores with bare ``mise run up``."""
    _inject(monkeypatch, {"arm64": _BOTH_RUNNING["arm64"]})
    assert doctor.check_devcontainers_running(_arches_setup()) == [
        "devcontainers: no amd64 container for this clone — run `mise run up`"
    ]


def test_devcontainers_one_running_container_satisfies_the_arch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stale exited sibling next to a running one is not a down architecture."""
    _inject(
        monkeypatch,
        {
            "amd64": [("old1", "exited", "stale"), ("e5ae", "running", _AMD64_NAME)],
            "arm64": _BOTH_RUNNING["arm64"],
        },
    )
    assert doctor.check_devcontainers_running(_arches_setup()) == []


def test_devcontainers_default_arch_comes_from_mise_not_the_process_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cold #2: outside mise the process env says arm64; mise says what `up` does.

    The process environ carries the host-fallback arm64 triple, and mise
    resolves the default to amd64 — the restore commands must follow mise.
    """
    _inject(monkeypatch, {})
    setup = _setup(
        baseline=_ARCHES_BASELINE, environ={"DOTFILES_PLATFORM": _ARM64_PLATFORM}
    )
    assert doctor.check_devcontainers_running(setup) == [
        "devcontainers: no amd64 container for this clone — run `mise run up`",
        (
            "devcontainers: no arm64 container for this clone — run "
            "`MISE_ENV=arm64 mise run up`"
        ),
    ]


def test_devcontainers_an_arm64_default_asks_mise_about_amd64(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Whichever arch mise calls default, the OTHER is the profile checked."""
    calls = _inject(
        monkeypatch,
        {},
        profiles={
            None: doctor.MiseResolution(_ARM64_PLATFORM, "arm64", ""),
            "amd64": doctor.MiseResolution(_AMD64_PLATFORM, "amd64", ""),
        },
    )
    assert doctor.check_devcontainers_running(_arches_setup()) == [
        (
            "devcontainers: no amd64 container for this clone — run "
            "`MISE_ENV=amd64 mise run up`"
        ),
        "devcontainers: no arm64 container for this clone — run `mise run up`",
    ]
    assert calls.mise == [None, "amd64"]


def test_devcontainers_a_profile_resolving_the_wrong_arch_is_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cold #1: `MISE_ENV=arm64` silently selecting amd64 is the real hazard.

    An unrecognised or missing env profile resolves the DEFAULT (measured on mise
    2026.9.18), so `MISE_ENV=arm64 mise run up` would recreate amd64.
    """
    _inject(
        monkeypatch,
        profiles={
            **_HEALTHY_PROFILES,
            "arm64": doctor.MiseResolution(_AMD64_PLATFORM, "amd64", "26233"),
        },
    )
    assert doctor.check_devcontainers_running(_arches_setup()) == [
        (
            "devcontainers: `MISE_ENV=arm64` resolves DOTFILES_PLATFORM="
            f"{_AMD64_PLATFORM}, not the published {_ARM64_PLATFORM}, so "
            "`MISE_ENV=arm64 mise run up` would bring up amd64; check mise.arm64.toml"
        ),
        (
            "devcontainers: `MISE_ENV=arm64` resolves DEVCONTAINER_SSH_PORT=26233, the "
            "same port the default amd64 container uses, so the two collide; blank it "
            "in mise.arm64.toml"
        ),
    ]


@pytest.mark.parametrize(
    ("default_port", "profile_port", "collides"),
    [
        ("26233", "26233", True),
        ("26233", "", False),
        ("26233", "4445", False),
        ("", "", False),
    ],
    ids=["same-pin", "blank-profile", "distinct-pin", "both-derived"],
)
def test_devcontainers_port_collision_needs_two_equal_non_empty_pins(
    monkeypatch: pytest.MonkeyPatch,
    default_port: str,
    profile_port: str,
    *,
    collides: bool,
) -> None:
    """Blank means "derive per arch" (#677), so only two equal pins collide."""
    _inject(
        monkeypatch,
        profiles={
            None: doctor.MiseResolution(_AMD64_PLATFORM, "amd64", default_port),
            "arm64": doctor.MiseResolution(_ARM64_PLATFORM, "arm64", profile_port),
        },
    )
    findings = doctor.check_devcontainers_running(_arches_setup())
    assert any("collide" in finding for finding in findings) is collides
    assert len(findings) == int(collides)


def test_devcontainers_a_failed_default_resolution_is_one_finding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No default means no restore command for ANY arch: docker is not asked."""
    calls = _inject(
        monkeypatch, profiles={None: doctor.MiseEnvError("mise not found on PATH")}
    )
    assert doctor.check_devcontainers_running(_arches_setup()) == [
        "devcontainers: UNVERIFIABLE — mise env failed (mise not found on PATH)"
    ]
    assert calls.docker == []


def test_devcontainers_a_failed_profile_skips_only_that_arch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """amd64 is still checked (and its finding kept); arm64 is unverifiable."""
    calls = _inject(
        monkeypatch,
        {},
        profiles={**_HEALTHY_PROFILES, "arm64": doctor.MiseEnvError(_MISE_DOWN)},
    )
    assert doctor.check_devcontainers_running(_arches_setup()) == [
        "devcontainers: no amd64 container for this clone — run `mise run up`",
        f"devcontainers: UNVERIFIABLE — mise env failed ({_MISE_DOWN})",
    ]
    assert calls.docker == ["amd64"]


def test_devcontainers_a_down_daemon_keeps_earlier_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cold #5: a later arch's docker failure must not discard a definite finding."""
    calls = _inject(monkeypatch, {"amd64": [], "arm64": _DAEMON_DOWN})
    assert doctor.check_devcontainers_running(_arches_setup()) == [
        "devcontainers: no amd64 container for this clone — run `mise run up`",
        f"devcontainers: UNVERIFIABLE — {_DAEMON_DOWN}",
    ]
    assert calls.docker == ["amd64", "arm64"]


def test_devcontainers_a_down_daemon_stops_further_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One unverifiable finding, and no query after the one that failed."""
    calls = _inject(monkeypatch, {"amd64": _DAEMON_DOWN})
    assert doctor.check_devcontainers_running(_arches_setup()) == [
        f"devcontainers: UNVERIFIABLE — {_DAEMON_DOWN}"
    ]
    assert calls.docker == ["amd64"]


@pytest.mark.parametrize("section", [{}, {"arches": []}, {"arches": "amd64"}])
def test_devcontainers_reports_an_unconfigured_baseline(
    monkeypatch: pytest.MonkeyPatch, section: dict[str, object]
) -> None:
    """A missing list must not read as a healthy host — and nothing is asked."""
    calls = _inject(monkeypatch)
    assert doctor.check_devcontainers_running(
        _arches_setup({"devcontainers": section})
    ) == [
        (
            "devcontainers: doctor.toml has no [devcontainers].arches, so no "
            "container is being checked"
        )
    ]
    assert calls == _Calls()


@pytest.mark.parametrize(
    ("arches", "bad"),
    [
        (["amd64", "riscv"], "'riscv'"),
        (["amd64", 3], "3"),
        (["amd64", "amd64"], "'amd64'"),
        (["x86_64", "amd64"], "'amd64'"),
    ],
    ids=["unknown-word", "not-a-string", "duplicate", "duplicate-alias"],
)
def test_devcontainers_rejects_unusable_arch_entries(
    monkeypatch: pytest.MonkeyPatch, arches: list[object], bad: str
) -> None:
    """Cold #6: each entry must normalize to a distinct known arch."""
    calls = _inject(monkeypatch)
    findings = doctor.check_devcontainers_running(
        _arches_setup({"devcontainers": {"arches": arches}})
    )
    assert len(findings) == 1
    assert "unusable entries" in findings[0]
    assert bad in findings[0]
    assert calls == _Calls()


def test_devcontainers_normalizes_an_alias_to_the_arch_word(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`aarch64` is arm64: the restore command names the MISE_ENV that exists."""
    _inject(monkeypatch, {"amd64": _BOTH_RUNNING["amd64"]})
    assert doctor.check_devcontainers_running(
        _arches_setup({"devcontainers": {"arches": ["amd64", "aarch64"]}})
    ) == [
        (
            "devcontainers: no arm64 container for this clone — run "
            "`MISE_ENV=arm64 mise run up`"
        )
    ]


def test_devcontainers_is_silent_in_a_linked_worktree(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Containers belong to the main checkout; a worktree would see none."""
    calls = _inject(monkeypatch, {}, worktree=True)
    assert doctor.check_devcontainers_running(_arches_setup()) == []
    assert calls == _Calls()


@pytest.mark.parametrize("system", ["Linux", "Windows", ""])
def test_devcontainers_is_silent_off_the_macos_host(
    monkeypatch: pytest.MonkeyPatch, system: str
) -> None:
    """In the container there is no docker CLI; on CI the concept does not apply.

    Every container missing, so the silence can only come from the host gate.
    """
    calls = _inject(monkeypatch, {}, system=system)
    assert doctor.check_devcontainers_running(_arches_setup()) == []
    assert calls == _Calls()


def test_host_system_reads_the_platform_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """The seam is the real ``platform.system`` — not a constant."""
    monkeypatch.setattr(doctor.platform, "system", lambda: "Plan9")
    assert doctor.host_system() == "Plan9"


# --- the docker seam ------------------------------------------------------- #


def _completed(
    returncode: int, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def _names() -> doctor.devcontainer_names.DevcontainerNames:
    return doctor.devcontainer_names.resolve_names(
        workspace="/repo", user="u", platform="arm64", env={}
    )


def test_docker_container_rows_queries_both_labels_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Workspace AND arch label, each behind its own --filter; -a; a hard bound."""
    seen: dict[str, object] = {}

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["argv"] = argv
        seen.update(kwargs)
        return _completed(0, f"a914\texited\t{_ARM64_NAME}\n\n")

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    names = _names()
    assert doctor.docker_container_rows(names) == [("a914", "exited", _ARM64_NAME)]
    argv = seen["argv"]
    assert isinstance(argv, list)
    assert argv[:3] == ["docker", "ps", "-a"]
    for label in (names.workspace_label, names.arch_label):
        at = argv.index(f"label={label}")
        assert argv[at - 1] == "--filter", f"{label} is not a --filter value"
    assert argv.count("--filter") == 2
    assert argv[argv.index("--format") + 1] == "{{.ID}}\t{{.State}}\t{{.Names}}"
    assert seen["timeout"] == 10.0
    assert seen["check"] is False


def test_docker_container_rows_empty_output_is_no_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rc=0 with nothing listed is a real "absent", distinct from a failure."""
    monkeypatch.setattr(doctor.subprocess, "run", lambda *_a, **_k: _completed(0))
    assert doctor.docker_container_rows(_names()) == []


@pytest.mark.parametrize(
    ("outcome", "message"),
    [
        (
            _completed(1, stderr="Cannot connect to the Docker daemon\nIs it running?"),
            (
                "docker ps failed: Cannot connect to the Docker daemon; is Docker "
                "Desktop running and the context right?"
            ),
        ),
        (
            _completed(125),
            (
                "docker ps failed: exit 125; is Docker Desktop running and the "
                "context right?"
            ),
        ),
        (
            _completed(0, "only-two\tfields\n"),
            "unparsable docker ps line: only-two\tfields",
        ),
        (
            subprocess.TimeoutExpired(["docker"], 10.0),
            "docker ps did not answer within 10 s",
        ),
        (
            FileNotFoundError(2, "No such file or directory", "docker"),
            "docker CLI not found on PATH",
        ),
        (
            PermissionError(13, "Permission denied", "docker"),
            "docker could not run: [Errno 13] Permission denied: 'docker'",
        ),
    ],
    ids=[
        "daemon-down",
        "silent-nonzero",
        "malformed",
        "timeout",
        "missing-binary",
        "not-executable",
    ],
)
def test_docker_container_rows_names_each_cause(
    monkeypatch: pytest.MonkeyPatch,
    outcome: subprocess.CompletedProcess[str] | BaseException,
    message: str,
) -> None:
    """Cold #10: the hint follows the cause; every failure raises (rc kept)."""

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    with pytest.raises(doctor.DockerUnavailableError) as info:
        doctor.docker_container_rows(_names())
    assert str(info.value) == message


# --- the mise seam --------------------------------------------------------- #


_AMBIENT = {
    "PATH": "/usr/bin",
    "HOME": "/home/u",
    "MISE_ENV": "arm64",
    "DOTFILES_PLATFORM": _ARM64_PLATFORM,
    "DEVCONTAINER_SSH_PORT": "26233",
}


@pytest.mark.parametrize(
    ("mise_env", "argv"),
    [
        (None, ["mise", "env", "--json"]),
        ("arm64", ["mise", "-E", "arm64", "env", "--json"]),
    ],
)
def test_mise_env_resolution_asks_mise_from_config_alone(
    monkeypatch: pytest.MonkeyPatch, mise_env: str | None, argv: list[str]
) -> None:
    """The profile flag, the repo cwd, a bound, no stdin — and no ambient leak.

    ``mise.toml`` templates DOTFILES_PLATFORM from the ambient value, so a
    parent under ``MISE_ENV=arm64`` would otherwise make arm64 the default.
    """
    seen: dict[str, object] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["argv"] = cmd
        seen.update(kwargs)
        return _completed(
            0, json.dumps({"DOTFILES_PLATFORM": _ARM64_PLATFORM, "OTHER": "x"})
        )

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    got = doctor.mise_env_resolution(Path("/repo"), _AMBIENT, mise_env)
    assert got == doctor.MiseResolution(_ARM64_PLATFORM, "arm64", "")
    assert seen["argv"] == argv
    assert seen["cwd"] == Path("/repo")
    assert seen["timeout"] == 20.0
    assert seen["stdin"] is subprocess.DEVNULL
    assert seen["check"] is False
    assert seen["env"] == {
        "PATH": "/usr/bin",
        "HOME": "/home/u",
        "MISE_ENV_CACHE": "0",
    }


def test_mise_env_resolution_reads_the_port_as_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pinned port comes back as the string mise resolved, trimmed."""
    payload = {"DOTFILES_PLATFORM": _AMD64_PLATFORM, "DEVCONTAINER_SSH_PORT": " 26233 "}
    monkeypatch.setattr(
        doctor.subprocess, "run", lambda *_a, **_k: _completed(0, json.dumps(payload))
    )
    assert doctor.mise_env_resolution(Path("/repo"), {}) == doctor.MiseResolution(
        _AMD64_PLATFORM, "amd64", "26233"
    )


@pytest.mark.parametrize(
    ("outcome", "message"),
    [
        (_completed(1, stderr="mise ERROR not trusted\nmore"), "exited 1: mise ERROR"),
        (_completed(0, "{not json"), "unparsable JSON"),
        (_completed(0, "[1, 2]"), "not an object"),
        (_completed(0, "{}"), "resolves DOTFILES_PLATFORM=''"),
        (_completed(0, '{"DOTFILES_PLATFORM": "linux/s390x"}'), "linux/s390x"),
        (subprocess.TimeoutExpired(["mise"], 20.0), "did not answer within 20 s"),
        (FileNotFoundError(2, "No such file", "mise"), "mise not found on PATH"),
    ],
    ids=[
        "nonzero",
        "bad-json",
        "not-object",
        "no-platform",
        "unknown-arch",
        "timeout",
        "missing",
    ],
)
def test_mise_env_resolution_failures_raise(
    monkeypatch: pytest.MonkeyPatch,
    outcome: subprocess.CompletedProcess[str] | BaseException,
    message: str,
) -> None:
    """Every way mise can fail to answer is a MiseEnvError, never a guess."""

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    with pytest.raises(doctor.MiseEnvError, match=re.escape(message)):
        doctor.mise_env_resolution(Path("/repo"), {}, "arm64")


# --- the git seam ---------------------------------------------------------- #


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def test_is_linked_worktree_discriminates_main_worktree_and_non_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real git, both arms: the main checkout is False, a linked worktree True.

    Global and system git config are cut off (cold #12), so an operator's
    hooks, templates or `init.defaultBranch` cannot change the answer.
    """
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-global-config"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-b", "main")
    _git(main, "commit", "--allow-empty", "-m", "init")
    linked = tmp_path / "linked"
    _git(main, "worktree", "add", str(linked))

    assert doctor.is_linked_worktree(main) is False
    assert doctor.is_linked_worktree(linked) is True
    assert doctor.is_linked_worktree(tmp_path / "nowhere") is False


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError(2, "No such file or directory", "git"),
        subprocess.TimeoutExpired(["git"], 10.0),
    ],
    ids=["git-missing", "git-hung"],
)
def test_is_linked_worktree_fails_open_to_checking(
    monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> None:
    """Code-review #2: a missing or hung git is "not a worktree", never a crash."""
    seen: dict[str, object] = {}

    def fake_run(*_args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.update(kwargs)
        raise error

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    assert doctor.is_linked_worktree(Path("/repo")) is False
    assert seen["timeout"] == 10.0


def test_mise_env_resolution_strips_the_mise_env_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MISE_PROFILE / MISE_ENVIRONMENT select a profile like MISE_ENV (2026.9.18)."""
    seen: dict[str, object] = {}

    def fake_run(_cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen.update(kwargs)
        return _completed(0, json.dumps({"DOTFILES_PLATFORM": _ARM64_PLATFORM}))

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    ambient = {"PATH": "/usr/bin", "MISE_PROFILE": "arm64", "MISE_ENVIRONMENT": "arm64"}
    doctor.mise_env_resolution(Path("/repo"), ambient, None)
    env = seen["env"]
    assert isinstance(env, dict)
    assert "MISE_PROFILE" not in env
    assert "MISE_ENVIRONMENT" not in env
    assert env["MISE_ENV_CACHE"] == "0"


def test_mise_env_failure_quotes_the_cause_on_a_later_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mise prints the real cause ("not trusted") on line 2 of an untrusted config."""
    stderr = "mise ERROR error parsing config file\nmise ERROR not trusted\nhint\nx\n"
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda cmd, **_kwargs: subprocess.CompletedProcess(cmd, 1, "", stderr),
    )
    with pytest.raises(doctor.MiseEnvError) as info:
        doctor.mise_env_resolution(Path("/repo"), {}, None)
    assert "not trusted" in str(info.value)
    assert "| x" not in str(info.value)


def test_a_profile_resolving_a_level_less_triple_is_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A level-less arm64 triple shares the arch word; sync rejects it."""
    _inject(
        monkeypatch,
        profiles={
            **_HEALTHY_PROFILES,
            "arm64": doctor.MiseResolution("linux/arm64", "arm64", ""),
        },
    )
    findings = doctor.check_devcontainers_running(_arches_setup())
    assert any(f"not the published {_ARM64_PLATFORM}" in f for f in findings)


# --------------------------------------------------------------------------- #
# native-only — the doctor adapter over path_drift.check_native_only
# --------------------------------------------------------------------------- #


def test_native_only_reports_blindness_rather_than_passing() -> None:
    setup = _setup(environ={"PATH": "/x", "MISE_TASK_NAME": "doctor"})
    assert doctor.check_native_only(setup) == [doctor.NATIVE_ONLY_BLIND_ADVICE]


def test_native_only_reads_the_baseline_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The adapter must hand ``[path_drift.native_only]`` through, not the default.

    The baseline names a binary no default covers; a FAIL for it proves the
    declared table, not ``DEFAULT_NATIVE_ONLY``, decided what was checked.
    """
    monkeypatch.setattr(doctor_path_drift, "_SYSTEM_MISE_DATA", tmp_path / "sys")
    shims = tmp_path / "home" / ".local" / "share" / "mise" / "shims"
    shims.mkdir(parents=True)
    (shims / "zzfake").write_text("#!/bin/sh\n")
    (shims / "zzfake").chmod(0o755)
    monkeypatch.setattr(doctor_path_drift, "run_mise_ls", lambda: ({}, None))
    setup = _setup(
        baseline={"path_drift": {"native_only": {"zzfake": ["zzfake-tool"]}}},
        environ={"DOTFILES_AMBIENT_PATH": str(shims)},
        home=tmp_path / "home",
    )
    findings = doctor.check_native_only(setup)
    assert any("`zzfake` resolves to mise's copy" in f for f in findings)
    assert not any("agy" in f for f in findings)
