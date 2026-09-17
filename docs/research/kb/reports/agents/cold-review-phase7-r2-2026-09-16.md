# Cold review ROUND 2 (Opus, by ref) of the Phase 7 working tree — 2026-09-16, verbatim

Lane: `cold-reviewer` subagent `cold-review-phase7-r2`, `model: opus`, base `3d03ea8` + uncommitted tree after the SDLC round-2 run; closure table over round 1 + fresh findings. Copied verbatim at receipt; architect dispositions in the round-3 spec (appended to the round-3 report).

---

# Cold review — Phase 7 uncommitted working tree, ROUND 2

- Base ref: `3d03ea8` -> `3d03ea86db9edc6d747e5a29208c1c07c4cd9db7` (== `git rev-parse HEAD`)
- Branch: `feat/phase7-session-handoff-sdlc-review`
- Scope: `git diff 3d03ea8` + every staged-new and untracked file
- Round 1 report: `cold-review-phase7.md` (same scratchpad). Read AFTER forming
  independent findings on the changed regions.
- Constraint: read-only. No repo gates run (another lane owns them). Gate
  verdicts below were derived by re-implementing the gate's own data model
  read-only; each states its control arm.

## `git status --short` at review time

```
 M .agents/skills/session-handoff/SKILL.md
 M .agents/skills/session-resume/SKILL.md
 M .claude/rules/long-running-command-hangs.md
 M .claude/rules/persistence-gate-retry.md
 M .claude/skills/session-handoff/SKILL.md
 M .claude/skills/session-resume/SKILL.md
 M .claude/skills/session-review/SKILL.md
A  docs/agents/plan-pointer.json
A  docs/handoffs/agentsview-2026-09-16.md
A  docs/session-review-reference.md
 M mise.toml
A  python/src/dotfiles_setup/agentsview_pass.py
A  python/src/dotfiles_setup/bounded_wait.py
 M python/src/dotfiles_setup/handoff_check.py
 M python/src/dotfiles_setup/hook_guard.py
 M python/src/dotfiles_setup/main.py
A  python/src/dotfiles_setup/plan_pointer.py
 M python/src/dotfiles_setup/reap.py
 M python/src/dotfiles_setup/session_ledger.py
A  python/src/dotfiles_setup/session_orphans.py
 M python/src/dotfiles_setup/session_review.py
 M python/src/dotfiles_setup/skills_mirror.py
 M python/verification/suites.toml
A  tests/fixtures/session_review/claude-attachment-path-arms.jsonl
A  tests/fixtures/session_review/claude-harness-attachments.jsonl
A  tests/test_agentsview_pass.py
A  tests/test_bounded_wait.py
 M tests/test_handoff_check.py
 M tests/test_hook_guard.py
A  tests/test_plan_pointer.py
 M tests/test_reap.py
 M tests/test_session_ledger.py
A  tests/test_session_orphans.py
 M tests/test_session_review.py
?? docs/research/kb/reports/agents/agentsview-session-handoff-review-2026-09-16-BRIEF.md
?? docs/research/kb/reports/agents/agentsview-session-handoff-review-2026-09-16.md
?? docs/research/kb/reports/agents/codex-sdlc-session-handoff-implement-2026-09-16.md
?? docs/research/kb/reports/agents/codex-sdlc-session-handoff-implement-r2-2026-09-16.md
?? docs/research/kb/reports/agents/codex-sdlc-session-handoff-review-2026-09-16.md
?? docs/research/kb/reports/agents/cold-review-phase7-2026-09-16.md
```

## Part 1 — NEW findings (independent pass)

All arm tables below were run read-only by importing the module from
`python/src` (and, for the parent replay, from a `git archive 3d03ea8`
extraction). No repository gate was invoked.

### HIGH

**N0 — `mise run session-orphans` can never return 0: its own `ps` snapshot
process is always a `BLOCK OTHER` descendant, and the handoff checklist item
requires zero.** `reap.snapshot` shells out to `ps`; that `ps` is a CHILD of the
Python process (itself a descendant of the claude root) and is not on the
caller's ANCESTOR chain, so `build_plan`'s `own_chain` exclusion never covers
it. Measured three consecutive times on the live tree:

```
session-orphans plan: root=70123 descendants=4
  protected caller chain: 1, 40181, 46910, 46913, 46914, 51361, 70123
  WAIT-LOOP: 0
  OTHER: 4
    BLOCK OTHER   41949 (3m19s, S+) caffeinate -i -t 300
    BLOCK OTHER   72172 (4h41m, S+) npm exec @modelcontextprotocol/server-pdf --stdio
    BLOCK OTHER   72378 (4h41m, S+) node .../mcp-pdf-server --stdio
    BLOCK OTHER   46921 (0s, R) ps -eo pid=,ppid=,etime=,stat=,args=
session-orphans: BLOCK — allow every OTHER pid explicitly with --allow
```

Run 2 -> `BLOCK OTHER 47389 ... ps -eo`; run 3 -> `BLOCK OTHER 47419 ... ps -eo`.
The pid differs every run, so `--allow` — the escape hatch the message names —
cannot cover this row. `rc=1` was read from a direct invocation with no pipe.

The skill makes this load-bearing: `.claude/skills/session-handoff/SKILL.md:310`
requires "`mise run session-orphans` reports no unallowed `OTHER` descendants",
which is now unsatisfiable. Two further rows in the same run are Claude Code's
own MCP servers and its `caffeinate`, which are session-local but not things an
operator would stop.

Control arm: the same command reports `WAIT-LOOP: 0` and a correctly populated
`protected caller chain` including the caller's own pid, so the census is not
simply broken — only the `OTHER` partition is contaminated by the probe itself.
`file:line` — `python/src/dotfiles_setup/session_orphans.py:67-81`,
`python/src/dotfiles_setup/reap.py:70`,
`.claude/skills/session-handoff/SKILL.md:310`.

**N0b — `handoff-check`'s new `forbidden_task_carrier` verdict fires on the
handoff written under the NEW convention, so `mise run handoff-check` is red on
its default target.** `_TASK_CARRIER_HEADING` matches "next task" anywhere in a
heading, including a heading that POINTS AT `task_plan.md` instead of carrying a
task. Measured on the live tree:

```
$ uv run --project python dotfiles-setup handoff-check      # newest handoff
handoff-check: 1 finding(s) in .agent/plans/session-2026-09-16c.md
- forbidden_task_carrier: `## Where the next task lives` — task_plan.md is the
  only task carrier; handoffs carry state and evidence
rc=1
```

The flagged section is the compliant one:

```
## Where the next task lives

**`task_plan.md` -> "Phase 7 — NEXT SESSION"** is the ONLY next-task carrier
(operator ruling 2026-09-16, goal 1). This file carries state, traps and
evidence pointers — no task text.
```

Corpus sweep over 69 handoffs: 48 carrier findings, of which six are
demonstrably mentions rather than carriers —
`## Where the next task lives`,
`## What the audit says beyond the next task`,
`## ⚠️ Two prior "queued next task" memory entries turned out to be STALE`,
`## Phase 18 — the next task, in order`,
`## Upstream defects to file (NEXT TASK 1) — two separate issues`,
`## ⛔ OPEN — /grilling round 3, unanswered. THIS IS THE NEXT TASK'S BLOCKER.`
The remaining 42 are genuine legacy `## NEXT TASK` headings, so the check does
mostly do its job; the defect is that it cannot express "this heading points at
the carrier".
`file:line` — `python/src/dotfiles_setup/handoff_check.py:35`,
`.agent/plans/session-2026-09-16c.md:7`.

**N0c — the generated `.agents` mirror asserts something false about the new
census task.** `skills-mirror --check` is clean (rc=0, "`.agents/skills` matches
the generator"), so this is not mirror rot — the generator's `Claude -> Codex`
RULE rewrote a sentence in which "Claude" is the SUBJECT of the census, not
harness branding, and `PER_FILE["session-handoff"]` has no reversion for it:

```
$ diff .claude/skills/session-handoff/SKILL.md .agents/skills/session-handoff/SKILL.md
127c127
< this project's current and two prior Claude sessions, and reports unbounded
---
> this project's current and two prior Codex sessions, and reports unbounded
```

`agentsview_pass` hard-codes `--agent claude` and `_session_ids` RAISES on any
row whose `agent` is not `"claude"`, so the mirrored sentence describes
behaviour the task cannot have. This is the exact class `skills_mirror.py:57`
already documents ("`Claude` there produces `Codex and Codex`").
`file:line` — `.agents/skills/session-handoff/SKILL.md:127`,
`python/src/dotfiles_setup/skills_mirror.py:166-183`,
`python/src/dotfiles_setup/agentsview_pass.py:296-297`, `:157-165`.


### MEDIUM

**N1 — the rebuilt wait-loop predicate does not fire on `while true` /
`while :` / `until false`, the single most common unbounded-poll spelling.**
`python/src/dotfiles_setup/hook_guard.py:190-204` requires the CONDITION to be
a negation, a file test, or one of seven allow-listed commands. A constant-true
condition is none of those, so the loop is skipped before the `sleep` check
ever runs.

```
allow | while true; do sleep 30; done
allow | while :; do sleep 30; done
allow | until false; do sleep 30; done
allow | while [ 1 ]; do sleep 5; done
allow | while true; do curl -sf http://x && break; sleep 5; done
DENY  | until [ -f /tmp/x ]; do sleep 5; done          <- control arm
```

Control arm stated: the same table run through `hook_guard.match` denies the
file-test and `! curl` shapes, so the probe discriminates.
`file:line` — `python/src/dotfiles_setup/hook_guard.py:172-176` (`_COMMAND_WAIT`),
`:190-196` (the `continue`).

**N2 — the condition allow-list makes the rule blind to any predicate command
outside its seven names.** Same site. Measured:

```
allow | until ssh host true; do sleep 5; done
allow | until ping -c1 h; do sleep 5; done
allow | until psql -c 'select 1'; do sleep 5; done
allow | until mise run lint; do sleep 30; done
DENY  | until gh pr checks 1 --json bucket; do sleep 30; done   <- in the list
DENY  | while ! mise run smoke; do sleep 30; done               <- via `!`
```

The `!` and file-test arms cover the common spellings, so this is a recall gap
rather than a hole in the control arm; but `until <cmd>` with no `!` is the
idiomatic "retry until it succeeds" form and it is entirely unguarded.
`file:line` — `python/src/dotfiles_setup/hook_guard.py:172-177`.

**N3 — `agentsview_pass` counts a step-3c report write only when it arrives
through `Write`/`Edit`, and this repo's own bypass-mode instruction tells
agents to write files through Bash.** `_observation` classifies
`report_write` on `name in {"Write", "Edit"}` only.

```
Write rel path             writes=1        <- control arm
Write abs path             writes=1        <- control arm
Bash heredoc write         writes=0        cat > docs/research/kb/reports/agents/x.md <<'EOF'
MultiEdit                  writes=0
NotebookEdit               writes=0
```

Corroborated on the real corpus: `agentsview session tool-calls
0dcda3e3-37ab-452c-a180-9e5cbd34fb78 --json` returns 181 rows, the census
renders `step-3c writes : 0`, and six files exist under
`docs/research/kb/reports/agents/` in the working tree. (In this particular
session the writes came from delegates, not from a Bash heredoc — so the
corpus corroborates the blind spot without proving this instance of it.)
`file:line` — `python/src/dotfiles_setup/agentsview_pass.py:220-224`.

**N4 — the census cannot see subagent sessions, so a coordinator/delegate
split reads as zero evidence.** `agentsview session list` excludes child
sessions unless `--include-children` is passed, and `_run_pass` does not pass
it; `session tool-calls <parent-id>` likewise returns only the parent's rows.
Measured: `session list --agent claude --project dotfiles --limit 3 --json`
emitted on stderr `Excluded 94 sessions by default: 94 one-shot`, and the
parent census above reports `step-3c writes : 0` and `handoff Skill : not
invoked` while the reports exist on disk.
`file:line` — `python/src/dotfiles_setup/agentsview_pass.py:292-308`.

**N4b — the condition-bound exemption is still a word sniff, now scoped to the
condition; `(?is)` makes `SECONDS` case-insensitive, so a lowercase `seconds`
anywhere in the predicate exempts the loop.** Round 1's M2 was narrowed, not
closed.

```
allow | while ! grep -q seconds /tmp/log; do sleep 5; done
allow | until [ -f /tmp/seconds/x ]; do sleep 5; done
allow | until [ -f /tmp/x ] || [ -n "$END" ]; do sleep 5; done
DENY  | until grep -q deadline /tmp/log; do sleep 5; done   <- bare word now OK
DENY  | while ! curl -sf http://x/end; do sleep 5; done     <- bare word now OK
DENY  | until [ -f /tmp/x ]; do sleep 5; done               <- control arm
```

The two DENY rows are the improvement over round 1: `_CONDITION_BOUND` requires
a `$` sigil for `deadline`/`end`, so a bare occurrence no longer exempts. The
`SECONDS` alternative has no sigil requirement and is case-folded, so it keeps
the original defect for one token.
`file:line` — `python/src/dotfiles_setup/hook_guard.py:178-181`.

**N4c — three of the four new mise tasks have no `suites.toml` wiring
contract.** `python/verification/suites.toml` gains
`workflow.session-orphans-wiring` and `workflow.bounded-wait-wiring`. There is
no equivalent for `plan-pointer` or `session-agentsview-pass`, both of which are
on the handoff checklist. Measured: `grep -n "plan-pointer\|plan_pointer"
python/verification/suites.toml` returns nothing, while the two named suites
return 14 lines. Round 1 raised this for `bounded-wait` too; that half is now
closed.
`file:line` — `python/verification/suites.toml:1491-1548`,
`.claude/skills/session-handoff/SKILL.md:309`.

**N4d — `token_usage` and `token_usage_record` are counted under one census
label, so the two record types cannot be told apart.**
`acc.skipped_records["Codex record token_usage"]` is incremented for both.
Compare the Claude side, which keys on the real type
(`f"Claude attachment {attachment_type}"`). The census exists to make
known-and-skipped telemetry visible; collapsing two types into one name defeats
that for the Codex lane.
`file:line` — `python/src/dotfiles_setup/session_ledger.py:2594-2596`.

### LOW

**N5 — a single tool-call row with a null/unparseable `input_json` aborts the
whole pass.** `_input` raises `AgentsViewError`, `main` maps it to rc 2, so one
malformed row of 181 turns a census into UNVERIFIABLE. Measured:
`census(..., [{"ordinal":1,"tool_name":"TodoWrite","input_json":None}])` ->
`AgentsViewError: tool-call row has no parseable input_json`. Control arm: the
real 181-row corpus has `missing input_json: 0`, so the condition is not
currently reachable against this archive.
`file:line` — `python/src/dotfiles_setup/agentsview_pass.py:177-192`.

**N6 — `$(...)` and backtick command substitution still hide the loop unless
the substitution itself sits at command position.** The prefix admits
`(?:\$\(|\()\s*` only after `_CMD`, which requires string start or a real
separator.

```
DENY  | $(while ! pgrep y; do sleep 5; done)
allow | echo $(while ! pgrep y; do sleep 5; done)
allow | x=$(while ! pgrep y; do sleep 5; done)
allow | echo `while ! pgrep y; do sleep 5; done`
DENY  | ( while ! pgrep x; do sleep 5; done )                 <- r1 M3 closed
DENY  | if true; then while ! pgrep x; do sleep 5; done; fi   <- r1 M2 closed
```

`file:line` — `python/src/dotfiles_setup/hook_guard.py:161-167`.

**N7 — `_SLEEP_COMMAND` misses a path-qualified or sub-shelled `sleep` in the
body.** `_SLEEP_COMMAND` is `(?:^|[;&|\n\x00])\s*sleep\b` with no
`(?:\S*/)?` and no tolerance for `(`.

```
allow | until [ -f /tmp/x ]; do /bin/sleep 5; done
allow | until [ -f /tmp/x ]; do (sleep 5); done
DENY  | until [ -f /tmp/x ]; do sleep 5; done          <- control arm
```

`file:line` — `python/src/dotfiles_setup/hook_guard.py:185`.

**N8 — `_GIT_COMMIT` runs against the RAW command while the wait-loop check
runs against the masked view, so the two classifiers in the same function
disagree about what quoting means.** In practice the `_CMD`-style anchor keeps
`echo 'git commit -m x'` out (measured `commit_ord=None`), so no false positive
was reproduced; the inconsistency is a maintenance hazard, not a live defect.
`file:line` — `python/src/dotfiles_setup/agentsview_pass.py:25`, `:210-213`.

### INFORMATIONAL (pre-existing, NOT introduced by this diff)

**N9 — `_CMD`/`_WRAPPER` backtrack catastrophically, and the new rule does not
make it materially worse.** Measured through `hook_guard.match` on
`("env A=1 " * n) + "while ! curl x; do sleep 5"` (no `done`, so every rule
fails and backtracks fully):

| n | base `3d03ea8` | working tree |
|---|---|---|
| 8 | 2.8 ms | 3.4 ms |
| 12 | 43.1 ms | 52.5 ms |
| 16 | 760 ms | 839 ms |
| 18 | 3.29 s | 3.38 s |
| 22 (no-match filler) | 42.0 s | 51.0 s |

Parent replay from `git archive 3d03ea8 python/src`. The blow-up is a property
of the nested quantifiers in `_WRAPPER`, present at base, so this is context
for a future fix rather than a finding against this diff. It is also why the
first two probe runs in this review had to be killed.
`file:line` — `python/src/dotfiles_setup/hook_guard.py:117-120`.

**N10 — leading whitespace defeats every guard rule, inherited from `_CMD`.**
`'  npx foo' -> None` while `'npx foo' -> npx`; `'  gh pr create' -> None`;
`'  until [ -f x ]; do sleep 5; done' -> None`. Pre-existing, stated so the new
rule is not credited with a hole it inherited.
`file:line` — `python/src/dotfiles_setup/hook_guard.py:121`.


## Part 2 — Closure table for round 1

Each row was RE-MEASURED, not trusted. "arm" names the probe re-run.

| id | status | evidence |
|---|---|---|
| **H1** three `workflow.goal-history` tokens dropped from the session-review skill | **CLOSED** | `grep -c` for the three tokens in `.claude/skills/session-review/SKILL.md` -> 3. Re-implemented strict `per_path_tokens` scan over EVERY suite: **1,259 tokens checked, 0 fails**. Control arm: an injected `qplzvx-nonexistent-9931` token produced exactly 1 fail, so the probe discriminates. Union `tokens` scan: 0 fails. |
| **H2** `.agents` skill mirrors stale | **CLOSED** | `dotfiles-setup skills-mirror --check` -> `skills-mirror OK: .agents/skills matches the generator`, rc=0. `.agents/skills/session-review/SKILL.md` is still a symlink (cannot rot); the other two are real files and now regenerate identically. Residual: **N0c**, a semantically wrong rewrite the generator itself produces. |
| **M1** four wrapper/nesting evasions | **PARTIALLY CLOSED** | `_WRAPPER`/`_CMD` are now used. DENY: `nohup bash -c`, `env FOO=1 bash -c`, `setsid sh -c`, `/bin/bash -c`, double-quoted `sh -c`, `if true; then … fi`, `( … )`, `$( … )` at command position. STILL ALLOW: `echo $(while … done)`, `x=$(while … done)`, backticks — see **N6**. |
| **M2** whole-string word exemption | **PARTIALLY CLOSED** | Exemption is now scoped to the CONDITION (and `timeout N` to the PREFIX). DENY now: `# timeout` comment, `curl --connect-timeout 5`, `/tmp/lint-timeout.log`, `DEADLINE=10` on a prior line, bare `deadline`/`end` words. STILL ALLOW: lowercase `seconds` in the condition, `$END` — see **N4b**. |
| **M3** `(?is)` + `done` tempering blinds the rule | **CLOSED** | The `done` terminator now requires a separator before it. `until grep -q DONE /tmp/log; do sleep 5; done` -> DENY; `until grep -q RC /tmp/log; do sleep 5; done` -> DENY (control arm). |
| **M4** false positives on bounded loops | **CLOSED** | ALLOW: prescribed `deadline=$((SECONDS+540)); while [ $SECONDS -lt $deadline ]; …`, `i=0; while [ $i -lt 40 ]; …`, `while read -r f; …`, `while IFS= read -r l; …`, `"$SLEEP"`, `timeout 60 sh -c '…'`, `timeout 10m bash -c '…'`, `for i in 1 2 3; …`, `git commit -m "<the shape>"`, `echo '<the shape>'`. `tests/test_hook_guard.py` now carries a 10-case non-fire parametrization. |
| **M5** `bounded_wait` orphans grandchildren | **CLOSED** | `start_new_session=True` + `os.killpg` at `bounded_wait.py:46-61`. Re-ran the orphan arm: `sleep 93` rc=124 survivors `[]`; `sleep 94 \| cat` rc=124 survivors `[]`; `sleep 95 & wait` rc=124 survivors `[]`. Control arm: an unrelated `sleep 91` started by the probe was visible (`['42050 sleep 91']`) and gone after an explicit kill, so the survivor query discriminates. |
| **M6** missing skill file tracebacks | **CLOSED** | `remote_from_skill` converts `OSError` to `AgentsViewError` (`:83-86`). Arm: `main(..., skill_path=/nonexistent/zqvv/SKILL.md)` -> `AGENTSVIEW PASS — UNVERIFIABLE`, **rc=2**, no uncaught traceback. Control arm: a file that exists but lacks the marker -> the same rc=2 via the documented path. |
| **M7** ordinal 0 renders as "not invoked" | **CLOSED** | `is not None` at `:259-268`. Arm: a census with `Skill session-handoff` and `git commit` both at ordinal 0 renders `handoff Skill   : ord 0  (vs first git commit at ord 0)`. |
| **M8** `--kill` reaps bounded loops | **ADDRESSED BY DECISION** | Not changed; now stated. `session_orphans.py:4-6` — "At handoff, every session-local wait loop is an orphan, including a loop whose condition carries a deadline." `format_plan` labels each row `bounded`/`unbounded` (`:102-113`), and `.claude/skills/session-handoff/SKILL.md:95-97` repeats the rule. `tests/test_session_orphans.py:131` arms it. |
| **M9** `--kill` happy path untested | **CLOSED** | Three new tests: `test_kill_reaps_wait_loop_before_unallowed_other_blocks` (asserts `[(300, SIGTERM), (300, SIGKILL)]`), `test_kill_happy_path_terms_then_rechecks_the_wait_loop` (`[(300, SIGTERM)]`), `test_kill_reports_a_wait_loop_that_survives_escalation`. |
| **M10a** concurrent runs delete each other's segments | **NOT FIXED — DOCUMENTED** | The glob-and-unlink is unchanged (`session_review.py` `_write_segmented_artifact`). Two new docstrings declare it unsupported: "Two concurrent runs targeting the same report path are unsupported because segment pruning is scoped by report name" and "Publish one generation; same-path concurrent publishers are unsupported." |
| **M10b** `.0000.json` pointer with zero segments | **CLOSED** | `newest_omission_segment` is `None` when `omission_count` is 0, and `omission_segments_to_json` now returns `()` early for an empty census; the header renders `not-published`. |
| **M11** `diagnostic_types` expansion changed attachment recording | **CLOSED** | `file_like` no longer consults `warning_types \| diagnostic_types` — it is now exactly `{"file","image","document"}`. An unknown type carrying a path becomes a LOUD omission instead of a silent diagnostic. Armed by the new fixture `tests/fixtures/session_review/claude-attachment-path-arms.jsonl`, whose two rows are precisely `instructions` + `files:[…]` and `future_shape_zzq` + `path`. |
| **L1** `forbidden_task_carrier` fires on prose and inside fences | **PARTIALLY CLOSED** | Fence-awareness added and armed: ` ``` ` block -> clean, `~~~` block -> clean, inline backticks -> clean, nested deeper fence -> only the real heading flags. STILL OPEN: a heading that merely MENTIONS the next task flags, including the compliant pointer — see **N0b**. An unclosed fence also blinds the rest of the file (arm: `# H\n\n```\nfoo\n\n## NEXT TASK — do X` -> clean). |
| **L2** `_plan_findings` silenced by deleting the pointer | **CLOSED** | New `MISSING_PLAN_POINTER` verdict. Arms in a temp root: no plan -> clean; plan + no pointer -> `missing_plan_pointer`; plan + good pointer -> clean (control arm); wrong sha -> `stale_plan_pointer`; wrong phase -> `stale_plan_pointer`; invalid JSON -> `stale_plan_pointer`; JSON array -> `stale_plan_pointer`; plan without a NEXT SESSION heading -> `missing_active_plan`. |
| **L3** tracked plan digest unverifiable from a clone | **OPEN** | `task_plan.md` is still gitignored (`.gitignore:143`). Re-measured today: `shasum -a 256 task_plan.md` == pointer `plan_sha256` == `bfb7f519651507cfb48e59a928222210b2f0e362ba0befddfdf2bb693ca3b094`, so it is fresh — but nothing enforces that. `grep` for `plan-pointer` in `python/verification/suites.toml` returns 0 lines. See **N4c**. |
| **L4** `_primary_reason` string-sniffs messages | **CLOSED** | Now compares `SelectionCertification` enum members (`EXPLICIT_SESSION_ID_UNRESOLVED`, `UNCERTIFIED_ACTIVITY_FALLBACK`) rather than substrings of prose. |
| **L5** `render_coverage` no longer begins with its H1 | **NOT ADDRESSED (by design)** | The VERDICT block still precedes `# Session requirement and promise ledger`, and has grown (source root, invoking root, pytest-temp flag, counts, omission histogram, generation, artifact paths). Consumers keying on the first line still see a change. |
| **L6** `except TypeError, ValueError:` | **N/A — re-verified valid** | `python 3.14.0`; `ast.parse` OK; module imports OK; `requires-python = ">=3.14"`, `target-version = "py314"`. Still the only reason the unusual form is needed is `_write_segmented_artifact` raising `TypeError` for a data-validation failure. |
| **L7** `bounded_wait`'s real subprocess runner untested | **CLOSED** | `tests/test_bounded_wait.py` gains `test_real_command_predicates_satisfy_or_expire` and `test_timed_out_pipeline_leaves_no_surviving_process` — the pipeline case is exactly the M5 arm, now in the suite. `main.py` now imports `DEFAULT_INTERVAL_S` instead of re-declaring `15.0`. |
| **L8** the new rule shadows a more specific redirect | **NOT ADDRESSED (unchanged)** | Re-measured: `while ! test -f x; do gh run watch 1; sleep 5; done` -> `unbounded wait loop`. As in round 1 this is still an improvement over base (which matched nothing); recorded so it is not later read as a regression. |

### Severity-ordered NEW findings

1. **N0** (HIGH) — `session-orphans` can never return 0; its own `ps` is always a `BLOCK OTHER`, and the handoff checklist requires zero.
2. **N0b** (HIGH) — `handoff-check` flags the compliant "`## Where the next task lives`" pointer; the default invocation is rc=1 on the newest handoff.
3. **N0c** (HIGH) — the generated `.agents` session-handoff mirror says the census reads "Codex sessions"; the task hard-codes `--agent claude` and raises on anything else.
4. **N1** (MEDIUM) — `while true` / `while :` / `until false` / `while [ 1 ]` are not detected.
5. **N2** (MEDIUM) — `until <cmd>` with a predicate outside the seven-name allow-list is not detected.
6. **N3** (MEDIUM) — step-3c report writes are counted only for `Write`/`Edit`, not Bash heredocs or `MultiEdit`.
7. **N4** (MEDIUM) — the census cannot see subagent sessions (`--include-children` is never passed).
8. **N4b** (MEDIUM) — a lowercase `seconds` or `$END` in the condition still exempts a loop.
9. **N4c** (MEDIUM) — no `suites.toml` wiring contract for `plan-pointer` or `session-agentsview-pass`.
10. **N4d** (MEDIUM) — `token_usage` and `token_usage_record` collapse into one census label.
11. **N5** (LOW) — one malformed `input_json` row aborts the entire census.
12. **N6** (LOW) — `$( )` / backtick substitution not at command position still hides the loop.
13. **N7** (LOW) — `/bin/sleep` and `(sleep 5)` in the body defeat the sleep check.
14. **N8** (LOW) — `_GIT_COMMIT` reads the raw command while the wait check reads the masked view.
15. **N9** (INFORMATIONAL, pre-existing) — `_WRAPPER` backtracks catastrophically; base and working tree measure the same.
16. **N10** (INFORMATIONAL, pre-existing) — leading whitespace defeats every guard rule.

### Things re-checked and still SOUND

- `descendant_pids` BFS is cycle-safe and `build_plan` protects the caller's whole ancestor chain plus `INIT_PID` — confirmed on the live tree (`protected caller chain: 1, 40181, 46910, 46913, 46914, 51361, 70123`).
- `agentsview_pass` never prints a credential: `Remote.flags()` passes `--server-token-file <path>`; the live `install-remote` line was read with `grep -n`, not `cat`, and no token value appears in this report.
- The real AgentsView schema matches the parser: `session list --json` -> `{"sessions":[{"id","project","agent",…}]}`; `session tool-calls --json` -> `{"tool_calls":[{"ordinal","tool_name","input_json",…}],"count"}`, 181 rows, `missing input_json: 0`. Every flag the module passes (`--agent`, `--project`, `--limit`, `--json`, `--server`, `--server-token-file`) exists in `agentsview session list --help`.
- `bounded_wait.wait` validation: non-positive deadline -> 2, sub-second interval -> 2, both/neither of `--file`/`--cmd` -> 2.
- `dotfiles-setup` configures logging at INFO to stderr (`main.py:3058-3062`), so `session-orphans`' plan and `bounded-wait`'s diagnostics are actually visible.
- Path citations in the new tracked docs resolve: `handoff-check docs/handoffs/agentsview-2026-09-16.md` -> `OK — citations resolve`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the tree under review.
- [kenn-io/agentsview](https://github.com/kenn-io/agentsview) — `agentsview` CLI 0.43.0, probed locally via `--help` and two live JSON calls to confirm the flags and schema `agentsview_pass.py` depends on.
