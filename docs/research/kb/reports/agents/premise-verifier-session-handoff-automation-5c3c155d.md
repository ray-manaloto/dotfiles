# Premise report — `docs/specs/session-handoff-automation.md` @5c3c155d

> Persisted verbatim at receipt by coordinator 28f1a8f7, 2026-10-03. Producer: premise-verifier subagent (read-only).

PREMISE REPORT: `docs/specs/session-handoff-automation.md` (worktree `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/handoff-automation-research`, commit 5c3c155d)

This lane is read-only (no Write or Bash), so nothing was written to findings.md. That also means I could not run `gh`, so P12 and P15's GitHub state were not re-read live.

ROWS: 15 checked: 8 CONFIRMED (0 provenance corrected) / 1 REFUTED / 6 UNVERIFIABLE / 0 ASSUMED (0 checkable)

- **P1: CONFIRMED.**
  - `.claude/types/claude-code.d.ts:2020-2028`: `plugin.root` is "The plugin's directory (the one holding plugin.json), absolute".
  - `$CC/plugins-reference.md:376`: `@skills-dir` plugins are "discovered in place rather than copied into the plugin cache", so `root` is a real path inside the git tree.
  - Caveat: the vendored types were written by 2.1.277 (`d.ts:1`), and the runtime is 2.1.288 (`~/.claude/jobs/6fae0fec/state.json:31`).

- **P2: UNVERIFIABLE.**
  - The type says it fires "after each main-thread turn" (`d.ts:3594-3595`) and carries `context.percent` (`:8925-8932`, `:8797-8800`).
  - Nothing in the types or the `$CC` corpus separates attached from unattached sessions.
  - Circumstantial evidence that it does fire in a bg lane:
    - The F1 lane 6fae0fec showed `handoff ERROR: decide rc 2`. The only caller of `decide` is `measure()`, run from `session.measure` (`coordinator-handoff/hooks/register.ts:241,296`), so the hook did fire in that bg lane.
    - Its job record has `createdAt 01:44Z` and `firstTerminalAt 19:21Z` (`state.json:43,45`). If the coordinator saw that status before 19:21Z, P2 is confirmed for unattached sessions. I could not establish when the observation was made.
  - The 2026-10-02 live arms (`docs/research/kb/reports/agents/live-arms-coordinator-auto-handoff-2026-10-02.md:11,15`) were bg coordinators. Arm A was read off a screen, so it was attached.
  - Non-blocking for writing the spec, because L2 arms it. Blocking for D2's lane promise until L2 passes.

- **P3: REFUTED.**
  - (a) A fourth hook with the same defect is missing from the list: `.claude/skills/plugin-health/hooks/plugin-health.ts:36-41` runs `"uv", "run", "--project", "python", "dotfiles-setup", "plugin-health"` with `cwd: projectDir` from `CLAUDE_PROJECT_DIR`. The plugin is registered in `plugin-health/hooks/hooks.json:3`.
  - (b) `install-doctor/hooks/register.ts:233` is not a CLI call site. It is the fallback root used to compute `doctor.toml` for the Edit/Write repair permit (`:227-236`). Pointing it at the plugin tree would change which `doctor.toml` the permit accepts.
  - The coordinator-handoff call sites 116/183/204 and session-start 106-108 are correct.

- **P4: CONFIRMED.**
  - In `coordinator_handoff.py` I spot-read: `:74-80` (name regex, env names, defaults), `:106` STATE_SUBDIR, `:115` HEAVY_COMMAND_RE, `:179` Decision, `:197` is_coordinator, `:317` decide, `:426` successor_name, `:650` successor_brief, `:731-733` launch_argv, `:819` launch, `:1086` retire, `:1258-1300` main.
  - In `register.ts`: `:22` SKILL, `:99-102` env, `:154` "not coordinator" status, `:221-238` limit/probe/dry-run.

- **P5: CONFIRMED.**
  - `coordinator_handoff.py:1265-1272`: the only rc 2 is `worktree-unavailable`. `:1274-1288`: decide always writes JSON and returns 0.
  - Nuance: argparse also exits 2 for "unrecognized arguments". A future hook that passes a flag an older CLI lacks would be rc 2 without `invalid choice`, so `isSkew` would report it as ERROR rather than skew.

- **P6: UNVERIFIABLE, and the evidence leans no.**
  - `d.ts:18-19`: "The module, and every file it imports **from the plugin**…". That suggests imports are scoped to the plugin.
  - `$CC/plugins-reference.md:839-845`: paths that point outside the plugin root are rejected. Strictly that covers component paths only; a module's internal imports are not addressed.
  - Both existing modules already say "Helpers are deliberately local: each skills-dir plugin loads independently" (`coordinator-handoff/hooks/register.ts:11`, `session-start/hooks/register.ts:12`).
  - `plugin-health.ts:1` imports `../../../types/plugin-health` from outside its plugin, but that is a type-only import and is erased, so it settles nothing.
  - Cheapest way to settle it: `claude plugin validate <dir>`. Per `d.ts:7-10` it "reports … everything the engine would refuse".
  - Non-blocking, because the spec already names the fallback (a copy in each module plus a parity test).

- **P7: CONFIRMED for hooks.** `session-start/hooks/register.ts:233` calls `queue($, "reload-plugins", "--force")`, and live arm A logged "Reloaded: 17 plugins…" (`live-arms…:12`). See MISSING-3 for the skill-side gap.

- **P8: UNVERIFIABLE.**
  - `$CC/worktrees.md:89-92` lists **four** checks. The premise names three and leaves out "Command shape" (`:92`): commands are blocked when the text can't show that any git they run stays in the worktree.
  - A static `mise run handoff-inbox -- …` probably passes, and the python write itself is not a tool call, so it is not checked.
  - The checks bind only to sessions that are *isolated in a worktree* (`:83`, `agent-view.md:490-497`). The repo has no `worktree.bgIsolation` setting (Grep of `.claude/` returned 0 hits), so the default isolation applies.
  - Only arm L4 can settle this. Further risks are in MISSING-6.

- **P9: UNVERIFIABLE.**
  - `$CC/cross-session-messaging.md:264-266` describes the socket as where "other sessions on the machine deliver messages", and the doc is aimed at "a script or hook" posting.
  - `:275` restricts the socket to your OS user, so a same-user python process should be able to connect.
  - Gaps:
    - The wire format is undocumented apart from the optional auth line (`:279-282`).
    - Python has no supported way to discover another session's socket path: `claude agents --json` exposes no socket field (`agent-view.md:709-716`), and the registration files are undocumented (`:166`).
    - A foreign post is not own-child, so it goes through inbound controls (`:288-293`), and `refuse` drops it silently.
  - Non-blocking, because the fallback is named.

- **P10: CONFIRMED.** `pr.py:1031` defines `land_main`, and `:1043` calls `_land_post_merge`, which returns None on failure (`:1044-1045`). The full-success point is `:1062`. See MISSING-8 for the sha.

- **P11: CONFIRMED, with the location corrected.**
  - The aggregation is in `check_with_claims` (`handoff_check.py:654-670`). `check()` (`:673-682`) only wraps it.
  - `Finding` is defined at `:153`, and its `verdict` is a `Verdict` enum (`:137-149`) with **no `FAIL` member**. A new member is needed.

- **P12: UNVERIFIABLE (this lane cannot run `gh`).** The source is a live `gh api` read with no file:line. #1604/#1608 auto-merge shows up only in report form (`session-handoff-automation-sweep-2026-10-03.md:165`). Non-blocking for the spec; L3 re-arms it.

- **P13: CONFIRMED.** `session_common.py:172-192`: runs `git -C <cwd> worktree list --porcelain` and returns the first `worktree` entry, resolved.

- **P14: CONFIRMED.**
  - `$CC/plugins-reference.md:402`: project `@skills-dir` plugins load only from the primary working directory's `.claude/skills`.
  - Read fresh: `~/.claude/jobs/6fae0fec/state.json:32` has `"cwd": "/Users/rmanaloto/dev/github/ray-manaloto/dotfiles"`, while its transcript is under the worktree project dir (`:15`, `…-worktrees-llvm23-20261002/…jsonl`).

- **P15: UNVERIFIABLE (GitHub state not readable here), but consistent with "blocking".**
  - No fix code exists in `python/src/dotfiles_setup`: a Grep for `CronDelete|fencing` returned 0 hits. Control: the same Grep shape for `claude rm` returned 2 hits (`dag_project.py:100`, `dag_tick.py:236`).
  - `docs/handoffs/session-2026-10-03g.md:84-85` still lists "#1609 revival" as queued work.
  - Treat L2 as blocked.

MISSING:
1. **The lane-role rule fails on the real lane shape. Load-bearing.**
   - §3b says `ROLES["lane"]` requires that the "job-record cwd is a linked worktree", and §5 arm 3's fail arm maps a main-checkout cwd to `None`.
   - But the actual F1 lane's job record has cwd = the **main checkout** (`state.json:32`), even though it works in `dotfiles.worktrees/llvm23-20261002`.
   - The rule therefore classifies the motivating lane, and L1's own shape, as `None`, so it never fires.
   - The architect needs to choose a different discriminator, for example the transcript or project dir (`linkScanPath`, `state.json:15`) or `claude agents --json` `cwd` (`agent-view.md:711`, which I have not verified to follow a session's move into a worktree), or require lanes to be launched with a worktree cwd. Then re-arm arm 3 against a real job record.
2. **P3 omission. Load-bearing for D1's objective ("A hook can no longer run against a CLI from a different git tree").** `plugin-health.ts:36-41` needs the resolver and a skew arm, and it belongs in the §2 file table and the tests. Also decide whether `install-doctor:233` changes at all.
3. **A skill cannot call `$.command.run`. Load-bearing for §3g.**
   - §3g says "the calling skill runs `$.command.run({command:"reload-plugins"…})`". `$.command.run` is the hook API (`d.ts:2634` per the prior premise report; used at `session-start register.ts:80-83`). A SKILL.md is model instructions, and the model cannot call it.
   - Name the hook that queues the reload after `sync-to-main`, or accept that sessions run stale until restart.
4. **D1 moves state and inspection targets as a side effect.**
   - `project_root = Path(__file__).parent.parent.parent.parent` (`main.py:3242`), and session-start state is `project_root / STATE_SUBDIR` (`session_start.py:413`).
   - Resolving the CLI from the plugin tree therefore moves session-start state from the session's own checkout (`live-arms…:23-24`) to the plugin's tree, and makes install-doctor and plugin-health inspect that tree.
   - The architect should confirm this is intended and arm it.
5. **The handoff-check wiring has no handoff path.**
   - `check()`/`check_with_claims()` take the handoff `text`, not a path (`handoff_check.py:637-644,673-680`). Only `main()` knows the path (`:722-734`), so "findings.toml beside the checked handoff" can't be computed inside `check()`.
   - Default discovery only globs `.agent/plans/session-*.md` (`:189-194`, `_HANDOFF_RE` `:34-36`), so `docs/handoffs/lane-*.md` is never auto-checked.
   - The spec needs to say where `_ledger_findings` gets the path.
6. **P8 follow-ons, unverified.**
   - `mise run handoff-inbox` from a lane worktree runs `uv run --project python` relative to the **lane's** tree (pattern at `mise.toml:1035,1706`). A lane branched before L0 has neither the task nor the subcommand: the same skew class as F1.
   - mise config trust for a linked-worktree `mise.toml` is not addressed.
   - L4 should run from a pre-L0 branch too, or make `sync-to-main` a precondition.
7. **Inbound acceptance gates D3 and D4 delivery.**
   - Messages are delivered only when the receiver's `crossSessionInbound` allows them. `refuse` drops them silently (`cross-session-messaging.md:213-217`), and live arm "refuse control" proved non-delivery (`live-arms…:13`).
   - Successors get `accept` through `launch_argv` (`coordinator_handoff.py:109,733`), and the llvm23 lane has it (`state.json:21`), but nothing guarantees it for "every live `dotfiles-*` session" (L5).
8. **`notify_sessions(sha)` has no sha.** `merge_oid` is local to `_land_post_merge` (`pr.py:1021`), which returns only a bool or None (`:1028`), so the sha needs plumbing.
9. **The successor cwd changes the hook tree.** A lane successor started "in the same worktree" loads hooks from that worktree (P14). The coordinator path always starts with `cwd=main checkout` (`coordinator_handoff.py:839-844,944`). The lane variant must pass the worktree, and that worktree must already contain the hook skills, so sync must happen before launch, not as the successor's step 0.
10. **#1592.** `claude --bg launches need a SendMessage START` (`session-2026-10-03g.md:92`). The lane successor launch (§3c step 5) does not say how the successor is started.

VERDICT: correct the spec first. P3 is refuted (plugin-health hook omitted), the lane-role discriminator contradicts the real lane's job record (`state.json:32`), and §3g has a skill calling a hook-only API. P2, P6, P8, P9, P12 and P15 are non-blocking residuals, each with a named arm or fallback (L2, `claude plugin validate`/copy+parity, L4, SendMessage loop, L3, #1609 gate), for the architect to accept on the record.

## GitHub repos touched

_None._ (Local sources only: this repo's worktree at 5c3c155d, the knowledge-base offline `$CC` corpus, and local job records.)
