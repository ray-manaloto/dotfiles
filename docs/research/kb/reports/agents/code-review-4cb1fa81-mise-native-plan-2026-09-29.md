# /code-review medium on 4cb1fa81 (the handoff PR #1456 commit) — 2026-09-29

Verbatim. NOTE: launched to review S29-H since 4cb1fa81, the fork reviewed commit 4cb1fa81 itself; its findings are about the S29-M plan `docs/specs/mise-native-dotfiles-plan.md` and are kept for S29-M.

I reviewed commit `4cb1fa81` and found 4 issues, all in `docs/specs/mise-native-dotfiles-plan.md`. The ReportFindings tool isn't available in this session (ToolSearch found nothing), so the findings are only in this message.

Nearly all of the diff is mirrored docs and agent reports copied word for word, so there's no code to hunt bugs in. The two changes that carry real logic are fine:
- **`goal-history.md`:** the `goal_history_errors` check returns `()`. Changing the goal text makes it fail, so the check does catch errors. The digest chain holds from `10d5655f…` to `8ca5e36d…`.
- **`.gitleaks.toml`:** the new allowlist entry is narrow and points at a file that exists. gitleaks 8.30.1 and betterleaks both scan `docs/research/kb` with rc=0 and no leaks.

**Findings:**

1. **`docs/specs/mise-native-dotfiles-plan.md:295` (with §4.7, lines 457–473) — high.** The runtime-source selector can never take effect. The plan sets the default `DOTFILES_SETUP_PROJECT` in `config.toml` `[env]` and assumes "conf.d loads after config.toml", so `~/.config/mise/conf.d/90-source.local.toml` would override it. mise works the other way: `conf.d` fragments load before `config.toml`, and `config.toml` wins.
   - **Doc evidence:** the mirrored `mise-docs/configuration.md:91` says fragments load "before the directory's regular config such as `config.toml`".
   - **Test:** in a scratch config directory on mise 2026.9.17, the same key in both files resolved to the `config.toml` value. A key found only in `conf.d` loaded, which shows `conf.d` was read.
   - **Result:** `setup-source git:<sha>` / `dir:<path>` write the override, every alias and task still runs the `main` worktree, and the audit log records the wrong source.
   - **Weak probe:** P0-B1 (line 744) only checks that a new key appears, so it would pass while this bug is present.
   - **Also:** when `MISE_GLOBAL_CONFIG_FILE` is set (the plan's first-apply command), `conf.d` isn't loaded at all.
   - **Fix:** put the override in `config.local.toml`, which does override `config.toml`.

2. **`docs/specs/mise-native-dotfiles-plan.md:534` (with line 477) — medium.** The launchd agent's `args` and `environment` fill in `{{ env.DOTFILES_SETUP_PROJECT }}` once, when `sched-apply` runs. `setup-source` (§4.7) only writes the conf.d file and never re-applies the agent. After a source switch, each scheduled run is split:
   - the guard runs from the old source path baked into the plist;
   - the `update:claude` task it starts through `mise run` reads the new value from the mise env;
   - the guard's self-report records the old source.

   If the `sha-<sha12>` worktree is later deleted, every 15-minute run fails with uv rc 2 until someone re-applies manually.

3. **`docs/specs/mise-native-dotfiles-plan.md:705` — medium.** The T4 check can never succeed. It runs `mise run bounded-wait -- --cmd 'test $(jq -r .trigger < <(tail -1 …)) = launchd'`, but `bounded_wait.py:47` runs the command with `sh -c`. On this Mac `/bin/sh` is bash 3.2 in POSIX mode, which rejects the `< <(…)` syntax. Tested directly: `syntax error near unexpected token '<'`, rc=2. The wait always times out (rc 124), so T4 reports failure even when the scheduled run worked. Use `tail -1 file | jq -r .trigger` instead.

4. **`docs/specs/mise-native-dotfiles-plan.md:704` — low.** T3(a) injects a failure with `CLAUDE_UPDATE_JSON=/dev/full`, but `/dev/full` doesn't exist on macOS (`ls` rc=1; `/dev/null` is there). The run still fails with rc 1, but from permission-denied when creating a file in `/dev`, not from the write failure the test says it exercises. The test would pass even if write errors weren't handled.

**Summary:**
- `docs/specs/mise-native-dotfiles-plan.md:295` — the conf.d source override is shadowed by the `config.toml` default, so the selector never takes effect.
- `docs/specs/mise-native-dotfiles-plan.md:534` — the launchd plist keeps the source path from the last `sched-apply`, so a switch splits guard and task across sources.
- `docs/specs/mise-native-dotfiles-plan.md:705` — T4's `bounded-wait --cmd` uses syntax `sh` rejects, so it always times out.
- `docs/specs/mise-native-dotfiles-plan.md:704` — T3(a) uses `/dev/full`, which doesn't exist on macOS, so it doesn't test write-failure handling.

This lane wrote nothing to `findings.md` or `progress.md`; the report above is meant for the coordinator to save.
