# Zero-Bash-Logic: No New Bash, No Growth of Existing

Non-trivial logic (environment detection, tool config, validation,
orchestration) lives in `python/` (`dotfiles_setup`). Bash is restricted to
**thin check/smoke wrappers** in `scripts/` and `.devcontainer/scripts/`. This
was a doc-only policy (root `AGENTS.md`) until the `bash_logic_budget` hk step
gave it machine teeth.

## The gate

Two mechanisms, enforced by `dotfiles_setup.bash_budget` (the `bash-budget`
CLI subcommand, run by the `bash_logic_budget` hk step in `hk.pkl`):

1. **Allowlist gates NEW files.** Every tracked `scripts/*.sh` and
   `.devcontainer/scripts/*.sh` must have an `ALLOWLIST` entry in
   `python/src/dotfiles_setup/bash_budget.py`. A new `.sh` not on the list
   **fails** — move the logic into `python/` (the default answer), or add an
   explicit entry with a one-line justification (a reviewable diff).
2. **Per-file budget flags GROWTH.** Each entry's `max_lines` is the file's
   baseline line count. Growing past it **fails**; shrinking is always fine. A
   budget bump is a reviewable diff + justification, not silent creep.

A stale entry (an allowlisted path no longer tracked) also fails, so the map
can't rot after a script is deleted.

`plugins/**` is out of scope (vendored / third-party).

## Why the check logic is in python

A big inline-bash grep in the hk step would itself violate the policy it
enforces — so the logic lives in `bash_budget.py` and the hk step is a thin
wrapper, mirroring `hook_guard.py` and `lint.py`. The whole chain (hk step ↔
CLI ↔ module ↔ tests ↔ this rule) is asserted by
`workflow.bash-logic-enforcement` in suites.toml, so it can't silently drift
out. Detail: `docs/rules-evidence/zero-bash-logic.md`.

## Applies to

Every `scripts/*.sh` and `.devcontainer/scripts/*.sh` in this repo. A new
recurring workflow ships its logic as a `python/` module + a mise task
(`.claude/rules/mise-tasks-only.md`), not as a new shell script.

## See also

- `.claude/rules/use-tool-builtins.md` — prefer native/tool features over any
  homegrown code (bash or python); the parent principle.
- `.claude/rules/mise-tasks-only.md` — canonical mise tasks wrapping python
  libraries, not one-off command sequences.
- `python/src/dotfiles_setup/bash_budget.py` — the enforcer (allowlist +
  budget map + `find_violations`).
- `hk.pkl` — the `bash_logic_budget` step.
