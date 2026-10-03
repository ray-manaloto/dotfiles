# #1614 worktree ship-blocker review (side lane launched by the mods fn-hook analysis agent, 2026-10-03)

> Verbatim appendix from the hand-back of agent aa2e7655954bbf191, persisted by coordinator 97ffeddb.

## Appendix: your mid-task #1614 question (separate side lane)

You asked mid-task for a subagent review of the "#1614 worktree ship blocker" note, so I launched a read-only general-purpose agent. Its report was not written to `findings.md`; please persist it verbatim under `docs/research/kb/reports/agents/`. Its scratch logs are in `/tmp/wt1614/`. The report, verbatim:

> I checked the side agent's note against the repo and reran the test. It is right that the main checkout's mise settings leak into `.claude/worktrees/`, but both of its suggested fixes have a problem. **Recommendation:** move #1614 up to right after PR #1622 (#1606), which is what Ray already ruled. Do not adopt "keep worktrees outside the main checkout": Ray already rejected it, and #1606 is about to block it.
>
> This was a read-only lane: I changed no repo files. The report, pytest logs and `mise config ls` captures are in `/tmp/wt1614/`. Nothing was written to `findings.md`, so please save this report verbatim under `docs/research/kb/reports/agents/`.
>
> ## Two things the note gets wrong
> 1. **#1614 being sixth goes against Ray's ruling.** His Q2=A ruling (about 14:50) says "#1606 next after #1620, then #1614" (`../dotfiles.worktrees/coord-28f1a8f7/docs/handoffs/session-2026-10-03g-errata.md:26`, repeated in `session-2026-10-03h.md:34`). The 03h ship queue, on the coordinator's unmerged branch (PR #1623), still lists it sixth (`session-2026-10-03h.md:75-78`), after the coordinator branch, L0, L1 and the research branch. The older 03g order had it fourth (`docs/handoffs/session-2026-10-03g.md:82-83`), and the three items before it are now done or open as #1622. Moving it up just restores the ruled order.
> 2. **Keeping worktrees outside the checkout was already rejected and will soon be blocked.** Ray rejected "revert to external worktrees" (`session-2026-10-03g.md:83`).
>    - Entering a worktree outside `.claude/worktrees/` always asks for approval. Permission rules, "don't ask again" and auto mode can't suppress that prompt; only `bypassPermissions` skips it (`$CC/worktrees.md:43`). That breaks zero-human-intervention.
>    - #1606 (PR #1622, open) adds a guard that denies exactly that `EnterWorktree` call.
>
> ## Mechanism, re-measured on mise 2026.10.1
> - **The failing test** is `tests/test_session_review.py::test_mise_requirement_task_exposes_required_root_and_configurable_limit` (defined at :1044, fails at :1106 with `assert 0 != 0`).
>   - It tells mise to ignore the worktree's own `mise.toml` and expects `mise tasks info session-requirements` to fail.
>   - Inside a nested worktree, mise walks up to the main checkout's `mise.toml`, which defines the same task, so the command succeeds and the assertion fails.
>
> | Where I ran the test | rc |
> |---|---|
> | `.claude/worktrees/codegen-default-group` | **1** |
> | `../dotfiles.worktrees/llvm23-20261002` (outside) | 0 |
> | main checkout | 0 |
> | same inner worktree with `MISE_CEILING_PATHS=<main>/.claude/worktrees` | **0** |
>
> - **What leaks:** from the inner worktree, `mise config ls` also lists the main checkout's `mise.toml`, `mise.local.toml` and `.config/mise/conf.d/shared.toml`.
> - **The ceiling works** when set to `<main>/.claude/worktrees`, to the worktree itself, or to `<main>/.claude`.
>   - ⚠️ A non-canonical `$wt/..` silently does nothing: the main checkout's files stay listed and rc is still 0.
>   - This fits mise's rule that the ceiling directory itself is excluded (`settings.toml:430-452`, KB mirror).
> - **The leak is wider than this one test.** Without the ceiling, the old-base worktree picks up `DEVCONTAINER_SSH_PORT` from the main checkout's gitignored `mise.local.toml`. It also picks up two tasks, `coordinator-handoff` and `session-start`, that exist only in the main checkout's newer `mise.toml` (:1695, :1702). Fixing only the test would hide that.
> - **Why every ship from `.claude/worktrees` fails:** ship always runs the full pytest suite from the worktree. It runs either as ship's own gate or in the hk pre-push hook (`python/src/dotfiles_setup/pr.py:347-401`, run from the worktree at :448). Docs-only branches get no exemption. Shipping from a linked worktree is otherwise allowed, except for devcontainer changes (`pr.py:612-623`, #1481).
> - **Native options:**
>   - mise's `ceiling_paths` / `MISE_CEILING_PATHS` is the built-in mechanism for this, and it can be set in the repo's tracked `.miserc.toml` (which today holds only `auto_env = false`).
>   - Claude Code has no setting to place worktrees elsewhere; its only worktree settings are `baseRef`, `bgIsolation`, `sparsePaths` and `symlinkDirectories` (`$CC/settings-reference.md`).
>   - Moving worktrees would need a `WorktreeCreate` hook (`$CC/worktrees.md:220`), which turns off `.worktreeinclude` (:271).
>   - The earlier research report (`docs/research/kb/reports/agents/mise-claude-worktrees-research-2026-10-03.md`, untracked in the main checkout) already covers this. I spot-checked its key claims and they hold.
>
> ## Proposals
> **P1 (recommended): ship #1614 right after #1622 merges.** Add `ceiling_paths = ["{{ config_root | dirname }}"]` to `.miserc.toml`, with a lint/verify contract and a fixture test, per the issue's acceptance list.
> - PRO: matches Q2=A; one config line plus gates, research already done; its own branch carries the line, so it ships from `.claude/worktrees`; covers Claude, codex lanes, hk and the devcontainer with no env plumbing.
> - CON: only branches containing the line are fixed, so held lanes must rebase; `mise -C <wt>` run from outside still leaks; a template render error would break every mise command, so the gate is required; queue items 2-5 wait one PR.
>
> **P2 (interim, until #1614 lands): prefix ships from inner worktrees** with `MISE_CEILING_PATHS=<main>/.claude/worktrees mise run ship`, using an absolute, canonical path.
> - PRO: no code change; the single test passed with this prefix (the test copies the environment, :1051); no worktree moves and no approval prompts.
> - CON: I did not run a full ship, so passing the variable through `git push` into the pre-push hook is inferred, not measured. I also didn't check whether `hook_guard` allows the prefix. A typo like `$wt/..` silently does nothing, and codex lanes won't get it automatically.
>
> **P3 (not recommended, the note's idea): a standing rule to keep worktrees outside the checkout.**
> - PRO: shown to pass (llvm23, rc=0).
> - CON: Ray rejected it (03g:83); every entry prompts for approval (`$CC/worktrees.md:43`); the #1622 guard will deny it; moving worktrees disrupts running lanes.
>
> **P4 (fold into P1): make the test independent of where the worktree sits** by setting `container_env["MISE_CEILING_PATHS"] = str(REPO_ROOT.parent)`.
> - PRO: about 2 lines; arms the fixture per `.claude/rules/probes-need-a-control-arm.md` rule 8.
> - CON: on its own it only hides the symptom, while the real leak (stray env var, foreign tasks, and a possible parent `mise.lock` rewrite that another project reported) continues.
>
> **P5 (current fallback, the 03g step-2 recipe): ship from the main checkout.** Remove the worktree, `git switch` the branch in the main checkout, then ship.
> - PRO: shown to work (rc=0 in the main checkout).
> - CON: the main checkout leaves `main` and can hold only one branch at a time, so ships line up behind each other; it interrupts the lane; the watcher alerts if `main` is off-branch for more than 30 minutes.
>
> **Recommendation:** P1 with P4 in the same PR, and P2 only for ships that can't wait for #1614. Reject P3. After #1614 lands, rebase or relaunch the lanes in `.claude/worktrees` (agent-ac4032eba1703a858, codegen-default-group, coord-97ffeddb, handoff-automation-research, L0, L1) so they get the line.
>
> ## GitHub repos touched
> - [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): issues #1614 and #1606; PRs #1622 and #1623 (state); `pr.py`, the test file, `.miserc.toml`, the handoffs
> - [jdx/mise](https://github.com/jdx/mise): `settings.toml` `ceiling_paths` semantics (KB offline mirror)
> - [anthropics/claude-code](https://github.com/anthropics/claude-code): `worktrees.md` and `settings-reference.md` (KB offline mirror)
