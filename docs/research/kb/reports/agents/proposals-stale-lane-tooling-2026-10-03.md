# Stale lane tooling: which tree a lane's hooks load from, why the LLVM lane errs, and what to change

> Persisted verbatim at receipt by coordinator 28f1a8f7, 2026-10-03. Producer: Plan subagent (read-only), on Ray's
> request relayed by the handoff-automation lane. Coordinator action on receipt: the main checkout was returned to
> `main` (a49c28b9) — §0's immediate operational step.

This lane was read-only. I wrote nothing to `findings.md` or `progress.md`, so please persist this report. Every probe was read-only: `git` reflog/log/ls-tree, `jq` over `~/.claude/jobs` and the session transcripts, `claude agents --json`, `gh issue view`, `gh api search/issues` and the GraphQL discussions search.

## 0. Urgent finding: the main checkout is not on `main`, and every session launched from it has lost both handoff hooks

- **Main checkout state now:** `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles` is on `docs/lane-completion-protocol`.
  - It is 21 commits behind `origin/main`, and its merge-base `aeeb9164` (Oct 2 11:22) predates #1583.
  - `git ls-tree HEAD .claude/skills/` has no `coordinator-handoff` and no `session-start`.
  - Reflog: `14:58:04 -0500 checkout: moving from main to docs/lane-completion-protocol`.
- **What every main-launched session logged within 30 seconds of that switch:**
  - `session-start: hooks.json changed — names no hooks module now; hooks/register.ts unloaded`
  - `coordinator-handoff: plugin.json changed — … unloaded`
  - Sessions affected: 6fae0fec at 19:58:32Z, coordinator 28f1a8f7 at 19:58:41Z, watcher 7585361b at 19:58:31Z.
- **Control arm:** the three sessions launched with a worktree cwd (1d335db0 L0, bee298cf L1, 54a3c59c model-registry) logged 0 such lines.
- **Consequence:** the coordinator, the watcher and the LLVM lane currently have no auto-handoff trigger at all.
  - The LLVM lane's "decide rc 2" did not get fixed. It went quiet because the hook was unloaded.
- **This is not a one-off.** The main checkout left `main` 11 times today (`docs/handoff-2026-10-03{,d,e,g}`, `docs/review-batch-reports-…`, `docs/lane-g-reports`, `docs/lane-completion-protocol`, and others).
- **Correction to the framing:** "hooks load from MAIN" really means hooks load from whatever branch the main checkout has checked out, live.

## 1. Which tree a lane's hooks load from, established with evidence

**Docs:**
- Project-scope `@skills-dir` plugins "load only from the `.claude/skills/` of the session's primary working directory" (`$CC/plugins-reference.md:402`).
- The primary working directory is the launch directory until `/cd` moves it (`$CC/permissions.md:542,558`).
- `EnterWorktree` moves "project configuration such as CLAUDE.md and settings" (`$CC/worktrees.md:43`). It does not say that it moves `@skills-dir` plugins.
- `${CLAUDE_PROJECT_DIR}` "stays put" (`worktrees.md:46-49`).

**Job records** (`~/.claude/jobs/<id>/state.json` `.cwd`, the launch cwd) against `claude agents --json` (the current cwd):

| Session | Launch cwd (state.json) | Current cwd | Hook tree | Evidence |
|---|---|---|---|---|
| 6fae0fec llvm-23-bump | main checkout | wt llvm23 | **main checkout (live HEAD)** | gained `coordinator-handoff` in its skill listing at 03:12:16Z (transcript line 1069). That was 4 min after the main checkout switched to `feat/coordinator-auto-handoff` (reflog 22:08:46 -0500 = 03:08Z) and 41 min **before** #1583 merged (03:53Z). Lost both hooks at 19:58:32Z. Its own worktree has no `coordinator-handoff` dir |
| 8d6e7252, 2ed2df92 | main checkout | wt | main checkout (P14) | 0 unload lines, **inconclusive**: the last transcript writes were 19:42:58Z and 19:43:43Z, before the switch, so the sessions were idle or quiescent |
| 1d335db0 L0, bee298cf L1, 54a3c59c | their wt | their wt | **own branch** | 0 unload lines (control) |
| 28f1a8f7 coord, 7585361b watch (controls) | main checkout | main | main checkout | unload lines at 19:58Z |

**What this establishes:**
- **Hooks load live from the launch tree.**
  - Removing a plugin's manifest or hooks file in the main checkout unloads the hook in every session launched there.
  - Adding a plugin dir is picked up mid-session: the skill listing gained `coordinator-handoff` at 03:12Z.
- **Docs-versus-runtime gap:**
  - `skills.md:255` and `plugins-reference.md:407` say `hooks/` changes need `/reload-plugins`.
  - The runtime does watch `plugin.json` and `hooks.json`.
  - The vendored types say a reload refreshes "changed modules only" (`.claude/types/claude-code.d.ts:3545`).
  - **Not yet proven:** whether an edit to the *content* of `register.ts` (as a `git pull` after a land produces) hot-reloads with no `/reload-plugins`. This is armed below (A1).

## 2. Why the LLVM lane errs: yes, it is the inverse of D1

- **The hook comes from the main checkout and the CLI from the lane's branch.**
  - `origin/main:.claude/skills/coordinator-handoff/hooks/register.ts`, in the CLI-call block around line 115: `projectDir = (await $.env.get("CLAUDE_PROJECT_DIR")) ?? (await $.session.root())`, then `uv run --project python dotfiles-setup …` with `cwd: projectDir`.
  - `session-start/hooks/register.ts` (lines ~106-108) has the same pattern.
- **`$.session.root()` follows `EnterWorktree`** (d.ts:2362-2368), so it resolves to `dotfiles.worktrees/llvm23-20261002`.
  - That worktree is at `87599224` with merge-base `46d87389`, 13 commits behind `origin/main`, and it has no `coordinator_handoff.py`.
  - So `decide` hits argparse "invalid choice" and exits rc 2.
  - The earlier diagnosis (`origin/main:docs/research/kb/reports/agents/llvm23-lane-hook-errors-2026-10-03.md`) ran the control arm: `main.py` registers the subcommand on main (`:45-48`) and not in the lane.
- **Deduction on `CLAUDE_PROJECT_DIR`:** at the time of the 19:16Z error, the main checkout was on `main` and had #1583.
  - If `$.env.get("CLAUDE_PROJECT_DIR")` had returned the main checkout (the docs value), `decide` would have succeeded.
  - So in a function hook the variable is either unset (consistent with `ps eww`, which shows no `CLAUDE_PROJECT_DIR`) or holds the worktree.
  - **Either way the CLI ran from the worktree.** That supports the correction of research F1 (`session-handoff-automation-research-2026-10-03.md:43`): "CLAUDE_PROJECT_DIR is the lane's tree" is not the documented semantics, and is not needed to explain the error.
- **D1 as specified fixes this exact shape.** With the CLI taken from `git toplevel($.plugin.root)` (spec §0 D1, §2 `cliProject`), the hook from the main checkout uses the main checkout's CLI.

## 3. Options, with the recommended one first

### (E) Recommended: launch from the main checkout and `EnterWorktree` under `.claude/worktrees/`, keep the main checkout pinned to `main`, keep D1 as specified, and keep a reload arm plus the post-land notice

**Composition:**
1. **Lane-launch policy (option c, scoped).**
   - Create the lane worktree under the main checkout's `.claude/worktrees/<lane>`.
   - Launch `claude --bg` from the main checkout. The brief's first step is `EnterWorktree(path)`.
   - Hooks then come from the main checkout, and the code being edited is in the lane's branch.
2. **Main-checkout pin (new invariant).**
   - The main checkout's HEAD is always `main`.
   - The coordinator does docs and handoff commits in its own worktree. 28f1a8f7 already works in `coord-28f1a8f7`.
   - Enforce it in three places:
     - a doctor check;
     - the hooks report `n/a (main checkout on <branch>)` instead of silently unloading;
     - `ship` / `session-handoff` refuse to `git checkout <branch>` in the main checkout.
3. **D1 unchanged.** The CLI comes from the hook's own tree. For an `EnterWorktree` lane that tree is the main checkout.
4. **Reload.** `land_main` already runs `checkout main && pull --ff-only` in the main checkout (`python/src/dotfiles_setup/pr.py:1050-1051`).
   - The live watch may reload the modules by itself (arm A1).
   - If A1 shows that content edits are not hot-reloaded, add the per-tree generation marker Ray chose (proposals report Defect 3 option A) as the backstop.
5. **D4 notice.** Its purpose narrows to code currency: lanes still rebase so their *changes* build on current `main`. It no longer carries tooling.

**PRO:**
- It is the only option with live, control-armed evidence that one change to the main checkout reaches every session launched there with no action (§1: 03:12Z gain, 19:58Z unload; three worktree-launched controls show nothing).
- That is Ray's "merge once, every session picks it up", delivered by the harness plus the existing land pull.
- Hooks and CLI come from the same tree (D1), so no new skew class appears.
- It is compatible with Ray's lane-rule ruling (role by name, placement from `$.session.root()`; proposals report lines 60-70).
  - For these lanes `session_root` is the worktree.
  - `main_checkout(session_root) == main_checkout(plugin_root)` holds.
  - So the role test reads "lane".
- `.claude/worktrees/` targets do not prompt (`worktrees.md:41-43`; `parallel-work-split/SKILL.md:114-119`). That removes the cause of the standing launch rule.
- No user-level files are touched.

**CON:**
- **It reverses the standing memory rule.** `feedback_launch_lane_inside_worktree` and `parallel-work-split/SKILL.md:99-119` currently say "launch inside the worktree, never EnterWorktree".
  - That rule's justification is a prompt that fires only for paths outside `.claude/worktrees/`.
  - It needs Ray's ruling, plus an edit to the memory and to the skill. Note that #1606 (OPEN) is the coordinator-side version of the same prompt.
- **Placement change.** Lanes move from `../dotfiles.worktrees/` to `.claude/worktrees/`.
  - #1614 (OPEN): nested `.claude/worktrees` inherit the main checkout's mise config.
  - #1554-1555 concern worktree mounts.
- **The first turns run before `EnterWorktree`**, in the main checkout. That is the role-measurement arm already noted in the proposals report (line 76).
- **A lane cannot live-test its own hook edits.** Its hooks come from `main`. It needs harness tests or a throwaway session launched in its worktree. This can also be a PRO, because a lane cannot break its own guard.
- **The pin is a discipline.** It must be enforced by code, because today's 11 switches show it does not hold by habit.
- **Isolation checks.** The `EnterWorktree` isolation checks block Bash with a main-checkout cwd and `git -C <main>` (`worktrees.md:89-96`).
  - `mise run land` from such a lane writes to the main checkout from python (spec P8, a residual).
  - Landing should stay coordinator-only.

### (F) Alternative: a pinned tooling worktree loaded with `--plugin-dir`, keeping lanes launched inside their worktree

**Design:**
- A detached worktree, for example `dotfiles.worktrees/_tooling`, always at `origin/main` and never edited. `land` and `sync-to-main` move it with `checkout --detach origin/main`.
- Lanes launch in their own worktree with `--plugin-dir <_tooling>/.claude/skills`. A folder of plugins is supported from 2.1.265, and "children added or removed while running are picked up" (`$CC/changelog.md:448`; `cli-reference.md:113`).
- D1 resolves the CLI from `_tooling`.

**PRO:**
- Keeps the current launch rule and the placement under `../dotfiles.worktrees/`.
- The tooling tree's HEAD is immune to anyone's branch work, which cures §0 structurally.
- `--plugin-dir` is per session and survives `/bg` respawn (`changelog.md:3091`; `respawnFlags` carries flags, as in `6fae0fec/state.json`).
- No user-level files.

**CON:**
- **Unprobed same-name collision.** The worktree's own `.claude/skills/<x>` also loads as `<x>@skills-dir`.
  - The docs only cover `--plugin-dir` against a *marketplace* plugin of the same name (`plugins.md:299`; #72369 closed).
  - If both load, hooks double-fire. Mitigation: disable `<x>@skills-dir` by name in the lane's `--settings`.
- **Content hot-reload of `--plugin-dir` modules is unprobed.**
- **No atomic swap.** A checkout in place can race a hook mid-read. Per-sha directories with a symlink swap would fix that, but symlink-watch semantics are unknown.
- **One more tree to keep healthy:** uv venv sync and mise trust (#1614-style).
- **Every launcher must add the flag.** That includes `launch_argv` (`coordinator_handoff.py:109,733`) and `parallel-work-split`.

### (B) Per-turn or post-land rebase of lane worktrees, as spec §3g `sync-to-main`

**PRO:**
- Fixes code currency, which (E) and (F) do not address.
- It is already the specified D4 path.
- Prior art converges on one policy: grove#178 (rebase before evaluate; on conflict, fail with the file list); #77869's hook (ff-only, never resolve, `git merge-tree` report, idempotent notice, `flock`).

**CON:**
- **Does not fix hooks for `EnterWorktree` lanes.** Their hooks never come from the worktree (proposals report line 183).
- **For worktree-launched lanes it fixes tooling only at a boundary,** and only when the rebase is clean and the tree is not dirty.
- **The 6fae0fec lane is held** ("waiting for lock-format to land") and cannot rebase, which is exactly when stale tooling persists.
- **Auto-rebasing a working tree mid-task** rewrites the files the agent has open and invalidates its mental model.

**Policy if adopted:**
- Only at a boundary the lane declares, never per turn.
- Refuse on a dirty tree (rc 2) and do not stash: the stash stack is shared.
- On conflict, `rebase --abort`, then report `git merge-tree --write-tree --name-only` files via a queued question (rc 3, already in §3g).
- Never auto-resolve.
- Hold the lock across the fetch and the rebase.

### (D) D1 variant: CLI from `main_checkout(plugin_root)`

- **Not recommended.**
- **For `EnterWorktree` lanes it is a no-op:** `plugin_root` is already in the main checkout, so `main_checkout(plugin_root) == toplevel(plugin_root)`.
- **For worktree-launched lanes it creates the reverse skew:** an old branch hook against a new main-checkout CLI.
  - `isSkew` catches only argparse rc 2 (spec §2).
  - Schema or `REASONS` growth surfaces as "decide output not JSON" ERROR (proposals report, Defect 3 option C CON; `register.ts:32-36,90`).
- **It inherits §0:** the main checkout is not reliably `main`.
- **PRO:** one line, and it fixes the CLI half for worktree-launched lanes. That is only safe with a versioned JSON protocol (`decide --protocol N`) that the hook checks, which brings back the D1 "n/a" path.

### (A) Out-of-branch code: a personal-scope `~/.claude/skills` plugin or a `uv tool` CLI

**PRO:**
- **Personal scope** loads "in every project" with no trust gate (`plugins-reference.md:396`). It is independent of launch cwd and branch, so it is the cleanest "merge once" for hooks.
- **A `uv tool` CLI** is versioned and atomic.

**CON:**
- **Both are user-level writes, which the standing rule forbids.**
  - `feedback_no_user_level_file_updates` explicitly names `~/.claude/skills/**`.
  - `uv tool` writes `~/.local/share/uv/tools` and `~/.local/bin`.
  - Spec §4 says "No user-level writes". Ray would need to rule.
- **Cross-project blast radius.** The hooks would fire in knowledge-base and every other repo, and would need a repo guard.
- **Personal scope is not git-tracked by the session's repo,** so "merge" becomes "merge, then install". Some installer has to run after each land, which is user-level automation (#1397 is already the parking lot for user-level state).
- **A `uv tool` CLI fixes only the CLI half.**
  - Hooks still come from the tree.
  - `__file__` moves into site-packages, so `DOTFILES_PROJECT_ROOT` becomes mandatory (spec §2 `main.py:3242`).
- **A repo-hosted marketplace** (a variant: a `git-subdir` source pinned to `ref: main`, `plugin-marketplaces.md:262,276`) installs at project scope and is shared with worktrees (`worktrees.md:228`).
  - It needs `claude plugin update` after each land, plus `/reload-plugins` ("keep using the previous version's path", `plugins-reference.md:736`).
  - It has open bugs: #92761 (a linked worktree loads the first same-repo row) and #94547 (truncated cache dir).
  - `$.plugin.root` becomes a cache dir with no git toplevel, which breaks D1's `cliProject`.

### (G) Status quo: D1 plus `n/a (CLI skew)`, accepting stale tooling until rebase

- **PRO:** zero new mechanism.
- **CON:** it makes the failure visible but not fixed. The handoff never fires in a stale lane, which is today's 6fae0fec state.

## 4. External prior art and native support (probes with control arms)

**#77869 (anthropics/claude-code):**
- `gh issue view` returns `CLOSED / NOT_PLANNED`, closed 2026-09-18 by github-actions as **inactive**. That is not a design rejection.
- It concerns syncing worktree to main (an ff-forward of the lane branch into the main checkout), the opposite direction from ours. Its reference implementation is mwfoutch/claude-worktree-autosync (0 stars, last pushed 2026-07-28).

**Open upstream issues on the same class:**
- **#97349** "Long-lived worktree sessions silently run stale hook scripts — add a drift signal and an explicit hook script source". It says auto-sync is unsafe on dirty trees.
- **#99145:** desktop worktree sessions load skills from the main checkout.
- **#99012:** `--project-config-root <main checkout>` runs hooks in the config root.
  - This undocumented flag is a possible native form of (F).
  - It is not used: it is undocumented, and the desktop app owns it.
- **#83953:** project hooks are branch-local in worktrees.
- **#88747:** an absolute `core.hooksPath`, so worktrees run the main checkout's git hooks.
- None is resolved, so there is **no native fix to adopt**.

**Search counts and controls:**
- `search/issues` `repo:anthropics/claude-code worktree stale hook is:issue` returned 328; the scoped `worktree rebase main sync` query returned 13.
- Control: the `77869` query returned exactly 1 (the target), so the searches index the target.
- **Discussions:** `repo:anthropics/claude-code worktree` returned 0. Control: `hasDiscussionsEnabled=false`, so that 0 is not evidence.
  - A cross-GitHub discussions query returned 25.
  - soliplex/lab_bench#30 is the "frozen tooling snapshot on long-lived branches" analog. It notes GitHub runs workflows from the default branch, i.e. tooling from the default branch and data from the branch (not separately probed).

**Other projects:**
- bpamiri/grove#178 (OPEN): rebase before evaluate; fail on conflict with the files listed.
- daniel-ospina/agent-infra#1125: a "clean-but-diverged hub" deadlocks the agents' own tooling. It is the same hazard as §0: the shared checkout's HEAD drifts and the tooling breaks.

## 5. Arms the implementation must add

- **A1 (live; decides whether the generation marker is needed).**
  - Run a throwaway session launched in the main checkout. Change only the **content** of `coordinator-handoff/hooks/register.ts`, for example a status string, via a commit plus `git pull` on `main`.
  - Assert the new status appears with no `/reload-plugins`.
  - Control: a session launched in a worktree on an old branch keeps the old string.
  - Mutation: revert the commit, and the status reverts.
- **A2 (§0 guard).**
  - Doctor check: main checkout `HEAD == refs/heads/main`.
  - Hook status: `n/a (main checkout on <branch>)`.
  - Unit: a fixture on a docs branch reports n/a. Control: on `main`, OK.
  - `ship` and `session-handoff` refuse a `checkout <branch>` in the main checkout. A harness asserts rc 2.
- **A3 (launch policy).**
  - A lane launched from the main checkout that runs `EnterWorktree(.claude/worktrees/<lane>)` gets no prompt (state never `blocked` within 5 min).
  - `$.session.root()` = the worktree, logged once in DRY-RUN.
  - The role resolves to "lane".
  - Control: `EnterWorktree` to `../dotfiles.worktrees/x` prompts. That is the reason for the memory rule, and also the regression guard.
- **A4 (D1 on the LLVM shape).**
  - Bun harness: plugin root in the main checkout, `session.root()` = a worktree whose `python/` lacks `decide`.
  - D1 runs the main checkout's CLI with rc 0.
  - Mutation: restore `CLAUDE_PROJECT_DIR ?? session.root()`, and the harness goes red with rc 2.
- **A5 (reverse skew after land).** If A1 fails, apply the proposals report's generation-marker arms: the reload is queued once, and nothing happens without a change.
  - L5 control: a worktree-launched lane does not reload.
- **A6 (rebase policy, if B is kept).**
  - Dirty tree gives rc 2 and no stash entry is created. The stash list must be unchanged, because the stack is shared.
  - A conflict fixture gives `rebase --abort`, rc 3, and the merge-tree file list.
  - A clean fixture gives rc 0.
- **A7 (only if F is chosen).** Probe the same-name collision of `--plugin-dir` and `@skills-dir`: count hook invocations per event, with an expected count of 1. Also run A1 against a `--plugin-dir` module.

## 6. Rulings Ray needs to make

1. **Retire or rescope `feedback_launch_lane_inside_worktree`** in favour of (E): launch from the main checkout and `EnterWorktree` under `.claude/worktrees/`. This includes the placement move away from `../dotfiles.worktrees/`.
2. **Adopt the main-checkout-pinned-to-`main` invariant,** enforced by code. The coordinator would never check out branches in the main checkout.
3. **Confirm (A) stays out** under `feedback_no_user_level_file_updates`, or grant a specific exception.
4. **Immediate operational step:** return the main checkout to `main`. Until then, the coordinator, the watcher and 6fae0fec have no `coordinator-handoff` or `session-start` hooks.

### Critical files for implementation
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/.claude/skills/coordinator-handoff/hooks/register.ts
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/.claude/skills/session-start/hooks/register.ts
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-28f1a8f7/python/src/dotfiles_setup/pr.py (lines 1031-1063, `land_main` checkout/pull)
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/coord-28f1a8f7/.claude/skills/parallel-work-split/SKILL.md (lines 99-119, launch rule)
- /Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/docs/specs/session-handoff-automation.md (§0 D1/D4, §3g, P14)

## GitHub repos touched
- **anthropics/claude-code**, read only:
  - viewed #77869, #97349, #99145, #83953, #99012, #92761, #88747, #61866;
  - ran `search/issues` queries;
  - checked `hasDiscussionsEnabled` through GraphQL.
- **ray-manaloto/dotfiles**, read only: #1606 viewed; `search/issues` for skew and main-checkout issues (#1397, #1614, #1020 surfaced).
- **bpamiri/grove**, read only: #178.
- **daniel-ospina/agent-infra**, read only: #1125.
- **mwfoutch/claude-worktree-autosync**, read only: repo metadata.
- **soliplex/lab_bench**, read only: discussion #30.
- Cross-GitHub discussions GraphQL search (no repo-specific target).
