"""Tests for the default-branch write guard.

Every test builds a **real git repo** rather than mocking git. The fixture is
the thing most likely to lie here (``probes-need-a-control-arm.md`` rule 8:
"could this setup have produced the other result?"), and a mocked
``rev-parse`` would prove only that the mock returns what it was told to.

Each behaviour is asserted in BOTH directions — a guard verified only on the
deny path is a check that can only pass.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from dotfiles_setup import branch_guard, hook_guard

_PROJECT_ROOT = Path(__file__).parent.parent.absolute()
_WRAPPER = _PROJECT_ROOT / "scripts" / "pretooluse-guard.sh"

# Git subprocesses ONE guard decision costs today, measured end-to-end through
# the real wired wrapper. These are the current, unimproved numbers on purpose:
# a gate only ever observed in its passing state is decoration
# (`probes-need-a-control-arm.md` rule 2), so it is pinned at what it really is
# before anything depends on it. #527 lowers them by collapsing the three
# `rev-parse`/`symbolic-ref` calls into one; that ticket updates these.
#
# Asserted as EQUALITY, not as a `<=` budget, and that is load-bearing: the
# dangerous regression here REMOVES a call rather than adding one. Measured —
# dropping the `origin/HEAD` lookup (the rejected "name-only short-circuit")
# moves 3 -> 2 and 4 -> 3, which a budget would wave through while the guard
# silently stopped consulting the real default branch.
_GIT_CALLS_OUTSIDE_REPO = 1  # rev-parse --show-toplevel, which fails
_GIT_CALLS_ON_FEATURE_BRANCH = 3  # + abbrev-ref HEAD, + symbolic-ref origin/HEAD
_GIT_CALLS_DENY_ON_DEFAULT = 4  # + check-ignore

_WRAPPER_TIMEOUT_S = 120


def _run(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True)


def _head_sha(cwd: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _init_repo(root: Path, branch: str) -> Path:
    """A real git repo on `branch`, with a .gitignore and one commit."""
    root.mkdir(parents=True)
    _run(["git", "init", "-b", branch], root)
    _run(["git", "config", "user.email", "t@example.com"], root)
    _run(["git", "config", "user.name", "T"], root)
    (root / ".gitignore").write_text(".agent/\nmise.local.toml\n")
    (root / "tracked.md").write_text("hello\n")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-m", "init"], root)
    (root / ".agent").mkdir()
    return root


def _advertise_default(root: Path, branch: str) -> None:
    """Give `root` a remote whose advertised default is `branch`.

    Without this, `symbolic-ref refs/remotes/origin/HEAD` fails and the guard
    falls back to the conventional pair — which is what EVERY test in this file
    did before #525, leaving the resolvable-default path uncovered.
    """
    _run(["git", "remote", "add", "origin", "https://example.invalid/x.git"], root)
    _run(["git", "update-ref", f"refs/remotes/origin/{branch}", _head_sha(root)], root)
    _run(
        [
            "git",
            "symbolic-ref",
            "refs/remotes/origin/HEAD",
            f"refs/remotes/origin/{branch}",
        ],
        root,
    )


def _guard_via_wrapper(target: Path, tmp_path: Path) -> tuple[str, int]:
    """Run the REAL wired guard on `target`; return (stdout, git call count).

    The count comes from git's own tracing facility pointed at a path — not a
    monkeypatched `subprocess.run` and not a shim on PATH. A built-in does the
    job (`use-tool-builtins.md`), and writing to a path rather than stderr is
    what lets it survive the guard's captured pipes.
    """
    trace = tmp_path / "git-trace.log"
    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": str(target), "content": "x"}}
    )
    proc = subprocess.run(
        ["bash", str(_WRAPPER)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=_PROJECT_ROOT,
        env={
            **os.environ,
            "GIT_TRACE": str(trace),
            "CLAUDE_PROJECT_DIR": str(_PROJECT_ROOT),
        },
        check=False,
        timeout=_WRAPPER_TIMEOUT_S,
    )
    assert proc.returncode == 0, proc.stderr
    text = trace.read_text() if trace.exists() else ""
    # Three failure modes, told apart — otherwise a broken INSTRUMENT reads as
    # a faster guard, and `probes-need-a-control-arm.md` rule 4 (a parse error
    # is not a "no") is exactly what this counter would violate. Every arm here
    # runs `rev-parse` at least once, so:
    #   empty file                     -> GIT_TRACE never ran
    #   has `rev-parse`, but no token  -> git's trace FORMAT changed
    #   token present                  -> the count means what it says
    # `built-in: git ` is git's human-readable format, not a documented
    # contract, which is why it is checked rather than trusted.
    assert text, f"GIT_TRACE recorded nothing at {trace} — the tracer never ran"
    assert "rev-parse" in text, f"GIT_TRACE wrote something odd: {text[:200]}"
    calls = text.count("built-in: git ")
    assert calls, "git's trace format changed — 'built-in: git ' gone, but git ran"
    return proc.stdout, calls


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real git repo on `main` with NO remote — the fallback path."""
    return _init_repo(tmp_path / "repo", "main")


@pytest.fixture
def remote_repo(tmp_path: Path) -> Path:
    """A real git repo on `main` whose remote advertises `main` as default.

    This is the shape of every real clone, and the path that resolves through
    `origin/HEAD` rather than the conventional-pair fallback.
    """
    root = _init_repo(tmp_path / "remote-repo", "main")
    _advertise_default(root, "main")
    return root


def test_denies_tracked_file_on_default_branch(repo: Path) -> None:
    """The headline case: real work, on main, must be refused."""
    reason = branch_guard.decide({"file_path": str(repo / "tracked.md")})
    assert reason is not None
    assert "default branch" in reason
    assert "git checkout -b" in reason
    assert "tracked.md" in reason


def test_denies_a_new_untracked_file_on_default_branch(repo: Path) -> None:
    """The exact 2026-08-03-f failure: agent reports written to main.

    The file does not exist yet and is not tracked — but it is not ignored
    either, so it is work that belongs on a branch.
    """
    reason = branch_guard.decide({"file_path": str(repo / "docs" / "report.md")})
    assert reason is not None


def test_allows_same_file_on_a_feature_branch(repo: Path) -> None:
    """CONTROL ARM for the deny above — only the branch differs."""
    _run(["git", "checkout", "-b", "feat/x"], repo)
    assert branch_guard.decide({"file_path": str(repo / "tracked.md")}) is None


def test_allows_gitignored_paths_on_default_branch(repo: Path) -> None:
    """`.agent/` and friends can never reach a PR, so they are never blocked."""
    assert (
        branch_guard.decide({"file_path": str(repo / ".agent" / "notepad.md")}) is None
    )
    assert branch_guard.decide({"file_path": str(repo / "mise.local.toml")}) is None


def test_allows_paths_outside_any_repo(tmp_path: Path) -> None:
    """The auto-memory dir and the session scratchpad must stay writable."""
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    assert branch_guard.decide({"file_path": str(outside / "MEMORY.md")}) is None


def test_allows_when_detached_head(repo: Path) -> None:
    """A detached HEAD is not a branch anyone ships from."""
    _run(["git", "checkout", _head_sha(repo)], repo)
    assert branch_guard.decide({"file_path": str(repo / "tracked.md")}) is None


def test_allows_master_as_well_as_main(tmp_path: Path) -> None:
    """The fallback pair covers a `master`-default clone."""
    root = tmp_path / "old"
    root.mkdir()
    _run(["git", "init", "-b", "master"], root)
    _run(["git", "config", "user.email", "t@example.com"], root)
    _run(["git", "config", "user.name", "T"], root)
    (root / "f.md").write_text("x\n")
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-m", "i"], root)
    assert branch_guard.decide({"file_path": str(root / "f.md")}) is not None


def test_allows_missing_or_malformed_input() -> None:
    """Fails OPEN — a payload without a path must never block."""
    assert branch_guard.decide({}) is None
    assert branch_guard.decide({"file_path": ""}) is None
    assert branch_guard.decide({"file_path": 42}) is None


def test_notebook_path_is_honoured(repo: Path) -> None:
    """NotebookEdit carries `notebook_path`, not `file_path`."""
    assert branch_guard.decide({"notebook_path": str(repo / "nb.ipynb")}) is not None


def test_handles_covers_exactly_the_file_modifying_tools() -> None:
    """Both arms: the covered set, and a tool that must NOT route here."""
    for name in ("Edit", "Write", "NotebookEdit"):
        assert branch_guard.handles(name)
    for name in ("Bash", "AskUserQuestion", "Read", "Grep"):
        assert not branch_guard.handles(name)


def test_dispatch_routes_edit_to_the_branch_guard(repo: Path) -> None:
    """The WIRING, not just the module — `decide_payload` must reach it.

    Without this, the guard could be perfect and never called; that is the
    #343 fail-open shape.
    """
    reason = hook_guard.decide_payload("Write", {"file_path": str(repo / "tracked.md")})
    assert reason is not None
    assert "default branch" in reason


def test_dispatch_still_treats_bash_as_a_command() -> None:
    """CONTROL ARM: adding the branch guard must not swallow Bash rules."""
    assert hook_guard.decide_payload("Bash", {"command": "git status"}) is None
    assert hook_guard.decide_payload("Bash", {"command": "git commit --no-verify -m x"})


# --- the resolvable-default path (#525) -------------------------------------
#
# Everything above this line runs on a repo with NO remote, so `origin/HEAD`
# never resolves and `default_branch()` returns the conventional pair. That is
# the FALLBACK. The path that runs on every real clone had no coverage at all.


def test_denies_on_the_advertised_default_branch(remote_repo: Path) -> None:
    """The headline case again, but resolved through `origin/HEAD`."""
    reason = branch_guard.decide({"file_path": str(remote_repo / "tracked.md")})
    assert reason is not None
    assert "default branch" in reason
    assert "git checkout -b" in reason
    assert "tracked.md" in reason


def test_allows_a_feature_branch_when_the_default_is_advertised(
    remote_repo: Path,
) -> None:
    """CONTROL ARM for the deny above — only the branch differs."""
    _run(["git", "checkout", "-b", "feat/x"], remote_repo)
    assert branch_guard.decide({"file_path": str(remote_repo / "tracked.md")}) is None


def test_advertised_default_wins_over_the_conventional_names(tmp_path: Path) -> None:
    """`origin/HEAD` decides, not the branch's name. BOTH arms.

    A repo whose real default is `develop` must be protected on `develop` and
    NOT protected on a branch merely *named* `main`. The second arm is the one
    a name-only short-circuit would break — it would allow writes on the real
    default while denying them on a feature branch, i.e. the guard silently
    inverted.
    """
    root = _init_repo(tmp_path / "dev-default", "develop")
    _advertise_default(root, "develop")
    assert branch_guard.decide({"file_path": str(root / "tracked.md")}) is not None

    _run(["git", "checkout", "-b", "main"], root)
    assert branch_guard.decide({"file_path": str(root / "tracked.md")}) is None


# --- what one decision COSTS (#525, lowered by #527) ------------------------


def test_a_write_outside_any_repo_costs_one_git_call(tmp_path: Path) -> None:
    """The early exit really is early: one failed root lookup, nothing more."""
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    stdout, calls = _guard_via_wrapper(outside / "MEMORY.md", tmp_path)
    assert stdout.strip() == ""
    assert calls == _GIT_CALLS_OUTSIDE_REPO


def test_an_allowed_write_on_a_feature_branch_costs_three_git_calls(
    remote_repo: Path, tmp_path: Path
) -> None:
    """Root, branch, remote default — three processes for one allow."""
    _run(["git", "checkout", "-b", "feat/x"], remote_repo)
    stdout, calls = _guard_via_wrapper(remote_repo / "tracked.md", tmp_path)
    assert stdout.strip() == ""
    assert calls == _GIT_CALLS_ON_FEATURE_BRANCH


def test_a_denied_write_costs_four_git_calls(remote_repo: Path, tmp_path: Path) -> None:
    """The deny path adds the ignore check. Asserted WITH the decision.

    Counting alone would pass just as happily if the guard had decided
    nothing at all, so the decision is pinned in the same assertion.
    """
    stdout, calls = _guard_via_wrapper(remote_repo / "tracked.md", tmp_path)
    assert '"permissionDecision": "deny"' in stdout
    assert calls == _GIT_CALLS_DENY_ON_DEFAULT
