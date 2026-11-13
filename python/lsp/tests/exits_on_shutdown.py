"""A language server that answers initialize and dies on shutdown, as tsc 7.0.2 now and then does (probe.session)."""

import os
import sys

from lsprotocol import types
from pygls.lsp.server import LanguageServer

server = LanguageServer("exits-on-shutdown", "1.0")


@server.feature(types.SHUTDOWN)
def shutdown(_server: LanguageServer, _params: None) -> None:
    sys.stderr.write("panic: assignment to entry in nil map\n")
    sys.stderr.flush()
    os._exit(2)


server.start_io()
