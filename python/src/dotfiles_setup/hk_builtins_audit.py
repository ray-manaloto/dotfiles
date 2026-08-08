# Copyright (c) 2026 Raymond Manaloto
"""Generate `docs/hk-builtins-audit.md` from `hk builtins` + the hk configs.

## Why this is generated

The hand-written audit it replaces was a 2026-04-05 snapshot that drifted badly
and was never checked against anything. Measured 2026-07-27 on hk 1.52.0:

| | |
|---|---|
| `hk builtins` lists | 144 |
| the doc said it audited | 71 |
| the doc said "used" | 41 |
| actually wired (`Builtins.*`) | 28 |

Fifteen names it listed as *used* were not wired builtins — twelve appeared
nowhere in any config, three were custom steps miscategorised as builtins — and
a sixteenth, **`betterleaks`**, was listed as a "second scanner alongside
gitleaks" while being wired nowhere at all. A document asserting that a security
scanner runs, when it does not, is worse than one that claims nothing.

The doc did carry a "point-in-time, superseded" banner. That is not a defence:
the tables underneath still read as statements of fact, and the one that
mattered was false. So the tables are now derived, and a contract fails CI the
moment the committed file stops matching what this generator produces.

## What is derived and what is authored

Everything factual — which builtins exist, which are wired, in which config,
and which steps are custom — is read from `hk builtins` and the three `.pkl`
files. Only :data:`NOT_ADOPTED` is authored, because "why we chose not to" is a
judgement no tool can recover. It is validated on every run: an entry naming
something that is not a builtin, or something that IS now wired, fails — the
same "keep the map honest" rule as :mod:`dotfiles_setup.bash_budget`.

Regenerate with ``mise run hk-audit``; CI runs it with ``--check``.
"""

from __future__ import annotations

import logging
import re
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

CONFIGS: tuple[str, ...] = ("hk.pkl", "hk-common.pkl", "hk-image.pkl")

# A builtin is WIRED only when it is assigned — `= Builtins.x` or
# `= (Builtins.x) { … }`. A bare `Builtins.x` also matches a COMMENT, which is
# not a subtlety: the first draft of this module used the loose pattern and
# immediately reported `gitleaks` as wired in hk.pkl, on the strength of a
# comment in this very PR that names `Builtins.gitleaks` while describing the
# audit. The same substring trap the module exists to document.
_ASSIGNED_BUILTIN = r"=\s*\(?Builtins\.([a-zA-Z0-9_]+)"
DOC_PATH = "docs/hk-builtins-audit.md"

GENERATED_BANNER = (
    "<!-- GENERATED FILE — do not edit by hand.\n"
    "     Regenerate: mise run hk-audit\n"
    "     Gated by: workflow.hk-builtins-audit (suites.toml) + the hk_audit step.\n"
    "     Authored content lives in python/src/dotfiles_setup/hk_builtins_audit.py\n"
    "     (NOT_ADOPTED); everything else is read from `hk builtins` + the configs. -->"
)

# Builtins deliberately not adopted, and why. Seeded from the hand-written
# audit, keeping only entries that name a builtin hk actually has — the old
# list also carried 14 names that were never hk builtins at all (`pyright`,
# `bandit`, `clippy`, `gofmt`, `tflint`, …), which is itself evidence it was a
# generic linter survey rather than an audit of this tool.
NOT_ADOPTED: dict[str, str] = {
    "biome": "No JS source in project",
    "black": "Superseded by ruff format",
    "dprint": "Redundant with the taplo/yamlfmt/prettier set",
    "eslint": "No JS source in project",
    "flake8": "Superseded by ruff",
    "golangci_lint": "No Go source in project",
    "go_fmt": "No Go source in project",
    "isort": "Superseded by ruff's I rules",
    "markdown_lint": "Runs markdownlint v1; repo uses markdownlint-cli2 (#154)",
    "mdschema": "Requires a schema file that does not exist yet (#160 T12)",
    "mypy": "Using ty instead",
    # `no_commit_to_branch` was here until #400 with the reason "Fails on CI's
    # detached HEAD; branch protection covers it". Both halves expired: hk
    # v1.52.0 (jdx/hk#1075) treats a detached HEAD as not-on-a-protected-branch,
    # and the measured branch protection was `required_pr: false`. It is now
    # wired in hk.pkl's pre-commit hook, so `stale_entries` would fail on an
    # entry left here — which is the map staying honest, as designed.
    "pinact": "GitHub API rate-limit in the hook; use `mise run pin-actions`",
    "pylint": "Superseded by ruff",
    "rubocop": "No Ruby source in project",
    "rumdl": "591 findings across 56 files — a burn-down project, deferred (#160 T12)",
    "rustfmt": "No Rust source in project",
    "ryl": "Redundant with yamllint",
    "stylelint": "No CSS files",
    "terraform": "No Terraform files",
    "tf_lint": "No Terraform files",
    "tombi": "Redundant with taplo",
    "tombi_format": "Redundant with the taplo formatter",
    "vale": "No formal style guide; network dependency in the hook",
    "xmllint": "No XML files in project",
}


def hk_version() -> str:
    """The hk version string, recorded in the generated doc."""
    result = subprocess.run(
        ["hk", "--version"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() or "unknown"


def available_builtins() -> list[str]:
    """Every builtin `hk builtins` reports — the authoritative list."""
    result = subprocess.run(
        ["hk", "builtins"], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        logger.error("hk builtins failed: %s", result.stderr.strip())
        return []
    return sorted(result.stdout.split())


def wired_builtins(root: Path, available: list[str]) -> dict[str, list[str]]:
    """Builtin -> the configs that reference it as `Builtins.<name>`."""
    known = set(available)
    wired: dict[str, list[str]] = {}
    for name in CONFIGS:
        path = root / name
        if not path.exists():
            continue
        for match in re.findall(_ASSIGNED_BUILTIN, path.read_text()):
            if match in known:
                wired.setdefault(match, [])
                if name not in wired[match]:
                    wired[match].append(name)
    return dict(sorted(wired.items()))


def defined_steps(root: Path) -> dict[str, list[str]]:
    """Step name -> the configs that define it, builtin-backed or custom."""
    steps: dict[str, list[str]] = {}
    for name in CONFIGS:
        path = root / name
        if not path.exists():
            continue
        pattern = r'^\s*\["([a-zA-Z0-9_-]+)"\]'
        for match in re.findall(pattern, path.read_text(), re.MULTILINE):
            steps.setdefault(match, [])
            if name not in steps[match]:
                steps[match].append(name)
    return dict(sorted(steps.items()))


def stale_entries(available: list[str], wired: dict[str, list[str]]) -> list[str]:
    """NOT_ADOPTED entries that have stopped being true."""
    known = set(available)
    problems = [
        f"{name}: not a builtin in this hk version — drop the entry"
        for name in NOT_ADOPTED
        if name not in known
    ]
    problems += [
        f"{name}: listed as not-adopted but IS wired in {', '.join(wired[name])}"
        for name in NOT_ADOPTED
        if name in wired
    ]
    return sorted(problems)


def render(root: Path) -> str:
    """The full generated document, as a string."""
    available = available_builtins()
    wired = wired_builtins(root, available)
    steps = defined_steps(root)
    custom = {n: c for n, c in steps.items() if n not in wired}
    unlisted = [n for n in available if n not in wired and n not in NOT_ADOPTED]

    out: list[str] = [
        "# hk Builtins Audit",
        "",
        GENERATED_BANNER,
        "",
        f"- **hk version:** {hk_version()}",
        f"- **Builtins available:** {len(available)}",
        f"- **Wired as builtins:** {len(wired)}",
        (
            f"- **Steps defined in total:** {len(steps)} "
            f"({len(custom)} custom, with their own check/fix commands)"
        ),
        "",
        "A *wired builtin* is referenced as `Builtins.<name>`. A *custom step* is a",
        '`["name"] { … }` block carrying its own commands — it may share a',
        "name with a builtin without being one, which is how the previous",
        "hand-written audit came to list `ruff_format` and `editorconfig-checker`",
        "as builtins in use.",
        "",
        f"## Wired builtins ({len(wired)})",
        "",
        "| Builtin | Declared in |",
        "|---------|-------------|",
    ]
    out += [f"| `{name}` | {', '.join(cfgs)} |" for name, cfgs in wired.items()]

    out += [
        "",
        f"## Custom steps ({len(custom)})",
        "",
        "Not builtins. Each carries its own `check`/`fix`, so `hk builtins` has no",
        "opinion about them, and neither does this table beyond recording them.",
        "",
        "| Step | Declared in |",
        "|------|-------------|",
    ]
    out += [f"| `{name}` | {', '.join(cfgs)} |" for name, cfgs in custom.items()]

    out += [
        "",
        f"## Deliberately not adopted ({len(NOT_ADOPTED)})",
        "",
        "The only authored section — a judgement no tool can recover. Edit it in",
        "`hk_builtins_audit.py`; an entry that stops naming a real builtin, or that",
        "names one now wired, fails the gate.",
        "",
        "| Builtin | Reason |",
        "|---------|--------|",
    ]
    out += [f"| `{name}` | {NOT_ADOPTED[name]} |" for name in sorted(NOT_ADOPTED)]

    out += [
        "",
        f"## Not yet considered ({len(unlisted)})",
        "",
        "Available in this hk version, neither wired nor explicitly declined.",
        "Listed so the unexamined remainder is visible rather than implied — the",
        "previous audit's biggest silent gap was 87 builtins it never mentioned.",
        "",
        "```",
    ]
    rows = (", ".join(unlisted[i : i + 6]) for i in range(0, len(unlisted), 6))
    out += ["\n".join(rows)]
    out += ["```", ""]
    return "\n".join(out)


def hk_builtins_audit_main(root: Path, *, check: bool = False) -> int:
    """Write the audit doc, or (with ``check``) verify the committed one."""
    available = available_builtins()
    if not available:
        logger.error("`hk builtins` produced nothing — cannot audit. Is hk installed?")
        return 1

    problems = stale_entries(available, wired_builtins(root, available))
    if problems:
        for problem in problems:
            logger.error("NOT_ADOPTED %s", problem)
        return 1

    content = render(root)
    target = root / DOC_PATH
    if not check:
        target.write_text(content)
        logger.info("wrote %s", DOC_PATH)
        return 0

    current = target.read_text() if target.exists() else ""
    if current == content:
        return 0
    logger.error(
        "%s is out of date with `hk builtins` + the hk configs. "
        "Regenerate with `mise run hk-audit`.",
        DOC_PATH,
    )
    return 1
