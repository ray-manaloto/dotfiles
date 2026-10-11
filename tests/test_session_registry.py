# Copyright (c) 2026 Raymond Manaloto
"""Public fleet/card/issue previews with isolated Git and harness boundaries."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

sys.path.insert(0, str(Path(__file__).parent.parent / "python/src"))
from dotfiles_setup import handoff_inbox
from dotfiles_setup import session_registry as registry
from dotfiles_setup.main import setup_parser
from dotfiles_setup.session_common import SessionError
from dotfiles_setup.session_ledger import TranscriptBases

STAMP = datetime(2026, 10, 5, 13, tzinfo=UTC)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.invalid",
            *args,
        ],
        check=True,
        capture_output=True,
    )


def _row(
    cwd: Path,
    sid: str,
    name: str | None,
    *,
    state: str = "working",
    started: str = "2026-10-05T12:00:00Z",
) -> dict[str, object]:
    row: dict[str, object] = {
        "cwd": str(cwd),
        "id": sid[:8],
        "kind": "background",
        "sessionId": sid,
        "startedAt": started,
        "state": state,
    }
    if name is not None:
        row["name"] = name
    return row


@pytest.fixture
def fleet(
    tmp_path: Path,
) -> tuple[
    tuple[Path, Path],
    Path,
    dict[str, object],
    Callable[..., subprocess.CompletedProcess[str]],
    TranscriptBases,
]:
    roots = tmp_path / "dotfiles", tmp_path / "knowledge-base"
    for root in roots:
        root.mkdir()
        _git(root, "init", "-q", "-b", "main")
        _git(root, "commit", "-q", "--allow-empty", "-m", "root")
        _git(
            root,
            "remote",
            "add",
            "origin",
            f"git@github.com:ray-manaloto/{root.name}.git",
        )
    worktree = tmp_path / "not-a-dotfiles-prefix"
    _git(roots[0], "worktree", "add", "-q", "-b", "lane", str(worktree))
    rows = [
        _row(
            roots[0],
            "coordinator-old",
            "dotfiles-old.coordinator",
            state="stopped",
            started="2026-10-05T15:00:00+03:00",
        ),
        _row(
            worktree,
            "coordinator-new",
            "dotfiles-new.coordinator",
            started="2026-10-05T12:30:00Z",
        ),
        _row(roots[0], "watcher-old", "dotfiles-old.watch", state="blocked"),
        _row(
            roots[0],
            "watcher-new",
            "dotfiles-new.watch",
            state="done",
            started="2026-10-05T12:40:00Z",
        ),
        _row(roots[1], "kb-stopped", "kb-old.watch", state="stopped"),
        _row(roots[1], "kb-blocked", "kb-build", state="blocked"),
        _row(roots[1], "shared-session-id", None),
        _row(roots[0], "malicious-session", "../escaped", state="stopped"),
        _row(roots[0], "duplicate-one", "same-lane"),
        _row(roots[0], "duplicate-two", "same-lane"),
        _row(roots[0], "done-lane", "finished", state="done"),
    ]
    control: dict[str, object] = {
        "rows": rows,
        "rc": 0,
        "issues": [[]],
        "issue_rc": 0,
        "calls": [],
    }

    def runner(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls = control["calls"]
        assert isinstance(calls, list)
        calls.append(argv)
        if argv[0] == "claude":
            return subprocess.CompletedProcess(
                argv,
                int(str(control["rc"])),
                json.dumps(control["rows"]),
                "controlled failure",
            )
        if argv[0] == "gh":
            assert argv[1:4] == ["api", "--paginate", "--slurp"]
            assert "POST" not in argv
            assert "PATCH" not in argv
            return subprocess.CompletedProcess(
                argv,
                int(str(control["issue_rc"])),
                json.dumps(control["issues"]),
                "controlled read failure",
            )
        return subprocess.run(argv, text=True, capture_output=True, check=False)

    codex = tmp_path / "codex"
    codex.mkdir()
    (codex / "source.jsonl").write_text(
        json.dumps(
            {
                "type": "session_meta",
                "payload": {
                    "id": "shared-session-id",
                    "cwd": str(roots[1]),
                    "timestamp": "2026-10-05T12:50:00Z",
                },
            }
        )
        + "\n"
    )
    return (
        roots,
        worktree,
        control,
        runner,
        TranscriptBases(codex=codex, claude=tmp_path / "claude"),
    )


def test_inventory_optional_name_provider_identity_topology_and_unknown_liveness(
    fleet: tuple,
) -> None:
    roots, worktree, _control, runner, bases = fleet
    snapshot = registry.collect(roots, runner=runner, bases=bases, clock=lambda: STAMP)
    assert snapshot["omissions"] == []
    assert snapshot["collected_at"] == "2026-10-05T13:00:00+00:00"
    assert {repo["github_repo"] for repo in snapshot["repositories"]} == {
        "ray-manaloto/dotfiles",
        "ray-manaloto/knowledge-base",
    }
    collision = [
        row for row in snapshot["sessions"] if row["session_id"] == "shared-session-id"
    ]
    assert {row["provider"] for row in collision} == {"claude", "codex"}
    assert all(row["name"] is None and row["role"] == "unknown" for row in collision)
    assert all(row["liveness"]["status"] == "unknown" for row in snapshot["sessions"])
    worktree_session = next(
        row for row in snapshot["sessions"] if row["cwd"] == str(worktree)
    )
    assert worktree_session["repo_key"] == "ray-manaloto/dotfiles"
    assert len(snapshot["sessions"]) == 12


def test_card_publication_paths_duplicate_keys_archive_and_failed_census_preservation(
    fleet: tuple,
) -> None:
    roots, _worktree, control, runner, bases = fleet
    snapshot = registry.collect(roots, runner=runner, bases=bases, clock=lambda: STAMP)
    result = registry.write_cards(
        snapshot, state_root=roots[0], authorize=lambda: "coordinator"
    )
    assert len(result["written"]) == 8
    assert all(
        Path(path).parent == roots[0] / ".agent/lanes" for path in result["written"]
    )
    assert not (roots[0] / "escape").exists()
    duplicate = sorted((roots[0] / ".agent/lanes").glob("same-lane*.md"))
    assert len(duplicate) == 2
    assert duplicate[0].name != duplicate[1].name
    before = {Path(path): Path(path).read_bytes() for path in result["written"]}
    control["rc"] = 1
    failed = registry.collect(roots, runner=runner, bases=bases)
    preserved = registry.write_cards(
        failed, state_root=roots[0], authorize=lambda: "coordinator"
    )
    assert preserved["written"] == []
    assert preserved["omissions"]
    assert all(path.read_bytes() == data for path, data in before.items())
    control["rc"] = 0
    control["rows"] = []
    empty = registry.collect(roots, runner=runner, bases=bases)
    archived = registry.write_cards(
        empty, state_root=roots[0], authorize=lambda: "coordinator"
    )
    assert len(archived["archived"]) == 8
    assert not list((roots[0] / ".agent/lanes").glob("*.md"))
    assert all(
        Path(path).read_bytes() in before.values() for path in archived["archived"]
    )


def test_unknown_repo_missing_writer_authorization_and_symlink_are_refused(
    fleet: tuple, tmp_path: Path
) -> None:
    roots, _worktree, _control, runner, bases = fleet
    snapshot = registry.collect(roots, runner=runner, bases=bases)
    with pytest.raises(SessionError, match="authorization"):
        registry.write_cards(snapshot, state_root=roots[0])
    with pytest.raises(SessionError, match="unknown repository"):
        registry.write_cards(
            snapshot, state_root=tmp_path, authorize=lambda: "coordinator"
        )

    def refused() -> str:
        msg = "superseded"
        raise handoff_inbox.InboxError(msg)

    with pytest.raises(handoff_inbox.InboxError, match="superseded"):
        registry.write_cards(snapshot, state_root=roots[0], authorize=refused)
    outside = tmp_path / "outside"
    outside.mkdir()
    (roots[0] / ".agent").symlink_to(outside, target_is_directory=True)
    with pytest.raises(SessionError, match="escapes"):
        registry.write_cards(
            snapshot, state_root=roots[0], authorize=lambda: "coordinator"
        )
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize(("failed_rows", "rc"), [([], 1), ({}, 0), ([{}], 0)])
def test_inventory_failure_is_explicit(
    fleet: tuple, failed_rows: object, rc: int
) -> None:
    roots, _worktree, control, runner, bases = fleet
    control["rows"], control["rc"] = failed_rows, rc
    snapshot = registry.collect(roots, runner=runner, bases=bases)
    assert snapshot["omissions"]
    assert any("claude agents" in reason for reason in snapshot["omissions"])


def test_unregistered_cwd_is_retained_without_guessing_membership(
    fleet: tuple, tmp_path: Path
) -> None:
    roots, _worktree, control, runner, bases = fleet
    control["rows"] = [
        _row(
            tmp_path / "dotfiles-imposter",
            "imposter-session",
            "dotfiles-imposter.coordinator",
        )
    ]
    snapshot = registry.collect(roots, runner=runner, bases=bases)
    row = next(
        row for row in snapshot["sessions"] if row["session_id"] == "imposter-session"
    )
    assert row["repo_key"] is None
    assert "unregistered session cwd" in snapshot["omissions"][0]


def test_chains_timestamp_order_predecessor_evidence_and_card_content(
    fleet: tuple,
) -> None:
    roots, _worktree, _control, runner, bases = fleet
    plan = roots[0] / "task_plan.md"
    plan.write_text(
        "# same-lane\n- [ ] open integration\n- [x] completed research\n"
        "## Research same-lane\n- investigate shape\n"
        "## Blockers same-lane\n- SLOT GO absent\n"
        "## Suggestions same-lane\n- reuse native CLI\n"
    )
    launch = roots[0] / ".agent/state/coordinator-handoff/coordinator-old.json"
    launch.parent.mkdir(parents=True)
    launch.write_text(json.dumps({"launch": {"successor": "dotfiles-new.coordinator"}}))
    snapshot = registry.collect(roots, runner=runner, bases=bases)
    chain = next(
        chain
        for chain in snapshot["chains"]
        if chain["stable_key"] == "ray-manaloto/dotfiles:coordinator"
    )
    assert chain["display_session_id"] == "claude:coordinator-new"
    assert chain["member_session_ids"] == [
        "claude:coordinator-old",
        "claude:coordinator-new",
    ]
    assert chain["predecessor_edges"] == [
        {
            "predecessor": "claude:coordinator-old",
            "successor": "claude:coordinator-new",
            "evidence_ref": str(launch),
        }
    ]
    row = next(
        row for row in snapshot["sessions"] if row["session_id"] == "duplicate-one"
    )
    assert row["task_refs"] == [
        f"{plan}:2",
        f"{plan}:3",
        f"{plan}:5",
        f"{plan}:7",
        f"{plan}:9",
    ]
    text = registry.render_card(snapshot, row)
    for expected in (
        str(roots[0]),
        "open integration",
        "completed research",
        "investigate shape",
        "SLOT GO absent",
        "reuse native CLI",
        "## Source timestamps",
    ):
        assert expected in text
    assert "HEAD: `unknown`" not in text


def test_issue_preview_role_chain_done_filter_marker_reuse_and_read_failure(
    fleet: tuple,
) -> None:
    roots, _worktree, control, runner, bases = fleet
    snapshot = registry.collect(roots, runner=runner, bases=bases)
    preview = registry.issue_plan(snapshot, runner=runner)
    coordinator = next(
        intent
        for intent in preview["intentions"]
        if intent["stable_key"] == "ray-manaloto/dotfiles:coordinator"
    )
    assert coordinator["action"] == "create"
    assert coordinator["member_session_ids"] == [
        "claude:coordinator-old",
        "claude:coordinator-new",
    ]
    assert not any(
        "claude:done-lane" in intent["member_session_ids"]
        for intent in preview["intentions"]
    )
    assert (
        len(
            [
                intent
                for intent in preview["intentions"]
                if intent["stable_key"] == "ray-manaloto/dotfiles:watcher"
            ]
        )
        == 1
    )
    assert any(
        intent["repo"] == "ray-manaloto/knowledge-base" and intent["action"] == "create"
        for intent in preview["intentions"]
    )
    digest = hashlib.sha256(b"ray-manaloto/dotfiles:coordinator").hexdigest()
    control["issues"] = [
        [
            {
                "number": 1900,
                "title": "renamed existing issue",
                "body": f"<!-- lane-registry:{digest} -->",
                "html_url": "https://github.com/ray-manaloto/dotfiles/issues/1900",
            }
        ]
    ]
    reuse = registry.issue_plan(snapshot, runner=runner)
    assert (
        next(
            intent
            for intent in reuse["intentions"]
            if intent["stable_key"] == coordinator["stable_key"]
        )["action"]
        == "reuse"
    )
    assert "# Coordinator plan delta" in reuse["plan_delta"]
    control["issue_rc"] = 1
    blocked = registry.issue_plan(snapshot, runner=runner)
    assert all(intent["action"] == "blocked" for intent in blocked["intentions"])
    assert not (roots[0] / ".agent/plans").exists()


def test_imported_issue_reference_reuses_changed_title(fleet: tuple) -> None:
    roots, _worktree, control, runner, bases = fleet
    url = "https://github.com/ray-manaloto/dotfiles/issues/1800"
    (roots[0] / "task_plan.md").write_text(f"# same-lane\n- [ ] tracked issue {url}\n")
    control["issues"] = [
        [
            {
                "number": 1800,
                "title": "different title",
                "body": "unrelated old prose",
                "html_url": url,
            }
        ]
    ]
    snapshot = registry.collect(roots, runner=runner, bases=bases)
    intentions = registry.issue_plan(snapshot, runner=runner)["intentions"]
    duplicates = [
        intent
        for intent in intentions
        if any("duplicate-" in sid for sid in intent["member_session_ids"])
    ]
    assert len(duplicates) == 2
    assert all(
        intent["action"] == "reuse" and intent["issue_url"] == url
        for intent in duplicates
    )


def test_public_cli_modes_and_inventory_failure_rc(
    fleet: tuple, capsys: pytest.CaptureFixture[str]
) -> None:
    roots, _worktree, control, runner, bases = fleet
    parser = setup_parser()
    args = parser.parse_args(
        [
            "lane-cards",
            "--json",
            "--repo-root",
            str(roots[0]),
            "--repo-root",
            str(roots[1]),
        ]
    )
    control["rc"] = 1
    assert registry.main(args, roots[0], runner=runner, bases=bases) == 2
    assert json.loads(capsys.readouterr().out)["omissions"]
    with pytest.raises(SystemExit):
        parser.parse_args(["lane-cards", "--json", "--write"])
    assert not (roots[0] / ".agent/lanes").exists()


def test_nameless_cards_are_provider_qualified_and_coordinator_is_not_invented(
    fleet: tuple,
) -> None:
    roots, _worktree, _control, runner, bases = fleet
    snapshot = registry.collect(roots, runner=runner, bases=bases)
    written = registry.write_cards(
        snapshot, state_root=roots[1], authorize=lambda: "coordinator"
    )
    names = {Path(path).name for path in written["written"]}
    assert "claude-shared-session-id.md" in names
    assert "codex-shared-session-id.md" in names
    card = (roots[1] / ".agent/lanes/claude-shared-session-id.md").read_text()
    assert "Role: unknown; ownership: unknown" in card
    assert "Role: coordinator" not in card


def test_public_topology_failure_retains_other_repository(fleet: tuple) -> None:
    roots, _worktree, _control, runner, bases = fleet

    def failing_git(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if argv[:3] == ["git", "-C", str(roots[1])]:
            return subprocess.CompletedProcess(argv, 1, "", "controlled Git failure")
        return runner(argv, **kwargs)

    snapshot = registry.collect(roots, runner=failing_git, bases=bases)
    assert [repo["github_repo"] for repo in snapshot["repositories"]] == [
        "ray-manaloto/dotfiles"
    ]
    assert any(
        "repository inventory unavailable" in omission
        for omission in snapshot["omissions"]
    )
    assert any(
        row["repo_key"] == "ray-manaloto/dotfiles" for row in snapshot["sessions"]
    )


def test_ordinary_lane_identity_only_collapses_with_an_explicit_predecessor(
    fleet: tuple,
) -> None:
    roots, _worktree, _control, runner, bases = fleet
    snapshot = registry.collect(roots, runner=runner, bases=bases)
    lanes = [row for row in snapshot["sessions"] if row["name"] == "same-lane"]
    initial = registry.collapse_chains(lanes)
    assert len(initial) == 2
    lanes[1]["lineage"] = [
        {
            "predecessor": "claude:duplicate-one",
            "successor": "claude:duplicate-two",
            "evidence_ref": "verified-launch-record",
        }
    ]
    collapsed = registry.collapse_chains(lanes)
    assert len(collapsed) == 1
    assert set(collapsed[0]["member_session_ids"]) == {
        "claude:duplicate-one",
        "claude:duplicate-two",
    }


def test_native_millisecond_inventory_chooses_latest_chain_member(fleet: tuple) -> None:
    roots, _worktree, control, runner, bases = fleet
    rows = control["rows"]
    assert isinstance(rows, list)
    old, new = rows[0], rows[1]
    old["sessionId"] = "zzzz-old-coordinator"
    new["sessionId"] = "aaaa-new-coordinator"
    old["startedAt"] = 1791201600000
    new["startedAt"] = 1791203400000
    snapshot = registry.collect(roots, runner=runner, bases=bases)
    chain = next(
        chain
        for chain in snapshot["chains"]
        if chain["stable_key"] == "ray-manaloto/dotfiles:coordinator"
    )
    assert chain["display_session_id"] == "claude:aaaa-new-coordinator"
    member = next(
        row
        for row in snapshot["sessions"]
        if row["session_id"] == "aaaa-new-coordinator"
    )
    assert member["started_at"] == "2026-10-05T12:30:00+00:00"


def test_missing_codex_directory_is_inventory_unknown(fleet: tuple) -> None:
    roots, _worktree, _control, runner, bases = fleet
    assert bases.codex is not None
    (bases.codex / "source.jsonl").unlink()
    bases.codex.rmdir()
    snapshot = registry.collect(roots, runner=runner, bases=bases)
    assert (
        "codex inventory unavailable: sessions directory absent"
        in snapshot["omissions"]
    )
    assert any(row["provider"] == "claude" for row in snapshot["sessions"])


@pytest.mark.parametrize("explicit_claims", [True, False])
def test_lane_cards_public_write_uses_codex_claim_and_claude_handback(
    fleet: tuple,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    explicit_claims: bool,
) -> None:
    roots, worktree, _control, runner, bases = fleet
    jobs = tmp_path / "isolated-jobs"
    claims = (
        tmp_path / "claims"
        if explicit_claims
        else roots[0] / handoff_inbox.COORDINATOR_CLAIMS
    )
    caller = "lane-card-codex-native-id"
    monkeypatch.delenv(handoff_inbox.SESSION_ENV, raising=False)
    monkeypatch.setenv(handoff_inbox.CODEX_ENV, caller)
    handoff_inbox.coordinator_claim(
        {handoff_inbox.CODEX_ENV: caller},
        jobs,
        claims_dir=claims,
        takeover=("dotfiles-card-claim.coordinator", "none"),
        now=lambda: STAMP,
    )
    flags = ["--claims-dir", str(claims)] if explicit_claims else []
    args = setup_parser().parse_args(
        [
            "lane-cards",
            "--write",
            "--repo-root",
            str(roots[0]),
            "--repo-root",
            str(roots[1]),
            "--jobs-dir",
            str(jobs),
            *flags,
        ]
    )
    assert registry.main(args, worktree, runner=runner, bases=bases) == 0
    cards = list((roots[0] / ".agent/lanes").glob("*.md"))
    assert cards
    before = {path: path.read_bytes() for path in cards}
    successor = "claude-card-successor"
    job = jobs / successor[:8] / "state.json"
    job.parent.mkdir(parents=True)
    job.write_text(
        json.dumps(
            {
                "sessionId": successor,
                "name": "dotfiles-card-handback.coordinator",
                "createdAt": "2099-01-01T00:00:00Z",
                "state": "done",
            }
        )
    )
    assert registry.main(args, worktree, runner=runner, bases=bases) == 2
    assert {path: path.read_bytes() for path in cards} == before
