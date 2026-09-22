# Copyright (c) 2026 Raymond Manaloto
"""Behavioral tests for Graphify lock, skill, and PATH currency."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import graphify, graphify_currency, graphify_skill
from dotfiles_setup import main as cli_main

LOCKED = "0.9.65"
NEWER = "0.9.66"
PUBLISHED = "2026-09-22T12:34:56Z"
SUBPROCESS_TOOL_ALLOWLIST = ("mise", "gh", "uv", "graphify")
_MISE_SPAWN_ERROR = "cannot spawn mise"
_GRAPHIFY_SPAWN_ERROR = "cannot spawn graphify"


def _completed(
    args: list[str],
    *,
    rc: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, rc, stdout, stderr)


def _write_lock(project_root: Path, version: str) -> None:
    lock = project_root / "python/uv.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(
        f'version = 1\n\n[[package]]\nname = "graphifyy"\nversion = "{version}"\n',
        encoding="utf-8",
    )


def _patch_installed_version(monkeypatch: pytest.MonkeyPatch, version: str) -> None:
    monkeypatch.setattr(
        graphify_currency.importlib.metadata,
        "version",
        lambda name: version if name == graphify_currency.DIST else "",
    )
    monkeypatch.setattr(
        graphify_skill,
        "version",
        lambda name: version if name == graphify_currency.DIST else "",
    )


def _seed_skill_surface(project_root: Path) -> None:
    for platform in graphify_skill.MANAGED_PLATFORMS:
        graphify_skill.install_skill(platform, project_dir=project_root)
    agents = graphify_skill.resolve_placement("agents", project_dir=project_root)
    agents.skill_dst.parent.mkdir(parents=True, exist_ok=True)
    agents.skill_dst.write_text("<!-- DELIBERATE STUB -->\n", encoding="utf-8")
    graphify_skill.write_stamp("agents", project_dir=project_root)
    _write_receipt(project_root, LOCKED)


def _write_receipt(project_root: Path, version: str) -> Path:
    receipt = project_root / graphify_currency.RECEIPT_DIR / f"{version}.md"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(
        f"# Graphify v{version} release receipt\n\n- Tag: `v{version}`\n",
        encoding="utf-8",
    )
    return receipt


def _patch_ambient_binary(
    monkeypatch: pytest.MonkeyPatch,
    *,
    binary: str = "/ambient/bin/graphify",
) -> str:
    monkeypatch.setenv("DOTFILES_AMBIENT_PATH", "/ambient/bin:/usr/bin")
    monkeypatch.delenv("MISE_TASK_NAME", raising=False)
    monkeypatch.setattr(
        graphify_currency.shutil,
        "which",
        lambda name, path=None: binary if name == "graphify" and path else None,
    )
    return binary


def _snapshot(project_root: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(project_root): path.read_bytes()
        for path in project_root.rglob("*")
        if path.is_file()
    }


def test_locked_version_reads_the_single_uv_lock_entry(tmp_path: Path) -> None:
    _write_lock(tmp_path, LOCKED)
    assert graphify_currency.locked_version(tmp_path) == LOCKED


@pytest.mark.parametrize(
    "lock_text",
    [
        "version = 1\n",
        (
            'version = 1\n[[package]]\nname = "graphifyy"\nversion = "0.9.64"\n'
            '[[package]]\nname = "graphifyy"\nversion = "0.9.65"\n'
        ),
    ],
)
def test_locked_version_rejects_absent_or_duplicate_entries(
    tmp_path: Path, lock_text: str
) -> None:
    lock = tmp_path / "python/uv.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text(lock_text, encoding="utf-8")
    with pytest.raises(graphify_currency.GraphifyCurrencyError):
        graphify_currency.locked_version(tmp_path)


def test_release_notes_between_filters_and_sorts_paginated_json() -> None:
    pages = (
        json.dumps(
            [
                {
                    "tag_name": "v0.9.66",
                    "published_at": PUBLISHED,
                    "body": "newest",
                },
                {
                    "tag_name": "v0.9.64",
                    "published_at": PUBLISHED,
                    "body": "too old",
                },
            ]
        )
        + "\n"
        + json.dumps(
            [
                {
                    "tag_name": "v0.9.65",
                    "published_at": PUBLISHED,
                    "body": "middle",
                }
            ]
        )
    )

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert args == [
            "gh",
            "api",
            "repos/Graphify-Labs/graphify/releases",
            "--paginate",
        ]
        return _completed(args, stdout=pages)

    assert graphify_currency.release_notes_between(
        "0.9.64", "0.9.66", run=fake_run
    ) == [
        graphify_currency.ReleaseNote("0.9.65", "v0.9.65", PUBLISHED, "middle"),
        graphify_currency.ReleaseNote("0.9.66", "v0.9.66", PUBLISHED, "newest"),
    ]


def test_release_notes_require_the_target_release() -> None:
    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _completed(
            args,
            stdout=json.dumps(
                [
                    {
                        "tag_name": "v0.9.65",
                        "published_at": PUBLISHED,
                        "body": "middle",
                    }
                ]
            ),
        )

    with pytest.raises(graphify_currency.GraphifyCurrencyError, match=NEWER):
        graphify_currency.release_notes_between(LOCKED, NEWER, run=fake_run)


def test_write_release_receipts_are_tracked_per_release(tmp_path: Path) -> None:
    receipts = graphify_currency.write_release_receipts(
        tmp_path,
        [
            graphify_currency.ReleaseNote(
                NEWER,
                f"v{NEWER}",
                PUBLISHED,
                "Fixed data loss.\nBody spacing stays verbatim.",
            )
        ],
    )
    assert receipts == (tmp_path / f"docs/receipts/graphify/{NEWER}.md",)
    receipt = receipts[0]
    assert receipt.read_text(encoding="utf-8") == (
        f"# Graphify v{NEWER} release receipt\n\n"
        "Written by `mise run graphify-update`.\n\n"
        f"- Tag: `v{NEWER}`\n"
        f"- Published at: `{PUBLISHED}`\n\n"
        "## Release notes (verbatim)\n\n"
        "Fixed data loss.\nBody spacing stays verbatim.\n"
    )


def test_upgrade_lock_runs_native_uv_commands_sequentially(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["cwd"] == tmp_path
        calls.append(args)
        return _completed(args)

    graphify_currency.upgrade_lock(tmp_path, run=fake_run)
    assert calls == [
        ["uv", "lock", "--project", "python", "--upgrade-package", "graphifyy"],
        ["uv", "sync", "--project", "python"],
    ]


def test_upgrade_lock_stops_before_sync_when_lock_fails(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return _completed(args, rc=1, stderr="resolution failed")

    with pytest.raises(graphify_currency.GraphifyCurrencyError, match="resolution"):
        graphify_currency.upgrade_lock(tmp_path, run=fake_run)
    assert calls == [
        ["uv", "lock", "--project", "python", "--upgrade-package", "graphifyy"]
    ]


def test_check_is_read_only_and_clean_when_every_surface_agrees(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    before = _snapshot(tmp_path)
    binary = _patch_ambient_binary(monkeypatch)

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert args == ["mise", "latest", "pipx:graphifyy"]
        return _completed(
            args,
            stdout=f"{LOCKED}\n",
            stderr="unrelated warning must not replace stdout\n",
        )

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)
    original_run = fake_run

    def run_with_path(
        args: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args == [binary, "--version"]:
            assert kwargs["env"] == {"PATH": "/ambient/bin:/usr/bin"}
            return _completed(args, stdout=f"graphify {LOCKED}\n")
        return original_run(args, **kwargs)

    monkeypatch.setattr(graphify_currency.subprocess, "run", run_with_path)

    assert graphify_currency.check(tmp_path) == ()
    assert _snapshot(tmp_path) == before


def test_check_reports_every_currency_axis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_installed_version(monkeypatch, "0.9.64")
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    binary = _patch_ambient_binary(monkeypatch, binary="/shim/graphify")
    claude = tmp_path / ".claude/skills/graphify/SKILL.md"
    claude.write_text("locally changed", encoding="utf-8")
    agents_stamp = tmp_path / ".agents/skills/graphify/.graphify_version"
    agents_stamp.write_text("0.0.0\n", encoding="utf-8")

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args == ["mise", "latest", "pipx:graphifyy"]:
            return _completed(args, stdout=f"{NEWER}\n")
        if args == [binary, "--version"]:
            return _completed(args, stdout="graphify 0.9.63\n")
        pytest.fail(f"unexpected subprocess: {args}")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)
    kinds = {drift.kind for drift in graphify_currency.check(tmp_path)}
    assert kinds == {
        "lock-behind-latest",
        "installed!=locked",
        "stamp",
        "skill-bytes",
        "path-binary",
    }


def test_check_reports_unverifiable_latest_stderr(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    binary = _patch_ambient_binary(monkeypatch)

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args == [binary, "--version"]:
            return _completed(args, stdout=f"graphify {LOCKED}\n")
        return _completed(args, rc=1, stderr="offline registry")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)

    drifts = graphify_currency.check(tmp_path)
    assert [drift.kind for drift in drifts] == ["lock-behind-latest"]
    assert drifts[0].detail == "UNVERIFIABLE: offline registry"


def test_offline_check_skips_network_and_keeps_local_axes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    binary = _patch_ambient_binary(monkeypatch)

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == [binary, "--version"]
        assert kwargs["env"] == {"PATH": "/ambient/bin:/usr/bin"}
        return _completed(args, stdout=f"graphify {LOCKED}\n")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)
    assert graphify_currency.check(tmp_path, offline=True) == ()


def test_offline_check_fails_when_locked_release_receipt_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    (tmp_path / graphify_currency.RECEIPT_DIR / f"{LOCKED}.md").unlink()
    binary = _patch_ambient_binary(monkeypatch)
    monkeypatch.setattr(
        graphify_currency.subprocess,
        "run",
        lambda args, **_kwargs: _completed(
            args,
            stdout=f"graphify {LOCKED}\n" if args == [binary, "--version"] else "",
        ),
    )

    drifts = graphify_currency.check(tmp_path, offline=True)
    receipt = next(drift for drift in drifts if drift.kind == "receipt-missing")
    assert receipt.detail == (
        f"receipt-missing: docs/receipts/graphify/{LOCKED}.md — "
        "run mise run graphify-update"
    )


def test_path_probe_uses_mise_resolved_path_when_ambient_capture_is_blind(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    binary_dir = tmp_path / "mise/bin"
    binary_dir.mkdir(parents=True)
    binary = binary_dir / "graphify"
    binary.write_text(f"#!/bin/sh\nprintf 'graphify {LOCKED}\\n'\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.delenv("DOTFILES_AMBIENT_PATH", raising=False)
    monkeypatch.setenv("MISE_TASK_NAME", "doctor")
    monkeypatch.setenv("PATH", str(binary_dir))

    assert graphify_currency.graphify_check_main(tmp_path, offline=True) == 0
    assert (
        f"graphify path-binary: {binary} "
        f"(version={LOCKED}; mise-resolved PATH; stale-activation blind)"
        in capsys.readouterr().out
    )


def test_path_probe_fails_when_mise_resolved_path_has_no_graphify(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    empty_path = tmp_path / "empty-bin"
    empty_path.mkdir()
    monkeypatch.delenv("DOTFILES_AMBIENT_PATH", raising=False)
    monkeypatch.setenv("MISE_TASK_NAME", "doctor")
    monkeypatch.setenv("PATH", str(empty_path))

    drifts = graphify_currency.check(tmp_path, offline=True)
    path_drift = next(drift for drift in drifts if drift.kind == "path-binary")
    assert path_drift.detail == (
        "path-binary UNVERIFIABLE (graphify absent from mise-resolved PATH)"
    )


def test_path_probe_executes_the_binary_resolved_from_ambient_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    binary = _patch_ambient_binary(monkeypatch, binary="/fake/bin/graphify")

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == [binary, "--version"]
        assert kwargs["env"] == {"PATH": "/ambient/bin:/usr/bin"}
        return _completed(args, stdout="graphify 0.0.1\n")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)
    drifts = graphify_currency.check(tmp_path, offline=True)
    path_drift = next(drift for drift in drifts if drift.kind == "path-binary")
    assert "/fake/bin/graphify reports 0.0.1 != locked 0.9.65" in path_drift.detail


def test_path_probe_never_accepts_the_uv_project_venv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    venv = tmp_path / "python/.venv"
    ambient = tmp_path / "ambient/bin"
    monkeypatch.delenv("DOTFILES_AMBIENT_PATH", raising=False)
    monkeypatch.delenv("MISE_TASK_NAME", raising=False)
    monkeypatch.setenv("VIRTUAL_ENV", str(venv))
    monkeypatch.setenv("PATH", f"{venv / 'bin'}:{ambient}")

    def fake_which(_name: str, *, path: str) -> str:
        assert path == str(ambient)
        return str(ambient / "graphify")

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert args == [str(ambient / "graphify"), "--version"]
        assert kwargs["env"] == {"PATH": str(ambient)}
        return _completed(args, stdout="graphify 0.0.1\n")

    monkeypatch.setattr(graphify_currency.shutil, "which", fake_which)
    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)
    drifts = graphify_currency.check(tmp_path, offline=True)
    path_drift = next(drift for drift in drifts if drift.kind == "path-binary")
    assert str(ambient / "graphify") in path_drift.detail


@pytest.mark.parametrize(
    ("failure", "finding"),
    [
        ("timeout", "timed out after 30 seconds"),
        ("oserror", "cannot spawn mise"),
        ("nonzero", "registry offline"),
        ("malformed", "mise latest returned invalid version 'not-a-version'"),
    ],
)
def test_latest_probe_failures_are_exact_unverifiable_findings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    failure: str,
    finding: str,
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    binary = _patch_ambient_binary(monkeypatch)

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args == [binary, "--version"]:
            return _completed(args, stdout=f"graphify {LOCKED}\n")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 30)
        if failure == "oserror":
            raise OSError(_MISE_SPAWN_ERROR)
        if failure == "nonzero":
            return _completed(args, rc=2, stderr="registry offline")
        return _completed(args, stdout="not-a-version\n")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)
    assert graphify_currency.graphify_check_main(tmp_path) == 1
    output = capsys.readouterr().out
    assert "graphify drift [lock-behind-latest] UNVERIFIABLE:" in output
    assert finding in output


@pytest.mark.parametrize(
    ("failure", "finding"),
    [
        ("timeout", "timed out after 10 seconds"),
        ("oserror", "cannot spawn graphify"),
        ("nonzero", "graphify version failed"),
        ("malformed", "graphify --version returned no usable version"),
    ],
)
def test_path_version_probe_failures_are_exact_findings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    failure: str,
    finding: str,
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    binary = _patch_ambient_binary(monkeypatch)

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert args == [binary, "--version"]
        if failure == "timeout":
            raise subprocess.TimeoutExpired(args, 10)
        if failure == "oserror":
            raise OSError(_GRAPHIFY_SPAWN_ERROR)
        if failure == "nonzero":
            return _completed(args, rc=2, stderr="graphify version failed")
        return _completed(args, stdout="not a version\n")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)
    drifts = graphify_currency.check(tmp_path, offline=True)
    path_drift = next(drift for drift in drifts if drift.kind == "path-binary")
    assert path_drift.detail.startswith("path-binary UNVERIFIABLE (")
    assert finding in path_drift.detail


def test_release_fetch_nonzero_and_malformed_json_fail_closed() -> None:
    def nonzero(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return _completed(args, rc=2, stderr="GitHub unavailable")

    with pytest.raises(
        graphify_currency.GraphifyCurrencyError,
        match="gh api failed: GitHub unavailable",
    ):
        graphify_currency.release_notes_between(LOCKED, NEWER, run=nonzero)

    def malformed(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _completed(args, stdout="{not-json")

    with pytest.raises(
        graphify_currency.GraphifyCurrencyError,
        match="gh api returned invalid JSON",
    ):
        graphify_currency.release_notes_between(LOCKED, NEWER, run=malformed)


def test_repository_locked_graphify_has_tracked_receipt() -> None:
    repo = Path(__file__).parent.parent
    locked = graphify_currency.locked_version(repo)
    receipt = repo / graphify_currency.RECEIPT_DIR / f"{locked}.md"
    assert receipt.is_file(), (
        f"receipt-missing: {receipt.relative_to(repo)} — run mise run graphify-update"
    )
    assert f"- Tag: `v{locked}`" in receipt.read_text(encoding="utf-8")


def test_online_check_prints_graph_health_without_folding_it_into_currency_rc(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    binary = _patch_ambient_binary(monkeypatch)

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args == ["mise", "latest", "pipx:graphifyy"]:
            return _completed(args, stdout=f"{LOCKED}\n")
        assert args == [binary, "--version"]
        return _completed(args, stdout=f"graphify {LOCKED}\n")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)
    monkeypatch.setattr(
        graphify,
        "graphify_health",
        lambda _root: graphify.HealthResult(
            graphify.GraphifyStatus.STALE,
            LOCKED,
            "built at an older commit",
        ),
    )

    assert graphify_currency.graphify_check_main(tmp_path) == 0
    output = capsys.readouterr().out
    assert (
        "graphify path-binary: /ambient/bin/graphify "
        "(version=0.9.65; ambient PATH)" in output
    )
    assert "graphify currency current" in output
    assert "graphify-health: stale (runtime=0.9.65) built at an older commit" in output


def test_update_current_still_repairs_a_stale_stamp(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    stamp = tmp_path / ".codex/skills/graphify/.graphify_version"
    stamp.write_text("0.0.0\n", encoding="utf-8")

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args == ["mise", "latest", "pipx:graphifyy"]:
            return _completed(args, stdout=f"{LOCKED}\n")
        if args[-2:] == ["graphify", "refresh-skills"]:
            graphify_skill.refresh_skills(tmp_path)
            return _completed(args, stdout=f"skill refreshed -> {stamp.parent}\n")
        if args[-3:] == ["graphify", "check", "--offline"]:
            return _completed(args, stdout="graphify currency current\n")
        pytest.fail(f"unexpected subprocess: {args}")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)

    assert graphify_currency.graphify_update_main(tmp_path) == 0
    assert stamp.read_text(encoding="utf-8") == f"{LOCKED}\n"
    output = capsys.readouterr().out
    assert f"graphifyy locked {LOCKED}, latest {LOCKED}" in output
    assert "already current" in output
    assert "skill refreshed ->" in output
    assert "graphify currency current" in output


def test_update_writes_receipt_before_native_uv_and_then_refreshes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    _patch_installed_version(monkeypatch, NEWER)
    calls: list[str] = []

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args == ["mise", "latest", "pipx:graphifyy"]:
            calls.append("mise")
            return _completed(args, stdout=f"{NEWER}\n")
        if args[0] == "gh":
            calls.append("gh")
            return _completed(
                args,
                stdout=json.dumps(
                    [
                        {
                            "tag_name": f"v{NEWER}",
                            "published_at": PUBLISHED,
                            "body": "Reviewed change.",
                        }
                    ]
                ),
            )
        if args[:2] == ["uv", "lock"]:
            receipt = tmp_path / f"docs/receipts/graphify/{NEWER}.md"
            assert receipt.is_file(), "receipt must precede lock mutation"
            calls.append("uv-lock")
            _write_lock(tmp_path, NEWER)
            return _completed(args)
        if args[:2] == ["uv", "sync"]:
            calls.append("uv-sync")
            return _completed(args)
        if args[-2:] == ["graphify", "refresh-skills"]:
            calls.append("fresh-refresh")
            graphify_skill.refresh_skills(tmp_path)
            return _completed(args, stdout="skills refreshed\n")
        if args[-3:] == ["graphify", "check", "--offline"]:
            calls.append("fresh-check")
            assert all(
                (tmp_path / f".{platform}/skills/graphify/.graphify_version").read_text(
                    encoding="utf-8"
                )
                == f"{NEWER}\n"
                for platform in ("claude", "codex", "agents")
            )
            return _completed(args, stdout="graphify currency current\n")
        pytest.fail(f"unexpected subprocess: {args}")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)

    assert graphify_currency.graphify_update_main(tmp_path) == 0
    assert calls == [
        "mise",
        "gh",
        "uv-lock",
        "uv-sync",
        "fresh-refresh",
        "fresh-check",
    ]
    output = capsys.readouterr().out
    assert f"docs/receipts/graphify/{NEWER}.md" in output
    assert "environment synced" in output
    for platform in ("claude", "codex", "agents"):
        stamp = tmp_path / f".{platform}/skills/graphify/.graphify_version"
        assert stamp.read_text(encoding="utf-8") == f"{NEWER}\n"


def test_update_refreshes_changed_placement_metadata_in_a_fresh_process(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A sync can replace both package bytes and destination metadata."""
    _patch_installed_version(monkeypatch, LOCKED)
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    _patch_installed_version(monkeypatch, NEWER)
    synced = False
    refreshed = tmp_path / ".codex-v2/skills/graphify/SKILL.md"

    monkeypatch.setattr(
        graphify_currency.graphify_skill,
        "refresh_skills",
        lambda _root: pytest.fail("cached pre-sync installer metadata was used"),
    )

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        nonlocal synced
        if args[0] == "mise":
            return _completed(args, stdout=f"{NEWER}\n")
        if args[0] == "gh":
            return _completed(
                args,
                stdout=json.dumps(
                    [
                        {
                            "tag_name": f"v{NEWER}",
                            "published_at": PUBLISHED,
                            "body": "placement changed",
                        }
                    ]
                ),
            )
        if args[:2] == ["uv", "lock"]:
            _write_lock(tmp_path, NEWER)
            return _completed(args)
        if args[:2] == ["uv", "sync"]:
            synced = True
            return _completed(args)
        if args[-2:] == ["graphify", "refresh-skills"]:
            assert synced, "fresh refresh must happen after sync"
            refreshed.parent.mkdir(parents=True)
            refreshed.write_text("new package bytes", encoding="utf-8")
            return _completed(args, stdout=f"skill refreshed -> {refreshed}\n")
        if args[-3:] == ["graphify", "check", "--offline"]:
            assert refreshed.read_text(encoding="utf-8") == "new package bytes"
            return _completed(args, stdout="graphify currency current\n")
        pytest.fail(f"unexpected subprocess: {args}")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)
    assert graphify_currency.graphify_update_main(tmp_path) == 0
    assert refreshed.is_file()


def test_update_does_not_mutate_when_release_fetch_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_lock(tmp_path, LOCKED)
    calls: list[str] = []

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args[0])
        if args[0] == "mise":
            return _completed(args, stdout=f"{NEWER}\n")
        if args[0] == "gh":
            return _completed(args, rc=1, stderr="GitHub unavailable")
        pytest.fail("uv must not run without a receipt")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)

    assert graphify_currency.graphify_update_main(tmp_path) == 1
    assert calls == ["mise", "gh"]
    assert graphify_currency.locked_version(tmp_path) == LOCKED
    assert not (tmp_path / f"docs/receipts/graphify/{NEWER}.md").exists()
    assert "GitHub unavailable" in capsys.readouterr().err


def test_upgrade_stops_before_rebuild_when_update_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(graphify_currency, "graphify_update_main", lambda _root: 7)
    monkeypatch.setattr(
        "dotfiles_setup.graphify.graphify_rebuild_main",
        lambda _root: pytest.fail("rebuild must not run"),
    )
    assert graphify_currency.graphify_upgrade_main(tmp_path) == 7


def test_upgrade_runs_update_before_rebuild(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        graphify_currency,
        "graphify_update_main",
        lambda _root: calls.append("update") or 0,
    )
    monkeypatch.setattr(
        "dotfiles_setup.graphify.graphify_rebuild_main",
        lambda _root: calls.append("rebuild") or 3,
    )
    assert graphify_currency.graphify_upgrade_main(tmp_path) == 3
    assert calls == ["update", "rebuild"]


def _subprocess_literal(call: ast.Call) -> tuple[str, ...] | None:
    """Return a normalized argv for a literal run boundary, if this is one."""
    name = ""
    if isinstance(call.func, ast.Name):
        name = call.func.id
    elif (
        isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "subprocess"
    ):
        name = call.func.attr
    if name not in {"run", "Popen", "check_output"} and not name.startswith("_run"):
        return None
    if not call.args or not isinstance(call.args[0], ast.List):
        return None
    values: list[str] = []
    for index, item in enumerate(call.args[0].elts):
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            values.append(item.value)
        elif index == 0 and isinstance(item, ast.Name) and item.id == "binary":
            values.append("graphify")
        else:
            values.append("<dynamic>")
    return tuple(values)


def _git_output_literal(call: ast.Call) -> tuple[str, ...] | None:
    """Return normalized argv for a direct `_git_output` call."""
    if not isinstance(call.func, ast.Name) or call.func.id != "_git_output":
        return None
    values: list[str] = []
    for item in call.args[1:]:
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            values.append(item.value)
        else:
            values.append("<dynamic>")
    return tuple(values)


def _module_imports(tree: ast.AST) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_zero_token_subprocess_surface_is_ast_allowlisted() -> None:
    repo = Path(__file__).parent.parent
    full_modules = (
        repo / "python/src/dotfiles_setup/graphify_currency.py",
        repo / "python/src/dotfiles_setup/graphify_skill.py",
    )
    trees = [ast.parse(path.read_text(encoding="utf-8")) for path in full_modules]
    graphify_tree = ast.parse(
        (repo / "python/src/dotfiles_setup/graphify.py").read_text(encoding="utf-8")
    )
    rebuild_nodes = [
        node
        for node in graphify_tree.body
        if isinstance(node, ast.FunctionDef) and node.name in {"_run", "update"}
    ]
    scanned: list[ast.AST] = [*trees, *rebuild_nodes]

    assert all(
        not imported.startswith("graphify.llm")
        for tree in (graphify_tree, *trees)
        for imported in _module_imports(tree)
    )
    commands = [
        command
        for root in scanned
        for node in ast.walk(root)
        if isinstance(node, ast.Call)
        if (command := _subprocess_literal(node)) is not None
    ]
    assert commands
    assert {command[0] for command in commands} <= set(SUBPROCESS_TOOL_ALLOWLIST)
    graphify_commands = [command for command in commands if command[0] == "graphify"]
    assert graphify_commands == [
        ("graphify", "--version"),
        ("graphify", "update", "<dynamic>"),
    ]
    git_commands = {
        command
        for node in ast.walk(graphify_tree)
        if isinstance(node, ast.Call)
        if (command := _git_output_literal(node)) is not None
    }
    assert git_commands == {
        ("rev-parse", "HEAD"),
        ("diff", "--name-status", "--diff-filter=ACDMR", "<dynamic>"),
    }


@pytest.mark.parametrize(
    ("command", "entrypoint"),
    [
        ("update", "graphify_update_main"),
        ("check", "graphify_check_main"),
        ("upgrade", "graphify_upgrade_main"),
        ("refresh-skills", "graphify_skill_refresh_main"),
    ],
)
def test_currency_cli_parser_and_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    command: str,
    entrypoint: str,
) -> None:
    parsed = cli_main.setup_parser().parse_args(["graphify", command])
    seen: list[tuple[Path, dict[str, object]]] = []

    def fake_main(project_root: Path, **kwargs: object) -> int:
        seen.append((project_root, kwargs))
        return 7

    monkeypatch.setattr(cli_main, entrypoint, fake_main)
    with pytest.raises(SystemExit) as exited:
        cli_main.handle_graphify(parsed, tmp_path)
    assert exited.value.code == 7
    expected_kwargs = {"offline": False} if command == "check" else {}
    assert seen == [(tmp_path, expected_kwargs)]


def test_currency_cli_offline_flag_dispatches_without_network(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    parsed = cli_main.setup_parser().parse_args(["graphify", "check", "--offline"])
    seen: list[tuple[Path, bool]] = []

    def fake_check(project_root: Path, *, offline: bool = False) -> int:
        seen.append((project_root, offline))
        return 0

    monkeypatch.setattr(cli_main, "graphify_check_main", fake_check)
    with pytest.raises(SystemExit) as exited:
        cli_main.handle_graphify(parsed, tmp_path)
    assert exited.value.code == 0
    assert seen == [(tmp_path, True)]
