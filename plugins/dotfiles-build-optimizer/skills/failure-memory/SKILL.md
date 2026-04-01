---
name: failure-memory
description: Record recurring CI failure signatures, successful fixes, rejected fixes, and tool/backend incompatibilities for this repo only. Use after triage, after remediation, or after rejecting an approach so the next iteration does not repeat the same blind fix.
---

# Failure Memory

## Overview

Store only repo-local, evidence-backed memory for the dotfiles CI workflow.

## Storage

- `.omx/state/dotfiles-build-optimizer/failure-memory.jsonl`
- `.omx/logs/dotfiles-build-optimizer/`

## Recording

Use:

```bash
uv run --script plugins/dotfiles-build-optimizer/scripts/record_failure_memory.py \
  --input <path-to-report.json>
```

## Rules

- Record exact signatures.
- Record rejected fixes.
- Record proven local validation commands.
- Do not store generic chatter or redundant logs.
