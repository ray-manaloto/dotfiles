# Copyright (c) 2026 Raymond Manaloto
"""No-new-bash-logic enforcement: allowlist + per-file growth budget.

The zero-bash-logic policy (root `AGENTS.md` — "Non-trivial logic lives in
`python/`; bash restricted to thin check/smoke wrappers") was doc-only until
this module. It gives that policy machine teeth for the two host-side shell
directories in scope:

- ``scripts/*.sh`` and ``.devcontainer/scripts/*.sh`` (git's ``*`` spans ``/``
  in a plain pathspec, so nested ``scripts/sub/x.sh`` is caught too — the
  subdir bypass is closed).
- ``plugins/**`` is OUT of scope (vendored / third-party).

Two mechanisms, per Ray's locked decision (2026-07-13-e):

1. **Allowlist gates NEW files.** Every in-scope ``.sh`` must have an
   :data:`ALLOWLIST` entry. A new script not on the list FAILS — the author
   either moves the logic into ``python/`` (the default answer) or adds an
   explicit entry with a one-line justification (a reviewable diff).
2. **Per-file budget flags GROWTH.** Each entry's ``max_lines`` is its baseline
   line count. Growth past baseline FAILS (shrinking is always fine); a budget
   bump is a reviewable diff + justification, not a silent creep.

A stale entry (allowlisted path no longer tracked) also FAILS, so the map can't
rot after a script is deleted — same "keep the wiring honest" spirit as the
``no_global_skill_leakage`` hk step.

The check logic lives here (not in a big inline-bash hk step) so the enforcer
does not itself violate the policy it enforces. The hk step
(``bash_logic_budget``) and the ``bash-budget`` CLI subcommand are thin
wrappers over :func:`find_violations`.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# git pathspecs for the two in-scope shell directories. `*` spans `/` in a
# plain git pathspec, so these also match nested `.sh` under each directory.
SCOPE_PATHSPECS: tuple[str, ...] = (
    "scripts/*.sh",
    ".devcontainer/scripts/*.sh",
)


@dataclass(frozen=True)
class BashAllowance:
    """A permitted in-scope shell script: its line budget + why bash is OK."""

    max_lines: int
    reason: str


# Declarative allowlist + growth budget. `max_lines` = the file's baseline line
# count (`wc -l`) at adoption; growth past it FAILS. Each `reason` justifies why
# thin bash is acceptable here rather than Python. Bumping a budget or adding an
# entry is a reviewable diff — keep the justification honest.
ALLOWLIST: dict[str, BashAllowance] = {
    ".devcontainer/scripts/on-create.sh": BashAllowance(
        74,
        "devcontainer postCreate lifecycle hook — thin wrapper from devcontainer.json",
    ),
    "scripts/benchmark-docker.sh": BashAllowance(
        # 167 -> 171 (#673): four lines resolving the target platform and its
        # expected `uname -m` from `dotfiles-setup platform`, replacing ten
        # hard-coded platform/machine literals. Assignments only — the
        # triple->arch mapping stayed in python.
        171,
        "docker build/pull timing harness — thin wrapper over docker/hyperfine CLIs",
    ),
    "scripts/check-chezmoi-templates.sh": BashAllowance(
        48, "hk check wrapper — renders home/ templates via the chezmoi CLI"
    ),
    "scripts/check-claude-agents-md-pairs.sh": BashAllowance(
        45, "hk check wrapper — CLAUDE.md/AGENTS.md sibling-pair assertion"
    ),
    "scripts/check-claude-md-stub.sh": BashAllowance(
        57, "hk check wrapper — CLAUDE.md thin-import-stub assertion"
    ),
    "scripts/devcontainer-smoke.sh": BashAllowance(
        157,
        "tier 1-3 smoke harness — thin wrapper; the non-trivial tier-1/tier-3 "
        "cores live in `dotfiles-setup image smoke-script` (#223)",
    ),
    "scripts/ensure-docker-up.sh": BashAllowance(
        74, "hk/mise precondition wrapper — starts Docker Desktop if the daemon is down"
    ),
    "scripts/pretooluse-guard.sh": BashAllowance(
        42,
        "fail-open shim — runs `dotfiles-setup hook pretooluse` (the guard is "
        "Python). 25 -> 42 for #343: the shim must anchor every path to "
        "$CLAUDE_PROJECT_DIR (it runs in the session's cwd, not the repo) and "
        "must RECORD each fail-open. Both have to be bash — they are the layer "
        "that runs when Python cannot, so a Python fail-open counter could "
        "never observe the case it exists to count",
    ),
    "scripts/graphify-hook-guard.sh": BashAllowance(
        30,
        "fail-open shim — execs `dotfiles-setup graphify hook-guard "
        "search|read` via `uv run --project python` (the repo-pinned 0.9.42, "
        "matching graphify-query/health/update — not the user-global PATH "
        "shim). The nudge-text rewrite itself lives in Python "
        "(graphify.py::rewrite_hook_nudge, unit-tested) per zero-bash-logic; "
        "this shim stays a thin resolve-and-exec wrapper.",
    ),
    "scripts/validate-devcontainer-json.sh": BashAllowance(
        73,
        "hk check wrapper — 3-layer devcontainer.json validation via "
        "biome/devcontainer/check-jsonschema CLIs",
    ),
    "scripts/web-setup.sh": BashAllowance(
        75, "Claude Code web/cloud bootstrap — thin environment wrapper"
    ),
}


@dataclass(frozen=True)
class BashViolation:
    """A zero-bash-logic policy breach found by :func:`find_violations`."""

    path: str
    kind: str  # "unlisted" | "growth" | "stale"
    detail: str


def tracked_in_scope(repo_root: Path) -> list[str]:
    """Tracked in-scope shell scripts, via ``git ls-files``."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "--", *SCOPE_PATHSPECS],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def line_count(path: Path) -> int:
    """Newline count — identical to ``wc -l`` for the baselines."""
    return path.read_text(errors="replace").count("\n")


def find_violations(repo_root: Path) -> list[BashViolation]:
    """Return every zero-bash-logic breach in the in-scope shell dirs.

    Three failure kinds:

    - ``unlisted`` — a tracked in-scope ``.sh`` with no :data:`ALLOWLIST`
      entry (move the logic to ``python/``, or add a justified entry).
    - ``growth`` — an allowlisted script now longer than its budget.
    - ``stale`` — an allowlisted path no longer tracked (prune the entry).
    """
    tracked = tracked_in_scope(repo_root)
    violations: list[BashViolation] = []

    for rel in tracked:
        allowance = ALLOWLIST.get(rel)
        if allowance is None:
            violations.append(
                BashViolation(
                    rel,
                    "unlisted",
                    "not in the bash-budget allowlist — move non-trivial logic "
                    "into python/, or add a justified ALLOWLIST entry in "
                    "python/src/dotfiles_setup/bash_budget.py",
                )
            )
            continue
        lines = line_count(repo_root / rel)
        if lines > allowance.max_lines:
            violations.append(
                BashViolation(
                    rel,
                    "growth",
                    f"{lines} lines exceeds budget {allowance.max_lines} — shrink "
                    f"it, move logic to python/, or bump the budget with a reason",
                )
            )

    tracked_set = set(tracked)
    violations.extend(
        BashViolation(
            rel,
            "stale",
            "allowlisted but no longer tracked — remove the stale ALLOWLIST "
            "entry in python/src/dotfiles_setup/bash_budget.py",
        )
        for rel in ALLOWLIST
        if rel not in tracked_set
    )

    return violations


def bash_budget_main(repo_root: Path) -> int:
    """CLI entry: report violations to stderr; exit 1 if any, else 0."""
    violations = find_violations(repo_root)
    if violations:
        for v in violations:
            logger.error("bash-budget %s: %s — %s", v.kind, v.path, v.detail)
        return 1
    logger.info(
        "bash-budget OK: %d in-scope shell scripts within allowlist + budget",
        len(ALLOWLIST),
    )
    return 0
