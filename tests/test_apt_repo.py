# Copyright (c) 2026 Raymond Manaloto
"""Tests for `dotfiles_setup.apt_repo`.

Every test drives the injected `fetcher` seam, so nothing here touches the
network — the same seam `gcc_sha` uses. The fixtures are real paragraphs
copied from apt.llvm.org's `llvm-toolchain-resolute-22` index (2026-07-15),
so the naming traps they encode are the ones that actually bit #251.
"""

from __future__ import annotations

import gzip

import pytest
from dotfiles_setup.apt_repo import (
    LLVM_DEV,
    AptPackage,
    RepoQuery,
    available_packages,
    filter_packages,
    llvm_suite,
    parse_packages,
    render_toml,
)

# Real paragraphs from apt.llvm.org resolute-22, trimmed to the fields we read.
# `clang-22` is Section: devel; `libclang-cpp22` is Section: libs (a Depends:
# arrival, never declared); `libomp-22-dev` is the OpenMP trap — it matches no
# substring of "openmp".
_INDEX = b"""\
Package: clang-22
Version: 1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17
Section: devel
Description: C, C++ and Objective-C compiler
 Clang project is a C, C++, Objective-C and Objective-C++ front-end.

Package: libclang-cpp22
Version: 1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17
Section: libs
Description: C++ interface to the Clang library

Package: libomp-22-dev
Version: 1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17
Section: libdevel
Description: LLVM OpenMP runtime - dev package

Package: mlir-22-tools
Version: 1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17
Section: devel
Description: Multi-Level IR Compiler Framework - tools
"""


def _fetcher(_url: str) -> bytes:
    """Stand-in for the curl subprocess; returns the gzipped fixture."""
    return gzip.compress(_INDEX)


class TestLlvmSuite:
    """`llvm_suite` encodes apt.llvm.org's suite naming, including its trap."""

    def test_numbered_version_gets_a_numbered_suite(self) -> None:
        """A major version maps to `llvm-toolchain-<dist>-<major>`."""
        assert llvm_suite("resolute", 22) == "llvm-toolchain-resolute-22"

    def test_dev_maps_to_the_unnumbered_suite(self) -> None:
        """The trap: development is NOT `-23`, it is the bare suite.

        Probed 2026-07-15: `llvm-toolchain-resolute-23` is a 404 while the
        unnumbered suite serves clang 23. Building the numbered form would
        404 for exactly the channel #251 wants next.
        """
        assert llvm_suite("resolute", LLVM_DEV) == "llvm-toolchain-resolute"

    def test_dist_is_not_hardcoded(self) -> None:
        """The Ubuntu codename is a parameter, not baked in."""
        assert llvm_suite("noble", 21) == "llvm-toolchain-noble-21"


class TestRepoQuery:
    """URL construction and the LLVM convenience constructor."""

    def test_packages_url_shape(self) -> None:
        """The index URL follows the standard apt dists/ layout."""
        q = RepoQuery(repo="https://example.test/r", suite="s")
        assert q.packages_url == (
            "https://example.test/r/dists/s/main/binary-amd64/Packages.gz"
        )

    def test_for_llvm_defaults_to_resolute_amd64(self) -> None:
        """amd64 is the image's architecture (R3); the default must match."""
        q = RepoQuery.for_llvm(22)
        assert q.suite == "llvm-toolchain-resolute-22"
        assert q.arch == "amd64"
        assert q.repo == "https://apt.llvm.org/resolute"

    def test_for_llvm_dev_channel(self) -> None:
        """`LLVM_DEV` reaches the unnumbered suite through the constructor."""
        assert RepoQuery.for_llvm(LLVM_DEV).suite == "llvm-toolchain-resolute"

    def test_arch_is_threaded_through(self) -> None:
        """A non-default arch reaches the URL (multi-arch work, #102/#224)."""
        assert "binary-arm64" in RepoQuery.for_llvm(22, arch="arm64").packages_url


class TestParsePackages:
    """deb822 parsing, delegated to python-debian."""

    def test_parses_every_paragraph_sorted(self) -> None:
        """All paragraphs are returned, ordered by package name."""
        pkgs = parse_packages(_INDEX)
        assert [p.name for p in pkgs] == [
            "clang-22",
            "libclang-cpp22",
            "libomp-22-dev",
            "mlir-22-tools",
        ]

    def test_captures_version_and_section(self) -> None:
        """Version and Section are read verbatim from the paragraph."""
        clang = next(p for p in parse_packages(_INDEX) if p.name == "clang-22")
        assert clang.version.startswith("1:22.1.8~++")
        assert clang.section == "devel"

    def test_description_is_the_synopsis_only(self) -> None:
        """A multi-line Description keeps the first line, not the body."""
        clang = next(p for p in parse_packages(_INDEX) if p.name == "clang-22")
        assert clang.description == "C, C++ and Objective-C compiler"

    def test_empty_index_is_empty_not_an_error(self) -> None:
        """An empty body parses to no packages rather than raising."""
        assert parse_packages(b"") == []


class TestAvailablePackages:
    """The fetch+decompress+parse pipeline, through the injected seam."""

    def test_reads_the_query_url(self) -> None:
        """The fetcher is called with exactly the query's index URL."""
        seen: list[str] = []

        def spy(url: str) -> bytes:
            seen.append(url)
            return gzip.compress(_INDEX)

        available_packages(RepoQuery.for_llvm(22), fetcher=spy)
        assert seen == [RepoQuery.for_llvm(22).packages_url]

    def test_decompresses_and_parses(self) -> None:
        """A gzipped index round-trips to parsed packages."""
        pkgs = available_packages(RepoQuery.for_llvm(22), fetcher=_fetcher)
        assert len(pkgs) == 4

    def test_fetcher_failure_propagates(self) -> None:
        """A 404 must surface, never parse as an empty package set.

        `_default_fetcher` raises on a non-zero curl exit precisely so an
        unpublished suite fails loud. If this ever swallowed the error, the
        caller would read "0 packages" and conclude the repo carries nothing —
        a silent false negative of exactly the shape tests/AGENTS.md names.
        """

        def boom(_url: str) -> bytes:
            msg = "curl failed for ...: 404"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError, match="404"):
            available_packages(RepoQuery.for_llvm(23), fetcher=boom)


class TestFilterPackages:
    """Runtime libs arrive via Depends:; declaring them is noise."""

    def test_exclude_runtime_drops_section_libs(self) -> None:
        """`Section: libs` paragraphs are dropped, tool packages kept."""
        pkgs = parse_packages(_INDEX)
        kept = [p.name for p in filter_packages(pkgs, exclude_runtime=True)]
        assert "libclang-cpp22" not in kept
        assert "clang-22" in kept

    def test_default_keeps_everything(self) -> None:
        """Filtering is opt-in; the default is a passthrough."""
        pkgs = parse_packages(_INDEX)
        assert len(filter_packages(pkgs)) == len(pkgs)


class TestRenderToml:
    """The output is pasted into mise-system.toml, so the shape is a contract."""

    def test_declaration_uses_the_apt_prefix(self) -> None:
        """Mise keys bootstrap packages as `manager:package`."""
        pkg = AptPackage("clang-22", "1:22", "devel", "")
        assert pkg.declaration == "apt:clang-22"

    def test_latest_by_default(self) -> None:
        """Unpinned declarations render as `"latest"`, matching the file."""
        out = render_toml([AptPackage("bolt-22", "1:22.1.8", "devel", "")])
        assert out == '"apt:bolt-22" = "latest"'

    def test_pin_emits_the_exact_version(self) -> None:
        """`--pin` renders apt's native `name=version` value."""
        out = render_toml(
            [AptPackage("bolt-22", "1:22.1.8~++2026", "devel", "")], pin=True
        )
        assert out == '"apt:bolt-22" = "1:22.1.8~++2026"'

    def test_openmp_names_itself_libomp(self) -> None:
        """The naming trap, pinned: "openmp" is not a substring of the package.

        #251's plan was written from memory and proposed names that do not
        exist (`apt:mlir-22`). This asserts the enumerator reports what the
        repo actually publishes, which is the whole reason it exists.
        """
        names = [p.name for p in parse_packages(_INDEX)]
        assert "libomp-22-dev" in names
        assert not any("openmp" in n for n in names)
