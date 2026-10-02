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
`DOTFILES_COORDINATOR_HANDOFF_STEP_PCT` (default 5) above it. The judgement
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

It records the census of this session's live heavy runs (ship, land, sync,
verify-local, bounded-wait, kb-ship, kb-land), then starts
`claude --bg -n dotfiles-<Chicago ISO ns>.coordinator` from the main checkout
with a brief carrying the transcript path, the handoff, the ship queue, the
census and the queued questions. rc 2 means it refused (missing handoff, not a
coordinator, census unavailable): record that in the handoff and stop.

## 3. Go idle

Tell the successor nothing more. Start no new work and message no lane. The
successor reviews your transcript against the handoff, notifies the lanes,
settles each recorded run, and retires this session through
`mise run coordinator-handoff -- retire` — never a bare `claude stop`.
