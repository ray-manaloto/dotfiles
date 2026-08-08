# Copyright (c) 2026 Raymond Manaloto

"""Partition linter violations into "mine" and "the upgrade's" (#651).

A linter bump makes every newly-enabled rule look like a regression in your own
change. Measured 2026-08-08, ruff 0.15.20 -> 0.16.2 against **one unchanged
tree**:

=====================  =======  ==========================================
ruff                    total    breakdown
=====================  =======  ==========================================
0.15.20 (previous)      **2**    I001 x1, D403 x1 — both genuinely mine
0.16.2 (new pin)      **138**    + CPY001 x106, ISC004 x30 — pre-existing
=====================  =======  ==========================================

Without the partition the choice reads as *"fix 138 or suppress"*; with it, as
*"fix 2, then decide policy on two new rule classes"*. That is the difference
between a panic and a decision, and it is the control-arm discipline
``.claude/rules/probes-need-a-control-arm.md`` already mandates — **the old
version IS the control arm**, run against the same tree, so any difference is
attributable to the tool rather than to the code.

Three things this module treats as load-bearing:

- **Diff by RULE CODE, not by line.** The question is *which rule classes are
  new*, and a line-level diff answers it with a wall of diagnostics that has to
  be re-summarised by hand — the very work being automated.
- **Report BOTH directions.** A rule that stopped firing is information too: it
  means the upgrade removed or relaxed something a gate used to catch, which is
  a silent loss of coverage rather than good news.
- **A baseline equal to the current pin is refused, loudly.** Comparing a
  version against itself is a probe with one face: it can only report "no
  change", and reporting that as a clean bill would be exactly the false
  negative rule 9 exists to refuse.

The baseline defaults to the version at the **previous revision that touched
the lockfile** — not ``HEAD~1``, which is merely the previous commit and
usually did not touch it at all. That default makes the common case ("I just
bumped it") need no argument, and it is derived rather than remembered.

Nothing here is ruff-specific: :data:`TOOLS` describes each tool's invocation
and how to recover a rule code from its output, and every seam (tool, baseline,
paths, runner) is a parameter with this repo's case as the default.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

logger = logging.getLogger(__name__)

#: The lockfile the pinned versions are read from.
LOCKFILE = "python/uv.lock"

#: What this repo lints. Not a hard-coded scope: it is the default of a
#: parameter, so the same functions serve one file or another project.
DEFAULT_PATHS: tuple[str, ...] = ("python/src", "tests")

_TIMEOUT_S = 300.0


def parse_ruff(stdout: str) -> Counter[str]:
    """Rule codes from ``ruff check --output-format json``."""
    try:
        parsed = json.loads(stdout or "[]")
    except json.JSONDecodeError:
        return Counter()
    return Counter(
        entry["code"]
        for entry in (parsed if isinstance(parsed, list) else [])
        if isinstance(entry, dict) and isinstance(entry.get("code"), str)
    )


_TY_CODE = re.compile(r"^\w+\[([a-z0-9-]+)\]", re.MULTILINE)


def parse_ty(stdout: str) -> Counter[str]:
    """Rule names from ``ty check --output-format concise``.

    ty has no JSON output (``full``, ``concise``, ``gitlab``, ``github``,
    ``junit``), so the concise form is parsed for its ``error[rule-name]``
    prefix. Checked against the real CLI rather than assumed.
    """
    return Counter(_TY_CODE.findall(stdout))


@dataclass(frozen=True)
class ToolSpec:
    """How to run one linter at an arbitrary version and read its rule codes."""

    name: str
    argv: tuple[str, ...]
    parse: Callable[[str], Counter[str]]
    #: Package name in ``uv.lock``; usually but not necessarily the tool name.
    package: str = ""

    @property
    def lock_name(self) -> str:
        """The package name to look up in the lockfile."""
        return self.package or self.name


TOOLS: dict[str, ToolSpec] = {
    "ruff": ToolSpec(
        name="ruff",
        argv=("check", "--output-format", "json"),
        parse=parse_ruff,
    ),
    "ty": ToolSpec(
        name="ty",
        argv=("check", "--output-format", "concise"),
        parse=parse_ty,
    ),
}


@dataclass(frozen=True)
class Delta:
    """Per-code counts at two versions, and what moved between them."""

    tool: str
    baseline_version: str
    current_version: str
    baseline: Counter[str]
    current: Counter[str]

    @property
    def introduced(self) -> list[tuple[str, int]]:
        """Codes the new version fires that the old one did not — the upgrade's."""
        return sorted(
            (
                (code, n)
                for code, n in self.current.items()
                if code not in self.baseline
            ),
            key=lambda pair: (-pair[1], pair[0]),
        )

    @property
    def retired(self) -> list[tuple[str, int]]:
        """Codes the old version fired and the new one does not.

        Not automatically good news: a rule that stopped firing is coverage the
        gate used to have and silently lost.
        """
        return sorted(
            (
                (code, n)
                for code, n in self.baseline.items()
                if code not in self.current
            ),
            key=lambda pair: (-pair[1], pair[0]),
        )

    @property
    def mine(self) -> list[tuple[str, int]]:
        """Codes BOTH versions fire — attributable to the code, not the bump."""
        return sorted(
            (
                (code, self.current[code])
                for code in self.current
                if code in self.baseline
            ),
            key=lambda pair: (-pair[1], pair[0]),
        )


def locked_version(lock_text: str, package: str) -> str | None:
    """The version ``uv.lock`` pins for ``package``; None when it is absent."""
    match = re.search(
        rf'\[\[package\]\]\nname = "{re.escape(package)}"\nversion = "([^"]+)"',
        lock_text,
    )
    return match.group(1) if match else None


def previous_lock_revision(repo_root: Path, lockfile: str = LOCKFILE) -> str | None:
    """The revision BEFORE the most recent one that touched the lockfile.

    Deliberately not ``HEAD~1``: the previous commit usually did not touch the
    lockfile at all, so its pins are identical to HEAD's and the comparison
    would be a version against itself.
    """
    result = subprocess.run(
        ["git", "-C", str(repo_root), "log", "-2", "--format=%H", "--", lockfile],
        capture_output=True,
        text=True,
        check=False,
    )
    revisions = result.stdout.split()
    return revisions[1] if len(revisions) > 1 else None


def version_at(
    repo_root: Path, revision: str, package: str, lockfile: str
) -> str | None:
    """The pinned version of ``package`` as of ``revision``."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{revision}:{lockfile}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return locked_version(result.stdout, package)


def run_at_version(
    spec: ToolSpec,
    version: str,
    paths: Sequence[str],
    *,
    cwd: Path,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> Counter[str]:
    """Run ``spec`` pinned to ``version`` over ``paths`` and count rule codes.

    ``uvx <tool>@<version>`` rather than the project environment: the whole
    point is to run a version the project is NOT pinned to, which an
    environment-resolved binary cannot do. A non-zero exit is expected and
    ignored — a linter that found violations is the normal case here.
    """
    argv = ["uvx", f"{spec.name}@{version}", *spec.argv, *paths]
    result = run(
        argv, capture_output=True, text=True, check=False, cwd=cwd, timeout=_TIMEOUT_S
    )
    return spec.parse(result.stdout)


def _table(rows: Sequence[tuple[str, int]], empty: str) -> list[str]:
    if not rows:
        return [f"_{empty}_"]
    return [
        "| code | count |",
        "|---|---|",
        *(f"| `{code}` | {count} |" for code, count in rows),
    ]


def render_report(delta: Delta) -> str:
    """The partition, as the decision it is meant to support."""
    introduced = sum(n for _, n in delta.introduced)
    mine = sum(n for _, n in delta.mine)
    return "\n".join(
        [
            (
                f"# lint-delta: {delta.tool} {delta.baseline_version} -> "
                f"{delta.current_version}"
            ),
            "",
            (
                f"**{mine} attributable to the code, {introduced} to the "
                f"upgrade.** Same tree, two tool versions — the old version is "
                f"the control arm, so every difference below belongs to the bump."
            ),
            "",
            "## Yours — both versions fire these",
            "",
            *_table(delta.mine, "nothing: every violation came in with the upgrade"),
            "",
            "## The upgrade's — new rule classes",
            "",
            *_table(delta.introduced, "no new rule fired"),
            "",
            "## Retired — the OLD version fired these and the new one does not",
            "",
            *_table(
                delta.retired,
                "nothing stopped firing",
            ),
            "",
            (
                "A retired code is not automatically good news: it is coverage "
                "the gate used to have. Check whether the rule was removed, "
                "renamed, or merely stopped matching."
            ),
            "",
        ]
    )


def lint_delta_main(
    repo_root: Path,
    *,
    tool: str = "ruff",
    baseline: str | None = None,
    paths: Sequence[str] = DEFAULT_PATHS,
    lockfile: str = LOCKFILE,
) -> int:
    """Run both versions over the same tree and report the partition.

    Exits 2 rather than 0 when the comparison cannot discriminate — an absent
    baseline, or a baseline equal to the current pin. Reporting "no new rules"
    from a version compared against itself would be a probe with one face.
    """
    spec = TOOLS.get(tool)
    if spec is None:
        logger.error("unknown tool %r; known: %s", tool, ", ".join(sorted(TOOLS)))
        return 2

    current = locked_version((repo_root / lockfile).read_text(), spec.lock_name)
    if current is None:
        logger.error("%s does not pin %s", lockfile, spec.lock_name)
        return 2

    if baseline is None:
        revision = previous_lock_revision(repo_root, lockfile)
        baseline = (
            version_at(repo_root, revision, spec.lock_name, lockfile)
            if revision
            else None
        )
        if baseline is None:
            logger.error(
                "could not derive a baseline: no earlier revision of %s pins %s. "
                "Name one with --baseline <version>.",
                lockfile,
                spec.lock_name,
            )
            return 2

    if baseline == current:
        logger.error(
            "baseline %s == current pin %s, so this comparison can only report "
            "'no change' — a probe with one face. The previous revision of %s "
            "did not bump %s; name an older version with --baseline.",
            baseline,
            current,
            lockfile,
            spec.lock_name,
        )
        return 2

    logger.info(
        "running %s at %s and %s over %s", tool, baseline, current, ", ".join(paths)
    )
    delta = Delta(
        tool=tool,
        baseline_version=baseline,
        current_version=current,
        baseline=run_at_version(spec, baseline, paths, cwd=repo_root),
        current=run_at_version(spec, current, paths, cwd=repo_root),
    )
    logger.info("%s", render_report(delta))
    return 0
