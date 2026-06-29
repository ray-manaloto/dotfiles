"""Run hk pre-commit under a hard timeout so a hung lint self-aborts.

hk has **no native timeout** — verified against hk 1.46 (installed) and
the live v1.48 docs: `hk run` exposes only `--jobs`/`--fail-fast`,
`configuration.md` has no `timeout` step key, and the full `HK_*` env-var
list has none either. A step that blocks (network, stdin, a stuck
`docker_bake_check` waiting on Docker) would otherwise wedge the whole
run indefinitely; one such hang idled at 0% CPU for ~7h in session
2026-06-29 before it was noticed and killed.

This wraps the hk invocation in an out-of-process timeout. hk and its
children run in a fresh process group (`start_new_session=True`) so the
timeout kills the entire tree, not just the hk parent — the system
`timeout(1)` binary is not portable (absent on stock macOS hosts), so the
kill is done in-process. On expiry the tail of hk's debug log is printed
for diagnosis and the GNU-`timeout` convention exit code 124 is returned.

Default ceiling is 600s, overridable via `--timeout` or the
`DOTFILES_LINT_TIMEOUT` env var. See
`.claude/rules/long-running-command-hangs.md`.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 600
TIMEOUT_ENV_VAR = "DOTFILES_LINT_TIMEOUT"
TIMEOUT_EXIT_CODE = 124  # GNU coreutils `timeout` convention
KILL_GRACE_SECONDS = 10
LOG_TAIL_LINES = 40
HK_COMMAND = ("hk", "run", "pre-commit", "--all", "--stash", "none")
DEFAULT_LOG_FILE = Path.home() / ".local" / "state" / "dotfiles" / "hk-lint.log"


def resolve_timeout(cli_timeout: int | None = None) -> int:
    """Resolve the timeout ceiling: `--timeout` > env var > default.

    Raises:
        ValueError: when the chosen override is not a positive integer.
    """
    if cli_timeout is not None:
        candidate, source = cli_timeout, "--timeout"
    else:
        raw = os.environ.get(TIMEOUT_ENV_VAR)
        if not raw:
            return DEFAULT_TIMEOUT_SECONDS
        try:
            candidate = int(raw)
        except ValueError as exc:
            msg = f"{TIMEOUT_ENV_VAR}={raw!r} is not an integer"
            raise ValueError(msg) from exc
        source = TIMEOUT_ENV_VAR
    if candidate <= 0:
        msg = f"{source} must be a positive number of seconds; got {candidate}"
        raise ValueError(msg)
    return candidate


def _terminate_group(proc: subprocess.Popen[bytes]) -> None:
    """SIGTERM the process group led by `proc`, escalating to SIGKILL."""
    try:
        pgid = os.getpgid(proc.pid)
    except ProcessLookupError:
        return
    os.killpg(pgid, signal.SIGTERM)
    try:
        proc.wait(timeout=KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        os.killpg(pgid, signal.SIGKILL)


def _print_log_tail(log_file: Path) -> None:
    """Log the last `LOG_TAIL_LINES` of `log_file` to aid diagnosis."""
    if not log_file.exists():
        logger.error("hk log %s not found; nothing to tail", log_file)
        return
    lines = log_file.read_text(errors="replace").splitlines()
    tail = lines[-LOG_TAIL_LINES:]
    logger.error("Last %d line(s) of %s:", len(tail), log_file)
    for line in tail:
        logger.error("  %s", line)


def run_guarded(
    timeout: int,
    *,
    command: tuple[str, ...] = HK_COMMAND,
    log_file: Path = DEFAULT_LOG_FILE,
) -> int:
    """Run `command` under `timeout` seconds; kill the group on expiry.

    Returns the command's exit code, or `TIMEOUT_EXIT_CODE` on timeout.
    Points `HK_LOG_FILE` at a dedicated per-run file (truncated up front)
    so the on-timeout tail reflects only this run.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("")  # truncate so the tail is this run only
    env = {
        **os.environ,
        "HK_LOG_FILE": str(log_file),
        "HK_LOG_FILE_LEVEL": "debug",
    }
    logger.info("Running %s (timeout %ds)", " ".join(command), timeout)
    proc = subprocess.Popen(command, start_new_session=True, env=env)
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        return _handle_timeout(proc, timeout, command[0], log_file)


def _handle_timeout(
    proc: subprocess.Popen[bytes],
    timeout: int,
    name: str,
    log_file: Path,
) -> int:
    """Kill a timed-out run's process group and surface the log tail."""
    logger.error(
        "%s exceeded %ds — killing the process group and aborting.", name, timeout
    )
    _terminate_group(proc)
    _print_log_tail(log_file)
    return TIMEOUT_EXIT_CODE
