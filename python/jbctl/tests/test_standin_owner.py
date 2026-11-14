"""A stand-in IDE ends with the test process that made it, even when that process never reaches its teardown."""

import os
import subprocess
import time
from pathlib import Path

import psutil

from .conftest import launcher


def test_a_stand_in_ends_when_its_owner_is_gone(tmp_path: Path) -> None:
    """jbctl starts an IDE in its own session, as Toolbox does, so a test run killed before its teardown (hk
    aborting a step sends SIGTERM) used to leave the stand-in running for days. Here the owner is a process the test
    ends with SIGKILL, which nothing in it can catch."""
    owner = subprocess.Popen(["sleep", "60"])
    (tmp_path / "fake.app/Contents/MacOS").mkdir(parents=True)
    standin = launcher(tmp_path / "fake.app")
    env = os.environ | {"STANDIN_OWNER": str(owner.pid), "JBCTL_STATION_DIR": str(tmp_path)}
    ide = subprocess.Popen(
        [standin, "--no-about", "--no-station"], env=env, stdout=subprocess.PIPE, start_new_session=True, text=True
    )
    assert ide.stdout
    ide.stdout.readline()  # it is up
    owner.kill()
    owner.wait()
    deadline = time.monotonic() + 10
    while ide.poll() is None and time.monotonic() < deadline:
        time.sleep(0.1)
    alive = ide.poll() is None
    if alive:
        psutil.Process(ide.pid).kill()
    assert not alive, "the stand-in outlived its owner"
