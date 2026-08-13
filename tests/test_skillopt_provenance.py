# Copyright (c) 2026 Raymond Manaloto
"""Controls for published SkillOpt source and present-day replay evidence."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from dotfiles_setup import skillopt_provenance as subject

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence


def _copy_replay(repo: Path) -> Path:
    source = Path(__file__).parents[1] / subject.REPLAY_DIR / subject.REPLAY_RECEIPT
    target = repo / subject.REPLAY_DIR / subject.REPLAY_RECEIPT
    target.parent.mkdir(parents=True)
    target.write_bytes(source.read_bytes())
    return target


def _fetch() -> Callable[[Sequence[str]], bytes]:
    def fetch(argv: Sequence[str]) -> bytes:
        endpoint = argv[0]
        for fix in subject.FIXES:
            if endpoint.endswith(f"git/commits/{fix.commit}"):
                return json.dumps(
                    {"sha": fix.commit, "tree": {"sha": fix.tree}}
                ).encode()
            if endpoint.endswith(f"contents/{fix.path}?ref={fix.commit}"):
                blob = subject.subprocess.run(
                    ["git", "show", f"{fix.commit}:{fix.path}"],
                    check=True,
                    capture_output=True,
                ).stdout
                return json.dumps(
                    {"sha": fix.git_blob, "content": base64.b64encode(blob).decode()}
                ).encode()
            if endpoint.endswith(f"pulls/{fix.pull}"):
                return json.dumps(
                    {
                        "merged": True,
                        "merge_commit_sha": fix.commit,
                        "base": {"repo": {"full_name": subject.REPOSITORY}},
                    }
                ).encode()
        message = "unexpected endpoint"
        raise AssertionError(message)

    return fetch


def test_manifest_is_stable_and_all_live_objects_bind(tmp_path: Path) -> None:
    subject.export(tmp_path)
    _copy_replay(tmp_path)
    first = (tmp_path / subject.MANIFEST).read_bytes()
    subject.export(tmp_path)
    assert (tmp_path / subject.MANIFEST).read_bytes() == first
    subject.verify_local(tmp_path)
    subject.verify_live(_fetch())


def test_only_real_replay_is_verified_and_none_is_adoption_evidence() -> None:
    payload = json.loads(subject.manifest_bytes())
    assert [row["authority_status"] for row in payload["fixes"]] == [
        "verified_replay",
        "object_provenance_only",
        "object_provenance_only",
    ]
    assert all(row["adoption_eligible"] is False for row in payload["fixes"])
    assert payload["not_historical_execution"] is True


@pytest.mark.parametrize(
    "field",
    [
        "repository",
        "commit_sha",
        "tree_sha",
        "test_path",
        "test_blob_sha256",
        "authority_status",
    ],
)
def test_coordinated_manifest_and_digest_tamper_fails(
    tmp_path: Path, field: str
) -> None:
    subject.export(tmp_path)
    target = tmp_path / subject.MANIFEST
    payload = json.loads(target.read_text())
    if field == "repository":
        payload[field] = "attacker/repo"
    else:
        payload["fixes"][0][field] = "f" * 40
    changed = (
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    target.write_bytes(changed)
    target.with_suffix(".sha256").write_text(subject.digest(changed) + "\n")
    with pytest.raises(subject.ProvenanceError, match="tampered"):
        subject.verify_local(tmp_path)


def test_wrong_reachable_tree_and_blob_fail(tmp_path: Path) -> None:
    subject.export(tmp_path)

    def wrong(argv: Sequence[str]) -> bytes:
        if "git/commits/" in argv[0]:
            fix = subject.FIXES[0]
            return json.dumps({"sha": fix.commit, "tree": {"sha": "f" * 40}}).encode()
        return _fetch()(argv)

    with pytest.raises(subject.ProvenanceError, match="commit or tree"):
        subject.verify_live(wrong)


def test_api_failure_is_bounded_without_body_or_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = b"ghp_secret response body"

    def fail(
        *args: object, **kwargs: object
    ) -> subject.subprocess.CompletedProcess[bytes]:
        del args, kwargs
        return subject.subprocess.CompletedProcess([], 1, secret, secret)

    monkeypatch.setattr(subject.subprocess, "run", fail)
    with pytest.raises(subject.ProvenanceError, match="readback failed") as caught:
        subject.github_fetch(("repos/ray-manaloto/dotfiles/pulls/1",))
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("mutation", ["delete", "tamper", "extra"])
def test_replay_inventory_mutations_fail(tmp_path: Path, mutation: str) -> None:
    subject.export(tmp_path)
    target = _copy_replay(tmp_path)
    if mutation == "delete":
        target.unlink()
    elif mutation == "tamper":
        target.write_bytes(target.read_bytes() + b" ")
    else:
        (target.parent / "fabricated.json").write_text("{}\n")
    with pytest.raises(subject.ProvenanceError, match="inventory"):
        subject.verify_local(tmp_path)
