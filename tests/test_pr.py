"""Tests for the ship/land PR workflow (dotfiles_setup.pr)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from typing import TYPE_CHECKING

import pytest
from dotfiles_setup import pr

if TYPE_CHECKING:
    from dotfiles_setup.sync import SyncOptions

_WORKSPACE = Path("/workspaces-host/dotfiles")


def _cp(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[], returncode=returncode, stdout=stdout, stderr=""
    )


# ------------------------------------------------------- surface detection


@pytest.mark.parametrize(
    "path",
    [
        ".devcontainer/Dockerfile",
        ".devcontainer/scripts/on-create.sh",
        "docker-bake.hcl",
        "scripts/devcontainer-smoke.sh",
        "python/src/dotfiles_setup/sync.py",
        "python/src/dotfiles_setup/container.py",
        "python/verification/suites.toml",
    ],
)
def test_surface_paths_detected(path: str) -> None:
    assert pr.touches_surface([path])


@pytest.mark.parametrize(
    "path",
    ["AGENTS.md", "hk.pkl", "python/src/dotfiles_setup/audit.py", "tests/test_pr.py"],
)
def test_non_surface_paths_not_detected(path: str) -> None:
    assert not pr.touches_surface([path])


# ------------------------------------------------------------ gate matrix


def test_gate_matrix_always_has_core_gates() -> None:
    names = [g.name for g in pr.gate_matrix(["README.md"])]
    assert names[:4] == ["lint", "pytest", "verify-contracts", "hook-selfcheck"]
    assert "sync-full" not in names
    assert "pin-actions" not in names


def test_hook_selfcheck_is_an_unconditional_gate() -> None:
    # The host-side hook validation runs on EVERY ship, like lint/pytest —
    # a hook regression can arrive from any diff, not just a hook-file change.
    for paths in (["README.md"], [".github/workflows/ci.yml"], ["python/x.py"]):
        gate = next(g for g in pr.gate_matrix(paths) if g.name == "hook-selfcheck")
        assert gate.cmd == (
            "uv",
            "run",
            "--project",
            "python",
            "dotfiles-setup",
            "hook",
            "selfcheck",
        )


def test_gate_matrix_gha_adds_pin_actions() -> None:
    names = [g.name for g in pr.gate_matrix([".github/workflows/ci.yml"])]
    assert "pin-actions" in names


def test_gate_matrix_docs_adds_lint_docs() -> None:
    names = [g.name for g in pr.gate_matrix([".claude/rules/do-not.md"])]
    assert "lint-docs" in names
    names = [g.name for g in pr.gate_matrix(["tests/AGENTS.md"])]
    assert "lint-docs" in names


def test_gate_matrix_bootstrap_packages_add_apt_pin_gate() -> None:
    # The pin declarations, and the Dockerfile the pins resolve AGAINST (its
    # ARG BASE_IMAGE / signing key) — a base bump can invalidate every pin
    # without touching a pin line, so both are probe inputs (#299).
    names = [g.name for g in pr.gate_matrix([".devcontainer/mise-system.toml"])]
    assert "verify-apt-pins" in names
    names = [g.name for g in pr.gate_matrix([".devcontainer/Dockerfile"])]
    assert "verify-apt-pins" in names


def test_gate_matrix_unrelated_surface_omits_apt_pin_gate() -> None:
    # Control arm: the gate costs a ~60s container probe, so an unrelated
    # change must not pay it. Without this, the test above is satisfied by a
    # gate matrix that runs verify-apt-pins unconditionally.
    names = [g.name for g in pr.gate_matrix(["README.md"])]
    assert "verify-apt-pins" not in names
    names = [g.name for g in pr.gate_matrix([".github/workflows/ci.yml"])]
    assert "verify-apt-pins" not in names


def test_gate_matrix_apt_pin_gate_survives_the_base_input_deferral() -> None:
    """The pin gate must fire even though its paths ARE base inputs.

    Base-input changes make ship defer container validation to CI, so the
    sync-full gate is deliberately absent here. That deferral is exactly why
    the pin probe earns its place: it is the only local check left that a pin
    still resolves, and it fails in ~60s instead of after a ~37min CI base
    build. A future refactor that folds this gate under the same
    `not changes_base_image_inputs(...)` condition as sync-full would silently
    disable it for every change that can break a pin.
    """
    names = [g.name for g in pr.gate_matrix([".devcontainer/mise-system.toml"])]
    assert pr.changes_base_image_inputs([".devcontainer/mise-system.toml"])
    assert "sync-full" not in names
    assert "verify-apt-pins" in names


def test_gate_matrix_non_base_surface_adds_full_sync_last() -> None:
    # A surface change that does NOT rebuild the base (validation tooling /
    # overlay) still runs the local container gate last.
    names = [g.name for g in pr.gate_matrix(["scripts/devcontainer-smoke.sh"])]
    assert names[-1] == "sync-full"
    names = [g.name for g in pr.gate_matrix(["python/src/dotfiles_setup/sync.py"])]
    assert names[-1] == "sync-full"


@pytest.mark.parametrize(
    "path",
    [
        ".devcontainer/Dockerfile",
        ".devcontainer/mise-system.toml",
        ".devcontainer/mise-system.lock",
        ".devcontainer/mise-runtime.toml",
        ".devcontainer/mise-runtime.lock",
        ".config/mise/conf.d/shared.toml",
        "hk-common.pkl",
        "hk-image.pkl",
        "docker-bake.hcl",
    ],
)
def test_base_input_changes_detected(path: str) -> None:
    assert pr.changes_base_image_inputs([path])


@pytest.mark.parametrize(
    "path",
    [
        "scripts/devcontainer-smoke.sh",
        "python/src/dotfiles_setup/sync.py",
        "python/src/dotfiles_setup/pr.py",
        "mise.toml",
        ".devcontainer/devcontainer.json",
        "README.md",
    ],
)
def test_non_base_paths_not_base_inputs(path: str) -> None:
    assert not pr.changes_base_image_inputs([path])


def test_gate_matrix_base_input_defers_full_sync() -> None:
    # A base-image build input can only be validated by the PR's own CI
    # (the local :dev base is built from the merge-base), so the local
    # container gate is DEFERRED — not appended — for these changes.
    for path in (".devcontainer/Dockerfile", ".config/mise/conf.d/shared.toml"):
        names = [g.name for g in pr.gate_matrix([path])]
        assert "sync-full" not in names
        assert names[:3] == ["lint", "pytest", "verify-contracts"]


def test_gate_matrix_base_input_wins_over_non_base_surface() -> None:
    # When a diff touches BOTH a base input and a non-base surface path,
    # the base-input deferral wins (the container still can't converge).
    names = [
        g.name
        for g in pr.gate_matrix(
            [".config/mise/conf.d/shared.toml", "python/src/dotfiles_setup/sync.py"]
        )
    ]
    assert "sync-full" not in names


def test_run_gates_stops_at_first_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[str] = []

    def fake_stream(cmd: list[str], **_k: object) -> int:
        ran.append(cmd[-1])
        return 1 if len(ran) == 2 else 0

    monkeypatch.setattr(pr, "_stream", fake_stream)
    gates = [
        pr.Gate("a", ("x", "a")),
        pr.Gate("b", ("x", "b")),
        pr.Gate("c", ("x", "c")),
    ]
    assert pr.run_gates(_WORKSPACE, gates) is False
    assert ran == ["a", "b"]


# ------------------------------------------------------ check verification


def test_pr_checks_green_all_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    checks = [
        {"name": "lint", "bucket": "pass"},
        {"name": "build", "bucket": "skipping"},
    ]
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(checks)))
    ok, detail = pr.pr_checks_green(1)
    assert ok
    assert "2 checks" in detail


@pytest.mark.parametrize("bucket", ["fail", "pending", "cancel"])
def test_pr_checks_not_green_on_bad_bucket(
    monkeypatch: pytest.MonkeyPatch, bucket: str
) -> None:
    checks = [{"name": "lint", "bucket": "pass"}, {"name": "x", "bucket": bucket}]
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(checks)))
    ok, detail = pr.pr_checks_green(1)
    assert not ok
    assert f"x={bucket}" in detail


# ------------------------------------------------------------------- ship


def test_ship_refuses_main(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pr, "_current_branch", lambda _w: "main")
    assert pr.ship_main(_WORKSPACE) == 1


def test_ship_refuses_dirty_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pr, "_current_branch", lambda _w: "feat/x")
    monkeypatch.setattr(pr, "_working_tree_clean", lambda _w: False)
    assert pr.ship_main(_WORKSPACE) == 1


def test_ship_gate_failure_stops_before_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pr, "_current_branch", lambda _w: "feat/x")
    monkeypatch.setattr(pr, "_working_tree_clean", lambda _w: True)
    monkeypatch.setattr(pr, "changed_paths_vs_main", lambda _w: ["a.py"])
    monkeypatch.setattr(pr, "run_gates", lambda *_a: False)

    def _boom(*_a: object, **_k: object) -> int:
        msg = "must not push after a failed gate"
        raise AssertionError(msg)

    monkeypatch.setattr(pr, "_stream", _boom)
    assert pr.ship_main(_WORKSPACE) == 1


# ------------------------------------------------------------------- land


def testenable_auto_merge_builds_pinned_squash_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    head = "b" * 40
    seen: list[list[str]] = []

    def fake_run(cmd: list[str], **_k: object) -> subprocess.CompletedProcess[str]:
        seen.append(cmd)
        return _cp()

    monkeypatch.setattr(pr, "_run", fake_run)
    assert pr.enable_auto_merge(_WORKSPACE, 7, head) is True
    cmd = seen[-1]
    assert cmd[:3] == ["gh", "pr", "merge"]
    assert "--auto" in cmd
    assert "--squash" in cmd
    assert "--match-head-commit" in cmd
    assert head in cmd


def testenable_auto_merge_retries_transient_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter([_cp("422 Failed enabling auto-merge", returncode=1), _cp()])
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: next(responses))
    monkeypatch.setattr(pr.time, "sleep", lambda _s: None)
    assert pr.enable_auto_merge(_WORKSPACE, 7, "a" * 40) is True


def testenable_auto_merge_fails_after_all_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp("422", returncode=1))
    monkeypatch.setattr(pr.time, "sleep", lambda _s: None)
    assert pr.enable_auto_merge(_WORKSPACE, 7, "a" * 40) is False


def test_ship_enables_auto_merge_and_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ship opens the PR, enables native auto-merge (pinned to HEAD), returns 0.

    GitHub owns the wait — ship never watches the build.
    """
    enabled: dict[str, object] = {}
    monkeypatch.setattr(pr, "_current_branch", lambda _w: "feat/x")
    monkeypatch.setattr(pr, "_working_tree_clean", lambda _w: True)
    monkeypatch.setattr(pr, "changed_paths_vs_main", lambda _w: ["README.md"])
    monkeypatch.setattr(pr, "run_gates", lambda *_a: True)
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)  # git push
    monkeypatch.setattr(pr, "_open_or_update_pr", lambda *_a, **_k: 42)
    monkeypatch.setattr(pr, "_await_checks_registered", lambda _n: True)
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp("abc123\n"))  # rev-parse

    def fake_enable(_w: Path, n: int, head: str) -> bool:
        enabled["pr"] = n
        enabled["head"] = head
        return True

    monkeypatch.setattr(pr, "enable_auto_merge", fake_enable)
    assert pr.ship_main(_WORKSPACE) == 0
    assert enabled["pr"] == 42
    assert enabled["head"] == "abc123"


def test_ship_fails_if_auto_merge_enable_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pr, "_current_branch", lambda _w: "feat/x")
    monkeypatch.setattr(pr, "_working_tree_clean", lambda _w: True)
    monkeypatch.setattr(pr, "changed_paths_vs_main", lambda _w: ["README.md"])
    monkeypatch.setattr(pr, "run_gates", lambda *_a: True)
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr, "_open_or_update_pr", lambda *_a, **_k: 42)
    monkeypatch.setattr(pr, "_await_checks_registered", lambda _n: True)
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp("abc123\n"))
    monkeypatch.setattr(pr, "enable_auto_merge", lambda *_a: False)
    assert pr.ship_main(_WORKSPACE) == 1


def test_land_requires_merged(monkeypatch: pytest.MonkeyPatch) -> None:
    """A still-OPEN PR means auto-merge is pending ci-gate — land exits 1."""
    view = {"state": "OPEN", "baseRefName": "main"}
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    assert pr.land_main(_WORKSPACE, 7) == 1


def test_land_refuses_non_main_base(monkeypatch: pytest.MonkeyPatch) -> None:
    """Land only validates main-based PRs."""
    view = {"state": "MERGED", "baseRefName": "develop"}
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    assert pr.land_main(_WORKSPACE, 7) == 1


def test_land_merged_validates_and_syncs(monkeypatch: pytest.MonkeyPatch) -> None:
    view = {"state": "MERGED", "baseRefName": "main"}
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    monkeypatch.setattr(pr, "_pr_changed_paths", lambda _n: ["a.py"])
    monkeypatch.setattr(pr, "_merge_commit_oid", lambda _n: "c" * 40)
    monkeypatch.setattr(pr, "_main_run_conclusion", lambda _o, **_k: True)
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr, "sync_main", lambda *_a, **_k: 0)
    assert pr.land_main(_WORKSPACE, 7) == 0


def test_land_surface_pr_validates_full_tier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = {"state": "MERGED", "baseRefName": "main"}
    seen: dict[str, bool] = {}
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    monkeypatch.setattr(
        pr, "_pr_changed_paths", lambda _n: [".devcontainer/Dockerfile"]
    )
    monkeypatch.setattr(pr, "_merge_commit_oid", lambda _n: "e" * 40)
    monkeypatch.setattr(pr, "_main_run_conclusion", lambda _o, **_k: True)
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)

    def fake_sync(_w: Path, options: SyncOptions) -> int:
        seen["full"] = options.full
        return 0

    monkeypatch.setattr(pr, "sync_main", fake_sync)
    assert pr.land_main(_WORKSPACE, 7) == 0
    assert seen["full"] is True


def test_land_resume_is_accepted_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resume is accepted for compat — land is always the post-merge replay."""
    view = {"state": "MERGED", "baseRefName": "main"}
    monkeypatch.setattr(pr, "_run", lambda *_a, **_k: _cp(json.dumps(view)))
    monkeypatch.setattr(pr, "_pr_changed_paths", lambda _n: ["a.py"])
    monkeypatch.setattr(pr, "_merge_commit_oid", lambda _n: "c" * 40)
    monkeypatch.setattr(pr, "_main_run_conclusion", lambda _o, **_k: True)
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr, "sync_main", lambda *_a, **_k: 0)
    assert pr.land_main(_WORKSPACE, 7, resume=True) == 0


@pytest.mark.parametrize(
    "path",
    ["hk-common.pkl", "hk-image.pkl", ".config/mise/conf.d/shared.toml", "mise.toml"],
)
def test_surface_covers_image_copy_inputs(path: str) -> None:
    """Review finding [5]: image COPY inputs + task definitions are surface."""
    assert pr.touches_surface([path])


# ------------------------------------------- main-CI expectation (post #178)


def _ci_yml_push_paths() -> list[str]:
    """The on.push.paths entries as written in ci.yml (comments skipped)."""
    text = (
        Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"
    ).read_text()
    block = text.split("push:", 1)[1].split("paths:", 1)[1]
    entries: list[str] = []
    for line in block.splitlines()[1:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if not stripped.startswith("- "):
            break
        entries.append(stripped[2:].strip('"'))
    return entries


def _fnmatch_patterns_for(yaml_path: str) -> tuple[str, ...]:
    """The fnmatch mirror of one ci.yml glob (``x/**`` needs two patterns)."""
    if yaml_path.endswith("/**"):
        base = yaml_path.removesuffix("/**")
        return (f"{base}/*", f"{base}/**/*")
    return (yaml_path,)


def test_ci_push_paths_mirror_ci_yml() -> None:
    """CI_PUSH_PATHS must stay in lockstep with ci.yml on.push.paths.

    Land's "no main run expected" outcome (#178) is only correct while the
    mirrored constant matches the workflow — this test fails on drift in
    either direction.
    """
    entries = _ci_yml_push_paths()
    assert entries, "failed to parse ci.yml on.push.paths"
    expected: set[str] = set()
    for entry in entries:
        expected.update(_fnmatch_patterns_for(entry))
    assert set(pr.CI_PUSH_PATHS) == expected


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["mise.toml", "mise.lock", ".agnix.toml"], False),  # the #178 shape
        ([".config/mise/conf.d/shared.toml"], True),
        (["python/src/dotfiles_setup/pr.py"], True),
        (["home/dot_zshrc"], True),
        ([".devcontainer/mise-system.lock"], True),
        ([".claude/rules/do-not.md", "AGENTS.md"], False),
    ],
)
def test_expects_main_run(paths: list[str], *, expected: bool) -> None:
    assert pr.expects_main_run(paths) is expected


def _land_run_dispatch(view: dict[str, str], *, run_id: str = "") -> object:
    """Fake ``pr._run`` dispatching by gh subcommand for land_main flows."""

    def fake(cmd: list[str], **_k: object) -> subprocess.CompletedProcess[str]:
        if "run" in cmd and "list" in cmd:
            return _cp(f"{run_id}\n" if run_id else "")
        if "conclusion" in cmd:
            return _cp("success\n")
        if "mergeCommit" in cmd:
            return _cp(json.dumps({"mergeCommit": {"oid": "c" * 40}}))
        if "checks" in cmd:
            return _cp(json.dumps([{"name": "lint", "bucket": "pass"}]))
        return _cp(json.dumps(view))

    return fake


def test_land_passes_when_no_main_run_expected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """#178: a merge whose paths match no ci.yml push path needs no run."""
    view = {"state": "MERGED", "baseRefName": "main"}
    monkeypatch.setattr(pr, "_run", _land_run_dispatch(view))
    monkeypatch.setattr(
        pr, "_pr_changed_paths", lambda _n: ["mise.toml", ".agnix.toml"]
    )
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr, "sync_main", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr.time, "sleep", lambda _s: None)
    assert pr.land_main(_WORKSPACE, 7) == 0


def test_land_fails_when_expected_main_run_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ci.yml-push-path merge with no main run is a real failure."""
    view = {"state": "MERGED", "baseRefName": "main"}
    monkeypatch.setattr(pr, "_run", _land_run_dispatch(view))
    monkeypatch.setattr(
        pr, "_pr_changed_paths", lambda _n: [".config/mise/conf.d/shared.toml"]
    )
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr, "sync_main", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr.time, "sleep", lambda _s: None)
    assert pr.land_main(_WORKSPACE, 7) == 1


def test_land_watches_main_run_when_one_unexpectedly_appears(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Grace poll: a run appearing despite no expectation is still verified."""
    view = {"state": "MERGED", "baseRefName": "main"}
    monkeypatch.setattr(pr, "_run", _land_run_dispatch(view, run_id="999"))
    monkeypatch.setattr(pr, "_pr_changed_paths", lambda _n: ["docs/x.md"])
    monkeypatch.setattr(pr, "_stream", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr, "sync_main", lambda *_a, **_k: 0)
    monkeypatch.setattr(pr.time, "sleep", lambda _s: None)
    assert pr.land_main(_WORKSPACE, 7) == 0
