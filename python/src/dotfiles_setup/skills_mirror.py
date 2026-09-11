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
`CLAUDE.md`'s relationship to `AGENTS.md` — a concept with no Codex-side
counterpart, since there is no general `CLAUDE.md` rule to have rewritten it
in the first place (see RESPEC 2 below). `PER_FILE` carries exactly these,
each commented with why the general rule is wrong for that spot.

## Why there is no `CLAUDE.md` -> `AGENTS.md` rule ("RESPEC 2")

A `("CLAUDE.md", "AGENTS.md")` rule was tried and measured against every
skill it would fire on: `graphify-skill-install` (2 occurrences, both real
third-party-tool facts needing reversion), `memory-index-curation` (3
occurrences, same), `session-handoff` (2 occurrences, 1 reworded + 1 deleted
outright — the concept doesn't exist on the Codex side), and `mcp2cli` (1
occurrence, `~/CLAUDE.md`, with no established Codex-side equivalent — see
below). All 8 needed hand intervention; none were correctly, mechanically
converted. A rule wrong every time it fires, propped up entirely by
exceptions, is not a rule — RULES has no `CLAUDE.md` entry, and every
citation of it survives untouched unless a `PER_FILE` entry says otherwise.

`mcp2cli`'s `~/CLAUDE.md` (Ray's personal, user-global Claude Code memory
file, where these mcp2cli shorthand aliases happen to be documented) has no
`PER_FILE` entry either. Codex's own docs name an analogous *mechanism* —
`$CODEX_HOME/AGENTS.md` (default `~/.codex/AGENTS.md`) is its "global scope"
instructions file — but on this machine that file is empty: the aliases
this sentence describes are not actually documented there. Asserting
`~/.codex/AGENTS.md` would be a confident wrong citation (a reader would
find nothing); leaving `~/CLAUDE.md` untouched is an honest one.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# `oh-my-claudecode` (the corruption this module's docstring calls
# `oh-my-Codex:sciomc`) and `code.claude.com` (a real external domain, cited by
# memory-index-curation, the old mirror had corrupted to the nonexistent
# `code.Codex.com`) were once run through a masking pass so no RULES rewrite
# could touch them. That masking pass was DELETED (cold review F2): every rule
# in RULES matches "Claude" (capital C), "claude mcp", or "claude code" (with a
# space) — none of them ever matches either literal's lowercase, unspaced
# "claude" — so the mask protected nothing; applying RULES alone to either
# literal already leaves it unchanged. `test_render_leaves_protected_literals_
# intact` is the real invariant now: it asserts the outcome directly, and it
# FAILS the moment anyone adds a lowercase or case-insensitive `claude` rule,
# which a masking pass that runs regardless of RULES' contents never could.

# Ordered literal rewrites, longest source first where they overlap.
#
# `.claude/skills/` -> `.agents/skills/` is the ONLY path prefix rewritten:
# it is the mirror's own real location. `.claude/rules/`, `.claude/agents/`,
# `.claude/projects/` and bare `~/.claude` are deliberately ABSENT from this
# list — none of them has a per-platform copy, so the correct citation is the
# single real path, unchanged, for either harness. See the module docstring
# for the evidence (session 2026-09-10, "RESPEC 1").
#
# There is deliberately NO `CLAUDE.md` -> `AGENTS.md` rule (RESPEC 2). It was
# tried and measured: of the 8 places `CLAUDE.md` appears across non-EXEMPT
# skills, 7 needed a `PER_FILE` reversion or deletion and the 8th
# (`mcp2cli`'s `~/CLAUDE.md`) had no safe rewrite target either — see that
# skill's absence from `PER_FILE` below. A rule wrong 7 times out of 8,
# propped up entirely by exceptions, is not a rule; deleting it and leaving
# every citation of `CLAUDE.md` untouched is what the evidence supports.
RULES: tuple[tuple[str, str], ...] = (
    (".claude/skills/", ".agents/skills/"),
    ("Claude Code", "Codex"),
    ("Claude", "Codex"),
    # Lowercase: the real binary is `codex mcp`, not `Codex mcp` (verified:
    # `codex mcp --help` prints "Manage external MCP servers for Codex").
    # Capitalizing the replacement was cold-review finding F5 — it emitted a
    # command that does not exist.
    ("claude mcp", "codex mcp"),
    # A lowercase YAML frontmatter search-trigger variant (verified: exactly
    # one file, one occurrence, `tmux-extended-keys`), folded into RULES
    # rather than kept as a `PER_FILE` exception — a rule generalizes to the
    # next occurrence of this case variant; an exception would not.
    ("claude code", "Codex"),
)

# Skill name -> extra rewrites applied AFTER RULES, for genuinely
# non-mechanical differences. Each entry is commented with why the general
# RULES are wrong for that specific spot.
PER_FILE: dict[str, tuple[tuple[str, str], ...]] = {
    # No `adversarial-review` entry (cold-review F1): its `session-handoff`
    # mention is not a citation of which skill a Codex reader should invoke —
    # it names `session-handoff`'s audit step as the thing that makes a
    # SIBLING rule (`agent-report-persistence.md` rule 5) enforced. Rewriting
    # it to `clear-prep` asserts a false claim about `agent-report-
    # persistence.md`, which never mentions `clear-prep`. Contrast
    # `PER_FILE["handoff"]` below, where the name IS the skill to invoke.
    #
    # The mirror cites `clear-prep` where the source cites `session-handoff`,
    # because `clear-prep` (CODEX_ONLY) is the Codex-side equivalent of the
    # same-machine `/clear` handoff skill.
    "handoff": (("session-handoff", "clear-prep"),),
    # The source names `CLAUDE.md`'s relationship to `AGENTS.md`. With no
    # general `CLAUDE.md` rule (RESPEC 2), the source's literal `CLAUDE.md`
    # text survives RULES untouched — these two entries match that literal
    # text directly, not a RULES-rewritten form. The first names a concept
    # (a `CLAUDE.md` stub importing `AGENTS.md`) that has no Codex-side
    # counterpart at all, so it is deleted rather than reworded. The second
    # inverts the sentence: on the Codex side there is no `CLAUDE.md` layer
    # to route through, so pointing at `AGENTS.md` directly is already
    # correct.
    "session-handoff": (
        (
            "(the `CLAUDE.md` is a thin `@AGENTS.md` stub — edit `AGENTS.md`). Root",
            "Root",
        ),
        (
            (
                "point to `CLAUDE.md` (which imports\n  `AGENTS.md`), never reference "
                "`AGENTS.md` directly\n  (`feedback_refer_to_claude_md_not_agents_md`)."
            ),
            (
                "point to `AGENTS.md` directly — there is no `CLAUDE.md` layer\n"
                "  to route through on this side "
                "(`feedback_refer_to_claude_md_not_agents_md`\n"
                "  describes the `.claude`-side convention this inverts)."
            ),
        ),
    ),
    # This skill documents what EACH NAMED PLATFORM's installer actually
    # does (`claude`, `agents`, `codex`, `gemini` are all literal CLI
    # argument values, not citations of this doc corpus). A blind rewrite
    # asserts things that are false about the other platform: that the
    # pinned bundle refresh target is `.agents/skills/graphify/` (it is
    # `.claude/skills/graphify/` for the `claude` platform arg), and that
    # Codex — not Claude Code — has the PreToolUse redirect hook. Revert
    # each to the source's literal, platform-accurate wording. (Its two
    # `CLAUDE.md` occurrences need no entry here at all — RESPEC 2 dropped
    # the general `CLAUDE.md` rule, so that literal text now survives
    # untouched.)
    "graphify-skill-install": (
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
    # No `memory-index-curation` entry: its three `CLAUDE.md` occurrences
    # (a literal filename searched for by `find -name "CLAUDE.md"`, and the
    # `@path`-is-a-CLAUDE.md-loader claim) needed a hand reversion only
    # because the old general `CLAUDE.md` rule rewrote them wrong. RESPEC 2
    # dropped that rule, so the source's literal `CLAUDE.md` text — already
    # correct, since both are real third-party-tool facts, not citations of
    # this doc corpus — now survives untouched.
    #
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
    # No `tmux-extended-keys` entry (RESPEC 2): its lowercase
    # `"claude code newline tmux"` frontmatter trigger is now handled by
    # RULES' `("claude code", "Codex")` entry, promoted from a `PER_FILE`
    # exception because a rule generalizes to the next occurrence of this
    # case variant and an exception would not.
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

    `source_text` is a `.claude/skills/<skill>/SKILL.md` body. Order: apply
    RULES in order, then PER_FILE[skill] (each of which is expected to match
    exactly once; a zero-count PER_FILE pattern usually means the source
    moved and the override needs re-deriving, not widening — enforced by
    `find_stale_per_file()`).

    `render` is a fixed point on the real skill corpus: `render(render(text,
    skill), skill) == render(text, skill)`. A `PER_FILE` replacement that
    reintroduces a bare `Claude`/`Claude Code`/`claude mcp`/`claude code`
    literal (as opposed to `.claude`, which no RULES entry matches) breaks
    this — a second render pass would rewrite what the first one just wrote.
    `session-handoff`'s `.claude`-side wording is exactly this fix.
    """
    text = source_text
    for old, new in RULES:
        text = text.replace(old, new)
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


def reference_paths(root: Path) -> list[tuple[Path, Path]]:
    """Every managed `(source, destination)` reference-file path pair.

    Walks `.claude/skills/<name>/references/**` for every non-`EXEMPT`
    skill and mirrors each file to
    `.agents/skills/<name>/references/**`, preserving any nested structure
    under `references/`. Unlike `mirror_paths()`'s `SKILL.md` pairs, these
    are copied byte-for-byte with no `RULES` applied — a reference file can
    cite a literal CLI flag (`context7-cli/references/setup.md`'s
    `--claude` flag, which is an argument to a real command, not a citation
    of this doc corpus) or a path that a rewrite would silently break.
    Covering these files without rewriting them is what stops them
    drifting the way hand-maintained `SKILL.md` mirrors did (team-lead
    follow-up, session 2026-09-10).

    `graphify/references/**` exists only on the `.claude` side (`graphify`
    is `EXEMPT`) — the generator must not create a mirror for it.
    """
    claude_dir = root / ".claude" / "skills"
    agents_dir = root / ".agents" / "skills"
    pairs: list[tuple[Path, Path]] = []
    if not claude_dir.is_dir():
        return pairs
    for skill_dir in sorted(claude_dir.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name in EXEMPT:
            continue
        refs_dir = skill_dir / "references"
        if not refs_dir.is_dir():
            continue
        for source in sorted(p for p in refs_dir.rglob("*") if p.is_file()):
            relative = source.relative_to(skill_dir)
            pairs.append((source, agents_dir / skill_dir.name / relative))
    return pairs


def find_drift(root: Path) -> list[str]:
    """Skill names whose committed `.agents` copy differs from the generator.

    Sorted. Covers `SKILL.md` (compared against `render()`), every
    `references/**` file (compared byte-for-byte via `reference_paths()`),
    and — since cold-review F6 — every UNMANAGED `.agents/skills/<name>/
    SKILL.md`: a directory with no `.claude/skills/<name>` source, not
    `EXEMPT`, and not `CODEX_ONLY`. Before this, a ghost skill dropped
    directly into `.agents/skills/` was invisible: `mirror_paths()` only
    walks `.claude/skills/`, so nothing ever compared it to anything and it
    could carry stale or fabricated instructions forever. A missing
    `.agents` counterpart for a MANAGED skill still counts as drift too (the
    file has never been mirrored).
    """
    drifted: set[str] = set()
    for source, destination in mirror_paths(root):
        rendered = render(source.read_text(encoding="utf-8"), source.parent.name)
        if (
            not destination.is_file()
            or destination.read_text(encoding="utf-8") != rendered
        ):
            drifted.add(source.parent.name)
    claude_skills_dir = root / ".claude" / "skills"
    for source, destination in reference_paths(root):
        skill_name = source.relative_to(claude_skills_dir).parts[0]
        if not destination.is_file() or destination.read_bytes() != source.read_bytes():
            drifted.add(skill_name)
    managed_names = {source.parent.name for source, _ in mirror_paths(root)}
    agents_skills_dir = root / ".agents" / "skills"
    if agents_skills_dir.is_dir():
        for skill_dir in sorted(agents_skills_dir.iterdir()):
            name = skill_dir.name
            if (
                not skill_dir.is_dir()
                or name in managed_names
                or name in EXEMPT
                or name in CODEX_ONLY
            ):
                continue
            if (skill_dir / "SKILL.md").is_file():
                drifted.add(name)
    return sorted(drifted)


def write_mirror(root: Path) -> list[str]:
    """Write every drifted mirror file to match the generator.

    Covers both `SKILL.md` (via `render()`) and every `references/**` file
    (byte-for-byte via `reference_paths()`). Creates parent directories as
    needed. Returns the sorted skill names actually rewritten (skills
    already matching are left untouched, so a run with nothing to do
    touches no mtimes).
    """
    written: set[str] = set()
    for source, destination in mirror_paths(root):
        rendered = render(source.read_text(encoding="utf-8"), source.parent.name)
        if (
            destination.is_file()
            and destination.read_text(encoding="utf-8") == rendered
        ):
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
        written.add(source.parent.name)
    claude_skills_dir = root / ".claude" / "skills"
    for source, destination in reference_paths(root):
        skill_name = source.relative_to(claude_skills_dir).parts[0]
        content = source.read_bytes()
        if destination.is_file() and destination.read_bytes() == content:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        written.add(skill_name)
    return sorted(written)


def find_stale_per_file(root: Path) -> list[str]:
    """Skill names whose `PER_FILE` override no longer matches its source.

    Sorted. Applies `RULES` to the live `.claude/skills/<skill>/SKILL.md`
    body (the same starting point `render()` hands to `PER_FILE`), then
    replays that skill's `PER_FILE` rewrites one at a time in order,
    stopping and reporting the skill the moment a pattern's count is zero.
    A zero-count pattern usually means the source moved out from under the
    override and the override needs re-deriving, not widening — that is
    what `PER_FILE`'s own docstring says, but until cold-review F8 nothing
    outside `pytest` ever checked it: `hk.pkl` has no `test` step, so a
    silently-stale override could ship through `mise run lint` and
    pre-commit untouched. Folding this into `find_stale_per_file` (called
    from `skills_mirror_main`'s `--check` path) is what makes
    `skills_mirror_parity` — the hk step wrapping `--check` — the enforcing
    site instead of only the test suite.

    A skill named in `PER_FILE` with no `.claude/skills/<skill>/SKILL.md`
    (there are none today) is skipped, matching how `mirror_paths()`
    already treats a missing source as absence rather than an error.
    """
    stale: set[str] = set()
    claude_dir = root / ".claude" / "skills"
    for skill, rewrites in PER_FILE.items():
        source_path = claude_dir / skill / "SKILL.md"
        if not source_path.is_file():
            continue
        text = source_path.read_text(encoding="utf-8")
        for old, new in RULES:
            text = text.replace(old, new)
        for old, new in rewrites:
            if old not in text:
                stale.add(skill)
                break
            text = text.replace(old, new)
    return sorted(stale)


def skills_mirror_main(repo_root: Path, *, check: bool = False) -> int:
    """CLI entry for `dotfiles-setup skills-mirror`.

    Bare form WRITES and reports what changed; `--check` is read-only and
    exits 1 naming every drifted skill and every stale `PER_FILE` override.
    """
    if check:
        drifted = find_drift(repo_root)
        stale = find_stale_per_file(repo_root)
        if drifted or stale:
            for name in drifted:
                logger.error("skills-mirror DRIFT: %s", name)
            for name in stale:
                logger.error("skills-mirror STALE PER_FILE: %s", name)
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
