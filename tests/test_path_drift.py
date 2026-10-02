# Copyright (c) 2026 Raymond Manaloto
"""Tests for the PATH-drift preflight (dotfiles_setup.path_drift).

The property that matters most is not "does it find drift" — it is **does it
know when it cannot see**. This check runs from a mise task, and mise repairs
``PATH`` before the task starts, so the natural failure mode is a probe that
reports "clean" about a shell it never looked at. Every test below that names
``BLIND`` is guarding that, and the drift tests are its control arm: a probe
that can only say BLIND would be just as useless.

Real-repo guards at the bottom pin the two things a fixture cannot: that the
shipped ``doctor.toml`` really carries the ``[path_drift]`` baseline the check
reads, and that the SessionStart hook really captures the ambient ``PATH``
(without which the shipped check is the can-only-pass probe this module exists
to refuse).
"""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import path_drift

REPO_ROOT = Path(__file__).parent.parent

INSTALLS = "/home/u/.local/share/mise/installs"


def _listing(**tools: tuple[str, str]) -> dict[str, object]:
    """``mise ls --current --json``-shaped listing: tool -> (slug, version)."""
    return {
        tool: [{"version": version, "install_path": f"{INSTALLS}/{slug}/{version}"}]
        for tool, (slug, version) in tools.items()
    }


def _path(*entries: str) -> str:
    return ":".join(f"{INSTALLS}/{entry}" for entry in entries)


# --------------------------------------------------------------------------- #
# Provenance — the blindness detector
# --------------------------------------------------------------------------- #


def test_an_explicit_ambient_path_wins_over_everything() -> None:
    value, provenance = path_drift.resolve_ambient_path(
        {"PATH": "/inherited", path_drift.AMBIENT_PATH_ENV: "/captured"},
        ambient_path="/explicit",
    )
    assert (value, provenance) == ("/explicit", path_drift.Provenance.EXPLICIT)


def test_a_captured_ambient_path_is_used_even_under_a_mise_task() -> None:
    """The whole point of the seam: capture beats the marker."""
    value, provenance = path_drift.resolve_ambient_path(
        {
            "PATH": "/repaired-by-mise",
            path_drift.AMBIENT_PATH_ENV: "/the-real-shell",
            path_drift.MISE_TASK_MARKER: "doctor",
        }
    )
    assert (value, provenance) == ("/the-real-shell", path_drift.Provenance.EXPLICIT)


def test_an_inherited_path_is_trusted_when_mise_did_not_rewrite_it() -> None:
    _, provenance = path_drift.resolve_ambient_path({"PATH": "/from-the-shell"})
    assert provenance is path_drift.Provenance.INHERITED


def test_an_inherited_path_under_a_mise_task_is_blind_not_trusted() -> None:
    """The measured hazard: `mise run <task>` replaces the stale install dir."""
    _, provenance = path_drift.resolve_ambient_path(
        {"PATH": "/repaired-by-mise", path_drift.MISE_TASK_MARKER: "doctor"}
    )
    assert provenance is path_drift.Provenance.BLIND


def test_a_blind_report_is_not_usable_and_carries_no_drifts() -> None:
    """A blind probe must never be mistaken for a clean one.

    The realistic regression is someone dropping the hook's env prefix; this
    pins that doing so degrades to BLIND rather than to an empty finding list
    that renders as a PASS.
    """
    report = path_drift.check_path_drift(
        environ={"PATH": _path("hk/1.0.0"), path_drift.MISE_TASK_MARKER: "doctor"},
        listing=_listing(hk=("hk", "2.0.0")),
    )
    assert report.provenance is path_drift.Provenance.BLIND
    assert not report.usable
    assert report.drifts == ()


# --------------------------------------------------------------------------- #
# The comparison
# --------------------------------------------------------------------------- #


def test_a_stale_install_dir_on_path_is_drift() -> None:
    report = path_drift.check_path_drift(
        environ={},
        ambient_path=_path("hk/1.54.0", "uv/0.12.3/uv-aarch64-apple-darwin"),
        listing=_listing(hk=("hk", "1.54.1"), uv=("uv", "0.12.3")),
    )
    assert report.usable
    assert [d.tool for d in report.drifts] == ["hk"]
    assert report.drifts[0].describe() == "hk 1.54.0 on PATH, mise resolves 1.54.1"


def test_a_matching_version_is_not_drift_even_under_a_subdirectory() -> None:
    """The uv install nests its binary a level down; the version is still parts[1]."""
    report = path_drift.check_path_drift(
        environ={},
        ambient_path=_path("uv/0.12.3/uv-aarch64-apple-darwin"),
        listing=_listing(uv=("uv", "0.12.3")),
    )
    assert report.drifts == ()
    assert report.tools_compared == 1


def test_a_shim_is_never_drift() -> None:
    """A shim resolves its version at exec time, so it cannot be stale.

    It is excluded structurally (not under the installs root) rather than by a
    name match, so a renamed shim directory cannot silently re-introduce a
    false positive.
    """
    report = path_drift.check_path_drift(
        environ={},
        ambient_path="/home/u/.local/share/mise/shims",
        listing=_listing(ruff=("ruff", "0.14.0")),
    )
    assert report.drifts == ()
    assert report.tools_compared == 0


def test_a_path_entry_mise_does_not_consider_active_is_not_drift() -> None:
    report = path_drift.check_path_drift(
        environ={},
        ambient_path=_path("some-other-tool/9.9.9"),
        listing=_listing(hk=("hk", "1.54.1")),
    )
    assert report.drifts == ()


def test_a_slug_with_one_shared_version_is_resolving_correctly() -> None:
    """Intersection, not equality — two entries where one matches is fine."""
    ambient = {"hk": frozenset({"1.54.0", "1.54.1"})}
    active = {"hk": path_drift.ActiveTool("hk", "hk", frozenset({"1.54.1"}))}
    assert path_drift.compare(ambient, active) == ()


def test_gate_critical_tools_are_selected_by_mise_tool_name_and_by_slug() -> None:
    """`npm:renovate` is the tool name; `npm-renovate` is the directory slug."""
    report = path_drift.check_path_drift(
        environ={},
        ambient_path=_path("npm-renovate/44.13.2", "aws-cli/2.36.17"),
        listing={
            "npm:renovate": [
                {"install_path": f"{INSTALLS}/npm-renovate/44.14.10"},
            ],
            "aws-cli": [{"install_path": f"{INSTALLS}/aws-cli/2.36.19"}],
        },
    )
    assert len(report.drifts) == 2
    assert [d.tool for d in report.gate_drifts(("npm:renovate",))] == ["npm:renovate"]
    assert [d.tool for d in report.gate_drifts(("npm-renovate",))] == ["npm:renovate"]


def test_the_installs_root_is_derived_from_mise_not_from_home() -> None:
    """A relocated ``MISE_DATA_DIR`` must still be parsed, not silently missed."""
    listing = {"hk": [{"install_path": "/opt/mise-data/installs/hk/2.0.0"}]}
    report = path_drift.check_path_drift(
        environ={},
        ambient_path="/opt/mise-data/installs/hk/1.0.0",
        listing=listing,
    )
    assert [d.describe() for d in report.drifts] == [
        "hk 1.0.0 on PATH, mise resolves 2.0.0"
    ]


def test_an_empty_listing_is_an_error_not_a_clean_bill() -> None:
    report = path_drift.check_path_drift(
        environ={}, ambient_path="/usr/bin", listing={}
    )
    assert not report.usable
    assert report.error is not None


def test_absent_findings_report_an_active_tool_with_no_path_entry() -> None:
    active = {"hk": path_drift.ActiveTool("hk", "hk", frozenset({"1.0.0"}))}
    assert path_drift.absent_findings({}, active) == ("hk",)
    assert path_drift.absent_findings({"hk": frozenset({"1.0.0"})}, active) == ()


# --------------------------------------------------------------------------- #
# Exit codes — blind must never be success
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("strict", "expected"),
    [(False, 0), (True, 1)],
)
def test_drift_exits_zero_by_default_and_one_under_strict(
    monkeypatch: pytest.MonkeyPatch, *, strict: bool, expected: int
) -> None:
    monkeypatch.setattr(
        path_drift,
        "run_mise_ls",
        lambda: (_listing(hk=("hk", "1.54.1")), None),
    )
    rc = path_drift.path_drift_main(
        ambient_path=_path("hk/1.54.0"), strict=strict, verbose=False
    )
    assert rc == expected


def test_blind_exits_two_under_strict_and_non_strict_alike(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blind is its own exit code: it can never be folded into success.

    The listing is deliberately HEALTHY and the ``PATH`` deliberately DRIFTED,
    so 2 can only come from the blindness branch. An empty listing would also
    exit 2 — via the error path — and the test would keep passing after the
    blindness check was deleted, which is exactly how it was first written.
    """
    monkeypatch.setenv(path_drift.MISE_TASK_MARKER, "doctor")
    monkeypatch.setenv("PATH", _path("hk/1.54.0"))
    monkeypatch.delenv(path_drift.AMBIENT_PATH_ENV, raising=False)
    monkeypatch.setattr(
        path_drift, "run_mise_ls", lambda: (_listing(hk=("hk", "1.54.1")), None)
    )
    assert path_drift.path_drift_main(strict=False) == 2
    assert path_drift.path_drift_main(strict=True) == 2


def test_a_clean_shell_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        path_drift,
        "run_mise_ls",
        lambda: (_listing(hk=("hk", "1.54.1")), None),
    )
    assert path_drift.path_drift_main(ambient_path=_path("hk/1.54.1"), strict=True) == 0


def test_a_failed_mise_invocation_exits_two_rather_than_reporting_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(path_drift, "run_mise_ls", lambda: ({}, "mise exited 1"))
    assert path_drift.path_drift_main(ambient_path="/usr/bin", strict=False) == 2


# --------------------------------------------------------------------------- #
# Real-repo guards — the wiring the fixtures cannot see
# --------------------------------------------------------------------------- #


def test_the_session_start_hook_captures_the_ambient_path() -> None:
    """Without this prefix the shipped check can ONLY report BLIND.

    Mutation-tested realistically: the regression is not a renamed variable, it
    is someone dropping the assignment while tidying the hook command — which
    this assertion catches, because it looks for the capture attached to the
    doctor invocation rather than for the variable name anywhere in the file.
    """
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text())
    commands = [
        hook["command"]
        for entry in settings["hooks"]["SessionStart"]
        for hook in entry["hooks"]
    ]
    doctor_calls = [c for c in commands if "run doctor" in c]
    assert doctor_calls, "no SessionStart hook runs the doctor at all"
    assert all(
        f'{path_drift.AMBIENT_PATH_ENV}="$PATH" mise' in command
        for command in doctor_calls
    ), (
        f"the SessionStart doctor hook must capture the shell PATH into "
        f"{path_drift.AMBIENT_PATH_ENV} before mise rewrites it, or the "
        f"path-drift check is blind on every session"
    )


def test_the_shipped_baseline_declares_the_gate_tools() -> None:
    baseline = tomllib.loads((REPO_ROOT / "doctor.toml").read_text())
    declared = baseline["path_drift"]["gate_tools"]
    assert declared, "an empty gate_tools list silently disables the ranking"
    # Every default has actually drifted at least once (#596); the baseline may
    # add to that set but dropping one un-ranks a tool whose staleness has
    # already produced a red gate.
    assert set(path_drift.DEFAULT_GATE_TOOLS) <= set(declared)


# --------------------------------------------------------------------------- #
# Native-only binaries (Ray, 2026-10-01) — real executables in a fake world
# --------------------------------------------------------------------------- #
#
# ``which_all`` checks the filesystem, so these build real executables under
# ``tmp_path``: a fake HOME with a native ``~/.local/bin`` and a fake mise data
# directory. The system-wide mise data directory is redirected into ``tmp_path``
# too, so the host's own ``/usr/local/share/mise`` can never decide a result.


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    monkeypatch.setattr(path_drift, "_SYSTEM_MISE_DATA", tmp_path / "sysmise")
    home = tmp_path / "home"
    data = home / ".local" / "share" / "mise"
    return {
        "home": home,
        "native": home / ".local" / "bin",
        "installs": data / "installs",
        "shims": data / "shims",
    }


def _exe(directory: Path, name: str = "agy") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    binary = directory / name
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o755)
    return directory


def _native_only(
    world: dict[str, Path], *entries: Path, **overrides: tuple[str, ...]
) -> path_drift.NativeOnlyReport:
    return path_drift.check_native_only(
        overrides or {"agy": ("antigravity-cli",)},
        environ={},
        ambient_path=":".join(map(str, entries)),
        listing={
            "hk": [{"install_path": str(world["installs"] / "hk" / "1.0.0")}],
        },
        home=world["home"],
    )


def test_native_first_passes(world: dict[str, Path]) -> None:
    report = _native_only(world, _exe(world["native"]), Path("/usr/bin"))
    assert (report.failures, report.warnings) == ((), ())


def test_a_mise_shim_first_fails(world: dict[str, Path]) -> None:
    report = _native_only(world, _exe(world["shims"]), _exe(world["native"]))
    assert len(report.failures) == 1
    assert "resolves to mise's copy" in report.failures[0]
    assert "mise uninstall --all antigravity-cli && mise reshim" in report.failures[0]


def test_an_installs_dir_first_fails(world: dict[str, Path]) -> None:
    """The exact 2026-10-01 shape: ``installs/antigravity-cli/1.2.14/agy``."""
    mise_dir = _exe(world["installs"] / "antigravity-cli" / "1.2.14")
    report = _native_only(world, mise_dir, _exe(world["native"]))
    assert any("resolves to mise's copy" in f for f in report.failures)
    # The directory itself is also the "re-created" signal.
    assert any("was re-created" in w for w in report.warnings)


def test_a_symlink_into_an_installs_dir_is_not_native(world: dict[str, Path]) -> None:
    target = _exe(world["installs"] / "antigravity-cli" / "1.2.14") / "agy"
    world["native"].mkdir(parents=True)
    (world["native"] / "agy").symlink_to(target)
    report = _native_only(world, world["native"])
    assert any("resolves to mise's copy" in f for f in report.failures)


def test_no_native_copy_at_all_fails(world: dict[str, Path]) -> None:
    report = _native_only(world, Path("/nonexistent-dir"))
    assert len(report.failures) == 1
    assert "not found at all" in report.failures[0]


def test_only_mise_copies_fail_twice(world: dict[str, Path]) -> None:
    report = _native_only(world, _exe(world["shims"]))
    assert len(report.failures) == 2
    assert "only mise copies" in report.failures[1]


def test_a_later_mise_hit_warns_but_does_not_fail(world: dict[str, Path]) -> None:
    report = _native_only(world, _exe(world["native"]), _exe(world["shims"]))
    assert report.failures == ()
    assert len(report.warnings) == 1
    assert "one PATH reorder from winning" in report.warnings[0]


def test_a_leftover_install_dir_warns(world: dict[str, Path]) -> None:
    (world["installs"] / "npm-openai-codex").mkdir(parents=True)
    report = _native_only(
        world, _exe(world["native"], "codex"), codex=("codex", "npm:@openai/codex")
    )
    assert report.failures == ()
    assert len(report.warnings) == 1
    assert "npm-openai-codex exists" in report.warnings[0]
    assert "mise uninstall --all npm:@openai/codex" in report.warnings[0]


def test_a_similarly_named_install_dir_is_not_flagged(world: dict[str, Path]) -> None:
    """``npm-oh-my-codex`` really exists on this host and is not codex."""
    (world["installs"] / "npm-oh-my-codex").mkdir(parents=True)
    report = _native_only(
        world, _exe(world["native"], "codex"), codex=("codex", "npm:@openai/codex")
    )
    assert (report.failures, report.warnings) == ((), ())


def test_native_only_is_blind_under_a_mise_task() -> None:
    report = path_drift.check_native_only(
        environ={"PATH": "/whatever", path_drift.MISE_TASK_MARKER: "doctor"},
    )
    assert report.provenance is path_drift.Provenance.BLIND
    assert (report.failures, report.warnings) == ((), ())


def test_a_failed_mise_ls_still_checks_the_default_dirs(
    world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(path_drift, "run_mise_ls", lambda: ({}, "mise exited 1"))
    report = path_drift.check_native_only(
        {"agy": ("antigravity-cli",)},
        environ={},
        ambient_path=f"{_exe(world['shims'])}:{_exe(world['native'])}",
        home=world["home"],
    )
    assert any("resolves to mise's copy" in f for f in report.failures)
    assert any("could not ask mise" in w for w in report.warnings)


@pytest.mark.parametrize(
    ("spec", "slug"),
    [
        ("antigravity-cli", "antigravity-cli"),
        ("npm:@openai/codex", "npm-openai-codex"),
        ("github:anthropics/claude-code", "github-anthropics-claude-code"),
        ("npm:@anthropic-ai/claude-code", "npm-anthropic-ai-claude-code"),
        ("npm:@devcontainers/cli", "npm-devcontainers-cli"),
    ],
)
def test_mise_slug_matches_measured_install_dirs(spec: str, slug: str) -> None:
    assert path_drift.mise_slug(spec) == slug


def test_the_shipped_baseline_declares_native_only_at_least_the_defaults() -> None:
    baseline = tomllib.loads((REPO_ROOT / "doctor.toml").read_text())
    declared = baseline["path_drift"]["native_only"]
    for binary, specs in path_drift.DEFAULT_NATIVE_ONLY.items():
        assert set(specs) <= set(declared[binary]), binary


def test_an_undeclared_mise_data_dir_is_still_recognised_by_shape(
    world: dict[str, Path], tmp_path: Path
) -> None:
    """A data dir no config names (``…/mise/installs/<slug>/<ver>``) is mise's."""
    stray = _exe(tmp_path / "elsewhere" / "mise" / "installs" / "antigravity-cli" / "9")
    report = _native_only(world, stray, _exe(world["native"]))
    assert any("resolves to mise's copy" in f for f in report.failures)


def test_a_dir_merely_named_mise_is_not_mise(
    world: dict[str, Path], tmp_path: Path
) -> None:
    """Control arm for the shape match: ``mise`` alone is not ``mise/installs``."""
    report = _native_only(world, _exe(tmp_path / "mise" / "bin"))
    assert (report.failures, report.warnings) == ((), ())
