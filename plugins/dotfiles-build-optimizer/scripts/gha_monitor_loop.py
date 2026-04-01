#!/usr/bin/env python3
"""Repo-local monitor loop for failed GitHub Actions runs."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def latest_failed_run() -> str:
    runs = json.loads(
        run(
            [
                "gh",
                "run",
                "list",
                "--limit",
                "20",
                "--json",
                "databaseId,conclusion",
            ]
        )
    )
    for item in runs:
        if item.get("conclusion") == "failure":
            return str(item["databaseId"])
    raise RuntimeError("No failed run found")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    parser.add_argument("--latest-failed", action="store_true")
    parser.add_argument(
        "--output-dir",
        default=".omx/state/dotfiles-build-optimizer/latest-run",
    )
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()

    run_id = args.run_id or (latest_failed_run() if args.latest_failed or not args.run_id else None)
    if not run_id:
        raise SystemExit("Provide --run-id or use --latest-failed")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "failure-report.json"

    run(
        [
            "uv",
            "run",
            "--script",
            "plugins/dotfiles-build-optimizer/scripts/gha_run_triage.py",
            run_id,
            "--output",
            str(report_path),
        ]
    )

    subprocess.run(
        [
            "uv",
            "run",
            "--script",
            "plugins/dotfiles-build-optimizer/scripts/record_failure_memory.py",
            "--input",
            str(report_path),
        ],
        check=True,
    )

    print(f"Failure report written to {report_path}")
    print("Next recommended skills:")
    print("- $gha-research-team")
    print("- $branch-remediator")
    print("- $local-preflight")

    if args.watch:
        subprocess.run(["gh", "run", "watch", run_id, "--interval", "10", "--exit-status"], check=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
