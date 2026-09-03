# Copyright (c) 2026 Raymond Manaloto
"""InstructionsLoaded hook: append one JSONL record per instruction-file load.

Every `.claude/rules/*.md` and tracked `CLAUDE.md`/`AGENTS.md` load fires this
hook — at session start and on every lazy (scoped) load, in the main thread
AND inside every subagent (#917). The static gate
(`.claude/rules/md-size-budgets.md`) can only see whether a rule's `paths:`
glob matches a FILE on disk; it structurally cannot see whether the rule ever
FIRED in a real session. This module is the observation channel that closes
that gap — `instructions_report.py` turns the records this writes into the
never-fired report.

**HOT PATH — STDLIB IMPORTS ONLY, at module scope and below.** This hook
fires on every one of the ~37 eligible instruction files per session start,
and again per subagent. Measured (spec #917 C1): `uv run --project python
python -c "import json,sys,os,pathlib"` = 0.04s; the same interpreter
importing `dotfiles_setup.main` = 0.23-0.27s — a ~6x-per-file tax the eager
corpus already pays too much of. `tests/test_instructions_observer.py`
asserts this module's transitive imports never cross into `dotfiles_setup`
or any third-party package, so the cost cannot regress silently. The
`instructions-report` CLI side (`instructions_report.py`) has no such
constraint — it runs on demand, not on the hot path.

**Fail open, always** (C2). The `InstructionsLoaded` event has no decision
control and Claude Code ignores its exit code, so a crash here cannot block
loading — but it also must never write to stdout/stderr, which would surface
as hook noise in every session. Any exception, malformed stdin, unwritable
target directory, or missing field is swallowed; `observe_main` always
returns 0. A best-effort line is appended to a sibling `errors.log` so a
systemic failure is not silently lost forever (still wrapped in its own
try/except — the error path cannot itself become a new way to fail loudly).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

# A private, silent logger — NOT the package logger. `propagate = False` and a
# lone `NullHandler` guarantee `logger.exception(...)` below never reaches
# stdout/stderr even if some other import configures root logging later; it
# exists purely so the fail-open catch-all can carry `exc_info` (the pattern
# `ruff`'s BLE001 rule requires to recognize a deliberately-blind except as
# handled, C2) without adding hook noise.
_LOGGER = logging.getLogger(f"{__name__}.silent")
_LOGGER.addHandler(logging.NullHandler())
_LOGGER.propagate = False

#: Directory (repo-relative) records land in. `.agent/` is git-ignored by a
#: blanket rule (`.gitignore`), so this subdirectory needs no new entry.
_RECORDS_DIRNAME = ".agent/instructions-loaded"
_ERROR_LOG_NAME = "errors.log"

#: C3 — session_id reaches a filename. Conservative charset only; anything
#: else (`/`, `..`, NUL, an absolute prefix) is stripped rather than escaped,
#: so there is no path-traversal shape left to reason about.
_SESSION_ID_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"
)
_SESSION_ID_FALLBACK = "unknown"
_MAX_SESSION_ID_LEN = 128

#: C4 — a realistic record is ~1-3KB (the three path fields are bounded by
#: PATH_MAX; the longest `paths:` frontmatter block measured in the corpus is
#: 117 bytes). This cap is a hard backstop, not a tuned budget: a record over
#: it is DROPPED rather than truncated or split, because a truncated write is
#: exactly the corrupt-JSONL-line failure C4 exists to prevent.
_MAX_RECORD_BYTES = 8192

#: Payload keys copied through verbatim as strings (or None if absent/wrong
#: type). C5 — paths and reasons only; `cwd` and `transcript_path` are
#: deliberately excluded (the latter leaks a user-home path for no analytical
#: gain).
_STRING_FIELDS: tuple[str, ...] = (
    "session_id",
    "memory_type",
    "load_reason",
    "agent_id",
    "agent_type",
)
_PATH_FIELDS: tuple[str, ...] = ("file_path", "trigger_file_path", "parent_file_path")


def _project_root() -> Path:
    """Resolve the project root from ``$CLAUDE_PROJECT_DIR`` — never ``cwd``.

    C1b / #343 class: hooks run in the session's CURRENT directory, not the
    project root, so a relative records path resolved against ``Path.cwd()``
    would silently land in whatever sibling repo the session happens to be
    working in. Fall back to this module's own repo root (resolved from
    ``__file__``) only when the env var is unset or not a real directory —
    never to ``Path.cwd()``.
    """
    env_root = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_root:
        candidate = Path(env_root)
        if candidate.is_dir():
            return candidate
    # python/src/dotfiles_setup/instructions_observer.py -> repo root.
    return Path(__file__).resolve().parent.parent.parent.parent


def usable_session_id(value: object) -> str | None:
    r"""Return the sanitized, usable form of ``session_id``, or ``None``.

    U1 — the single shared definition of "usable session id", used by both
    `session_filename` (this module, hot path) and `instructions_report`'s
    session counting. Filters to the conservative `_SESSION_ID_CHARS`
    charset, caps the length, and treats a value that reduces to nothing
    survivable — missing, ``None``, a non-string, empty, whitespace-only, or
    pure path-traversal characters — as unusable (``None``), rather than as
    a distinct real session. Before this predicate was shared, the report
    counted `""`, `" "`, `"\\t"` as three distinct real sessions even though
    the observer had already collapsed all of them into one `unknown.jsonl`
    file — the report and the write path disagreed on the same fact.
    """
    if not isinstance(value, str):
        return None
    cleaned = "".join(ch for ch in value if ch in _SESSION_ID_CHARS)
    cleaned = cleaned[:_MAX_SESSION_ID_LEN]
    return cleaned or None


def session_filename(session_id: object) -> str:
    """Sanitize ``session_id`` into a safe ``<id>.jsonl`` filename (C3).

    Reduces to a conservative charset, caps the length, and falls back to a
    fixed name when the input is missing, ``None``, a non-string, or reduces
    to nothing survivable (e.g. it was pure path-traversal characters) — per
    `usable_session_id`.
    """
    cleaned = usable_session_id(session_id) or _SESSION_ID_FALLBACK
    return f"{cleaned}.jsonl"


def _normalize_path(value: object, project_root: Path) -> str | None:
    """Repo-relative when under ``project_root``; absolute otherwise (C5).

    R7: normalizes LEXICALLY (``os.path.normpath``), never via
    ``Path.resolve()``. ``resolve()`` follows a symlink out of the repo —
    e.g. a nested ``.claude/rules/`` tree shared in via a symlink, a
    documented pattern — so a file that genuinely loaded from inside the
    repo would resolve to an absolute path elsewhere on disk and could
    never compare equal to ``scoped_rules_on_disk``'s unresolved
    repo-relative listing. Lexical normalization also drops the two
    filesystem stats ``resolve()`` costs per path, on a hot path that pays
    for every one of the ~37 eligible files per session (C1).
    """
    if not isinstance(value, str) or not value:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        return value
    normalized = os.path.normpath(str(candidate))
    root = os.path.normpath(str(project_root))
    try:
        return str(Path(normalized).relative_to(root))
    except ValueError:
        return value


def _string_or_none(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def _globs_or_none(payload: dict) -> list[str] | None:
    """``globs`` is present ONLY for ``path_glob_match`` loads; tolerate its absence."""
    value = payload.get("globs")
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return None


def build_record(payload: dict, *, project_root: Path, now: str) -> dict:
    """Build the one JSONL-record dict for a single ``InstructionsLoaded`` payload.

    Args:
        payload: The parsed hook JSON from stdin.
        project_root: Resolved via :func:`_project_root` (never ``cwd``).
        now: An ISO-8601 UTC timestamp, injected so this stays pure/testable.
    """
    record: dict[str, object] = {"ts": now}
    for key in _STRING_FIELDS:
        record[key] = _string_or_none(payload, key)
    for key in _PATH_FIELDS:
        record[key] = _normalize_path(payload.get(key), project_root)
    record["globs"] = _globs_or_none(payload)
    return record


def _log_error(project_root: Path, message: str) -> None:
    """Best-effort append to the sibling error log — itself wrapped (C2).

    R4: the error channel must not share a fate with what it reports on.
    Try the primary sibling log first — colocated with the records for the
    common case — and on ANY failure there (read-only tree, full disk,
    permission denied — the exact conditions this function exists to
    survive) fall back to the OS temp dir, which does not depend on
    ``project_root`` being writable at all. Both attempts are best-effort;
    a failure of the fallback too is swallowed exactly like every other
    path on this hot path (C2) — there is nowhere left to report it.
    """
    line = f"{datetime.now(UTC).isoformat()} {message}\n"
    try:
        directory = project_root / _RECORDS_DIRNAME
        directory.mkdir(parents=True, exist_ok=True)
        with Path(directory / _ERROR_LOG_NAME).open("a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError:
        pass
    else:
        return
    # S6: the fallback matches the primary writer's own hygiene — 0600 (the
    # records file's mode) via os.open's mode argument, and O_NOFOLLOW so a
    # symlink planted at this well-known path in a shared temp dir is
    # refused rather than followed.
    try:
        fallback = (
            Path(tempfile.gettempdir()) / "dotfiles-instructions-observer-errors.log"
        )
        fd = os.open(
            fallback, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600
        )
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)
    except OSError:
        pass


def _write_record(record: dict, session_id: object, project_root: Path) -> None:
    """Encode once, then issue ONE unbuffered ``os.write`` (C4).

    O_APPEND atomicity is per-``write(2)`` syscall, not per Python-level
    ``write()`` — a buffered text handle can flush a long record across
    several syscalls and let two concurrent subagent writers interleave into
    a corrupt JSONL line. Opens with ``O_WRONLY|O_CREAT|O_APPEND`` and issues
    exactly one ``os.write`` on that descriptor; no lock file (that
    reintroduces cost and a failure mode on the hot path).

    Every path that DROPS a record — containment miss, oversize, a short
    write — logs why (R4); none returns silently.
    """
    directory = (project_root / _RECORDS_DIRNAME).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = (directory / session_filename(session_id)).resolve()
    if not target.is_relative_to(directory):
        # Cannot happen given the C3 sanitizer, but the containment check is
        # asserted rather than trusted — see probes-need-a-control-arm.md.
        _log_error(project_root, f"write_record: containment check failed for {target}")
        return
    blob = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
    if len(blob) > _MAX_RECORD_BYTES:
        _log_error(
            project_root,
            f"write_record: record of {len(blob)} bytes exceeds "
            f"_MAX_RECORD_BYTES={_MAX_RECORD_BYTES}; dropped",
        )
        return
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        written = os.write(fd, blob)
        if written != len(blob):
            # R10: checked, not looped. A second os.write() on the same
            # descriptor is no longer atomic against a concurrent writer —
            # it could interleave with another subagent's record, which is
            # the exact corruption C4 exists to prevent. A short write here
            # is logged and the partial line is left as-is rather than risk
            # that.
            _log_error(
                project_root,
                f"write_record: short os.write ({written}/{len(blob)} bytes)",
            )
    finally:
        os.close(fd)


def observe_main(argv: list[str] | None = None) -> int:
    """Read the hook payload from stdin, append one record. ALWAYS returns 0 (C2).

    Args:
        argv: Unused — the hook invokes this module directly with no
            arguments (``python -m dotfiles_setup.instructions_observer``);
            the parameter exists to match the CLI-entrypoint shape used
            elsewhere in this package.
    """
    del argv
    project_root = _project_root()
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return 0
        now = datetime.now(UTC).isoformat()
        record = build_record(payload, project_root=project_root, now=now)
        _write_record(record, payload.get("session_id"), project_root)
    except Exception as exc:
        _LOGGER.exception("instructions_observer: fail-open on hot path")
        # S6: `_log_error` already wraps both of its own attempts in
        # try/except OSError, but this outer wrap is the last one — nothing
        # catches for it. C2's rule ("the error path cannot itself become a
        # new way to fail loudly") has to hold even for a hypothetical
        # non-OSError raised inside `_log_error` itself.
        try:
            _log_error(project_root, f"{type(exc).__name__}: {exc}")
        except Exception:
            _LOGGER.exception("instructions_observer: _log_error itself failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(observe_main())
