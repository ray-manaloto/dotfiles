"""herdr-startup's roll.py reads a tab's READY-TO-RESTART answer from its transcript, not its screen."""

import datetime
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "unix/home/.config/agents/skills/herdr-startup/scripts/roll.py"
spec = importlib.util.spec_from_file_location("roll", SCRIPT)
assert spec and spec.loader
roll = importlib.util.module_from_spec(spec)
spec.loader.exec_module(roll)

SENT = datetime.datetime(2026, 11, 13, 0, 26, tzinfo=datetime.UTC)


def user(stamp: str, text: str) -> dict:
    return {
        "type": "user",
        "timestamp": stamp,
        "message": {"role": "user", "content": text},
    }


def said(stamp: str, *texts: str, sidechain: bool = False) -> dict:
    content = [{"type": "tool_use", "name": "Bash", "input": {}}]
    content += [{"type": "text", "text": text} for text in texts]
    return {
        "type": "assistant",
        "timestamp": stamp,
        "isSidechain": sidechain,
        "message": {"role": "assistant", "content": content},
    }


class ReplyTest(unittest.TestCase):
    def answer(self, *records: dict, tail: str = "") -> str | None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "session.jsonl"
            path.write_text("".join(json.dumps(r) + "\n" for r in records) + tail)
            return roll.reply(str(path), SENT)

    def test_the_marker_counts_after_a_later_side_notes_turn(self) -> None:
        self.assertEqual(
            self.answer(
                user("2026-11-13T00:26:01Z", roll.HANDSHAKE),
                said(
                    "2026-11-13T00:26:12Z", "Resume block written.\n\nREADY-TO-RESTART"
                ),
                user("2026-11-13T00:26:30Z", "[side-notes] a note about this session"),
                said("2026-11-13T00:26:40Z", "The note does not hold."),
            ),
            "ready",
        )

    def test_a_turn_with_no_marker_is_no_answer(self) -> None:
        self.assertIsNone(
            self.answer(
                user("2026-11-13T00:26:01Z", roll.HANDSHAKE),
                said("2026-11-13T00:26:12Z", "Still finishing the review."),
            )
        )

    def test_the_handshake_text_itself_is_not_an_answer(self) -> None:
        # The request names both markers; only assistant text counts.
        self.assertIn("READY-TO-RESTART", roll.HANDSHAKE)
        self.assertIsNone(self.answer(user("2026-11-13T00:26:01Z", roll.HANDSHAKE)))

    def test_a_marker_from_before_the_handshake_is_ignored(self) -> None:
        self.assertIsNone(self.answer(said("2026-11-13T00:25:00Z", "READY-TO-RESTART")))

    def test_busy_keep_me_is_busy(self) -> None:
        self.assertEqual(
            self.answer(
                said(
                    "2026-11-13T00:26:12Z", "BUSY-KEEP-ME the owner's question is open"
                )
            ),
            "busy",
        )

    def test_the_last_marker_wins(self) -> None:
        self.assertEqual(
            self.answer(
                said("2026-11-13T00:26:12Z", "BUSY-KEEP-ME a job is running"),
                said("2026-11-13T00:30:00Z", "The job ended.\n\nREADY-TO-RESTART"),
            ),
            "ready",
        )

    def test_a_subagents_marker_and_a_half_written_line_are_skipped(self) -> None:
        self.assertIsNone(
            self.answer(
                said("2026-11-13T00:26:12Z", "READY-TO-RESTART", sidechain=True),
                tail='{"type": "assistant", "timest',
            )
        )


class TranscriptTest(unittest.TestCase):
    def test_the_session_is_found_under_any_project_and_in_the_graph(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "projects" / "-some-project" / "abc.jsonl"
            path.parent.mkdir(parents=True)
            path.write_text("")
            self.assertEqual(roll.transcript("abc", str(root / "projects")), str(path))
            self.assertIsNone(roll.transcript("missing", str(root / "projects")))
            graph = root / "graph.json"
            terminal = {"address": "t1", "kind": "claude", "session": "abc"}
            codex = {"address": "t2", "kind": "codex", "session": "def"}
            tabs = [{"terminals": [terminal, codex]}]
            graph.write_text(json.dumps({"spaces": [{"tabs": tabs}]}))
            self.assertEqual(roll.session_of("t1", str(graph)), "abc")
            self.assertIsNone(roll.session_of("t2", str(graph)))
