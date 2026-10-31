from pathlib import Path

import pytest

from p2996 import build, config, source
from p2996.log import P2996Error
from p2996.models import Build, Config, Source

from .conftest import Recipe, Upstream, events, git

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


async def test_a_new_commit_replaces_the_tree_in_place(recipe: Recipe, upstream: Upstream) -> None:
    old = git(upstream.path, "rev-parse", "HEAD")
    first = Path((await recipe.source(old))["checkout"])
    head = upstream.write("llvm/new.txt", "new\n")
    assert Path((await recipe.source(head))["checkout"]) == first
    assert git(first, "rev-parse", "HEAD") == head
    assert (first / "llvm/new.txt").is_file()
    assert (first / "notes.txt").read_text() == PATCHED
    await recipe.source(old)
    assert not (first / "llvm/new.txt").exists()
    assert (first / "notes.txt").read_text() == PATCHED


async def test_a_patch_upstream_broke_stops_with_its_name(cfg: Config, upstream: Upstream, patches: Path) -> None:
    head = upstream.write("notes.txt", "one\nchanged\nthree\n")
    with pytest.raises(P2996Error, match=f"notes.patch no longer applies to {head}"):
        await source.run(cfg, Source(), patches)
    with pytest.raises(P2996Error, match=head):
        await build.run(cfg, Build(commit=head))


async def test_a_changed_patch_replaces_the_old_one(recipe: Recipe, upstream: Upstream, patches: Path) -> None:
    head = upstream.write("a.txt", "x\n")
    tree = Path((await recipe.source(head))["checkout"])
    patch = patches / "notes.patch"
    patch.write_text(patch.read_text().replace("TWO", "Two"))
    await recipe.source(head)
    assert (tree / "notes.txt").read_text() == "one\nTwo\nthree\n"


async def test_a_commit_that_is_not_a_full_sha_is_refused(cfg: Config) -> None:
    with pytest.raises(P2996Error, match="full commit"):
        await source.run(cfg, Source(commit="p2996"))
    assert not config.src(cfg).exists()
