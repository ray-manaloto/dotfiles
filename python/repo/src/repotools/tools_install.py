"""Install the committed workflow and repository tools, repairing unhealthy copies."""

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from pydantic import ValidationError

from .git import git
from .models import Failure, Healthy, ToolAction, ToolInstalled, ToolReceipt

TOOLS = {"workflowtools": "python/workflow", "repotools": "python/repo"}


def health(tool: Path, bin_dir: Path) -> str | Healthy:
    executable = bin_dir / tool.name
    try:
        records = list(tool.glob(f"lib/python*/site-packages/{tool.name}-*.dist-info/RECORD"))
        if len(records) != 1:
            return "it has two RECORD files" if records else "its RECORD is missing"
        if not executable.is_file():
            return f"{executable} is missing"
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("VIRTUAL_ENV", None)
        probe = subprocess.run(
            [executable], capture_output=True, check=False, timeout=30, stdin=subprocess.DEVNULL, env=env
        )
        if probe.returncode != 1 or probe.stdout:
            return f"{executable} did not answer the start probe (exit {probe.returncode})"
        try:
            failure = Failure.model_validate_json(probe.stderr)
        except ValidationError:
            # Stderr that is not one JSON error event, invalid UTF-8 included, is a wrong answer; the caller reports
            # it as the reason.
            failure = None
        if failure is None or not failure.error.startswith(f"{tool.name}: the first argument is one of"):
            return f"{executable} did not return the expected start refusal"
        return Healthy(record_sha256=hashlib.sha256(records[0].read_bytes()).hexdigest())
    except (OSError, subprocess.TimeoutExpired) as error:
        # A console script that cannot start (no execute permission, a missing interpreter) or hangs. The caller
        # writes the text as a JSON error event before it repairs the copy, or raises it when a fresh install fails.
        return f"{executable} did not start: {error}"


def read_receipt(path: Path) -> ToolReceipt | str | None:
    """The receipt, None when there is none yet, or the problem that makes it unreadable."""
    if not path.exists():
        return None
    try:
        return ToolReceipt.model_validate_json(path.read_bytes())
    except ValidationError as error:
        # A corrupt receipt: the caller writes this text as a JSON error event before it repairs the copy.
        return f"its receipt is invalid: {error.errors()[0]['msg']}"


def problems(
    name: str, tree: str, receipt: ToolReceipt | str | None, healthy: Healthy | str, *, present: bool
) -> list[str]:
    """Every problem with the installed copy; a first install or a new commit is not a problem."""
    found = []
    if isinstance(receipt, str):
        found.append(receipt)
    elif receipt is not None and receipt.name != name:
        found.append(f"its receipt names {receipt.name}")
    if isinstance(healthy, str):
        # A copy that is there, or that a receipt says was installed, and is not healthy.
        if present or isinstance(receipt, ToolReceipt):
            found.append(healthy)
    elif isinstance(receipt, ToolReceipt) and receipt.tree == tree and healthy.record_sha256 != receipt.record_sha256:
        found.append("its RECORD changed since the receipt")
    return found


def write_receipt(path: Path, receipt: ToolReceipt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temporary:
        temporary.write(receipt.model_dump_json() + "\n")
    try:
        Path(temporary.name).replace(path)
    finally:
        Path(temporary.name).unlink(missing_ok=True)


def install(name: str, top: Path, tool_dir: Path, bin_dir: Path, state: Path) -> ToolInstalled:
    source = TOOLS[name]
    tree = git("rev-parse", f"HEAD:{source}").strip()
    path = state / "dotfiles" / "tools" / f"{name}.json"
    receipt = read_receipt(path)
    healthy = health(tool_dir / name, bin_dir)
    found = problems(name, tree, receipt, healthy, present=(tool_dir / name).exists())
    for problem in found:
        sys.stderr.write(Failure(error=f"tools-install: {name}: {problem}").model_dump_json() + "\n")
    current = isinstance(receipt, ToolReceipt) and receipt.tree == tree and isinstance(healthy, Healthy) and not found
    action = ToolAction.unchanged
    if not current:
        # An unsuccessful reinstall must not leave a receipt claiming the old copy is healthy.
        path.unlink(missing_ok=True)
        # --force: a console script left behind by a deleted tool folder has no uv receipt, so without it uv
        # refuses to overwrite the script (uv 0.13.7 crates/uv-tool-commands/src/common.rs:871-899).
        subprocess.run(
            ["uv", "tool", "install", "--reinstall", "--force", f"./{source}"],
            cwd=top,
            capture_output=True,
            check=True,
            text=True,
        )
        healthy = health(tool_dir / name, bin_dir)
        if isinstance(healthy, str):
            msg = f"tools-install: uv installed {name} but {healthy}"
            raise ValueError(msg)
        write_receipt(path, ToolReceipt(name=name, tree=tree, record_sha256=healthy.record_sha256))
        action = ToolAction.installed
    return ToolInstalled(tool=name, tree=tree, action=action, bin=str(bin_dir / name))


def run() -> None:
    top = Path(git("rev-parse", "--show-toplevel").strip())
    for source in TOOLS.values():
        if git("status", "--porcelain", "--", source):
            msg = f"tools-install: {source} has uncommitted changes; the installed copy must match a commit"
            raise ValueError(msg)
    tool_dir = Path(subprocess.run(["uv", "tool", "dir"], capture_output=True, check=True, text=True).stdout.strip())
    bin_dir = Path(
        subprocess.run(["uv", "tool", "dir", "--bin"], capture_output=True, check=True, text=True).stdout.strip()
    ).absolute()
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    for name in TOOLS:
        sys.stdout.write(install(name, top, tool_dir, bin_dir, state).model_dump_json() + "\n")
