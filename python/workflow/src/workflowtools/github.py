"""Read GitHub issues through gh, preserving unavailability as a named event."""

import re
import subprocess
from collections.abc import Iterable

from pydantic import TypeAdapter

from . import git, roadmap
from .models import Check, Finding, GitHubIssue, IssueState, IssueTicket, Unavailable

ORIGIN = re.compile(r"github\.com[:/]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")
PAGES = TypeAdapter(list[list[GitHubIssue]])


def origin() -> tuple[str, str] | None:
    try:
        remote = git.git("remote", "get-url", "origin").strip()
    except subprocess.CalledProcessError:
        return None
    match = ORIGIN.search(remote)
    return (match[1], match[2]) if match else None


def unavailable(repo: tuple[str, str], detail: str) -> Unavailable:
    return Unavailable(kind="github-unavailable", check=Check.tickets, repo="/".join(repo), detail=detail)


def api(repo: tuple[str, str], *args: str) -> str | Unavailable:
    try:
        done = subprocess.run(["gh", "api", *args], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return unavailable(repo, "gh is not installed")
    if done.returncode:
        return unavailable(repo, done.stderr.partition("\n")[0])
    return done.stdout


def issue(owner: str, repo: str, number: int) -> GitHubIssue | Unavailable:
    result = api((owner, repo), f"repos/{owner}/{repo}/issues/{number}")
    if isinstance(result, Unavailable):
        return result
    try:
        return GitHubIssue.model_validate_json(result)
    except ValueError:
        return unavailable((owner, repo), "gh returned output that is not the expected JSON")


def pages(owner: str, repo: str, number: int, endpoint: str) -> list[GitHubIssue] | Unavailable:
    result = api((owner, repo), "--paginate", "--slurp", f"repos/{owner}/{repo}/issues/{number}/{endpoint}")
    if isinstance(result, Unavailable):
        return result
    try:
        return [entry for page in PAGES.validate_json(result) for entry in page]
    except ValueError:
        return unavailable((owner, repo), "gh returned output that is not the expected JSON")


def sub_issues(owner: str, repo: str, number: int) -> list[GitHubIssue] | Unavailable:
    return pages(owner, repo, number, "sub_issues")


def blocked_by(owner: str, repo: str, number: int) -> list[GitHubIssue] | Unavailable:
    return pages(owner, repo, number, "dependencies/blocked_by")


def spec_issues(
    specs: list[int], repo: tuple[str, str]
) -> tuple[dict[int, GitHubIssue], dict[int, list[GitHubIssue]]] | Unavailable:
    parents: dict[int, GitHubIssue] = {}
    children: dict[int, list[GitHubIssue]] = {}
    for spec in specs:
        parent = issue(*repo, spec)
        if isinstance(parent, Unavailable):
            return parent
        parents[spec] = parent
        entries = sub_issues(*repo, spec)
        if isinstance(entries, Unavailable):
            return entries
        children[spec] = entries
    return parents, children


def dependencies(numbers: Iterable[int], repo: tuple[str, str]) -> dict[int, list[GitHubIssue]] | Unavailable:
    blockers: dict[int, list[GitHubIssue]] = {}
    for number in numbers:
        result = blocked_by(*repo, number)
        if isinstance(result, Unavailable):
            return result
        blockers[number] = result
    return blockers


def link_findings(tickets: list[IssueTicket], repo: tuple[str, str], path: str) -> list[Finding]:
    found = []
    for ticket in tickets:
        linked = "/".join(ticket.url.split("/")[3:5])
        if linked != "/".join(repo):
            found.append(
                roadmap.problem(path, f"line {ticket.line}: #{ticket.number} links to {linked}, not the origin {'/'.join(repo)}")
            )
    return found


def membership_findings(
    tickets: list[IssueTicket], children: dict[int, list[GitHubIssue]], path: str
) -> list[Finding]:
    found = []
    members = {spec: {child.number for child in entries} for spec, entries in children.items()}
    for spec, entries in children.items():
        local = {ticket.number for ticket in tickets if ticket.spec == spec}
        found.extend(
            roadmap.problem(path, f"spec #{spec}: sub-issue #{child.number} has no roadmap line")
            for child in entries if child.number not in local
        )
    found.extend(
        roadmap.problem(path, f"line {ticket.line}: #{ticket.number} is not a sub-issue of spec #{ticket.spec}")
        for ticket in tickets if ticket.number != ticket.spec and ticket.number not in members[ticket.spec]
    )
    return found


def state_findings(tickets: list[IssueTicket], states: dict[int, IssueState], path: str) -> list[Finding]:
    return [
        roadmap.problem(path, f"line {ticket.line}: #{ticket.number} is {states[ticket.number].value} on GitHub")
        for ticket in tickets
        if ticket.number in states and ticket.checked != (states[ticket.number] == IssueState.closed)
    ]


def numbers_text(numbers: Iterable[int]) -> str:
    return ", ".join(f"#{number}" for number in sorted(set(numbers))) or "none"


def blocker_findings(tickets: list[IssueTicket], blockers: dict[int, list[GitHubIssue]], path: str) -> list[Finding]:
    found = []
    for ticket in tickets:
        if ticket.number == ticket.spec:
            continue
        numbers = {entry.number for entry in blockers[ticket.number]}
        if set(ticket.blocked_by) != numbers:
            found.append(
                roadmap.problem(
                    path, f"line {ticket.line}: #{ticket.number} is blocked by {numbers_text(numbers)} on GitHub"
                )
            )
    return found


def scope(
    tickets: list[IssueTicket], specs: list[int], repo: tuple[str, str], *, path: str = "task_plan.md"
) -> tuple[dict[int, IssueState], list[Finding] | Unavailable]:
    fetched = spec_issues(specs, repo)
    if isinstance(fetched, Unavailable):
        return {}, fetched
    parents, children = fetched
    blockers = dependencies((ticket.number for ticket in tickets if ticket.number != ticket.spec), repo)
    if isinstance(blockers, Unavailable):
        return {}, blockers
    states = {entry.number: entry.state for entry in parents.values()}
    states.update((entry.number, entry.state) for entries in children.values() for entry in entries)
    findings = [
        *link_findings(tickets, repo, path),
        *membership_findings(tickets, children, path),
        *state_findings(tickets, states, path),
        *blocker_findings(tickets, blockers, path),
    ]
    states.update((entry.number, entry.state) for entries in blockers.values() for entry in entries)
    return states, findings
