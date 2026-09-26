# Copyright (c) 2026 Raymond Manaloto
"""Regression coverage for keeping test-created mise configs out of host state (#1169).

Ported from knowledge-base#818 `tests/test_mise_state_isolation.py`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_CHILD_TIMEOUT = 60


def _tracked_config_mapping(state_dir: Path) -> dict[str, str]:
    """Return the exact tracked-config entry-name to resolved-target mapping."""
    tracked_configs = state_dir / "tracked-configs"
    if not tracked_configs.is_dir():
        return {}
    return {
        entry.name: str(entry.resolve(strict=False))
        for entry in sorted(tracked_configs.iterdir())
    }


def test_child_pytest_registers_mise_config_only_in_its_isolated_state(
    tmp_path: Path,
) -> None:
    """A nested pytest run must never add its throwaway config to outer mise state.

    FAIL ARM: removing ``monkeypatch.setenv`` from ``isolated_mise_state`` makes
    the child inherit ``outer_state``; mise then adds the scratch config there,
    changing the exact mapping below and turning this test red.
    """
    if shutil.which("mise") is None:
        pytest.skip("mise does not resolve on PATH")

    outer_state = tmp_path / "outer-state"
    outer_tracked = outer_state / "tracked-configs"
    outer_tracked.mkdir(parents=True)
    seed_config = tmp_path / "seed" / "mise.toml"
    seed_config.parent.mkdir()
    seed_config.write_text("[tools]\n", encoding="utf-8")
    (outer_tracked / "seed").symlink_to(seed_config)
    outer_before = _tracked_config_mapping(outer_state)

    marker = tmp_path / "child-tmp-path"
    scratch_test = tmp_path / "test_child_mise_state.py"
    scratch_test.write_text(
        f"""from __future__ import annotations

import os
import subprocess
from pathlib import Path

_MARKER = Path({str(marker)!r})


def test_real_mise_registers_the_scratch_config(tmp_path: Path) -> None:
    config = tmp_path / "mise.toml"
    config.write_text("[tools]\\n", encoding="utf-8")
    child_env = {{**os.environ, "MISE_TRUSTED_CONFIG_PATHS": str(tmp_path)}}
    proc = subprocess.run(
        ["mise", "ls", "--json"],
        cwd=tmp_path,
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
        timeout={_CHILD_TIMEOUT},
    )
    assert proc.returncode == 0, proc.stderr
    _MARKER.write_text(str(tmp_path), encoding="utf-8")
""",
        encoding="utf-8",
    )

    xdg_state_home = tmp_path / "xdg-state"
    xdg_state_home.mkdir()
    child_env = {
        **os.environ,
        "MISE_STATE_DIR": str(outer_state),
        "XDG_STATE_HOME": str(xdg_state_home),
    }
    child = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-o",
            "addopts=",
            "-p",
            "no:cacheprovider",
            "-p",
            "conftest",
            str(scratch_test),
        ],
        cwd=_REPO_ROOT / "tests",
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
        timeout=_CHILD_TIMEOUT,
    )

    assert child.returncode == 0, child.stdout + child.stderr
    assert _tracked_config_mapping(outer_state) == outer_before

    child_tmp_path = Path(marker.read_text(encoding="utf-8"))
    child_mapping = _tracked_config_mapping(
        child_tmp_path.parent / f"{child_tmp_path.name}.mise-state"
    )
    child_config = str((child_tmp_path / "mise.toml").resolve())
    assert child_config in child_mapping.values()
