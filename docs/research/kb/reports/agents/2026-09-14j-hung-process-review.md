# Hung processes: every incident, the common defect, and the fix — 2026-09-15

Consolidated review requested at handoff. **Six incidents across this session
and the historical record, all the same defect in different costumes**, plus the
ratified design for preventing recurrence.

## The incidents

| # | Incident | Lifetime | How it was found |
|---|---|---|---|
| 1 | `until [ -f pin-actions.json ]` exited INSTANTLY against a file from an earlier run | n/a | noticed only because durations looked wrong |
| 2 | `until ! pgrep -f "dotfiles-setup gate run"` matched its OWN waiting shell | ~5 min, killed | `ps` showed the "gate runs" were my own zsh wrappers |
| 3 | orphaned `until [ -f pytest.json ] && [ -f pin-actions.json ]` wait loop | **32 min** | **the operator's status line ("1 shell")** — my sweep said none |
| 4 | 17-day-old `tail -f` wait loop from session `58dab3e3` | **17d 13h** | `mise run reap` dry run |
| 5 | two overlapping `gate run` loops interleaving into one receipt directory | ~1 h | a receipt's age was OLDER than a gate that runs before it |
| 6 | historical: `hk run pre-commit --all` at 0% CPU, no children | **~7 h** | `.claude/rules/long-running-command-hangs.md` |

## The common defect

**Every one is a wait whose terminating condition could not occur, or a probe
that could not observe the thing it was waiting on.** Neither is detectable by
reading the code — each looks correct. What they share is that *no arm of the
check can produce the other answer*:

- **#1** the file already existed -> the wait was a no-op. **Delete the artifact
  first, or the wait proves nothing.**
- **#2** the pattern appears in the waiting shell's own argv -> self-match,
  never exits. A `pgrep -f "<literal>"` written INSIDE a shell whose command
  line contains `<literal>` always finds itself.
- **#3** the producer of the awaited file had been killed -> unsatisfiable. AND
  the sweep that should have caught it **excluded `zsh -c source`**, which is
  exactly how the harness runs a background task: *the probe filtered out the
  category its target belongs to.*
- **#4** nothing ever enumerates another session's leftovers.
- **#5** shared mutable receipt directory with **no writer identity** — two runs'
  verdicts, each individually plausible, indistinguishable.
- **#6** a stalled process at 0% CPU is indistinguishable from a working one
  unless you sample CPU over time.

## Why the existing rule did not prevent it

`.claude/rules/long-running-command-hangs.md` already says to bound every
long-running command — and every incident above happened anyway, because the
rule governs the command being WAITED ON, not the WAIT ITSELF. The waits were
hand-rolled shell, created ad hoc, and nothing enumerates or bounds them.

`mise run reap` exists and is good — it has ancestor-chain protection, an age
floor, TERM->KILL escalation and `--strict` "for use in a gate". But
`ancestor_pids()` feeds **only** `protected_pids()` ("the set no pattern can
ever select"). **Ancestry is used for PROTECTION, never for SELECTION** — so
there is no way to ask "what is descended from me?", which is the exact question
incident #3 needed. `--pattern` is required, and a pattern is what failed.

## Ratified design (operator, 2026-09-15)

1. **A standalone task** — enumerate processes descended from this session's
   `claude` pid — **invoked by `/session-handoff`.** Not a `SessionEnd` hook:
   `SessionEnd` cannot block, and the operator chose an explicit call.
2. **Report + reap wait-loops; BLOCK on anything else.** Auto-reap the
   unambiguous shapes (`until`/`while` + `sleep` wrappers with no other
   purpose); anything else is reported and needs an explicit decision. This
   session had BOTH classes live at once — my orphan and ChatGPT.app's valid
   `codex exec` — so neither "kill all" nor "report only" is right.
3. **Address the root cause too**: a bounded-wait helper (deadline REQUIRED,
   explicit failure, never infinite) plus a `hook_guard` rule redirecting the
   hand-rolled `until [ -f X ]; do sleep` shape to it. An unsatisfiable wait
   becomes unrepresentable when a deadline is mandatory.
4. **Lands in the same PR as the `GateResult` fixes, after them** — same defect
   family: state that outlives its producer.

⚠️ **The guard rule must not ship before the helper.** A deny whose redirect
target cannot do the job is an outage, not enforcement
(`.claude/rules/mise-tasks-only.md`).

## What was done NOW, at handoff

`.claude/skills/session-handoff/SKILL.md` step 1 was strengthened with the
ancestry method, the three probe shapes that cannot discriminate, and the
unsatisfiable-wait warning. **It deliberately names no task**: `doc_refs` scans
`.claude/skills/*/SKILL.md` for `mise run <task>` references and would fail on a
task that does not exist yet — the repo mechanically enforcing the same
"redirect target must exist" principle as item 3's caveat.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — every incident and the design.
