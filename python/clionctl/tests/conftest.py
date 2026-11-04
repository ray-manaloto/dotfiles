"""A scratch station folder, stand-in IDE bundles launched through LaunchServices, and the command run in-process."""

import json
import os
import plistlib
import shutil
import signal
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import psutil
import pytest

from clionctl.cli import main

STANDIN = Path(__file__).with_name("standin.py")


@pytest.fixture
def folder(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """The station folder clion-ctl reads (CLION_CTL_STATION_DIR), short enough for a Unix socket path. Every process
    started from it is killed at the end: the test's stand-ins, never a real IDE."""
    path = Path(tempfile.mkdtemp(prefix="cc", dir="/tmp")).resolve()
    monkeypatch.setenv("CLION_CTL_STATION_DIR", str(path))
    yield path
    for process in psutil.process_iter(["cmdline"]):
        if any(str(path) in arg for arg in process.info["cmdline"] or []):
            os.kill(process.pid, signal.SIGKILL)
    shutil.rmtree(path)


def bundle(folder: Path, name: str, mode: str = "obey", mcp_port: int | None = None) -> Path:
    """A stand-in IDE's .app: Info.plist, the stand-in as its executable, and its standin.json."""
    app = folder / f"{name}.app"
    (app / "Contents/MacOS").mkdir(parents=True)
    (app / "Contents/Resources").mkdir()
    plist = {"CFBundleExecutable": "ide", "CFBundleIdentifier": "test.clionctl.standin", "CFBundlePackageType": "APPL"}
    (app / "Contents/Info.plist").write_bytes(plistlib.dumps(plist))
    executable = app / "Contents/MacOS/ide"
    executable.write_text(f"#!{sys.executable}\n{STANDIN.read_text()}")
    executable.chmod(0o755)
    config = {"folder": str(folder), "mode": mode, "mcp_port": mcp_port}
    (app / "Contents/Resources/standin.json").write_text(json.dumps(config))
    return app


def written(app: Path, kind: str, pid: int) -> object:
    """What the stand-in with this pid wrote: its arguments (argv) or the /exit body it got (exit)."""
    return json.loads((app / f"Contents/Resources/{kind}-{pid}.json").read_text())


def report(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, list[dict], list[dict]]:
    """Run a command: its exit code, and its stdout and stderr JSON lines."""
    try:
        main(list(args))
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    captured = capsys.readouterr()
    out = [json.loads(line) for line in captured.out.splitlines()]
    err = [json.loads(line) for line in captured.err.splitlines()]
    return code, out, err


def launch(capsys: pytest.CaptureFixture[str], app: Path, *args: str) -> dict:
    code, out, err = report(capsys, "start", "--app", str(app), "--timeout", "30", *args)
    assert (code, err) == (0, [])
    return out[0]
