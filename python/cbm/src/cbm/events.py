"""JSON-line events: checks and the end of a command on stdout, caught errors on stderr."""

import sys

from .models import Check, Done, Error


def emit(event: Check | Done | Error) -> None:
    stream = sys.stderr if isinstance(event, Error) else sys.stdout
    stream.write(event.model_dump_json() + "\n")
    stream.flush()


def check(name: str, *, ok: bool, detail: str = "") -> bool:
    emit(Check(name=name, ok=ok, detail=detail))
    return ok
