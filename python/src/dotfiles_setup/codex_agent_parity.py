# Copyright (c) 2026 Raymond Manaloto
"""Two-surface consistency gate for the hand-authored codex-backed agent lanes.

The four lanes added by #884 ship as a pair per agent: a Claude-side wrapper at
``.claude/agents/codex-<name>.md`` and the codex-side role definition at
``.codex/agents/codex-<name>.toml``. The two halves deliberately DIFFER in body
— the ``.md`` addresses a Claude Code subagent that shells out, the ``.toml``
addresses the codex role that does the reasoning — so byte-equality is the wrong
check. What must hold is the wiring: both halves exist, they agree on identity,
each asks for the model and effort the lane exists to buy, the ``.md`` still
forbids the failure that would look like success, and neither has been
overwritten by the exporter.

**Who consumes these files.** The Codex Desktop app reads and WRITES
``.codex/agents/`` — it produced the four non-``codex-``-prefixed mirrors there
in a single batch (identical ``18:52:09`` mtime). The ``codex exec`` CLI path the
``.md`` wrappers actually invoke does NOT read this directory; it is given the
prompt on stdin. So the tomls have a real consumer, and a real overwrite hazard,
even though nothing in the shell-out path loads them.

## Why the check is a SENTINEL, not a corruption sniff

The first version of this gate looked for the exporter's output strings
(``Codex Code``, ``.Codex/``, ``Codex mcp add``). That is
``probes-need-a-control-arm.md`` rule 9 — binding a check to text you do not
own — and it was already a no-op on live evidence. Measured 2026-08-31 across
the four exported mirrors (occurrence counts, not line counts):

===================  ===========  ==================  =========  ==========
marker               adversarial  claude-code-expert  staleness  dockerfile
===================  ===========  ==================  =========  ==========
``Codex Code``                 0                   0          0           0
``.Codex/``                    2                   6          0           0
``Codex mcp add``              0                   0          0           0
===================  ===========  ==================  =========  ==========

Two of the three could never fire, and ``staleness-auditor.toml`` is
unambiguously corrupted (``"does Codex Code do X"``, ``docs/Codex``) while
scoring **zero on all three**. The reason is sharper than "the phrasing drifted":
that file DOES contain ``Codex Code``, split across a line wrap — flattening
whitespace finds it, the raw scan does not. **Any multi-word content marker is
defeatable by reflow**, which is a second, permanent reason not to rely on one.

A positive test is no better: the obvious "a hand-authored file mentions
``claude``" rule fails too, because ``claude-code-expert.toml`` is an exported
mirror carrying 29 case-insensitive ``claude`` hits.

So the primary check is :data:`SENTINEL` — a line THIS repo writes into every
hand-authored toml. Its failure mode is "our file was replaced", which is the
thing we actually care about, and it holds no matter what the exporter emits on
any given day. The negative markers are kept as a secondary signal, broadened
with the two shapes measured above and matched against whitespace-flattened
text so a line wrap cannot hide them.

The logic lives here rather than in an inline-bash hk step, per
``.claude/rules/zero-bash-logic.md``; the ``codex_agent_parity`` hk step and the
``codex-agent-parity`` CLI subcommand are thin wrappers over
:func:`find_violations`.
"""

from __future__ import annotations

import logging
import re
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

# THE PRIMARY CHECK. A token this repo owns and writes into every hand-authored
# toml. An exporter overwrite destroys it whatever strings that export contains.
# It must never be added to anything the exporter produces, or the gate stops
# discriminating — `tests/test_codex_agent_parity.py` pins its absence from the
# four exported mirrors for exactly that reason.
SENTINEL = "dotfiles-hand-authored-codex-lane"

# Secondary signal only. Matched against WHITESPACE-FLATTENED text, because the
# live corrupted mirror hides `Codex Code` behind a line wrap.
CORRUPTION_MARKERS: tuple[str, ...] = (
    "Codex Code",
    ".Codex/",
    "Codex mcp add",
    "does Codex",
    "docs/Codex",
)

# What the `.md` wrapper must still say. Each is a string THIS repo authored, so
# none of them can drift out from under us the way an exporter's output can.
#
# The two flags are load-bearing together: omit either and codex resolves it from
# `~/.codex/config.toml`, a file this repo neither owns nor watches, silently
# running the lane at `medium` on whatever model that file names.
MD_REQUIRED_MARKERS: tuple[tuple[str, str], ...] = (
    ("--model gpt-5.6-sol", "the explicit model pin in the codex invocation"),
    (
        f'model_reasoning_effort="{REQUIRED_EFFORT}"',
        "the explicit effort pin in the codex invocation",
    ),
    (
        "Never substitute your own reasoning for a failed codex call",
        (
            "the prohibition on backfilling a failed codex call with in-model "
            "reasoning — the failure that looks exactly like success"
        ),
    ),
)

_FRONTMATTER_RE = re.compile(r"\A---\n(?P<fm>.*?)\n---\n", re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ParityViolation:
    """One failure, with the path that carries it."""

    kind: str
    path: str
    detail: str


def flatten(text: str) -> str:
    """Collapse every whitespace run to one space.

    A multi-word marker is invisible to a raw scan once the text is reflowed:
    the live corrupted mirror carries ``Codex Code`` split across a line break.
    """
    return _WHITESPACE_RE.sub(" ", text)


def _read(path: Path) -> str:
    """Read a file as text, never raising on undecodable bytes.

    A non-UTF-8 toml is itself evidence something overwrote the file, so it must
    surface as a named violation rather than an unhandled ``UnicodeDecodeError``
    reported as an unexplained command failure.
    """
    return path.read_text(encoding="utf-8", errors="replace")


def _stems(directory: Path, suffix: str) -> set[str]:
    """Stems of in-scope agent files in ``directory``, or empty if it is absent."""
    if not directory.is_dir():
        return set()
    return {
        p.name[: -len(suffix)]
        for p in directory.iterdir()
        if p.is_file() and p.name.startswith(STEM_PREFIX) and p.name.endswith(suffix)
    }


def _frontmatter(text: str) -> dict[str, str]:
    """Parse the leading YAML frontmatter block into a flat key -> value map."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    out: dict[str, str] = {}
    for line in match.group("fm").splitlines():
        key, sep, value = line.partition(":")
        if sep and not key.startswith((" ", "\t", "#")):
            out[key.strip()] = value.strip()
    return out


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
    """Yield sentinel, corruption, identity and effort violations per codex toml."""
    directory = repo_root / CODEX_AGENT_DIR
    for stem in sorted(_stems(directory, ".toml")):
        path = directory / f"{stem}.toml"
        rel = f"{CODEX_AGENT_DIR}/{stem}.toml"
        raw = _read(path)
        flat = flatten(raw)

        if SENTINEL not in raw:
            yield ParityViolation(
                kind="sentinel-missing",
                path=rel,
                detail=(
                    f"the {SENTINEL!r} line is gone — this repo no longer owns "
                    "these bytes. The Codex Desktop app writes this directory; "
                    "restore the file from git rather than editing it in place"
                ),
            )

        found = [m for m in CORRUPTION_MARKERS if m in flat]
        if found:
            yield ParityViolation(
                kind="corrupted",
                path=rel,
                detail=(
                    f"carries the Codex-exporter product-name substitution "
                    f"{found!r} (matched on whitespace-flattened text, because a "
                    "line wrap hides a two-word marker); restore it from git"
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


def _md_violations(repo_root: Path) -> Iterator[ParityViolation]:
    """Yield identity, model-pin and prohibition violations per claude wrapper."""
    directory = repo_root / CLAUDE_AGENT_DIR
    for stem in sorted(_stems(directory, ".md")):
        path = directory / f"{stem}.md"
        rel = f"{CLAUDE_AGENT_DIR}/{stem}.md"
        raw = _read(path)
        flat = flatten(raw)
        front = _frontmatter(raw)

        if not front:
            yield ParityViolation(
                kind="md-no-frontmatter",
                path=rel,
                detail="no leading `---` YAML frontmatter block",
            )
            continue

        if front.get("name") != stem:
            yield ParityViolation(
                kind="md-name-mismatch",
                path=rel,
                detail=(
                    f"frontmatter name is {front.get('name')!r}, expected the "
                    f"filename stem {stem!r}"
                ),
            )

        # The VALUE is a tuning decision and deliberately unchecked; its absence
        # is not, because an unpinned wrapper runs on the session default, which
        # is the Opus spend these lanes exist to avoid.
        if "model" not in front:
            yield ParityViolation(
                kind="md-no-model",
                path=rel,
                detail=(
                    "no `model:` frontmatter line — the wrapper would run its "
                    "clerical turns on the session default"
                ),
            )

        for marker, why in MD_REQUIRED_MARKERS:
            if flatten(marker) not in flat:
                yield ParityViolation(
                    kind="md-missing-marker",
                    path=rel,
                    detail=f"does not carry {marker!r} — {why}",
                )


def find_violations(repo_root: Path) -> list[ParityViolation]:
    """Every parity violation across the hand-authored codex agent lanes."""
    return [
        *_pairing_violations(repo_root),
        *_toml_violations(repo_root),
        *_md_violations(repo_root),
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
        "codex-agent-parity OK: %d hand-authored lane(s) paired, sentinel "
        "intact, named consistently, pinned to %s effort, and carrying the "
        "no-substitute prohibition",
        paired,
        REQUIRED_EFFORT,
    )
    return 0
