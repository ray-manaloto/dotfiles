"""Running JetBrains IDEs, found by their station sockets, and the station's POST /exit."""

import os
import re
import tempfile
from collections.abc import Awaitable, Callable
from pathlib import Path

import anyio
import anyio.to_thread
import httpx
import psutil

from .models import ExitRequest, Failure, Ide, Reason

# Each IDE's station plugin listens on jb.station.ij.<pid>.sock, and the file stays behind when the IDE ends
# (lvillis/za src/command/ide/mod.rs:1974-2059 reads the same name and checks the pid).
SOCKET = re.compile(r"jb\.station\.ij\.(\d+)\.sock")
BUNDLE = re.compile(r"(.+\.app)/Contents/MacOS/[^/]+")
POLL = 0.2
# _CS_DARWIN_USER_TEMP_DIR in the macOS SDK's unistd.h; os.confstr_names does not list it.
DARWIN_USER_TEMP_DIR = 65537


class Refused(Exception):  # noqa: N818 - a refusal the command reports, not a bug
    """A command that cannot go on, with the Failure event it prints."""

    def __init__(self, error: Reason, detail: str, pid: int | None = None) -> None:
        super().__init__(detail)
        self.failure = Failure(error=error, detail=detail, pid=pid)


def folder() -> Path:
    """Where the IDEs bind their sockets: the JVM's temporary folder on macOS, the per-user one confstr gives,
    whatever TMPDIR or XDG_RUNTIME_DIR say. CLION_CTL_STATION_DIR replaces it. confstr gives None off macOS."""
    override = os.environ.get("CLION_CTL_STATION_DIR")
    return Path(override or os.confstr(DARWIN_USER_TEMP_DIR) or tempfile.gettempdir())


def bundle(argv: list[str]) -> str | None:
    """The .app bundle the command line runs from: argv[0] for an IDE, argv[1] for a script run by its shebang."""
    return next((str(Path(found[1]).resolve()) for arg in argv if (found := BUNDLE.fullmatch(arg))), None)


def inspect(pid: int, socket: Path) -> Ide | None:
    """The IDE behind a socket, or None when no live process of this user has that socket open."""
    try:
        process = psutil.Process(pid)
        # Another user's process that reused the pid; its connections would be AccessDenied.
        if process.uids().real != os.getuid():
            return None
        if str(socket) not in {connection.laddr for connection in process.net_connections("unix")}:
            return None
        argv = process.cmdline()
        listening = process.net_connections("tcp")
    # NoSuchProcess (ZombieProcess too): a stale socket.
    except psutil.NoSuchProcess:
        return None
    ports = sorted({connection.laddr.port for connection in listening if connection.status == psutil.CONN_LISTEN})
    return Ide(pid=pid, app=bundle(argv), socket=str(socket), ports=ports)


def scan() -> list[Ide]:
    sockets = sorted(folder().glob("jb.station.ij.*.sock"))
    found = [inspect(int(name[1]), socket) for socket in sockets if (name := SOCKET.fullmatch(socket.name))]
    return [ide for ide in found if ide]


async def running() -> list[Ide]:
    return await anyio.to_thread.run_sync(scan)


def alive(pid: int) -> bool:
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


async def poll[T](check: Callable[[], Awaitable[T | None]]) -> T:
    """The first result of check that is not None; the caller bounds the wait with a cancel scope."""
    # The state is another process's (its pid, its socket, its ports), which sends no event to wait on.
    while (result := await check()) is None:  # noqa: ASYNC110 - see above
        await anyio.sleep(POLL)
    return result


async def exit_ide(ide: Ide, *, restart: bool) -> None:
    """POST /exit with force false: the IDE quits or restarts as its own menu does, saving projects and asking first
    when a process still runs. userInitiated only skips the Exit confirmation (Application.exit's exitConfirmed)."""
    body = ExitRequest(user_initiated=True, force=False, restart=restart).model_dump(by_alias=True)
    transport = httpx.AsyncHTTPTransport(uds=ide.socket)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost", timeout=30) as client:
            response = await client.post("/exit", json=body)
    # The connection failed or the station hung up before it answered.
    except httpx.HTTPError as error:
        raise Refused(Reason.station, f"{ide.socket}: {error!r}", ide.pid) from None
    if response.status_code != httpx.codes.OK:
        missing = response.headers.get("X-Station-Failure", "")
        raise Refused(Reason.station, f"{ide.socket}: POST /exit answered {response.status_code} {missing}", ide.pid)
