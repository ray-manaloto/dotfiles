# Copyright (c) 2026 Raymond Manaloto
"""Generated drift-verdict enum; edit the schema and rerun `mise run codegen`."""

from enum import IntEnum


class DriftVerdict(IntEnum):
    """Exit code of an OFFLINE drift check: in sync, drift, or error."""

    IN_SYNC = 0
    DRIFT = 1
    ERROR = 2
