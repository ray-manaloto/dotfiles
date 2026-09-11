# Copyright (c) 2026 Raymond Manaloto
"""Shared pytest configuration: the `host_only` CI skip and the composite's commands.

`host_only` marks the handful of tests asserting facts about a real
developer host — a host-installed CLI (`claude`, `gemini`) or a
chezmoi-applied `~/.zshenv` under zsh. No amount of `mise install` on a
runner makes them pass, so they are skipped there and ONLY there; on the
Mac host (and under `mise run ship`) they run normally.

Why a hook and not `-m "not host_only"` in the CI step: `pytest.ini`'s
`addopts` already carries `-m "not image_exec and not codex_exec"`, and a
command-line `-m` REPLACES it rather than anding with it (last one wins).
A CI `-m` would therefore have to restate the whole expression, and would
silently re-enable the credit-spending `codex_exec` tests the day someone
adds a marker and forgets. This cannot drift.
"""

import os
from pathlib import Path

import pytest
import yaml


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip `host_only` tests when running on a CI runner ($CI is set)."""
    # `== "true"`, matching rule_sync.py:223 rather than plain truthiness:
    # a stray `CI=false` must not silently skip these — a quiet loss of
    # coverage is the #808 failure mode itself. GitHub Actions sets
    # `CI=true`.
    if os.environ.get("CI") != "true":
        return
    skip = pytest.mark.skip(
        reason="host_only: needs a real developer host, not a CI runner"
    )
    for item in items:
        if "host_only" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def lock_refresh_commands() -> str:
    """Every shell command the lock-refresh composite actually runs.

    Parsed out of the YAML rather than grepped out of the file, so a comment
    can never satisfy an assertion about a command. That distinction is
    load-bearing and was mutation-proven by the fixture this replaces: the
    composite names its flags in prose directly above the step, so a
    whole-file substring check passes with the flag deleted from the command.
    Joining only the `run:` values keeps that property structurally, without
    a hand-rolled comment stripper.
    """
    action = (
        Path(__file__).parent.parent
        / ".github"
        / "actions"
        / "lock-refresh"
        / "action.yml"
    ).read_text()
    steps = yaml.safe_load(action)["runs"]["steps"]
    return "\n".join(step.get("run", "") for step in steps)
