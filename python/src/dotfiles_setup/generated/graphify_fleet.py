# Copyright (c) 2026 Raymond Manaloto
"""Generated graphify-fleet models; edit the schema and rerun `mise run codegen`."""

from enum import StrEnum
from typing import Annotated

from dotfiles_setup.codec import Meta
from dotfiles_setup.codec import Struct as _Struct


class Struct(_Struct, forbid_unknown_fields=True):
    """Generated msgspec base type; see the schema it was generated from."""


class LegName(StrEnum):
    """One independently pinned graphify surface."""

    dotfiles = "dotfiles"
    kb = "kb"
    host = "host"


class LegState(StrEnum):
    """Currency of a leg against the upstream latest release."""

    current = "current"
    behind = "behind"
    drift = "drift"
    unverifiable = "unverifiable"


class Upstream(Struct):
    """The newest upstream graphify release, or why it is unknown."""

    repo: str
    version: str | None
    error: str | None


class PinSite(Struct):
    """One place a graphify version or revision is recorded."""

    location: str
    value: str | None


class Leg(Struct):
    """One pinned surface, its sites, and every finding about it."""

    name: LegName
    state: LegState
    version: str | None
    sites: list[PinSite]
    findings: list[str]


type FeatureHitsAdditionalProperty = Annotated[int, Meta(ge=0)]


class ForkProbe(Struct):
    """Whether upstream's latest tag contains every probed fork term."""

    tag: str | None
    feature_hits: dict[str, FeatureHitsAdditionalProperty]
    control_hits: Annotated[int, Meta(ge=0)] | None
    native: bool | None
    error: str | None


class PlanStep(Struct):
    """One ordered action; human-gated steps are printed, never run."""

    leg: LegName
    summary: str
    commands: list[str]
    human_gate: bool
    runnable: bool


class FleetPlan(Struct):
    """Graphify pin state across dotfiles, KB and host, with ordered steps."""

    upstream: Upstream
    legs: list[Leg]
    fork_probe: ForkProbe
    verdict: LegState
    steps: list[PlanStep]
