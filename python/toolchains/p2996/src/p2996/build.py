"""p2996 build: prepare the source, configure, and compile unless that id is already installed."""

import os
import shlex
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

import anyio

from . import inputs, proc, source
from .config import (
    BOOTSTRAP,
    PATCHES,
    build_log,
    build_tree,
    checkout,
    configured_prefix,
    installed_mark,
    iwyu_checkout,
    last_build,
    link,
    sccache_stats,
)
from .log import P2996Error, log
from .models import Build, Config, Source

_CLEARED = ("CC", "CXX", "CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "SDKROOT")
# sccache fails a compile whose depfile vanished before it stored the outputs (README, Nothing else runs ninja
# in the build folder); ninja resumes, so a second run repeats only that step.
SCCACHE_ZIP = b"failed to zip up compiler outputs"


async def compile_(command: list[str], env: dict[str, str], copy: Path) -> None:
    """Run the compile, once more when sccache lost a depfile; a second failure is the build's.

    copy holds the output of the newest run, to watch the build without running ninja in its folder.
    """
    code, zip_failed = await proc.tee(*command, env=env, watch=SCCACHE_ZIP, copy=copy)
    if code and zip_failed:
        log.warning("compile retry", reason=SCCACHE_ZIP.decode(), code=code)
        code, _ = await proc.tee(*command, env=env, watch=SCCACHE_ZIP, copy=copy)
    if code:
        raise subprocess.CalledProcessError(code, command)


def python_libdir(libdir: Path, library: str, version: str) -> Path:
    """The folder lldb's rpath names for libpython: mise's major.minor link when it holds the same library.

    sysconfig's LIBDIR is mise's hashed install folder (installs/python-<hash>/lib), which a reinstall or
    prune replaces; installs/python/<major.minor> is the link mise keeps pointing at the current one.
    """
    stable = libdir.parent.parent / "python" / version / "lib"
    if (stable / library).is_file() and (stable / library).samefile(libdir / library):
        return stable
    return libdir


async def require_codesign(cfg: Config) -> None:
    """Stop before configure unless P2996_CODESIGN can sign, as lldb's debugserver will be at the end.

    A certificate without its private key (an interrupted setup) finds no identity and fails here too.
    """
    with tempfile.TemporaryDirectory() as scratch:
        probe = Path(scratch) / "probe"
        shutil.copyfile("/usr/bin/true", probe)
        try:
            await proc.run("codesign", "-f", "-s", cfg.codesign, "--keychain", str(cfg.keychain), str(probe))
        except subprocess.CalledProcessError as error:
            script = checkout(cfg) / "lldb/scripts/macos-setup-codesign.sh"
            msg = f"p2996 build: {cfg.codesign} in {cfg.keychain} cannot sign; create it once with bash {script}"
            raise P2996Error(msg) from error


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
    env["P2996_JOBS"] = str(args.jobs or cfg.jobs)
    env["P2996_REMOTE"] = cfg.remote
    env["P2996_CODESIGN"] = cfg.codesign
    env["P2996_ZSTD"] = await proc.output("mise", "where", "conda:zstd-static")
    # lldb links libpython through @rpath: the folder of the Python that Python3_EXECUTABLE below runs.
    env["P2996_PYTHON_LIBDIR"] = str(
        python_libdir(
            Path(sysconfig.get_config_var("LIBDIR")),
            sysconfig.get_config_var("LDLIBRARY"),
            f"{sys.version_info.major}.{sys.version_info.minor}",
        )
    )
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
        # include-what-you-use builds in the LLVM tree (bootstrap.cmake names it); its folder is in the
        # cache, so the id counts it through P2996_IWYU_COMMIT.
        f"-DLLVM_EXTERNAL_IWYU_SOURCE_DIR:PATH={iwyu_checkout(cfg)}",
    ]
    command = ["cmake", "--build", str(built), "--parallel", env["P2996_JOBS"]]
    if args.dry_run:
        log.info(
            "build dry run",
            P2996_SDK=env["P2996_SDK"],
            LUA_DIR=env["LUA_DIR"],
            configure=shlex.join(configure),
            compile=shlex.join(command),
        )
        return
    await require_codesign(cfg)
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
        await compile_(command, env, build_log(cfg))
    except subprocess.CalledProcessError as error:
        msg = (
            f"p2996 build: {commit} with include-what-you-use {cfg.iwyu_commit} failed to compile; the previous "
            "install stays active. If include-what-you-use failed, P2996_IWYU_COMMIT may need the clang_NN branch "
            "of the new LLVM major"
        )
        raise P2996Error(msg) from error
    finally:
        stats = await proc.output(launcher, "--show-adv-stats", "--stats-format=json", env=env)
        sccache_stats(cfg).write_text(stats)
    link(last_build(cfg), name)
    log.info("build done", id=name, build=str(built), commit=commit)
