"""p2996 build: configure (every run, so bootstrap.cmake edits apply) and build; a rerun resumes."""

import fcntl
import os
import shlex
import subprocess
import sys
from pathlib import Path

from .config import RESOURCES, build_dir, prefix, src
from .models import Config

_CLEARED = ("CC", "CXX", "CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "SDKROOT")


def _xcrun(*args: str) -> str:
    return subprocess.run(["xcrun", *args], check=True, capture_output=True, text=True).stdout.strip()


def run(cfg: Config, *, dry_run: bool, bootstrap: Path = RESOURCES / "bootstrap.cmake") -> None:
    env = {k: v for k, v in os.environ.items() if k not in _CLEARED}
    env["P2996_SDK"] = str(Path(_xcrun("--show-sdk-path")).resolve())
    env["NINJA_STATUS"] = "[%f/%t %es] "
    # lua is on PATH through the mise shims, whose prefix has no headers; FindLua honours LUA_DIR.
    lua = subprocess.run(["mise", "where", "lua"], check=True, capture_output=True, text=True)
    env["LUA_DIR"] = lua.stdout.strip()
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
        f"-DCMAKE_C_COMPILER={_xcrun('-f', 'clang')}",
        f"-DCMAKE_CXX_COMPILER={_xcrun('-f', 'clang++')}",
        f"-DCMAKE_INSTALL_PREFIX={prefix(cfg)}",
        # This project's venv: the locked opt-viewer and MLIR modules. lldb links its base python,
        # so a python upgrade needs a rebuild.
        f"-DPython3_EXECUTABLE={sys.executable}",
        "-DLLDB_ENABLE_PYTHON=ON",
    ]
    compile_ = ["cmake", "--build", str(build_dir(cfg)), "--parallel", "4"]
    if dry_run:
        print(f"P2996_SDK={env['P2996_SDK']} LUA_DIR={env['LUA_DIR']} {shlex.join(configure)}\n{shlex.join(compile_)}")
        return
    # One heavy build at a time: the gate the legacy host_lock.py takes, held without waiting.
    lock_path = Path(cfg.lock)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            msg = "p2996 build: another heavy build holds the lock"
            raise SystemExit(msg) from None
        subprocess.run(configure, check=True, env=env)
        subprocess.run(compile_, check=True, env=env)
