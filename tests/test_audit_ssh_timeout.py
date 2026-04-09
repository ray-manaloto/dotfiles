"""Tests for bounded ssh-add -l timeout behavior in audit.

Gating tests for PR 1. See issue #77 for the lifecycle debt this does NOT fix.
"""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from dotfiles_setup.audit import AuditError, DevEnvironmentAuditor
from dotfiles_setup.config import DotfilesConfig


def _make_auditor() -> DevEnvironmentAuditor:
    cfg = DotfilesConfig()
    return DevEnvironmentAuditor(config=cfg)


def test_audit_raises_on_ssh_add_timeout() -> None:
    """ssh-add -l hanging past timeout must raise AuditError, not SystemExit."""
    auditor = _make_auditor()

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if cmd[:2] == ["ssh-add", "-l"]:
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=3)
        # All other subprocess calls: pretend they succeeded with empty output.
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with (
        patch("dotfiles_setup.audit.subprocess.run", side_effect=fake_run),
        pytest.raises(
            AuditError, match=r"^SSH bridge unresponsive — see host-ssh-proxy\.log"
        ),
    ):
        auditor.audit_ssh()


def test_audit_distinguishes_no_keys_from_unresponsive() -> None:
    """`ssh-add -l` exit 1 with 'no identities' must NOT raise AuditError."""
    auditor = _make_auditor()

    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if cmd[:2] == ["ssh-add", "-l"]:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="The agent has no identities.\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("dotfiles_setup.audit.subprocess.run", side_effect=fake_run):
        # Should not raise — empty agent is not a bridge failure.
        auditor.audit_ssh()
