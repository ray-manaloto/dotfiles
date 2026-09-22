# Copyright (c) 2026 Raymond Manaloto
"""Behavioral tests for Graphify lock, skill, and PATH currency."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "python" / "src"))

from dotfiles_setup import graphify_currency, graphify_skill
from dotfiles_setup import main as cli_main

LOCKED = "0.9.65"
NEWER = "0.9.66"


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


def test_latest_version_reads_stdout_only() -> None:
    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert args == ["mise", "latest", "pipx:graphifyy"]
        return _completed(args, stdout=f"{LOCKED}\n", stderr="unrelated warning\n")

    assert graphify_currency.latest_version(run=fake_run) == LOCKED


def test_latest_version_returns_none_on_nonzero() -> None:
    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _completed(args, rc=1, stderr="registry offline")

    assert graphify_currency.latest_version(run=fake_run) is None


def test_release_notes_between_filters_and_sorts_paginated_json() -> None:
    pages = (
        json.dumps(
            [
                {"tag_name": "v0.9.66", "body": "newest"},
                {"tag_name": "v0.9.64", "body": "too old"},
            ]
        )
        + "\n"
        + json.dumps([{"tag_name": "v0.9.65", "body": "middle"}])
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
    ) == [("v0.9.65", "middle"), ("v0.9.66", "newest")]


def test_release_notes_require_the_target_release() -> None:
    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _completed(
            args,
            stdout=json.dumps([{"tag_name": "v0.9.65", "body": "middle"}]),
        )

    with pytest.raises(graphify_currency.GraphifyCurrencyError, match=NEWER):
        graphify_currency.release_notes_between(LOCKED, NEWER, run=fake_run)


def test_write_release_receipt_is_project_scoped(tmp_path: Path) -> None:
    receipt = graphify_currency.write_release_receipt(
        tmp_path,
        [("v0.9.66", "Fixed data loss.")],
        high=NEWER,
    )
    assert receipt == tmp_path / ".agent/graphify/release-notes-0.9.66.md"
    assert receipt.read_text(encoding="utf-8") == (
        "# Graphify release notes through 0.9.66\n\n## v0.9.66\n\nFixed data loss.\n"
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

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert args == ["mise", "latest", "pipx:graphifyy"]
        return _completed(args, stdout=f"{LOCKED}\n")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)
    monkeypatch.setattr(graphify_currency.shutil, "which", lambda _name: None)

    assert graphify_currency.check(tmp_path) == ()
    assert _snapshot(tmp_path) == before


def test_check_reports_every_currency_axis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_installed_version(monkeypatch, "0.9.64")
    _write_lock(tmp_path, LOCKED)
    _seed_skill_surface(tmp_path)
    claude = tmp_path / ".claude/skills/graphify/SKILL.md"
    claude.write_text("locally changed", encoding="utf-8")
    agents_stamp = tmp_path / ".agents/skills/graphify/.graphify_version"
    agents_stamp.write_text("0.0.0\n", encoding="utf-8")

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if args == ["mise", "latest", "pipx:graphifyy"]:
            return _completed(args, stdout=f"{NEWER}\n")
        if args == ["graphify", "--version"]:
            return _completed(args, stdout="graphify 0.9.63\n")
        pytest.fail(f"unexpected subprocess: {args}")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)
    monkeypatch.setattr(
        graphify_currency.shutil, "which", lambda _name: "/shim/graphify"
    )

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

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return _completed(args, rc=1, stderr="offline registry")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)
    monkeypatch.setattr(graphify_currency.shutil, "which", lambda _name: None)

    drifts = graphify_currency.check(tmp_path)
    assert [drift.kind for drift in drifts] == ["lock-behind-latest"]
    assert drifts[0].detail == "UNVERIFIABLE: offline registry"


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
        assert args == ["mise", "latest", "pipx:graphifyy"]
        return _completed(args, stdout=f"{LOCKED}\n")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)

    assert graphify_currency.graphify_update_main(tmp_path) == 0
    assert stamp.read_text(encoding="utf-8") == f"{LOCKED}\n"
    output = capsys.readouterr().out
    assert f"graphifyy locked {LOCKED}, latest {LOCKED}" in output
    assert "already current" in output
    assert f"skill refreshed -> {stamp.parent / 'SKILL.md'}" in output


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
                    [{"tag_name": f"v{NEWER}", "body": "Reviewed change."}]
                ),
            )
        if args[:2] == ["uv", "lock"]:
            receipt = tmp_path / f".agent/graphify/release-notes-{NEWER}.md"
            assert receipt.is_file(), "receipt must precede lock mutation"
            calls.append("uv-lock")
            _write_lock(tmp_path, NEWER)
            return _completed(args)
        if args[:2] == ["uv", "sync"]:
            calls.append("uv-sync")
            return _completed(args)
        pytest.fail(f"unexpected subprocess: {args}")

    monkeypatch.setattr(graphify_currency.subprocess, "run", fake_run)

    assert graphify_currency.graphify_update_main(tmp_path) == 0
    assert calls == ["mise", "gh", "uv-lock", "uv-sync"]
    output = capsys.readouterr().out
    assert f"release-notes-{NEWER}.md (1 releases)" in output
    assert "environment synced" in output
    for platform in ("claude", "codex", "agents"):
        stamp = tmp_path / f".{platform}/skills/graphify/.graphify_version"
        assert stamp.read_text(encoding="utf-8") == f"{NEWER}\n"


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
    assert not (tmp_path / ".agent/graphify").exists()
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


def test_currency_subprocess_commands_are_allowlisted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def fake_run(
        args: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args[0] == "mise":
            return _completed(args, stdout=f"{LOCKED}\n")
        if args[0] == "gh":
            return _completed(
                args,
                stdout=json.dumps([{"tag_name": f"v{LOCKED}", "body": "notes"}]),
            )
        if args[0] == "graphify":
            return _completed(args, stdout=f"graphify {LOCKED}\n")
        return _completed(args)

    monkeypatch.setattr(
        graphify_currency.shutil, "which", lambda _name: "/shim/graphify"
    )
    assert graphify_currency.latest_version(run=fake_run) == LOCKED
    assert graphify_currency.release_notes_between("0.9.64", LOCKED, run=fake_run)
    graphify_currency.upgrade_lock(tmp_path, run=fake_run)
    assert graphify_currency.path_binary_version(run=fake_run) == LOCKED

    assert {args[0] for args in calls} == {"mise", "gh", "uv", "graphify"}
    graphify_calls = [args for args in calls if args[0] == "graphify"]
    assert graphify_calls == [["graphify", "--version"]]


@pytest.mark.parametrize(
    ("command", "entrypoint"),
    [
        ("update", "graphify_update_main"),
        ("check", "graphify_check_main"),
        ("upgrade", "graphify_upgrade_main"),
    ],
)
def test_currency_cli_parser_and_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    command: str,
    entrypoint: str,
) -> None:
    parsed = cli_main.setup_parser().parse_args(["graphify", command])
    seen: list[Path] = []

    def fake_main(project_root: Path) -> int:
        seen.append(project_root)
        return 7

    monkeypatch.setattr(cli_main, entrypoint, fake_main)
    with pytest.raises(SystemExit) as exited:
        cli_main.handle_graphify(parsed, tmp_path)
    assert exited.value.code == 7
    assert seen == [tmp_path]
