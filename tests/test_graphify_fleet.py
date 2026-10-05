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
            "_run_semantic_extract": 0,
            "UNWIND $rows": 0,
            "_codex_resolvable_disable_args": 0,
            "claude-cli": CONTROL_HITS,
        }
        self.uv_tools = "skypilot v0.13.0\n- sky\n"
        self.upgrade_rc = 0
        self.git_warning = ""

    def __call__(self, argv: list[str], **_kwargs: object) -> Done:
        """Dispatch one subprocess call to the matching fake answer."""
        self.calls.append(argv)
        if argv[0] == "git":
            return self._git(argv)
        answers = {
            # The PyPI latest probe graphify-update itself uses (not gh).
            ("mise", "latest", "pipx:graphifyy"): lambda: _done(
                argv,
                self.upstream_rc,
                self.upstream.removeprefix("v") + "\n",
                "mise: boom",
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
            ok = self.tag_present
            return _done(argv, 0 if ok else 1, err=self.git_warning if ok else "")
        hits = self.grep_hits[argv[argv.index("-lF") + 1]]
        out = "".join(f"tag:graphify/f{i}.py\n" for i in range(hits))
        return _done(argv, 0 if hits else 1, out, self.git_warning if hits else "")


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
    assert status.upstream.error == "mise: boom"
    assert not any(argv[:1] == ["gh"] for argv in run.calls)
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


def test_plan_only_original_terms_hit_keeps_fork_replay(
    roots: Roots, currency: Currency
) -> None:
    run = FakeRun()
    run.upstream = "v0.9.76"
    run.grep_hits.update({"openai-cli": 3, "fallback-backend": 3})
    status, ctx = graphify_fleet.gather(run, roots, currency.probes)
    assert status.fork_probe.native is False
    assert status.fork_probe.feature_hits == {
        "openai-cli": 3,
        "fallback-backend": 3,
        "_run_semantic_extract": 0,
        "UNWIND $rows": 0,
        "_codex_resolvable_disable_args": 0,
    }
    kb_first = next(
        step
        for step in graphify_fleet.plan(status, ctx, roots).steps
        if step.leg is LegName.kb
    )
    assert "replay the fork payload" in kb_first.summary
    assert any("rebase --onto v0.9.76 v0.9.57" in cmd for cmd in kb_first.commands)


@pytest.mark.parametrize(
    "missing_term",
    [
        "openai-cli",
        "fallback-backend",
        "_run_semantic_extract",
        "UNWIND $rows",
        "_codex_resolvable_disable_args",
    ],
)
def test_fork_probe_each_missing_term_prevents_native(
    roots: Roots, missing_term: str
) -> None:
    run = FakeRun()
    run.grep_hits.update(
        {
            "openai-cli": 3,
            "fallback-backend": 3,
            "_run_semantic_extract": 1,
            "UNWIND $rows": 1,
            "_codex_resolvable_disable_args": 1,
        }
    )
    run.grep_hits[missing_term] = 0
    probe = graphify_fleet.probe_fork_features(run, roots, "0.9.76")
    assert probe.native is False
    assert probe.error is None


def test_fork_probe_all_terms_still_requires_control(roots: Roots) -> None:
    run = FakeRun()
    run.grep_hits = {
        "openai-cli": 3,
        "fallback-backend": 3,
        "_run_semantic_extract": 1,
        "UNWIND $rows": 1,
        "_codex_resolvable_disable_args": 1,
        "claude-cli": 0,
    }
    probe = graphify_fleet.probe_fork_features(run, roots, "0.9.76")
    assert probe.native is None
    assert "probe is blind" in (probe.error or "")


def test_fork_probe_passes_literal_dollar_to_fixed_string_git(roots: Roots) -> None:
    run = FakeRun()
    graphify_fleet.probe_fork_features(run, roots, "0.9.76")
    assert [
        "git",
        "-C",
        str(roots.fork),
        "grep",
        "-lF",
        "UNWIND $rows",
        "v0.9.76",
        "--",
        "graphify/",
    ] in run.calls


def test_plan_orders_host_then_dotfiles_then_human_fork_rebase(
    roots: Roots, currency: Currency, capsys: Capsys
) -> None:
    run = FakeRun()
    run.upstream = "v0.9.76"
    rc = _main(_argv("plan", roots, "--json"), run, roots, currency)
    document = codec.decode(capsys.readouterr().out.encode(), FleetPlan)
    assert rc == 1
    legs = [step.leg for step in document.steps]
    # Host first: graphify-upgrade's closing check needs the new PATH binary.
    assert legs == [LegName.host, LegName.dotfiles, LegName.kb, LegName.kb]
    host, dotfiles, rebase, pin = document.steps
    assert dotfiles.runnable
    assert not dotfiles.human_gate
    assert rebase.human_gate
    assert not rebase.runnable
    preview = rebase.commands[0]
    for required in (
        f"--source-repo {roots.fork}",
        f"--candidate {FORK_SHA}",
        "--upstream-repository Graphify-Labs/graphify",
        "--upstream-url https://github.com/Graphify-Labs/graphify.git",
        "--output-plan ",
    ):
        assert required in preview
    assert any("rebase --onto v0.9.76 v0.9.57" in cmd for cmd in rebase.commands)
    assert "T8" in pin.summary
    assert "mise use -g pipx:graphifyy@0.9.76" in host.commands


def test_kb_drift_outranks_behind_and_blocks_the_version_move(
    roots: Roots, currency: Currency
) -> None:
    run = FakeRun()
    run.upstream = "v0.9.76"
    run.kb_files["sources/graphify.manifest"] = _MANIFEST.replace(FORK_SHA, OTHER_SHA)
    status, ctx = graphify_fleet.gather(run, roots, currency.probes)
    kb = status.legs[1]
    assert kb.state is LegState.drift
    assert "also behind upstream 0.9.76" in kb.findings
    kb_steps = [
        s for s in graphify_fleet.plan(status, ctx, roots).steps if s.leg is LegName.kb
    ]
    assert len(kb_steps) == 1
    assert kb_steps[0].commands == []
    assert "reconcile" in kb_steps[0].summary


def test_unanswered_fork_probe_prints_no_kb_commands(
    roots: Roots, currency: Currency
) -> None:
    run = FakeRun()
    run.upstream = "v0.9.76"
    run.tag_present = False
    status, ctx = graphify_fleet.gather(run, roots, currency.probes)
    kb_steps = [
        s for s in graphify_fleet.plan(status, ctx, roots).steps if s.leg is LegName.kb
    ]
    assert len(kb_steps) == 1
    assert kb_steps[0].commands == []
    assert "UNVERIFIABLE" in kb_steps[0].summary


@pytest.mark.parametrize("path", ["pyproject.toml", "uv.lock", "currency.toml"])
def test_malformed_kb_toml_marks_leg_unverifiable_not_crash(
    roots: Roots, currency: Currency, path: str
) -> None:
    run = FakeRun()
    run.kb_files[path] = "[[unterminated"
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    kb = status.legs[1]
    assert kb.state is LegState.unverifiable
    assert status.legs[0].state is LegState.current


def test_plan_native_upstream_proposes_retirement(
    roots: Roots, currency: Currency
) -> None:
    run = FakeRun()
    run.upstream = "v0.9.76"
    run.grep_hits.update(
        {
            "openai-cli": 3,
            "fallback-backend": 3,
            "_run_semantic_extract": 1,
            "UNWIND $rows": 1,
            "_codex_resolvable_disable_args": 1,
        }
    )
    status, ctx = graphify_fleet.gather(run, roots, currency.probes)
    assert status.fork_probe.native is True
    assert status.fork_probe.feature_hits == {
        "openai-cli": 3,
        "fallback-backend": 3,
        "_run_semantic_extract": 1,
        "UNWIND $rows": 1,
        "_codex_resolvable_disable_args": 1,
    }
    document = graphify_fleet.plan(status, ctx, roots)
    kb_first = next(step for step in document.steps if step.leg is LegName.kb)
    assert "every fork feature" not in kb_first.summary
    assert "all 5 probed fork terms" in kb_first.summary
    assert "human decision" in kb_first.summary
    assert f"git -C {roots.fork} log v0.9.57..{FORK_SHA}" in kb_first.summary
    assert "currency.toml" in kb_first.summary
    assert kb_first.commands == []
    assert kb_first.human_gate
    assert not kb_first.runnable
    rendered = graphify_fleet.render(document)
    assert "every fork feature" not in rendered
    assert "all 5 probed fork terms" in rendered
    assert "human decision" in rendered
    assert f"git -C {roots.fork} log v0.9.57..{FORK_SHA}" in rendered
    assert (
        "openai-cli=3 fallback-backend=3 _run_semantic_extract=1 "
        "UNWIND $rows=1 _codex_resolvable_disable_args=1 control claude-cli=18"
    ) in rendered


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
    assert run.calls.count(["mise", "run", "graphify-upgrade"]) == 1
    assert run.calls[-1] == ["mise", "run", "graphify-upgrade"]


def test_apply_dotfiles_refuses_while_host_leg_is_not_current(
    roots: Roots, currency: Currency, capsys: Capsys
) -> None:
    run = FakeRun()
    run.upstream = "v0.9.76"  # user-global pin 0.9.57 is now behind
    rc = _main(_argv("apply", roots, "--leg", "dotfiles"), run, roots, currency)
    assert rc == 2
    assert "apply --leg host" in capsys.readouterr().err
    assert ["mise", "run", "graphify-upgrade"] not in run.calls


def test_drift_outranks_behind_in_the_verdict(roots: Roots, currency: Currency) -> None:
    run = FakeRun()
    run.upstream = "v0.9.76"  # dotfiles and host behind
    run.kb_files["sources/graphify.manifest"] = _MANIFEST.replace(FORK_SHA, OTHER_SHA)
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    assert status.verdict is LegState.drift


def test_cli_registration_passes_flags_through() -> None:
    args = setup_parser().parse_args(["graphify-fleet", "apply", "--leg", "kb"])
    assert args.command == "graphify-fleet"
    assert args.fleet_argv == ["apply", "--leg", "kb"]


def test_skill_names_every_probed_fork_term() -> None:
    skill = Path(__file__).parent.parent / ".claude/skills/graphify-fleet/SKILL.md"
    text = skill.read_text(encoding="utf-8")
    for term in graphify_fleet.FORK_FEATURE_TERMS:
        assert f"`{term}`" in text, term
    assert f"{len(graphify_fleet.FORK_FEATURE_TERMS)} probed fork terms" in text


def test_kb_pinned_to_upstream_pypi_is_not_drift(
    roots: Roots, currency: Currency
) -> None:
    run = FakeRun()
    run.kb_files.update(
        {
            "pyproject.toml": '[project]\ndependencies = ["graphifyy[all]==0.9.57"]\n',
            "uv.lock": '[[package]]\nname = "graphifyy"\nversion = "0.9.57"\n',
            "sources/graphify.manifest": (
                "url = https://github.com/Graphify-Labs/graphify\n"
                f"ref = v0.9.57\ncommit = {OTHER_SHA}\n"
            ),
            "currency.toml": "",
        }
    )
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    assert status.legs[1].state is LegState.current

    # A PyPI-pinned KB whose manifest still describes an older release.
    run.kb_files["sources/graphify.manifest"] = (
        "url = https://github.com/Graphify-Labs/graphify\n"
        f"ref = v0.9.50\ncommit = {OTHER_SHA}\n"
    )
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    assert "manifest ref v0.9.50 != installed v0.9.57" in status.legs[1].findings

    # The manifest still needs ref + commit: KB's manifest loader rejects
    # a URL-only file, so a retired fork must not hide that as "current".
    run.kb_files["sources/graphify.manifest"] = (
        "url = https://github.com/Graphify-Labs/graphify\n"
    )
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    kb = status.legs[1]
    assert kb.state is LegState.drift
    assert "sources/graphify.manifest lacks ref, commit" in kb.findings


def test_native_upstream_prints_no_fork_pin_step(
    roots: Roots, currency: Currency
) -> None:
    run = FakeRun()
    run.upstream = "v0.9.76"
    run.grep_hits.update(dict.fromkeys(graphify_fleet.FORK_FEATURE_TERMS, 1))
    status, ctx = graphify_fleet.gather(run, roots, currency.probes)
    steps = graphify_fleet.plan(status, ctx, roots).steps
    kb_steps = [step for step in steps if step.leg is LegName.kb]
    assert len(kb_steps) == 1
    assert not any("kb-graphify-pin" in c for s in kb_steps for c in s.commands)


def test_git_warning_on_success_does_not_blind_the_fork_probe(
    roots: Roots, currency: Currency
) -> None:
    run = FakeRun()
    run.git_warning = "warning: refname 'v0.9.57' is ambiguous.\n"
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    assert status.fork_probe.error is None
    assert status.fork_probe.control_hits == CONTROL_HITS


def test_non_version_host_pin_is_unverifiable(roots: Roots, currency: Currency) -> None:
    roots.mise_global_config.write_text(
        '[tools]\n"pipx:graphifyy" = "latest"\n', encoding="utf-8"
    )
    run = FakeRun()
    status, _ = graphify_fleet.gather(run, roots, currency.probes)
    host = status.legs[2]
    assert host.state is LegState.unverifiable
    assert any("'latest' is not an exact version" in f for f in host.findings)
