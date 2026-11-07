"""repotools scratch-env in-process: one command with every home path in a scratch folder, in a stand-in checkout."""

import json
import os
import shutil
import sysconfig
from pathlib import Path

import pytest

from repotools.cli import main

HOME_PATHS = {
    "HOME": "home",
    "TMPDIR": "tmp",
    "XDG_CONFIG_HOME": "config",
    "XDG_DATA_HOME": "data",
    "XDG_STATE_HOME": "state",
    "XDG_CACHE_HOME": "cache",
}
# mise, and the system tools the commands below use.
CALLER = os.pathsep.join([str(Path(shutil.which("mise") or "mise").parent), "/usr/bin", "/bin"])


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A checkout at tmp/repo holding only a mise.toml, as the current folder, and the caller's PATH."""
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo/mise.toml").write_text("[env]\nSTAND_IN = '1'\n")
    monkeypatch.chdir(tmp_path / "repo")
    monkeypatch.setenv("PATH", CALLER)
    return tmp_path / "repo"


def scratch(capfd: pytest.CaptureFixture[str], *argv: str | Path) -> tuple[int, str, str]:
    """The exit code, stdout and stderr of repotools scratch-env."""
    try:
        main(["scratch-env", *map(str, argv)])
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    out, err = capfd.readouterr()
    return code, out, err


def test_the_command_sees_only_the_scratch_paths(repo: Path, tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, out, err = scratch(capfd, tmp_path / "scratch", "/usr/bin/env")
    assert code == 0, err
    assert dict(line.split("=", 1) for line in out.splitlines()) == {
        **{name: str(tmp_path / "scratch" / folder) for name, folder in HOME_PATHS.items()},
        "USER": os.environ["USER"],
        "PATH": CALLER,
        "TERM": "dumb",
        "MISE_TRUSTED_CONFIG_PATHS": str(repo),
        "MISE_CEILING_PATHS": str(tmp_path),
        "MISE_AUTO_INSTALL": "0",
    }
    assert all((tmp_path / "scratch" / folder).is_dir() for folder in HOME_PATHS.values())


@pytest.mark.usefixtures("repo")
@pytest.mark.parametrize("caller", ["elsewhere", None])
def test_a_relative_folder_is_the_callers(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str], caller: str | None
) -> None:
    # From `mise run`, the folder it started in; run directly, the current one.
    base = tmp_path / caller if caller else repo
    if caller:
        monkeypatch.setenv("MISE_ORIGINAL_CWD", str(base))
    else:
        monkeypatch.delenv("MISE_ORIGINAL_CWD", raising=False)
    code, out, err = scratch(capfd, "scratch", "/usr/bin/printenv", "HOME")
    assert (code, out) == (0, f"{base / 'scratch/home'}\n"), err
    assert (base / "scratch/home").is_dir()


def test_the_venvs_own_path_entries_stay_out(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    # uv run puts the venv in front once; the caller's own copy behind it stays.
    scripts = sysconfig.get_path("scripts")
    monkeypatch.setenv("PATH", os.pathsep.join([scripts, scripts, CALLER]))
    code, out, _err = scratch(capfd, tmp_path / "scratch", "/bin/sh", "-c", 'printf %s "$PATH"')
    assert (code, out) == (0, os.pathsep.join([scripts, CALLER]))


def test_exit_code_and_both_streams_pass_through(repo: Path, tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, out, err = scratch(capfd, tmp_path / "scratch", "/bin/sh", "-c", "pwd; echo err >&2; exit 7")
    assert (code, out) == (7, f"{repo}\n")
    # The receipt that the climb stopped comes first: the only config is the checkout's.
    receipt, last = err.rsplit("\n", 2)[:2]
    assert str(repo / "mise.toml").replace(str(Path.home()), "~") in receipt
    assert last == "err"


@pytest.mark.usefixtures("repo")
def test_a_signal_reads_as_a_shell_reports_it(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    code, _out, _err = scratch(capfd, tmp_path / "scratch", "/bin/sh", "-c", "kill -TERM $$")
    assert code == 128 + 15


@pytest.mark.usefixtures("repo")
def test_a_command_that_cant_start_exits_as_env_does(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "plain").write_text("not a program\n")
    missing = scratch(capfd, tmp_path / "scratch", tmp_path / "missing")
    assert missing[:2] == (127, "")
    assert json.loads(missing[2].splitlines()[-1]) == {"error": f"{tmp_path / 'missing'}: No such file or directory"}
    plain = scratch(capfd, tmp_path / "scratch", tmp_path / "plain")
    assert plain[:2] == (126, "")
    assert json.loads(plain[2].splitlines()[-1]) == {"error": f"{tmp_path / 'plain'}: Permission denied"}


@pytest.mark.usefixtures("repo")
def test_a_used_folder_keeps_what_it_holds(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "scratch/home").mkdir(parents=True)
    (tmp_path / "scratch/home/kept").write_text("kept\n")
    assert scratch(capfd, tmp_path / "scratch", "/bin/cat", tmp_path / "scratch/home/kept")[:2] == (0, "kept\n")


@pytest.mark.parametrize("argv", [[], ["folder"]])
def test_a_missing_folder_or_command_refuses(repo: Path, capfd: pytest.CaptureFixture[str], argv: list[str]) -> None:
    code, out, err = scratch(capfd, *argv)
    assert (code, out) == (1, "")
    assert '"error"' in err
    assert not (repo / "folder").exists()
