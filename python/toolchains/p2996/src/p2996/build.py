"""p2996 build: configure (every run, so bootstrap.cmake edits apply) and build; a rerun resumes."""

import fcntl
import os
import shlex
import sys
from pathlib import Path

import anyio

from . import proc
from .config import RESOURCES, build_dir, prefix, src
from .log import P2996Error, log
from .models import Build, Config

_CLEARED = ("CC", "CXX", "CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "SDKROOT")


async def run(cfg: Config, args: Build, bootstrap: Path = RESOURCES / "bootstrap.cmake") -> None:
    env = {k: v for k, v in os.environ.items() if k not in _CLEARED}
    env["P2996_SDK"] = str(await anyio.Path(await proc.output("xcrun", "--show-sdk-path")).resolve())
    env["NINJA_STATUS"] = "[%f/%t %es] "
    # lua is on PATH through the mise shims, whose prefix has no headers; FindLua honours LUA_DIR.
    env["LUA_DIR"] = await proc.output("mise", "where", "lua")
    configure = [
        "cmake",
        "-S",
        str(src(cfg) / "llvm"),
        "-B",
        str(build_dir(cfg)),
        "-G",
        "Ninja",
        "-C",
        str(bootstrap),
        f"-DCMAKE_C_COMPILER={await proc.output('xcrun', '-f', 'clang')}",
        f"-DCMAKE_CXX_COMPILER={await proc.output('xcrun', '-f', 'clang++')}",
        f"-DCMAKE_INSTALL_PREFIX={await prefix(cfg)}",
        # This project's venv: the locked opt-viewer and MLIR modules. lldb links its base python,
        # so a python upgrade needs a rebuild.
        f"-DPython3_EXECUTABLE={sys.executable}",
        "-DLLDB_ENABLE_PYTHON=ON",
    ]
    compile_ = ["cmake", "--build", str(build_dir(cfg)), "--parallel", "4"]
    if args.dry_run:
        log.info(
            "build dry run",
            P2996_SDK=env["P2996_SDK"],
            LUA_DIR=env["LUA_DIR"],
            configure=shlex.join(configure),
            compile=shlex.join(compile_),
        )
        return
    # One heavy build at a time: the gate the legacy host_lock.py takes, held without waiting.
    cfg.lock.parent.mkdir(parents=True, exist_ok=True)
    with cfg.lock.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            msg = "p2996 build: another heavy build holds the lock"
            raise P2996Error(msg) from None
        await proc.run(*configure, env=env, capture=False)
        await proc.run(*compile_, env=env, capture=False)
    log.info("build done", build=str(build_dir(cfg)))
