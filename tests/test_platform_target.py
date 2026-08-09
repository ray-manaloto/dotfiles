# Copyright (c) 2026 Raymond Manaloto
"""Tests for the one platform parameter (dotfiles_setup.platform_target, #673).

Two layers, mirroring ``test_bash_budget.py``: isolated logic tests that pin the
host arch and the environment so both branches of every resolution rule are
exercised, and real-repo guards that the tree currently passes the gate, that a
planted literal FAILS it, and that the CLI wires end-to-end.

The FAIL arms matter more than the PASS arms here. A completeness gate verified
only on a clean tree is decoration (`.claude/rules/probes-need-a-control-arm.md`
rule 2), and the regression this gate exists to catch — a platform literal
re-appearing at a site nobody remembered — is invisible in a green run.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import platform_target
from dotfiles_setup.image import _is_emulated

REPO_ROOT = Path(__file__).parent.parent

AMD64_TRIPLE = "linux/amd64/v2"
ARM64_TRIPLE = "linux/arm64/v8"


class _FakeUname:
    """Just enough of ``os.uname_result`` for :func:`host_arch`."""

    def __init__(self, machine: str) -> None:
        self.machine = machine


@pytest.fixture
def _no_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run with the repo pin absent, so host fallback is reachable.

    Without this the ambient mise `[env]` supplies DOTFILES_PLATFORM and every
    fallback assertion would silently be testing the pin instead — a fixture
    that can only produce one answer (`probes-need-a-control-arm.md` rule 8).
    """
    monkeypatch.delenv(platform_target.PLATFORM_ENV_VAR, raising=False)


def _pin_host(monkeypatch: pytest.MonkeyPatch, machine: str) -> None:
    monkeypatch.setattr(platform_target.os, "uname", lambda: _FakeUname(machine))


# --------------------------------------------------------------------------
# Arch normalisation — uname and docker disagree on the spelling
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("x86_64", "amd64"),
        ("amd64", "amd64"),
        ("AMD64", "amd64"),
        ("  arm64 ", "arm64"),
        ("aarch64", "arm64"),
        ("riscv64", None),
        ("", None),
    ],
)
def test_normalize_arch(token: str, expected: str | None) -> None:
    assert platform_target.normalize_arch(token) == expected


@pytest.mark.parametrize(
    ("machine", "expected"),
    [("x86_64", AMD64_TRIPLE), ("arm64", ARM64_TRIPLE), ("aarch64", ARM64_TRIPLE)],
)
def test_host_platform_is_a_full_triple(
    monkeypatch: pytest.MonkeyPatch, machine: str, expected: str
) -> None:
    """The parameter carries a microarchitecture LEVEL, not an arch word."""
    _pin_host(monkeypatch, machine)
    assert platform_target.host_platform() == expected


def test_host_arch_refuses_an_unknown_machine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guessing a microarchitecture level would build an image nothing runs."""
    _pin_host(monkeypatch, "riscv64")
    with pytest.raises(ValueError, match="unsupported host architecture"):
        platform_target.host_arch()


# --------------------------------------------------------------------------
# Resolution order: override -> repo pin -> host native
# --------------------------------------------------------------------------


def test_override_beats_the_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(platform_target.PLATFORM_ENV_VAR, AMD64_TRIPLE)
    assert platform_target.resolve_platform(ARM64_TRIPLE) == ARM64_TRIPLE


def test_pin_beats_the_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """The repo pin is why #673 changes no behaviour on an arm64 Mac."""
    _pin_host(monkeypatch, "arm64")
    monkeypatch.setenv(platform_target.PLATFORM_ENV_VAR, AMD64_TRIPLE)
    assert platform_target.resolve_platform() == AMD64_TRIPLE


@pytest.mark.usefixtures("_no_pin")
def test_host_is_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unpinned, the parameter really does default to the host architecture."""
    _pin_host(monkeypatch, "arm64")
    assert platform_target.resolve_platform() == ARM64_TRIPLE


@pytest.mark.usefixtures("_no_pin")
def test_blank_pin_is_not_a_pin(monkeypatch: pytest.MonkeyPatch) -> None:
    """An exported-but-empty var must fall through, not yield ``--platform=``."""
    _pin_host(monkeypatch, "x86_64")
    monkeypatch.setenv(platform_target.PLATFORM_ENV_VAR, "   ")
    assert platform_target.resolve_platform() == AMD64_TRIPLE


def test_explicit_env_mapping_is_honoured() -> None:
    assert (
        platform_target.resolve_platform(
            env={platform_target.PLATFORM_ENV_VAR: ARM64_TRIPLE}
        )
        == ARM64_TRIPLE
    )


# --------------------------------------------------------------------------
# Derived facts
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("triple", "arch", "os_arch", "machine"),
    [
        (AMD64_TRIPLE, "amd64", "linux/amd64", "x86_64"),
        (ARM64_TRIPLE, "arm64", "linux/arm64", "aarch64"),
        ("linux/amd64", "amd64", "linux/amd64", "x86_64"),
    ],
)
def test_derived_facts(triple: str, arch: str, os_arch: str, machine: str) -> None:
    assert platform_target.platform_arch(triple) == arch
    assert platform_target.os_arch(triple) == os_arch
    assert platform_target.expected_uname_machine(triple) == machine


def test_platform_arch_refuses_a_platform_with_no_arch() -> None:
    with pytest.raises(ValueError, match="no recognised architecture"):
        platform_target.platform_arch("linux/riscv64")


@pytest.mark.parametrize(
    ("host_machine", "triple", "emulated"),
    [
        ("x86_64", AMD64_TRIPLE, False),
        ("x86_64", ARM64_TRIPLE, True),
        ("arm64", AMD64_TRIPLE, True),
        ("arm64", ARM64_TRIPLE, False),
    ],
)
def test_is_emulated_both_arms(
    monkeypatch: pytest.MonkeyPatch,
    host_machine: str,
    triple: str,
    *,
    emulated: bool,
) -> None:
    """TSan aborts under emulation, so this must answer BOTH ways.

    ``image._is_emulated`` is asserted alongside because the mapping must exist
    once, not twice — a second copy is exactly how the two drift apart.
    """
    _pin_host(monkeypatch, host_machine)
    assert platform_target.is_emulated(triple) is emulated
    assert _is_emulated(triple) is emulated


@pytest.mark.parametrize(
    ("field", "expected"),
    [("triple", AMD64_TRIPLE), ("arch", "amd64"), ("machine", "x86_64")],
)
def test_platform_field(
    monkeypatch: pytest.MonkeyPatch, field: str, expected: str
) -> None:
    monkeypatch.setenv(platform_target.PLATFORM_ENV_VAR, AMD64_TRIPLE)
    assert platform_target.platform_field(field) == expected


def test_platform_field_rejects_an_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown platform field"):
        platform_target.platform_field("microarch")


# --------------------------------------------------------------------------
# The completeness gate — the tree, and a planted regression
# --------------------------------------------------------------------------


def test_repo_tree_has_no_stray_literals() -> None:
    violations = platform_target.find_violations(REPO_ROOT)
    assert violations == [], [v.render() for v in violations]


def test_repo_defaults_agree() -> None:
    assert platform_target.find_default_drift(REPO_ROOT) is None


def test_planted_literal_is_caught(tmp_path: Path) -> None:
    """FAIL arm: the regression is a literal at a site nobody remembered.

    Mutating a REAL consumer (a python module under the scanned tree) rather
    than a synthetic name, because a mutation that is not the real failure
    proves nothing.
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    target = tmp_path / "python" / "src" / "dotfiles_setup" / "docker.py"
    target.parent.mkdir(parents=True)
    target.write_text('CMD = ["docker", "pull", "--platform", "linux/amd64/v2"]\n')
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)

    violations = platform_target.find_violations(tmp_path)

    assert [v.literal for v in violations] == ["linux/amd64/v2"]
    assert violations[0].path == "python/src/dotfiles_setup/docker.py"
    assert violations[0].line == 1
    assert platform_target.PLATFORM_ENV_VAR in violations[0].render()


def test_untracked_literal_is_invisible_by_design(tmp_path: Path) -> None:
    """Control arm for the scan's bound: it enumerates the TRACKED tree.

    Stated rather than assumed, because "no findings" from a bounded search is
    not the same answer as "no literals".
    """
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "stray.py").write_text('P = "linux/amd64/v2"\n')

    assert platform_target.find_violations(tmp_path) == []


@pytest.mark.parametrize("excluded", ["tests/t.py", "docs/d.toml", "plugins/p.py"])
def test_excluded_trees_may_name_a_platform(tmp_path: Path, excluded: str) -> None:
    """Fixtures and archived evidence legitimately carry concrete platforms."""
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    target = tmp_path / excluded
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('P = "linux/arm64/v8"\n')
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)

    assert platform_target.find_violations(tmp_path) == []


def test_default_drift_between_the_two_permitted_sites(tmp_path: Path) -> None:
    """FAIL arm: bake and mise disagreeing is the split-brain, restated."""
    (tmp_path / "mise.toml").write_text(
        "[env]\n"
        f"{platform_target.PLATFORM_ENV_VAR} = "
        "\"{{ env.DOTFILES_PLATFORM | default(value='linux/amd64/v2') }}\"\n"
    )
    (tmp_path / "docker-bake.hcl").write_text(
        'variable "PLATFORM" {\n  default = "linux/arm64/v8"\n}\n'
    )

    drift = platform_target.find_default_drift(tmp_path)

    assert drift is not None
    assert "linux/amd64/v2" in drift
    assert "linux/arm64/v8" in drift


def test_a_deleted_default_is_a_failure_not_a_pass(tmp_path: Path) -> None:
    """A missing declaration must not read as 'the two agree'."""
    (tmp_path / "docker-bake.hcl").write_text(
        'variable "PLATFORM" {\n  default = "linux/amd64/v2"\n}\n'
    )

    drift = platform_target.find_default_drift(tmp_path)

    assert drift is not None
    assert platform_target.PLATFORM_ENV_VAR in drift


# --------------------------------------------------------------------------
# CLI wiring — a library nothing calls is not a gate
# --------------------------------------------------------------------------


def _cli(*args: str, platform: str | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    if platform is not None:
        env[platform_target.PLATFORM_ENV_VAR] = platform
    return subprocess.run(
        ["uv", "run", "--project", "python", "dotfiles-setup", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
    )


def test_platform_literals_cli_passes_on_the_real_tree() -> None:
    assert _cli("platform-literals").returncode == 0


@pytest.mark.parametrize(
    ("triple", "field", "expected"),
    [
        (AMD64_TRIPLE, "triple", AMD64_TRIPLE),
        (AMD64_TRIPLE, "machine", "x86_64"),
        (ARM64_TRIPLE, "machine", "aarch64"),
    ],
)
def test_platform_cli_prints_the_resolved_fact(
    triple: str, field: str, expected: str
) -> None:
    """`verify-arch` and the benchmark script read these; they must be exact.

    The pin is passed explicitly rather than inherited: a test that reads the
    ambient value would pass on whatever the shell happened to export, which is
    the one thing it must not certify.
    """
    result = _cli("platform", field, platform=triple)
    assert result.returncode == 0
    assert result.stdout.strip() == expected
