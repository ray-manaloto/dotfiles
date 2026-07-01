"""Tests for the devcontainer freshness gate (dotfiles_setup.container)."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

import pytest

from dotfiles_setup import container

_WORKSPACE = Path("/workspaces-host/dotfiles")


def _cp(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


class _FakeDocker:
    """Routes container._run calls to canned outputs keyed by the command shape."""

    def __init__(
        self,
        *,
        container_id: str | None = "cafef00dbeef",
        bind_source: str | None = str(_WORKSPACE),
        smoke_rc: int = 0,
        smoke_out: str = "=== All smoke checks passed ===\n",
        head: str = "e61b3ea0",
        branch: str = "main",
    ) -> None:
        self.container_id = container_id
        self.bind_source = bind_source
        self.smoke_rc = smoke_rc
        self.smoke_out = smoke_out
        self.head = head
        self.branch = branch

    def __call__(self, cmd: list[str], **_kwargs: object):
        if cmd[:2] == ["git", "-C"]:
            return _cp((self.head if cmd[-1] == "HEAD" else self.branch) + "\n")
        if cmd[:3] == ["docker", "ps", "-q"]:
            return _cp((self.container_id + "\n") if self.container_id else "")
        if cmd[:2] == ["docker", "inspect"]:
            if self.bind_source is None:
                return _cp("[]")
            return _cp(
                '[{"Type":"bind","Source":"%s","Destination":"/workspaces/dotfiles"}]'
                % self.bind_source
            )
        if cmd[:2] == ["devcontainer", "exec"]:
            return _cp(self.smoke_out, returncode=self.smoke_rc)
        raise AssertionError(f"unexpected command: {cmd}")


def _names(checks):
    return {c.name: c for c in checks}


def test_all_green_when_fresh(monkeypatch: pytest.MonkeyPatch) -> None:
    """A running, bind-mounted container with green smoke passes all checks."""
    monkeypatch.setattr(container, "_run", _FakeDocker())
    checks = container.verify_latest(_WORKSPACE)

    assert all(c.ok for c in checks)
    assert {"container-running", "workspace-bind-mount", "smoke-tiers-1-3"} == set(
        _names(checks)
    )


def test_no_container_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    """With no running container, only the (failed) container-running check returns."""
    monkeypatch.setattr(container, "_run", _FakeDocker(container_id=None))
    checks = container.verify_latest(_WORKSPACE)

    assert len(checks) == 1
    assert checks[0].name == "container-running"
    assert checks[0].ok is False


def test_not_bind_mounted_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """A container that does not bind-mount the workspace fails source liveness."""
    monkeypatch.setattr(container, "_run", _FakeDocker(bind_source="/some/other/path"))

    assert (
        _names(container.verify_latest(_WORKSPACE))["workspace-bind-mount"].ok is False
    )


def test_stale_base_fails_via_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stale base (smoke identity FAIL) hard-fails smoke-tiers-1-3."""
    monkeypatch.setattr(
        container,
        "_run",
        _FakeDocker(
            smoke_rc=1,
            smoke_out="[tier1] image identity\n  FAIL: in-image mise config X != repo Y\n",
        ),
    )
    smoke = _names(container.verify_latest(_WORKSPACE))["smoke-tiers-1-3"]

    assert smoke.ok is False
    assert "FAIL" in smoke.detail
    assert "dev-rebuild" in smoke.detail


def test_run_smoke_false_skips_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_smoke=False omits the smoke check (for a fast pre-check)."""
    monkeypatch.setattr(container, "_run", _FakeDocker())

    assert "smoke-tiers-1-3" not in _names(
        container.verify_latest(_WORKSPACE, run_smoke=False)
    )


def test_main_returns_1_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """verify_latest_main returns 1 when any check fails."""
    monkeypatch.setattr(container, "_run", _FakeDocker(smoke_rc=1))

    assert container.verify_latest_main(_WORKSPACE) == 1


def test_main_returns_0_when_all_green(monkeypatch: pytest.MonkeyPatch) -> None:
    """verify_latest_main returns 0 when every check passes."""
    monkeypatch.setattr(container, "_run", _FakeDocker())

    assert container.verify_latest_main(_WORKSPACE) == 0
