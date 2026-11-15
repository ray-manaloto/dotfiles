"""Run CLI and subprocess regressions with a deadline outside the process under test."""

import os
import signal
import subprocess
import sys
from typing import BinaryIO

import pytest

STOP = """
import signal
def stop(signum, frame):
    raise SystemExit(124)
signal.signal(signal.SIGTERM, stop)
"""


def run_python(code: str, *, stdin: BinaryIO | None = None) -> subprocess.CompletedProcess[bytes]:
    command = [sys.executable, "-c", STOP + code]
    with subprocess.Popen(
        command, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True
    ) as child:
        try:
            stdout, stderr = child.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            # Terminate the owned group; the handler lets subprocess.run reap its Git child.
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.communicate()
            raise
    return subprocess.CompletedProcess(command, child.returncode, stdout, stderr)


def drop_repo_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop git's repository variables (its own list, `git rev-parse --local-env-vars`). A hook in a linked worktree
    exports GIT_DIR, GIT_WORK_TREE and GIT_INDEX_FILE; under them a test's scratch `git init`, `git config` or
    `git add` writes into the real repository: core.worktree or a test identity into its shared config, or files
    into its index."""
    names = subprocess.run(["git", "rev-parse", "--local-env-vars"], capture_output=True, check=True, text=True)
    for name in names.stdout.split():
        monkeypatch.delenv(name, raising=False)


def clean_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """No global or system git config: the owner's global hk hooks would fire on a scratch repository's commit."""
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
