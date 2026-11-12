"""secret-set through the real fnox, against a scratch fnox config and a stand-in doppler that records each call."""

import json
import os
import pty
import shutil
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from hometools import cli, secret

# doppler is the only program that reaches the network (CODING_STANDARDS 2): this stand-in, linked as `doppler`
# ahead of the real one, logs its argv, the token and the other secret fnox exec gave it, and its stdin, one JSON
# line per call in $STAND_IN_FOLDER/calls.jsonl. `secrets --only-names --json` answers names.txt, exiting
# names.code; `secrets set` exits set.code; a file named unlink-doppler makes the first call remove itself.
STAND_IN = """
import json, os, sys
from pathlib import Path
folder = Path(os.environ["STAND_IN_FOLDER"])
call = {"argv": sys.argv[1:], "token": os.environ.get("DOPPLER_TOKEN"), "other": os.environ.get("OTHER")}
call["host"] = os.environ.get("DOPPLER_API_HOST")
call["stdin"] = sys.stdin.read() if sys.argv[2] == "set" else None
with (folder / "calls.jsonl").open("a") as log:
    log.write(json.dumps(call) + "\\n")
if (folder / "unlink-doppler").exists():
    (folder / "bin/doppler").unlink()
if sys.argv[1:3] == ["secrets", "--only-names"]:
    sys.stdout.write((folder / "names.txt").read_text())
    raise SystemExit(int((folder / "names.code").read_text()))
raise SystemExit(int((folder / "set.code").read_text()))
"""

# A plain provider stands in for the Keychain: the write token is a test string, and OTHER, a second secret, shows
# that only the token reaches doppler.
CONFIG = """
[providers.plain]
type = "plain"

[secrets]
OTHER = { provider = "plain", value = "another-secret" }
DOPPLER_WRITE_TOKEN = { provider = "plain", value = "write-token-for-tests" }
"""

PEM = "-----BEGIN RSA PRIVATE KEY-----\nAAAA\nBBBB\n-----END RSA PRIVATE KEY-----\n"
TAIL = ["--project", "dotfiles", "--config", "dev_personal"]
LIST = ["secrets", "--only-names", "--json", *TAIL]
SET = ["secrets", "set", "NEW_KEY", "--silent", "--no-interactive", *TAIL]


@dataclass
class Doppler:
    folder: Path

    def answer(self, names: str = '{"EXISTING": {}}', names_code: int = 0, set_code: int = 0) -> None:
        (self.folder / "names.txt").write_text(names)
        (self.folder / "names.code").write_text(str(names_code))
        (self.folder / "set.code").write_text(str(set_code))

    def calls(self) -> list[dict[str, object]]:
        log = self.folder / "calls.jsonl"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


@pytest.fixture
def doppler(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Doppler:
    fnox = shutil.which("fnox")
    if fnox is None:
        pytest.skip("fnox is a global mise tool")
    home = tmp_path / "home"
    (home / ".config/fnox").mkdir(parents=True)
    (home / ".config/fnox/config.toml").write_text(CONFIG)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    program = bin_dir / "doppler"
    program.write_text(f"#!{sys.executable} -I\n{STAND_IN}")
    program.chmod(0o755)
    (bin_dir / "fnox").symlink_to(Path(fnox).resolve())
    for name in [name for name in os.environ if name.startswith(("FNOX_", "DOPPLER_"))]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("STAND_IN_FOLDER", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    stand_in = Doppler(tmp_path)
    stand_in.answer()
    return stand_in


@pytest.fixture
def stdin() -> Iterator[Callable[[int], None]]:
    """Puts a descriptor on this process's file descriptor 0, as a shell does, and puts pytest's back after."""
    saved = os.dup(0)

    def attach(fd: int) -> None:
        os.dup2(fd, 0)
        os.close(fd)

    yield attach
    os.dup2(saved, 0)
    os.close(saved)


@pytest.fixture
def pipe_in(stdin: Callable[[int], None]) -> Callable[[str], None]:
    """A real pipe on stdin holding value, as `pbpaste | mise run secret:set NAME` gives one."""

    def fill(value: str) -> None:
        read, write = os.pipe()
        os.write(write, value.encode())
        os.close(write)
        stdin(read)

    return fill


def refused(capsys: pytest.CaptureFixture[str], name: str) -> str:
    with pytest.raises(SystemExit) as stopped:
        secret.set_secret(name)
    assert stopped.value.code == 1
    return json.loads(capsys.readouterr().err)["error"]


def test_stores_a_multiline_value(
    doppler: Doppler,
    pipe_in: Callable[[str], None],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Only the write token reaches doppler: an inherited DOPPLER_* variable does not.
    monkeypatch.setenv("DOPPLER_API_HOST", "https://inherited.invalid")
    monkeypatch.setenv("DOPPLER_TOKEN", "inherited-token")
    pipe_in(PEM)
    secret.set_secret("NEW_KEY")
    listed, stored = doppler.calls()
    assert listed == {"argv": LIST, "token": "write-token-for-tests", "other": None, "host": None, "stdin": None}
    assert stored == {"argv": SET, "token": "write-token-for-tests", "other": None, "host": None, "stdin": PEM}
    assert capsys.readouterr().out == "secret:set: stored NEW_KEY in dotfiles/dev_personal\n"


@pytest.mark.parametrize("name", ["lower_case", "MIXED_Case", "_LEADING", "TRAILING_", "DOUBLE__UNDERSCORE", "9X", ""])
def test_refuses_a_name_not_upper_snake(
    doppler: Doppler, pipe_in: Callable[[str], None], capsys: pytest.CaptureFixture[str], name: str
) -> None:
    pipe_in(PEM)
    assert refused(capsys, name) == "secret:set: the name is not UPPER_SNAKE"
    assert doppler.calls() == []


@pytest.mark.parametrize("value", ["", " \n\t\n"])
def test_refuses_an_empty_value(
    doppler: Doppler, pipe_in: Callable[[str], None], capsys: pytest.CaptureFixture[str], value: str
) -> None:
    pipe_in(value)
    assert refused(capsys, "NEW_KEY") == "secret:set: the value is empty"
    assert doppler.calls() == []


def test_refuses_a_terminal(doppler: Doppler, stdin: Callable[[int], None], capsys: pytest.CaptureFixture[str]) -> None:
    leader, follower = pty.openpty()
    os.close(leader)
    stdin(follower)
    error = refused(capsys, "NEW_KEY")
    assert error == "secret:set: pipe the value in, for example: pbpaste | mise run secret:set NAME"
    assert doppler.calls() == []


def test_refuses_a_name_doppler_has(
    doppler: Doppler, pipe_in: Callable[[str], None], capsys: pytest.CaptureFixture[str]
) -> None:
    pipe_in(PEM)
    error = refused(capsys, "EXISTING")
    assert error == "secret:set: EXISTING already exists in dotfiles/dev_personal; change it in the Doppler dashboard"
    assert [call["argv"] for call in doppler.calls()] == [LIST]


def test_stops_when_the_names_cannot_be_listed(
    doppler: Doppler, pipe_in: Callable[[str], None], capsys: pytest.CaptureFixture[str]
) -> None:
    doppler.answer(names_code=3)
    pipe_in(PEM)
    assert refused(capsys, "NEW_KEY") == "secret:set: listing the names in dotfiles/dev_personal failed (exit 3)"
    assert [call["argv"] for call in doppler.calls()] == [LIST]


@pytest.mark.parametrize("names", ["not json", '["NEW_KEY"]'])
def test_stops_when_the_names_are_not_an_object(
    doppler: Doppler, pipe_in: Callable[[str], None], capsys: pytest.CaptureFixture[str], names: str
) -> None:
    doppler.answer(names=names)
    pipe_in(PEM)
    error = refused(capsys, "NEW_KEY")
    assert (
        error == "secret:set: doppler listed the names in dotfiles/dev_personal as something other than a JSON object"
    )


def test_stops_when_the_set_fails(
    doppler: Doppler, pipe_in: Callable[[str], None], capsys: pytest.CaptureFixture[str]
) -> None:
    doppler.answer(set_code=4)
    pipe_in(PEM)
    assert refused(capsys, "NEW_KEY") == "secret:set: doppler secrets set NEW_KEY failed (exit 4)"
    assert [call["argv"] for call in doppler.calls()] == [LIST, SET]


def test_stops_when_fnox_cannot_start_to_list(
    doppler: Doppler,
    pipe_in: Callable[[str], None],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (doppler.folder / "bin/fnox").unlink()
    monkeypatch.setenv("PATH", str(doppler.folder / "bin"))
    pipe_in(PEM)
    assert refused(capsys, "NEW_KEY") == "secret:set: fnox: No such file or directory"


def test_stops_when_doppler_cannot_start_to_list(
    doppler: Doppler,
    pipe_in: Callable[[str], None],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (doppler.folder / "bin/doppler").unlink()
    monkeypatch.setenv("PATH", str(doppler.folder / "bin"))
    pipe_in(PEM)
    assert refused(capsys, "NEW_KEY") == "secret:set: doppler: No such file or directory"
    assert doppler.calls() == []


def test_stops_when_doppler_cannot_start_to_set(
    doppler: Doppler,
    pipe_in: Callable[[str], None],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The listing call removes the only doppler on PATH, so the set call's doppler cannot start.
    (doppler.folder / "unlink-doppler").touch()
    monkeypatch.setenv("PATH", f"{doppler.folder / 'bin'}{os.pathsep}/usr/bin")
    pipe_in(PEM)
    assert refused(capsys, "NEW_KEY") == "secret:set: doppler: No such file or directory"
    assert [call["argv"] for call in doppler.calls()] == [LIST]


def test_stops_when_fnox_has_no_write_token(
    doppler: Doppler, pipe_in: Callable[[str], None], capsys: pytest.CaptureFixture[str]
) -> None:
    config = doppler.folder / "home/.config/fnox/config.toml"
    config.write_text(
        CONFIG.replace('DOPPLER_WRITE_TOKEN = { provider = "plain", value = "write-token-for-tests" }', "")
    )
    pipe_in(PEM)
    assert refused(capsys, "NEW_KEY").startswith(
        "secret:set: fnox could not read DOPPLER_WRITE_TOKEN from the Keychain"
    )
    assert doppler.calls() == []


@pytest.mark.usefixtures("doppler")
def test_cli_runs_secret_set(pipe_in: Callable[[str], None], capsys: pytest.CaptureFixture[str]) -> None:
    pipe_in(PEM)
    cli.main(["secret-set", "NEW_KEY"])
    assert capsys.readouterr().out == "secret:set: stored NEW_KEY in dotfiles/dev_personal\n"


@pytest.mark.parametrize("argv", [["secret-set"], ["update-check", "NAME"]])
def test_cli_takes_a_name_only_for_secret_set(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as stopped:
        cli.main(argv)
    assert stopped.value.code == 2
    assert "secret-set takes one NAME; the other commands take none" in capsys.readouterr().err
