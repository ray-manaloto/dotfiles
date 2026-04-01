#!/usr/bin/env python3
"""Normalize a GitHub Actions run into a triage report using gh."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


def run_json(cmd: list[str]) -> Any:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def run_text(cmd: list[str]) -> str:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def parse_run_id(value: str) -> str:
    match = re.search(r"/actions/runs/(\d+)", value)
    return match.group(1) if match else value


def latest_failed_run() -> str:
    runs = run_json(
        [
            "gh",
            "run",
            "list",
            "--limit",
            "20",
            "--json",
            "databaseId,conclusion,url",
        ]
    )
    for run in runs:
        if run.get("conclusion") == "failure":
            return str(run["databaseId"])
    raise RuntimeError("No failed run found")


def extract_signatures(log_text: str) -> tuple[list[str], list[str]]:
    error_lines: list[str] = []
    warning_lines: list[str] = []
    for raw in log_text.splitlines():
        line = raw.strip()
        lower = line.lower()
        if "error" in lower or "failed to" in lower:
            error_lines.append(line)
        elif "warn" in lower or "warning" in lower:
            warning_lines.append(line)
    return sorted(set(error_lines[:20])), sorted(set(warning_lines[:20]))


def likely_owners(error_signatures: list[str]) -> list[str]:
    owners: set[str] = set()
    combined = "\n".join(error_signatures).lower()
    if "docker" in combined or "buildx" in combined or "bake" in combined:
        owners.add("docker-bake")
    if "devcontainer" in combined or "sshd" in combined:
        owners.add("devcontainer")
    if "chezmoi" in combined:
        owners.add("chezmoi")
    if "mise" in combined or "conda:" in combined or "pipx:" in combined:
        owners.add("mise")
    if "hk" in combined or "pre-commit" in combined:
        owners.add("hk")
    if "pytest" in combined or "uv run" in combined:
        owners.add("python-automation")
    return sorted(owners)


def build_report(run_id: str) -> dict[str, Any]:
    run = run_json(
        [
            "gh",
            "run",
            "view",
            run_id,
            "--json",
            "displayTitle,headBranch,headSha,url,workflowName,status,conclusion,jobs",
        ]
    )
    failed_jobs = [job for job in run.get("jobs", []) if job.get("conclusion") == "failure"]
    job_reports = []
    all_errors: list[str] = []
    all_warnings: list[str] = []
    for job in failed_jobs:
        log_text = run_text(["gh", "run", "view", run_id, "--job", str(job["databaseId"]), "--log"])
        errors, warnings = extract_signatures(log_text)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        job_reports.append(
            {
                "job_id": job["databaseId"],
                "job_name": job.get("name"),
                "job_url": job.get("url"),
                "error_signatures": errors,
                "warning_signatures": warnings,
            }
        )

    return {
        "run_id": int(run_id),
        "workflow_name": run.get("workflowName") or run.get("displayTitle"),
        "sha": run.get("headSha"),
        "branch": run.get("headBranch"),
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "run_url": run.get("url"),
        "failing_jobs": job_reports,
        "error_signatures": sorted(set(all_errors)),
        "warning_signatures": sorted(set(all_warnings)),
        "likely_owners": likely_owners(all_errors),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", nargs="?", help="Run id or run URL")
    parser.add_argument("--latest-failed", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    run_id = latest_failed_run() if args.latest_failed else parse_run_id(args.run or "")
    if not run_id:
        raise SystemExit("Provide a run id, run URL, or --latest-failed")

    report = build_report(run_id)
    output = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
