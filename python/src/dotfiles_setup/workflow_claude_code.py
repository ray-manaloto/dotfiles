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

The other routes are derived too. Sorted ``.config/mise/conf.d/*.toml`` files
followed by ``mise.toml`` supply the tracked task graph, while
:data:`dotfiles_setup.lint.HK_COMMAND` supplies the hook reached by
``dotfiles-setup lint``. ``mise.local.toml`` is deliberately not read: it is
gitignored and per-clone, so it does not exist where CI runs.

Command parsing intentionally covers this repository's shell vocabulary, not
all POSIX shell syntax. Full-line shell comments are ignored; inline trailing
comments and quoted arguments containing spaces remain residuals. Quotes are
token terminators, which is sufficient to see a command inside
``bash -c "mise run lint"`` without pretending to interpret the shell.

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


@dataclass(frozen=True)
class Flag:
    """One documented CLI flag and every spelling accepted by the tool."""

    spellings: tuple[str, ...]
    takes_value: bool = False
    optional_value: bool = False


# Transcribed from hk 1.57.0 `hk --help`. Unknown dash-prefixed tokens are
# skipped as booleans: a new boolean cannot hide the command, but a new
# value-taking flag can consume what this parser sees as the command until this
# table is updated.
HK_GLOBAL_FLAGS = (
    Flag(("--cd",), takes_value=True),
    Flag(("--format",), takes_value=True),
    Flag(("-j", "--jobs"), takes_value=True),
    Flag(("-p", "--profile"), takes_value=True),
    Flag(("-s", "--slow")),
    Flag(("-v", "--verbose")),
    Flag(("-n", "--no-progress")),
    Flag(("-q", "--quiet")),
    Flag(("--silent",)),
    Flag(("--trace",)),
    Flag(("--json",)),
)

# Transcribed from hk 1.57.0 `hk run --help`. `-W/--why` takes an optional
# value. A following known hook or alias is conservatively treated as the hook,
# so `hk run -W pc` still reaches `pre-commit`; another bare token is its value.
# The unknown-flag forward-compatibility rule above applies here too.
HK_RUN_FLAGS = (
    Flag(("-e", "--exclude"), takes_value=True),
    Flag(("-g", "--glob"), takes_value=True),
    Flag(("-S", "--step"), takes_value=True),
    Flag(("--files0-from",), takes_value=True),
    Flag(("--format",), takes_value=True),
    Flag(("--from-ref",), takes_value=True),
    Flag(("--to-ref",), takes_value=True),
    Flag(("--sarif",), takes_value=True),
    Flag(("--skip-step",), takes_value=True),
    Flag(("--stash",), takes_value=True),
    Flag(("-W", "--why"), optional_value=True),
    Flag(("-a", "--all")),
    Flag(("-c", "--check")),
    Flag(("-f", "--fix")),
    Flag(("-J", "--json")),
    Flag(("-P", "--plan")),
    Flag(("--fail-fast",)),
    Flag(("--no-fail-fast",)),
    Flag(("--no-stage",)),
    Flag(("--pr",)),
    Flag(("--safe",)),
    Flag(("--stage",)),
    Flag(("--staged",)),
    Flag(("--stats",)),
    Flag(("--unstaged",)),
)

# Transcribed from mise 2026.9.9 `mise --help`. As with hk, unknown flags are
# skipped as booleans; a new value-taking flag requires a table update because
# its value can otherwise hide the `run` subcommand.
MISE_GLOBAL_FLAGS = (
    Flag(("-C", "--cd"), takes_value=True),
    Flag(("-E", "--env"), takes_value=True),
    Flag(("-j", "--jobs"), takes_value=True),
    Flag(("-q", "--quiet")),
    Flag(("-v", "--verbose")),
    Flag(("-y", "--yes")),
    Flag(("--no-config",)),
    Flag(("--no-env",)),
    Flag(("--no-hooks",)),
    Flag(("--raw",)),
    Flag(("--locked",)),
    Flag(("--silent",)),
)

# Transcribed from mise 2026.9.9 `mise run --help`. The flag walk restarts
# after every `:::` task separator. The unknown-flag rule above applies here.
MISE_RUN_FLAGS = (
    Flag(("--affected-base",), takes_value=True),
    Flag(("--affected-head",), takes_value=True),
    Flag(("-C", "--cd"), takes_value=True),
    Flag(("-j", "--jobs"), takes_value=True),
    Flag(("-o", "--output"), takes_value=True),
    Flag(("-s", "--shell"), takes_value=True),
    Flag(("-t", "--tool"), takes_value=True),
    Flag(("--allow-env",), takes_value=True),
    Flag(("--allow-net",), takes_value=True),
    Flag(("--allow-read",), takes_value=True),
    Flag(("--allow-write",), takes_value=True),
    Flag(("--task-cache",), takes_value=True),
    Flag(("--timeout",), takes_value=True),
    Flag(("-E", "--env"), takes_value=True),
    Flag(("--affected",)),
    Flag(("--affected-explain",)),
    Flag(("--affected-json",)),
    Flag(("--all",)),
    Flag(("-c", "--continue-on-error")),
    Flag(("-f", "--force")),
    Flag(("-n", "--dry-run")),
    Flag(("-q", "--quiet")),
    Flag(("-r", "--raw")),
    Flag(("-S", "--silent")),
    Flag(("--deny-all",)),
    Flag(("--deny-env",)),
    Flag(("--deny-net",)),
    Flag(("--deny-read",)),
    Flag(("--deny-write",)),
    Flag(("--fresh-env",)),
    Flag(("--no-cache",)),
    Flag(("--no-deps",)),
    Flag(("--no-timings",)),
    Flag(("--skip-deps",)),
    Flag(("--skip-tools",)),
    Flag(("--task-cache-explain",)),
    Flag(("--task-cache-explain-json",)),
    Flag(("--task-cache-stats",)),
    Flag(("-v", "--verbose")),
    Flag(("-y", "--yes")),
    Flag(("--locked",)),
)

HK_HOOK_ALIASES = {
    "pc": "pre-commit",
    "cm": "commit-msg",
    "pp": "pre-push",
    "pcm": "prepare-commit-msg",
}

_HK_DOCUMENTED_HOOKS = frozenset(
    {
        "check",
        "commit-msg",
        "fix",
        "post-checkout",
        "post-commit",
        "post-merge",
        "post-rewrite",
        "pre-commit",
        "pre-push",
        "pre-rebase",
        "prepare-commit-msg",
    }
)
_SHELL_TOKEN_RE = re.compile(r"[^\s;&|)\"'`]+")
_SHELL_COMMENT_RE = re.compile(r"^\s*#")


def _flag_index(flags: tuple[Flag, ...]) -> dict[str, Flag]:
    return {spelling: flag for flag in flags for spelling in flag.spellings}


_HK_GLOBAL_FLAG_INDEX = _flag_index(HK_GLOBAL_FLAGS)
_HK_RUN_FLAG_INDEX = _flag_index(HK_GLOBAL_FLAGS + HK_RUN_FLAGS)
_MISE_GLOBAL_FLAG_INDEX = _flag_index(MISE_GLOBAL_FLAGS)
_MISE_RUN_FLAG_INDEX = _flag_index(MISE_RUN_FLAGS)


def _shell_tokens(command: str) -> tuple[str, ...]:
    """Small shell-ish token stream after dropping full-line comments."""
    uncommented = "\n".join(
        line for line in command.splitlines() if not _SHELL_COMMENT_RE.match(line)
    )
    return tuple(_SHELL_TOKEN_RE.findall(uncommented))


def _advance_flag(
    tokens: tuple[str, ...],
    index: int,
    flags: dict[str, Flag],
    known_hooks: frozenset[str] = frozenset(),
) -> int | None:
    """Index after one known/forward-compatible flag, or ``None`` for a bare token."""
    token = tokens[index]
    spelling, separator, _value = token.partition("=")
    flag = flags.get(spelling)
    if flag is None:
        return index + 1 if token.startswith("-") else None
    if separator:
        return index + 1
    if flag.takes_value:
        return min(index + 2, len(tokens))
    if flag.optional_value and index + 1 < len(tokens):
        following = tokens[index + 1]
        known = known_hooks | _HK_DOCUMENTED_HOOKS | frozenset(HK_HOOK_ALIASES)
        if not following.startswith("-") and following not in known:
            return index + 2
    return index + 1


def _hk_hook_at(
    tokens: tuple[str, ...], index: int, known_hooks: frozenset[str]
) -> str | None:
    """Parse one `hk` candidate according to hk's global/run argv grammar."""
    while index < len(tokens):
        advanced = _advance_flag(tokens, index, _HK_GLOBAL_FLAG_INDEX)
        if advanced is not None:
            index = advanced
            continue
        command = tokens[index]
        if command in {"check", "c"}:
            return "check"
        if command in {"fix", "f"}:
            return "fix"
        if command not in {"run", "r"}:
            return None
        index += 1
        break

    while index < len(tokens):
        advanced = _advance_flag(tokens, index, _HK_RUN_FLAG_INDEX, known_hooks)
        if advanced is not None:
            index = advanced
            continue
        return HK_HOOK_ALIASES.get(tokens[index], tokens[index])
    return None


def _mise_tasks_at(tokens: tuple[str, ...], index: int) -> set[str]:
    """Parse one `mise` candidate, including every `:::`-separated task."""
    while index < len(tokens):
        advanced = _advance_flag(tokens, index, _MISE_GLOBAL_FLAG_INDEX)
        if advanced is not None:
            index = advanced
            continue
        if tokens[index] not in {"run", "r"}:
            return set()
        index += 1
        break

    tasks: set[str] = set()
    awaiting_task = True
    while index < len(tokens):
        if awaiting_task:
            if tokens[index] == ":::":
                index += 1
                continue
            advanced = _advance_flag(tokens, index, _MISE_RUN_FLAG_INDEX)
            if advanced is not None:
                index = advanced
                continue
            tasks.add(tokens[index])
            awaiting_task = False
        elif tokens[index] == ":::":
            awaiting_task = True
        index += 1
    return tasks


#: A pkl mapping entry: `["name"] {` or `["name"] = ...`.
_PKL_ENTRY_RE = re.compile(r'^\s*\["([^"]+)"\]\s*[={]', re.MULTILINE)

#: The same entry name, anchored at END of the text searched, so it reads the
#: key immediately preceding a `{` rather than the first key in a window.
_PKL_ENTRY_NAME_RE = re.compile(r'\["([^"]+)"\]\s*$')


def _hooks_in_command(
    command: str, known_hooks: frozenset[str] = frozenset()
) -> set[str]:
    """Hook names reached directly by one shell command block."""
    tokens = _shell_tokens(command)
    hooks: set[str] = set()
    for index, word in enumerate(tokens):
        if (
            word == "hk"
            and (hook := _hk_hook_at(tokens, index + 1, known_hooks)) is not None
        ):
            hooks.add(hook)
        if word == "dotfiles-setup" and tokens[index + 1 : index + 2] == ("lint",):
            hooks.add(HK_COMMAND[2])
    return hooks


def _mise_tasks_in_command(command: str) -> set[str]:
    """Task names reached by tracked `mise run` spellings in a run block."""
    tokens = _shell_tokens(command)
    return {
        task
        for index, word in enumerate(tokens)
        if word == "mise"
        for task in _mise_tasks_at(tokens, index + 1)
    }


def _run_strings(value: object) -> tuple[str, ...]:
    """Normalize mise's string/list/absent `run` shapes without raising."""
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, str))
    return ()


def _tracked_mise_tasks(root: Path) -> dict[str, object]:
    """Merge tracked task tables in mise's observed configuration order."""
    paths = [*sorted((root / ".config/mise/conf.d").glob("*.toml")), root / "mise.toml"]
    raw_tasks: dict[str, object] = {}
    for path in paths:
        if not path.is_file():
            continue
        try:
            document = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            relative = path.relative_to(root).as_posix()
            message = f"{relative}: {error}"
            raise ValueError(message) from None
        tasks = document.get("tasks")
        if isinstance(tasks, dict):
            raw_tasks.update((str(name), task) for name, task in tasks.items())
    return raw_tasks


def mise_task_hooks(root: Path) -> dict[str, frozenset[str]]:
    """Tracked mise tasks mapped to every hk hook their closure reaches.

    Sorted ``.config/mise/conf.d/*.toml`` fragments load first and
    ``mise.toml`` loads last, matching ``mise config ls`` precedence. A later
    definition of the same task replaces the earlier definition.

    Both explicit ``depends`` edges and task calls inside ``run`` bodies join
    the graph. Repeated union to a fixed point makes cycles terminate naturally
    while preserving a reachable hook elsewhere in the same component.
    """
    raw_tasks = _tracked_mise_tasks(root)
    if not raw_tasks:
        return {}

    known_hooks = _HK_DOCUMENTED_HOOKS
    hk_path = root / "hk.pkl"
    if hk_path.is_file():
        known_hooks |= frozenset(
            name for name, _body in hook_bodies(hk_path.read_text(encoding="utf-8"))
        )

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

        direct[name] = {
            hook for command in runs for hook in _hooks_in_command(command, known_hooks)
        }
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
    command: str,
    task_hooks: dict[str, frozenset[str]],
    known_hooks: frozenset[str] = frozenset(),
) -> frozenset[str]:
    """Direct hooks plus hooks reached through any tracked mise task."""
    hooks = _hooks_in_command(command, known_hooks)
    for task in _mise_tasks_in_command(command):
        hooks.update(task_hooks.get(task, frozenset()))
    return frozenset(hooks)


def _expand_local(
    uses: str,
    root: Path,
    task_hooks: dict[str, frozenset[str]],
    known_hooks: frozenset[str],
    seen: frozenset[str],
) -> tuple[WorkflowStep, ...]:
    """Steps inside a local composite, recursively and in execution order.

    The caller retains the ``uses:`` entry and splices this result immediately
    after it. A path-local ``seen`` set terminates cycles without suppressing a
    legitimate second invocation of the same action elsewhere in the job.
    """
    if not uses.startswith(("./", "$/")):
        return ()
    resolved_root = root.resolve()
    action_dir = (root / uses[2:]).resolve()
    identity = action_dir.as_posix()
    if not action_dir.is_relative_to(resolved_root) or identity in seen:
        return ()
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
    nested_seen = seen | {identity}
    for step in _ordered_steps(_steps_of(document)):
        if isinstance(step, RunStep):
            expanded.append(
                RunStep(
                    step.command,
                    _reached_hooks(step.command, task_hooks, known_hooks),
                )
            )
        else:
            expanded.append(step)
            expanded.extend(
                _expand_local(
                    step.reference,
                    root,
                    task_hooks,
                    known_hooks,
                    nested_seen,
                )
            )
    return tuple(expanded)


def resolve_job(job: Job, root: Path, task_hooks: dict[str, frozenset[str]]) -> Job:
    """Resolve routes and inline local composites without losing step order."""
    known_hooks = _HK_DOCUMENTED_HOOKS | frozenset(hooks_running_the_gate(root))
    resolved: list[WorkflowStep] = []
    for step in job.steps:
        if isinstance(step, RunStep):
            resolved.append(
                RunStep(
                    step.command,
                    _reached_hooks(step.command, task_hooks, known_hooks),
                )
            )
        else:
            resolved.append(step)
            resolved.extend(
                _expand_local(
                    step.reference,
                    root,
                    task_hooks,
                    known_hooks,
                    frozenset(),
                )
            )
    return _job_with_steps(job.workflow, job.name, tuple(resolved))


def job_runs_the_gate(job: Job, hooks: set[str]) -> bool:
    """Whether any ordered run step reaches an hk hook carrying the gate."""
    if job.steps:
        return any(
            bool(_step_hooks(step, hooks) & hooks)
            for step in job.steps
            if isinstance(step, RunStep)
        )
    return any(
        _hooks_in_command(command, frozenset(hooks)) & hooks
        for command in job.run_commands
    )


def job_installs_claude_code(job: Job) -> bool:
    """Whether the job uses the setup-claude-code composite."""
    references = (
        (step.reference for step in job.steps if isinstance(step, UsesStep))
        if job.steps
        else iter(job.uses)
    )
    return any(reference.endswith(SETUP_ACTION) for reference in references)


def _step_hooks(step: RunStep, hooks: set[str]) -> frozenset[str]:
    """Resolved hooks, falling back to direct parsing for an unresolved job."""
    return step.reached_hooks or frozenset(
        _hooks_in_command(step.command, frozenset(hooks))
    )


def _first_gate_step(job: Job, hooks: set[str]) -> int | None:
    """Index of the first ordered run step reaching a gated hook."""
    for index, step in enumerate(job.steps):
        if isinstance(step, RunStep) and _step_hooks(step, hooks) & hooks:
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
            if not job_runs_the_gate(job, hooks):
                continue
            if not job_installs_claude_code(job):
                violations.append(_never_installs_violation(job))
            elif not job_installs_before_gate(job, hooks):
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
