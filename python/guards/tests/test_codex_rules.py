"""The Codex exec-policy file, judged by the real `codex execpolicy check`."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

RULES = Path(__file__).resolve().parents[3] / "unix" / "home" / ".codex" / "rules" / "guards.rules"
CODEX = shutil.which("codex")


def decision(command: list[str]) -> str:
    assert CODEX is not None
    argv = [CODEX, "execpolicy", "check", "--rules", str(RULES), "--", *command]
    result = subprocess.run(argv, capture_output=True, text=True, check=True)
    return json.loads(result.stdout).get("decision", "none")


@pytest.mark.skipif(CODEX is None, reason="codex is not installed")
@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("brew install jq", "forbidden"),
        ("brew tap foo/bar", "forbidden"),
        ("brew list", "none"),
        ("doppler secrets get API_KEY --plain", "forbidden"),
        ("doppler secrets download", "forbidden"),
        ("doppler run -- env", "forbidden"),
        ("doppler secrets substitute tpl.yaml", "forbidden"),
        ("doppler secrets set KEY", "none"),
        ("fnox get API_KEY", "forbidden"),
        ("fnox export", "forbidden"),
        ("fnox exec --only KEY -- env", "none"),
        ("docker desktop update", "forbidden"),
        ("docker desktop start --timeout 300", "none"),
    ],
)
def test_codex_execpolicy(command: str, expected: str) -> None:
    assert decision(command.split()) == expected
