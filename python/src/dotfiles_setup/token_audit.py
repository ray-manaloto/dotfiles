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

## The blind spot this gate had, and the second rule (#397, 2026-07-28)

:func:`find_ambiguous` reads **only** ``per_path_tokens``. A bare ``tokens``
list was therefore invisible to it — and the ``build.*`` / ``ci.*`` / ``arch.*``
tail was 105 bare tokens, none of them audited. Converting them cost nothing
semantically: ``_resolve_paths`` does no globbing, so a bare list over ONE path
is identical in effect to ``per_path_tokens`` for that path, and 51 of the
tail's 54 ``require_tokens`` suites named exactly one path.

The gate then had plenty to say. **33 of the 39 ambiguities it surfaced were
LIVE holes** — delete the real wiring line, leave the other match standing, and
the contract stays green. Proven both directions against the real engine on a
temp tree (old token + mutated tree PASSES; the rebound token FAILS naming
itself), with a control arm over the 103 already-unique tail tokens, every one
of which correctly reported *not* a hole.

A stand-in shape appeared that #394's three did not have: **the file's own
comment**. Counted, not eyeballed — for 11 of the 33 the sole surviving match
was a comment line, for 10 it was a comment plus code, and for 12 code alone.
A Dockerfile explains its own ``ARG`` above it, a workflow documents its own
job, devcontainer.json narrates every mount in a header block; deleting the
wiring leaves the narration, and the narration satisfies the token. (PR #403's
commit message called this "overwhelmingly" the case before anyone counted. It
is a third. See the spec's 2026-07-28 revision.)

Hence :func:`find_unaudited`: a ``require_tokens`` suite naming exactly one path
must bind through ``per_path_tokens``, never a bare ``tokens`` list. That form
is convertible with zero semantic change, so there is no reason to write it —
and writing it silently exempts the suite from the rule above.
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
#
# #397 (2026-07-28) brought the `build.*`/`ci.*`/`arch.*` tail under this gate
# by converting its single-path bare `tokens` to `per_path_tokens`. That
# surfaced 39 more ambiguities; 33 were the `selfcheck` shape and were rebound
# (in 11 of those, the sole stand-in was a COMMENT). The 8 below are genuine.
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
    # ---- #397: the build.* / ci.* / arch.* tail ----------------------------
    (
        "build.amd64-platform-wired-mise",
        "mise.toml",
        'DOCKER_DEFAULT_PLATFORM = "linux/amd64/v2"',
    ): "one per lifecycle task (up / dev-rebuild / verify-image) — PR #86's "
    "split-brain WAS one task missing it, so multiplicity IS the assertion",
    (
        "build.clang-p2996-ref-in-bake",
        "docker-bake.hcl",
        "CLANG_P2996_REF = CLANG_P2996_REF",
    ): "one per target whose cache the ref must invalidate (dev, p2996-cache)",
    (
        "ci.sbom-attestation",
        "docker-bake.hcl",
        "type=sbom",
    ): "one per published target (dev / base / p2996-cache); all three attest "
    "identically by design (#160 T7)",
    (
        "ci.provenance-attestation",
        "docker-bake.hcl",
        "type=provenance,mode=max",
    ): "one per published target (dev / base / p2996-cache) — #160 T7",
    (
        "ci.p2996-ref-dispatch-wired",
        ".github/workflows/build-publish.yml",
        "inputs.p2996_ref != ''",
    ): "the 'Resolve p2996 ref override' step repeats in p2996-prep / dev-prep "
    "/ build so all three track the SAME upstream SHA — multiplicity IS the "
    "assertion",
    (
        "ci.p2996-ref-dispatch-wired",
        ".github/workflows/build-publish.yml",
        "CLANG_P2996_REF=${P2996_REF}",
    ): "the same three resolve steps as the sibling token above",
    (
        "ci.p2996-prep-job-exists",
        ".github/workflows/build-publish.yml",
        "docker manifest inspect",
    ): "the registry cache-probe idiom is textually IDENTICAL in base-prep / "
    "p2996-prep / dev-prep, so no substring can discriminate them; the job "
    "identity is carried by the sibling `p2996-prep:` token",
    (
        "ci.dev-prep-gate-exists",
        ".github/workflows/build-publish.yml",
        "hash=$(uv run --project python dotfiles-setup dev-hash)",
    ): "twice by design — dev-prep computes the probe hash, dev-tag recomputes "
    "it to stamp the validated marker; both clauses are the contract",
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


def find_unaudited(root: Path) -> list[str]:
    """Single-path ``require_tokens`` suites that bind through a bare list.

    Such a token is invisible to :func:`find_ambiguous`, and the bare form buys
    nothing: with one path, the union IS that path. A suite naming SEVERAL
    paths is a different question (#299's union) and is left alone.
    """
    return [
        f"{suite['name']} binds {len(suite['tokens'])} token(s) through a bare "
        f"`tokens` list over the single path {suite['paths'][0]!r} — that form "
        f"is invisible to the uniqueness audit and means exactly the same "
        f"thing as `per_path_tokens`. Move them (#397)."
        for suite in verify.load_manifest(root / MANIFEST)
        if suite.get("handler") == "require_tokens"
        and suite.get("tokens")
        and len(suite.get("paths", [])) == 1
    ]


def find_violations(root: Path) -> list[str]:
    """New ambiguity, unaudited bare tokens, and allowlist entries gone stale."""
    ambiguous = find_ambiguous(root)
    seen = {a.key for a in ambiguous}

    problems = find_unaudited(root)
    problems += [
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
