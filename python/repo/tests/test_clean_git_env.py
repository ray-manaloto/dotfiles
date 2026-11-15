"""A test's scratch git never writes into the repository a hook runs in."""

import os
import subprocess
import sys
from pathlib import Path


def test_a_scratch_identity_stays_in_its_scratch_repository(tmp_path: Path) -> None:
    # What the fixtures here do: init a scratch repository and give it an identity.
    subprocess.run(["git", "init", "-q", tmp_path], check=True)
    subprocess.run(["git", "config", "user.name", "Scratch Tester"], cwd=tmp_path, check=True)
    assert "Scratch Tester" in (tmp_path / ".git/config").read_text()


def test_the_suite_under_a_hook_git_dir_leaves_the_real_repository_alone(tmp_path: Path) -> None:
    # A hook in a linked worktree exports GIT_DIR, GIT_WORK_TREE and GIT_INDEX_FILE. Run the test above under them, as
    # pytest does from the hook, and the autouse fixture in conftest.py must keep its writes out of that repository.
    # Without it, the shared config of the real repository got the scratch identity (and core.worktree).
    real = tmp_path / "real"
    subprocess.run(["git", "init", "-q", real], check=True)
    before = (real / ".git/config").read_text()
    hook = {"GIT_DIR": str(real / ".git"), "GIT_WORK_TREE": str(real), "GIT_INDEX_FILE": str(real / ".git/index")}
    test = f"{__file__}::test_a_scratch_identity_stays_in_its_scratch_repository"
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-cov", "-p", "no:xdist", test],
        cwd=Path(__file__).parents[1],
        env={**os.environ, **hook},
        capture_output=True,
        check=False,
        text=True,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert (real / ".git/config").read_text() == before
