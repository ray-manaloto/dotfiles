# Copyright (c) 2026 Raymond Manaloto
"""Fixture tests for the graphify-fleet status/plan/apply automation.

Every subprocess the module makes goes through an injected ``run``; the fake
below answers by argv shape, so each test states exactly which probe answers
what, and an unexpected command fails loudly instead of reaching the host. The
reused dotfiles probes arrive through the ``FleetProbes`` seam, not patching.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import codec, graphify_currency, graphify_fleet
from dotfiles_setup.generated.graphify_fleet import FleetPlan, LegName, LegState
from dotfiles_setup.main import setup_parser

FORK_SHA = "3c9b930f386f80c393fe658e1afb685030828c6a"
OTHER_SHA = "0" * 40
FORK_URL = "https://github.com/ray-manaloto/graphify"
CONTROL_HITS = 18

_PYPROJECT = f"""
[project]
dependencies = ["graphifyy[all]==0.9.57"]

[tool.uv.sources]
graphifyy = {{ git = "{FORK_URL}", rev = "{FORK_SHA}" }}
"""
_LOCK = f"""
[[package]]
name = "graphifyy"
version = "0.9.57"
source = {{ git = "{FORK_URL}?rev={FORK_SHA}#{FORK_SHA}" }}
"""
_MANIFEST = f"""
# comment = ignored
url = {FORK_URL}
ref = kb-pin/openai-cli-backend-v0.9.57
commit = {FORK_SHA}
"""
_CURRENCY = """
[tool.graphify.fork]
base_ref = "v0.9.57"
"""

type Done = subprocess.CompletedProcess[str]
Roots = graphify_fleet.FleetRoots
Capsys = pytest.CaptureFixture[str]


def _done(argv: list[str], rc: int = 0, out: str = "", err: str = "") -> Done:
    return subprocess.CompletedProcess(argv, rc, out, err)


class FakeRun:
    """Answer each probe by argv shape; record every call."""

    def __init__(self) -> None:
        """Start with every leg at 0.9.57 and upstream at v0.9.57."""
        self.calls: list[list[str]] = []
        self.upstream = "v0.9.57"
        self.upstream_rc = 0
        self.kb_files = {
            "pyproject.toml": _PYPROJECT,
            "uv.lock": _LOCK,
            "sources/graphify.manifest": _MANIFEST,
            "currency.toml": _CURRENCY,
        }
        self.tag_present = True
        self.grep_hits = {
            "openai-cli": 0,
            "fallback-backend": 0,
            "claude-cli": CONTROL_HITS,
        }
        self.uv_tools = "skypilot v0.13.0\n- sky\n"
        self.upgrade_rc = 0

    def __call__(self, argv: list[str], **_kwargs: object) -> Done:
        """Dispatch one subprocess call to the matching fake answer."""
        self.calls.append(argv)
        if argv[0] == "git":
            return self._git(argv)
        answers = {
            ("gh", "release", "view"): lambda: _done(
                argv, self.upstream_rc, self.upstream + "\n", "gh: boom"
            ),
            ("uv", "tool", "list"): lambda: _done(argv, out=self.uv_tools),
            ("mise", "run", "graphify-upgrade"): lambda: _done(argv, self.upgrade_rc),
        }
        answer = answers.get(tuple(argv[:3]))
        if answer is None:
            message = f"unexpected command {argv}"
            raise AssertionError(message)
        return answer()

    def _git(self, argv: list[str]) -> Done:
        if "show" in argv:
            ref, _, path = argv[-1].partition(":")
            if ref == "origin/main" and path in self.kb_files:
                return _done(argv, out=self.kb_files[path])
            return _done(argv, 128, err=f"fatal: invalid object name {ref}")
        if "rev-parse" in argv:
            return _done(argv, 0 if self.tag_present else 1)
        hits = self.grep_hits[argv[argv.index("-lF") + 1]]
        out = "".join(f"tag:graphify/f{i}.py\n" for i in range(hits))
        return _done(argv, 0 if hits else 1, out)


@dataclass(frozen=True)
class FakeProbe:
    """A PATH-binary probe answer, shaped like graphify_currency's."""

    value: str | None
    error: str
    path: str | None
    provenance_note: str


class Currency:
    """Injected dotfiles probes (lock, offline check, PATH binary) via the seam."""

    def __init__(self) -> None:
        """Default to a fully current dotfiles leg and host binary."""
        self.locked = "0.9.57"
        self.drifts: tuple[graphify_currency.Drift, ...] = ()
        self.path: str | None = "0.9.57"

    def _check(
        self, _root: Path, *, offline: bool
    ) -> tuple[graphify_currency.Drift, ...]:
        assert offline, "status must never run the network latest probe"
        return self.drifts

    def _path(self, *, run: object) -> FakeProbe:
        del run
        return FakeProbe(
            value=self.path,
            error="" if self.path else "path-binary UNVERIFIABLE (absent)",
            path="/mise/bin/graphify" if self.path else None,
            provenance_note="ambient PATH",
        )

    @property
    def probes(self) -> graphify_fleet.FleetProbes:
        """The seam value handed to ``gather``/``graphify_fleet_main``."""
        return graphify_fleet.FleetProbes(
            locked=lambda _root: self.locked,
            check=self._check,
            path_binary=self._path,
        )


@pytest.fixture
def roots(tmp_path: Path) -> Roots:
    """Build a dotfiles tree with 0.9.57 stamps and a user-global mise config."""
    dotfiles = tmp_path / "dotfiles"
    for stamp in graphify_fleet.STAMP_PATHS:
        (dotfiles / stamp).parent.mkdir(parents=True)
        (dotfiles / stamp).write_text("0.9.57\n", encoding="utf-8")
    config = tmp_path / "mise-config.toml"
    config.write_text(
        '[tools]\n"pipx:graphifyy" = { version = "0.9.57", extras = ["all"] }\n',
        encoding="utf-8",
    )
    return graphify_fleet.FleetRoots(
        dotfiles=dotfiles,
        kb=tmp_path / "kb",
        kb_ref="origin/main",
        fork=tmp_path / "fork",
        mise_global_config=config,
    )


@pytest.fixture
def currency() -> Currency:
    """Fresh injected dotfiles probes per test."""
    return Currency()


def _argv(verb: str, roots: Roots, *extra: str) -> list[str]:
    return [
        verb,
        *extra,
        "--kb-root",
        str(roots.kb),
        "--fork-root",
        str(roots.fork),
        "--mise-global-config",
        str(roots.mise_global_config),
    ]


def _main(argv: list[str], run: FakeRun, roots: Roots, currency: Currency) -> int:
    return graphify_fleet.graphify_fleet_main(
        argv, roots.dotfiles, run=run, probes=currency.probes
    )


def _legs(document: FleetPlan) -> dict[LegName, LegState]:
    return {leg.name: leg.state for leg in document.legs}


def test_status_all_current_exits_zero(
    roots: Roots, currency: Currency, capsys: Capsys
) -> None:
    run = FakeRun()
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    assert _legs(status) == dict.fromkeys(LegName, LegState.current)
    assert status.fork_probe.control_hits == CONTROL_HITS
    assert status.fork_probe.native is False

    assert _main(_argv("status", roots), run, roots, currency) == 0
    assert "verdict: current (rc=0)" in capsys.readouterr().out


def test_status_behind_json_round_trips(
    roots: Roots, currency: Currency, capsys: Capsys
) -> None:
    run = FakeRun()
    run.upstream = "v0.9.76"
    rc = _main(_argv("status", roots, "--json"), run, roots, currency)
    document = codec.decode(capsys.readouterr().out.encode(), FleetPlan)
    assert rc == 1
    assert _legs(document) == dict.fromkeys(LegName, LegState.behind)
    assert document.verdict is LegState.behind
    assert document.steps == []


def test_upstream_failure_is_unverifiable_never_current(
    roots: Roots, currency: Currency
) -> None:
    run = FakeRun()
    run.upstream_rc = 1
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    assert status.upstream.version is None
    assert status.upstream.error == "gh: boom"
    assert set(_legs(status).values()) == {LegState.unverifiable}
    assert status.verdict is LegState.unverifiable


def test_kb_ref_unreadable_fails_closed(roots: Roots, currency: Currency) -> None:
    run = FakeRun()
    bad = graphify_fleet.FleetRoots(
        roots.dotfiles, roots.kb, "origin/nope", roots.fork, roots.mise_global_config
    )
    status, _ = graphify_fleet.gather(run, bad, currency.probes)
    kb = status.legs[1]
    assert kb.state is LegState.unverifiable
    assert any("invalid object name" in finding for finding in kb.findings)


def test_kb_disagreeing_revisions_are_drift(roots: Roots, currency: Currency) -> None:
    run = FakeRun()
    run.kb_files["sources/graphify.manifest"] = _MANIFEST.replace(FORK_SHA, OTHER_SHA)
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    kb = status.legs[1]
    assert kb.state is LegState.drift
    assert any("disagree" in finding for finding in kb.findings)


def test_dotfiles_drift_and_unverifiable_partition(
    roots: Roots, currency: Currency
) -> None:
    run = FakeRun()
    currency.drifts = (
        graphify_currency.Drift("stamp", ".claude/...: stale"),
        graphify_currency.Drift("path-binary", "host axis, not dotfiles"),
    )
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    dotfiles = status.legs[0]
    assert dotfiles.state is LegState.drift
    assert dotfiles.findings == ["[stamp] .claude/...: stale"]

    currency.drifts = (graphify_currency.Drift("skill-bytes", "UNVERIFIABLE: x"),)
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    assert status.legs[0].state is LegState.unverifiable


def test_host_path_binary_disagreeing_with_pin_is_drift(
    roots: Roots, currency: Currency
) -> None:
    run = FakeRun()
    currency.path = "0.9.61"
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    host = status.legs[2]
    assert host.state is LegState.drift
    assert any("0.9.61 != user-global pin 0.9.57" in f for f in host.findings)

    currency.path = None
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    assert status.legs[2].state is LegState.unverifiable


def test_fork_probe_blind_control_arm(roots: Roots, currency: Currency) -> None:
    run = FakeRun()
    run.upstream = "v0.9.76"
    run.grep_hits["claude-cli"] = 0
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    assert status.fork_probe.native is None
    assert "probe is blind" in (status.fork_probe.error or "")
    # The KB is behind and the plan depends on the probe: fail closed.
    assert status.verdict is LegState.unverifiable


def test_fork_probe_missing_tag_never_fetches(roots: Roots, currency: Currency) -> None:
    run = FakeRun()
    run.tag_present = False
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    assert "absent" in (status.fork_probe.error or "")
    assert not any("fetch" in argv for argv in run.calls)


def test_plan_orders_dotfiles_then_human_fork_rebase(
    roots: Roots, currency: Currency, capsys: Capsys
) -> None:
    run = FakeRun()
    run.upstream = "v0.9.76"
    rc = _main(_argv("plan", roots, "--json"), run, roots, currency)
    document = codec.decode(capsys.readouterr().out.encode(), FleetPlan)
    assert rc == 1
    legs = [step.leg for step in document.steps]
    assert legs == [LegName.dotfiles, LegName.kb, LegName.kb, LegName.host]
    dotfiles, rebase, pin, host = document.steps
    assert dotfiles.runnable
    assert not dotfiles.human_gate
    assert rebase.human_gate
    assert not rebase.runnable
    assert any(f"preview --candidate {FORK_SHA}" in cmd for cmd in rebase.commands)
    assert any("rebase --onto v0.9.76 v0.9.57" in cmd for cmd in rebase.commands)
    assert "T8" in pin.summary
    assert "mise use -g pipx:graphifyy@0.9.76" in host.commands


def test_plan_native_upstream_proposes_retirement(
    roots: Roots, currency: Currency
) -> None:
    run = FakeRun()
    run.upstream = "v0.9.76"
    run.grep_hits.update({"openai-cli": 3, "fallback-backend": 1})
    status, ctx = graphify_fleet.gather(run, roots, currency.probes)
    assert status.fork_probe.native is True
    steps = graphify_fleet.plan(status, ctx, roots).steps
    kb_first = next(step for step in steps if step.leg is LegName.kb)
    assert "natively" in kb_first.summary
    assert kb_first.commands == []


def test_apply_host_prints_uninstall_and_never_runs_it(
    roots: Roots, currency: Currency, capsys: Capsys
) -> None:
    run = FakeRun()
    run.uv_tools = "graphifyy v0.9.61\n- graphify\n"
    rc = _main(_argv("apply", roots, "--leg", "host"), run, roots, currency)
    assert rc == 1
    assert "$ uv tool uninstall graphifyy" in capsys.readouterr().out
    assert not any("uninstall" in argv for argv in run.calls)


def test_apply_kb_refuses_until_t8(
    roots: Roots, currency: Currency, capsys: Capsys
) -> None:
    run = FakeRun()
    rc = _main(_argv("apply", roots, "--leg", "kb"), run, roots, currency)
    assert rc == 2
    assert "not wired until T8" in capsys.readouterr().err
    assert run.calls == []


@pytest.mark.parametrize("upgrade_rc", [0, 3])
def test_apply_dotfiles_delegates_to_graphify_upgrade(
    roots: Roots, currency: Currency, upgrade_rc: int
) -> None:
    run = FakeRun()
    run.upgrade_rc = upgrade_rc
    rc = _main(_argv("apply", roots, "--leg", "dotfiles"), run, roots, currency)
    assert rc == upgrade_rc
    assert run.calls == [["mise", "run", "graphify-upgrade"]]


def test_cli_registration_passes_flags_through() -> None:
    args = setup_parser().parse_args(["graphify-fleet", "apply", "--leg", "kb"])
    assert args.command == "graphify-fleet"
    assert args.fleet_argv == ["apply", "--leg", "kb"]
