import subprocess
from pathlib import Path

import pytest

from p2996 import cli, config
from p2996.models import Command, Config

from .conftest import Upstream, executable, git
from .test_install import configure_trees
from .test_review import CODEX
from .test_verify import STAND_IN


def test_every_generated_command_has_a_subcommand_and_a_runner() -> None:
    for command in Command:
        with pytest.raises(SystemExit) as exit_:
            cli.parser().parse_args([command, "--help"])
        assert exit_.value.code == 0
    assert set(cli.RUN) == set(Command)


def test_unknown_command_exits_2() -> None:
    with pytest.raises(SystemExit) as exit_:
        cli.main(["nope"])
    assert exit_.value.code == 2


def test_cli_without_mise_env_names_the_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("REMOTE", "BRANCH", "ROOT", "CACHE", "LOCK"):
        monkeypatch.delenv(f"P2996_{name}", raising=False)
    with pytest.raises(SystemExit, match="P2996_REMOTE"):
        cli.main(["clean"])


def test_source_build_install_verify_through_the_cli(
    env: Config, upstream: Upstream, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    old = git(upstream.path, "rev-parse", "HEAD")
    head = upstream.write("llvm/new.txt", "new\n")
    # The shipped LLVM patches name files the toy upstream lacks: the checkout happens, then the
    # first patch stops the task with its name, as it would after an upstream rewrite.
    with pytest.raises(SystemExit, match=f"asan-macos27-dyld.patch no longer applies to {old}"):
        cli.main(["source", "--commit", old])
    assert config.commit(env) == old
    with pytest.raises(SystemExit, match=f"no longer applies to {head}"):
        cli.main(["source"])
    assert config.commit(env) == head
    cli.main(["build", "--dry-run"])
    cli.main(["build"])
    assert (config.build_dir(env) / "tiny").is_file()
    cli.main(["clean"])  # the install trees below are other CMake projects
    configure_trees(env, tmp_path)
    cli.main(["install"])
    executable(config.prefix(env) / "bin/clang++-p2996", STAND_IN)
    capsys.readouterr()
    # The stand-in compiles with Apple clang, which has no <meta>: the shipped sample must fail there.
    with pytest.raises(subprocess.CalledProcessError):
        cli.main(["verify"])
    assert "Configuration file:" not in capsys.readouterr().out


def test_clean_removes_the_build_and_optionally_the_checkout(env: Config) -> None:
    config.build_dir(env).mkdir(parents=True)
    config.src(env).mkdir(parents=True)
    cli.main(["clean"])
    assert not config.build_dir(env).exists()
    assert config.src(env).exists()
    cli.main(["clean", "--source"])
    assert not config.src(env).exists()


def test_review_log_through_the_cli(env: Config, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable(tmp_path / "fake-bin/codex", CODEX)
    monkeypatch.setenv("PATH", f"{tmp_path / 'fake-bin'}:/usr/bin:/bin")
    log = tmp_path / "build.log"
    log.write_text("")
    cli.main(["review-log", str(log), "--out", str(tmp_path / "r.md")])
    assert f"- LLVM source checkout: {config.src(env)}" in (tmp_path / "r.md").read_text()
