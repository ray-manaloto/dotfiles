#!/usr/bin/env python3
"""Generate a normalized failure report for a GitHub Actions workflow run."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any


def github_get(url: str, token: str) -> dict[str, Any]:
    # Ruff S310 (audit URL for permitted schemes): addressed by boundary
    # validation rather than an inline suppression. This script only
    # talks to api.github.com, so allow nothing else.
    if not url.startswith("https://api.github.com/"):
        msg = f"refusing non-GitHub URL: {url!r}"
        raise ValueError(msg)
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def collect_signatures(jobs: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    error_signatures: list[str] = []
    warning_signatures: list[str] = []
    for job in jobs:
        for step in job.get("steps", []):
            name = step.get("name", "unknown-step")
            conclusion = step.get("conclusion", "unknown")
            if conclusion == "failure":
                error_signatures.append(f"{job.get('name', 'unknown-job')}::{name}")
            elif conclusion not in {"success", "skipped"}:
                warning_signatures.append(f"{job.get('name', 'unknown-job')}::{name}::{conclusion}")
    return sorted(set(error_signatures)), sorted(set(warning_signatures))


def build_report(repo: str, run_id: str, token: str) -> dict[str, Any]:
    run = github_get(f"https://api.github.com/repos/{repo}/actions/runs/{run_id}", token)
    jobs_response = github_get(
        f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100",
        token,
    )
    jobs = jobs_response.get("jobs", [])
    failed_jobs = [job for job in jobs if job.get("conclusion") == "failure"]
    error_signatures, warning_signatures = collect_signatures(jobs)

    return {
        "run_id": int(run_id),
        "workflow_name": run.get("name"),
        "head_sha": run.get("head_sha"),
        "branch": run.get("head_branch"),
        "failed_jobs": [
            {
                "id": job.get("id"),
                "name": job.get("name"),
                "url": job.get("html_url"),
                "failed_steps": [
                    {
                        "number": step.get("number"),
                        "name": step.get("name"),
                        "conclusion": step.get("conclusion"),
                    }
                    for step in job.get("steps", [])
                    if step.get("conclusion") == "failure"
                ],
            }
            for job in failed_jobs
        ],
        "failed_steps": [
            step.get("name")
            for job in failed_jobs
            for step in job.get("steps", [])
            if step.get("conclusion") == "failure"
        ],
        "error_signatures": error_signatures,
        "warning_signatures": warning_signatures,
        "artifact_urls": [job.get("html_url") for job in failed_jobs if job.get("html_url")],
        "created_at": run.get("created_at"),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "failure-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary_lines = [
        f"# Failure report for run {report['run_id']}",
        "",
        f"- Workflow: {report['workflow_name']}",
        f"- Branch: {report['branch']}",
        f"- SHA: {report['head_sha']}",
        f"- Failed jobs: {len(report['failed_jobs'])}",
        "",
        "## Error signatures",
        *[f"- {sig}" for sig in report["error_signatures"]],
    ]
    (output_dir / "fix-summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is required", file=sys.stderr)
        return 1

    report = build_report(args.repo, args.run_id, token)
    write_outputs(Path(args.output_dir), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
