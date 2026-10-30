from pathlib import Path

import pytest

from p2996 import config, source
from p2996.log import P2996Error
from p2996.models import Config, Source

from .conftest import Upstream, events, git

pytestmark = pytest.mark.anyio


def notes(cfg: Config) -> str:
    return (config.src(cfg) / "notes.txt").read_text()


async def test_latest_is_the_branch_head(cfg: Config, upstream: Upstream) -> None:
    head = upstream.write("extra.txt", "x\n")
    assert await source.latest(cfg) == head


async def test_first_run_checks_out_the_newest_commit_and_patches_it(
    cfg: Config, upstream: Upstream, patches: Path, logs: pytest.CaptureFixture[str]
) -> None:
    head = git(upstream.path, "rev-parse", "HEAD")
    await source.run(cfg, Source(), patches)
    assert await config.commit(cfg) == head
    assert notes(cfg) == "one\nTWO\nthree\n"
    out, err = events(logs)
    assert [(e["event"], e.get("patch")) for e in out] == [("patch applied", "notes.patch"), ("source ready", None)]
    assert out[1]["commit"] == head
    assert out[1]["level"] == "info"
    assert not err


async def test_rerun_keeps_the_checkout_and_skips_applied_patches(
    cfg: Config, patches: Path, logs: pytest.CaptureFixture[str]
) -> None:
    await source.run(cfg, Source(), patches)
    await source.run(cfg, Source(), patches)
    assert "patch applied already" in [e["event"] for e in events(logs)[0]]
    assert notes(cfg) == "one\nTWO\nthree\n"


async def test_a_new_upstream_commit_replaces_the_patched_checkout(
    cfg: Config, upstream: Upstream, patches: Path
) -> None:
    await source.run(cfg, Source(), patches)
    head = upstream.write("llvm/new.txt", "new\n")
    await source.run(cfg, Source(), patches)
    assert await config.commit(cfg) == head
    assert (config.src(cfg) / "llvm/new.txt").is_file()
    assert notes(cfg) == "one\nTWO\nthree\n"


async def test_commit_argument_pins_an_older_commit(cfg: Config, upstream: Upstream, patches: Path) -> None:
    old = git(upstream.path, "rev-parse", "HEAD")
    upstream.write("llvm/new.txt", "new\n")
    await source.run(cfg, Source(commit=old), patches)
    assert await config.commit(cfg) == old


async def test_a_patch_upstream_broke_stops_with_its_name(cfg: Config, upstream: Upstream, patches: Path) -> None:
    head = upstream.write("notes.txt", "one\nchanged\nthree\n")
    with pytest.raises(P2996Error, match=f"notes.patch no longer applies to {head}"):
        await source.run(cfg, Source(), patches)
