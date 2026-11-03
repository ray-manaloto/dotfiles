"""Tickets under .scratch/<feature>/issues/ against the status table in docs/agents/issue-tracker.md."""

import re
from pathlib import Path

from .git import top
from .models import Check, Finding, Listed, Listing, Ticket, Tickets

TABLE = "docs/agents/issue-tracker.md"
# A status row: | `name` | meaning | yes or no, whether the status satisfies a Blocking edge |
ROW = re.compile(r"^\|\s*`([a-z-]+)`\s*\|[^|]*\|\s*(yes|no)\s*\|\s*$", re.MULTILINE)
STATUS = re.compile(r"^(?:\*\*Status:\*\*|Status:)[ \t]*(.*)$", re.MULTILINE)
BLOCKED = re.compile(r"^(?:\*\*Blocked by:\*\*|Blocked by:)[ \t]*(.*)$", re.MULTILINE)
PR_LINK = re.compile(r"https://github\.com/\S+/pull/\d+")


def status(ticket: Ticket) -> str:
    return ticket.statuses[0].split(" ", 1)[0] if ticket.statuses else ""


def blockers(ticket: Ticket) -> list[str]:
    """Two-digit numbers on the Blocked by line, outside parenthesised notes."""
    text = ticket.blocked_by[0] if ticket.blocked_by else "None"
    return re.findall(r"\b\d{2}\b", re.sub(r"\([^)]*\)", "", text))


def load(root: Path, feature: str | None) -> tuple[dict[tuple[str, str], Ticket], list[Finding]]:
    tickets: dict[tuple[str, str], Ticket] = {}
    found = []
    for path in sorted((root / ".scratch").glob(f"{feature or '*'}/issues/*.md")):
        relative = str(path.relative_to(root))
        if not re.match(r"\d{2}-", path.name):
            found.append(finding(relative, "name must start with a two-digit ticket number"))
            continue
        text = path.read_text()
        ticket = Ticket(
            path=relative,
            feature=path.parent.parent.name,
            number=path.name[:2],
            statuses=STATUS.findall(text),
            blocked_by=BLOCKED.findall(text),
        )
        key = (ticket.feature, ticket.number)
        if key in tickets:
            found.append(finding(relative, f"number {ticket.number} is used twice in {ticket.feature}"))
        tickets[key] = ticket
    return tickets, found


def finding(path: str, detail: str) -> Finding:
    return Finding(path=path, check=Check.tickets, detail=detail)


def problems(
    ticket: Ticket, tickets: dict[tuple[str, str], Ticket], satisfying: set[str], known: set[str]
) -> list[str]:
    if len(ticket.statuses) != 1:
        return [f"needs exactly one Status line, found {len(ticket.statuses)}"]
    state, detail = status(ticket), ticket.statuses[0]
    found = []
    if state not in known:
        found.append(f"status {state!r} is not in {TABLE}")
    if state == "done" and not (PR_LINK.search(detail) or detail.startswith("done pre-workflow")):
        found.append("done needs its PR link")
    if len(ticket.blocked_by) > 1:
        found.append("more than one Blocked by line")
    if not blockers(ticket) and ticket.blocked_by and not ticket.blocked_by[0].startswith("None"):
        found.append("Blocked by needs ticket numbers or None")
    for number in blockers(ticket):
        other = tickets.get((ticket.feature, number))
        if other is None or number == ticket.number:
            found.append(f"blocker {number} is not another ticket in {ticket.feature}")
        elif state in satisfying | {"claimed"} and status(other) not in satisfying:
            found.append(f"is {state} but blocker {number} is {status(other)}")
        elif status(other) == "wontfix" and state != "wontfix":
            found.append(f"blocker {number} is wontfix, so this ticket can never start")
    return found


def cycles(tickets: dict[tuple[str, str], Ticket]) -> list[Finding]:
    found = []
    settled: set[tuple[str, str]] = set()

    def visit(key: tuple[str, str], trail: list[tuple[str, str]]) -> None:
        if key in trail:
            ring = " -> ".join(number for _, number in [*trail[trail.index(key) :], key])
            found.append(finding(f".scratch/{key[0]}", f"Blocking edges form a cycle: {ring}"))
            return
        if key in settled or key not in tickets:
            return
        for number in blockers(tickets[key]):
            visit((key[0], number), [*trail, key])
        settled.add(key)

    for key in sorted(tickets):
        visit(key, [])
    return found


def listed(tickets: dict[tuple[str, str], Ticket], satisfying: set[str], options: Tickets) -> list[Listed]:
    def ready(ticket: Ticket) -> bool:
        return status(ticket) == "ready-for-agent" and all(
            (ticket.feature, number) in tickets and status(tickets[(ticket.feature, number)]) in satisfying
            for number in blockers(ticket)
        )

    def unfinished(ticket: Ticket) -> bool:
        return status(ticket) not in satisfying | {"wontfix"}

    wanted = ready if options.listing is Listing.frontier else unfinished
    return [Listed(path=ticket.path) for _, ticket in sorted(tickets.items()) if wanted(ticket)]


def run(options: Tickets) -> tuple[list[Finding], list[Listed]]:
    root = top()
    rows = ROW.findall((root / TABLE).read_text())
    if not rows:
        return [finding(TABLE, "has no status table")], []
    if options.feature and not (root / ".scratch" / options.feature).is_dir():
        return [finding(f".scratch/{options.feature}", "no such feature")], []
    known = {name for name, _ in rows}
    satisfying = {name for name, unblocks in rows if unblocks == "yes"}
    # --feature narrows the check too: another feature's broken ticket does not block this one's listing.
    tickets, found = load(root, options.feature)
    found += [finding(t.path, p) for t in tickets.values() for p in problems(t, tickets, satisfying, known)]
    found += cycles(tickets)
    if found or options.listing is None:
        return found, []
    return found, listed(tickets, satisfying, options)
