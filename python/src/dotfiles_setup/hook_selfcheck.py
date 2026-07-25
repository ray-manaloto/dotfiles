"""Host-side hook self-check: exercise the WIRED hook entrypoints end-to-end.

``tests/test_hook_guard.py`` calls :func:`hook_guard.decide` *in process* — it
never drives the actual path the harness uses: ``.claude/settings.json`` ->
``scripts/pretooluse-guard.sh`` (the fail-open wrapper) -> ``dotfiles-setup
hook pretooluse``. This module closes that gap. It:

- asserts ``.claude/settings.json`` wires the project hooks
  (:data:`_SETTINGS_WIRING`): the PreToolUse deny guard (scoped to ``Bash``),
  the SessionStart web-setup bootstrap, and the SessionEnd command-audit
  refresh;
- drives the REAL PreToolUse wrapper end-to-end — a denied command must DENY,
  an allowed one must stay silent;
- ``bash -n`` syntax-checks the wired hook scripts (a parse error in
  ``web-setup.sh`` would brick a cold Claude-web session before the first Bash
  tool call).

``dotfiles-setup hook selfcheck`` runs it, and ``mise run ship`` / ``mise run
land`` gate on it (an always-run core gate, like lint/pytest/verify) so a hook
regression is caught automatically.

Each ``check_*`` helper returns a list of failure strings (empty == pass) so
the checks are unit-testable without capturing stdout;
:func:`hook_selfcheck_main` runs them all, prints a PASS/FAIL line per check,
and returns 0 iff every check passed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

from dotfiles_setup import hook_guard

if TYPE_CHECKING:
    from pathlib import Path

_PROBE_TIMEOUT_S = 60.0

# A representative denied command (has a canonical mise task) and an allowed
# one (a plain diagnostic). Driven through the REAL wrapper end-to-end; the
# full rule battery lives in tests/test_hook_guard.py.
_DENIED_SAMPLE = "gh pr create --fill"
_DENIED_HINT = "mise run ship"
_ALLOWED_SAMPLE = "git status --porcelain"

_PRETOOLUSE_WRAPPER = "scripts/pretooluse-guard.sh"
_WEB_SETUP = "scripts/web-setup.sh"
_HOOK_SCRIPTS = (_PRETOOLUSE_WRAPPER, _WEB_SETUP)

# Each settings.json hook event -> (command substrings that MUST appear in its
# wired command(s), required matcher or None). Keeps the project hooks from
# silently drifting out of .claude/settings.json (the wiring the end-to-end
# check then exercises). PreToolUse must stay scoped to Bash.
#
# SessionEnd runs the command-audit refine loop once per session (the recurring
# half of mise-tasks-only enforcement). A matcher would SCOPE it to particular
# end reasons (clear/logout/resume/...) — it must fire on all of them, hence
# None. Deliberately NOT a `Stop` hook: Stop fires every turn and can block,
# which would put a transcript scan on the per-turn path.
_SESSION_END_REPORT = ".agent/command-audit.md"
_SETTINGS_WIRING: tuple[tuple[str, tuple[str, ...], str | None], ...] = (
    ("PreToolUse", (_PRETOOLUSE_WRAPPER,), "Bash"),
    ("SessionStart", (_WEB_SETUP, "CLAUDE_CODE_REMOTE"), None),
    ("SessionEnd", ("mise run command-audit", _SESSION_END_REPORT), None),
)


def _run(
    cmd: list[str], *, stdin: str | None = None, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
            timeout=_PROBE_TIMEOUT_S,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", "probe timed out")
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, "", str(exc))


def _hook_payload(command: str) -> str:
    """The PreToolUse stdin JSON the harness sends the hook."""
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def _event_entries(settings: dict, event: str) -> list[tuple[str, str]]:
    """(matcher, command) pairs wired for a settings.json hook event."""
    entries: list[tuple[str, str]] = []
    for entry in settings.get("hooks", {}).get(event, []):
        matcher = entry.get("matcher", "")
        matcher = matcher if isinstance(matcher, str) else ""
        entries.extend(
            (matcher, cmd)
            for hook in entry.get("hooks", [])
            if isinstance((cmd := hook.get("command")), str)
        )
    return entries


def check_settings_wiring(settings_path: Path) -> list[str]:
    """Every project hook must be wired to its wrapper (with the right matcher)."""
    failures: list[str] = []
    try:
        settings = json.loads(settings_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not read {settings_path}: {exc}"]
    for event, required, matcher in _SETTINGS_WIRING:
        entries = _event_entries(settings, event)
        if not entries:
            failures.append(f"settings.json has no {event} hook wired")
            continue
        joined = "\n".join(cmd for _, cmd in entries)
        failures.extend(
            f"settings.json {event} hook is missing {token!r}"
            for token in required
            if token not in joined
        )
        if matcher is not None and not any(matcher in m for m, _ in entries):
            failures.append(
                f"settings.json {event} hook must be scoped with matcher "
                f"{matcher!r} (tool events fire on every tool otherwise)"
            )
    return failures


def check_pretooluse_endtoend(project_root: Path) -> list[str]:
    """Drive the REAL PreToolUse wrapper end-to-end (deny + allow).

    A denied command must deny, an allowed one must stay silent. Exercises
    settings.json's wired entrypoint (wrapper -> uv -> ``dotfiles-setup hook
    pretooluse`` -> :func:`hook_guard.decide`), not just ``decide`` alone.
    """
    failures: list[str] = []
    wrapper = str(project_root / _PRETOOLUSE_WRAPPER)

    denied = _run(
        ["bash", wrapper], stdin=_hook_payload(_DENIED_SAMPLE), cwd=project_root
    )
    if denied.returncode != 0:
        failures.append(
            f"pretooluse wrapper exited {denied.returncode} on a denied command "
            f"(must exit 0 and emit the decision as JSON): {denied.stderr.strip()}"
        )
    elif '"permissionDecision": "deny"' not in denied.stdout:
        failures.append(
            f"pretooluse wrapper did not DENY {_DENIED_SAMPLE!r} — the wired "
            f"guard path is broken. stdout={denied.stdout.strip()!r}"
        )
    elif _DENIED_HINT not in denied.stdout:
        failures.append(
            f"pretooluse deny for {_DENIED_SAMPLE!r} lost its redirect hint "
            f"({_DENIED_HINT!r})"
        )

    allowed = _run(
        ["bash", wrapper], stdin=_hook_payload(_ALLOWED_SAMPLE), cwd=project_root
    )
    if allowed.returncode != 0:
        failures.append(
            f"pretooluse wrapper exited {allowed.returncode} on an allowed "
            f"command: {allowed.stderr.strip()}"
        )
    elif allowed.stdout.strip():
        failures.append(
            f"pretooluse wrapper was not silent on the allowed command "
            f"{_ALLOWED_SAMPLE!r}: {allowed.stdout.strip()!r}"
        )
    return failures


def check_guard_decisions() -> list[str]:
    """In-process smoke of :func:`hook_guard.decide` (belt-and-braces)."""
    failures: list[str] = []
    if hook_guard.decide(_DENIED_SAMPLE) is None:
        failures.append(f"decide() no longer denies {_DENIED_SAMPLE!r}")
    if hook_guard.decide(_ALLOWED_SAMPLE) is not None:
        failures.append(f"decide() wrongly denies the diagnostic {_ALLOWED_SAMPLE!r}")
    return failures


def check_script_syntax(project_root: Path) -> list[str]:
    """``bash -n`` every wired hook script — a parse error would brick a hook."""
    failures: list[str] = []
    for rel in _HOOK_SCRIPTS:
        res = _run(["bash", "-n", str(project_root / rel)])
        if res.returncode != 0:
            failures.append(f"{rel} failed `bash -n`: {res.stderr.strip()}")
    return failures


def hook_selfcheck_main(project_root: Path) -> int:
    """Run every host-side hook check; print PASS/FAIL per check; 0 iff clean."""
    settings_path = project_root / ".claude" / "settings.json"
    checks = (
        ("settings-wiring", lambda: check_settings_wiring(settings_path)),
        ("script-syntax", lambda: check_script_syntax(project_root)),
        ("guard-decisions", check_guard_decisions),
        ("pretooluse-endtoend", lambda: check_pretooluse_endtoend(project_root)),
    )
    ok = True
    for name, run in checks:
        failures = run()
        if failures:
            ok = False
            for failure in failures:
                sys.stdout.write(f"FAIL  hook-selfcheck[{name}]: {failure}\n")
        else:
            sys.stdout.write(f"PASS  hook-selfcheck[{name}]\n")
    if ok:
        sys.stdout.write("hook-selfcheck: OK — all wired host-side hooks pass\n")
    return 0 if ok else 1
