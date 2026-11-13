"""monit-alert: tell the owner that a monit rule fired, and record the alert where agents can read it.

monit runs `mise run monit:alert` from each rule in monitrc (unix/home/.config/mise/config.toml) and hands it the
alert in MONIT_SERVICE, MONIT_EVENT and MONIT_DESCRIPTION. monit splits an exec string on spaces, so the text can't
go on the command line; it is read here. Two steps, the second tried even when the first fails:

- a macOS notification, its text passed to osascript as arguments, never written into the script;
- ~/.local/state/dotfiles/monit/alert.json, the last alert, replaced whole each run (a temporary file in the same
  folder, then os.replace), so a reader never sees half a record.

It sends nothing to any agent's terminal (owner, 2026-11-13): agents read alert.json themselves.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .disk import setting
from .models import Failure, MonitAlert

OSASCRIPT = "/usr/bin/osascript"
# osascript's time limit; MONIT_ALERT_SECONDS overrides it for one run.
SECONDS = 60
# The notification's text comes in as argv, so nothing in it is AppleScript.
NOTIFY = [
    "-e",
    "on run argv",
    "-e",
    'display notification (item 2 of argv) with title ("monit: " & item 1 of argv)',
    "-e",
    "end run",
]


def record_path() -> Path:
    return Path.home() / ".local/state/dotfiles/monit/alert.json"


def notify(service: str, description: str, osascript: str = OSASCRIPT) -> str | None:
    """None once the notification is posted, else why it wasn't."""
    argv = [osascript, *NOTIFY, service, description]
    try:
        done = subprocess.run(
            argv, capture_output=True, text=True, timeout=setting("MONIT_ALERT_SECONDS", SECONDS), check=False
        )
    except (OSError, subprocess.TimeoutExpired) as failed:
        return f"{osascript}: {type(failed).__name__}"
    if done.returncode:
        return f"{osascript} exited {done.returncode}: {done.stderr.strip()}"
    return None


def write(record: MonitAlert, path: Path) -> str | None:
    """None once path holds record, else why it doesn't; a failed write leaves the old record and no temporary file."""
    # The temporary file is removed on any failure after it exists: a full disk fails the write or the close, as
    # well as the rename, and that is when monit alerts.
    temporary: Path | None = None
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=".alert-", delete=False) as out:
            temporary = Path(out.name)
            out.write(record.model_dump_json() + "\n")
        temporary.replace(path)
    except OSError as failed:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        return f"{path}: {failed.strerror or type(failed).__name__}"
    return None


def alert(record: MonitAlert, path: Path, osascript: str = OSASCRIPT) -> MonitAlert:
    """Both steps; ValueError naming each one that failed."""
    unsent = notify(record.service, record.description, osascript)
    unwritten = write(record, path)
    failed = [f"notification: {unsent}"] * bool(unsent) + [f"alert.json: {unwritten}"] * bool(unwritten)
    if failed:
        raise ValueError("monit-alert: " + "; ".join(failed))
    return record


def run_alert() -> None:
    record = MonitAlert(
        at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        service=os.environ.get("MONIT_SERVICE") or "monit",
        event=os.environ.get("MONIT_EVENT") or "",
        description=os.environ.get("MONIT_DESCRIPTION") or "an alert with no description",
    )
    try:
        done = alert(record, record_path(), os.environ.get("MONIT_ALERT_OSASCRIPT") or OSASCRIPT)
    except ValueError as failed:
        sys.stderr.write(Failure(error=str(failed)).model_dump_json() + "\n")
        raise SystemExit(1) from None
    sys.stdout.write(done.model_dump_json() + "\n")
