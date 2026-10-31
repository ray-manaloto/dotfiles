import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from p2996 import config, install, proc
from p2996.log import P2996Error
from p2996.models import Config, Install

from .conftest import LINKS, Recipe, Upstream, tools, versions, whole

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


async def test_a_failed_build_leaves_the_last_successful_one_on_record(
    cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    good = await recipe.ship(upstream.release("v1"))
    broken = upstream.release("v2", fail=True)
    await recipe.source(broken)
    with pytest.raises(subprocess.CalledProcessError):
        await recipe.build(broken)
    done = await recipe.install()
    assert done["prefix"] == str(cfg.root / good)
    assert done.get("commit") == good
    assert versions(cfg.root) == whole("v1")


async def test_install_refuses_when_no_build_succeeded(cfg: Config, recipe: Recipe, upstream: Upstream) -> None:
    commit = upstream.release("v1", fail=True)
    await recipe.source(commit)
    with pytest.raises(subprocess.CalledProcessError):
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


async def test_install_takes_over_the_layout_the_old_install_left(
    cfg: Config, recipe: Recipe, upstream: Upstream
) -> None:
    # What every machine has today: ROOT/bin is a real directory of links, the rest links to one prefix.
    root, old = cfg.root, "0" * 40
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

    await recipe.ship(upstream.release("v2"))
    await recipe.install()

    assert versions(root) == whole("v2")
    assert tools(root) == set(LINKS)
    assert not (root / "share/old-marker").exists()
    assert (root / old / "bin/clang++-p2996").is_file()
