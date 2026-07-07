"""Apply an autofix.ci artifact locally (`mise run autofix-apply -- <run-id>`).

The autofix workflow uploads its computed fixes as an ``autofix.ci``
artifact (``autofix.json``: base64 file contents keyed by repo path).
Normally the autofix.ci App pushes them back to the PR branch; when the
App cannot (uninstalled, revoked, outage — the historical
``500 … not installed`` mode, issue #94), this command replays the
documented manual recipe reproducibly: download the run's artifact,
decode every addition, write it into the working tree. Committing stays
with the operator (clean-git-state applies).
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_DOWNLOAD_TIMEOUT_S = 300.0


def apply_autofix_artifact(artifact_json: str, repo_root: Path) -> list[str]:
    """Write every addition from an autofix.json payload; returns the paths.

    Raises ValueError on payloads that do not match the autofix.ci v1
    shape — fail loud rather than partially applying.
    """
    data = json.loads(artifact_json)
    changes = data.get("changes", data)
    additions = changes.get("additions")
    if data.get("version") != 1 or additions is None:
        msg = "unrecognized autofix.json payload (expected version 1 with additions)"
        raise ValueError(msg)
    written: list[str] = []
    for add in additions:
        rel = Path(add["path"])
        if rel.is_absolute() or ".." in rel.parts:
            msg = f"refusing suspicious artifact path: {add['path']}"
            raise ValueError(msg)
        target = repo_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(add["contents"]))
        written.append(add["path"])
    if changes.get("deletions"):
        # Never observed in this repo; refuse rather than guess semantics.
        msg = "artifact contains deletions — apply those by hand"
        raise ValueError(msg)
    return written


def autofix_apply_main(run_id: str, repo_root: Path) -> int:
    """Download the run's autofix.ci artifact and apply it to the tree."""
    with tempfile.TemporaryDirectory() as tmp:
        res = subprocess.run(
            ["gh", "run", "download", run_id, "--name", "autofix.ci", "--dir", tmp],
            capture_output=True,
            text=True,
            check=False,
            timeout=_DOWNLOAD_TIMEOUT_S,
        )
        if res.returncode != 0:
            sys.stderr.write(f"gh run download failed: {res.stderr.strip()}\n")
            return 1
        artifact = Path(tmp) / "autofix.json"
        if not artifact.exists():
            sys.stderr.write("no autofix.json in the downloaded artifact\n")
            return 1
        try:
            written = apply_autofix_artifact(artifact.read_text(), repo_root)
        except (ValueError, json.JSONDecodeError, KeyError) as exc:
            sys.stderr.write(f"artifact not applied: {exc}\n")
            return 1
    for path in written:
        sys.stdout.write(f"applied {path}\n")
    sys.stdout.write(
        f"autofix-apply: {len(written)} file(s) written — review, stage, commit\n"
    )
    return 0
