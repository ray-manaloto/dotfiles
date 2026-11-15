"""claude-doctor: Claude Code is the native install only, and no installer has hooked the shell startup files."""

# Claude Code comes only from its native installer, ~/.local/bin/claude, which updates itself. A global npm install
# into a mise node puts a second, older claude ahead of it on a shell's PATH (mise's install bins come first), so new
# sessions and roll:start would run that one. These checks read the filesystem, not PATH: a task's PATH is not a
# tab's. roll:start and roll:all refuse while stray() finds one (roll/__init__.py main).

import os
import re
import sys
from collections.abc import Iterator
from pathlib import Path

from .models import Failure

PACKAGE = Path("lib/node_modules/@anthropic-ai/claude-code")
# A line sourcing `$HOME/.local/share/../bin/env` (or env.fish): what an installer that derives its bin folder from
# XDG_DATA_HOME appends to every startup file it finds. dotfiles never writes that path.
HOOKED = re.compile(r"^\s*(\.|source)\s.*/\.\./bin/env(\.fish)?\b", re.MULTILINE)
STARTUP = (".profile", ".bash_profile", ".bashrc", ".zprofile", ".zshrc", ".config/zsh/.zshrc", ".config/zsh/.zprofile")


def folders(home: Path) -> tuple[list[Path], Path]:
    """mise's install folders and its shims folder, resolved as mise does (mise v2026.11.8
    crates/mise-util/src/env.rs:92-93, 157-158, 198-218; crates/mise-util/src/dirs.rs:39-44)."""
    env = os.environ
    data = Path(env.get("MISE_DATA_DIR") or Path(env.get("XDG_DATA_HOME") or home / ".local/share") / "mise")
    installs = Path(env.get("MISE_INSTALLS_DIR") or data / "installs")
    store = env.get("MISE_INSTALL_STORE_DIR")
    return [installs, *([Path(store)] if store else [])], Path(env.get("MISE_SHIMS_DIR") or data / "shims")


def present(path: Path) -> bool:
    return path.exists() or path.is_symlink()  # a dangling link to a removed package still runs first on PATH


def stray(home: Path) -> list[Path]:
    """Every claude-code package or claude command mise holds: under a node install, an install bin or the shims."""
    installs, shims = folders(home)
    found = [path for folder in installs for pattern in (f"*/{PACKAGE}", "*/bin/claude")
             for path in folder.glob(pattern) if present(path)]  # fmt: skip
    return sorted({*found, *([shims / "claude"] if present(shims / "claude") else [])})


def startup_files(home: Path) -> Iterator[Path]:
    yield from (home / name for name in STARTUP)
    yield from sorted((home / ".config/fish/conf.d").glob("*.fish"))


def hooked(home: Path) -> list[Path]:
    """The startup files with an installer's `.../../bin/env` line."""
    return [path for path in startup_files(home) if path.is_file() and HOOKED.search(path.read_text(errors="replace"))]


def problems(home: Path) -> list[str]:
    found = [f"{path}: Claude Code outside its native install; remove it (`npm uninstall -g @anthropic-ai/claude-code`"
             " with that node's npm)" for path in stray(home)]  # fmt: skip
    found += [f"{path}: an installer's PATH line (`.../../bin/env`); remove that line" for path in hooked(home)]
    return found


def main() -> None:
    found = problems(Path.home())
    if found:
        sys.stderr.write(Failure(error="\n".join(found)).model_dump_json() + "\n")
        raise SystemExit(1)
    sys.stdout.write("claude:doctor OK: only the native claude, no installer PATH lines\n")
