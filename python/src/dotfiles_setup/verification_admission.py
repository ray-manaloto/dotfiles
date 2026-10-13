# Copyright (c) 2026 Raymond Manaloto
"""Compiler-only admission and saved-byte binding for required proof verifiers.

Python's compiler supplies syntax validation; hashlib supplies byte identity.
Existing AST/lint contracts do not bind START to saved code, so this module adds
only that lifecycle boundary. Callers declare all required Python helpers.
This is a pre-execution integrity check, not a sandbox against concurrent writers
or a mechanism for discovering and sealing every transitive product import.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import tempfile
import uuid
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

MAX_TIMEOUT_S = 3600


class AdmissionError(ValueError):
    """Refuse a required verifier before executing any of its code."""


def _saved_file(path: Path) -> tuple[Path, bytes]:
    if path.suffix != ".py" or path.is_symlink() or not path.is_file():
        msg = f"required saved Python file missing or invalid: {path}"
        raise AdmissionError(msg)
    try:
        resolved = path.resolve(strict=True)
        source = resolved.read_bytes()
        compile(source, str(resolved), "exec", dont_inherit=True)
    except (OSError, SyntaxError, ValueError) as error:
        msg = f"compiler preflight refused {path}: {error}"
        raise AdmissionError(msg) from error
    return resolved, source


def preflight(verifier: Path, *, helpers: Sequence[Path] = ()) -> dict[str, object]:
    """Compile saved files without importing them and bind their literal bytes."""
    files = []
    for path in (verifier, *helpers):
        resolved, source = _saved_file(path)
        files.append(
            {"path": str(resolved), "sha256": hashlib.sha256(source).hexdigest()}
        )
    if len({entry["path"] for entry in files}) != len(files):
        msg = "duplicate verifier/helper path"
        raise AdmissionError(msg)
    return {"verifier": files[0], "helpers": files[1:]}


def start(verifier: Path, *, helpers: Sequence[Path] = (), attempt_dir: Path) -> Path:
    """Create START only after compiler-only preflight has admitted saved bytes."""
    binding = {
        "schema_version": "dotfiles.verification-start.v1",
        "attempt_id": str(uuid.uuid4()),
        "started_at": datetime.now(UTC).isoformat(),
        "binding": preflight(verifier, helpers=helpers),
    }
    attempt_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    record = attempt_dir / "START.json"
    with record.open("x", encoding="utf-8") as stream:
        json.dump(binding, stream, indent=2)
        stream.write("\n")
    return record.resolve()


def execute(
    record: Path, *, timeout_s: float = MAX_TIMEOUT_S
) -> subprocess.CompletedProcess[bytes]:
    """Recheck START, then run its saved verifier and retain the actual exit."""
    if not math.isfinite(timeout_s) or not 0 < timeout_s <= MAX_TIMEOUT_S:
        msg = "execution timeout must be positive and at most 3600 seconds"
        raise AdmissionError(msg)
    try:
        if record.name != "START.json" or record.is_symlink():
            msg = "execution requires the saved START.json"
            raise AdmissionError(msg)
        raw = record.read_bytes()
        start_record = json.loads(raw)
        if start_record["schema_version"] != "dotfiles.verification-start.v1":
            msg = "unsupported START schema"
            raise AdmissionError(msg)
        binding = start_record["binding"]
        verifier = Path(binding["verifier"]["path"])
        helpers = [Path(entry["path"]) for entry in binding["helpers"]]
    except (OSError, ValueError, KeyError, TypeError) as error:
        msg = f"invalid saved START: {error}"
        raise AdmissionError(msg) from error
    if preflight(verifier, helpers=helpers) != binding:
        msg = "START saved bytes changed before execution"
        raise AdmissionError(msg)
    # Resolve the existing cleanup primitive only after admission. Preflight
    # must import no product modules, including infrastructure helpers.
    process_stream = import_module("dotfiles_setup.process_stream")
    try:
        with (record.parent / "execution.claim").open("x") as claim:
            claim.write(hashlib.sha256(raw).hexdigest() + "\n")
    except FileExistsError as error:
        msg = "START already used; create a fresh attempt"
        raise AdmissionError(msg) from error
    # A fresh cache prefix prevents timestamp-valid historical helper bytecode
    # from substituting for the bound source. -B prevents any new bytecode writes.
    with tempfile.TemporaryDirectory(prefix="verifier-pycache-") as cache:
        command = [sys.executable, "-B", "-X", f"pycache_prefix={cache}", str(verifier)]
        timed_out = False
        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        ) as process:
            try:
                stdout, stderr = process.communicate(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                timed_out = True
                process_stream.terminate_group(process)
                stdout, stderr = process.communicate(timeout=10)
            except BaseException:
                process_stream.terminate_group(process)
                raise
            result = subprocess.CompletedProcess(
                command, process.returncode, stdout, stderr
            )
    for name, payload in (("stdout.bin", stdout), ("stderr.bin", stderr)):
        with (record.parent / name).open("xb") as output:
            output.write(payload)
    evidence = {
        "command": command,
        "returncode": result.returncode,
        "timed_out": timed_out,
        "start_sha256": hashlib.sha256(raw).hexdigest(),
    }
    with (record.parent / "execution.json").open("x", encoding="utf-8") as output:
        output.write(json.dumps(evidence, indent=2) + "\n")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """CLI for explicit saved-file preflight, START publication and execution."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("preflight", "start"):
        command = commands.add_parser(action)
        command.add_argument("--verifier", type=Path, required=True)
        command.add_argument("--helper", type=Path, action="append", default=[])
        if action == "start":
            command.add_argument("--attempt-dir", type=Path, required=True)
    execute_parser = commands.add_parser("execute")
    execute_parser.add_argument("--start", type=Path, required=True)
    options = parser.parse_args(argv)
    try:
        if options.action == "preflight":
            sys.stdout.write(
                json.dumps(preflight(options.verifier, helpers=options.helper)) + "\n"
            )
        elif options.action == "start":
            record = start(
                options.verifier,
                helpers=options.helper,
                attempt_dir=options.attempt_dir,
            )
            sys.stdout.write(f"{record}\n")
        else:
            result = execute(options.start)
            sys.stdout.buffer.write(result.stdout)
            sys.stderr.buffer.write(result.stderr)
            return (
                result.returncode if result.returncode >= 0 else 128 - result.returncode
            )
    except (AdmissionError, OSError, ValueError, KeyError, TypeError) as error:
        sys.stderr.write(f"verifier admission refused: {error}\n")
        return 2
    return 0
