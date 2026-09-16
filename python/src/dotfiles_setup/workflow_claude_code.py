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

The other routes are derived too. ``mise.toml`` supplies the tracked task
graph, while :data:`dotfiles_setup.lint.HK_COMMAND` supplies the hook reached
by ``dotfiles-setup lint``. ``mise.local.toml`` is deliberately not read: it
is gitignored and per-clone, so it does not exist where CI runs.

The logic lives here rather than in an inline-bash hk step, per
``.claude/rules/zero-bash-logic.md``; the ``workflow-claude-code`` CLI
subcommand and the ``workflow_claude_code`` hk step are thin wrappers over
:func:`find_violations`.
"""

from __future__ import annotations

import re
import sys
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING

import yaml

from dotfiles_setup.lint import HK_COMMAND

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

#: hk commands that execute hooks. The middle group is the complete hk 1.57.0
#: GLOBAL-flag surface measured for this gate; subcommand-specific flags come
#: after the hook selection and do not affect routing.
_HK_COMMAND_RE = re.compile(
    r"""
    \bhk\b
    (?:
        \s+
        (?:
            (?:--cd|--format|-j|--jobs|-p|--profile)\s+\S+
            |(?:-s|-v|-n|-q|--silent|--trace|--json)\b
        )
    )*
    \s+
    (?:
        (?:run|r)\b\s+(?P<run>[A-Za-z][\w-]*)\b
        |(?P<check>check|c)\b
        |(?P<fix>fix|f)\b
    )
    """,
    re.VERBOSE,
)

_DOTFILES_LINT_RE = re.compile(r"\bdotfiles-setup\b\s+lint(?=\s|[;&|)]|$)")

#: `mise run <task>` / `mise r <task>`. Both the subcommand and task token are
#: bounded so `mise reshim` cannot become the alias `mise r`, and a prefix of a
#: longer task name cannot resolve accidentally.
_MISE_TASK_RE = re.compile(
    r"\bmise\b\s+(?:run|r)\b\s+"
    r"([A-Za-z0-9][\w:.-]*)(?=\s|[;&|)]|$)"
)

#: A pkl mapping entry: `["name"] {` or `["name"] = ...`.
_PKL_ENTRY_RE = re.compile(r'^\s*\["([^"]+)"\]\s*[={]', re.MULTILINE)

#: The same entry name, anchored at END of the text searched, so it reads the
#: key immediately preceding a `{` rather than the first key in a window.
_PKL_ENTRY_NAME_RE = re.compile(r'\["([^"]+)"\]\s*$')


def _hooks_in_command(command: str) -> set[str]:
    """Hook names reached directly by one shell command block."""
    hooks: set[str] = set()
    for match in _HK_COMMAND_RE.finditer(command):
        if hook := match.group("run"):
            hooks.add(hook)
        elif match.group("check"):
            hooks.add("check")
        elif match.group("fix"):
            hooks.add("fix")
    if _DOTFILES_LINT_RE.search(command):
        hooks.add(HK_COMMAND[2])
    return hooks


def _mise_tasks_in_command(command: str) -> set[str]:
    """Task names reached by tracked `mise run` spellings in a run block."""
    return {match.group(1) for match in _MISE_TASK_RE.finditer(command)}


def _run_strings(value: object) -> tuple[str, ...]:
    """Normalize mise's string/list/absent `run` shapes without raising."""
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, str))
    return ()


def mise_task_hooks(root: Path) -> dict[str, frozenset[str]]:
    """Tracked mise tasks mapped to every hk hook their closure reaches.

    Both explicit ``depends`` edges and task calls inside ``run`` bodies join
    the graph. Repeated union to a fixed point makes cycles terminate naturally
    while preserving a reachable hook elsewhere in the same component.
    """
    path = root / "mise.toml"
    if not path.is_file():
        return {}

    document = tomllib.loads(path.read_text(encoding="utf-8"))
    raw_tasks = document.get("tasks")
    if not isinstance(raw_tasks, dict):
        return {}

    direct: dict[str, set[str]] = {}
    edges: dict[str, set[str]] = {}
    for raw_name, raw_task in raw_tasks.items():
        name = str(raw_name)
        if isinstance(raw_task, str):
            runs = (raw_task,)
            depends: object = None
        elif isinstance(raw_task, dict):
            runs = _run_strings(raw_task.get("run"))
            depends = raw_task.get("depends")
        else:
            runs = ()
            depends = None

        direct[name] = {hook for command in runs for hook in _hooks_in_command(command)}
        run_edges = {
            task for command in runs for task in _mise_tasks_in_command(command)
        }
        dependency_edges = (
            {item for item in depends if isinstance(item, str)}
            if isinstance(depends, list)
            else set()
        )
        edges[name] = run_edges | dependency_edges

    reachable = {name: set(hooks) for name, hooks in direct.items()}
    changed = True
    while changed:
        changed = False
        for name, dependencies in edges.items():
            inherited = {
                hook
                for dependency in dependencies
                for hook in reachable.get(dependency, set())
            }
            before = len(reachable[name])
            reachable[name].update(inherited)
            changed = changed or len(reachable[name]) != before

    return {name: frozenset(hooks) for name, hooks in reachable.items() if hooks}


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
class RunStep:
    """An ordered workflow/composite `run:` entry and its resolved routes."""

    command: str
    reached_hooks: frozenset[str] = frozenset()


@dataclass(frozen=True)
class UsesStep:
    """An ordered workflow/composite `uses:` entry."""

    reference: str


type WorkflowStep = RunStep | UsesStep


@dataclass(frozen=True)
class Job:
    """One workflow job with both compatibility views and ordered steps.

    ``run_commands`` and ``uses`` remain available to existing callers. Only
    ``steps`` can answer whether setup happened before the first gated route.
    """

    workflow: str
    """Repo-relative path, e.g. `.github/workflows/ci.yml`."""

    name: str
    """The job's key under `jobs:`."""

    run_commands: tuple[str, ...]
    """Every `run:` block's text, in order."""

    uses: tuple[str, ...]
    """Every `uses:` reference, in order."""

    steps: tuple[WorkflowStep, ...] = ()
    """Run and uses entries in execution order, including local expansions."""


def _steps_of(body: object) -> list[dict[object, object]]:
    """The `steps:`/`runs.steps:` list of a job or composite action."""
    if not isinstance(body, dict):
        return []
    steps: object = body.get("steps")
    if steps is None:
        runs: object = body.get("runs")
        if isinstance(runs, dict):
            steps = runs.get("steps")
    if not isinstance(steps, list):
        return []
    return [step for step in steps if isinstance(step, dict)]


def _ordered_steps(entries: list[dict[object, object]]) -> tuple[WorkflowStep, ...]:
    """Typed step entries in the order GitHub executes them."""
    ordered: list[WorkflowStep] = []
    for entry in entries:
        run = entry.get("run")
        if isinstance(run, str):
            ordered.append(RunStep(run))
        uses = entry.get("uses")
        if isinstance(uses, str):
            ordered.append(UsesStep(uses))
    return tuple(ordered)


def _job_with_steps(workflow: str, name: str, steps: tuple[WorkflowStep, ...]) -> Job:
    """Build compatibility views from the ordered source of truth."""
    return Job(
        workflow=workflow,
        name=name,
        run_commands=tuple(step.command for step in steps if isinstance(step, RunStep)),
        uses=tuple(step.reference for step in steps if isinstance(step, UsesStep)),
        steps=steps,
    )


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
        records.append(
            _job_with_steps(
                workflow,
                str(name),
                _ordered_steps(_steps_of(job)),
            )
        )
    return records


def _reached_hooks(
    command: str, task_hooks: dict[str, frozenset[str]]
) -> frozenset[str]:
    """Direct hooks plus hooks reached through any tracked mise task."""
    hooks = _hooks_in_command(command)
    for task in _mise_tasks_in_command(command):
        hooks.update(task_hooks.get(task, frozenset()))
    return frozenset(hooks)


def _expand_local(
    uses: str,
    root: Path,
    task_hooks: dict[str, frozenset[str]],
    seen: frozenset[str],
) -> tuple[WorkflowStep, ...]:
    """Steps inside a local composite, recursively and in execution order.

    The caller retains the ``uses:`` entry and splices this result immediately
    after it. A path-local ``seen`` set terminates cycles without suppressing a
    legitimate second invocation of the same action elsewhere in the job.
    """
    if not uses.startswith(("./", "$/")) or uses in seen:
        return ()
    action_dir = root / uses[2:]
    candidates = (action_dir / "action.yml", action_dir / "action.yaml")
    action_file = next((path for path in candidates if path.is_file()), None)
    if action_file is None:
        return ()
    try:
        document = yaml.safe_load(action_file.read_text(encoding="utf-8"))
    except yaml.YAMLError, OSError, UnicodeDecodeError:
        return ()

    runs = document.get("runs") if isinstance(document, dict) else None
    using = runs.get("using") if isinstance(runs, dict) else None
    if str(using).lower() != "composite":
        return ()

    expanded: list[WorkflowStep] = []
    nested_seen = seen | {uses}
    for step in _ordered_steps(_steps_of(document)):
        if isinstance(step, RunStep):
            expanded.append(
                RunStep(step.command, _reached_hooks(step.command, task_hooks))
            )
        else:
            expanded.append(step)
            expanded.extend(
                _expand_local(step.reference, root, task_hooks, nested_seen)
            )
    return tuple(expanded)


def resolve_job(job: Job, root: Path, task_hooks: dict[str, frozenset[str]]) -> Job:
    """Resolve routes and inline local composites without losing step order."""
    resolved: list[WorkflowStep] = []
    for step in job.steps:
        if isinstance(step, RunStep):
            resolved.append(
                RunStep(step.command, _reached_hooks(step.command, task_hooks))
            )
        else:
            resolved.append(step)
            resolved.extend(
                _expand_local(step.reference, root, task_hooks, frozenset())
            )
    return _job_with_steps(job.workflow, job.name, tuple(resolved))


def job_runs_the_gate(job: Job, hooks: set[str]) -> bool:
    """Whether any ordered run step reaches an hk hook carrying the gate."""
    if job.steps:
        return any(
            bool((step.reached_hooks or _hooks_in_command(step.command)) & hooks)
            for step in job.steps
            if isinstance(step, RunStep)
        )
    return any(_hooks_in_command(command) & hooks for command in job.run_commands)


def job_installs_claude_code(job: Job) -> bool:
    """Whether the job uses the setup-claude-code composite."""
    references = (
        (step.reference for step in job.steps if isinstance(step, UsesStep))
        if job.steps
        else iter(job.uses)
    )
    return any(reference.endswith(SETUP_ACTION) for reference in references)


def _first_gate_step(job: Job, hooks: set[str]) -> int | None:
    """Index of the first ordered run step reaching a gated hook."""
    for index, step in enumerate(job.steps):
        if isinstance(step, RunStep) and step.reached_hooks & hooks:
            return index
    return None


def _first_install_step(job: Job) -> int | None:
    """Index of the first ordered Claude Code setup action."""
    for index, step in enumerate(job.steps):
        if isinstance(step, UsesStep) and step.reference.endswith(SETUP_ACTION):
            return index
    return None


def job_installs_before_gate(job: Job, hooks: set[str]) -> bool:
    """Whether the first setup action precedes the first gated run step."""
    install_index = _first_install_step(job)
    gate_index = _first_gate_step(job, hooks)
    return (
        install_index is not None
        and gate_index is not None
        and install_index < gate_index
    )


@dataclass(frozen=True)
class SkippedWorkflow:
    """A workflow this gate deliberately left to actionlint."""

    workflow: str
    exception_class: str


@dataclass(frozen=True)
class WorkflowScan:
    """Side-effect-free result consumed by both tests and the CLI seam."""

    violations: tuple[str, ...]
    skipped: tuple[SkippedWorkflow, ...]


def _never_installs_violation(job: Job) -> str:
    return (
        f"{job.workflow}: job `{job.name}` runs an hk hook that includes "
        f"`{GATE_STEP}` but never installs Claude Code. That step shells "
        f"out to `claude`, which is NOT a mise tool here, so the job "
        f"fails on a missing binary. Add before the hk step:\n"
        f"      - name: Install Claude Code\n"
        f"        uses: $/{SETUP_ACTION}"
    )


def _late_install_violation(job: Job) -> str:
    return (
        f"{job.workflow}: job `{job.name}` runs an hk hook that includes "
        f"`{GATE_STEP}` but installs Claude Code AFTER the first hk step. "
        f"The install comes too late: that hk step can already shell out to "
        f"`claude`. Move this step before the hk step:\n"
        f"      - name: Install Claude Code\n"
        f"        uses: $/{SETUP_ACTION}"
    )


def scan_workflows(root: Path) -> WorkflowScan:
    """Collect violations and named fail-open workflow parse skips."""
    hooks = hooks_running_the_gate(root)
    task_hooks = mise_task_hooks(root)
    violations: list[str] = []
    skipped: list[SkippedWorkflow] = []
    for path in sorted((root / WORKFLOW_DIR).glob("*.y*ml")):
        workflow = f"{WORKFLOW_DIR}/{path.name}"
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError, UnicodeDecodeError) as error:
            # Deliberate fail-OPEN on malformed YAML, matching
            # `workflow_hooks.parse_jobs`: `actionlint` already gates workflow
            # syntax in both CI and hk, so a parse error here is a duplicate
            # failure with a worse message. Measured before this guard existed:
            # a workflow that did not parse produced a raw
            # `yaml.scanner.ScannerError` traceback under "Unexpected command
            # failure" instead of naming the file.
            skipped.append(SkippedWorkflow(workflow, type(error).__name__))
            continue
        for parsed_job in parse_jobs(document, workflow):
            job = resolve_job(parsed_job, root, task_hooks)
            gate_index = _first_gate_step(job, hooks)
            if gate_index is None:
                continue
            install_index = _first_install_step(job)
            if install_index is None:
                violations.append(_never_installs_violation(job))
            elif install_index > gate_index:
                violations.append(_late_install_violation(job))
    return WorkflowScan(tuple(violations), tuple(skipped))


def find_violations(root: Path) -> list[str]:
    """Human-readable violation lines; empty means the policy holds.

    Ordered by workflow then job so the output is stable across runs.
    """
    return list(scan_workflows(root).violations)


def workflow_claude_code_main(root: Path) -> int:
    """CLI entry: 0 when every hk-running job installs Claude Code, else 1."""
    result = scan_workflows(root)
    for skipped in result.skipped:
        sys.stdout.write(
            f"workflow-claude-code: skipped {skipped.workflow} "
            f"({skipped.exception_class})\n"
        )
    if not result.violations:
        hooks = ", ".join(sorted(hooks_running_the_gate(root)))
        sys.stdout.write(
            f"workflow-claude-code OK: every job running hk "
            f"({hooks}) installs Claude Code\n"
        )
        return 0
    sys.stdout.write("workflow-claude-code: violations\n\n")
    for line in result.violations:
        sys.stdout.write(f"  - {line}\n")
    sys.stdout.write(f"\n{len(result.violations)} violation(s).\n")
    return 1
