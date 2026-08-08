# Copyright (c) 2026 Raymond Manaloto
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
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotfiles_setup import hook_guard

_PROBE_TIMEOUT_S = 60.0

# A representative denied command (has a canonical mise task) and an allowed
# one (a plain diagnostic). Driven through the REAL wrapper end-to-end; the
# full rule battery lives in tests/test_hook_guard.py.
_DENIED_SAMPLE = "gh pr create --fill"
_DENIED_HINT = "mise run ship"
_ALLOWED_SAMPLE = "git status --porcelain"

#: Public: the tests drive this wrapper and the off-root arm by name.
PRETOOLUSE_WRAPPER = "scripts/pretooluse-guard.sh"
_WEB_SETUP = "scripts/web-setup.sh"
_HOOK_SCRIPTS = (PRETOOLUSE_WRAPPER, _WEB_SETUP)

# Each settings.json hook event -> (command substrings that MUST appear in its
# wired command(s), required matchers or None). Keeps the project hooks from
# silently drifting out of .claude/settings.json (the wiring the end-to-end
# check then exercises).
#
# PreToolUse must stay scoped, and to ALL FIVE tools it guards: `Bash` (the
# mise-tasks-only redirects), `AskUserQuestion` (the ask-quality standard, Ray
# 2026-08-02 — see dotfiles_setup.ask_quality), and `Edit`/`Write`/
# `NotebookEdit` (the write-time default-branch guard, #400 — see
# dotfiles_setup.branch_guard). Each is asserted separately, because the
# matcher is one alternation string: a check that only looked for "Bash" would
# keep passing if AskUserQuestion were dropped from it, and the guard would go
# silently absent for that tool exactly as #343 did for off-root Bash.
#
# The assertion is exact ALTERNATION-TOKEN membership, never substring
# containment — "Edit" is a substring of "NotebookEdit", so a containment test
# let a matcher that dropped bare `Edit` report fully wired. See
# check_settings_wiring.
#
# SessionEnd runs the command-audit refine loop once per session (the recurring
# half of mise-tasks-only enforcement). A matcher would SCOPE it to particular
# end reasons (clear/logout/resume/...) — it must fire on all of them, hence
# None. Deliberately NOT a `Stop` hook: Stop fires every turn and can block,
# which would put a transcript scan on the per-turn path.
#
# SessionStart carries the two host-only checkups that no in-tree gate can do:
# the offline tool-currency drift check, and the #418 project doctor (declared
# setup vs this host). Both are silent when healthy and both always exit 0, so
# neither can disrupt a session; asserting them here is what keeps them from
# quietly falling out of settings.json, which is the only place they are wired.
_SESSION_END_REPORT = ".agent/command-audit.md"
_SETTINGS_WIRING: tuple[tuple[str, tuple[str, ...], tuple[str, ...] | None], ...] = (
    # All five matcher tools are required, not just the two the guard started
    # with. The three file-modifying ones route to `branch_guard` (#400); with
    # only ("Bash", "AskUserQuestion") required, narrowing the live matcher
    # back would silently kill the write-time default-branch gate while ship
    # and land both stayed green — a check that can only pass
    # (`probes-need-a-control-arm.md`).
    (
        "PreToolUse",
        (PRETOOLUSE_WRAPPER,),
        ("Bash", "AskUserQuestion", "Edit", "Write", "NotebookEdit"),
    ),
    (
        "SessionStart",
        (_WEB_SETUP, "CLAUDE_CODE_REMOTE", "run tool-currency-check", "run doctor"),
        None,
    ),
    ("SessionEnd", ("run command-audit", _SESSION_END_REPORT), None),
)

# Claude Code runs hooks "in the current directory", not the project root, and
# exports ${CLAUDE_PROJECT_DIR} so a hook can find its own repo anyway. A hook
# command that names a bare relative path therefore resolves against whatever
# directory the session happens to be in — and silently fails open there, since
# a non-zero non-2 PreToolUse exit is a NON-BLOCKING error that lets the tool
# call proceed. That is #343: 125 denied Bash calls executed unchecked while the
# cwd was a sibling repo. Every wired command must anchor its paths.
_PROJECT_DIR_ANCHOR = "CLAUDE_PROJECT_DIR"


def _run(
    cmd: list[str],
    *,
    stdin: str | None = None,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
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
            env=env,
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
    for event, required, matchers in _SETTINGS_WIRING:
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
        # Exact ALTERNATION-TOKEN membership, never substring containment.
        # `matcher in m` looks equivalent and is not: "Edit" is a substring of
        # "NotebookEdit", so a matcher that dropped bare `Edit` while keeping
        # `NotebookEdit` satisfied the `Edit` requirement and reported fully
        # wired — the branch_guard write gate for plain `Edit` calls would go
        # unenforced with ship and land both green. Found by cold review; the
        # arm that missed it narrowed the matcher to `Bash|AskUserQuestion`,
        # removing BOTH tokens at once, which is not how the real regression
        # looks (`probes-need-a-control-arm.md` rule 2 — mutate realistically).
        tokens = {t.strip() for m, _ in entries for t in m.split("|") if t.strip()}
        failures.extend(
            f"settings.json {event} hook must be scoped with matcher "
            f"{matcher!r} (tool events fire on every tool otherwise)"
            for matcher in matchers or ()
            if matcher not in tokens
        )
    failures.extend(_unanchored_hooks(settings))
    return failures


def _unanchored_hooks(settings: dict) -> list[str]:
    """Every wired hook command must anchor its paths to ``$CLAUDE_PROJECT_DIR``.

    Hooks run in the session's CURRENT directory, so a bare relative path is
    resolved against a sibling repo the moment the session works in one — and
    the guard then fails open silently (#343). Checking the whole hook block
    rather than a named list is deliberate: the defect is a property of *any*
    unanchored command, so a hook added later must not be able to reintroduce
    it unnoticed.
    """
    failures: list[str] = []
    for event, entries in settings.get("hooks", {}).items():
        if not isinstance(entries, list):
            continue
        for matcher, command in _event_entries(settings, str(event)):
            if _PROJECT_DIR_ANCHOR in command:
                continue
            failures.append(
                f"settings.json {event} hook (matcher={matcher or '-'!r}) does "
                f"not anchor its paths to ${_PROJECT_DIR_ANCHOR} and will "
                f"resolve against whatever cwd the session is in: {command!r}"
            )
    return failures


def check_pretooluse_endtoend(project_root: Path) -> list[str]:
    """Drive the REAL PreToolUse wrapper end-to-end (deny + allow).

    A denied command must deny, an allowed one must stay silent. Exercises
    settings.json's wired entrypoint (wrapper -> uv -> ``dotfiles-setup hook
    pretooluse`` -> :func:`hook_guard.decide`), not just ``decide`` alone.
    """
    failures: list[str] = []
    wrapper = str(project_root / PRETOOLUSE_WRAPPER)

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
    failures.extend(check_ask_quality_endtoend(project_root, wrapper))
    failures.extend(check_offroot_arm(project_root, wrapper))
    return failures


def _ask_payload(*, cited: bool) -> str:
    """A single-select AskUserQuestion that differs ONLY in whether it cites.

    Both arms are otherwise compliant (recommendation first, PRO:/CON: on every
    option), so a difference in the wrapper's verdict can only come from the
    citation rule — the control arm for the deny.
    """
    where = "per `mise.toml`" if cited else "which do you prefer"
    return json.dumps(
        {
            "tool_name": "AskUserQuestion",
            "tool_input": {
                "questions": [
                    {
                        "question": f"Selfcheck probe — {where}?",
                        "header": "Probe",
                        "multiSelect": False,
                        "options": [
                            {
                                "label": "A (Recommended)",
                                "description": "PRO: a. CON: b.",
                            },
                            {"label": "B", "description": "PRO: c. CON: d."},
                        ],
                    }
                ]
            },
        }
    )


def check_ask_quality_endtoend(project_root: Path, wrapper: str) -> list[str]:
    """Drive the ask-quality gate through the REAL wrapper (deny + allow).

    The wiring check proves ``AskUserQuestion`` is in the matcher; this proves
    the guard actually decides on it. Without the allow arm the deny would be
    indistinguishable from a gate that denies every ask.
    """
    failures: list[str] = []

    denied = _run(["bash", wrapper], stdin=_ask_payload(cited=False), cwd=project_root)
    if denied.returncode != 0:
        failures.append(
            f"pretooluse wrapper exited {denied.returncode} on a non-compliant "
            f"AskUserQuestion (must exit 0): {denied.stderr.strip()}"
        )
    elif '"permissionDecision": "deny"' not in denied.stdout:
        failures.append(
            "pretooluse wrapper did not DENY an uncited AskUserQuestion — the "
            f"ask-quality gate is not reachable. stdout={denied.stdout.strip()!r}"
        )

    allowed = _run(["bash", wrapper], stdin=_ask_payload(cited=True), cwd=project_root)
    if allowed.returncode != 0:
        failures.append(
            f"pretooluse wrapper exited {allowed.returncode} on a compliant "
            f"AskUserQuestion: {allowed.stderr.strip()}"
        )
    elif allowed.stdout.strip():
        failures.append(
            "pretooluse wrapper was not silent on a COMPLIANT AskUserQuestion — "
            f"the gate denies every ask: {allowed.stdout.strip()!r}"
        )
    return failures


def _offroot_env(project_root: Path) -> dict[str, str]:
    """The hook's environment with this process's own venv resolution removed.

    Drops ``VIRTUAL_ENV`` and every ``PATH`` entry inside the project, so the
    wrapper must resolve the guard through ``$CLAUDE_PROJECT_DIR`` rather than
    through a venv it happened to inherit. See :func:`check_offroot_arm`.

    ``UV_PROJECT_ENVIRONMENT`` is deliberately PRESERVED, and that is a
    correction, not an oversight. Stripping it broke the devcontainer, where
    ``devcontainer.json`` sets it to ``/home/$USER/.venvs/dotfiles-python`` on
    purpose: without it uv falls back to ``<project>/.venv`` inside the
    bind-mounted workspace and dies on the host's stale copy (``failed to remove
    directory python/.venv/lib: Directory not empty``). It is environment
    CONFIGURATION the container requires, not an answer leaked from this
    process — the distinction the first version got wrong, and only the
    in-container `sync-full` gate caught it.

    Bound worth stating: where that variable already points at a ready venv
    holding ``dotfiles-setup``, this arm verifies the wrapper is REACHABLE
    off-root rather than that it re-resolves its project. The resolution half is
    covered on the host, and statically everywhere by :func:`_unanchored_hooks`.
    """
    root = str(project_root)
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    env["PATH"] = os.pathsep.join(
        p for p in env.get("PATH", "").split(os.pathsep) if p and not p.startswith(root)
    )
    env[_PROJECT_DIR_ANCHOR] = root
    return env


def check_offroot_arm(project_root: Path, wrapper: str) -> list[str]:
    """The same deny, driven from a cwd that is NOT the project root (#343).

    Both arms above run with ``cwd=project_root``, so they could not observe the
    defect that let 125 denied commands through: hooks execute in the session's
    current directory, and every relative path in the chain — settings.json's
    script path AND the wrapper's own ``uv run --project python`` — resolved
    against a sibling repo instead. Measured before the fix: rc=127 from the
    script path, rc=2 from the uv project. Both exit non-zero-non-2, which
    PreToolUse treats as a non-blocking error, so the call proceeded.

    A throwaway directory is the foreign cwd rather than a sibling clone: the
    arm must hold on any machine, including CI, where no second repo exists.

    THE ENVIRONMENT IS SCRUBBED, and that is what makes the arm able to fail.
    The first version inherited ``os.environ`` wholesale — and since the
    selfcheck itself runs under ``uv run --project python``, the child already
    had the project's venv on ``PATH``. So ``dotfiles-setup`` resolved no matter
    what the wrapper asked for, and the probe passed with the defect
    reintroduced. A probe that inherits a pre-resolved answer cannot observe the
    resolution it is testing.
    """
    with tempfile.TemporaryDirectory() as foreign:
        result = _run(
            ["bash", wrapper],
            stdin=_hook_payload(_DENIED_SAMPLE),
            cwd=Path(foreign),
            env=_offroot_env(project_root),
        )
    if result.returncode != 0:
        return [
            (
                f"pretooluse wrapper exited {result.returncode} when run from a "
                f"foreign cwd — it must resolve via ${_PROJECT_DIR_ANCHOR}: "
                f"{result.stderr.strip()}"
            )
        ]
    if '"permissionDecision": "deny"' not in result.stdout:
        return [
            (
                f"pretooluse wrapper did not DENY {_DENIED_SAMPLE!r} when run from "
                f"a foreign cwd — the guard fails OPEN off-root (#343). "
                f"stdout={result.stdout.strip()!r} stderr={result.stderr.strip()!r}"
            )
        ]
    return []


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
