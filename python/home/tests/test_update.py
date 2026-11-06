"""update-brew and update-check in-process on the scratch toolchain: each path of each."""

# brew list --pinned and mise run toolchain:verify run for real on the scratch toolchain (tests/scratch_toolchain.py).
# brew update, brew upgrade, brew outdated, mise outdated and mise upgrade download or read the network, so
# tests/stand_in.py answers them from a script (CODING_STANDARDS 2).

import json
import shlex
import signal
import sys
from pathlib import Path

import pytest

from hometools.cli import main

from .scratch_toolchain import Scratch

STAND_IN = Path(__file__).with_name("stand_in.py")
REAL: dict[str, object] = {"real": True}
PINNED, VERIFY = "brew list --pinned", "mise run toolchain:verify"
BREW, MISE, DRY = "brew outdated --json", "mise outdated --json", "mise upgrade --dry-run-code"
NONE_OUTDATED: dict[str, object] = {"stdout": '{"formulae": [], "casks": []}\n'}


class Tools:
    """The stand-ins' folder on the scratch toolchain: what each call answers, and the calls made."""

    def __init__(self, folder: Path, tc: Scratch) -> None:
        self.folder, self.tc = folder, tc

    def answer(self, calls: dict[str, dict[str, object]]) -> None:
        """calls in shell form: the stand-in keys each by its argv."""
        script = {json.dumps(shlex.split(call)): answer for call, answer in calls.items()}
        (self.folder / "script.json").write_text(json.dumps(script))

    def calls(self) -> list[str]:
        """The calls made, in shell form: an argument with a space in it stays quoted."""
        log = self.folder / "calls.jsonl"
        return [shlex.join(json.loads(line)) for line in log.read_text().splitlines()] if log.exists() else []

    def without_brew(self) -> None:
        """No brew on PATH: neither the stand-in nor the scratch prefix's."""
        (self.folder / "brew").unlink()
        self.tc.unlink(self.tc.prefix / "bin/brew")


@pytest.fixture
def tools(toolchain: Scratch, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Tools:
    """brew and mise stood in ahead of the scratch toolchain's on PATH."""
    folder = tmp_path / "stand-in"
    folder.mkdir()
    for name in ("brew", "mise"):
        (folder / name).symlink_to(STAND_IN)
    monkeypatch.setenv("PATH", f"{folder}:{toolchain.env()['PATH']}")
    monkeypatch.setenv("STAND_IN", str(folder))
    # toolchain:verify runs hometools through uv, offline: this Python, not one it would download.
    monkeypatch.setenv("UV_PYTHON", str(Path(sys.base_prefix) / "bin/python3"))
    return Tools(folder, toolchain)


def hometools(capfd: pytest.CaptureFixture[str], command: str) -> tuple[int, str, str]:
    try:
        main([command])
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    out, err = capfd.readouterr()
    return code, out, err


def error(err: str) -> str:
    """The Failure event the command ended with."""
    return json.loads(err.splitlines()[-1])["error"]


def test_update_brew_refuses_on_the_first_unpinned_package(tools: Tools, capfd: pytest.CaptureFixture[str]) -> None:
    tools.tc.unlink(tools.tc.prefix / "var/homebrew/pinned/llvm")
    tools.tc.unlink(tools.tc.prefix / "var/homebrew/pinned/pkgconf")
    tools.answer({PINNED: REAL})
    code, out, err = hometools(capfd, "update-brew")
    line = "update:brew: llvm is not pinned; run 'brew pin llvm' or do a planned toolchain upgrade (DL-595)"
    assert (code, out, error(err)) == (1, "", line)
    assert tools.calls() == [PINNED]


def test_update_brew_updates_upgrades_and_verifies(tools: Tools, capfd: pytest.CaptureFixture[str]) -> None:
    tools.answer(
        {PINNED: REAL, "brew update": {"stdout": "Already up-to-date.\n"}, "brew upgrade --yes": {}, VERIFY: REAL}
    )
    code, out, err = hometools(capfd, "update-brew")
    assert code == 0, err
    assert out.startswith("Already up-to-date.\n")
    assert out.splitlines()[-1].startswith("toolchain:verify OK: ")
    assert tools.calls() == [PINNED, "brew update", "brew upgrade --yes", VERIFY]


@pytest.mark.parametrize("failing", ["brew update", "brew upgrade --yes"])
def test_update_brew_stops_with_a_failed_steps_exit_code(
    tools: Tools, capfd: pytest.CaptureFixture[str], failing: str
) -> None:
    steps = [PINNED, "brew update", "brew upgrade --yes"]
    tools.answer({PINNED: REAL, "brew update": {}, failing: {"stderr": "it broke\n", "code": 4}})
    code, _out, err = hometools(capfd, "update-brew")
    assert (code, err.splitlines()[0], error(err)) == (4, "it broke", f"{failing} exited 4")
    assert tools.calls() == steps[: steps.index(failing) + 1]


def test_update_brew_exits_128_plus_the_signal_that_killed_a_step(
    tools: Tools, capfd: pytest.CaptureFixture[str]
) -> None:
    tools.answer({PINNED: REAL, "brew update": {"signal": signal.SIGTERM}})
    code, _out, err = hometools(capfd, "update-brew")
    assert (code, error(err)) == (143, "brew update exited 143")
    assert tools.calls() == [PINNED, "brew update"]


def test_update_brew_fails_when_the_toolchain_fails_to_verify(tools: Tools, capfd: pytest.CaptureFixture[str]) -> None:
    tools.tc.hold(llvm_major="1")
    tools.answer({PINNED: REAL, "brew update": {}, "brew upgrade --yes": {}, VERIFY: REAL})
    code, _out, err = hometools(capfd, "update-brew")
    assert (code, error(err)) == (1, f"{VERIFY} exited 1")
    assert "is not 1.x" in err
    assert tools.calls() == [PINNED, "brew update", "brew upgrade --yes", VERIFY]


def test_update_brew_without_brew_exits_127(tools: Tools, capfd: pytest.CaptureFixture[str]) -> None:
    tools.without_brew()
    code, out, err = hometools(capfd, "update-brew")
    assert (code, out, error(err)) == (127, "", "brew: No such file or directory")


@pytest.mark.parametrize(
    ("answers", "want"),
    [
        ((NONE_OUTDATED, {"stdout": "{}\n"}, {}), 0),
        (({"stdout": '{"formulae": [{"name": "jq"}], "casks": []}'}, {"stdout": "{}"}, {}), 1),
        (({"stdout": '{"formulae": [], "casks": [{"name": "docker-desktop"}]}'}, {"stdout": "{}"}, {}), 1),
        ((NONE_OUTDATED, {"stdout": '{"jq": {"current": "1.8.1", "latest": "1.8.2"}}'}, {}), 1),
        ((NONE_OUTDATED, {"stdout": "{}"}, {"stdout": "Would upgrade jq\n", "code": 1}), 1),
    ],
    ids=["in-sync", "formula", "cask", "mise-tool", "mise-upgrade"],
)
def test_update_check_prints_every_report_and_exits_on_drift(
    tools: Tools, capfd: pytest.CaptureFixture[str], answers: tuple[dict[str, object], ...], want: int
) -> None:
    """answers: brew outdated's, mise outdated's and mise upgrade's."""
    brew, mise, dry = answers
    tools.answer({BREW: brew, MISE: mise, DRY: dry})
    code, out, err = hometools(capfd, "update-check")
    reports = [str(brew["stdout"]).rstrip("\n"), str(mise["stdout"]).rstrip("\n")]
    assert (code, out, err) == (want, "\n".join(reports) + "\n" + str(dry.get("stdout", "")), "")
    assert tools.calls() == [BREW, MISE, DRY]


@pytest.mark.parametrize(
    ("brew", "mise", "source"),
    [
        ({"code": 1}, {}, "brew outdated"),
        ({"stdout": "Error: no JSON\n"}, {}, "brew outdated"),
        ({"stdout": "[]\n"}, {}, "brew outdated"),
        ({"stdout": ""}, {}, "brew outdated"),
        (NONE_OUTDATED, {"code": 1}, "mise outdated"),
        (NONE_OUTDATED, {"stdout": "mise WARN something\n"}, "mise outdated"),
        ({"stdout": '{"formulae": [{"name": "jq"}], "casks": []}'}, {"stdout": "oops\n"}, "mise outdated"),
    ],
    ids=[
        "brew-fails",
        "brew-not-json",
        "brew-not-an-object",
        "brew-empty",
        "mise-fails",
        "mise-not-json",
        "brew-drift-mise-not-json",
    ],
)
def test_update_check_exits_2_when_a_source_cannot_answer(
    tools: Tools, capfd: pytest.CaptureFixture[str], brew: dict[str, object], mise: dict[str, object], source: str
) -> None:
    tools.answer({BREW: brew, MISE: mise})
    code, _out, err = hometools(capfd, "update-check")
    assert (code, error(err)) == (2, f"update:check: '{source}' failed — COULD NOT CHECK")
    assert DRY not in tools.calls()


def test_update_check_counts_a_mise_upgrade_that_cannot_start_as_drift(
    tools: Tools, capfd: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mise answers outdated, then is gone: the shell task's `mise upgrade ... || drift=1` exited 1."""
    # On PATH only the stand-ins and the python3 they start with, so no other mise is found.
    python = tmp_path / "python"
    python.mkdir()
    (python / "python3").symlink_to(Path(sys.base_prefix) / "bin/python3")
    monkeypatch.setenv("PATH", f"{tools.folder}:{python}")
    # mise outdated runs this: it removes the mise stand-in, then answers nothing outdated.
    last = tmp_path / "last-answer"
    last.write_text(
        f"#!{python / 'python3'} -I\nimport os\nos.unlink(os.environ['STAND_IN'] + '/mise')\nprint('{{}}')\n"
    )
    last.chmod(0o755)
    tools.answer({BREW: NONE_OUTDATED, MISE: {"real": str(last)}})
    code, out, err = hometools(capfd, "update-check")
    assert (code, out, error(err)) == (1, '{"formulae": [], "casks": []}\n{}\n', "mise: No such file or directory")
    assert tools.calls() == [BREW, MISE]


def test_update_check_without_brew_cannot_check(tools: Tools, capfd: pytest.CaptureFixture[str]) -> None:
    tools.without_brew()
    tools.answer({})
    code, out, err = hometools(capfd, "update-check")
    assert (code, out, error(err)) == (2, "", "update:check: 'brew outdated' failed — COULD NOT CHECK")
