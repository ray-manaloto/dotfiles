# Cold review — coordinator-auto-handoff `0e068e60` (round 3, T1-T5)

- Subject: `0e068e60c7dc2d60b8794fa370993ec985fe972b` ("fix(coordinator-handoff): review round-3 corrections T1-T5")
- Base: `dd871ef74fb44a05ad2f4626c9beede94576dead` (parent, verified `git rev-parse 0e068e60^`)
- Diff: `git diff dd871ef7 0e068e60` — 15 files, +941 / -103
- Author family: codex. Reviewer: cold-reviewer (Claude Opus), diff-only, read-only probes.
- Constraints honoured: no tests, bun, tsc, lint or gate executed (host slot discipline). The only
  code executed was `_REDIRECT_RE` + `_log_path` extracted verbatim from `git show <ref>:…` and run
  in the project venv's Python 3.14 against a captured `ps` string (probes P1/P2).
- Memory: consulted `.claude/agent-memory-local/cold-reviewer/` (round-1/2 hotspots: rollback
  re-fire loops, started-but-unrecorded, probe-done-after-failure, wrapper `/dev/null` prelude).
- Brief shape: open hunting (no enumerated domain was supplied), so per the adversarial-review
  skill this round cannot end the loop by itself; findings carry a Q-SCOPE disposition.

Status: COMPLETE

## Verdict

**SHIP** — with F1 fixed in this unit (it is a SKILL.md text change, no code round needed) or
ticketed before merge; F2-F9 are ticket recommendations, not change requests.

No HIGH. Every T-item is implemented as its own clause describes (bounded check, table below).
The two MEDIUMs are consequences the T-items introduced but did not cover: an rc-3 start
failure now leaves an idle coordinator whose status line reads healthy (F1), and the new
`probe_pending` marker has no expiry (F2) — the same defect class that T5/F8 just removed from
`launch_pending`.

## Findings

| # | Severity | Claim | file:line | Q-SCOPE | Blocks ship? |
|---|---|---|---|---|---|
| F1 | MEDIUM | After `launch` rc 3 the level is kept, but the skill then goes idle (§3), so no turn may ever reach the "next step". The status line meanwhile reads a healthy `handoff next @35%`, so a failed start is invisible and the session can stall without a successor. | `.claude/skills/coordinator-handoff/SKILL.md:75-76`, `:85-88`; `python/src/dotfiles_setup/coordinator_handoff.py:1000`, `:299-303`; `.claude/skills/coordinator-handoff/hooks/register.ts:155-156` | in scope (T1 changed the rc-3 semantics and rewrote this SKILL sentence) | DO NOT SHIP until the rc-3 SKILL text is fixed or ticketed |
| F2 | MEDIUM | `probe_pending` has no TTL. If the `command.run` promise never settles (module reload, session exit or resume while the probe is queued), every later probe decide returns `probe-in-progress`. The status then reads `handoff probe pending` for the rest of the session, and no documented recovery exists. This is the same "unconfirmed marker blocks forever" class T5/F8 fixed for `launch_pending`. | `python/src/dotfiles_setup/coordinator_handoff.py:297-298`, `:308`; contrast `:86`, `:233-253`; `.claude/skills/coordinator-handoff/hooks/register.ts:166`, `:283-288` | in scope (T4) | SHIP (PROBE is a validation-only mode); ticket |
| F3 | LOW | The T3 fallback parses after the LAST `eval '`. A user command containing its own `eval '…'` therefore yields the inner eval's redirect with a stray quote (`/tmp/inner.log'`), not the run's real log. The harness's own `eval '` is the FIRST occurrence. The test pins an unescaped nested-eval shape the harness never emits. | `python/src/dotfiles_setup/coordinator_handoff.py:468`; `tests/test_coordinator_handoff.py:1651` | in scope (T3; the spec's "LAST" premise is the error) | SHIP; ticket (`partition` instead of `rpartition`) |
| F4 | LOW | A shape T3 newly reaches: a nested-shell user command whose redirect is its last word (`zsh -c 'mise run ship > /tmp/z.log'`) resolves to `/tmp/z.log'`. `_REDIRECT_RE`'s bare-word group does not exclude quotes. This was unreachable on the wrapper path before T3, because the prelude's `/dev/null` always matched first. | `python/src/dotfiles_setup/coordinator_handoff.py:126-128`, `:474-480` | sibling (pre-existing regex, newly reachable) | SHIP; ticket |
| F5 | LOW | rc 4 says "do not relaunch". Nothing enforces that when BOTH the receipt write and the main-state write fail: the un-started `launch_pending` goes stale after 15 min, and the hook re-fires at the next step and relaunches. The SKILL's "Its pending record is marked `started: true`" is then false. The author acknowledged this limit, but the text still asserts it unconditionally. | `python/src/dotfiles_setup/coordinator_handoff.py:964-973`, `:1002-1008`; `.claude/skills/coordinator-handoff/SKILL.md:77-80` | in scope (T2 wording) | SHIP; narrow the SKILL sentence |
| F6 | LOW | rc 3 via "cannot finalise state" (start failed AND the main lock or write failed) leaves `launch_pending` in place. The SKILL's "pending state is removed" is false on this path, and for 15 minutes decide reports `launch-in-progress`, so the status reads `handoff launch in progress` when no launch is in progress. | `python/src/dotfiles_setup/coordinator_handoff.py:1009-1012`; `.claude/skills/coordinator-handoff/SKILL.md:75-76`; `register.ts:161-162` | in scope (T1 text) | SHIP; ticket |
| F7 | LOW | In PROBE mode `releaseFailure` overwrites the cause ("skill not listed", "command.run rejected: …", "delivery failed: …") with the fixed string "probe delivery failed". The cause is never shown or logged, so a failed probe cannot be diagnosed from the status, toast or log. | `.claude/skills/coordinator-handoff/hooks/register.ts:175-178` | in scope (T4) | SHIP; ticket (append the cause) |
| F8 | INFO | `confirmProbe` shows `handoff probe done` on any rc 0 of `release --probe --delivered`, but python returns 0 and sets nothing when `probe_pending` is already absent. Separately, a previous attempt's `probe delivery failed` keeps showing while a retry is in flight, because `probeErrors` is cleared only on success. | `register.ts:209-211`, `:258-261`; `coordinator_handoff.py:414-417` | in scope (T4) | SHIP |
| F9 | INFO | Stale operator text. The `release` subcommand help still reads "Restore an undelivered firing level", and `release`'s docstring "Undo only this undelivered fire", though it now also confirms delivered probes. `launch`'s bare `except OSError` labels any non-state OSError (stdout `BrokenPipe` from `_write`, `transcript_path` glob) as `state-write-failed`. | `coordinator_handoff.py:1205-1207`, `:401`, `:876-878` | in scope (T4/T5 text) | SHIP |

### F1 detail — the trace

1. `launch` gets `claude --bg` rc ≠ 0. `_start_successor` deletes only `launch_pending` (`:1000`)
   and returns 3. `last_fired` stays at the fired level (T1, by design and per Ray's ruling).
2. The skill's §2 rc-3 sentence (`SKILL.md:75-76`) says "the hook retries at the next step". §2
   gives no instruction to keep working, and §3 (`SKILL.md:85-88`) says "Start no new work and
   message no lane".
3. `session.measure` fires "After each turn, and when a plan limit's percent used changes" (KB
   `plugins__mods__reference.md:111`, re-read). The hook acts only when `e.changed` includes
   `context` (`register.ts:300`), so a plan-limit event cannot advance it; only turns can. The idle session gets turns only from lane messages. No successor exists, so the
   lanes still report to the idle old coordinator. The retry needs ≥ one step of context growth
   (for example 5% of a 1M window) from those turns.
4. Every measurement meanwhile returns `below-next-step` (`:299-303`), which the hook renders as
   `handoff next @35%` (`register.ts:155-156`). No warning is raised (`_launch_in_progress` returns
   False with no warning when there is no pending entry, `:235-236`). The file's own contract
   says "every failure is a value" and that a broken trigger must not look like "below the limit"
   (`register.ts:13-19`). Here it does.
5. Before T1 (round 2), the very next turn re-fired. That was the loop T1 removed, but at least
   it was visible. Now the failure is silent until the next step.

Q-CLAIM: the clause "the hook retries at the next step" has an enforcing line, `_judge`'s
threshold. Nothing guarantees a next measurement once §3 idles the session.

Suggested in-unit fix (text only): on rc 3, record the failure in the handoff and do NOT go
idle; keep coordinating, because the next fire comes at level + step. Optionally ticket a
persisted `start_failed` marker that `decide` surfaces as a warning, so the status reads e.g.
`handoff start failed; retry @35%`.

### F2 detail

- The only path that clears `probe_pending` runs inside the module that fired it:
  `.then(confirmProbe)` or `.catch(releaseFailure)` (`register.ts:283-288`).
- The vendored types say `command.run` is "queued and run once the session is idle"
  (`.claude/types/claude-code.d.ts:2623-2634`). The window between fire and settlement therefore
  lasts as long as the session stays busy.
- The KB mods API says "Timers stop when the module reloads" (`plugins__mods__api.md:136`).
  Whether a pending `command.run` promise survives a hot reload is UNVERIFIED.
- `launch_pending` carries a 15-min TTL (`:86`, `:250`); `probe_pending` carries none. The SKILL
  (`SKILL.md:20-22`) does not mention manual recovery (`release --probe`).

## Bounded check — is each T-item implemented as its clause says? (5 items)

| Item | Clause | Enforcing line(s) | Result |
|---|---|---|---|
| T1 | rc 3 keeps `last_fired`, clears only `launch_pending` | `coordinator_handoff.py:995-1001` (no `_rollback_fire` on the start path any more); test `tests/test_coordinator_handoff.py:1228` asserts 45 kept, 49.9 quiet, 50 fires | implemented; see F1, F6 |
| T2 | rc 4; `started: true` pending; decide → `already-launched` regardless of age; retire accepts; docstring rc 0/2/3/4 | `:291` (checked before the TTL at `:293`), `:851-861`, `:983-990`, `:995-1008`, `:1109-1117`, docstring `:826-834`; receipt sidecar `:263-284`, `:964-973` | implemented, plus an independent receipt; see F5 |
| T3 | Parse only after the `eval '`; `/dev/null` → no log; brief "wait on pid exit" | `:468-480`, `:659`, `:715`; P1 shows the base returns `/dev/null` and the subject the real file | implemented; see F3, F4 |
| T4 | Probe used only after `command.run` resolves; rejection → `release --probe` + `handoff ERROR: probe delivery failed`; `probe done` only after success | `:297-298`, `:308`, `:414-417`; `register.ts:175-216`, `:279`, `:283-288` | implemented; see F2, F7, F8 |
| T5 | F6 distinct reasons; F7 10-min negative TTL via `$.clock.now`; F8 unknown age → stale + warning; F9 ≤3 pending reads then one ERROR | `:781`, `:785`, `:843`, `:870-878`, `:1270`; `register.ts:219-226`, `:249`; `:247-249`; `session-start/hooks/register.ts:192-216` | implemented |

Arm-count arithmetic (not executed): the coordinator harness goes from 34 to 40 arms (3 from the
T4 failure loop plus 3 single T4 arms; the T5 block replaces S4 one-for-one), matching
`tests/test_coordinator_handoff_hook.py` `_EXPECTED_ARMS = 40`. Session-start goes from 28 to 33
(4 from the loop plus 1), matching `_EXPECTED_ARMS = 33`. Pass/fail status of every arm is
UNVERIFIED: nothing was run.

## Q-FRESH — decision→action pairs re-validated against fresh inputs?

| Decision → action | Re-validated before acting? |
|---|---|
| `decide` fire → skill → `launch` | Yes. `launch` re-reads state under the lock via `_read_launch_state` (`:849-851`). |
| `_launch_locked` reserve → unlocked `claude --bg` → finalise | Yes. Finalise re-reads under the lock and compares the pending `name`+`at` (`:975-982`). A receipt folded in by a concurrent `decide` carries the same `name`/`at`, so promotion still matches (traced). |
| probe fire → `command.run` → confirm or release | Partly. The confirm runs under the lock, but no attempt token binds it to the fire that queued it (F8). |
| negative role cache → skip decide | Yes, after the 10-min TTL (`register.ts:219-226`). |
| `retire` snapshot → `claude stop` | Unchanged by this diff (snapshot `:1313`, before the state read). Out of scope. |

## Q-CLAIM — operator-facing strings this diff adds or changes

| String (clause) | Enforcing line | Verdict |
|---|---|---|
| "launch_pending age unknown; treating as stale and ignoring" | `:247-249` | enforced |
| "recovering unreadable state from started receipt" | `:273-279` | enforced |
| decide reasons `probe-in-progress`, `state-unreadable` | `:297-298`, `:364-366` | enforced |
| launch `worktree-unavailable` / `state-locked` / `state-unreadable` / `state-write-failed` | `:842-844`, `:870-878` | `state-write-failed` over-broad (F9) |
| `census-unavailable: …` / `handoff-unreadable: …` | `:775-785` | enforced |
| "successor STARTED but not recorded — do not relaunch" (2 sites) | `:986-990`, `:1004-1008` | "do not relaunch" unenforced on double failure (F5). "not recorded" is loose: the pending-changed branch DID just record a started pending. |
| brief " — no rc file — wait on pid exit" / "With no log, wait on pid exit." | `:659`, `:715` | enforced |
| `release` help "Restore an undelivered firing level" | `:1205-1207` | stale (F9) |
| "--delivered requires --probe" | `:1303-1305` | enforced |
| hook `handoff probe pending` (2 sites) | `register.ts:166`, `:279` | can be permanently false (F2) |
| hook `handoff ERROR: probe delivery failed` | `register.ts:175-178`, `:258-261` | enforced, but drops the cause (F7) and persists during a retry (F8) |
| hook `handoff ERROR: probe confirmation failed` | `register.ts:212-214` | enforced |
| hook `handoff probe done` (confirm) | `register.ts:209-211` | rc 0 even when nothing was confirmed (F8) |
| SKILL "a miss there expires after 10 minutes of module time" | `register.ts:220`, `:249` | enforced |
| SKILL "rc 0 means started and recorded" | `:1013` | enforced |
| SKILL rc 3 "pending state is removed, the fired level is kept, and the hook retries at the next step" | `:1000`; next measurement not guaranteed | F1, F6 |
| SKILL rc 4 "Its pending record is marked `started: true` …" | `:983-998`, `:964-973` | F5 |
| SKILL "Redirect fallback skips the harness's final `eval` prelude; `/dev/null` is no log." | `:468-480` | "final" eval is wrong when the user command has its own `eval '` (F3) |
| session-start SKILL "at most three attempts … then one terminal ERROR; reload the module to retry" | `session-start/hooks/register.ts:192-216` | enforced (module maps reset on reload; `session.start` re-fires after a reload, KB `plugins__mods__reference.md:105`) |

## Probes (each with its control arm)

### P1 — `_log_path` against this session's REAL Bash-tool wrapper argv

- Captured `ps -o args= -p $$ > /tmp/cr-0e068e60-wrapper.txt`: 767 bytes, starting
  `/bin/zsh -c source <snapshot>`, with exactly one `eval '` at offset 665 and the first
  `/dev/null` at offset 99 (the prelude). The real tail after the payload is
  `' < /dev/null && pwd -P >| /tmp/claude-279b-cwd`.
- Extracted `_REDIRECT_RE` + `_log_path` verbatim via `git show <ref>:…` (ast-selected nodes) and
  ran them with `python/.venv/bin/python` (3.14.0). User commands were embedded with the
  harness's own `'` → `'\''` escaping.

| case | dd871ef7 (control) | 0e068e60 |
|---|---|---|
| measured wrapper, user redirect `> /tmp/cr-…txt` | `/dev/null` | `/tmp/cr-0e068e60-wrapper.txt` |
| no user redirect (`mise run ship`) | `/dev/null` | `None` |
| user cmd with escaped single quote | `/dev/null` | `/tmp/log.txt` |
| `mise run ship > /tmp/real.log 2>&1; eval 'echo hi > /tmp/inner.log'` | `/dev/null` | `/tmp/inner.log'` (F3) |
| `\012`-rendered newline, `> "$LOG"` | `/dev/null` | `unexpanded:$LOG` |

The base returns `/dev/null` on every row, while the subject returns the real target on rows
1-3 and 5. The probe therefore discriminates, with the base as the control arm.

### P2 — nested-shell user commands

| user command | dd871ef7 | 0e068e60 |
|---|---|---|
| control: `mise run ship > /tmp/x.log 2>&1` | `/dev/null` | `/tmp/x.log` |
| `zsh -c 'mise run ship > /tmp/x.log 2>&1'` | `/dev/null` | `/tmp/x.log` |
| `bash -c "mise run ship > /tmp/y.log 2>&1"` | `/dev/null` | `/tmp/y.log` |
| `zsh -c 'mise run ship > /tmp/z.log'` (redirect is the last word) | `/dev/null` | `/tmp/z.log'` (F4) |

### P3 — consumers of the state directory (does `<sid>.started.json` collide?)

`git grep` for `coordinator-handoff`/`coordinator_handoff`/`STATE_SUBDIR` outside the module and
tests finds only SKILL/doc/mise-task text. `git grep '\.glob('` over `python/src` finds no globber
of the handoff state dir. Control arm: the same grep found `coordinator_handoff.py:438`'s
`projects_dir.glob`, so the grep sees this module. Write temp names are distinct:
`<sid>.<pid>.tmp` vs `<sid>.started.<pid>.tmp`. Lock names are distinct: `<sid>.json.lock` vs
`<sid>.started.json.lock`. Session ids cannot contain `.` (`session_common.py:38`).

### P4 — `read_state` now raises `StateUnreadableError` (an `OSError` subclass)

The other consumer, `session_start.py`, catches `OSError` at `:290`, `:335` and `:355`, so its
behaviour and labels are unchanged.

## Other things checked and found sound

- T2 receipt: written only when `started` (`:964`), atomically (`write_state`) under its own lock.
  It is folded into state only when no `launch` exists (`:280`). A corrupt main state plus a
  valid receipt recovers with the receipt's census (`:271-279`). A corrupt receipt fails closed
  (`state-unreadable`, rc 2).
- The SKILL mirror under `.agents/` differs from `.claude/` only by the expected path rewrites
  (lines 10 and 37).
- T5/F8: a `started: true` pending is checked BEFORE the TTL logic in both `_judge` (`:291`) and
  `launch` (`:851`), so "stale" never un-blocks a started successor.

## Ticket recommendations (escape hatch)

1. F2 — give `probe_pending` the same TTL/stale-warning treatment as `launch_pending`, and
   document `release --probe` as the manual reset.
2. F3/F4 — take the FIRST `eval '` (`str.partition`); exclude `'"` from `_REDIRECT_RE`'s bare
   word; replace the test row at `tests/test_coordinator_handoff.py:1651` with a harness-escaped
   (`'\''`) nested eval whose correct answer is the outer run's redirect.
3. F5/F6 — narrow the rc-3/rc-4 SKILL sentences to what the code guarantees.
4. F7/F8 — keep the cause in the probe ERROR; clear `probeErrors` when a retry fires; have
   `release --probe --delivered` return non-zero when nothing was pending.

## GitHub repos touched

_None._ Local evidence only: this worktree's git objects, the vendored
`.claude/types/claude-code.d.ts`, and the knowledge-base's offline mirror of the Claude Code docs
(`~/dev/github/ray-manaloto/knowledge-base/sources/media/claude-code-docs/plugins__mods__{api,reference}.md`).
