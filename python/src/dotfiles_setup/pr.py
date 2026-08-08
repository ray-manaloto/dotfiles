# Copyright (c) 2026 Raymond Manaloto
"""Ship/land/automerge: the full PR loop as library code (zero-bash-logic).

``dotfiles-setup pr ship`` (wrapped by ``mise run ship``) takes the
current feature branch from "work is committed/staged" to "PR open with
checks watched"; ``dotfiles-setup pr land <n>`` (wrapped by
``mise run land``) takes a green PR through squash-merge, main-CI watch,
and post-merge LOCAL validation on this Mac. Together they encode the
verify-before-advancing rule as code instead of discipline.

``dotfiles-setup pr automerge <n>`` (wrapped by ``mise run automerge``) is
the third verb, and it exists because the first two left a hole (#369): a
**bot-opened** PR never runs ship, so nothing ever armed auto-merge on it,
land refuses an OPEN PR, and ``gh pr merge`` is guard-denied — the guard
denied the only working command and redirected to a task that could not do
the job. *A guard whose redirect target cannot perform the redirected action
is not enforcement, it is an outage* — the same shape fixed for
knowledge-base PRs in #349/#350, here along a different axis (PR provenance
rather than target repo). See :func:`automerge_main`.

Design notes (deep-research verified, 2026-07-07 —
``docs/research/runs/research-20260707-gha-shipland-enforcement/report.md``):

- **The CI wait is GitHub's, not ours — native auto-merge, no polling.**
  A base-image build can take hours, so a client-side watch (fixed timeout
  OR hand-rolled poll) is the wrong shape. ship enables **GitHub-native
  auto-merge** (``gh pr merge --auto --squash --match-head-commit <sha>``,
  :func:`enable_auto_merge`) and returns; GitHub merges the PR server-side
  the instant the branch-protection-required ``ci-gate`` check goes green.
  No client process stays alive, no ``gh run watch``/``--watch`` (both have
  exited/reported prematurely; see ``.claude/rules/gh-cli-watch.md``).
  ``--match-head-commit`` scopes the enable to the gated SHA and GitHub
  auto-disables auto-merge on new pushes, closing the verify-then-merge
  race. **land** is the post-merge step (confirm merged → main-CI concluded
  → ff main → local ``verify-local``), run after the PR has auto-merged.
- **Green is read from the ``--json`` buckets**, never a watch exit code:
  a PR/run is green iff every check bucket is ``pass``/``skipping`` and the
  API ``conclusion`` is ``success``.
- **Hard path-aware gate (no *operator* override)**: when the diff
  touches the devcontainer/image/validation surface
  (:data:`SURFACE_PATTERNS`) but NOT a base-image build input, ship
  requires a full local ``mise run sync -- --full`` (verify-local chain)
  BEFORE the PR opens, and land re-runs it after the merge. Zero-skip:
  there is no *flag* to bypass this.
- **Base-image input changes DEFER container validation to CI** (not a
  bypass — an automatic, principled deferral): when the diff changes a
  base/p2996 build input (:data:`BASE_INPUT_PATTERNS` — mise-system/
  runtime toml+lock, shared.toml, hk-common/image.pkl, Dockerfile,
  docker-bake.hcl), the new base is built ONLY by the branch's own PR
  CI. The local ``:dev`` base is built from the merge-base and cannot be
  made current for the branch (base builds are CI-only; a chezmoi/tool
  bump can even make the stale base's ``onCreate`` fail outright). Per
  ``verify-before-advancing.md``, ship then runs lint/pytest/verify
  locally, skips the impossible local container convergence, and still
  gates on CI's base-build + smoke via the watched PR checks
  (``watch_pr_checks``). CI is the validator — not a zero-skip
  violation. This closes the ship deadlock for base-tool bumps (a
  chezmoi/gcc/mise-system bump otherwise cannot open its own PR).
- **Main-CI expectation is path-aware** (:data:`CI_PUSH_PATHS`): ci.yml's
  push trigger is path-filtered, so a merge whose diff matches no push
  path legitimately produces NO main run — land passes that outcome
  instead of false-failing (#178).
- Gate order is cheap-first: lint → pytest → verify → conditional
  (pin-actions / lint-docs) → full sync last.

Everything long-running streams to the terminal (never wait blind);
quick probes are captured + timeout-bounded.
"""

from __future__ import annotations

import dataclasses
import fnmatch
import json
import subprocess
import sys
import time
from typing import TYPE_CHECKING

from dotfiles_setup.sync import SyncOptions, sync_main

if TYPE_CHECKING:
    from pathlib import Path

_PROBE_TIMEOUT_S = 120.0

# The devcontainer/image/validation surface: a diff touching any of these
# makes full local verification (sync --full == verify-local chain)
# mandatory in ship AND land. Glob-style, matched against repo-relative
# paths with fnmatch.
SURFACE_PATTERNS: tuple[str, ...] = (
    ".devcontainer/*",
    ".devcontainer/**/*",
    "docker-bake.hcl",
    "scripts/devcontainer-smoke.sh",
    "scripts/workspace-hash.sh",
    "python/src/dotfiles_setup/container.py",
    "python/src/dotfiles_setup/sync.py",
    "python/src/dotfiles_setup/image.py",
    "python/src/dotfiles_setup/docker.py",
    "python/src/dotfiles_setup/pr.py",
    "python/verification/*",
    # Review finding [5]: image COPY inputs + the task definitions the
    # validation chain executes are surface too — changing them alters
    # what gets built or how it gets verified.
    "hk-common.pkl",
    "hk-image.pkl",
    ".config/mise/conf.d/*",
    "mise.toml",
)

# The subset of the surface that feeds the CI-built base/p2996 image — the
# base-hash + p2996-hash inputs. A branch changing any of these needs a NEW
# base image, built ONLY by that PR's own CI; the local ``:dev`` base is built
# from the merge-base and cannot be made current for the branch (base builds
# are CI-only — never local, per do-not.md). So the local container gate cannot
# validate such a branch — worse, a base-tool bump (chezmoi/gcc) can make the
# stale base's ``onCreate`` fail outright. For these, ship DEFERS container
# validation to CI (see the module docstring): still runs lint/pytest/verify
# locally, and still gates on CI's base-build + smoke via the watched PR checks.
# Keep in lockstep with the base-hash/p2996-hash input set (main.py base-hash,
# p2996_hash.py) — tests/test_pr.py pins the expected behavior.
BASE_INPUT_PATTERNS: tuple[str, ...] = (
    ".devcontainer/Dockerfile",
    ".devcontainer/mise-system.toml",
    ".devcontainer/mise-system.lock",
    ".devcontainer/mise-runtime.toml",
    ".devcontainer/mise-runtime.lock",
    ".config/mise/conf.d/shared.toml",
    "hk-common.pkl",
    "hk-image.pkl",
    "docker-bake.hcl",
)

# ci.yml's on.push.paths, mirrored: a merge to main whose diff matches NONE
# of these produces NO main ci.yml run — that is the expected outcome, not a
# failure (found landing #178: a mise.toml-only merge false-failed land).
# tests/test_pr.py asserts this constant stays in lockstep with ci.yml.
CI_PUSH_PATHS: tuple[str, ...] = (
    ".devcontainer/*",
    ".devcontainer/**/*",
    "docker-bake.hcl",
    "home/*",
    "home/**/*",
    "python/*",
    "python/**/*",
    ".github/workflows/ci.yml",
    "hk.pkl",
    "hk-image.pkl",
    "hk-common.pkl",
    "renovate.json",
    ".config/mise/conf.d/shared.toml",
)

# The inputs to the `verify-apt-pins` probe (apt_pins.MISE_SYSTEM_TOML +
# apt_pins.DOCKERFILE). BOTH are probe inputs, not just the pin declarations:
# the Dockerfile carries `ARG BASE_IMAGE` and the LLVM signing key — what the
# pins get resolved AGAINST — so a base bump can invalidate every pin without
# touching a pin line.
#
# Both are also BASE_INPUT_PATTERNS, i.e. exactly the changes for which ship
# DEFERS container validation to CI. That is why this gate earns its place:
# it is the ~60s local probe standing in for the deferred container gate, and
# an unresolvable pin otherwise surfaces only after a ~37min CI base build
# (.claude/rules/local-devcontainer-first.md).
_APT_PIN_PATTERNS = (
    ".devcontainer/mise-system.toml",
    ".devcontainer/Dockerfile",
)

# Conditional gates from verify-before-advancing's check matrix.
_GHA_PATTERNS = (".github/*", ".github/**/*")
_DOCS_PATTERNS = (
    "AGENTS.md",
    "*/AGENTS.md",
    "**/AGENTS.md",
    "CLAUDE.md",
    "*/CLAUDE.md",
    "**/CLAUDE.md",
    ".claude/**/*.md",
)

_GREEN_BUCKETS = frozenset({"pass", "skipping"})

# The GitHub Apps whose PRs `automerge` will arm (#369, scope locked by Ray
# 2026-07-27). Re-derived, not assumed: `gh pr list --state all --limit 60
# --json number,author` over this repo returns exactly two non-human logins,
# and they own all three stuck PRs (#138, #236, #386).
#
# A login ALLOWLIST, deliberately, not `author.is_bot`: is_bot would admit any
# app that ever opens a PR here, whereas the point of the ship/automerge split
# is that a NAMED set of bots gets the verb that skips the local gates. A user
# login cannot contain `/`, so an `app/…` login is not spoofable by a human
# account. Control arm for the discriminator: `sortakool` -> is_bot=false and
# is absent from this set, so a human PR takes the refusal path.
BOT_PR_AUTHORS: frozenset[str] = frozenset(
    {
        "app/renovate",
        "app/dotfiles-refresh-bot-org",
    }
)


@dataclasses.dataclass(frozen=True)
class Gate:
    """One named validation command in the ship gate matrix."""

    name: str
    cmd: tuple[str, ...]


def _run(
    cmd: list[str],
    *,
    timeout: float | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    # Degrade a hung probe to a failed probe (never an uncaught crash).
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=timeout, cwd=cwd
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=cmd, returncode=124, stdout="", stderr="probe timed out"
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            args=cmd, returncode=127, stdout="", stderr=str(exc)
        )


def _stream(cmd: list[str], *, cwd: Path | None = None) -> int:
    """Run a long operation streaming to the terminal (never wait blind)."""
    return subprocess.run(cmd, check=False, cwd=cwd).returncode


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def touches_surface(paths: list[str]) -> bool:
    """True when the diff touches the devcontainer/image/validation surface."""
    return any(_matches_any(p, SURFACE_PATTERNS) for p in paths)


def changes_base_image_inputs(paths: list[str]) -> bool:
    """True when the diff changes a base/p2996 build input.

    The new base image is built by the branch's own PR CI; the local ``:dev``
    base is built from the merge-base and cannot be made current for the
    branch, so ship defers local container validation to CI for these changes
    (:data:`BASE_INPUT_PATTERNS`, module docstring, verify-before-advancing.md).
    """
    return any(_matches_any(p, BASE_INPUT_PATTERNS) for p in paths)


def changes_apt_pin_inputs(paths: list[str]) -> bool:
    """True when the diff changes an input to the apt-pin resolvability probe.

    Either the `[bootstrap.packages]` declarations themselves or the base
    image / signing key they resolve against (:data:`_APT_PIN_PATTERNS`).
    """
    return any(_matches_any(p, _APT_PIN_PATTERNS) for p in paths)


def expects_main_run(paths: list[str]) -> bool:
    """True when merging these paths triggers a main ci.yml run.

    Mirrors ci.yml's ``on.push.paths`` (:data:`CI_PUSH_PATHS`). A merge
    matching none produces no main run, so land treats that absence as
    success rather than a false failure (#178).
    """
    return any(_matches_any(p, CI_PUSH_PATHS) for p in paths)


def changed_paths_vs_main(workspace: Path) -> list[str]:
    """Repo-relative paths changed on this branch vs origin/main (incl. staged)."""
    merged: set[str] = set()
    for args in (
        ["git", "-C", str(workspace), "diff", "--name-only", "origin/main...HEAD"],
        ["git", "-C", str(workspace), "diff", "--name-only", "--cached"],
    ):
        merged.update(line for line in _run(args).stdout.splitlines() if line)
    return sorted(merged)


def gate_matrix(paths: list[str]) -> list[Gate]:
    """The ordered, path-aware gate list for ship — cheap gates first.

    Always: lint, pytest, verify contracts, hook-selfcheck (the wired
    host-side hooks, end-to-end). Conditional per
    verify-before-advancing: pin-actions on .github changes, lint-docs on
    agent-doc changes, verify-apt-pins on apt-pin inputs
    (:func:`changes_apt_pin_inputs`). The full-sync hard gate runs LAST (most expensive)
    when the devcontainer/image/validation surface changed — EXCEPT when a
    base-image build input changed (:func:`changes_base_image_inputs`), for
    which the local base cannot validate the branch and container validation
    defers to CI (module docstring). No *operator* override either way.
    """
    gates = [
        Gate("lint", ("mise", "run", "lint")),
        Gate(
            "pytest",
            ("uv", "run", "--project", "python", "pytest", "tests/", "-x", "-q"),
        ),
        Gate(
            "verify-contracts",
            ("uv", "run", "--project", "python", "dotfiles-setup", "verify", "run"),
        ),
        # Host-side hook validation: drives the WIRED PreToolUse guard + the
        # advisory UserPromptSubmit/PostToolUse hooks end-to-end (settings.json
        # wiring, the real wrappers, `bash -n`), so a hook regression is caught
        # like any other gate. Always-run and cheap — see hook_selfcheck.py.
        Gate(
            "hook-selfcheck",
            ("uv", "run", "--project", "python", "dotfiles-setup", "hook", "selfcheck"),
        ),
        # Tiers 1+2 (#354 PR 2/PR 3). Always-run and free: the offline set spends
        # no API calls, and it catches the classes tier 0 structurally cannot — a
        # declaration that is present and does not resolve (tier 1), and a guard
        # that is declared and wired and still decides wrongly (tier 2). Its live
        # half stays on demand (`mise run eval -- --live`).
        #
        # The `hook-selfcheck` gate above STAYS and is not superseded: it answers
        # "is the guard WIRED?", the precondition for tier 2's "does the wired
        # guard DECIDE correctly?". Ordered first so a wiring break fails fast
        # with a clear message instead of a wall of fixture mismatches.
        Gate("eval", ("mise", "run", "eval")),
    ]
    if any(_matches_any(p, _GHA_PATTERNS) for p in paths):
        gates.append(Gate("pin-actions", ("mise", "run", "pin-actions")))
    if any(_matches_any(p, _DOCS_PATTERNS) for p in paths):
        gates.append(Gate("lint-docs", ("mise", "run", "lint-docs")))
    # ~60s in a throwaway base container, and deliberately NOT conditioned on
    # changes_base_image_inputs: these paths ARE base inputs, so the container
    # gate below is skipped for them and this probe is the only local check
    # that a pin still resolves. Local-first (#288/#299) — it exists precisely
    # to fail in 60s instead of after a ~37min CI base build.
    if changes_apt_pin_inputs(paths):
        gates.append(Gate("verify-apt-pins", ("mise", "run", "verify-apt-pins")))
    if touches_surface(paths) and not changes_base_image_inputs(paths):
        gates.append(Gate("sync-full", ("mise", "run", "sync", "--", "--full")))
    return gates


def run_gates(workspace: Path, gates: list[Gate]) -> bool:
    """Run each gate streamed; stop at the first failure (it IS the task)."""
    for gate in gates:
        sys.stdout.write(f"==> gate: {gate.name}\n")
        rc = _stream(list(gate.cmd), cwd=workspace)
        marker = "PASS" if rc == 0 else "FAIL"
        sys.stdout.write(f"{marker}  gate {gate.name} rc={rc}\n")
        if rc != 0:
            return False
    return True


def pr_checks_green(pr_number: int) -> tuple[bool, str]:
    """API-verified: every check bucket is pass/skipping (none fail/pending)."""
    res = _run(
        ["gh", "pr", "checks", str(pr_number), "--json", "name,bucket"],
        timeout=_PROBE_TIMEOUT_S,
    )
    if res.returncode != 0:
        return False, f"gh pr checks --json failed: {res.stderr.strip()}"
    checks = json.loads(res.stdout)
    bad = [c for c in checks if c["bucket"] not in _GREEN_BUCKETS]
    if bad:
        detail = ", ".join(f"{c['name']}={c['bucket']}" for c in bad)
        return False, detail
    return True, f"{len(checks)} checks pass/skipping"


def _await_checks_registered(pr_number: int, *, attempts: int = 40) -> bool:
    """Poll until GitHub reports at least one check for the PR.

    Checks register asynchronously after push/PR-create; ``gh pr checks``
    exits nonzero with "no checks reported" in that window (probe-observed
    on PR #173's first ship). That state is *pending*, not failure.
    """
    for _ in range(attempts):
        res = _run(
            ["gh", "pr", "checks", str(pr_number), "--json", "name,bucket"],
            timeout=_PROBE_TIMEOUT_S,
        )
        if res.returncode == 0 and json.loads(res.stdout or "[]"):
            return True
        time.sleep(15)
    sys.stdout.write(
        f"FAIL  pr-checks: no checks registered on PR #{pr_number} within "
        f"{attempts * 15}s\n"
    )
    return False


# Absolute backstop for the terminal-state poll. A cold base+p2996 build is
# ~2.5h (memory: feedback_ci_build_duration_baseline); 4h leaves margin. This
# is a genuinely-stuck guard, NOT a "typical build takes this long" estimate —
# the poll returns as soon as CI reaches terminal, however long that is.
# GitHub's March-2026 auto-merge regression can 422 the *enable* call until
# requirements are near-met (community #190610). A short bounded retry
# (seconds-to-minutes, NOT an hours-long poll) rides it out; if GitHub only
# accepts once ci-gate is green, auto-merge degrades to an immediate merge —
# still correct, still poll-free. Verify on the first real auto-merge PR.
_AUTOMERGE_ENABLE_ATTEMPTS = 5
_AUTOMERGE_ENABLE_BACKOFF_S = 20


def enable_auto_merge(
    workspace: Path, pr_number: int, head: str, *, verb: str = "ship"
) -> bool:
    """Enable GitHub-native auto-merge (squash), pinned to the verified head.

    GitHub then merges the PR server-side the instant the required ``ci-gate``
    check goes green — no client poll, no timeout, tolerant of multi-hour base
    builds. ``--match-head-commit`` scopes the enable to the SHA ship gated (and
    GitHub auto-disables auto-merge if new commits are pushed), closing the
    verify-then-merge race. Runs as a subprocess, so it is not a hand-rolled
    watch — GitHub owns the wait.

    ``verb`` only labels the failure line: both ``ship`` and ``automerge``
    (#369) arm through this one function, so the arming semantics cannot drift
    apart between the two entrypoints.
    """
    cmd = [
        "gh",
        "pr",
        "merge",
        str(pr_number),
        "--auto",
        "--squash",
        "--delete-branch",
        "--match-head-commit",
        head,
    ]
    res = _run(cmd, timeout=_PROBE_TIMEOUT_S, cwd=workspace)
    for attempt in range(1, _AUTOMERGE_ENABLE_ATTEMPTS):
        if res.returncode == 0:
            return True
        sys.stdout.write(
            f"==> auto-merge enable attempt {attempt} failed "
            f"({res.stderr.strip()[:80]}); retrying (transient 422)…\n"
        )
        time.sleep(_AUTOMERGE_ENABLE_BACKOFF_S)
        res = _run(cmd, timeout=_PROBE_TIMEOUT_S, cwd=workspace)
    if res.returncode == 0:
        return True
    sys.stdout.write(
        f"FAIL  {verb}: could not enable auto-merge on PR #{pr_number}: "
        f"{res.stderr.strip()}\n"
    )
    return False


def _current_branch(workspace: Path) -> str:
    return _run(
        ["git", "-C", str(workspace), "rev-parse", "--abbrev-ref", "HEAD"]
    ).stdout.strip()


def _working_tree_clean(workspace: Path) -> bool:
    return not _run(
        ["git", "-C", str(workspace), "status", "--porcelain"]
    ).stdout.strip()


def _ship_preflight(workspace: Path) -> tuple[str, list[str]] | None:
    """Branch/tree/diff preconditions for ship; None (after printing) on fail."""
    branch = _current_branch(workspace)
    if branch in ("main", "HEAD"):
        sys.stdout.write("FAIL  ship: refusing to ship from main/detached HEAD\n")
        return None
    if not _working_tree_clean(workspace):
        sys.stdout.write(
            "FAIL  ship: working tree not clean — commit (or stash) first so "
            "the gates validate exactly what ships\n"
        )
        return None
    paths = changed_paths_vs_main(workspace)
    if not paths:
        sys.stdout.write("FAIL  ship: no changes vs origin/main\n")
        return None
    return branch, paths


def _open_or_update_pr(workspace: Path, title: str | None) -> int | None:
    """Open (or reuse) the branch PR; returns its number or None on failure."""
    # Review finding [8]: branch-implicit gh calls must run in the
    # workspace repo, not the caller's cwd.
    existing = _run(
        ["gh", "pr", "view", "--json", "number,state"],
        timeout=_PROBE_TIMEOUT_S,
        cwd=workspace,
    )
    if existing.returncode == 0 and json.loads(existing.stdout).get("state") == "OPEN":
        number = int(json.loads(existing.stdout)["number"])
        sys.stdout.write(f"==> PR #{number} already open — pushed update\n")
        return number
    create = ["gh", "pr", "create", "--fill"]
    if title:
        create += ["--title", title]
    create_rc = _stream(create, cwd=workspace)
    if create_rc != 0:
        # Report the status we SAW, never a prose summary of it (#358, design
        # principle 8). The knowledge-base twin of this line printed a bare
        # "PR create failed" through GitHub's 2026-07-24 PR outage, so a hard
        # server error was indistinguishable from flakiness and got retried
        # three times before anyone looked at the actual response.
        sys.stdout.write(f"FAIL  ship: gh pr create rc={create_rc}\n")
        return None
    view = _run(
        ["gh", "pr", "view", "--json", "number"],
        timeout=_PROBE_TIMEOUT_S,
        cwd=workspace,
    )
    if view.returncode != 0 or not view.stdout.strip():
        # Review finding [10]: never JSON-parse an unchecked gh result.
        sys.stdout.write(
            "FAIL  ship: created PR but could not resolve its number "
            f"(gh pr view rc={view.returncode})\n"
        )
        return None
    return int(json.loads(view.stdout)["number"])


def ship_main(workspace: Path, *, title: str | None = None) -> int:
    """Gates → push → open PR → enable native auto-merge → return.

    Requires committed work on a branch. Commit creation stays with the
    operator/agent (messages need human judgment); ship refuses a dirty tree
    so nothing half-staged leaks past the gates (`clean-git-state` rule).
    The CI wait is GitHub's, not ours: ship enables auto-merge and returns;
    GitHub merges when the required ``ci-gate`` check goes green (no client
    poll, no timeout — a base build can take hours). land is the post-merge
    Mac-validation step. See :func:`enable_auto_merge`.
    """
    preflight = _ship_preflight(workspace)
    if preflight is None:
        return 1
    branch, paths = preflight
    base_change = changes_base_image_inputs(paths)
    if base_change:
        tag = "  [base-image inputs changed → container validation DEFERRED to CI]"
    elif touches_surface(paths):
        tag = "  [devcontainer surface → full-sync gate]"
    else:
        tag = ""
    sys.stdout.write(f"==> ship {branch}: {len(paths)} changed paths{tag}\n")
    if base_change:
        sys.stdout.write(
            "==> NOTE: a base-image build input changed; the new base is built "
            "by this PR's CI, so the local :dev base cannot validate it (base "
            "builds are CI-only). Running lint/pytest/verify locally; CI's "
            "base-build + smoke gate the PR (watched below). "
            "See verify-before-advancing.md.\n"
        )
    if not run_gates(workspace, gate_matrix(paths)):
        return 1

    push_rc = _stream(["git", "push", "-u", "origin", branch], cwd=workspace)
    if push_rc != 0:
        sys.stdout.write(f"FAIL  ship: git push rc={push_rc}\n")
        return 1

    number = _open_or_update_pr(workspace, title)
    if number is None:
        return 1
    head = _run(
        ["git", "-C", str(workspace), "rev-parse", "HEAD"], timeout=_PROBE_TIMEOUT_S
    ).stdout.strip()
    # Confirm CI kicked off (auto-merge waits for ci-gate regardless, but if CI
    # never triggers the PR would never merge — surface that early).
    if _await_checks_registered(number):
        sys.stdout.write(f"==> CI started on PR #{number}\n")
    else:
        sys.stdout.write(
            f"WARN  ship: no CI checks registered yet on PR #{number} — auto-merge "
            "waits for ci-gate; if CI never triggers, the PR won't merge\n"
        )
    # Native auto-merge is the wait: GitHub merges when ci-gate is green. No
    # client poll, no timeout — the wrong-shape fixed-timeout watch is gone.
    if not enable_auto_merge(workspace, number, head):
        return 1
    sys.stdout.write(
        f"\nship: OK — PR #{number} open, local gates green, AUTO-MERGE enabled.\n"
        f"GitHub merges it the instant ci-gate goes green (no poll; a base build "
        f"can take hours). After it merges, run `mise run land -- {number}` for "
        "the post-merge Mac validation (or `mise run sync` on next bring-up).\n"
    )
    return 0


def _automerge_refusal(pr_number: int, info: dict[str, object]) -> str | None:
    """The reason `automerge` will not arm this PR, or None when it will.

    Split out from :func:`automerge_main` so every refusal is testable without
    a subprocess, and so the precondition ORDER is visible in one place. Order
    is by what the operator most likely got wrong: wrong state, then wrong
    provenance (the split this verb exists to encode), then draft, then base.
    """
    state = info.get("state")
    if state != "OPEN":
        follow_up = (
            f" It is already merged — run `mise run land -- {pr_number}` for the "
            "post-merge Mac validation."
            if state == "MERGED"
            else ""
        )
        return (
            f"FAIL  automerge: PR #{pr_number} is {state}, not OPEN — there is "
            f"nothing to arm.{follow_up}"
        )
    author = info.get("author")
    login = author.get("login", "") if isinstance(author, dict) else ""
    if login not in BOT_PR_AUTHORS:
        return (
            f"FAIL  automerge: PR #{pr_number} was opened by {login!r}, which is "
            f"not one of the bots this verb serves "
            f"({', '.join(sorted(BOT_PR_AUTHORS))}). Use `mise run ship` from the "
            "branch instead — ship gates the tree BEFORE arming auto-merge and "
            "automerge does not gate anything, so one verb per provenance means "
            "no judgement call at the call site."
        )
    if info.get("isDraft"):
        return (
            f"FAIL  automerge: PR #{pr_number} is a draft — GitHub refuses to "
            "enable auto-merge on a draft. Mark it ready for review first."
        )
    base = info.get("baseRefName")
    if base != "main":
        return (
            f"FAIL  automerge: PR #{pr_number} targets {base!r}, not main. The "
            "post-merge validation this verb points at (`mise run land`) only "
            "validates main-based PRs."
        )
    if not info.get("headRefOid"):
        return (
            f"FAIL  automerge: PR #{pr_number} has no headRefOid — cannot pin the "
            "arming to a SHA."
        )
    return None


def automerge_main(workspace: Path, pr_number: int) -> int:
    """Arm GitHub-native auto-merge on a BOT-opened PR, then exit (#369).

    The missing verb. ship arms auto-merge for work you shipped; a bot-opened
    PR (Renovate, the refresh bot) never runs ship, so nothing armed it, and
    land — post-merge validation — refuses an OPEN PR. This closes that hole
    WITHOUT re-entangling land with merging (the ship/land split deliberately
    undid that).

    Four properties, all decisions rather than preferences (Ray, 2026-07-27,
    recorded verbatim on #369):

    - **Bot-authored PRs only** (:data:`BOT_PR_AUTHORS`). A human PR is refused
      and pointed at ship, because ship gates the tree before arming and this
      verb does not. One verb per provenance = no judgement call at the call
      site.
    - **Arm and exit** — it prints the ``mise run land`` follow-up rather than
      waiting. Waiting would turn a seconds-long local verb into a 20-40min
      Mac-side op that gets reaped when the turn goes idle
      (``feedback_long_mac_ops_keep_turn_engaged``).
    - **Arm even when the branch is behind main.** Renovate branches sit behind
      (#369 records #342's base as ``66579dc``), but ``ci-gate`` and the other
      required checks run against the MERGE RESULT and auto-merge waits for
      them. A local freshness gate would be a second, weaker opinion about a
      question GitHub has already answered — and would push against #257
      (rebase churn).
    - **Per-PR, never a sweep.** Nothing is armed unless it is named, which is
      what keeps a HELD PR (#386, pending the corpus re-baseline) held.

    It arms through :func:`enable_auto_merge`, the same call ship uses, pinned
    with ``--match-head-commit`` to the head SHA read here. If the bot
    force-pushes a rebase afterwards, the arming no longer matches its head —
    re-run the verb.
    """
    view = _run(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "state,isDraft,baseRefName,headRefOid,author",
        ],
        timeout=_PROBE_TIMEOUT_S,
        cwd=workspace,
    )
    if view.returncode != 0 or not view.stdout.strip():
        # Report the status we SAW, never a prose summary of it (#358).
        sys.stdout.write(
            f"FAIL  automerge: gh pr view rc={view.returncode}: {view.stderr.strip()}\n"
        )
        return 1
    info = json.loads(view.stdout)
    refusal = _automerge_refusal(pr_number, info)
    if refusal is not None:
        sys.stdout.write(f"{refusal}\n")
        return 1
    head = str(info["headRefOid"])
    if not enable_auto_merge(workspace, pr_number, head, verb="automerge"):
        return 1
    sys.stdout.write(
        f"\nautomerge: OK — PR #{pr_number} armed (squash, pinned to "
        f"{head[:7]}).\nGitHub merges it the instant ci-gate goes green; the "
        "required checks run against the merge result, so a branch behind main "
        "is fine.\nNothing was gated locally — that is CI's job here. After it "
        f"merges, run `mise run land -- {pr_number}` for the post-merge Mac "
        "validation.\n"
    )
    return 0


def _merge_commit_oid(pr_number: int) -> str | None:
    res = _run(
        ["gh", "pr", "view", str(pr_number), "--json", "mergeCommit"],
        timeout=_PROBE_TIMEOUT_S,
    )
    if res.returncode != 0:
        return None
    commit = json.loads(res.stdout).get("mergeCommit") or {}
    return commit.get("oid")


def _main_run_conclusion(merge_oid: str, *, expect_run: bool = True) -> bool:
    """Watch the main ci.yml run for the merge commit; verify via the API.

    ``expect_run=False`` (merge diff matches no ci.yml push path): a short
    grace poll still runs — if a run DOES appear (constant drifted vs
    ci.yml) it is watched normally — but no run within the grace window is
    the expected outcome and passes.
    """
    run_id = ""
    sys.stdout.write("==> waiting for main ci.yml run on the merge commit\n")
    find = [
        "gh",
        "run",
        "list",
        "--branch",
        "main",
        "--workflow",
        "ci.yml",
        "--commit",
        merge_oid,
        "--limit",
        "1",
        "--json",
        "databaseId",
        "--jq",
        ".[0].databaseId // empty",
    ]
    # ~10 min at 15s when a run is expected (it registers within seconds);
    # a short grace poll otherwise, in case CI_PUSH_PATHS drifted vs ci.yml.
    attempts = 40 if expect_run else 4
    for _ in range(attempts):
        run_id = _run(find, timeout=_PROBE_TIMEOUT_S).stdout.strip()
        if run_id:
            break
        time.sleep(15)
    if not run_id:
        if not expect_run:
            sys.stdout.write(
                "PASS  main run: none expected — the merge diff matches no "
                "ci.yml push path (PR-level CI validated the merge)\n"
            )
            return True
        sys.stdout.write("FAIL  land: no main ci.yml run appeared for the merge\n")
        return False
    _stream(["gh", "run", "watch", run_id, "--exit-status"])
    conclusion = _run(
        ["gh", "run", "view", run_id, "--json", "conclusion", "--jq", ".conclusion"],
        timeout=_PROBE_TIMEOUT_S,
    ).stdout.strip()
    sys.stdout.write(
        f"{'PASS' if conclusion == 'success' else 'FAIL'}  main run {run_id} "
        f"conclusion={conclusion}\n"
    )
    return conclusion == "success"


def _pr_changed_paths(pr_number: int) -> list[str]:
    """ALL changed paths of the PR, paginated.

    Review finding [9]: ``gh pr view --json files`` caps at 100 entries,
    which could silently drop the surface-triggering file on a large PR.
    """
    res = _run(
        [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/files",
            "--paginate",
            "--jq",
            ".[].filename",
        ],
        timeout=_PROBE_TIMEOUT_S,
    )
    return [line for line in res.stdout.splitlines() if line]


def _land_post_merge(pr_number: int) -> bool | None:
    """Confirm the PR auto-merged + the main ci.yml run concluded; surface flag.

    ship enables native auto-merge, so by the time land runs GitHub should have
    already squash-merged the PR (when ci-gate went green). land does NOT merge
    — it validates the merged result. Returns the surface flag (which local
    validation tier to run), or None on fail. A still-OPEN PR means auto-merge
    is pending ci-gate; land says so and exits (re-run once it has merged).
    """
    view = _run(
        ["gh", "pr", "view", str(pr_number), "--json", "state,baseRefName"],
        timeout=_PROBE_TIMEOUT_S,
    )
    if view.returncode != 0:
        sys.stdout.write(f"FAIL  land: gh pr view failed: {view.stderr.strip()}\n")
        return None
    info = json.loads(view.stdout)
    if info.get("baseRefName") != "main":
        # Post-merge main-CI watch + local main fast-forward assume a main PR.
        sys.stdout.write(
            f"FAIL  land: PR #{pr_number} targets {info.get('baseRefName')!r}, "
            "not main — land only validates main-based PRs\n"
        )
        return None
    if info["state"] != "MERGED":
        sys.stdout.write(
            f"land: PR #{pr_number} is {info['state']}, not yet MERGED — ship "
            "enabled auto-merge; GitHub merges when ci-gate is green. Re-run land "
            "once it has merged (land is the post-merge Mac validation now).\n"
        )
        return None
    merge_oid = _merge_commit_oid(pr_number)
    pr_paths = _pr_changed_paths(pr_number)
    if not merge_oid or not _main_run_conclusion(
        merge_oid, expect_run=expects_main_run(pr_paths)
    ):
        return None
    return touches_surface(pr_paths)


def land_main(workspace: Path, pr_number: int, *, resume: bool = False) -> int:
    """Post-merge validation for an auto-merged PR.

    ship enables native auto-merge, so GitHub merges the PR when ci-gate is
    green. land is the post-merge step: confirm the PR MERGED, verify the main
    ci.yml run concluded success, fast-forward local main, and run the
    Mac-local ``verify-local`` (arm64 R1/R2/R3 + persistence) that can't run in
    CI. Run it once the PR has merged; it is idempotent (safe to re-run). The
    ``resume`` flag is accepted for compatibility — land is always the
    idempotent post-merge replay now, so it has no separate effect.
    """
    _ = resume  # land is always the idempotent post-merge replay now
    surface = _land_post_merge(pr_number)
    if surface is None:
        return 1

    # Post-merge validation must run against main's code (the merged
    # state), not whatever branch the checkout happens to be on.
    if (
        _stream(["git", "-C", str(workspace), "checkout", "main"]) != 0
        or _stream(["git", "-C", str(workspace), "pull", "--ff-only"]) != 0
    ):
        sys.stdout.write("FAIL  land: could not fast-forward local main\n")
        return 1

    sys.stdout.write(
        f"==> post-merge local validation ({'full' if surface else 'smoke'} tier)\n"
    )
    rc = sync_main(workspace, SyncOptions(full=surface))
    if rc != 0:
        return rc
    sys.stdout.write(f"\nland: OK — PR #{pr_number} merged, main green, Mac synced\n")
    return 0
