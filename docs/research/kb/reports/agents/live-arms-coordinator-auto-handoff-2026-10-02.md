# Live arms — coordinator-auto-handoff + session-start mods (2026-10-02, slot 2)

Branch `feat/coordinator-auto-handoff` @ `2119f6b6`, Claude Code 2.1.288, launched with
`claude --bg` from the lane worktree (primary dir ⇒ the branch's `.claude/skills/*` plugins load
as `@skills-dir`). Every probe session was stopped by id (`claude stop <id>`, rc=0 each). Spec §5.4
and §8 verification. Evidence logs: `~/.claude/jobs/79921362/tmp/{live-*,logs*,stops,wait*}.log`
(machine-local); the facts below are copied from them.

| Arm | Session (id · name) | Settings | Observed | Verdict |
|---|---|---|---|---|
| A dry-run heartbeat | `f6687621` · `dotfiles-20261002T214932.377186000-05.coordinator` | refuse; PCT=1; DRY_RUN=1 | first turn at 13% context; state `{"dry_run_fired": 11.0, "last_seen": {"percent": 13.0}}` (no `last_fired` ⇒ real level unspent); screen: toast `coordinator-handoff DRY-RUN: would run /coordinator-handoff f6687621-… 13 (context 13%, level 11%)`, status `handoff DRY-RUN @11%` | PASS |
| A session-start | same | — | queued `/reload-skills` (`137 skills available (no changes)`) and `/reload-plugins --force` (`Reloaded: 17 plugins · 87 skills · 33 agents · 15 hooks`) as "Prompt from the session-start plugin"; status `session-start ok`; conforming `-n` name kept | PASS |
| refuse control | A | refuse | SendMessage to A reported "in inbox"; A's transcript has **0** occurrences of the message text vs **4** of its own prompt text (positive control, same grep, same file) ⇒ not delivered | PASS |
| B ERROR arm | `5990b71c` · `…214932.729963000-05.coordinator` | refuse; PCT=1; DRY_RUN=1; `UV_PYTHON=/nonexistent/python3` | toast `coordinator-handoff: decide rc 24`; no state file (python never ran); `session-start ERROR: decide rc 2` and `session-start ERROR: pending rename failed: pending rc 2` on the status line | PASS (failure visible, not silent) |
| C real submit (P2) | `4bcfb646` · `…214933.057847000-05.coordinator` | refuse; PCT=1; PROBE=1 | transcript: `<command-name>/coordinator-handoff</command-name> <command-args>--probe</command-args>` queued by the hook's `command.run` from `session.measure`; skill loaded; reply `coordinator-handoff probe OK`; state `{"probe_fired": true}` | PASS — P2 CONFIRMED live |
| D `claude stop` teardown (ruling 9) | `5f2ebc28` · `…214933.373785000-05.teardown-probe` | refuse | before stop: `sleep 613` (pid 88271, parent zsh 88270) live; job `inFlight={'tasks':1,'kinds':['local_bash']}`. `claude stop 5f2ebc28` rc=0 → 30 s bounded wait for death **timed out (124)**; both processes alive, reparented to ppid 1. Killed by the architect afterwards. | `claude stop` does **NOT** kill background tasks ⇒ no ship/land detach ticket needed; inFlight signal confirmed |
| E rename (no `-n`, feature branch) | `9801809e` | refuse | job name → `dotfiles-20261002T215358.984283000-05.coordinator-auto-handoff`, `nameSource:"user"`; state `action: rename`, `renamed` recorded | PASS |
| F defer + `$.model.complete` 2.1.288 shape | `4cd53397`, detached scratch worktree | refuse | state `action: defer`, prefix `dotfiles-20261002T215427.646370000-05`; after the first prompt the name became `…646370000-05.investigate-flaky-timezone-parser-test` (prompt-derived slug, NOT the `.session` fallback) | PASS — runtime result shape handled (#1497 types stale) |
| G nonconforming `-n` kept (Ray 2026-10-02) | `40910670` · `probe-nonconforming-lane-20261002` | refuse | name unchanged; state `action: nonconforming`; status `session-start: name not in convention` | PASS |

Notes / residue:
- `ns` digits end in `000`: `time.time_ns()` on macOS has µs resolution. Format is correct (9 digits); precision is the host's.
- session-start state lives in the session's own checkout `.agent/state/session-start/` while
  coordinator-handoff state lives in the main checkout — consistent within each mod (session ids are unique); noted, not a defect.
- Workspace trust did not block the detached scratch worktree (F ran).

## GitHub repos touched

_None._
