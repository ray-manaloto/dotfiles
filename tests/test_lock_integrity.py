# Copyright (c) 2026 Raymond Manaloto
"""Tests for the lockfile platform-coverage gate (dotfiles_setup.lock_integrity).

Why this gate exists alongside ``test_lock_coverage.py``: that module asserts
every lockfile *covers its config's tools* and that versions match pins — a
TOOL-level view. The #370 damage is invisible to it. When `mise install` on
macOS re-locked ``mise.lock``, the ``[[tools.*]]`` block count did not move at
all (226 before, 226 after); what vanished was 548 lines of linux conda
entries. A tool-count check reported "fine". So the two gates are complementary
and neither substitutes for the other.

Both arms are exercised for each finding kind, and the two "legitimate change"
shapes (adding and removing a tool) are asserted to stay silent — a gate that
fires on ordinary work gets disabled.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import lock_integrity

REPO_ROOT = Path(__file__).parent.parent


def _tool_lock(name: str, version: str, platforms: tuple[str, ...]) -> str:
    """A minimal lockfile body for one tool across ``platforms``."""
    quoted = f'"{name}"' if not name.isidentifier() else name
    out = [f"[[tools.{quoted}]]", f'version = "{version}"', ""]
    for platform in platforms:
        out += [
            f'[tools.{quoted}."platforms.{platform}"]',
            f'checksum = "sha256:{platform}"',
            "",
        ]
    return "\n".join(out)


def _conda_lock(platforms: tuple[str, ...]) -> str:
    return "\n".join(
        f'[conda-packages.{p}."zlib-1.3-h0"]\nchecksum = "sha256:{p}"\n'
        for p in platforms
    )


# --------------------------------------------------------------------------
# conda arm — the one the real-world failure actually trips
# --------------------------------------------------------------------------


def test_conda_platform_loss_is_reported() -> None:
    committed = _conda_lock(("linux-x64", "linux-arm64", "windows-x64"))
    candidate = _conda_lock(("macos-arm64",))
    findings = lock_integrity.regressions(committed, candidate)
    assert len(findings) == 1
    assert "conda-packages" in findings[0]
    assert "linux-x64" in findings[0]
    # The message must name the cause, not just the symptom — the operator's
    # next action depends on knowing it was an install, not a lock.
    assert "mise install" in findings[0]


def test_conda_platform_gain_is_not_a_regression() -> None:
    committed = _conda_lock(("linux-x64",))
    candidate = _conda_lock(("linux-x64", "macos-arm64"))
    assert lock_integrity.regressions(committed, candidate) == []


# --------------------------------------------------------------------------
# per-tool arm — NOT exercised by the observed damage, so it is proven here
# --------------------------------------------------------------------------


def test_tool_platform_loss_is_reported() -> None:
    committed = _tool_lock("biome", "2.5.6", ("linux-x64", "macos-arm64"))
    candidate = _tool_lock("biome", "2.5.6", ("macos-arm64",))
    findings = lock_integrity.regressions(committed, candidate)
    assert len(findings) == 1
    assert "tool biome" in findings[0]
    assert "linux-x64" in findings[0]


def test_quoted_backend_qualified_tool_name_is_parsed() -> None:
    """Backend-qualified names are quoted in the lock; the regex must accept them."""
    name = "aqua:jackchuka/mdschema"
    committed = _tool_lock(name, "0.14.1", ("linux-x64", "macos-arm64"))
    assert lock_integrity.tool_platforms(committed) == {
        name: {"linux-x64", "macos-arm64"}
    }
    candidate = _tool_lock(name, "0.14.1", ("macos-arm64",))
    findings = lock_integrity.regressions(committed, candidate)
    assert len(findings) == 1
    assert name in findings[0]


# --------------------------------------------------------------------------
# legitimate changes must stay silent
# --------------------------------------------------------------------------


def test_version_bump_keeping_platforms_passes() -> None:
    """The exact shape of a deliberate pin bump + scoped re-lock."""
    platforms = ("linux-x64", "linux-arm64", "macos-arm64")
    committed = _tool_lock("biome", "2.5.5", platforms)
    candidate = _tool_lock("biome", "2.5.6", platforms)
    assert lock_integrity.regressions(committed, candidate) == []


def test_tool_removal_is_not_a_regression() -> None:
    committed = _tool_lock("biome", "2.5.6", ("linux-x64", "macos-arm64"))
    assert lock_integrity.regressions(committed, "") == []


def test_tool_addition_is_not_a_regression() -> None:
    committed = _tool_lock("biome", "2.5.6", ("linux-x64",))
    candidate = committed + "\n" + _tool_lock("rumdl", "v0.2.45", ("linux-x64",))
    assert lock_integrity.regressions(committed, candidate) == []


# --------------------------------------------------------------------------
# real-repo guards
# --------------------------------------------------------------------------


def test_committed_root_lock_retains_linux_conda_coverage() -> None:
    """The committed lock must still carry the amd64 image's conda entries.

    This is the absolute floor the regression check cannot express: if a
    damaged lock ever lands on the default branch, HEAD becomes the damaged
    baseline and the diff-based gate goes quiet from then on.
    """
    platforms = lock_integrity.conda_platforms((REPO_ROOT / "mise.lock").read_text())
    assert "linux-x64" in platforms, (
        "mise.lock lost its linux-x64 conda entries — the amd64 devcontainer "
        "needs them (jdx/mise#7700)"
    )


def test_repo_currently_passes() -> None:
    assert lock_integrity.check_lockfiles(REPO_ROOT) == []


def test_untracked_lockfile_is_skipped() -> None:
    """A path git does not know at HEAD has no baseline, and must not fail."""
    assert lock_integrity.committed_text(REPO_ROOT, "no/such.lock") is None
    assert lock_integrity.check_lockfiles(REPO_ROOT, ("no/such.lock",)) == []


def test_bare_lock_is_refused() -> None:
    """No tool named must REFUSE, not fall through to a whole-file re-lock.

    The whole-file form is the destructive one (measured: conda 962 -> 427 with
    no config change at all), so the canonical task has to fail closed. A
    fall-through would make `mise run lock` the dangerous path it used to be.
    """
    assert lock_integrity.scoped_lock_main(REPO_ROOT, []) == 1


def test_scoped_lock_rejects_undeclared_tool() -> None:
    """An unrecognised name must fail, because `mise lock` itself returns 0.

    Measured: `mise lock definitely:not/a-tool` exits 0 with an empty diff, and
    so does a short name standing in for a backend-qualified key. Trusting the
    exit code would report a successful re-lock that never happened.
    """
    assert lock_integrity.scoped_lock_main(REPO_ROOT, ["definitely:not/a-tool"]) == 1


def test_short_name_for_backend_qualified_key_is_rejected() -> None:
    """`betterleaks` is not the key; `aqua:betterleaks/betterleaks` is."""
    declared = lock_integrity.declared_host_tools(REPO_ROOT)
    assert "aqua:betterleaks/betterleaks" in declared
    assert "betterleaks" not in declared
    assert lock_integrity.scoped_lock_main(REPO_ROOT, ["betterleaks"]) == 1


def test_declared_host_tools_spans_both_config_files() -> None:
    """The host config is root mise.toml PLUS the shared fragment."""
    declared = lock_integrity.declared_host_tools(REPO_ROOT)
    assert "biome" in declared, "root mise.toml tools missing"
    assert "hk" in declared, ".config/mise/conf.d/shared.toml tools missing"


def test_declared_tools_scopes_to_exactly_the_given_files() -> None:
    """`declared_tools` is the parameterised primitive `declared_host_tools` wraps.

    A caller that owns only ONE of the two config files — `lock_shared`,
    scoped to the shared fragment alone (#650 round 2's HIGH 2: the union
    let a root-only tool like `aws-cli` pass validation for a task that never
    touches the root lock) — must be able to ask for exactly that file, not
    the union.
    """
    shared_only = lock_integrity.declared_tools(
        REPO_ROOT, (".config/mise/conf.d/shared.toml",)
    )
    assert "hk" in shared_only
    assert "biome" not in shared_only, "root-only tool leaked into a scoped read"
    assert "aws-cli" not in shared_only, "root-only tool leaked into a scoped read"


def test_cli_wires_end_to_end() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            "python",
            "dotfiles-setup",
            "lock-check",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
