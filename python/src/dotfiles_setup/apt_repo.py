# Copyright (c) 2026 Raymond Manaloto
"""Enumerate the packages an apt repository publishes.

`bootstrap_packages` parses the packages we *declare* in
`.devcontainer/mise-system.toml` `[bootstrap.packages]`. This module is its
complement: what a repository *offers*, so a declaration can be written from
evidence instead of memory.

Why this exists (#251): the LLVM package names are not guessable, and every
hand-written guess so far has been wrong. Issue #251's own plan proposed
`apt:mlir-22`, which does not exist (`libmlir-22`, `libmlir-22-dev`,
`mlir-22-tools` do); OpenMP ships as `libomp-22-dev`, matching no substring of
"openmp"; and the development channel is the *unnumbered* suite, so the
plausible `llvm-toolchain-resolute-23` is a 404.

Why not the obvious alternatives (`.claude/rules/use-tool-builtins.md`):

- **mise cannot.** `mise bootstrap packages` is apply/status/import/prune/
  upgrade/use. There is no search. `import` reads *installed* packages and
  `dpkg-query` likewise — neither ever sees *available*.
- **`apt-cache` needs the repo configured first**, which is backwards when the
  question is whether to adopt that repo at all. It also needs populated
  `/var/lib/apt/lists`, and the image ships that directory empty (#222).
- **deb822 parsing is not hand-rolled**: `python-debian` (Debian's own
  maintainers; Ubuntu's `python3-debian`) does it, with `use_apt_pkg=False` so
  no libapt is needed and the same code runs in-container and on the host.

Fetching goes through an injected `fetcher` seam defaulting to `curl -fsSL`,
matching `gcc_sha._default_fetcher` — "subprocess is this repo's blessed fetch
mechanism; no HTTP client dependency is introduced". The seam is what makes
this testable offline (`tests/test_apt_repo.py`).
"""

from __future__ import annotations

import gzip
import subprocess
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from debian.deb822 import Packages

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    Fetcher = Callable[[str], bytes]

#: apt.llvm.org's base URL for one Ubuntu release (`resolute` == 26.04).
LLVM_REPO_TEMPLATE = "https://apt.llvm.org/{dist}"

#: The sentinel for apt.llvm.org's development/trunk channel.
#:
#: apt.llvm.org publishes the in-development major under the **unnumbered**
#: suite (`llvm-toolchain-<dist>`), not under `llvm-toolchain-<dist>-<major>`.
#: Probed 2026-07-15: `-21` -> 21.1.8, `-22` -> 22.1.8, unnumbered -> 23.0,
#: and `-23` is a 404.
LLVM_DEV = "dev"


def llvm_suite(dist: str, version: int | str) -> str:
    """The apt.llvm.org suite for `version` on `dist`.

    Args:
        dist: Ubuntu codename, e.g. `resolute` for 26.04.
        version: A major version (`21`, `22`) or :data:`LLVM_DEV` for the
            unnumbered development/trunk suite.

    Takes a *version*, never a channel label. apt.llvm.org's "stable /
    qualification / development" roles shift every release cycle (2026-07-15:
    21 stable, 22 qualification, 23 development), so a label pinned today
    silently becomes a different major later — exactly the drift this repo's
    pinning discipline exists to prevent.
    """
    if version == LLVM_DEV:
        return f"llvm-toolchain-{dist}"
    return f"llvm-toolchain-{dist}-{version}"


@dataclass(frozen=True)
class RepoQuery:
    """One apt repository index: repo + suite + component + architecture."""

    repo: str
    suite: str
    component: str = "main"
    arch: str = "amd64"

    @property
    def packages_url(self) -> str:
        """The `Packages.gz` index URL this query addresses."""
        return (
            f"{self.repo}/dists/{self.suite}/"
            f"{self.component}/binary-{self.arch}/Packages.gz"
        )

    @classmethod
    def for_llvm(
        cls, version: int | str, *, dist: str = "resolute", arch: str = "amd64"
    ) -> RepoQuery:
        """A query for apt.llvm.org's `version` channel on `dist`."""
        return cls(
            repo=LLVM_REPO_TEMPLATE.format(dist=dist),
            suite=llvm_suite(dist, version),
            arch=arch,
        )


@dataclass(frozen=True)
class AptPackage:
    """One paragraph of an apt `Packages` index."""

    name: str
    version: str
    section: str
    description: str

    @property
    def declaration(self) -> str:
        """The `[bootstrap.packages]` key mise expects for this package."""
        return f"apt:{self.name}"


def _default_fetcher(url: str) -> bytes:
    """Fetch `url` with `curl -fsSL` and return the raw body.

    `-f` turns an HTTP 404 into a non-zero exit, so a suite apt.llvm.org has
    not published — the documented failure mode in #251, and the real
    behaviour of `llvm-toolchain-<dist>-23` — fails loudly here instead of
    parsing as an empty package set.

    Raises:
        RuntimeError: when curl exits non-zero.
    """
    proc = subprocess.run(
        ["curl", "-fsSL", url],
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip()
        msg = f"curl failed for {url} (exit {proc.returncode}): {detail}"
        raise RuntimeError(msg)
    return proc.stdout


def parse_packages(raw: bytes) -> list[AptPackage]:
    """Parse a decompressed `Packages` index into `AptPackage` records.

    `use_apt_pkg=False` selects python-debian's pure-python parser, so this
    runs anywhere — including hosts with no libapt.
    """
    out: list[AptPackage] = []
    for para in Packages.iter_paragraphs(raw, use_apt_pkg=False):
        name = para.get("Package")
        if not name:
            continue
        description = (para.get("Description") or "").splitlines()
        out.append(
            AptPackage(
                name=name,
                version=para.get("Version", ""),
                section=para.get("Section", ""),
                description=description[0] if description else "",
            )
        )
    return sorted(out, key=lambda p: p.name)


def available_packages(
    query: RepoQuery, *, fetcher: Fetcher | None = None
) -> list[AptPackage]:
    """Every package `query` publishes, sorted by name.

    Args:
        query: The repository index to read.
        fetcher: Injected for tests; defaults to the curl subprocess.
    """
    fetch = fetcher or _default_fetcher
    return parse_packages(gzip.decompress(fetch(query.packages_url)))


def filter_packages(
    packages: Iterable[AptPackage], *, exclude_runtime: bool = False
) -> list[AptPackage]:
    """Drop paragraphs pulled in as dependencies rather than declared.

    Runtime shared-object packages (`Section: libs`) arrive via `Depends:`
    when a tool package is installed; declaring them in `[bootstrap.packages]`
    adds noise without changing what lands in the image.
    """
    if not exclude_runtime:
        return list(packages)
    return [p for p in packages if p.section != "libs"]


def render_toml(packages: Iterable[AptPackage], *, pin: bool = False) -> str:
    """Render `[bootstrap.packages]` lines for `packages`.

    Args:
        packages: Packages to declare.
        pin: Emit each exact version instead of `"latest"`. apt.llvm.org's
            index carries exactly one build per package and rotates it daily,
            so a pin written here goes stale — see #251.
    """
    return "\n".join(
        f'"{p.declaration}" = {f'"{p.version}"' if pin else '"latest"'}'
        for p in packages
    )


def render_report(query: RepoQuery, packages: list[AptPackage]) -> str:
    """A human-readable listing of what `query` publishes."""
    width = max((len(p.name) for p in packages), default=0)
    lines = [
        f"{query.repo}  {query.suite}  {query.component}/binary-{query.arch}",
        f"{len(packages)} packages",
        "",
    ]
    lines.extend(f"  {p.name:<{width}}  {p.version}" for p in packages)
    return "\n".join(lines) + "\n"


def apt_repo_main(
    query: RepoQuery,
    *,
    toml: bool = False,
    pin: bool = False,
    exclude_runtime: bool = False,
) -> int:
    """CLI entrypoint: list what `query` publishes."""
    try:
        pkgs = available_packages(query)
    except RuntimeError as exc:
        sys.stderr.write(f"FAIL {exc}\n")
        return 1

    pkgs = filter_packages(pkgs, exclude_runtime=exclude_runtime)
    text = render_toml(pkgs, pin=pin) + "\n" if toml else render_report(query, pkgs)
    sys.stdout.write(text)
    return 0
