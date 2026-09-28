# Copyright (c) 2026 Raymond Manaloto
"""The persistence gate's tool-set key (#1172), run through real jq.

The key lives in `mise.toml [tasks.persistence]` as `PARITY_KEY=...`; these
tests extract THAT string, so they bind the shipped gate rather than a copy of
it. jq is pinned in `.config/mise/conf.d/shared.toml`, so it exists wherever
this suite runs.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent


def _parity_key() -> str:
    text = (REPO_ROOT / "mise.toml").read_text()
    matches = re.findall(r"^PARITY_KEY='(.*)'$", text, flags=re.MULTILINE)
    assert len(matches) == 1, "exactly one PARITY_KEY assignment in mise.toml"
    return matches[0]


def _keys(snapshot: dict[str, list[dict[str, object]]]) -> set[str]:
    jq = shutil.which("jq")
    assert jq is not None, "jq is pinned in shared.toml and must be on PATH"
    proc = subprocess.run(
        [jq, "-r", _parity_key()],
        input=json.dumps(snapshot),
        capture_output=True,
        text=True,
        check=True,
    )
    return set(proc.stdout.splitlines())


def _row(version: str, requested: str | None, *, active: bool) -> dict[str, object]:
    return {"version": version, "requested_version": requested, "active": active}


_BEFORE = {
    "ripgrep": [_row("15.1.0", "latest", active=True)],
    "actionlint": [_row("1.7.7", "1.7.7", active=True)],
}


@pytest.mark.parametrize(
    "after",
    [
        pytest.param(
            {
                "ripgrep": [
                    _row("15.2.0", "latest", active=True),
                    _row("15.1.0", None, active=False),  # the bump's leftover
                ],
                "actionlint": [_row("1.7.7", "1.7.7", active=True)],
            },
            id="latest-bump-leaves-inactive-old-version",
        ),
        pytest.param(
            {
                "ripgrep": [_row("15.1.0", "latest", active=True)],
                "actionlint": [
                    _row("1.7.7", "1.7.7", active=True),
                    _row("1.7.6", None, active=False),
                ],
            },
            id="inactive-leftover-alone",
        ),
    ],
)
def test_currency_motion_is_not_persistence_loss(
    after: dict[str, list[dict[str, object]]],
) -> None:
    assert _keys(after) == _keys(_BEFORE)


def test_latest_switching_between_installed_versions_passes() -> None:
    before = {
        "ripgrep": [
            _row("15.1.0", "latest", active=True),
            _row("15.2.0", None, active=False),
        ]
    }
    after = {
        "ripgrep": [
            _row("15.2.0", "latest", active=True),
            _row("15.1.0", None, active=False),
        ]
    }
    assert _keys(after) == _keys(before)


@pytest.mark.parametrize(
    "after",
    [
        pytest.param(
            {"actionlint": [_row("1.7.7", "1.7.7", active=True)]},
            id="latest-tool-vanished",
        ),
        pytest.param(
            {
                "ripgrep": [_row("15.1.0", "latest", active=True)],
                "actionlint": [_row("1.7.8", "1.7.7", active=True)],
            },
            id="exact-pin-version-changed",
        ),
    ],
)
def test_real_loss_still_fails(after: dict[str, list[dict[str, object]]]) -> None:
    assert _keys(after) != _keys(_BEFORE)
