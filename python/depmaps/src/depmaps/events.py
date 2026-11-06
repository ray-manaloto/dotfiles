"""JSON-line events: results and the end of a command on stdout, caught errors on stderr."""

import sys

from .models import Change, DepStatus, Done, Error, ErrorCode, FileChange, Mapped, Pruned


class DepmapsError(Exception):
    """A failure a step turns into one Error event; the command then exits 1."""

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def emit(event: Change | DepStatus | Done | Error | FileChange | Mapped | Pruned) -> None:
    stream = sys.stderr if isinstance(event, Error) else sys.stdout
    stream.write(event.model_dump_json() + "\n")
    stream.flush()
