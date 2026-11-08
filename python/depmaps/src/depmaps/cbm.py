"""The codebase-memory-mcp CLI: its version, index_repository and delete_project."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .events import DepmapsError
from .models import Config, ErrorCode
from .process import run


def call(cfg: Config, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return run(cfg.cbm, *args, cwd=Path.home(), timeout=None)
    except OSError as error:
        raise DepmapsError(ErrorCode.cbm_failed, f"depmaps: {cfg.cbm}: {error}") from None


def version(cfg: Config) -> str:
    """The last field of `--version`: codebase-memory-mcp 0.12.1 prints `codebase-memory-mcp 0.12.1`."""
    done = call(cfg, "--version")
    fields = done.stdout.split()
    if done.returncode or not fields:
        raise DepmapsError(ErrorCode.cbm_failed, f"depmaps: {cfg.cbm} --version exited {done.returncode}")
    return fields[-1]


def tool(cfg: Config, name: str, arguments: dict[str, Any], accepted: set[str]) -> None:
    """One tool call through `cli --quiet`: the reply's text, one JSON object, on stdout with exit status 0.

    A reply marked isError, such as delete_project's not_found, goes to stderr with exit status 1 instead
    (src/main.c:711-736 at 0.12.1).
    """
    done = call(cfg, "cli", "--quiet", name, json.dumps(arguments))
    lines = (done.stderr if done.returncode else done.stdout).strip().splitlines()
    try:
        reply = json.loads(lines[-1]) if lines else None
    except json.JSONDecodeError:
        reply = None
    status = reply.get("status") if isinstance(reply, dict) else None
    if status not in accepted:
        detail = (done.stdout.strip() or done.stderr.strip())[:500]
        raise DepmapsError(ErrorCode.cbm_failed, f"depmaps: cbm {name} exited {done.returncode}: {detail}")


def index(cfg: Config, source: Path, project: str) -> None:
    arguments = {"repo_path": str(source), "name": project, "mode": "full", "persistence": True}
    tool(cfg, "index_repository", arguments, {"indexed"})


def delete(cfg: Config, project: str) -> None:
    # A project already gone answers not_found, and exit status 1, at 0.12.1.
    tool(cfg, "delete_project", {"project": project}, {"deleted", "not_found"})


def database(project: str) -> Path:
    """The project's graph, where cbm keeps it at 0.12.1.

    The cache folder is CBM_CACHE_DIR when set and non-empty, else ~/.cache/codebase-memory-mcp
    (src/foundation/platform.c:635-648), and a project's file is <cache>/<project>.db (src/store/store.c:1428).
    """
    cache = os.environ.get("CBM_CACHE_DIR") or str(Path.home() / ".cache/codebase-memory-mcp")
    return Path(cache) / f"{project}.db"
