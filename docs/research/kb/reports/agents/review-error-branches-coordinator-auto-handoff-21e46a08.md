# Opus error-branch read — coordinator-auto-handoff 21e46a08

## Brief

Read-only review (no edits, no tests, no gates). Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles.worktrees/coordinator-auto-handoff-20261002, commit 21e46a08. Per this repo's review tiers, a change touching process control / session termination gets an Opus read of EVERY error, nil/None, empty and timeout branch. Scope: python/src/dotfiles_setup/coordinator_handoff.py (decide/state write, census, launch, retire incl. pid-liveness + argv recheck, inFlight read, `claude stop` invocation), python/src/dotfiles_setup/session_start.py, and both hook modules .claude/skills/coordinator-handoff/hooks/register.ts and .claude/skills/session-start/hooks/register.ts. Spec for intent: docs/specs/coordinator-auto-handoff-2026-10-02.md (§3b, §3d, §4, §8).

For each branch answer: what input reaches it, what the code does, and whether that is SAFE (fails closed where a wrong answer could stop a live coordinator, kill or orphan a heavy run, fire the handoff every turn, rename a lane the coordinator addresses by name, or hide a failure from the status line). Specifically check: pid reuse / zombie (kill(pid,0) true on a zombie), a census taken with no claude ancestor, a state file write failure or a corrupted state JSON, concurrent decide calls, `claude stop` missing/failing, an inFlight field missing vs 0, a `/rename` collision, `$.command.list` throwing, and timeouts in `$.process.run`. Cite file:line for every finding with severity (HIGH/MED/LOW) and a concrete failure scenario. Under 600 words. Return the report as your final message.

## Report (verbatim)

Opus review of commit 21e46a08. It was read-only: nothing edited and no gates run, so nothing was persisted. Please persist this report.

**HIGH**

1. **A second handoff fires after a successful launch.** `_judge` (coordinator_handoff.py:246-260) and `launch` (:590-649) never check `state["launch"]`. The skill's own unattended `/session-handoff` and ship work will grow the old session's context. So will an inbound lane SendMessage arriving after it goes idle (its `--settings` allow cross-session inbound). Either can push it past 35%. `decide` then fires again, and register.ts:187 queues the command for when the session is idle. The result is a second full handoff and a second `claude --bg` successor, so two coordinators run at once, and `launch` overwrites the first successor's census and launch record. Fix: once a launch record exists, `decide` should answer `already-launched`, and `launch` should refuse to run twice.

2. **session-start treats "no job record" as "no name" and renames the session.** session_start.py:159-167 reuses `session_name`, which returns `None` for anything missing, unreadable or mismatched (coordinator_handoff.py:189-199). In coordinator_handoff, `None` correctly fails closed as "not a coordinator". Here `None` leads to `rename` or `defer`, which is fail-open. Two cases hit this:
   - A foreground `claude -n mylane` has no `~/.claude/jobs` record, so the name it was given gets overwritten. That breaks spec §8's rule that a `-n` name is never renamed.
   - If `session.start` fires before a bg spare's job record is written or claimed (an ordering I have not verified), a lane the coordinator addresses by name gets renamed.

**MED**

3. **No lock on the shared state file, so concurrent writes clobber each other.** `decide` writes `last_seen` on every measurement at or above the limit (:287-293). `launch` read-modify-writes the same `<old>.json` (:638-647), and `write_state` has no lock (:226-231). Two failure orders:
   - A hook `decide` reads before `launch`'s write and writes after it. The census and launch record are wiped, and `retire` returns rc 2 forever (:750-756).
   - `launch` writes back an older `last_fired`, and a level re-fires.
   
   Two overlapping `session.measure` calls (the uv run is 60 s cold) can both read no `last_fired`, both fire, and launch two successors.

4. **Old and new sessions use different state directories.** The state dir is `project_root`, the package's own checkout (main.py:3005). `decide` and `launch` write under the old session's checkout. The successor runs `retire` from the main checkout (:633, :649), and the brief passes no `--state-dir` (:524). If the old coordinator ran from a worktree, `retire` returns rc 2 every time. That fails closed, but it stalls and invites a bare `claude stop`.

5. **rc 1 is ambiguous in `retire`.** A missing `claude` raises an uncaught FileNotFoundError, giving a traceback and rc 1 (:784-785). A failing `claude stop` passes its own rc through. Both are indistinguishable from the BLOCK rc 1 (:777), which the brief (:526) tells the successor means "wait". The `claude stop` call also has no timeout. The same applies in `launch`: a git timeout in `main_checkout` (:355-361) raises TimeoutExpired, which `_gather` (:585) doesn't catch, so it exits rc 1 instead of the documented rc 2.

6. **The census misses heavy runs it doesn't recognise.** `HEAVY_COMMAND_RE` (:84-90) requires the literal `mise run X` and omits `dev-rebuild`, `up`, `persistence`, `gate`, `lock-image`, and `mise -C <dir> run …`. An hours-long `dev-rebuild` is not recorded, so the census can't block retire. Only `inFlight` can save it, and that check is skipped when the field can't be read (item 7).

7. **An unreadable `inFlight` fails open.** A missing field, a non-int, or a renamed key (:692-699) returns `None`. `retire` then logs a warning and lets the census decide alone (:704-710). That is what the spec says to do, but a harness schema change silently disables the second blocker permanently. A missing field and `0` are told apart correctly.

8. **A deferred rename can be lost silently.** register.ts:166-167 queues `/reload-plugins --force` before setting `pending` (:184). In an idle interactive session the reload runs before the first prompt and discards the module's memory. Spec §8 says `session.start` re-fires only for a *changed* module, so `pending` is gone and the defer never happens, with no error shown. Unverified; needs a live probe.

**LOW**

- **Retire's pid checks are safe.** Pid reuse and zombies can't block it: it compares the exact argv (:757-762), and a zombie or reused pid shows a different argv. `ps args=` is unbounded when not on a tty (measured 8348 chars, and `COLUMNS=60` had no effect), so truncation is not a risk.
- **A failure after `decide` costs the level.** Any failure after `decide` persisted (a `$.process.run` timeout per d.ts "kills and rejects", a `command.list` throw, or the skill not being listed) uses up that level. The error is visible through `fail()` on the status line (register.ts:46-54, :199-203), but the handoff waits for the next step. DRY_RUN and PROBE runs also consume real levels (:166-175).
- **A census with no claude ancestor fails closed.** It raises (:429-431), and `launch` returns rc 2.
- **A corrupt state JSON resets things.** `read_state` returns `{}` (:220-223), so `decide` re-arms at the limit and its next write erases any census. `retire` fails closed with rc 2.
- **A failed state write in `decide` stays visible.** It returns `fire:false` with `state-write-failed` (:294-297), which shows `ERROR` every turn.
- **Some hook inputs are read outside the try block.** register.ts:195-196 reads `e.changed` and `e.context` outside `try`. A throw there leaves the status line stale rather than showing an error.
- **`/rename` collisions are unlikely and unchecked.** Names carry ns-precision stamps, so a clash is effectively impossible, but nothing checks for one. `mark_renamed` records the rename as queued, not confirmed (register.ts:149-150), so a rejected `/rename` is toasted once and never retried.

**Repos touched:** none; I read only the local repo and the installed `claude-code.d.ts`.
