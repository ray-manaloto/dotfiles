# Codex cold review — final delta, 2026-09-24

**Ref reviewed:** `48a1ee12c36de6e43482738945d89e104c50c969..e6599421fda835ceccc2f15341776b5148e9bb4d`
(base `48a1ee12`, head `e6599421`, branch `docs/session-2026-09-23d-handoff`)
**Diff size (full range):** 1530 lines; **scoped to the named focus files:** 464 lines
(well under the 1,500-line single-batch guard — reviewed as one invocation).
**Reviewer:** Codex CLI (`codex-cli 0.154.0`, GPT-5.6 Sol), via `fable-orchestrator` `codex-review` lane,
sandbox `read-only`.
**Fast mode:** off (standard tier — no FAST MODE line in the caller's request).
**Effort:** applied: xhigh (per the caller's `EFFORT: xhigh` line).
**Files in scope** (per the caller's instructions; `docs/research/kb/reports/agents/*.md` prose excluded):

- `.claude/agents/codex-astra-{adversarial-critic,advisor,claude-code-expert,implementer,operator,staleness-auditor}.md`
- `.claude/agents/codex-sol-{adversarial-critic,advisor,claude-code-expert,implementer,operator,staleness-auditor}.md`
- `.claude/rules/ai-cli-invocation.md`
- `.claude/skills/session-handoff/SKILL.md`
- `.agents/skills/session-handoff/SKILL.md`
- `docs/agents/goal-history.md`
- `docs/agents/plan-pointer.json`
- `python/verification/suites.toml`

## Findings (as returned by codex, severity-ranked)

**[P2] Cross-family reviewer selection can be keyed on the wrong actor.**
`.claude/skills/session-handoff/SKILL.md:147` (mirrored byte-identically at
`.agents/skills/session-handoff/SKILL.md:147`) requires the "bugs" review lane to be "a model
family that did NOT write the diff; when the Anthropic orchestrator wrote it,
`fable-orchestrator:codex-reviewer` (an OpenAI model)." Codex's claim: when the Sonnet wrapper
delegates implementation to a Codex lane (`.claude/agents/codex-sol-implementer.md:3-4,12-16`),
Codex — not the Anthropic orchestrator — is the one that actually wrote the change. If the
reviewer-selection logic keys on "did the orchestrator write it" rather than on the true diff
author, a Codex-authored diff could be routed to `codex-reviewer`, which is same-family with the
author and violates the row's own stated requirement (the cross-family principle this repo's
`.claude/CLAUDE.md` also states explicitly for cold review). Codex's recommendation: key the
choice on the actual authoring model, not on which orchestrator dispatched the work.

**[P2] "Current goal" prose contradicts the newly recorded execution order.**
`docs/agents/goal-history.md:1624` (the "Current goal" paragraph) still opens with "Run Phase 11
of task_plan.md first, starting with the pwf current-workflow migration…" — but the same entry's
"Changed requirement" field (`docs/agents/goal-history.md:1612`) records Ray's 2026-09-24 ruling
"ship this branch before any #1351 dispatch; build the codex step-2a remainder first," and the
entry's own "Current workflow" Mermaid diagram (`docs/agents/goal-history.md:1630-1632`) encodes
that same new order (`ship this branch -> codex 2a remainder -> class fix -> pr-loop -> /implement
-> Phase 10 step 0`), matching `docs/agents/plan-pointer.json:1`. A resume consumer reading only
the "Current goal" prose (the field goal-history.md itself designates as the canonical
restatement) could therefore start Phase 11/PWF-migration work before the newly recorded
prerequisite (shipping this branch, then the codex step-2a remainder) is satisfied. Codex's
recommendation: update the "Current goal" text to match the new order, or state explicitly which
of the two (prose vs. diagram) controls when they disagree.

## Spot-check of citations

Both citations were verified by reading the working-tree bytes at the cited lines (head SHA is
checked out, so no `git show` detour was needed):

- `.claude/skills/session-handoff/SKILL.md:147` — confirmed verbatim: the "bugs" row's "Lane"
  column reads "cold review of the branch diff by ref (base = merge-base with `main`) | a model
  family that did NOT write the diff; when the Anthropic orchestrator wrote it,
  `fable-orchestrator:codex-reviewer` (an OpenAI model)". Matches codex's claim.
- `docs/agents/goal-history.md:1608-1632` — confirmed the contradiction: "Changed requirement"
  (line 1612) and "Current workflow" diagram (lines 1630-1632) both encode "ship first, codex 2a
  remainder next, Phase 11/PWF migration later"; "Current goal" (line 1624) still opens with "Run
  Phase 11 of task_plan.md first, starting with the pwf current-workflow migration." The
  disagreement is real and both halves cited resolve to the claimed content.

No citation was found to be miscited, stale, or pointing at the wrong line.

## Other scoped files: no defects reported

Codex read the full scoped diff (all twelve `codex-astra-*`/`codex-sol-*` agent files,
`.claude/rules/ai-cli-invocation.md`, `docs/agents/plan-pointer.json`, and
`python/verification/suites.toml`) and reported no additional defects — no divergence between
the twelve near-duplicate agent files that breaks a counterpart's contract, no
gate/test breakage traced to the `suites.toml` change, and no contradiction between
`ai-cli-invocation.md` and the agent files that reference CLI invocation patterns. Codex did not
state this negative result as a separate explicit line in the final output (its `FINAL` output
covered only the two findings above plus a one-line summary); this report records that the review
covered the full scope and returned nothing further, consistent with reading the full command log
(the log shows codex diffing and reading every scoped file, including a full `git diff
--unified=80` restricted to exactly the seventeen scoped paths, before issuing its two findings).

## Uncited claims

None — codex's final output contained exactly the two findings above, both cited.

## Uncovered

None — all seventeen files named by the caller were within the single-batch diff (464 lines,
under the 1,500-line guard) and were confirmed read by codex (full-file `nl -ba` dumps and a
scoped `git diff --unified=80` restricted to exactly these paths both appear in the run log).

## Run mechanics

- Launched detached via `fable-orchestrator`'s `run-lane.sh` (`codex-review` lane, sandbox
  `sandbox_mode = read-only`), `LANE_CODEX_EFFORT=xhigh`, timeout 2400s.
- PID 54081 / watchdog 54082; total wall time ~50 minutes (well inside the 2400s bound — the
  supervisor's polling loop, not the review itself, accounted for most of the wait between
  `wait` calls returning `STILL-RUNNING`).
- Exit was clean (`EXITED`, reaped as `REAPED: 54081 (group dead)`); no watchdog kill fired.
- Raw supervisor artifacts (this session, ephemeral under `/var/folders/.../T/`):
  `codex-review-final.XXXXXX.vm7sTRYgnH` (final text), `codex-review-log.XXXXXX.uM5Sg6R1hB`
  (JSONL event log + supervisor markers). These are scratch paths outside the repo and are not
  expected to survive past this session; this report is the durable record.

## GitHub repos touched

_None._ This was a local cold-diff review; no external repo source, issue, or docs were consulted.

---

## Coordinator annotation (2026-09-24)

This review ran on npm codex **0.154.0** with model **gpt-5.6-sol** through `fable-orchestrator:codex-reviewer`'s `run-lane.sh` (Ray's `ps` screenshot at 00:28), not native 0.156.1 / gpt-6-sol. It is still an OpenAI-family read of a Claude-authored diff. Why the plugin was used and resolves the old codex: `fable-orchestrator-still-used-2026-09-24.md` (Brief U).
