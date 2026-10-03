---
name: coordinator-handoff
description: "Hand a dotfiles coordinator session over to a named successor with no human step: unattended /session-handoff, tracked handoff copy, census of live heavy runs, `claude --bg` successor from the main checkout, then idle. Auto-submitted by this plugin's session.measure hook when a coordinator's context reaches the limit (default 30%); arguments are `<old session id> <percent>`, or `--probe`."
argument-hint: "<old session id> <percent> | --probe"
---

# coordinator-handoff — the old coordinator's half

The `session.measure` hook in
`.claude/skills/coordinator-handoff/hooks/register.ts` submits this skill when a
session named `dotfiles-….coordinator` (bg job record, fail closed) crosses
`DOTFILES_COORDINATOR_HANDOFF_PCT` (default 30) and again every
`DOTFILES_COORDINATOR_HANDOFF_STEP_PCT` (default 5) above it until launch.
An existing launch record prevents every subsequent fire and second launch.
The first measurement checks the role. A miss below the limit gets one re-check
at the limit; a miss there expires after 10 minutes of module time. A coordinator
is cached for the module's lifetime. Lanes write no
handoff state. PROBE passes `--probe` and fires once per session; DRY_RUN passes
`--dry-run` and fires once per preview level. Neither spends real levels.
Failed real delivery releases the consumed level. A probe stays pending until
its command resolves; successful delivery confirms it, rejection releases it
with `release --probe` and shows `handoff ERROR: probe delivery failed`.
The judgement
is `mise run coordinator-handoff -- decide`; the spec is
`docs/specs/coordinator-auto-handoff-2026-10-02.md`.

`$ARGUMENTS` is `<old session id> <percent>` — the id is THIS session's.

## 0. Probe

If `$ARGUMENTS` is `--probe`, reply exactly `coordinator-handoff probe OK` and
stop. Nothing else runs: this arm only proves the hook's real `command.run`
path reached the skill.

## 1. Unattended `/session-handoff`

Run `.claude/skills/session-handoff/SKILL.md` in full, under its
"Unattended run" section: no human is at the prompt and none will be.

- Every §0 ambiguity, §1c finding that needs a ruling, and open ruling goes
  into the handoff's `## Queued questions` section in ask-quality shape —
  recommended option first, `PRO:`/`CON:` per option, a citation. Never an
  AskUserQuestion, never a stall. The successor puts them to Ray.
- Nothing flagged as questionable is committed or posted.
- Write the tracked copy `docs/handoffs/session-<YYYY-MM-DD><letter>.md` on a
  `docs/handoff-<YYYY-MM-DD><letter>` branch and ship it early as a PR with
  `mise run ship` from the main checkout, launched as a harness background run
  with a file-captured rc (its push carries the ssh keepalive). If another
  ship holds the host slot, push the branch now and put its ship at the head
  of the queue.
- Bring `.agent/plans/main-checkout-ship-queue.md` up to date.
- Skip §6's resume line: there is no `/clear`.

## 2. Launch the successor

```bash
mise run coordinator-handoff -- launch \
  --handoff docs/handoffs/session-<YYYY-MM-DD><letter>.md --old-session <id>
```

It records the census of this session's live heavy runs, as defined by
`HEAVY_COMMAND_RE` in `python/src/dotfiles_setup/coordinator_handoff.py`, then starts
`claude --bg -n dotfiles-<Chicago ISO ns>.coordinator` from the main checkout
with a brief carrying the transcript path, the handoff, the ship queue, the
census and the queued questions. State lives in the CWD repository's main
checkout; the brief gives retire its exact `--state-dir`. rc 2 means refused
(invalid id, missing handoff, not a coordinator, already launched, unavailable
census/state, a start already in progress, or a 10 s lock timeout): record that
in the handoff and stop. A pending start blocks another for 15 minutes; stale
or unreadable-age pending state is ignored with a warning. Refusal reasons
distinguish `state-locked`, `state-unreadable`, `state-write-failed`,
`worktree-unavailable`, `handoff-unreadable`, and `census-unavailable` (process
snapshot/tree failure; unavailable fd-1 logs use the redirect fallback).
rc 0 means started and recorded (dry-run: nothing recorded or executed).
rc 3 means start failed (missing executable, 60 s timeout or nonzero rc): pending
state is removed, the fired level is kept, and the hook retries at the next step.
rc 4 means successor STARTED but not recorded — do not relaunch. Its pending
record is marked `started: true`; it blocks firing regardless of age and is
accepted by retire. An independent started receipt preserves that confirmation
if the session-state lock or promotion write fails.
Harness logs marked `harness-output:` have no rc file; wait on pid exit.
Redirect fallback skips the harness's final `eval` prelude; `/dev/null` is no
log. With no log, wait on pid exit.

## 3. Go idle

Tell the successor nothing more. Start no new work and message no lane. The
successor reviews your transcript against the handoff, notifies the lanes,
settles each recorded run, and retires this session through
`mise run coordinator-handoff -- retire` — never a bare `claude stop`.
