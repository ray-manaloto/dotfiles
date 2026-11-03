"""repotools main-guard as git runs it: a reference-transaction config hook in a real clone with an origin."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from repotools import main_guard
from repotools.cli import main

SCRIPT = str(Path(sys.executable).parent / "repotools")  # what uv installed from [project.scripts]
CHECKOUT = Path(__file__).parents[3]  # The repository root, where //repo: tasks resolve.
IDENTITY = ["-c", "user.name=t", "-c", "user.email=t@e"]


def git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *IDENTITY, *args], capture_output=True, check=False, text=True, cwd=cwd)


def ok(*args: str, cwd: Path | None = None) -> str:
    done = git(*args, cwd=cwd)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def refused(*args: str, cwd: Path | None = None) -> str:
    done = git(*args, cwd=cwd)
    assert done.returncode != 0, done.stdout
    return done.stderr


def tip(ref: str = "refs/heads/main") -> str:
    return ok("rev-parse", ref)


@pytest.fixture
def origin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The upstream: a repository whose main has one commit."""
    # A hook exports GIT_*, which would point git at the real checkout.
    for name in [name for name in os.environ if name.startswith("GIT_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    root = tmp_path / "origin"
    ok("init", "-q", "-b", "main", str(root))
    ok("commit", "-q", "--allow-empty", "-m", "one", cwd=root)
    return root


@pytest.fixture
def clone(origin: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A clone of origin, on main, with the guard installed and a feature branch one commit ahead."""
    root = origin.parent / "clone"
    ok("clone", "-q", str(origin), str(root))
    monkeypatch.chdir(root)
    main(["main-guard-install", "--bin", SCRIPT])
    ok("branch", "feature")
    ok("checkout", "-q", "feature")
    ok("commit", "-q", "--allow-empty", "-m", "feature")
    ok("checkout", "-q", "main")
    return root


@pytest.mark.usefixtures("clone")
def test_a_commit_on_main_is_refused() -> None:
    before = tip()
    error = refused("commit", "-q", "--allow-empty", "-m", "direct")
    assert "refs/heads/main may move only to refs/remotes/origin/main" in error
    assert tip() == before


@pytest.mark.usefixtures("clone")
def test_a_commit_on_main_without_hk_is_still_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HK", "0")
    assert "may move only" in refused("commit", "-q", "--no-verify", "--allow-empty", "-m", "direct")


@pytest.mark.usefixtures("clone")
def test_a_reset_of_main_to_another_commit_is_refused() -> None:
    assert "may move only" in refused("reset", "-q", "--hard", "feature")


@pytest.mark.usefixtures("clone")
def test_branch_force_on_main_is_refused() -> None:
    ok("checkout", "-q", "feature")
    assert "may move only" in refused("branch", "-f", "main", "feature")


def test_update_ref_on_main_is_refused_from_a_subfolder_of_a_linked_worktree(clone: Path) -> None:
    ok("worktree", "add", "-q", str(clone.parent / "wt"), "feature")
    (clone.parent / "wt" / "sub").mkdir()
    before = tip()
    assert "may move only" in refused("update-ref", "refs/heads/main", "feature", cwd=clone.parent / "wt" / "sub")
    assert tip() == before


@pytest.mark.usefixtures("clone")
def test_deleting_main_is_refused() -> None:
    ok("checkout", "-q", "feature")
    assert "may move only" in refused("branch", "-D", "main")
    assert tip()


def test_packing_main_is_allowed_and_a_packed_main_still_cannot_be_deleted(clone: Path) -> None:
    before = tip()
    ok("pack-refs", "--all", "--prune")
    assert f"{before} refs/heads/main" in (clone / ".git" / "packed-refs").read_text().splitlines()
    ok("checkout", "-q", "feature")
    assert "may move only" in refused("branch", "-D", "main")
    assert tip() == before


@pytest.mark.usefixtures("clone")
def test_a_fast_forward_to_a_fetched_origin_main_is_allowed(origin: Path) -> None:
    ok("commit", "-q", "--allow-empty", "-m", "merged on GitHub", cwd=origin)
    ok("fetch", "-q")
    ok("merge", "-q", "--ff-only", "origin/main")
    assert tip() == tip("refs/remotes/origin/main")


@pytest.mark.usefixtures("clone")
def test_other_branches_move_freely() -> None:
    ok("checkout", "-q", "feature")
    ok("commit", "-q", "--allow-empty", "-m", "more")
    ok("branch", "-f", "other", "main")
    ok("branch", "-D", "other")


@pytest.mark.usefixtures("clone")
def test_without_origin_main_the_refusal_says_missing() -> None:
    ok("update-ref", "-d", "refs/remotes/origin/main")
    assert "(missing)" in refused("reset", "-q", "--hard", "feature")


@pytest.mark.usefixtures("clone")
def test_rows_that_name_other_refs_or_are_malformed_pass() -> None:
    rows = "\nnot a row\n0 1 refs/heads/feature\nref:refs/heads/x ref:refs/heads/y HEAD\n"
    done = subprocess.run([SCRIPT, "main-guard"], input=rows, capture_output=True, check=False, text=True)
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


@pytest.mark.usefixtures("clone")
def test_install_twice_then_remove_twice() -> None:
    main(["main-guard-install", "--bin", SCRIPT])
    assert ok("config", "--local", "--get-all", "hook.main-guard.event") == "reference-transaction"
    main(["main-guard-remove"])
    main(["main-guard-remove"])
    assert git("config", "--local", "--get", "hook.main-guard.command").returncode == 1
    ok("commit", "-q", "--allow-empty", "-m", "unguarded")


def test_an_install_whose_executable_does_not_run_registers_nothing(
    clone: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["main-guard-remove"])
    with pytest.raises(SystemExit) as stopped:
        main(["main-guard-install", "--bin", str(clone / "missing")])
    assert stopped.value.code == 1
    assert "missing" in json.loads(capsys.readouterr().err)["error"]
    assert git("config", "--local", "--get", "hook.main-guard.command").returncode == 1


def test_the_shell_gate_starts_nothing_for_other_refs_and_fails_closed_for_main(clone: Path) -> None:
    # A guard executable that is gone: a feature commit never reaches it, a move of main refuses.
    ok("config", "--local", "hook.main-guard.command", main_guard.command(str(clone / "gone dir" / "repotools")))
    ok("checkout", "-q", "feature")
    ok("commit", "-q", "--allow-empty", "-m", "fast path")
    before = tip()
    error = refused("branch", "-f", "main", "feature")
    assert "did not start; repair it with mise run //repo:main-guard-install" in error
    assert tip() == before


def test_a_copy_whose_python_was_pruned_names_the_repair(clone: Path) -> None:
    # The real copy, from the real task, into scratch uv tool folders; then its venv's Python goes, as a prune does.
    tools = clone.parent / "uv"
    env = {**os.environ, "UV_TOOL_DIR": str(tools / "tools"), "UV_TOOL_BIN_DIR": str(tools / "bin")}
    mise = shutil.which("mise")
    assert mise is not None, "the global mise config installs mise"
    subprocess.run([mise, "run", "//repo:main-guard-copy"], cwd=CHECKOUT, env=env, capture_output=True, check=True)
    copy = tools / "bin" / "repotools"
    main(["main-guard-install", "--bin", str(copy)])
    ok("checkout", "-q", "feature")
    ok("commit", "-q", "--allow-empty", "-m", "the copy runs")
    python = tools / "tools" / "repotools" / "bin" / "python"
    python.unlink()
    python.symlink_to(clone.parent / "pruned" / "python3")
    ok("commit", "-q", "--allow-empty", "-m", "a feature commit never starts it")
    error = refused("branch", "-f", "main", "feature")
    assert f"main guard: {copy} did not start; repair it with mise run //repo:main-guard-install" in error


@pytest.mark.usefixtures("clone")
def test_a_refusal_by_a_working_guard_has_no_repair_hint() -> None:
    error = refused("commit", "-q", "--allow-empty", "-m", "direct")
    assert "may move only" in error
    assert "did not start" not in error
    assert "installed copy" not in error


@pytest.mark.usefixtures("clone")
def test_an_origin_main_with_other_guard_source_warns_and_still_fast_forwards(origin: Path) -> None:
    (origin / "python" / "repo").mkdir(parents=True)
    (origin / "python" / "repo" / "guard.py").write_text("one\n")
    ok("add", ".", cwd=origin)
    ok("commit", "-q", "-m", "guard fix", cwd=origin)
    ok("fetch", "-q")
    done = git("merge", "-q", "--ff-only", "origin/main")
    assert done.returncode == 0, done.stderr
    assert "the installed copy is not origin/main's python/repo" in done.stderr
    # Installed from that tree, a fast-forward that keeps it says nothing.
    main(["main-guard-install", "--bin", SCRIPT])
    ok("commit", "-q", "--allow-empty", "-m", "docs only", cwd=origin)
    ok("fetch", "-q")
    done = git("merge", "-q", "--ff-only", "origin/main")
    assert done.returncode == 0, done.stderr
    assert "installed copy" not in done.stderr
