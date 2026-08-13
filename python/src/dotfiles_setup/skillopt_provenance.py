# Copyright (c) 2026 Raymond Manaloto
"""Present-day replay evidence for three landed session-review fixes."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dotfiles_setup.process_env import fnox_command, fnox_parent_env

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

REPOSITORY = "ray-manaloto/dotfiles"
SCHEMA = "dotfiles.skillopt-present-day-replay.v1"
MANIFEST = Path("skillopt/provenance/session-review-history.json")
REPLAY_DIR = Path("skillopt/provenance/replays")
REPLAY_RECEIPTS = (
    "unknown-omission-53101bf577f7cbe3b0a63f5dbcf722994621a3ff4903ba88aae2782682008abb.json",
    "open-disposition-e86663ab2a62b5290cabf2d22a99d30bafe6db2a21834fb590caa05a318df1cb.json",
    "form-pairing-7ab92796945bd677956e1a245a80eb2780cfc2f3e62cf95d07b90c0bdce80591.json",
)
LOGGER = logging.getLogger(__name__)
_MESSAGES = {
    "timeout": "GitHub provenance readback timed out",
    "spawn": "GitHub provenance readback could not start",
    "readback": "GitHub provenance readback failed",
    "json": "GitHub provenance response was invalid",
    "object": "GitHub provenance response was not an object",
    "commit": "GitHub commit or tree identity does not match",
    "blob_response": "GitHub blob response was invalid",
    "blob": "GitHub test blob or node does not match",
    "pr": "GitHub merged pull request binding does not match",
    "anchor": "hostile mutation anchor is not exact",
    "inventory": "provenance inventory is missing or tampered",
}


@dataclass(frozen=True, slots=True)
class Fix:
    """Immutable GitHub object identity and a present-day hostile replay."""

    identity: str
    commit: str
    tree: str
    pull: int
    path: str
    git_blob: str
    blob_sha256: str
    node: str
    old: str
    new: str


FIXES = (
    Fix(
        "unknown-omission",
        "9ad895823768e6c21db2b2e66e42784818979b91",
        "9968b728dbda41df9376b3e728b6460efcfd7147",
        728,
        "tests/test_session_ledger.py",
        "5ed89d0e7898813419bcb7e3bb094a2da3c70b18",
        "e0e63796a3e902cc1ff580c8c09f096d5781500adc8d807fb273896c37ba1805",
        "test_unknown_record_makes_coverage_incomplete_not_clean",
        "        if record_type not in known:\n"
        "            acc.omissions.append(\n"
        '                f"{source_id}:{line}: unknown Codex record '
        '{record_type!r}"\n'
        "            )\n",
        "        if record_type not in known:\n            pass\n",
    ),
    Fix(
        "open-disposition",
        "8afffede4aa26b7b421116f2f9635356fd210122",
        "47faa5071800b5bbbbfc37fe5f505cab21d0b650",
        732,
        "tests/test_session_ledger.py",
        "d090a2e76decfbb5298ca0040e4d9ce27e872fc5",
        "6dbfc831f12cbe8ffe79fe8c051ccd34b1c4a9d7ee7079fcd3c24376d8f000fc",
        "test_persisted_disposition_never_converges_or_authorizes_complete",
        "        return False\n\n    @property\n    def audit_evidence_complete",
        "        return True\n\n    @property\n    def audit_evidence_complete",
    ),
    Fix(
        "form-pairing",
        "4773dc08a77ce3205c71090192ddc90cee41d114",
        "eccff2593ee14f00b1a499e297c730f131ff24f5",
        740,
        "tests/test_session_ledger.py",
        "603a5486e03a744d4534074fcaa4760dfdb98bdf",
        "6eca8d41a137b479ca58c77d55d3bab204bd60a1153e2d1bf869a82762ff12e3",
        "test_native_root_custom_form_carrier_requires_exact_call_and_turn_pairing",
        'response_type in {"function_call_output", "custom_tool_call_output"}',
        'response_type == "function_call_output"',
    ),
)


class ProvenanceError(RuntimeError):
    """Bounded failure with no response body or credential values."""


def digest(data: bytes) -> str:
    """Return SHA-256 hex."""
    return hashlib.sha256(data).hexdigest()


def _error(message: str) -> ProvenanceError:
    return ProvenanceError(message)


def manifest_bytes() -> bytes:
    """Return canonical immutable source inventory, excluding execution claims."""
    data = {
        "schema": SCHEMA,
        "evidence_kind": "present_day_replay",
        "not_historical_execution": True,
        "repository": REPOSITORY,
        "verified_replay_receipts": [
            {
                "path": str(REPLAY_DIR / name),
                "sha256": name.removesuffix(".json").rsplit("-", 1)[1],
            }
            for name in REPLAY_RECEIPTS
        ],
        "fixes": [
            (
                {
                    key: value
                    for key, value in asdict(fix).items()
                    if key not in {"old", "new"}
                }
                | {
                    "authority_status": "verified_replay",
                    "adoption_eligible": False,
                }
            )
            | {"mutation_patch_sha256": digest((fix.old + "\0" + fix.new).encode())}
            for fix in FIXES
        ],
    }
    return (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()


def export(repo: Path) -> None:
    """Write canonical manifest and independent compiled baseline digest."""
    target = repo / MANIFEST
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(manifest_bytes())
    target.with_suffix(".sha256").write_text(digest(manifest_bytes()) + "\n")


def github_fetch(argv: Sequence[str]) -> bytes:
    """Read one GitHub endpoint through noninteractive fnox without body logging."""
    try:
        result = subprocess.run(
            fnox_command(("gh", "api", *argv)),
            capture_output=True,
            check=False,
            timeout=60,
            env=fnox_parent_env(),
        )
    except subprocess.TimeoutExpired as exc:
        raise _error(_MESSAGES["timeout"]) from exc
    except OSError as exc:
        raise _error(_MESSAGES["spawn"]) from exc
    if result.returncode != 0 or result.stderr:
        raise _error(_MESSAGES["readback"])
    return result.stdout


def _json_fetch(
    fetch: Callable[[Sequence[str]], bytes], endpoint: str
) -> dict[str, object]:
    try:
        value = json.loads(fetch((endpoint,)))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise _error(_MESSAGES["json"]) from exc
    if not isinstance(value, dict):
        raise _error(_MESSAGES["object"])
    return value


def verify_live(fetch: Callable[[Sequence[str]], bytes] = github_fetch) -> None:
    """Bind commit, tree, exact path/blob and merged PR base/head."""
    for fix in FIXES:
        commit = _json_fetch(fetch, f"repos/{REPOSITORY}/git/commits/{fix.commit}")
        tree = commit.get("tree")
        if (
            commit.get("sha") != fix.commit
            or not isinstance(tree, dict)
            or tree.get("sha") != fix.tree
        ):
            raise _error(_MESSAGES["commit"])
        content = _json_fetch(
            fetch, f"repos/{REPOSITORY}/contents/{fix.path}?ref={fix.commit}"
        )
        try:
            encoded = "".join(str(content["content"]).split())
            blob = base64.b64decode(encoded, validate=True)
        except (KeyError, ValueError) as exc:
            raise _error(_MESSAGES["blob_response"]) from exc
        if (
            content.get("sha") != fix.git_blob
            or digest(blob) != fix.blob_sha256
            or f"def {fix.node}(" not in blob.decode()
        ):
            raise _error(_MESSAGES["blob"])
        pr = _json_fetch(fetch, f"repos/{REPOSITORY}/pulls/{fix.pull}")
        base = pr.get("base")
        if (
            pr.get("merged") is not True
            or pr.get("merge_commit_sha") != fix.commit
            or not isinstance(base, dict)
            or not isinstance(base.get("repo"), dict)
            or base["repo"].get("full_name") != REPOSITORY
        ):
            raise _error(_MESSAGES["pr"])


def _run(checkout: Path, fix: Fix) -> dict[str, object]:
    argv = (
        "uv",
        "run",
        "--project",
        "python",
        "pytest",
        f"{fix.path}::{fix.node}",
        "-q",
    )
    started = time.time_ns()
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in {"GH_TOKEN", "GITHUB_TOKEN"}
    }
    environment["UV_CACHE_DIR"] = str(checkout / ".uv-cache")
    result = subprocess.run(
        argv,
        cwd=checkout,
        capture_output=True,
        check=False,
        timeout=180,
        env=environment,
    )
    return {
        "argv_sha256": digest("\0".join(argv).encode()),
        "runner": "uv+pytest",
        "python": sys.version.split()[0],
        "started_ns": started,
        "ended_ns": time.time_ns(),
        "rc": result.returncode,
        "stdout_bytes": len(result.stdout),
        "stdout_sha256": digest(result.stdout),
        "stderr_bytes": len(result.stderr),
        "stderr_sha256": digest(result.stderr),
    }


def replay(repo: Path) -> None:
    """Re-execute clean and hostile controls without rewriting committed receipts."""
    for fix in FIXES:
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            archive = subprocess.run(
                ("git", "archive", fix.commit),
                cwd=repo,
                capture_output=True,
                check=True,
            ).stdout
            tar = checkout / "source.tar"
            tar.write_bytes(archive)
            shutil.unpack_archive(tar, checkout)
            tar.unlink()
            positive = _run(checkout, fix)
            source = checkout / "python/src/dotfiles_setup/session_ledger.py"
            text = source.read_text()
            if text.count(fix.old) != 1:
                raise _error(_MESSAGES["anchor"])
            source.write_text(text.replace(fix.old, fix.new))
            negative = _run(checkout, fix)
            if positive["rc"] != 0 or negative["rc"] == 0:
                message = (
                    f"present-day replay did not discriminate: {fix.identity} "
                    f"positive={positive['rc']} hostile={negative['rc']}"
                )
                raise _error(message)


def _verify_receipt(replay_root: Path, name: str, fix: Fix) -> None:
    raw = (replay_root / name).read_bytes()
    if digest(raw) != name.removesuffix(".json").rsplit("-", 1)[1]:
        raise _error(_MESSAGES["inventory"])
    try:
        receipt = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise _error(_MESSAGES["inventory"]) from exc
    keys = {
        "schema",
        "evidence_kind",
        "not_historical_execution",
        "repository",
        "source_commit",
        "source_tree",
        "test_path",
        "test_blob_sha256",
        "test_node",
        "mutation_patch_sha256",
        "positive",
        "hostile_mutation",
    }
    if not isinstance(receipt, dict) or set(receipt) != keys:
        raise _error(_MESSAGES["inventory"])
    positive = receipt["positive"]
    hostile = receipt["hostile_mutation"]
    if not isinstance(positive, dict) or not isinstance(hostile, dict):
        raise _error(_MESSAGES["inventory"])
    common = (
        receipt["schema"] == SCHEMA
        and receipt["evidence_kind"] == "present_day_replay"
        and receipt["not_historical_execution"] is True
        and receipt["repository"] == REPOSITORY
        and receipt["source_commit"] == fix.commit
        and receipt["source_tree"] == fix.tree
        and receipt["test_path"] == fix.path
        and receipt["test_blob_sha256"] == fix.blob_sha256
        and receipt["test_node"] == fix.node
        and receipt["mutation_patch_sha256"]
        == digest((fix.old + "\0" + fix.new).encode())
        and positive.get("outcome") == "PASSED"
        and positive.get("rc") == 0
        and hostile.get("outcome") == "REJECTED"
        and isinstance(hostile.get("rc"), int)
        and hostile["rc"] != 0
        and positive.get("argv_sha256") == hostile.get("argv_sha256")
        and positive.get("runner") == hostile.get("runner")
        and positive.get("python") == hostile.get("python")
        and positive.get("started_ns", 0) < positive.get("ended_ns", 0)
        and positive.get("ended_ns", 0) <= hostile.get("started_ns", 0)
        and hostile.get("started_ns", 0) < hostile.get("ended_ns", 0)
    )
    if not common:
        raise _error(_MESSAGES["inventory"])


def verify_local(repo: Path) -> None:
    """Fail closed on transition/deletion/tamper of manifest inventory."""
    target = repo / MANIFEST
    if (
        not target.is_file()
        or target.read_bytes() != manifest_bytes()
        or target.with_suffix(".sha256").read_text() != digest(manifest_bytes()) + "\n"
    ):
        raise _error(_MESSAGES["inventory"])
    replay_root = repo / REPLAY_DIR
    files = tuple(sorted(path.name for path in replay_root.glob("*.json")))
    if files != tuple(sorted(REPLAY_RECEIPTS)):
        raise _error(_MESSAGES["inventory"])
    by_identity: dict[str, str] = {
        name.rsplit("-", 1)[0]: name for name in REPLAY_RECEIPTS
    }
    if set(by_identity) != {fix.identity for fix in FIXES}:
        raise _error(_MESSAGES["inventory"])
    for fix in FIXES:
        _verify_receipt(replay_root, by_identity[fix.identity], fix)


def main(argv: list[str] | None = None) -> int:
    """Write/replay optionally, then verify local and live authority."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args(argv)
    repo = Path.cwd()
    try:
        if args.write:
            export(repo)
        if args.replay:
            replay(repo)
        verify_local(repo)
        verify_live()
    except OSError, ProvenanceError, subprocess.SubprocessError:
        LOGGER.log(logging.ERROR, "skillopt-provenance-check failed")
        return 1
    LOGGER.info("verified %d present-day replay sources", len(FIXES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
