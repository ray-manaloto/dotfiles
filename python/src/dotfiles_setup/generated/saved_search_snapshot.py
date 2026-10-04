# Copyright (c) 2026 Raymond Manaloto
"""Generated saved-search snapshot models; edit the schema and rerun codegen."""

from enum import StrEnum
from typing import Annotated

from dotfiles_setup.codec import UNSET, Meta, UnsetType
from dotfiles_setup.codec import Struct as _Struct


class Struct(_Struct, forbid_unknown_fields=True):
    """Generated msgspec base type; see the schema it was generated from."""


class RerunStatus(StrEnum):
    """Verified answer or explicit failure of a rerun."""

    ok = "ok"
    empty_verified = "empty-verified"
    empty_unarmed = "empty-unarmed"
    rate_limited = "rate-limited"
    incomplete = "incomplete"
    uncollectable = "uncollectable"
    error = "error"


class Kind(StrEnum):
    """GitHub search endpoint family."""

    code = "code"
    issues = "issues"
    discussions = "discussions"
    releases = "releases"


class WatchRun(Struct):
    """Search outcome with its count and returned URLs."""

    id: str
    kind: Annotated[Kind, Meta(description="GitHub search endpoint family.")]
    query: str
    repo: str | None
    status: RerunStatus
    count: Annotated[int, Meta(ge=-1)]
    urls: list[str]
    confirmed: Annotated[int, Meta(ge=0)] | None
    reason: str | None
    complete: (
        Annotated[
            bool, Meta(description="True when every hit was collected (collect all).")
        ]
        | UnsetType
    ) = UNSET


class SearchControl(Struct):
    """Fresh positive or negative control outcome."""

    role: str
    query: str
    count: Annotated[int, Meta(ge=-1)]
    rc: int
    status: RerunStatus


class SavedSearchSnapshot(Struct):
    """One saved-search rerun and its fresh controls."""

    file: str
    generated_at: str
    watches: list[WatchRun]
    controls: list[SearchControl]
