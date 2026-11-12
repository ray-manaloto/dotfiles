"""hk runs //python:test for a commit that changes the shared agent rules or the zsh startup files."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HK_PKL = REPO / "hk.pkl"
STEP = "python-tests"


def evaluated_hooks() -> dict:
    # hk.pkl as hk reads it: evaluated by the real pkl, not matched as text.
    done = subprocess.run(
        ["pkl", "eval", "-f", "json", str(HK_PKL)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(done.stdout)["hooks"]


class PythonTestsStepTest(unittest.TestCase):
    def test_check_and_pre_commit_run_the_python_tests(self) -> None:
        hooks = evaluated_hooks()
        for hook in ("pre-commit", "check"):
            with self.subTest(hook=hook):
                step = hooks[hook]["steps"][STEP]
                self.assertEqual(
                    (step["check"], step["profiles"]),
                    ("mise run //python:test", ["!ci"]),
                )

    def test_the_step_runs_only_for_the_files_the_tests_read(self) -> None:
        # The real step's glob in a scratch repo, with a check that only says it ran.
        glob = evaluated_hooks()["pre-commit"]["steps"][STEP]["glob"]
        first_line = HK_PKL.read_text().splitlines()[0]
        cases = {
            "unix/home/.config/agents/AGENTS.md": True,
            "unix/home/.config/agents/workflow/ship.md": True,
            "unix/home/.config/zsh/.zshrc": True,
            "unix/home/.config/zsh/.zshrc.d/10-zsh.zsh": True,
            "unix/home/.zshenv": True,
            "README.md": False,
            "unix/home/.config/mise/config.toml": False,
        }
        for path, runs in cases.items():
            with self.subTest(path=path), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                git = ["git", "-C", tmp, "-c", "user.name=t", "-c", "user.email=t@e"]
                subprocess.run([*git, "init", "-q"], check=True)
                steps = f'["{STEP}"] {{\n        glob = new Listing {{ {" ".join(json.dumps(g) for g in glob)} }}\n'
                steps += '        check = "echo STEP-RAN"\n    }\n'
                (root / "hk.pkl").write_text(
                    f'{first_line}\n\nhooks {{\n    ["check"] {{\n        steps {{\n    {steps}}}\n    }}\n}}\n'
                )
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("x\n")
                subprocess.run([*git, "add", "-A"], check=True)
                done = subprocess.run(
                    ["hk", "check"],
                    check=False,
                    cwd=tmp,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
                self.assertEqual(
                    "STEP-RAN" in done.stdout + done.stderr,
                    runs,
                    done.stdout + done.stderr,
                )


if __name__ == "__main__":
    unittest.main()
