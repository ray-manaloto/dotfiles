"""Check, list and recover issue tickets or resolve a worker's named plan."""

import os
from pathlib import Path

from pydantic import BaseModel

from . import git, github, roadmap
from .models import (
    Check,
    Finding,
    GitHubIssue,
    IssueState,
    IssueTicket,
    Listing,
    PlanResolved,
    Skipped,
    Tickets,
    Unavailable,
)


def code(lines: list[BaseModel], *, require_github: bool) -> int:
    if any(isinstance(line, Finding) for line in lines):
        return 1
    if any(isinstance(line, Unavailable) or (require_github and isinstance(line, Skipped)) for line in lines):
        return 2
    return 0


def select(tickets: list[IssueTicket], states: dict[int, IssueState] | None, listing: Listing) -> list[IssueTicket]:
    closed = (
        {number for number, state in states.items() if state == IssueState.closed}
        if states is not None
        else {ticket.number for ticket in tickets if ticket.checked}
    )
    return [
        ticket.model_copy(update={"state": states[ticket.number] if states is not None else None})
        for ticket in tickets
        if ticket.number != ticket.spec
        and not ticket.checked
        and (listing == Listing.open or all(number in closed for number in ticket.blocked_by))
    ]


def rebuild_specs(path: Path, spec: int | None) -> list[int]:
    if spec is not None:
        return [spec]
    try:
        text = path.read_text()
    # Recovery cannot infer its scope from a missing, unreadable or undecodable roadmap.
    except OSError, UnicodeError:
        return []
    return list(dict.fromkeys(number for number, _ in roadmap.sections(text)))


def render_issue(issue: GitHubIssue, plan: str | None, blockers: list[int] | None = None) -> str:
    line = f"- [{'x' if issue.state == IssueState.closed else ' '}] #{issue.number} {issue.title} ({issue.html_url})"
    if plan is not None:
        line += f" — PLAN_ID {plan}"
    if blockers is not None:
        line += f" — blocked by {github.numbers_text(blockers)}"
    return line


def rebuild(path: Path, shown: str, spec: int | None) -> tuple[list[BaseModel], str]:
    specs = rebuild_specs(path, spec)
    if not specs:
        return [roadmap.problem(shown, "--rebuild without a readable spec section needs --spec N")], ""
    repo = github.origin()
    if repo is None:
        return [roadmap.problem(shown, "--rebuild needs a GitHub origin")], ""
    associations, found = roadmap.plans()
    if found:
        return list(found), ""
    fetched = github.spec_issues(specs, repo)
    if isinstance(fetched, Unavailable):
        return [fetched], ""
    parents, children = fetched
    blockers = github.dependencies((child.number for entries in children.values() for child in entries), repo)
    if isinstance(blockers, Unavailable):
        return [blockers], ""
    output = []
    for number in specs:
        parent = parents[number]
        output.extend(
            [
                f"## spec #{number} {parent.title} ({parent.html_url})",
                "",
                render_issue(parent, associations.get(number)),
            ]
        )
        output.extend(
            render_issue(child, associations.get(child.number), [blocker.number for blocker in blockers[child.number]])
            for child in children[number]
        )
        output.append("")
    return [], "\n".join(output) + "\n"


def plan_section(text: str, plan_id: str) -> int | None:
    for spec, lines in roadmap.sections(text):
        for _, line in lines:
            match = roadmap.PLAN_ID.search(line)
            if match is not None and match[1] == plan_id:
                return spec
    return None


def resolved_plan(tickets: list[IssueTicket], plan_id: str, shown: str) -> list[BaseModel]:
    target = next((ticket for ticket in tickets if ticket.plan_id == plan_id), None)
    if target is None:
        return [roadmap.problem(shown, f"PLAN_ID {plan_id} is on no roadmap line")]
    folder = roadmap.planning() / plan_id
    if not (folder / "task_plan.md").is_file():
        return [roadmap.problem(shown, f"no plan at {folder}")]
    return [PlanResolved(kind="plan", plan_id=plan_id, path=str(folder), issue=target.number, url=target.url)]


def resolve(path: Path, shown: str) -> list[BaseModel]:
    plan_id = os.environ.get("PLAN_ID")
    if not plan_id:
        return [roadmap.problem("task_plan.md", "PLAN_ID is not set")]
    try:
        text = path.read_text()
    except FileNotFoundError:
        return [roadmap.problem(shown, f"no roadmap at {path.absolute()}")]
    spec = plan_section(text, plan_id)
    if spec is None:
        return [roadmap.problem(shown, f"PLAN_ID {plan_id} is on no roadmap line")]
    tickets, _, found = roadmap.parse(text, shown, spec=spec)
    found = roadmap.local_findings(tickets, found, shown)
    if found:
        return list(found)
    return resolved_plan(tickets, plan_id, shown)


def run(options: Tickets) -> tuple[list[BaseModel], str]:
    path = Path(options.roadmap) if options.roadmap is not None else git.main_checkout() / "task_plan.md"
    shown = options.roadmap if options.roadmap is not None else "task_plan.md"
    if options.rebuild:
        return rebuild(path, shown, options.spec)
    if options.plan:
        return resolve(path, shown), ""
    tickets, specs, found = roadmap.read(path, spec=options.spec, display=shown)
    if not specs:
        return list(found), ""
    lines: list[BaseModel] = list(roadmap.local_findings(tickets, found, shown))
    repo = github.origin()
    states = None
    if repo is None:
        lines.append(
            Skipped(check=Check.tickets, reason="origin is not a GitHub repository: the GitHub scope was not checked")
        )
    else:
        states, result = github.scope(tickets, specs, repo, path=shown)
        lines.extend([result] if isinstance(result, Unavailable) else result)
    if options.listing is not None and not code(lines, require_github=options.require_github):
        lines.extend(select(tickets, states, options.listing))
    return lines, ""
