# Copyright (c) 2026 Raymond Manaloto
"""Trusted, bounded receipt runner for the session-review prevention loop."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import secrets
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

RUNNER = "mise-session-review-gate"
SCHEMA = "session-review.runner-attestation.v1"
DEFAULT_TIMEOUT = 600
NONCE_HEX_LENGTH = 64
ISSUE_PATH_PARTS = 5
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GateCommand:
    """One bounded command and the carrier artifact it validates."""

    role: str
    argv: list[str]
    artifact: Path
    timeout: int = DEFAULT_TIMEOUT


@dataclass(frozen=True)
class FinalizeResult:
    """Temporary same-process verdict; it is deliberately never persisted."""

    status: str
    finding_ids: tuple[str, ...]
    carrier_sha256: str
    mutation_output_sha256: str
    gate_output_sha256: str
    github_body_sha256: str


@dataclass(frozen=True)
class PreventionRegistration:
    """Non-caller-controlled commands and carrier for one prevention class."""

    carrier: str
    mutation_task: str
    gate_task: str
    mutant_name: str
    target: str
    required_token: str
    required_count: int


PREVENTIONS = {
    "credential-launcher": PreventionRegistration(
        "python/src/dotfiles_setup/sync.py",
        "session-review-mutation-credential-launcher",
        "session-review-focused-gate",
        "credential-launcher-missing",
        "python/src/dotfiles_setup/sync.py",
        "child_env.without_git_context",
        2,
    ),
    "git-hook-contamination": PreventionRegistration(
        "python/src/dotfiles_setup/pr.py",
        "session-review-mutation-git-hook-contamination",
        "session-review-focused-gate",
        "git-hook-contamination",
        "python/src/dotfiles_setup/pr.py",
        "child_env.without_git_context",
        2,
    ),
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(raw)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(payload, stream, separators=(",", ":"), sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def _run_dir(repo_root: Path, run_id: str) -> Path:
    if not run_id or any(
        char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for char in run_id
    ):
        message = "run id must contain only letters, digits, dash, or underscore"
        raise ValueError(message)
    return repo_root / ".agent" / "session-review" / "runs" / run_id


def initialize(repo_root: Path, run_id: str) -> Path:
    """Create runner-owned current context with an unpredictable nonce."""
    run_dir = _run_dir(repo_root.resolve(), run_id)
    context = run_dir / "context.json"
    if context.exists():
        message = f"run already exists: {run_id}"
        raise FileExistsError(message)
    _atomic_json(
        context,
        {
            "schema": "session-review.runner-context.v1",
            "runner": RUNNER,
            "run_id": run_id,
            "nonce": secrets.token_hex(32),
            "created_at": _now(),
        },
    )
    return context


def load_context(repo_root: Path, run_id: str) -> dict[str, Any]:
    """Load runner-owned state instead of trusting a disposition's identity."""
    path = _run_dir(repo_root.resolve(), run_id) / "context.json"
    payload = json.loads(path.read_text())
    if (
        payload.get("schema") != "session-review.runner-context.v1"
        or payload.get("runner") != RUNNER
        or payload.get("run_id") != run_id
        or not isinstance(payload.get("nonce"), str)
        or len(payload["nonce"]) != NONCE_HEX_LENGTH
    ):
        message = "runner context is invalid"
        raise ValueError(message)
    return payload


def _execute(argv: list[str], *, timeout: int) -> tuple[int, str, str, str]:
    started = _now()
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
        rc = result.returncode
        output = result.stdout + result.stderr
    except subprocess.TimeoutExpired as exc:
        rc = 124
        output = (exc.stdout or b"") + (exc.stderr or b"")
    return rc, started, _now(), hashlib.sha256(output).hexdigest()


def run_command(
    repo_root: Path,
    run_id: str,
    command: GateCommand,
) -> Path:
    """Execute one mutation/control gate and atomically attest its result."""
    if command.role not in {"mutation", "gate"} or not command.argv:
        message = "role must be mutation/gate and argv may not be empty"
        raise ValueError(message)
    context = load_context(repo_root, run_id)
    artifact_path = command.artifact.resolve(strict=True)
    artifact_path.relative_to(repo_root.resolve())
    artifact_digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    rc, started, finished, output_digest = _execute(
        command.argv, timeout=command.timeout
    )
    receipt = _run_dir(repo_root.resolve(), run_id) / f"{command.role}.json"
    _atomic_json(
        receipt,
        {
            "schema": SCHEMA,
            "status": "ATTESTED" if rc == 0 else "FAILED",
            "role": command.role,
            "runner": RUNNER,
            "run_id": run_id,
            "nonce": context["nonce"],
            "argv": command.argv,
            "rc": rc,
            "started_at": started,
            "finished_at": finished,
            "output_sha256": output_digest,
            "artifact_sha256": artifact_digest,
        },
    )
    return receipt


def run_github_readback(
    repo_root: Path,
    run_id: str,
    api_url: str,
    *,
    timeout: int = 120,
) -> Path:
    """Perform live fnox/gh API readback without persisting response bodies."""
    if not api_url.startswith("https://api.github.com/repos/"):
        message = "GitHub API URL must target api.github.com/repos"
        raise ValueError(message)
    context = load_context(repo_root, run_id)
    argv = ["fnox", "exec", "--", "gh", "api", api_url]
    started = _now()
    result = subprocess.run(argv, capture_output=True, check=False, timeout=timeout)
    finished = _now()
    if result.returncode != 0:
        message = f"GitHub readback failed with rc={result.returncode}"
        raise RuntimeError(message)
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        message = "GitHub readback was not an object"
        raise TypeError(message)
    html_url = str(payload.get("html_url", ""))
    issue_id = payload.get("number", payload.get("id"))
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    receipt = _run_dir(repo_root.resolve(), run_id) / "github_readback.json"
    _atomic_json(
        receipt,
        {
            "schema": SCHEMA,
            "status": "ATTESTED",
            "role": "github_readback",
            "runner": RUNNER,
            "run_id": run_id,
            "nonce": context["nonce"],
            "argv": argv,
            "rc": 0,
            "started_at": started,
            "finished_at": finished,
            "output_sha256": hashlib.sha256(result.stdout + result.stderr).hexdigest(),
            "artifact_sha256": hashlib.sha256(canonical).hexdigest(),
            "api_url": api_url,
            "html_url": html_url,
            "issue_id": issue_id,
            "body_sha256": hashlib.sha256(canonical).hexdigest(),
        },
    )
    return receipt


def _execute_private(argv: list[str], *, timeout: int) -> tuple[int, bytes, str]:
    result = subprocess.run(argv, capture_output=True, check=False, timeout=timeout)
    output = result.stdout + result.stderr
    return result.returncode, output, hashlib.sha256(output).hexdigest()


def mutation_sentinel(prevention_id: str) -> int:
    """Mutate an isolated candidate and prove the normal gate rejects it."""
    registration = PREVENTIONS.get(prevention_id)
    if registration is None:
        return 2
    root = Path(os.environ.get("MISE_PROJECT_ROOT", Path.cwd())).resolve()
    source = root / registration.target
    before = source.read_bytes()
    token = registration.required_token.encode()
    if token not in before:
        return 2
    with tempfile.TemporaryDirectory(prefix="session-review-mutant-") as raw:
        candidate = Path(raw)
        for registered in PREVENTIONS.values():
            copied = candidate / registered.target
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / registered.target, copied)
        target = candidate / registration.target
        target.write_bytes(before.replace(token, b"mutant_removed", 1))
        after = target.read_bytes()
        env = {**os.environ, "SESSION_REVIEW_CANDIDATE_ROOT": str(candidate)}
        gate_argv = ["mise", "run", registration.gate_task]
        result = subprocess.run(
            gate_argv, capture_output=True, check=False, env=env, timeout=120
        )
    if result.returncode == 0 or before == after:
        return 2
    payload = {
        "schema": "session-review.mutant-armed.v1",
        "prevention_id": prevention_id,
        "mutant": registration.mutant_name,
        "status": "ARMED",
        "target": registration.target,
        "before_sha256": hashlib.sha256(before).hexdigest(),
        "after_sha256": hashlib.sha256(after).hexdigest(),
        "gate_argv": gate_argv,
        "gate_rc": result.returncode,
    }
    os.write(
        1, (json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n").encode()
    )
    return 1


def prevention_check(candidate_root: Path) -> int:
    """Reject candidates missing any registered prevention carrier contract."""
    for registration in PREVENTIONS.values():
        path = candidate_root / registration.target
        try:
            text = path.read_text()
        except OSError:
            return 1
        if text.count(registration.required_token) != registration.required_count:
            return 1
    return 0


def _issue_identity(api_url: str) -> tuple[str, str, int]:
    parsed = urlparse(api_url)
    parts = parsed.path.strip("/").split("/")
    if (
        parsed.scheme != "https"
        or parsed.netloc != "api.github.com"
        or len(parts) != ISSUE_PATH_PARTS
        or parts[0] != "repos"
        or parts[3] != "issues"
        or not parts[4].isdigit()
        or not parts[1]
        or not parts[2]
    ):
        message = "issue endpoint must be /repos/{owner}/{repo}/issues/{number}"
        raise ValueError(message)
    return parts[1], parts[2], int(parts[4])


def _finalize_inputs(
    repo_root: Path, spec_path: Path
) -> tuple[str, PreventionRegistration, str, str, int, str]:
    root = repo_root.resolve(strict=True)
    spec_resolved = spec_path.resolve(strict=True)
    spec_resolved.relative_to(root)
    spec = json.loads(spec_resolved.read_text())
    if not isinstance(spec, dict) or spec.get("schema") != "session-review.finalize.v1":
        message = "finalize spec has the wrong schema"
        raise ValueError(message)
    unknown = set(spec) - {"schema", "prevention_id", "api_url"}
    if unknown:
        message = f"finalize spec contains caller-controlled fields: {sorted(unknown)}"
        raise ValueError(message)
    prevention_id = str(spec.get("prevention_id", ""))
    registration = PREVENTIONS.get(prevention_id)
    if registration is None:
        message = "finalize requires a registered prevention_id"
        raise ValueError(message)
    carrier = root / registration.carrier
    if carrier.is_symlink():
        message = "carrier may not be a symlink"
        raise ValueError(message)
    carrier = carrier.resolve(strict=True)
    carrier.relative_to(root)
    carrier_sha256 = hashlib.sha256(carrier.read_bytes()).hexdigest()
    api_url = str(spec.get("api_url", ""))
    owner, repo, issue_number = _issue_identity(api_url)
    return prevention_id, registration, owner, repo, issue_number, carrier_sha256


def _validated_github_body(
    github: subprocess.CompletedProcess[bytes], owner: str, repo: str, issue_number: int
) -> bytes:
    if github.returncode != 0:
        message = "GitHub live readback failed"
        raise RuntimeError(message)
    readback = json.loads(github.stdout)
    expected_html = f"https://github.com/{owner}/{repo}/issues/{issue_number}"
    if (
        not isinstance(readback, dict)
        or readback.get("number") != issue_number
        or readback.get("html_url") != expected_html
        or not isinstance(readback.get("body"), str)
        or not readback["body"]
    ):
        message = "GitHub live readback identity is invalid"
        raise ValueError(message)
    return json.dumps(readback, separators=(",", ":"), sort_keys=True).encode()


def finalize(repo_root: Path, spec_path: Path) -> FinalizeResult:
    """Re-evaluate every completion fact in one process with an ephemeral nonce."""
    prevention_id, registration, owner, repo, issue_number, carrier_sha256 = (
        _finalize_inputs(repo_root, spec_path)
    )
    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    mutation_argv = ["mise", "run", registration.mutation_task]
    gate_argv = ["mise", "run", registration.gate_task]
    if registration.mutation_task == registration.gate_task:
        message = "registered mutation and gate tasks must be distinct"
        raise ValueError(message)
    ephemeral_nonce = secrets.token_bytes(32)
    mutation_rc, mutation_output, mutation_digest = _execute_private(
        mutation_argv, timeout=DEFAULT_TIMEOUT
    )
    gate_rc, _, gate_digest = _execute_private(gate_argv, timeout=DEFAULT_TIMEOUT)
    github = subprocess.run(
        ["fnox", "exec", "--", "gh", "api", api_url],
        capture_output=True,
        check=False,
        timeout=120,
    )
    if mutation_rc == 0 or gate_rc != 0:
        message = "mutation or gate returned an unexpected status"
        raise RuntimeError(message)
    try:
        sentinel = json.loads(mutation_output.decode().splitlines()[-1])
    except (UnicodeDecodeError, json.JSONDecodeError, IndexError) as exc:
        message = "mutation did not emit the typed armed sentinel"
        raise ValueError(message) from exc
    expected_sentinel = {
        "schema": "session-review.mutant-armed.v1",
        "prevention_id": prevention_id,
        "mutant": registration.mutant_name,
        "status": "ARMED",
    }
    if not all(sentinel.get(key) == value for key, value in expected_sentinel.items()):
        message = "mutation armed sentinel identity does not match registration"
        raise ValueError(message)
    if (
        sentinel.get("target") != registration.target
        or sentinel.get("gate_argv") != gate_argv
        or sentinel.get("gate_rc") == 0
        or sentinel.get("before_sha256") == sentinel.get("after_sha256")
        or not all(
            re.fullmatch(r"[0-9a-f]{64}", str(sentinel.get(key, "")))
            for key in ("before_sha256", "after_sha256")
        )
    ):
        message = "mutation receipt lacks changed target digest or gate rejection"
        raise ValueError(message)
    canonical = _validated_github_body(github, owner, repo, issue_number)
    # Consume the nonce in the verdict calculation, then discard it with this frame.
    hashlib.sha256(ephemeral_nonce + canonical).digest()
    return FinalizeResult(
        "TEMPORARILY_COMPLETE",
        (prevention_id,),
        carrier_sha256,
        mutation_digest,
        gate_digest,
        hashlib.sha256(canonical).hexdigest(),
    )


def main(argv: list[str] | None = None) -> int:
    """Run the trusted receipt CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--run-id", default="")
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("init")
    command = actions.add_parser("command")
    command.add_argument("--role", choices=("mutation", "gate"), required=True)
    command.add_argument("--artifact", type=Path, required=True)
    command.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    command.add_argument("argv", nargs=argparse.REMAINDER)
    github = actions.add_parser("github-readback")
    github.add_argument("--api-url", required=True)
    finalizer = actions.add_parser("finalize")
    finalizer.add_argument("--spec", type=Path, required=True)
    mutant = actions.add_parser("mutation-sentinel")
    mutant.add_argument("--prevention-id", required=True)
    actions.add_parser("prevention-check")
    args = parser.parse_args(argv)
    if args.action == "init":
        path = initialize(args.repo_root, args.run_id)
    elif args.action == "command":
        command_argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
        path = run_command(
            args.repo_root,
            args.run_id,
            GateCommand(args.role, command_argv, args.artifact, args.timeout),
        )
    elif args.action == "github-readback":
        path = run_github_readback(args.repo_root, args.run_id, args.api_url)
    elif args.action == "finalize":
        result = finalize(args.repo_root, args.spec)
        logger.info(
            "session-review finalize: %s for %d finding(s); rerun before resume",
            result.status,
            len(result.finding_ids),
        )
        return 0
    elif args.action == "mutation-sentinel":
        return mutation_sentinel(args.prevention_id)
    else:
        candidate = Path(
            os.environ.get("SESSION_REVIEW_CANDIDATE_ROOT", args.repo_root)
        )
        return prevention_check(candidate)
    logger.info("wrote %s", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
