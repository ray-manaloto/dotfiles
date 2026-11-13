"""Talk to a language server the way Claude Code starts it: pygls's client over stdio, no JSON-RPC of our own."""

import asyncio
import os
import signal
import subprocess
from pathlib import Path

from lsprotocol import types
from pygls.lsp.client import LanguageClient

from .models import Check, PluginServer, Probe
from .tools import limit

# Each request's limit, in seconds. clangd answers references only after it has parsed the files it opened.
REQUEST = ("LSPTOOLS_REQUEST_SECONDS", 60.0)
LANGUAGES = {".ts": "typescript", ".tsx": "typescriptreact", ".cpp": "cpp", ".hpp": "cpp", ".c": "c", ".h": "c"}


def command_of(server: PluginServer, root: Path) -> list[str]:
    """The server's command line, with ${CLAUDE_PLUGIN_ROOT} expanded as Claude Code expands it."""
    return [arg.replace("${CLAUDE_PLUGIN_ROOT}", str(root)) for arg in (server.command, *server.args)]


class Client(LanguageClient):
    """pygls's client, keeping what the server wrote to stderr: why a server that exits at once failed."""

    stderr = ""

    async def server_exit(self, server: asyncio.subprocess.Process) -> None:
        stream = server.stderr
        self.stderr = (await stream.read()).decode(errors="replace") if stream else ""


def children() -> dict[int, str]:
    """This process's children and their command lines: an `sh -c 'exec …'` launcher has become the server."""
    table = subprocess.Popen(["ps", "-A", "-o", "pid=,ppid=,command="], stdout=subprocess.PIPE, text=True)
    out, _ = table.communicate()
    rows = [line.split(None, 2) for line in out.splitlines()]
    me, ps = str(os.getpid()), str(table.pid)
    return {int(pid): command for pid, ppid, command in rows if ppid == me and pid != ps}


async def ended(client: Client, failed: Exception) -> str:
    """Why the server stopped answering, with the end of its stderr, once it is gone: one that hangs is killed first,
    since pygls's stop waits for the process to end."""
    for pid in children():
        os.kill(pid, signal.SIGKILL)
    await client.stop()
    said = " ".join(client.stderr.split()[-60:]) or "nothing on stderr"
    why = str(failed) or f"no answer within {limit(*REQUEST):g} s"
    return f"{why}; stderr: {said}"


async def session(argv: list[str], folder: Path, probe: Probe | None) -> list[Check]:
    """initialize (and with probe, smoke on folder's fixture), then shutdown: one Check per step.

    A server that exits or stops answering before shutdown ends the session with a failed "server" Check.
    """
    client = Client("lsptools", "0.1.0")
    await client.start_io(argv[0], *argv[1:], cwd=folder)
    checks: list[Check] = []
    try:
        await steps(client, folder, probe, checks)
    except (RuntimeError, TimeoutError) as failed:
        return [*checks, Check(name="server", ok=False, detail=await ended(client, failed))]
    try:
        await asyncio.wait_for(client.shutdown_async(None), limit(*REQUEST))
        client.exit(None)
    except (RuntimeError, TimeoutError) as failed:
        # tsc 7.0.2 panics now and then as it shuts down ("assignment to entry in nil map", lspwatcher.go:160: a
        # file watch its background queue adds after shutdown began). Every check before it stands on its own, so
        # this is noted, not failed.
        return [*checks, Check(name="shutdown", ok=True, detail=f"not clean: {await ended(client, failed)}")]
    await client.stop()
    return [*checks, Check(name="shutdown", ok=True, detail="clean")]


async def steps(client: Client, folder: Path, probe: Probe | None, checks: list[Check]) -> None:
    """initialize and smoke, appending each Check as it passes, so a failure keeps the ones before it."""
    result = await asyncio.wait_for(
        client.initialize_async(
            types.InitializeParams(
                process_id=os.getpid(),
                root_uri=folder.as_uri(),
                capabilities=types.ClientCapabilities(),
                workspace_folders=[types.WorkspaceFolder(uri=folder.as_uri(), name=folder.name)],
            )
        ),
        limit(*REQUEST),
    )
    info = result.server_info
    named = f"{info.name} {info.version or ''}".strip() if info else "no serverInfo"
    checks.append(Check(name="initialize", ok=True, detail=f"{named}; {'; '.join(children().values())}"))
    client.initialized(types.InitializedParams())
    if probe:
        checks += await smoke(client, folder, probe)


async def smoke(client: LanguageClient, folder: Path, probe: Probe) -> list[Check]:
    """documentSymbol, hover, definition and references on the fixture, as Claude Code's LSP tool asks them."""
    for name in (probe.defined_in, probe.used_in):
        path = folder / name
        client.text_document_did_open(
            types.DidOpenTextDocumentParams(
                text_document=types.TextDocumentItem(
                    uri=path.as_uri(), language_id=LANGUAGES[path.suffix], version=1, text=path.read_text()
                )
            )
        )
    defined = types.TextDocumentIdentifier(uri=(folder / probe.defined_in).as_uri())
    at = types.Position(line=probe.line, character=probe.character)
    symbols = await asyncio.wait_for(
        client.text_document_document_symbol_async(types.DocumentSymbolParams(text_document=defined)), limit(*REQUEST)
    )
    names = [symbol.name for symbol in symbols or []]
    hover = await asyncio.wait_for(
        client.text_document_hover_async(types.HoverParams(text_document=defined, position=at)), limit(*REQUEST)
    )
    shown = hover.contents.value if hover and isinstance(hover.contents, types.MarkupContent) else ""
    found = await asyncio.wait_for(
        client.text_document_definition_async(types.DefinitionParams(text_document=defined, position=at)),
        limit(*REQUEST),
    )
    targets = found if isinstance(found, list) else [found] if found else []
    uses = await asyncio.wait_for(
        client.text_document_references_async(
            types.ReferenceParams(
                text_document=defined, position=at, context=types.ReferenceContext(include_declaration=True)
            )
        ),
        limit(*REQUEST),
    )
    files = sorted({Path(use.uri).name for use in uses or []})
    return [
        Check(name="documentSymbol", ok=probe.symbol in names, detail=", ".join(names) or "no symbols"),
        Check(name="hover", ok=probe.symbol in shown, detail=" ".join(shown.split())[:200] or "no hover"),
        Check(name="definition", ok=bool(targets), detail=f"{len(targets)} location(s)"),
        Check(
            name="references",
            ok=probe.used_in in files,
            detail=f"{len(uses or [])} in {', '.join(files) or 'no files'}",
        ),
    ]
