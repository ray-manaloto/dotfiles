# Copyright (c) 2026 Raymond Manaloto
"""Offline control arms for GA selection, IWYU readiness, parity and planning."""

from __future__ import annotations

import gzip
import json
import subprocess
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
VERSION = "1:22.1.8~++snapshot"
PIN_TEXT = f"""[bootstrap.packages]
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


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Prepare a small independent repository with every parity consumer."""
    files = {
        SYSTEM: PIN_TEXT,
        DOCKER: "ARG BASE_IMAGE=ubuntu:26.04@sha256:abc\nARG LLVM_MAJOR=22\n",
        "docker-bake.hcl": (
            'variable "BASE_IMAGE" {\n default = "ubuntu:26.04@sha256:abc"\n}\n'
        ),
        "renovate.json": json.dumps(
            {
                "customManagers": [
                    {
                        "registryUrls": [
                            "https://apt.llvm.org/resolute?suite=llvm-toolchain-resolute-22&components=main&binaryArch=amd64"
                        ]
                    }
                ]
            }
        ),
    }
    for name in ("image", "apt_pins", "apt_repo", "main"):
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
    served: set[int], *, ready: int = 23, trunk: int = 24
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
                (200, f"Codename: llvm-toolchain-resolute-{major}\n".encode())
                if major in served
                else (404, b"")
            )
        return 200, gzip.compress(
            f"Package: clang-{trunk}\nVersion: {trunk}.0\n\n".encode()
        )

    return fetch


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
        repo, network(served, ready=ready, trunk=trunk), releases(ga)
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
        llvm_major.detect(repo, network(served, ready=ready, trunk=trunk), releases(ga))


def test_ga_filter_and_no_matches() -> None:
    """RC/init/prerelease/draft records cannot select a new major."""
    assert llvm_major.newest_ga_major(releases(23)) == 23
    with pytest.raises(ValueError, match="no GA"):
        llvm_major.newest_ga_major(lambda: releases(23)()[1:])


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
    """The anchor and the complete LLVM family cannot contradict each other."""
    variants = {
        "missing": PIN_TEXT.replace('"apt:clang-22"', '"apt:not-clang"'),
        "multiple": PIN_TEXT.replace("[env]", f'"apt:clang-23" = "{VERSION}"\n[env]'),
        "anchor-version": PIN_TEXT.replace(VERSION, "1:23.1.0"),
        "mixed-major": PIN_TEXT.replace('"apt:libllvm22"', '"apt:libllvm23"'),
        "mixed-version": PIN_TEXT.replace(
            f'"apt:libllvm22" = "{VERSION}"', '"apt:libllvm22" = "1:22.1.7"'
        ),
    }
    with pytest.raises((TypeError, ValueError)):
        llvm_major.pinned_major(variants[mutation])


def test_pin_inventory() -> None:
    """Shared version captures four major-less names and the commented pin."""
    assert llvm_major.pinned_major(PIN_TEXT) == 22
    pins = llvm_major.llvm_pins(PIN_TEXT)
    assert len(pins) == 8
    assert pins["clang-22-doc"] == (VERSION, False)
    assert pins["libomp5"] == (VERSION, True)
    assert "curl" not in pins


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
    assert not llvm_major.iwyu_ready(22, lambda _: (200, json.dumps(files).encode()))


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
        ("renovate.json", "resolute-22", "resolute-23", "renovate.json suite"),
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


def test_commented_pin_parity(repo: Path) -> None:
    """An inactive package naming another major still violates parity."""
    file = repo / SYSTEM
    file.write_text(file.read_text().replace("clang-22-doc", "clang-23-doc"))
    assert "mixed majors" in llvm_major.parity_violations(repo)[0]


def plan_network(names: set[str], *, fault: str = "") -> llvm_major.Fetcher:
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
        index = "\n\n".join(
            f"Package: {name}\nVersion: "
            f"{'1:23.1.1' if fault == 'version' and i == 0 else '1:23.1.0'}"
            for i, name in enumerate(selected)
        )
        return 200, gzip.compress((index + "\n\n").encode())

    return fetch


def test_plan_preserves_status_and_majorless_names(repo: Path) -> None:
    """A future bump changes only pins/path/ARG/registry suite and stays clean."""
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
    plan = llvm_major.plan_bump(repo, detection, plan_network(names))
    assert set(plan.pins) == names
    assert plan.pins["clang-23-doc"] == ("1:23.1.0", False)
    assert plan.pins["libomp5"] == ("1:23.1.0", True)
    assert set(plan.after) == {SYSTEM, DOCKER, "renovate.json"}
    assert (repo / SYSTEM).read_text() == PIN_TEXT
    plan.write(repo)
    assert llvm_major.parity_violations(repo) == []
    assert '"apt:curl" = "8.0"' in (repo / SYSTEM).read_text()


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
        lambda root, *, json_output: handler(
            root,
            json_output=json_output,
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


def test_cli_held_bump_changes_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
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


def test_explicit_dry_run_skips_gates(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The major control arm plans but cannot write or consult release/gate data."""
    names = {name.replace("22", "23") for name in llvm_major.llvm_pins(PIN_TEXT)}
    assert (
        llvm_major.bump_main(repo, dry_run=True, major=23, fetch=plan_network(names))
        == 0
    )
    assert "8 pins (7 active, 1 commented), amd64 + arm64" in capsys.readouterr().out
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
    plan = llvm_major.plan_bump(repo, detection, plan_network(names))
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
