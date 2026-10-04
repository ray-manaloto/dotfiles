# Copyright (c) 2026 Raymond Manaloto
"""Offline control arms for GA selection, IWYU readiness, parity and planning."""

from __future__ import annotations

import gzip
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from dotfiles_setup import apt_pins, llvm_major, main
from dotfiles_setup.image import _parse_apt_llvm_version

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ".devcontainer/mise-system.toml"
DOCKER = ".devcontainer/Dockerfile"
VERSION = "1:22.1.8~++20260804082631+ca7933e47d3a-1~exp1~20260804082728.35"
NEXT_VERSION = VERSION.replace("22.1.8", "23.1.0")
NOW = datetime(2026, 10, 4, tzinfo=UTC)
TAG22 = "ca7933e47d3a3451d81e72ac174dcb5aa28b59d1"
TAG23 = "85ac560262434c9ccfc0c183ec22d4138ed647fb"
HEAD23 = "21ef2ddb806006eba611b8a769ae72e5f86f9418"
PIN_TEXT = f"""[tools]
"conda:include-what-you-use" = "0.26"
[bootstrap.packages]
"apt:clang-22" = "{VERSION}"
"apt:libclang-cpp22" = "{VERSION}"
"apt:libllvm22" = "{VERSION}"
"apt:libc++1" = "{VERSION}"
"apt:libc++abi1" = "{VERSION}"
"apt:libomp5" = "{VERSION}"
"apt:llvm-libunwind1" = "{VERSION}"
# "apt:clang-22-doc" = "{VERSION}"
"apt:curl" = "8.0"
[env]
_.path = ["/usr/lib/llvm-22/bin"]
"""


def lock_text(version: str = "0.26", major: int = 22) -> str:
    """Independently encode the real lock's quoted platform key shape."""
    return f"""[[tools."conda:include-what-you-use"]]
version = "{version}"
[tools."conda:include-what-you-use"."platforms.linux-x64"]
conda_deps = ["libllvm{major}-{major}.1.8-build_3"]
[tools."conda:include-what-you-use"."platforms.linux-arm64"]
conda_deps = ["libllvm{major}-{major}.1.8-build_3"]
[tools."conda:include-what-you-use"."platforms.linux-x64-musl"]
conda_deps = []
[tools."conda:include-what-you-use"."platforms.linux-arm64-baseline"]
conda_deps = []
[tools."conda:include-what-you-use"."platforms.linux-x64-musl-baseline"]
conda_deps = []
"""


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Prepare a small independent repository with every parity consumer."""
    files = {
        SYSTEM: PIN_TEXT,
        ".devcontainer/mise-system.lock": lock_text(),
        DOCKER: "ARG BASE_IMAGE=ubuntu:26.04@sha256:abc\nARG LLVM_MAJOR=22\n",
        "docker-bake.hcl": (
            'variable "BASE_IMAGE" {\n default = "ubuntu:26.04@sha256:abc"\n}\n'
        ),
        "renovate.json": json.dumps(
            {
                "customManagers": [
                    manager
                    for manager in json.loads((ROOT / "renovate.json").read_text())[
                        "customManagers"
                    ]
                    if manager.get("datasourceTemplate") == "deb"
                ],
                "packageRules": [
                    rule
                    for rule in json.loads((ROOT / "renovate.json").read_text())[
                        "packageRules"
                    ]
                    if "apt-ubuntu-pockets" in rule.get("description", "")
                    or rule.get("groupName") == "apt.llvm.org LLVM debs"
                ],
            }
        ),
    }
    for name in ("image", "apt_pins", "apt_repo", "apt_liveness", "main"):
        files[f"python/src/dotfiles_setup/{name}.py"] = (
            '"""Historical clang-19 example."""\n# /usr/lib/llvm-19/bin\n'
        )
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return tmp_path


def releases(major: int) -> Callable[[], list[dict]]:
    """Supply one GA release and higher drafts/prereleases/RC/init tags."""
    return lambda: [
        {"tag_name": f"llvmorg-{major}.1.0", "draft": False, "prerelease": False},
        *[
            {
                "tag_name": f"llvmorg-{candidate}.1.0",
                "draft": False,
                "prerelease": False,
            }
            for candidate in range(23, major)
        ],
        {"tag_name": "llvmorg-99.1.0", "draft": True, "prerelease": False},
        {"tag_name": "llvmorg-98.1.0", "draft": False, "prerelease": True},
        {"tag_name": "llvmorg-97.1.0-rc1", "draft": False, "prerelease": False},
        {"tag_name": "llvmorg-96.1.0-init", "draft": False, "prerelease": False},
    ]


def iwyu_file(
    subdir: str, major: int, *, version: str = "0.26", build: int = 1
) -> dict:
    """Use the saved primary response's main-label Linux file shape."""
    raw = json.loads(
        (
            ROOT
            / "docs/research/kb/raw/llvm-23-lane-2026-10-02"
            / "conda-forge-include-what-you-use-files-2026-10-03.json"
        ).read_text()
    )
    file = next(
        file
        for file in raw
        if file.get("attrs", {}).get("subdir") == subdir
        and "main" in file.get("labels", [])
    )
    return {
        **file,
        "version": version,
        "attrs": {
            **file["attrs"],
            "build_number": build,
            "depends": [f"libllvm{major} >=0"],
        },
    }


def network(
    served: set[int],
    *,
    ready: int = 23,
    trunk: int = 24,
    build: str = TAG22[:12],
    release_date: datetime = datetime(2026, 7, 14, tzinfo=UTC),
) -> llvm_major.Fetcher:
    """A status-aware offline network with real-shaped indexes and IWYU files."""

    def fetch(url: str) -> tuple[int, bytes]:
        if "meta-release" in url:
            return 200, b"Dist: resolute\nVersion: 26.04.1 LTS\n"
        if "api.anaconda.org" in url:
            return 200, json.dumps(
                [iwyu_file(arch, ready) for arch in ("linux-64", "linux-aarch64")]
            ).encode()
        if url.endswith("Release"):
            major = int(url.split("/")[-2].rsplit("-", maxsplit=1)[1])
            return (
                (
                    200,
                    (
                        f"Codename: llvm-toolchain-resolute-{major}\n"
                        f"Date: {release_date.strftime('%a, %d %b %Y %H:%M:%S %z')}\n"
                    ).encode(),
                )
                if major in served
                else (404, b"")
            )
        if "llvm-toolchain-resolute-" in url:
            major = int(url.split("/")[-4].rsplit("-", maxsplit=1)[1])
            version = f"1:{major}.1.8~++20260714082631+{build}-1~exp1~20260714082728.35"
            return 200, gzip.compress(
                f"Package: clang-{major}\nVersion: {version}\n\n".encode()
            )
        return 200, gzip.compress(
            f"Package: clang-{trunk}\nVersion: {trunk}.0\n\n".encode()
        )

    return fetch


def github(
    *,
    head: str = TAG22,
    tag_commit: str = TAG22,
    ahead: int = 0,
    release_data: list[dict] | None = None,
) -> llvm_major.GitHubFetcher:
    """Inject GitHub's public branch/peeled commit/compare response shapes."""

    def gh(endpoint: str) -> dict | list[dict]:
        if endpoint == "repos/llvm/llvm-project/releases":
            return releases(22)() if release_data is None else release_data
        if "/branches/" in endpoint:
            return {"commit": {"sha": head}}
        if "/commits/" in endpoint:
            return {"sha": tag_commit}
        if "/compare/" in endpoint:
            return {"ahead_by": ahead}
        pytest.fail(f"unexpected GitHub endpoint {endpoint}")

    return gh


def gh_output(argv: list[str], payload: dict | list) -> bytes:
    """Model gh's included HTTP response independently from the JSON payload."""
    body = json.dumps(payload).encode()
    return b"HTTP/2.0 200 OK\r\n\r\n" + body if "--include" in argv else body


@pytest.fixture
def offline_gh(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep CLI/bump integration controls offline at the actual gh boundary."""
    boundary = github()

    def run(argv: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        assert argv[:2] == ["gh", "api"]
        payload = [boundary(argv[-1])] if "--paginate" in argv else boundary(argv[-1])
        return subprocess.CompletedProcess(argv, 0, gh_output(argv, payload), b"")

    monkeypatch.setattr(llvm_major.subprocess, "run", run)


@pytest.mark.parametrize(
    "case",
    [
        (23, {22, 23}, 23, 24, 23, None),
        (23, {22}, 23, 24, 22, None),
        (24, {22}, 24, 25, 22, None),
        (23, {22, 23}, 22, 24, 22, 23),
        (24, {22, 23, 24}, 23, 25, 23, 24),
        (24, {22, 23}, 23, 25, 23, None),
        (23, {22, 23}, 23, 25, 23, None),
    ],
)
def test_detect_gates(
    repo: Path,
    case: tuple[int, set[int], int, int, int, int | None],
) -> None:
    """Arm both fallback levels, the IWYU hold, and both valid trunk offsets."""
    ga, served, ready, trunk, target, held = case
    detection = llvm_major.detect(
        repo,
        network(served, ready=ready, trunk=trunk),
        releases(ga),
        gh=github(),
        now=NOW,
    )
    assert detection.target == target
    assert detection.held_on == held
    assert detection.served == {major: major in served for major in range(22, ga + 1)}
    if held is not None:
        assert "held: IWYU" in detection.reason


@pytest.mark.parametrize(
    "case",
    [
        (23, set(), 23, 24, "no suite"),
        (21, {22}, 22, 23, "downgrade"),
        (23, {22}, 23, 27, "K-1"),
        (23, {22, 24}, 23, 24, "numbered suite"),
        (23, {23}, 22, 24, "IWYU-blocked"),
    ],
)
def test_detect_fail_loud(
    repo: Path, case: tuple[int, set[int], int, int, str]
) -> None:
    """No served/ready candidate or a failed cross-check never reselects."""
    ga, served, ready, trunk, message = case
    with pytest.raises((ValueError, RuntimeError), match=message):
        llvm_major.detect(
            repo,
            network(served, ready=ready, trunk=trunk),
            releases(ga),
            gh=github(),
            now=NOW,
        )


def test_ga_filter_and_no_matches() -> None:
    """RC/init/prerelease/draft records cannot select a new major."""
    assert llvm_major.newest_ga_major(releases(23)) == 23
    with pytest.raises(ValueError, match="no GA"):
        llvm_major.newest_ga_major(lambda: releases(23)()[1:])


@pytest.mark.parametrize("major", [22, 23])
def test_freeze_live_shapes(major: int) -> None:
    """The observed 22 control says yes; the observed moving 23 suite says no."""
    frozen = major == 22
    head = TAG22 if frozen else HEAD23
    tag_commit = TAG22 if frozen else TAG23
    build = TAG22[:12] if frozen else "67f4a076a097"
    date = (
        datetime(2026, 7, 14, tzinfo=UTC)
        if frozen
        else datetime(2026, 9, 22, tzinfo=UTC)
    )
    tag = "llvmorg-22.1.8" if frozen else "llvmorg-23.1.2"
    state = llvm_major.freeze_state(
        major,
        "resolute",
        network({major}, build=build, release_date=date),
        github(
            head=head,
            tag_commit=tag_commit,
            ahead=0 if frozen else 27,
            release_data=[{"tag_name": tag, "draft": False, "prerelease": False}],
        ),
        now=NOW,
    )
    assert state.frozen is frozen
    assert state.major == major
    assert state.branch_head == head
    assert state.tag == tag
    assert state.tag_commit == tag_commit
    assert state.apt_build == build
    assert state.release_date == date
    assert state.ahead_of_tag == (0 if frozen else 27)


@pytest.mark.parametrize(
    ("ahead", "build", "age", "expected"),
    [
        (0, TAG22[:12], timedelta(days=14), True),
        (2, TAG22[:12], timedelta(days=14), False),
        (1, TAG23[:12], timedelta(days=14), True),
        (1, TAG22[:12], timedelta(days=14), True),
        (0, "67f4a076a097", timedelta(days=14), False),
        (0, TAG22[:12], timedelta(days=13), False),
        (0, TAG22[:12], timedelta(days=14, microseconds=-1), False),
        (0, TAG22[:12], timedelta(days=14, microseconds=1), True),
        (0, TAG22[:12], timedelta(days=-1), False),
    ],
)
def test_freeze_independent_conditions(
    ahead: int, build: str, age: timedelta, *, expected: bool
) -> None:
    """Change one axis at a time, including both allowed commit identities."""
    state = llvm_major.freeze_state(
        22,
        "resolute",
        network({22}, build=build, release_date=NOW),
        github(head=TAG23, ahead=ahead),
        now=NOW + age,
    )
    assert state.frozen is expected


@pytest.mark.parametrize(
    "fault", ["version", "missing-date", "bad-date", "no-zone", "duplicate-date"]
)
def test_freeze_malformed_apt_evidence(fault: str) -> None:
    """Unreadable build metadata raises instead of masquerading as a hold."""
    boundary = network({22})

    def fetch(url: str) -> tuple[int, bytes]:
        status, body = boundary(url)
        if url.endswith("Release"):
            if fault == "missing-date":
                body = b"Codename: llvm-toolchain-resolute-22\n"
            elif fault == "bad-date":
                body = b"Date: not-a-date\n"
            elif fault == "no-zone":
                body = b"Date: Tue, 14 Jul 2026 00:00:00\n"
            elif fault == "duplicate-date":
                body += b"Date: Tue, 14 Jul 2026 00:00:00 +0000\n"
        elif fault == "version":
            body = gzip.compress(b"Package: clang-22\nVersion: invalid\n\n")
        return status, body

    with pytest.raises(ValueError, match=r"Date|date|apt version"):
        llvm_major.freeze_state(22, "resolute", fetch, github(), now=NOW)


@pytest.mark.parametrize("endpoint", ["branches", "commits", "compare"])
def test_freeze_github_http_failures(
    monkeypatch: pytest.MonkeyPatch, endpoint: str
) -> None:
    """Real gh adapter rejects 404s for every evidence endpoint, notably branches."""
    boundary = github()

    def run(argv: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        if f"/{endpoint}/" in argv[-1]:
            return subprocess.CompletedProcess(
                argv, 1, b"", b"gh: Not Found (HTTP 404)"
            )
        payload = [boundary(argv[-1])] if "--paginate" in argv else boundary(argv[-1])
        return subprocess.CompletedProcess(argv, 0, gh_output(argv, payload), b"")

    monkeypatch.setattr(llvm_major.subprocess, "run", run)
    with pytest.raises(RuntimeError, match="HTTP 404"):
        llvm_major.freeze_state(
            22,
            "resolute",
            network({22}),
            llvm_major.default_gh,
            now=NOW,
        )


@pytest.mark.parametrize("status", [301, 404, 500])
@pytest.mark.parametrize("site", ["Release", "Packages.gz"])
def test_freeze_apt_http_failures(status: int, site: str) -> None:
    """Every non-200 in an asked freeze probe is an error, including 404."""
    boundary = network({22})

    def fetch(url: str) -> tuple[int, bytes]:
        return (status, b"") if url.endswith(site) else boundary(url)

    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        llvm_major.freeze_state(22, "resolute", fetch, github(), now=NOW)


@pytest.mark.parametrize("status", [200, 201, 301, 500])
def test_freeze_gh_requires_http_200(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    """Even a successful process must provide a 200 evidence response."""

    def run(argv: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        assert "--include" in argv
        body = (
            f"HTTP/2.0 {status} Status\n\n".encode()
            + json.dumps({"sha": TAG22}).encode()
        )
        return subprocess.CompletedProcess(argv, 0, body, b"")

    monkeypatch.setattr(llvm_major.subprocess, "run", run)
    if status == 200:
        assert llvm_major.default_gh(
            "repos/llvm/llvm-project/commits/llvmorg-22.1.8"
        ) == {"sha": TAG22}
    else:
        with pytest.raises(RuntimeError, match=f"HTTP {status}"):
            llvm_major.default_gh("repos/llvm/llvm-project/commits/llvmorg-22.1.8")


def test_freeze_numeric_latest_ga_tag() -> None:
    """Newest means numeric major/minor/patch, with drafts and RCs excluded."""
    tags = [
        {"tag_name": tag, "draft": False, "prerelease": False}
        for tag in (
            "llvmorg-22.1.9",
            "llvmorg-22.1.10",
            "llvmorg-22.1.11-rc1",
            "llvmorg-23.1.0",
        )
    ]
    tags.extend(
        [
            {"tag_name": "llvmorg-22.2.0", "draft": True, "prerelease": False},
            {"tag_name": "llvmorg-22.3.0", "draft": False, "prerelease": True},
        ]
    )
    calls = []
    boundary = github(release_data=tags)

    def gh(endpoint: str) -> dict | list[dict]:
        calls.append(endpoint)
        return boundary(endpoint)

    state = llvm_major.freeze_state(22, "resolute", network({22}), gh, now=NOW)
    assert state.tag == "llvmorg-22.1.10"
    assert "repos/llvm/llvm-project/commits/llvmorg-22.1.10" in calls
    assert "repos/llvm/llvm-project/compare/llvmorg-22.1.10...release/22.x" in calls


@pytest.mark.parametrize(
    ("ready", "frozen", "target", "held_gates"),
    [
        (23, False, 22, "freeze"),
        (22, False, 22, "IWYU, freeze"),
        (22, True, 22, "IWYU"),
        (23, True, 23, None),
    ],
)
def test_detect_requires_both_gates(
    repo: Path, ready: int, *, frozen: bool, target: int, held_gates: str | None
) -> None:
    """IWYU becoming ready must not lift the independent release freeze hold."""
    detection = llvm_major.detect(
        repo,
        network({22, 23}, ready=ready),
        releases(23),
        gh=github(ahead=0 if frozen else 2),
        now=NOW,
    )
    assert detection.target == target
    assert detection.frozen == {23: frozen}
    assert detection.iwyu_ready == {23: ready == 23}
    assert set(detection.freeze_evidence) == {23}
    if held_gates is None:
        assert detection.held_on is None
    else:
        assert detection.held_on == 23
        assert detection.reason.startswith(f"23 GA+served, held: {held_gates};")
        assert "release/23.x" in detection.reason
        assert "built 2026-07-14" in detection.reason


def test_detect_never_regates_pin(repo: Path) -> None:
    """A served current pin stays usable without any compatibility/freeze probe."""
    boundary = network({22})

    def fetch(url: str) -> tuple[int, bytes]:
        assert "anaconda" not in url
        assert "llvm-toolchain-resolute-22/main/" not in url
        return boundary(url)

    def gh(endpoint: str) -> dict:
        pytest.fail(f"pinned major was re-gated: {endpoint}")

    detection = llvm_major.detect(repo, fetch, releases(22), gh=gh, now=NOW)
    assert detection.target == 22
    assert detection.freeze_evidence == {}
    assert detection.frozen == {}
    assert detection.iwyu_ready == {}


def test_detect_reuses_release_snapshot(repo: Path) -> None:
    """Selection and freeze read one GA list and the same Release response."""
    calls = []
    ga_calls = []
    boundary = network({22, 23})

    def fetch(url: str) -> tuple[int, bytes]:
        calls.append(url)
        return boundary(url)

    def ga() -> list[dict]:
        ga_calls.append(True)
        return releases(23)()

    detection = llvm_major.detect(repo, fetch, ga, gh=github(), now=NOW)
    assert detection.target == 23
    assert ga_calls == [True]
    assert (
        calls.count(
            "https://apt.llvm.org/resolute/dists/llvm-toolchain-resolute-23/Release"
        )
        == 1
    )


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (200, b"Codename: llvm-toolchain-resolute-23\n", True),
        (200, b"Codename: something-else\n", False),
        (404, b"", False),
    ],
)
def test_release_answer(status: int, body: bytes, *, expected: bool) -> None:
    """Only the exact Codename line on 200 says yes; 404 says no."""
    assert llvm_major.suite_served("resolute", 23, lambda _: (status, body)) is expected


@pytest.mark.parametrize("status", [301, 500])
def test_release_unanswered_status(status: int) -> None:
    """A redirect or server error raises rather than acting as absence."""
    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        llvm_major.suite_served("resolute", 23, lambda _: (status, b""))


def test_release_network_error() -> None:
    """Transport failure is propagated, never converted to False."""

    def broken(_: str) -> tuple[int, bytes]:
        msg = "network unavailable"
        raise OSError(msg)

    with pytest.raises(OSError, match="network"):
        llvm_major.suite_served("resolute", 23, broken)


@pytest.mark.parametrize(
    "mutation",
    ["missing", "multiple", "anchor-version", "mixed-major", "mixed-version"],
)
def test_pin_errors(mutation: str) -> None:
    """The anchor and apt.llvm.org snapshot pins cannot contradict each other."""
    variants = {
        "missing": PIN_TEXT.replace('"apt:clang-22"', '"apt:not-clang"'),
        "multiple": PIN_TEXT.replace("[env]", f'"apt:clang-23" = "{VERSION}"\n[env]'),
        "anchor-version": PIN_TEXT.replace(VERSION, "1:23.1.0"),
        "mixed-major": PIN_TEXT.replace('"apt:libllvm22"', '"apt:libllvm23"'),
        "mixed-version": PIN_TEXT.replace(
            f'"apt:libllvm22" = "{VERSION}"',
            f'"apt:libllvm22" = "{VERSION.replace("22.1.8", "22.1.7")}"',
        ),
    }
    with pytest.raises((TypeError, ValueError)):
        llvm_major.pinned_major(variants[mutation])


def test_pin_inventory() -> None:
    """Snapshot signatures capture major-less names and the commented pin."""
    assert llvm_major.pinned_major(PIN_TEXT) == 22
    pins = llvm_major.llvm_pins(PIN_TEXT)
    assert len(pins) == 8
    assert pins["clang-22-doc"] == (VERSION, False)
    assert pins["libomp5"] == (VERSION, True)
    assert "curl" not in pins


@pytest.mark.parametrize("name_major", [22, 23])
@pytest.mark.parametrize("version", [VERSION, NEXT_VERSION])
@pytest.mark.parametrize("prefix", ["", "# "])
def test_libbolt_pin_signature(name_major: int, version: str, prefix: str) -> None:
    """Active and commented libbolt names and versions must match the anchor."""
    name = f"libbolt-{name_major}-dev"
    text = PIN_TEXT.replace("[env]", f'{prefix}"apt:{name}" = "{version}"\n[env]')
    if name_major != 22 or version != VERSION:
        with pytest.raises(ValueError, match="mixed"):
            llvm_major.pinned_major(text)
        with pytest.raises(ValueError, match="mixed"):
            llvm_major.llvm_pins(text)
    else:
        assert llvm_major.pinned_major(text) == 22
        assert llvm_major.llvm_pins(text)[name] == (VERSION, not bool(prefix))


@pytest.mark.parametrize("version", ["1.8.1-0.1ubuntu1", VERSION])
def test_libunwind_signature_membership(repo: Path, version: str) -> None:
    """A package name alone never classifies an Ubuntu pin as LLVM."""
    text = PIN_TEXT.replace("[env]", f'"apt:libunwind-dev" = "{version}"\n[env]')
    (repo / SYSTEM).write_text(text)
    assert llvm_major.pinned_major(text) == 22
    assert llvm_major.parity_violations(repo) == []
    assert ("libunwind-dev" in llvm_major.llvm_pins(text)) is (version == VERSION)


@pytest.mark.parametrize("preceding", ["#\n", "# \t\n", "\n"])
@pytest.mark.parametrize("prefix", ["", " \t", "# ", "\t#\t"])
def test_pin_marker_stays_on_its_line(preceding: str, prefix: str) -> None:
    """A bare comment or blank line cannot change the next pin's active state."""
    text = PIN_TEXT.replace('"apt:libllvm22"', f'{preceding}{prefix}"apt:libllvm22"')
    assert llvm_major.llvm_pins(text)["libllvm22"] == (VERSION, "#" not in prefix)


@pytest.mark.parametrize("major", [22, 23])
def test_image_anchor_on_either_tree(major: int) -> None:
    """The version resolver can read both HEAD and a differently pinned base."""
    text = PIN_TEXT.replace("22", str(major))
    assert _parse_apt_llvm_version(text) == f"{major}.1.8"


def test_commented_second_anchor_raises() -> None:
    """An inactive extra clang anchor is ambiguous too."""
    text = PIN_TEXT.replace("[env]", f'# "apt:clang-22" = "{VERSION}"\n[env]')
    with pytest.raises(TypeError, match="exactly one"):
        llvm_major.pinned_major(text)


@pytest.mark.parametrize(("other", "expected"), [(23, True), (22, False)])
def test_iwyu_both_arches(other: int, *, expected: bool) -> None:
    """One architecture targeting an older clang blocks the dual-arch image."""
    files = [iwyu_file("linux-64", 23), iwyu_file("linux-aarch64", other)]
    assert (
        llvm_major.iwyu_ready(23, lambda _: (200, json.dumps(files).encode()))
        is expected
    )


def test_iwyu_numeric_version_and_build() -> None:
    """Numeric 0.26 beats 0.9 and build 1 beats build 0 at the same version."""
    files = [
        iwyu_file(arch, major, version=version, build=build)
        for arch in ("linux-64", "linux-aarch64")
        for major, version, build in [(22, "0.9", 9), (22, "0.26", 0), (23, "0.26", 1)]
    ]
    assert llvm_major.iwyu_ready(23, lambda _: (200, json.dumps(files).encode()))
    assert llvm_major.iwyu_versions_for(
        22, lambda _: (200, json.dumps(files).encode())
    ) == ["0.9"]


@pytest.mark.parametrize("subdir", ["linux-64", "linux-aarch64"])
@pytest.mark.parametrize("other", [22, 23])
@pytest.mark.parametrize("reverse", [False, True])
def test_iwyu_tied_newest_builds(subdir: str, other: int, *, reverse: bool) -> None:
    """Tied newest majors must agree regardless of architecture or API order."""
    files = [iwyu_file(arch, 23) for arch in ("linux-64", "linux-aarch64")]
    files.append(iwyu_file(subdir, other))
    files.append(iwyu_file(subdir, 22, build=0))
    if reverse:
        files.reverse()

    def fetch(_: str) -> tuple[int, bytes]:
        return 200, json.dumps(files).encode()

    if other != 23:
        with pytest.raises(ValueError, match=f"ambiguous newest IWYU {subdir}"):
            llvm_major.iwyu_ready(23, fetch)
    else:
        assert llvm_major.iwyu_ready(23, fetch)
        assert not llvm_major.iwyu_ready(22, fetch)


@pytest.mark.parametrize(
    "fault",
    [
        "missing-arch",
        "version",
        "no-dep",
        "windows-only",
        "label-less",
        "non-json",
        "not-list",
    ],
)
def test_iwyu_metadata_failures(fault: str) -> None:
    """Missing coverage or changed metadata fails loudly, never a false hold."""
    files = [iwyu_file(arch, 23) for arch in ("linux-64", "linux-aarch64")]
    if fault == "missing-arch":
        files.pop()
    elif fault == "version":
        files[0]["version"] = "0.rc"
    elif fault == "no-dep":
        files[0]["attrs"]["depends"] = ["libclang-cpp23.1 >=0"]
    elif fault == "windows-only":
        for file in files:
            file["attrs"]["subdir"] = "win-64"
    elif fault == "label-less":
        for file in files:
            file.pop("labels")
    body = (
        b"invalid-json"
        if fault == "non-json"
        else json.dumps({} if fault == "not-list" else files).encode()
    )
    with pytest.raises((ValueError, TypeError)):
        llvm_major.iwyu_ready(23, lambda _: (200, body))


@pytest.mark.parametrize("status", [301, 404, 500])
def test_iwyu_http_failures(status: int) -> None:
    """IWYU metadata requires a direct 200; even 404 cannot mean not ready."""
    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        llvm_major.iwyu_ready(23, lambda _: (status, b"[]"))


def test_iwyu_ignores_unrelated_files() -> None:
    """Windows and label-less newer files cannot override the Linux main builds."""
    files = [iwyu_file(arch, 23) for arch in ("linux-64", "linux-aarch64")]
    files.extend(
        [
            {"version": "bad", "labels": ["main"], "attrs": {"subdir": "win-64"}},
            {"version": "bad", "attrs": {"subdir": "linux-64"}},
        ]
    )
    assert llvm_major.iwyu_ready(23, lambda _: (200, json.dumps(files).encode()))


@pytest.mark.parametrize(
    ("path", "old", "new", "message"),
    [
        (DOCKER, "LLVM_MAJOR=22", "LLVM_MAJOR=23", "ARG LLVM_MAJOR"),
        (SYSTEM, "/usr/lib/llvm-22/bin", "/usr/lib/llvm-23/bin", "_.path"),
        ("renovate.json", "{{{llvmMajor}}}", "23", "renovate.json suite"),
        (DOCKER, "ARG LLVM_MAJOR=22", "ARG LLVM_MAJOR=22\nRUN clang-23", "literal"),
        (
            "python/src/dotfiles_setup/main.py",
            "# /usr/lib/llvm-19/bin",
            'parser.add_argument("--llvm-version", default="22")',
            "default",
        ),
        (
            "python/src/dotfiles_setup/image.py",
            "# /usr/lib/llvm-19/bin",
            'pin = "apt:clang-22"',
            "literal",
        ),
    ],
)
def test_parity_single_fault(
    repo: Path, path: str, old: str, new: str, message: str
) -> None:
    """Each consumer's realistic isolated mutation produces one violation."""
    assert llvm_major.parity_violations(repo) == []
    file = repo / path
    file.write_text(file.read_text().replace(old, new))
    violations = llvm_major.parity_violations(repo)
    assert len(violations) == 1
    assert message in violations[0]


def test_actual_tree_parity() -> None:
    """The real consumers are checked, including f-string shell scripts."""
    assert llvm_major.parity_violations(ROOT) == []


@pytest.mark.parametrize("fault", ["delete", "release", "updates", "security", "extra"])
def test_ubuntu_pocket_parity_requires_exact_urls(repo: Path, fault: str) -> None:
    """All three canonical amd64 main pockets are required together."""
    assert llvm_major.parity_violations(repo) == []
    file = repo / "renovate.json"
    config = json.loads(file.read_text())
    rule = config["packageRules"][0]
    if fault == "delete":
        config["packageRules"].remove(rule)
    elif fault == "extra":
        rule["registryUrls"].append(rule["registryUrls"][0])
    else:
        index = ["release", "updates", "security"].index(fault)
        rule["registryUrls"][index] = rule["registryUrls"][index].replace(
            "components=main", "components=universe"
        )
    file.write_text(json.dumps(config))
    assert any("Ubuntu pockets" in item for item in llvm_major.parity_violations(repo))


def test_ubuntu_pocket_parity_derives_codename_from_template(repo: Path) -> None:
    """A different valid template codename must bind its own three pockets."""
    file = repo / "renovate.json"
    file.write_text(file.read_text().replace("resolute", "future"))
    assert llvm_major.parity_violations(repo) == []
    config = json.loads(file.read_text())
    config["packageRules"][0]["registryUrls"][1] = config["packageRules"][0][
        "registryUrls"
    ][1].replace("future", "resolute")
    file.write_text(json.dumps(config))
    assert any("Ubuntu pockets" in item for item in llvm_major.parity_violations(repo))


@pytest.mark.parametrize("encoding", ["group", "negation", "capture"])
def test_snapshot_signature_parity_refuses_drift(repo: Path, encoding: str) -> None:
    """Parity rejects each stale encoding of the canonical snapshot signature."""
    file = repo / "renovate.json"
    config = json.loads(file.read_text())
    if encoding == "capture":
        manager = config["customManagers"][0]
        manager["matchStrings"][0] = manager["matchStrings"][0].replace(
            r"\d+:", r"(?:\d+:)?", 1
        )
    else:
        rule = config["packageRules"][1 if encoding == "group" else 0]
        rule["matchCurrentValue"] = (
            "!" if encoding == "negation" else ""
        ) + r"/~\+\+\d{14}\+[0-9a-f]+-1~exp1~/"
    file.write_text(json.dumps(config))
    assert llvm_major.parity_violations(repo)


@pytest.mark.parametrize("first_comment", [False, True])
@pytest.mark.parametrize("second_comment", [False, True])
def test_bootstrap_pins_rejects_duplicate_names_with_both_lines(
    *, first_comment: bool, second_comment: bool
) -> None:
    """Active and commented duplicates must never collapse into one dict entry."""
    text = (
        '# header\n[env]\nvalue = "before"\n[bootstrap.packages]\n'
        f'{"# " if first_comment else ""}"apt:curl" = "1"\n'
        "\n"
        f'{"# " if second_comment else ""}"apt:curl" = "2"\n'
    )
    with pytest.raises(ValueError, match=r"duplicate.*curl.*lines 5 and 7"):
        llvm_major.bootstrap_pins(text)


@pytest.mark.parametrize("fault", ["capture", "override", "duplicate", "literal"])
def test_native_registry_parity_refuses_drift(repo: Path, fault: str) -> None:
    """Require a version-major capture and protection from URL overrides."""
    file = repo / "renovate.json"
    config = json.loads(file.read_text())
    manager = config["customManagers"][0]
    if fault == "capture":
        manager["matchStrings"][0] = manager["matchStrings"][0].replace(
            "llvmMajor", "unused"
        )
    elif fault == "override":
        config["packageRules"] = [
            {"matchDatasources": ["deb"], "registryUrls": ["https://example.com"]}
        ]
    elif fault == "duplicate":
        config["customManagers"].append(manager.copy())
    else:
        manager["registryUrls"] = [
            "https://apt.llvm.org/resolute?suite=llvm-toolchain-resolute-22"
        ]
    file.write_text(json.dumps(config))
    assert any("renovate.json" in item for item in llvm_major.parity_violations(repo))


def test_apt_liveness_literals_are_in_parity_scope(repo: Path) -> None:
    """The new consumer cannot silently acquire a frozen LLVM major."""
    file = repo / "python/src/dotfiles_setup/apt_liveness.py"
    file.write_text('query = "llvm-toolchain-resolute-22"\n')
    assert any("literal" in item for item in llvm_major.parity_violations(repo))


def test_native_registry_plan_rejects_wrong_base_codename(repo: Path) -> None:
    """Native major following must not permit a suite on the wrong Ubuntu base."""
    detection = llvm_major.Detection("future", 22, 23, 23, {}, 24, {}, None, "control")
    names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
    before = tree_bytes(repo)
    with pytest.raises(ValueError, match="registry suite contradicts plan codename"):
        llvm_major.plan_bump(
            repo, detection, plan_network(names), explicit_control=True
        )
    assert tree_bytes(repo) == before


def test_commented_pin_parity(repo: Path) -> None:
    """An inactive package naming another major still violates parity."""
    file = repo / SYSTEM
    file.write_text(file.read_text().replace("clang-22-doc", "clang-23-doc"))
    assert "mixed majors" in llvm_major.parity_violations(repo)[0]


def plan_network(
    names: set[str], *, fault: str = "", version: str = "1:23.1.0"
) -> llvm_major.Fetcher:
    """Serve complete indexes or one intentional inventory/version defect."""

    def fetch(url: str) -> tuple[int, bytes]:
        if "meta-release" in url:
            return 200, b"Dist: resolute\nVersion: 26.04.1 LTS\n"
        if url.endswith("Release") or "anaconda" in url:
            msg = "explicit dry-run must skip both gates"
            raise AssertionError(msg)
        selected = sorted(names)
        if fault == "missing" and "arm64" in url:
            selected.pop()
        if fault == "extra":
            selected.append("unexpected-tool-23")
        alternate_version = version.replace("23.1.0", "23.1.1")
        index = "\n\n".join(
            f"Package: {name}\nVersion: "
            f"{alternate_version if fault == 'version' and i == 0 else version}"
            for i, name in enumerate(selected)
        )
        return 200, gzip.compress((index + "\n\n").encode())

    return fetch


def test_plan_preserves_status_and_majorless_names(repo: Path) -> None:
    """A future bump changes pins/path/ARG while the native URL stays clean."""
    detection = llvm_major.Detection(
        "resolute", 22, 23, 23, {}, 24, {}, None, "control"
    )
    names = {
        "clang-23",
        "libclang-cpp23",
        "libllvm23",
        "libc++1",
        "libc++abi1",
        "libomp5",
        "llvm-libunwind1",
        "clang-23-doc",
    }
    plan = llvm_major.plan_bump(
        repo, detection, plan_network(names), explicit_control=True
    )
    assert set(plan.pins) == names
    assert plan.pins["clang-23-doc"] == ("1:23.1.0", False)
    assert plan.pins["libomp5"] == ("1:23.1.0", True)
    assert set(plan.after) == {SYSTEM, DOCKER, "renovate.json"}
    assert plan.after["renovate.json"] == plan.before["renovate.json"]
    assert (repo / SYSTEM).read_text() == PIN_TEXT
    plan.write(repo)
    assert llvm_major.parity_violations(repo, include_iwyu_lock=False) == []
    assert "IWYU lock stale or off-major" in llvm_major.parity_violations(repo)[0]
    assert '"apt:curl" = "8.0"' in (repo / SYSTEM).read_text()


def tree_bytes(repo: Path) -> dict[Path, bytes]:
    """Snapshot every fixture file to verify refusal leaves the whole tree intact."""
    return {path: path.read_bytes() for path in repo.rglob("*") if path.is_file()}


def test_plan_rejects_existing_parity_violation(repo: Path) -> None:
    """The public planner rejects parity before consulting indexes or writing."""
    file = repo / DOCKER
    file.write_text(file.read_text().replace("LLVM_MAJOR=22", "LLVM_MAJOR=23"))
    before = tree_bytes(repo)
    detection = llvm_major.Detection(
        "resolute", 22, 23, 23, {}, 24, {}, None, "control"
    )

    def unexpected_fetch(_: str) -> tuple[int, bytes]:
        msg = "parity must run before fetching indexes"
        raise AssertionError(msg)

    with pytest.raises(ValueError, match=r"inconsistent tree:.*ARG LLVM_MAJOR"):
        llvm_major.plan_bump(repo, detection, unexpected_fetch)
    assert tree_bytes(repo) == before


@pytest.mark.parametrize("site", ["_.path", "pin"])
def test_plan_rejects_duplicate_rewrite_targets(repo: Path, site: str) -> None:
    """Parity-clean duplicate textual targets cannot produce a writable plan."""
    if site == "_.path":
        file = repo / SYSTEM
        file.write_text(file.read_text() + '# "/usr/lib/llvm-22/bin"\n')
    elif site == "pin":
        file = repo / SYSTEM
        file.write_text(
            file.read_text().replace(
                "[env]", f'  # "apt:clang-22-doc" = "{VERSION}"\n[env]'
            )
        )
    assert llvm_major.parity_violations(repo) == []
    before = tree_bytes(repo)
    detection = llvm_major.Detection(
        "resolute", 22, 23, 23, {}, 24, {}, None, "control"
    )
    names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
    message = (
        "duplicate apt package 'clang-22-doc' on lines 11 and 13"
        if site == "pin"
        else "expected exactly one rewrite, got 2"
    )
    with pytest.raises(ValueError, match=message):
        llvm_major.plan_bump(
            repo,
            detection,
            plan_network(names, version=NEXT_VERSION),
            explicit_control=True,
        )
    assert tree_bytes(repo) == before


def test_plan_rejects_missing_textual_path_target(repo: Path) -> None:
    """Valid TOML using single quotes must fail before an unrewritten path lands."""
    file = repo / SYSTEM
    file.write_text(
        file.read_text().replace('"/usr/lib/llvm-22/bin"', "'/usr/lib/llvm-22/bin'")
    )
    assert llvm_major.parity_violations(repo) == []
    before = tree_bytes(repo)
    detection = llvm_major.Detection(
        "resolute", 22, 23, 23, {}, 24, {}, None, "control"
    )
    names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
    with pytest.raises(
        ValueError, match=r"_.path: expected exactly one rewrite, got 0"
    ):
        llvm_major.plan_bump(
            repo,
            detection,
            plan_network(names, version=NEXT_VERSION),
            explicit_control=True,
        )
    assert tree_bytes(repo) == before


@pytest.mark.parametrize("space", ["", "  ", "\t", " \t\n\n"])
def test_plan_arg_accepts_parity_whitespace(repo: Path, space: str) -> None:
    """Every ARG trailing whitespace accepted by parity is preserved by the plan."""
    file = repo / DOCKER
    file.write_text(file.read_text().replace("LLVM_MAJOR=22", f"LLVM_MAJOR=22{space}"))
    assert llvm_major.parity_violations(repo) == []
    detection = llvm_major.Detection(
        "resolute", 22, 23, 23, {}, 24, {}, None, "control"
    )
    names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
    plan = llvm_major.plan_bump(
        repo,
        detection,
        plan_network(names, version=NEXT_VERSION),
        explicit_control=True,
    )
    assert plan.after[DOCKER] == file.read_text().replace(
        "LLVM_MAJOR=22", "LLVM_MAJOR=23"
    )
    plan.write(repo)
    assert llvm_major.parity_violations(repo, include_iwyu_lock=False) == []


@pytest.mark.parametrize("fault", ["missing", "extra", "version"])
def test_plan_rejects_incomplete_inventory(repo: Path, fault: str) -> None:
    """Missing arm64 names, extras and mixed builds all refuse to write."""
    detection = llvm_major.Detection(
        "resolute", 22, 23, 23, {}, 24, {}, None, "control"
    )
    names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
    with pytest.raises(
        ValueError,
        match={
            "missing": "arm64",
            "extra": "unexpected-tool",
            "version": "one version",
        }[fault],
    ):
        llvm_major.plan_bump(repo, detection, plan_network(names, fault=fault))
    assert (repo / SYSTEM).read_text() == PIN_TEXT


@pytest.mark.parametrize(
    "case",
    [
        ({22}, 22, 22, 0),
        ({22, 23}, 23, 23, 3),
        ({22, 23}, 22, 23, 4),
        (set(), 23, 23, 1),
    ],
)
@pytest.mark.usefixtures("offline_gh")
def test_cli_detect(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    case: tuple[set[int], int, int, int],
) -> None:
    """Actual parser/dispatch preserve all four detector exit codes offline."""
    served, ready, ga, expected = case
    handler = llvm_major.detect_main
    monkeypatch.setattr(
        llvm_major,
        "detect_main",
        lambda root, *, json_output, markdown: handler(
            root,
            json_output=json_output,
            markdown=markdown,
            fetch=network(served, ready=ready, trunk=ga + 1),
            releases=releases(ga),
        ),
    )
    args = main.setup_parser().parse_args(["llvm-detect", "--json"])
    with pytest.raises(SystemExit) as result:
        main.run_command(args, repo)
    assert result.value.code == expected
    output = capsys.readouterr()
    if expected == 1:
        assert "no suite" in output.err
    else:
        assert json.loads(output.out)["pinned"] == 22


@pytest.mark.usefixtures("offline_gh")
def test_cli_held_bump_changes_nothing(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The real bump dispatch's held path returns zero and preserves all bytes."""
    before = {
        str(path): path.read_bytes() for path in repo.rglob("*") if path.is_file()
    }
    handler = llvm_major.bump_main
    monkeypatch.setattr(
        llvm_major,
        "bump_main",
        lambda root, *, dry_run, major: handler(
            root,
            dry_run=dry_run,
            major=major,
            fetch=network({22, 23}, ready=22),
            releases=releases(23),
        ),
    )
    with pytest.raises(SystemExit) as result:
        main.run_command(main.setup_parser().parse_args(["llvm-bump"]), repo)
    assert result.value.code == 0
    assert "23 GA+served, held: IWYU" in capsys.readouterr().out
    assert before == {
        str(path): path.read_bytes() for path in repo.rglob("*") if path.is_file()
    }


@pytest.mark.parametrize("explicit", [False, True])
def test_cli_apt_repo_uses_dispatched_root(
    repo: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    explicit: bool,
) -> None:
    """The real dispatch defaults to its alternate root while honoring overrides."""
    (repo / SYSTEM).write_text(PIN_TEXT.replace("22", "23"))
    selected = 22 if explicit else 23

    def run(argv: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        assert argv[0] == "curl"
        assert f"/llvm-toolchain-resolute-{selected}/" in argv[-1]
        index = gzip.compress(
            f"Package: clang-{selected}\nVersion: {selected}.1.0\n\n".encode()
        )
        return subprocess.CompletedProcess(argv, 0, index, b"")

    monkeypatch.setattr(subprocess, "run", run)
    argv = ["apt-repo", "--toml", "--pin"]
    if explicit:
        argv.extend(["--llvm-version", str(selected)])
    with pytest.raises(SystemExit) as result:
        main.run_command(main.setup_parser().parse_args(argv), repo)
    assert result.value.code == 0
    assert f'"apt:clang-{selected}"' in capsys.readouterr().out


def test_explicit_dry_run_skips_gates(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The major control arm plans but cannot write or consult release/gate data."""
    names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
    assert (
        llvm_major.bump_main(repo, dry_run=True, major=23, fetch=plan_network(names))
        == 0
    )
    output = capsys.readouterr().out
    assert "8 pins (7 active, 1 commented), amd64 + arm64" in output
    assert "IWYU pin: not planned (explicit control; gates skipped)" in output
    assert (repo / SYSTEM).read_text() == PIN_TEXT
    assert llvm_major.bump_main(repo, major=23) == 1
    assert "only with --dry-run" in capsys.readouterr().err


@pytest.mark.parametrize("pins", [{}, {"clang-22": "1:22", "clang-23": "1:23"}])
def test_probe_script_rejects_ambiguous_clang(pins: dict[str, str]) -> None:
    """The apt pin probe cannot infer a major without one unambiguous key."""
    with pytest.raises(ValueError, match="exactly one"):
        apt_pins.probe_script(pins, "ABCD")


def test_probe_script_uses_key() -> None:
    """A 23 fixture reaches the suite, guarding against a hidden current major."""
    assert "llvm-toolchain-%s-23" in apt_pins.probe_script({"clang-23": "1:23"}, "ABCD")


def test_base_consistency_and_metadata_fallback(repo: Path) -> None:
    """Bake must agree with Docker; development metadata may resolve the base."""

    def fetch(url: str) -> tuple[int, bytes]:
        return 200, b"Dist: resolute\nVersion: 26.04.1 LTS\n" if url.endswith(
            "development"
        ) else b"Dist: old\nVersion: 24.04\n"

    assert llvm_major.codename_for_base_image(repo, fetch) == "resolute"
    (repo / DOCKER).write_text((repo / DOCKER).read_text().replace("26.04", "24.04"))
    with pytest.raises(ValueError, match="disagrees"):
        llvm_major.codename_for_base_image(repo, fetch)


def test_plan_rejects_foreign_write(repo: Path) -> None:
    """An edit after planning prevents any plan file from being written."""
    names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
    detection = llvm_major.Detection(
        "resolute", 22, 23, 23, {}, 24, {}, None, "control"
    )
    plan = llvm_major.plan_bump(
        repo, detection, plan_network(names), explicit_control=True
    )
    (repo / DOCKER).write_text("foreign edit\n")
    with pytest.raises(RuntimeError, match="changed after planning"):
        plan.write(repo)
    assert (repo / SYSTEM).read_text() == PIN_TEXT


def test_default_fetcher_preserves_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    """Curl's real argv omits -L and its 301 is returned to the gate unchanged."""

    def run(argv: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        assert "-L" not in argv
        assert "--location" not in argv
        return subprocess.CompletedProcess(argv, 0, b"redirect\n301", b"")

    monkeypatch.setattr(subprocess, "run", run)
    assert llvm_major.default_fetcher("https://example.test") == (301, b"redirect")


@pytest.fixture
def saved_iwyu_files() -> list[dict]:
    """Use complete primary metadata, including older amd64-only versions."""
    return json.loads(
        (
            ROOT
            / "docs/research/kb/raw/llvm-23-lane-2026-10-02"
            / "conda-forge-include-what-you-use-files-2026-10-03.json"
        ).read_text()
    )


def files_fetcher(files: list[dict]) -> llvm_major.Fetcher:
    """Return response bytes through the injected network boundary."""
    payload = json.dumps(files).encode()
    return lambda _: (200, payload)


def test_iwyu_pin_holds_when_new_major_arrives(saved_iwyu_files: list[dict]) -> None:
    """The coordinator's future-release arm keeps the pinned-major version."""
    files = saved_iwyu_files + [
        iwyu_file(arch, 23, version="0.27") for arch in ("linux-64", "linux-aarch64")
    ]
    assert llvm_major.iwyu_pin_for(22, files_fetcher(files)) == "0.26"
    assert llvm_major.iwyu_versions_for(23, files_fetcher(files)) == ["0.27"]
    assert llvm_major.iwyu_versions_for(23, files_fetcher(saved_iwyu_files)) == []
    with pytest.raises(ValueError, match="no dual-arch version"):
        llvm_major.iwyu_pin_for(23, files_fetcher(saved_iwyu_files))


def test_iwyu_readiness_survives_later_major(saved_iwyu_files: list[dict]) -> None:
    """A later LLVM release cannot erase a usable older-major IWYU version."""
    files = saved_iwyu_files + [
        iwyu_file(arch, major, version=version)
        for arch in ("linux-64", "linux-aarch64")
        for major, version in ((23, "0.27"), (24, "0.28"))
    ]
    assert llvm_major.iwyu_ready(23, files_fetcher(files))
    assert llvm_major.iwyu_versions_for(23, files_fetcher(files)) == ["0.27"]
    assert llvm_major.iwyu_versions_for(24, files_fetcher(files)) == ["0.28"]


@pytest.mark.parametrize("major", [13, 14, 15, 16])
def test_iwyu_older_single_arch_versions_skipped(
    saved_iwyu_files: list[dict], major: int
) -> None:
    assert llvm_major.iwyu_versions_for(major, files_fetcher(saved_iwyu_files)) == []
    assert llvm_major.iwyu_pin_for(22, files_fetcher(saved_iwyu_files)) == "0.26"


def test_iwyu_versions_sort_numerically() -> None:
    files = [
        iwyu_file(arch, 22, version=version)
        for arch in ("linux-64", "linux-aarch64")
        for version in ("0.9", "0.26", "0.10")
    ]
    assert llvm_major.iwyu_versions_for(22, files_fetcher(files)) == [
        "0.9",
        "0.10",
        "0.26",
    ]
    assert llvm_major.iwyu_pin_for(22, files_fetcher(files)) == "0.26"


def test_incomplete_version_skips_build_validation(
    saved_iwyu_files: list[dict],
) -> None:
    incomplete = iwyu_file("linux-64", 22, version="0.30")
    incomplete["attrs"].pop("build_number")
    incomplete["attrs"]["depends"] = []
    assert (
        llvm_major.iwyu_pin_for(22, files_fetcher([*saved_iwyu_files, incomplete]))
        == "0.26"
    )


@pytest.mark.parametrize(
    "deps", [[], ["libllvm22 >=0", "libllvm23 >=0"], ["libllvm22 >=0", "libllvm22 >=0"]]
)
def test_iwyu_build_requires_one_dependency(deps: list[str]) -> None:
    files = [iwyu_file(arch, 22) for arch in ("linux-64", "linux-aarch64")]
    files[0]["attrs"]["depends"] = deps
    with pytest.raises(ValueError, match="exactly one"):
        llvm_major.iwyu_versions_for(22, files_fetcher(files))


def test_real_iwyu_lock_state() -> None:
    assert llvm_major.iwyu_lock_state(
        (ROOT / ".devcontainer/mise-system.lock").read_text()
    ) == ("0.26", {"linux-x64": 22, "linux-arm64": 22})


@pytest.mark.parametrize("platform", ["linux-x64", "linux-arm64"])
@pytest.mark.parametrize("fault", ["missing", "no-dep", "two-deps"])
def test_iwyu_lock_rejects_missing_or_invalid_platform(
    platform: str, fault: str
) -> None:
    text = lock_text()
    if fault == "missing":
        text = text.replace(
            f'"platforms.{platform}"', f'"platforms.{platform}-ignored"'
        )
    else:
        header = f'[tools."conda:include-what-you-use"."platforms.{platform}"]\n'
        original = header + 'conda_deps = ["libllvm22-22.1.8-build_3"]'
        deps = (
            "[]"
            if fault == "no-dep"
            else '["libllvm22-22.1.8-build_3", "libllvm23-23.1.0-build_0"]'
        )
        text = text.replace(
            original,
            header + f"conda_deps = {deps}",
        )
    with pytest.raises((KeyError, ValueError)):
        llvm_major.iwyu_lock_state(text)


@pytest.mark.parametrize("pin", ['"latest"', '{ version = "0.26" }', '"0"', '"0.26.*"'])
def test_iwyu_pin_parity(repo: Path, pin: str) -> None:
    file = repo / SYSTEM
    file.write_text(
        file.read_text().replace(
            '"conda:include-what-you-use" = "0.26"',
            f'"conda:include-what-you-use" = {pin}',
        )
    )
    assert any(
        "IWYU pin" in violation for violation in llvm_major.parity_violations(repo)
    )
    assert any(
        "IWYU pin" in violation
        for violation in llvm_major.parity_violations(repo, include_iwyu_lock=False)
    )


@pytest.mark.parametrize(
    ("version", "major"), [("0.26", 23), ("0.27", 22), ("0.26", 22)]
)
def test_iwyu_lock_parity(repo: Path, version: str, major: int) -> None:
    (repo / ".devcontainer/mise-system.lock").write_text(lock_text(version, major))
    violations = llvm_major.parity_violations(repo)
    if version == "0.26" and major == 22:
        assert violations == []
    else:
        assert len(violations) == 1
        assert "IWYU lock stale or off-major" in violations[0]
        assert "toml 0.26, apt 22" in violations[0]
        assert "mise run lock-image" in violations[0]
        assert llvm_major.parity_violations(repo, include_iwyu_lock=False) == []


@pytest.mark.parametrize("platform", ["linux-x64", "linux-arm64"])
def test_iwyu_lock_parity_checks_each_platform(repo: Path, platform: str) -> None:
    text = lock_text()
    header = f'[tools."conda:include-what-you-use"."platforms.{platform}"]\n'
    text = text.replace(
        header + 'conda_deps = ["libllvm22-22.1.8-build_3"]',
        header + 'conda_deps = ["libllvm23-23.1.0-build_0"]',
    )
    (repo / ".devcontainer/mise-system.lock").write_text(text)
    assert "IWYU lock stale or off-major" in llvm_major.parity_violations(repo)[0]


def detected_bump_fetcher() -> llvm_major.Fetcher:
    """Serve detection and complete target indexes at the network boundary."""
    gates = network({22, 23})
    names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
    indexes = plan_network(names, version=NEXT_VERSION)

    def fetch(url: str) -> tuple[int, bytes]:
        if "anaconda" in url:
            return files_fetcher(
                [
                    iwyu_file(arch, 23, version="0.27")
                    for arch in ("linux-64", "linux-aarch64")
                ]
            )(url)
        if "llvm-toolchain-resolute-23/" in url and not url.endswith("Release"):
            return indexes(url)
        return gates(url)

    return fetch


@pytest.mark.usefixtures("offline_gh")
def test_detected_bump_moves_iwyu_and_defers_only_lock(
    repo: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    old_lock = (repo / ".devcontainer/mise-system.lock").read_bytes()
    assert (
        llvm_major.bump_main(
            repo,
            fetch=detected_bump_fetcher(),
            releases=releases(23),
        )
        == 0
    )
    output = capsys.readouterr().out
    assert '"conda:include-what-you-use" = "0.27"' in (repo / SYSTEM).read_text()
    assert (repo / SYSTEM).read_text().count('"conda:include-what-you-use"') == 1
    assert "IWYU pin: 0.27" in output
    assert "Next: mise run lock-image (IWYU lock is now stale by design)" in output
    assert (repo / ".devcontainer/mise-system.lock").read_bytes() == old_lock
    assert llvm_major.parity_violations(repo, include_iwyu_lock=False) == []
    assert llvm_major.parity_main(repo) == 1
    assert "IWYU lock stale or off-major" in capsys.readouterr().out
    (repo / ".devcontainer/mise-system.lock").write_text(lock_text("0.27", 23))
    assert llvm_major.parity_violations(repo) == []


@pytest.mark.parametrize("duplicate", [False, True])
def test_detected_bump_counts_iwyu_rewrite(repo: Path, *, duplicate: bool) -> None:
    file = repo / SYSTEM
    if duplicate:
        file.write_text(file.read_text() + '\n"conda:include-what-you-use" = "0.26"\n')
    else:
        file.write_text(
            file.read_text().replace(
                '"conda:include-what-you-use"', "'conda:include-what-you-use'"
            )
        )
    assert llvm_major.parity_violations(repo) == []
    before = tree_bytes(repo)
    detection = llvm_major.detect(
        repo, detected_bump_fetcher(), releases(23), gh=github(), now=NOW
    )
    with pytest.raises(
        ValueError,
        match=f"IWYU pin: expected exactly one rewrite, got {2 if duplicate else 0}",
    ):
        llvm_major.plan_bump(repo, detection, detected_bump_fetcher())
    assert tree_bytes(repo) == before


def test_cli_detect_markdown_held(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Use real parser/dispatch while injecting only subprocess responses."""
    fetch = network({22, 23}, ready=22)

    def run(argv: list[str], **_: object) -> subprocess.CompletedProcess[bytes]:
        if argv[0] == "gh":
            payload = [releases(23)()] if "--paginate" in argv else github()(argv[-1])
            body = gh_output(argv, payload)
        else:
            status, payload = fetch(argv[-1])
            body = payload + f"\n{status}".encode()
        return subprocess.CompletedProcess(argv, 0, body, b"")

    monkeypatch.setattr(subprocess, "run", run)
    args = main.setup_parser().parse_args(["llvm-detect", "--markdown"])
    with pytest.raises(SystemExit) as result:
        main.run_command(args, repo)
    assert result.value.code == 4
    report = capsys.readouterr().out
    for field in (
        "Pinned: 22",
        "Newest GA: 23",
        "Served:",
        "IWYU ready:",
        "Target: 22",
        "Held on: 23",
        "23 GA+served, held: IWYU",
        "| Major | Release head | Latest GA tag |",
        "| 23 |",
        TAG22,
        "llvmorg-23.1.0",
        "Frozen:",
    ):
        assert field in report
