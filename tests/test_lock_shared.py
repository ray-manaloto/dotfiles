# Copyright (c) 2026 Raymond Manaloto
"""Tests for the shared-lockfile task (dotfiles_setup.lock_shared).

`.config/mise/mise.lock` needed its own regen path because neither existing
sibling covers it: `lock`/`lock-tools` (dotfiles_setup.lock_integrity) never
leave this host, which is fine for the root lock but wrong here — mise
resolves a DIFFERENT release asset than macOS for at least one shared tool,
and the choice is made by the RESOLVING host, not by the platform being
locked for (measured 2026-08-27: uv wrote the gnu tarball for linux-x64 on
macOS; a linux host resolves musl for that same entry). `lock-image`
(dotfiles_setup.image_lock) does not cover it either — it only ever touches
the two `.devcontainer/*.lock` files.

Nothing here reaches the network, spawns mise, or spawns devcontainer exec:
the subprocess runner, the host-capability check, and the coverage verifier
are all faked, the same way `tests/test_image_lock.py` fakes its sibling.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import lock_shared

if TYPE_CHECKING:
    import pytest

REPO_ROOT = Path(__file__).parent.parent


def _completed(rc: int) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess([], rc, b"", b"")


# --------------------------------------------------------------------------- #
# Named-tools-only validation (#370's model) — before any routing decision
# --------------------------------------------------------------------------- #


def test_bare_tools_is_refused() -> None:
    assert lock_shared.lock_shared_main(REPO_ROOT, [], container=False) == 1


def test_undeclared_tool_is_rejected() -> None:
    assert (
        lock_shared.lock_shared_main(
            REPO_ROOT, ["definitely:not/a-tool"], container=False
        )
        == 1
    )


def test_short_name_for_backend_qualified_key_is_rejected() -> None:
    """A bare short name must not silently pass validation and do nothing.

    `betterleaks` is declared as `aqua:betterleaks/betterleaks`.
    """
    assert (
        lock_shared.lock_shared_main(REPO_ROOT, ["betterleaks"], container=False) == 1
    )


def test_validation_runs_before_any_subprocess_is_spawned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bad tool name must fail fast, not after a devcontainer round-trip."""
    called: list[str] = []
    monkeypatch.setattr(
        lock_shared.subprocess,
        "run",
        lambda *_a, **_k: (called.append("ran"), _completed(0))[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["not/a/tool"]) == 1
    assert not called


# --------------------------------------------------------------------------- #
# Container routing (image_lock's pattern, generalised)
# --------------------------------------------------------------------------- #


def test_an_incapable_host_routes_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (False, "Darwin"))
    seen: list[list[str]] = []
    monkeypatch.setattr(
        lock_shared.subprocess,
        "run",
        lambda argv, **_k: (seen.append(argv), _completed(0))[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"]) == 0
    assert seen
    argv = seen[0]
    assert argv[0] == "devcontainer"
    assert "lock-shared" in argv
    assert "image-lock" not in argv
    assert "--remote-env" in argv
    assert f"{lock_shared.IGNORED_CONFIG_PATHS_VAR}=" in argv
    assert argv[-1] == "uv"


def test_an_incapable_host_with_no_container_refuses_instead_of_guessing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The refusal is the feature.

    Locking here anyway writes a lock that LOOKS fine and only fails on the
    platform it was written for.
    """
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (False, "Darwin/arm64"))
    called: list[str] = []
    monkeypatch.setattr(
        lock_shared.subprocess,
        "run",
        lambda *_a, **_k: (called.append("ran"), _completed(0))[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"], container=False) == 1
    assert not called, "nothing may be executed once the host is refused"


def test_container_true_routes_even_from_a_capable_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (True, "Linux/x86_64"))
    seen: list[list[str]] = []
    monkeypatch.setattr(
        lock_shared.subprocess,
        "run",
        lambda argv, **_k: (seen.append(argv), _completed(0))[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"], container=True) == 0
    assert seen[0][0] == "devcontainer"


# --------------------------------------------------------------------------- #
# Local execution (already on a capable host, or the routed inner call)
# --------------------------------------------------------------------------- #


def test_a_capable_host_locks_each_tool_then_verifies_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (True, "Linux/x86_64"))
    calls: list[tuple[list[str], object]] = []

    def fake_run(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        calls.append((argv, kwargs.get("cwd")))
        return _completed(0)

    monkeypatch.setattr(lock_shared.subprocess, "run", fake_run)
    verified: list[Path] = []
    monkeypatch.setattr(
        lock_shared,
        "lock_integrity_main",
        lambda root: (verified.append(root), 0)[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"], container=False) == 0
    assert calls == [(["mise", "lock", "uv"], REPO_ROOT)]
    assert verified == [REPO_ROOT]


def test_a_failed_mise_lock_call_short_circuits_before_verifying_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (True, "Linux/x86_64"))
    monkeypatch.setattr(lock_shared.subprocess, "run", lambda *_a, **_k: _completed(3))
    verified: list[str] = []
    monkeypatch.setattr(
        lock_shared,
        "lock_integrity_main",
        lambda _root: (verified.append("checked"), 0)[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"], container=False) == 3
    assert not verified, "coverage must not be asserted after a failed lock"


def test_coverage_verification_is_delegated_not_reimplemented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The regression predicate lives in ONE place (#648).

    A second coverage check written here would be exactly the duplication
    that let the image-lock version go stale. This asserts the return value
    is whatever the delegate reports, not a locally-computed verdict.
    """
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (True, "Linux/x86_64"))
    monkeypatch.setattr(lock_shared.subprocess, "run", lambda *_a, **_k: _completed(0))
    monkeypatch.setattr(lock_shared, "lock_integrity_main", lambda _root: 1)
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"], container=False) == 1


# --------------------------------------------------------------------------- #
# The wiring the fixtures cannot see
# --------------------------------------------------------------------------- #


def test_the_mise_task_calls_the_cli_rather_than_reimplementing_the_recipe() -> None:
    """The recipe living in TWO places is the defect #650 was filed about.

    Same shape here would be just as costly for `lock-image`.
    """
    mise_toml = (REPO_ROOT / "mise.toml").read_text()
    assert "[tasks.lock-shared]" in mise_toml
    assert "dotfiles-setup lock-shared" in mise_toml
