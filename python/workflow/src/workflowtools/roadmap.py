"""Read roadmap spec sections and their named-plan associations without writing either."""

import os
import re
from collections.abc import Iterator
from pathlib import Path

from . import git
from .models import Check, Finding, IssueTicket

SPEC = re.compile(r"^## .*\bspec #(\d+)\b")
TICKET = re.compile(
    r"^- \[( |x)\] #(\d+) (.+?) \((https://github\.com/([\w.-]+)/([\w.-]+)/issues/(\d+))\)(.*)$"
)
PLAN_ID = re.compile(r"— PLAN_ID (\S+)")
BLOCKERS = re.compile(r"— blocked by ([^;(]*)")
GOAL = re.compile(r"^Implement https://github\.com/([\w.-]+)/([\w.-]+)/issues/(\d+)\b", re.MULTILINE)


def problem(path: str, detail: str) -> Finding:
    return Finding(path=path, check=Check.tickets, detail=detail)


def sections(text: str) -> Iterator[tuple[int, list[tuple[int, str]]]]:
    spec = None
    lines: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if line.startswith(("# ", "## ")):
            if spec is not None:
                yield spec, lines
            match = SPEC.match(line)
            spec = int(match[1]) if match else None
            lines = []
        elif spec is not None and line.startswith("- ["):
            lines.append((number, line))
    if spec is not None:
        yield spec, lines


def parse_line(text: str, number: int, spec: int, path: str) -> tuple[IssueTicket | None, list[Finding]]:
    match = TICKET.match(text)
    if match is None:
        return None, [problem(path, f"line {number}: a ticket line needs #N <title> (<issue link>)")]
    checkbox, issue, title, url, _, _, linked, rest = match.groups()
    found = []
    if int(issue) != int(linked):
        found.append(problem(path, f"line {number}: #{issue} links to issue {linked}"))
    blocked = BLOCKERS.search(rest)
    if blocked is None and int(issue) != spec:
        found.append(problem(path, f'line {number}: #{issue} needs "— blocked by none" or "— blocked by #M, ..."'))
    plan = PLAN_ID.search(rest)
    return IssueTicket(
        kind="ticket",
        number=int(issue),
        title=title,
        url=url,
        spec=spec,
        line=number,
        checked=checkbox == "x",
        plan_id=plan[1] if plan else None,
        blocked_by=[int(n) for n in re.findall(r"#(\d+)", blocked[1])] if blocked else [],
        state=None,
    ), found


def parse(text: str, path: str, *, spec: int | None = None) -> tuple[list[IssueTicket], list[int], list[Finding]]:
    tickets: list[IssueTicket] = []
    specs: list[int] = []
    found: list[Finding] = []
    seen: dict[int, int] = {}
    for section, lines in sections(text):
        if spec is not None and section != spec:
            continue
        if section not in specs:
            specs.append(section)
        for number, text_line in lines:
            ticket, problems = parse_line(text_line, number, section, path)
            found.extend(problems)
            if ticket is None:
                continue
            if ticket.number in seen:
                found.append(problem(path, f"line {number}: #{ticket.number} is already on line {seen[ticket.number]}"))
            else:
                seen[ticket.number] = number
            tickets.append(ticket)
    if not specs:
        detail = "the roadmap has no spec section" if spec is None else f"the roadmap has no section for spec #{spec}"
        found.append(problem(path, detail))
    return tickets, specs, found


def read(
    path: Path, *, spec: int | None = None, display: str | None = None
) -> tuple[list[IssueTicket], list[int], list[Finding]]:
    shown = str(path) if display is None else display
    try:
        text = path.read_text()
    except FileNotFoundError:
        return [], [], [problem(shown, f"no roadmap at {path.absolute()}")]
    return parse(text, shown, spec=spec)


def planning() -> Path:
    if root := os.environ.get("PWF_PLAN_ROOT"):
        return (Path(root) / ".planning").absolute()
    main = git.main_checkout()
    return main.parent / f"{main.name}.plans" / ".planning"


def named_plans() -> dict[str, int]:
    named: dict[str, int] = {}
    for path in sorted(planning().glob("*/task_plan.md")):
        if match := GOAL.search(path.read_text()):
            named[path.parent.name] = int(match[3])
    return named


def plans(
    named: dict[str, int] | None = None, *, issues: set[int] | None = None
) -> tuple[dict[int, str], list[Finding]]:
    associations: dict[int, str] = {}
    found = []
    for plan, issue in (named_plans() if named is None else named).items():
        if issue in associations:
            if issues is None or issue in issues:
                found.append(problem(str(planning()), f"plans {associations[issue]} and {plan} both name #{issue}"))
        else:
            associations[issue] = plan
    return associations, found


def check_plans(tickets: list[IssueTicket], path: str, named: dict[str, int]) -> list[Finding]:
    associations, _ = plans(named, issues=set())
    found = []
    for ticket in tickets:
        if ticket.plan_id is not None and ticket.plan_id in named and named[ticket.plan_id] != ticket.number:
            found.append(
                problem(path, f"line {ticket.line}: PLAN_ID {ticket.plan_id} belongs to #{named[ticket.plan_id]}")
            )
        if ticket.number in associations and ticket.plan_id != associations[ticket.number]:
            found.append(
                problem(
                    path,
                    f"line {ticket.line}: #{ticket.number} has plan {associations[ticket.number]} "
                    f"but its line names {ticket.plan_id or 'none'}",
                )
            )
    return found


def local_findings(tickets: list[IssueTicket], found: list[Finding], path: str) -> list[Finding]:
    named = named_plans()
    _, duplicates = plans(named, issues={ticket.number for ticket in tickets})

    def order(finding: Finding) -> int:
        match = re.match(r"line (\d+):", finding.detail)
        return int(match[1]) if match else 0

    return [*sorted([*found, *check_plans(tickets, path, named)], key=order), *duplicates]
