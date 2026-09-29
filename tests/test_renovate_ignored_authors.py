# Copyright (c) 2026 Raymond Manaloto
"""Renovate must not freeze on our own repair bots' commits (#1435, option B-prime).

`gcc-sha-repair` and `image-lock-pr` commit onto Renovate branches. An author
Renovate does not recognise marks the branch MODIFIED and Renovate stops
updating it for good — that froze #947 and #1063. Both bot addresses are in
`gitIgnoredAuthors`; `rebaseWhen` is pinned to `conflicted` locally so the
rebase frequency does not silently depend on the extended preset. The list
replaces (does not merge with) the preset's, so github-actions is re-listed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
_SLUG = "dotfiles-refresh-bot-org"
_BOT_ID = "298071151"
_ADDRESS_TEMPLATES = {
    # workflow -> the email template its "Configure git identity" writes
    "gcc-sha-repair.yml": 'user.email "${APP_SLUG}[bot]@users.noreply.github.com"',
    "refresh.yml": 'user.email "${BOT_ID}+${APP_SLUG}[bot]@users.noreply.github.com"',
}


def _config() -> dict:
    return json.loads((REPO_ROOT / "renovate.json").read_text())


def _render(template: str) -> str:
    """Expand a workflow's identity template with the App's real slug and id."""
    address = re.search(r'"(?P<email>[^"]+)"', template)
    assert address is not None
    return (
        address.group("email")
        .replace("${APP_SLUG}", _SLUG)
        .replace("${BOT_ID}", _BOT_ID)
    )


def test_rebase_when_is_pinned_locally() -> None:
    assert _config()["rebaseWhen"] == "conflicted"


def test_every_repair_bot_identity_is_an_ignored_author() -> None:
    ignored = _config()["gitIgnoredAuthors"]
    for workflow, template in _ADDRESS_TEMPLATES.items():
        text = (REPO_ROOT / ".github" / "workflows" / workflow).read_text()
        # If a workflow changes the identity it commits as, this fails here
        # rather than silently re-freezing Renovate on the new address.
        assert template in text, workflow
        assert _render(template) in ignored, workflow


def test_preset_github_actions_address_is_relisted() -> None:
    """The `gitIgnoredAuthors` list REPLACES the preset's rather than merging it."""
    assert (
        "41898282+github-actions[bot]@users.noreply.github.com"
        in _config()["gitIgnoredAuthors"]
    )


def test_render_distinguishes_the_two_identity_shapes() -> None:
    """Control arm: the two templates render to DIFFERENT addresses."""
    rendered = {_render(t) for t in _ADDRESS_TEMPLATES.values()}
    assert rendered == {
        f"{_SLUG}[bot]@users.noreply.github.com",
        f"{_BOT_ID}+{_SLUG}[bot]@users.noreply.github.com",
    }
