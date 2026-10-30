from pathlib import Path

import pytest

from p2996 import config, source
from p2996.models import Config

from .conftest import Upstream, git


def notes(cfg: Config) -> str:
    return (config.src(cfg) / "notes.txt").read_text()


def test_latest_is_the_branch_head(cfg: Config, upstream: Upstream) -> None:
    head = upstream.write("extra.txt", "x\n")
    assert source.latest(cfg) == head


def test_first_run_checks_out_the_newest_commit_and_patches_it(
    cfg: Config, upstream: Upstream, patches: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    head = git(upstream.path, "rev-parse", "HEAD")
    source.run(cfg, None, patches)
    assert config.commit(cfg) == head
    assert notes(cfg) == "one\nTWO\nthree\n"
    assert "applied: notes.patch" in capsys.readouterr().out


def test_rerun_keeps_the_checkout_and_skips_applied_patches(
    cfg: Config, patches: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source.run(cfg, None, patches)
    source.run(cfg, None, patches)
    assert "applied already: notes.patch" in capsys.readouterr().out
    assert notes(cfg) == "one\nTWO\nthree\n"


def test_a_new_upstream_commit_replaces_the_patched_checkout(cfg: Config, upstream: Upstream, patches: Path) -> None:
    source.run(cfg, None, patches)
    head = upstream.write("llvm/new.txt", "new\n")
    source.run(cfg, None, patches)
    assert config.commit(cfg) == head
    assert (config.src(cfg) / "llvm/new.txt").is_file()
    assert notes(cfg) == "one\nTWO\nthree\n"


def test_commit_argument_pins_an_older_commit(cfg: Config, upstream: Upstream, patches: Path) -> None:
    old = git(upstream.path, "rev-parse", "HEAD")
    upstream.write("llvm/new.txt", "new\n")
    source.run(cfg, old, patches)
    assert config.commit(cfg) == old


def test_a_patch_upstream_broke_stops_with_its_name(cfg: Config, upstream: Upstream, patches: Path) -> None:
    head = upstream.write("notes.txt", "one\nchanged\nthree\n")
    with pytest.raises(SystemExit, match=f"notes.patch no longer applies to {head}"):
        source.run(cfg, None, patches)
