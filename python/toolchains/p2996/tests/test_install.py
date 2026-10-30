import subprocess
from pathlib import Path

import pytest

from p2996 import config, install, source
from p2996.models import Config

# One install tree per build dir p2996 install reads: the main build and the two runtime sub-builds.
TREES = {
    ".": ["clang", "clang-p2996", "clang++-p2996", "llvm-ar"],
    "runtimes/builtins-bins": [],
    "runtimes/runtimes-bins": ["runtime-tool"],
}


def configure_trees(cfg: Config, tmp_path: Path) -> None:
    for tree, programs in TREES.items():
        project = tmp_path / "projects" / tree
        project.mkdir(parents=True)
        for name in programs:
            (project / name).write_text("#!/bin/sh\n")
        listed = " ".join(programs)
        (project / "CMakeLists.txt").write_text(
            "cmake_minimum_required(VERSION 3.20)\nproject(tree NONE)\n"
            + (f"install(PROGRAMS {listed} DESTINATION bin)\n" if programs else "")
        )
        subprocess.run(
            ["cmake", "-S", project, "-B", config.build_dir(cfg) / tree, "-G", "Ninja"], check=True, capture_output=True
        )


@pytest.fixture
def installed(cfg: Config, patches: Path, tmp_path: Path) -> Path:
    source.run(cfg, None, patches)
    configure_trees(cfg, tmp_path)
    install.run(cfg)
    return config.prefix(cfg)


def test_install_writes_the_default_configs(installed: Path) -> None:
    sdk = subprocess.run(["xcrun", "--show-sdk-path"], check=True, capture_output=True, text=True).stdout.strip()
    assert (installed / "bin/arm64-apple-darwin.cfg").read_text().endswith(f"-isysroot {sdk}\n")
    cxx = (installed / "bin/arm64-apple-darwin-clang++.cfg").read_text().splitlines()
    assert cxx[1:] == [
        "@arm64-apple-darwin.cfg",
        f"$-Wl,-L,{installed}/lib",
        f"$-Wl,-rpath,{installed}/lib",
        "$-Wl,-lunwind",
    ]


def test_install_links_every_tool_once_with_the_p2996_suffix(cfg: Config, installed: Path) -> None:
    links = {link.name: link.readlink() for link in config.bin_dir(cfg).iterdir()}
    sha = installed.name
    assert links == {
        "arm64-apple-darwin.cfg": Path(f"../{sha}/bin/arm64-apple-darwin.cfg"),
        "arm64-apple-darwin-clang++.cfg": Path(f"../{sha}/bin/arm64-apple-darwin-clang++.cfg"),
        "clang-p2996": Path(f"../{sha}/bin/clang-p2996"),
        "clang++-p2996": Path(f"../{sha}/bin/clang++-p2996"),
        "llvm-ar-p2996": Path(f"../{sha}/bin/llvm-ar"),
        "runtime-tool-p2996": Path(f"../{sha}/bin/runtime-tool"),
    }
    assert all((config.bin_dir(cfg) / name).exists() for name in links)


def test_reinstall_replaces_stale_links(cfg: Config, installed: Path) -> None:
    (config.bin_dir(cfg) / "stale-p2996").symlink_to("../gone/bin/stale")
    install.run(cfg)
    assert not (config.bin_dir(cfg) / "stale-p2996").is_symlink()
    assert (installed / "bin/llvm-ar").is_file()
