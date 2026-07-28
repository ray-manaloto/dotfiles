# Evidence — `zero-bash-logic`

Design rationale behind `.claude/rules/zero-bash-logic.md`. Extracted so the
eager copy carries the gate itself and this file carries why it is built the way
it is.

## Why the check logic lives in python

A big inline-bash grep in the hk step **would itself violate the policy it
enforces**. So the allowlist + budget logic lives in
`python/src/dotfiles_setup/bash_budget.py`, and both the hk step and the CLI
subcommand are thin wrappers over `find_violations`.

This mirrors the two other guards in this repo:

| Guard | Logic in python | Thin seam |
|---|---|---|
| PreToolUse redirect guard | `hook_guard.py` | `settings.json` → wrapper |
| hk timeout wrapper | `lint.py` | `mise run lint` |
| bash budget | `bash_budget.py` | `bash_logic_budget` hk step |

Logic in python, a thin shell/hk seam — in every case.

## Wiring, kept honest by a contract

`workflow.bash-logic-enforcement` in `python/verification/suites.toml` asserts
the whole chain exists: hk step ↔ `dotfiles-setup bash-budget` ↔ module ↔ tests
↔ the rule file. So the guard cannot silently drift out — the same pattern as
`workflow.mise-tasks-enforcement`.

This matters because every layer of the chain is individually deletable without
breaking anything visible: an hk step can be commented out, a CLI subcommand can
be renamed, and nothing fails until the day it was supposed to catch something.

## History

The policy was **doc-only** (a paragraph in the root `AGENTS.md`) until the
`bash_logic_budget` hk step gave it machine teeth. The two mechanisms it added —
an allowlist that gates NEW files, and a per-file `max_lines` budget that flags
GROWTH — exist because a doc-only version can be violated by a diff nobody
reads. A stale entry (an allowlisted path no longer tracked) also fails, so the
map cannot rot after a script is deleted.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the rule,
  `python/src/dotfiles_setup/bash_budget.py`, `hk.pkl`,
  `python/verification/suites.toml`.
