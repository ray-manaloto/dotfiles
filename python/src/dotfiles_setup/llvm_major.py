# Copyright (c) 2026 Raymond Manaloto
"""Detect GA LLVM majors, gate on IWYU/freeze, and keep consumers tied to pins.

gh provides authenticated pagination, curl preserves HTTP status, and apt_repo
uses Debian's index parser. None owns the repository's GA + served + dual-arch
IWYU/freeze policy or its pin inventory; only that repository policy lives here.
"""

from __future__ import annotations

import ast
import difflib
import json
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from functools import cache
from http import HTTPStatus
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from dotfiles_setup import apt_repo
from dotfiles_setup.p2996_hash import _extract_bake_variable

if TYPE_CHECKING:
    from pathlib import Path

Fetcher = Callable[[str], tuple[int, bytes]]
ReleaseFetcher = Callable[[], list[dict]]
GitHubFetcher = Callable[[str], dict | list[dict]]

_SYSTEM = ".devcontainer/mise-system.toml"
_DOCKER = ".devcontainer/Dockerfile"
_IWYU_URL = "https://api.anaconda.org/package/conda-forge/include-what-you-use/files"
_IWYU_TOOL = "conda:include-what-you-use"
_LIBLLVM = re.compile(r"^libllvm(\d+)\b")
_ANCHOR = re.compile(r"^clang-(\d+)$")
_PIN = re.compile(
    r'^(?P<prefix>[ \t]*(?P<comment>#[ \t]*)?)"apt:(?P<name>[^"]+)"'
    r'(?P<space>[ \t]*=[ \t]*)"(?P<version>[^"]+)"(?P<suffix>[^\n]*)$',
    re.MULTILINE,
)
_APT_LLVM_VERSION = re.compile(r"^\d+:\d+(?:\.\d+)*~\+\+\d{14}\+[0-9a-f]+-1~exp1~")
_APT_BUILD = re.compile(r"\+([0-9a-f]{12})-1~exp1~")
_FREEZE_AGE = timedelta(days=14)
_PACKAGE_SECTION = re.compile(r"(?ms)^\[bootstrap\.packages\]\s*\n(.*?)(?=^\[|\Z)")
_LITERAL = re.compile(
    r"/usr/lib/llvm-\d+\b|llvm-toolchain-[\w%{}.-]+-\d+\b|"
    r"(?:apt:)?clang-\d+\b"
)


@dataclass(frozen=True)
class Freeze:
    """One candidate major's release-branch and live suite freeze evidence."""

    major: int
    branch_head: str
    tag: str
    tag_commit: str
    ahead_of_tag: int
    apt_build: str
    release_date: datetime
    frozen: bool
    apt_matches_head: bool


@dataclass(frozen=True)
class Detection:
    """The selector's inputs, probed gates, target, and hold explanation."""

    codename: str
    pinned: int
    newest_ga: int
    target: int
    served: dict[int, bool]
    trunk: int
    iwyu_ready: dict[int, bool]
    held_on: int | None
    reason: str
    frozen: dict[int, bool] = field(default_factory=dict)
    freeze_evidence: dict[int, Freeze] = field(default_factory=dict)


@dataclass(frozen=True)
class BumpPlan:
    """A fully validated pin inventory and exact before/after file contents."""

    detection: Detection
    pins: dict[str, tuple[str, bool]]
    before: dict[str, str]
    after: dict[str, str]
    iwyu_pin: str | None = None

    def render(self) -> str:
        """Show the inventory and unified diffs without changing any file."""
        active = sum(active for _, active in self.pins.values())
        lines = [
            (
                f"LLVM {self.detection.pinned} -> {self.detection.target}: "
                f"{len(self.pins)} pins ({active} active, "
                f"{len(self.pins) - active} commented), amd64 + arm64"
            ),
            f"versions: {sorted({version for version, _ in self.pins.values()})}",
            (
                f"IWYU pin: {self.iwyu_pin}"
                if self.iwyu_pin is not None
                else "IWYU pin: not planned (explicit control; gates skipped)"
            ),
            "pin set:",
            *[
                f'{"" if active else "# "}"apt:{name}" = "{version}"'
                for name, (version, active) in sorted(self.pins.items())
            ],
            "diff:",
        ]
        diff = "".join(
            "".join(
                difflib.unified_diff(
                    self.before[name].splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=name,
                    tofile=name,
                )
            )
            for name, content in self.after.items()
        )
        return "\n".join(lines) + "\n" + (diff or "(empty)\n")

    def write(self, root: Path) -> None:
        """Write changed files only after verifying the entire snapshot."""
        for name, content in self.before.items():
            if (root / name).read_text() != content:
                msg = f"{name} changed after planning; refusing to write"
                raise RuntimeError(msg)
        for name, content in self.after.items():
            if content != self.before[name]:
                (root / name).write_text(content)


def default_fetcher(url: str) -> tuple[int, bytes]:
    """Fetch without following redirects or folding HTTP errors into absence."""
    result = subprocess.run(
        ["curl", "-sS", "--max-time", "60", "--write-out", "\n%{http_code}", url],
        capture_output=True,
        check=False,
        timeout=70,
    )
    if result.returncode:
        msg = f"curl failed for {url}: {result.stderr.decode(errors='replace').strip()}"
        raise RuntimeError(msg)
    body, _, status = result.stdout.rpartition(b"\n")
    return int(status), body


def fetch_releases() -> list[dict]:
    """Read every release page with authenticated gh, never releases/latest."""
    result = subprocess.run(
        ["gh", "api", "--paginate", "--slurp", "repos/llvm/llvm-project/releases"],
        capture_output=True,
        check=False,
        timeout=120,
    )
    if result.returncode:
        msg = f"gh releases failed: {result.stderr.decode(errors='replace').strip()}"
        raise RuntimeError(msg)
    return [release for page in json.loads(result.stdout) for release in page]


def default_gh(endpoint: str) -> dict | list[dict]:
    """Read a GitHub object through authenticated gh; HTTP failures raise."""
    if endpoint == "repos/llvm/llvm-project/releases":
        return fetch_releases()
    result = subprocess.run(
        ["gh", "api", "--include", endpoint],
        capture_output=True,
        check=False,
        timeout=120,
    )
    if result.returncode:
        msg = f"gh {endpoint} failed: {result.stderr.decode(errors='replace').strip()}"
        raise RuntimeError(msg)
    headers, separator, body = result.stdout.replace(b"\r\n", b"\n").partition(b"\n\n")
    status = re.match(rb"HTTP/\S+ (\d{3})\b", headers)
    if not separator or status is None:
        msg = f"gh {endpoint}: missing HTTP status"
        raise ValueError(msg)
    if int(status[1]) != HTTPStatus.OK:
        msg = f"gh {endpoint}: HTTP {int(status[1])}, expected 200"
        raise RuntimeError(msg)
    payload = json.loads(body)
    if not isinstance(payload, dict):
        msg = f"gh {endpoint}: expected a JSON object"
        raise TypeError(msg)
    return payload


def _gh_object(endpoint: str, gh: GitHubFetcher) -> dict:
    """Validate the object shape before reading branch/commit/compare evidence."""
    payload = gh(endpoint)
    if not isinstance(payload, dict):
        msg = f"gh {endpoint}: expected a JSON object"
        raise TypeError(msg)
    return payload


def _gh_releases(gh: GitHubFetcher) -> list[dict]:
    """Read the same paginated GA list supplied to the candidate detector."""
    payload = gh("repos/llvm/llvm-project/releases")
    if not isinstance(payload, list):
        msg = "gh releases: expected a JSON list"
        raise TypeError(msg)
    return payload


def _package_section(text: str) -> str:
    """Limit pin matching to the declared bootstrap package table."""
    match = _PACKAGE_SECTION.search(text)
    return match.group(1) if match else ""


def _anchor(text: str) -> tuple[int, str]:
    """Validate the single active clang anchor and its Debian version major."""
    packages = tomllib.loads(text).get("bootstrap", {}).get("packages", {})
    anchors = [
        (name, value)
        for name, value in packages.items()
        if re.fullmatch(r"apt:clang-\d+", name)
    ]
    inventory_anchors = [
        pin
        for pin in _PIN.finditer(_package_section(text))
        if _ANCHOR.fullmatch(pin["name"])
    ]
    if len(anchors) != 1 or len(inventory_anchors) != 1:
        msg = "expected exactly one apt:clang-<N> anchor in [bootstrap.packages]"
        raise TypeError(msg)
    name, value = anchors[0]
    major = int(name.rsplit("-", maxsplit=1)[1])
    if not isinstance(value, str):
        msg = f"{name} must have a string pin"
        raise TypeError(msg)
    version = re.match(r"(?:\d+:)?(\d+)\b", value)
    if version is None or int(version.group(1)) != major:
        msg = f"{name} contradicts its version {value!r}"
        raise ValueError(msg)
    return major, value


def llvm_pins(mise_system_text: str) -> dict[str, tuple[str, bool]]:
    """Validate parity, then return active/commented apt.llvm.org snapshot pins."""
    pinned_major(mise_system_text)
    return {
        name: pin
        for name, pin in bootstrap_pins(mise_system_text).items()
        if _APT_LLVM_VERSION.match(pin[0])
    }


def bootstrap_pins(mise_system_text: str) -> dict[str, tuple[str, bool]]:
    """Return all apt pins, rejecting active/commented duplicates with line numbers."""
    section = _PACKAGE_SECTION.search(mise_system_text)
    if section is None:
        return {}
    pins: dict[str, tuple[str, bool]] = {}
    lines: dict[str, int] = {}
    for match in _PIN.finditer(section[1]):
        name = match["name"]
        line = mise_system_text.count("\n", 0, section.start(1) + match.start()) + 1
        if name in pins:
            msg = f"duplicate apt package {name!r} on lines {lines[name]} and {line}"
            raise ValueError(msg)
        pins[name] = (match["version"], not bool(match["comment"]))
        lines[name] = line
    return pins


def pinned_major(mise_system_text: str) -> int:
    """Derive the anchor major and reject mixed apt.llvm.org snapshot pins."""
    major, value = _anchor(mise_system_text)
    for pin in _PIN.finditer(_package_section(mise_system_text)):
        if _APT_LLVM_VERSION.match(pin["version"]):
            if pin["version"] != value:
                msg = f"LLVM pin {pin['name']} has mixed version strings"
                raise ValueError(msg)
            # The suite has four major-less runtime names; only development
            # and major-suffixed family names encode the toolchain major.
            tokens = re.findall(r"(?:-|cpp|libllvm)(\d+)(?=-|$)", pin["name"])
            if any(int(token) != major for token in tokens):
                msg = f"LLVM pin {pin['name']} has mixed majors (anchor {major})"
                raise ValueError(msg)
    return major


def _body(url: str, fetch: Fetcher) -> bytes:
    """Adapt status-aware fetching to apt_repo's bytes-only parser seam."""
    status, body = fetch(url)
    if status != HTTPStatus.OK:
        msg = f"{url}: HTTP {status}, expected 200"
        raise RuntimeError(msg)
    return body


def codename_for_base_image(root: Path, fetch: Fetcher) -> str:
    """Resolve Ubuntu metadata after checking Dockerfile/bake base agreement."""
    docker = (root / _DOCKER).read_text()
    match = re.search(r"(?m)^ARG BASE_IMAGE=(\S+)", docker)
    bake = _extract_bake_variable((root / "docker-bake.hcl").read_text(), "BASE_IMAGE")
    if match is None or match.group(1) != bake:
        msg = "BASE_IMAGE disagrees between Dockerfile and docker-bake.hcl"
        raise ValueError(msg)
    ubuntu = re.fullmatch(r"ubuntu:(\d{2}\.\d{2})@sha256:[0-9a-f]+", bake)
    if ubuntu is None:
        msg = f"BASE_IMAGE is not a digest-pinned Ubuntu YY.MM image: {bake}"
        raise ValueError(msg)
    for endpoint in ("meta-release", "meta-release-development"):
        raw = _body(f"https://changelogs.ubuntu.com/{endpoint}", fetch).decode()
        for block in re.split(r"\n\s*\n", raw):
            fields = dict(
                line.split(": ", 1) for line in block.splitlines() if ": " in line
            )
            if fields.get("Version", "").startswith(ubuntu.group(1)) and fields.get(
                "Dist"
            ):
                return fields["Dist"]
    msg = f"Ubuntu {ubuntu.group(1)} absent from both meta-release endpoints"
    raise ValueError(msg)


def _ga_tags(fetch_releases: ReleaseFetcher) -> dict[tuple[int, int, int], str]:
    """Index GA tags by numeric version, excluding draft, RC and init releases."""
    tags = {}
    for release in fetch_releases():
        if release.get("prerelease") is False and release.get("draft") is False:
            match = re.fullmatch(
                r"llvmorg-(\d+)\.(\d+)\.(\d+)", release.get("tag_name", "")
            )
            if match:
                tags[(int(match[1]), int(match[2]), int(match[3]))] = match.group(0)
    if not tags:
        msg = "no GA llvmorg-MAJOR.MINOR.PATCH releases found"
        raise ValueError(msg)
    return tags


def newest_ga_major(fetch_releases: ReleaseFetcher) -> int:
    """Select the greatest GA major, excluding draft, RC and init releases."""
    return max(_ga_tags(fetch_releases))[0]


def _commit_sha(value: object, site: str) -> str:
    """Require full commit identities rather than an unchecked prefix."""
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        msg = f"{site}: expected a full commit SHA"
        raise ValueError(msg)
    return value


def _suite_freeze_build(
    major: int, codename: str, fetch: Fetcher
) -> tuple[str, datetime]:
    """Read the live clang build and timezone-aware Release Date using apt_repo."""
    suite = apt_repo.llvm_suite(codename, major)
    release = _body(
        f"https://apt.llvm.org/{codename}/dists/{suite}/Release", fetch
    ).decode()
    dates = [
        line.removeprefix("Date: ")
        for line in release.splitlines()
        if line.startswith("Date: ")
    ]
    if len(dates) != 1:
        msg = f"Release {suite}: expected exactly one Date line"
        raise ValueError(msg)
    release_date = parsedate_to_datetime(dates[0])
    if release_date.tzinfo is None:
        msg = f"Release {suite}: Date must have a timezone"
        raise ValueError(msg)
    packages = apt_repo.available_packages(
        apt_repo.RepoQuery.for_llvm(major, dist=codename),
        fetcher=lambda url: _body(url, fetch),
    )
    versions = [
        package.version for package in packages if package.name == f"clang-{major}"
    ]
    if len(versions) != 1:
        msg = (
            f"{suite}/main/binary-amd64/Packages.gz: "
            f"expected exactly one clang-{major} version"
        )
        raise ValueError(msg)
    version = versions[0]
    match = _APT_BUILD.search(version)
    if (
        _APT_LLVM_VERSION.match(version) is None
        or re.match(rf"\d+:{major}\.", version) is None
        or match is None
    ):
        msg = f"unparsable clang-{major} apt version {version!r}"
        raise ValueError(msg)
    return match.group(1), release_date.astimezone(UTC)


def freeze_state(
    major: int,
    codename: str,
    fetch: Fetcher,
    gh: GitHubFetcher,
    *,
    now: datetime,
) -> Freeze:
    """Require tag/tag+1, an apt build of head, and at least 14 quiet days.

    GitHub exposes commit comparisons and apt exposes build metadata, but neither
    supplies this repository's combined readiness rule. Reuse the detector's
    release snapshot when supplied; a missing branch or unreadable probe raises.
    """
    tags = {
        version: tag
        for version, tag in _ga_tags(lambda: _gh_releases(gh)).items()
        if version[0] == major
    }
    if not tags:
        msg = f"no GA llvmorg-{major} tag found"
        raise ValueError(msg)
    if now.tzinfo is None:
        msg = "freeze clock must have a timezone"
        raise ValueError(msg)
    tag = tags[max(tags)]
    repo = "repos/llvm/llvm-project"
    branch = f"release/{major}.x"
    head = _commit_sha(
        _gh_object(f"{repo}/branches/{branch}", gh)["commit"]["sha"], branch
    )
    tag_commit = _commit_sha(_gh_object(f"{repo}/commits/{tag}", gh)["sha"], tag)
    ahead = _gh_object(f"{repo}/compare/{tag}...{branch}", gh)["ahead_by"]
    if type(ahead) is not int or ahead < 0:
        msg = f"{branch}: ahead_by must be a nonnegative integer"
        raise ValueError(msg)
    build, release_date = _suite_freeze_build(major, codename, fetch)
    apt_matches_head = build == head[:12]
    frozen = ahead <= 1 and apt_matches_head and now - release_date >= _FREEZE_AGE
    return Freeze(
        major,
        head,
        tag,
        tag_commit,
        ahead,
        build,
        release_date,
        frozen,
        apt_matches_head,
    )


def _freeze_summary(evidence: Freeze) -> str:
    """Explain all freeze axes in a single line, including a held apt build."""
    relation = "matches" if evidence.apt_matches_head else "\u2260"
    return (
        f"release/{evidence.major}.x {evidence.ahead_of_tag} ahead of {evidence.tag}; "
        f"apt build {evidence.apt_build} {relation} head; "
        f"suite published {evidence.release_date.date()} (Release Date)"
    )


def suite_served(codename: str, major: int, fetch: Fetcher) -> bool:
    """Accept only a direct 200 with the suite's exact Codename line; 404 is no."""
    suite = apt_repo.llvm_suite(codename, major)
    status, body = fetch(f"https://apt.llvm.org/{codename}/dists/{suite}/Release")
    if status == HTTPStatus.NOT_FOUND:
        return False
    if status != HTTPStatus.OK:
        msg = f"Release {suite}: HTTP {status}, expected 200 or 404"
        raise RuntimeError(msg)
    return f"Codename: {suite}".encode() in body.splitlines()


def _iwyu_build_key(file: dict) -> tuple[tuple[int, ...], int]:
    """Compare dotted integer versions numerically, then conda build numbers."""
    segments = file["version"].split(".")
    if not all(re.fullmatch(r"\d+", segment) for segment in segments):
        msg = f"non-integer IWYU version {file['version']!r}"
        raise ValueError(msg)
    return tuple(map(int, segments)), int(file["attrs"]["build_number"])


def _libllvm_major(deps: list[str], site: str) -> int:
    """Require exactly one libllvm dependency in API or lock metadata."""
    majors = [int(match.group(1)) for dep in deps if (match := _LIBLLVM.match(dep))]
    if len(majors) != 1:
        msg = f"{site} needs exactly one libllvm<N> dependency"
        raise ValueError(msg)
    return majors[0]


def _iwyu_newest_major(builds: list[dict], subdir: str) -> int:
    """Validate tied newest builds within one version and architecture."""
    newest_key = max(map(_iwyu_build_key, builds))
    majors = {
        _libllvm_major(build["attrs"].get("depends", []), f"newest IWYU {subdir} build")
        for build in builds
        if _iwyu_build_key(build) == newest_key
    }
    if len(majors) != 1:
        msg = (
            f"ambiguous newest IWYU {subdir} builds have "
            f"libllvm majors {sorted(majors)}"
        )
        raise ValueError(msg)
    return majors.pop()


def iwyu_versions_for(major: int, fetch: Fetcher) -> list[str]:
    """Return numerically sorted versions supporting the major on both arches."""
    files = json.loads(_body(_IWYU_URL, fetch))
    if not isinstance(files, list):
        msg = "IWYU files response must be a JSON list"
        raise TypeError(msg)
    subdirs = ("linux-64", "linux-aarch64")
    versions: dict[str, dict[str, list[dict]]] = {}
    for file in files:
        subdir = file.get("attrs", {}).get("subdir")
        if "main" in file.get("labels", []) and subdir in subdirs:
            versions.setdefault(file["version"], {}).setdefault(subdir, []).append(file)
    usable = {
        version: builds
        for version, builds in versions.items()
        if all(subdir in builds for subdir in subdirs)
    }
    if not usable:
        msg = "IWYU has no usable main-label versions for linux-64 and linux-aarch64"
        raise ValueError(msg)
    matching = []
    for version, builds in usable.items():
        targets = [_iwyu_newest_major(builds[subdir], subdir) for subdir in subdirs]
        if targets == [major, major]:
            matching.append(version)
    return sorted(matching, key=lambda version: tuple(map(int, version.split("."))))


def iwyu_ready(major: int, fetch: Fetcher) -> bool:
    """Accept any version whose newest Linux builds both target the major."""
    return bool(iwyu_versions_for(major, fetch))


def iwyu_pin_for(major: int, fetch: Fetcher) -> str:
    """Select the newest compatible version, refusing an unsupported major."""
    versions = iwyu_versions_for(major, fetch)
    if not versions:
        msg = f"IWYU has no dual-arch version targeting libllvm{major}"
        raise ValueError(msg)
    return versions[-1]


def iwyu_lock_state(lock_text: str) -> tuple[str, dict[str, int]]:
    """Read IWYU's locked version and the two published Linux libllvm majors."""
    tool = tomllib.loads(lock_text)["tools"][_IWYU_TOOL][0]
    version = tool["version"]
    if not isinstance(version, str):
        msg = "IWYU lock version must be a string"
        raise TypeError(msg)
    majors = {
        platform: _libllvm_major(tool[f"platforms.{platform}"]["conda_deps"], platform)
        for platform in ("linux-x64", "linux-arm64")
    }
    return version, majors


def trunk_major(codename: str, fetch: Fetcher) -> int:
    """Read the single clang-K anchor from the unnumbered amd64 index."""
    packages = apt_repo.available_packages(
        apt_repo.RepoQuery.for_llvm(apt_repo.LLVM_DEV, dist=codename),
        fetcher=lambda url: _body(url, fetch),
    )
    majors = {
        int(match.group(1))
        for package in packages
        if (match := _ANCHOR.fullmatch(package.name))
    }
    if len(majors) != 1:
        msg = "trunk index must have exactly one clang-<K> anchor"
        raise ValueError(msg)
    return majors.pop()


def _target_reason(
    codename: str,
    span: tuple[int, int],
    served: dict[int, bool],
    ready: dict[int, bool],
    evidence: dict[int, Freeze],
) -> tuple[int, int | None, str]:
    """Apply both independent gates to every served candidate without re-gating P."""
    pinned, newest = span
    candidates = [major for major, available in served.items() if available]
    if not candidates:
        msg = f"no suite served in [{pinned}, {newest}] for {codename}"
        raise RuntimeError(msg)
    eligible = [
        major
        for major in candidates
        if major == pinned or (ready[major] and evidence[major].frozen)
    ]
    if not eligible:
        msg = (
            "pinned suite is gone and all served replacements are "
            "IWYU-blocked or freeze-blocked"
        )
        raise RuntimeError(msg)
    target = max(eligible)
    served_target = max(candidates)
    held = served_target if served_target > target else None
    if held is not None:
        gates = []
        if not ready[held]:
            gates.append("IWYU")
        if not evidence[held].frozen:
            gates.append("freeze")
        reason = (
            f"{held} GA+served, held: {', '.join(gates)}; "
            + (
                "IWYU: conda-forge include-what-you-use has no version whose "
                "newest builds on both Linux architectures "
                f"target libllvm{held}; "
                if not ready[held]
                else ""
            )
            + f"freeze: {_freeze_summary(evidence[held])}"
        )
    elif served[newest]:
        reason = f"M={newest} served"
    else:
        reason = (
            f"M={newest} not served for {codename}; "
            f"highest served in [P, M-1] = {target}"
        )
    return target, held, reason


def detect(
    root: Path,
    fetch: Fetcher = default_fetcher,
    releases: ReleaseFetcher = fetch_releases,
    *,
    gh: GitHubFetcher = default_gh,
    now: datetime | None = None,
) -> Detection:
    """Detect using GA + served + IWYU + freeze; trunk assertions never select."""
    fetch = cache(fetch)
    releases = cache(releases)
    now = datetime.now(UTC) if now is None else now
    pinned = pinned_major((root / _SYSTEM).read_text())
    codename = codename_for_base_image(root, fetch)
    newest = newest_ga_major(releases)
    if newest < pinned:
        msg = f"newest GA {newest} is below pinned {pinned}; refusing downgrade"
        raise ValueError(msg)
    served = {
        major: suite_served(codename, major, fetch)
        for major in range(pinned, newest + 1)
    }
    candidates = [
        major for major, available in served.items() if available and major > pinned
    ]
    ready = {major: iwyu_ready(major, fetch) for major in candidates}

    def github(endpoint: str) -> dict | list[dict]:
        if endpoint == "repos/llvm/llvm-project/releases":
            return releases()
        return gh(endpoint)

    evidence = {
        major: freeze_state(major, codename, fetch, github, now=now)
        for major in candidates
    }
    target, held, reason = _target_reason(
        codename, (pinned, newest), served, ready, evidence
    )
    trunk = trunk_major(codename, fetch)
    if trunk - 1 not in {newest, newest + 1}:
        msg = f"trunk cross-check: K-1={trunk - 1} outside {{M, M+1}} for M={newest}"
        raise ValueError(msg)
    if suite_served(codename, trunk, fetch):
        msg = f"trunk cross-check: numbered suite for trunk {trunk} is served"
        raise ValueError(msg)
    return Detection(
        codename,
        pinned,
        newest,
        target,
        served,
        trunk,
        ready,
        held,
        reason,
        frozen={major: state.frozen for major, state in evidence.items()},
        freeze_evidence=evidence,
    )


def _python_violations(path: Path) -> list[str]:
    """Inspect code strings (including f-strings), exempting comments/docstrings."""
    tree = ast.parse(path.read_text())
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(
            node, ast.Module | ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
        )
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    violations = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
            and _LITERAL.search(node.value)
        ):
            violations.append(f"{path.name}:{node.lineno}: LLVM major literal in code")
        if (
            isinstance(node, ast.Call)
            and any(
                isinstance(arg, ast.Constant) and arg.value == "--llvm-version"
                for arg in node.args
            )
            and any(
                keyword.arg == "default"
                and not (
                    isinstance(keyword.value, ast.Constant)
                    and keyword.value.value is None
                )
                for keyword in node.keywords
            )
        ):
            violations.append(
                f"{path.name}:{node.lineno}: --llvm-version default must be None"
            )
    return violations


def _registry_urls(text: str) -> list[str]:
    """Find apt.llvm.org registryUrls wherever Renovate nests its managers."""

    def visit(node: object) -> list[str]:
        if isinstance(node, dict):
            return [
                url
                for url in node.get("registryUrls", [])
                if urlsplit(url).hostname == "apt.llvm.org"
            ] + [url for value in node.values() for url in visit(value)]
        if isinstance(node, list):
            return [url for value in node for url in visit(value)]
        return []

    return visit(json.loads(text))


def _renovate_violations(text: str, codename: str | None = None) -> list[str]:
    """Bind the native capture/template route and exclude LLVM URL overrides."""
    config = json.loads(text)
    managers = [
        manager
        for manager in config.get("customManagers", [])
        if "apt.llvm.org" in manager.get("registryUrlTemplate", "")
    ]
    if len(managers) != 1 or _registry_urls(text):
        return [
            "renovate.json needs exactly one LLVM registryUrlTemplate, no literal URL"
        ]
    manager = managers[0]
    template = manager["registryUrlTemplate"]
    match = re.fullmatch(
        r"\{\{#if llvmMajor\}\}https://apt\.llvm\.org/(?P<dist>[a-z]+)"
        r"\?suite=llvm-toolchain-(?P=dist)-\{\{\{llvmMajor\}\}\}"
        r"&components=main&binaryArch=amd64\{\{else\}\}"
        r"https://archive\.ubuntu\.com/ubuntu\?suite=(?P=dist)"
        r"&components=main&binaryArch=amd64\{\{/if\}\}",
        template,
    )
    if match is None or (codename is not None and match["dist"] != codename):
        return [
            "renovate.json suite template must follow llvmMajor and the base codename"
        ]
    # The quote before currentValue anchors this capture at the value's start;
    # Renovate's file-level regex cannot use ^ to anchor an individual value.
    snapshot = _APT_LLVM_VERSION.pattern.removeprefix("^").replace(
        r"\d+:\d+", r"\d+:(?<llvmMajor>\d+)", 1
    )
    pattern = (
        r'"apt:(?<depName>[a-z0-9.+-]+)"\s*=\s*"'
        rf'(?<currentValue>(?:{snapshot}[^"]*|[0-9][^"]*))"'
    )
    if (
        manager.get("matchStrings") != [pattern]
        or manager.get("datasourceTemplate") != "deb"
    ):
        return [
            "renovate.json LLVM version-major capture must preserve snapshot routing"
        ]
    selector = f"/{_APT_LLVM_VERSION.pattern}/"
    rules = config.get("packageRules", [])
    groups = [
        rule for rule in rules if rule.get("groupName") == "apt.llvm.org LLVM debs"
    ]
    violations = []
    if len(groups) != 1 or groups[0].get("matchCurrentValue") != selector:
        violations.append("renovate.json LLVM group must match the snapshot signature")
    overrides = [rule for rule in rules if rule.get("registryUrls")]
    if any(rule.get("matchCurrentValue") != f"!{selector}" for rule in overrides):
        violations.append(
            "renovate.json registryUrls overrides must exclude LLVM snapshots"
        )
    pockets = [
        rule
        for rule in overrides
        if rule.get("matchDatasources") == ["deb"]
        and rule.get("matchCurrentValue") == f"!{selector}"
    ]
    urls = [
        f"https://{host}.ubuntu.com/ubuntu?suite={match['dist']}{pocket}"
        "&components=main&binaryArch=amd64"
        for host, pocket in (
            ("archive", ""),
            ("archive", "-updates"),
            ("security", "-security"),
        )
    ]
    if len(pockets) != 1 or pockets[0].get("registryUrls") != urls:
        violations.append(
            "renovate.json Ubuntu pockets must contain exactly the three canonical URLs"
        )
    return violations


def _config_violations(root: Path, text: str, major: int) -> list[str]:
    """Check the parameter default, path, Renovate suite and commented pins."""
    violations = []
    docker = (root / _DOCKER).read_text()
    if re.findall(r"(?m)^ARG LLVM_MAJOR=(\d+)\s*$", docker) != [str(major)]:
        violations.append(f"Dockerfile ARG LLVM_MAJOR must equal {major} exactly once")
    code = "\n".join(
        line for line in docker.splitlines() if not line.lstrip().startswith("#")
    )
    if _LITERAL.search(code):
        violations.append(
            "Dockerfile contains an LLVM major literal outside ARG LLVM_MAJOR"
        )
    paths = tomllib.loads(text).get("env", {}).get("_", {}).get("path", [])
    if [path for path in paths if path.startswith("/usr/lib/llvm-")] != [
        f"/usr/lib/llvm-{major}/bin"
    ]:
        violations.append(
            f"mise-system.toml _.path must contain exactly /usr/lib/llvm-{major}/bin"
        )
    violations.extend(_renovate_violations((root / "renovate.json").read_text()))
    return violations


def _iwyu_pin_violations(pin: object) -> list[str]:
    """Classify a drifting or table-form IWYU pin independently of its lock."""
    if not isinstance(pin, str) or re.fullmatch(r"\d+(?:\.\d+)+", pin) is None:
        return ["IWYU pin must be a plain exact version (digits and dots)"]
    return []


def _iwyu_lock_violations(root: Path, pin: object, major: int) -> list[str]:
    """Classify a stale or off-major lock without any network access."""
    try:
        version, majors = iwyu_lock_state(
            (root / ".devcontainer/mise-system.lock").read_text()
        )
    except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        return [f"IWYU lock invalid: {exc} — run `mise run lock-image`"]
    if version != pin or any(value != major for value in majors.values()):
        targets = "/".join(f"libllvm{value}" for value in sorted(set(majors.values())))
        return [
            (
                f"IWYU lock stale or off-major: lock {version}/{targets}, "
                f"toml {pin}, apt {major} — run `mise run lock-image`"
            )
        ]
    return []


def parity_violations(root: Path, *, include_iwyu_lock: bool = True) -> list[str]:
    """Check every LLVM consumer offline against the bootstrap pin anchor."""
    try:
        text = (root / _SYSTEM).read_text()
        major = pinned_major(text)
        violations = _config_violations(root, text, major)
        pin = tomllib.loads(text).get("tools", {}).get(_IWYU_TOOL)
        violations.extend(_iwyu_pin_violations(pin))
        if include_iwyu_lock:
            violations.extend(_iwyu_lock_violations(root, pin, major))
        for name in ("image", "apt_pins", "apt_repo", "apt_liveness", "main"):
            violations.extend(
                _python_violations(root / f"python/src/dotfiles_setup/{name}.py")
            )
    except (OSError, ValueError, TypeError, SyntaxError) as exc:
        return [f"LLVM parity: {exc}"]
    return violations


def _mapped_pins(text: str, pinned: int, target: int) -> dict[str, tuple[str, bool]]:
    """Map bounded major tokens, preserving major-less names and active state."""
    return {
        re.sub(rf"(?<!\d){pinned}(?!\d)", str(target), name): value
        for name, value in llvm_pins(text).items()
    }


def _index_version(codename: str, target: int, names: set[str], fetch: Fetcher) -> str:
    """Require complete identical single-version inventories on both arches."""
    versions = set()
    for arch in ("amd64", "arm64"):
        packages = apt_repo.available_packages(
            apt_repo.RepoQuery.for_llvm(target, dist=codename, arch=arch),
            fetcher=lambda url: _body(url, fetch),
        )
        found = {package.name for package in packages}
        if names - found:
            msg = f"missing packages on {arch}: {sorted(names - found)}"
            raise ValueError(msg)
        if found - names:
            msg = (
                f"extra packages on {arch}: {sorted(found - names)}; "
                "choose active/commented policy"
            )
            raise ValueError(msg)
        versions.update(package.version for package in packages)
    if len(versions) != 1:
        msg = f"LLVM indexes must share one version, got {sorted(versions)}"
        raise ValueError(msg)
    version = versions.pop()
    if re.match(rf"(?:\d+:)?{target}(?=\.)", version) is None:
        msg = f"target {target} index has contradictory version {version!r}"
        raise ValueError(msg)
    return version


def _rewrite_once(
    pattern: str,
    replacement: str | Callable[[re.Match[str]], str],
    text: str,
    site: str,
) -> str:
    """Require exactly one textual target before returning its rewritten text."""
    rewritten, count = re.subn(pattern, replacement, text)
    if count != 1:
        msg = f"{site}: expected exactly one rewrite, got {count}"
        raise ValueError(msg)
    return rewritten


def _require_detected_build(version: str, evidence: Freeze) -> None:
    """Refuse a fresh apt version built from a different detection commit."""
    build = _APT_BUILD.search(version)
    if build is None or build.group(1) != evidence.apt_build:
        msg = f"apt rebuilt -{evidence.major} since detection; re-run"
        raise RuntimeError(msg)


def plan_bump(
    root: Path, detection: Detection, fetch: Fetcher, *, explicit_control: bool = False
) -> BumpPlan:
    """Require parity, validate both inventories, and count every planned rewrite."""
    if violations := parity_violations(root):
        msg = "cannot plan from an inconsistent tree: " + "; ".join(violations)
        raise ValueError(msg)
    before = {
        name: (root / name).read_text() for name in (_SYSTEM, _DOCKER, "renovate.json")
    }
    pinned, target = detection.pinned, detection.target
    if pinned_major(before[_SYSTEM]) != pinned or target < pinned:
        msg = "plan detection disagrees with pins or requests a downgrade"
        raise ValueError(msg)
    pins = _mapped_pins(before[_SYSTEM], pinned, target)
    version = _index_version(detection.codename, target, set(pins), fetch)
    if not explicit_control and target > pinned:
        _require_detected_build(version, detection.freeze_evidence[target])
    pins = {name: (version, active) for name, (_, active) in pins.items()}
    old = llvm_pins(before[_SYSTEM])
    counts = dict.fromkeys(old, 0)

    def replace_pin(match: re.Match[str]) -> str:
        if match["name"] not in old:
            return match.group(0)
        counts[match["name"]] += 1
        name = re.sub(rf"(?<!\d){pinned}(?!\d)", str(target), match["name"])
        return (
            f'{match["prefix"]}"apt:{name}"{match["space"]}"{version}"{match["suffix"]}'
        )

    section = _package_section(before[_SYSTEM])
    rewritten_section = _PIN.sub(replace_pin, section)
    for name, count in counts.items():
        if count != 1:
            msg = f"LLVM pin {name}: expected exactly one rewrite, got {count}"
            raise ValueError(msg)
    system = _rewrite_once(
        re.escape(section),
        lambda _: rewritten_section,
        before[_SYSTEM],
        "package table",
    )
    system = _rewrite_once(
        re.escape(f'"/usr/lib/llvm-{pinned}/bin"'),
        f'"/usr/lib/llvm-{target}/bin"',
        system,
        "_.path",
    )
    iwyu_pin = None
    if not explicit_control:
        iwyu_pin = iwyu_pin_for(target, fetch)
        system = _rewrite_once(
            r'(?m)^("conda:include-what-you-use"[ \t]*=[ \t]*)"[^"]+"',
            lambda match: f'{match[1]}"{iwyu_pin}"',
            system,
            "IWYU pin",
        )
    docker = _rewrite_once(
        r"(?m)^(ARG LLVM_MAJOR=)\d+(\s*)$",
        rf"\g<1>{target}\g<2>",
        before[_DOCKER],
        "ARG LLVM_MAJOR",
    )
    if violations := _renovate_violations(before["renovate.json"], detection.codename):
        msg = "registry suite contradicts plan codename: " + "; ".join(violations)
        raise ValueError(msg)
    return BumpPlan(
        detection,
        pins,
        before,
        {_SYSTEM: system, _DOCKER: docker, "renovate.json": before["renovate.json"]},
        iwyu_pin,
    )


def parity_main(root: Path, *, include_iwyu_lock: bool = True) -> int:
    """Print every violation and return the offline parity gate's exit code."""
    violations = parity_violations(root, include_iwyu_lock=include_iwyu_lock)
    sys.stdout.write(
        "\n".join(violations) + "\n" if violations else "LLVM parity clean\n"
    )
    return int(bool(violations))


def detect_main(
    root: Path,
    *,
    json_output: bool = False,
    markdown: bool = False,
    fetch: Fetcher = default_fetcher,
    releases: ReleaseFetcher = fetch_releases,
) -> int:
    """Print Detection with rc 0 current, 3 due, 4 held, or 1 on failed probes."""
    try:
        detection = detect(root, fetch, releases)
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as exc:
        sys.stderr.write(f"LLVM detection failed: {exc}\n")
        return 1
    data = asdict(detection)
    if markdown:
        report = (
            "# LLVM major currency\n\n"
            + "\n".join(
                f"- {label}: {data[key]}"
                for key, label in (
                    ("pinned", "Pinned"),
                    ("newest_ga", "Newest GA"),
                    ("served", "Served"),
                    ("iwyu_ready", "IWYU ready"),
                    ("frozen", "Frozen"),
                    ("target", "Target"),
                    ("held_on", "Held on"),
                    ("reason", "Reason"),
                )
            )
            + "\n\n| Major | Release head | Latest GA tag | Tag commit | Ahead | "
            "Apt build | Release Date (UTC) | Frozen |\n"
            + "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            + "\n".join(
                f"| {state.major} | {state.branch_head} | {state.tag} | "
                f"{state.tag_commit} | {state.ahead_of_tag} | {state.apt_build} | "
                f"{state.release_date.isoformat()} | {state.frozen} |"
                for state in detection.freeze_evidence.values()
            )
            + "\n"
        )
    else:
        report = (
            json.dumps(data, indent=2, default=lambda value: value.isoformat()) + "\n"
            if json_output
            else detection.reason + "\n"
        )
    sys.stdout.write(report)
    if detection.target > detection.pinned:
        return 3
    return 4 if detection.held_on is not None else 0


def _bump(
    root: Path,
    *,
    dry_run: bool = False,
    major: int | None = None,
    fetch: Fetcher = default_fetcher,
    releases: ReleaseFetcher = fetch_releases,
) -> int:
    """Execute the validated operation, leaving exception reporting to the CLI."""
    if major is not None and not dry_run:
        msg = "--major is valid only with --dry-run"
        raise ValueError(msg)
    if major is None:
        detection = detect(root, fetch, releases)
        if detection.target == detection.pinned:
            sys.stdout.write(detection.reason + "\n")
            return 0
    else:
        pinned = pinned_major((root / _SYSTEM).read_text())
        detection = Detection(
            codename_for_base_image(root, fetch),
            pinned,
            major,
            major,
            {},
            0,
            {},
            None,
            "explicit dry-run control; detection and gates skipped",
        )
    if violations := parity_violations(root):
        msg = "cannot plan from an inconsistent tree: " + "; ".join(violations)
        raise ValueError(msg)
    plan = plan_bump(root, detection, fetch, explicit_control=major is not None)
    sys.stdout.write(plan.render())
    if dry_run:
        return 0
    plan.write(root)
    sys.stdout.write("Next: mise run lock-image (IWYU lock is now stale by design)\n")
    return parity_main(root, include_iwyu_lock=False)


def bump_main(
    root: Path,
    *,
    dry_run: bool = False,
    major: int | None = None,
    fetch: Fetcher = default_fetcher,
    releases: ReleaseFetcher = fetch_releases,
) -> int:
    """Print a plan or write an eligible bump; IWYU/freeze holds change no files."""
    try:
        return _bump(
            root,
            dry_run=dry_run,
            major=major,
            fetch=fetch,
            releases=releases,
        )
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as exc:
        sys.stderr.write(f"LLVM bump failed: {exc}\n")
        return 1
