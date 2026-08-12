# Copyright (c) 2026 Raymond Manaloto
"""Mutation/control tests for the trusted session-review receipt runner."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest
from dotfiles_setup import session_gate, session_ledger


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    return repo


def test_runner_generates_nonce_and_atomically_attests_real_command(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    carrier = repo / "carrier.py"
    carrier.write_text("PREVENTION = True\n")
    context_path = session_gate.initialize(repo, "run-1")
    context = json.loads(context_path.read_text())
    assert len(context["nonce"]) == 64

    receipt_path = session_gate.run_command(
        repo,
        "run-1",
        session_gate.GateCommand("gate", ["mise", "--version"], carrier, timeout=30),
    )
    receipt = json.loads(receipt_path.read_text())
    assert receipt["status"] == "ATTESTED"
    assert receipt["rc"] == 0
    assert receipt["nonce"] == context["nonce"]
    assert (
        receipt["artifact_sha256"] == hashlib.sha256(carrier.read_bytes()).hexdigest()
    )
    assert "stdout" not in receipt
    assert "stderr" not in receipt


def test_runner_records_failed_mutation_but_loader_cannot_accept_it(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    carrier = repo / "carrier.py"
    carrier.write_text("PREVENTION = True\n")
    session_gate.initialize(repo, "run-red")
    receipt_path = session_gate.run_command(
        repo,
        "run-red",
        session_gate.GateCommand(
            "mutation",
            ["mise", "definitely-not-a-command"],
            carrier,
            timeout=30,
        ),
    )
    receipt = json.loads(receipt_path.read_text())
    assert receipt["status"] == "FAILED"
    assert receipt["rc"] != 0


def test_github_runner_uses_fnox_gh_and_never_persists_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    session_gate.initialize(repo, "run-gh")
    body = json.dumps(
        {"number": 7, "html_url": "https://github.com/example/repo/issues/7"}
    ).encode()

    def fake_run(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        del kwargs
        assert argv[:5] == ["fnox", "exec", "--", "gh", "api"]
        return subprocess.CompletedProcess(argv, 0, body, b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    receipt_path = session_gate.run_github_readback(
        repo,
        "run-gh",
        "https://api.github.com/repos/example/repo/issues/7",
    )
    receipt_text = receipt_path.read_text()
    receipt = json.loads(receipt_text)
    assert receipt["status"] == "ATTESTED"
    assert "example/repo/issues/7" in receipt["html_url"]
    assert '"number"' not in receipt_text


def test_offline_forgery_matching_schema_but_not_runner_state_is_rejected(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path)
    session_gate.initialize(repo, "real-run")
    forged = repo / "forged.json"
    forged.write_text("[]")
    with pytest.raises(FileNotFoundError):
        session_ledger.load_dispositions(
            forged,
            repo_root=repo,
            run_id="attacker-chosen-run",
        )


def _finalize_spec(repo: Path) -> Path:
    carrier = repo / "python" / "src" / "dotfiles_setup" / "pr.py"
    carrier.parent.mkdir(parents=True)
    carrier.write_text("PREVENTION = True\n")
    spec = repo / "finalize.json"
    spec.write_text(
        json.dumps(
            {
                "schema": "session-review.finalize.v1",
                "prevention_id": "credential-launcher",
                "api_url": "https://api.github.com/repos/example/repo/issues/7",
            }
        )
    )
    return spec


def test_finalize_temporarily_completes_only_from_same_process_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    spec = _finalize_spec(repo)
    sentinel = json.dumps(
        {
            "schema": "session-review.mutant-armed.v1",
            "prevention_id": "credential-launcher",
            "mutant": "ship-push-fnox-boundary-missing",
            "status": "ARMED",
            "target": "python/src/dotfiles_setup/pr.py",
            "before_sha256": "c" * 64,
            "after_sha256": "d" * 64,
            "gate_argv": ["mise", "run", "session-review-focused-gate"],
            "gate_rc": 1,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    results = iter([(1, sentinel, "a" * 64), (0, b"", "b" * 64)])

    def fake_execute(argv: list[str], *, timeout: int) -> tuple[int, bytes, str]:
        del argv, timeout
        return next(results)

    monkeypatch.setattr(session_gate, "_execute_private", fake_execute)
    body = json.dumps(
        {
            "number": 7,
            "html_url": "https://github.com/example/repo/issues/7",
            "body": "tracked prevention",
        }
    ).encode()

    def fake_github(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        del kwargs
        return subprocess.CompletedProcess(argv, 0, body, b"")

    monkeypatch.setattr(subprocess, "run", fake_github)
    result = session_gate.finalize(repo, spec)
    assert result.status == "TEMPORARILY_COMPLETE"
    assert result.finding_ids == ("credential-launcher",)
    assert not (repo / ".agent").exists()


def test_finalize_red_control_rejects_wrong_mutation_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    spec = _finalize_spec(repo)
    results = iter([(0, b"", "a" * 64), (0, b"", "b" * 64)])

    def fake_execute(argv: list[str], *, timeout: int) -> tuple[int, bytes, str]:
        del argv, timeout
        return next(results)

    def fake_github(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        del kwargs
        return subprocess.CompletedProcess(argv, 0, b"{}", b"")

    monkeypatch.setattr(session_gate, "_execute_private", fake_execute)
    monkeypatch.setattr(subprocess, "run", fake_github)
    with pytest.raises(RuntimeError, match="unexpected status"):
        session_gate.finalize(repo, spec)


@pytest.mark.parametrize(
    "mutation",
    [
        {"prevention_id": "unknown"},
        {"prevention_id": "credential-launcher", "argv": ["mise", "--help"]},
        {"prevention_id": "credential-launcher", "expected_rc": 0},
    ],
)
def test_finalize_rejects_caller_command_or_unknown_prevention(
    tmp_path: Path, mutation: dict[str, object]
) -> None:
    repo = _repo(tmp_path)
    spec = _finalize_spec(repo)
    payload = json.loads(spec.read_text())
    payload.update(mutation)
    spec.write_text(json.dumps(payload))
    if mutation["prevention_id"] == "unknown":
        with pytest.raises(ValueError, match="registered prevention_id"):
            session_gate.finalize(repo, spec)
    else:
        with pytest.raises(ValueError, match="caller-controlled fields"):
            session_gate.finalize(repo, spec)


@pytest.mark.parametrize(
    "url",
    [
        "https://api.github.com/repos/example/repo",
        "https://api.github.com/repos/example/repo/pulls/7",
        "https://api.github.com/repos/example/repo/issues",
        "https://evil.example/repos/example/repo/issues/7",
    ],
)
def test_finalize_rejects_non_issue_endpoints(tmp_path: Path, url: str) -> None:
    repo = _repo(tmp_path)
    spec = _finalize_spec(repo)
    payload = json.loads(spec.read_text())
    payload["api_url"] = url
    spec.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="issue endpoint"):
        session_gate.finalize(repo, spec)


def test_critic_replay_rejects_same_registered_mutation_and_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    spec = _finalize_spec(repo)
    original = session_gate.PREVENTIONS["credential-launcher"]
    monkeypatch.setitem(
        session_gate.PREVENTIONS,
        "credential-launcher",
        session_gate.PreventionRegistration(
            original.carrier,
            "session-review-focused-gate",
            "session-review-focused-gate",
            original.mutant_name,
            original.target,
            original.required_token,
            original.required_count,
        ),
    )
    with pytest.raises(ValueError, match="must be distinct"):
        session_gate.finalize(repo, spec)


def test_critic_replay_rejects_nonzero_mutation_without_named_armed_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    spec = _finalize_spec(repo)
    results = iter([(1, b"not armed\n", "a" * 64), (0, b"", "b" * 64)])

    def fake_execute(argv: list[str], *, timeout: int) -> tuple[int, bytes, str]:
        del argv, timeout
        return next(results)

    def fake_github(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        del kwargs
        return subprocess.CompletedProcess(argv, 0, b"{}", b"")

    monkeypatch.setattr(session_gate, "_execute_private", fake_execute)
    monkeypatch.setattr(subprocess, "run", fake_github)
    with pytest.raises(ValueError, match="typed armed sentinel"):
        session_gate.finalize(repo, spec)


def test_mutation_is_killed_when_no_registered_edit_occurs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _repo(tmp_path)
    target = repo / "python" / "src" / "dotfiles_setup" / "pr.py"
    target.parent.mkdir(parents=True)
    target.write_text("no registered carrier token\n")
    monkeypatch.setenv("MISE_PROJECT_ROOT", str(repo))
    assert session_gate.mutation_sentinel("credential-launcher") == 2


def test_credential_launcher_prevention_replays_historical_uncredentialed_push(
    tmp_path: Path,
) -> None:
    """The hostile arm must reproduce ship's real pre-fnox push boundary."""
    root = Path(__file__).parent.parent
    registration = session_gate.PREVENTIONS["credential-launcher"]
    assert session_gate.prevention_check(root) == 0
    assert registration.carrier == "python/src/dotfiles_setup/pr.py"
    assert registration.target == registration.carrier
    assert registration.mutant_name == "ship-push-fnox-boundary-missing"

    candidate = tmp_path / "candidate"
    for registered in session_gate.PREVENTIONS.values():
        target = candidate / registered.target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / registered.target).read_bytes())
    target = candidate / registration.target
    target.write_text(
        target.read_text().replace(
            registration.required_token,
            registration.mutant_replacement,
            1,
        )
    )

    assert '_stream(["git", "push", "-u", "origin", branch], cwd=workspace)' in (
        target.read_text()
    )
    assert session_gate.prevention_check(candidate) == 1


def test_normal_prevention_gate_accepts_real_tree_and_rejects_mutant(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parent.parent
    assert session_gate.prevention_check(root) == 0
    candidate = tmp_path / "candidate"
    for registration in session_gate.PREVENTIONS.values():
        target = candidate / registration.target
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((root / registration.target).read_text())
    registration = session_gate.PREVENTIONS["git-hook-contamination"]
    target = candidate / registration.target
    target.write_text(
        target.read_text().replace(registration.required_token, "removed", 1)
    )
    assert session_gate.prevention_check(candidate) == 1


def test_git_hook_prevention_targets_the_post_hook_child_boundary() -> None:
    """The registry must mutate the layer Git cannot re-poison afterwards."""
    registration = session_gate.PREVENTIONS["git-hook-contamination"]
    assert registration.carrier == "python/src/dotfiles_setup/process_env.py"
    assert registration.target == registration.carrier
    assert registration.required_count == 1
    root = Path(__file__).parent.parent
    assert (root / registration.target).read_text().count(
        registration.required_token
    ) == registration.required_count
