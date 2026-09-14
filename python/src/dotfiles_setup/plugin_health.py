# Copyright (c) 2026 Raymond Manaloto
"""Plugin/skill setup health: are declared plugins actually installed and enabled?

The check verifies that plugins declared as enabled in ``.claude/settings.json``
are actually present and not explicitly disabled, resolved through
``claude plugin list --json``.

.. note::
    This check reports OBSERVABLE FACTS, not inferred states:
    - declared_not_installed: in settings but no CLI row exists
    - declared_disabled_here: in settings, project-scoped row exists with enabled=false
    - installed_not_declared: project-scoped row enabled=true but not in settings

    It does NOT report an id when it has no project-scoped row but exists in
    other scopes (user, other projects). That state is uninterpretable and
    silence is correct.
"""

from __future__ import annotations

import enum
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.codec import Format, encode

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

#: Timeout for the `claude plugin list` subprocess (seconds).
PLUGIN_LIST_TIMEOUT = 10

#: Timeout for the e2e session check (seconds).
E2E_SESSION_TIMEOUT = 30


class PluginHealthCode(enum.IntEnum):
    """Exit code and report classification for plugin health check."""

    OK = 0
    DRIFT = 1  # observed facts contradict expectations
    CLI_UNAVAILABLE = 2  # `claude` not found / not executable
    CLI_FAILED = 3  # ran, non-zero rc
    MALFORMED_PAYLOAD = 4  # rc 0, undecodable or not a JSON array
    BASELINE_INVALID = 5  # settings.json unreadable / ill-typed
    E2E_TIMEOUT = 6  # cross-session check hung
    E2E_VALIDATE_FAILED = 7  # `claude plugin validate` rc != 0
    E2E_SESSION_FAILED = 8  # fresh session check rc != 0


@dataclass(frozen=True, kw_only=True)
class PluginRow:
    """One row from `claude plugin list --json`.

    All fields except id are Optional because the actual payload has 8 distinct
    key sets. Unknown keys are tolerated (the CLI may add more).
    """

    id: str
    version: str | None = None
    scope: str | None = None
    enabled: bool | None = None
    install_path: str | None = None
    project_path: str | None = None


@dataclass(kw_only=True)
class PluginHealthReport:
    """The result of the plugin health check: observable facts only."""

    code: int  # PluginHealthCode member
    declared_not_installed: list[str] = field(default_factory=list)
    declared_disabled_here: list[str] = field(default_factory=list)
    installed_not_declared: list[str] = field(default_factory=list)
    cli_failed_diagnostic: str | None = None


#: Cap on any diagnostic string copied into the report. Child stderr and msgspec
#: error text are both unbounded and can carry absolute paths, so they are
#: truncated before they reach a report that is rendered into SessionStart
#: context (which is transcript-persisted).
_DIAGNOSTIC_MAX_CHARS = 500


def _truncate(text: str) -> str:
    """A bounded, single-line diagnostic. Never branched on — display only."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= _DIAGNOSTIC_MAX_CHARS:
        return collapsed
    return collapsed[: _DIAGNOSTIC_MAX_CHARS - 1] + "…"


def _as_str(value: object) -> str | None:
    """A wire value narrowed to `str`, or None. Never coerces a non-string."""
    return value if isinstance(value, str) else None


def _as_bool(value: object) -> bool | None:
    """A wire value narrowed to `bool`, or None. A non-bool is NOT coerced."""
    return value if isinstance(value, bool) else None


def _row_from_wire(entry: dict[str, object]) -> PluginRow:
    """One decoded row, tolerating every one of the payload's 8 key shapes.

    Unknown keys (`mcpServers`, `notes`, `noteDetails`) are ignored rather than
    rejected: the CLI adds fields on its own schedule and a strict model would
    turn a harmless addition into MALFORMED_PAYLOAD.
    """
    return PluginRow(
        id=_as_str(entry.get("id")) or "",
        version=_as_str(entry.get("version")),
        scope=_as_str(entry.get("scope")),
        enabled=_as_bool(entry.get("enabled")),
        install_path=_as_str(entry.get("installPath")),
        project_path=_as_str(entry.get("projectPath")),
    )


def _run_plugin_list(
    ambient_path: str | None, timeout: int
) -> tuple[PluginHealthCode, str, str]:
    """Spawn the CLI. Returns (code, stdout, diagnostic); code OK means usable.

    Split out of :func:`read_rows` so each function has one job — spawning, and
    parsing — rather than seven exits in one body.
    """
    env = os.environ.copy()
    if ambient_path:
        env["PATH"] = ambient_path

    try:
        result = subprocess.run(
            ["claude", "plugin", "list", "--json"],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return PluginHealthCode.CLI_UNAVAILABLE, "", "`claude` is not on PATH"
    except subprocess.TimeoutExpired:
        return (
            PluginHealthCode.E2E_TIMEOUT,
            "",
            "timed out waiting for `claude plugin list`",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return PluginHealthCode.CLI_UNAVAILABLE, "", _truncate(str(exc))

    if result.returncode != 0:
        # The rc IS the contract. stderr is carried for display only and is
        # never branched on.
        return PluginHealthCode.CLI_FAILED, "", _truncate(result.stderr)
    return PluginHealthCode.OK, result.stdout, ""


def read_rows(
    ambient_path: str | None = None,
    timeout: int = PLUGIN_LIST_TIMEOUT,
) -> tuple[PluginHealthCode, list[PluginRow], str]:
    """Run `claude plugin list --json` and decode it into rows.

    Returns ``(code, rows, diagnostic)``. ``rows`` is empty unless ``code`` is
    OK; ``diagnostic`` is display-only text, never a branch input.
    """
    code, stdout, diagnostic = _run_plugin_list(ambient_path, timeout)
    if code is not PluginHealthCode.OK:
        return code, [], diagnostic

    # The payload is an UNTYPED external document, so it is read with stdlib
    # json like every other external file here (`doctor.load_json`); `codec` is
    # for OUR models, and a `dict[str, object]` target has no registered
    # conversion (measured: UnsupportedTypeError on `object`).
    #
    # One decode of the whole document. An earlier revision did `json.loads`
    # and THEN handed each resulting dict to `codec.decode`, which takes bytes
    # — so every row raised and a healthy payload read as malformed (measured:
    # rc=4 against a payload that parses cleanly to 271 rows). The cause is now
    # reported rather than swallowed; a silent MALFORMED_PAYLOAD is
    # indistinguishable from a parser bug, and that is exactly how the original
    # defect got misread as a broken environment.
    try:
        raw = json.loads(stdout)
    except ValueError as exc:
        return PluginHealthCode.MALFORMED_PAYLOAD, [], _truncate(str(exc))

    if not isinstance(raw, list):
        return (
            PluginHealthCode.MALFORMED_PAYLOAD,
            [],
            f"expected a JSON array, got {type(raw).__name__}",
        )

    rows = [_row_from_wire(entry) for entry in raw if isinstance(entry, dict)]
    return PluginHealthCode.OK, rows, ""


def evaluate(
    declared: list[str],
    rows: list[PluginRow],
    project_root: Path | None = None,
) -> PluginHealthReport:
    """Reconcile declared plugins against observable CLI facts.

    Reports three observable findings (all can be empty):
    - declared_not_installed: in DECLARED, no CLI row exists
    - declared_disabled_here: in DECLARED, project-root row exists with enabled=false
    - installed_not_declared: project-root row enabled=true but not in DECLARED

    Args:
        declared: enabled plugin ids from enabled_plugin_ids()
        rows: decoded PluginRow list from read_rows()
        project_root: the project root path (for matching the wire's projectPath)

    Returns:
        Report with code DRIFT if any list is non-empty, OK otherwise.
    """
    declared_set = set(declared)
    project_root_str = str(project_root.resolve()) if project_root else None

    # INSTALLED = set of all ids that appear in any row
    installed = {row.id for row in rows}

    # Build maps by id for quick lookup
    rows_by_id: dict[str, list[PluginRow]] = {}
    for row in rows:
        if row.id not in rows_by_id:
            rows_by_id[row.id] = []
        rows_by_id[row.id].append(row)

    # Three observable findings:
    declared_not_installed = sorted(declared_set - installed)

    declared_disabled_here: list[str] = []
    for plugin_id in declared:
        for row in rows_by_id.get(plugin_id, []):
            if row.project_path == project_root_str and row.enabled is False:
                declared_disabled_here.append(plugin_id)
                break
    declared_disabled_here.sort()

    installed_not_declared = sorted(
        {
            row.id
            for row in rows
            if row.project_path == project_root_str
            and row.enabled is True
            and row.id not in declared_set
        }
    )

    # DRIFT if any finding is non-empty
    has_drift = (
        bool(declared_not_installed)
        or bool(declared_disabled_here)
        or bool(installed_not_declared)
    )

    return PluginHealthReport(
        code=PluginHealthCode.DRIFT if has_drift else PluginHealthCode.OK,
        declared_not_installed=declared_not_installed,
        declared_disabled_here=declared_disabled_here,
        installed_not_declared=installed_not_declared,
    )


def check_plugin_health(setup: object, declared: list[str]) -> list[str]:
    """Doctor LIVE check: reconcile declared plugins against actual CLI facts.

    Registered in ``LIVE_CHECKS``, not ``CHECKS``, because it spawns
    ``claude plugin list`` — the same reason ``mcp-health`` lives there.

    An earlier revision returned ``[]`` unconditionally with a comment saying
    the real work happened elsewhere. That is a check that can only pass, sitting
    in a registry that reads as coverage: precisely what
    ``.claude/rules/probes-need-a-control-arm.md`` exists to stop. It now runs
    the real reconciliation and renders findings as lines, naming plugin ids only
    and never a filesystem path.
    """
    project_root = getattr(setup, "repo_root", None)
    code, rows, diagnostic = read_rows()
    if code is PluginHealthCode.CLI_UNAVAILABLE:
        return [
            "plugin-health: `claude` is not executable here, so nothing was checked"
        ]
    if code is PluginHealthCode.CLI_FAILED:
        return [f"plugin-health: `claude plugin list --json` failed: {diagnostic}"]
    if code is PluginHealthCode.MALFORMED_PAYLOAD:
        return [f"plugin-health: could not decode the plugin list: {diagnostic}"]
    if code is not PluginHealthCode.OK:
        return [f"plugin-health: unexpected state {code.name}"]

    report = evaluate(declared, rows, project_root)
    findings: list[str] = []
    if report.declared_not_installed:
        findings.append(
            "plugin-health: declared enabled but NOT INSTALLED: "
            + ", ".join(report.declared_not_installed)
        )
    if report.declared_disabled_here:
        findings.append(
            "plugin-health: settings enable these but this project's row says "
            "disabled: " + ", ".join(report.declared_disabled_here)
        )
    if report.installed_not_declared:
        findings.append(
            "plugin-health: enabled for this project but NOT declared in settings "
            "(entered outside a reviewed diff): "
            + ", ".join(report.installed_not_declared)
        )
    return findings


def _declared_from_settings(*sources: Mapping[str, object]) -> list[str]:
    """Enabled plugin ids, user-then-project, later sources winning.

    This deliberately MIRRORS ``doctor.enabled_plugin_ids`` rather than calling
    it: ``doctor`` imports this module for its LIVE_CHECKS adapter, so importing
    ``doctor`` back would be circular, and a deferred import inside the function
    trips PLC0415 (which this repo cannot silence — inline suppressions are
    banned outright).

    The duplication is held safe by a PARITY TEST asserting the two agree on the
    same fixtures, which is the pattern this repo already uses for cross-module
    invariants. If they ever diverge, that test fails rather than one caller
    silently reporting a different set than the other.
    """
    enabled: dict[str, bool] = {}
    for source in sources:
        raw = source.get("enabledPlugins")
        if isinstance(raw, dict):
            enabled.update(
                {
                    k: v
                    for k, v in raw.items()
                    if isinstance(k, str) and isinstance(v, bool)
                }
            )
    return sorted(name for name, on in enabled.items() if on)


def plugin_health_main(*, project_root: Path | None = None) -> int:
    """Main entry point: check plugin health and print JSON report.

    Mirrors claude_doctor_main: prints report as JSON on stdout, returns
    the PluginHealthCode as the process exit code.
    """
    if project_root is None:
        project_root = Path.cwd()

    # Read declared plugins
    settings_path = project_root / ".claude" / "settings.json"
    user_settings: dict[str, object] = {}
    user_path = Path.home() / ".claude" / "settings.json"
    try:
        if user_path.is_file():
            user_settings = json.loads(user_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        # A broken USER settings file is not fatal: the project file still
        # carries the declarations this check is about.
        logger.debug("plugin_health: could not read user settings: %s", e)

    try:
        settings = json.loads(settings_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        logger.debug("plugin_health: could not read settings: %s", e)
        report = PluginHealthReport(code=PluginHealthCode.BASELINE_INVALID)
        report_bytes = encode(report, fmt=Format.JSON)
        sys.stdout.buffer.write(report_bytes)
        sys.stdout.buffer.write(b"\n")
        return PluginHealthCode.BASELINE_INVALID

    declared = _declared_from_settings(user_settings, settings)

    # Query actual plugins
    ambient_path = os.environ.get("DOTFILES_AMBIENT_PATH")
    code, rows, diagnostic = read_rows(ambient_path=ambient_path)

    if code != PluginHealthCode.OK:
        report = PluginHealthReport(
            code=code,
            cli_failed_diagnostic=diagnostic or None,
        )
        report_bytes = encode(report, fmt=Format.JSON)
        sys.stdout.buffer.write(report_bytes)
        sys.stdout.buffer.write(b"\n")
        return code

    # Reconcile
    report = evaluate(declared, rows, project_root)

    report_bytes = encode(report, fmt=Format.JSON)
    sys.stdout.buffer.write(report_bytes)
    sys.stdout.buffer.write(b"\n")

    return report.code


def plugin_health_e2e_main(*, project_root: Path | None = None) -> int:
    """Cross-session e2e check: launch a fresh claude process against this project.

    Tests that a fresh session against this project starts cleanly.
    Runs `claude -p "test" -q` with a timeout and reports rc.
    """
    if project_root is None:
        project_root = Path.cwd()

    env = os.environ.copy()
    # Do NOT export CLAUDE_CODE_OAUTH_TOKEN — it would override /login
    env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)

    try:
        result = subprocess.run(
            ["claude", "-p", "healthy", "-q"],
            env=env,
            capture_output=True,
            timeout=E2E_SESSION_TIMEOUT,
            cwd=str(project_root),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return PluginHealthCode.E2E_TIMEOUT
    except FileNotFoundError:
        return PluginHealthCode.CLI_UNAVAILABLE
    except OSError, subprocess.SubprocessError:
        return PluginHealthCode.E2E_SESSION_FAILED

    if result.returncode != 0:
        return PluginHealthCode.E2E_SESSION_FAILED

    return PluginHealthCode.OK
