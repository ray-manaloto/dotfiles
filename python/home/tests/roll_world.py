"""A scratch herdr world for the roll tests: real processes, real ps, lsof and git, stood-in hc and herdr-app."""

# hc and herdr-app would reach this Mac's core, its tabs and its agents, and claude, gh, curl and mise reach the
# network or a model, so tests/stand_in.py answers them from a script (CODING_STANDARDS 2). The agents are real
# processes started from a scratch HOME: ps lists them, lsof sees their folders and open files, and the steps read
# them exactly as they read a live session.

import contextlib
import json
import os
import signal
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from hometools.cli import main
from hometools.models import RollRun

STAND_IN = Path(__file__).with_name("stand_in.py")
STOOD_IN = ("hc", "herdr-app", "mise", "claude", "gh", "curl")
# A harness stand-in: it sleeps until the test ends. child=<argv> starts a child process (a background job or an
# MCP server), open=<path> keeps a file open (a Codex rollout).
AGENT = f"""#!{sys.executable} -I
import subprocess, sys, time
held = []
for word in sys.argv[1:]:
    if word.startswith("child="):
        held.append(subprocess.Popen(word[6:].split("|")))
    if word.startswith("open="):
        held.append(open(word[5:]))
time.sleep(120)
"""
type Answer = dict[str, object] | list[dict[str, object]]


def out(value: object) -> dict[str, object]:
    """A stand-in answer that prints value as JSON."""
    return {"stdout": json.dumps(value)}


class World:
    """The scratch HOME, the stand-ins' script, and the processes the test started."""

    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root, self.home, self.stand_in, self.bin = root, root / "home", root / "stand-in", root / "bin"
        for folder in (self.home, self.stand_in, self.bin):
            folder.mkdir()
        for name in STOOD_IN:
            (self.stand_in / name).symlink_to(STAND_IN)
        for name in ("claude", "codex", "opencode", "fnox"):
            (self.bin / name).write_text(AGENT)
            (self.bin / name).chmod(0o755)
        monkeypatch.setenv("HOME", str(self.home))
        monkeypatch.setenv("STAND_IN", str(self.stand_in))
        monkeypatch.setenv("PATH", f"{self.stand_in}:{os.environ['PATH']}")
        monkeypatch.setenv("HC_TERMINAL_ID", "t9")
        # Every XDG folder follows the scratch HOME (state, config, data, cache, runtime).
        for name in [name for name in os.environ if name.startswith("XDG_")]:
            monkeypatch.delenv(name)
        self.script: dict[str, Answer] = {}
        self.started: list[subprocess.Popen[bytes]] = []
        self.wiki = root / "wiki"
        (self.wiki / "lanes").mkdir(parents=True)

    def answer(self, calls: dict[tuple[str, ...], Answer]) -> None:
        """Add answers by argv; the stand-in keys each by its JSON argv."""
        self.script |= {json.dumps(list(argv)): reply for argv, reply in calls.items()}
        (self.stand_in / "script.json").write_text(json.dumps(self.script))

    def calls(self) -> list[tuple[str, ...]]:
        log = self.stand_in / "calls.jsonl"
        return [tuple(json.loads(line)) for line in log.read_text().splitlines()] if log.exists() else []

    def spawn(self, program: str, *args: str, cwd: Path | None = None) -> int:
        """A real process of a harness stand-in in its own process group, ended when the test ends."""
        folder = cwd or self.root
        folder.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen([self.bin / program, *args], cwd=folder, start_new_session=True)
        self.started.append(proc)
        return proc.pid

    def stop(self) -> None:
        for proc in self.started:
            # Only the groups this test started (no pattern kill).
            # A group whose processes all ended: gone, or (macOS, its leader not yet reaped) not permitted.
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()

    def claude_record(self, pid: int, session: str) -> None:
        """Claude Code's ~/.claude/sessions/<pid>.json, with the trailing data it can carry."""
        record = self.home / f".claude/sessions/{pid}.json"
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps({"sessionId": session, "cwd": "/"}) + "\ntrailing")

    def transcript(self, session: str, *records: dict[str, object]) -> Path:
        path = self.home / f".claude/projects/-project/{session}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(record) + "\n" for record in records))
        return path

    def state(self) -> Path:
        return self.home / ".local/state/dotfiles/roll"

    def runs(self) -> list[RollRun]:
        log = self.state() / "runs.jsonl"
        return [RollRun.model_validate_json(line) for line in log.read_text().splitlines()] if log.exists() else []


def terminal(address: str, where: str, agent: str = "claude-code", status: str = "idle") -> dict[str, object]:
    """One row of hc ls --json."""
    return {"address": address, "agent": agent, "state": "live", "status": status, "where": where}


def info(
    address: str,
    pid: int | None,
    argv: Sequence[str],
    cwd: Path | str,
    **extra: object,
) -> dict[str, object]:
    """hc get <address> --json: the foreground process and its status."""
    found: dict[str, object] = {
        "address": address,
        "pid": None,
        "cwd": str(cwd),
        "parent": None,
        "foreground": {"pid": pid, "argv": list(argv), "cwd": str(cwd), "name": extra.pop("name", "x")},
        "status": {"state": extra.pop("state", "idle"), "kind": extra.pop("kind", None), "msg": "a status"},
        "labels": {"where": extra.pop("where", "")},
    }
    return found | extra


def layout(*spaces: tuple[str, str, Sequence[tuple[str, str, Sequence[str]]]]) -> dict[str, object]:
    """herdr-app ls: (space name, folder, [(tab id, tab name, [terminal addresses])])."""
    return {
        "spaces": [
            {
                "id": f"sp-{name}",
                "name": name,
                "folder": folder,
                "tabs": [
                    {"id": tab_id, "name": tab, "terminals": [{"terminal": address} for address in terms]}
                    for tab_id, tab, terms in tabs
                ],
            }
            for name, folder, tabs in spaces
        ]
    }


def hometools(capfd: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    try:
        main(["roll", *argv])
        code = 0
    except SystemExit as stop:
        code = int(stop.code or 0)
    got, err = capfd.readouterr()
    return code, got, err


def lines(text: str) -> list[dict[str, object]]:
    """The JSON lines of a step's output."""
    return [json.loads(line) for line in text.splitlines() if line.startswith("{")]


def after(otherwise: dict[str, object], *pairs: tuple[Sequence[str], dict[str, object]]) -> dict[str, object]:
    """An answer that changes once a call is made: the last pair whose argv was called, else otherwise."""
    return {"after": [[list(argv), answer] for argv, answer in pairs], "else": otherwise}


def replier(world: World, path: Path, text: str) -> dict[str, object]:
    """An hc send --wait that the tab answers: it appends an assistant turn, stamped now, to its transcript."""
    script = world.bin / f"reply-{len(list(world.bin.iterdir()))}"
    record = {"type": "assistant", "isSidechain": False, "message": {"content": [{"type": "text", "text": text}]}}
    script.write_text(
        f"#!{sys.executable} -I\nimport datetime, json\nrecord = {record!r}\n"
        "record['timestamp'] = datetime.datetime.now(datetime.UTC).isoformat()\n"
        f"open({str(path)!r}, 'a').write(json.dumps(record) + '\\n')\n"
    )
    script.chmod(0o755)
    return {"real": str(script)}
