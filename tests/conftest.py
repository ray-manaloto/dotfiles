# Copyright (c) 2026 Raymond Manaloto
"""Shared pytest configuration: the `host_only` CI skip and the composite's commands.

`host_only` marks the handful of tests asserting facts about a real
developer host — a host-installed CLI (`claude`, `codex`, `gemini`) or a
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

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import session_ledger

_REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def isolated_git_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep tests independent of the developer's global and system Git config.

    A machine-level hook (hk v2's recommended `hk install --global` writes
    `hook.hk-*` into `~/.gitconfig`) otherwise runs inside every throwaway repo.
    The file is a SIBLING of `tmp_path`, like `isolated_mise_state`'s dir, so
    tests that assert a tmp dir's exact contents are unaffected.

    It carries the ONE scoped `safe.directory` entry the chezmoi-managed global
    gitconfig renders for this checkout (#1183, `home/dot_gitconfig.tmpl`):
    replacing the global file without it re-opens `dubious ownership` for every
    test that runs git against the real repo under the devcontainer's virtiofs
    uid-0 flicker (smoke tier 2 runs this suite in-container).
    """
    gitconfig = tmp_path.parent / f"{tmp_path.name}.gitconfig"
    gitconfig.write_text(
        "[user]\n\tname = T\n\temail = t@example.com\n"
        f"[safe]\n\tdirectory = {_REPO_ROOT}\n"
    )
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


@pytest.fixture(autouse=True)
def isolated_host_locks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Give every test its own host-lock directory (``host_lock.LOCK_DIR_ENV``).

    The heavy-gate lock is HOST-wide by design, and the suite itself runs under
    it (the pre-push ``test-hook-isolated`` task holds it). A test that drives
    ``run_gate``/``ship_main`` against the real path would therefore wait on
    the very run executing it — and parallel workers would wait on each other.
    The inherited holder variables are dropped too, so a test never "re-enters"
    a lock its own runner holds. A sibling of ``tmp_path``, like the dirs above.
    """
    lock_dir = tmp_path.parent / f"{tmp_path.name}.locks"
    monkeypatch.setenv("DOTFILES_LOCK_DIR", str(lock_dir))
    for name in list(os.environ):
        if name.startswith("DOTFILES_LOCK_HOLDER_"):
            monkeypatch.delenv(name)
    return lock_dir


def _ambient_mise_state_dir() -> Path:
    """The state dir mise would use without the fixture (its documented order)."""
    if explicit := os.environ.get("MISE_STATE_DIR"):
        return Path(explicit)
    xdg = os.environ.get("XDG_STATE_HOME")
    return (Path(xdg) if xdg else Path.home() / ".local" / "state") / "mise"


#: Workers for `-n auto` when PYTEST_XDIST_AUTO_NUM_WORKERS is unset: a cap
#: for a SHARED host (xdist's own default is every core — 12 here — and two
#: concurrent suites at that width drove the load average past 100).
DEFAULT_TEST_WORKERS = 4


@pytest.hookimpl(optionalhook=True)
def pytest_xdist_auto_num_workers(config: pytest.Config) -> int | None:
    """`-n auto` -> DEFAULT_TEST_WORKERS, unless the native knob is set.

    Returning None when PYTEST_XDIST_AUTO_NUM_WORKERS is set hands the answer
    to xdist's own implementation, which reads that variable — so there is one
    knob, and it is xdist's.
    """
    _ = config
    if os.environ.get("PYTEST_XDIST_AUTO_NUM_WORKERS"):
        return None
    return DEFAULT_TEST_WORKERS


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


@pytest.fixture
def digest_fixture(
    tmp_path: Path,
) -> tuple[tuple[Path, Path], session_ledger.TranscriptBases, str]:
    """Native-shaped roots in isolated repositories, worktrees and provider stores."""
    secret = "planted-credential-" + uuid.uuid4().hex
    roots = (tmp_path / "dotfiles", tmp_path / "knowledge-base")
    unrelated = tmp_path / "unrelated"
    git_env = {
        **os.environ,
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }
    for root in (*roots, unrelated):
        root.mkdir()
        subprocess.run(
            ["git", "-c", "init.defaultBranch=main", "init", str(root)],
            check=True,
            capture_output=True,
            env=git_env,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "-c",
                "core.hooksPath=/dev/null",
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "--allow-empty",
                "-m",
                "fixture",
            ],
            check=True,
            capture_output=True,
            env=git_env,
        )
    worktree = tmp_path / "dotfiles-worktree"
    subprocess.run(
        [
            "git",
            "-C",
            str(roots[0]),
            "-c",
            "core.hooksPath=/dev/null",
            "worktree",
            "add",
            "-b",
            "fixture-lane",
            str(worktree),
        ],
        check=True,
        capture_output=True,
        env=git_env,
    )
    codex_base = tmp_path / "codex"
    claude_base = tmp_path / "claude"
    bases = session_ledger.TranscriptBases(codex=codex_base, claude=claude_base)
    codex_base.mkdir()
    claude_base.mkdir()
    after = "2026-10-02T06:00:00Z"
    before = "2026-10-02T04:59:59Z"

    def write(
        provider: str,
        cwd: Path,
        name: str,
        entries: list[tuple[str, str, str]],
        *,
        parent: str = "",
    ) -> None:
        records = []
        if provider == "codex":
            records.append(
                {
                    "type": "session_meta",
                    "payload": {
                        "id": name,
                        "cwd": str(cwd),
                        "cli_version": "0.160.0",
                        "parent_thread_id": parent,
                    },
                }
            )
            path = codex_base / (name + ".jsonl")
        else:
            project = claude_base / session_ledger.command_audit.encode_cwd(cwd)
            path = project / (
                "claude-root/subagents/" + name + ".jsonl"
                if parent
                else name + ".jsonl"
            )
        for number, (command, timestamp, outcome) in enumerate(entries):
            call_id = name + str(number)
            if provider == "codex":
                records.append(
                    {
                        "timestamp": timestamp,
                        "type": "response_item",
                        "payload": {
                            "type": "function_call",
                            "name": "functions.exec_command",
                            "call_id": call_id,
                            "arguments": json.dumps(
                                {"cmd": command, "nested": {"token": secret}}
                            ),
                        },
                    }
                )
                result = (
                    "approval policy is Never; reject command — you cannot ask "
                    "for escalated permissions if the approval policy is Never"
                    if outcome == "refused"
                    else json.dumps(
                        {"wall_time_seconds": 0.1, "exit_code": 0, "output": secret}
                    )
                )
                records.append(
                    {
                        "timestamp": timestamp,
                        "type": "response_item",
                        "payload": {
                            "type": "function_call_output",
                            "call_id": call_id,
                            "output": result,
                        },
                    }
                )
            else:
                records.append(
                    {
                        "type": "assistant",
                        "sessionId": name,
                        "cwd": str(cwd),
                        "timestamp": timestamp,
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": call_id,
                                    "name": "Bash",
                                    "input": {
                                        "command": command,
                                        "nested": {"token": secret},
                                    },
                                }
                            ]
                        },
                    }
                )
                records.append(
                    {
                        "type": "user",
                        "sessionId": name,
                        "timestamp": timestamp,
                        "toolUseResult": "Permission to use Bash denied"
                        if outcome == "refused"
                        else {"stdout": secret},
                        "message": {
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": call_id,
                                    "is_error": outcome == "refused",
                                    "content": secret,
                                }
                            ]
                        },
                    }
                )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(row) + "\n" for row in records))

    hit = (
        "git gc --prune="
        + secret
        + " https://user:"
        + secret
        + "@example.invalid/?token="
        + secret
    )
    for provider in ("claude", "codex"):
        write(
            provider,
            roots[0],
            provider + "-root",
            [
                (hit, after, "executed"),
                (hit, after, "refused"),
                ("git fetch", before, "executed"),
            ],
        )
        write(provider, roots[1], provider + "-kb", [(hit, after, "executed")])
        write(
            provider,
            roots[0],
            provider + "-child",
            [(hit, after, "executed")],
            parent=provider + "-root",
        )
        write(
            provider,
            worktree,
            provider + "-worktree",
            [("git commit -m " + secret, after, "executed")],
        )
        write(
            provider,
            unrelated,
            provider + "-unrelated",
            [("git push", after, "executed")],
        )
    return roots, bases, secret
