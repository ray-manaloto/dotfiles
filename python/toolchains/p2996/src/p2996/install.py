"""p2996 install: install the last successful build, verify it, then swap ROOT/current in one rename."""

import os
import shutil
from pathlib import Path

from . import config, proc, verify
from .config import bin_dir, build_tree, last_build
from .log import P2996Error, log
from .models import Config, Install

# What PATH and tools reach: fixed links through ROOT/current, so one rename changes all of them.
ENTRIES = ("bin", "include", "lib", "libexec", "share")


async def run(cfg: Config, _: Install) -> None:
    last = last_build(cfg)
    if not last.is_symlink():
        msg = "p2996 install: no successful build; run p2996 build"
        raise P2996Error(msg)
    name = last.readlink().name
    root, view, current = cfg.root, f"{name}/view", cfg.root / "current"
    active = str(current.readlink()) if current.is_symlink() else None
    if active != view:
        await assemble(cfg, name)
        await verify.check(root / view / "bin/clang++-p2996")
        if active:
            config.link(root / "previous", active)
        config.link(current, view)
    else:
        await write_configs(root / name)  # The SDK can move under a build that is otherwise current.
    for part in ENTRIES:
        entry = root / part
        if not entry.is_symlink() and entry.is_dir():
            shutil.rmtree(entry)  # The real ROOT/bin of the layout before this one.
        if not entry.is_symlink() or str(entry.readlink()) != f"current/{part}":
            config.link(entry, f"current/{part}")
    back = root / "previous"
    log.info(
        "installed",
        prefix=str(root / name),
        commit=name.partition("-")[0],
        links=str(bin_dir(cfg)),
        previous=str(root / back.readlink()) if back.is_symlink() else None,
    )


async def write_configs(pre: Path) -> None:
    # Clang reads <triple>.cfg, then arm64-apple-darwin<N>.cfg, then the unversioned name from its own
    # resolved bin dir; only the unversioned names are written, so a macOS bump never shadows them.
    sdk = await proc.output("xcrun", "--show-sdk-path")
    (pre / "bin/arm64-apple-darwin.cfg").write_text(
        f"# P2996 default config for every driver mode on arm64 macOS; the SDK is xcrun's.\n-isysroot {sdk}\n"
    )
    (pre / "bin/arm64-apple-darwin-clang++.cfg").write_text(
        "# C++ driver: the SDK, plus the P2996 libc++, libc++abi and libunwind at link time ($ = link only).\n"
        f"@arm64-apple-darwin.cfg\n$-Wl,-L,{pre}/lib\n$-Wl,-rpath,{pre}/lib\n$-Wl,-lunwind\n"
    )


async def assemble(cfg: Config, name: str) -> None:
    """Install into ROOT/<name> and lay out ROOT/<name>/view; nothing active changes."""
    pre, build = cfg.root / name, build_tree(cfg, name)
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("DESTDIR", "CMAKE_INSTALL_MODE", "CMAKE_INSTALL_PARALLEL_LEVEL")
    }
    for tree in (build, build / "runtimes/builtins-bins", build / "runtimes/runtimes-bins"):
        await proc.run("cmake", "--install", tree, "--prefix", pre, env=env, capture=False)
    for part in ("bin", "include", "lib"):
        if not (pre / part).is_dir():
            msg = f"p2996 install: {name} has no {part}"
            raise P2996Error(msg)
    await write_configs(pre)
    view = pre / "view"
    shutil.rmtree(view, ignore_errors=True)
    (view / "bin").mkdir(parents=True)
    # LLVM's own *-p2996 drivers and the .cfg files keep their names; every other tool gets -p2996
    # unless LLVM already installed that suffixed name (clang -> clang-p2996).
    for tool in sorted((pre / "bin").iterdir()):
        name = tool.name
        if name.endswith(("-p2996", ".cfg")):
            link = name
        elif (tool.parent / f"{name}-p2996").exists():
            continue
        else:
            link = f"{name}-p2996"
        (view / "bin" / link).symlink_to(f"../../bin/{name}")
    # Tools that find their headers from their own path, not its resolved target (clang-scan-deps
    # looks in ROOT/bin/../lib/clang), need ROOT to look like the prefix (DL-761).
    for name in ("include", "lib", "libexec", "share"):
        if (pre / name).is_dir():
            (view / name).symlink_to(f"../{name}")
