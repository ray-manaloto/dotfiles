# G1/G3 live probes: what happens to a running background subagent on `claude stop` and on a `/clear` sent by cross-session message (2026-10-03)

- **Requested by:** Ray's session-close ruling (B primary + narrow A), relayed by coordinator `dotfiles-20261003T153107.566780000-05.coordinator`: "First, live two-arm probes per real-integration-evidence: G1 … and G3".
- **Constraints followed:**
  - Throwaway `claude --bg` sessions only, named `probe-g1-*` / `probe-g3-*`, with cwd in a scratch dir outside the repo (`~/.claude/jobs/4daaf7e1/tmp/probes/<arm>/`).
  - No existing session was stopped, removed or messaged.
  - No heavy gates ran.
  - Every probe session was stopped, removed and verified gone.
- **Runtime:** Claude Code 2.1.288 (`claude --version`), sessions on `--model haiku`.
- **Verbatim evidence:** `docs/research/kb/raw/session-close-probes-2026-10-03/`. It holds `snap-0{1..4}-*.json` (timed snapshots of beats, subagent transcript bytes/mtime/last record and session state), per-arm `prompt.txt`, `beat.py`, `beat.log`, `launch.log`, `notified.txt`, `stop.log` and `clear-sent.txt`, plus `cleanup.log` and `daemon-log-excerpt.txt`.

## Setup (identical in every arm)

Each probe session got the same prompt (`<arm>/prompt.txt`):
- Launch **one** background `Agent` subagent (`run_in_background: true`, haiku).
- The subagent runs `python3 <arm>/beat.py` 15 times, one call at a time. Each call appends an ISO timestamp to `beat.log` and then sleeps 20 s.
- The parent records any later arrival through `note.py`.

Launch command: `claude --bg -n probe-<arm>-<HHMMSS> --model haiku --allowedTools "Bash(python3:*)" "Agent" --settings '{"crossSessionInbound":"accept"}' "<prompt>"`, with cwd = `<arm>/`.

| Arm | Session | Launched | Action |
|---|---|---|---|
| g1-ctl (control) | `787c84a4` | 16:06:48 | none |
| g1-stop | `d05956b8` | 16:07:26 | `claude stop d05956b8` at 16:08:42 (rc 0, "stopped d05956b8") |
| g3-clear | `192d4d3b` | 16:07:26 | `SendMessage` with body `/clear` at 16:08:48 |

## G1: `claude stop` **kills** a running background subagent; nothing carries over

| Snapshot | g1-ctl (control) | g1-stop |
|---|---|---|
| pre-stop, 16:08:36 (`snap-01`) | 5 beats; transcript 190,345 B, mtime 16:08:28, last record `assistant [tool_use]`; session `working` | 2 beats (last 16:08:30); transcript 173,513 B, mtime 16:08:30, last record `assistant [tool_use]`; session `working` |
| about 2 min after the stop (`snap-02`) | **11 beats** (last 16:10:37); transcript 223,166 B, mtime 16:10:37 | **2 beats** (last still 16:08:30); transcript **frozen** at 176,262 B, mtime **16:08:42**; last record `attachment` (a `remote_session_change` reminder), **not** a handback or final text; session `stopped` |

- Daemon log (`daemon-log-excerpt.txt`): `[2026-10-03T21:08:43.849Z] [bg] bg settled d05956b8 (killed)`.
- **Answer:** a user `claude stop` of a `--bg` session kills its running background `Agent` subagent mid-task. The beats stop, and the transcript stops at the stop instant without a SubagentHandback. No report is delivered anywhere.
- The control arm, with the same setup and no stop, kept beating over the same window. So the probe discriminates: the silence comes from the stop, not from the setup.
- **Consequence for HANDOVER-A:** once the old session is stopped, waiting cannot recover anything. `retire` must block **before** it stops the session, and the only way to save an unsettled subagent's work is the deadline recovery of its **transcript**. Recovery is therefore load-bearing, not a fallback.

## G3: a `/clear` sent by cross-session message **does not clear**; it arrives as plain text

- `g3-clear/notified.txt`: `2026-10-03T16:08:50.745211 cross-session message /clear from dotfiles-20261003T141519.handoff-automation-research`. The session's model received it as message text and logged it, as its prompt instructed.
- **Same session id** afterwards: the project dir holds a single `192d4d3b-….jsonl` and no new session file. The subagent kept beating: 9 beats by 16:10:36 (`snap-02`) and 11 at cleanup.
- **Answer to the sub-question "can a `--bg` session be made to `/clear` with no human?":** not by cross-session message. This matches the maintainer statement quoted on #85289.
- **Unanswered:** whether a still-running subagent's completion notification is delivered after a real `/clear`. A real `/clear` could not be driven unattended, so this half needs a human at `claude attach`. Option C (same-session `/clear`) stays **untested**, as the session-close report concluded.

## Settled-transcript shape (for the HANDOVER-A criterion)

- Intended source: the g1-ctl subagent's completion. Its arm was **unarmed**: I waited on `grep -q BEAT-DONE <transcript>`, and that string is in the subagent's own prompt, so the wait returned at once (rc 0) while the subagent was still running (last record `assistant [tool_use]`, 12-13 beats). The probe was then stopped early because weekly usage was at 92% (see below). So this arm produced no settled-shape evidence.
- **Measured instead** on two settled subagents of this lane's own session, the rev-5/rev-6 premise-verifiers `agent-a2316dfa20ba004c2.jsonl` and `agent-ac4bda499515c1f95.jsonl`. Their last two records are:
  - `assistant [tool_use SubagentHandback]`;
  - `user [tool_result {"success":true,"message":"Report delivered to your caller."}]`.
- **Contrast:** the killed g1-stop subagent ends in an `attachment` record after an `assistant [tool_use]`. The criterion "last record is the `tool_result` of a `SubagentHandback` `tool_use`" separates these two cases.

## Cost note

- The weekly usage meter on a probe's status bar read "wk 92% ↻3d". Ray asked the coordinator for a review of this.
- All three probe sessions also looped on repeated "visible output" system reminders, spending turns in `notified.txt` (g1-ctl logged 12 or more in about 4 min). That is a cost trap for any future live arm using `--bg` sessions.

## Cleanup (verified)

- `claude stop` + `claude rm` on `787c84a4`, `192d4d3b` and `d05956b8`: rc 0 each (`cleanup.log`: "stopped …", "removed …").
- `claude agents --json --all` afterwards: 53 rows. None is `787c84a4`, `192d4d3b` or `d05956b8`. The only `probe-*` row is the pre-existing `probe-nonconforming-lane-20261002` (`40910670`), which I did not create or touch. Control: `dotfiles-*` rows are present, so the listing works.
- `ls ~/.claude/jobs | grep -c -E "787c84a4|192d4d3b|d05956b8"` gives 0.

## GitHub repos touched

_None._ (Local runtime only; anthropics/claude-code#85289 is cited from the session-close report.)
