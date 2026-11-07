"""The integration tier: this checkout's toolchain:verify through real mise, uv and the toolchain on this Mac."""

# The in-process tests run the real tools on a scratch copy of the toolchain (tests/scratch_toolchain.py); this tier
# runs them on the install itself, with this Mac's own conf.d and mise.lock. It only reads: verify changes nothing,
# task history is off for it, and bootstrap:toolchain stays out because it installs packages. A copy of
# ~/.config/mise links each entry back, except config.toml and tasks, which link to this checkout, as `mise run
# shell:apply` deploys them; MISE_CONFIG_DIR moves the whole global config folder there, conf.d and mise.lock
# included.

# This is the check that the config's [vars] versions are the ones installed: verify compares them exactly. The
# in-process tests take theirs from the install, so only this tier fails a [vars] bump whose version is not
# installed or is mistyped; repotools toolchain-gate runs it at pre-commit on any [vars] change. To bump gcc or
# llvm, install the new version first, then edit [vars] and run `mise run bootstrap:toolchain`.

import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(sys.platform != "darwin", reason="the held toolchain is a macOS Homebrew install"),
]

CHECKOUT = Path(__file__).resolve().parents[3]
DEPLOYED = CHECKOUT / "unix/home/.config/mise"


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """~/.config/mise as deployed from this checkout."""
    folder = tmp_path / "mise"
    folder.mkdir()
    for entry in (Path.home() / ".config/mise").iterdir():
        target = DEPLOYED / entry.name if entry.name in {"config.toml", "tasks"} else entry
        (folder / entry.name).symlink_to(target)
    return folder


def verify(config_dir: Path, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"} | {
        "MISE_CONFIG_DIR": str(config_dir),
        # No run record under $MISE_STATE_DIR/task-history (mise src/task/task_history.rs:175-194). The state folder
        # stays the user's: it holds the app receipts `bootstrap packages status` reads
        # (crates/mise-system-packages/src/brew/cask/state.rs:2012).
        "MISE_TASK_HISTORY": "0",
        # Read-only: no tool install before the task runs (mise src/task/task_tool_installer.rs:234-245).
        "MISE_AUTO_INSTALL": "0",
    }
    argv = ["mise", "run", "toolchain:verify"]
    return subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, check=False)


def test_the_real_toolchain_verifies(config_dir: Path, tmp_path: Path) -> None:
    done = verify(config_dir, tmp_path)
    assert done.returncode == 0, done.stderr
    held = tomllib.loads((DEPLOYED / "config.toml").read_text())["vars"]
    want = rf"toolchain:verify OK: clang {re.escape(held['llvm'])}, gcc {re.escape(held['gcc'])}, .*"
    assert re.fullmatch(want, done.stdout.splitlines()[-1]), done.stdout
    assert str(config_dir / "tasks/toolchain/verify") in done.stderr


@pytest.mark.parametrize(("key", "program"), [("gcc", "gcc"), ("llvm", "clang")])
def test_a_vars_version_not_installed_fails(key: str, program: str, config_dir: Path, tmp_path: Path) -> None:
    # A bump to a version this Mac does not have, as a typo or an install not yet done would leave it.
    text = (DEPLOYED / "config.toml").read_text()
    held = tomllib.loads(text)["vars"][key]
    line = f'{key} = "{held}"'
    assert text.count(line) == 1
    (config_dir / "config.toml").unlink()
    (config_dir / "config.toml").write_text(text.replace(line, f'{key} = "{held}.99"'))
    done = verify(config_dir, tmp_path)
    assert done.returncode == 1
    assert f'{{"error":"{program} {held} is not [vars] {key} {held}.99"}}' in done.stderr
