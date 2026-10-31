from pathlib import Path

import anyio
import pytest

from p2996 import build, source
from p2996.log import P2996Error
from p2996.models import Build, Config, Source

from .conftest import Recipe, Upstream, events, git, tree

pytestmark = pytest.mark.anyio

PATCHED = "one\nTWO\nthree\n"


async def test_latest_is_the_branch_head(cfg: Config, upstream: Upstream) -> None:
    head = upstream.write("extra.txt", "x\n")
    assert await source.latest(cfg) == head


async def test_first_run_checks_out_the_newest_commit_and_patches_it(
    cfg: Config, upstream: Upstream, patches: Path, logs: pytest.CaptureFixture[str]
) -> None:
    head = git(upstream.path, "rev-parse", "HEAD")
    await source.run(cfg, Source(), patches)
    out, err = events(logs)
    assert [(e["event"], e.get("patch")) for e in out] == [("patch applied", "notes.patch"), ("source ready", None)]
    assert out[1]["commit"] == head
    assert out[1]["level"] == "info"
    checkout = Path(out[1]["checkout"])
    assert git(checkout, "rev-parse", "HEAD") == head
    assert (checkout / "notes.txt").read_text() == PATCHED
    assert not err


async def test_a_new_upstream_commit_gets_its_own_tree_and_leaves_the_old_one_untouched(
    recipe: Recipe, upstream: Upstream
) -> None:
    old = git(upstream.path, "rev-parse", "HEAD")
    first = Path((await recipe.source(old))["checkout"])
    before = tree(first)
    head = upstream.write("llvm/new.txt", "new\n")
    second = Path((await recipe.source(head))["checkout"])
    assert second != first
    assert tree(first) == before
    assert git(second, "rev-parse", "HEAD") == head
    assert (second / "llvm/new.txt").is_file()
    assert (second / "notes.txt").read_text() == PATCHED
    # Going back finds the old tree as it was: nothing to fetch or rebuild.
    assert (await recipe.source(old))["checkout"] == str(first)
    assert tree(first) == before


async def test_the_same_commit_prepared_twice_at_once_gives_one_complete_tree(
    cfg: Config, upstream: Upstream, patches: Path, logs: pytest.CaptureFixture[str]
) -> None:
    head = git(upstream.path, "rev-parse", "HEAD")
    async with anyio.create_task_group() as running:
        running.start_soon(source.run, cfg, Source(commit=head), patches)
        running.start_soon(source.run, cfg, Source(commit=head), patches)
    ready = [e["checkout"] for e in events(logs)[0] if e["event"] == "source ready"]
    assert len(ready) == 2
    assert ready[0] == ready[1]
    assert (Path(ready[0]) / "notes.txt").read_text() == PATCHED


async def test_a_patch_upstream_broke_stops_with_its_name(cfg: Config, upstream: Upstream, patches: Path) -> None:
    head = upstream.write("notes.txt", "one\nchanged\nthree\n")
    with pytest.raises(P2996Error, match=f"notes.patch no longer applies to {head}"):
        await source.run(cfg, Source(), patches)
    with pytest.raises(P2996Error, match=head):
        await build.run(cfg, Build(commit=head))
