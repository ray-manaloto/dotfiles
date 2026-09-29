# Copyright (c) 2026 Raymond Manaloto
"""Renovate must not freeze on our own bots' commits (#1435, option B-prime).

A commit on a Renovate branch whose author Renovate does not recognise marks
the branch MODIFIED, and Renovate then stops updating it for good — that froze
#947 and #1063. Every git identity a workflow commits under must therefore be
in `gitIgnoredAuthors` (the list REPLACES the preset's, so github-actions is
re-listed), and `rebaseWhen` is pinned to `conflicted` locally, including the
`pin` update type whose own default is `behind-base-branch`.

What this can and cannot check offline: it enumerates every identity set by
`git config [--global|--local] user.email`, `git -c user.email=` or
`GIT_{AUTHOR,COMMITTER}_EMAIL` in the workflows and composite actions (no
hand-kept list), and FAILS on such a line it cannot parse (e.g. a `$VAR`).
Identities passed as action inputs (`committer:`/`author:`) are out of reach.
It expands the App placeholders with `_SLUG` / `_BOT_ID`; those two are
constants verified live when written (`gh api /users/<slug>[bot]` ->
298071151, 2026-09-29); an App rename or reinstall is NOT visible offline, which
is why the refresh.yml identity comment says to update renovate.json with it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
_SLUG = "dotfiles-refresh-bot-org"
_BOT_ID = "298071151"
_EMAIL = re.compile(
    r"""^(?!\s*#).*?(?:git\s+config\s+(?:--(?:global|local)\s+)?user\.email|"""
    r"""-c\s+user\.email=|GIT_(?:AUTHOR|COMMITTER)_EMAIL\s*[:=])"""
    r"""\s*"?(?P<email>[^"\s]+@[^"\s]+)"?""",
    re.MULTILINE,
)
# Any non-comment line that SETS an identity by one of these spellings. A line
# matching this but not `_EMAIL` (e.g. `user.email "$EMAIL"`) is unparsable
# here and FAILS the gate rather than being skipped.
_IDENTITY_LINE = re.compile(
    r"^(?!\s*#).*(?:user\.email|GIT_(?:AUTHOR|COMMITTER)_EMAIL).*$", re.MULTILINE
)


def _config() -> dict:
    return json.loads((REPO_ROOT / "renovate.json").read_text())


def _identities(text: str) -> list[str]:
    """Every commit email a workflow text sets, placeholders expanded."""
    return [
        match.group("email").replace("${APP_SLUG}", _SLUG).replace("${BOT_ID}", _BOT_ID)
        for match in _EMAIL.finditer(text)
    ]


def _workflow_texts() -> dict[str, str]:
    github = REPO_ROOT / ".github"
    paths = [
        *github.glob("workflows/*.y*ml"),
        *github.glob("actions/*/action.y*ml"),
    ]
    return {str(path.relative_to(REPO_ROOT)): path.read_text() for path in paths}


def test_rebase_when_is_pinned_locally_including_pin_updates() -> None:
    config = _config()
    assert config["rebaseWhen"] == "conflicted"
    assert config["pin"]["rebaseWhen"] == "conflicted"


def test_every_workflow_commit_identity_is_an_ignored_author() -> None:
    ignored = set(_config()["gitIgnoredAuthors"])
    found = {
        (path, email)
        for path, text in _workflow_texts().items()
        for email in _identities(text)
    }
    # Both repair bots and the github-actions committers are really present;
    # an empty scan would make the next assertion vacuous.
    assert {email for _, email in found} >= {
        f"{_SLUG}[bot]@users.noreply.github.com",
        f"{_BOT_ID}+{_SLUG}[bot]@users.noreply.github.com",
        "41898282+github-actions[bot]@users.noreply.github.com",
    }
    assert {(path, email) for path, email in found if email not in ignored} == set()


def test_no_identity_line_escapes_the_parser() -> None:
    """Fail closed: an identity line the scan cannot read is a finding, not a skip."""
    unparsed = [
        (path, line.strip())
        for path, text in _workflow_texts().items()
        for line in _IDENTITY_LINE.findall(text)
        if not _EMAIL.search(line)
    ]
    assert unparsed == []


def test_identity_scan_catches_every_spelling() -> None:
    """Control arm: a NEW or overriding identity must be found, comments not."""
    text = (
        '          git config user.email "${APP_SLUG}[bot]@users.noreply.github.com"\n'
        '          git config --global user.email "new-bot[bot]@example.com"\n'
        "          GIT_COMMITTER_EMAIL: other[bot]@example.com\n"
        "          git -c user.email=inline[bot]@example.com commit -m x\n"
        '          git config --local user.email "local[bot]@example.com"\n'
        '          # git config user.email "commented@example.com"\n'
    )
    assert _identities(text) == [
        f"{_SLUG}[bot]@users.noreply.github.com",
        "new-bot[bot]@example.com",
        "other[bot]@example.com",
        "inline[bot]@example.com",
        "local[bot]@example.com",
    ]
    variable = '          git config user.email "$EMAIL"\n'
    assert _identities(variable) == []
    assert _IDENTITY_LINE.findall(variable)  # ...so the fail-closed test sees it
