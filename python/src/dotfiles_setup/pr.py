"""Ship/land: the full PR loop as library code (zero-bash-logic).

``dotfiles-setup pr ship`` (wrapped by ``mise run ship``) takes the
current feature branch from "work is committed/staged" to "PR open with
checks watched"; ``dotfiles-setup pr land <n>`` (wrapped by
``mise run land``) takes a green PR through squash-merge, main-CI watch,
and post-merge LOCAL validation on this Mac. Together they encode the
verify-before-advancing rule as code instead of discipline.

Design notes (deep-research verified, 2026-07-07 —
``.omc/research/research-20260707-gha-shipland-enforcement/report.md``):

- **Check verification reads the ``--json`` buckets**, never a watch
  command's exit code alone (``gh run watch --exit-status`` has reported
  0 prematurely; see ``.claude/rules/gh-cli-watch.md``). A PR is green
  iff every check bucket is ``pass`` or ``skipping``. ship also waits for
  the ``ci-gate`` aggregator (:data:`_AGGREGATE_CHECK`) to register before
  ``--watch``, so a build PR is not declared green on an early check wave
  before build-publish's matrix jobs register (#181).
- **The merge is delegated to GitHub's requirements engine** with the
  head SHA pinned: ``gh pr merge --squash --match-head-commit <sha>``
  returns 409 if the branch moved after we verified it — closing the
  verify-then-merge race.
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

# The always-run aggregator job (ci.yml) that `needs` every other job and is
# branch-protection-required on every PR. ship waits for THIS to register
# before `gh pr checks --watch`, so --watch cannot exit on an early all-green
# wave before the build-publish matrix jobs (base-prep/build/smoke-test)
# register — the premature-green ship gap found landing #181.
_AGGREGATE_CHECK = "ci-gate"


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

    Always: lint, pytest, verify contracts. Conditional per
    verify-before-advancing: pin-actions on .github changes, lint-docs on
    agent-doc changes. The full-sync hard gate runs LAST (most expensive)
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
    ]
    if any(_matches_any(p, _GHA_PATTERNS) for p in paths):
        gates.append(Gate("pin-actions", ("mise", "run", "pin-actions")))
    if any(_matches_any(p, _DOCS_PATTERNS) for p in paths):
        gates.append(Gate("lint-docs", ("mise", "run", "lint-docs")))
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


def _await_aggregate_registered(pr_number: int, *, attempts: int = 40) -> bool:
    """Poll until the ``ci-gate`` aggregator check is registered.

    build-publish's matrix jobs (base-prep/build/smoke-test) register in
    WAVES after ``changes`` decides build=true, so waiting for *any* check
    (``_await_checks_registered``) let ``gh pr checks --watch`` exit on an
    early all-green wave before the build jobs appeared — ship declared #181
    green prematurely. :data:`_AGGREGATE_CHECK` ``needs`` every job, so once
    it is present the subsequent ``--watch`` cannot terminate until the whole
    chain (including the late-registering build jobs) is terminal.
    """
    for _ in range(attempts):
        res = _run(
            ["gh", "pr", "checks", str(pr_number), "--json", "name"],
            timeout=_PROBE_TIMEOUT_S,
        )
        if res.returncode == 0 and any(
            c.get("name") == _AGGREGATE_CHECK for c in json.loads(res.stdout or "[]")
        ):
            return True
        time.sleep(15)
    sys.stdout.write(
        f"FAIL  pr-checks: aggregator {_AGGREGATE_CHECK!r} never registered on "
        f"PR #{pr_number} within {attempts * 15}s\n"
    )
    return False


def watch_pr_checks(pr_number: int) -> bool:
    """Await registration, watch to terminal state, verify via JSON buckets.

    Waits for the ``ci-gate`` aggregator to register before ``--watch`` so a
    build PR is not declared green on an early check wave (#181 gap).
    """
    if not _await_checks_registered(pr_number):
        return False
    if not _await_aggregate_registered(pr_number):
        return False
    _stream(["gh", "pr", "checks", str(pr_number), "--watch", "--fail-fast"])
    ok, detail = pr_checks_green(pr_number)
    sys.stdout.write(f"{'PASS' if ok else 'FAIL'}  pr-checks: {detail}\n")
    return ok


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
    if _stream(create, cwd=workspace) != 0:
        sys.stdout.write("FAIL  ship: gh pr create failed\n")
        return None
    view = _run(
        ["gh", "pr", "view", "--json", "number"],
        timeout=_PROBE_TIMEOUT_S,
        cwd=workspace,
    )
    if view.returncode != 0 or not view.stdout.strip():
        # Review finding [10]: never JSON-parse an unchecked gh result.
        sys.stdout.write("FAIL  ship: created PR but could not resolve its number\n")
        return None
    return int(json.loads(view.stdout)["number"])


def ship_main(workspace: Path, *, title: str | None = None) -> int:
    """Gates → push → PR → watched checks. Requires committed work on a branch.

    Commit creation stays with the operator/agent (messages need human
    judgment); ship refuses a dirty tree so nothing half-staged leaks
    past the gates (`clean-git-state` rule).
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

    if _stream(["git", "push", "-u", "origin", branch], cwd=workspace) != 0:
        sys.stdout.write("FAIL  ship: git push failed\n")
        return 1

    number = _open_or_update_pr(workspace, title)
    if number is None or not watch_pr_checks(number):
        return 1
    sys.stdout.write(f"\nship: OK — PR #{number} green and ready for land\n")
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


def _land_preflight(pr_number: int) -> tuple[str, bool] | None:
    """PR open + base main + checks verified green; None on fail."""
    view = _run(
        [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--json",
            "state,headRefOid,baseRefName",
        ],
        timeout=_PROBE_TIMEOUT_S,
    )
    if view.returncode != 0:
        sys.stdout.write(f"FAIL  land: gh pr view failed: {view.stderr.strip()}\n")
        return None
    info = json.loads(view.stdout)
    if info["state"] != "OPEN":
        sys.stdout.write(f"FAIL  land: PR #{pr_number} is {info['state']}\n")
        return None
    if info.get("baseRefName") != "main":
        # Review finding [11]: land's post-merge main-CI watch and local
        # main fast-forward only make sense for main-based PRs.
        sys.stdout.write(
            f"FAIL  land: PR #{pr_number} targets {info.get('baseRefName')!r}, "
            "not main — land only lands main-based PRs\n"
        )
        return None
    ok, detail = pr_checks_green(pr_number)
    sys.stdout.write(f"{'PASS' if ok else 'FAIL'}  pr-checks: {detail}\n")
    if not ok:
        return None
    surface = touches_surface(_pr_changed_paths(pr_number))
    return info["headRefOid"], surface


def _merge_and_watch_main(workspace: Path, pr_number: int, head: str) -> bool:
    """Pinned squash-merge, then the main ci.yml run must conclude success.

    Known-accepted race (review finding [7]): main can advance between
    check-verification and this merge; --match-head-commit pins only the
    PR head. Accepted because the post-merge main-CI watch below re-runs
    the full gate chain on the ACTUAL merge commit and land fails loud if
    it does not conclude success — the race window cannot produce a
    silently-broken main.
    """
    merge = [
        "gh",
        "pr",
        "merge",
        str(pr_number),
        "--squash",
        "--delete-branch",
        "--match-head-commit",
        head,
    ]
    if _stream(merge, cwd=workspace) != 0:
        sys.stdout.write(
            "FAIL  land: merge refused (head moved since verification, or "
            "branch protection unmet) — re-verify and rerun\n"
        )
        return False
    merge_oid = _merge_commit_oid(pr_number)
    if not merge_oid:
        sys.stdout.write("FAIL  land: could not resolve the merge commit oid\n")
        return False
    expect_run = expects_main_run(_pr_changed_paths(pr_number))
    return _main_run_conclusion(merge_oid, expect_run=expect_run)


def _land_merge_phase(workspace: Path, pr_number: int, *, resume: bool) -> bool | None:
    """Merge (or resume-verify) phase; returns surface flag or None on fail."""
    if resume:
        state = _run(
            ["gh", "pr", "view", str(pr_number), "--json", "state"],
            timeout=_PROBE_TIMEOUT_S,
        )
        if state.returncode != 0 or json.loads(state.stdout)["state"] != "MERGED":
            sys.stdout.write(
                f"FAIL  land --resume: PR #{pr_number} is not MERGED — use a "
                "plain land\n"
            )
            return None
        merge_oid = _merge_commit_oid(pr_number)
        pr_paths = _pr_changed_paths(pr_number)
        if not merge_oid or not _main_run_conclusion(
            merge_oid, expect_run=expects_main_run(pr_paths)
        ):
            return None
        return touches_surface(pr_paths)
    preflight = _land_preflight(pr_number)
    if preflight is None:
        return None
    head, surface = preflight
    if not _merge_and_watch_main(workspace, pr_number, head):
        return None
    return surface


def land_main(workspace: Path, pr_number: int, *, resume: bool = False) -> int:
    """Verify green → pinned squash-merge → main-CI watch → local validation.

    ``resume=True`` (review finding [6]): re-enter after a failure that
    happened AFTER the merge (main-CI watch, fast-forward, local
    validation) — skips the merge for an already-MERGED PR and replays
    the idempotent post-merge steps, so a merged-but-unvalidated PR never
    strands.
    """
    surface = _land_merge_phase(workspace, pr_number, resume=resume)
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
