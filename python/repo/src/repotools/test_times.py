"""Each test task's run history and its last run's slowest tests, read from mise's own records."""
# mise 2026.11.4 keeps both: `mise tasks history --summary --json` (src/cli/tasks/history.rs) and, with task.logs on,
# the last output of a task whose output mise reads (`mise tasks log`, src/task/task_run_log.rs).

import json
import re
import subprocess
import sys

from .models import TestTime

# pytest's --durations block: its header line, then one line per test until the next section rule.
HEADER = re.compile(r"=+ slowest \d+ durations =+")
RULE = re.compile(r"[=-]{3,}")


def mise(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["mise", *args], capture_output=True, text=True, check=False)


def slowest(log: str) -> list[str]:
    found: list[str] = []
    inside = False
    for line in log.splitlines():
        if HEADER.fullmatch(line.strip()):
            inside = True
        elif inside and RULE.match(line):
            break
        elif inside and line.strip():
            found.append(line.strip())
    return found


def report() -> None:
    history = mise("tasks", "history", "--summary", "--json")
    history.check_returncode()
    for row in json.loads(history.stdout):
        # A test task is named test, at any root: test, //:test, //python/repo:test, and plain:test.
        if row["task"].rpartition(":")[2] != "test":
            continue
        # A task with no kept log (never logged, or task.logs off) makes `mise tasks log` fail: no slowest lines.
        log = mise("tasks", "log", row["task"])
        time = TestTime(
            task=row["task"],
            runs=row["runs"],
            failures=row["failures"],
            median_ms=row.get("median_ms"),
            last_ms=row.get("last_ms"),
            last_status=row["last_status"],
            slowest=slowest(log.stdout) if log.returncode == 0 else [],
        )
        sys.stdout.write(time.model_dump_json() + "\n")
