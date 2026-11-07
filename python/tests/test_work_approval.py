"""The work skill's hk approval step, set up as the skill says, in a real git repository with real hk."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STEP = REPO / "unix/home/.config/agents/skills/work/hk-approval.pkl"
SESSION = "01a19f1e-28d7-7b12-bce2-4731b8693992"
# A read-only last turn as Codex 0.166.0 records it (python/repo/tests/test_pane_approval.py).
READ_ONLY = {
    "type": "managed",
    "file_system": {
        "type": "restricted",
        "entries": [
            {"path": {"type": "special", "value": {"kind": "root"}}, "access": "read"}
        ],
    },
    "network": "restricted",
}


class WorkApprovalStepTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        self.repo = self.root / "repo"
        self.message = self.root / "message"
        self.message.write_text("feat: one\n\nWhy it changes.\n")
        (self.root / "gitconfig").write_text("[user]\n\tname = t\n\temail = t@e\n")
        # A pre-commit hook exports GIT_*, which would point git at the real checkout.
        self.env = {
            name: value
            for name, value in os.environ.items()
            if not name.startswith(("GIT_", "HK"))
        }
        self.env |= {
            "GIT_CONFIG_GLOBAL": str(self.root / "gitconfig"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "CODEX_HOME": str(self.root / "codex"),
            # This branch's repotools, the one the step calls.
            "PATH": f"{REPO / 'python/repo/.venv/bin'}{os.pathsep}{os.environ['PATH']}",
        }
        self.repo.mkdir()
        self.run_in("git", "init", "-q")
        # Setup step 5 of the skill: hk init, the commit-msg hook added, validate, install.
        self.run_in("hk", "init")
        config = self.repo / "hk.pkl"
        config.write_text(config.read_text() + "\n" + STEP.read_text())
        self.run_in("hk", "validate")
        self.run_in("hk", "install")
        (self.repo / "a.txt").write_text("one\n")
        self.run_in("git", "add", "-A")
        self.run_in("repotools", "pane-pin", "--session", SESSION)

    def run_in(
        self, *argv: str, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        done = subprocess.run(
            argv,
            cwd=self.repo,
            env=self.env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if check and done.returncode != 0:
            raise AssertionError((argv, done.returncode, done.stdout, done.stderr))
        return done

    def answer(self, text: str) -> None:
        """The pinned reviewer's rollout, whose last read-only turn ends with this answer."""
        settings = {
            "turn_id": "t1",
            "cwd": str(self.repo),
            "approval_policy": "never",
            "sandbox_policy": {"type": "read-only"},
            "permission_profile": READ_ONLY,
        }
        message = {
            "type": "message",
            "role": "assistant",
            "phase": "final_answer",
            "content": [{"type": "output_text", "text": text}],
        }
        records = [
            {"type": "session_meta", "payload": {"id": SESSION, "cwd": str(self.repo)}},
            {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "t1"}},
            {"type": "turn_context", "payload": settings},
            {"type": "response_item", "payload": message},
            {
                "type": "event_msg",
                "payload": {
                    "type": "task_complete",
                    "turn_id": "t1",
                    "last_agent_message": text,
                },
            },
        ]
        folder = self.root / "codex/sessions/2026/11/06"
        folder.mkdir(parents=True, exist_ok=True)
        log = folder / f"rollout-2026-11-06T00-00-00-{SESSION}.jsonl"
        log.write_text("".join(json.dumps(record) + "\n" for record in records))

    def approve(self) -> None:
        shown = self.run_in(
            "repotools", "pane-fingerprint", "--message", str(self.message)
        ).stdout
        self.answer(f"Reviewed.\nPANE-APPROVE {json.loads(shown)['fingerprint']}")

    def commit(self) -> subprocess.CompletedProcess[str]:
        return self.run_in("git", "commit", "-q", "-F", str(self.message), check=False)

    def head(self) -> str:
        return self.run_in(
            "git", "rev-parse", "--verify", "-q", "HEAD", check=False
        ).stdout.strip()

    def assert_refused(
        self, done: subprocess.CompletedProcess[str], before: str
    ) -> None:
        self.assertNotEqual(done.returncode, 0, done.stderr)
        self.assertIn("pane-approval", done.stderr)
        self.assertEqual(self.head(), before)

    def test_a_commit_with_no_approval_is_refused(self) -> None:
        self.answer("Reviewed. Two findings to fix first.")
        self.assert_refused(self.commit(), "")

    def test_an_approved_first_commit_is_made(self) -> None:
        self.approve()
        self.assertEqual(self.commit().returncode, 0)
        self.assertTrue(self.head())

    def test_the_approved_commit_is_refused_once_its_bytes_change(self) -> None:
        self.approve()
        (self.repo / "a.txt").write_text("two\n")
        self.run_in("git", "add", "-A")
        self.assert_refused(self.commit(), "")
        # The same staged bytes, a changed message: still not what the pane approved.
        (self.repo / "a.txt").write_text("one\n")
        self.run_in("git", "add", "-A")
        self.message.write_text("feat: one\n\nWhy it changes, reworded.\n")
        self.assert_refused(self.commit(), "")
        # Back to the approved bytes: the approval holds again, because it is bound to them alone.
        self.message.write_text("feat: one\n\nWhy it changes.\n")
        self.assertEqual(self.commit().returncode, 0)


if __name__ == "__main__":
    unittest.main()
