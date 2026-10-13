# Copyright (c) 2026 Raymond Manaloto
"""Public environment admission controls; never execute inherited env dumps."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import environment_admission


@pytest.mark.parametrize(
    "command",
    [
        "printenv",
        "env | sort",
        "/usr/bin/env",
        "env -0",
        "env -u SYNTHETIC | sort",
        "env SYNTHETIC=value",
        "export -p",
        "declare -x",
        "typeset -xp",
        "set",
        "pwd; printenv",
    ],
)
def test_literal_broad_stdout_routes_are_denied(command: str) -> None:
    assert environment_admission.decide(command) is not None


@pytest.mark.parametrize(
    "command",
    [
        "env -u SYNTHETIC command --help",
        "env -u SYNTHETIC python -c 'print(1)'",
        "env SYNTHETIC=value command --help",
        "printenv SYNTHETIC >/dev/null",
        '[ -n "$SYNTHETIC" ] && echo SET || echo ABSENT',
        (
            "python -c 'import os; "
            'print("SET" if "SYNTHETIC" in os.environ else "ABSENT")\''
        ),
        "printf '%s\\n' 'Do not run env | sort, printenv, or export -p'",
        "rg 'env|printenv|export -p' docs",
        "cat <<'EOF'\nDo not run env or printenv.\nEOF",
        "env --help",
        "set -e",
        "export SYNTHETIC=value",
        "declare -p SYNTHETIC",
    ],
)
def test_legitimate_environment_handling_and_prose_remain_allowed(command: str) -> None:
    assert environment_admission.decide(command) is None


@pytest.mark.parametrize(
    "command",
    [
        "env -u SYNTHETIC printenv",
        "command /usr/bin/printenv -0 | sort",
        "env >/dev/stdout",
        "sh -c 'env'",
        "env -u SYNTHETIC bash -c 'printenv'",
        "python -c 'import os; print(dict(os.environ))'",
        "python3 -c 'import os, json; print(json.dumps(dict(os.environ)))'",
        "node -e 'console.log(process.env)'",
        "cat /proc/self/environ",
    ],
)
def test_literal_equivalent_environment_routes_are_denied(command: str) -> None:
    assert environment_admission.decide(command) is not None


@pytest.mark.parametrize(
    "command",
    [
        "python -c 'print(\"Do not print(dict(os.environ))\")'",
        "python -c 'import os, json; json.dumps(dict(os.environ))'",
        "node -e 'console.log(\"Do not print process.env)\")'",
    ],
)
def test_interpreter_prose_and_nonstdout_code_remain_allowed(command: str) -> None:
    assert environment_admission.decide(command) is None


def test_standalone_hook_denies_synthetic_shell_payload_without_echoing_input() -> None:
    root = Path(__file__).resolve().parent.parent
    sentinel = "SYNTHETIC_NONSECRET_SENTINEL_1847"
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "exec_command",
        "tool_input": {"command": f"env SYNTHETIC={sentinel}"},
    }
    result = subprocess.run(
        [sys.executable, "-P", str(root / "scripts/codex-environment-admission.py")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=root,
        env={"PATH": "/usr/bin:/bin", "SYNTHETIC": sentinel},
        timeout=10,
        check=False,
    )
    assert result.returncode == 0
    decision = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]
    assert decision == "deny"
    assert sentinel not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "command",
    [
        "export",
        "declare",
        "typeset",
        "'env'",
        '"/usr/bin/printenv"',
        'echo "$(env)"',
        'echo "`printenv`"',
    ],
)
def test_direct_quoted_commands_and_literal_substitutions_are_denied(
    command: str,
) -> None:
    assert environment_admission.decide(command) is not None


@pytest.mark.parametrize(
    "command",
    ["echo 'Do not run $(env) or `printenv`'", r'echo "Do not run \$(env)"'],
)
def test_quoted_and_escaped_substitution_prohibition_remains_allowed(
    command: str,
) -> None:
    assert environment_admission.decide(command) is None


@pytest.mark.parametrize(
    ("payload", "denied"),
    [
        ({"tool_name": "Bash", "tool_input": {"command": "env"}}, True),
        ({"tool_name": "shell_command", "tool_input": {"command": "printenv"}}, True),
        ({"tool_name": "functions.exec_command", "tool_input": {"cmd": "env"}}, True),
        ({"tool_name": "Read", "tool_input": {"file_path": "env"}}, False),
        (
            {
                "tool_name": "Bash",
                "tool_input": {"command": "printenv SYNTHETIC >/dev/null"},
            },
            False,
        ),
        (
            {
                "tool_name": "Bash",
                "tool_input": {"command": "env -u SYNTHETIC /bin/true"},
            },
            False,
        ),
        ({"tool_name": "Bash", "tool_input": {}}, True),
        ({"tool_name": "Bash", "tool_input": []}, True),
        ({"tool_name": [], "tool_input": {"command": "env"}}, True),
    ],
)
def test_native_hook_protocol_has_deny_and_silent_allow_controls(
    payload: dict[str, object], *, denied: bool
) -> None:
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-P", str(root / "scripts/codex-environment-admission.py")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=root,
        env={"PATH": "/usr/bin:/bin", "SYNTHETIC": "nonsecret-protocol-control"},
        timeout=10,
        check=False,
    )
    assert result.returncode == 0
    if denied:
        decision = json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]
        assert decision == "deny"
    else:
        assert result.stdout == ""
