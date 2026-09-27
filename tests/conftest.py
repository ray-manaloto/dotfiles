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


@pytest.fixture(autouse=True)
def isolated_git_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep tests independent of the developer's global and system Git config.

    A machine-level hook (hk v2's recommended `hk install --global` writes
    `hook.hk-*` into `~/.gitconfig`) otherwise runs inside every throwaway repo.
    The file is a SIBLING of `tmp_path`, like `isolated_mise_state`'s dir, so
    tests that assert a tmp dir's exact contents are unaffected.
    """
    gitconfig = tmp_path.parent / f"{tmp_path.name}.gitconfig"
    gitconfig.write_text("[user]\n\tname = T\n\temail = t@example.com\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gitconfig))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    return gitconfig


@pytest.fixture(autouse=True)
def isolated_mise_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep every test's mise registry in its own disposable state directory.

    Without this, a test that runs the real `mise` against a throwaway
    `mise.toml` registers it in the HOST's `tracked-configs`, and every later
    host `mise` command re-parses it (#1169/#1248). Same fixture as
    knowledge-base#818 + #819 (the trust-store share).

    The directory is a SIBLING of `tmp_path`, not inside it: `git` resolves
    through a mise shim here, so any Git call creates the state dir, and inside
    `tmp_path` it would read as drift in tests that prove a tmp dir is empty or
    a fixture repo is clean.
    """
    ambient = _ambient_mise_state_dir()
    state_dir = tmp_path.parent / f"{tmp_path.name}.mise-state"
    state_dir.mkdir(exist_ok=True)
    # MISE_STATE_DIR moves TRUST records too. A host that trusts this checkout
    # via `mise trust` (rather than a global `trusted_config_paths`) would lose
    # that trust inside every test, and `mise env`/`mise run` would refuse the
    # repo config. Share the ambient trust store; isolate only tracking.
    ambient_trust = ambient / "trusted-configs"
    if ambient_trust.is_dir():
        (state_dir / "trusted-configs").symlink_to(ambient_trust)
    monkeypatch.setenv("MISE_STATE_DIR", str(state_dir))
    return state_dir


def _ambient_mise_state_dir() -> Path:
    """The state dir mise would use without the fixture (its documented order)."""
    if explicit := os.environ.get("MISE_STATE_DIR"):
        return Path(explicit)
    xdg = os.environ.get("XDG_STATE_HOME")
    return (Path(xdg) if xdg else Path.home() / ".local" / "state") / "mise"


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
