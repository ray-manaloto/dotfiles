"""cbm install and cbm verify, run as the installed command, against the stand-in CBM binary."""

import json
import os
import signal
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

import pytest

from .conftest import CBM, TIMEOUT, calls, cbm, events, failed, launcher, link, mode, restored

SCOUT = "Codex agent codebase-memory-scout: launcher, scout profile, read-only CBM tools only"
CHECKS = 18


def test_install_then_verify_pass(home: Path) -> None:
    done = cbm("install")
    assert done.returncode == 0, done.stderr
    assert failed(done.stdout) == []
    assert events(done.stdout)[-1] == {"event": "done", "command": "install", "failed": 0}
    assert not done.stderr
    assert restored(home)
    recorded = calls(home)
    assert f"install --skip-binary --clients=claude,codex --dir={launcher(home).parent} -y" in recorded
    assert "config set auto_index false" in recorded
    verified = cbm("verify")
    assert verified.returncode == 0
    assert len(events(verified.stdout)) == CHECKS + 1
    # A second install removes this package's own launcher first and puts it back.
    assert cbm("install").returncode == 0
    assert restored(home)


def test_verify_before_install_fails_and_reports_the_missing_launcher(home: Path) -> None:
    done = cbm("verify")
    assert done.returncode == 1
    assert len(failed(done.stdout)) == CHECKS - 1  # only "no CBM copy in ~/.local/bin" holds
    errors = events(done.stderr)
    assert {error["path"] for error in errors} == {str(launcher(home))}
    assert all(error["message"].startswith("cbm: codebase-memory-mcp could not run") for error in errors)
    assert "install" not in calls(home)


def test_installer_failure_restores_launcher_and_exits_1(home: Path) -> None:
    mode(home, "fail")
    done = cbm("install")
    assert done.returncode == 1
    assert events(done.stderr) == [
        {"event": "error", "message": "cbm: the CBM installer exited 3", "path": str(link(home))}
    ]
    assert restored(home)


def test_installer_that_cannot_start_restores_launcher(home: Path) -> None:
    assert cbm("install").returncode == 0
    link(home).chmod(0o644)
    done = cbm("install")
    assert done.returncode == 1
    [error] = events(done.stderr)
    assert error["message"].startswith("cbm: the CBM installer could not start")
    assert error["path"] == str(link(home))
    assert restored(home)


def test_a_launcher_the_installer_left_is_kept_and_fails_the_check(home: Path) -> None:
    mode(home, "link")
    done = cbm("install")
    assert done.returncode == 1
    assert "launcher is a symlink to the mise global link" in failed(done.stdout)
    assert launcher(home).readlink() == launcher(home).parent / "elsewhere"


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_signals_during_install_restore_launcher(home: Path, sig: signal.Signals) -> None:
    # The command in its own process group, signalled as Ctrl-C or `kill` on the job would be.
    assert cbm("install").returncode == 0
    mode(home, "hang")
    with subprocess.Popen(
        [str(CBM), "install"], env=os.environ.copy(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, start_new_session=True,
    ) as proc:  # fmt: skip
        deadline = time.monotonic() + TIMEOUT
        while not (home / "started").exists():
            assert time.monotonic() < deadline, "the stand-in installer never started"
            assert proc.poll() is None, proc.communicate()
            time.sleep(0.05)
        assert not launcher(home).is_symlink()
        os.killpg(proc.pid, sig)
        proc.communicate(timeout=TIMEOUT)
    assert proc.returncode == 128 + sig
    assert restored(home)


def test_verify_without_the_global_link_fails_its_checks_without_a_crash(home: Path) -> None:
    assert cbm("install").returncode == 0
    link(home).unlink()
    done = cbm("verify")
    assert done.returncode == 1
    assert "Traceback" not in done.stderr
    assert str(link(home)) in {error["path"] for error in events(done.stderr)}
    assert events(done.stdout)[-1]["event"] == "done"


def test_a_second_install_while_one_runs_is_refused(home: Path) -> None:
    assert cbm("install").returncode == 0
    mode(home, "hang")
    with subprocess.Popen(
        [str(CBM), "install"], env=os.environ.copy(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, start_new_session=True,
    ) as first:  # fmt: skip
        deadline = time.monotonic() + TIMEOUT
        while not (home / "started").exists():
            assert time.monotonic() < deadline, "the stand-in installer never started"
            time.sleep(0.05)
        second = cbm("install")
        os.killpg(first.pid, signal.SIGTERM)
        first.communicate(timeout=TIMEOUT)
    assert second.returncode == 1
    [error] = events(second.stderr)
    assert error["message"] == "cbm: another cbm install is running; rerun when it has finished"
    assert restored(home)
    # The refused run never reached the installer: only the first install and the hanging one did.
    assert len([line for line in calls(home).splitlines() if line.startswith("install ")]) == 2


def test_missing_global_link_changes_nothing(home: Path) -> None:
    link(home).unlink()
    done = cbm("install")
    assert done.returncode == 1
    [error] = events(done.stderr)
    assert "mise install" in error["message"]
    assert error["path"] == str(link(home))
    assert not launcher(home).exists()
    assert not launcher(home).is_symlink()


def test_foreign_launcher_is_refused(home: Path) -> None:
    launcher(home).parent.mkdir(parents=True)
    launcher(home).symlink_to(home / "elsewhere")
    done = cbm("install")
    assert done.returncode == 1
    assert events(done.stderr)[0]["path"] == str(launcher(home))
    assert launcher(home).readlink() == home / "elsewhere"
    assert not calls(home)


def test_regular_file_launcher_is_refused(home: Path) -> None:
    launcher(home).parent.mkdir(parents=True)
    launcher(home).write_text("mine")
    assert cbm("install").returncode == 1
    assert launcher(home).read_text() == "mine"


@pytest.mark.parametrize("value", ["", " , ", "claude,foo", "antigravity", "claude,claude", "codex,claude,codex"])
@pytest.mark.parametrize("command", ["install", "verify"])
def test_bad_client_lists_exit_2(home: Path, monkeypatch: pytest.MonkeyPatch, value: str, command: str) -> None:
    monkeypatch.setenv("CBM_CLIENTS", value)
    done = cbm(command)
    assert done.returncode == 2
    [error] = events(done.stderr)
    assert "CBM_CLIENTS" in error["message"]
    assert not done.stdout
    assert not calls(home)


def test_a_repeated_client_is_named_as_the_reason(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CBM_CLIENTS", "claude,claude")
    [error] = events(cbm("install").stderr)
    assert "names a client twice" in error["message"]
    assert not calls(home)


def test_client_order_is_kept(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CBM_CLIENTS", "codex,claude")
    assert cbm("install").returncode == 0
    assert "--clients=codex,claude " in calls(home)


@pytest.mark.parametrize("name", ["CODEX_HOME", "CLAUDE_CONFIG_DIR"])
def test_moved_config_folders_exit_2(home: Path, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    monkeypatch.setenv(name, str(home / "other"))
    done = cbm("install")
    assert done.returncode == 2
    assert f"unset {name}" in events(done.stderr)[0]["message"]
    assert not calls(home)


@pytest.mark.parametrize("argv", [[], ["nope"], ["install", "verify"]])
def test_bad_usage_exits_2(home: Path, argv: list[str]) -> None:
    done = cbm(*argv)
    assert done.returncode == 2
    assert events(done.stderr) == [{"event": "error", "message": "usage: cbm {install,verify}", "path": None}]
    assert not calls(home)


@pytest.mark.parametrize(("client", "other"), [("claude", "codex"), ("codex", "claude")])
def test_one_client_installs_and_checks_only_that_client(
    home: Path, monkeypatch: pytest.MonkeyPatch, client: str, other: str
) -> None:
    monkeypatch.setenv("CBM_CLIENTS", client)
    done = cbm("install")
    assert done.returncode == 0, done.stdout + done.stderr
    assert f"--clients={client} " in calls(home)
    names = [event["name"] for event in events(done.stdout) if event["event"] == "check"]
    assert not [name for name in names if name.startswith(other.capitalize())]
    assert not (home / f".{other}").exists()


def test_config_set_failing_fails_install(home: Path) -> None:
    (home / "config-fails").touch()
    done = cbm("install")
    assert done.returncode == 1
    assert {"config set auto_index false", "auto_index is false"} <= set(failed(done.stdout))
    assert events(done.stdout)[-1]["failed"] == 2


def test_installer_never_sees_the_cbm_namespace(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CBM_RUNTIME_DIR", str(home / "other-namespace"))
    monkeypatch.setenv("CBM_CACHE_DIR", str(home / "other-cache"))
    assert cbm("install").returncode == 0
    seen = set(json.loads((home / "install-env.json").read_text()))
    assert "HOME" in seen
    assert not seen & {"CBM_RUNTIME_DIR", "CBM_CACHE_DIR"}


def check_after(home: Path, edit: Callable[[], object], failing: str) -> subprocess.CompletedProcess[str]:
    """Install, apply one edit to the result, and expect verify to fail exactly that check."""
    assert cbm("install").returncode == 0, calls(home)
    edit()
    done = cbm("verify")
    assert done.returncode == 1
    assert failed(done.stdout) == [failing]
    return done


def test_missing_hook_group_fails(home: Path) -> None:
    mode(home, "missing-hook")
    done = cbm("install")
    assert done.returncode == 1
    [check] = [event for event in events(done.stdout) if event["event"] == "check" and not event["ok"]]
    assert check == {"event": "check", "name": "Claude has the 7 CBM hook groups, once each", "ok": False,
                     "detail": "6 found"}  # fmt: skip


def test_duplicate_claude_hook_fails(home: Path) -> None:
    path = home / ".claude/settings.json"

    def edit() -> None:
        settings = json.loads(path.read_text())
        settings["hooks"]["PostToolUse"].append(settings["hooks"]["PostToolUse"][0])
        path.write_text(json.dumps(settings))

    check_after(home, edit, "Claude has the 7 CBM hook groups, once each")


@pytest.mark.parametrize("extra", [{"args": ["--tool-profile=scout"]}, {"env": {"CBM_RUNTIME_DIR": "/elsewhere"}}])
def test_claude_mcp_with_args_or_env_fails(home: Path, extra: dict[str, object]) -> None:
    path = home / ".claude.json"

    def edit() -> None:
        entry = {"command": str(launcher(home)), "args": [], **extra}
        path.write_text(json.dumps({"mcpServers": {"codebase-memory-mcp": entry}}))

    check_after(home, edit, "Claude MCP entry names the launcher, no args or env")


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s + '[mcp_servers.codebase-memory-mcp.env]\nCBM_CACHE_DIR = "/elsewhere"\n',
        lambda s: s.replace('env_vars = ["CBM_CACHE_DIR", "CBM_RUNTIME_DIR"]\n', ""),
    ],
)
def test_codex_mcp_with_env_or_without_the_forwarded_names_fails(home: Path, change: Callable[[str], str]) -> None:
    path = home / ".codex/config.toml"
    codex_mcp = "Codex MCP entry names the launcher, no args or env"
    check_after(home, lambda: path.write_text(change(path.read_text())), codex_mcp)


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s.replace("--tool-profile=scout", "--tool-profile=analysis"),
        lambda s: s.replace('enabled_tools = ["search_graph"]\n', ""),
        lambda s: s.replace('["search_graph"]', '["search_graph", "index_repository"]'),
        lambda s: s.replace('["search_graph"]', '["not_a_cbm_tool"]'),
        lambda s: s.replace('["search_graph"]', '["search_graph", "search_graph"]'),
    ],
)
def test_wrong_codex_role_fails(home: Path, change: Callable[[str], str]) -> None:
    role = home / ".codex/agents/codebase-memory-scout.toml"
    check_after(home, lambda: role.write_text(change(role.read_text())), SCOUT)


def test_malformed_codex_role_is_an_error_event_and_fails(home: Path) -> None:
    role = home / ".codex/agents/codebase-memory-scout.toml"
    done = check_after(home, lambda: role.write_text("not = [toml"), SCOUT)
    [error] = events(done.stderr)
    assert error["message"].startswith("cbm: cannot parse TOML")
    assert error["path"] == str(role)


def test_malformed_claude_settings_is_an_error_event_and_fails(home: Path) -> None:
    settings = home / ".claude/settings.json"
    done = check_after(home, lambda: settings.write_text("{not json"), "Claude has the 7 CBM hook groups, once each")
    [error] = events(done.stderr)
    assert error["message"].startswith("cbm: cannot parse JSON")
    assert error["path"] == str(settings)


@pytest.mark.parametrize(
    "change",
    [
        lambda s: s.replace("mcp__codebase-memory-mcp__search_graph", "mcp__codebase-memory-mcp__index_repository"),
        lambda s: s.replace(
            "  - mcp__codebase-memory-mcp__search_graph\n", "  - mcp__codebase-memory-mcp__search_graph\n" * 2
        ),
    ],
)
def test_unknown_or_duplicate_claude_agent_tool_fails(home: Path, change: Callable[[str], str]) -> None:
    agent = home / ".claude/agents/codebase-memory.md"
    check_after(
        home, lambda: agent.write_text(change(agent.read_text())),
        "Claude agent codebase-memory: present, read-only CBM tools only",
    )  # fmt: skip


def test_empty_agents_md_block_fails(home: Path) -> None:
    agents_md = home / ".codex/AGENTS.md"
    empty = "<!-- codebase-memory-mcp:start -->\n<!-- codebase-memory-mcp:end -->\n"
    check_after(
        home, lambda: agents_md.write_text(empty), "Codex AGENTS.md has the CBM managed block, pointing at the skill"
    )


def test_version_command_failing_fails_both_version_checks(home: Path) -> None:
    # Without the mise build's version the MCP session's version cannot be matched either.
    assert cbm("install").returncode == 0
    (home / "version-fails").touch()
    done = cbm("verify")
    assert done.returncode == 1
    assert failed(done.stdout) == ["launcher runs the mise global build", MCP]


def test_auto_index_left_on_fails(home: Path) -> None:
    check_after(home, lambda: (home / "cbm-config").write_text("true"), "auto_index is false")


MCP = "MCP server answers over stdio: the mise build, every read-only tool"


@pytest.mark.parametrize("flag", ["mcp-old", "mcp-missing-tool"])
def test_mcp_server_with_another_version_or_a_missing_tool_fails(home: Path, flag: str) -> None:
    done = check_after(home, (home / flag).touch, MCP)
    [check] = [event for event in events(done.stdout) if event.get("name") == MCP]
    want = {"mcp-old": "0.0.1, 14 tools", "mcp-missing-tool": "9.9.9, 13 tools, missing trace_path"}
    assert check["detail"] == want[flag]


def test_mcp_server_answering_garbage_is_an_error_event_and_fails(home: Path) -> None:
    done = check_after(home, (home / "mcp-garbage").touch, MCP)
    [error] = events(done.stderr)
    assert error["message"].startswith("cbm: the MCP server answered something other than JSON")
    assert error["path"] == str(launcher(home))
