"""p2996 build: prepare the source, configure and build; a rerun resumes."""

import os
import shlex
import sys
from pathlib import Path

import anyio

from . import proc, source
from .config import BOOTSTRAP, PATCHES, build_tree, checkout, finished, identity, last_build, link, started_build
from .log import log
from .models import Build, Config, Source

_CLEARED = ("CC", "CXX", "CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "SDKROOT")


async def run(cfg: Config, args: Build, patches: Path = PATCHES, bootstrap: Path = BOOTSTRAP) -> None:
    commit = args.commit or await source.latest(cfg)
    if not args.dry_run:
        await source.run(cfg, Source(commit=commit), patches, bootstrap)
    name = identity(commit, patches, bootstrap)
    tree = checkout(cfg, name)
    built = build_tree(cfg, name)
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
        f"-DCMAKE_INSTALL_PREFIX={cfg.root / name}",
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
    built.mkdir(parents=True, exist_ok=True)
    link(started_build(cfg), name)
    await proc.run(*configure, env=env, capture=False)
    await proc.run(*compile_, env=env, capture=False)
    done = finished(cfg, name)
    done.parent.mkdir(exist_ok=True)
    done.write_text(f"{int(done.read_text()) + 1 if done.exists() else 1}\n")
    link(last_build(cfg), name)
    log.info("build done", build=str(built), commit=commit)
