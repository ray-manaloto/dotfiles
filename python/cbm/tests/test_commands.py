"""Command routing and process context, observed through the installed cbm command."""

import json
from pathlib import Path

import pytest

from .conftest import calls, cbm, events, git, launcher, link, provision


@pytest.mark.parametrize(
    "args",
    [
        ["upgrade"],
        ["upgrade", "check"],
        ["upgrade", "trial"],
        ["upgrade", "trial", "--candidate", "9.9.10"],
        ["upgrade", "review"],
        ["upgrade", "prepare"],
        ["accept", "change-id", "--reason", "private explanation", "--public-reason", "public explanation"],
        ["accept", "change-id", "--reason=-x", "--public-reason=-y"],
    ],
)
def test_future_commands_are_recognized_but_do_not_change_setup(home: Path, args: list[str]) -> None:
    done = cbm(*args)
    assert done.returncode == 1
    assert events(done.stderr) == [
        {
            "event": "error",
            "code": "command_failed",
            "message": f"cbm: {args[0]} is not implemented yet",
            "path": None,
        }
    ]
    assert not done.stdout
    assert not calls(home)
    assert not launcher(home).exists()
    assert not (home / ".claude").exists()
    assert not (home / ".codex").exists()


@pytest.mark.parametrize(
    "args",
    [
        ["upgrade", "unknown"],
        ["upgrade", "check", "extra"],
        ["upgrade", "check", "--candidate", "9.9.10"],
        ["upgrade", "--candidate", "9.9.10"],
        ["upgrade", "trial", "--candidate"],
        ["upgrade", "trial", "--cand", "9.9.10"],
        ["upgrade", "trial", "--unknown"],
        ["accept"],
        ["accept", "change-id", "--reason", "private explanation"],
        ["accept", "change-id", "--public-reason", "public explanation"],
        ["accept", "change-id", "--reason", "private", "--public-reason", "public", "extra"],
    ],
)
def test_bad_future_command_syntax_is_a_usage_error(home: Path, args: list[str]) -> None:
    done = cbm(*args)
    assert done.returncode == 2
    [error] = events(done.stderr)
    assert error["code"] == "invalid_usage"
    assert error["message"].startswith(f"usage: cbm {args[0]}")
    assert not done.stdout
    assert not calls(home)


@pytest.mark.parametrize("columns", ["20", "50", "200"])
def test_usage_message_is_independent_of_terminal_width(
    home: Path, monkeypatch: pytest.MonkeyPatch, columns: str
) -> None:
    monkeypatch.setenv("COLUMNS", columns)
    done = cbm("accept")
    assert done.returncode == 2
    [error] = events(done.stderr)
    assert error["code"] == "invalid_usage"
    assert error["message"] == "usage: cbm accept --reason REASON --public-reason PUBLIC_REASON change_id"
    assert not calls(home)


@pytest.mark.parametrize("force", [False, True])
def test_verify_detects_a_corrupt_reused_build_unless_explicitly_replaced(
    home: Path, upgrade_home: dict[str, Path], *, force: bool
) -> None:
    assert cbm("install", cwd=upgrade_home["worktree"]).returncode == 0
    tool = "github:DeusData/codebase-memory-mcp@9.9.10"
    provision(home, tool)
    selected = link(home).parent.parent / "9.9.10"
    binary = selected / "codebase-memory-mcp"
    link(home).parent.unlink()
    link(home).parent.symlink_to(selected, target_is_directory=True)
    corrupt = b"a damaged reused executable\n"
    binary.write_bytes(corrupt)
    # Provisioning is test setup, like creating the temporary git repos. Ordinary mise installation
    # must leave reused bytes intact; the observable check remains the installed cbm command.
    provision(home, tool, *(["--force"] if force else []))
    done = cbm("verify", cwd=upgrade_home["worktree"])
    assert done.returncode == (0 if force else 1)
    assert events(done.stdout)[-1]["outcome"] == ("done" if force else "failed")
    if force:
        assert "codebase-memory-mcp 9.9.10" in done.stdout
        assert not done.stderr
    else:
        assert binary.read_bytes() == corrupt
        assert {error["code"] for error in events(done.stderr)} == {"command_failed"}


@pytest.mark.parametrize("version", ["9.9.9", "9.9.10"])
def test_setup_keeps_the_global_build_and_live_context(
    home: Path, upgrade_home: dict[str, Path], monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    # Provision a preinstalled build from the local release archive; install/verify never run mise.
    release = json.loads((home / "mise-fixture.json").read_text())["releases"][version]
    selected = Path(release["installed"])
    provision(home, f"github:DeusData/codebase-memory-mcp@{version}")
    binary = selected / "codebase-memory-mcp"
    link(home).parent.unlink()
    link(home).parent.symlink_to(selected, target_is_directory=True)
    monkeypatch.setenv("CBM_RUNTIME_DIR", str(home / "trial-runtime"))
    monkeypatch.setenv("CBM_CACHE_DIR", str(home / "trial-cache"))
    monkeypatch.setenv("CBM_TEST_SENTINEL", "preserve this value")
    provisioned = (home / "mise-calls.jsonl").read_bytes()

    installed = cbm("install", cwd=upgrade_home["worktree"])
    assert installed.returncode == 0, installed.stdout + installed.stderr
    verified = cbm("verify", cwd=upgrade_home["worktree"])
    assert verified.returncode == 0, verified.stdout + verified.stderr
    assert events(verified.stdout)[-1]["outcome"] == "done"
    recorded = events((home / "processes.jsonl").read_text())
    assert {row["launcher"] for row in recorded} == {str(link(home)), str(launcher(home))}
    for row in recorded:
        assert row["version"] == version
        assert row["executable"] == str(binary)
        assert row["home"] == str(home)
        assert row["cwd"] == str(home)
        assert row["runtime"] is None
        assert row["cache"] is None
        assert row["sentinel"] == "preserve this value"
    assert git(upgrade_home["worktree"], "status", "--porcelain") == ""
    assert (home / "mise-calls.jsonl").read_bytes() == provisioned
