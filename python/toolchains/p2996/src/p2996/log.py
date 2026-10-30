"""structlog through stdlib handlers: JSON lines, info on stdout, warnings and errors on stderr (DL-762)."""

import logging
import sys
from typing import TextIO

import structlog

log = structlog.stdlib.get_logger("p2996")


class P2996Error(Exception):
    """A step refused to go on; the CLI logs the message as an error event and exits 1."""


class _Below(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno < logging.WARNING


class _Std(logging.StreamHandler[TextIO]):
    """Writes to whatever sys.stdout or sys.stderr is at emit time (pytest swaps them per test)."""

    def __init__(self, name: str) -> None:
        self._stream_name = name
        super().__init__()

    @property
    def stream(self) -> TextIO:
        return getattr(sys, self._stream_name)

    @stream.setter
    def stream(self, _: object) -> None:
        pass


def configure() -> None:
    """JSON lines from the p2996 logger: below WARNING on stdout, the rest on stderr."""
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[structlog.stdlib.ProcessorFormatter.remove_processors_meta, structlog.processors.JSONRenderer()]
    )
    out = _Std("stdout")
    out.addFilter(_Below())
    err = _Std("stderr")
    err.setLevel(logging.WARNING)
    for handler in (out, err):
        handler.setFormatter(formatter)
    logger = logging.getLogger("p2996")
    logger.handlers = [out, err]
    logger.setLevel(logging.INFO)
    logger.propagate = False
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
