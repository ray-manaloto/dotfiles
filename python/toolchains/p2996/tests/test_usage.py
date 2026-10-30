"""The mise task usage specs and the generated CLI models stay in step (DL-762)."""

# For every command: build an argv that sets every flag and arg of its task's usage spec, let the
# real usage CLI bind it (the usage_* variables mise exports), expand the task's real run line with
# bash, and parse what reaches p2996 with the real CLI parser. A spec flag the model lacks, a model
# field the spec lacks, or a run line that drops a variable fails here.

import json
import subprocess
import tomllib

import pytest

from p2996 import cli, config
from p2996.models import Command

TASKS = tomllib.loads((config.PROJECT / "mise.toml").read_text())["tasks"]

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
        argv += [f"--{flag['name']}", f"sample-{flag['name']}"] if "<" in flag["usage"] else [f"--{flag['name']}"]
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
