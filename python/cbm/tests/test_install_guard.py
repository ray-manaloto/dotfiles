"""Install requires the main checkout unless explicitly opted in; verify is read-only anywhere."""

import errno
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest

from .conftest import CBM, TIMEOUT, cbm, events, git, launcher, package_source, restored


def snapshot(root: Path) -> dict[str, tuple[int, bytes | str | None]]:
    """Capture files, directories, modes and symlink targets, including dangling links."""
    return {
        str(path.relative_to(root)): (
            path.lstat().st_mode,
            str(path.readlink()) if path.is_symlink() else path.read_bytes() if path.is_file() else None,
        )
        for path in root.rglob("*")
    }


UNSAFE = ("branch", "worktree", "linked-main", "detached", "outside", "bare")


@pytest.fixture(params=UNSAFE)
def unsafe_checkout(home: Path, request: pytest.FixtureRequest) -> Path:
    checkout = home / "checkout"
    match request.param:
        case "branch":
            git(checkout, "checkout", "-b", "feature")
        case "worktree":
            linked = home / "linked"
            git(checkout, "worktree", "add", "-b", "feature", str(linked))
            checkout = linked
        case "linked-main":
            git(checkout, "checkout", "-b", "feature")
            linked = home / "linked"
            git(checkout, "worktree", "add", str(linked), "main")
            checkout = linked
        case "detached":
            git(checkout, "checkout", "--detach")
        case "outside":
            checkout = home
        case "bare":
            checkout = home / "bare"
            git(home, "init", "--bare", "--initial-branch=main", str(checkout))
    return checkout


def assert_refused(home: Path, cwd: Path, *message_parts: str) -> None:
    before = snapshot(home)
    done = cbm("install", cwd=cwd)
    assert done.returncode == 1, done.stdout + done.stderr
    [error] = events(done.stderr)
    assert error["code"] == "install_checkout_refused"
    assert error["message"]
    for part in message_parts:
        assert part in error["message"].casefold()
    assert events(done.stdout) == [
        {
            "event": "done",
            "command": "install",
            "failed": 1,
            "outcome": "failed",
            "message": "cbm: install refused: checkout check failed",
        }
    ]
    assert snapshot(home) == before


# An existing setup goes through the same snapshot comparison, so one kind with it is enough.
@pytest.mark.parametrize(
    ("unsafe_checkout", "existing"),
    [*((kind, False) for kind in UNSAFE), ("outside", True)],
    indirect=["unsafe_checkout"],
)
def test_unsafe_install_changes_nothing(home: Path, unsafe_checkout: Path, *, existing: bool) -> None:
    if existing:
        # A separate real main checkout provisions the existing setup, including its launcher symlink.
        initial = home / "initial"
        initial.mkdir()
        git(initial, "init", "--initial-branch=main")
        git(initial, "commit", "--allow-empty", "-m", "Initial fixture")
        assert cbm("install", cwd=initial).returncode == 0
    assert_refused(home, unsafe_checkout)


# The opt-in is one check before Git runs; a branch and a bare repository reach it two different ways.
@pytest.mark.parametrize("unsafe_checkout", ["branch", "bare"], indirect=True)
def test_explicit_opt_in_allows_install(home: Path, unsafe_checkout: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CBM_INSTALL_ALLOW_NON_MAIN", "1")
    done = cbm("install", cwd=unsafe_checkout)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not done.stderr
    assert events(done.stdout)[-1]["outcome"] == "done"
    assert restored(home)


@pytest.mark.parametrize("opt_in", [False, True])
def test_running_package_checkout_is_checked_from_main_cwd(
    home: Path, unsafe_checkout: Path, monkeypatch: pytest.MonkeyPatch, *, opt_in: bool
) -> None:
    package_source(unsafe_checkout, monkeypatch)
    # Use the actual uv-installed entrypoint unchanged, including its interpreter and import.
    command = unsafe_checkout / ".venv/bin/cbm"
    command.parent.mkdir(parents=True)
    shutil.copy2(CBM, command)
    if opt_in:
        monkeypatch.setenv("CBM_INSTALL_ALLOW_NON_MAIN", "1")
    before = snapshot(home)
    done = subprocess.run(
        [str(command), "install"], cwd=home / "package-checkout", env=os.environ.copy(),
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=TIMEOUT, check=False,
    )  # fmt: skip
    if opt_in:
        assert done.returncode == 0, done.stdout + done.stderr
        assert not done.stderr
        assert events(done.stdout)[-1]["outcome"] == "done"
        assert restored(home)
    else:
        assert done.returncode == 1, done.stdout + done.stderr
        [error] = events(done.stderr)
        assert error["code"] == "install_checkout_refused"
        assert "running package" in error["message"]
        assert events(done.stdout)[-1]["outcome"] == "failed"
        assert snapshot(home) == before


@pytest.mark.parametrize("location", ["cwd", "package"])
def test_form_feed_in_primary_checkout_path_allows_install(
    home: Path, monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    checkout = home / "primary\fcheckout"
    checkout.mkdir()
    if location == "package":
        package_source(checkout, monkeypatch)
    git(checkout, "init", "--initial-branch=main")
    git(checkout, "commit", "--allow-empty", "-m", "Initial fixture")
    done = cbm("install", cwd=checkout if location == "cwd" else home / "checkout")
    assert done.returncode == 0, done.stdout + done.stderr
    assert not done.stderr
    assert events(done.stdout)[-1]["outcome"] == "done"
    assert restored(home)


@pytest.mark.parametrize("value", ["", "0", "true", "yes"])
def test_opt_in_requires_the_documented_value(home: Path, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("CBM_INSTALL_ALLOW_NON_MAIN", value)
    git(home / "checkout", "checkout", "-b", "feature")
    assert_refused(home, home / "checkout", "primary checkout on main", "cbm_install_allow_non_main=1")


def test_main_package_subdirectory_allows_install(home: Path) -> None:
    package = home / "checkout/python/cbm"
    package.mkdir(parents=True)
    done = cbm("install", cwd=package)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not done.stderr
    assert events(done.stdout)[-1]["outcome"] == "done"
    assert restored(home)


@pytest.mark.parametrize("location", ["cwd", "package"])
def test_empty_main_repo_refuses_with_checkout_guidance(
    home: Path, monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    empty = home / "empty-repo"
    empty.mkdir()
    git(empty, "init", "--initial-branch=main")
    if location == "package":
        package_source(empty, monkeypatch)
    assert_refused(
        home, empty if location == "cwd" else home / "checkout",
        "install requires the primary checkout on main", "cbm_install_allow_non_main=1",
    )  # fmt: skip


@pytest.mark.parametrize("existing", [False, True])
def test_deleted_working_directory_refuses_without_changes(home: Path, *, existing: bool) -> None:
    if existing:
        assert cbm("install", cwd=home / "checkout").returncode == 0
    # CPython 3.15.2 site.py:1084-1095 processes site-packages (.pth coverage startup) before
    # sitecustomize. Delete the real cwd here, before the installed CLI executes, keeping coverage alive.
    startup = home / "package-checkout/python/cbm/src/sitecustomize.py"
    startup.write_text("import os\nos.rmdir(os.getcwd())\n")
    before = snapshot(home)
    deleted = home / "deleted-working-directory"
    deleted.mkdir()
    done = cbm("install", cwd=deleted)
    assert done.returncode == 1, done.stdout + done.stderr
    [error] = events(done.stderr)
    assert error["code"] == "install_checkout_refused"
    assert "current directory" in error["message"]
    assert events(done.stdout) == [
        {
            "event": "done",
            "command": "install",
            "failed": 1,
            "outcome": "failed",
            "message": "cbm: install refused: checkout check failed",
        }
    ]
    assert not deleted.exists()
    assert snapshot(home) == before


def test_missing_git_fails_closed(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    empty = home / "empty-bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    assert_refused(home, home / "checkout", "git", "no such file or directory")


@pytest.mark.parametrize("failure", ["invalid-config", "timeout"])
def test_git_failure_reports_the_cause_without_changes(
    home: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    config = home / "git-config"
    if failure == "invalid-config":
        config.write_text("[invalid\n")
        message = "bad config"
    else:
        # Real Git opens the global config for reading (git/git v2.56.0 config.c:1423-1437,
        # 1595-1598). A FIFO without a writer exercises the guard's real process timeout.
        os.mkfifo(config)
        monkeypatch.setenv("CBM_INSTALL_GIT_TIMEOUT_SECONDS", "0.1")
        message = "timed out after 0.1 seconds"
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    assert_refused(home, home / "checkout", "git", message)


def test_undecodable_git_output_is_a_refusal(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checkout = home / "checkout"
    config = checkout / ".git/config"
    # Git parses this as an integer (git/git v2.56.0 setup.c:724-725) and prints the raw bad
    # value on failure (config.c:1191-1237), producing non-UTF-8 stderr without a stand-in.
    config.write_bytes(config.read_bytes() + b"\n[core]\nrepositoryformatversion = \xff\n")
    monkeypatch.setenv("PYTHONUTF8", "1")
    assert_refused(home, checkout, "git", "decode")


# Without Git on PATH, the setting error still comes first: it is checked before Git discovery.
@pytest.mark.parametrize(
    ("value", "git_available"),
    [*((value, True) for value in ("", "invalid", "0", "-1", "11", "nan", "inf")), ("invalid", False)],
)
def test_invalid_git_timeout_is_a_setting_error(
    home: Path, monkeypatch: pytest.MonkeyPatch, value: str, *, git_available: bool
) -> None:
    monkeypatch.setenv("CBM_INSTALL_GIT_TIMEOUT_SECONDS", value)
    if not git_available:
        empty = home / "empty-bin"
        empty.mkdir()
        monkeypatch.setenv("PATH", str(empty))
    before = snapshot(home)
    done = cbm("install", cwd=home / "checkout")
    assert done.returncode == 2, done.stdout + done.stderr
    [error] = events(done.stderr)
    assert error["code"] == "invalid_setting"
    assert "CBM_INSTALL_GIT_TIMEOUT_SECONDS" in error["message"]
    assert not done.stdout
    assert snapshot(home) == before


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_signals_during_discovery_emit_failed_done_without_changes(
    home: Path, monkeypatch: pytest.MonkeyPatch, sig: signal.Signals
) -> None:
    config = home / "git-config"
    os.mkfifo(config)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    before = snapshot(home)
    with subprocess.Popen(
        [str(CBM), "install"], cwd=home / "checkout", env=os.environ.copy(), stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
    ) as proc:  # fmt: skip
        deadline = time.monotonic() + TIMEOUT
        while True:
            try:
                writer = os.open(config, os.O_WRONLY | os.O_NONBLOCK)
                break
            except OSError as open_error:
                if open_error.errno != errno.ENXIO:
                    raise
                assert proc.poll() is None, proc.communicate(timeout=TIMEOUT)
                assert time.monotonic() < deadline, "Git never opened its configuration FIFO"
                time.sleep(0.01)
        # A writer connects once real Git opens the FIFO for reading (git/git v2.56.0 config.c:1423-1437).
        # Keeping it open without data holds discovery until the process-group signal arrives.
        with os.fdopen(writer, "wb"):
            os.killpg(proc.pid, sig)
            stdout, stderr = proc.communicate(timeout=TIMEOUT)
    assert proc.returncode == 128 + sig, stdout + stderr
    [error] = events(stderr)
    assert error["code"] == "install_checkout_refused"
    assert "interrupt" in error["message"].casefold()
    assert events(stdout) == [
        {
            "event": "done",
            "command": "install",
            "failed": 1,
            "outcome": "failed",
            "message": "cbm: install refused: checkout check interrupted",
        }
    ]
    assert snapshot(home) == before


def test_fixture_ignores_ambient_global_git_trust(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (home / ".gitconfig").write_text("[safe]\n\tdirectory = *\n")
    monkeypatch.setenv("GIT_TEST_ASSUME_DIFFERENT_OWNER", "1")
    assert_refused(home, home / "checkout", "dubious ownership")


@pytest.mark.parametrize("configuration", ["none", "global", "environment"])
def test_git_safe_directory_configuration_is_preserved(
    home: Path, monkeypatch: pytest.MonkeyPatch, configuration: str
) -> None:
    checkout = home / "checkout"
    # Git's own ownership-test switch avoids privileged chown; it still evaluates real protected
    # safe.directory config (git/git v2.56.0 setup.c:1437-1462). No Python internals are patched.
    monkeypatch.setenv("GIT_TEST_ASSUME_DIFFERENT_OWNER", "1")
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    if configuration == "none":
        assert_refused(home, checkout, "git", "dubious ownership")
        return
    if configuration == "global":
        config = home / "git-config"
        git(checkout, "config", "--file", str(config), "safe.directory", str(checkout))
        git(checkout, "config", "--file", str(config), "--add", "safe.directory", str(home / "package-checkout"))
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    else:
        monkeypatch.setenv("GIT_CONFIG_COUNT", "2")
        monkeypatch.setenv("GIT_CONFIG_KEY_0", "safe.directory")
        monkeypatch.setenv("GIT_CONFIG_VALUE_0", str(checkout))
        monkeypatch.setenv("GIT_CONFIG_KEY_1", "safe.directory")
        monkeypatch.setenv("GIT_CONFIG_VALUE_1", str(home / "package-checkout"))
    done = cbm("install", cwd=checkout)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not done.stderr
    assert events(done.stdout)[-1]["outcome"] == "done"
    assert restored(home)


def test_inherited_git_location_cannot_disguise_a_linked_checkout(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checkout, linked = home / "checkout", home / "linked"
    git(checkout, "worktree", "add", "-b", "feature", str(linked))
    monkeypatch.setenv("GIT_DIR", str(checkout / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(checkout))
    monkeypatch.setenv("GIT_COMMON_DIR", str(checkout / ".git"))
    assert_refused(home, linked)


# verify never runs the checkout check, so one unsafe kind shows it.
@pytest.mark.parametrize("unsafe_checkout", ["worktree"], indirect=True)
def test_verify_from_any_checkout_preserves_setup(
    home: Path, unsafe_checkout: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CBM_INSTALL_ALLOW_NON_MAIN", "1")
    assert cbm("install", cwd=unsafe_checkout).returncode == 0
    monkeypatch.delenv("CBM_INSTALL_ALLOW_NON_MAIN")
    before = snapshot(home)
    done = cbm("verify", cwd=unsafe_checkout)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not done.stderr
    assert events(done.stdout)[-1]["outcome"] == "done"
    # Only the existing stand-in's process journals change when read-only probes run.
    after = snapshot(home)
    for journal in ("calls", "processes.jsonl"):
        before.pop(journal)
        after.pop(journal)
    assert after == before
    assert launcher(home).is_symlink()
