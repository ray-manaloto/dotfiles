"""Copy a checkout's files, never what git ignores, for tests that need the repo outside the real checkout.

A copy of the whole folder takes every build output with it. On 2026-11-13 a worktree's swift/.build held a 24 GB
compilation cache (CompilationCache.noindex/.../data.v1); nine copies at once under pytest -n auto took free space
from 279 GiB to 32 GiB. The tracked files and the untracked ones git does not ignore are a few hundred MB.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parents[2]


def load_scratch_toolchain() -> ModuleType:
    """Load python/home/tests/scratch_toolchain.py under a synthetic package so its relative imports resolve."""
    pkg_name = "_home_tests"
    pkg_dir = REPO / "python/home/tests"
    if pkg_name not in sys.modules:
        pkg_spec = importlib.util.spec_from_file_location(
            pkg_name,
            pkg_dir / "__init__.py",
            submodule_search_locations=[str(pkg_dir)],
        )
        assert pkg_spec and pkg_spec.loader
        pkg = importlib.util.module_from_spec(pkg_spec)
        sys.modules[pkg_name] = pkg
        pkg_spec.loader.exec_module(pkg)
    mod_name = f"{pkg_name}.scratch_toolchain"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(
        mod_name, pkg_dir / "scratch_toolchain.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def copy_checkout(dest: Path, source: Path = REPO) -> Path:
    """dest holding source's tracked files and its untracked, unignored ones (git ls-files --exclude-standard)."""
    listed = subprocess.run(
        ["git", "-C", source, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        check=True,
    ).stdout
    dest.mkdir(parents=True)
    # Bytes, not text: text mode would turn a carriage return in a file name into a newline.
    for name in sorted({os.fsdecode(raw) for raw in listed.split(b"\0")[:-1]}):
        path = source / name
        if path.is_symlink() or path.exists():  # a file deleted but not yet staged is gone
            (dest / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest / name, follow_symlinks=False)
    return dest
