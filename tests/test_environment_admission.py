# Copyright (c) 2026 Raymond Manaloto
"""Public environment admission controls; never execute inherited env dumps."""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest
from dotfiles_setup import environment_admission


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        ("env 2>/dev/null", True),
        ("printenv 2>/dev/null", True),
        ("env -0 12>>/dev/null", True),
        ("printenv -0 2>&1", True),
        ("env</dev/null", True),
        ("printenv</dev/null", True),
        ("env -u SYNTHETIC 0</dev/null", True),
        ("printenv -0 </dev/null", True),
        ("env /bin/true 2>/dev/null", False),
        ("printenv SYNTHETIC 2>/dev/null", False),
        ("printenv 2 >/dev/null", False),
        ("env 2 >/dev/null", False),
        ("python -c 'import os; print(os.environ if 1 < 2 else {})'", True),
        ("python -c 'print(1 < 2)'", False),
        ("node -e 'console.log(1 < 2)'", False),
        ("env -u SYNTHETIC python -c 'print(1 > 0)' 2>/dev/null", False),
    ],
)
def test_redirect_syntax_preserves_command_argument_roles(
    command: str, *, denied: bool
) -> None:
    assert (environment_admission.decide(command) is not None) is denied


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        ("python script.py -c 'print(os.environ)'", False),
        ("python -m module -c 'print(os.environ)'", False),
        ("python - -c 'print(os.environ)'", False),
        ("python -- -c 'print(os.environ)'", False),
        ("node script.js -e 'console.log(process.env)'", False),
        ("node - -p process.env", False),
        ("node -- -p process.env", False),
        ("python -W -c script.py 'print(os.environ)'", False),
        ("python -X -c script.py 'print(os.environ)'", False),
        ("python --check-hash-based-pycs -c script.py 'print(os.environ)'", False),
        ("node -r -p script.js process.env", False),
        ("node --require=-p script.js process.env", False),
        ("node -r=synthetic -p process.env", True),
        ("node --require synthetic -e 'console.log(process.env)'", True),
        ("node --trace-warnings -e 'console.log(process.env)'", True),
        ("node --trace-warnings -e 'console.log(1)'", False),
        ("python -B -Wignore -Xdev -c 'print(os.environ)' --help", True),
        (
            "python -I -W ignore -X dev --check-hash-based-pycs always -c 'print(1)'",
            False,
        ),
        ("python -c 'print(1)' -c 'print(os.environ)'", False),
        ("node -e 'console.log(1)' -e 'console.log(process.env)'", False),
        ("node -e 'console.log(process.env)' --help", True),
        ("python script.py --unknown -c 'print(os.environ)'", False),
        ("node script.js --unknown -p process.env", False),
        ("python -c 'print(1)' --unknown", False),
        ("node -p '1' --unknown", False),
        ("python -c", False),
        ("python -W", False),
        ("node -p", False),
        ("node --require", False),
    ],
)
def test_interpreter_arguments_are_selected_only_in_option_position(
    command: str, *, denied: bool
) -> None:
    assert (environment_admission.decide(command) is not None) is denied


@pytest.mark.parametrize(
    "option",
    [
        "-b",
        "-bb",
        "-B",
        "-d",
        "-E",
        "-i",
        "-I",
        "-O",
        "-OO",
        "-P",
        "-q",
        "-s",
        "-S",
        "-u",
        "-v",
        "-vv",
        "-x",
    ],
)
def test_supported_python_option_preserves_inline_program_inspection(
    option: str,
) -> None:
    assert environment_admission.decide(f"python {option} -c 'print(os.environ)'")
    assert environment_admission.decide(f"python {option} -c 'print(1)'") is None


@pytest.mark.parametrize(
    "invocation",
    [
        "python -h",
        "python -?",
        "python --help",
        "python --help-env",
        "python --help-xoptions",
        "python --help-all",
        "python -V",
        "python -VV",
        "python --version",
        "node -h",
        "node --help",
        "node -v",
        "node --version",
    ],
)
def test_genuine_interpreter_help_does_not_select_later_code(invocation: str) -> None:
    assert (
        environment_admission.decide(
            f"{invocation} -c 'print(os.environ)' -p process.env"
        )
        is None
    )


@pytest.mark.parametrize(
    "command",
    [
        "python --unknown -c 'print(1)'",
        "python -BO -c 'print(1)'",
        "node --unknown -p 1",
        "node -vp 1",
        "env -u SYNTHETIC python --unknown -c 'print(1)'",
        "sh -c 'node --unknown -p 1'",
        'echo "$(node --unknown -p 1)"',
    ],
)
def test_unsupported_interpreter_option_has_fixed_inspectability_reason(
    command: str,
) -> None:
    assert environment_admission.decide(command) == (
        "Cannot inspect unsupported interpreter option syntax."
    )


@pytest.mark.parametrize(
    ("code", "denied"),
    [
        ('console.log("Do not console.log(process.env)")', False),
        ('console.log("Do not stdout.write(JSON.stringify(process.env))")', False),
        (
            'console.log("Do not console.log(process.env)");console.log(process.env)',
            True,
        ),
        ("console.log(process.env)", True),
        ('console.log("1 <<EOF console.log(process.env)")', False),
        ('console.log("console.log(process.env) /")', True),
        ('console.log("console.log(process.env) `")', True),
        ('console.log("console.log(process.env)");\nconsole.log(1)', True),
        ('console.log("console.log(process.env)', True),
    ],
)
def test_node_balanced_prose_is_masked_only_in_the_supported_subset(
    code: str, *, denied: bool
) -> None:
    assert (
        environment_admission.decide("node -e " + shlex.quote(code)) is not None
    ) is denied


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        ("en\\\nv", True),
        ("print\\\nenv -0", True),
        ('"en\\\nv"', True),
        ('"en' + "\\" * 2 + '\nv"', False),
        ('"en' + "\\" * 3 + '\nv"', False),
        ("env -u SYNTHETIC \\\n/bin/true", False),
        ("print\\\nenv SYNTHETIC >/dev/null", False),
        ("echo 'en\\\nv'", False),
        ("'en\\\nv'", False),
        ('python -c "import os; print(\\\nos.environ)"', True),
        ('python -c "print(\\\n1)"', False),
        ('echo "$(en\\\nv)"', True),
        ("cat <<'EOF'\nen\\\nv\nEOF\nprintenv", True),
        ("cat <<'EOF'\nen\\\nv\nEOF", False),
        ("# excluded mixed syntax\nen\\\nv", False),
        ("en\\\r\nv", False),
    ],
)
def test_ordinary_continuations_share_the_analysis_copy_without_changing_data(
    command: str, *, denied: bool
) -> None:
    payload: dict[str, object] = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    assert (environment_admission.decide_payload(payload) is not None) is denied
    assert payload["tool_input"] == {"command": command}


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


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        ("bash -lc 'printenv'", True),
        ("sh -ec 'env'", True),
        ("/bin/zsh -fc 'env'", True),
        ("dash -c 'printenv'", True),
        ("bash --noprofile --norc -lc 'env'", True),
        ("bash -o posix -lc 'env'", True),
        ("bash ./script.sh -lc printenv", False),
        ("bash -lc 'printenv SYNTHETIC >/dev/null'", False),
        ("bash -lc 'printf \"Do not run printenv\"'", False),
        ("bash -l", False),
        ("bash -c", False),
    ],
)
def test_shell_option_clusters_preserve_command_and_script_argument_roles(
    command: str, *, denied: bool
) -> None:
    assert (environment_admission.decide(command) is not None) is denied


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        ("node -p 'process.env'", True),
        ("node --print 'process.env'", True),
        ("node --print=process.env", True),
        ("node -p 'JSON.stringify(process.env)'", True),
        ("node -p '(process.env)'", True),
        ("node --eval='console.log(process.env)'", True),
        ("node -e 'console.log(process.env)'", True),
        ("node -e 'process.env'", False),
        ("node -p '\"process.env\"'", False),
        ("node -p 'Boolean(process.env.SYNTHETIC)'", False),
        ('node -p \'process.env.SYNTHETIC ? "SET" : "ABSENT"\'', False),
    ],
)
def test_node_print_mode_distinguishes_collections_from_presence_and_prose(
    command: str, *, denied: bool
) -> None:
    assert (environment_admission.decide(command) is not None) is denied


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
        ({"tool_name": "Bash", "tool_input": {"command": "bash -lc 'env'"}}, True),
        (
            {
                "tool_name": "exec_command",
                "tool_input": {"cmd": "node -p 'process.env'"},
            },
            True,
        ),
        (
            {
                "tool_name": "Bash",
                "tool_input": {"command": "bash -lc 'printenv SYNTHETIC >/dev/null'"},
            },
            False,
        ),
        (
            {
                "tool_name": "Bash",
                "tool_input": {"command": "node -p 'Boolean(process.env.SYNTHETIC)'"},
            },
            False,
        ),
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


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        ("bash -c 'printenv' --help", True),
        ("env python -c 'import os; print(os.environ)' --version", True),
        ("node -e 'console.log(process.env)' --help", True),
        ("bash --help", False),
        ("python --version", False),
        ("node --help", False),
        ("bash -c 'echo safe' --help", False),
        ("python -c 'print(1)' --version", False),
        ("node -e 'console.log(1)' --help", False),
        ("env --help", False),
    ],
)
def test_help_exemption_respects_executed_program_arguments(
    command: str, *, denied: bool
) -> None:
    assert (environment_admission.decide(command) is not None) is denied


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        ("env -v", True),
        ("env -iv0", True),
        ("env -", True),
        ("env -uSYNTHETIC printenv", True),
        ("env -C/tmp printenv", True),
        ("env -P/bin printenv", True),
        ("env -P /bin printenv", True),
        ("env --unset=SYNTHETIC printenv", True),
        ("env --chdir=/tmp printenv", True),
        ("env -v echo safe", False),
        ("env -iv0 echo safe", False),
        ("env - echo safe", False),
        ("env -uSYNTHETIC printenv SYNTHETIC", False),
        ("env -C/tmp echo safe", False),
        ("env -P/bin echo safe", False),
        ("env -P /bin echo safe", False),
        ("env --unset=SYNTHETIC echo safe", False),
        ("env --chdir=/tmp echo safe", False),
        ("env SYNTHETIC=value -v", False),
        ("env -- -v", False),
        ("env echo -v", False),
        ("env -v --help", False),
        ("env -u --help printenv", True),
    ],
)
def test_env_options_keep_values_assignments_and_utility_roles(
    command: str, *, denied: bool
) -> None:
    assert (environment_admission.decide(command) is not None) is denied


@pytest.mark.parametrize(
    ("command", "outcome"),
    [
        ("env -S printenv", "broad"),
        ("env -Sprintenv", "broad"),
        ("env -S '-u SYNTHETIC printenv'", "broad"),
        ("env -S-P/bin printenv", "broad"),
        ("env -S 'echo safe'", "allow"),
        ("env -S 'echo \"safe words\"'", "allow"),
        ("env -S 'echo\tsafe'", "allow"),
        ("env -v -S echo", "allow"),
        ("env -S-P/bin echo safe", "allow"),
        (r"env -S 'echo\_safe'", "split"),
        ("env -S 'echo $SYNTHETIC'", "split"),
        ("env -S 'echo #safe'", "split"),
        ("env -S 'echo\nsafe'", "split"),
        ("env -S 'echo\vsafe'", "split"),
        ("env -S 'echo\u00a0safe'", "split"),
        ("env -S 'echo \"broken'", "split"),
        ("env -vSprintenv", "option"),
        ("env --unsupported", "option"),
        ("bash -c 'env -S \"echo #safe\"'", "split"),
        ("env -v sh -c 'env -S \"echo #safe\"'", "split"),
        ("echo \"$(env -S 'echo #safe')\"", "split"),
    ],
)
def test_env_split_subset_and_nested_inspectability_reasons(
    command: str, outcome: str
) -> None:
    expected = {
        "allow": None,
        "broad": environment_admission.DENY_REASON,
        "split": (
            "Cannot inspect unsupported env -S syntax; use literal words with "
            "balanced quotes and ASCII space/tab separators."
        ),
        "option": "Cannot inspect unsupported env option syntax.",
    }
    assert environment_admission.decide(command) == expected[outcome]


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        ("sh -c 'env > /dev/stdout'", True),
        ("node -e '(() => console.log(process.env))()'", True),
        ("sh -c 'echo safe > /dev/stdout'", False),
        ("node -e '(() => console.log(1))()'", False),
    ],
)
def test_quoted_redirects_and_arrow_programs_retain_executable_text(
    command: str, *, denied: bool
) -> None:
    assert (environment_admission.decide(command) is not None) is denied


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        ("echo $(sh -c 'printenv')", True),
        ("echo `sh -c 'printenv'`", True),
        ("echo $(sh -c 'echo safe')", False),
        ("echo `sh -c 'echo safe'`", False),
        ("echo '$(sh -c printenv)'", False),
        ("cat <<'EOF'\n`sh -c 'printenv'`\nEOF", False),
    ],
)
def test_substitution_literal_programs_are_inspected_as_source(
    command: str, *, denied: bool
) -> None:
    assert (environment_admission.decide(command) is not None) is denied


@pytest.mark.parametrize(
    ("command", "denied"),
    [
        ("bash --noprofile --help -c 'env'", False),
        ("python -I --help -c 'import os; print(os.environ)'", False),
        ("node --trace-warnings --help -e 'console.log(process.env)'", False),
        ("bash --noprofile -c 'env' --help", True),
        ("python -I -c 'import os; print(os.environ)' --help", True),
        ("node --trace-warnings -e 'console.log(process.env)' --help", True),
    ],
)
def test_help_in_option_position_precedes_program_execution(
    command: str, *, denied: bool
) -> None:
    assert (environment_admission.decide(command) is not None) is denied
