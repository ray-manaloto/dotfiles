"""p2996 build: prepare the source, configure, and compile unless that id is already installed."""

import os
import shlex
import subprocess
import sys
from pathlib import Path

import anyio

from . import inputs, proc, source
from .config import (
    BOOTSTRAP,
    PATCHES,
    build_tree,
    checkout,
    configured_prefix,
    installed_mark,
    last_build,
    link,
    sccache_stats,
)
from .log import P2996Error, log
from .models import Build, Config, Source

_CLEARED = ("CC", "CXX", "CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "SDKROOT")


async def run(cfg: Config, args: Build, patches: Path = PATCHES, bootstrap: Path = BOOTSTRAP) -> None:
    commit = args.commit or await source.latest(cfg)
    if not args.dry_run:
        await source.run(cfg, Source(commit=commit), patches)
    tree, built = checkout(cfg), build_tree(cfg)
    env = {k: v for k, v in os.environ.items() if k not in _CLEARED}
    env["P2996_SDK"] = str(await anyio.Path(await proc.output("xcrun", "--show-sdk-path")).resolve())
    env["NINJA_STATUS"] = "[%f/%t %es] "
    # lua is on PATH through the mise shims, whose prefix has no headers; FindLua honours LUA_DIR.
    env["LUA_DIR"] = await proc.output("mise", "where", "lua")
    # The real binary, not the mise shim, which would add 0.4 s to every compile.
    launcher = env["P2996_LAUNCHER"] = await proc.output("mise", "which", "sccache")
    env["P2996_JOBS"] = str(cfg.jobs)
    env["P2996_ZSTD"] = await proc.output("mise", "where", "conda:zstd-static")
    configure = [
        "cmake",
        # A fresh cache: the id must not depend on what an earlier commit left in this folder.
        "--fresh",
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
        f"-DCMAKE_INSTALL_PREFIX={configured_prefix(cfg)}",
        # This project's venv: the locked opt-viewer and MLIR modules. lldb links its base python,
        # so a python upgrade needs a rebuild.
        f"-DPython3_EXECUTABLE={sys.executable}",
        "-DLLDB_ENABLE_PYTHON=ON",
    ]
    compile_ = ["cmake", "--build", str(built), "--parallel", env["P2996_JOBS"]]
    if args.dry_run:
        log.info(
            "build dry run",
            P2996_SDK=env["P2996_SDK"],
            LUA_DIR=env["LUA_DIR"],
            configure=shlex.join(configure),
            compile=shlex.join(compile_),
        )
        return
    await anyio.to_thread.run_sync(inputs.forget_sub_builds, built)
    inputs.query(built)
    await proc.run(*configure, env=env, capture=False)
    # Hashing every SDK file takes seconds, so it runs off the event loop.
    name = await anyio.to_thread.run_sync(inputs.write, cfg, commit, patches, bootstrap, Path(env["P2996_SDK"]))
    mark = installed_mark(cfg, name)
    if args.force:
        # Install replaces an id without its mark; sccache recompiles and overwrites what it holds.
        mark.unlink(missing_ok=True)
        env["SCCACHE_RECACHE"] = "1"
    elif mark.exists():
        link(last_build(cfg), name)
        log.info("build skipped", id=name, commit=commit)
        return
    await proc.run(launcher, "--zero-stats", env=env)
    try:
        await proc.run(*compile_, env=env, capture=False)
    except subprocess.CalledProcessError as error:
        msg = f"p2996 build: {commit} failed to compile; the previous install stays active"
        raise P2996Error(msg) from error
    finally:
        stats = await proc.output(launcher, "--show-adv-stats", "--stats-format=json", env=env)
        sccache_stats(cfg).write_text(stats)
    link(last_build(cfg), name)
    log.info("build done", id=name, build=str(built), commit=commit)
