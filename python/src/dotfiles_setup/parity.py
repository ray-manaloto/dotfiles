"""Cross-repo parity gate (#354 tier 0, `eval.cross-repo-parity`).

dotfiles and knowledge-base document the same cross-vendor orchestration
doctrine. For an unknown number of sessions only one of them carried it in
config — and neither repo could see that, because each was internally
consistent. That is the #354 defect class raised one level: a declaration made
in two places and observed in neither.

The gated set is declared as data in ``parity.toml``: the orchestration plugins,
the trigger/mode lines, and — since 2026-07-25 — the ``.claude/rules/`` stems.
Everything else the repos differ on is emitted as an advisory divergence block,
because a narrow gate is only honest when the difference it declines to gate is
still printed. Silent truncation reads as "covered everything".

Widening the gate is ordered work, not a config edit: declaring an item before
the other repo carries it turns ``main`` red for everyone. The ``rules`` axis
was added only after knowledge-base#24 ported all 22.

Two behaviours here are easy to get backwards, and both are pinned in
``tests/test_parity.py``:

* a plugin present in ``settings.json`` with the value ``false`` is ABSENT.
  Enablement is the value, not the key — a check that asks "is it listed?"
  reports green while the plugin is switched off.
* a run that could not SEE the other repo must not report green. Locally that
  is a loud SKIP (not every clone has the sibling); in CI it is a hard FAIL,
  because there the checkout is this gate's own wiring and its absence is
  exactly the inert-declaration bug reproduced one level up.
"""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from dotfiles_setup import _project_root

#: Where the sibling clone lives when nothing overrides it. CI checks the repo
#: out inside the workspace and points ``KB_REPO_PATH`` at it; a dev box has it
#: beside this one.
DEFAULT_KB_DIRNAME = "knowledge-base"


@dataclass(frozen=True)
class Shared:
    """The declared set every listed repo must carry."""

    plugins: tuple[str, ...]
    lines: tuple[str, ...]
    #: Rule STEMS (``.claude/rules/<stem>.md``). Presence, never content — each
    #: rule is adapted per repo, so byte-equality would force one repo to carry
    #: the other's false statements. What must not drift is which concerns are
    #: governed. Defaulted so a ``parity.toml`` predating this axis still loads.
    rules: tuple[str, ...] = ()


@dataclass(frozen=True)
class ParityGap:
    """One declared thing that one repo does not carry."""

    repo: str
    kind: str
    ref: str


def _normalise(line: str) -> str:
    return " ".join(line.split())


def load_shared(path: Path) -> Shared:
    """Read the declared shared set from ``parity.toml``."""
    data = tomllib.loads(path.read_text()).get("shared", {})
    return Shared(
        plugins=tuple(data.get("plugins", [])),
        lines=tuple(data.get("lines", [])),
        rules=tuple(data.get("rules", [])),
    )


def enabled_plugins(repo_root: Path) -> set[str]:
    """Plugins whose value is exactly ``true`` in ``.claude/settings.json``.

    A missing or unreadable settings file yields the empty set rather than an
    error, so the caller reports it as a GAP. "Cannot read it" must never
    resolve to "it is fine".
    """
    settings = repo_root / ".claude" / "settings.json"
    if not settings.is_file():
        return set()
    try:
        data = json.loads(settings.read_text())
    except json.JSONDecodeError:
        return set()
    plugins = data.get("enabledPlugins", {})
    if not isinstance(plugins, dict):
        return set()
    return {name for name, on in plugins.items() if on is True}


def shipped_skills(repo_root: Path) -> set[str]:
    """Project skill directories that actually carry a ``SKILL.md``."""
    skills = repo_root / ".claude" / "skills"
    if not skills.is_dir():
        return set()
    return {p.name for p in skills.iterdir() if (p / "SKILL.md").is_file()}


def declared_rules(repo_root: Path) -> set[str]:
    """Rule STEMS under ``.claude/rules/`` — every rule, eager or scoped.

    Scoped rules are included deliberately. ``paths:`` frontmatter changes
    *when* a rule loads, not whether the repo governs that concern, and the
    parity question is the latter. Filtering to eager-only would let a repo
    satisfy the gate by scoping a rule into near-irrelevance.
    """
    rules = repo_root / ".claude" / "rules"
    if not rules.is_dir():
        return set()
    return {p.stem for p in rules.glob("*.md")}


def _claude_md_lines(repo_root: Path) -> set[str]:
    doc = repo_root / ".claude" / "CLAUDE.md"
    if not doc.is_file():
        return set()
    return {_normalise(line) for line in doc.read_text().splitlines()}


def find_parity_gaps(repos: dict[str, Path], shared: Shared) -> list[ParityGap]:
    """Return every declared item some repo does not carry.

    Args:
        repos: Display name -> repo root, for every repo the set applies to.
        shared: The declared set, normally from :func:`load_shared`.

    Returns:
        One :class:`ParityGap` per (repo, missing item), repo order preserved.
    """
    gaps: list[ParityGap] = []
    for name, root in repos.items():
        enabled = enabled_plugins(root)
        gaps.extend(
            ParityGap(repo=name, kind="plugin", ref=plugin)
            for plugin in shared.plugins
            if plugin not in enabled
        )
        present = _claude_md_lines(root)
        gaps.extend(
            ParityGap(repo=name, kind="line", ref=line)
            for line in shared.lines
            if _normalise(line) not in present
        )
        rules = declared_rules(root)
        gaps.extend(
            ParityGap(repo=name, kind="rule", ref=rule)
            for rule in shared.rules
            if rule not in rules
        )
    return gaps


def divergence_report(repos: dict[str, Path]) -> str:
    """Advisory: everything the repos differ on, gated or not.

    Ray's 2026-07-24 decision was doctrine-core gated and *the rest reported*.
    This is the reported half. It blocks nothing and names everything, so
    widening the gate later is a data question rather than a rediscovery.
    """
    axes = (
        ("plugins", enabled_plugins),
        ("skills", shipped_skills),
        ("rules", declared_rules),
    )
    names = list(repos)
    out: list[str] = ["advisory divergence (blocks nothing):"]
    for axis, reader in axes:
        sets = {name: reader(root) for name, root in repos.items()}
        shared_all = set.intersection(*sets.values()) if sets else set()
        counts = ", ".join(f"{name}={len(sets[name])}" for name in names)
        out.append(f"  {axis}: {counts}, shared={len(shared_all)}")
        for name in names:
            only = sorted(sets[name] - shared_all)
            if only:
                out.append(f"    only in {name} ({len(only)}): {', '.join(only)}")
    return "\n".join(out)


def resolve_kb_path(explicit: Path | None) -> Path:
    """Explicit argument, then ``KB_REPO_PATH``, then the sibling directory.

    CI cannot check a second repo out beside the workspace (``actions/checkout``
    refuses a path outside it), so it clones into the workspace and exports
    ``KB_REPO_PATH``. A dev box needs neither and gets the sibling default.
    """
    if explicit is not None:
        return explicit
    from_env = os.environ.get("KB_REPO_PATH")
    if from_env:
        return Path(from_env)
    return _project_root().parent / DEFAULT_KB_DIRNAME


def run(
    repo_root: Path,
    *,
    kb_path: Path | None = None,
    in_ci: bool | None = None,
) -> tuple[int, str]:
    """Run the parity gate. Returns ``(exit_code, report)``.

    Args:
        repo_root: This repo's root.
        kb_path: Explicit knowledge-base path; resolved per
            :func:`resolve_kb_path` when omitted.
        in_ci: Treat an unreachable sibling repo as a hard failure. Defaults to
            the ``CI`` environment variable.
    """
    if in_ci is None:
        in_ci = os.environ.get("CI") == "true"
    kb = resolve_kb_path(kb_path)

    if not (kb / ".claude").is_dir():
        detail = f"knowledge-base not found at {kb}"
        if in_ci:
            # In CI this gate's own checkout is what is missing. Skipping here
            # would make the gate inert exactly the way #354's trigger was.
            return 1, f"FAIL parity: {detail} (CI must check it out)"
        return 0, (
            f"SKIP parity: {detail} (set KB_REPO_PATH, or clone it beside this repo)"
        )

    repos = {"dotfiles": repo_root, "knowledge-base": kb}
    shared = load_shared(repo_root / "parity.toml")
    gaps = find_parity_gaps(repos, shared)
    lines = [divergence_report(repos), ""]

    if gaps:
        lines.append(f"FAIL parity: {len(gaps)} declared item(s) missing")
        lines.extend(f"  {gap.repo}: missing {gap.kind} `{gap.ref}`" for gap in gaps)
        return 1, "\n".join(lines)

    lines.append(
        f"OK parity: {len(shared.plugins)} plugin(s) + {len(shared.lines)} line(s) "
        f"+ {len(shared.rules)} rule(s) hold in {', '.join(repos)}"
    )
    return 0, "\n".join(lines)
