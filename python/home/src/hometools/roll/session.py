"""roll:stop, roll:start and roll:verify for one session: stop at a stop point, resume in place, check it came back."""

import datetime as dt
import json
import re
import shlex
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote

from hometools.models import Background, GraphSpace, GraphTab, GraphTerminal, Kind, Role, SessionResult, Timing
from hometools.roll.graph import claude_session, codex_session, opencode_session
from hometools.roll.live import (
    PROGRAMS,
    Live,
    answer,
    bare_shell,
    call,
    entries,
    field,
    poll,
    processes,
    raw_env,
    role,
    rows,
    runs,
)

HANDSHAKE = (
    "From the herdr rolling restart (roll:stop): it restarts your session to load the updated harness and plugins. "
    "Start nothing new. Bring your current step to a safe stopping point, write or update the Resume block at the "
    "top of your lane page (what you were doing, next step, any job to restart, every session-only cron, loop or "
    "monitor you run, since they end with this session, and your worktree path with any staged or uncommitted work "
    "and the commit or review step it waits on), then end your turn with the single line READY-TO-RESTART {token}. "
    "If a background job or an owner question must not be interrupted, end with the line BUSY-KEEP-ME {token} and "
    "the reason instead. Your session resumes in this same tab within a minute."
)
ROLLING = (
    "Resumed by the herdr rolling restart (roll:start) to load the current harness and plugins. Nothing else was "
    "stopped: your worktree and other tabs are as you left them. Read the Resume block at the top of your lane page. "
    "Run CronList first: session-only crons usually survive a resume. Re-create only the crons, loops and monitors "
    "the Resume block lists that are missing, delete duplicates, and continue from its next step."
)
REBOOT = (
    "Resumed after a Mac reboot by the chief of staff (herdr-startup). Your shells and background jobs ended with "
    "the reboot, and /private/tmp scratchpads were cleared (saved copies are under ~/.local/state/scratch-keep/). "
    "Read the 'Resume after reboot' block at the top of your lane page, check your worktree (git status), restart "
    "only the jobs listed there, then continue. If you had a pending owner question, ask it again interactively."
)
# The one chief of staff, resumed by name in its own tab; never claude respawn, never a second one.
CHIEF = ("claude", "--permission-mode", "auto", "--resume", "chief-of-staff", "/herdr-startup rolling")
CHIEF_KEY = "--resume chief-of-staff"
READY, BUSY = "READY-TO-RESTART", "BUSY-KEEP-ME"
IDLE = frozenset({"done", "idle"})
WAITING = frozenset({"permission", "blocked"})
# Long-lived children a session keeps for itself; anything else under it counts as a background job.
SERVICE = re.compile(
    # Whole words only: a bare exa or bun x would also match python example.py or bun xyz, a job /exit kills.
    r"\b(mcp|lsp|language-server|clangd|pyright|gopls|rust-analyzer|typescript-language-server|jdtls|sourcekit|"
    r"caffeinate|codebase-memory|openwiki|context7|exa|firecrawl|playwright|uv tool run|uv tool uvx|npx -y|npm exec|"
    r"bun x|modelcontextprotocol|node_repl|cua_node|codex-code-mode-host|hc (watch|tail)|fnox (daemon|mcp))\b|"
    r"node .*server|^codex | server(\s|$)",
    re.IGNORECASE,
)
DIALOG = "Background work is running"
# The dialog's own lines: its option list (a cursor mark, then numbered choices), not the items it names.
DIALOG_CHROME = ("\N{HEAVY RIGHT-POINTING ANGLE QUOTATION MARK ORNAMENT}", "1.", "2.")
TRUST = re.compile(r"trust (this|the) folder|do you trust", re.IGNORECASE)
FOOTER = re.compile(r"(\d+) in background")
STAMP = "%a %b %d %H:%M:%S %Y"
SCREEN = 4000

Target = tuple[GraphSpace, GraphTab, GraphTerminal]


class Skip(Exception):  # noqa: N818 - an outcome, not an error: it carries the result word to the step
    """The session is left as it is: result is skipped-<why> or failed-<why>, notes say what was seen."""

    def __init__(self, result: str, *notes: str) -> None:
        super().__init__(result)
        self.result, self.notes = result, list(notes)


def need(ok: object, result: str, *notes: str) -> None:
    """Go on only when ok holds; otherwise the session is left as it is, with result."""
    if not ok:
        raise Skip(result, *notes)


def request(token: str) -> str:
    """The handshake for one run: its answer carries the run id, so an answer left on a screen from an earlier
    run is never taken for this one."""
    return HANDSHAKE.format(token=token)


def where(target: Target) -> str:
    return f"{target[0].name} / {target[1].name}"


def outcome(target: Target, result: str, notes: list[str], address: str | None = None) -> SessionResult:
    """The step's line for the session; address is the terminal it now runs in when start opened a new tab."""
    term = target[2]
    return SessionResult(
        where=where(target), terminal=address or term.address, kind=term.kind, session=term.session, result=result,
        notes=notes,
    )  # fmt: skip


def status(address: str) -> tuple[str | None, str | None, list[str]]:
    """hc get's status state and kind, and the foreground argv, read now."""
    info = answer("hc", "get", address, "--json")
    state, kind, argv = field(info, "status", "state"), field(info, "status", "kind"), field(info, "foreground", "argv")
    words = [str(word) for word in argv] if isinstance(argv, list) else []
    return (state if isinstance(state, str) else None), (kind if isinstance(kind, str) else None), words


def screen(address: str) -> str:
    return (call("hc", "read", address) or "")[-SCREEN:]


def jobs(live: Live, address: str, kind: Kind) -> list[str]:
    """Background work under the session: child processes other than its services, and hc run children that die
    with it (herdr-core terminals, not child processes, so the process scan misses them)."""
    pid, _ = live.foreground(address)
    found = []
    for child in live.descendants(pid)[1:] if pid else []:
        args = live.procs[child][2]
        # The harness itself under a launcher (fnox proxy run), its own helpers (opencode serve, opencode-pty), and
        # children that already exited and wait to be reaped (ps prints <defunct>).
        if SERVICE.search(args) or bare_shell(args.split()[:1]) or owned(kind, args) or args == "<defunct>":
            continue
        found.append(args.split(" && ", 1)[-1][:120] if "shell-snapshots" in args else args[:120])
    for other, info in live.info.items():
        if str(field(info, "parent")) in {address, str(pid)} and field(info, "die_with_parent") is not False:
            found.append(f"hc run child {other} dies with this session")
    return found


def owned(kind: Kind, args: str) -> bool:
    """args runs the harness's own program, or one named after it; under an interpreter line (python -I script)
    the program is the third word."""
    return any(Path(word).name.startswith(PROGRAMS[kind]) for word in args.split()[:3])


def transcript(session: str) -> Path | None:
    """The Claude session's transcript, ~/.claude/projects/<project>/<session>.jsonl."""
    found = list((Path.home() / ".claude/projects").glob(f"*/{session}.jsonl"))
    return found[0] if len(found) == 1 else None


def records(path: Path) -> list[dict[str, object]]:
    """The transcript's records; a line still being written is skipped."""
    found = []
    for line in path.read_text().splitlines():
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            found.append(record)
    return found


def reply(path: Path, since: dt.datetime, token: str) -> str | None:
    """ready or busy from the last marker in assistant text written after since, else None. Read from the
    transcript, not the screen: Claude draws the reply behind a bullet, and later turns push it off."""
    found = None
    for record in records(path):
        stamp = field(record, "timestamp")
        if field(record, "type") != "assistant" or field(record, "isSidechain") or not isinstance(stamp, str):
            continue
        if dt.datetime.fromisoformat(stamp) <= since:
            continue
        for block in rows(field(record, "message"), "content"):
            text = str(block.get("text", "")).strip() if block.get("type") == "text" else ""
            if text.splitlines() and text.splitlines()[-1].strip() in {READY, f"{READY} {token}"}:
                found = "ready"
            elif text.startswith(BUSY):
                found = "busy"
    return found


def screen_reply(address: str, token: str) -> str | None:
    """For Codex and OpenCode, whose transcripts differ: the last marker line on the screen that carries this run's
    token. The transcript is read by time; a screen has no times, so a bare marker may be an earlier run's."""
    found = None
    for line in screen(address).splitlines():
        text = line.strip(" \N{BOX DRAWINGS LIGHT VERTICAL}\N{BLACK CIRCLE}\N{BULLET}>")
        if text == f"{READY} {token}":
            found = "ready"
        elif text.startswith(f"{BUSY} {token}"):
            found = "busy"
    return found


def footer(address: str) -> str | None:
    match = FOOTER.search(screen(address))
    return f"{match[1]} background item(s) in footer (crons or agents)" if match and int(match[1]) else None


def tab_of(address: str) -> tuple[dict[str, object], dict[str, object]] | None:
    """The space and tab herdr-app ls shows the terminal in, read now."""
    for space in rows(answer("herdr-app", "ls"), "spaces"):
        for tab in rows(space, "tabs"):
            if any(term.get("terminal") == address for term in rows(tab, "terminals")):
                return space, tab
    return None


def same_tab(space: GraphSpace, tab: GraphTab, address: str) -> None:
    """The terminal is still in that tab of that space: herdr-app ls read right before acting (owner ruling). A tab
    moved into another space (one excluded from the roll, say) is skipped-moved."""
    now = tab_of(address)
    need(now, "skipped-gone", f"herdr-app ls has no {address}")
    space_now, tab_now = now or ({}, {})
    names = f"{field(space_now, 'name')} / {field(tab_now, 'name')}"
    shown = f"herdr-app ls shows {address} in {names} ({field(tab_now, 'id')})"
    same = (
        field(space_now, "name") == space.name and field(tab_now, "id") == tab.id and field(tab_now, "name") == tab.name
    )
    need(same, "skipped-moved", shown)


def current(live: Live, term: GraphTerminal, why: str) -> int | None:
    """The terminal's foreground, read now, still runs the harness and the session the graph names (found as the
    snapshot finds it): result why otherwise. Its foreground pid."""
    live.reread(term.address)
    pid, argv = live.foreground(term.address)
    need(runs(term.kind, argv), why, shlex.join(argv))
    tree = live.tree(term.address)
    finders = {Kind.claude: lambda: claude_session(tree), Kind.codex: lambda: codex_session(tree)}
    found = finders.get(term.kind, lambda: opencode_session(argv))()
    need(found == term.session, "skipped-session-changed", f"now {found}")
    return pid


def attempt(keep: Path, term: GraphTerminal) -> str:
    """A token new to every handshake: the run id and the attempt number, counted in the run folder's handshakes.log
    (one line per handshake sent, a retry of the same run included), so no earlier answer still on a screen counts."""
    log = keep / "handshakes.log"
    count = len(log.read_text().splitlines()) if log.exists() else 0
    token = f"{keep.name}-{count + 1}"
    with log.open("a") as lines:
        lines.write(f"{token} {term.address} {term.session}\n")
    return token


def handshake(term: GraphTerminal, timing: Timing, token: str) -> str | None:
    """Ask for a stop point and wait for the answer; hc wait returns early on a message, so wait while it works. A
    send that fails (hc exits non-zero; a wait that times out is a check-in and exits 0, herdr-core
    src/cli.rs:355 at v0.1.21) asked nothing: skipped."""
    path = transcript(term.session) if term.kind is Kind.claude and term.session else None
    need(path or term.kind is not Kind.claude, "skipped-no-transcript", f"session {term.session}")
    since = dt.datetime.now(dt.UTC)

    def heard() -> str | None:
        found = reply(path, since, token) if path else screen_reply(term.address, token)
        # An idle tab with no marker has answered nothing: stop waiting.
        return found or (None if status(term.address)[0] not in IDLE else "")

    wait = str(int(timing.wait))
    sent = call("hc", "send", "--wait", "--timeout", wait, term.address, request(token), timeout=timing.wait + 60)
    need(sent is not None, "skipped-handshake-not-sent")
    return poll(heard, timing.wait, timing.interval) or None


def exited(term: GraphTerminal) -> bool | None:
    return True if not runs(term.kind, status(term.address)[2]) else None


def exit_session(term: GraphTerminal, timing: Timing) -> list[str]:
    """/exit, untagged; the 'Background work is running' dialog's items. Scheduled tasks alone survive a resume
    (seen 2026-11-11), so exit; anything else means Stay: Esc and skip."""
    call("hc", "send", term.address, "/exit", env=raw_env())

    def settled() -> str | None:
        text = screen(term.address)
        return text if DIALOG in text else ("" if exited(term) else None)

    text = poll(settled, timing.settle, timing.interval)
    need(text is not None, "failed-exit-timeout")
    if not text:
        return []
    block = str(text).split("will stop when you exit:", 1)[-1].split("Exit and stop tasks", 1)[0]
    items = [line.strip() for line in block.splitlines() if line.strip() and not line.strip().startswith(DIALOG_CHROME)]
    crons = bool(items) and all(item.startswith("scheduled task") for item in items)
    call("hc", "keys", term.address, "enter" if crons else "esc")
    need(crons, "skipped-background-work-at-exit", *items[:6])
    need(poll(lambda: exited(term), timing.settle, timing.interval), "failed-exit-timeout", *items)
    return items


def kept(keep: Path, target: Target) -> Path:
    """keep/background/<space>--<tab>--<session>.json, each name percent-encoded: a / or a leading .. in a herdr
    name stays one file name inside the run folder, and two sessions in one tab keep a receipt each."""
    names = (target[0].name, target[1].name, str(target[2].session))
    return keep / "background" / ("--".join(quote(name, safe="") for name in names) + ".json")


def stop(live: Live, target: Target, timing: Timing, keep: Path | None, mark: dt.datetime | None) -> SessionResult:
    """Ask the session for a stop point, then /exit it, recording its background work and its worktree's git status
    in keep/background (the run folder, which also counts the handshakes; None for a dry run, which only plans).
    A session already current (mark: when the plugin code set last changed) is left running. The foreground and the
    session are read fresh before the handshake and again before /exit."""
    space, tab, term = target
    try:
        need(term.address != live.me, "skipped-self", "the tab running this step")
        pid = current(live, term, f"skipped-foreground-not-{term.kind}")
        stale = outdated(term, started(pid) if pid else None, mark)
        need(stale, "skipped-already-current", "on the installed version, started after it changed")
        state, _, _ = status(term.address)
        busy = jobs(live, term.address, term.kind)
        need(state in IDLE and not busy, "skipped-busy", f"status {state}", *busy[:6])
        if keep is None:
            return outcome(target, "planned", ["handshake, then /exit", f"status {state}", *stale])
        path = kept(keep, target)
        record = Background(where=where(target), terminal=term.address, session=term.session, jobs=[], footer=None,
                            exit_dialog=[], worktree=None)  # fmt: skip
        write(path, record)
        same_tab(space, tab, term.address)
        heard = handshake(term, timing, attempt(keep, term))
        state, kind, argv = status(term.address)
        need(kind not in WAITING, "skipped-blocked", f"answer {heard}")
        need(heard == "ready", f"skipped-{heard or 'no-answer'}")
        need(state in IDLE, "skipped-busy-after-answer", f"status {state}")
        need(runs(term.kind, argv), "skipped-foreground-changed", shlex.join(argv))
        same_tab(space, tab, term.address)
        current(live, term, "skipped-foreground-changed")
        busy = jobs(live, term.address, term.kind)
        need(not busy, "skipped-job-started", *busy[:6])
        record = record.model_copy(update={"footer": footer(term.address), "worktree": worktree(term.cwd)})
        write(path, record)
        items = exit_session(term, timing)
    except Skip as skip:
        return outcome(target, skip.result, skip.notes)
    write(path, record.model_copy(update={"exit_dialog": items}))
    return outcome(target, "stopped", [f"background: {path}"])


def write(path: Path, record: Background) -> None:
    """The background record, written before the handshake (a run folder that can't take it stops the session
    from being asked at all) and again with what /exit showed."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(record.model_dump_json(indent=1) + "\n")
    except OSError as failed:
        why = "failed-background-not-written"
        raise Skip(why, str(failed)) from None


def resume_argv(target: Target, prompt: str) -> list[str]:
    """The command that resumes the session in its own folder."""
    space, tab, term = target
    old = term.argv or []
    if role(space.name, tab.name) is Role.coordinator:
        return list(CHIEF)
    if term.kind is Kind.claude:
        # The model and effort the session was started with.
        keep = [
            word for i, flag in enumerate(old[:-1]) if flag in {"--model", "--effort"} for word in (flag, old[i + 1])
        ]
        return ["claude", "--permission-mode", "auto", *keep, "--resume", str(term.session), prompt]
    if term.kind is Kind.codex:
        return ["codex-hc", "resume", str(term.session), *codex_flags(old)]
    # OpenCode under the same fnox proxy launcher prefix it ran with, the launcher by name: its mise install
    # path changes with each fnox upgrade.
    cut = next((i for i, word in enumerate(old) if Path(word).name == "opencode"), 0)
    prefix = [Path(old[0]).name, *old[1:cut]] if cut else []
    return [*prefix, "opencode", "--standalone", "-s", str(term.session)]


# What a Codex session ran with that its resume keeps (codex-rs/utils/cli/src/shared_options.rs and
# tui/src/cli.rs at rust-v0.169.0, accepted after `codex resume <id>`): the approval and sandbox policies, model and
# profile. codex-hc adds its own -c shell_environment_policy.set.HC_* overrides for the new terminal, so the old
# ones are dropped; other -c overrides are kept.
CODEX_PAIRS = frozenset({"-a", "--ask-for-approval", "-s", "--sandbox", "-m", "--model", "-p", "--profile", "-c"})
CODEX_ALONE = frozenset({"--dangerously-bypass-approvals-and-sandbox", "--yolo", "--approve-for-me", "--not-so-yolo"})
HC_OVERRIDE = "shell_environment_policy.set.HC_"


def codex_flags(old: list[str]) -> list[str]:
    kept_, words = [], iter(old)
    for word in words:
        flag, equals, _ = word.partition("=")
        if word in CODEX_ALONE or (equals and flag in CODEX_PAIRS and flag.startswith("--")):
            kept_.append(word)
        elif word in CODEX_PAIRS and (value := next(words, None)) is not None and not value.startswith(HC_OVERRIDE):
            kept_ += [word, value]
    return kept_


def key_of(target: Target) -> str:
    """What the resumed process's argv holds: the session id, or the coordinator's resume by name."""
    space, tab, term = target
    return CHIEF_KEY if role(space.name, tab.name) is Role.coordinator else str(term.session)


def folder_of(target: Target) -> str:
    space, _, term = target
    if term.cwd and Path(term.cwd).is_dir():
        return term.cwd
    return space.folder or str(Path.home())


def running(address: str, key: str, kind: Kind) -> int | None:
    """The harness process for the session in that terminal: in its foreground process tree, running the harness's
    program, with key in its args; the deepest one (a launcher above it holds key too)."""
    root = field(answer("hc", "get", address, "--json"), "foreground", "pid")
    if not isinstance(root, int):
        return None
    procs = processes()
    tree, stack = [], [root]
    while stack:
        parent = stack.pop()
        tree.append(parent)
        stack.extend(child for child, (ppid, _, _) in procs.items() if ppid == parent)
    found = [pid for pid in tree if pid in procs and key in procs[pid][2] and owned(kind, procs[pid][2])]
    leaves = [pid for pid in found if not any(procs[other][0] == pid for other in found)]
    return max(leaves, default=None)


def cwd(pid: int) -> str | None:
    text = call("lsof", "-a", "-d", "cwd", "-p", str(pid), "-Fn") or ""
    return next((line[1:] for line in text.splitlines() if line.startswith("n")), None)


def start(target: Target, timing: Timing, *, apply: bool, prompt: str) -> SessionResult:
    """Resume the session: typed into the tab's bare shell, else a new tab (and space) with that argv. A session
    that comes back in another folder is failed-wrong-folder (herdr has opened a tab in another space's folder)."""
    argv, folder = resume_argv(target, prompt), folder_of(target)
    notes = [shlex.join(argv), f"in {folder}"]
    if not apply:
        return outcome(target, "planned", notes)
    address = None
    try:
        address = open_session(target, argv, folder) or poll(lambda: opened(target), timing.settle, timing.interval)
        need(address, "failed-not-running", *notes, "no terminal in the new tab")
        found = str(address)
        pid = poll(lambda: running(found, key_of(target), target[2].kind), timing.settle, timing.interval)
        need(pid, "failed-not-running", *notes)
        now = cwd(int(str(pid)))
        need(not now or Path(now).resolve() == Path(folder).resolve(), "failed-wrong-folder", f"now {now}")
    except Skip as skip:
        return outcome(target, skip.result, skip.notes, address)
    return outcome(target, "started", notes, address)


def opened(target: Target) -> str | None:
    """The one terminal of the tab start opened, found by space and tab name in herdr-app ls."""
    for space in rows(answer("herdr-app", "ls"), "spaces"):
        for tab in rows(space, "tabs") if space.get("name") == target[0].name else []:
            found = addresses(tab)
            if tab.get("name") == target[1].name and len(found) == 1:
                return found[0]
    return None


def addresses(tab: dict[str, object] | None) -> list[str]:
    return [str(term.get("terminal")) for term in rows(tab, "terminals")]


def open_session(target: Target, argv: list[str], folder: str) -> str | None:
    """Type the resume into the session's own terminal when it is a bare shell: its tab picked by id (a renamed tab,
    or one the terminal left, is skipped-moved) and checked against herdr-app ls right before the send. After a
    reboot herdr restores tabs under new ids, so a tab of the same name is used only when it holds one terminal.
    With no such tab, a new tab (or space) runs the argv. The terminal typed into; None for a new tab."""
    space, tab, term = target
    layout = rows(answer("herdr-app", "ls"), "spaces")
    live_space = next((s for s in layout if s.get("name") == space.name), None)
    by_id, in_space = next(((t, s) for s in layout for t in rows(s, "tabs") if t.get("id") == tab.id), (None, None))
    by_name = next((t for t in rows(live_space, "tabs") if t.get("name") == tab.name), None)
    if by_id is not None:
        need(
            field(in_space, "name") == space.name, "skipped-moved", f"tab {tab.id} is now in {field(in_space, 'name')}"
        )
        need(by_id.get("name") == tab.name, "skipped-moved", f"tab {tab.id} is now {by_id.get('name')}")
        need(term.address in addresses(by_id), "skipped-moved", f"{term.address} is not in tab {tab.id}")
        mine, address = tab, term.address
    elif by_name is not None:
        found = addresses(by_name)
        need(len(found) == 1, "skipped-moved", f"{where(target)} now has {len(found)} terminals")
        mine, address = GraphTab(id=str(by_name.get("id")), name=tab.name, terminals=[]), found[0]
    if by_id is not None or by_name is not None:
        need(bare_shell(status(address)[2]), "skipped-tab-busy", f"{address}'s foreground is not a shell")
        same_tab(space, mine, address)
        call("hc", "send", address, f"cd {shlex.quote(folder)} && {shlex.join(argv)}", env=raw_env())
        return address
    named = ["--name", tab.name, "--folder", folder, "--argv", json.dumps(argv)]
    if live_space is not None:
        made = call("herdr-app", "do", "tab.new", "--space", str(live_space["id"]), *named)
    else:
        made = call("herdr-app", "do", "space.new", "--tab", tab.name, *named[2:], "--name", space.name)
    need(made is not None, "failed-open", f"herdr-app could not open {where(target)}")
    return None


def installed_claude() -> str | None:
    folder = Path.home() / ".local/share/claude/versions"
    names = [entry.name for entry in entries(folder)]
    return max(names, key=lambda name: [int(n) for n in re.findall(r"\d+", name)], default=None)


def started(pid: int) -> dt.datetime | None:
    found = processes().get(pid)
    return dt.datetime.strptime(found[1], STAMP) if found else None  # noqa: DTZ007 - ps prints local time


def binary(kind: Kind) -> Path:
    where_ = {Kind.claude: ".local/bin/claude", Kind.codex: ".local/bin/codex"}
    return Path.home() / where_.get(kind, ".opencode/bin/opencode")


def worktree(folder: str | None) -> str | None:
    """git status of the session's folder, so verify can show the restart left staged and uncommitted work alone;
    None outside a repository. --no-optional-locks: it never takes index.lock under a live session."""
    if not folder:
        return None
    return call("git", "--no-optional-locks", "-C", folder, "status", "--porcelain=v1", "--branch")


def outdated(
    term: GraphTerminal, since: dt.datetime | None, mark: dt.datetime | None, address: str | None = None
) -> list[str]:
    """What keeps the running process from being current: an old Claude version or plugins changed after it started
    (mark); for Codex and OpenCode, a binary newer than the process."""
    failed = []
    if term.kind is Kind.claude:
        name = field(answer("hc", "get", address or term.address, "--json"), "foreground", "name")
        if (want := installed_claude()) and name != want:
            failed.append(f"version {name}, installed {want}")
        if mark and since and since <= mark:
            failed.append(f"started {since:%H:%M:%S}, before the plugins changed at {mark:%H:%M:%S}")
    elif since and binary(term.kind).exists():
        changed = dt.datetime.fromtimestamp(binary(term.kind).stat().st_mtime)  # noqa: DTZ006 - ps prints local time
        if since < changed:
            failed.append(f"started before {binary(term.kind)} changed")
    return failed


def verify(
    target: Target,
    mark: dt.datetime | None,
    read: Callable[[str], str],
    before: str | None = None,
    address: str | None = None,
) -> SessionResult:
    """Back and current: running in its terminal (address: the one start resumed it in, else the graph's), current,
    its resume prompt taken, no trust or other dialog, in its folder, and its worktree's git status as roll:stop
    recorded it (before; None when it recorded none)."""
    term = target[2]
    address = address or term.address
    pid = running(address, key_of(target), term.kind)
    if pid is None:
        return outcome(target, "failed-not-running", [], address)
    since = started(pid)
    failed = outdated(term, since, mark, address)
    path = transcript(term.session) if term.kind is Kind.claude and term.session else None
    if term.kind is Kind.claude and (path is None or not arrived(path, since)):
        failed.append("resume prompt not in the transcript")
    if before is not None and worktree(term.cwd) != before:
        failed.append("worktree git status changed across the restart")
    state, kind, _ = status(address)
    if kind in WAITING or TRUST.search(read(address)):
        failed.append(f"waiting on a dialog ({kind or 'trust'})")
    if term.cwd and (now := cwd(pid)) and Path(now).resolve() != Path(term.cwd).resolve():
        failed.append(f"folder {now}, want {term.cwd}")
    return outcome(target, "failed-check" if failed else "ok", failed or [f"pid {pid}", f"status {state}"], address)


def arrived(path: Path, since: dt.datetime | None) -> bool:
    """A user turn at or after the process started: the resume prompt is the first one."""
    for record in records(path):
        stamp = field(record, "timestamp")
        if field(record, "type") == "user" and isinstance(stamp, str):
            when = dt.datetime.fromisoformat(stamp).astimezone().replace(tzinfo=None)
            if since is None or when >= since:
                return True
    return False


def untouched(target: Target, live: Live) -> SessionResult:
    """An excluded session: the same foreground pid as at the snapshot."""
    term = target[2]
    pid, _ = live.foreground(term.address)
    same = term.pid is not None and pid == term.pid
    return outcome(target, "untouched" if same else "failed-changed", [f"pid {term.pid} -> {pid}"])
