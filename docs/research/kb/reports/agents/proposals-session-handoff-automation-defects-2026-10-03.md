# Proposals: three defects in the session-handoff-automation spec

> Persisted verbatim at receipt by coordinator 28f1a8f7, 2026-10-03. Producer: Plan subagent (read-only), commissioned
> on Ray's request for "cited research proposals w pros/cons". Inputs: spec rev 1 5c3c155d, rev 2 3af1dae6, and
> `premise-verifier-session-handoff-automation-5c3c155d.md`.

I reviewed rev 1 (`5c3c155d`) and re-read rev 2 (`3af1dae6`) as you asked; rev 2's three [HELD] fixes are scored as one option each.

**Recommendations:**
- **Lane discriminator:** the session name decides the role. Placement comes from `$.session.root()`, which the hook already has, not from a per-turn `claude agents --json` call.
- **plugin-health:** rev 2's fix is right. The one change is that the "session project" value must be `$.session.root()`, not `CLAUDE_PROJECT_DIR`. Leave `install-doctor/hooks/register.ts:233` alone.
- **Reload:** don't use rev 2's per-session marker. A reload signal keyed to the plugin's own tree is needed, because `mise run land` already pulls the main checkout (`pr.py:1050-1051`), and that leaves every session whose hooks load from main running stale hooks.

This lane is read-only, so nothing was written to `findings.md` or `progress.md`; please persist this report. Every probe was read-only: `jq` over `~/.claude/jobs/*/state.json` and transcripts, `claude agents --json`, and `ps eww`.

---

## Defect 1: the lane discriminator (MISSING-1)

### Probe: every candidate signal against real sessions (2026-10-03 ~19:50Z)

"wt" means a linked worktree of dotfiles. `agents cwd` is the live `claude agents --json` value. "Transcript cwd" comes from the `.cwd` field of the session's own transcript lines.

| Session | Role by name | job `cwd` (state.json) | `linkScanPath` project dir | agents `cwd` | transcript cwd | How it moved |
|---|---|---|---|---|---|---|
| 6fae0fec llvm-23-bump | lane | **main** | wt llvm23 | **wt** llvm23 | main ×43, then wt ×1646 | `EnterWorktree(path)` |
| 8d6e7252 saved-searches-1502 | lane | **main** | wt | **wt** | main ×38, then wt | `EnterWorktree(path)` |
| 2ed2df92 lane-G | lane | **main** | wt | **wt** | main, then wt | `EnterWorktree(path)` ×2 |
| 1d335db0 L0-urgent-code | lane | wt `.claude/worktrees/L0-urgent-code` | wt | wt | wt | launched in the wt |
| bee298cf L1-docs-rules | lane | wt | wt | wt | wt | launched in the wt |
| 54a3c59c model-registry | lane | wt `dotfiles.worktrees/…` | wt | wt | wt | launched in the wt |
| **28f1a8f7 coordinator (control)** | coordinator | main | main | **main** | main ×191, then **wt** `coord-28f1a8f7` ×150 | shell `cd` (transcript line 192), no `EnterWorktree` |
| **a8d7baf5 coordinator (control, stopped)** | coordinator | main | **wt** `handoff-2026-10-03c` | (not listed) | main, then wt | `EnterWorktree` ×2 |
| **f6687621 / 5990b71c / 4bcfb646 coordinators (control)** | coordinator | **wt** `coordinator-auto-handoff-…` | wt | — | — | launched in the wt |
| **7585361b dotfiles-20261003.watch (control)** | watch | main | main | main | main / `.agent/state/watch` | none |
| **998ab91b dotfiles-20261002.watch (control)** | watch | **wt** fanout-fixes | **wt** lane-completion | **wt** lane-completion | wt | `EnterWorktree(path)` |
| 38ae1474 dotfiles-20261001.s29-00b | lane-shaped name | main | main | — | — | none: a lane name in main |
| kb-*, ledger-* | — | other repos | — | — | — | the hook is absent there (`ls` of `.claude/skills/coordinator-handoff` fails in both repos) |

**What this shows:**
- **No worktree signal tells the roles apart.** Every route marks at least one coordinator or watcher as "in a worktree":
  - job cwd: f6687621 and 998ab91b;
  - `linkScanPath`: a8d7baf5 and 998ab91b;
  - agents cwd: 998ab91b;
  - transcript cwd: 28f1a8f7.
- **The name is the only signal that partitions the roles in all 47 records.** Name precedence must therefore come before any cwd test.
- **Only `EnterWorktree` (a session move) changes the agents `cwd`. A shell `cd` does not:** 28f1a8f7 still reads main.
  - That is exactly the documented `$.session.root()` contract: "where it started, or where `/cd`, a host's directory change or a worktree move took it. A shell `cd` during the session does not move it" (`.claude/types/claude-code.d.ts:2362-2368`).
  - By contrast, `$.session.cwd()` is "the directory the session runs in" (`:2358-2360`).
- **`CLAUDE_PROJECT_DIR` cannot be the signal.** It "stays put" on `EnterWorktree`; only the hook input's `cwd` follows (`$CC/hooks.md:626-630`, `$CC/worktrees.md:46-49`).
- **Exec-time env has no role signal.** The `ps eww` env of 5 live sessions (6fae0fec, 28f1a8f7, 1d335db0, 998ab91b, 7585361b) shows `PWD=<main>` for all of them, L0 included, plus `CLAUDE_CODE_SESSION_KIND=bg`. There is no `CLAUDE_PROJECT_DIR`.
  - Inference: the daemon spawns sessions, so a shell-exported variable at `claude --bg` time does not reach the session. Further evidence: `providerEnv` stores only AWS vars (`6fae0fec/state.json:38-41`).
- **F1 is indirect live evidence that `$.session.root()` follows `EnterWorktree`.** The hook resolved its CLI cwd as `$.env.get("CLAUDE_PROJECT_DIR") ?? $.session.root()` (`coordinator-handoff/hooks/register.ts:115`) and got the pre-#1583 worktree's CLI (rc 2).
  - The docs say `CLAUDE_PROJECT_DIR` stays at main, so the worktree most likely came from the `session.root()` fallback.
  - This is not proven: an in-process setenv is invisible to `ps`. The research report's claim that `CLAUDE_PROJECT_DIR` "is the lane's tree" (`session-handoff-automation-research-2026-10-03.md:43`) contradicts the docs and should be corrected.
- **Name grammar:** do NOT reuse `CONFORMING_NAME_RE` (`session_start.py:69-71`). It rejects the live lanes L0, L1, lane-G, model-registry and handoff-automation-research, and `dotfiles-20261003.watch` (24 of 47 dotfiles names fail it).
  - Rev 2's `^dotfiles-.+\.[A-Za-z0-9._-]+$` matches all of them. It also matches a stamp with no feature (`dotfiles-20261002T204357.298786000-05`, with "feature" `298786000-05`), so the feature must be required to contain a letter.
- **Cost of `claude agents --json`:** 0.21 / 0.23 / 0.21 s over 3 runs with 23 rows, rc 0.

### Option A (recommended): role by name, placement from the hook's own `$.session.root()`
- **Change:**
  - The TS `decide` passes `--session-root "$(await $.session.root())"`. That is an in-process call the module already makes at `register.ts:115`.
  - `role_of(name, session_root, plugin_root)`:
    1. Not `^dotfiles-` → `None`.
    2. `.coordinator$` → coordinator; `.watch$` → watch. This happens before any cwd test.
    3. Otherwise the session is a lane if `main_checkout(session_root) == main_checkout(plugin_root)`, meaning same repo, and `session_root != main_checkout(session_root)`, meaning a linked worktree.
    4. A lane name not in a worktree returns a **visible** new reason `lane-unplaced` (status `handoff n/a (lane not in worktree)`), not a silent `None`.
- **PRO:**
  - No subprocess and no supervisor dependency.
  - Same semantics as the agents `cwd` that rev 2 measured: it follows `EnterWorktree` and not shell `cd` (d.ts:2362-2368), which matches the 6fae0fec and 28f1a8f7 rows above.
  - Unit-testable with a fake `$`.
  - The same-repo check stops a `dotfiles-*` name working in another repo (`dotfiles-20261002.fnox-provider`, cwd in `harness-evolution-ledger.worktrees/`) from passing as a lane.
- **CON:**
  - Live behaviour on 2.1.288 is unarmed: the types were written by 2.1.277 (d.ts:1), and the only evidence is F1, which is indirect.
  - It adds a `decide` argument, so an old CLI rejects it with argparse "unrecognized arguments" (rc 2). Rev 2's `isSkew` now covers that.
- **Required arm:** the lane's first measurement happens *before* `EnterWorktree` (6fae0fec has 43 main-cwd transcript lines first). The hook caches `not-below-limit` and re-checks once at the limit (`register.ts:228-231,248`). The spec must arm this sequence:
  - the first measure, with root = main, gives `lane-unplaced`;
  - a measure at or above 40% with root = worktree fires.
  - Mutation: drop the at-limit re-check and the test goes red. Without the re-check, the motivating lane never fires.

### Option B: rev 2's `claude agents --json` live `cwd`, read by python `decide`
- **PRO:**
  - The documented "supported way to read session state from outside Claude Code" (`$CC/agent-view.md:719`).
  - Measured correct on 6fae0fec. I re-confirmed it: agents `cwd` = `dotfiles.worktrees/llvm23-20261002`, while state.json `cwd` = main.
  - About 0.2 s per call. With the role cache, it runs only at the first measure and at or above the limit, not every turn.
- **CON:**
  - The docs never say the field follows a worktree move. The table says only "The working directory" (`:711`); `:81` covers only the `--cwd` filter.
  - It nests the `claude` CLI inside a hook-spawned `uv` process:
    - It depends on `claude` being on that PATH. The hooks hand down env explicitly, and plugin-health passes `DOTFILES_AMBIENT_PATH` because PATH differs (`plugin-health.ts:35,42`).
    - It can start the background service as a side effect (`agent-view.md:464,887`).
  - Matching must use `sessionId`, which is present only "when set" (`:716`).
  - It is test-hostile, needing a fake `claude`.
  - It reads a different source of truth from the one the hook already holds.
- **Use it as the fallback** when `--session-root` is absent, not as the primary.

### Option C: an explicit role at launch, `--settings '{"env":{"DOTFILES_SESSION_ROLE":"lane"}}'`
- **PRO:**
  - Explicit, with no inference.
  - `--settings` persists in `respawnFlags` (`6fae0fec/state.json:17-24`), so it survives `claude respawn`.
  - Readable with the literal `$.env.get("DOTFILES_SESSION_ROLE")`.
- **CON:**
  - 0 of 47 `respawnFlags` carry it today, so every live lane is unclassified until relaunched.
  - Every launcher, a human included, must remember it.
  - Unverified whether `settings.env` reaches `$.env.get` in a function hook.
  - It duplicates what the name already says.
  - A registration-file variant would race, because the session id is unknown until `--bg` returns.

### Option D: name only, with the placement check moved to `launch --role lane` (rc 2 when root is not a linked worktree)
- **PRO:** the simplest. The name alone partitions every probed record.
- **CON:**
  - A lane-named session in main (38ae1474 `s29-00b`) fires and runs the whole handoff before `launch` refuses.
  - Placement then fails late rather than as a status.

**Rejected by the probe:**
- job-record `cwd` (false negatives: 6fae0fec, 8d6e7252, 2ed2df92);
- `linkScanPath` (false positive: coordinator a8d7baf5; the docs also say `~/.claude/jobs` is "not a stable interface", `agent-view.md:731`);
- transcript cwd (false positive: coordinator 28f1a8f7, via a shell `cd`);
- `CLAUDE_PROJECT_DIR` (`hooks.md:626-630`);
- shell env at launch (see the `ps eww` evidence above).

### Arms the spec must add (it replaces rev 2 §5 item 3)
- **Positive:** 6fae0fec, 8d6e7252, 1d335db0 and 54a3c59c map to lane. Fixtures: name plus session_root.
- **Controls with a worktree root:**
  - 998ab91b `dotfiles-20261002.watch` with root = worktree must be **watch**;
  - a8d7baf5 and f6687621 coordinators with root = worktree must be **coordinator**.
  - Rev 2's control uses 28f1a8f7 with root = main, which a cwd-only rule also passes, so it proves nothing about name precedence.
- **Negatives:**
  - 38ae1474 `s29-00b` in main → `lane-unplaced`, visible;
  - `probe-nonconforming-lane-20261002` → None;
  - the stamp-only name `dotfiles-20261002T204357.298786000-05` → None;
  - `dotfiles-20261002.fnox-provider` with root in another repo → None.
- **Mutation:** evaluate the cwd test before the name test, and the 998ab91b control goes red.
- **Live (L1):** the F1-shape lane's status shows `$.session.root()` = the worktree path. Log it once in DRY-RUN. That turns the indirect evidence direct.

---

## Defect 2: P3 omission (`plugin-health.ts:36-41`) and `install-doctor:233`

**Evidence:**
- `plugin-health.ts:36-44` runs `uv run --project python dotfiles-setup plugin-health` with `cwd: CLAUDE_PROJECT_DIR` and no fallback. It is a `classic.SessionStart` hook (`:56`) that fails open and silent (`:49-51`). It has no `$.ui.status`, so today a skew is invisible.
- Python matches `claude plugin list --json` rows by `projectPath == project_root` (`plugin_health.py:255,281,290`), and `project_root` comes from `main.py:3242` / `Path.cwd()` (`:393-394`).
- `install-doctor:229-236` uses `$.session.root()` for the permit root. `:233` (`CLAUDE_PROJECT_DIR`) is reached only if that call throws, and a cached `baseline_path` from python takes precedence (`:227`).

### Option A (recommended): rev 2 (1), with one correction
- **Change:**
  - plugin-health gets the per-module `cliProject`/`isSkew` copy and `DOTFILES_PROJECT_ROOT`.
  - It gains a visible skew signal: a status line, or `additionalContext` "plugin-health n/a (CLI skew)".
  - `install-doctor:233` stays unchanged.
- **Correction:** rev 2 leaves "`<session project>`" undefined, and passes `cwd=CLAUDE_PROJECT_DIR` for coordinator-handoff. Define the session project once, in all four copies, as `$.session.root()`, falling back to `CLAUDE_PROJECT_DIR`. That is the same expression as `install-doctor:229-234`.
  - The point is consistency: python's `baseline_path`, which wins at `:227`, and the hook's fallback permit root then name the same `doctor.toml`.
  - For an `EnterWorktree` lane, `CLAUDE_PROJECT_DIR` = main, but `root()` = the worktree (`hooks.md:626-630`).
  - At `classic.SessionStart` the two coincide, except on a resume after a move, which is worth one arm.
- **PRO:** D1's objective becomes true for all four modules; minimal diff; the permit semantics are untouched.
- **CON:** a fourth copy of the resolver, held by the parity test. plugin-health's silent fail-open behaviour needs a new visible channel.

### Option B: plugin-health gets skew detection only; it keeps the `CLAUDE_PROJECT_DIR` CLI
- **PRO:** what it inspects does not change.
- **CON:** D1's objective ("never runs python code from a different git tree", rev 2 §1) stays false for one hook, and the F1 class remains open there.

### Option C: fold plugin-health's SessionStart check into session-start, which drops to three resolver copies
- **PRO:** less parity surface.
- **CON:** larger scope; it changes hook ordering and the `additionalContext` contract. Not justified by this defect.

**On `install-doctor:233`:**
- Recommended: leave it. Rejected alternatives:
  - pointing it at `DOTFILES_PROJECT_ROOT`: circular, because the hook sets that variable itself;
  - deleting the fallback (fail closed): defensible, since `CLAUDE_PROJECT_DIR` is the start dir and could permit main's `doctor.toml` from a moved session, but it changes behaviour for a path that is essentially unreachable.
- **Arm:** with no cached report and `root()` throwing, the permit accepts `<CLAUDE_PROJECT_DIR>/doctor.toml` and rejects `<plugin tree>/doctor.toml`. This proves D1 did not move the permit.

---

## Defect 3: §3g's skill calling the hook-only `$.command.run`

**Evidence:**
- `queue()` (`session-start/hooks/register.ts:80-84`) is the existing hook-side carrier, used at `:231-234`.
- `prompt.submit` (`:288-299`) fires for peer messages, notifications and schedules as well as typed prompts (`PromptOrigin`, d.ts:7017-7025; `session.receive` origins `peer-send-message` and others, `:9040-9075`). So it does fire in unattended lanes.
- `session.measure` fires "after each main-thread turn" (d.ts:3594-3595).
- `$.fs.exists`/`stat` exist (d.ts:2738+), so a marker check needs no subprocess.
- **The gap rev 2 misses:** `land_main` itself runs `git checkout main && git pull --ff-only` in the main checkout (`pr.py:1050-1051`).
  - After every land, every session whose hooks load from main runs old in-memory modules against a *new* on-disk CLI, which D1 resolves from that same tree. That is the reverse skew.
  - Affected sessions: the coordinator, the watcher, and every `EnterWorktree`-shape lane (6fae0fec, 8d6e7252, 2ed2df92; P14).
  - A per-session marker written by `sync-to-main` reaches only the caller.
  - Rebasing an `EnterWorktree`-shape lane's worktree does not change its hooks at all, because they load from main. The reload matters for main-checkout sessions and for lanes launched with a worktree cwd (the L0 shape).

### Option A (recommended): a generation marker per plugin tree, checked in `session.measure` and `prompt.submit`
- **Change:**
  - Writers: `sync-to-main`, and `land_main` after `pull --ff-only`, write `<tree>/.agent/state/plugin-generation` = HEAD sha.
  - Each module records the value it saw when registered.
  - On a change, it queues `reload-skills` and `reload-plugins --force` once, via the existing `queue()` pattern. The `measure` hook is the earliest point after the syncing turn; `prompt.submit` is the backstop.
  - Hosting it in session-start keeps one owner of reloads.
- **PRO:**
  - Covers every session loading from the moved tree, including those that never ran `sync-to-main` themselves.
  - Fires after the very turn that synced, with no extra prompt needed.
  - Uses only `$.fs` plus the existing `queue()`.
- **CON:**
  - `reload-plugins` in N sessions at once after each land.
  - The interaction with #1592 needs an arm, because the reloads swallow a pending launch prompt (rev 2 §0).
  - Unverified whether `/reload-plugins` after `EnterWorktree` re-reads the start dir or the moved root (`$CC/worktrees.md:43` says project configuration moves).

### Option B: rev 2 (3), a per-session marker plus `prompt.submit`
- **PRO:** small; the precedent is in place (`register.ts:80,232-233`); `prompt.submit` provably sees peer and notification origins.
- **CON:**
  - Covers only the session that ran `sync-to-main`, and misses the `land_main` pull at `pr.py:1050-1051`.
  - Lands one prompt later than option A.
  - Its marker path is in the main checkout under `session-start` state, which couples it to MISSING-4's `DOTFILES_PROJECT_ROOT` choice.

### Option C: accept stale hooks until restart; D1 skew is shown as `n/a`
- **PRO:** zero code; D1 already makes skew visible rather than an ERROR.
- **CON:** `isSkew` catches only argparse rc 2. A new CLI with an old hook fails as "decide output not JSON" whenever the `Decision` schema or `REASONS` list grows (`register.ts:32-36,90`), so it shows as ERROR, not `n/a`. The handoff trigger can then silently stop firing until `claude respawn`.

### Arms
- **Unit:**
  - A bun harness with a changed generation queues both reloads exactly once.
  - An unchanged generation queues nothing.
  - Mutation: drop the `land_main` writer, and a "land then measure" fixture goes red.
- **L5:** after a real `land`, a lane that did *not* run `sync-to-main` but loads hooks from main shows the reload in its log on its next turn.
  - Control: a lane launched in a worktree that has not synced shows no reload.

---

## Other findings
- **MISSING-7, live:** lane L0 (1d335db0) `respawnFlags` has no `crossSessionInbound: accept` (only `-n … --model`). Neither do lane-B, lane-E, lane-G or s29-00b. The D3 digest and D4 notice cannot reach them today, which confirms rev 2's `parallel-work-split` change is needed.
- **Name precedence also governs state placement.** Rev 2 routes coordinator-handoff state through `DOTFILES_PROJECT_ROOT`. For lanes, say whether per-session handoff state lives in `main_checkout(root)`, as `handoff-inbox` does, or in the worktree. A worktree is deleted on `claude rm`, which takes its state with it.

### Critical files for implementation
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/.claude/skills/coordinator-handoff/hooks/register.ts`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/python/src/dotfiles_setup/coordinator_handoff.py`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/.claude/skills/session-start/hooks/register.ts`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/.claude/skills/plugin-health/hooks/plugin-health.ts`
- `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research/python/src/dotfiles_setup/pr.py`

## GitHub repos touched
_None._ Sources were local only: the `handoff-automation-research` worktree at `5c3c155d` and `3af1dae6`, the knowledge-base offline `$CC` corpus, `~/.claude/jobs` records and transcripts, live `claude agents --json`, and `ps eww`.
