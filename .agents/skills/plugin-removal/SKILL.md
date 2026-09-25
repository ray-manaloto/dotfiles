---
name: plugin-removal
description: Remove a Codex or codex plugin through the checked inventory, dry-run plan, native CLIs, verification, and per-repository PR workflow. Use whenever a plugin, marketplace, plugin cache, or trusted plugin hook must be removed. The procedure is dry-run-first and keeps worktrees report-only.
---

# Plugin removal

Use one exact `name@marketplace` selector throughout. The contract is
`docs/specs/plugin-remove-pipeline.md` as amended by `-r2.md` and `-r3.md` (later
files win); `python/src/dotfiles_setup/plugin_remove.py` is authoritative where
they differ. This wrapper owns the judgment and repository workflow around it.

## Procedure

1. Invoke `plugin-inventory` and run:

   ```bash
   mise run plugin-inventory -- <name@marketplace>
   ```

   Resolve every probe error before treating an empty field as absence.

2. Review every `references` hit. Remove live instructions that tell a reader
   to USE the plugin, and live configuration that enables it. KEEP the
   `doctor.toml` `[removed_plugins]` entry (the reappearance guard), test
   fixtures, and historical records (specs, reports, receipts). Independently
   re-derive any count near a hit. Apply repository edits on branches; report
   worktree settings but leave those branches untouched.

3. Inspect the non-mutating plan:

   ```bash
   mise run plugin-remove -- <name@marketplace>
   ```

   Confirm every install scope, exact cache/data target, marketplace-guard note,
   and blocker. A blocked dry run exits 1. Create the dotfiles branch (and a
   branch in every repository whose project settings the plan names) BEFORE
   `--apply`: it appends the bare plugin name to `doctor.toml`
   `[removed_plugins].names` and minimally edits project `settings*.json`, all
   tracked. After explicit approval, run the dry run again immediately before
   `--apply` and change nothing in between — `--apply` re-inventories and
   re-plans, so a state change between the two runs executes a plan you did not
   review:

   ```bash
   mise run plugin-remove -- <name@marketplace> --apply
   ```

   The apply path backs up cache and data with a manifest (under
   `.agent/state/plugin-remove/<UTC stamp>/`) before uninstalling, preserves
   minimal settings diffs, and stops at the first failed post-condition with
   that step's rc. A blocked `--apply` exits 2 without mutating.

4. Invoke `plugin-health`, then verify both guards:

   ```bash
   mise run plugin-health            # rc is the verdict
   mise run doctor -- --strict       # rc=1 on ANY drift, incl. removed-plugins
   ```

   Both must exit 0. `mise run doctor` without `--strict` always exits 0 and
   proves nothing.

   Re-run `plugin-inventory`; every location and native-CLI match must now be
   absent, with no probe errors.

5. Keep one branch and PR per repository touched. In dotfiles use `mise run
   ship` and `mise run land -- PR_NUMBER`. In knowledge-base, first run that
   repo's kb-review skill (it ends by writing the review receipt that kb-ship
   checks), then `mise run kb-ship`, and `mise run kb-land -- PR_NUMBER` after
   merge.

Do not commit or ship cross-repository edits from the removal library; those
review boundaries belong to this wrapper and the caller.
