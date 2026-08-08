# Copyright (c) 2026 Raymond Manaloto
"""Deny repo-file modifications made while sitting on the default branch.

``do-not.md`` #9 already says "do NOT commit onto the default branch — branch
FIRST", and it is enforced at *commit* time by hk's ``no_commit_to_branch``.
That layer is blind to the failure this module closes: **work accumulating on
``main`` before any commit is attempted**.

Session 2026-08-03-f produced it. ``mise run land`` leaves you on ``main``; two
sub-agents then wrote their reports straight into the working tree there, and
nothing said a word — the tree simply grew untracked files on the default
branch. It only becomes visible when something tries to commit, which is far too
late if the intervening work was expensive. Ray's instruction: *"all work should
be on a branch that can be on a pr"*, enforced *"whenever anything is modified on
the repo"*.

So this fires on ``Edit`` / ``Write`` / ``NotebookEdit`` — the moment a file is
about to change, not the moment it is about to be committed.

**What it deliberately ALLOWS**, because a guard that blocks these gets switched
off (``mise-tasks-only.md``: "a redirect that misfires on legitimate diagnostics
erodes trust in the guard"):

- anything **outside the repo** — the auto-memory dir, the session scratchpad;
- anything **git-ignored** — ``.agent/``, ``graphify-out/``, ``mise.local.toml``;
  these are machine-local by construction and can never go on a PR;
- everything, when **not on the default branch** (the normal case).

Like its siblings it fails **OPEN**: any error resolving git state allows the
call. A crashed guard must not brick every edit.
"""

from __future__ import annotations

import enum
import subprocess
from pathlib import Path

# Branches treated as protected when the remote's default cannot be resolved.
# `main` first: this repo's default (`AGENTS.md` — "Main branch (you will
# usually use this for PRs): main").
_FALLBACK_DEFAULTS = ("main", "master")

_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})

# Worktree root, current branch and the remote's advertised default, in one
# invocation (#527). `--abbrev-ref` is sticky — it applies to every ref after
# it — so `HEAD` prints the branch and `refs/remotes/origin/HEAD` prints
# `origin/<default>`, the same shape `symbolic-ref --short` produced.
#
# `--quiet --verify` is what makes the fallback distinguishable rather than
# indistinguishable: it turns an unresolvable `origin/HEAD` into a quiet exit 1
# with clean stdout. Without it git exits 128 — the same code as "not a
# repository" — AND prints the unresolved ref back on stdout, where it looks
# just like a resolved answer to anything that reads the line.
_COMBINED_FACTS = [
    "rev-parse",
    "--show-toplevel",
    "--abbrev-ref",
    "HEAD",
    "--quiet",
    "--verify",
    "refs/remotes/origin/HEAD",
]
_COMBINED_FACT_COUNT = 3
_UNRESOLVED_REF_RC = 1

_REASON = (
    "You are on the default branch ({branch}) and about to modify {path}.\n"
    "All work belongs on a branch that can become a PR — branch FIRST, then edit.\n"
    "\n"
    "    git checkout -b <type>/<slug>\n"
    "\n"
    "Then re-run this edit and ship with `mise run ship`.\n"
    "This is `.claude/rules/do-not.md` #9. `mise run land` leaves you on the "
    "default branch, which is how work ends up here unnoticed.\n"
    "Writes outside the repo and to git-ignored paths (.agent/, the scratchpad) "
    "are NOT affected by this guard."
)


def _git_capture(args: list[str], cwd: Path) -> tuple[int, str] | None:
    """``(returncode, stripped stdout)``, or None when git could not be run.

    The None is NOT "git said no" — it is "git never answered" (missing binary,
    timeout). ``probes-need-a-control-arm.md`` rule 4: a process that never ran
    is not a negative result, and the two are told apart here so that
    :func:`_protected` can act on the return code.
    """
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        return None
    return proc.returncode, proc.stdout.strip()


def _git(args: list[str], cwd: Path) -> str | None:
    """Run a read-only git command, returning stripped stdout or None."""
    res = _git_capture(args, cwd)
    if res is None or res[0] != 0:
        return None
    return res[1]


def _probe_dir(start: Path) -> Path | None:
    """The nearest existing ancestor directory of ``start``, or None.

    ``start`` routinely does NOT exist yet — a Write creating a new file, often
    inside a directory that does not exist either. So walk up to the first
    ancestor that IS a directory before asking git; running git with a
    nonexistent cwd just errors, and the guard would then fail open on exactly
    the case it was built for (caught by
    ``test_denies_a_new_untracked_file_on_default_branch``).
    """
    probe = start if start.is_dir() else start.parent
    while not probe.is_dir():
        parent = probe.parent
        if parent == probe:  # reached the filesystem root
            return None
        probe = parent
    return probe


def default_branch(root: Path) -> tuple[str, ...]:
    """Protected branch names for ``root``.

    Prefers the remote's advertised default; falls back to the conventional
    pair so the guard still works in a clone with no ``origin/HEAD`` ref.
    """
    out = _git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], root)
    if out and "/" in out:
        return (out.split("/", 1)[1],)
    return _FALLBACK_DEFAULTS


def is_ignored(path: Path, root: Path) -> bool:
    """True when git ignores ``path`` (so it can never reach a PR)."""
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "-q", "--", str(path)],
            cwd=root,
            capture_output=True,
            timeout=5,
            check=False,
        )
    except OSError, subprocess.SubprocessError:
        return False
    return proc.returncode == 0


def _target(tool_input: dict[str, object]) -> Path | None:
    """The file a tool call is about to modify, absolute — or None."""
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return Path(raw).expanduser().resolve()
    except OSError, RuntimeError:
        return None


def _separate_facts(probe: Path) -> tuple[Path, str, tuple[str, ...]] | None:
    """``(root, branch, defaults)`` via the three pre-#527 invocations.

    The fallback for when the combined call could not deliver the advertised
    default. It re-asks from scratch rather than reusing anything the combined
    call printed: that output belongs to an invocation that did not return 0,
    and #527's rule is that such output is never parsed.
    """
    out = _git(["rev-parse", "--show-toplevel"], probe)
    if out is None:
        return None
    root = Path(out).resolve()
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], root)
    if branch is None:
        return None
    return root, branch, default_branch(root)


class CombinedResult(enum.Enum):
    """What the combined ``rev-parse`` established about the probe directory."""

    RESOLVED = "resolved"
    FALL_BACK = "fall_back"
    NO_REPOSITORY = "no_repository"


def classify(code: int, lines: list[str]) -> CombinedResult:
    """Which path the combined call's result puts us on.

    Split out as a pure function so every case is testable from a value — the
    seam is a parameter, not a patch (``tests/AGENTS.md``: mock at system
    boundaries only, and prefer injecting over constructing). That matters
    because one case below **cannot be produced by any real git**, so a
    subprocess-driven test could never reach it.

    ``--quiet --verify`` in the arg vector is what makes these separable at
    all. Without it a missing ``origin/HEAD`` is a *fatal* 128 — identical to
    "not a repository" — and git echoes the unresolved ref back on stdout,
    where it reads exactly like an answer.

    - **0 with every fact present** — resolved. The common path, and the point.
    - **0 with any other line count** — git ran fine in a repository but did
      not say what we asked. Unreachable today; it would take a change in
      git's output. It falls back rather than allowing, because "a repository
      is present" is established and the permissive reading is not.
    - **1** — a repository whose ``origin/HEAD`` does not resolve (no remote, a
      hand-added one, a stock CI checkout). Fall back to the separate
      invocations; the conventional pair then behaves exactly as before.
    - **anything else** — no usable repository here (outside any repo, an
      unborn HEAD, a bare repo). Allow, which is what the fallback concludes
      anyway: its first call runs in this same directory and fails the same
      way (armed by ``test_an_unborn_head_repo_is_allowed``). Short-circuiting
      keeps a write outside any repo — the scratchpad, the auto-memory dir,
      the hot path — at the single invocation it has always cost.
    """
    if code == 0:
        return (
            CombinedResult.RESOLVED
            if len(lines) == _COMBINED_FACT_COUNT
            else CombinedResult.FALL_BACK
        )
    if code == _UNRESOLVED_REF_RC:
        return CombinedResult.FALL_BACK
    return CombinedResult.NO_REPOSITORY


def _protected(target: Path) -> tuple[Path, str] | None:
    """``(root, branch)`` when ``target`` sits in a repo on its default branch.

    None means "not our business": outside any repo (the scratchpad, the
    auto-memory dir), or on a feature branch, or on a detached HEAD — which is
    not a branch anyone ships from.

    Worktree root, current branch and the remote's advertised default all come
    from ONE ``git`` invocation (#527). Process startup is the entire cost of a
    read-only git call, so asking for three facts costs about what asking for
    one did, and the common in-repo decision went 3 invocations to 1.
    :func:`_classify` owns which of those results means what.
    """
    probe = _probe_dir(target)
    if probe is None:
        return None
    combined = _git_capture(_COMBINED_FACTS, probe)
    if combined is None:  # git never ran — fail open
        return None
    code, out = combined
    lines = out.splitlines()
    outcome = classify(code, lines)
    if outcome is CombinedResult.RESOLVED:
        root, branch, advertised = Path(lines[0]).resolve(), lines[1], lines[2]
        defaults = (
            (advertised.split("/", 1)[1],) if "/" in advertised else _FALLBACK_DEFAULTS
        )
    elif outcome is CombinedResult.FALL_BACK:
        resolved = _separate_facts(probe)
        if resolved is None:
            return None
        root, branch, defaults = resolved
    else:
        return None
    if not target.is_relative_to(root) or branch == "HEAD" or branch not in defaults:
        return None
    return root, branch


def decide(tool_input: dict[str, object]) -> str | None:
    """Deny reason for an Edit/Write/NotebookEdit, or None to allow.

    Fails OPEN — every unresolvable step returns None.
    """
    target = _target(tool_input)
    if target is None:
        return None
    found = _protected(target)
    if found is None:
        return None
    root, branch = found
    if is_ignored(target, root):
        return None
    return _REASON.format(branch=branch, path=target.relative_to(root))


def handles(tool_name: str) -> bool:
    """True when ``tool_name`` is a file-modifying tool this guard covers."""
    return tool_name in _TOOLS
