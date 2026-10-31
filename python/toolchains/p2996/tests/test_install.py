import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from p2996 import build, config, install, proc
from p2996.log import P2996Error
from p2996.models import Build, Config, Install

from .conftest import LINKS, Recipe, Upstream, tools, tree, versions, whole

pytestmark = pytest.mark.anyio


@pytest.fixture
async def installed(recipe: Recipe, upstream: Upstream) -> Path:
    await recipe.ship(upstream.release("v1"))
    return Path((await recipe.install())["prefix"])


async def test_install_writes_the_default_configs(installed: Path) -> None:
    sdk = await proc.output("xcrun", "--show-sdk-path")
    assert (installed / "bin/arm64-apple-darwin.cfg").read_text().endswith(f"-isysroot {sdk}\n")
    cxx = (installed / "bin/arm64-apple-darwin-clang++.cfg").read_text().splitlines()
    assert cxx[1:] == [
        "@arm64-apple-darwin.cfg",
        f"$-Wl,-L,{installed}/lib",
        f"$-Wl,-rpath,{installed}/lib",
        "$-Wl,-lunwind",
    ]


async def test_install_links_every_tool_once_with_the_p2996_suffix(cfg: Config, installed: Path) -> None:
    assert tools(cfg.root) == set(LINKS)
    for link, tool in LINKS.items():
        assert (config.bin_dir(cfg) / link).resolve() == (installed / "bin" / tool).resolve()


async def test_install_makes_root_look_like_the_prefix(cfg: Config, installed: Path) -> None:
    # clang-scan-deps-p2996 finds headers through ROOT/bin/../include and ../lib (DL-761).
    root = cfg.root
    assert (root / "include").resolve() == (installed / "include").resolve()
    assert (root / "lib").resolve() == (installed / "lib").resolve()
    assert (root / "bin/../include/c++/v1/meta").is_file()
    assert not (root / "libexec").exists()


async def test_install_refuses_when_no_build_succeeded(cfg: Config, recipe: Recipe, upstream: Upstream) -> None:
    commit = upstream.release("v1", fail=True)
    await recipe.source(commit)
    with pytest.raises(P2996Error, match="failed to compile"):
        await recipe.build(commit)
    with pytest.raises(P2996Error, match="successful build"):
        await install.run(cfg, Install())
    assert tools(cfg.root) == set()


async def test_the_previous_view_stays_available_for_rollback(cfg: Config, recipe: Recipe, upstream: Upstream) -> None:
    await recipe.ship(upstream.release("v1"))
    assert (await recipe.install()).get("previous") is None
    await recipe.ship(upstream.release("v2"))
    previous = (await recipe.install()).get("previous")
    assert previous, "install names no previous view"
    assert versions(Path(previous)) == whole("v1")
    assert tools(Path(previous)) == set(LINKS)
    assert versions(cfg.root) == whole("v2")

    # Reinstalling the active build must not make it its own way back.
    assert (await recipe.install()).get("previous") == previous
    assert versions(Path(previous)) == whole("v1")


@pytest.mark.parametrize(
    ("bad", "reason"),
    [
        ({"answer": 44}, "sample printed 'reflection value=44'"),
        ({"skip": "include"}, "include"),
        ({"skip": "lib"}, "lib"),
    ],
)
async def test_a_bad_version_is_never_activated(
    bad: dict, reason: str, cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    await recipe.ship(upstream.release("v1"))
    await recipe.install()
    await recipe.ship(upstream.release("v2", **bad))
    with pytest.raises(P2996Error, match=reason):
        await install.run(cfg, Install())
    assert versions(cfg.root) == whole("v1")


async def test_one_rename_swaps_the_whole_version(
    cfg: Config, recipe: Recipe, upstream: Upstream, monkeypatch: pytest.MonkeyPatch
) -> None:
    await recipe.ship(upstream.release("v1"))
    await recipe.install()
    await recipe.ship(upstream.release("v2"))
    views: list[tuple[str, dict]] = []

    def watched(name: str) -> Callable:
        real = getattr(os, name)

        def step(*args: object, **kwargs: object) -> None:
            real(*args, **kwargs)
            views.append((name, versions(cfg.root)))

        return step

    for name in ("remove", "rename", "replace", "symlink", "unlink"):
        monkeypatch.setattr(os, name, watched(name))
    await recipe.install()

    assert [view for _, view in views if view not in (whole("v1"), whole("v2"))] == []
    assert views[-1][1] == whole("v2")
    flip = next(i for i, (_, view) in enumerate(views) if view == whole("v2"))
    assert all(view == whole("v2") for _, view in views[flip:])
    assert views[flip][0] in ("rename", "replace")


def old_layout(root: Path, old: str) -> None:
    """What the install before this layout left: ROOT/bin is a real directory of links, the rest links to one prefix."""
    (root / old / "bin").mkdir(parents=True)
    (root / old / "include").mkdir()
    (root / old / "lib").mkdir()
    (root / old / "share").mkdir()
    (root / old / "share/old-marker").write_text("old\n")
    (root / old / "bin/clang++-p2996").write_text("version=old\n")
    (root / "bin").mkdir()
    (root / "bin/clang++-p2996").symlink_to(f"../{old}/bin/clang++-p2996")
    (root / "bin/stale-p2996").symlink_to("../gone/bin/stale")
    for name in ("include", "lib", "share"):
        (root / name).symlink_to(f"{old}/{name}")


async def test_install_refuses_the_old_layout_and_leaves_it_working(
    cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    root = cfg.root
    old_layout(root, "0" * 40)
    await recipe.ship(upstream.release("v2"))
    before = tree(root)
    with pytest.raises(P2996Error, match="old layout"):
        await install.run(cfg, Install())
    assert tree(root) == before


async def test_a_rebuild_after_the_cache_is_gone_finds_its_install(
    cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    commit = await recipe.ship(upstream.release("v1"))
    first = (await recipe.install())["prefix"]
    shutil.rmtree(cfg.cache)
    await recipe.source(commit)
    await build.run(cfg, Build(commit=commit), recipe.patches)
    assert recipe.logged("build skipped").get("commit") == commit
    assert (await recipe.install())["prefix"] == first


async def test_a_skipped_build_of_an_older_id_makes_it_active_again(
    cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    old = await recipe.ship(upstream.release("v1"))
    first = (await recipe.install())["prefix"]
    await recipe.ship(upstream.release("v2"))
    await recipe.install()
    await build.run(cfg, Build(commit=old), recipe.patches)
    assert (await recipe.install())["prefix"] == first
    assert versions(cfg.root) == whole("v1")


async def test_a_changed_recipe_for_the_active_commit_reaches_root(
    cfg: Config, recipe: Recipe, upstream: Upstream, patches: Path
) -> None:
    commit = await recipe.ship(upstream.release("v1"))
    first = (await recipe.install())["prefix"]
    patch = patches / "notes.patch"
    patch.write_text(patch.read_text().replace("TWO", "Two"))
    await recipe.ship(commit)
    done = await recipe.install()
    assert done["prefix"] != first
    assert done.get("previous") == f"{first}/view"
    assert (cfg.root / "bin/clang++-p2996").resolve().is_relative_to(done["prefix"])


async def test_reinstalling_rewrites_the_default_configs(cfg: Config, installed: Path) -> None:
    file = installed / "bin/arm64-apple-darwin.cfg"
    good = file.read_text()
    file.write_text("-isysroot /gone\n")
    await install.run(cfg, Install())
    assert file.read_text() == good


async def crashed_install(cfg: Config, recipe: Recipe, commit: str) -> None:
    """Leave what a crash partway through assembly leaves: a view with parts missing, no mark, nothing active."""
    prefix = Path((await recipe.install())["prefix"])
    (prefix / "installed").unlink()
    (prefix / "view/include").unlink()
    (prefix / "view/bin/llvm-ar-p2996").unlink()
    (cfg.root / "current").unlink()
    assert prefix.name.startswith(commit)


async def test_an_interrupted_install_is_assembled_again(cfg: Config, recipe: Recipe, upstream: Upstream) -> None:
    await crashed_install(cfg, recipe, await recipe.ship(upstream.release("v1")))
    await recipe.install()
    assert tools(cfg.root) == set(LINKS)
    assert versions(cfg.root) == whole("v1")


async def test_an_interrupted_install_does_not_skip_the_next_build(
    cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    commit = await recipe.ship(upstream.release("v1"))
    await crashed_install(cfg, recipe, commit)
    assert (await recipe.build(commit)).get("commit") == commit


async def test_an_install_that_failed_verify_does_not_skip_the_next_build(
    cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    commit = await recipe.ship(upstream.release("v1", answer=44))
    with pytest.raises(P2996Error):
        await install.run(cfg, Install())
    assert (await recipe.build(commit)).get("commit") == commit
