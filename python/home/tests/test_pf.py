"""pf:load, pf:confirm, pf:unload and pf:status, their revert, and the files mise bootstrap writes for them."""

# sudo, launchctl and the root pfctl calls change this Mac's firewall and launchd, so they cannot run in a test
# (CODING_STANDARDS 2): tests/stand_in.py stands in for each, logs every call and answers from a script. The rules
# themselves are parsed by the real pfctl -n, which needs no root and loads nothing.

import json
import os
import plistlib
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Mapping
from pathlib import Path

import pytest

from hometools import pf
from hometools.cli import main

CHECKOUT = Path(__file__).resolve().parents[3]
CONFIG = CHECKOUT / "unix/home/.config/mise/config.toml"
TASKS = CHECKOUT / "unix/home/.config/mise/tasks/pf"
STAND_IN = Path(__file__).with_name("stand_in.py")

# What a stand-in prints and exits with (tests/stand_in.py).
type Reply = Mapping[str, object]

PARSE = ["pfctl", "-n", "-a", pf.ANCHOR, "-f", pf.RULES]
CLEAR = ["sudo", "rm", "-f", pf.CONFIRMED]
ARM = ["sudo", "-b", sys.executable, "-I", "-c", pf.REVERT, "120", pf.CONFIRMED, pf.PFCTL, pf.ANCHOR]
LOAD = ["sudo", pf.PFCTL, "-a", pf.ANCHOR, "-f", pf.RULES]
INFO = ["sudo", pf.PFCTL, "-s", "info"]
ENABLE = ["sudo", pf.PFCTL, "-E"]
ANCHORS = ["sudo", pf.PFCTL, "-a", "com.apple", "-s", "Anchors"]
RULES = ["sudo", pf.PFCTL, "-a", pf.ANCHOR, "-s", "rules"]
PRINT = ["launchctl", "print", f"system/{pf.LABEL}"]
TOUCH = ["sudo", "touch", pf.CONFIRMED]
TURN_ON = ["sudo", "launchctl", "enable", f"system/{pf.LABEL}"]
BOOTSTRAP = ["sudo", "launchctl", "bootstrap", "system", pf.PLIST]
BOOTOUT = ["sudo", "launchctl", "bootout", f"system/{pf.LABEL}"]
TURN_OFF = ["sudo", "launchctl", "disable", f"system/{pf.LABEL}"]
FLUSH = ["sudo", pf.PFCTL, "-a", pf.ANCHOR, "-F", "all"]

LISTED = {"stdout": "  com.apple/100.dotfiles-tailnet\n  com.apple/200.AirDrop\n"}
TWO_RULES = {"stdout": "pass in quick on lo0 all\nblock return in quick proto tcp from any to any port = 22\n"}
ENABLED = {"stdout": "Status: Enabled for 0 days 00:01:02\n"}
DISABLED = {"stdout": "Status: Disabled\n"}
LOADED = {"code": 0}
UNLOADED = {"code": pf.NOT_LOADED}


class Mac:
    """The stand-in programs: answer() scripts them, calls() reads what ran, in order."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def answer(self, answers: dict[tuple[str, ...], Reply]) -> None:
        script = {json.dumps(list(call)): reply for call, reply in answers.items()}
        (self.folder / "script.json").write_text(json.dumps(script))

    def calls(self) -> list[list[str]]:
        log = self.folder / "calls.jsonl"
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


@pytest.fixture
def mac(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Mac:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name in ("sudo", "launchctl", "pfctl"):
        (bin_dir / name).symlink_to(STAND_IN)
    monkeypatch.setenv("STAND_IN", str(tmp_path))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return Mac(tmp_path)


def hometools(capfd: pytest.CaptureFixture[str], command: str) -> tuple[int, str, str]:
    try:
        main([command])
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    out, err = capfd.readouterr()
    return code, out, err


def answers(*pairs: tuple[list[str], Reply]) -> dict[tuple[str, ...], Reply]:
    return {tuple(call): reply for call, reply in pairs}


def test_load_arms_the_revert_before_the_rules_and_turns_pf_on(mac: Mac, capfd: pytest.CaptureFixture[str]) -> None:
    mac.answer(answers((PARSE, {}), (CLEAR, {}), (ARM, {}), (LOAD, {}), (INFO, DISABLED), (ENABLE, {})))
    code, out, _err = hometools(capfd, "pf-load")
    assert code == 0
    assert mac.calls() == [PARSE, CLEAR, ARM, LOAD, INFO, ENABLE]
    assert "revert in 120 s" in out
    assert out.rstrip().endswith("then run: mise run pf:confirm")


def test_load_leaves_pf_alone_when_it_is_on(mac: Mac, capfd: pytest.CaptureFixture[str]) -> None:
    mac.answer(answers((PARSE, {}), (CLEAR, {}), (ARM, {}), (LOAD, {}), (INFO, ENABLED)))
    code, _out, _err = hometools(capfd, "pf-load")
    assert code == 0
    assert mac.calls() == [PARSE, CLEAR, ARM, LOAD, INFO]


def test_load_changes_nothing_when_the_rules_do_not_parse(mac: Mac, capfd: pytest.CaptureFixture[str]) -> None:
    mac.answer(answers((PARSE, {"stderr": f"{pf.RULES}:3: syntax error\n", "code": 1})))
    code, out, err = hometools(capfd, "pf-load")
    assert (code, out) == (1, "")
    assert json.loads(err.splitlines()[-1]) == {"error": "pfctl exited 1"}
    assert mac.calls() == [PARSE]


def test_confirm_keeps_the_rules_and_turns_the_boot_daemon_on(mac: Mac, capfd: pytest.CaptureFixture[str]) -> None:
    mac.answer(
        answers((ANCHORS, LISTED), (RULES, TWO_RULES), (TOUCH, {}), (TURN_ON, {}), (PRINT, UNLOADED), (BOOTSTRAP, {}))
    )
    code, out, _err = hometools(capfd, "pf-confirm")
    assert (code, out) == (0, "pf:confirm: rules kept; a restart loads them again\n")
    assert mac.calls() == [ANCHORS, RULES, TOUCH, TURN_ON, PRINT, BOOTSTRAP]


def test_confirm_does_not_bootstrap_a_loaded_daemon_again(mac: Mac, capfd: pytest.CaptureFixture[str]) -> None:
    mac.answer(answers((ANCHORS, LISTED), (RULES, TWO_RULES), (TOUCH, {}), (TURN_ON, {}), (PRINT, LOADED)))
    code, _out, _err = hometools(capfd, "pf-confirm")
    assert code == 0
    assert mac.calls() == [ANCHORS, RULES, TOUCH, TURN_ON, PRINT]


def test_confirm_refuses_once_the_revert_has_run(mac: Mac, capfd: pytest.CaptureFixture[str]) -> None:
    # The revert flushed the anchor and pf dropped it: com.apple lists only Apple's own.
    mac.answer(answers((ANCHORS, {"stdout": "  com.apple/200.AirDrop\n"})))
    code, out, err = hometools(capfd, "pf-confirm")
    assert (code, out) == (1, "")
    want = "pf:confirm: no rules are loaded (the revert already ran?); run: mise run pf:load"
    assert json.loads(err.splitlines()[-1]) == {"error": want}
    assert mac.calls() == [ANCHORS]


@pytest.mark.parametrize(("boot", "calls"), [(LOADED, [PRINT, BOOTOUT]), (UNLOADED, [PRINT])])
def test_unload_removes_the_rules_and_the_boot_daemon(
    mac: Mac, capfd: pytest.CaptureFixture[str], boot: Reply, calls: list[list[str]]
) -> None:
    mac.answer(answers((PRINT, boot), (BOOTOUT, {}), (TURN_OFF, {}), (FLUSH, {})))
    code, out, _err = hometools(capfd, "pf-unload")
    assert (code, out) == (0, "pf:unload: rules removed; the boot daemon is off\n")
    assert mac.calls() == [*calls, TURN_OFF, FLUSH]


def test_status_passes_when_everything_is_on(mac: Mac, capfd: pytest.CaptureFixture[str]) -> None:
    mac.answer(answers((INFO, ENABLED), (ANCHORS, LISTED), (RULES, TWO_RULES), (PRINT, LOADED)))
    code, out, _err = hometools(capfd, "pf-status")
    assert code == 0
    assert json.loads(out) == {"enabled": True, "rules": 2, "boot": True}


# Each case: pf -s info, com.apple's anchors, launchctl print, and the line printed.
OFF_CASES = [
    # Another program ran pfctl -d: pf is off and the rules guard nothing.
    (DISABLED, LISTED, LOADED, {"enabled": False, "rules": 2, "boot": True}),
    (ENABLED, {"stdout": ""}, LOADED, {"enabled": True, "rules": 0, "boot": True}),
    (ENABLED, LISTED, UNLOADED, {"enabled": True, "rules": 2, "boot": False}),
]


@pytest.mark.parametrize("case", OFF_CASES)
def test_status_fails_when_any_part_is_off(
    mac: Mac, capfd: pytest.CaptureFixture[str], case: tuple[Reply, ...]
) -> None:
    info, anchors, boot, want = case
    mac.answer(answers((INFO, info), (ANCHORS, anchors), (RULES, TWO_RULES), (PRINT, boot)))
    code, out, _err = hometools(capfd, "pf-status")
    assert code == 1
    assert json.loads(out) == want


def test_a_launchctl_failure_is_an_error_not_an_unloaded_daemon(mac: Mac, capfd: pytest.CaptureFixture[str]) -> None:
    mac.answer(answers((PRINT, {"code": 5})))
    code, out, err = hometools(capfd, "pf-unload")
    assert (code, out) == (1, "")
    assert json.loads(err.splitlines()[-1]) == {"error": "launchctl exited 5"}


@pytest.mark.parametrize("calls", [[["pfctl", "-a", pf.ANCHOR, "-F", "all"]], []], ids=["unconfirmed", "confirmed"])
def test_the_revert_flushes_only_unconfirmed_rules(mac: Mac, tmp_path: Path, calls: list[list[str]]) -> None:
    # The revert as root runs it, with no wait and the stand-in in pfctl's place.
    mac.answer(answers((["pfctl", "-a", pf.ANCHOR, "-F", "all"], {})))
    flag = tmp_path / "confirmed"
    if not calls:
        flag.touch()
    pfctl = tmp_path / "bin/pfctl"
    argv = [sys.executable, "-I", "-c", pf.REVERT, "0", str(flag), str(pfctl), pf.ANCHOR]
    subprocess.run(argv, check=True)
    assert mac.calls() == calls


def bootstrap_file(path: str) -> str:
    return tomllib.loads(CONFIG.read_text())["bootstrap"]["files"][path]["content"]


@pytest.mark.skipif(sys.platform != "darwin", reason="pfctl is macOS's")
def test_the_rules_parse_and_refuse_everyone_else(tmp_path: Path) -> None:
    rules = tmp_path / "dotfiles-tailnet"
    rules.write_text(bootstrap_file(pf.RULES))
    done = subprocess.run(
        ["/sbin/pfctl", "-n", "-v", "-a", pf.ANCHOR, "-f", rules], capture_output=True, text=True, check=True
    )
    parsed = [line for line in done.stdout.splitlines() if line.startswith(("pass", "block"))]
    assert parsed[0] == "pass in quick on lo0 all flags S/SA keep state"
    for port in (22, 88, 445, 3031, 3283, 5900):
        for proto in ("tcp", "udp"):
            assert any(f"pass in quick proto {proto} from <tailnet> to any port = {port} " in line for line in parsed)
            assert f"block return in quick proto {proto} from any to any port = {port}" in parsed
    # Passes come before every block: pf stops at the first quick rule that matches.
    assert max(i for i, line in enumerate(parsed) if line.startswith("pass")) < min(
        i for i, line in enumerate(parsed) if line.startswith("block")
    )


@pytest.mark.skipif(sys.platform != "darwin", reason="plutil is macOS's")
def test_the_boot_daemon_loads_the_same_rules_and_starts_off(tmp_path: Path) -> None:
    plist = tmp_path / "daemon.plist"
    plist.write_text(bootstrap_file(pf.PLIST))
    subprocess.run(["/usr/bin/plutil", "-lint", plist], capture_output=True, check=True)
    daemon = plistlib.loads(plist.read_bytes())
    assert daemon == {
        "Label": pf.LABEL,
        "Disabled": True,
        "ProgramArguments": [pf.PFCTL, "-E", "-a", pf.ANCHOR, "-f", pf.RULES],
        "RunAtLoad": True,
    }


@pytest.mark.parametrize("name", ["load", "confirm", "unload", "status"])
def test_each_launcher_runs_its_hometools_command(tmp_path: Path, name: str) -> None:
    # Without uv on PATH the launcher stops with its one JSON error, naming the task.
    copy = tmp_path / "unix/home/.config/mise/tasks/pf" / name
    copy.parent.mkdir(parents=True)
    shutil.copy2(TASKS / name, copy)
    done = subprocess.run(
        [sys.executable, "-I", copy], capture_output=True, text=True, env={"PATH": str(tmp_path)}, check=False
    )
    assert (done.returncode, done.stdout) == (127, "")
    assert json.loads(done.stderr) == {"error": f"pf:{name}: hometools could not start (uv: No such file or directory)"}
    assert f'"hometools", "pf-{name}"]' in (TASKS / name).read_text()
