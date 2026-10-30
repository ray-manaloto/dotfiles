import re
import subprocess
from pathlib import Path

import pytest

from p2996 import config, verify
from p2996.models import Config

from .conftest import executable

# Stands in for clang++-p2996 until the real build exists: it reports the default config the way
# clang --version does, and compiles with the real Apple clang (which has no -freflection).
STAND_IN = """\
import os, subprocess, sys
args = sys.argv[1:]
if args == ["--version"]:
    here = os.path.dirname(os.path.abspath(__file__))
    print("clang version 23.0.0 (p2996 stand-in)")
    print(f"Configuration file: {here}/arm64-apple-darwin-clang++.cfg")
    sys.exit(0)
args = ["-std=c++2c" if a == "-std=c++26" else a for a in args if a != "-freflection"]
sys.exit(subprocess.run(["xcrun", "clang++", *args]).returncode)
"""

PLAIN_SAMPLE = '#include <cstdio>\nint main() { std::puts("reflection value=43"); }\n'


@pytest.fixture
def sample(tmp_path: Path) -> Path:
    path = tmp_path / "sample.cpp"
    path.write_text(PLAIN_SAMPLE)
    return path


def test_verify_compiles_and_runs_the_sample(cfg: Config, sample: Path, capsys: pytest.CaptureFixture[str]) -> None:
    executable(config.bin_dir(cfg) / "clang++-p2996", STAND_IN)
    verify.run(cfg, sample)
    assert capsys.readouterr().out == "p2996 verify OK: clang version 23.0.0 (p2996 stand-in)\n"


def test_verify_refuses_a_compiler_without_the_default_config(cfg: Config, sample: Path) -> None:
    apple = subprocess.run(["xcrun", "-f", "clang++"], check=True, capture_output=True, text=True).stdout.strip()
    config.bin_dir(cfg).mkdir(parents=True)
    (config.bin_dir(cfg) / "clang++-p2996").symlink_to(apple)
    with pytest.raises(SystemExit, match=re.escape("does not load arm64-apple-darwin-clang++.cfg")):
        verify.run(cfg, sample)


def test_verify_refuses_a_wrong_answer(cfg: Config, sample: Path) -> None:
    executable(config.bin_dir(cfg) / "clang++-p2996", STAND_IN)
    with pytest.raises(SystemExit, match="sample printed 'reflection value=43'"):
        verify.run(cfg, sample, expect="reflection value=44")


def test_the_shipped_sample_uses_reflection() -> None:
    text = (config.RESOURCES / "reflection.cpp").read_text()
    assert "#include <meta>" in text
    assert "^^Record" in text
