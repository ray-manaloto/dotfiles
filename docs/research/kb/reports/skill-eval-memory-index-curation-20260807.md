# `/skill-creator` eval of `memory-index-curation` — a NULL RESULT, and two tool bugs

**Date:** 2026-08-07 · **Outcome:** the eval could not distinguish the improved
skill from the original. Recorded so nobody spends the tokens again without
changing the design.

Raw artifacts (4 sandboxed memory-dir fixtures per iteration, per-run
`grading.json`, agent reports) lived in a session-scoped scratchpad and were
deliberately **not** promoted — the conclusion below is the durable part, and
the fixtures were four copies of a 246-file memory directory.

## Design

- **Subject:** `.claude/skills/memory-index-curation/SKILL.md`, before vs after
  the 2026-08-07 edit (PR #643).
- **Baseline:** the OLD skill version, snapshotted — not "no skill". For an
  *improvement*, a no-skill baseline flatters the result, because both arms
  would otherwise carry the verify→migrate→shorten discipline that already
  existed and the delta would measure the original skill, not the edit.
- **Isolation:** `memory_index.py` honours `CLAUDE_CONFIG_DIR`, so each run got
  its own copy of the real memory dir. Armed before use: sandbox reported
  **105** entries vs the real **104**.
- **Fixture:** 22,030 B (88.1% of the 25 KB cap) with **two planted index-only
  facts** — issue ref `#9971` and sha `deadbe7`, present in a hook and absent
  from its topic file. That makes the skill's whole purpose gradable: a run that
  trims without migrating them destroys them, provably.
- **12 runs:** 2 tasks (trim-to-target, delete-a-memory) × 2 arms × 3 iterations.

## Result

| | iter-1 | iter-2 | iter-3 (process assertions) |
|---|---|---|---|
| new skill | 9/9 | 9/9 | ~7/8 |
| old skill | 9/9 | 9/9 | ~7/8 |

**No assertion — outcome or process — reliably separated the two versions.**
Both arms hit every byte target and preserved both planted facts every time.
Final trim sizes across runs: 17,478 / 17,377 / 17,090 / 16,917 / 16,836 B
against a 17,500 B target.

The honest reading: the original skill's core (verify → migrate → shorten, and
"a clean `rc=0` is a floor, not a clearance") was already sufficient to make a
capable agent do the right thing. The 2026-08-07 additions are defensible
because each claim is independently **true**, not because they measurably change
behaviour.

One thing the old-skill arm did that neither version documents: a corpus-wide
grep that found a **prose-only** fact the checker is structurally blind to, and
migrated it. Better than the new text asks for.

## What the exercise actually produced

Four defects, none of them in the skill:

1. **A rigged fixture (mine).** The first build sat at 17,609 B = 70.4% while the
   prompt claimed 88%, so "trim to under 70%" was nearly satisfied on arrival and
   that assertion could only pass. Caught mid-flight and rebuilt.
2. **An assertion that rewarded scope creep (mine).** "Checker ends rc=0" on the
   *delete* task imported the fixture's unrelated planted facts, so the arm that
   did work outside its brief scored the point. Dropped.
3. **Three premature gradings (mine).** Report-file stability is NOT agent
   completion — an agent goes quiet while thinking. Twice the numbers reported
   were artifacts of scoring a still-running run; one sandbox was still mutating
   90 seconds after a "quiescent" check passed. Only a 4-minute window held.
4. **Two upstream `/skill-creator` bugs** (see below).

## Upstream bugs

- **Trigger eval is non-functional here.** `run_eval.py` reports ~0 recall for
  every description, including a query that names the skill outright — the
  control arm that proves it is the probe, not the description. Known upstream:
  `anthropics/claude-plugins-official` **#4425**, **#2678**, **#2003** (plus
  #632, #4692, #3172, #1749), all OPEN, with fix PRs #3339, #3714, #1988 all
  **closed unmerged**. Root cause per #4425: it registers the description as a
  *slash command* then watches for a *`Skill`* tool call.
- **`improve_description.py:147` silently adopts prose as the description.** A
  missed `<new_description>` regex falls back to `text.strip()`, so a
  conversational reply becomes the candidate — the literal string
  `"Description delivered above."` was evaluated as a description. Filed as
  `anthropics/claude-plugins-official` **#5069** (not previously reported; dedup
  control-armed across six query shapes).

## If someone retries this

Do not reuse these assertions. Both tasks are ones a capable agent completes
correctly from either version, so they cannot discriminate. A design with a
chance would need a task where the *wrong* procedure produces a *different
artifact* — e.g. an index whose only copy of a fact is a prose sentence the
checker cannot extract, where a naive trim measurably loses it.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the skill under test and its checker.
- [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) — `/skill-creator`; issues searched for dedup and #5069 filed.
