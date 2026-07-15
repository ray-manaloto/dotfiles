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
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
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
# GITHUB_MCP_PAT is deliberately absent — it is scoped to the MCP server.
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
class DryRunResult:
    """The outcome of one local Renovate dry-run."""

    total_deps: int
    updates: list[PendingUpdate]
    problems: list[str]
    # False when no github.com token was available, i.e. every github-datasource
    # dep was skipped and `updates` is a FLOOR rather than a total.
    complete: bool = True


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


def parse_report(raw: str, *, complete: bool = True) -> DryRunResult:
    """Extract the pending updates from renovate's native JSON report."""
    report = json.loads(raw)
    repo = report.get("repositories", {}).get("local", {})
    updates: list[PendingUpdate] = []
    total = 0
    for manager, files in (repo.get("packageFiles") or {}).items():
        for entry in files:
            package_file = entry.get("packageFile", "?")
            for dep in entry.get("deps", []):
                total += 1
                updates.extend(
                    PendingUpdate(
                        manager=manager,
                        package_file=package_file,
                        dep_name=dep.get("depName", "?"),
                        current_value=dep.get("currentValue", "?"),
                        new_value=upd.get("newValue", "?"),
                    )
                    for upd in dep.get("updates") or []
                )
    problems = [
        str(p.get("msg", p))
        for p in (repo.get("problems") or [])
        if isinstance(p, dict)
    ]
    return DryRunResult(
        total_deps=total, updates=updates, problems=problems, complete=complete
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
            sys.stderr.write(
                f"\nrenovate exited {proc.returncode} and produced no report.\n"
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
