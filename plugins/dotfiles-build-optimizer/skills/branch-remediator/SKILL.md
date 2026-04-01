---
name: branch-remediator
description: Create or reuse a branch for fixing a failed CI run in this repo, run local preflight, push the branch, and optionally create or update a PR using the GitHub plugin. Use when a remediation plan is ready and fixes must never go directly to main.
---

# Branch Remediator

## Overview

Perform branch-based remediation only. Never patch `main` directly.

## Branch Naming

Use:

```bash
plugins/dotfiles-build-optimizer/scripts/branch_remediator.sh <run-id>
```

This creates or switches to:

- `codex/ci-fix/<run-id>`

## Required Flow

1. Create or switch branch
2. Apply fixes
3. Run `local-preflight`
4. Push branch
5. Use the GitHub plugin for PR search/create/update if helpful

## Tool Split

Use the GitHub plugin for:

- branch search or creation context
- commit comparison
- PR creation and PR metadata

Use `gh` for:

- Actions run watching
- log retrieval
