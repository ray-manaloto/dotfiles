# Copyright (c) 2026 Raymond Manaloto
"""Generated saved-search file models; edit the schema and rerun codegen."""

from enum import StrEnum
from typing import Annotated, Literal

from msgspec import UNSET, Meta, UnsetType, field
from msgspec import Struct as _Struct


class Struct(_Struct, forbid_unknown_fields=True):
    """Generated msgspec base type; see the schema it was generated from."""


class WatchKind(StrEnum):
    """GitHub search endpoint family."""

    code = "code"
    issues = "issues"
    discussions = "discussions"
    releases = "releases"


class CodeRole(StrEnum):
    """Evidence or positive-control role of a code search."""

    query = "query"
    must_hit = "must-hit"
    health = "health"
    readme = "readme"


class Cadence(StrEnum):
    """Expected refresh interval for a saved search."""

    daily = "daily"
    weekly = "weekly"


class Collect(StrEnum):
    """Top limit hits, or every hit up to the 1000 cap (default for code queries)."""

    top = "top"
    all = "all"


class Watch(Struct):
    """One reproducible search with optional draft controls."""

    id: Annotated[str, Meta(pattern="^[a-z0-9][a-z0-9-]{0,79}$")]
    kind: WatchKind
    queries: Annotated[list[str], Meta(min_length=1)]
    origin: str | UnsetType = UNSET
    question: str | UnsetType = UNSET
    cadence: Cadence | UnsetType = UNSET
    tags: list[str] | UnsetType = UNSET
    limit: Annotated[int, Meta(ge=1, le=100)] | UnsetType = UNSET
    repo: (
        Annotated[str, Meta(pattern="^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")] | UnsetType
    ) = UNSET
    role: CodeRole | UnsetType = UNSET
    collect: Collect | UnsetType = UNSET
    grep: str | UnsetType = UNSET
    path_grep: str | UnsetType = UNSET
    control_hit: str | UnsetType = UNSET
    control_hit_grep: str | UnsetType = UNSET
    control_hit_path_grep: str | UnsetType = UNSET
    control_absent: str | UnsetType = UNSET


class Result(Struct):
    """Baseline observation for one watch."""

    watch_id: str
    date_run: str
    status: str | UnsetType = UNSET
    count: Annotated[int, Meta(ge=-1)] | UnsetType = UNSET
    total_count: Annotated[int, Meta(ge=-1)] | UnsetType = UNSET
    urls: list[str] | UnsetType = UNSET


class SavedSearchFile(Struct):
    """Tracked searches and their recorded baselines."""

    schema_version: Literal[1]
    watch: list[Watch]
    question: str | UnsetType = UNSET
    origin: str | UnsetType = UNSET
    result: list[Result] | UnsetType = field(default_factory=list)
