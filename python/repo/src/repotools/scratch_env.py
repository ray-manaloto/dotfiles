"""scratch-env: run one command from this checkout with every home-derived path inside a scratch folder."""

# The climb stops above the checkout and auto-install is off, so a config the climb reached installs nothing.
# mise runs the root task from the checkout, as env.sh's cd to its own top did.

import os
import subprocess
import sys
import sysconfig
from pathlib import Path

from .models import Failure, ScratchEnv

FOLDERS = {
    "HOME": "home",
    "TMPDIR": "tmp",
    "XDG_CONFIG_HOME": "config",
    "XDG_DATA_HOME": "data",
    "XDG_STATE_HOME": "state",
    "XDG_CACHE_HOME": "cache",
}


def caller_path() -> str:
    """PATH as mise gave the task, its tool paths first: uv run puts the venv's scripts folder in front once (uv
    0.13.7 crates/uv-project-commands/src/run.rs:1195-1219), so that one copy goes and a caller's own stays."""
    entries = os.environ["PATH"].split(os.pathsep)
    if entries[0] == sysconfig.get_path("scripts"):
        entries.pop(0)
    return os.pathsep.join(entries)


def isolated(folder: Path, top: Path) -> dict[str, str]:
    return {
        **{name: str(folder / sub) for name, sub in FOLDERS.items()},
        "USER": os.environ["USER"],
        "PATH": caller_path(),
        "TERM": "dumb",
        "MISE_TRUSTED_CONFIG_PATHS": str(top),
        "MISE_CEILING_PATHS": str(top.parent),
        "MISE_AUTO_INSTALL": "0",
    }


def run(options: ScratchEnv) -> None:
    top = Path.cwd().resolve()
    # A relative folder is the caller's: mise runs the task from the checkout and passes the folder `mise run`
    # started in as MISE_ORIGINAL_CWD (src/task/task_executor.rs:3137-3143 at v2026.11.3).
    folder = Path(os.environ.get("MISE_ORIGINAL_CWD", top)) / options.folder
    for sub in FOLDERS.values():
        (folder / sub).mkdir(parents=True, exist_ok=True)
    env = isolated(folder, top)
    sys.stdout.flush()
    sys.stderr.flush()
    # The receipt that the climb stopped, on stderr: the only config listed is this checkout's mise.toml.
    subprocess.run(["mise", "config", "ls"], env=env, stdout=sys.stderr.fileno(), check=True)
    try:
        done = subprocess.run(options.command, env=env, check=False)
    except OSError as failed:
        # As env(1) reports a command it can't start: 127 when it isn't there, 126 when it can't run.
        sys.stderr.write(Failure(error=f"{options.command[0]}: {failed.strerror}").model_dump_json() + "\n")
        raise SystemExit(127 if isinstance(failed, FileNotFoundError) else 126) from None
    if done.returncode:
        # A signal's death reads as a shell reports it, 128 plus the signal.
        raise SystemExit(128 - done.returncode if done.returncode < 0 else done.returncode)
