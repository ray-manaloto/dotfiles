"""What a roll step reads once: hc's terminals, herdr-app's layout, each terminal's hc get and the process table."""

import json
import os
import re
import subprocess
import time
from collections.abc import Callable, Mapping
from pathlib import Path

from hometools.models import Kind, MiseLinks, Result, Role

COORDINATOR = "chief-of-staff"
# One rule for every step (close.py counted only -lead; checks.py and roll.py also -coord and -v2).
LEADS = ("-lead", "-coord", "-v2")
# hc's agent and status.app names for the harnesses a roll resumes.
APPS = {"claude-code": Kind.claude, "codex": Kind.codex, "opencode": Kind.opencode}
# The program a harness's foreground argv names, so a step sees when it has exited to the shell.
PROGRAMS = {Kind.claude: "claude", Kind.codex: "codex", Kind.opencode: "opencode"}
SHELLS = frozenset({"zsh", "bash", "sh", "fish"})
# A send from an agent tab arrives wrapped as <hc from=...> chat; /exit and typed commands must go untagged.
RAW = ("HC_TERMINAL_ID", "HC_SCOPE")
SECONDS = 120
# hc and herdr-app answer a read at once; a core that does not answer within this is reported as unreadable.
QUICK = 15
# Launchers a harness runs under: fnox proxy run -- <program>, and env [-u NAME] [NAME=VALUE] <program>.
LAUNCHERS = frozenset({"fnox", "env"})


def call(
    *argv: str, env: Mapping[str, str] | None = None, timeout: float = SECONDS, codes: frozenset[int] = frozenset({0})
) -> str | None:
    """argv's stdout, or None when it can't start, exits with a code outside codes or runs past timeout."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env, check=False)
    # A program that is missing or hangs is a read that failed: the step reports it as missing data.
    except OSError, subprocess.TimeoutExpired:
        return None
    return done.stdout if done.returncode in codes else None


def answer(*argv: str) -> dict[str, object]:
    """argv's JSON object; {} when it fails or prints anything else."""
    try:
        value = json.loads(call(*argv, timeout=QUICK) or "")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def raw_env() -> dict[str, str]:
    return {name: value for name, value in os.environ.items() if name not in RAW}


def role(space: str, tab: str) -> Role:
    """The chief of staff by name (its space and tab are both chief-of-staff), never by HC_TERMINAL_ID."""
    if space == tab == COORDINATOR:
        return Role.coordinator
    if tab.endswith(LEADS) or space == COORDINATOR:
        return Role.lead
    return Role.child


def poll[T](probe: Callable[[], T | None], seconds: float, interval: float) -> T | None:
    """probe's first answer that is not None, asked every interval seconds until seconds have passed."""
    end = time.monotonic() + seconds
    while True:
        found = probe()
        if found is not None or time.monotonic() >= end:
            return found
        time.sleep(interval)


def field(value: object, *path: str) -> object:
    """value[path[0]][path[1]]..., or None where a level is missing or not an object."""
    for key in path:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def rows(value: object, key: str) -> list[dict[str, object]]:
    """The objects in value[key], a list; [] when it is missing or not a list."""
    found = field(value, key)
    return [row for row in found if isinstance(row, dict)] if isinstance(found, list) else []


def processes() -> dict[int, tuple[int, str, str]]:
    """Every process: pid -> (parent pid, start time as ps prints it, args)."""
    # LC_ALL=C: lstart in English, as the start time's parser reads it.
    text = call("ps", "-axo", "pid=,ppid=,lstart=,args=", env=os.environ | {"LC_ALL": "C"}) or ""
    rows_ = (
        re.match(r"\s*(\d+)\s+(\d+)\s+(\w{3}\s+\w{3}\s+\d+\s+[\d:]+\s+\d{4})\s+(.*)", line)
        for line in text.splitlines()
    )
    return {int(m[1]): (int(m[2]), m[3], m[4]) for m in rows_ if m}


class Live:
    """The live herdr layout and processes, read once when the step starts."""

    def __init__(self) -> None:
        read = answer("hc", "ls", "--json")
        # hc ls that failed or printed anything but a terminal list: the graph step refuses rather than see no agents.
        self.listed = isinstance(field(read, "terminals"), list)
        listed = rows(read, "terminals")
        self.terminals = {str(row["address"]): row for row in listed if row.get("state") == "live"}
        self.layout = answer("herdr-app", "ls")
        self.info = {address: answer("hc", "get", address, "--json") for address in self.terminals}
        self.procs = processes()
        self.me = os.environ.get("HC_TERMINAL_ID")

    def reread(self, address: str) -> None:
        """The terminal's hc get and the process table again, after a wait in which a job may have started."""
        self.info[address] = answer("hc", "get", address, "--json")
        self.procs = processes()

    def spaces(self) -> list[dict[str, object]]:
        return rows(self.layout, "spaces")

    def descendants(self, pid: int) -> list[int]:
        """pid and every process under it."""
        found, stack = [], [pid]
        while stack:
            parent = stack.pop()
            found.append(parent)
            stack.extend(child for child, (ppid, _, _) in self.procs.items() if ppid == parent)
        return found

    def foreground(self, address: str) -> tuple[int | None, list[str]]:
        """The terminal's foreground pid and argv."""
        pid = field(self.info.get(address), "foreground", "pid")
        argv = field(self.info.get(address), "foreground", "argv")
        return (pid if isinstance(pid, int) else None), [str(word) for word in argv] if isinstance(argv, list) else []

    def tree(self, address: str) -> list[int]:
        """The foreground process and its children first, then everything under the terminal's own process."""
        root = field(self.info.get(address), "pid")
        pid, _ = self.foreground(address)
        mine = self.descendants(pid) if pid else []
        return mine + (self.descendants(root) if isinstance(root, int) else [])


def dangling() -> MiseLinks:
    """Every <installs>/<tool>/<link> whose target is missing, the global links first. mise 2026.11.8 rebuilds
    runtime links only for tools in the current toolset (src/runtime_symlinks.rs:281) and clears dangling ones only
    when it uninstalls a version of that backend (src/cli/prune.rs:283), so a dropped tool's links can dangle
    unseen. Reported only: never removed here."""
    installs = Path(os.environ.get("MISE_DATA_DIR") or Path.home() / ".local/share/mise") / "installs"
    tools = sorted(tool for tool in installs.glob("*") if tool.is_dir() and not tool.is_symlink())
    found = [
        f"{tool.name}/{link.name}"
        for tool in tools
        for link in entries(tool)
        if link.is_symlink() and not link.exists()
    ]
    found.sort(key=lambda name: not name.endswith("/global"))
    return MiseLinks(check="mise-links", result=Result.fail if found else Result.pass_, dangling=found)


def entries(folder: Path) -> list[Path]:
    """folder's entries, sorted; [] for a folder that is gone or can't be read (a check reports what it can see)."""
    try:
        return sorted(folder.iterdir())
    except OSError:
        return []


def program(argv: list[str]) -> str | None:
    """The program argv runs, past its launchers: fnox ... -- env -u NAME NAME=VALUE opencode ... is opencode."""
    words = list(argv)
    while words and Path(words[0]).name in LAUNCHERS:
        rest = words[words.index("--") + 1 :] if Path(words[0]).name == "fnox" and "--" in words else words[1:]
        if Path(words[0]).name == "env":
            while rest and (rest[0].startswith("-") or "=" in rest[0]):
                rest = rest[2:] if rest[0] == "-u" else rest[1:]
        words = rest
    return Path(words[0]).name if words else None


def runs(kind: Kind, argv: list[str]) -> bool:
    """argv runs the harness kind, directly or under its launchers."""
    return program(argv) == PROGRAMS[kind]


def bare_shell(argv: list[str]) -> bool:
    return bool(argv) and Path(argv[0]).name.lstrip("-") in SHELLS
