---
name: gha-monitor-loop
description: Watch this repo's CI failure-report workflow outputs, triage failed runs, launch the research team, drive branch-based remediation, and repeat until the workflow is green or blocked. Use when you want the full repo-local monitor and fix loop for GitHub Actions failures in this dotfiles repo.
---

# GHA Monitor Loop

## Overview

Run the full loop for this repo:

1. detect failed run
2. triage it
3. launch research team
4. remediate on a branch
5. watch the new run
6. record memory
7. repeat until green or blocked

## Inputs

- latest failed run
- run id
- run URL
- failure artifact from `.github/workflows/ci-failure-report.yml`

## Tool Split

Use `gh` for:

- `gh run list`
- `gh run view --json`
- `gh run view --log`
- `gh run watch`
- artifact-aware workflow inspection

Use the GitHub plugin for:

- commit comparison
- branch operations
- PR or issue lifecycle work

## Repo-Local Helpers

- `gha-run-triage`
- `gha-research-team`
- `branch-remediator`
- `failure-memory`
- `local-preflight`
