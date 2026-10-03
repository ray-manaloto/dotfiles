# Copyright (c) 2026 Raymond Manaloto
"""Upsert one exact-title standing issue through the native gh CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


def default_runner(argv: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a bounded gh operation with argv, preserving its exit code."""
    return subprocess.run(
        argv, capture_output=True, text=True, check=False, timeout=120
    )


def standing_issue_main(
    *,
    repo: str,
    title: str,
    body_file: Path | None = None,
    close_comment: str | None = None,
    runner: Runner = default_runner,
) -> int:
    """Edit/create an exact-title open issue, or close it if it exists."""
    if (body_file is None) == (close_comment is None):
        sys.stderr.write("Use --body-file or --close with --close-comment\n")
        return 1
    try:
        result = runner(
            [
                "gh",
                "issue",
                "list",
                "--repo",
                repo,
                "--state",
                "open",
                "--search",
                f'in:title "{title}"',
                "--json",
                "number,title",
            ]
        )
        if result.returncode:
            sys.stderr.write(result.stderr)
            return result.returncode
        issues = json.loads(result.stdout)
        number = next(
            (str(issue["number"]) for issue in issues if issue["title"] == title), None
        )
        if body_file is None:
            if number is None:
                return 0
            argv = [
                "gh",
                "issue",
                "close",
                number,
                "--repo",
                repo,
                "--comment",
                str(close_comment),
            ]
        elif number is not None:
            argv = [
                "gh",
                "issue",
                "edit",
                number,
                "--repo",
                repo,
                "--body-file",
                str(body_file),
            ]
        else:
            argv = [
                "gh",
                "issue",
                "create",
                "--repo",
                repo,
                "--title",
                title,
                "--body-file",
                str(body_file),
                "--label",
                "dependencies,needs-triage",
            ]
        result = runner(argv)
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as exc:
        sys.stderr.write(f"Standing issue failed: {exc}\n")
        return 1
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode
