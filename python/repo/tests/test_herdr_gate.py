"""repotools herdr-gate and hk's herdr step: a change, deletion included, to the herdr doctor or hc-safe selects it."""

import contextlib
import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from repotools.cli import main
from tests import clean_git_env

HK_PKL = Path(__file__).resolve().parents[3] / "hk.pkl"
LAUNCHER = "unix/home/.config/mise/tasks/herdr/doctor"
HC_SAFE = "unix/home/.local/bin/hc-safe"
DOCTOR = "python/home/src/hometools/herdr.py"
SKIP = "herdr-gate: nothing the herdr doctor or hc-safe runs from is staged; //home:herdr-unit skipped\n"


def git(*args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@e", *args], capture_output=True, check=True, text=True
    )
    return done.stdout


def put(path: str, text: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text)
    git("add", "--", path)


@pytest.fixture(autouse=True)
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """A repository whose HEAD holds the doctor's launcher, hc-safe, the doctor and an unrelated file; the test runs
    inside it, and the working folder is restored afterwards."""
    clean_git_env(monkeypatch)
    git("init", "-q", "-b", "main", str(tmp_path))
    with contextlib.chdir(tmp_path):
        for path in (LAUNCHER, HC_SAFE, DOCTOR, "python/home/tests/test_herdr_doctor.py", "README.md"):
            put(path, "one\n")
        git("commit", "-q", "-m", "one")
        yield tmp_path


def gate(capsys: pytest.CaptureFixture[str]) -> tuple[str, str]:
    main(["herdr-gate"])
    captured = capsys.readouterr()
    return captured.out, captured.err


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda: git("rm", "-q", LAUNCHER), id="the launcher deleted"),
        pytest.param(lambda: put(LAUNCHER, "two\n"), id="the launcher changed"),
        pytest.param(lambda: git("rm", "-q", HC_SAFE), id="hc-safe deleted"),
        pytest.param(lambda: put(HC_SAFE, "two\n"), id="hc-safe changed"),
        pytest.param(lambda: git("rm", "-q", DOCTOR), id="the doctor deleted"),
        pytest.param(lambda: put(DOCTOR, "two\n"), id="the doctor changed"),
        pytest.param(lambda: git("mv", DOCTOR, "python/home/doctor.py"), id="the doctor renamed away"),
        pytest.param(lambda: put("python/home/tests/test_herdr_contract.py", ""), id="a herdr test added"),
        pytest.param(lambda: put(".claude/skills/verify/SKILL.md", "x\n"), id="the verify skill"),
        pytest.param(lambda: put("python/home/mise.toml", "x\n"), id="the package tasks"),
    ],
)
def test_a_herdr_change_runs(change: Callable[[], object], capsys: pytest.CaptureFixture[str]) -> None:
    change()
    assert gate(capsys) == ("run\n", "")


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda: put("README.md", "x\n"), id="another file"),
        pytest.param(lambda: put("python/home/src/hometools/toolchain.py", "x\n"), id="another hometools module"),
        pytest.param(lambda: None, id="nothing staged"),
    ],
)
def test_any_other_change_skips_with_the_reason(
    change: Callable[[], object], capsys: pytest.CaptureFixture[str]
) -> None:
    change()
    assert gate(capsys) == ("", SKIP)


def pkl_string(text: str) -> str:
    """text as a Pkl string literal: a backslash, quote and control character escaped, everything else as it is."""
    named = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}
    body = "".join(named.get(c, f"\\u{{{ord(c):x}}}" if ord(c) < 0x20 else c) for c in text)
    return f'"{body}"'


def section(text: str, start: str) -> str:
    """The braces block that opens at start."""
    block = text[text.index(start) :]
    depth = 0
    for i, char in enumerate(block):
        depth += {"{": 1, "}": -1}.get(char, 0)
        if char == "}" and depth == 0:
            return block[: i + 1]
    msg = f"{start} does not close"
    raise AssertionError(msg)


def test_hk_runs_the_herdr_step_from_both_the_check_hook_and_pre_commit() -> None:
    # hk.pkl as hk reads it: evaluated by the real pkl, not matched as text (review:python R3).
    done = subprocess.run(["pkl", "eval", "-f", "json", str(HK_PKL)], capture_output=True, text=True, check=True)
    hooks = json.loads(done.stdout)["hooks"]
    check = hooks["check"]["steps"]["herdr"]
    assert (check["check"], check["profiles"]) == ("mise run //home:herdr-unit", ["!ci"])
    pre_commit = hooks["pre-commit"]["steps"]["herdr"]
    assert (pre_commit["check"], pre_commit["profiles"]) == ("mise run //repo:herdr-gate", ["!ci"])
    assert "glob" not in pre_commit  # glob = null: pkl leaves it out, and hk then runs the step on every commit.


def test_hk_runs_the_step_on_a_commit_that_only_deletes_hc_safe(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """This repository's own pre-commit herdr step, run by the real hk, with the gate in place of its mise task."""
    for name in [name for name in os.environ if name.startswith("HK_")]:
        monkeypatch.delenv(name)
    real = HK_PKL.read_text()
    herdr = section(section(section(real, '["pre-commit"] {'), "steps = (linters) {"), '["herdr"] {')
    # A path with a space, a quote and a letter that is not ASCII: shell-quoted, then written as a Pkl string.
    marker = tmp_path_factory.mktemp("it's a märker") / "gate out"
    script = Path(sys.executable).parent / "repotools"
    assert 'check = "mise run //repo:herdr-gate"' in herdr
    command = f"{shlex.quote(str(script))} herdr-gate > {shlex.quote(str(marker))}"
    herdr = herdr.replace('check = "mise run //repo:herdr-gate"', f"check = {pkl_string(command)}")
    hooks = f'hooks {{\n    ["pre-commit"] {{\n        steps {{\n            {herdr}\n        }}\n    }}\n}}\n'
    Path("hk.pkl").write_text(real.splitlines()[0] + "\n\n" + hooks)
    git("add", "hk.pkl")
    git("commit", "-q", "-m", "hk")
    git("rm", "-q", HC_SAFE)
    hook = ["-c", "hook.hk.event=pre-commit", "-c", "hook.hk.command=hk run pre-commit --from-hook"]
    done = subprocess.run(
        ["git", *hook, "-c", "user.name=t", "-c", "user.email=t@e", "commit", "-q", "-m", "drop hc-safe"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert marker.read_text() == "run\n"
