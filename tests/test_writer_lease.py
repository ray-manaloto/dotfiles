# Copyright (c) 2026 Raymond Manaloto
"""Real-process contract tests for the Git-common-dir writer lease (#753)."""

from __future__ import annotations

import json
import os
import select
import shlex
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from dotfiles_setup import writer_lease

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

_HANDOFF_A = "a" * 64
_HANDOFF_B = "b" * 64
_READY_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class LeaseArgs:
    """Arguments shared by the real public lease subprocess helpers."""

    task_id: str
    handoff_sha256: str
    owner: str | None = None
    transition: str | None = None
    expected_prior_receipt_sha256: str | None = None


@dataclass(frozen=True)
class HookCall:
    """One real native-hook invocation."""

    event: str
    session_id: str
    tool_name: str
    tool_use_id: str
    tool_input: dict[str, object]


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout.strip()


def test_git_executable_is_an_explicit_absolute_project_contract() -> None:
    """Host and container resolution must never consult ambient PATH."""
    executable = writer_lease.git_executable()

    assert executable.is_absolute()
    assert executable in {
        candidate.resolve(strict=False)
        for candidate in writer_lease.trusted_git_executables()
    }
    assert executable.is_file()
    assert os.access(executable, os.X_OK)


def test_container_git_contract_is_derived_from_the_locked_package() -> None:
    """The container path is derived from the lock, never a duplicate literal."""
    executable = writer_lease.container_git_executable()

    assert executable.parent.name == "bin"
    assert executable.parent.parent.parent == writer_lease.CONTAINER_GIT_INSTALL_ROOT


def test_container_git_contract_rejects_lock_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A lock with no authoritative Git package fails closed."""
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    source = (project_root / ".devcontainer/mise-system.lock").read_text(
        encoding="utf-8"
    )
    drifted = tmp_path / "mise-system.lock"
    drifted.write_text(
        source.replace('"conda:git"', '"retired:git"'),
        encoding="utf-8",
    )

    with pytest.raises(
        writer_lease.LeaseError,
        match="does not declare conda:git",
    ):
        writer_lease.container_git_executable(drifted)


def _write_executable(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


def test_linux_git_ignores_an_executable_usr_bin_fallback(tmp_path: Path) -> None:
    """Linux must select only lock-derived conda Git, even if /usr/bin exists."""
    root = tmp_path / "linux-root"
    hostile_host_git = root / "usr" / "bin" / "git"
    _write_executable(hostile_host_git)
    install_root = root / writer_lease.CONTAINER_GIT_INSTALL_ROOT.relative_to("/")
    locked_git = writer_lease.container_git_executable(install_root=install_root)
    _write_executable(locked_git)

    selected = writer_lease.git_executable(platform="linux", filesystem_root=root)

    assert hostile_host_git.is_file()
    assert os.access(hostile_host_git, os.X_OK)
    assert selected == locked_git.resolve()
    assert selected != hostile_host_git.resolve()


def test_darwin_git_fails_closed_without_exact_usr_bin_path(tmp_path: Path) -> None:
    """Darwin cannot fall back to a wrong host path or the Linux locked path."""
    root = tmp_path / "darwin-root"
    _write_executable(root / "bin" / "git")
    install_root = root / writer_lease.CONTAINER_GIT_INSTALL_ROOT.relative_to("/")
    _write_executable(writer_lease.container_git_executable(install_root=install_root))

    with pytest.raises(
        writer_lease.LeaseError,
        match="trusted Darwin Git executable is unavailable",
    ):
        writer_lease.git_executable(platform="darwin", filesystem_root=root)


def _repo_with_linked_worktree(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    linked = tmp_path / "linked"
    repo.mkdir(parents=True)
    _git(repo, "init", "--initial-branch", "main")
    _git(repo, "config", "user.email", "writer-lease@example.invalid")
    _git(repo, "config", "user.name", "Writer Lease Test")
    (repo / "README.md").write_text("writer lease fixture\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "fixture")
    _git(repo, "worktree", "add", "-b", "successor", str(linked))
    return repo, linked


def _lease_command(
    operation: str,
    lease: LeaseArgs,
) -> list[str]:
    command = [sys.executable, "-m", "dotfiles_setup.main", "writer-lease", operation]
    command.extend(["--task-id", lease.task_id])
    command.extend(["--handoff-sha256", lease.handoff_sha256])
    if lease.owner is not None:
        command.extend(["--owner", lease.owner])
    if lease.transition is not None:
        command.extend(["--expected-transition", lease.transition])
    if lease.expected_prior_receipt_sha256 is not None:
        command.extend(
            [
                "--expected-prior-receipt-sha256",
                lease.expected_prior_receipt_sha256,
            ]
        )
    return command


def _start_holder(
    cwd: Path,
    *,
    lease: LeaseArgs,
) -> tuple[subprocess.Popen[str], dict[str, Any]]:
    process = subprocess.Popen(
        _lease_command("hold", lease),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=os.environ.copy(),
    )
    assert process.stdout is not None
    readable, _, _ = select.select([process.stdout], [], [], _READY_TIMEOUT_SECONDS)
    if not readable:
        process.kill()
        _, stderr = process.communicate(timeout=5)
        pytest.fail(f"writer-lease holder produced no readiness receipt: {stderr}")
    line = process.stdout.readline()
    if not line:
        _, stderr = process.communicate(timeout=5)
        pytest.fail(
            f"writer-lease holder exited {process.returncode} before ready: {stderr}"
        )
    payload: dict[str, Any] = json.loads(line)
    assert payload["status"] == "held"
    assert process.poll() is None
    return process, payload


def _stop(process: subprocess.Popen[str], *, abrupt: bool = False) -> None:
    if process.poll() is not None:
        return
    process.kill() if abrupt else process.terminate()
    process.communicate(timeout=5)


def _status(cwd: Path) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-m", "dotfiles_setup.main", "writer-lease", "status"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    payload: dict[str, Any] = json.loads(result.stdout)
    return payload


def _pretooluse(
    cwd: Path,
    *,
    session_id: str,
    target: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "dotfiles_setup.main", "hook", "pretooluse"],
        cwd=cwd,
        input=json.dumps(
            {
                "session_id": session_id,
                "tool_name": "Edit",
                "tool_input": {"file_path": str(target)},
                "tool_use_id": "claude-direct-edit",
            }
        ),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def _codex_pretooluse(
    cwd: Path,
    *,
    session_id: str,
    tool_name: str,
    tool_input: Mapping[str, object],
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "dotfiles_setup.codex_writer_lease_hook"],
        cwd=cwd,
        input=json.dumps(
            {
                "cwd": str(cwd),
                "hook_event_name": "PreToolUse",
                "session_id": session_id,
                "tool_use_id": "tool-review-control",
                "tool_input": tool_input,
                "tool_name": tool_name,
            }
        ),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def _common_dir(cwd: Path) -> Path:
    return Path(_git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"))


def _raw_hook(
    cwd: Path,
    call: HookCall,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "dotfiles_setup.codex_writer_lease_hook"],
        cwd=cwd,
        input=json.dumps(
            {
                "cwd": str(cwd),
                "hook_event_name": call.event,
                "session_id": call.session_id,
                "tool_input": call.tool_input,
                "tool_name": call.tool_name,
                "tool_use_id": call.tool_use_id,
            }
        ),
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )


def _writer_state_bytes(cwd: Path) -> dict[str, tuple[int, bytes | str]]:
    result: dict[str, tuple[int, bytes | str]] = {}
    for path in sorted(cwd.rglob("*")):
        if path == cwd / ".git" or cwd / ".git" in path.parents:
            continue
        relative = str(path.relative_to(cwd))
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            result[relative] = (metadata.st_mode, str(path.readlink()))
        elif stat.S_ISREG(metadata.st_mode):
            result[relative] = (metadata.st_mode, path.read_bytes())
    return result


def _start_state_lock_holder(lock_path: Path, seconds: float) -> subprocess.Popen[str]:
    script = """
import fcntl
import os
import sys
import time
fd = os.open(sys.argv[1], os.O_RDWR | os.O_CLOEXEC)
fcntl.flock(fd, fcntl.LOCK_EX)
print("locked", flush=True)
time.sleep(float(sys.argv[2]))
os.close(fd)
"""
    process = subprocess.Popen(
        [sys.executable, "-c", script, str(lock_path), str(seconds)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    assert process.stdout.readline().strip() == "locked"
    return process


@pytest.fixture
def holders() -> Iterator[list[subprocess.Popen[str]]]:
    running: list[subprocess.Popen[str]] = []
    yield running
    for process in running:
        _stop(process, abrupt=True)


def test_real_linked_worktree_contention_and_pre_mutation_identity(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, linked = _repo_with_linked_worktree(tmp_path)
    repo_before = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    linked_before = _git(linked, "status", "--porcelain=v1", "--untracked-files=all")
    first, receipt = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="task-a",
            owner="/root/task-a",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(first)
    assert _status(repo)["state"] == "live"

    contender = subprocess.run(
        _lease_command(
            "hold",
            LeaseArgs(
                task_id="task-b",
                owner="/root/task-b",
                handoff_sha256=_HANDOFF_B,
                transition="initial",
            ),
        ),
        cwd=linked,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert contender.returncode != 0
    assert "live writer" in contender.stderr

    matching = subprocess.run(
        _lease_command("check", LeaseArgs("task-a", _HANDOFF_A)),
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert matching.returncode == 0, matching.stderr
    assert json.loads(matching.stdout)["receipt_sha256"] == receipt["receipt_sha256"]

    wrong_task = subprocess.run(
        _lease_command("check", LeaseArgs("task-b", _HANDOFF_A)),
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert wrong_task.returncode != 0
    assert "task identity" in wrong_task.stderr

    wrong_handoff = subprocess.run(
        _lease_command("check", LeaseArgs("task-a", _HANDOFF_B)),
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert wrong_handoff.returncode != 0
    assert "handoff digest" in wrong_handoff.stderr

    wrong_worktree = subprocess.run(
        _lease_command("check", LeaseArgs("task-a", _HANDOFF_A)),
        cwd=linked,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert wrong_worktree.returncode != 0
    assert "worktree identity" in wrong_worktree.stderr
    repo_after = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    assert repo_after == repo_before
    assert (
        _git(linked, "status", "--porcelain=v1", "--untracked-files=all")
        == linked_before
    )


def test_clean_digest_bound_handoff(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, linked = _repo_with_linked_worktree(tmp_path)
    first, first_receipt = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="task-a",
            owner="/root/task-a",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(first)
    _stop(first)
    stale_status = _status(repo)
    assert stale_status["state"] == "stale"
    assert stale_status["receipt_sha256"] == first_receipt["receipt_sha256"]

    successor, successor_receipt = _start_holder(
        linked,
        lease=LeaseArgs(
            task_id="task-b",
            owner="/root/task-b",
            handoff_sha256=_HANDOFF_B,
            transition="handoff",
            expected_prior_receipt_sha256=first_receipt["receipt_sha256"],
        ),
    )
    holders.append(successor)
    assert _status(linked)["state"] == "live"
    assert successor_receipt["receipt"]["transition"] == "handoff"
    assert (
        successor_receipt["receipt"]["prior_receipt_sha256"]
        == first_receipt["receipt_sha256"]
    )


def test_abrupt_death_requires_exact_digest_recovery(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, linked = _repo_with_linked_worktree(tmp_path)
    first, first_receipt = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="task-a",
            owner="/root/task-a",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(first)
    _stop(first, abrupt=True)

    unbound = subprocess.run(
        _lease_command(
            "hold",
            LeaseArgs(
                task_id="task-b",
                owner="/root/task-b",
                handoff_sha256=_HANDOFF_B,
                transition="initial",
            ),
        ),
        cwd=linked,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert unbound.returncode != 0
    assert "prior receipt" in unbound.stderr

    wrong_digest = subprocess.run(
        _lease_command(
            "hold",
            LeaseArgs(
                task_id="task-b",
                owner="/root/task-b",
                handoff_sha256=_HANDOFF_B,
                transition="recovery",
                expected_prior_receipt_sha256="c" * 64,
            ),
        ),
        cwd=linked,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert wrong_digest.returncode != 0
    assert "prior receipt digest" in wrong_digest.stderr

    recovered, recovery_receipt = _start_holder(
        linked,
        lease=LeaseArgs(
            task_id="task-b",
            owner="/root/task-b",
            handoff_sha256=_HANDOFF_B,
            transition="recovery",
            expected_prior_receipt_sha256=first_receipt["receipt_sha256"],
        ),
    )
    holders.append(recovered)
    assert recovery_receipt["receipt"]["transition"] == "recovery"


def test_malformed_receipt_fails_closed_without_rewriting_it(tmp_path: Path) -> None:
    repo, _linked = _repo_with_linked_worktree(tmp_path)
    common_dir = Path(
        _git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    )
    receipt = common_dir / "codex-writer-lease" / "receipt.json"
    receipt.parent.mkdir(mode=0o700)
    malformed = b'{"schema":"wrong"}\n'
    receipt.write_bytes(malformed)

    result = subprocess.run(
        _lease_command(
            "hold",
            LeaseArgs(
                task_id="task-a",
                owner="/root/task-a",
                handoff_sha256=_HANDOFF_A,
                transition="recovery",
                expected_prior_receipt_sha256="c" * 64,
            ),
        ),
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode != 0
    assert "legacy" in result.stderr
    assert receipt.read_bytes() == malformed


def test_independent_git_common_directories_do_not_contend(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    first_repo, _ = _repo_with_linked_worktree(tmp_path / "first")
    second_repo, _ = _repo_with_linked_worktree(tmp_path / "second")
    first, _ = _start_holder(
        first_repo,
        lease=LeaseArgs(
            task_id="task-a",
            owner="/root/task-a",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(first)
    second, _ = _start_holder(
        second_repo,
        lease=LeaseArgs(
            task_id="task-b",
            owner="/root/task-b",
            handoff_sha256=_HANDOFF_B,
            transition="initial",
        ),
    )
    holders.append(second)
    assert first.poll() is None
    assert second.poll() is None


def test_real_pretooluse_hook_allows_owner_and_denies_second_session(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, _linked = _repo_with_linked_worktree(tmp_path)
    _git(repo, "checkout", "-b", "owner")
    holder, _receipt = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="session-a",
            owner="claude-session-a",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(holder)
    target = repo / "README.md"

    owner = _pretooluse(repo, session_id="session-a", target=target)
    assert owner.returncode == 0
    assert owner.stdout == ""

    contender = _pretooluse(repo, session_id="session-b", target=target)
    assert contender.returncode == 0
    assert '"permissionDecision": "deny"' in contender.stdout
    assert "writer lease" in contender.stdout.lower()


def test_codex_native_hook_blocks_hostile_bash_and_apply_patch(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, _linked = _repo_with_linked_worktree(tmp_path)
    holder, _receipt = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="codex-owner",
            owner="/root/codex-owner",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(holder)

    owner = _codex_pretooluse(
        repo,
        session_id="codex-owner",
        tool_name="apply_patch",
        tool_input={"command": "*** Begin Patch\n*** End Patch"},
    )
    assert owner.returncode == 0
    assert owner.stdout == ""

    for tool_name, tool_input in (
        ("apply_patch", {"command": "*** Begin Patch\n*** End Patch"}),
        ("Bash", {"command": "git add README.md"}),
    ):
        contender = _codex_pretooluse(
            repo,
            session_id="codex-contender",
            tool_name=tool_name,
            tool_input=tool_input,
        )
        assert contender.returncode == 0
        output = json.loads(contender.stdout)
        decision = output["hookSpecificOutput"]
        assert decision["permissionDecision"] == "deny"
        assert "task identity" in decision["permissionDecisionReason"]


def test_codex_hook_allows_only_plain_lease_bootstrap_without_an_owner(
    tmp_path: Path,
) -> None:
    repo, _linked = _repo_with_linked_worktree(tmp_path)
    mise = writer_lease.mise_executable()
    allowed = _codex_pretooluse(
        repo,
        session_id="codex-successor",
        tool_name="Bash",
        tool_input={"command": f"{mise} -C {repo.resolve()} run writer-lease-status"},
    )
    assert allowed.returncode == 0
    assert allowed.stdout == ""

    duplicate = _codex_pretooluse(
        repo,
        session_id="codex-successor",
        tool_name="Bash",
        tool_input={
            "command": (
                f"{mise} -C {repo.resolve()} run writer-lease-hold -- "
                "--task-id codex-successor --owner codex:codex-successor "
                f"--handoff-sha256 {_HANDOFF_A} --task-id codex-successor"
            )
        },
    )
    assert duplicate.returncode == 0
    assert (
        json.loads(duplicate.stdout)["hookSpecificOutput"]["permissionDecision"]
        == "deny"
    )

    compound = _codex_pretooluse(
        repo,
        session_id="codex-successor",
        tool_name="Bash",
        tool_input={
            "command": (
                f"{mise} -C {repo.resolve()} run writer-lease-status; git add README.md"
            )
        },
    )
    assert compound.returncode == 0
    assert (
        json.loads(compound.stdout)["hookSpecificOutput"]["permissionDecision"]
        == "deny"
    )


def test_receipt_is_bound_to_the_actual_live_holder_not_any_flock(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, _linked = _repo_with_linked_worktree(tmp_path)
    holder, receipt = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="task-a",
            owner="/root/task-a",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(holder)
    _stop(holder, abrupt=True)
    lock_path = _common_dir(repo) / "codex-writer-lease" / "writer.lock"
    unrelated = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import fcntl,pathlib,sys,time; "
                "f=pathlib.Path(sys.argv[1]).open('a'); "
                "fcntl.flock(f.fileno(), fcntl.LOCK_EX); "
                "print('ready', flush=True); time.sleep(30)"
            ),
            str(lock_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    holders.append(unrelated)
    assert unrelated.stdout is not None
    assert unrelated.stdout.readline().strip() == "ready"

    stale_identity = subprocess.run(
        _lease_command("check", LeaseArgs("task-a", _HANDOFF_A)),
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert stale_identity.returncode != 0
    assert "holder" in stale_identity.stderr.lower()
    assert receipt["receipt_sha256"] in json.dumps(_status(repo))


def test_status_is_non_mutating_and_unsafe_state_paths_fail_closed(
    tmp_path: Path,
) -> None:
    repo, _linked = _repo_with_linked_worktree(tmp_path / "absent")
    state = _common_dir(repo) / "codex-writer-lease"
    assert not state.exists()
    assert _status(repo)["state"] == "absent"
    assert not state.exists()

    victim_repo, _ = _repo_with_linked_worktree(tmp_path / "symlink")
    victim_state = _common_dir(victim_repo) / "codex-writer-lease"
    shared = tmp_path / "shared"
    shared.mkdir()
    victim_state.symlink_to(shared, target_is_directory=True)
    result = subprocess.run(
        [sys.executable, "-m", "dotfiles_setup.main", "writer-lease", "status"],
        cwd=victim_repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode != 0
    assert "unsafe" in result.stderr.lower()
    assert list(shared.iterdir()) == []


def test_fifo_and_directory_lock_paths_deny_without_hanging(tmp_path: Path) -> None:
    for kind in ("fifo", "directory"):
        repo, _ = _repo_with_linked_worktree(tmp_path / kind)
        state = _common_dir(repo) / "codex-writer-lease"
        state.mkdir(mode=0o700)
        lock_path = state / "writer.lock"
        if kind == "fifo":
            os.mkfifo(lock_path, mode=0o600)
        else:
            lock_path.mkdir()
        result = _raw_hook(
            repo,
            HookCall(
                event="PreToolUse",
                session_id="hostile",
                tool_name="Bash",
                tool_use_id=f"tool-{kind}",
                tool_input={"command": "git add README.md"},
            ),
        )
        assert result.returncode == 0
        decision = json.loads(result.stdout)["hookSpecificOutput"]
        assert decision["permissionDecision"] == "deny"
        assert "unsafe" in decision["permissionDecisionReason"].lower()


def test_invalid_audit_is_rejected_and_audit_failure_never_publishes_receipt(
    tmp_path: Path,
) -> None:
    repo, _ = _repo_with_linked_worktree(tmp_path / "invalid")
    holder, _ = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="task-a",
            owner="/root/task-a",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    _stop(holder)
    state = _common_dir(repo) / "codex-writer-lease"
    prior_digest = _status(repo)["receipt_sha256"]
    generation = (state / "current").read_text(encoding="ascii")
    audit = state / generation / "audit.jsonl"
    audit.write_bytes(audit.read_bytes() + b"not-json\n")
    before = _writer_state_bytes(state)
    result = subprocess.run(
        _lease_command(
            "hold",
            LeaseArgs(
                task_id="task-b",
                owner="/root/task-b",
                handoff_sha256=_HANDOFF_B,
                transition="handoff",
                expected_prior_receipt_sha256=prior_digest,
            ),
        ),
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert result.returncode != 0
    assert "generation digest" in result.stderr.lower()
    assert _writer_state_bytes(state) == before

    broken_repo, _ = _repo_with_linked_worktree(tmp_path / "transaction")
    broken_state = _common_dir(broken_repo) / "codex-writer-lease"
    broken_state.mkdir(mode=0o700)
    (broken_state / "audit.jsonl").mkdir()
    broken = subprocess.run(
        _lease_command(
            "hold",
            LeaseArgs(
                task_id="task-a",
                owner="/root/task-a",
                handoff_sha256=_HANDOFF_A,
                transition="initial",
            ),
        ),
        cwd=broken_repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert broken.returncode != 0
    assert not (broken_state / "current").exists()


def test_bootstrap_rejects_environment_path_and_unpinned_argv(tmp_path: Path) -> None:
    repo, _ = _repo_with_linked_worktree(tmp_path)
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_mise = fake_bin / "mise"
    fake_mise.write_text("#!/bin/sh\nprintf hostile > README.md\n", encoding="utf-8")
    fake_mise.chmod(0o755)
    before = (repo / "README.md").read_bytes()
    command = f"env PATH={fake_bin} mise run writer-lease-status"
    decision = _raw_hook(
        repo,
        HookCall(
            event="PreToolUse",
            session_id="hostile",
            tool_name="Bash",
            tool_use_id="tool-bootstrap",
            tool_input={"command": command},
        ),
    )
    assert decision.returncode == 0
    assert (
        json.loads(decision.stdout)["hookSpecificOutput"]["permissionDecision"]
        == "deny"
    )
    assert (repo / "README.md").read_bytes() == before


def test_inflight_mutation_drains_before_handoff_and_posttooluse_releases_it(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, linked = _repo_with_linked_worktree(tmp_path)
    first, first_receipt = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="session-a",
            owner="/root/session-a",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(first)
    started = _raw_hook(
        repo,
        HookCall(
            event="PreToolUse",
            session_id="session-a",
            tool_name="Bash",
            tool_use_id="exec-delayed",
            tool_input={"command": "sleep 30; printf late > README.md"},
        ),
    )
    assert started.returncode == 0
    assert started.stdout == ""
    first.terminate()
    with pytest.raises(subprocess.TimeoutExpired):
        first.wait(timeout=0.5)

    finished = _raw_hook(
        repo,
        HookCall(
            event="PostToolUse",
            session_id="session-a",
            tool_name="Bash",
            tool_use_id="exec-delayed",
            tool_input={"command": "sleep 30; printf late > README.md"},
        ),
    )
    assert finished.returncode == 0, finished.stderr
    assert finished.stdout == "", finished.stdout
    first.wait(timeout=5)
    successor, successor_receipt = _start_holder(
        linked,
        lease=LeaseArgs(
            task_id="session-b",
            owner="/root/session-b",
            handoff_sha256=_HANDOFF_B,
            transition="handoff",
            expected_prior_receipt_sha256=first_receipt["receipt_sha256"],
        ),
    )
    holders.append(successor)
    assert successor_receipt["receipt"]["transition"] == "handoff"


def test_crash_transition_is_derived_as_recovery_and_claude_bash_is_owned(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, linked = _repo_with_linked_worktree(tmp_path)
    first, first_receipt = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="session-a",
            owner="/root/session-a",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(first)
    claude_bash = subprocess.run(
        [sys.executable, "-m", "dotfiles_setup.main", "hook", "pretooluse"],
        cwd=repo,
        input=json.dumps(
            {
                "session_id": "session-b",
                "tool_name": "Bash",
                "tool_input": {"command": "printf hostile > README.md"},
                "tool_use_id": "claude-bash",
            }
        ),
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert '"permissionDecision": "deny"' in claude_bash.stdout
    _stop(first, abrupt=True)
    mislabeled = subprocess.run(
        _lease_command(
            "hold",
            LeaseArgs(
                task_id="session-b",
                owner="/root/session-b",
                handoff_sha256=_HANDOFF_B,
                transition="handoff",
                expected_prior_receipt_sha256=first_receipt["receipt_sha256"],
            ),
        ),
        cwd=linked,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert mislabeled.returncode != 0
    assert "recovery" in mislabeled.stderr.lower()


def test_lease_flows_preserve_dirty_ignored_untracked_and_omc_bytes(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, linked = _repo_with_linked_worktree(tmp_path)
    (repo / ".gitignore").write_text("ignored.bin\n", encoding="utf-8")
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "ignore fixture")
    (repo / "README.md").write_bytes(b"dirty\x00tracked\n")
    (repo / "ignored.bin").write_bytes(b"ignored\x00bytes")
    (repo / "untracked.bin").write_bytes(b"untracked\x00bytes")
    (repo / ".omc").mkdir()
    (repo / ".omc" / "evidence.bin").write_bytes(b"omc\x00evidence")
    before_bytes = _writer_state_bytes(repo)
    before_status = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")

    holder, receipt = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="task-a",
            owner="/root/task-a",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(holder)
    assert _status(repo)["state"] == "live"
    _stop(holder)
    successor, _ = _start_holder(
        linked,
        lease=LeaseArgs(
            task_id="task-b",
            owner="/root/task-b",
            handoff_sha256=_HANDOFF_B,
            transition="handoff",
            expected_prior_receipt_sha256=receipt["receipt_sha256"],
        ),
    )
    holders.append(successor)
    _stop(successor)
    assert _writer_state_bytes(repo) == before_bytes
    assert (
        _git(repo, "status", "--porcelain=v1", "--untracked-files=all") == before_status
    )


def test_recovery_refuses_inflight_until_write_stdin_completion_drains_it(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, linked = _repo_with_linked_worktree(tmp_path)
    first, first_receipt = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="session-a",
            owner="/root/session-a",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(first)
    started = _raw_hook(
        repo,
        HookCall(
            event="PreToolUse",
            session_id="session-a",
            tool_name="Bash",
            tool_use_id="exec-background",
            tool_input={"command": "sleep 30; printf late > README.md"},
        ),
    )
    assert started.stdout == ""
    _stop(first, abrupt=True)

    blocked = subprocess.run(
        _lease_command(
            "hold",
            LeaseArgs(
                task_id="session-b",
                owner="/root/session-b",
                handoff_sha256=_HANDOFF_B,
                transition="recovery",
                expected_prior_receipt_sha256=first_receipt["receipt_sha256"],
            ),
        ),
        cwd=linked,
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    assert blocked.returncode != 0
    assert "in-flight" in blocked.stderr

    # Codex emits the original Bash tool_use_id when write_stdin observes final
    # unified-exec completion. This real PostToolUse replay drains that entry.
    finished = _raw_hook(
        repo,
        HookCall(
            event="PostToolUse",
            session_id="session-a",
            tool_name="Bash",
            tool_use_id="exec-background",
            tool_input={"command": "sleep 30; printf late > README.md"},
        ),
    )
    assert finished.stdout == ""
    recovered, recovery_receipt = _start_holder(
        linked,
        lease=LeaseArgs(
            task_id="session-b",
            owner="/root/session-b",
            handoff_sha256=_HANDOFF_B,
            transition="recovery",
            expected_prior_receipt_sha256=first_receipt["receipt_sha256"],
        ),
    )
    holders.append(recovered)
    assert recovery_receipt["receipt"]["transition"] == "recovery"


def test_state_files_are_private_regular_and_receipt_audit_symlinks_deny(
    tmp_path: Path,
) -> None:
    for attacked_name in ("receipt.json", "audit.jsonl"):
        repo, _ = _repo_with_linked_worktree(tmp_path / attacked_name)
        holder, _ = _start_holder(
            repo,
            lease=LeaseArgs(
                task_id="session-a",
                owner="/root/session-a",
                handoff_sha256=_HANDOFF_A,
                transition="initial",
            ),
        )
        _stop(holder)
        state = _common_dir(repo) / "codex-writer-lease"
        assert stat.S_IMODE(state.lstat().st_mode) == 0o700
        generation = (state / "current").read_text(encoding="ascii")
        regular_paths = [
            state / "current",
            state / "state.lock",
            state / "writer.lock",
            state / generation / "receipt.json",
            state / generation / "audit.jsonl",
            state / generation / "inflight.json",
        ]
        assert all(stat.S_ISREG(path.lstat().st_mode) for path in regular_paths)
        assert all(
            stat.S_IMODE(path.lstat().st_mode) == 0o600 for path in regular_paths
        )

        victim = tmp_path / f"victim-{attacked_name}"
        victim.write_bytes(b"preserve-victim")
        attacked = state / generation / attacked_name
        attacked.rename(attacked.with_suffix(attacked.suffix + ".preserved"))
        attacked.symlink_to(victim)
        before = victim.read_bytes()
        result = _raw_hook(
            repo,
            HookCall(
                event="PreToolUse",
                session_id="hostile",
                tool_name="Bash",
                tool_use_id=f"attack-{attacked_name}",
                tool_input={"command": "git add README.md"},
            ),
        )
        assert result.returncode == 0
        decision = json.loads(result.stdout)["hookSpecificOutput"]
        assert decision["permissionDecision"] == "deny"
        assert "unsafe" in decision["permissionDecisionReason"].lower()
        assert victim.read_bytes() == before


def test_pinned_system_runner_uses_real_project_runtime_and_drains_posttooluse(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, _ = _repo_with_linked_worktree(tmp_path)
    project_root = Path(__file__).resolve().parents[1]
    (repo / "python").mkdir()
    (repo / "python" / ".venv").symlink_to(project_root / "python" / ".venv")
    (repo / "python" / "src").mkdir()
    (repo / "python" / "src" / "dotfiles_setup").symlink_to(
        project_root / "python" / "src" / "dotfiles_setup"
    )
    runner = project_root / "scripts" / "writer-lease-hook-runner.py"
    (repo / "scripts").mkdir()
    (repo / "scripts" / runner.name).symlink_to(runner)
    nested = repo / "nested" / "session-cwd"
    nested.mkdir(parents=True)
    (nested / ".git").mkdir()
    hooks = json.loads((project_root / ".codex/hooks.json").read_text(encoding="utf-8"))
    pre_command = hooks["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
    post_command = hooks["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
    assert pre_command == post_command
    holder, _ = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="runner-owner",
            owner="/root/runner-owner",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(holder)

    def run(call: HookCall) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["/bin/sh", "-c", pre_command],
            cwd=nested,
            input=json.dumps(
                {
                    "cwd": str(nested),
                    "hook_event_name": call.event,
                    "session_id": call.session_id,
                    "tool_input": call.tool_input,
                    "tool_name": call.tool_name,
                    "tool_use_id": call.tool_use_id,
                }
            ).encode(),
            capture_output=True,
            check=False,
            timeout=10,
        )

    owner_call = HookCall(
        event="PreToolUse",
        session_id="runner-owner",
        tool_name="Bash",
        tool_use_id="runner-tool",
        tool_input={"command": "git status"},
    )
    owner_pre = run(owner_call)
    assert owner_pre.returncode == 0
    assert owner_pre.stdout == b""
    assert _status(repo)["inflight"] == ["runner-tool"]
    owner_post = run(
        HookCall(
            event="PostToolUse",
            session_id="runner-owner",
            tool_name="Bash",
            tool_use_id="runner-tool",
            tool_input={"command": "git status"},
        )
    )
    assert owner_post.returncode == 0
    assert owner_post.stdout == b""
    assert _status(repo)["inflight"] == []
    hostile = run(
        HookCall(
            event="PreToolUse",
            session_id="runner-hostile",
            tool_name="Bash",
            tool_use_id="runner-hostile-tool",
            tool_input={"command": "git add README.md"},
        )
    )
    assert hostile.returncode == 0
    hostile_decision = json.loads(hostile.stdout)["hookSpecificOutput"]
    assert hostile_decision["permissionDecision"] == "deny"


def test_codex_hook_command_reaches_the_tracked_runner_from_nested_cwd() -> None:
    """The public command locates the tracked runner without a platform Git."""
    project_root = Path(__file__).resolve().parents[1]
    hooks = json.loads((project_root / ".codex/hooks.json").read_text(encoding="utf-8"))
    command = hooks["hooks"]["PreToolUse"][0]["hooks"][0]["command"]

    arguments = shlex.split(command)
    assert arguments[:4] == ["/usr/bin/python3", "-I", "-S", "-c"]
    assert "/usr/bin/git" not in command
    assert "pathlib" in arguments[4]
    assert "runpy.run_path" in arguments[4]
    assert 'roots[-1]/"scripts/writer-lease-hook-runner.py"' in arguments[4]
    nested = project_root / "python" / "src" / "dotfiles_setup"
    payload = {
        "cwd": str(nested),
        "hook_event_name": "PreToolUse",
        "session_id": "hostile-bootstrap-control",
        "tool_input": {"command": "git add README.md"},
        "tool_name": "Bash",
        "tool_use_id": "hostile-bootstrap-tool",
    }
    result = subprocess.run(
        ["/bin/sh", "-c", command],
        cwd=nested,
        input=json.dumps(payload).encode(),
        capture_output=True,
        check=False,
        timeout=10,
    )

    assert result.returncode == 0
    decision = json.loads(result.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "enforcement failed closed" not in decision["permissionDecisionReason"]


def test_many_tool_pairs_keep_one_linear_generation_with_full_audit(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, _ = _repo_with_linked_worktree(tmp_path)
    holder, _ = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="scale-owner",
            owner="/root/scale-owner",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(holder)
    state = _common_dir(repo) / "codex-writer-lease"

    def current_audit_size() -> int:
        generation = (state / "current").read_text(encoding="ascii")
        return (state / generation / "audit.jsonl").stat().st_size

    audit_bytes_published = current_audit_size()
    started_at = time.monotonic()
    pair_count = 256
    for index in range(pair_count):
        tool_id = f"scale-tool-{index:02d}"
        for event in ("PreToolUse", "PostToolUse"):
            result = _raw_hook(
                repo,
                HookCall(
                    event=event,
                    session_id="scale-owner",
                    tool_name="Bash",
                    tool_use_id=tool_id,
                    tool_input={"command": "/usr/bin/true"},
                ),
            )
            assert result.returncode == 0
            assert result.stdout == ""
            audit_bytes_published += current_audit_size()
    elapsed = time.monotonic() - started_at

    generations = sorted(state.glob("gen-*"))
    assert len(generations) == 1
    assert list(state.glob(".reclaim-*")) == []
    audit_manifest = json.loads(
        (generations[0] / "audit.jsonl").read_text(encoding="utf-8")
    )
    event_count = 1 + pair_count * 2
    assert audit_manifest["schema"] == "dotfiles.writer-lease-audit-head.v1"
    assert audit_manifest["sealed_count"] + len(audit_manifest["tail"]) == event_count
    assert 1 <= len(audit_manifest["tail"]) <= 64
    chunks = sorted((state / "audit-chunks").glob("chunk-*.json"))
    expected_chunks = (event_count - 1) // 64
    assert len(chunks) == expected_chunks
    assert all(path.stat().st_size < 32 * 1024 for path in chunks)
    assert (generations[0] / "audit.jsonl").stat().st_size < 32 * 1024
    sealed_bytes_written = sum(path.stat().st_size for path in chunks)
    assert (
        audit_bytes_published + sealed_bytes_written
        < (event_count + expected_chunks) * 32 * 1024
    )
    state_bytes = sum(
        path.stat().st_size for path in state.rglob("*") if path.is_file()
    )
    assert state_bytes < 512 * 1024
    # The 512 real Python process launches vary by platform. This is only a
    # stuck-process ceiling; cumulative bytes above are the amplification gate.
    assert elapsed < 180


def test_sealed_audit_chunk_corruption_denies_without_state_mutation(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, _ = _repo_with_linked_worktree(tmp_path)
    holder, _ = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="chunk-owner",
            owner="/root/chunk-owner",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(holder)
    for index in range(32):
        tool_id = f"chunk-tool-{index:02d}"
        for event in ("PreToolUse", "PostToolUse"):
            result = _raw_hook(
                repo,
                HookCall(
                    event=event,
                    session_id="chunk-owner",
                    tool_name="Bash",
                    tool_use_id=tool_id,
                    tool_input={"command": "/usr/bin/true"},
                ),
            )
            assert result.returncode == 0
            assert result.stdout == ""

    state = _common_dir(repo) / "codex-writer-lease"
    chunks = list((state / "audit-chunks").glob("chunk-*.json"))
    assert len(chunks) == 1
    assert stat.S_IMODE((state / "audit-chunks").lstat().st_mode) == 0o700
    assert stat.S_IMODE(chunks[0].lstat().st_mode) == 0o600
    chunks[0].write_bytes(chunks[0].read_bytes() + b" ")
    before = _writer_state_bytes(state)

    denied = _raw_hook(
        repo,
        HookCall(
            event="PreToolUse",
            session_id="chunk-owner",
            tool_name="Bash",
            tool_use_id="corrupt-chunk",
            tool_input={"command": "git add README.md"},
        ),
    )

    assert denied.returncode == 0
    decision = json.loads(denied.stdout)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "digest" in decision["permissionDecisionReason"].lower()
    assert _writer_state_bytes(state) == before


def test_failed_claude_bash_drains_for_clean_release_and_crash_recovery(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    settings = json.loads(
        (project_root / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    failure_hooks = settings["hooks"]["PostToolUseFailure"]
    assert failure_hooks == settings["hooks"]["PostToolUse"]

    repo, linked = _repo_with_linked_worktree(tmp_path)
    first, first_receipt = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="failure-a",
            owner="/root/failure-a",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(first)

    def fail_and_drain(cwd: Path, session_id: str, tool_id: str) -> None:
        call = HookCall(
            event="PreToolUse",
            session_id=session_id,
            tool_name="Bash",
            tool_use_id=tool_id,
            tool_input={"command": "/bin/sh -c 'exit 23'"},
        )
        assert _raw_hook(cwd, call).stdout == ""
        failed = subprocess.run(
            ["/bin/sh", "-c", "exit 23"],
            cwd=cwd,
            check=False,
            timeout=5,
        )
        assert failed.returncode == 23
        failure = _raw_hook(
            cwd,
            HookCall(
                event="PostToolUseFailure",
                session_id=session_id,
                tool_name="Bash",
                tool_use_id=tool_id,
                tool_input=call.tool_input,
            ),
        )
        assert failure.returncode == 0
        assert failure.stdout == ""
        assert _status(cwd)["inflight"] == []

    fail_and_drain(repo, "failure-a", "failed-clean")
    _stop(first)
    second, second_receipt = _start_holder(
        linked,
        lease=LeaseArgs(
            task_id="failure-b",
            owner="/root/failure-b",
            handoff_sha256=_HANDOFF_B,
            transition="handoff",
            expected_prior_receipt_sha256=first_receipt["receipt_sha256"],
        ),
    )
    holders.append(second)
    fail_and_drain(linked, "failure-b", "failed-recovery")
    _stop(second, abrupt=True)
    recovered, _ = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="failure-c",
            owner="/root/failure-c",
            handoff_sha256=_HANDOFF_A,
            transition="recovery",
            expected_prior_receipt_sha256=second_receipt["receipt_sha256"],
        ),
    )
    holders.append(recovered)


def test_reclaim_is_anchored_when_state_path_becomes_external_symlink(
    tmp_path: Path,
) -> None:
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    old = state / "gen-old"
    old.mkdir(mode=0o700)
    for name in ("receipt.json", "audit.jsonl", "inflight.json"):
        (old / name).write_bytes(f"internal-{name}".encode())
        (old / name).chmod(0o600)

    external = tmp_path / "external"
    external.mkdir(mode=0o700)
    external_old = external / "gen-old"
    external_old.mkdir(mode=0o700)
    expected_external: dict[str, bytes] = {}
    for name in ("receipt.json", "audit.jsonl", "inflight.json"):
        payload = f"external-victim-{name}".encode()
        (external_old / name).write_bytes(payload)
        (external_old / name).chmod(0o600)
        expected_external[name] = payload

    state_fd = os.open(
        state,
        os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY | os.O_NOFOLLOW,
    )
    preserved = tmp_path / "state-preserved"
    state.rename(preserved)
    state.symlink_to(external, target_is_directory=True)
    try:
        debt = writer_lease.reclaim_generations_anchored(
            state_fd,
            ("gen-old",),
            keep="gen-current",
        )
    finally:
        os.close(state_fd)

    assert debt == ()
    assert not (preserved / "gen-old").exists()
    assert {
        name: (external_old / name).read_bytes() for name in expected_external
    } == expected_external


def test_malformed_reclaim_is_typed_debt_not_postcommit_denial(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, _ = _repo_with_linked_worktree(tmp_path)
    holder, _ = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="debt-owner",
            owner="/root/debt-owner",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(holder)
    state = _common_dir(repo) / "codex-writer-lease"
    malformed = state / ".reclaim-malformed"
    malformed.mkdir(mode=0o700)
    victim = malformed / "external-victim"
    victim.write_bytes(b"preserve-malformed-reclaim")
    victim.chmod(0o600)
    tool_id = "debt-tool"

    for event, expected_inflight in (
        ("PreToolUse", [tool_id]),
        ("PostToolUse", []),
    ):
        result = _raw_hook(
            repo,
            HookCall(
                event=event,
                session_id="debt-owner",
                tool_name="Bash",
                tool_use_id=tool_id,
                tool_input={"command": "/usr/bin/true"},
            ),
        )
        assert result.returncode == 0
        assert result.stdout == ""
        assert _status(repo)["inflight"] == expected_inflight
    status = _status(repo)
    assert status["cleanup_debt"] == [
        {"kind": "malformed_reclaim", "name": ".reclaim-malformed"}
    ]
    assert victim.read_bytes() == b"preserve-malformed-reclaim"


def test_completion_and_release_retry_overlapping_state_lock_many_times(
    tmp_path: Path, holders: list[subprocess.Popen[str]]
) -> None:
    repo, linked = _repo_with_linked_worktree(tmp_path)
    holder, receipt = _start_holder(
        repo,
        lease=LeaseArgs(
            task_id="retry-owner",
            owner="/root/retry-owner",
            handoff_sha256=_HANDOFF_A,
            transition="initial",
        ),
    )
    holders.append(holder)
    lock_path = _common_dir(repo) / "codex-writer-lease" / "state.lock"
    repetition_count = 24
    for index in range(repetition_count):
        tool_id = f"retry-tool-{index:02d}"
        assert (
            _raw_hook(
                repo,
                HookCall(
                    event="PreToolUse",
                    session_id="retry-owner",
                    tool_name="Bash",
                    tool_use_id=tool_id,
                    tool_input={"command": "/usr/bin/true"},
                ),
            ).stdout
            == ""
        )
        locker = _start_state_lock_holder(lock_path, 0.2)
        completion = _raw_hook(
            repo,
            HookCall(
                event=("PostToolUse", "PostToolUseFailure")[index % 2],
                session_id="retry-owner",
                tool_name="Bash",
                tool_use_id=tool_id,
                tool_input={"command": "/usr/bin/true"},
            ),
        )
        locker.communicate(timeout=5)
        assert completion.returncode == 0
        assert completion.stdout == ""
    assert _status(repo)["inflight"] == []

    release_locker = _start_state_lock_holder(lock_path, 0.2)
    holder.terminate()
    release_locker.communicate(timeout=5)
    holder.communicate(timeout=5)
    assert holder.returncode == 0
    successor, _ = _start_holder(
        linked,
        lease=LeaseArgs(
            task_id="retry-successor",
            owner="/root/retry-successor",
            handoff_sha256=_HANDOFF_B,
            transition="handoff",
            expected_prior_receipt_sha256=receipt["receipt_sha256"],
        ),
    )
    holders.append(successor)
