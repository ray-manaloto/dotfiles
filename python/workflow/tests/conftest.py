"""Real git repositories for every test, and the command line run in-process."""

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from workflowtools.cli import main


@pytest.fixture(autouse=True)
def no_hook_git(monkeypatch: pytest.MonkeyPatch) -> None:
    """A pre-commit hook exports GIT_DIR and friends, and they would point every test's git at the real checkout."""
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", root], check=True)
    monkeypatch.chdir(root)
    return root


def write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def add(root: Path, files: dict[str, str]) -> None:
    write(root, files)
    subprocess.run(["git", "-C", root, "add", "-f", "."], check=True)


def report(capsys: pytest.CaptureFixture[str], *args: str) -> list[dict[str, str]]:
    """Run a command; its stdout JSON lines, and SystemExit's code as a string under the "exit" key of a last line."""
    try:
        main(list(args))
        code = 0
    except SystemExit as stop:
        code = stop.code
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    return [*lines, {"exit": str(code)}]


@pytest.fixture
def gh_stand_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, object], set[str]], Path]:
    def install(responses: dict[str, object], failing: set[str]) -> Path:
        data = tmp_path / "gh.json"
        log = tmp_path / "gh.log"
        program = tmp_path / "bin" / "gh"
        program.parent.mkdir(exist_ok=True)
        data.write_text(json.dumps(responses))
        program.write_text(
            f"#!{sys.executable}\n"
            "import json, sys\n"
            "from pathlib import Path\n"
            f"with Path({str(log)!r}).open('a') as stream:\n"
            "    stream.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "endpoint = sys.argv[-1]\n"
            f"if endpoint in {sorted(failing)!r}:\n"
            "    sys.stderr.write('HTTP 503\\n')\n"
            "    raise SystemExit(1)\n"
            f"value = json.loads(Path({str(data)!r}).read_text()).get(endpoint)\n"
            "print(value if value == '<not json>' else json.dumps(value))\n"
        )
        program.chmod(0o755)
        monkeypatch.setenv("PATH", f"{program.parent}{os.pathsep}{os.environ['PATH']}")
        return log

    return install


@pytest.fixture
def roadmap_repo(repo: Path) -> Path:
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/o/r.git"], check=True)
    add(repo, {".gitignore": "/task_plan.md\n/other.md\n/rebuilt.md\n"})
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Workflow Test",
            "-c",
            "user.email=workflow@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    return repo
