import os
import subprocess
from pathlib import Path

import pytest

from p2996 import config, review
from p2996.models import Config, ReviewLog

from .conftest import Recipe, Upstream, executable

pytestmark = pytest.mark.anyio

# Stands in for codex: refuses anything but a read-only exec and writes the prompt it got as the report.
CODEX = """\
import sys
args = sys.argv[1:]
assert args[:2] == ["exec", "-C"], args
assert args[3:5] == ["-c", 'sandbox_mode="read-only"'], args
assert args[-1] == "-" and not {"-s", "--ephemeral", "--dangerously-bypass-hook-trust"} & set(args), args
out = args[args.index("-o") + 1]
open(out, "w").write(f"cwd {args[2]}\\n" + sys.stdin.read())
"""


@pytest.fixture
def codex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable(tmp_path / "fake-bin/codex", CODEX)
    monkeypatch.setenv("PATH", f"{tmp_path / 'fake-bin'}:{Path('/usr/bin')}:{Path('/bin')}")


@pytest.mark.usefixtures("codex")
async def test_review_fills_the_prompt_and_writes_beside_the_log(cfg: Config, tmp_path: Path) -> None:
    log = tmp_path / "logs/build.log"
    log.parent.mkdir()
    log.write_text("CMake Warning: x\n")
    config.build_dir(cfg).mkdir(parents=True)
    config.link(config.started_build(cfg), "abc")
    await review.run(cfg, ReviewLog(log=log))
    report = (tmp_path / "logs/build.log.review.md").read_text()
    assert report.startswith(f"cwd {config.PROJECT}\n")
    assert f"- Build log: {log}\n" in report
    assert f"- LLVM source checkout: {config.checkout(cfg, 'abc')}\n" in report
    assert "@" not in report.replace("@loader_path", "")


@pytest.mark.usefixtures("codex")
async def test_review_honours_out(cfg: Config, tmp_path: Path) -> None:
    log = tmp_path / "build.log"
    log.write_text("")
    await review.run(cfg, ReviewLog(log=log, out=tmp_path / "report.md"))
    assert (tmp_path / "report.md").is_file()
    assert not (tmp_path / "build.log.review.md").exists()


async def test_review_of_a_failed_build_names_the_tree_that_build_used(
    cfg: Config, recipe: Recipe, upstream: Upstream, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await recipe.ship(upstream.release("v1"))
    broken = upstream.release("v2", fail=True)
    tree = (await recipe.source(broken))["checkout"]
    with pytest.raises(subprocess.CalledProcessError):
        await recipe.build(broken)
    executable(tmp_path / "fake-bin/codex", CODEX)
    monkeypatch.setenv("PATH", f"{tmp_path / 'fake-bin'}:{os.environ['PATH']}")
    log = tmp_path / "build.log"
    log.write_text("error\n")
    await review.run(cfg, ReviewLog(log=log))
    assert f"- LLVM source checkout: {tree}\n" in (tmp_path / "build.log.review.md").read_text()
