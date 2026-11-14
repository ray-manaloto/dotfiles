"""roll:snapshot: the session graph (space, tab, terminal, agent, session id, folder) and the lane pages' children.

Session ids come from the live processes: Claude Code writes ~/.claude/sessions/<pid>.json for each interactive
process, Codex keeps its rollout file open (found with lsof), and OpenCode runs with -s ses_... in its argv, under the
fnox proxy launcher. graph.json goes where herdr-startup reads it, <wiki>/sessions/graph.json, written atomically,
with a timestamped copy beside it.
"""

import datetime as dt
import itertools
import json
import re
import tempfile
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from hometools.models import (
    Graph,
    GraphSpace,
    GraphTab,
    GraphTerminal,
    Kind,
    LaneParent,
    Role,
    SnapshotReport,
    WorkElsewhere,
)
from hometools.roll.live import APPS, Live, call, field, role, rows

UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
ROLLOUT = re.compile(rf"(/\S*rollout-\S*?-({UUID})\.jsonl)")
LINE = 200


class GraphError(Exception):
    """graph.json exists but is not a graph: the snapshot stops rather than drop the projects it keeps."""


def default_wiki() -> Path:
    return Path.home() / "dev/tmp/fix-herdr/wiki"


def claude_session(pids: list[int]) -> str | None:
    """The sessionId of the first pid with a ~/.claude/sessions/<pid>.json record."""
    for pid in pids:
        record = Path.home() / f".claude/sessions/{pid}.json"
        try:
            # The record can carry trailing data after the first JSON object; read only that object.
            found, _ = json.JSONDecoder().raw_decode(record.read_text())
        except OSError, ValueError:  # no record for this pid, or one being written
            continue
        session = field(found, "sessionId")
        if isinstance(session, str):
            return session
    return None


def codex_session(pids: list[int]) -> str | None:
    """The root thread of the Codex rollout file one of pids holds open."""
    # lsof exits 1 when one of the pids has gone (a short-lived child); what it printed for the rest still counts.
    held = call("lsof", "-p", ",".join(map(str, pids)), codes=frozenset({0, 1})) if pids else None
    match = ROLLOUT.search(held or "")
    if not match:
        return None
    # A multi-agent sub-agent's rollout can be the open file; it can't be resumed on its own. Its
    # session_meta.session_id names the root thread to resume.
    try:
        with Path(match[1]).open() as rollout:
            meta = json.loads(rollout.readline())
    except OSError, ValueError:  # the rollout went away or its first line is not written yet
        return match[2]
    root = field(meta, "payload", "session_id")
    return root if isinstance(root, str) else match[2]


def opencode_session(argv: list[str]) -> str | None:
    """OpenCode's session from -s or --session in its argv."""
    for flag, value in itertools.pairwise(argv):
        if flag in {"-s", "--session"} and value.startswith("ses_"):
            return value
    return None


def lane_children(wiki: Path) -> dict[str, list[LaneParent]]:
    """Each terminal address a lane page's '## Children' section names, with the lines that name it."""
    found: dict[str, list[LaneParent]] = {}
    for page in sorted((wiki / "lanes").glob("*.md")):
        inside = False
        for line in page.read_text(errors="replace").splitlines():
            if line.startswith("## "):
                inside = line.strip().lower().startswith("## children")
                continue
            for address in re.findall(r"\((t[0-9a-z]+)\)", line) if inside else []:
                found.setdefault(address, []).append(LaneParent(lane=page.name, line=line.strip()[:LINE]))
    return found


def terminal(live: Live, address: str, coordinator: str | None, lanes: dict[str, list[LaneParent]]) -> GraphTerminal:
    tree = live.tree(address)
    pid, argv = live.foreground(address)
    session, kind = claude_session(tree), Kind.claude
    if session is None:
        session, kind = codex_session(tree), Kind.codex
    if session is None:
        session, kind = opencode_session(argv), Kind.opencode
    if session is None:
        # An agent whose id was not found stays its kind, so the report names it.
        kind = APPS.get(str(live.terminals.get(address, {}).get("agent")), Kind.shell)
    folder = field(live.info.get(address), "foreground", "cwd") or field(live.info.get(address), "cwd")
    status = field(live.info.get(address), "status", "msg")
    return GraphTerminal(
        address=address,
        kind=kind,
        session=session,
        cwd=folder if isinstance(folder, str) else None,
        argv=argv or None,
        status=status if isinstance(status, str) else None,
        lane_parents=lanes.get(address, []),
        is_coordinator=address == coordinator,
        pid=pid,
    )


def coordinator_of(live: Live) -> str | None:
    for space in live.spaces():
        for tab in rows(space, "tabs"):
            if role(str(space.get("name")), str(tab.get("name"))) is Role.coordinator:
                for term in rows(tab, "terminals"):
                    return str(term["terminal"])
    return None


def build(live: Live, wiki: Path) -> Graph:
    """The live graph; GraphError when herdr-app ls answered no spaces, since a graph built from nothing would mark
    every project closed (kept from the previous graph) and roll nothing."""
    if not live.spaces():
        msg = "roll: herdr-app ls answered no spaces; is herdr running? nothing was written"
        raise GraphError(msg)
    if not live.listed:
        msg = "roll: hc ls --json answered no terminal list; is the herdr core running? nothing was written"
        raise GraphError(msg)
    lanes = lane_children(wiki)
    coordinator = coordinator_of(live)
    spaces = []
    for space in live.spaces():
        tabs = []
        for tab in rows(space, "tabs"):
            terms = [str(term["terminal"]) for term in rows(tab, "terminals")]
            made = [terminal(live, address, coordinator, lanes) for address in terms if address in live.terminals]
            tabs.append(GraphTab(id=str(tab["id"]), name=str(tab["name"]), terminals=made))
        folder = space.get("folder")
        spaces.append(
            GraphSpace(
                id=str(space["id"]),
                name=str(space["name"]),
                folder=folder if isinstance(folder, str) else None,
                tabs=tabs,
            )
        )
    taken = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    return Graph(taken_at=taken, coordinator=coordinator, spaces=spaces)


def previous(path: Path) -> Graph | None:
    try:
        text = path.read_text()
    except FileNotFoundError:
        return None
    try:
        return Graph.model_validate_json(text)
    except ValidationError as bad:
        msg = f"roll:snapshot: {path} is not a graph ({bad.error_count()} errors); move it aside first"
        raise GraphError(msg) from None


def merge(graph: Graph, old: Graph | None) -> Graph:
    """Keep the previous graph's closed projects, and a live project's closed tabs whose sessions are not running."""
    if old is None:
        return graph
    live = {space.name: space for space in graph.spaces}
    kept = []
    for space in old.spaces:
        now = live.get(space.name)
        if now is None:
            kept.append(space.model_copy(update={"kept_from_previous_graph": True}))
            continue
        running = {term.session for tab in now.tabs for term in tab.terminals} - {None}
        names = {tab.name for tab in now.tabs}
        gone = [
            tab.model_copy(update={"kept_from_previous_graph": True})
            for tab in space.tabs
            if tab.name not in names
            and (sessions := {t.session for t in tab.terminals} - {None})
            and not sessions & running
        ]
        live[space.name] = now.model_copy(update={"tabs": now.tabs + gone})
    return graph.model_copy(update={"spaces": [live[space.name] for space in graph.spaces] + kept})


def write(path: Path, text: str) -> None:
    """text into path atomically: a temporary file in the same folder, then a rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, prefix=f".{path.name}.", delete=False) as temp:
        temp.write(text)
    Path(temp.name).replace(path)


def ledger(graph: Graph) -> str:
    lines = [
        f"# Session graph ({graph.taken_at})",
        "",
        "Generated by hometools roll snapshot. One row per terminal; roll:start reopens the agent ones.",
        "",
        "| space | tab | terminal | kind | session | cwd | listed under |",
        "|---|---|---|---|---|---|---|",
    ]
    for space in graph.spaces:
        for tab in space.tabs:
            for term in tab.terminals:
                under = ", ".join(parent.lane for parent in term.lane_parents) or "-"
                me = " (coordinator)" if term.is_coordinator else ""
                row = [space.name, tab.name, term.address + me, term.kind, term.session or "-", term.cwd or "-", under]
                lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def git(folder: str, *args: str) -> str:
    """git in folder; --no-optional-locks so a status never takes index.lock under a live session."""
    return call("git", "--no-optional-locks", "-C", folder, *args) or ""


def work_elsewhere(graph: Graph, wiki: Path) -> list[WorkElsewhere]:
    """Live worker sessions whose checkout is clean while another worktree of the repo has changes and a lane-page
    bullet about the tab names that worktree (owner 2026-11-10: fix before closing). Leads stay in main."""
    blocks = [block for page in (wiki / "lanes").glob("*.md") for block in re.split(r"\n(?=\s*- )", page.read_text())]
    found = []
    for space in graph.spaces:
        for tab in space.tabs:
            # Leads stay in main; a project or tab closed now (kept from the previous graph) has no live session.
            if role(space.name, tab.name) is not Role.child or space.kept_from_previous_graph:
                continue
            for term in [] if tab.kept_from_previous_graph else tab.terminals:
                for other in changed_elsewhere(term) if term.cwd else []:
                    # Only a bullet about this tab counts: its name in the bullet's first 80 characters.
                    if any(tab.name in block.lstrip()[:80] and Path(other).name in block for block in blocks):
                        where = f"{space.name} / {tab.name}"
                        found.append(WorkElsewhere(tab=where, session=term.session, cwd=str(term.cwd), work_in=other))
    return found


def changed_elsewhere(term: GraphTerminal) -> list[str]:
    """The repo's other worktrees with staged or uncommitted changes, when the session's own checkout is clean."""
    cwd = str(term.cwd)
    if term.kind is Kind.shell or not Path(cwd).is_dir() or not git(cwd, "rev-parse", "--git-dir"):
        return []
    if git(cwd, "status", "--porcelain", "--untracked-files=no").strip():
        return []
    others = [line.removeprefix("worktree ") for line in git(cwd, "worktree", "list", "--porcelain").splitlines()]
    others = [o for o in others if o.startswith("/") and Path(o).resolve() != Path(cwd).resolve()]
    return [o for o in others if git(o, "status", "--porcelain", "--untracked-files=no").strip()]


def report(graph: Graph, wiki: Path, written: tuple[Path, Path] | None) -> SnapshotReport:
    live = [(space, tab, term) for space in graph.spaces for tab in space.tabs for term in tab.terminals]
    live = [(s, t, x) for s, t, x in live if not s.kept_from_previous_graph and not t.kept_from_previous_graph]
    agents = [(s, t, x) for s, t, x in live if x.kind is not Kind.shell]
    return SnapshotReport(
        graph=str(written[0]) if written else None,
        graph_copy=str(written[1]) if written else None,
        terminals=len(live),
        agents=len(agents),
        agents_without_session=[x.address for _, _, x in agents if not x.session],
        children_without_lane=[
            f"{s.name} / {t.name}"
            for s, t, x in agents
            if x.kind is Kind.claude and role(s.name, t.name) is Role.child and not x.lane_parents
        ],
        work_elsewhere=work_elsewhere(graph, wiki),
    )


def snapshot(
    live: Live, wiki: Path, *, apply: bool, copy_to: Path, check: Callable[[Graph], object]
) -> tuple[Graph, SnapshotReport]:
    """The graph; with apply, graph.json and ledger.md written, a timestamped copy beside them and in copy_to. check
    sees the graph first and raises to stop the write."""
    path = wiki / "sessions/graph.json"
    graph = merge(build(live, wiki), previous(path))
    check(graph)
    written = None
    if apply:
        # Unset optional fields stay out, as the scripts wrote graph.json; null required ones stay in.
        text = graph.model_dump_json(indent=2, exclude_unset=True)
        stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
        copy = path.with_name(f"graph-{stamp}.json")
        write(path, text)
        write(copy, text)
        write(path.with_name("ledger.md"), ledger(graph))
        write(copy_to, text)
        written = (path, copy)
    return graph, report(graph, wiki, written)
