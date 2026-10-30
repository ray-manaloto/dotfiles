from pathlib import Path

import pytest

from p2996 import cli, config
from p2996.models import Build, Command, Config, ReviewLog

from .conftest import Upstream, events, executable, git
from .test_install import configure_trees
from .test_review import CODEX
from .test_verify import STAND_IN


def fails(argv: list[str], logs: pytest.CaptureFixture[str]) -> dict:
    """Run the CLI, expect exit 1, and return its one error event."""
    with pytest.raises(SystemExit) as exit_:
        cli.main(argv)
    assert exit_.value.code == 1
    out, [error] = events(logs)
    assert error["level"] == "error"
    assert all(e["level"] == "info" for e in out)
    return error


def test_every_generated_command_has_a_model_runner_and_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert set(cli.COMMANDS) == set(Command)
    for command in Command:
        with pytest.raises(SystemExit) as exit_:
            cli.parse([command, "--help"])
        assert exit_.value.code == 0
        assert f"usage: p2996 {command}" in capsys.readouterr().out


def test_parse_returns_the_generated_model() -> None:
    assert cli.parse(["build", "--dry-run"]) == (Command.build, Build(dry_run=True))
    assert cli.parse(["review-log", "--log", "b.log"]) == (Command.review_log, ReviewLog(log=Path("b.log")))


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["nope"], "the first argument is one of source, build, install, verify, clean, review-log"),
        ([], "the first argument is one of"),
        (["build", "--nope"], "unrecognized arguments: --nope"),
        (["build", "--dry-run", "yes"], "unrecognized arguments: yes"),
        (["review-log"], "log\n  Field required"),
    ],
)
def test_bad_arguments_log_one_error_and_exit_1(
    argv: list[str], message: str, logs: pytest.CaptureFixture[str]
) -> None:
    assert message in fails(argv, logs)["event"]


def test_cli_without_mise_env_names_the_variables(
    monkeypatch: pytest.MonkeyPatch, logs: pytest.CaptureFixture[str]
) -> None:
    for name in ("REMOTE", "BRANCH", "ROOT", "CACHE", "LOCK"):
        monkeypatch.delenv(f"P2996_{name}", raising=False)
    assert "P2996_REMOTE" in fails(["clean"], logs)["event"]


def test_source_build_install_verify_through_the_cli(
    env: Config, upstream: Upstream, tmp_path: Path, logs: pytest.CaptureFixture[str]
) -> None:
    old = git(upstream.path, "rev-parse", "HEAD")
    head = upstream.write("llvm/new.txt", "new\n")
    # The shipped LLVM patches name files the toy upstream lacks: the checkout happens, then the
    # first patch stops the task with its name, as it would after an upstream rewrite.
    assert f"asan-macos27-dyld.patch no longer applies to {old}" in fails(["source", "--commit", old], logs)["event"]
    assert git(config.src(env), "rev-parse", "HEAD") == old
    assert f"no longer applies to {head}" in fails(["source"], logs)["event"]
    assert git(config.src(env), "rev-parse", "HEAD") == head
    cli.main(["build", "--dry-run"])
    cli.main(["build"])
    assert (config.build_dir(env) / "tiny").is_file()
    cli.main(["clean"])  # the install trees below are other CMake projects
    configure_trees(env, tmp_path)
    cli.main(["install"])
    executable(env.root / head / "bin/clang++-p2996", STAND_IN)
    logs.readouterr()
    # The stand-in compiles with Apple clang, which has no <meta>: the compile step fails, and the
    # error event carries the command, its exit code and clang's stderr.
    error = fails(["verify"], logs)
    assert error["event"] == "command failed"
    assert error["command"][0] == str(config.bin_dir(env) / "clang++-p2996")
    assert error["code"] == 1
    assert "'meta' file not found" in error["stderr"]


def test_clean_removes_the_build_and_optionally_the_checkout(env: Config, logs: pytest.CaptureFixture[str]) -> None:
    config.build_dir(env).mkdir(parents=True)
    config.src(env).mkdir(parents=True)
    cli.main(["clean"])
    assert not config.build_dir(env).exists()
    assert config.src(env).exists()
    cli.main(["clean", "--source"])
    assert not config.src(env).exists()
    assert [e["path"] for e in events(logs)[0]] == [str(config.build_dir(env))] * 2 + [str(config.src(env))]


def test_review_log_through_the_cli(env: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable(tmp_path / "fake-bin/codex", CODEX)
    monkeypatch.setenv("PATH", f"{tmp_path / 'fake-bin'}:/usr/bin:/bin")
    log = tmp_path / "build.log"
    log.write_text("")
    cli.main(["review-log", "--log", str(log), "--out", str(tmp_path / "r.md")])
    assert f"- LLVM source checkout: {config.src(env)}" in (tmp_path / "r.md").read_text()
