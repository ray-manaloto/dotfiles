# Opus cold review — session-handoff rename (2026-08-29)

Substitute cross-family lens: diff authored by a codex-implementer lane applying an architect-written spec; grok-reviewer unavailable, so this Opus pass is the announced fallback.

## Brief (prompt sent to the agent)

Cold review, diff only. Repo: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`. The change is STAGED but not yet committed — `git diff --cached`.

Context: renames the skill `.claude/skills/clear-prep` to `.claude/skills/session-handoff`, flips its `disable-model-invocation` frontmatter field from `true` to `false` (a deliberate behavior change: the skill can now be auto-invoked by Claude, not just typed by the user — it has real side effects: it writes memory files, edits GitHub issues, runs an AskUserQuestion loop, and can commit doc changes), and updates 9 other files' cross-references to the old name.

Checked with a skeptical eye: (1) is the rename complete/consistent (control-armed grep), (2) does the rewritten frontmatter description stand alone and stay under the 1,536-char truncation ceiling, (3) does anything in the skill's own body assume it can only ever be started by deliberate user command — now false, (4) do the 9 other edited files still read naturally, (5) anything the multiple rounds of spec-fixing along the way (a wrong line count, an incomplete exclusion list) might have papered over.

## Report (verbatim)

## Findings

**HIGH — 1. The rename made two spec claims factually false.** `docs/specs/research-nudge-hooks.md:68-69` now reads "`session-handoff`, `handoff`, `resume` and `wayfinder` are all `disable-model-invocation: true`. **Claude cannot invoke any of them.**" — under a heading literally titled *"Two hard constraints that no design removes"*. This diff removed it. Same false claim at `docs/specs/ticket-bound-receipts.md:421-422` ("All are `disable-model-invocation: true`"). Mechanical replace propagated the name into sentences whose truth the same commit inverted.

**HIGH — 2. Unasked out-of-project write.** `SKILL.md:149-155` writes memory files under `~/.claude/projects/.../memory/`. Auto-invocation collides head-on with `feedback_no_user_level_file_updates` ("never touch files outside the project unasked"). The typed `/clear-prep` *was* the consent; nothing replaces it.

**HIGH — 3. Unguarded mutations under self-trigger.** `SKILL.md:194-198` stages and commits; `SKILL.md:98-99` runs `gh issue edit`/`comment`. Note the skill *does* guard the riskiest sibling — "open a PR only if the user asks" (`:197`) — which proves the author knew consent mattered, yet commit and issue-edit got no equivalent clause.

**MEDIUM — 4. Rename incomplete inside the renamed file.** `SKILL.md:8` H1 is still `# Clear-Prep — Session Handoff Before /clear`. Also `.claude/rules/agent-report-persistence.md:56`: bold lead-in "**Clear-prep audits coverage.**" sits beside a `/session-handoff` link in the same sentence.

**MEDIUM — 5. Timing assumes an imminent user-initiated clear.** `SKILL.md:10` "Run this **before** `/clear`" and `:233` "Run `/clear`, paste that line" — an unprompted mid-session fire tells the user to clear when they never asked.

**LOW — 6.** `docs/specs/research-nudge-hooks.md:146` says "(247 lines)"; file is 250 — pre-existing (`git show HEAD` also 250), but the diff edited that exact line and left the number wrong.

**LOW — 7.** `python/src/dotfiles_setup/doc_refs.py:8` retains "clear-prep" (your exclusion hid it); now a dead skill name.

## Ruled out
Grep is clean and the probe discriminates: `clear-prep` → rc=1 under your exclusions, control `session-handoff` → rc=0 across 11 files; unscoped `git grep` plus a non-git working-tree sweep found hits only in the excluded research/report trees. No hits in `suites.toml`, `settings.json`, `tests/`, or any `.toml`/`.json`. Description is 405/1,536 chars and reads standalone without the old name. Size 250/500 lines, 13,989/32,000 bytes — within the `skill` budget. The same-machine vs cross-surface distinction survives intact in `handoff/SKILL.md` and `docs/handoffs/README.md:11,38`; the other seven edited files read naturally.

## Refutation pass (architect) and disposition

- Finding 1: CONFIRMED, fixed. Both spec docs corrected to name `session-handoff` as the deliberate exception, citing the 2026-08-29 change.
- Finding 2: put to the user (Ray) as an explicit decision — resolved: auto-invocation approval covers the memory write, no separate ask needed; recorded explicitly in `SKILL.md`'s step 4 addendum rather than left implicit.
- Finding 3: put to the user — resolved: commit/issue-edit stay unguarded for self-triggered runs (no blocking question), but self-triggered runs now dispatch a cold-review pass over the exact diff/issue-comment before either executes. Added to `SKILL.md` step 4.
- Finding 4: CONFIRMED, fixed. Case-sensitive find-replace missed title-case "Clear-Prep"/"Clear-prep" — both occurrences corrected; full case-insensitive repo sweep run afterward, zero remaining hits.
- Finding 5: accepted as-is — the skill's own description already covers self-invocation framing; body imperative voice is a minor wording nit, not fixed.
- Finding 6: CONFIRMED, fixed (247 → 250, later 267 after the review-gate addition — re-verified).
- Finding 7: REFUTED — this exclusion was deliberate per the dispatch spec (a historical comment describing a past event, matching this repo's convention of not rewriting history); not a miss.

## GitHub repos touched

- None — self-contained skill-file rename review.
