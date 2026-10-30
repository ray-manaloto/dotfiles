"""p2996 install: install into ROOT/<commit>, write the default .cfg files, link ROOT/bin/*-p2996."""

import os
import shutil
import subprocess
from pathlib import Path

from .config import bin_dir, build_dir, commit, prefix
from .models import Config


def run(cfg: Config) -> None:
    sha, pre, links, build = commit(cfg), prefix(cfg), bin_dir(cfg), build_dir(cfg)
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("DESTDIR", "CMAKE_INSTALL_MODE", "CMAKE_INSTALL_PARALLEL_LEVEL")
    }
    for tree in (build, build / "runtimes/builtins-bins", build / "runtimes/runtimes-bins"):
        subprocess.run(["cmake", "--install", str(tree), "--prefix", str(pre)], check=True, env=env)
    # Clang reads <triple>.cfg, then arm64-apple-darwin<N>.cfg, then the unversioned name from its own
    # resolved bin dir; only the unversioned names are written, so a macOS bump never shadows them.
    sdk = subprocess.run(["xcrun", "--show-sdk-path"], check=True, capture_output=True, text=True).stdout.strip()
    (pre / "bin/arm64-apple-darwin.cfg").write_text(
        f"# P2996 default config for every driver mode on arm64 macOS; the SDK is xcrun's.\n-isysroot {sdk}\n"
    )
    (pre / "bin/arm64-apple-darwin-clang++.cfg").write_text(
        "# C++ driver: the SDK, plus the P2996 libc++, libc++abi and libunwind at link time ($ = link only).\n"
        f"@arm64-apple-darwin.cfg\n$-Wl,-L,{pre}/lib\n$-Wl,-rpath,{pre}/lib\n$-Wl,-lunwind\n"
    )
    # LLVM's own *-p2996 drivers and the .cfg files keep their names; every other tool gets -p2996
    # unless LLVM already installed that suffixed name (clang -> clang-p2996).
    shutil.rmtree(links, ignore_errors=True)
    links.mkdir(parents=True)
    for tool in sorted((pre / "bin").iterdir()):
        name = tool.name
        if name.endswith(("-p2996", ".cfg")):
            link = name
        elif (tool.parent / f"{name}-p2996").exists():
            continue
        else:
            link = f"{name}-p2996"
        (links / link).symlink_to(f"../{sha}/bin/{name}")
    # Tools that find their headers from their own path, not its resolved target (clang-scan-deps
    # looks in ROOT/bin/../lib/clang), need ROOT to look like the prefix (DL-761).
    for name in ("include", "lib", "libexec", "share"):
        view = Path(cfg.root) / name
        view.unlink(missing_ok=True)
        if (pre / name).is_dir():
            view.symlink_to(f"{sha}/{name}")
    print(f"p2996 install: {pre}, links in {links}")
