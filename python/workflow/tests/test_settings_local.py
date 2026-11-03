"""workflowtools settings-local, in a main checkout and a linked worktree."""

import subprocess
from pathlib import Path

import pytest

from .conftest import add, report, write

LOCAL = ".claude/settings.local.json"
MOVE = f"move its rules to .claude/settings.json, then delete {LOCAL}"


def test_a_clean_checkout_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {".claude/settings.json": "{}"})
    assert report(capsys, "settings-local") == [{"exit": "0"}]


def test_a_file_in_the_main_checkout_is_reported_once(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo, {LOCAL: "{}"})
    assert report(capsys, "settings-local") == [
        {"path": str((repo / LOCAL).resolve()), "check": "settings-local", "detail": f"exists; {MOVE}"},
        {"exit": "1"},
    ]


def test_a_tracked_file_is_reported_twice(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {LOCAL: "{}"})
    assert report(capsys, "settings-local")[1:] == [
        {"path": LOCAL, "check": "settings-local", "detail": f"is in the index; {MOVE}"},
        {"exit": "1"},
    ]


def test_a_linked_worktree_sees_both_files(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    add(repo, {"a": "a"})
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "a"], check=True)
    linked = repo.parent / "linked"
    subprocess.run(["git", "-C", repo, "worktree", "add", "-q", linked], check=True)
    write(repo, {LOCAL: "{}"})
    write(linked, {LOCAL: "{}"})
    monkeypatch.chdir(linked)
    assert [line.get("path") for line in report(capsys, "settings-local")] == [
        str((linked / LOCAL).resolve()),
        str((repo / LOCAL).resolve()),
        None,
    ]
