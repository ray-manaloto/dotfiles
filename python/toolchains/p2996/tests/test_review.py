from pathlib import Path

import pytest

from p2996 import config, review
from p2996.models import Config

from .conftest import executable

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
def test_review_fills_the_prompt_and_writes_beside_the_log(cfg: Config, tmp_path: Path) -> None:
    log = tmp_path / "logs/build.log"
    log.parent.mkdir()
    log.write_text("CMake Warning: x\n")
    review.run(cfg, log, None)
    report = (tmp_path / "logs/build.log.review.md").read_text()
    assert report.startswith(f"cwd {config.PROJECT}\n")
    assert f"- Build log: {log}\n" in report
    assert f"- LLVM source checkout: {config.src(cfg)}\n" in report
    assert "@" not in report.replace("@loader_path", "")


@pytest.mark.usefixtures("codex")
def test_review_honours_out(cfg: Config, tmp_path: Path) -> None:
    log = tmp_path / "build.log"
    log.write_text("")
    review.run(cfg, log, tmp_path / "report.md")
    assert (tmp_path / "report.md").is_file()
    assert not (tmp_path / "build.log.review.md").exists()
