# Copyright (c) 2026 Raymond Manaloto
"""Graphify fleet: every graphify pin across dotfiles, the KB and the host.

``status`` reports each leg against upstream's latest release, ``plan`` orders
the steps that would bring the behind legs current, and ``apply --leg`` runs
the one leg this repo owns (dotfiles, via ``mise run graphify-upgrade``) while
only PRINTING the others: the host leg touches user-level files, and the KB leg
is wired to the KB-owned ``kb-graphify-pin`` task in T8.

Native-first justification (``use-tool-builtins.md``), re-checked 2026-10-04:

- **Renovate** bumps the PyPI ``graphifyy`` lock entry (``renovate.json``'s
  graphifyy rule, ``automerge: false``), but the KB pins a git REV of our fork
  plus derived sites (manifest, currency base, catalog hashes); no Renovate
  manager can replay a fork payload onto a new upstream tag.
- **kb-currency / tool-currency** report each repo's own pins and never apply;
  ``kb-currency-check`` always exits 0, and neither sees the other repo, the
  user-global mise pin and the PATH binary at once.
- **``graphify update`` / ``graphify install``** are the vendor writers this repo
  bans (``do-not.md`` #8); ``mise run graphify-upgrade`` is the sanctioned
  dotfiles writer, and this module only delegates to it.

So the only new logic is the cross-repo READ and the ordering; every per-repo
mechanism is reused (``graphify_currency.check``/``_path_binary_probe``).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from packaging.version import InvalidVersion, Version

from dotfiles_setup import codec, graphify_currency
from dotfiles_setup.generated.drift_verdict import DriftVerdict
from dotfiles_setup.generated.graphify_fleet import (
    FleetPlan,
    ForkProbe,
    Leg,
    LegName,
    LegState,
    PinSite,
    PlanStep,
    Upstream,
)
from dotfiles_setup.graphify_currency import _path_binary_probe

type Run = Callable[..., subprocess.CompletedProcess[str]]

UPSTREAM_REPO = graphify_currency.GITHUB_REPO
KB_REF_DEFAULT = "origin/main"
STAMP_PATHS = (
    Path(".claude/skills/graphify/.graphify_version"),
    Path(".codex/skills/graphify/.graphify_version"),
    Path(".agents/skills/graphify/.graphify_version"),
)
# Terms only our fork's payload introduces; ``claude-cli`` is the control arm,
# a sibling backend upstream DOES ship, so a blind grep cannot read as "absent".
FORK_FEATURE_TERMS: tuple[str, ...] = (
    # 8adbc178, 45371550, 5c755a83: Codex CLI backend and credential/MCP wiring.
    "openai-cli",
    # fe4686da, 6a0ba926: retry a zero-success semantic pass on a second backend.
    "fallback-backend",
    # c38f63d5: watch --semantic extracts automatically on document changes.
    "_run_semantic_extract",
    # c71245de: batched Neo4j/FalkorDB graph push.
    "UNWIND $rows",
    # 3c9b930f: disable only MCP servers Codex can resolve in the extraction cwd.
    "_codex_resolvable_disable_args",
)
FORK_CONTROL_TERM = "claude-cli"
KB_NOT_WIRED = (
    "apply --leg kb is not wired until T8: the KB task `kb-graphify-pin` "
    "does not exist yet. Run `mise run graphify-fleet -- plan` for the "
    "manual KB steps."
)

_GIT_TIMEOUT_SECONDS = 30
_GH_TIMEOUT_SECONDS = 60
_UV_TIMEOUT_SECONDS = 30
_PYPROJECT_PIN_RE = re.compile(r'"graphifyy(?:\[[^\]]*\])?==([^";\s]+)"')
_UV_TOOL_RE = re.compile(r"^graphifyy v(\S+)", re.MULTILINE)
_SEVERITY = {
    LegState.current: 0,
    LegState.drift: 1,
    LegState.behind: 2,
    LegState.unverifiable: 3,
}
# Host first: graphify-upgrade's closing offline check requires the PATH
# binary to equal the new lock, so a stale host pin fails the dotfiles step
# after it has already moved the lock (codex lens F1).
_PLAN_ORDER = (LegName.host, LegName.dotfiles, LegName.kb)
_EXIT = {
    LegState.current: DriftVerdict.IN_SYNC,
    LegState.drift: DriftVerdict.DRIFT,
    LegState.behind: DriftVerdict.DRIFT,
    LegState.unverifiable: DriftVerdict.ERROR,
}


@dataclass(frozen=True)
class FleetRoots:
    """Where each leg's pins are read from."""

    dotfiles: Path
    kb: Path
    kb_ref: str
    fork: Path
    mise_global_config: Path


def default_roots(project_root: Path) -> FleetRoots:
    """Return the canonical checkout locations on this machine."""
    org = Path.home() / "dev/github/ray-manaloto"
    return FleetRoots(
        dotfiles=project_root,
        kb=org / "knowledge-base",
        kb_ref=KB_REF_DEFAULT,
        fork=org / "graphify",
        mise_global_config=Path.home() / ".config/mise/config.toml",
    )


class PathProbe(Protocol):
    """What the host leg reads from ``graphify_currency._path_binary_probe``."""

    @property
    def value(self) -> str | None:
        """The PATH binary's version, or None when it could not be read."""

    @property
    def error(self) -> str:
        """Why ``value`` is None."""

    @property
    def path(self) -> str | None:
        """The resolved binary."""

    @property
    def provenance_note(self) -> str:
        """Which PATH was searched."""


@dataclass(frozen=True)
class FleetProbes:
    """The reused dotfiles currency probes — a seam, so tests need no patching."""

    locked: Callable[[Path], str] = graphify_currency.locked_version
    check: Callable[..., tuple[graphify_currency.Drift, ...]] = graphify_currency.check
    path_binary: Callable[..., PathProbe] = _path_binary_probe


@dataclass
class _LegBuilder:
    name: LegName
    version: str | None = None
    sites: list[PinSite] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    unverifiable: bool = False
    drift: bool = False

    def site(self, location: str, value: str | None) -> None:
        self.sites.append(PinSite(location=location, value=value))

    def blind(self, finding: str) -> None:
        self.findings.append(f"UNVERIFIABLE: {finding}")
        self.unverifiable = True

    def drifted(self, finding: str) -> None:
        self.findings.append(finding)
        self.drift = True

    def build(self, upstream: str | None) -> Leg:
        state = LegState.current
        if self.unverifiable or self.version is None:
            state = LegState.unverifiable
        elif upstream is None:
            self.findings.append("UNVERIFIABLE: upstream latest unknown")
            state = LegState.unverifiable
        elif self.drift:
            # Drift outranks behind: a version move built on sites that
            # disagree would carry the disagreement forward (codex lens F2).
            if _older(self.version, upstream):
                self.findings.append(f"also behind upstream {upstream}")
            state = LegState.drift
        elif _older(self.version, upstream):
            state = LegState.behind
        return Leg(
            name=self.name,
            state=state,
            version=self.version,
            sites=self.sites,
            findings=self.findings,
        )


def _older(version: str, upstream: str) -> bool:
    try:
        return Version(version) < Version(upstream)
    except InvalidVersion:
        return False


def _call(
    run: Run, argv: list[str], *, timeout: int
) -> subprocess.CompletedProcess[str] | str:
    """Run one read-only probe; return its result or the failure text."""
    try:
        return run(argv, capture_output=True, text=True, check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"{' '.join(argv)}: {exc}"


def probe_upstream(run: Run) -> Upstream:
    """Return upstream's latest release tag (the only network call)."""
    argv = ["gh", "release", "view", "-R", UPSTREAM_REPO, "--json", "tagName"]
    result = _call(run, [*argv, "--jq", ".tagName"], timeout=_GH_TIMEOUT_SECONDS)
    if isinstance(result, str):
        return Upstream(repo=UPSTREAM_REPO, version=None, error=result)
    tag = result.stdout.strip()
    if result.returncode != 0 or not tag:
        detail = result.stderr.strip() or f"gh release view exited {result.returncode}"
        return Upstream(repo=UPSTREAM_REPO, version=None, error=detail)
    version = tag.removeprefix("v")
    try:
        Version(version)
    except InvalidVersion:
        return Upstream(
            repo=UPSTREAM_REPO, version=None, error=f"unparsable tag {tag!r}"
        )
    return Upstream(repo=UPSTREAM_REPO, version=version, error=None)


def _dotfiles_leg(roots: FleetRoots, probes: FleetProbes) -> _LegBuilder:
    leg = _LegBuilder(LegName.dotfiles)
    root = roots.dotfiles
    try:
        leg.version = probes.locked(root)
    except graphify_currency.GraphifyCurrencyError as exc:
        leg.blind(str(exc))
    leg.site("python/uv.lock", leg.version)
    for stamp in STAMP_PATHS:
        path = root / stamp
        value = path.read_text(encoding="utf-8").strip() if path.is_file() else None
        leg.site(str(stamp), value)
    # The PATH-binary axis is the host leg's; everything else check() finds
    # (installed!=locked, receipt, stamps, skill bytes) is this repo's.
    for drift in probes.check(root, offline=True):
        if drift.kind == "path-binary":
            continue
        finding = f"[{drift.kind}] {drift.detail}"
        if "UNVERIFIABLE" in drift.detail:
            leg.blind(finding)
        else:
            leg.drifted(finding)
    return leg


class _ProbeError(RuntimeError):
    """A read-only probe could not answer."""


def _git(run: Run, repo: Path, *args: str, ok: tuple[int, ...] = (0,)) -> str:
    """Run one read-only git command in ``repo``; raise unless its rc is ``ok``."""
    result = _call(run, ["git", "-C", str(repo), *args], timeout=_GIT_TIMEOUT_SECONDS)
    if isinstance(result, str):
        raise _ProbeError(result)
    if result.returncode not in ok or result.stderr.strip():
        detail = result.stderr.strip() or f"exited {result.returncode}"
        message = f"git {' '.join(args)}: {detail}"
        raise _ProbeError(message)
    return result.stdout


def _git_show(run: Run, roots: FleetRoots, path: str) -> str:
    """Return ``<kb_ref>:<path>`` from the KB clone, never its working tree."""
    return _git(run, roots.kb, "show", f"{roots.kb_ref}:{path}")


def _manifest_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        fields[key.strip()] = value.strip()
    return fields


def _lock_entry(text: str) -> tuple[str | None, str | None]:
    payload = tomllib.loads(text)
    for package in payload.get("package", []):
        if isinstance(package, dict) and package.get("name") == "graphifyy":
            source = package.get("source", {})
            git = source.get("git", "") if isinstance(source, dict) else ""
            return package.get("version"), git.rpartition("#")[2] or None
    return None, None


def _kb_leg(run: Run, roots: FleetRoots) -> tuple[_LegBuilder, str | None, str | None]:
    """Return the KB leg plus its fork commit and fork base ref."""
    leg = _LegBuilder(LegName.kb)
    leg.findings.append(f"read from {roots.kb}@{roots.kb_ref} (no fetch)")
    try:
        pyproject = _git_show(run, roots, "pyproject.toml")
        sources = tomllib.loads(pyproject).get("tool", {}).get("uv", {})
        lock_version, lock_rev = _lock_entry(_git_show(run, roots, "uv.lock"))
        manifest = _manifest_fields(_git_show(run, roots, "sources/graphify.manifest"))
        currency = tomllib.loads(_git_show(run, roots, "currency.toml"))
    except (_ProbeError, tomllib.TOMLDecodeError) as exc:
        leg.blind(str(exc))
        return leg, None, None

    pin = _PYPROJECT_PIN_RE.search(pyproject)
    source_rev = sources.get("sources", {}).get("graphifyy", {}).get("rev")
    fork = currency.get("tool", {}).get("graphify", {}).get("fork", {})
    base_ref = fork.get("base_ref")

    leg.version = pin.group(1) if pin else None
    leg.site("pyproject.toml graphifyy==", leg.version)
    leg.site("pyproject.toml [tool.uv.sources] rev", source_rev)
    leg.site("uv.lock graphifyy version", lock_version)
    leg.site("uv.lock graphifyy rev", lock_rev)
    leg.site("sources/graphify.manifest ref", manifest.get("ref"))
    leg.site("sources/graphify.manifest commit", manifest.get("commit"))
    leg.site("currency.toml [tool.graphify.fork] base_ref", base_ref)

    if leg.version is None:
        leg.blind("pyproject.toml has no exact graphifyy== pin")
    if lock_version != leg.version:
        leg.drifted(f"uv.lock version {lock_version} != pyproject {leg.version}")
    revs = {source_rev, lock_rev, manifest.get("commit")}
    if len(revs) != 1 or None in revs:
        leg.drifted(f"fork revisions disagree across sites: {sorted(map(str, revs))}")
    if base_ref is not None and leg.version and base_ref != f"v{leg.version}":
        leg.drifted(f"fork base_ref {base_ref} != v{leg.version}")
    return leg, source_rev, base_ref


def _global_pin(path: Path) -> str | None:
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    entry = payload.get("tools", {}).get(graphify_currency.MISE_TOOL)
    if isinstance(entry, dict):
        entry = entry.get("version")
    return entry if isinstance(entry, str) else None


def _host_leg(
    run: Run, roots: FleetRoots, probes: FleetProbes
) -> tuple[_LegBuilder, bool]:
    """Return the host leg plus whether a stray ``uv tool`` graphify exists."""
    leg = _LegBuilder(LegName.host)
    try:
        leg.version = _global_pin(roots.mise_global_config)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        leg.blind(f"{roots.mise_global_config}: {exc}")
    leg.site(f"{roots.mise_global_config} {graphify_currency.MISE_TOOL}", leg.version)
    if leg.version is None and not leg.unverifiable:
        leg.blind(f"no {graphify_currency.MISE_TOOL} pin in the user-global config")

    probe = probes.path_binary(run=run)
    leg.site(f"PATH graphify {probe.path or '(absent)'}", probe.value)
    if probe.value is None:
        leg.blind(probe.error)
    elif leg.version is not None and probe.value != leg.version:
        leg.drifted(
            f"PATH graphify {probe.path} reports {probe.value} != "
            f"user-global pin {leg.version} ({probe.provenance_note})"
        )

    stray = False
    result = _call(
        run, ["uv", "tool", "list", "--no-color"], timeout=_UV_TIMEOUT_SECONDS
    )
    if isinstance(result, str) or result.returncode != 0:
        detail = result if isinstance(result, str) else result.stderr.strip()
        leg.blind(f"uv tool list: {detail}")
    elif match := _UV_TOOL_RE.search(result.stdout):
        stray = True
        leg.site("uv tool graphifyy", match.group(1))
        leg.drifted(f"stray `uv tool` graphifyy {match.group(1)} can shadow the pin")
    return leg, stray


def _grep_count(run: Run, roots: FleetRoots, tag: str, term: str) -> int:
    # git grep exits 1 for "no match"; any other rc or stderr is a failed probe.
    stdout = _git(
        run, roots.fork, "grep", "-lF", term, tag, "--", "graphify/", ok=(0, 1)
    )
    return len([line for line in stdout.splitlines() if line.strip()])


def _fork_hits(run: Run, roots: FleetRoots, tag: str) -> tuple[dict[str, int], int]:
    """Return per-feature file counts at ``tag`` plus the control-arm count."""
    try:
        _git(run, roots.fork, "rev-parse", "-q", "--verify", f"{tag}^{{commit}}")
    except _ProbeError as exc:
        message = (
            f"tag {tag} absent from {roots.fork} — fetch tags there first "
            f"(this probe never fetches): {exc}"
        )
        raise _ProbeError(message) from exc
    hits = {term: _grep_count(run, roots, tag, term) for term in FORK_FEATURE_TERMS}
    return hits, _grep_count(run, roots, tag, FORK_CONTROL_TERM)


def probe_fork_features(run: Run, roots: FleetRoots, upstream: str | None) -> ForkProbe:
    """Grep upstream's latest tag for the fork's features, with a control arm."""
    if upstream is None:
        return ForkProbe(
            tag=None,
            feature_hits={},
            control_hits=None,
            native=None,
            error="upstream latest unknown",
        )
    tag = f"v{upstream}"
    try:
        hits, control = _fork_hits(run, roots, tag)
    except _ProbeError as exc:
        return ForkProbe(
            tag=tag, feature_hits={}, control_hits=None, native=None, error=str(exc)
        )
    if control == 0:
        return ForkProbe(
            tag=tag,
            feature_hits=hits,
            control_hits=0,
            native=None,
            error=f"control arm {FORK_CONTROL_TERM!r} found 0 files: probe is blind",
        )
    return ForkProbe(
        tag=tag,
        feature_hits=hits,
        control_hits=control,
        native=all(count > 0 for count in hits.values()),
        error=None,
    )


@dataclass(frozen=True)
class _Context:
    """Facts ``plan`` needs beyond the typed status document."""

    fork_commit: str | None
    fork_base_ref: str | None
    stray_uv_tool: bool


def gather(
    run: Run, roots: FleetRoots, probes: FleetProbes | None = None
) -> tuple[FleetPlan, _Context]:
    """Read every leg; return the status document (no steps) and plan context."""
    probes = probes or FleetProbes()
    upstream = probe_upstream(run)
    latest = upstream.version
    dotfiles = _dotfiles_leg(roots, probes)
    kb, fork_commit, base_ref = _kb_leg(run, roots)
    host, stray = _host_leg(run, roots, probes)
    legs = [dotfiles.build(latest), kb.build(latest), host.build(latest)]
    fork_probe = probe_fork_features(run, roots, latest)
    verdict = max((leg.state for leg in legs), key=_SEVERITY.__getitem__)
    kb_behind = legs[1].state is LegState.behind
    if kb_behind and fork_probe.error is not None:
        verdict = LegState.unverifiable
    status = FleetPlan(
        upstream=upstream, legs=legs, fork_probe=fork_probe, verdict=verdict, steps=[]
    )
    return status, _Context(fork_commit, base_ref, stray)


def _kb_steps(
    status: FleetPlan, leg: Leg, ctx: _Context, roots: FleetRoots
) -> list[PlanStep]:
    latest = status.upstream.version
    if leg.state is LegState.drift:
        return [
            PlanStep(
                leg=leg.name,
                summary="reconcile the KB's disagreeing pin sites (see findings)",
                commands=[],
                human_gate=True,
                runnable=False,
            )
        ]
    probe = status.fork_probe
    if probe.error is not None:
        # An unanswered probe cannot establish that the fork is still needed,
        # so no replay or pin command is printed (codex lens F3).
        return [
            PlanStep(
                leg=leg.name,
                summary=f"fork-feature probe UNVERIFIABLE ({probe.error}): resolve it "
                "before choosing between a fork replay and retiring the fork",
                commands=[],
                human_gate=True,
                runnable=False,
            )
        ]
    if probe.native:
        fork_step = PlanStep(
            leg=leg.name,
            summary=(
                f"upstream {probe.tag} contains all {len(probe.feature_hits)} probed "
                "fork terms: retiring the fork is a human decision (manifest "
                "`clears_when`); confirm against the fork commit list "
                f"(`git log {ctx.fork_base_ref or '<old base tag>'}.."
                f"{ctx.fork_commit or '<KB fork commit>'}`)"
            ),
            commands=[],
            human_gate=True,
            runnable=False,
        )
        new_commit = "<upstream commit>"
    else:
        branch = f"kb-pin/openai-cli-backend-v{latest}"
        commit = ctx.fork_commit or "<KB fork commit>"
        fork_step = PlanStep(
            leg=leg.name,
            summary=(
                f"replay the fork payload onto v{latest} — HUMAN-REVIEWED; stop on "
                "any conflict (fork-maintenance preview first, rebase is the fallback)"
            ),
            commands=[
                (
                    "mise -C <fork-maintenance checkout> run fork-maintenance -- "
                    f"preview --source-repo {roots.fork} --candidate {commit} "
                    f"--upstream-repository {UPSTREAM_REPO} "
                    f"--upstream-url https://github.com/{UPSTREAM_REPO}.git "
                    f"--output-plan {roots.fork.parent}/graphify.evidence/"
                    f"{latest}/plan.json"
                ),
                f"git -C {roots.fork} switch -c {branch} {commit}",
                (
                    f"git -C {roots.fork} rebase --onto v{latest} "
                    f"{ctx.fork_base_ref or '<old base tag>'}"
                ),
            ],
            human_gate=True,
            runnable=False,
        )
        new_commit = "<new fork commit>"
    pin_step = PlanStep(
        leg=leg.name,
        summary="move every KB pin site to the new fork commit (not wired until T8)",
        commands=[
            f"mise -C {roots.kb} run kb-graphify-pin -- {latest} {new_commit} v{latest}"
        ],
        human_gate=True,
        runnable=False,
    )
    return [fork_step, pin_step]


def _host_commands(leg: Leg, latest: str | None, ctx: _Context) -> list[str]:
    commands: list[str] = []
    if ctx.stray_uv_tool:
        commands.append("uv tool uninstall graphifyy")
    if leg.version is not None and latest is not None and _older(leg.version, latest):
        commands.append(f"mise use -g {graphify_currency.MISE_TOOL}@{latest}")
    if leg.state is not LegState.current:
        commands.append("exec $SHELL  # re-resolve PATH, then re-run status")
    return commands


def plan(status: FleetPlan, ctx: _Context, roots: FleetRoots) -> FleetPlan:
    """Return ``status`` with ordered steps for every leg that is not current."""
    steps: list[PlanStep] = []
    by_name = {leg.name: leg for leg in status.legs}
    for leg in (by_name[name] for name in _PLAN_ORDER):
        if leg.state is LegState.current:
            continue
        if leg.state is LegState.unverifiable:
            steps.append(
                PlanStep(
                    leg=leg.name,
                    summary="UNVERIFIABLE — resolve the probe failure before planning",
                    commands=[],
                    human_gate=True,
                    runnable=False,
                )
            )
        elif leg.name is LegName.dotfiles:
            steps.append(
                PlanStep(
                    leg=leg.name,
                    summary="update lock, receipts, skills and stamps; rebuild graph",
                    commands=["mise run graphify-fleet -- apply --leg dotfiles"],
                    human_gate=False,
                    runnable=True,
                )
            )
        elif leg.name is LegName.kb:
            steps.extend(_kb_steps(status, leg, ctx, roots))
        else:
            steps.append(
                PlanStep(
                    leg=leg.name,
                    summary="user-level change: printed only, run it yourself",
                    commands=_host_commands(leg, status.upstream.version, ctx),
                    human_gate=True,
                    runnable=False,
                )
            )
    return FleetPlan(
        upstream=status.upstream,
        legs=status.legs,
        fork_probe=status.fork_probe,
        verdict=status.verdict,
        steps=steps,
    )


def render(document: FleetPlan) -> str:
    """Render a status/plan document as plain text."""
    upstream = document.upstream
    lines = [
        (
            f"graphify-fleet: upstream {upstream.repo} latest "
            f"{upstream.version or f'UNVERIFIABLE ({upstream.error})'}"
        )
    ]
    for leg in document.legs:
        lines.append(f"[{leg.name}] {leg.state} {leg.version or '-'}")
        lines.extend(f"  site {site.location} = {site.value}" for site in leg.sites)
        lines.extend(f"  finding {finding}" for finding in leg.findings)
    probe = document.fork_probe
    if probe.error is not None:
        lines.append(f"fork-probe {probe.tag or '-'}: UNVERIFIABLE ({probe.error})")
    else:
        hits = " ".join(f"{term}={count}" for term, count in probe.feature_hits.items())
        lines.append(
            f"fork-probe {probe.tag}: {hits} control {FORK_CONTROL_TERM}="
            f"{probe.control_hits} -> native={probe.native}"
        )
    for index, step in enumerate(document.steps, start=1):
        gate = "HUMAN" if step.human_gate else "auto"
        lines.append(f"step {index} [{step.leg}] ({gate}) {step.summary}")
        lines.extend(f"    $ {command}" for command in step.commands)
    lines.append(f"verdict: {document.verdict} (rc={int(_EXIT[document.verdict])})")
    return "\n".join(lines) + "\n"


def _emit(document: FleetPlan, *, as_json: bool) -> int:
    if as_json:
        sys.stdout.write(codec.encode(document).decode() + "\n")
    else:
        sys.stdout.write(render(document))
    return int(_EXIT[document.verdict])


def apply_leg(
    leg: LegName, run: Run, roots: FleetRoots, probes: FleetProbes | None = None
) -> int:
    """Advance one leg: dotfiles runs, host prints, kb refuses until T8."""
    if leg is LegName.kb:
        sys.stderr.write(KB_NOT_WIRED + "\n")
        return int(DriftVerdict.ERROR)
    if leg is LegName.host:
        status, ctx = gather(run, roots, probes)
        host = next(item for item in status.legs if item.name is LegName.host)
        if host.state is LegState.current:
            sys.stdout.write("host leg current; nothing to run\n")
            return int(DriftVerdict.IN_SYNC)
        sys.stdout.write("host leg: run these yourself (never run by this tool):\n")
        for command in _host_commands(host, status.upstream.version, ctx):
            sys.stdout.write(f"  $ {command}\n")
        return int(_EXIT[host.state])
    try:
        result = run(
            ["mise", "run", "graphify-upgrade"], cwd=roots.dotfiles, check=False
        )
    except OSError as exc:
        sys.stderr.write(f"mise run graphify-upgrade: {exc}\n")
        return int(DriftVerdict.ERROR)
    return result.returncode


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dotfiles-setup graphify-fleet")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--kb-root", type=Path, default=None)
    common.add_argument("--kb-ref", default=KB_REF_DEFAULT)
    common.add_argument("--fork-root", type=Path, default=None)
    common.add_argument("--mise-global-config", type=Path, default=None)
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb in ("status", "plan"):
        verb_parser = sub.add_parser(verb, parents=[common])
        verb_parser.add_argument("--json", action="store_true", dest="as_json")
    apply_parser = sub.add_parser("apply", parents=[common])
    apply_parser.add_argument(
        "--leg", required=True, choices=[leg.value for leg in LegName]
    )
    return parser


def graphify_fleet_main(
    argv: Sequence[str],
    project_root: Path,
    run: Run = subprocess.run,
    probes: FleetProbes | None = None,
) -> int:
    """CLI entry: ``status`` / ``plan`` / ``apply --leg``; rc per DriftVerdict."""
    args = _parser().parse_args(list(argv))
    defaults = default_roots(project_root)
    roots = FleetRoots(
        dotfiles=project_root,
        kb=args.kb_root or defaults.kb,
        kb_ref=args.kb_ref,
        fork=args.fork_root or defaults.fork,
        mise_global_config=args.mise_global_config or defaults.mise_global_config,
    )
    if args.verb == "apply":
        return apply_leg(LegName(args.leg), run, roots, probes)
    status, ctx = gather(run, roots, probes)
    if args.verb == "plan":
        status = plan(status, ctx, roots)
    return _emit(status, as_json=args.as_json)
