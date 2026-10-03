# L0 F2 (terminal-state skip in the newest-coordinator gate): review and proposals

> Read-only review lane, 2026-10-03. Subject: `fix/L0-handoff-findings-urgent` @ `81be2fc0`
> (worktree `.claude/worktrees/L0-urgent-code`, abbreviated `L0/` below). `$CC` =
> `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code`.
> No source was edited. One out-of-tree probe script was run from `/tmp` and then deleted.

## Bottom line

**F2 as committed is a regression. It reopens the hole the gate exists to close.** In Claude Code, `done`
does not mean dead. It means the session finished its turn and is waiting, "whether or not its process is still
alive" (`$CC/agent-view.md:726`). A coordinator that is live but idle (waiting on lanes) reads `done`. F2 skips that
record, so an older, superseded coordinator that happens to read `working` passes as "newest". I measured this
directly (P-3 below): with F2, the older coordinator **PASSED**; with F2 removed (control), it was **REFUSED**.

F2 also gets the set wrong in the other direction. It omits the documented `failed` state, and `stopped` is
resumable. The lockout F2 targets has never happened in production, because the gate is not on `main` yet.
Recommendation: **(c) revert F2 from the L0 batch, plus (d) carry a corrected version into the redesign**. This
overturns the coordinator's "Keep F2", on new evidence.

## Q1. Does the redesign make F2 moot?

**No.** The ancestry redesign changes how the gate establishes *who the caller is*. It does not change *who counts
as newest*.
- Option (a) says: "Require `ps lstart <= startedAt`, require that row's `sessionId` to equal the env
  `CLAUDE_CODE_SESSION_ID`, then run the existing name and newest-`createdAt` checks"
  (`dotfiles.worktrees/coord-28f1a8f7/docs/research/kb/reports/agents/proposals-handoff-inbox-coordinator-gate-2026-10-03.md:39`).
- Its arm 7 re-pins "Superseded coordinator, resolved through ancestry → refuse" (`:113`).
- The function-hook report keeps that floor: "Python keeps option (a) … → newest coordinator"
  (`…/proposals-fn-hooks-coordinator-gate-2026-10-03.md:103`). Its arm 4 is "Superseded coordinator → deny" (`:186`).

So the scan that picks the newest `createdAt` over `~/.claude/jobs/*/state.json` survives the redesign unchanged
(`L0/python/src/dotfiles_setup/handoff_inbox.py:184-198`), and the question F2 addresses survives with it. F2 is
orthogonal to identity and has to be decided either way.

One thing the redesign *should* change: the docs say the job files "are not a stable interface"
(`$CC/agent-view.md:731`) and say to read state through `claude agents --json` instead (`:764`). Option (a) already
calls that command (proposal `:26`), so a corrected F2 belongs there.

## Q2. Is {done, stopped} the complete set of terminal job states?

**No, on three counts.**

1. **The documented enum has five values:** "One of `working`, `blocked`, `done`, `failed`, or `stopped`"
   (`$CC/agent-view.md:713`). F2 omits `failed` (`L0/…/handoff_inbox.py:80`).
2. **`done` is not terminal.** "The last turn finished what you asked for and the session is ready for your next
   prompt, whether or not its process is still alive" (`$CC/agent-view.md:726`). Also: "A session that finished its
   turn and is waiting for your next instruction reads `done`" (`:729`). The coordinator's message quoted `:726`;
   I re-read that line and the quote is verbatim.
   - **Measured** (`claude agents --json --all`, rc=0, reading only `kind`/`state`/`status`/`pid`-presence): among
     background sessions, **6 are `done` with a live pid** (status `idle`) and 22 are `done` with no pid.
   - So `done` covers both live-idle and exited sessions, and a session in either case resumes on a reply.
   - Control arm: the same query shows the live coordinator 97ffeddb as `working`/alive/`busy`, so the probe does
     distinguish states and liveness.
3. **`stopped` and `failed` are resumable.**
   - "You wake a stopped session … by attaching or replying to it" (`$CC/agent-view.md:604`).
   - "`claude respawn <id>` — Restart a session, running or stopped" (`:695`).
   - A session that `failed` at shutdown restarts when you attach or reply to it (`:811`, `:846`).
   - Because the gate reads state at call time, a woken record simply counts again. Resumability therefore does not
     break F2's logic. It does mean that nothing in the enum is permanently terminal, and the name
     `TERMINAL_JOB_STATES` is wrong.

**Is `blocked` terminal? No.** "The session is waiting on you: a question it asked, a permission or sandbox
decision…" (`$CC/agent-view.md:725`). Both `blocked` records I measured have a live pid.

**State counts across `~/.claude/jobs/*/state.json`** (state field only; 53 records, 0 unparseable): done 29,
stopped 10, working 12, blocked 2.
- L0's count (done 30, working 11, stopped 9, blocked 2) is the same order of magnitude. I did not reconcile the
  difference: the records change state over time, so this is an inherited number re-measured, not a contradiction.
- `failed` appears 0 times locally. That is not evidence it cannot occur: the doc names it (`:713`) and says when it
  occurs, namely sessions that ended with a shutdown (`:811`).

**The 12 coordinator-named records** (createdAt, id, state):
- 98eb9783 done
- 7541ae79 stopped
- f6687621 done (02:49:43Z)
- 5990b71c done (02:50:22Z)
- 4bcfb646 stopped (02:50:23Z)
- 30d222ef done
- a8d7baf5, 2dffefaf, a2ccbbc5, 27e2bf5c, 28f1a8f7: all stopped
- **97ffeddb working (20:31:07Z, the newest, live)**

## Q3. Security: can F2 be abused, and does it widen or narrow the spoofing surface?

**It widens it, and no forgery is needed.**

- **Accidental bypass, measured (P-3).** Fixture: the older coordinator is `working`, and a newer coordinator is
  `done`, i.e. live but idle.
  - With F2 at `81be2fc0`: `OLDER caller PASSED as dotfiles-20261003T140808.0-05.coordinator`.
  - Control, with `TERMINAL_JOB_STATES = frozenset()` (F2 removed):
    `OLDER caller REFUSED: … is not the newest coordinator (newest is '…144132…')`. rc=0.
- **This is the gate's own stated target.** The docstring says the gate "stops a LANE session or a SUPERSEDED
  coordinator writing by mistake" (`L0/…/handoff_inbox.py:31-32`). F2 lets a superseded coordinator through whenever
  its successor is between turns. For a coordinator, between turns is the normal resting state.
- **The scenario is realistic.** It needs only a superseded coordinator that reads `working`:
  - it is still inside its handoff turn;
  - `retire` failed, which `coordinator_handoff.py:1162-1168` allows (`claude stop` rc≠0 → rc 3);
  - or it is between steps of work it drives itself, which reads `working` (`$CC/agent-view.md:724`). I measured 11
    sessions that are `working` while their process status is `idle`.
- **Why the tests miss it.** The test fixtures never write a `state` field (`L0/tests/test_handoff_inbox.py:62-67`).
  The superseded-coordinator arm therefore runs only against a stateless newest record, and the new F2 test
  (`:311-337`) only adds dead records. The fixture cannot produce the failing case (probes rule 8).
- **Spoofing surface.**
  - Before F2, only the single newest id passed.
  - With F2, every coordinator id that is newer than all live-or-dead `working`/`blocked` records passes whenever
    the newer ones are idle or stopped. Older ids appear in prose: the live coordinator's job `intent` quotes the
    previous coordinator's full id (proposal `:15`). So a copied `CLAUDE_CODE_SESSION_ID=<older>` now passes more
    often.
  - F2 does not touch the env-trust or `--jobs-dir` holes (`L0/…/handoff_inbox.py:28-31`).
- **Forged or stale records.**
  - Writing `"state":"done"` into the real newest record would hide it. However, the harness replaces `state` "on the
    next update" (`$CC/agent-view.md:731`), so a forgery is transient.
  - Under F2, the cheaper attack is simply to wait for the newest coordinator to go idle.
  - Before F2, a forged newer coordinator-named record could only cause denial of service (a lockout that fails
    closed), never a pass for an older session. F2 turns a record-state signal into a source of passes.
- **F9 interaction.** The scan still skips unreadable records (`L0/…/handoff_inbox.py:185-188`), so it fails open.
  This is unchanged by F2.

## Q4. Does the lockout F2 fixes actually occur today?

**No, not today in production. It is a latent risk.**
- **The gate is not on `main`.** `python/src/dotfiles_setup/handoff_inbox.py` is absent from the main checkout. The
  control arm is that `coordinator_handoff.py` in the same directory is present. On this branch it exists only from
  `767ff5b7`, 2026-10-03 15:00 -0500 (`git log` on the file).
- **The current data gives no lockout even without F2.** The newest coordinator record is 97ffeddb (20:31:07Z),
  which is live and `working`. That is the caller who would pass.
- **The 02:49–02:50Z burst is real but historical.** 4bcfb646 (`stopped`, 02:50:23.615Z) is newer than f6687621 and
  5990b71c, both `done`. If either of those had been the surviving coordinator, the pre-F2 gate would have refused it.
  But the gate did not exist then, and nine later coordinator records now outrank the burst.
- **The lockout fails closed and visibly** (rc 2, "not the newest coordinator (newest is X)",
  `L0/…/handoff_inbox.py:199-204`).
- **Possible recovery without code: `claude rm <id>`.** It removes a session "from the list", and "the removal
  survives supervisor restarts" (`$CC/agent-view.md:530`, `:697`). **UNVERIFIED** whether it deletes
  `~/.claude/jobs/<id>/state.json`. I did not run it, because it is destructive. An arm is owed (O-arm 4 below).

## Options, recommended first

**(c)+(d) Revert F2 from the L0 batch now, and carry a corrected rule into the redesign. RECOMMENDED.**
- How:
  - Drop the `state` clause (`handoff_inbox.py:195`), `TERMINAL_JOB_STATES` (`:79-80`), the docstring sentence
    (`:24-26`), and the test `:311-337`.
  - Keep the rest of `81be2fc0` (F5/F7/F8/F3/F6/F10 are independent).
  - Add one sentence to the docstring: "a dead newer coordinator record refuses everyone; recovery is open, see
    redesign".
  - Hand this report to the redesign as an input.
- PRO:
  - Removes a measured regression.
  - Honours "Don't change the gate" until Ray rules.
  - The residual risk fails closed, has never occurred, and affects an unshipped gate.
- CON:
  - The lockout remains possible with no override until the redesign lands.
  - It overturns the coordinator's "Keep F2" and needs that conversation.
- Arms:
  1. After the revert, P-3 refuses the older caller.
  2. The existing superseded arm (`test_handoff_inbox.py:135-142`) still passes.
  3. Add a test with a `done` newest record and a `working` older caller that refuses. This pins the regression so
     no later F2 reintroduces it. Mutation: re-add the F2 clause, and the test fails.

**(e1) Narrow F2 to `{"stopped"}` only, as the proposal Ray rules on. Second choice, and the input for (d).**
- Rationale:
  - `stopped` means someone ran `claude stop`/`Ctrl+X`, or the process was ended from outside Claude Code
    (`$CC/agent-view.md:116`). That is a deliberate retirement. `retire` itself produces exactly this state
    (`coordinator_handoff.py:1162`).
  - `done` must not be skipped (Q2/Q3).
  - `failed` must not be skipped either. After a reboot, every session, including the live newest coordinator, shows
    `failed` until it is re-attached (`:811`). Skipping it would let whichever older session someone wakes first
    pass.
  - A woken `stopped` record reads non-stopped again and is counted, which is correct.
- PRO: fixes the measured 02:50 burst shape, whose newest record is `stopped`, without the `done` hole.
- CON:
  - Does not cover a dead successor that reads `done` with no pid. That case is indistinguishable from a live-idle
    one, and both resume on reply (22 done/no-pid against 6 done/alive measured).
  - Still reads an unstable file (`:731`).
- Arms:
  1. A `stopped` newer record plus the live caller → pass.
  2. A `done` newer record plus an older `working` caller → refuse. This is P-3 inverted.
  3. A `failed` newer record → refuse.
  4. Re-derive from `claude agents --json --all` rather than `state.json`.

**(b) Split F2 into its own commit or PR, held until Ray rules.**
- PRO: preserves the work and the process boundary.
- CON: holds code that is measurably wrong. If it is split, it must be rewritten to (e1) first, or it is a hazard
  waiting to be merged.
- Arms: P-3 refuses on the held branch before anyone may un-hold it.

**(e2) Explicit supersession tombstone, folded into the redesign.**
- How:
  - `retire`, run by the successor, also appends the retired session id to a list under
    `<main>/.agent/state/handoff-inbox/` that `_locked_write` holds.
  - "Newest" becomes the newest coordinator record that is not tombstoned. No harness state is consulted.
- PRO:
  - Uses our own deterministic record instead of an unstable, non-terminal harness enum.
  - A woken retired coordinator stays retired.
- CON:
  - Same-uid forgeable, like everything here (the docstring's limit).
  - A crashed successor that never ran `retire` still locks out. Pair it with (e3).
- Arms:
  1. A tombstoned newer record is skipped.
  2. A non-tombstoned idle `done` newer record still refuses the older caller.
  3. A tombstone write failure makes `retire` return non-zero.

**(e3) A manual break-glass, Ray only.**
- How: the function-hook option 4, `$.command.register` with `origin.kind==='composer'`
  (`…/proposals-fn-hooks-coordinator-gate-2026-10-03.md:151-159`). The command tombstones a named stale record.
- PRO: an override nobody else can trigger, which answers cold review F2's "There is no override".
- CON: not autonomous. Its origin when invoked through the Skill tool is unverified (fn-hook probe P8).
- Arms: fn-hook P8. A model-originated invocation must be refused.

**(a) Keep F2 in this batch as is. NOT RECOMMENDED.**
- PRO: no churn.
- CON:
  - P-3 shows it lets a superseded coordinator pass whenever the successor is idle.
  - It omits `failed`.
  - It changes a gate Ray asked not to be changed.
- To justify keeping it, someone would have to show that a live newest coordinator never reads `done` while an older
  one reads `working`. `$CC/agent-view.md:726` and the 6 measured `done`/alive sessions refute that.

## Probe log (with control arms)

- **P-1:** `$CC` grep for the state enum.
  - Hits: `agent-view.md:713`, `:724-729`.
  - Control: the same grep found `claude agents` in `network-config.md:164`, so the corpus and the grep both work.
- **P-2:** state counts from the jobs files and from `claude agents --json --all` (rc=0).
  - Only `state`, `kind`, `status`, pid presence, and coordinator `name`/`createdAt`/id were read.
  - Control: the live coordinator shows `working`/alive/`busy`.
- **P-3:** an out-of-tree `/tmp` script run with `uv run --project python` from `L0/`, then deleted.
  - F2 arm: PASSED.
  - F2-removed control: REFUSED.
  - rc=0.
- **P-4:** gate absent on `main`. Control: `coordinator_handoff.py` is present in the same directory.
- **Not run:** `claude rm` on a throwaway session, to see whether it deletes `~/.claude/jobs/<id>`. It is
  destructive and owed as O-arm 4.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): L0 worktree `81be2fc0` (`handoff_inbox.py`, tests,
  cold-review report, `coordinator_handoff.py`), the coord-28f1a8f7 proposals, and the main checkout (presence probe).
  Nothing was modified.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): offline `$CC` docs (`agent-view.md`).
