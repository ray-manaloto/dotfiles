"""Codex hooks live in hooks.json only: cbm install seeds it, cbm verify refuses CBM hooks in config.toml."""

import json
import os
import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

from .codex_text import CODEX_BEGIN, codex_block, codex_commands, codex_marked
from .conftest import calls, cbm, check_after, events, failed, launcher, mode

HOOKS = "Codex has the SessionStart and SubagentStart CBM hooks"
TOML_HOOKS = "Codex config.toml has no CBM hooks; hooks.json holds them"
SEED = b'{"hooks": {}}\n'


def codex(home: Path) -> Path:
    return home / ".codex"


def commands(home: Path) -> tuple[str, str]:
    return codex_commands(str(launcher(home)))


def test_a_fresh_host_gets_a_seeded_hooks_json_and_verifies(home: Path) -> None:
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 0, done.stdout + done.stderr
    assert failed(done.stdout) == []
    # The installer's own stdout passes through, and it wrote the hooks (src/cli/cli.c:9802-9805).
    assert "  hooks: SessionStart + SubagentStart (dynamic graph context)" in done.stdout.splitlines()
    # The installer found the seed, so it took the JSON path (src/cli/cli.c:9738).
    assert (home / "codex-hooks-seen").read_bytes() == SEED
    command, windows = commands(home)
    hook = {"type": "command", "command": command, "command_windows": windows, "timeout": 5}
    assert json.loads((codex(home) / "hooks.json").read_text()) == {"hooks": {
        "SessionStart": [{"matcher": "startup|resume|clear|compact", "hooks": [hook]}],
        "SubagentStart": [{"matcher": "*", "hooks": [hook]}],
    }}  # fmt: skip
    assert "hooks" not in tomllib.loads((codex(home) / "config.toml").read_text())
    verified = cbm("verify", cwd=home / "checkout")
    assert verified.returncode == 0, verified.stdout
    assert [event["ok"] for event in events(verified.stdout) if event.get("name") == TOML_HOOKS] == [True]
    assert events(verified.stdout)[-1]["outcome"] == "done"


def test_only_codex_is_seeded(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CBM_CLIENTS", "claude")
    assert cbm("install", cwd=home / "checkout").returncode == 0
    assert not codex(home).exists()


def test_an_existing_hooks_json_is_never_replaced(home: Path) -> None:
    mine = b'{ "hooks" :{"Stop": [ {"hooks": [{"type": "command", "command": "mine"}]} ]} }\n'
    codex(home).mkdir()
    (codex(home) / "hooks.json").write_bytes(mine)
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 0, done.stdout + done.stderr
    assert (home / "codex-hooks-seen").read_bytes() == mine
    assert json.loads((codex(home) / "hooks.json").read_text())["hooks"]["Stop"] == json.loads(mine)["hooks"]["Stop"]


def test_a_dangling_hooks_json_link_is_kept_and_fails_verify(home: Path) -> None:
    # Nothing is written through the link. Upstream's stat() misses it and writes the TOML block (cli.c:9738,
    # :9797-9798), which verify then names.
    codex(home).mkdir()
    (codex(home) / "hooks.json").symlink_to(home / "elsewhere.json")
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 1
    assert failed(done.stdout) == [HOOKS, TOML_HOOKS]
    assert (codex(home) / "hooks.json").readlink() == home / "elsewhere.json"
    assert not (home / "elsewhere.json").exists()
    assert not (home / "codex-hooks-seen").exists()
    assert (codex(home) / "config.toml").read_text().endswith(codex_marked(*commands(home)))


def test_a_hooks_json_holding_cbm_and_foreign_hooks_goes_to_the_installer_unchanged(home: Path) -> None:
    # The installer merges hooks.json itself (cli.c:4625-4725); cbm hands it over as it is and verifies the result.
    command, _ = commands(home)
    old = {"type": "command", "command": command, "timeout": 9}
    shared = {"matcher": "startup|resume|clear|compact", "hooks": [old, {"type": "command", "command": "mine"}]}
    before = json.dumps({"hooks": {"SessionStart": [shared]}}).encode()
    codex(home).mkdir()
    (codex(home) / "hooks.json").write_bytes(before)
    assert cbm("install", cwd=home / "checkout").returncode == 0
    assert (home / "codex-hooks-seen").read_bytes() == before
    assert cbm("verify", cwd=home / "checkout").returncode == 0


def test_an_old_toml_block_moves_to_hooks_json(home: Path) -> None:
    # An earlier install without hooks.json left the marked block (cli.c:9797-9798); upstream removes it once
    # the JSON hooks are written (:9791-9796).
    codex(home).mkdir()
    (codex(home) / "config.toml").write_text('model = "gpt"\n\n' + codex_marked(*commands(home)))
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 0, done.stdout + done.stderr
    config = tomllib.loads((codex(home) / "config.toml").read_text())
    assert "hooks" not in config
    assert config["model"] == "gpt"
    assert set(json.loads((codex(home) / "hooks.json").read_text())["hooks"]) == {"SessionStart", "SubagentStart"}
    assert cbm("verify", cwd=home / "checkout").returncode == 0


def test_a_modified_toml_block_is_refused_and_kept(home: Path) -> None:
    modified = codex_marked(*commands(home)).replace("timeout = 5", "timeout = 10", 1)
    codex(home).mkdir()
    (codex(home) / "config.toml").write_text(modified)
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 1
    assert "op=hook_preflight" in done.stderr  # the installer's own line, passed through
    assert "reason=ambiguous_hook_ownership" in done.stderr
    [error] = events(done.stderr)
    assert error["code"] == "codex_hook_migration_refused"
    assert error["path"] == str(codex(home) / "config.toml")
    assert "op=hook_preflight or op=hook_install" in error["message"]
    assert "no such line means it failed before its Codex step" in error["message"]
    assert "Codex CLI:" in done.stdout.splitlines()  # the installer's stdout, passed through before cbm's records
    assert events(done.stdout)[-1] == {
        "event": "done",
        "command": "install",
        "failed": 1,
        "outcome": "failed",
        "message": "cbm: install failed: codex_hook_migration_refused",
    }
    assert (codex(home) / "config.toml").read_text() == modified
    assert "config set auto_index false" not in calls(home)


def test_a_marked_block_with_foreign_commands_is_refused_and_kept(home: Path) -> None:
    # The markers alone do not make a block CBM's: both commands must be (config_toml_edit.c:3490-3491). The hook is
    # not CBM's either, so the failure stays installer_failed.
    foreign = codex_marked("'/usr/bin/other-tool' hook-augment", "& '/usr/bin/other-tool' hook-augment")
    codex(home).mkdir()
    (codex(home) / "config.toml").write_text(foreign)
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 1
    assert "reason=ambiguous_hook_ownership" in done.stderr
    assert [error["code"] for error in events(done.stderr)] == ["installer_failed"]
    assert (codex(home) / "config.toml").read_text() == foreign


def test_a_failed_installer_without_toml_hooks_stays_installer_failed(home: Path) -> None:
    (home / "mode").write_text("fail")
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 1
    assert [error["code"] for error in events(done.stderr)] == ["installer_failed"]
    assert events(done.stdout)[-1]["message"] == "cbm: install failed: installer_failed"


def test_another_failure_beside_a_toml_block_stays_installer_failed(home: Path) -> None:
    # A dangling link sends upstream to config.toml (cli.c:9738, :9797-9798); another step then fails the install.
    codex(home).mkdir()
    (codex(home) / "hooks.json").symlink_to(home / "elsewhere.json")
    mode(home, "other-fails")
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 1
    assert [error["code"] for error in events(done.stderr)] == ["installer_failed"]
    assert (codex(home) / "config.toml").read_text().endswith(codex_marked(*commands(home)))
    assert events(done.stdout)[-1]["message"] == "cbm: install failed: installer_failed"


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes into a mode 0o500 folder, so the seed would not fail")
def test_a_hooks_json_that_cannot_be_written_stops_before_the_installer(home: Path) -> None:
    codex(home).mkdir(mode=0o500)
    try:
        done = cbm("install", cwd=home / "checkout")
    finally:
        codex(home).chmod(0o700)
    assert done.returncode == 1
    assert [error["code"] for error in events(done.stderr)] == ["codex_hooks_seed_failed"]
    assert "install" not in calls(home)
    assert list(codex(home).iterdir()) == []


def test_a_hooks_json_that_cannot_be_seeded_stops_before_the_installer(home: Path) -> None:
    codex(home).write_text("not a folder")
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 1
    [error] = events(done.stderr)
    assert error["code"] == "codex_hooks_seed_failed"
    assert error["path"] == str(codex(home) / "hooks.json")
    assert events(done.stdout)[-1]["outcome"] == "failed"
    assert "install" not in calls(home)
    assert codex(home).read_text() == "not a folder"


def inline(command: str, windows: str, *, legacy: bool = False) -> str:
    # The inline forms upstream recognises (src/cli/config_toml_edit.c:3371-3434, scanned at :3698).
    if legacy:  # the released SessionStart-only echo (config_toml_edit.c:3355-3358)
        hook = 'type = "command", command = "echo \\"Code discovery: prefer codebase-memory-mcp\\""'
    else:
        hook = f'type = "command", command = "{command}", command_windows = "{windows}", timeout = 5'
    return f'hooks.SessionStart = [{{ matcher = "startup|resume|clear|compact", hooks = [{{ {hook} }}] }}]\n'


OLD_BINARY = codex_commands("/old/bin/codebase-memory-mcp")
# Each form a CBM registration takes in config.toml; verify reads the parsed TOML, so markers do not matter.
FORMS: dict[str, Callable[[str, tuple[str, str]], str]] = {
    "marked": lambda text, cmds: text + codex_marked(*cmds),
    "markerless array of tables": lambda text, cmds: text + codex_block(*cmds),
    "markerless, another binary": lambda text, _: text + codex_block(*OLD_BINARY),
    "inline": lambda text, cmds: inline(*cmds) + text,
    "inline legacy echo": lambda text, cmds: inline(*cmds, legacy=True) + text,
    "inline under a hooks table": lambda text, cmds: text + "[hooks]\n" + inline(*cmds).removeprefix("hooks."),
    "windows command only": lambda text, cmds: text + codex_block("echo mine", cmds[1]),
    "after a malformed group": lambda text, cmds: after_malformed(*cmds) + text,
}


def after_malformed(command: str, windows: str) -> str:
    """A CBM hook in a SessionStart list whose first group has a hooks value that is not a list."""
    return inline(command, windows).replace("= [{", "= [{ hooks = 1 }, {", 1)


def test_malformed_hook_levels_in_config_toml_are_not_cbm_hooks(home: Path) -> None:
    assert cbm("install", cwd=home / "checkout").returncode == 0
    path = codex(home) / "config.toml"
    malformed = "hooks.SessionStart = [{ hooks = 1 }, { hooks = [1, { command = 2 }] }, 3]\nhooks.Stop = 4\n"
    path.write_text(malformed + path.read_text())
    done = cbm("verify", cwd=home / "checkout")
    assert done.returncode == 0, done.stdout + done.stderr
    assert [event["ok"] for event in events(done.stdout) if event.get("name") == TOML_HOOKS] == [True]


def test_a_cbm_hook_after_a_malformed_group_is_found_when_the_install_fails(home: Path) -> None:
    text = after_malformed(*commands(home))
    codex(home).mkdir()
    (codex(home) / "config.toml").write_text(text)
    mode(home, "fail")
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 1
    assert [error["code"] for error in events(done.stderr)] == ["codex_hook_migration_refused"]
    assert events(done.stdout)[-1]["message"] == "cbm: install failed: codex_hook_migration_refused"
    assert (codex(home) / "config.toml").read_text() == text


def test_only_malformed_groups_on_a_failed_install_stay_installer_failed(home: Path) -> None:
    codex(home).mkdir()
    (codex(home) / "config.toml").write_text("hooks.SessionStart = [{ hooks = 1 }]\n")
    mode(home, "fail")
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 1
    assert [error["code"] for error in events(done.stderr)] == ["installer_failed"]


def unreadable_install(home: Path) -> subprocess.CompletedProcess[str]:
    """A failed install whose config.toml cannot be read: classification is unavailable, so installer_failed."""
    mode(home, "fail")
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 1
    errors = events(done.stderr)
    assert [error["code"] for error in errors] == ["unreadable_file", "installer_failed"]
    assert errors[0]["path"] == str(codex(home) / "config.toml")
    assert errors[0]["message"].startswith("cbm: cannot read: ")
    assert events(done.stdout)[-1] == {
        "event": "done",
        "command": "install",
        "failed": 1,
        "outcome": "failed",
        "message": "cbm: install failed: installer_failed",
    }
    return done


def test_a_config_toml_folder_after_a_failed_install_stays_installer_failed(home: Path) -> None:
    (codex(home) / "config.toml").mkdir(parents=True)
    unreadable_install(home)
    assert list((codex(home) / "config.toml").iterdir()) == []


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a mode 0o000 file, so the read would not fail")
def test_an_unreadable_config_toml_after_a_failed_install_stays_installer_failed(home: Path) -> None:
    text = codex_marked(*commands(home))
    path = codex(home) / "config.toml"
    codex(home).mkdir()
    path.write_text(text)
    path.chmod(0o000)
    try:
        unreadable_install(home)
    finally:
        path.chmod(0o600)
    assert path.read_text() == text


def test_verify_reports_a_config_toml_it_cannot_read(home: Path) -> None:
    assert cbm("install", cwd=home / "checkout").returncode == 0
    path = codex(home) / "config.toml"
    path.unlink()
    path.mkdir()
    done = cbm("verify", cwd=home / "checkout")
    assert done.returncode == 1
    [error] = events(done.stderr)
    assert error["code"] == "unreadable_file"
    assert error["path"] == str(path)
    assert events(done.stdout)[-1]["outcome"] == "failed"


@pytest.mark.parametrize("form", list(FORMS))
def test_a_cbm_hook_in_config_toml_beside_hooks_json_fails_verify(home: Path, form: str) -> None:
    path = codex(home) / "config.toml"
    done = check_after(home, lambda: path.write_text(FORMS[form](path.read_text(), commands(home))), TOML_HOOKS)
    [check] = [event for event in events(done.stdout) if event.get("name") == TOML_HOOKS]
    assert "SessionStart" in check["detail"]
    assert CODEX_BEGIN in path.read_text() or form != "marked"


def test_a_foreign_hook_in_config_toml_passes(home: Path) -> None:
    assert cbm("install", cwd=home / "checkout").returncode == 0
    path = codex(home) / "config.toml"
    path.write_text(path.read_text() + codex_block("'/usr/bin/other-tool' hook-augment", "& other hook-augment"))
    done = cbm("verify", cwd=home / "checkout")
    assert done.returncode == 0, done.stdout


def test_verify_reports_a_hooks_json_it_cannot_read(home: Path) -> None:
    assert cbm("install", cwd=home / "checkout").returncode == 0
    path = codex(home) / "hooks.json"
    path.unlink()
    path.mkdir()
    done = cbm("verify", cwd=home / "checkout")
    assert done.returncode == 1, done.stdout + done.stderr
    [error] = events(done.stderr)
    assert error["code"] == "unreadable_file"
    assert error["path"] == str(path)
    assert error["message"].startswith("cbm: cannot read: ")
    assert failed(done.stdout) == [HOOKS]
    assert events(done.stdout)[-1]["outcome"] == "failed"


@pytest.mark.parametrize("value", ["[]", "1", '"hooks"', "null"])
def test_a_hooks_json_that_is_not_an_object_fails_its_check(home: Path, value: str) -> None:
    assert cbm("install", cwd=home / "checkout").returncode == 0
    path = codex(home) / "hooks.json"
    path.write_text(value)
    done = cbm("verify", cwd=home / "checkout")
    assert done.returncode == 1, done.stdout + done.stderr
    [error] = events(done.stderr)
    assert error["code"] == "invalid_json"
    assert error["path"] == str(path)
    assert error["message"] == "cbm: expected a JSON object at the top level"
    assert failed(done.stdout) == [HOOKS]


MALFORMED_JSON_GROUPS = [1, {"hooks": 1}, {"matcher": "*", "hooks": [1, {"command": 2}, {"type": []}]}]


@pytest.mark.parametrize(
    "hooks", [[], 4, {"SessionStart": 4}, {"SessionStart": MALFORMED_JSON_GROUPS, "SubagentStart": [None]}]
)
def test_malformed_hooks_json_levels_fail_the_hooks_check(home: Path, hooks: object) -> None:
    path = codex(home) / "hooks.json"
    done = check_after(home, lambda: path.write_text(json.dumps({"hooks": hooks})), HOOKS)
    assert not events(done.stderr)


def test_malformed_groups_beside_the_cbm_hooks_in_hooks_json_are_not_cbm_hooks(home: Path) -> None:
    assert cbm("install", cwd=home / "checkout").returncode == 0
    path = codex(home) / "hooks.json"
    settings = json.loads(path.read_text())
    settings["hooks"]["SessionStart"][:0] = MALFORMED_JSON_GROUPS
    settings["hooks"]["Stop"] = 4
    path.write_text(json.dumps(settings))
    done = cbm("verify", cwd=home / "checkout")
    assert done.returncode == 0, done.stdout + done.stderr


def test_a_cbm_hook_under_a_matcher_that_is_not_text_fails_the_hooks_check(home: Path) -> None:
    assert cbm("install", cwd=home / "checkout").returncode == 0
    path = codex(home) / "hooks.json"
    settings = json.loads(path.read_text())
    settings["hooks"]["SessionStart"][0]["matcher"] = ["startup"]
    done = check_after(home, lambda: path.write_text(json.dumps(settings)), HOOKS)
    [check] = [event for event in events(done.stdout) if event.get("name") == HOOKS]
    assert "['startup']" in check["detail"]


def test_a_fifo_config_toml_after_a_failed_install_stays_installer_failed(home: Path) -> None:
    # A FIFO would block a plain read forever; it is reported as unreadable and the failure events still come.
    codex(home).mkdir()
    os.mkfifo(codex(home) / "config.toml")
    unreadable_install(home)
    assert (codex(home) / "config.toml").is_fifo()


def test_invalid_utf8_in_config_toml_after_a_failed_install_stays_installer_failed(home: Path) -> None:
    codex(home).mkdir()
    (codex(home) / "config.toml").write_bytes(b'model = "\xff"\n')
    unreadable_install(home)
    assert (codex(home) / "config.toml").read_bytes() == b'model = "\xff"\n'


@pytest.mark.parametrize("kind", ["fifo", "invalid utf-8"])
def test_verify_reports_a_hooks_json_it_cannot_decode_or_should_not_open(home: Path, kind: str) -> None:
    assert cbm("install", cwd=home / "checkout").returncode == 0
    path = codex(home) / "hooks.json"
    path.unlink()
    if kind == "fifo":
        os.mkfifo(path)
    else:
        path.write_bytes(b'{"hooks": "\xff"}')
    done = cbm("verify", cwd=home / "checkout")
    assert done.returncode == 1, done.stdout + done.stderr
    [error] = events(done.stderr)
    assert error["code"] == "unreadable_file"
    assert error["path"] == str(path)
    assert error["message"].startswith("cbm: cannot read: ")
    assert failed(done.stdout) == [HOOKS]
    assert events(done.stdout)[-1]["outcome"] == "failed"
