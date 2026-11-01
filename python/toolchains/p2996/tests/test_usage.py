"""The mise task usage specs and the generated CLI models stay in step (DL-762)."""

# For every command: build an argv that sets every flag and arg of its task's usage spec, let the
# real usage CLI bind it (the usage_* variables mise exports), expand the task's real run line with
# bash, and parse what reaches p2996 with the real CLI parser. A spec flag the model lacks, a model
# field the spec lacks, or a run line that drops a variable fails here.

import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from p2996 import cli, config
from p2996.models import Command, Config

from .conftest import Upstream, git

TASKS = tomllib.loads((config.PROJECT / "mise.toml").read_text())["tasks"]

# A value the model accepts for a flag that has a pattern; every other flag takes sample-<name>.
SAMPLES = {"commit": "0" * 40}

# uv run --locked p2996 <argv>: drop "run --locked", then print the argv p2996 would get.
SHIMS = 'uv() { shift 2; "$@"; }; p2996() { printf "%s\\0" "$@"; }; '


def spec(command: Command) -> dict:
    """The usage spec as mise parses it from the task (args and flags with their names)."""
    info = subprocess.run(
        ["mise", "tasks", "info", f"//p2996:{command}", "--json"],
        cwd=config.PROJECT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(info.stdout)["usage_spec"]["cmd"]


def sample(command: Command) -> list[str]:
    cmd = spec(command)
    argv = [f"sample-{arg['name']}" for arg in cmd["args"]]
    for flag in cmd["flags"]:
        name = flag["name"]
        argv += [f"--{name}", SAMPLES.get(name, f"sample-{name}")] if "<" in flag["usage"] else [f"--{name}"]
    return argv


def bind(command: Command, argv: list[str]) -> dict[str, str]:
    """What usage binds argv to, as the usage_<name> variables a task sees."""
    explained = subprocess.run(
        ["usage", "explain", "--format", "json", "-s", TASKS[command].get("usage", ""), command, *argv],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(explained.stdout)
    assert report["errors"] == [], report["errors"]
    return {value["name"]: value["value"] for value in report["values"]}


def expand(command: Command, values: dict[str, str]) -> list[str]:
    env = {f"usage_{name.replace('-', '_')}": value for name, value in values.items()}
    done = subprocess.run(
        ["/bin/bash", "-c", SHIMS + TASKS[command]["run"]], env=env, check=True, capture_output=True, text=True
    )
    return done.stdout.split("\0")[:-1]


@pytest.mark.parametrize("command", list(Command))
def test_every_spec_value_reaches_the_model(command: Command) -> None:
    values = bind(command, sample(command))
    parsed_command, model = cli.parse(expand(command, values))
    assert parsed_command == command
    fields = model.model_dump()
    assert set(fields) == {name.replace("-", "_") for name in values}
    for name, value in values.items():
        got = fields[name.replace("-", "_")]
        assert got is True if value == "true" else str(got) == value, (name, got, value)


@pytest.mark.parametrize("command", list(Command))
def test_only_the_required_args_parse_to_the_defaults(command: Command) -> None:
    argv = [f"sample-{arg['name']}" for arg in spec(command)["args"]]
    _, model = cli.parse(expand(command, bind(command, argv)))
    model_cls = type(model)
    for name, field in model_cls.model_fields.items():
        if not field.is_required():
            assert getattr(model, name) == field.default, name


def project_copy(top: Path, cfg: Config) -> Path:
    """This project with the toy recipe's values: mise.toml's [env] wins over what a caller exports."""
    copy = top / "project"
    junk = shutil.ignore_patterns(".venv", ".*_cache", "__pycache__", "*.patch")
    shutil.copytree(config.PROJECT, copy, ignore=junk)
    values = {f"P2996_{name.upper()}": value for name, value in cfg.model_dump().items()}
    values |= {name: os.environ[name] for name in ("SCCACHE_DIR", "SCCACHE_IDLE_TIMEOUT")}
    lines = (copy / "mise.toml").read_text().splitlines()
    for at, line in enumerate(lines):
        name = line.partition(" = ")[0]
        if name in values:
            lines[at] = f'{name} = "{values[name]}"'
    (copy / "mise.toml").write_text("\n".join(lines) + "\n")
    return copy


def test_a_pinned_build_task_prepares_and_builds_that_commit(cfg: Config, upstream: Upstream, tmp_path: Path) -> None:
    pinned = upstream.release("v1")
    upstream.release("v2")  # The branch has moved on, so anything that ignores --commit gets this one.
    done = subprocess.run(
        ["mise", "run", "--raw", "build", "--commit", pinned],
        cwd=project_copy(tmp_path, cfg),
        env=os.environ | {"MISE_TRUSTED_CONFIG_PATHS": str(tmp_path)},
        check=True,
        capture_output=True,
        text=True,
    )
    events = [json.loads(line) for line in done.stdout.splitlines() if line.startswith("{")]
    # Only the pinned commit is ever prepared: a task dependency would fetch the branch tip first.
    [ready] = [event for event in events if event["event"] == "source ready"]
    [built] = [event for event in events if event["event"] == "build done"]
    assert (ready["commit"], built["commit"]) == (pinned, pinned)
    assert git(Path(ready["checkout"]), "rev-parse", "HEAD") == pinned
