# Copyright (c) 2026 Raymond Manaloto
"""Detect GA LLVM majors, gate on IWYU, and keep consumers tied to the pins.

gh provides authenticated pagination, curl preserves HTTP status, and apt_repo
uses Debian's index parser. None owns the repository's GA + served + dual-arch
IWYU policy or its active/commented pin inventory; only that policy lives here.
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
from dataclasses import asdict, dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit

from dotfiles_setup import apt_repo
from dotfiles_setup.p2996_hash import _extract_bake_variable

if TYPE_CHECKING:
    from pathlib import Path

Fetcher = Callable[[str], tuple[int, bytes]]
ReleaseFetcher = Callable[[], list[dict]]

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
_LITERAL = re.compile(
    r"/usr/lib/llvm-\d+\b|llvm-toolchain-[\w%{}.-]+-\d+\b|"
    r"(?:apt:)?clang-\d+\b"
)


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


def _package_section(text: str) -> str:
    """Limit pin matching to the declared bootstrap package table."""
    match = re.search(r"(?ms)^\[bootstrap\.packages\]\s*\n(.*?)(?=^\[|\Z)", text)
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
        match["name"]: (match["version"], not bool(match["comment"]))
        for match in _PIN.finditer(_package_section(mise_system_text))
        if _APT_LLVM_VERSION.match(match["version"])
    }


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


def newest_ga_major(fetch_releases: ReleaseFetcher) -> int:
    """Select the greatest GA major, excluding draft, RC and init releases."""
    majors = []
    for release in fetch_releases():
        if release.get("prerelease") is False and release.get("draft") is False:
            match = re.fullmatch(
                r"llvmorg-(\d+)\.\d+\.\d+", release.get("tag_name", "")
            )
            if match:
                majors.append(int(match.group(1)))
    if not majors:
        msg = "no GA llvmorg-MAJOR.MINOR.PATCH releases found"
        raise ValueError(msg)
    return max(majors)


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
    codename: str, pinned: int, newest: int, served: dict[int, bool], fetch: Fetcher
) -> tuple[int, dict[int, bool], int | None, str]:
    """Apply the IWYU hold to every served candidate without re-gating P."""
    candidates = [major for major, available in served.items() if available]
    if not candidates:
        msg = f"no suite served in [{pinned}, {newest}] for {codename}"
        raise RuntimeError(msg)
    ready = {major: iwyu_ready(major, fetch) for major in candidates if major > pinned}
    eligible = [major for major in candidates if major == pinned or ready[major]]
    if not eligible:
        msg = "pinned suite is gone and all served replacements are IWYU-blocked"
        raise RuntimeError(msg)
    target = max(eligible)
    served_target = max(candidates)
    held = served_target if served_target > target else None
    if held is not None:
        reason = (
            f"{held} GA+served, held: IWYU (conda-forge include-what-you-use "
            f"has no version whose newest builds on both Linux architectures "
            f"target libllvm{held})"
        )
    elif served[newest]:
        reason = f"M={newest} served"
    else:
        reason = (
            f"M={newest} not served for {codename}; "
            f"highest served in [P, M-1] = {target}"
        )
    return target, ready, held, reason


def detect(
    root: Path,
    fetch: Fetcher = default_fetcher,
    releases: ReleaseFetcher = fetch_releases,
) -> Detection:
    """Detect using GA + served + IWYU, with trunk assertions that never select."""
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
    target, ready, held, reason = _target_reason(
        codename, pinned, newest, served, fetch
    )
    trunk = trunk_major(codename, fetch)
    if trunk - 1 not in {newest, newest + 1}:
        msg = f"trunk cross-check: K-1={trunk - 1} outside {{M, M+1}} for M={newest}"
        raise ValueError(msg)
    if suite_served(codename, trunk, fetch):
        msg = f"trunk cross-check: numbered suite for trunk {trunk} is served"
        raise ValueError(msg)
    return Detection(
        codename, pinned, newest, target, served, trunk, ready, held, reason
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
    urls = _registry_urls((root / "renovate.json").read_text())
    if len(urls) != 1:
        violations.append(
            "renovate.json must have exactly one apt.llvm.org registryUrl"
        )
    else:
        url = urlsplit(urls[0])
        codename = url.path.strip("/")
        if parse_qs(url.query).get("suite") != [f"llvm-toolchain-{codename}-{major}"]:
            violations.append(
                f"renovate.json suite must equal llvm-toolchain-{codename}-{major}"
            )
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
        for name in ("image", "apt_pins", "apt_repo", "main"):
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
    urls = _registry_urls(before["renovate.json"])
    if len(urls) != 1:
        msg = "cannot plan without exactly one apt.llvm.org registryUrl"
        raise ValueError(msg)
    url = urls[0]
    suite = f"llvm-toolchain-{detection.codename}-{pinned}"
    if parse_qs(urlsplit(url).query).get("suite") != [suite]:
        msg = f"registry suite contradicts plan codename/pins: expected {suite}"
        raise ValueError(msg)
    next_url = _rewrite_once(
        re.escape(suite),
        f"llvm-toolchain-{detection.codename}-{target}",
        url,
        "renovate suite",
    )
    renovate = _rewrite_once(
        re.escape(url), next_url, before["renovate.json"], "renovate registryUrl"
    )
    return BumpPlan(
        detection,
        pins,
        before,
        {_SYSTEM: system, _DOCKER: docker, "renovate.json": renovate},
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
                    ("target", "Target"),
                    ("held_on", "Held on"),
                    ("reason", "Reason"),
                )
            )
            + "\n"
        )
    else:
        report = (
            json.dumps(data, indent=2) + "\n"
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
    """Print a plan or write an eligible bump; an IWYU hold changes no files."""
    try:
        return _bump(root, dry_run=dry_run, major=major, fetch=fetch, releases=releases)
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
