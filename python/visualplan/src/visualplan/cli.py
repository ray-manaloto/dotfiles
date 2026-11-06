"""visualplan render <plan.json> <page.html>: write the plan's page, or one JSON error line and exit 2."""

import argparse
import sys
import tempfile
from pathlib import Path

from pydantic import BaseModel, ValidationError

from .models import Failure, Wrote
from .page import GENERATOR, load, render

DATA_ERROR = 2


class ForeignFileError(Exception):
    """The page path holds a file visualplan did not write."""


def emit(model: BaseModel, *, err: bool = False) -> None:
    (sys.stderr if err else sys.stdout).write(model.model_dump_json() + "\n")


def write(out: Path, text: str) -> None:
    """A fresh file in the page's folder renamed over it, so a reader never sees half a page."""
    # Only a page carrying GENERATOR is replaced. That refuses the plan itself too: a JSON file cannot hold the
    # marker as written, since a quote inside a JSON string is escaped.
    if out.is_file() and GENERATOR not in out.read_text(errors="replace"):
        msg = f"{out} is not a page visualplan wrote: move it away or write the page to another file"
        raise ForeignFileError(msg)
    # SIM115: opened outside a with-block so the try below also unlinks it when the write or close fails.
    fresh = tempfile.NamedTemporaryFile("w", dir=out.parent, prefix=f".{out.name}.", delete=False)  # noqa: SIM115
    try:
        with fresh:
            fresh.write(text)
        Path(fresh.name).replace(out)  # os.replace: atomic within one folder
    except OSError:
        Path(fresh.name).unlink()
        raise


def main(argv: list[str] | None = None) -> int:
    top = argparse.ArgumentParser(prog="visualplan", description=__doc__)
    sub = top.add_subparsers(dest="command", required=True)
    render_cmd = sub.add_parser("render", help="write the page for a plan.json")
    render_cmd.add_argument("plan", type=Path)
    render_cmd.add_argument("page", type=Path)
    args = top.parse_args(argv)
    try:
        write(args.page, render(load(args.plan)))
    # The plan cannot be read or the page written (OSError), the plan breaks the schema (ValidationError) or the page
    # path holds another file (ForeignFileError): each becomes the one error line.
    except (OSError, ValidationError, ForeignFileError) as error:
        emit(Failure(error=str(error)), err=True)
        return DATA_ERROR
    emit(Wrote(wrote=str(args.page)))
    return 0
