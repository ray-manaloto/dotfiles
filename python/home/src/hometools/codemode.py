"""claude-code-mode: one interactive Claude session in Code Mode, every override given for this launch only."""

# Code Mode is opt-in per launch (owner, 2026-11-15): ~/.claude/settings.json stays as it is. In the live trial
# (Claude Code 2.1.325, chief-of-staff's research notes, section 9) it turned on only with the shell variable below
# and all three of: Remote Control off, no mod folders (the side-note mods hook tool.call), and the
# code-modernization plugin off (its mod hooks tool.call too); with any of them left, startup said Code Mode "doesn't
# yet work with an installed mod (a plugin with JavaScript hooks) that checks tool calls". A Code Mode session
# resumes only with the variable set, which roll:stop knows (roll/session.py code_mode).

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NoReturn

from . import nativeclaude
from .models import Failure

VARIABLE = "CLAUDE_CODE_EXPERIMENTAL_CODE_MODE"
SETTINGS = {
    "remoteControlAtStartup": False,
    "env": {"CLAUDE_CODE_PLUGIN_DIRS": ""},
    "enabledPlugins": {"code-modernization@claude-plugins-official": False},
}
# What a session started from another Claude session (a herdr tab opened by an agent) inherits and must not keep:
# CLAUDE_CODE_CHILD_SESSION turns its transcript off, so it could never be resumed; the rest name the parent's
# session, socket and plugin data. CLAUDE_CODE_PLUGIN_DIRS would load the mods that keep Code Mode off.
INHERITED = frozenset({
    "CLAUDE_CODE_CHILD_SESSION", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_BRIDGE_SESSION_ID",
    "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_EXECPATH",
    "CLAUDE_CODE_SESSION_ATTENDED", "CLAUDECODE", "CLAUDE_PID", "CLAUDE_EFFORT", "CLAUDE_PLUGIN_DATA",
    "CLAUDE_CODE_PLUGIN_DIRS",
})  # fmt: skip
UV_RUN = frozenset({"VIRTUAL_ENV", "UV_RUN_RECURSION_DEPTH"})


def command(prompt: str | None) -> list[str]:
    return [
        "claude",
        "--settings",
        json.dumps(SETTINGS, separators=(",", ":")),
        *(["--", prompt] if prompt else []),
    ]  # `--`: a prompt like --help stays the prompt


def environment(inherited: Mapping[str, str], venv: Path) -> dict[str, str]:
    """inherited without the session markers above and without what `uv run` added to start hometools (its venv
    first on PATH, VIRTUAL_ENV, its recursion count), so the session's shell is the caller's, not this package's."""
    kept = {name: value for name, value in inherited.items() if name not in INHERITED | UV_RUN}
    paths = [entry for entry in kept.get("PATH", "").split(os.pathsep) if entry and Path(entry) != venv / "bin"]
    return kept | {"PATH": os.pathsep.join(paths), VARIABLE: "1"}


def fail(error: str, code: int) -> NoReturn:
    sys.stderr.write(Failure(error=error).model_dump_json() + "\n")
    raise SystemExit(code)


def main(rest: Sequence[str]) -> NoReturn:
    parser = argparse.ArgumentParser(prog="hometools claude-code-mode")
    # mise runs a global file task elsewhere and names the caller's folder in MISE_ORIGINAL_CWD.
    here = os.environ.get("MISE_ORIGINAL_CWD", ".")
    parser.add_argument("--folder", default=here, help="The folder the session works in (default: the caller's)")
    parser.add_argument("prompt", nargs="?", help="The first prompt")
    args = parser.parse_args(rest)
    folder = Path(args.folder).expanduser()
    if not folder.is_dir():
        fail(f"claude-code-mode: {folder} is not a folder", 2)
    # exec finds claude on PATH, where a stray npm copy in a mise node comes ahead of the native one.
    if stray := nativeclaude.stray(Path.home()):
        fail(f"claude-code-mode: Claude Code outside its native install at {stray[0]}; run claude:doctor", 3)
    os.chdir(folder)
    try:
        env = environment(os.environ, Path(sys.prefix))
        os.execvpe("claude", command(args.prompt), env)  # noqa: S606 - replaces this process
    except OSError as failed:  # claude missing or not runnable: the one error this step turns into its event
        fail(f"claude-code-mode: claude could not start: {failed.strerror}", 127)
