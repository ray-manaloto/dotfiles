"""bootstrap:toolchain through the real mise, from a copy of the tracked config in a throwaway HOME."""

# The repo had no seam for global tasks; this one extends test_usage.py's real-mise pattern. The real
# mise renders [vars] and runs the task graph; the mise and brew the task calls are stand-ins first
# on PATH, because the real ones would install packages. Offline and without auto-install, nothing
# leaves the temporary directory. The refusal has to come from `brew list --versions` or `brew info
# --json=v2`, the two read-only questions the stand-in answers the way the real brew does.

import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

from p2996 import config

from .conftest import executable

GLOBAL_CONFIG = config.PROJECT.parents[2] / "unix/home/.config/mise/config.toml"
PINS = tomllib.loads(GLOBAL_CONFIG.read_text())["vars"]
# Every exact-version formula conf.d/toolchain.toml declares, at its [vars] version.
INSTALLED = {
    "gcc": PINS["gcc"],
    "llvm": PINS["llvm"],
    "lld": PINS["llvm"],
    "lldb": PINS["llvm"],
    "include-what-you-use": PINS["iwyu"],
    "gdb": PINS["gdb"],
    "make": PINS["make"],
    "pkgconf": PINS["pkgconf"],
}

MISE = """\
import os, sys
with open(os.environ["JOURNAL"], "a") as journal:
    print("mise", *sys.argv[1:], file=journal)
"""

BREW = """\
import json, os, sys
installed = json.loads(os.environ["INSTALLED"])
args = sys.argv[1:]
with open(os.environ["JOURNAL"], "a") as journal:
    print("brew", *args, file=journal)
names = [arg for arg in args[1:] if not arg.startswith("-")]
if args[0] == "list" and "--versions" in args:
    for name in names or installed:
        if name in installed:
            print(name, installed[name])
    sys.exit(0 if all(name in installed for name in names) else 1)
if args[:2] == ["info", "--json=v2"]:
    present = [name for name in names if name in installed]
    found = [{"name": n, "installed": [{"version": installed[n]}], "linked_keg": installed[n]} for n in present]
    print(json.dumps({"formulae": found, "casks": []}))
    sys.exit(0)
sys.exit(2)
"""


def bootstrap(tmp_path: Path, installed: dict[str, str]) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run the real task; returns the finished process and every call its stand-ins journaled."""
    home = tmp_path / "home"
    (home / ".config/mise").mkdir(parents=True)
    shutil.copy(GLOBAL_CONFIG, home / ".config/mise/config.toml")
    bin_dir = tmp_path / "bin"
    executable(bin_dir / "mise", MISE)
    executable(bin_dir / "brew", BREW)
    journal = tmp_path / "journal"
    journal.touch()
    real_mise = shutil.which("mise")
    assert real_mise
    done = subprocess.run(
        # -q: mise would otherwise echo the task's script to stderr, package names and all.
        [real_mise, "run", "-q", "bootstrap:toolchain"],
        cwd=home,
        env={
            "HOME": str(home),
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "JOURNAL": str(journal),
            "INSTALLED": json.dumps(installed),
            "MISE_OFFLINE": "1",
            "MISE_AUTO_INSTALL": "0",
            "MISE_TASK_RUN_AUTO_INSTALL": "0",
            "MISE_NOT_FOUND_AUTO_INSTALL": "0",
        },
        capture_output=True,
        text=True,
        check=False,
    )
    return done, journal.read_text().splitlines()


def changes(journal: list[str]) -> list[str]:
    """Journaled calls that could change the machine: everything but a brew question."""
    return [line for line in journal if not line.startswith(("brew list", "brew info"))]


def named(formula: str, text: str) -> bool:
    return re.search(rf"\b{re.escape(formula)}\b", text) is not None


def test_bootstrap_refuses_a_wrong_compiler_version_before_it_changes_anything(tmp_path: Path) -> None:
    done, journal = bootstrap(tmp_path, INSTALLED | {"gcc": "15.2.0"})
    assert done.returncode != 0, journal
    assert named("gcc", done.stderr), done.stderr
    assert INSTALLED["gcc"] in done.stderr
    assert changes(journal) == []


def test_bootstrap_names_every_absent_compiler_package(tmp_path: Path) -> None:
    packages = {name: pin for name, pin in INSTALLED.items() if name not in ("gcc", "llvm")}
    done, journal = bootstrap(tmp_path, packages)
    assert done.returncode != 0, journal
    assert named("gcc", done.stderr), done.stderr
    assert named("llvm", done.stderr), done.stderr
    assert changes(journal) == []


def test_bootstrap_runs_its_steps_when_every_pinned_package_is_installed(tmp_path: Path) -> None:
    done, journal = bootstrap(tmp_path, INSTALLED)
    assert done.returncode == 0, done.stderr
    assert changes(journal) == [
        "mise bootstrap --only files,packages --yes",
        "mise bootstrap --only files,packages --yes",
        "mise run toolchain:verify",
    ]
