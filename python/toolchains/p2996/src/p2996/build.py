"""p2996 build: configure (every run, so bootstrap.cmake edits apply) and build; a rerun resumes."""

import os
import shlex
import sys
from pathlib import Path

import anyio

from . import proc
from .config import RESOURCES, build_tree, checkout, last_build, link
from .log import P2996Error, log
from .models import Build, Config
from .source import latest

_CLEARED = ("CC", "CXX", "CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "SDKROOT")


async def run(cfg: Config, args: Build, bootstrap: Path = RESOURCES / "bootstrap.cmake") -> None:
    commit = args.commit or await latest(cfg)
    tree = checkout(cfg, commit)
    if not await anyio.Path(tree).is_dir():
        msg = f"p2996 build: {commit} has no prepared source; run p2996 source for it"
        raise P2996Error(msg)
    built = build_tree(cfg, commit)
    env = {k: v for k, v in os.environ.items() if k not in _CLEARED}
    env["P2996_SDK"] = str(await anyio.Path(await proc.output("xcrun", "--show-sdk-path")).resolve())
    env["NINJA_STATUS"] = "[%f/%t %es] "
    # lua is on PATH through the mise shims, whose prefix has no headers; FindLua honours LUA_DIR.
    env["LUA_DIR"] = await proc.output("mise", "where", "lua")
    configure = [
        "cmake",
        "-S",
        str(tree / "llvm"),
        "-B",
        str(built),
        "-G",
        "Ninja",
        "-C",
        str(bootstrap),
        f"-DCMAKE_C_COMPILER={await proc.output('xcrun', '-f', 'clang')}",
        f"-DCMAKE_CXX_COMPILER={await proc.output('xcrun', '-f', 'clang++')}",
        f"-DCMAKE_INSTALL_PREFIX={cfg.root / commit}",
        # This project's venv: the locked opt-viewer and MLIR modules. lldb links its base python,
        # so a python upgrade needs a rebuild.
        f"-DPython3_EXECUTABLE={sys.executable}",
        "-DLLDB_ENABLE_PYTHON=ON",
    ]
    compile_ = ["cmake", "--build", str(built), "--parallel", "4"]
    if args.dry_run:
        log.info(
            "build dry run",
            P2996_SDK=env["P2996_SDK"],
            LUA_DIR=env["LUA_DIR"],
            configure=shlex.join(configure),
            compile=shlex.join(compile_),
        )
        return
    await proc.run(*configure, env=env, capture=False)
    await proc.run(*compile_, env=env, capture=False)
    link(last_build(cfg), commit)
    log.info("build done", build=str(built), commit=commit)
