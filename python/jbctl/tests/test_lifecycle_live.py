"""start, restart and stop of a real spare IDE, opt-in: JBCTL_LIFECYCLE_IDE names it (e.g. rustrover)."""

# This test brings the IDE forward (start and restart are foreground actions) and quits it, so the owner runs it
# with //jbctl:lifecycle <ide>, never inside //jbctl:coverage. The IDE opens a test-owned, detached worktree of
# the local mise checkout at its latest commit, under a unique name. A window of the IDE must show that name after
# start and after restart. The name is compared in this process and never printed.

import json
import os
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from jbctl import ide

from .conftest import run

IDE = os.environ.get("JBCTL_LIFECYCLE_IDE", "")
MISE = Path(os.environ.get("JBCTL_LIFECYCLE_REPO") or Path.home() / "dev/github/jdx/mise")
pytestmark = pytest.mark.skipif(not IDE, reason="set JBCTL_LIFECYCLE_IDE to a spare IDE's Toolbox script name")


@pytest.fixture
def project(tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / f"jbctl-live-{uuid.uuid4().hex[:12]}"
    subprocess.run(["git", "-C", MISE, "worktree", "add", "--detach", folder, "HEAD"], check=True, capture_output=True)
    yield folder
    # Removed only once the IDE that may have it open has quit; otherwise both stay for the owner.
    jbctl = Path(sys.executable).with_name("jbctl")  # this checkout's own, beside the venv's python
    status = subprocess.run([jbctl, "status", "--ide", IDE], capture_output=True, text=True, check=True).stdout
    if json.loads(status)["ides"][0]["state"] == "stopped":
        subprocess.run(["git", "-C", MISE, "worktree", "remove", "--force", folder], check=True, capture_output=True)


def opened(pid: int, folder: Path) -> bool:
    """Whether, within two minutes, a window of the IDE shows the project's unique name."""
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if any(w.get("pid") == pid and folder.name in (w.get("title") or "") for w in ide.windows()):
            return True
        time.sleep(2)
    return False


def test_lifecycle(capsys: pytest.CaptureFixture[str], project: Path) -> None:
    code, [listed], _ = run(capsys, "status", "--ide", IDE)
    assert (code, listed["ides"][0]["state"]) == (0, "stopped"), "quit the IDE first: the test starts it itself"
    try:
        code, [event], error = run(
            capsys, "start", "--foreground", "--ide", IDE, "--project", str(project), "--timeout", "300"
        )
        assert (code, error) == (0, ""), event
        first = event["lifecycle"]["pid"]
        assert opened(first, project), "the IDE did not open the test project after start"
        code, [event], error = run(capsys, "restart", "--foreground", "--ide", IDE, "--timeout", "300")
        assert (code, error, event["lifecycle"]["previous_pid"]) == (0, "", first), event
        assert opened(event["lifecycle"]["pid"], project), "the IDE did not reopen the test project after restart"
    finally:
        # Quit before the fixture removes the worktree; a refusal leaves the IDE and the worktree for the owner.
        code, events, _ = run(capsys, "stop", "--ide", IDE, "--timeout", "120")
        assert code == 0 or "0 IDEs run" in str(events), events
