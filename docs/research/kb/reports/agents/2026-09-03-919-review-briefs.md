# #919 — review lane BRIEFS (verbatim), 2026-09-03

Persisted per `.claude/rules/agent-report-persistence.md` rule 5: a findings-bearing
lane's BRIEF is as much an artifact as its report. #601 lost seven briefs to an
ephemeral scratchpad while the reports survived — the answers outlived the questions.

The implementer lane's briefs are the three spec revisions, already tracked as
`2026-09-03-919-SPEC.md`, `-SPEC-r2.md`, `-SPEC-r3.md`. The three below were
in-transcript only.

---

## `cold-review-919` (Opus, ref `33bdaed`)

COLD REVIEW. You are given a REF, not an intent. Do not ask what the change is
"supposed" to do — infer it from the code and judge it on its own terms.

Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles
REF: commit `33bdaed` (parent `7aae1d4`). Read it with `git diff 7aae1d4 33bdaed`.

Read the full surrounding files, not just the hunks:
- python/src/dotfiles_setup/hook_selfcheck.py
- tests/test_hook_selfcheck.py
- .claude/settings.json

### Your job

Find what is WRONG that the author did not see. This is a change to a GATE — a
module whose entire purpose is to fail when something else is missing. The
characteristic defect class here is a check that cannot fail, or that stops
discriminating without anyone noticing.

Specifically hunt for:

1. **Assertions that cannot fail.** For each NEW test, mutate the production
   code realistically and confirm the test actually goes red. A test that
   passes with the change reverted is a tautology. Do this by really editing
   and reverting, not by reasoning about it. Use `git stash` / a scratch copy;
   leave the tree exactly as you found it and say so.
2. **Checks weakened by the change.** Did adding this row silently change what
   a PRE-EXISTING test proves? Read every test in the file that touches the
   fixture or the events involved and ask whether its docstring is still true.
3. **Tokens that bind more than one site.** A required-substring assertion that
   matches somewhere other than the intended handler asserts less than it
   claims. Check each new token against the real `.claude/settings.json`.
4. **Assertion strings that can pass for the wrong reason** — substring
   collisions, quoting, an `any(...)` satisfied by an unrelated failure.
5. Anything else genuinely wrong: correctness, the repo's own conventions,
   comments that state something the code does not do.

### Bounds

- Read-only on the repo's tracked state. If you must mutate to prove a finding,
  restore byte-exactly and report `git status --short` afterwards.
- Every finding needs a `file:line` anchor and a concrete failure scenario:
  inputs/state -> wrong outcome. A finding you could not verify is labelled
  UNVERIFIED explicitly.
- Do NOT edit the code under review. Report only.
- Rank findings most-severe first. "No findings" is an acceptable answer, but
  if you say it, name the riskiest thing you checked and why it held.

### Stop condition

You are done when you have (a) mutation-tested every new assertion, (b) re-read
every pre-existing test that shares the fixture, and (c) either produced a
ranked finding list or a no-findings verdict naming what you checked.

Write your report INCREMENTALLY as you go to
docs/research/kb/reports/agents/2026-09-03-cold-review-919.md
— write it early and keep updating it; do not hold it in memory until the end.
Send your final findings via SendMessage before going idle.

---

## `cold-review-919b` (Opus, ref `3ac54a5`)

COLD REVIEW. You are given a REF, not an intent. Infer what the change does from
the code; judge it on its own terms.

REF: commit `3ac54a5` (parent `33bdaed`). Read it with `git diff 33bdaed 3ac54a5`.

Read the full surrounding files, not just the hunks: hook_selfcheck.py,
tests/test_hook_selfcheck.py, .claude/settings.json

### Your job

This changes the matching semantics of a GATE — a module whose whole purpose is
to fail when a hook registration goes missing or drifts. Find what is wrong that
the author did not see.

Hunt specifically for:

1. **A hole the new scoping opens.** The check now selects "owning" entries and
   falls back to all entries when none owns a row. Construct settings shapes
   where a real regression now passes green that would previously have gone
   red. The fallback branch is the obvious suspect — but not the only one.
   Consider: an entry whose command contains a required substring only
   incidentally; a row whose required substrings are split across entries; an
   empty or whitespace matcher; duplicate entries; an event whose commands are
   all rewritten.
2. **Assertions that cannot fail.** For each NEW or CHANGED test, mutate the
   production code realistically and confirm it goes red. Do it by really
   editing and reverting, not by reasoning. A test passing with the change
   reverted is a tautology.
3. **Checks weakened elsewhere.** Did the scoping change what any PRE-EXISTING
   test proves? Re-read every test in the file and ask whether its docstring is
   still true.
4. **Comments that state something the code does not do.** This diff rewrites
   two comment blocks and a module docstring, and one of them was rewritten
   precisely because the previous version was factually false. Verify each
   factual claim they now make against the actual code and git history.
5. Anything else genuinely wrong.

### Bounds

Same as the round-1 brief above (read-only, byte-exact restore, file:line
anchors, UNVERIFIED labels, no edits, ranked findings).

### Stop condition

Done when you have (a) constructed and tested at least four adversarial
settings shapes against the new scoping, (b) mutation-tested every new/changed
assertion, and (c) produced a ranked finding list or a no-findings verdict.

Report to docs/research/kb/reports/agents/2026-09-03-cold-review-919b.md,
incrementally. SendMessage final findings before going idle.

---

## `advisor-919` (fable-advisor, ship decision on `73e6e77`)

Ship/no-ship verdict, under 300 words, on this decision: is
`feat/hook-selfcheck-posttooluse-919` @ `73e6e77` ready to ship (mise run ship)?

Context. Ticket #919: assert the PostToolUse hook registration
(mise-config-context dispatcher) in the ship/land hook-selfcheck gate, so
deleting it fails the gate instead of leaving lint/pytest/verify all green. Two
respec rounds already ran (the two-round bound):

- 33bdaed: initial row. Cold review (Opus) found F1 — a LIVE, pre-existing hole:
  `check_settings_wiring` flattened all entries of a hook event into one blob, so
  a required matcher token could be satisfied by an unrelated entry
  (.claude/settings.json has 3 PreToolUse entries). Also found the row's own
  justifying comment was factually false (my spec's error).
- 3ac54a5 (round 1): "owning-entry" scoping fix. Cold review round 2 (4,000-shape
  randomized differential, mutation ledger) found the fix's command-half was a
  provable no-op, and the SAME defect class was still live on two other axes
  (command-axis splitting across entries; matcher-token pooling across "owning"
  entries via a decoy). I confirmed both holes myself with control arms.
- 73e6e77 (round 2, current HEAD): replaced pooling entirely with a
  one-single-entry rule (must satisfy ALL required substrings AND ALL required
  matcher tokens in ONE entry, no pooling in either direction). Deliberately
  rejects one unused split-entry shape (documented trade-off).

My own independent verification of 73e6e77 (not lane-reported, I ran it myself):
- 10/10 adversarial settings shapes correct, including 3 I invented beyond what
  any lane tested (qualifying entry in last position — for/else break still finds
  it; duplicate qualifying entries — green, correct; matcher WIDENED to a
  superset — green, correct).
- mise run lint rc=0; pytest tests/ 2907 passed rc=0; mise run verify 146
  passed/0 failed rc=0.
- Filed #954 separately for a real but out-of-scope gap: no suites.toml
  verification contract binds the dispatcher (deferred, not blocking).

Files read fresh this session for this decision:
python/src/dotfiles_setup/hook_selfcheck.py (current check_settings_wiring, lines
~195-254), tests/test_hook_selfcheck.py.

Decisive evidence: the 10-shape battery above (all correct) and the three gate
results (all rc=0). Question: is a third respec round warranted, or does 73e6e77
close the class well enough to ship? Is deferring #954 (no verification contract)
to a separate ticket the right call, or should it block?

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review.
