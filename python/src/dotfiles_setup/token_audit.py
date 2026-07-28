"""Contract-token uniqueness: a token that matches twice can be satisfied twice.

## Why this exists (#394, 2026-07-27)

The #394 sweep anchored 164 enforcement-seam tokens so a prefix-preserving
rename could not hide inside them, then proved the three holes that were live
by deleting the real wiring line and leaving the swallower standing. **Anchoring
fixed none of them:**

| token | line deleted | what kept the contract green |
|---|---|---|
| `permissionDecision` | the deny-emit | the TEST FILE's assertion (union) |
| `selfcheck` | the subparser registration | the `elif command ==` dispatch branch |
| `--output` | `command_audit_parser`'s flag | `memory_index_parser`'s own `--output` |

Every one is the same shape: the token matched **somewhere other than the site
it meant**. A word-boundary matcher — #394's step 4, and the obvious next move —
would have caught none of them, which is why the audit recommended this instead.

The rule is cheap to state and mechanical to check: **a `per_path_tokens` entry
should match its target file exactly once.** One match cannot be satisfied by a
stand-in. Where the multiplicity is genuine — a lockfile section repeated per
package, a doc that naturally names a task several times, a test fixture reused
across cases — it is recorded in :data:`AMBIGUITY_ALLOWED` with a reason, and a
NEW ambiguity fails.

Same shape as :mod:`dotfiles_setup.bash_budget`: an explicit map with
justifications, where a stale entry fails too, so the map cannot rot.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from dotfiles_setup import verify

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

MANIFEST = "python/verification/suites.toml"

# (suite, path, token) -> why matching more than once is correct here.
# Measured 2026-07-27: 25 entries were ambiguous; 7 were real defects of the
# `selfcheck` shape and were fixed by binding the unique site instead. These 18
# are the genuine remainder.
AMBIGUITY_ALLOWED: dict[tuple[str, str, str], str] = {
    (
        "build.locked-install-with-conda-sha",
        ".devcontainer/mise-system.lock",
        "[conda-packages.linux-x64",
    ): "a lockfile section header, once per package — multiplicity IS the assertion",
    (
        "build.locked-install-with-conda-sha",
        ".devcontainer/Dockerfile",
        "mise install --system --locked",
    ): "one install per build stage; every stage must carry --locked",
    (
        "eval.tier1-runner-wiring",
        "python/src/dotfiles_setup/eval_cases.py",
        "control=",
    ): "one per eval case — every case declaring a control arm is the point",
    (
        "eval.gate-reports-status",
        "python/src/dotfiles_setup/pr.py",
        "gh pr view rc={view.returncode}",
    ): "two real call sites, both of which must report the rc",
    (
        "workflow.adr-0001-enforcement",
        "tests/test_workflow_hooks.py",
        "HK_SKIP_HOOKS: pre-commit",
    ): "a test fixture reused across cases",
    (
        "workflow.adr-0001-enforcement",
        "tests/test_workflow_hooks.py",
        "workflow_hooks.job_writes_to_git(",
    ): "the function under test, called from several cases",
    (
        "workflow.apt-pins-enforcement",
        "tests/test_pr.py",
        'verify-apt-pins"',
    ): "the gate name asserted from several test cases",
    (
        "workflow.automerge-wiring",
        "python/src/dotfiles_setup/hook_guard.py",
        "mise run automerge -- <PR#>",
    ): "both the automerge rule and the generic merge rule name the verb (#369)",
    (
        "workflow.md-budget-enforcement",
        ".claude/rules/md-size-budgets.md",
        "Windsurf",
    ): "prose: the vendor whose limit the rule documents, named throughout",
    (
        "workflow.md-budget-enforcement",
        ".claude/rules/md-size-budgets.md",
        "SKILL.md",
    ): "prose: a load class the rule discusses in several places",
    (
        "workflow.command-audit-wiring",
        ".claude/rules/mise-tasks-only.md",
        "mise run command-audit`",
    ): "prose: a rule doc naturally names its task more than once",
    (
        "workflow.command-audit-wiring",
        ".claude/rules/mise-tasks-only.md",
        "SessionEnd`",
    ): "prose: the hook event, named where it is chosen and where it is justified",
    (
        "workflow.memory-index-wiring",
        ".claude/skills/memory-index-curation/SKILL.md",
        "mise run memory-index`",
    ): "prose: a skill naturally names its task more than once",
    (
        "workflow.memory-index-wiring",
        ".claude/skills/memory-index-curation/SKILL.md",
        "THEN shorten",
    ): "prose: the ordering rule, stated and then restated as the procedure",
    (
        "workflow.ship-land-wiring",
        ".claude/skills/pr-workflow/SKILL.md",
        "mise run ship`",
    ): "prose: the skill's own subject",
    (
        "workflow.ship-land-wiring",
        ".claude/skills/pr-workflow/SKILL.md",
        "mise run land`",
    ): "prose: the skill's own subject",
    (
        "workflow.sync-wiring",
        ".claude/skills/devcontainer-sync/SKILL.md",
        "mise run sync`",
    ): "prose: the skill's own subject",
    (
        "workflow.tool-currency-wiring",
        ".github/workflows/refresh.yml",
        "Tool currency report (daily)",
    ): "the job step name and the issue title it upserts",
}


@dataclass(frozen=True)
class Ambiguity:
    """A per-path token that does not match its file exactly once."""

    suite: str
    path: str
    token: str
    count: int

    @property
    def key(self) -> tuple[str, str, str]:
        """The allowlist key: suite, path, token."""
        return (self.suite, self.path, self.token)

    def render(self) -> str:
        """One line naming the suite, the file, the token and its match count."""
        return f"{self.suite} [{self.path}] {self.token!r} matches {self.count}x"


def find_ambiguous(root: Path) -> list[Ambiguity]:
    """Every per-path token that matches its target file other than once."""
    suites = verify.load_manifest(root / MANIFEST)
    found: list[Ambiguity] = []
    for suite in suites:
        for raw, tokens in suite.get("per_path_tokens", {}).items():
            target = root / raw
            text = target.read_text() if target.exists() else ""
            for token in tokens:
                count = text.count(token)
                if count != 1:
                    found.append(Ambiguity(suite["name"], raw, token, count))
    return found


def find_violations(root: Path) -> list[str]:
    """New ambiguity, plus allowlist entries that have stopped being true."""
    ambiguous = find_ambiguous(root)
    seen = {a.key for a in ambiguous}

    problems = [
        f"{a.render()} — not in AMBIGUITY_ALLOWED. Bind the ONE site that means "
        f"it (see #394), or add an entry with a reason."
        for a in ambiguous
        if a.key not in AMBIGUITY_ALLOWED
    ]
    problems += [
        f"{suite} [{path}] {token!r} is allowlisted but now matches exactly "
        f"once (or is gone) — drop the entry."
        for (suite, path, token) in AMBIGUITY_ALLOWED
        if (suite, path, token) not in seen
    ]
    return sorted(problems)


def token_audit_main(root: Path) -> int:
    """CLI entrypoint: report every ambiguous-binding problem; 1 if any."""
    problems = find_violations(root)
    if not problems:
        return 0
    for problem in problems:
        logger.error("%s", problem)
    logger.error(
        "%d contract-token binding problem(s). A token matching more than once "
        "can be satisfied by a stand-in — that is how a deleted registration "
        "stayed green (#394).",
        len(problems),
    )
    return 1
