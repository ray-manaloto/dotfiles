# Copyright (c) 2026 Raymond Manaloto
"""A partial-install job must not let `mise run` auto-install the root tools (#963).

A job whose setup step installs only a subset (`install_args`) and then calls a
bare `mise run <task>` makes mise install every other root tool first, UNLOCKED.
A fresh install of an aqua `type: http` tool with no published checksum
(aws-cli, docker-cli) then writes its blake3 into the tracked root `mise.lock`,
which is how `image-lock-pr` kept failing its own containment guard. The native
fix is `mise run --skip-tools`; this gate keeps every such call site on it.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
_MISE_RUN = re.compile(r"\bmise\s+run\b(?P<rest>[^\n]*)")


def _partial_install_mise_runs(workflow: dict) -> list[tuple[str, str]]:
    """Return (job, command) for each bare `mise run` in a subset-install job."""
    found: list[tuple[str, str]] = []
    for job_name, job in (workflow.get("jobs") or {}).items():
        steps = job.get("steps") or []
        partial = any((step.get("with") or {}).get("install_args") for step in steps)
        if not partial:
            continue
        for step in steps:
            run = step.get("run") or ""
            for line in run.splitlines():
                if line.lstrip().startswith("#"):
                    continue
                match = _MISE_RUN.search(line)
                if match and "--skip-tools" not in match.group("rest").split():
                    found.append((job_name, line.strip()))
    return found


def test_probe_flags_a_bare_mise_run_in_a_partial_install_job() -> None:
    """Control arm: the scanner must catch the #963 shape and pass the fix."""
    bare = {
        "jobs": {
            "j": {
                "steps": [
                    {"with": {"install_args": "python uv"}},
                    {"run": "mise run lock-image -- --no-container"},
                ]
            }
        }
    }
    fixed = {
        "jobs": {
            "j": {
                "steps": [
                    {"with": {"install_args": "python uv"}},
                    {"run": "mise run --skip-tools lock-image -- --no-container"},
                ]
            }
        }
    }
    full = {"jobs": {"j": {"steps": [{"run": "mise run lint"}]}}}
    assert _partial_install_mise_runs(bare) == [
        ("j", "mise run lock-image -- --no-container")
    ]
    assert _partial_install_mise_runs(fixed) == []
    assert _partial_install_mise_runs(full) == []


def test_partial_install_jobs_use_skip_tools() -> None:
    offenders = [
        (path.name, job, command)
        for path in sorted(WORKFLOWS.glob("*.yml"))
        for job, command in _partial_install_mise_runs(yaml.safe_load(path.read_text()))
    ]
    assert offenders == []
