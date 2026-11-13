"""opencode-jouet: keep jouet's agent guidance current in ~/.config/opencode/AGENTS.md.

OpenCode is not a `jouet setup` target (unlike Claude Code and Codex): it reads
~/.config/opencode/AGENTS.md as global instructions (OpenCode v2.2.7
packages/core/src/config/plugin/instruction.ts: `join(global.config, "AGENTS.md")`, where
`global.config` is `roots("opencode").config`, `XDG_CONFIG_HOME` or `~/.config` joined with
"opencode" (packages/util/src/global-roots.ts:6,15-16)). That file is also written by other
installers: codebase-memory-mcp's own `<!-- codebase-memory-mcp:start/end -->` block
(python/cbm/src/cbm/setup.py:51, cli.c:3777 at v0.12.1) and a hand-written herdr section, so this
command owns only the text between its own markers.

The marker upsert below follows codebase-memory-mcp's own `cbm_text_upsert_managed_block`
(v0.12.1 src/cli/config_text_edit.c:1017-1090, cli.c:3777): a managed block is found by scanning
for a line that is *exactly* the marker, once each, start before end; one marker, duplicate
markers, or the end before the start is refused unchanged rather than guessed at. A file with no
markers gets the block appended; an existing block is replaced in place, markers kept. The write
is atomic (temp file in the same directory, then a rename) and, like the C version's
`text_write_atomic_mode_at`, keeps the destination's existing file mode and skips the write
entirely when the content would not change.
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

from .models import Failure

START = "<!-- jouet:start -->"
END = "<!-- jouet:end -->"
# A line that is exactly the marker (MULTILINE's ^/$ anchor on line boundaries, excluding the \n).
_MARKER = "(?m)^{}$"


def target() -> Path:
    """OpenCode's global AGENTS.md: under XDG_CONFIG_HOME when set, as OpenCode resolves it, else ~/.config.
    Read lazily (not a module constant) so a test can set HOME or XDG_CONFIG_HOME first."""
    config = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(config) / "opencode/AGENTS.md"


class MarkersMalformedError(ValueError):
    """Only one marker, a duplicate of either, or the end marker before the start."""


def _stop(error: str) -> NoReturn:
    """The one JSON error event this command ends with; the exit code is always 1 (file untouched)."""
    sys.stderr.write(Failure(error=error).model_dump_json() + "\n")
    raise SystemExit(1)


def _fetch_block() -> str:
    """jouet's agent guidance for AGENTS.md (`jouet skill --format agents-md`); missing or failing stops here."""
    try:
        done = subprocess.run(
            ["jouet", "skill", "--format", "agents-md"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as failed:
        _stop(f"jouet: {failed.strerror}")
    if done.returncode != 0:
        _stop(f"jouet skill --format agents-md exited {done.returncode}: {done.stderr.strip()}")
    return done.stdout


def _region(text: str, path: Path) -> tuple[re.Match[str], re.Match[str]] | None:
    """The one (start, end) marker-line pair, or None when both are absent; anything else is malformed."""
    starts = list(re.finditer(_MARKER.format(re.escape(START)), text))
    ends = list(re.finditer(_MARKER.format(re.escape(END)), text))
    if not starts and not ends:
        return None
    if len(starts) == 1 and len(ends) == 1 and starts[0].start() < ends[0].start():
        return starts[0], ends[0]
    msg = f"{path}: jouet markers are malformed ({len(starts)} start, {len(ends)} end line(s))"
    raise MarkersMalformedError(msg)


def merged(text: str, block_content: str, path: Path) -> str:
    """text with jouet's block upserted: replaced in place when its markers are there, appended otherwise."""
    body = block_content.rstrip("\n")
    block = f"{START}\n{body}\n{END}\n"
    region = _region(text, path)
    if region is None:
        base = text.rstrip("\n")
        return f"{base}\n\n{block}" if base else block
    start_m, end_m = region
    # Consume the end marker line's own newline too, so nothing is duplicated or dropped around it.
    end_full = end_m.end() + 1 if end_m.end() < len(text) and text[end_m.end()] == "\n" else end_m.end()
    return text[: start_m.start()] + block + text[end_full:]


def write_atomic(path: Path, content: str) -> None:
    """content at path: a temp file in the same directory, then a rename; the old mode is kept."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode if path.exists() else None
    descriptor, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(content)
        if mode is not None:
            temp_path.chmod(mode)
        temp_path.replace(path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def sync() -> None:
    """Fetch jouet's block, then upsert it into target(); a malformed marker pair changes nothing."""
    path = target()
    block_content = _fetch_block()
    try:
        old = path.read_text() if path.exists() else ""
        new = merged(old, block_content, path)
        if new != old:
            write_atomic(path, new)
    except MarkersMalformedError as malformed:
        _stop(str(malformed))
    except OSError as failed:
        _stop(f"{path}: {failed.strerror or failed}")
