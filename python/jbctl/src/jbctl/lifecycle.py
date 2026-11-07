"""status, start, stop and restart of Toolbox IDEs, the way Toolbox itself launches and quits them (ADR 0002)."""

# start runs the install's launchCommand, as Toolbox's background mode does; stop sends the station's /exit, as
# Toolbox's Quit does; restart is the IDE's own /exit with restart. Every request is pinned to one process
# lifetime (pid and start time) and checked again just before it is sent. start and restart bring the IDE
# forward (measured on RustRover), so only the owner runs them on a real IDE.

import hashlib
import os
import time
from collections.abc import Iterator
from contextlib import ExitStack, suppress
from http import HTTPStatus
from pathlib import Path

import filelock
import httpx
import psutil

from . import ide, mcp, station, toolbox
from .ide import IdeError
from .models import (
    Action,
    Answer,
    IdeState,
    IdeStatus,
    Install,
    Lifecycle,
    Lifetime,
    McpState,
    Restart,
    Start,
    Status,
    Stop,
)

# Seconds between local checks of processes and sockets; no request goes to the IDE.
POLL = 0.5
# Seconds between /api/about requests to one IDE, and after an HTTP 429: its REST API allows 30 requests a minute
# per address (ide.rest.api.requests.per.minute), shared with anything else asking.
ASK = 4.0
BACKOFF = 30.0
# The built-in web server takes 63342, or the next free port after it.
WEB_PORTS = range(63342, 63362)
QUIT = {"userInitiated": True, "force": False, "restart": False}
# The jbax window kinds that hold no unapplied edits: project frames and the Welcome screen.
QUIET = {"frame", "welcome"}
# The launcher's commands: a run of the IDE's executable with one of these is a tool, not an IDE (JetBrains'
# command-line interface, plus the stdio MCP server agents start). Any other argument, a relative project folder
# included, is an IDE's own.
TOOLS = frozenset({
    "diff", "format", "inspect", "installPlugins", "ltedit", "merge", "remote-dev-server", "stdioMcpServer",
    "thinClient", "warmup",
})  # fmt: skip


def processes(install: Install) -> list[tuple[int, float]]:
    """This user's IDE processes started from inside the install's app, with or without a station socket yet."""
    inside = f"{Path(install.app).resolve()}/Contents/MacOS/"
    found = []
    for pid in psutil.pids():
        info = toolbox.snapshot(pid, "cmdline", "create_time", "uids") or {}
        argv, uids = info.get("cmdline") or [], info.get("uids")
        mine = uids and uids.real == os.getuid() and argv and os.path.realpath(argv[0]).startswith(inside)
        if mine and not TOOLS.intersection(argv[1:]):
            found.append((pid, info["create_time"]))
    return found


def alive(life: Lifetime) -> bool:
    """Whether this run of the IDE still runs; a reused pid is a different run."""
    with suppress(ChildProcessError):
        os.waitpid(life.pid, os.WNOHANG)  # reaps an IDE jbctl itself started, once it has ended
    info = toolbox.snapshot(life.pid, "create_time", "status")
    return bool(info) and info["create_time"] == life.created and info["status"] != psutil.STATUS_ZOMBIE


def about(install: Install, life: Lifetime) -> Answer:
    """Whether the built-in web server answers /api/about with this install's build, and if not, what each port
    said; the detail reaches status's note and the not-ready refusal."""
    said: list[str] = []
    for port in sorted(toolbox.listening(life.pid) & set(WEB_PORTS)):
        try:
            response = httpx.get(f"http://127.0.0.1:{port}/api/about", timeout=2)
        # A port that does not speak HTTP, or a server still starting: recorded in the answer's detail.
        except httpx.HTTPError as error:
            said.append(f"{port}: {type(error).__name__}")
            continue
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            return Answer(ready=False, busy=True, detail=f"{port}: HTTP 429")
        try:
            build = response.json().get("buildNumber") if response.status_code == HTTPStatus.OK else None
        # A body that is not JSON (ValueError), or JSON that is not an object (AttributeError): in the detail too.
        except ValueError, AttributeError:
            said.append(f"{port}: HTTP {response.status_code}, not a JSON object")
            continue
        if build == install.build:
            return Answer(ready=True, busy=False, detail="")
        said.append(f"{port}: HTTP {response.status_code}, build {build}")
    nothing = f"no port in {WEB_PORTS.start}-{WEB_PORTS.stop - 1} listens"
    return Answer(ready=False, busy=False, detail="; ".join(said) or nothing)


class NotReadyError(IdeError):
    """The IDE runs but was not ready in time: unlike a refusal, jbctl has already started it."""


def ready(install: Install, life: Lifetime, deadline: float) -> None:
    asked, answer = 0.0, Answer(ready=False, busy=False, detail="not asked yet")
    while alive(life):  # checked once more after the deadline: it may have ended during the last request or sleep
        if time.monotonic() >= deadline:
            msg = (
                f"pid {life.pid} is still running but was not ready in time: /api/about did not answer with build "
                f"{install.build} ({answer.detail}); wait and check jbctl status, or stop it with jbctl stop"
            )
            raise NotReadyError(msg)
        if time.monotonic() >= asked:
            answer = about(install, life)
            if answer.ready:
                return
            asked = time.monotonic() + (BACKOFF if answer.busy else ASK)
        time.sleep(POLL)
    msg = f"pid {life.pid} ended before it was ready"
    raise IdeError(msg)


def arrival(install: Install, before: set[Lifetime], deadline: float) -> Lifetime:
    """The one IDE run from the install's app that was not running before."""
    while time.monotonic() < deadline:
        new = [life for life in toolbox.lifetimes(Path(install.app)) if life not in before]
        if len(new) > 1:
            msg = f"{len(new)} new IDEs came up from {install.app}; jbctl cannot tell which is its own"
            raise IdeError(msg)
        if new:
            return new[0]
        time.sleep(POLL)
    msg = f"no IDE came up from {install.app} in time"
    raise IdeError(msg)


def ended(life: Lifetime, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while alive(life):
        if time.monotonic() >= deadline:
            return False
        time.sleep(POLL)
    return True


def dialogs(pid: int) -> str | None:
    """Why the IDE must not be asked to quit now: a window other than a project frame or the Welcome screen (a
    dialog, Settings, a popup) or one whose state cannot be read may hold its user's unapplied edits, and a forced
    quit dismisses every dialog.

    Settings is not AX-modal (measured in CLion 2026.3), so the modal flag alone misses it. jbax tells frames
    apart by their AX subrole (a titled standard window), not by title, so the check holds in any language.
    """
    try:
        listed = ide.jbax("windows", str(pid))["windows"]
    except IdeError as error:
        return f"its windows cannot be inspected ({error})"
    if held := [window for window in listed if window["kind"] not in QUIET or window["modal"] is not False]:
        return f"{len(held)} dialog or unreadable windows are open; they may hold unapplied edits, so close them first"
    return None


def occupant(target: Install, everything: list[Install], exempt: Lifetime | None) -> str | None:
    """Why starting the target now could make two IDEs share settings: another install of the product runs, or
    the target's config directory names a live process in its .lock (the IDE writes its pid there)."""
    for other in (install for install in everything if install.product_code == target.product_code):
        for pid, created in processes(other):
            if exempt is None or (pid, created) != (exempt.pid, exempt.created):
                return f"{other.script} (pid {pid}) runs, and another {target.tool_id} could share its settings"
    lock = Path(target.config) / ".lock"
    if lock.is_file():
        owner = lock.read_text().strip()
        if not owner.isdigit():
            return f"{lock} names no pid, so jbctl cannot tell who holds that config directory"
        if (exempt is None or int(owner) != exempt.pid) and psutil.pid_exists(int(owner)):
            return f"its config directory is in use by pid {owner} ({lock})"
    return None


def locks(target: Install) -> ExitStack:
    """Hold off another jbctl acting on this IDE, its product or its config directory, in a fixed order."""
    folder = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "jbctl/lifecycle"
    folder.mkdir(parents=True, exist_ok=True)
    # Both names come from outside (Toolbox's state.json, the launcher's options), so they are hashed: no path in them.
    config = hashlib.sha256(os.path.realpath(target.config).encode()).hexdigest()[:16]
    code = hashlib.sha256(target.product_code.encode()).hexdigest()[:16]
    stack = ExitStack()
    try:
        for name in sorted([f"config-{config}.lock", f"product-{code}.lock"]):
            stack.enter_context(filelock.FileLock(folder / name, timeout=0))
    except filelock.Timeout:
        stack.close()
        msg = "another jbctl is starting, stopping or restarting this IDE, its product or its config directory"
        raise IdeError(msg) from None
    return stack


def request(target: Install, life: Lifetime, body: dict[str, bool]) -> None:
    """POST /exit to the pinned run, after checking it is still the IDE that owns the station socket."""
    if life not in toolbox.lifetimes(Path(target.app)):
        msg = f"pid {life.pid} is no longer the IDE jbctl picked; nothing was sent"
        raise IdeError(msg)
    status, reply = station.post(life.pid, "/exit", body, ide.helper_timeout())
    if status != HTTPStatus.OK:
        msg = f"the IDE refused /exit: HTTP {status} {reply}"
        raise IdeError(msg)


def one(target: Install) -> Lifetime:
    lives = toolbox.lifetimes(Path(target.app))
    if len(lives) != 1:
        msg = f"{len(lives)} IDEs run from {target.app}; want exactly one"
        raise IdeError(msg)
    return lives[0]


def still(life: Lifetime, timeout: float) -> str:
    return (
        f"pid {life.pid} still runs after {timeout:g} s: the IDE may be asking a question (a running process, "
        "unsaved work); answer it in the IDE or wait. Nothing was killed."
    )


def start(target: Install, everything: list[Install], project: str | None, timeout: float) -> Lifecycle:
    if project is not None and not Path(project).is_dir():
        msg = f"{project} is not a folder"
        raise IdeError(msg)
    with locks(target):
        if running := processes(target):
            msg = f"{target.script} already runs as pid {running[0][0]}"
            raise IdeError(msg)
        if reason := occupant(target, everything, None):
            raise IdeError(reason)
        before = set(toolbox.lifetimes(Path(target.app)))
        argv = [target.launch, *([str(Path(project).resolve())] if project else [])]
        # As Toolbox's background mode runs it: the executable itself, in its own session, with no terminal.
        null = [(os.POSIX_SPAWN_OPEN, fd, os.devnull, os.O_RDWR, 0) for fd in (0, 1, 2)]
        os.posix_spawn(target.launch, argv, os.environ, file_actions=null, setsid=True)
        deadline = time.monotonic() + timeout
        life = arrival(target, before, deadline)
        try:
            ready(target, life, deadline)
        # jbctl launched it and it still runs: say so, rather than "refused", so nothing starts it a second time.
        except NotReadyError as error:
            return Lifecycle(script=target.script, action=Action.started_not_ready, pid=life.pid, reason=str(error))
    return Lifecycle(script=target.script, action=Action.started, pid=life.pid)


def stop(target: Install, timeout: float, *, force: bool, check: bool) -> Lifecycle:
    with locks(target):
        life = one(target)
        if reason := dialogs(life.pid):
            raise IdeError(reason)
        if check:
            return Lifecycle(script=target.script, action=Action.would_stop, pid=life.pid)
        request(target, life, QUIT)
        if not ended(life, timeout) and force:
            # A dialog that appeared during the wait may be the IDE's exit question or its user's own work: a
            # forced quit would dismiss it, so it is sent only when none is open.
            if reason := dialogs(life.pid):
                msg = f"{still(life, timeout)} No forced quit was sent: {reason}"
                raise IdeError(msg)
            request(target, life, QUIT | {"force": True})
            ended(life, timeout)
        if alive(life):
            raise IdeError(still(life, timeout * (2 if force else 1)))
    return Lifecycle(script=target.script, action=Action.stopped, pid=life.pid)


def restart(target: Install, everything: list[Install], timeout: float, *, check: bool) -> Lifecycle:
    with locks(target):
        life = one(target)
        if reason := dialogs(life.pid) or occupant(target, everything, life):
            raise IdeError(reason)
        # One /api/about request: a restart of an IDE that is not ready yet (perhaps from the last restart) waits.
        if not about(target, life).ready:
            msg = f"pid {life.pid} is not ready yet; wait (jbctl status) or stop it"
            raise IdeError(msg)
        if check:
            return Lifecycle(script=target.script, action=Action.would_restart, pid=life.pid)
        before = set(toolbox.lifetimes(Path(target.app)))
        request(target, life, QUIT | {"restart": True})
        if not ended(life, timeout):
            raise IdeError(still(life, timeout))
        deadline = time.monotonic() + timeout
        new = arrival(target, before, deadline)
        try:
            ready(target, new, deadline)
        except NotReadyError as error:
            not_ready = Action.restarted_not_ready
            return Lifecycle(
                script=target.script, action=not_ready, pid=new.pid, previous_pid=life.pid, reason=str(error)
            )
    return Lifecycle(script=target.script, action=Action.restarted, pid=new.pid, previous_pid=life.pid)


def pick(options: Status | Start | Stop | Restart, everything: list[Install]) -> list[Install]:
    """The installs --ide and --product name, in order and once each; --all is handled by the caller."""
    chosen = {name: toolbox.install(name) for name in options.ide}
    if options.product:
        same = [install for install in everything if install.tool_id == options.product]
        if not same:
            ids = ", ".join(sorted({install.tool_id for install in everything}))
            msg = f"Toolbox has no IDE with tool id {options.product}; its tool ids are {ids}"
            raise IdeError(msg)
        if not isinstance(options, Status):
            same = product(options, same)
        chosen |= {install.script: install for install in same}
    return list(chosen.values())


def product(options: Start | Stop | Restart, same: list[Install]) -> list[Install]:
    """The one install --product means: the only install of it (start), or the only one running."""
    scripts = ", ".join(install.script for install in same)
    if isinstance(options, Start):
        if len(same) > 1:
            msg = f"{options.product} has {len(same)} installs ({scripts}); pick one with --ide"
            raise IdeError(msg)
        return same
    up = [install for install in same if toolbox.lifetimes(Path(install.app))]
    if len(up) > 1:
        msg = f"{len(up)} installs of {options.product} run ({', '.join(i.script for i in up)}); pick one with --ide"
        raise IdeError(msg)
    if not up:
        msg = f"no install of {options.product} runs ({scripts})"
        raise IdeError(msg)
    return up


def alone(options: Status | Start | Stop | Restart) -> None:
    """--all excludes --ide and --product. Checked here because the schema cannot carry it to the models:
    datamodel-codegen drops if/then and not, and an anyOf of exclusive field sets becomes a union of models
    (Start1 | Start2), while CliApp parses one model class per command (as with check-direct's --ide/--mcp-url)."""
    if options.all and (options.ide or options.product):
        msg = "--all picks every IDE; leave out --ide and --product"
        raise ValueError(msg)


def status(options: Status) -> list[IdeStatus]:
    alone(options)
    everything = toolbox.installs()
    if options.all or options.ide or options.product:
        return [describe(install) for install in (everything if options.all else pick(options, everything))]
    return [row for row in map(describe, everything) if row.state != IdeState.stopped]


def describe(install: Install) -> IdeStatus:
    row = IdeStatus(script=install.script, tool_id=install.tool_id, state=IdeState.stopped)
    lives = toolbox.lifetimes(Path(install.app))
    if not lives:
        if started := processes(install):
            return row.model_copy(update={"state": IdeState.starting, "pid": started[0][0]})
        return row
    life = lives[0]
    answer = about(install, life)
    # Two IDEs from one install (one started outside jbctl): status shows the first, stop and restart refuse.
    pids = ", ".join(str(pid) for pid in sorted(other.pid for other in lives))
    notes = [f"{len(lives)} IDEs run from this install (pids {pids})"] if len(lives) > 1 else []
    update: dict[str, object] = {"state": IdeState.ready if answer.ready else IdeState.not_ready, "pid": life.pid}
    try:
        port, source = toolbox.mcp_port(install)
    # An unreadable or malformed mcpServer.xml (ET.ParseError is a SyntaxError), or a port that is not a number.
    except (OSError, SyntaxError, ValueError) as error:
        notes += [str(error), *([] if answer.ready else [f"/api/about: {answer.detail}"])]
        return row.model_copy(update=update | {"mcp": McpState.unknown, "note": "; ".join(notes)})
    answering = port in toolbox.listening(life.pid) and mcp.answers(f"http://127.0.0.1:{port}/stream")
    notes += [] if answering else [f"nothing answered MCP on {port} ({source})"]
    notes += [] if answer.ready else [f"/api/about: {answer.detail}"]
    mcp_state = McpState.answering if answering else McpState.not_answering
    return row.model_copy(update=update | {"mcp": mcp_state, "mcp_port": port, "note": "; ".join(notes) or None})


def plan(options: Start | Stop | Restart, everything: list[Install]) -> list[Lifecycle | Install]:
    """What --all would act on: the installs, and a skipped line for each one it leaves alone."""
    if not isinstance(options, Start):
        return [install for install in everything if toolbox.lifetimes(Path(install.app))]
    found: list[Lifecycle | Install] = []
    for tool_id in sorted({install.tool_id for install in everything}):
        same = [install for install in everything if install.tool_id == tool_id]
        scripts = ", ".join(install.script for install in same)
        if len(same) > 1:
            reason = f"{tool_id} has {len(same)} installs ({scripts}); pick one with --ide"
            found += [Lifecycle(script=install.script, action=Action.skipped, reason=reason) for install in same]
        elif running := processes(same[0]):
            reason = f"already runs as pid {running[0][0]}"
            found.append(Lifecycle(script=same[0].script, action=Action.skipped, reason=reason))
        else:
            found.append(same[0])
    return found


def act(options: Start | Stop | Restart) -> Iterator[Lifecycle]:
    """One Lifecycle per IDE, in order; a refusal for one IDE does not stop the others."""
    alone(options)
    everything = toolbox.installs()
    targets = plan(options, everything) if options.all else pick(options, everything)
    if not targets:
        msg = "nothing to act on: name IDEs with --ide or --product, or use --all"
        raise ValueError(msg)
    acting = [target for target in targets if isinstance(target, Install)] and (options.yes or not options.all)
    # restart --check sends nothing, so it brings nothing forward.
    forward = isinstance(options, Start) or (isinstance(options, Restart) and not options.check)
    if acting and forward and not (options.foreground or os.environ.get(ide.FOREGROUND) == "1"):
        msg = (
            f"{type(options).__name__.lower()} brings the IDE forward (measured on every launch and restart); pass "
            f"--foreground or set {ide.FOREGROUND}=1, only with the owner's go"
        )
        raise IdeError(msg)
    would = (
        Action.would_start
        if isinstance(options, Start)
        else Action.would_stop
        if isinstance(options, Stop)
        else Action.would_restart
    )
    for target in targets:
        if isinstance(target, Lifecycle):
            yield target
        # Only a plan when nothing would be checked: --check runs every IDE's guards, sending nothing, without --yes.
        elif options.all and not options.yes and not (isinstance(options, Stop | Restart) and options.check):
            yield Lifecycle(script=target.script, action=would)
        else:
            try:
                yield run(options, target, everything)
            # A refusal, a station that hung up (httpx), a launch that failed (OSError) or a process jbctl may not
            # read (psutil): that IDE's line says so, and the rest still run.
            except (IdeError, httpx.HTTPError, OSError, psutil.Error) as error:
                yield Lifecycle(script=target.script, action=Action.refused, reason=str(error))


def run(options: Start | Stop | Restart, target: Install, everything: list[Install]) -> Lifecycle:
    match options:
        case Start():
            return start(target, everything, options.project, options.timeout)
        case Stop():
            return stop(target, options.timeout, force=options.force, check=options.check)
        case _:
            return restart(target, everything, options.timeout, check=options.check)
