# Brief — synthesis lane: reconcile the five three-image audits

**Dispatched:** 2026-09-03, session `dotfiles-20260903.003`, branch `docs/three-image-migration-audit`.
You are the barrier lane. All five parallel audits have completed and persisted their reports.

## Read these five reports IN FULL first

All under `docs/research/kb/reports/agents/`:

1. `2026-09-03-three-image-audit-CONTEXT.md` — the shared brief they all worked from
2. `2026-09-03-three-image-audit-pwf.md`
3. `2026-09-03-three-image-audit-plans.md`
4. `2026-09-03-three-image-audit-issues.md`
5. `2026-09-03-three-image-audit-docs.md`
6. `2026-09-03-three-image-audit-sessions.md`

## Your job is RECONCILIATION, not summary

The lanes agree on the headline and **disagree on things that change what happens next**. Do not
average them. For each conflict below, go to the primary source and settle it with an anchor.

### Conflict 1 — ACCEPTED, or merely PROPOSED? (the decisive one)

- `pwf` reports #849 was **"formally ACCEPTED 2026-08-30"**, citing `progress.md:47` and an
  "operator decision" string found 3x in its corpus.
- `plans` reports **"NO operator decision recorded — only the question asked, not answered."**
- `issues` and `sessions` both report **spec/proposal, OPEN, not accepted.**

Settle it. Read `progress.md:47` yourself and quote it verbatim. Does that line record an
operator RULING, or a lane's summary of a spec being published? This decides whether the next
action is "implement an accepted spec" or "get a ruling first", so it must be anchored, not
inferred. **A published spec is not an acceptance** unless someone with authority said so.

### Conflict 2 — are there ONE or TWO distinct three-image ideas?

- `docs` reports a three-image idea (**base / p2996-cache / dev** as separately PUBLISHED
  images) that was **explicitly REVERSED** ~2026-08-30d before finalization.
- `pwf`/`plans`/`issues`/`sessions` all describe a different idea: **base OS tracks**
  (amd64/26.04, arm64/24.04, arm64/26.04) per #849.

Are these genuinely two separate proposals, or one proposal that a lane mis-summarised?
Anchor whichever answer is true. If two, say plainly which is dead and which is live, because a
future session WILL confuse them — #849's own text complains that this substitution already
happened twice (#847 dropped 24.04; #848 varied the RUNNER, not the base OS).

### Conflict 3 — independence

The `sessions` lane says it "integrates with existing findings from the issues and docs audit
lanes." If it read their reports rather than deriving from transcripts independently, its
agreement is **not** corroboration. Assess this and say so. Three lanes agreeing because two
copied the third is one data point, not three.

## Then answer the operator's actual question

> *"is `:dev` correct?"*

Give a direct answer with its condition attached — correct **today**, and correct **under #849
if delivered**, are two different claims. State both.

## Then produce the decision-ready part

1. **Delivery gap** — what exactly is missing for #849, in concrete terms (bake axis, CI legs,
   the `:dev-ubuntu2404` index, `mise run up` selection, smoke). Anchor each to a file.
2. **The unsolved sub-problem** — #849 flags that base OS is an input to the base tier's
   **content hash**, which is what lets CI skip a ~2.5h cold build, and says nobody specified
   what the probe does when base OS stops being a single global value. Is that STILL unsolved?
   Check `python/src/dotfiles_setup/` content-hash code and `docker-bake.hcl`. This is the thing
   most likely to be the real blocker.
3. **What is stale and should be corrected** — e.g. the `docs` lane found `AGENTS.md` calls
   `:dev` "the base image" without noting it is a dual-arch manifest list (#676).
4. **Recommended next action**, with the cheapest first step. Note that each CI attempt costs a
   ~2.5h base build, so a plan that front-loads local verification is worth more than one that
   iterates in CI.

## Rules

- Every claim gets a `file:line`, an issue number, or the command that produced it.
- **Control-arm every negative** (`.claude/rules/probes-need-a-control-arm.md`); invent the
  known-absent control string fresh rather than reusing one from a prior report.
- Where a lane's claim does not survive your check, **name the lane and overturn it**.
- Do not edit any file except your own report.
- Write incrementally to
  `docs/research/kb/reports/agents/2026-09-03-three-image-audit-SYNTHESIS.md`.
- End with `## GitHub repos touched`.
- **SendMessage your summary LAST**, before going idle.
