# Copyright (c) 2026 Raymond Manaloto
"""Tests for the local image-lock task (dotfiles_setup.image_lock).

This module encodes a recipe whose failure mode is **silent truncation**, so
the tests that matter are the ones pinning the three refusals: a host that
cannot write linux conda checksums, a missing ``npm``, and a convergence loop
that ran out of passes. Each is a case where doing the work anyway produces a
plausible-looking lock that is wrong.

The platform derivation is checked against the **real committed lock** as well
as a fixture — the fixture proves the parse, the real file proves the parse is
pointed at something whose shape has not moved (`macos-x64` entries that a
``--platform linux-x64`` pass would drop are the whole reason this exists).

Nothing here reaches the network or spawns mise: the installer fetch, the
subprocess runner and the host facts are all injected parameters.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import image_lock, platform_target

REPO_ROOT = Path(__file__).parent.parent

_TWO_PLATFORM_LOCK = (
    '[[tools.hk]]\nversion = "1.0"\n\n'
    '[tools.hk."platforms.linux-x64"]\nchecksum = "sha256:a"\n\n'
    '[tools.hk."platforms.macos-x64"]\nchecksum = "sha256:b"\n\n'
    '[conda-packages.linux-x64.git]\nurl = "https://example.invalid/g"\n'
)


def _completed(rc: int) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess([], rc, b"", b"")


class _Recorder:
    """A stand-in for ``subprocess.run`` that remembers what it was handed.

    One typed object rather than a fake per test: the assertions here are all
    "what argv / what env did the code build", so recording is the whole job.
    """

    def __init__(self, codes: list[int] | None = None) -> None:
        self.codes = list(codes or [0])
        self.argvs: list[list[str]] = []
        self.envs: list[dict[str, str]] = []

    def __call__(
        self, argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        self.argvs.append(argv)
        env = kwargs.get("env")
        if isinstance(env, dict):
            self.envs.append(env)
        rc = self.codes.pop(0) if len(self.codes) > 1 else self.codes[0]
        return _completed(rc)


# --------------------------------------------------------------------------- #
# Platform derivation — gotcha 2
# --------------------------------------------------------------------------- #


def test_platforms_union_tool_entries_and_the_conda_section() -> None:
    assert image_lock.lock_platforms(_TWO_PLATFORM_LOCK) == (
        "linux-x64",
        "macos-x64",
    )


def test_the_real_committed_lock_still_carries_a_non_linux_platform() -> None:
    """Pin that the derived platform set still includes a non-linux platform.

    If it did not, a ``--platform linux-x64`` pass would be safe and this
    module's central precaution would be dead code. Measured 2026-08-08: six
    platforms, 29 macos-x64 tool entries.
    """
    derived = image_lock.lock_platforms(
        (REPO_ROOT / image_lock.SYSTEM_LOCK).read_text()
    )
    assert "linux-x64" in derived
    assert any(name.startswith("macos-") for name in derived), (
        "the committed image lock no longer carries a macOS platform — "
        "re-check whether deriving the platform set is still load-bearing"
    )


def test_an_empty_lock_derives_no_platforms_rather_than_guessing() -> None:
    assert image_lock.lock_platforms("") == ()


# --------------------------------------------------------------------------- #
# Widening the publish matrix must widen the regen (#698)
# --------------------------------------------------------------------------- #


def test_a_required_platform_absent_from_the_lock_is_still_locked() -> None:
    """#698's ordering trap: deriving from the lock can only PRESERVE coverage.

    `lock_platforms` reads the committed file, so a newly-published
    architecture — which by definition has no entries yet — would be skipped by
    the very run meant to add it. The regen would report success across the
    platforms it already had.
    """
    platforms = image_lock.platforms_to_lock(
        _TWO_PLATFORM_LOCK, required=("linux-x64", "linux-arm64")
    )

    assert platforms == ("linux-arm64", "linux-x64", "macos-x64")


def test_every_published_architecture_is_required_by_default() -> None:
    """The default must be what CI publishes, not what the lock already holds.

    Binds the two declarations together: widening `PUBLISHED_ARCHES` is what
    makes the next regen produce that architecture's entries.
    """
    required = set(platform_target.mise_lock_platforms())

    derived = set(image_lock.platforms_to_lock(_TWO_PLATFORM_LOCK))

    assert required <= derived


def test_an_empty_lock_still_yields_the_required_platforms() -> None:
    """A lock written from nothing must not be born single-architecture."""
    assert image_lock.platforms_to_lock("", required=("linux-arm64",)) == (
        "linux-arm64",
    )


# --------------------------------------------------------------------------- #
# Host capability — gotcha 1
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("system", "machine", "capable"),
    [
        ("Linux", "x86_64", True),
        ("Linux", "amd64", True),
        ("Linux", "aarch64", False),
        ("Darwin", "arm64", False),
        ("Darwin", "x86_64", False),
        ("Windows", "AMD64", False),
    ],
)
def test_host_capability_covers_both_axes(
    *, system: str, machine: str, capable: bool
) -> None:
    """OS and machine are separate refusals; an arm64 Linux is not the image.

    The target is stated explicitly (#673): since the accepted machines derive
    from the platform parameter, a test that let it default would be asserting
    against whatever the ambient environment exported — and would invert on an
    unpinned arm64 host.
    """
    verdict, reason = image_lock.host_can_lock(
        system, machine, target_platform="linux/amd64/v2"
    )
    assert verdict is capable
    assert reason


@pytest.mark.parametrize(
    ("target", "machine", "capable"),
    [
        ("linux/amd64/v2", "x86_64", True),
        ("linux/amd64/v2", "aarch64", False),
        ("linux/arm64/v8", "aarch64", True),
        ("linux/arm64/v8", "x86_64", False),
    ],
)
def test_accepted_machines_follow_the_target_platform(
    *, target: str, machine: str, capable: bool
) -> None:
    """The lock host must match the IMAGE, so the gate tracks the parameter.

    Without this the gate would keep demanding x86_64 after #676 publishes
    arm64 — refusing the only host that could write that lock.
    """
    verdict, _ = image_lock.host_can_lock("Linux", machine, target_platform=target)
    assert verdict is capable


def test_the_darwin_refusal_names_the_upstream_defect() -> None:
    _, reason = image_lock.host_can_lock("Darwin", "arm64")
    assert "jdx/mise#7700" in reason


def test_npm_is_checked_by_name_not_by_a_package_manager() -> None:
    """The bun binary does NOT satisfy mise's npm backend, which execs npm."""
    assert image_lock.npm_available(
        lambda name: "/usr/bin/npm" if name == "npm" else None
    )
    assert not image_lock.npm_available(
        lambda name: "/usr/bin/bun" if name == "bun" else None
    )


# --------------------------------------------------------------------------- #
# The lock command and its convergence loop
# --------------------------------------------------------------------------- #


def test_every_platform_becomes_its_own_flag() -> None:
    argv = image_lock.lock_command(
        Path("/s/mise-pinned"), Path("/s"), ("linux-x64", "macos-x64")
    )
    assert argv == [
        "/s/mise-pinned",
        "lock",
        "--platform",
        "linux-x64",
        "--platform",
        "macos-x64",
        "-C",
        "/s",
    ]


def test_a_later_pass_may_rescue_an_earlier_failure() -> None:
    """The loop exists because GitHub quota exhausts mid-run, not for flakiness."""
    recorder = _Recorder([1, 1, 0])
    image_lock.run_lock_passes(
        Path("/s/mise-pinned"), Path("/s"), ("linux-x64",), passes=5, run=recorder
    )
    assert len(recorder.argvs) == 3


def test_exhausting_every_pass_raises_rather_than_collecting() -> None:
    with pytest.raises(image_lock.ImageLockError, match="did not converge"):
        image_lock.run_lock_passes(
            Path("/s/mise-pinned"),
            Path("/s"),
            ("linux-x64",),
            passes=2,
            run=lambda *_a, **_k: _completed(1),
        )


def test_both_tiers_are_locked_in_one_pass() -> None:
    """Pin MISE_ENV=runtime, which is what makes mise write mise.runtime.lock.

    Both tiers come from one pass (#160 T9). Dropping it is a realistic
    tidy-up, and the result is a runtime lock that is never regenerated at
    all — invisible in the system lock's diff.
    """
    recorder = _Recorder()
    image_lock.run_lock_passes(
        Path("/s/mise-pinned"), Path("/s"), ("linux-x64",), run=recorder
    )
    assert recorder.envs[0]["MISE_ENV"] == "runtime"
    assert recorder.envs[0]["MISE_TRUSTED_CONFIG_PATHS"] == "/s"


# --------------------------------------------------------------------------- #
# Installing the pinned mise
# --------------------------------------------------------------------------- #


def test_the_installer_fetch_refuses_a_non_https_url() -> None:
    """Its output is piped to `sh`, so the scheme is a security boundary."""
    with pytest.raises(image_lock.ImageLockError, match="non-https"):
        image_lock.fetch_installer("http://example.invalid/install.sh")
    with pytest.raises(image_lock.ImageLockError, match="non-https"):
        image_lock.fetch_installer("file:///tmp/install.sh")


def test_a_failed_install_raises_with_the_installer_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        image_lock.subprocess,
        "run",
        lambda *_a, **_k: subprocess.CompletedProcess([], 1, b"", b"no network"),
    )
    with pytest.raises(image_lock.ImageLockError, match="no network"):
        image_lock.install_pinned_mise(
            tmp_path, "2026.7.0", fetch=lambda _u: b"#!/bin/sh\n"
        )


def test_an_installer_that_exits_zero_without_writing_the_binary_still_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rc=0 is not evidence the binary exists — check the artifact, not the code."""
    monkeypatch.setattr(image_lock.subprocess, "run", lambda *_a, **_k: _completed(0))
    with pytest.raises(image_lock.ImageLockError, match="is absent"):
        image_lock.install_pinned_mise(
            tmp_path, "2026.7.0", fetch=lambda _u: b"#!/bin/sh\n"
        )


def test_the_pinned_version_is_passed_to_the_installer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pin that the Dockerfile's MISE_VERSION reaches the installer.

    Lock formats are not cross-version compatible, so an unpinned install
    produces a lock the image's ``mise install --locked`` rejects.
    """
    recorder = _Recorder()

    def writing_run(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        result = recorder(argv, **kwargs)
        Path(recorder.envs[-1]["MISE_INSTALL_PATH"]).write_text("#!/bin/sh\n")
        return result

    monkeypatch.setattr(image_lock.subprocess, "run", writing_run)
    binary = image_lock.install_pinned_mise(
        tmp_path, "2026.7.0", fetch=lambda _u: b"#!/bin/sh\n"
    )
    assert recorder.envs[-1]["MISE_VERSION"] == "v2026.7.0"
    assert binary == tmp_path / image_lock.PINNED_MISE_DIRNAME


# --------------------------------------------------------------------------- #
# Container routing
# --------------------------------------------------------------------------- #


def test_the_inner_call_cannot_recurse() -> None:
    """Pin the flag that terminates the recursion.

    Without ``--no-container`` the inner run re-evaluates the host; on a
    misconfigured container that finds it incapable and routes again, forever.
    """
    argv = image_lock.container_command(
        Path("/repo"),
        id_labels=("dotfiles.workspace=deadbeef", "dotfiles.arch=amd64"),
    )
    assert argv[:4] == ["devcontainer", "exec", "--workspace-folder", "/repo"]
    assert argv[4:8] == [
        "--id-label",
        "dotfiles.workspace=deadbeef",
        "--id-label",
        "dotfiles.arch=amd64",
    ]
    assert "--no-container" in argv
    assert "docker" not in argv


def test_platform_flags_are_passed_through_to_the_inner_call() -> None:
    argv = image_lock.container_command(Path("/repo"), ("--platform", "linux-x64"))
    assert argv[-2:] == ["--platform", "linux-x64"]


def test_an_incapable_host_routes_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(image_lock, "host_can_lock", lambda: (False, "Darwin"))
    seen: list[list[str]] = []
    monkeypatch.setattr(
        image_lock.subprocess,
        "run",
        lambda argv, **_k: (seen.append(argv), _completed(0))[1],
    )
    assert image_lock.image_lock_main(REPO_ROOT) == 0
    assert seen
    assert seen[0][0] == "devcontainer"


def test_an_incapable_host_with_no_container_refuses_instead_of_truncating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The refusal is the feature: doing it anyway yields a lock that LOOKS fine."""
    monkeypatch.setattr(image_lock, "host_can_lock", lambda: (False, "Darwin/arm64"))
    called: list[str] = []
    monkeypatch.setattr(
        image_lock.subprocess,
        "run",
        lambda *_a, **_k: (called.append("ran"), _completed(0))[1],
    )
    assert image_lock.image_lock_main(REPO_ROOT, container=False) == 1
    assert not called, "nothing may be executed once the host is refused"


def test_a_capable_host_without_npm_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(image_lock, "host_can_lock", lambda: (True, "Linux/x86_64"))
    monkeypatch.setattr(image_lock, "npm_available", lambda: False)
    assert image_lock.image_lock_main(REPO_ROOT, container=False) == 1


def test_container_true_routes_even_from_a_capable_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(image_lock, "host_can_lock", lambda: (True, "Linux/x86_64"))
    seen: list[list[str]] = []
    monkeypatch.setattr(
        image_lock.subprocess,
        "run",
        lambda argv, **_k: (seen.append(argv), _completed(0))[1],
    )
    assert image_lock.image_lock_main(REPO_ROOT, container=True) == 0
    assert seen[0][0] == "devcontainer"


# --------------------------------------------------------------------------- #
# The wiring the fixtures cannot see
# --------------------------------------------------------------------------- #


def test_the_mise_task_calls_the_cli_rather_than_reimplementing_the_recipe() -> None:
    """The recipe living in TWO places is the defect #650 was filed about."""
    mise_toml = (REPO_ROOT / "mise.toml").read_text()
    assert "[tasks.lock-image]" in mise_toml
    assert "dotfiles-setup image-lock" in mise_toml
