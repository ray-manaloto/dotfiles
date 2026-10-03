# Copyright (c) 2026 Raymond Manaloto
"""Check exact apt pin publication on both image architectures without docker.

Renovate discovers updates but does not alert on unpublished unchanged pins.
apt-cache needs configured local indexes; apt's solver is the separate
verify-apt-pins gate. Reuse python-debian through apt_repo for index parsing,
LLVM inventory/base metadata through llvm_major, and curl for bounded fetching.
"""

from __future__ import annotations

import gzip
import subprocess
import sys
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from dotfiles_setup import apt_repo, llvm_major

if TYPE_CHECKING:
    from collections.abc import Iterable


@dataclass(frozen=True)
class Finding:
    """An exact pin absent from its upstream indexes on one architecture."""

    name: str
    pinned: str
    active: bool
    arch: str
    kind: Literal["stale", "missing"]
    versions: tuple[str, ...]


def _ubuntu_queries(codename: str, arch: str) -> list[apt_repo.RepoQuery]:
    """Use the canonical ports mirror for every arm64 Ubuntu pocket."""
    return [
        apt_repo.RepoQuery(
            repo=(
                "http://ports.ubuntu.com/ubuntu-ports"
                if arch == "arm64"
                else (
                    "http://security.ubuntu.com/ubuntu"
                    if pocket == "-security"
                    else "http://archive.ubuntu.com/ubuntu"
                )
            ),
            suite=f"{codename}{pocket}",
            arch=arch,
        )
        for pocket in ("", "-updates", "-security")
    ]


def _index_versions(
    queries: Iterable[apt_repo.RepoQuery], fetch: llvm_major.Fetcher
) -> dict[str, set[str]]:
    """Merge pocket versions, refusing HTTP errors or unparsable indexes."""
    versions: dict[str, set[str]] = {}
    for query in queries:
        url = query.packages_url
        status, raw = fetch(url)
        if status != HTTPStatus.OK:
            msg = f"{url}: HTTP {status}, expected 200"
            raise RuntimeError(msg)
        packages = apt_repo.parse_packages(gzip.decompress(raw))
        if not packages or any(not package.version for package in packages):
            msg = f"{url}: empty or malformed Packages index"
            raise ValueError(msg)
        for package in packages:
            versions.setdefault(package.name, set()).add(package.version)
    return versions


def check(
    mise_system_text: str,
    fetch: llvm_major.Fetcher,
    *,
    root: Path | None = None,
) -> list[Finding]:
    """A pin is live only when its exact version is published for each arch."""
    pins = llvm_major.bootstrap_pins(mise_system_text)
    if not pins:
        msg = "no bootstrap apt pins found"
        raise ValueError(msg)
    llvm = llvm_major.llvm_pins(mise_system_text)
    major = llvm_major.pinned_major(mise_system_text)
    codename = llvm_major.codename_for_base_image(root or Path.cwd(), fetch)
    findings = []
    for arch in ("amd64", "arm64"):
        indexes = {
            True: _index_versions(
                [apt_repo.RepoQuery.for_llvm(major, dist=codename, arch=arch)], fetch
            ),
            False: _index_versions(_ubuntu_queries(codename, arch), fetch),
        }
        for name, (pinned, active) in sorted(pins.items()):
            published = indexes[name in llvm].get(name, set())
            if pinned not in published:
                findings.append(
                    Finding(
                        name,
                        pinned,
                        active,
                        arch,
                        "stale" if published else "missing",
                        tuple(sorted(published)),
                    )
                )
    return findings


def render_report(text: str, findings: list[Finding], *, markdown: bool) -> str:
    """Report active/commented counts and publication findings, not a solver verdict."""
    pins = llvm_major.bootstrap_pins(text)
    llvm = llvm_major.llvm_pins(text)
    active = sum(active for _, active in pins.values())
    llvm_active = sum(active for _, active in llvm.values())
    lines = [
        "# apt pin liveness" if markdown else "apt pin liveness",
        "",
        (
            f"{len(pins)} pins ({active} active, {len(pins) - active} commented); "
            f"{len(llvm)} LLVM ({llvm_active} active, "
            f"{len(llvm) - llvm_active} commented); "
            f"{len(pins) - len(llvm)} Ubuntu "
            f"({active - llvm_active} active, "
            f"{len(pins) - active - len(llvm) + llvm_active} commented)."
        ),
        "Architectures: amd64 + arm64.",
        "",
    ]
    if findings:
        lines.append("Exact pins not published in the live index:")
        lines.extend(
            f"- {item.kind}: {item.name} ({item.arch}, "
            f"{'active' if item.active else 'commented'}), pinned {item.pinned}; "
            f"live versions: {', '.join(item.versions) or 'name absent'}"
            for item in findings
        )
    else:
        lines.append("All exact pins are published in the live index for each arch.")
    lines.extend(["", "Installability is checked separately by verify-apt-pins."])
    return "\n".join(lines) + "\n"


def apt_liveness_main(
    root: Path,
    *,
    markdown: bool = False,
    fetch: llvm_major.Fetcher = llvm_major.default_fetcher,
) -> int:
    """Return 0 for all live, 3 for stale/missing pins, or 1 for a failed probe."""
    try:
        text = (root / ".devcontainer/mise-system.toml").read_text()
        findings = check(text, fetch, root=root)
        report = render_report(text, findings, markdown=markdown)
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as exc:
        sys.stderr.write(f"apt pin liveness failed: {exc}\n")
        return 1
    sys.stdout.write(report)
    return 3 if findings else 0
