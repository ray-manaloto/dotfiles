#!/usr/bin/env python3
"""Generate a normalized failure report for a GitHub Actions workflow run."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

# owner/name — validated before interpolation into a `gh api` path so an
# attacker-influenced --repo cannot traverse to a different API surface.
_REPO_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")


def gh_api(path: str) -> dict[str, Any]:
    """Fetch a GitHub REST API path via `gh api` and return the parsed JSON.

    `gh api` only ever talks to the authenticated GitHub host (auth via the
    `GITHUB_TOKEN`/`GH_TOKEN` env or `gh auth`), so — unlike a raw URL open —
    the scheme/host cannot be redirected by the caller. The only
    attacker-influenced surface is *path*, which callers validate before use.
    """
    result = subprocess.run(
        ["gh", "api", "-H", "X-GitHub-Api-Version: 2022-11-28", path],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def collect_signatures(jobs: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Split job step conclusions into error and warning signature lists."""
    error_signatures: list[str] = []
    warning_signatures: list[str] = []
    for job in jobs:
        for step in job.get("steps", []):
            name = step.get("name", "unknown-step")
            conclusion = step.get("conclusion", "unknown")
            if conclusion == "failure":
                error_signatures.append(f"{job.get('name', 'unknown-job')}::{name}")
            elif conclusion not in {"success", "skipped"}:
                warning_signatures.append(
                    f"{job.get('name', 'unknown-job')}::{name}::{conclusion}"
                )
    return sorted(set(error_signatures)), sorted(set(warning_signatures))


def build_report(repo: str, run_id: str) -> dict[str, Any]:
    """Build a normalized failure report dict for the given workflow run."""
    if not _REPO_RE.match(repo):
        msg = f"invalid repo {repo!r}; expected 'owner/name'"
        raise ValueError(msg)
    if not run_id.isdigit():
        msg = f"invalid run id {run_id!r}; expected digits"
        raise ValueError(msg)
    run = gh_api(f"repos/{repo}/actions/runs/{run_id}")
    jobs_response = gh_api(f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100")
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
        "artifact_urls": [
            job.get("html_url") for job in failed_jobs if job.get("html_url")
        ],
        "created_at": run.get("created_at"),
    }


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    """Write the failure report JSON and a markdown summary into *output_dir*."""
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
    (output_dir / "fix-summary.md").write_text(
        "\n".join(summary_lines) + "\n", encoding="utf-8"
    )


def main() -> int:
    """Parse CLI arguments and print the failure report as JSON."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    report = build_report(args.repo, args.run_id)
    write_outputs(Path(args.output_dir), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
