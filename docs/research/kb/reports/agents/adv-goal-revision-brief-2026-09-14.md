# Brief — `codex-astra-advisor`, goal revision, 2026-09-14

Session `dotfiles-20260914.000`. One lane launched this session; this is its
brief. Report: `adv-goal-revision-2026-09-14.md` (same directory).

Per `.claude/rules/agent-report-persistence.md` and #601's lesson — seven
review rounds once left all seven briefs in an ephemeral scratchpad, so the
reports survived but the questions that produced them did not.

## Objective handed to the lane

Return a **VERDICT** on whether the prior session's draft `/goal` text is still
correct against the project's real, freshly-reconciled status — and if not,
return **revised goal text**. Explicitly framed as a commitment-boundary
decision, not research, because `codex-*-advisor` lanes correctly decline pure
research (trap 6 of the prior handoff).

## Load-bearing constraints carried in the brief

- **The artifact's hard constraint**: `/goal` is a Stop hook whose evaluator
  **runs no commands and reads no files** — it judges only the transcript
  (`$CC/goal.md`). Therefore every clause must demand output be PRINTED, and a
  criterion naming a command the evaluator cannot run is unverifiable by
  construction. One paragraph, no markdown, no newlines.
- **Reconciled real status supplied inline** so the lane did not re-derive it:
  branch/SHA, the three green gates from the prior session, #1053 live at rc=1,
  host mise 2026.9.7, graph stale, 28 pins behind.
- **The fact the draft may not have accounted for**: the read-only half of
  Phase 2 was already landed at `decf0aa` — `mise.toml:1627`
  `[tasks.dependency-currency]` plus
  `python/src/dotfiles_setup/dependency_currency.py`. The lane was told to read
  both before answering.
- **Settled design, not to be re-litigated**: skill → mise task → python
  module; autonomous; ships via `mise run ship` accepting auto-merge on green;
  image-build-input bumps get their own PR; on a red gate drop that pin, keep
  the rest, report it; a canary is mandatory per
  `probes-need-a-control-arm.md` rule 9.
- **Four specific questions** the verdict had to answer: (1) is clause (1)
  trivially satisfied by the already-landed reporter; (2) is excepting #1053
  while requiring the work to ship internally contradictory; (3) is
  "image bumps get their own PR" transcript-verifiable; (4) what else could the
  evaluator not confirm from the transcript alone.
- **Persistence**: write the report incrementally, create the file early, do
  not batch at the end.
- **Advise only**: no edits outside its own report path; no `ship`, `land`, or
  any git/GitHub mutation.
- Report must end with a `## GitHub repos touched` section
  (`.claude/rules/research-repo-enumeration.md`).

## Outcome

**DRAFT NEEDS REVISION.** Deciding risk: clause (4) excepted #1053 from the
test gate, but `mise run ship` runs the full unfiltered suite as a hard gate
(`pr.py:324` → `:370` → `:581`) with no path that excepts it — so the draft
permitted a transcript state `ship` can structurally never pass through, while
the settled design requires the work to ship.

All four questions answered with `file:line` citations; revised six-clause text
produced and measured at **3,958 characters** against the 4,000 limit
(`$CC/goal.md:64`).

⚠️ **The revised text is superseded** — the operator ruled that clause (1)
should be dropped now that #1053 is closed, and that `codex-astra-advisor`
should **regenerate** the goal in the next session against status current at
that time. Treat the text in the report as the base to adapt, not as final.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo under review; issue #1053 read and closed.
