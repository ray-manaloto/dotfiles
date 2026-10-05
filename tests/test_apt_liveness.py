# Copyright (c) 2026 Raymond Manaloto
"""Publication checks use real package/version fields and injected index bytes."""

from __future__ import annotations

import gzip
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from dotfiles_setup import apt_liveness, llvm_major

ROOT = Path(__file__).resolve().parents[1]
VERSION = "1:22.1.8~++20260714015917+ca7933e47d3a-1~exp1~20260714135927.17"
ZLIB = "1:1.3.dfsg+really1.3.1-1ubuntu3"
TEXT = (
    "[bootstrap.packages]\n"
    f'"apt:clang-22" = "{VERSION}"\n'
    f'"apt:libc++1" = "{VERSION}"\n'
    f'# "apt:libbolt-22-dev" = "{VERSION}"\n'
    '"apt:curl" = "8.18.0-1ubuntu2.7"\n'
    f'"apt:zlib1g-dev" = "{ZLIB}"\n'
    "[env]\n"
    '"apt:outside" = "1"\n'
)


def paragraph(name: str, version: str) -> str:
    """Use the Package/Version/Section/Description fields of live paragraphs."""
    fields = {
        "clang-22": ("devel", "C, C++ and Objective-C compiler"),
        "libbolt-22-dev": ("libdevel", "Post-link optimizer"),
        "libc++1": ("libs", "LLVM C++ Standard library"),
        "curl": ("web", "command line tool for transferring data with URL syntax"),
        "zlib1g-dev": ("libdevel", "compression library - development"),
    }
    section, description = fields[name]
    return (
        f"Package: {name}\nVersion: {version}\n"
        f"Section: {section}\nDescription: {description}\n\n"
    )


def network(
    *,
    ubuntu_version: str = "8.18.0-1ubuntu2.7",
    omit: str = "",
    status: int = 200,
    malformed: bytes | None = None,
    pocket: str = "-updates",
) -> tuple[llvm_major.Fetcher, list[str]]:
    """Provide gzipped dual-arch indexes and the real base metadata response shape."""
    seen: list[str] = []

    def fetch(url: str) -> tuple[int, bytes]:
        seen.append(url)
        if "changelogs.ubuntu.com" in url:
            return 200, b"Dist: resolute\nVersion: 26.04\n\n"
        if status != 200:
            return status, b"upstream error"
        if malformed is not None:
            return 200, malformed
        if "apt.llvm.org" in url:
            names = ["clang-22", "libc++1", "libbolt-22-dev"]
            if "binary-arm64" in url:
                names = [name for name in names if name != omit]
            body = "".join(paragraph(name, VERSION) for name in names)
        else:
            suite = urlsplit(url).path.split("/")[3]
            curl = ubuntu_version if suite == f"resolute{pocket}" else "8.18.0-1ubuntu2"
            body = paragraph("curl", curl) + paragraph("zlib1g-dev", ZLIB)
        return 200, gzip.compress(body.encode())

    return fetch, seen


def test_all_live_and_arch_mirrors() -> None:
    fetch, seen = network()
    assert apt_liveness.check(TEXT, fetch, root=ROOT) == []
    indexes = [url for url in seen if url.endswith("Packages.gz")]
    assert len(indexes) == 8
    arm64_ubuntu = [
        url for url in indexes if "arm64" in url and "apt.llvm.org" not in url
    ]
    assert len(arm64_ubuntu) == 3
    assert all(
        url.startswith("http://ports.ubuntu.com/ubuntu-ports/") for url in arm64_ubuntu
    )
    assert any(
        "http://security.ubuntu.com/ubuntu/dists/resolute-security/" in url
        for url in indexes
    )


@pytest.mark.parametrize("pocket", ["", "-updates", "-security"])
def test_each_pocket_can_publish_the_exact_pin(pocket: str) -> None:
    fetch, _ = network(pocket=pocket)
    assert apt_liveness.check(TEXT, fetch, root=ROOT) == []


def test_ubuntu_bump_is_stale_and_lists_live_versions() -> None:
    fetch, _ = network(ubuntu_version="8.18.0-1ubuntu2.8")
    findings = apt_liveness.check(TEXT, fetch, root=ROOT)
    assert {item.arch for item in findings} == {"amd64", "arm64"}
    assert all(item.name == "curl" and item.kind == "stale" for item in findings)
    assert all("8.18.0-1ubuntu2.8" in item.versions for item in findings)
    assert all(item.pinned == "8.18.0-1ubuntu2.7" for item in findings)


@pytest.mark.parametrize("name", ["clang-22", "libc++1", "libbolt-22-dev"])
def test_llvm_missing_only_on_arm64_including_commented_pin(name: str) -> None:
    fetch, _ = network(omit=name)
    assert apt_liveness.check(TEXT, fetch, root=ROOT) == [
        apt_liveness.Finding(
            name, VERSION, name != "libbolt-22-dev", "arm64", "missing", ()
        )
    ]


def test_published_wrong_llvm_version_is_stale_on_one_arch() -> None:
    fetch, _ = network()

    def rotated(url: str) -> tuple[int, bytes]:
        status, body = fetch(url)
        if "apt.llvm.org" in url and "binary-arm64" in url:
            body = gzip.compress(
                gzip.decompress(body).replace(VERSION.encode(), b"1:22.1.8+changed")
            )
        return status, body

    findings = apt_liveness.check(TEXT, rotated, root=ROOT)
    assert len(findings) == 3
    assert all(item.arch == "arm64" and item.kind == "stale" for item in findings)
    assert all(item.versions == ("1:22.1.8+changed",) for item in findings)


@pytest.mark.parametrize("status", [301, 404, 500])
def test_http_failures_raise(status: int) -> None:
    fetch, _ = network(status=status)
    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        apt_liveness.check(TEXT, fetch, root=ROOT)


@pytest.mark.parametrize(
    "raw",
    [
        b"bad gzip",
        gzip.compress(b"not a Packages index"),
        gzip.compress(b"Package: broken\n\n"),
    ],
)
def test_malformed_index_raises(raw: bytes) -> None:
    fetch, _ = network(malformed=raw)
    with pytest.raises((OSError, ValueError)):
        apt_liveness.check(TEXT, fetch, root=ROOT)


def test_fetch_failure_raises() -> None:
    def broken(_: str) -> tuple[int, bytes]:
        msg = "network unavailable"
        raise RuntimeError(msg)

    with pytest.raises(RuntimeError, match="network unavailable"):
        apt_liveness.check(TEXT, broken, root=ROOT)


def test_epoch_only_routes_to_ubuntu() -> None:
    fetch, _ = network()

    def wrong_upstream(url: str) -> tuple[int, bytes]:
        status, body = fetch(url)
        if "changelogs.ubuntu.com" in url:
            return status, body
        plain = gzip.decompress(body)
        if "apt.llvm.org" in url:
            plain += paragraph("zlib1g-dev", ZLIB).encode()
        else:
            plain = plain.replace(ZLIB.encode(), b"1:9.9-1ubuntu1")
        return status, gzip.compress(plain)

    findings = apt_liveness.check(TEXT, wrong_upstream, root=ROOT)
    assert len(findings) == 2
    assert all(item.name == "zlib1g-dev" and item.kind == "stale" for item in findings)
    assert all(item.versions == ("1:9.9-1ubuntu1",) for item in findings)


def test_bootstrap_inventory_includes_comments_and_excludes_other_tables() -> None:
    pins = llvm_major.bootstrap_pins(TEXT)
    assert len(pins) == 5
    assert pins["libbolt-22-dev"] == (VERSION, False)
    assert pins["zlib1g-dev"] == (ZLIB, True)
    assert "outside" not in pins


@pytest.mark.parametrize(
    ("status", "version", "expected"),
    [
        (200, "8.18.0-1ubuntu2.7", 0),
        (200, "8.18.0-1ubuntu2.8", 3),
        (500, "8.18.0-1ubuntu2.7", 1),
    ],
)
def test_cli_exit_codes_and_markdown(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    status: int,
    version: str,
    expected: int,
) -> None:
    (tmp_path / ".devcontainer").mkdir()
    (tmp_path / ".devcontainer/mise-system.toml").write_text(TEXT)
    (tmp_path / ".devcontainer/Dockerfile").write_text(
        "ARG BASE_IMAGE=ubuntu:26.04@sha256:abc\n"
    )
    (tmp_path / "docker-bake.hcl").write_text(
        'variable "BASE_IMAGE" {\n default = "ubuntu:26.04@sha256:abc"\n}\n'
    )
    fetch, _ = network(status=status, ubuntu_version=version)
    assert (
        apt_liveness.apt_liveness_main(tmp_path, markdown=True, fetch=fetch) == expected
    )
    output = capsys.readouterr()
    if expected == 1:
        assert "HTTP 500" in output.err
        assert "published" not in output.out
    else:
        assert "# apt pin liveness" in output.out
        assert "5 pins (4 active, 1 commented)" in output.out
        assert "3 LLVM (2 active, 1 commented)" in output.out
        assert "2 Ubuntu (2 active, 0 commented)" in output.out
        assert ("stale: curl" in output.out) == (expected == 3)


def test_actual_tree_inventory() -> None:
    text = (ROOT / ".devcontainer/mise-system.toml").read_text()
    pins = llvm_major.bootstrap_pins(text)
    llvm = llvm_major.llvm_pins(text)
    assert len(pins) == 72
    assert sum(active for _, active in pins.values()) == 66
    assert len(llvm) == 58
    assert sum(active for _, active in llvm.values()) == 52


def test_report_limits_installability_claim() -> None:
    report = apt_liveness.render_report(TEXT, [], markdown=True)
    assert "Index presence is not installability." in report
    assert (
        "verify-apt-pins checks installability of active pins on one platform only"
        in report
    )


@pytest.mark.parametrize(
    "raw",
    [
        gzip.compress(paragraph("clang-22", VERSION).encode())[:-4],
        b"\x1f\x8b\x08\x00" + b"\x00" * 6 + b"\x07" + b"\x00" * 8,
        b"bad gzip",
        gzip.compress(b"Package: broken\n\n"),
    ],
    # missing-version-paragraph hits the post-parse "empty or malformed" check,
    # not the except tuple: parse_packages reads every field with .get, so there
    # is no KeyError arm (cold review F1 on 2c0ca279).
    ids=[
        "truncated-gzip",
        "corrupt-deflate",
        "bad-gzip-header",
        "missing-version-paragraph",
    ],
)
def test_cli_malformed_index_fails_cleanly_with_url(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], raw: bytes
) -> None:
    (tmp_path / ".devcontainer").mkdir()
    for name in (".devcontainer/Dockerfile", "docker-bake.hcl"):
        (tmp_path / name).write_text((ROOT / name).read_text())
    (tmp_path / ".devcontainer/mise-system.toml").write_text(TEXT)
    fetch, seen = network(malformed=raw)
    assert apt_liveness.apt_liveness_main(tmp_path, fetch=fetch) == 1
    output = capsys.readouterr()
    assert "apt pin liveness failed:" in output.err
    assert seen[-1] in output.err
    assert "Traceback" not in output.err
    assert output.out == ""
