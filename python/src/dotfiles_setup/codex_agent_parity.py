# Copyright (c) 2026 Raymond Manaloto
"""Two-surface consistency gate for the hand-authored codex-backed agent lanes.

The four lanes added by #884 ship as a pair per agent: a Claude-side wrapper at
``.claude/agents/codex-<name>.md`` and the codex-side role definition at
``.codex/agents/codex-<name>.toml``. The two halves deliberately DIFFER in body
— the ``.md`` addresses a Claude Code subagent that shells out, the ``.toml``
addresses the codex role that does the reasoning — so byte-equality is the wrong
check. What must hold is the wiring: both halves exist, they agree on identity,
the codex half asks for the effort the lane exists to buy, and neither has been
overwritten with corrupted content.

Three failure modes, each measured rather than assumed:

1. **Corruption.** The Codex desktop app EXPORTS mirrors into ``.codex/agents/``
   with a blind ``claude`` -> ``Codex`` substitution. Measured 2026-08-31 on the
   exported mirrors: ``claude-code-expert.toml`` scored 5 and
   ``adversarial-critic.toml`` 2 on :data:`CORRUPTION_MARKERS`, while all seven
   hand-authored knowledge-base tomls scored 0 (control arm: the same probe
   found 6 correct ``Claude``/``.claude/`` references inside one of them, so it
   was capable of matching text there). The exported mirrors stay gitignored;
   this gate exists so that if that exporter ever reaches a TRACKED
   ``codex-*.toml``, the gate is loud rather than the corruption silent.

   Note what is NOT claimed: that the exporter enumerates ``.claude/agents/*.md``
   one-for-one. That mechanism was refuted — ``.claude/skills/`` holds 31
   directories against ``.agents/skills/``'s 3, and ``.agents/skills/`` holds
   ``codex-task-orchestration``, which has no ``.claude/skills/`` source. The
   exporter mirrors a SELECTED subset. So the risk is real but unproven, and the
   response is one cheap loud check, not machinery.

2. **A half went missing.** A ``.md`` with no ``.toml`` counterpart (or the
   reverse) is worse than absence, because the surviving half still loads and
   the harness appears to accept it — the same reasoning as the
   ``session_review_skill_parity`` hk step this one follows.

3. **Identity or effort drift.** A ``name`` that disagrees with its filename
   stem, or a ``model_reasoning_effort`` that is not ``"xhigh"``. Without the
   effort declaration codex resolves it from ``~/.codex/config.toml`` — a file
   this repo neither owns nor watches — and silently runs at ``medium``, which
   is the exact downgrade these lanes were created to close.

The logic lives here rather than in an inline-bash hk step, per
``.claude/rules/zero-bash-logic.md``; the ``codex_agent_parity`` hk step and the
``codex-agent-parity`` CLI subcommand are thin wrappers over
:func:`find_violations`.
"""

from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

logger = logging.getLogger(__name__)

CLAUDE_AGENT_DIR = ".claude/agents"
CODEX_AGENT_DIR = ".codex/agents"

# Only the hand-authored lanes are in scope. The Codex-app EXPORTED mirrors in
# the same directory carry no `codex-` prefix, stay gitignored, and are not ours
# to police — see the module docstring.
STEM_PREFIX = "codex-"

REQUIRED_EFFORT = "xhigh"

# The signature of the exporter's blind `claude` -> `Codex` substitution. These
# are strings that CANNOT occur in correct prose: the product is "Claude Code",
# the directory is ".claude/", and the command is "claude mcp add".
CORRUPTION_MARKERS: tuple[str, ...] = (
    "Codex Code",
    ".Codex/",
    "Codex mcp add",
)


@dataclass(frozen=True)
class ParityViolation:
    """One failure, with the path that carries it."""

    kind: str
    path: str
    detail: str


def _stems(directory: Path, suffix: str) -> set[str]:
    """Stems of in-scope agent files in ``directory``, or empty if it is absent."""
    if not directory.is_dir():
        return set()
    return {
        p.name[: -len(suffix)]
        for p in directory.iterdir()
        if p.is_file() and p.name.startswith(STEM_PREFIX) and p.name.endswith(suffix)
    }


def _pairing_violations(repo_root: Path) -> Iterator[ParityViolation]:
    """Yield a violation for every lane that is missing one of its two halves."""
    claude = _stems(repo_root / CLAUDE_AGENT_DIR, ".md")
    codex = _stems(repo_root / CODEX_AGENT_DIR, ".toml")

    if not claude and not codex:
        yield ParityViolation(
            kind="empty",
            path=CLAUDE_AGENT_DIR,
            detail=(
                f"no {STEM_PREFIX}*.md and no {STEM_PREFIX}*.toml found — the "
                "check cannot answer, so it fails loud rather than reporting a "
                "vacuous pass"
            ),
        )
        return

    for stem in sorted(claude - codex):
        yield ParityViolation(
            kind="unpaired",
            path=f"{CLAUDE_AGENT_DIR}/{stem}.md",
            detail=f"no counterpart at {CODEX_AGENT_DIR}/{stem}.toml",
        )
    for stem in sorted(codex - claude):
        yield ParityViolation(
            kind="unpaired",
            path=f"{CODEX_AGENT_DIR}/{stem}.toml",
            detail=f"no counterpart at {CLAUDE_AGENT_DIR}/{stem}.md",
        )


def _toml_violations(repo_root: Path) -> Iterator[ParityViolation]:
    """Yield corruption, identity and effort violations for each codex toml."""
    directory = repo_root / CODEX_AGENT_DIR
    for stem in sorted(_stems(directory, ".toml")):
        path = directory / f"{stem}.toml"
        rel = f"{CODEX_AGENT_DIR}/{stem}.toml"
        raw = path.read_text(encoding="utf-8")

        found = [m for m in CORRUPTION_MARKERS if m in raw]
        if found:
            yield ParityViolation(
                kind="corrupted",
                path=rel,
                detail=(
                    f"contains the Codex-exporter substitution signature "
                    f"{found!r} — a tracked hand-authored file has been "
                    "overwritten by the exporter; restore it from git"
                ),
            )

        try:
            data = tomllib.loads(raw)
        except tomllib.TOMLDecodeError as exc:
            yield ParityViolation(kind="unparsable", path=rel, detail=str(exc))
            continue

        name = data.get("name")
        if name != stem:
            yield ParityViolation(
                kind="name-mismatch",
                path=rel,
                detail=f"name is {name!r}, expected the filename stem {stem!r}",
            )

        effort = data.get("model_reasoning_effort")
        if effort != REQUIRED_EFFORT:
            yield ParityViolation(
                kind="effort",
                path=rel,
                detail=(
                    f"model_reasoning_effort is {effort!r}, expected "
                    f"{REQUIRED_EFFORT!r} — without it codex resolves the "
                    "effort from ~/.codex/config.toml and silently runs at "
                    "medium"
                ),
            )


def find_violations(repo_root: Path) -> list[ParityViolation]:
    """Every parity violation across the hand-authored codex agent lanes."""
    return [
        *_pairing_violations(repo_root),
        *_toml_violations(repo_root),
    ]


def codex_agent_parity_main(repo_root: Path) -> int:
    """CLI entry point: log every violation, return 1 if any, else 0."""
    violations = find_violations(repo_root)
    if violations:
        for v in violations:
            logger.error("codex-agent-parity %s: %s — %s", v.kind, v.path, v.detail)
        return 1

    paired = len(_stems(repo_root / CODEX_AGENT_DIR, ".toml"))
    logger.info(
        "codex-agent-parity OK: %d hand-authored lane(s) paired, named "
        "consistently, at %s effort, and free of the exporter signature",
        paired,
        REQUIRED_EFFORT,
    )
    return 0
