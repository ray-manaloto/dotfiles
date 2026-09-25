---
name: plugin-removal
description: Remove a Codex or codex plugin through the checked inventory, dry-run plan, native CLIs, verification, and per-repository PR workflow. Use whenever a plugin, marketplace, plugin cache, or trusted plugin hook must be removed. The procedure is dry-run-first and keeps worktrees report-only.
---

# Plugin removal

Use one exact `name@marketplace` selector throughout. The mechanics are defined
by `docs/specs/plugin-remove-pipeline.md`; this wrapper owns the judgment and
repository workflow around them.

## Procedure

1. Invoke `plugin-inventory` and run:

   ```bash
   mise run plugin-inventory -- <name@marketplace>
   ```

   Resolve every probe error before treating an empty field as absence.

2. Review every `references` hit. Remove live instruction or configuration
   references, keep historical records, and independently re-derive any count
   near a hit. Apply repository edits on branches; report worktree settings but
   leave those branches untouched.

3. Inspect the non-mutating plan:

   ```bash
   mise run plugin-remove -- <name@marketplace>
   ```

   Confirm every install scope, exact cache/data target, marketplace-guard note,
   and blocker. A blocked dry run exits 1. After explicit approval to mutate the
   named host and repositories, apply that same plan:

   ```bash
   mise run plugin-remove -- <name@marketplace> --apply
   ```

   The apply path backs up cache and data with a manifest before uninstalling,
   preserves minimal settings diffs, and stops at the first failed
   post-condition.

4. Invoke `plugin-health`, then verify both guards:

   ```bash
   mise run plugin-health
   mise run doctor
   ```

   Re-run `plugin-inventory`; every location and native-CLI match must now be
   absent, with no probe errors.

5. Keep one branch and PR per repository touched. In dotfiles use `mise run
   ship` and `mise run land -- PR_NUMBER`. In knowledge-base run `mise run
   kb-review` before `mise run kb-ship`, then `mise run kb-land -- PR_NUMBER`
   after merge.

Do not commit or ship cross-repository edits from the removal library; those
review boundaries belong to this wrapper and the caller.
