---
name: gha-run-triage
description: Normalize a failed GitHub Actions run for this dotfiles repo into one machine-readable triage report. Use when given a run URL, run id, job URL, or "latest failed run" and you need failing jobs, failing steps, warning signatures, blocker signatures, and likely owner areas. Use the GitHub plugin for repo/PR context, but use `gh` for Actions run and log retrieval.
---

# GHA Run Triage

## Overview

Turn one failed GitHub Actions run into a compact JSON failure report that downstream research and remediation skills can consume.

## Workflow

Resolve the run id first.

- If given a run URL, extract the numeric id from `/actions/runs/<id>`.
- If asked for the latest failed run, use:

```bash
uv run --script plugins/dotfiles-build-optimizer/scripts/gha_run_triage.py --latest-failed
```

- If given a specific run, use:

```bash
uv run --script plugins/dotfiles-build-optimizer/scripts/gha_run_triage.py <run-id-or-url>
```

## Output Contract

Produce a JSON report with:

- `run_id`
- `workflow_name`
- `sha`
- `branch`
- `status`
- `conclusion`
- `run_url`
- `failing_jobs`
- `error_signatures`
- `warning_signatures`
- `likely_owners`

## Tool Split

Use:

- `gh run list`
- `gh run view --json`
- `gh run view --job <id> --log`

Use the GitHub plugin only for repo/branch/PR/issue context after the Actions failure is normalized.
---
name: gha-run-triage
description: Normalize a failed GitHub Actions run for this dotfiles repo into one machine-readable triage report. Use when given a run URL, run id, job URL, or "latest failed run" and you need failing jobs, failing steps, warning signatures, blocker signatures, and likely owner areas. Use the GitHub plugin for repo/PR context, but use `gh` for Actions run and log retrieval.
---

# GHA Run Triage

## Overview

Turn one failed GitHub Actions run into a compact JSON failure report that downstream research and remediation skills can consume.

## Workflow

Resolve the run id first.

- If given a run URL, extract the numeric id from `/actions/runs/<id>`.
- If asked for the latest failed run, use:

```bash
uv run --script plugins/dotfiles-build-optimizer/scripts/gha_run_triage.py --latest-failed
```

- If given a specific run, use:

```bash
uv run --script plugins/dotfiles-build-optimizer/scripts/gha_run_triage.py <run-id-or-url>
```

## Output Contract

Produce a JSON report with:

- `run_id`
- `workflow_name`
- `sha`
- `branch`
- `status`
- `conclusion`
- `run_url`
- `failing_jobs`
- `error_signatures`
- `warning_signatures`
- `likely_owners`

## Tool Split

Use:

- `gh run list`
- `gh run view --json`
- `gh run view --job <id> --log`

Use the GitHub plugin only for repo/branch/PR/issue context after the Actions failure is normalized.
