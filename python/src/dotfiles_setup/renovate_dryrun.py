# Copyright (c) 2026 Raymond Manaloto
"""Local Renovate dry-run — what WOULD Renovate change, without opening a PR.

``dotfiles-setup renovate-dryrun`` (wrapped by ``mise run renovate-dryrun``)
runs the real Renovate binary against this working tree and reports the
dependency updates it would raise. It never writes, branches, or opens a PR.

This is the only local way to answer "what would Renovate actually do to
``[bootstrap.packages]``?" (#251/#288) without waiting for a hosted scan. A
scratch-directory fixture proves the *customManager*; only this proves the
*task* — the distinction that produced #290.

Three renovate facts are load-bearing here; each was probed against the real
binary (npm:renovate 43.260.2) on 2026-07-15, and each is why this module
exists rather than a bare ``run =`` one-liner:

1. **``cloneSubmodules`` must be forced off (#290).** The preset we extend,
   ``github>jdx/renovate-config``, sets ``cloneSubmodules: true``. Renovate's
   ``initRepo`` calls ``cloneSubmodules(!!config.cloneSubmodules)``, which
   early-returns *unless* the flag is set — ours is, so it reaches
   ``syncGit()``, which throws ``Cannot sync git when platform=local``
   outright. No ``.gitmodules`` is needed to trigger it; the flag alone does.
   ``RENOVATE_CLONE_SUBMODULES=false`` does NOT fix it: env is the *global*
   config layer and repo config (renovate.json + its resolved presets) is
   applied over it. ``force`` is the documented layer applied AFTER repo
   resolution, so it is the only override that wins — and it keeps
   ``renovate.json`` byte-identical to what hosted Renovate reads.

2. **``--dry-run=full`` is silently downgraded.** The local platform's
   ``initPlatform`` coerces the mode: ``extract`` stays ``extract``, and
   anything else — ``full`` included — becomes ``lookup``. The task asked for
   ``full`` for months and never got it. We ask for ``lookup`` and mean it.

3. **The native report is populated in lookup mode.** ``addExtractionStats``
   is called BEFORE the ``dryRun !== 'lookup'`` guard in the repository
   worker, so ``reportType=file`` yields every packageFile's deps *with* their
   resolved ``updates[]``. That is renovate's own structured output, so we
   parse JSON rather than scraping a 5k-line debug log
   (``.claude/rules/use-tool-builtins.md``).

The local platform also returns ``persistRepoData: true``, which is the only
thing suppressing the repository worker's ``deleteLocalFile('.')`` — under
``platform=local`` the "localDir" IS this working tree. Do not set
``persistRepoData: false``.

A fourth fact, corrected in #299: ``mise.toml`` pins this task to node 24
because renovate 43.x declares ``engines.node ^24.11.0``. Under node 26 the
binary **extracts and resolves normally** and then exits non-zero on the
logged engine error — it does NOT lose data. The pin buys a clean exit code,
not correctness of the report. The earlier "extracts NOTHING" rationale was a
true statement about *some older renovate* applied outside the condition that
made it true; measured against 43.265.1 it is false, and it sent a reader
hunting a data-loss bug that does not exist. A fact needs its condition, not
just its source (``.claude/rules/verify-before-advancing.md``).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Renovate resolves `force` AFTER repo config (renovate.json + presets), so it
# is the only layer that can override the jdx preset's cloneSubmodules=true.
# See the module docstring, fact 1, and #290.
_FORCE_CONFIG = '{"cloneSubmodules":false}'

# `local` is the only platform that reads the working tree instead of cloning.
# `lookup` is what the local platform coerces every non-`extract` mode to
# anyway (fact 2) — naming it keeps the command honest about what it does.
RENOVATE_ARGS = ("--platform=local", "--dry-run=lookup")

# A lookup pass hits every datasource in the repo over the network.
_RENOVATE_TIMEOUT_S = 900.0

# Renovate reads github.com lookup credentials from GITHUB_COM_TOKEN (or
# RENOVATE_GITHUB_COM_TOKEN) ONLY, and promotes it to a hostRule scoped to
# matchHost: "github.com". It does not merely ignore a bare GITHUB_TOKEN — it
# DELETES it from its own env (parse/env.js, alongside GITLAB_TOKEN et al), so
# that a *platform* token can never leak into *datasource* lookups. That is why
# a shell with GITHUB_TOKEN exported still logs "GitHub token is required for
# some dependencies": the secret is inherited and then discarded by design.
#
# Without it, renovate silently SKIPS every github-datasource dep and reports a
# smaller number with no error — probed 2026-07-15 on this repo: 8 pending
# without a token vs 33 with one (53 deps unlooked-up). A tool that answers
# "8" when the truth is "33" is worse than one that refuses, so an untokened
# run is labelled INCOMPLETE rather than reported as a total.
#
# Order: the explicit renovate names first, then the conventional env tokens.
_TOKEN_ENV_VARS = (
    "GITHUB_COM_TOKEN",
    "RENOVATE_GITHUB_COM_TOKEN",
    "GITHUB_TOKEN",
    "GITHUB_API_TOKEN",
    "MISE_GITHUB_TOKEN",
)


@dataclass
class PendingUpdate:
    """One dependency Renovate would raise a PR for."""

    manager: str
    package_file: str
    dep_name: str
    current_value: str
    new_value: str

    def render(self) -> str:
        """Render as one aligned report row."""
        return (
            f"  [{self.manager}] {self.dep_name}: "
            f"{self.current_value} -> {self.new_value}  ({self.package_file})"
        )


@dataclass
class GroupStats:
    """Dep tallies for one manager, or one datasource.

    Exists so the report can answer "did my regex extract?" — the question
    #251 documented and #288 had to answer by bypassing the task and running
    the binary by hand. A pending-updates list alone cannot: a custom manager
    that matched zero files and a custom manager whose deps are all current
    both render as silence.
    """

    name: str
    deps: int
    updates: int
    skipped: int

    def render(self) -> str:
        """Render as one aligned report row."""
        skipped = f", {self.skipped} skipped" if self.skipped else ""
        # Pad the whole "N dep(s)," phrase, not the noun — padding the noun
        # put the space INSIDE, rendering "1 dep ,".
        count = f"{self.deps} {'dep' if self.deps == 1 else 'deps'},"
        return f"  {self.name:<14} {count:>9} {self.updates:>2} pending{skipped}"


@dataclass
class DryRunResult:
    """The outcome of one local Renovate dry-run."""

    total_deps: int
    updates: list[PendingUpdate]
    problems: list[str]
    # False when no github.com token was available, i.e. every github-datasource
    # dep was skipped and `updates` is a FLOOR rather than a total.
    complete: bool = True
    # What each manager/datasource actually extracted. Renovate's native report
    # carries `manager`, `datasource` and `skipReason` per dep; these were
    # discarded at the parse seam until #299.
    managers: list[GroupStats] = field(default_factory=list)
    datasources: list[GroupStats] = field(default_factory=list)


def resolve_github_token(env: dict[str, str] | None = None) -> str | None:
    """Find a github.com lookup token in the environment.

    Returns the first non-empty value among ``_TOKEN_ENV_VARS``, or None. The
    token is only ever handed to renovate as ``GITHUB_COM_TOKEN``, which
    renovate promotes to a hostRule scoped to ``matchHost: "github.com"``, and
    which its own docs state "needs only read-only access".
    """
    source = os.environ if env is None else env
    for name in _TOKEN_ENV_VARS:
        value = source.get(name)
        if value:
            return value
    return None


def renovate_env(
    report_path: Path, env: dict[str, str] | None = None
) -> dict[str, str]:
    """Build the environment for the renovate child process."""
    child = dict(os.environ if env is None else env)
    child["RENOVATE_FORCE"] = _FORCE_CONFIG
    child["RENOVATE_REPORT_TYPE"] = "file"
    child["RENOVATE_REPORT_PATH"] = str(report_path)
    token = resolve_github_token(child)
    if token:
        child["GITHUB_COM_TOKEN"] = token
    return child


def run_renovate(report_path: Path) -> subprocess.CompletedProcess[str]:
    """Run the renovate binary, writing its native JSON report to disk."""
    return subprocess.run(
        ["renovate", *RENOVATE_ARGS],
        env=renovate_env(report_path),
        capture_output=True,
        text=True,
        timeout=_RENOVATE_TIMEOUT_S,
        check=False,
    )


def _tally(
    counts: dict[str, list[int]], key: str, *, updates: int, skipped: int
) -> None:
    """Accumulate one dep into the [deps, updates, skipped] row for `key`."""
    row = counts.setdefault(key, [0, 0, 0])
    row[0] += 1
    row[1] += updates
    row[2] += skipped


def _stats(counts: dict[str, list[int]]) -> list[GroupStats]:
    """Render the tally rows as GroupStats, busiest first then alphabetical."""
    return [
        GroupStats(name=name, deps=row[0], updates=row[1], skipped=row[2])
        for name, row in sorted(counts.items(), key=lambda kv: (-kv[1][0], kv[0]))
    ]


def parse_report(raw: str, *, complete: bool = True) -> DryRunResult:
    """Extract the pending updates and extraction tallies from renovate's report.

    The per-manager/per-datasource tallies are the answer to "did it look?" —
    a manager absent from `managers` matched nothing, which is a different
    fact from "matched, and everything is current" (deps > 0, updates == 0).
    Renovate reports both identically in its pending list, which is why #288
    could not use this task and hand-ran the binary instead (#299).
    """
    report = json.loads(raw)
    repo = report.get("repositories", {}).get("local", {})
    updates: list[PendingUpdate] = []
    by_manager: dict[str, list[int]] = {}
    by_datasource: dict[str, list[int]] = {}
    total = 0
    for manager, files in (repo.get("packageFiles") or {}).items():
        for entry in files:
            package_file = entry.get("packageFile", "?")
            for dep in entry.get("deps", []):
                total += 1
                pending = dep.get("updates") or []
                # A skipReason means renovate declined to look this dep up --
                # NOT that it is current. Counting it as either would restate
                # the very confusion this report exists to remove.
                skipped = 1 if dep.get("skipReason") else 0
                _tally(by_manager, manager, updates=len(pending), skipped=skipped)
                _tally(
                    by_datasource,
                    dep.get("datasource", "?"),
                    updates=len(pending),
                    skipped=skipped,
                )
                updates.extend(
                    PendingUpdate(
                        manager=manager,
                        package_file=package_file,
                        dep_name=dep.get("depName", "?"),
                        current_value=dep.get("currentValue", "?"),
                        new_value=upd.get("newValue", "?"),
                    )
                    for upd in pending
                )
    problems = [
        str(p.get("msg", p))
        for p in (repo.get("problems") or [])
        if isinstance(p, dict)
    ]
    return DryRunResult(
        total_deps=total,
        updates=updates,
        problems=problems,
        complete=complete,
        managers=_stats(by_manager),
        datasources=_stats(by_datasource),
    )


def render_report(result: DryRunResult) -> str:
    """Render the dry-run outcome as a readable report."""
    lines = ["Renovate dry-run (platform=local, lookup) — no PRs opened", ""]
    if result.complete:
        lines.append(
            f"Scanned {result.total_deps} deps; {len(result.updates)} would be updated."
        )
    else:
        # Never print a bare total for an untokened run. Renovate skips every
        # github-datasource dep without GITHUB_COM_TOKEN and says so only in a
        # warning, so the count reads as authoritative when it is a floor —
        # measured 8 vs 33 on this repo. Lead with that, do not bury it.
        lines.append(
            f"!! INCOMPLETE — no github.com token found (looked for "
            f"{', '.join(_TOKEN_ENV_VARS)})."
        )
        lines.append(
            "   Renovate SKIPPED every github-datasource dep, so this is a "
            "FLOOR, not a total."
        )
        lines.append(
            "   Export GITHUB_COM_TOKEN (read-only is enough) for the real "
            "number. See docs.renovatebot.com/getting-started/running/"
            "#githubcom-token-for-changelogs-and-tools"
        )
        lines.append("")
        lines.append(
            f"Scanned {result.total_deps} deps; "
            f"at least {len(result.updates)} would be updated."
        )
    # Print the extraction tallies BEFORE the pending list: "which managers
    # matched, and how much" is the question you cannot answer from the
    # pending list, and a manager missing from this block extracted nothing.
    if result.managers:
        lines.append("")
        lines.append("Extracted by manager (absent == matched no files):")
        lines.extend(g.render() for g in result.managers)
    if result.datasources:
        lines.append("")
        lines.append("Looked up by datasource:")
        lines.extend(g.render() for g in result.datasources)
    if result.updates:
        lines.append("")
        lines.extend(u.render() for u in result.updates)
    if result.problems:
        lines.append("")
        lines.append(f"Problems reported ({len(result.problems)}):")
        lines.extend(f"  ! {p}" for p in result.problems)
    return "\n".join(lines)


def decide_exit_code(result: DryRunResult, *, check: bool) -> int:
    """Decide the process exit code for a completed dry-run.

    A bare run is a pure diagnostic and always succeeds: "Renovate would bump
    8 things" is the answer, not a failure. ``--check`` is the opt-in gate that
    turns pending updates into rc=1, mirroring ``mise run sync -- --check``
    ("dry-run staleness report (rc 1 if stale)") so the flag means the same
    thing across this repo's tasks.

    Args:
        result: the parsed dry-run outcome.
        check: True when the caller passed ``--check``.

    Returns:
        0, or 1 under ``--check`` when any update is pending.
    """
    if check and result.updates:
        return 1
    return 0


def renovate_dryrun_main(*, json_output: bool = False, check: bool = False) -> int:
    """Entry point for ``dotfiles-setup renovate-dryrun``."""
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "renovate-report.json"
        proc = run_renovate(report_path)
        if proc.returncode != 0 or not report_path.is_file():
            sys.stderr.write(proc.stderr or proc.stdout)
            # These two failures read identically until you say which is which,
            # and the difference decides where to look next: a report ON DISK
            # means extraction worked and the exit code is the complaint (an
            # unsupported node does exactly this), while no report means the
            # run died before writing one. Sending a reader to hunt for a file
            # that is sitting on disk is the bug this message had (#299).
            sys.stderr.write(
                f"\nrenovate exited {proc.returncode} but DID write its report "
                f"({report_path}) — extraction ran; the exit code is the "
                f"complaint. Re-read the errors above.\n"
                if report_path.is_file()
                else f"\nrenovate exited {proc.returncode} and produced no "
                f"report at {report_path}.\n"
            )
            return 1
        result = parse_report(
            report_path.read_text(), complete=resolve_github_token() is not None
        )

    if json_output:
        sys.stdout.write(json.dumps(asdict(result), indent=2) + "\n")
    else:
        sys.stdout.write(render_report(result) + "\n")
    return decide_exit_code(result, check=check)
