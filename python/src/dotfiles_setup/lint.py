# Copyright (c) 2026 Raymond Manaloto
"""Run the hk lint gate under a hard timeout so a hung lint self-aborts.

The gate is `hk run check --all` — the **read-only** hook, identical to what
CI runs (`ci.yml`), so `mise run lint` and CI check the same thing. It does
NOT auto-fix: a violation fails loud with `rc=1` instead of being silently
rewritten (the fix path is `mise run fmt` → `hk fix`). `check`, `pre-commit`,
and `fix` share the same `...allSteps` in `hk.pkl`, so coverage is identical.

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

The default log path is scoped per workspace *and* per process (#895): two
concurrent runs — two clones on this host, or two windows on one clone —
each get their own `hk-lint-<workspace hash>-<pid>.log`, and a stable
`hk-lint-<workspace hash>.log` symlink (repointed via a single atomic
`os.replace`, never an explicit unlink-then-relink) always names the most
recent run for that workspace, for `long-running-command-hangs.md` rule 2 to
read by a predictable name. This is safe **in-container** for a different
reason than on the Mac host: `HOME` there is the per-workspace home volume
(see `devcontainer_names.py`), so `workspace_hash` — which hashes the
*container* workspace path, identical across clones — is not what
discriminates; the already-scoped `HOME` is. A future change sharing one
home volume across clones would silently reopen the collision this scoping
closes on the host. The pre-#895 single fixed path is best-effort deleted
once it is seen, so it cannot linger as a frozen decoy at the name older
docs and memory still remember.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import time
from pathlib import Path

from dotfiles_setup.devcontainer_names import workspace_hash

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 600
TIMEOUT_ENV_VAR = "DOTFILES_LINT_TIMEOUT"
TIMEOUT_EXIT_CODE = 124  # GNU coreutils `timeout` convention
KILL_GRACE_SECONDS = 10
LOG_TAIL_LINES = 40
# Read-only gate (no --stash: check never fixes, so it has nothing to stash).
# Matches CI's `hk run check --all` so local == CI. Fix path is `mise run fmt`.
HK_COMMAND = ("hk", "run", "check", "--all")
LOG_DIR = Path.home() / ".local" / "state" / "dotfiles"
# An age floor of hours, not seconds: `mise run lint` bounds at 700s
# (mise.toml [tasks.lint]), but a direct `dotfiles-setup lint` is bounded
# only by the in-process 600s default, raisable without limit via
# `--timeout`/`DOTFILES_LINT_TIMEOUT` — so this floor must clear any
# plausible run, not just the 700s mise ceiling.
_PRUNE_MAX_AGE_SECONDS = 24 * 60 * 60


def _default_project_root() -> Path:
    """The repo root, by the same convention `main.py` uses for `project_root`.

    Only a fallback for a caller that doesn't thread its own `project_root`
    through (`main.py`'s CLI entry point always does).
    """
    return Path(__file__).resolve().parent.parent.parent.parent


def _per_run_log_path(project_root: Path) -> Path:
    """This run's dedicated log path: `hk-lint-<workspace hash>-<pid>.log`."""
    return LOG_DIR / f"hk-lint-{workspace_hash(project_root)}-{os.getpid()}.log"


def _stable_log_path(project_root: Path) -> Path:
    """The predictable per-workspace symlink `rule 2` reads by name."""
    return LOG_DIR / f"hk-lint-{workspace_hash(project_root)}.log"


def _update_stable_symlink(project_root: Path, per_run_log: Path) -> None:
    """Atomically repoint the stable symlink at `per_run_log`.

    A single `os.replace(tmp, stable)` both creates the link on first run and
    repoints it on every later one — it replaces a regular file, repoints an
    existing symlink, and never follows (so never clobbers) the old target.
    There is deliberately no separate "migrate a pre-existing regular file"
    branch: `Path.exists()` follows symlinks (so a dangling stable link would
    misreport `False`), and any check-then-unlink is its own TOCTOU — `replace`
    alone closes both. Never fails the run: caught broadly, since a directory
    at the stable path, a read-only state dir, or a filesystem without symlink
    support each raise a different `OSError` subtype.
    """
    stable = _stable_log_path(project_root)
    tmp = stable.with_name(f"{stable.name}.tmp-{os.getpid()}")
    try:
        tmp.unlink(missing_ok=True)  # a run that died mid-replace leaves one
        tmp.symlink_to(per_run_log)
        tmp.replace(stable)
    except OSError:
        logger.warning("Could not update stable lint-log symlink %s", stable)


def _prune_stale(
    candidates: list[Path], current_log: Path, *, skip_symlinks: bool
) -> None:
    """Delete entries in `candidates` older than the prune floor.

    `current_log` (this run's own file) is always spared. `skip_symlinks`
    is `True` for the per-run glob — the stable symlink can be reached
    through a name collision path even though this glob is not supposed to
    match it (see `_prune_old_logs`) — and `False` for the tmp-link glob,
    whose entries are ALWAYS symlinks and are exactly what that sweep exists
    to remove.
    """
    now = time.time()
    for candidate in candidates:
        if candidate == current_log:
            continue
        if skip_symlinks and candidate.is_symlink():
            continue
        try:
            age = now - candidate.lstat().st_mtime
            if age < _PRUNE_MAX_AGE_SECONDS:
                continue
            candidate.unlink()
        except OSError:
            logger.warning("Could not prune stale lint log %s", candidate)


def _prune_old_logs(project_root: Path, current_log: Path) -> None:
    """Delete this workspace's stale per-run logs and orphaned tmp links.

    Scoped to `hk-lint-<this workspace hash>-*.log` — `hk-lint-<hash>` (no
    trailing `-`) is the COMMON prefix with the stable symlink's name
    (`hk-lint-<hash>.log`), but that glob does not match the symlink itself
    (it has no `-<pid>` before `.log`); a broader glob would both sweep other
    workspaces' files and reach the symlink. Ages entries with `lstat` (never
    through a symlink) so a repointed link's mtime is never mistaken for a
    stale run's. Also sweeps `hk-lint-<hash>.log.tmp-<pid>` — a run killed
    between `symlink_to` and `replace` in `_update_stable_symlink` leaves one
    of these behind, and only a later run reusing the SAME pid would ever
    clear it otherwise.
    """
    hash_ = workspace_hash(project_root)
    try:
        per_run = list(LOG_DIR.glob(f"hk-lint-{hash_}-*.log"))
        tmp_links = list(LOG_DIR.glob(f"hk-lint-{hash_}.log.tmp-*"))
    except OSError:
        logger.warning("Could not scan %s for stale lint logs", LOG_DIR)
        return
    _prune_stale(per_run, current_log, skip_symlinks=True)
    _prune_stale(tmp_links, current_log, skip_symlinks=False)


def _remove_legacy_log_file() -> None:
    """Best-effort delete of the pre-#895 single fixed log path.

    A workspace/pid-scoped file that no longer exists fails LOUD at the
    remembered name — good, that is discoverable. A pre-#895 run instead
    left a regular file at the bare `hk-lint.log` name, which `_prune_old_logs`
    can never reach (its glob requires `-<pid>.log`), so without this it lies
    SILENTLY: a plausible, substantial, permanently-frozen body sits at
    exactly the name every persisted doc, receipt, and memory entry in this
    repo still tells an agent to read.
    """
    legacy = LOG_DIR / "hk-lint.log"
    try:
        if legacy.is_file() and not legacy.is_symlink():
            legacy.unlink()
    except OSError:
        logger.warning("Could not remove legacy lint log %s", legacy)


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
    log_file: Path | None = None,
    project_root: Path | None = None,
) -> int:
    """Run `command` under `timeout` seconds; kill the group on expiry.

    Returns the command's exit code, or `TIMEOUT_EXIT_CODE` on timeout.
    Points `HK_LOG_FILE` at a dedicated per-run file (truncated up front)
    so the on-timeout tail reflects only this run.

    An explicitly-passed `log_file` is used **verbatim** — no derivation, no
    stable symlink, no pruning — so a caller-supplied path behaves exactly as
    before. Only the default (`log_file=None`) case derives a per-workspace,
    per-process path under `LOG_DIR` and maintains the `hk-lint-<hash>.log`
    stable symlink; that derivation hashes `project_root` (defaulting to this
    repo's root) rather than the current working directory, so it agrees
    whether invoked as `mise run lint` (always run from the repo root) or as
    `uv run --project python dotfiles-setup lint` from `python/`.
    """
    resolved_root: Path | None = None
    if log_file is None:
        if project_root is None:
            project_root = _default_project_root()
        resolved_root = project_root
        log_file = _per_run_log_path(resolved_root)

    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("")  # truncate so the tail is this run only
    if resolved_root is not None:
        _remove_legacy_log_file()
        _update_stable_symlink(resolved_root, log_file)
        _prune_old_logs(resolved_root, log_file)
    env = {
        **os.environ,
        "HK_LOG_FILE": str(log_file),
        "HK_LOG_FILE_LEVEL": "debug",
    }
    logger.info(
        "Running %s (timeout %ds); log %s", " ".join(command), timeout, log_file
    )
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
