# Cold review: bd4857c..b6fd9a0 (fix/601-reflection-fixes)

Reviewed by reading code directly, without reading tickets/commit bodies/the
KB reflection report per instructions. Findings written incrementally.

## Confirmed findings

### HIGH — `check_settings_wiring`'s matcher check is defeated by substring collision: "Edit" ⊂ "NotebookEdit"

`python/src/dotfiles_setup/hook_selfcheck.py:169-174`:

```python
failures.extend(
    f"settings.json {event} hook must be scoped with matcher "
    f"{matcher!r} (tool events fire on every tool otherwise)"
    for matcher in matchers or ()
    if not any(matcher in m for m, _ in entries)
)
```

`matcher in m` is a **substring** test, not exact-token match. The widened
tuple (`hook_selfcheck.py:88`) requires `"Edit"` as one of five matcher
tokens — but `"Edit" in "NotebookEdit"` is `True` in Python. So a
`PreToolUse` matcher that silently loses its bare `Edit` token while
retaining `NotebookEdit` (e.g. `"Bash|AskUserQuestion|Write|NotebookEdit"`)
is reported as fully wired.

**Control-armed, not asserted**: ran `check_settings_wiring` against the real
`.claude/settings.json` with the matcher mutated to drop bare `Edit` (keeping
`NotebookEdit`) — **0 failures reported**. The check that this PR's own commit
message says exists specifically so "narrowing the live matcher back would
silently kill the write-time default-branch gate" while staying green
(quoting `hook_selfcheck.py:81-84`, itself citing
`probes-need-a-control-arm.md`) can itself stay green while exactly that
narrowing happens — for the `Edit` clause specifically. This is precisely the
"a clause with no enforcing line" shape the review brief asked about (Q-CLAIM):
the `Edit` requirement's enforcing line does not actually check for `Edit`,
it checks for a substring that `NotebookEdit` also satisfies.

Live impact: today's `.claude/settings.json` matcher
(`Bash|AskUserQuestion|Edit|Write|NotebookEdit`) does contain literal `Edit`,
so there is no CURRENT false pass — this is a latent gap in the gate itself,
not a currently-wrong wiring. But `mise run ship`/`land` gate on this check
(per the module docstring), so a future edit that drops the standalone `Edit`
token (plausible — e.g. someone "simplifies" the matcher list, or a rebase
collapses it) would sail through undetected, and the branch_guard write-time
gate for plain `Edit` calls would go silently unenforced exactly as #400 was
written to prevent.

Fix: exact token match (e.g. split `m` on `|` and check membership) rather
than substring containment.

### HIGH — `derive_axes` fails OPEN (and actively misleading) on a subject alias — a local `n = node` erases every field it reads

`python/src/dotfiles_setup/classifier_tables.py:281-321` (`_SubjectWalk.visit`)
matches subject-field reads via `isinstance(node.value, ast.Name) and
node.value.id in subjects`, where `subjects` is fixed at the start of the
walk (the parameter name(s) typed/named as the subject). It is never extended
when the function assigns the subject to a local variable.

**Control-armed, reproduced live** (not merely reasoned about): took the
`_COMMIT1_SOURCE` fixture from `tests/test_classifier_tables.py` (`is_needs_human`
omitting `queued_prompt` — the literal #601 round-5/6 defect this whole module
exists to catch) and added one line, `n = node`, before the existing field
reads, rewriting `node.state` → `n.state` etc. (the kind of edit a reviewer
approves without a second thought — "shorter name below"). Ran
`classifier_tables.derive_axes()` on it:

```
derived axes: ['pid_alive', 'stall_after_s', 'state_age_s']
'queued_prompt' in derived.axes: False
'state' in derived.axes: False
'tempo' in derived.axes: False
violations: [AxisViolation(kind='phantom', detail="the registry declares
['needs', 'queued_prompt', 'state', 'tempo'] but no parameter or subject
field of classify() reads them any more — drop the stale declaration ...")]
```

This is worse than a silent no-op: derivation doesn't just miss the axes, it
reports the **opposite** signal — a `phantom` violation telling the author to
**delete** the `state`/`tempo`/`needs`/`queued_prompt` declarations because
"nothing reads them any more," when they are still very much read (through
the alias). A developer following that message would strip the exact
protection #601 was built to install, and the gate would applaud.

Second sibling, same root cause (the walk only ever looks inside the single
parsed module's own AST): a predicate **imported from another module**
(`from other_module import is_escalated; ... if is_escalated(node): return
NEEDS_HUMAN`) is invisible to `_function_defs`/`_follow` — `derive_axes`
reports `pid_alive` as the only axis and `violations_for` returns **zero
violations**, though a whole new class is now decided by fields the registry
never named. Reproduced live the same way.

Neither case is live against the two *currently* registered classifiers
(`dag_tick.classify`/`branch_guard.classify` neither alias `node` nor
delegate cross-module today), so `find_violations(repo_root)` passes clean at
HEAD — this is a latent defect in the derivation engine, not a current false
pass. But the module's own stated purpose is "the only thing that catches
[an axis a hand-written list omits] is DERIVING the list from the code, with
… zero judgement" (`classifier_tables.py:17-21`), and a bare local alias of
the subject parameter is an entirely ordinary refactor with no lint or
convention in this repo forbidding it — nothing stops a future edit (in
`dag_tick.py` or in a THIRD classifier the `unlisted` scanner picks up later)
from introducing exactly this shape and getting a clean, or actively
misdirecting, gate. This is precisely the "sibling of that bug" class the
review brief asked to find in area 1: inference that fails open under a
routine refactor the tool never armed against, with no test in
`tests/test_classifier_tables.py` covering either shape (only
`test_derive_axes_follows_a_predicate_that_takes_the_whole_node`, which passes
the bare `node` name directly, not an aliased or cross-module reference).

### LOW — `project_transcripts` silently drops an orphaned session's subagent transcripts (ticket-scale, not a defect in this diff's stated goal)

`python/src/dotfiles_setup/command_audit.py:233-270`. The nested scan is
driven entirely off the ROOT file list (`proj.glob("*.jsonl")`); a
`<session-id>/` directory that survives after its sibling
`<session-id>.jsonl` root file is gone (deleted, moved, or never written for
some reason) contributes zero to `roots`, so `(proj / root.stem).rglob(...)`
is never reached for it — every subagent transcript under that orphaned
directory is silently unscanned, with no error and no note in the report.
The module's own docstring measures "of the 82 directories under the project
dir, the only one with no sibling root `.jsonl` is `memory/`" (line 256) —
true as a point-in-time measurement, not a structural guarantee, and the
audit tool has no way to notice if that stops holding (e.g. after a future
`/clear` or transcript-retention change starts pruning root files but not
subagent directories). Given the tool's own purpose is exhaustive guard-
coverage auditing, an unannounced blind spot here quietly undercounts
exactly the "subagent activity" category the recursion was added to see
(line 247-248). Recommend a ticket (not a blocking fix): assert or warn when
a `proj` subdirectory has no matching root file, rather than assuming the
2026-08-06 measurement stays true indefinitely.

## Q-FRESH — decision→action re-validation

The one place in this repo with a real classify→execute race
(`dag_tick.execute_respawn`/`execute_stop`, the #601 v4 finding) is
**untouched by this diff** — `python/src/dotfiles_setup/dag_tick.py` has zero
diff hunks between `bd4857c..b6fd9a0` (confirmed via `git diff --stat`). The
new code this diff *does* add (`classifier_tables.py`, the widened
`hook_selfcheck` matcher check, `command_audit.py`'s recursive scan) has no
decision→action pair of the same shape: each is a synchronous read-then-
decide-then-report, not a snapshot-then-later-act. The new verification
contract (`workflow.classifier-axis-enforcement`,
`python/verification/suites.toml`) explicitly disclaims covering temporal
defects ("it is blind to TEMPORAL defects — #601 round 4's classify->execute
race is not a cell in any state table") rather than silently omitting the
concern — an honest scope statement, not a gap in this diff. **Verdict:
N/A for this diff's new code; the pre-existing dag_tick.py race is out of
scope (Q-SCOPE) because it is not touched here.**

## Q-SCOPE

Both HIGH findings above are IN SCOPE: `hook_selfcheck.py` and
`classifier_tables.py` are both new/changed in this diff, and both defects
are in the new code itself, not inherited. The LOW finding
(`project_transcripts` orphaned-dir undercount) is in scope as a defect in
new/changed code (`command_audit.py`'s `project_transcripts` was rewritten
this diff) but is ticket-scale, not a blocker. `dag_tick.py`'s pre-existing
classify→execute race is explicitly OUT of scope — zero lines of that file
are touched by this diff.

## Q-CLAIM — operator-facing string audit

Walked every new/changed log line, CLI help text, violation `detail`, and hk
step description for a clause with no enforcing line:

- `hook_selfcheck.py:81-84` comment claims narrowing the matcher back "would
  silently kill the write-time default-branch gate" and calls the widened
  check a fix for "a check that can only pass" — **this is the HIGH finding
  above**: the check it describes as the fix is itself a check that can
  (partially) only pass, for the `Edit` clause specifically.
- `classifier_tables.py`'s `AxisViolation.detail` strings (`undeclared`,
  `illegal_pin`, `phantom`, `stale`, `table_missing`, `unlisted`) were spot-
  checked against `violations_for`/`find_violations`/`find_unlisted` —
  each detail string's claim (e.g. "the code reads X but the registry
  declares neither...") is generated directly from the same data the
  violation was raised from (not a separately-asserted claim), so there is
  no separate enforcement gap in the message text itself — the gap is
  upstream, in what `derive_axes` fails to find in the first place (the HIGH
  finding above).
- `command_audit.py`'s report strings (`_fail_open_section`,
  `render_report`) were spot-checked against `fail_open_summary`/`audit` —
  each rendered count traces to a real counter (`Counter`), no unenforced
  clause found.
- Did not find a third instance of the shape the brief warned is the
  branch's own history (three findings from one string across two rounds) —
  the one confirmed instance is the `hook_selfcheck.py` matcher check above.

## Severity summary

- **HIGH**: 2 (`hook_selfcheck.py` substring matcher check; `classifier_tables.py`
  alias/cross-module derivation blind spot)
- **LOW**: 1 (`command_audit.py` orphaned-session-dir undercount — ticket-scale)
- Tautology check (test_branch_guard.py / test_dag_tick.py deriving axes from
  the registry): **not a defect** — verified as a legitimate 3-source design
  (test literal ↔ registry ↔ AST-derived-from-code), the fourth meta-test each
  file adds judges the table against something external to the table, matching
  the explicit design rationale in both files' own docstrings and
  `tests/AGENTS.md`'s new "Both arms, one axis" section.

## GitHub repos touched

_None._
