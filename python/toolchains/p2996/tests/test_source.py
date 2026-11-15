import shutil
import subprocess
from pathlib import Path

import pytest
from pydantic import ValidationError

from p2996 import build, config, source
from p2996.log import P2996Error
from p2996.models import Build, Config, Source

from .conftest import Recipe, Upstream, events, fails, git

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


def test_a_commit_that_is_not_a_full_sha_is_refused(env: Config, logs: pytest.CaptureFixture[str]) -> None:
    assert "commit" in fails(["source", "--commit", "p2996"], logs)["event"]
    assert not config.src(env).exists()


async def test_a_resolved_commit_that_is_not_a_full_sha_is_refused(cfg: Config, tmp_path: Path) -> None:
    # A SHA-256 repository: the branch tip is a real 64-digit id, not the 40 digits a build id expects.
    longer = tmp_path / "sha256"
    longer.mkdir()
    git(longer, "init", "-q", "-b", cfg.branch, "--object-format=sha256")
    who = ("-c", "user.email=test@example.invalid", "-c", "user.name=test")
    git(longer, *who, "commit", "-q", "--allow-empty", "-m", "x")
    with pytest.raises(ValidationError):
        await source.run(cfg.model_copy(update={"remote": longer.as_uri()}), Source())
    assert not config.src(cfg).exists()


async def test_source_checks_out_include_what_you_use_at_its_pinned_commit(
    cfg: Config, iwyu: Upstream, patches: Path
) -> None:
    pinned = git(iwyu.path, "rev-parse", "HEAD")
    iwyu.write("later.txt", "not pinned\n")
    await source.run(cfg, Source(), patches)
    tree = config.iwyu_checkout(cfg)
    assert git(tree, "rev-parse", "HEAD") == pinned
    assert not (tree / "later.txt").exists()
    # A new pin replaces the tree in place, as a new p2996 commit does.
    newer = git(iwyu.path, "rev-parse", "HEAD")
    await source.run(cfg.model_copy(update={"iwyu_commit": newer}), Source(), patches)
    assert git(tree, "rev-parse", "HEAD") == newer
    assert (tree / "later.txt").is_file()


@pytest.mark.parametrize("shape", ["link", "folder", "repository"])
async def test_source_refuses_an_iwyu_folder_it_did_not_make(
    cfg: Config, patches: Path, tmp_path: Path, shape: str
) -> None:
    # git clean in that folder would delete files source never wrote.
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "keep.txt").write_text("mine\n")
    tree = config.iwyu_checkout(cfg)
    tree.parent.mkdir(parents=True)
    if shape == "link":
        tree.symlink_to(elsewhere)
    else:
        shutil.copytree(elsewhere, tree)
    if shape == "repository":
        git(tree, "init", "-q")
    with pytest.raises(P2996Error, match="not a checkout p2996 source made"):
        await source.run(cfg, Source(), patches)
    assert (elsewhere / "keep.txt").read_text() == "mine\n"
    assert (tree / "keep.txt").read_text() == "mine\n"


async def test_a_failed_first_iwyu_fetch_can_be_retried(cfg: Config, iwyu: Upstream, patches: Path) -> None:
    # A pin the remote does not have: the first fetch fails after the folder exists.
    missing = "0" * 40
    with pytest.raises(subprocess.CalledProcessError):
        await source.run(cfg.model_copy(update={"iwyu_commit": missing}), Source(), patches)
    await source.run(cfg, Source(), patches)
    assert git(config.iwyu_checkout(cfg), "rev-parse", "HEAD") == git(iwyu.path, "rev-parse", "HEAD")
