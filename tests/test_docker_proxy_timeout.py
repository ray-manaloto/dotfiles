"""Tests for bounded-fail-loud behavior in docker._proxy_connection.

Gating tests for PR 1: "bound ssh-bridge failure path to ≤3.5s".
See .omc/plans/session-2026-04-09b-bridge-faillound-then-72.md and issue #77.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from dotfiles_setup import docker as docker_mod


def test_container_proxy_connect_timeout(capsys: pytest.CaptureFixture[str]) -> None:
    """Container-side proxy must bound connect() and emit BRIDGE_UNREACHABLE."""
    fake_upstream = MagicMock()
    fake_upstream.connect.side_effect = TimeoutError("simulated blocking connect")
    fake_client = MagicMock()

    with patch.object(
        docker_mod.socket, "create_connection", side_effect=TimeoutError("simulated")
    ) as create_conn:
        docker_mod._proxy_connection(
            fake_client,
            target_unix=None,
            target_tcp=("host.docker.internal", 49981),
        )

    # create_connection must have been called with timeout=3.0
    _, kwargs = create_conn.call_args
    assert kwargs.get("timeout") == 3.0
    captured = capsys.readouterr()
    assert "BRIDGE_UNREACHABLE" in captured.err
    assert "host=host.docker.internal" in captured.err
    assert "port=49981" in captured.err
    fake_client.close.assert_called()


def test_container_proxy_closes_unix_client_on_upstream_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """On ConnectionRefusedError the unix client socket must be closed."""
    fake_client = MagicMock()

    with patch.object(
        docker_mod.socket,
        "create_connection",
        side_effect=ConnectionRefusedError(61, "Connection refused"),
    ):
        docker_mod._proxy_connection(
            fake_client,
            target_unix=None,
            target_tcp=("host.docker.internal", 49981),
        )

    fake_client.close.assert_called_once()
    captured = capsys.readouterr()
    assert "BRIDGE_UNREACHABLE" in captured.err
