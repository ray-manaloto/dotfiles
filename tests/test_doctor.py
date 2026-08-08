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
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import doctor

REPO_ROOT = Path(__file__).parent.parent

#: Raised by the fail-open fixtures; a literal in a `raise` trips EM101.
_CRASH_MESSAGE = "kaboom"

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
    # binary while `mise which` reports the new one. Raise this ONLY
    # alongside a new entry in CHECKS — the count is what catches a check that
    # was defined and never registered, which the set-difference above cannot
    # see once the function is also removed.
    assert len(doctor.CHECKS) == 9, "every specified check must be wired"


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
    assert [s.name for s in setup.servers] == []
