# Copyright (c) 2026 Raymond Manaloto
"""Generate the `.agents/skills/**/SKILL.md` mirror from `.claude/skills/**`.

`.agents/skills/**/SKILL.md` is a Codex-facing rewrite of the Claude Code
skill corpus at `.claude/skills/**/SKILL.md`. No generator existed for it —
every reference to `.agents/skills` elsewhere in the repo (`*.py`/`*.pkl`/
`*.toml`) is a checker or a config, never a producer — so the tree was
maintained BY HAND, and it silently rotted: a fix landing in a `.claude`
skill left the Codex-facing copy telling a Codex lane the old thing
(`devcontainer-sync` never received PR #804's per-architecture
container-outdated behaviour), and two independent mechanical corruptions
became permanent (`oh-my-claudecode` rendered as `oh-my-Codex`, and a
sentence naming `CLAUDE.md` as a `@AGENTS.md` stub becoming
self-referential once `CLAUDE.md` itself got rewritten).

This module makes the mirror GENERATED: :func:`render` is the one
transformation function, :func:`find_drift`/`--check` is the CI/hk gate, and
:func:`write_mirror` is what a human runs to regenerate it.

## Why a blind `.claude/` -> `.codex/` substitution is wrong

The obvious design — rewrite every `.claude/` path prefix to its vendor
counterpart — was tried and independently re-verified as a real defect
(session 2026-09-10, "RESPEC 1"), not a style choice:

- `git ls-files` tracks the real directory as lowercase `.codex/`, never
  `.Codex/`. macOS's case-insensitive filesystem hid this for the entire
  hand-maintained mirror (`ls -d .Codex` "succeeds" there and proves
  nothing); a Codex lane on the Linux devcontainer this repo actually
  targets gets ENOENT on any literal `.Codex/...` path.
- `.codex/` does not mirror `.claude/`'s tree at all. It holds exactly five
  `codex-*.toml` agent files (a different name AND format than
  `.claude/agents/*.md`) plus `.codex/skills/graphify/` — nothing else.
  `.codex/rules/` has never existed in any commit. So a blind rewrite of
  `.claude/rules/foo.md` into `.codex/rules/foo.md`, or
  `.claude/agents/adversarial-critic.md` into
  `.codex/agents/adversarial-critic.md`, asserts a path that never existed.
- The mirror's own self-references are the clearest proof: the file at
  `.agents/skills/handoff/SKILL.md` is what a reader is looking at, yet the
  old mirror cited its sibling as `.Codex/skills/resume/SKILL.md` — a path
  that has never been tracked — when the real file sits at
  `.agents/skills/resume/SKILL.md`, right next to the file citing it.

So `RULES` rewrites `.claude/skills/` -> `.agents/skills/` (the mirror's own
real location) and leaves `.claude/rules/`, `.claude/agents/` and
`.claude/projects/` (and bare `~/.claude`) untouched — there is no
per-platform copy of any of those, so the real, single-sourced path is the
correct citation regardless of which lane is reading it.

## Why some files need `PER_FILE` corrections at all

A handful of skills discuss the CLAUDE/Codex distinction itself rather than
merely citing sibling files — `graphify-skill-install` documents what each
named platform's installer actually does (a blind rewrite would claim
Codex's own installer does something only Claude's does), `session-review`
audits transcripts from BOTH harnesses in the same sentence (rewriting
"Claude" there produces "Codex and Codex"), and `session-handoff` names
`CLAUDE.md`'s relationship to `AGENTS.md`, which a blind rewrite of
`CLAUDE.md` turns into a self-reference. `PER_FILE` carries exactly these,
each commented with why the general rule is wrong for that spot.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Literals masked out before RULES run and restored after, so no rewrite can
# ever touch a substring inside them. `oh-my-claudecode` is what makes the
# `oh-my-Codex:sciomc` corruption UNPRODUCIBLE (not merely repaired) — no rule
# in RULES touches lowercase "claude" at all, but a future rule addition could,
# and the mask means it never matters. `code.claude.com` is a real external
# domain (Anthropic's own hosted docs) cited by memory-index-curation; the old
# mirror had corrupted it to the nonexistent `code.Codex.com`.
PROTECTED: tuple[str, ...] = (
    "oh-my-claudecode",
    "code.claude.com",
)

# Ordered literal rewrites, longest source first where they overlap. Applied
# after PROTECTED literals are masked out.
#
# `.claude/skills/` -> `.agents/skills/` is the ONLY path prefix rewritten:
# it is the mirror's own real location. `.claude/rules/`, `.claude/agents/`,
# `.claude/projects/` and bare `~/.claude` are deliberately ABSENT from this
# list — none of them has a per-platform copy, so the correct citation is the
# single real path, unchanged, for either harness. See the module docstring
# for the evidence (session 2026-09-10, "RESPEC 1").
RULES: tuple[tuple[str, str], ...] = (
    (".claude/skills/", ".agents/skills/"),
    ("Claude Code", "Codex"),
    ("Claude", "Codex"),
    ("claude mcp", "Codex mcp"),
    ("CLAUDE.md", "AGENTS.md"),
)

# Skill name -> extra rewrites applied AFTER RULES, for genuinely
# non-mechanical differences. Each entry is commented with why the general
# RULES are wrong for that specific spot.
PER_FILE: dict[str, tuple[tuple[str, str], ...]] = {
    # The mirror cites `clear-prep` where the source cites `session-handoff`,
    # because `clear-prep` (CODEX_ONLY) is the Codex-side equivalent of the
    # same-machine `/clear` handoff skill.
    "adversarial-review": (("session-handoff", "clear-prep"),),
    "handoff": (("session-handoff", "clear-prep"),),
    # The source names `CLAUDE.md`'s relationship to `AGENTS.md`. A blind
    # CLAUDE.md->AGENTS.md rewrite turns both sentences self-referential
    # ("the AGENTS.md is a thin @AGENTS.md stub"; "point to AGENTS.md (which
    # imports AGENTS.md)"). Render correct prose instead.
    "session-handoff": (
        (
            "(the `AGENTS.md` is a thin `@AGENTS.md` stub — edit `AGENTS.md`). Root",
            "Root",
        ),
        (
            (
                "point to `AGENTS.md` (which imports\n  `AGENTS.md`), never reference "
                "`AGENTS.md` directly\n  (`feedback_refer_to_claude_md_not_agents_md`)."
            ),
            (
                "point to `AGENTS.md` directly — there is no `CLAUDE.md` layer\n"
                "  to route through on this side "
                "(`feedback_refer_to_claude_md_not_agents_md`\n"
                "  describes the Claude-side convention this inverts)."
            ),
        ),
    ),
    # This skill documents what EACH NAMED PLATFORM's installer actually
    # does (`claude`, `agents`, `codex`, `gemini` are all literal CLI
    # argument values, not citations of this doc corpus). A blind rewrite
    # asserts things that are false about the other platform: that a bare
    # install mutates `~/.codex` (it mutates `~/.claude`), that the pinned
    # bundle refresh target is `.agents/skills/graphify/` (it is
    # `.claude/skills/graphify/` for the `claude` platform arg), and that
    # Codex — not Claude Code — has the PreToolUse redirect hook. Revert
    # each to the source's literal, platform-accurate wording.
    "graphify-skill-install": (
        ("~/.claude/AGENTS.md`), and a", "~/.claude/CLAUDE.md`), and a"),
        ("`AGENTS.md`/`AGENTS.md` append", "`AGENTS.md`/`CLAUDE.md` append"),
        (
            "and `.agents/skills/graphify/` needs\n  refreshing to match.",
            "and `.claude/skills/graphify/` needs\n  refreshing to match.",
        ),
        (
            "-- claude   # refresh .agents/skills/graphify/",
            "-- claude   # refresh .claude/skills/graphify/",
        ),
        (
            "exist to prevent. Codex has a PreToolUse hook enforcing the",
            "exist to prevent. Claude Code has a PreToolUse hook enforcing the",
        ),
    ),
    # Both spots cite a REAL third-party tool behavior (searching for a file
    # literally named "CLAUDE.md", and the "@path" loader being specific to
    # CLAUDE.md) — not a citation of this doc corpus. Revert the false
    # "AGENTS.md-loader" / "find -name AGENTS.md" claims the blind rewrite
    # produces.
    "memory-index-curation": (
        (
            (
                "are all scoped to AGENTS.md **by their own `find -name "
                '"AGENTS.md"`**, and'
            ),
            (
                "are all scoped to CLAUDE.md **by their own `find -name "
                '"CLAUDE.md"`**, and'
            ),
        ),
        (
            (
                '**Do NOT "refactor" the index to `@import`.** `@path` is a '
                "AGENTS.md-loader\n  feature; the loader walks `AGENTS.md` (and its "
                "`.local` variant) up from cwd,"
            ),
            (
                '**Do NOT "refactor" the index to `@import`.** `@path` is a '
                "CLAUDE.md-loader\n  feature; the loader walks `CLAUDE.md` (and its "
                "`.local` variant) up from cwd,"
            ),
        ),
    ),
    # This skill audits transcripts from BOTH harnesses in the same
    # sentences ("reads both Claude and Codex...", "Claude roots are
    # selected independently"). A blind rewrite collapses the contrast into
    # "Codex and Codex" / drops the Claude side entirely. hk.pkl's
    # pre-existing `session_review_skill_parity` step already asserted this
    # file must be BYTE-IDENTICAL to its `.claude` source — these four
    # reversions are what keeps it that way under the general RULES.
    "session-review": (
        ("Review Codex and Codex requirements", "Review Claude and Codex requirements"),
        ("It reads both Codex and", "It reads both Claude and"),
        (
            "as an explicit selector. Codex roots are selected independently",
            "as an explicit selector. Claude roots are selected independently",
        ),
        (
            "`selected=0` and remains `INCOMPLETE`; Codex evidence cannot satisfy the",
            "`selected=0` and remains `INCOMPLETE`; Claude evidence cannot satisfy the",
        ),
    ),
    # A YAML frontmatter search-trigger string, lowercase by that list's own
    # convention — RULES' case-sensitive "Claude Code" -> "Codex" rule does
    # not match it. Capitalize "Codex" as a proper noun, matching how this
    # doc capitalizes it everywhere else post-rewrite.
    "tmux-extended-keys": (("claude code newline tmux", "Codex newline tmux"),),
}

# Skills the generator must NEVER write, and `find_drift` must NEVER report.
# `.agents/skills/graphify/SKILL.md` is a DELIBERATE hand-authored redirect
# stub (marked `DELIBERATE STUB` inside the file), not a rewritten copy —
# `hk.pkl`'s `graphify_skill_surface` step and `doctor.toml`'s `[graphify]`
# section both assert its shape independently of this generator.
EXEMPT: frozenset[str] = frozenset({"graphify"})

# Skills that live ONLY in `.agents/skills/` with no `.claude/skills/`
# counterpart. The generator neither writes nor deletes them — they simply
# never appear in `mirror_paths()`, since that walks `.claude/skills/`. Named
# here for documentation and so a test can assert they are never touched.
CODEX_ONLY: frozenset[str] = frozenset({"clear-prep", "codex-task-orchestration"})


def render(source_text: str, skill: str) -> str:
    """Render `source_text` as the Codex-facing mirror text for `skill`.

    `source_text` is a `.claude/skills/<skill>/SKILL.md` body. Order: mask
    PROTECTED literals -> apply RULES in order -> unmask -> apply
    PER_FILE[skill] (each of which is expected to match exactly once; a
    zero-count PER_FILE pattern usually means the source moved and the
    override needs re-deriving, not widening).
    """
    text = source_text
    placeholders: dict[str, str] = {}
    for index, literal in enumerate(PROTECTED):
        placeholder = f"\x00PROTECTED{index}\x00"
        placeholders[placeholder] = literal
        text = text.replace(literal, placeholder)
    for old, new in RULES:
        text = text.replace(old, new)
    for placeholder, literal in placeholders.items():
        text = text.replace(placeholder, literal)
    for old, new in PER_FILE.get(skill, ()):
        text = text.replace(old, new)
    return text


def mirror_paths(root: Path) -> list[tuple[Path, Path]]:
    """Every managed `(source, destination)` SKILL.md path pair.

    Each pair is
    `(.claude/skills/<name>/SKILL.md, .agents/skills/<name>/SKILL.md)`,
    skipping `EXEMPT` skills. A `.claude` skill directory without a
    `SKILL.md` (there are none today) is silently skipped rather than
    raising, matching how `find_drift`/`write_mirror` already treat a
    missing `.agents` counterpart as drift rather than an error.
    """
    claude_dir = root / ".claude" / "skills"
    agents_dir = root / ".agents" / "skills"
    pairs: list[tuple[Path, Path]] = []
    if not claude_dir.is_dir():
        return pairs
    for skill_dir in sorted(claude_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name in EXEMPT:
            continue
        source = skill_dir / "SKILL.md"
        if not source.is_file():
            continue
        destination = agents_dir / skill_dir.name / "SKILL.md"
        pairs.append((source, destination))
    return pairs


def find_drift(root: Path) -> list[str]:
    """Skill names whose committed `.agents` copy differs from `render()`.

    Sorted. Compared against the current `.claude` source; a missing
    `.agents` counterpart counts as drift (the skill has never been
    mirrored).
    """
    drifted: list[str] = []
    for source, destination in mirror_paths(root):
        rendered = render(source.read_text(encoding="utf-8"), source.parent.name)
        if (
            not destination.is_file()
            or destination.read_text(encoding="utf-8") != rendered
        ):
            drifted.append(source.parent.name)
    return sorted(drifted)


def write_mirror(root: Path) -> list[str]:
    """Write every drifted mirror file to match `render()`.

    Creates parent directories as needed. Returns the sorted names actually
    rewritten (skills already matching are left untouched, so a run with
    nothing to do touches no mtimes).
    """
    written: list[str] = []
    for source, destination in mirror_paths(root):
        rendered = render(source.read_text(encoding="utf-8"), source.parent.name)
        if (
            destination.is_file()
            and destination.read_text(encoding="utf-8") == rendered
        ):
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
        written.append(source.parent.name)
    return sorted(written)


def skills_mirror_main(repo_root: Path, *, check: bool = False) -> int:
    """CLI entry for `dotfiles-setup skills-mirror`.

    Bare form WRITES and reports what changed; `--check` is read-only and
    exits 1 naming every drifted skill.
    """
    if check:
        drifted = find_drift(repo_root)
        if drifted:
            for name in drifted:
                logger.error("skills-mirror DRIFT: %s", name)
            return 1
        logger.info("skills-mirror OK: .agents/skills matches the generator")
        return 0
    written = write_mirror(repo_root)
    if written:
        for name in written:
            logger.info("skills-mirror WROTE: %s", name)
    else:
        logger.info("skills-mirror OK: .agents/skills already matches the generator")
    return 0
