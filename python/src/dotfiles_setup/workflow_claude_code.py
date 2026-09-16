# Copyright (c) 2026 Raymond Manaloto
"""Every CI job that runs hk's steps must install Claude Code first.

hk's ``fnhook_gates`` step shells out to ``claude plugin validate --strict``.
It cannot get the binary from mise: the ``github:anthropics/claude-code``
``[tools]`` pin was removed in ``6d1ae23`` so the native installer owns PATH
(grilling decision Q1), and with no pin to activate ``mise exec`` falls through
to an on-demand ``@latest`` install that ``MISE_LOCKED=1`` refuses on a runner.
Jobs therefore install it explicitly, through
``.github/actions/setup-claude-code``.

**This check exists because fixing it by name did not hold for one push.** PR
#1128's fix added the install to ``ci.yml``'s lint job only. ``autofix.yml``
runs the same hk steps, was not touched, and failed on the next run with::

    fnhook_gates ... [Errno 2] No such file or directory: 'claude'

Two call sites, one fixed. A third hk job added later would repeat it, so the
remedy is a gate that catches a **new** job rather than re-asserting the two
known ones — the same reasoning
``.claude/rules/mise-tasks-only.md`` records for ``workflow_hooks``.

The hook names are DERIVED from ``hk.pkl`` rather than hardcoded here. A
hardcoded ``{"check", "pre-commit", "fix"}`` would silently stop covering a
hook that starts spreading ``allSteps`` later, which is the same
"check that can only pass" ``.claude/rules/probes-need-a-control-arm.md``
rejects. :func:`hooks_running_the_gate` reads which hooks spread the mapping
that defines ``fnhook_gates``, and raises when the premise no longer holds
instead of returning an empty set that would exempt every workflow.

The logic lives here rather than in an inline-bash hk step, per
``.claude/rules/zero-bash-logic.md``; the ``workflow-claude-code`` CLI
subcommand and the ``workflow_claude_code`` hk step are thin wrappers over
:func:`find_violations`.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from pathlib import Path

WORKFLOW_DIR = ".github/workflows"

#: The composite that installs Claude Code. Matched on the trailing path so a
#: caller may spell it `./.github/...`, `$/.github/...`, or with a leading
#: `owner/repo/` — every form resolves to the same action.
SETUP_ACTION = ".github/actions/setup-claude-code"

#: The hk step that needs the binary. Named here so a reader can find the
#: dependency from either end, and asserted present by
#: :func:`hooks_running_the_gate`.
GATE_STEP = "fnhook_gates"

#: `hk run <hook>` — the only hk subcommand that executes steps. `hk validate`
#: parses the config and runs nothing, so a job that only validates needs no
#: binary and must not be flagged.
_HK_RUN_RE = re.compile(r"\bhk\s+run\s+([A-Za-z][\w-]*)")

#: A pkl mapping entry: `["name"] {` or `["name"] = ...`.
_PKL_ENTRY_RE = re.compile(r'^\s*\["([^"]+)"\]\s*[={]', re.MULTILINE)

#: The same entry name, anchored at END of the text searched, so it reads the
#: key immediately preceding a `{` rather than the first key in a window.
_PKL_ENTRY_NAME_RE = re.compile(r'\["([^"]+)"\]\s*$')


def _spread_name(source: str, step: str) -> str:
    """The pkl mapping that defines ``step``, e.g. ``allSteps``.

    Scans backwards from the step for the nearest `<name> = new Mapping` or
    `local <name> ... {` declaration it sits inside.
    """
    index = source.find(f'["{step}"]')
    if index < 0:
        message = (
            f"hk.pkl no longer defines a {step!r} step — this check's whole "
            f"premise is that hk shells out to claude; re-derive it rather "
            f"than letting it pass vacuously"
        )
        raise ValueError(message)
    declarations = re.findall(
        r"^(?:local\s+)?(\w+)\s*(?::[^=]+)?=\s*new\s+Mapping",
        source[:index],
        re.MULTILINE,
    )
    if not declarations:
        message = (
            f"hk.pkl defines {step!r} outside any named Mapping — the spread "
            f"this check follows no longer exists"
        )
        raise ValueError(message)
    return declarations[-1]


def hooks_running_the_gate(root: Path) -> set[str]:
    """Hook names whose hk step list includes :data:`GATE_STEP`.

    Raises rather than returning an empty set when the premise breaks: an
    empty set would exempt every workflow and turn this into a check that can
    only pass.
    """
    source = (root / "hk.pkl").read_text(encoding="utf-8")
    mapping = _spread_name(source, GATE_STEP)
    hooks = {
        name
        for name, body in hook_bodies(source)
        if f"...{mapping}" in body or f'["{GATE_STEP}"]' in body
    }
    if not hooks:
        message = (
            f"no hk hook spreads {mapping!r}, so nothing would ever need "
            f"Claude Code — refusing to report a vacuous pass"
        )
        raise ValueError(message)
    return hooks


def hook_bodies(source: str) -> list[tuple[str, str]]:
    """`(hook name, body)` for each TOP-LEVEL entry of hk.pkl's `hooks` mapping.

    Brace depth is tracked rather than splitting on the next `["name"]` match,
    because hooks contain steps spelled identically. Measured: the flat form
    read `pre-commit`'s own `["no_commit_to_branch"]` step as a sibling hook,
    which took `...allSteps` with it — so `pre-commit` dropped out of the
    derived set and `autofix.yml`, the very job this check was written for,
    went unflagged. A gate blind to its own motivating case is decoration.
    """
    start = source.find("hooks {")
    if start < 0:
        message = "hk.pkl has no `hooks {` mapping — cannot derive hook names"
        raise ValueError(message)
    region = source[start + len("hooks {") :]

    bodies: list[tuple[str, str]] = []
    depth = 0
    name: str | None = None
    body_start = 0
    for index, char in enumerate(region):
        if depth == 0 and char == "}":
            break  # end of the `hooks` mapping itself
        if char == "{":
            if depth == 0:
                # Anchored at the brace, so it reads the name IMMEDIATELY
                # before it. A windowed search returns the window's FIRST
                # match instead, which named `["fix"]` "check" — two hooks
                # collapsing onto one name, and `fix` silently uncovered.
                match = _PKL_ENTRY_NAME_RE.search(region[:index])
                name = match.group(1) if match else None
                body_start = index + 1
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and name is not None:
                bodies.append((name, region[body_start:index]))
                name = None
    return bodies


@dataclass(frozen=True)
class Job:
    """One workflow job, flattened to what the predicates below need.

    Mirrors :class:`dotfiles_setup.workflow_hooks.Job`: parsing YAML into a
    typed record keeps the predicates free of `Any` and of repeated isinstance
    narrowing, and makes each one testable from a literal.
    """

    workflow: str
    """Repo-relative path, e.g. `.github/workflows/ci.yml`."""

    name: str
    """The job's key under `jobs:`."""

    run_commands: tuple[str, ...]
    """Every `run:` block's text, in order."""

    uses: tuple[str, ...]
    """Every `uses:` reference, in order."""


def parse_jobs(document: object, workflow: str) -> list[Job]:
    """Flatten one parsed workflow into :class:`Job` records.

    A malformed or non-mapping document yields no jobs rather than raising:
    `.github/workflows` also holds files this check has no opinion about, and
    a parse quirk there must not take the whole gate down.
    """
    if not isinstance(document, dict):
        return []
    jobs = document.get("jobs")
    if not isinstance(jobs, dict):
        return []
    records: list[Job] = []
    for name, job in sorted(jobs.items()):
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        entries = (
            [step for step in steps if isinstance(step, dict)]
            if isinstance(steps, list)
            else []
        )
        records.append(
            Job(
                workflow=workflow,
                name=str(name),
                run_commands=tuple(
                    step["run"] for step in entries if isinstance(step.get("run"), str)
                ),
                uses=tuple(
                    step["uses"]
                    for step in entries
                    if isinstance(step.get("uses"), str)
                ),
            )
        )
    return records


def job_runs_the_gate(job: Job, hooks: set[str]) -> bool:
    """Whether any of the job's `run` steps invokes an hk hook carrying it."""
    return any(
        match.group(1) in hooks
        for command in job.run_commands
        for match in _HK_RUN_RE.finditer(command)
    )


def job_installs_claude_code(job: Job) -> bool:
    """Whether the job uses the setup-claude-code composite."""
    return any(reference.endswith(SETUP_ACTION) for reference in job.uses)


def find_violations(root: Path) -> list[str]:
    """Human-readable violation lines; empty means the policy holds.

    Ordered by workflow then job so the output is stable across runs.
    """
    hooks = hooks_running_the_gate(root)
    violations: list[str] = []
    for path in sorted((root / WORKFLOW_DIR).glob("*.y*ml")):
        workflow = f"{WORKFLOW_DIR}/{path.name}"
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        violations.extend(
            f"{job.workflow}: job `{job.name}` runs an hk hook that includes "
            f"`{GATE_STEP}` but never installs Claude Code. That step shells "
            f"out to `claude`, which is NOT a mise tool here, so the job "
            f"fails on a missing binary. Add before the hk step:\n"
            f"      - name: Install Claude Code\n"
            f"        uses: $/{SETUP_ACTION}"
            for job in parse_jobs(document, workflow)
            if job_runs_the_gate(job, hooks) and not job_installs_claude_code(job)
        )
    return violations


def workflow_claude_code_main(root: Path) -> int:
    """CLI entry: 0 when every hk-running job installs Claude Code, else 1."""
    violations = find_violations(root)
    if not violations:
        hooks = ", ".join(sorted(hooks_running_the_gate(root)))
        sys.stdout.write(
            f"workflow-claude-code OK: every job running hk "
            f"({hooks}) installs Claude Code\n"
        )
        return 0
    sys.stdout.write("workflow-claude-code: violations\n\n")
    for line in violations:
        sys.stdout.write(f"  - {line}\n")
    sys.stdout.write(f"\n{len(violations)} violation(s).\n")
    return 1
