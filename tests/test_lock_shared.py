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

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import lock_shared
from dotfiles_setup.devcontainer_names import resolve_names
from dotfiles_setup.lock_integrity import tool_platforms
from dotfiles_setup.main import setup_parser
from dotfiles_setup.platform_target import mise_lock_platforms

REPO_ROOT = Path(__file__).parent.parent
_REAL_WRITER_MATCHES_IMAGE = lock_shared.writer_matches_image


@pytest.fixture(autouse=True)
def _known_compatible_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Existing command-shape tests fake the external version preflight."""
    monkeypatch.setattr(lock_shared, "writer_matches_image", lambda *_a, **_k: True)


def _completed(rc: int, stdout: str = "") -> subprocess.CompletedProcess[str]:
    """A `text=True` `CompletedProcess` stand-in — real calls capture str, not bytes."""
    return subprocess.CompletedProcess([], rc, stdout, "")


def _workspace_mise_toml() -> str:
    """The `/workspaces/<basename>/mise.toml` string the routed argv must carry.

    Derived independently via `resolve_names` (the same PUBLIC primitive
    `devcontainer_exec_prefix`'s id-labels use) rather than calling the
    private helper under test, so the expectation tracks this repo's real
    basename without hardcoding "dotfiles" and without being tautological.
    """
    return f"/workspaces/{resolve_names(workspace=REPO_ROOT).basename}/mise.toml"


@pytest.mark.parametrize(
    ("reported", "expected"),
    [("2026.10.7 linux-x64", "match"), ("2026.9.8 linux-x64", "reject")],
)
def test_writer_version_probe_blocks_old_guest_before_a_lock_call(
    monkeypatch: pytest.MonkeyPatch, reported: str, expected: str
) -> None:
    monkeypatch.setattr(lock_shared, "writer_matches_image", _REAL_WRITER_MATCHES_IMAGE)
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return _completed(0, reported)

    monkeypatch.setattr(lock_shared.subprocess, "run", fake_run)
    assert lock_shared.writer_matches_image(REPO_ROOT, route=True) is (
        expected == "match"
    )
    assert len(calls) == 1
    assert calls[0][-2:] == ["mise", "--version"]


def test_old_guest_is_rejected_before_shared_lock_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lock_shared, "writer_matches_image", _REAL_WRITER_MATCHES_IMAGE)
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (False, "Darwin"))
    calls: list[list[str]] = []

    def fake_run(
        argv: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return _completed(0, "2026.9.8 linux-x64")

    monkeypatch.setattr(lock_shared.subprocess, "run", fake_run)
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"]) == 1
    assert len(calls) == 1
    assert calls[0][-2:] == ["mise", "--version"]


def test_shared_lock_stops_before_coverage_when_native_graph_is_damaged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (True, "Linux/x86_64"))
    monkeypatch.setattr(lock_shared.subprocess, "run", lambda *_a, **_k: _completed(0))

    def reject_graph(*_args: object, **_kwargs: object) -> None:
        msg = "bad graph"
        raise ValueError(msg)

    monkeypatch.setattr(
        lock_shared,
        "verify_lock_sidecars",
        reject_graph,
    )
    checked: list[str] = []
    monkeypatch.setattr(
        lock_shared,
        "lock_integrity_main",
        lambda _root: (checked.append("ran"), 0)[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"], container=False) == 1
    assert not checked


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


def test_a_root_only_tool_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Round 2's HIGH 2: a real declared tool this task still must not accept.

    `aws-cli` is declared in root `mise.toml`, not the shared fragment — the
    original validation reused `declared_host_tools` (the UNION of both host
    files) and would have accepted it, then locked it into the WRONG file
    (this module never touches the root `mise.lock`). Spawning is faked so a
    regression here reads as "ran anyway" rather than a coincidental pass.
    """
    called: list[str] = []
    monkeypatch.setattr(
        lock_shared.subprocess,
        "run",
        lambda *_a, **_k: (called.append("ran"), _completed(0))[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["aws-cli"], container=False) == 1
    assert not called, "a root-only tool must never reach a subprocess call"


def test_an_os_gated_root_only_tool_is_rejected() -> None:
    """A root-only, os-gated tool.

    `conda:ffmpeg` (os=["macos"]) is root-only and would be a guaranteed
    no-op if routed to linux — rejected for the same reason `aws-cli` is,
    before routing is ever considered.
    """
    assert (
        lock_shared.lock_shared_main(REPO_ROOT, ["conda:ffmpeg"], container=False) == 1
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
    """The routed command is `mise lock <tool>` itself — never this CLI re-invoked.

    Round 1 routed by re-invoking `dotfiles-setup lock-shared` inside the
    container via `image_lock.container_command`'s `mise exec --` wrapper.
    That wrapper resolves mise's ENTIRE declared toolset before running
    anything, and died on a live integration check
    (`.devcontainer/mise-system.toml`'s `github_attestations = false` against
    a host lock entry's `provenance = "github-attestations"`). This pins the
    fix: the routed argv is a direct `mise lock <tool>`, with `--remote-env`
    ahead of it — no `dotfiles-setup`, no `mise exec --`, no `--no-container`
    re-entry flag, because there is no more recursion to terminate.
    """
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (False, "Darwin"))
    seen: list[list[str]] = []
    monkeypatch.setattr(
        lock_shared.subprocess,
        "run",
        lambda argv, **_k: (seen.append(argv), _completed(0))[1],
    )
    monkeypatch.setattr(lock_shared, "lock_integrity_main", lambda _root: 0)
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"]) == 0
    assert seen
    argv = seen[0]
    assert argv[0] == "devcontainer"
    assert "dotfiles-setup" not in argv
    assert "lock-shared" not in argv
    assert "image-lock" not in argv
    assert "--no-container" not in argv
    assert "--remote-env" in argv
    # `uv` is exact-pinned in the shared fragment, so it is locked as
    # `uv@<pin>` (mise 2026.9.8 packslip quirk, #1398).
    assert argv[-3:-1] == ["mise", "lock"]
    assert argv[-1].startswith("uv@")

    # Round 2's HIGH 1: the value must un-ignore ONLY the shared fragment —
    # a wholesale clear (round 1's `MISE_IGNORED_CONFIG_PATHS=`) re-admits the
    # workspace's own root `mise.toml`, which — with `auto_install = true` set
    # in the container's user overlay — resolves and attempts to install all
    # 46 host tools before `mise lock` runs anything.
    env_value = argv[argv.index("--remote-env") + 1]
    expected = f"{lock_shared.IGNORED_CONFIG_PATHS_VAR}={_workspace_mise_toml()}"
    assert env_value == expected
    assert env_value != f"{lock_shared.IGNORED_CONFIG_PATHS_VAR}=", (
        "a wholesale clear re-admits the workspace root mise.toml too"
    )


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
    monkeypatch.setattr(lock_shared, "lock_integrity_main", lambda _root: 0)
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"], container=True) == 0
    assert seen[0][0] == "devcontainer"


def test_container_success_verifies_coverage_host_side_after_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Coverage is checked on THIS host after `devcontainer exec` returns.

    Round 1 verified coverage via recursion — the routed call re-entered this
    same function inside the container, where it ran the local branch's
    `lock_integrity_main`. There is no more recursion, so this pins the
    replacement: the outer call itself invokes `lock_integrity_main(repo_root)`
    once the routed `mise lock` has returned successfully.
    """
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (False, "Darwin"))
    monkeypatch.setattr(lock_shared.subprocess, "run", lambda *_a, **_k: _completed(0))
    verified: list[Path] = []
    monkeypatch.setattr(
        lock_shared,
        "lock_integrity_main",
        lambda root: (verified.append(root), 0)[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"]) == 0
    assert verified == [REPO_ROOT]


def test_container_failure_short_circuits_before_verifying_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed routed `mise lock` must not reach the coverage check at all."""
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (False, "Darwin"))
    monkeypatch.setattr(lock_shared.subprocess, "run", lambda *_a, **_k: _completed(2))
    verified: list[str] = []
    monkeypatch.setattr(
        lock_shared,
        "lock_integrity_main",
        lambda _root: (verified.append("checked"), 0)[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"]) == 2
    assert not verified, "coverage must not be asserted after a failed routed lock"


# --------------------------------------------------------------------------- #
# Local execution (already on a capable host, or the routed inner call)
# --------------------------------------------------------------------------- #


def test_a_capable_host_locks_each_tool_then_verifies_coverage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (True, "Linux/x86_64"))
    calls: list[tuple[list[str], Path | None, dict[str, str] | None]] = []

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        cwd = kwargs.get("cwd")
        env = kwargs.get("env")
        assert cwd is None or isinstance(cwd, Path)
        assert env is None or isinstance(env, dict)
        calls.append((argv, cwd, env))
        return _completed(0)

    monkeypatch.setattr(lock_shared.subprocess, "run", fake_run)
    verified: list[Path] = []
    monkeypatch.setattr(
        lock_shared,
        "lock_integrity_main",
        lambda root: (verified.append(root), 0)[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"], container=False) == 0
    assert len(calls) == 1
    argv, cwd, env = calls[0]
    assert argv[:2] == ["mise", "lock"]
    assert argv[2].startswith("uv@")
    assert len(argv) == 3
    assert cwd == REPO_ROOT
    assert verified == [REPO_ROOT]

    # Round 2's HIGH 3: the local call must pin the var explicitly too,
    # never inherit whatever `os.environ` happens to hold — run from INSIDE
    # the devcontainer directly (which the refusal message itself
    # recommends), the ambient value hides the shared fragment and `mise
    # lock` silently finds nothing.
    assert env is not None
    assert env[lock_shared.IGNORED_CONFIG_PATHS_VAR] == str(REPO_ROOT / "mise.toml")


def test_local_env_override_leaves_the_rest_of_os_environ_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The override must ADD to the ambient environment, not replace it."""
    monkeypatch.setenv("SOME_UNRELATED_VAR", "kept")
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (True, "Linux/x86_64"))
    seen_env: list[dict[str, str] | None] = []
    monkeypatch.setattr(
        lock_shared.subprocess,
        "run",
        lambda _argv, **k: (seen_env.append(k.get("env")), _completed(0))[1],
    )
    monkeypatch.setattr(lock_shared, "lock_integrity_main", lambda _root: 0)
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"], container=False) == 0
    env = seen_env[0]
    assert env is not None
    assert env["SOME_UNRELATED_VAR"] == "kept"
    assert env[lock_shared.IGNORED_CONFIG_PATHS_VAR] == str(REPO_ROOT / "mise.toml")


def test_routed_command_passes_no_python_level_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The routed form controls the var via `--remote-env`, not `env=`.

    `--remote-env` sets the value INSIDE the container's shell; a
    python-level `env=` override on the `devcontainer` CLI process itself
    would do nothing for the remote command and would be dead weight.
    """
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (False, "Darwin"))
    seen: list[tuple[list[str], object]] = []
    monkeypatch.setattr(
        lock_shared.subprocess,
        "run",
        lambda argv, **k: (seen.append((argv, k.get("env"))), _completed(0))[1],
    )
    monkeypatch.setattr(lock_shared, "lock_integrity_main", lambda _root: 0)
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"]) == 0
    argv, env = seen[0]
    assert argv[0] == "devcontainer"
    assert env is None


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
# Round 2's HIGH 3 — rc=0 is not "written"; mise's own no-tools signal must
# be treated as a hard failure, local or routed.
# --------------------------------------------------------------------------- #


#: mise's own message when a `mise lock <tool>` call finds nothing to lock —
#: the literal string, independent of `lock_shared._NO_TOOLS_MARKER`, so this
#: is an independent expectation rather than the test re-reading the
#: constant the code under test defines.
_MISE_NO_TOOLS_LINE = "No tools configured to lock"


def test_a_local_silent_no_op_fails_even_at_rc_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact round-2 failure mode.

    Run locally inside the devcontainer, ambient `MISE_IGNORED_CONFIG_PATHS`
    still hides the shared fragment, `mise lock` finds nothing, prints
    mise's own no-op line, and exits 0. Coverage-held (nothing changed) must
    not be reported as success.
    """
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (True, "Linux/x86_64"))
    monkeypatch.setattr(
        lock_shared.subprocess,
        "run",
        lambda *_a, **_k: _completed(0, stdout=f"{_MISE_NO_TOOLS_LINE}\n"),
    )
    verified: list[str] = []
    monkeypatch.setattr(
        lock_shared,
        "lock_integrity_main",
        lambda _root: (verified.append("checked"), 0)[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"], container=False) == 1
    assert not verified, "a detected no-op must short-circuit before coverage too"


def test_a_routed_silent_no_op_fails_even_at_rc_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same signal, routed.

    Guards against a FUTURE cause of the same no-op class, not just the
    specific env-inheritance bug round 2 fixed.
    """
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (False, "Darwin"))
    monkeypatch.setattr(
        lock_shared.subprocess,
        "run",
        lambda *_a, **_k: _completed(0, stdout=f"{_MISE_NO_TOOLS_LINE}\n"),
    )
    verified: list[str] = []
    monkeypatch.setattr(
        lock_shared,
        "lock_integrity_main",
        lambda _root: (verified.append("checked"), 0)[1],
    )
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"]) == 1
    assert not verified


def test_ordinary_output_does_not_trigger_the_no_op_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Control arm: normal `mise lock` chatter must not false-positive."""
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (True, "Linux/x86_64"))
    monkeypatch.setattr(
        lock_shared.subprocess,
        "run",
        lambda *_a, **_k: _completed(0, stdout="uv: updating lockfile...\n"),
    )
    monkeypatch.setattr(lock_shared, "lock_integrity_main", lambda _root: 0)
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"], container=False) == 0


# --------------------------------------------------------------------------- #
# The wiring the fixtures cannot see
# --------------------------------------------------------------------------- #


def test_lock_shared_is_registered_on_the_parser() -> None:
    """`main.setup_parser` really carries the subcommand.

    Deleting the `subparsers.add_parser("lock-shared", …)` block leaves the
    dispatch-dict entry and every `per_path_tokens` string intact, so the
    contract could stay green while the CLI subcommand no longer exists.
    This is the arm that fails on that deletion — argparse exits 2 on an
    unknown choice.
    """
    args = setup_parser().parse_args(["lock-shared", "uv"])
    assert args.command == "lock-shared"
    assert args.tools == ["uv"]
    assert args.container is None


def test_the_mise_task_calls_the_cli_rather_than_reimplementing_the_recipe() -> None:
    """The recipe living in TWO places is the defect #650 was filed about.

    Same shape here would be just as costly for `lock-image`.
    """
    mise_toml = (REPO_ROOT / "mise.toml").read_text()
    assert "[tasks.lock-shared]" in mise_toml
    assert "dotfiles-setup lock-shared" in mise_toml


def _routed_argv(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The routed argv for one `lock-shared` run, with subprocess stubbed."""
    monkeypatch.setattr(lock_shared, "host_can_lock", lambda: (False, "Darwin"))
    seen: list[list[str]] = []
    monkeypatch.setattr(
        lock_shared.subprocess,
        "run",
        lambda argv, **_k: (seen.append(argv), _completed(0))[1],
    )
    monkeypatch.setattr(lock_shared, "lock_integrity_main", lambda _root: 0)
    assert lock_shared.lock_shared_main(REPO_ROOT, ["uv"]) == 0
    assert seen
    return seen[0]


def _remote_env(argv: list[str], var: str) -> str | None:
    """The `--remote-env` value for one variable, or None if unset."""
    for index, item in enumerate(argv):
        if item == "--remote-env" and argv[index + 1].startswith(f"{var}="):
            return argv[index + 1].removeprefix(f"{var}=")
    return None


def test_routed_command_pins_the_full_shared_platform_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Routing must not inherit the IMAGE's `lockfile_platforms`.

    `.devcontainer/mise-system.toml` scopes the IMAGE locks to the published
    arches (`["linux-x64", "linux-arm64"]`, #698) — correct there, and
    catastrophic here: applied to `.config/mise/mise.lock` it truncates every
    re-locked tool from 11 platforms to 2, dropping the macOS and windows
    entries the host installs from. Measured 2026-08-27: bun, hk, typos, uv
    and yq all lost the same 9 platforms in one run.

    The expected value comes from the committed lockfile, not from a literal
    list recomputed the way the code builds it — an independent source of
    truth per tests/AGENTS.md.
    """
    argv = _routed_argv(monkeypatch)
    pinned = _remote_env(argv, lock_shared.LOCKFILE_PLATFORMS_VAR)
    assert pinned is not None, (
        "the routed argv sets no MISE_LOCKFILE_PLATFORMS, so the container's "
        "2-platform image setting applies and truncates the shared lockfile"
    )

    committed = (REPO_ROOT / lock_shared.SHARED_LOCK).read_text(encoding="utf-8")
    expected = set()
    for covered in tool_platforms(committed).values():
        expected |= covered
    assert set(pinned.split(",")) == expected

    # The FAIL direction: whatever the set is, it must not have collapsed to
    # the image's pair. Without this the assert above would still pass if the
    # committed lockfile itself were ever truncated to those two.
    assert set(pinned.split(",")) != {"linux-x64", "linux-arm64"}
    assert len(pinned.split(",")) > len(mise_lock_platforms())


def test_routed_command_re_enables_attestation_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Routing must not inherit the IMAGE's `github_attestations = false`.

    It is disabled for image builds because a token is not reliably available
    in buildkit secret mounts. Inherited here, the re-locked entry carries no
    provenance and mise refuses to replace an attested entry with an
    unattested one — reported as "could indicate a supply chain attack" on a
    release that IS properly attested. Measured against pixi 0.77.1, which
    carries one attestation per asset exactly as 0.76.2 does.

    Isolating arm (measured): pinning the full platform set alone still fails
    pixi with rc=1, so this override is independently load-bearing and cannot
    be folded into the platform fix.
    """
    argv = _routed_argv(monkeypatch)
    assert _remote_env(argv, lock_shared.GITHUB_ATTESTATIONS_VAR) == "true"


def test_shared_lock_platforms_refuses_an_empty_lockfile(tmp_path: Path) -> None:
    """An empty platform set must raise, never pass through as ``VAR=``.

    `MISE_LOCKFILE_PLATFORMS=` is not "no opinion" — it hands mise back the
    container's own narrow default, which is the exact truncation this
    closes. Failing loud is the only safe answer.
    """
    (tmp_path / ".config" / "mise").mkdir(parents=True)
    (tmp_path / lock_shared.SHARED_LOCK).write_text("# no tools\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no platform entries"):
        lock_shared.shared_lock_platforms(tmp_path)


def test_shared_lock_platforms_reads_the_real_committed_lockfile() -> None:
    """Control arm for the test above: the real file yields a non-empty set.

    Without this, the raise-on-empty test could pass while the reader was
    broken for every input.
    """
    platforms = lock_shared.shared_lock_platforms(REPO_ROOT)
    assert "linux-x64" in platforms
    assert len(platforms) > len(mise_lock_platforms())


# --- mise 2026.9.8 packslip quirk (#1398) ------------------------------------
#
# The former image/CI mise pin (2026.9.8) runs `mise lock <bare-name>` for a
# packslip-backend tool as a silent no-op (rc 0, no entry). Measured in the
# devcontainer 2026-09-27 on `hk = "2.3.0"`: bare `hk` -> 0 lines, `hk@2.3.0`
# -> the entry with its platform. So an exact pin must be named with its version.


def _shared_fragment(tmp_path: Path, body: str) -> Path:
    fragment = tmp_path / ".config" / "mise" / "conf.d" / "shared.toml"
    fragment.parent.mkdir(parents=True)
    fragment.write_text(body)
    return tmp_path


def test_an_exact_pin_is_locked_with_its_version(tmp_path: Path) -> None:
    root = _shared_fragment(tmp_path, '[tools]\nhk = "2.3.0"\n')
    assert lock_shared.lock_target(root, "hk") == "hk@2.3.0"


def test_latest_and_table_pins_keep_the_bare_name(tmp_path: Path) -> None:
    """CONTROL ARMS: no exact version to name, so no `@` spec is invented."""
    root = _shared_fragment(
        tmp_path,
        '[tools]\nbiome = "latest"\n"aqua:x/y" = { version = "1.0.0" }\n',
    )
    assert lock_shared.lock_target(root, "biome") == "biome"
    assert lock_shared.lock_target(root, "aqua:x/y") == "aqua:x/y"


def test_the_live_shared_pin_for_hk_is_versioned() -> None:
    """The real fragment: the tool that shipped an empty entry is now named."""
    assert lock_shared.lock_target(REPO_ROOT, "hk").startswith("hk@")
