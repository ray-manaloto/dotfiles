"""No .claude/settings.local.json: its rules belong in the tracked .claude/settings.json."""

from .git import main_checkout, top, tracked
from .models import Check, Finding

LOCAL = ".claude/settings.local.json"
MOVE = f"move its rules to .claude/settings.json, then delete {LOCAL}"


def findings() -> list[Finding]:
    # No glob sees a gitignored file, so each place is tested by path. The main checkout is where Claude Code
    # writes it from a linked worktree; in the main checkout itself the two are one file.
    main = main_checkout()
    files = dict.fromkeys(path.resolve() for path in (top() / LOCAL, main / LOCAL) if path.exists())
    found = [Finding(path=str(path), check=Check.settings_local, detail=f"exists; {MOVE}") for path in files]
    if tracked(LOCAL):
        found.append(Finding(path=LOCAL, check=Check.settings_local, detail=f"is in the index; {MOVE}"))
    return found
