# 1532 spec-axis review (raw, incremental)

- Named spec file (10-01c) V15-V17 rows audit takeover files/SKILL, NOT the PR files; 10-01c:73 says #1532 fixed V15-V17 from session-audit-vagueness-2026-10-01.md (commit 985030ac).
- True spec: 985030ac:session-audit-vagueness-2026-10-01.md V15 :233, V16 :247, V17 :261; diff matches dispositions verbatim.
- Verified at e6bc086a: 3a861923 = #1475 merge commit; #1471/#1473/#1474 exist and are research-sweep-run follow-ups (1471 CLOSED 2026-10-03, after the PR); #1486 exemption in both check scripts (:15-16, :16-17, :55/:39/:43); AGENTS.md 11978/12000 chars; in-lane path unenforced (SKILL.md:84-89, research_fanout.py has no mandatory-stage check).
- Spec file 985030ac:session-audit-vagueness-2026-10-01.md is NOT on origin/main (cat-file rc=128).

## Final report

**#1532 spec-axis review. Verdict: all three asks fixed exactly as specified. No defects; two minor notes.**

**Spec-source correction.** The brief named the V15-V17 rows in `session-audit-vagueness-2026-10-01c.md:248-276`. Those rows cover a kb takeover, a native-cli takeover and the parallel-work-split SKILL, none of which this PR touches. That file's own `:73` says "#1532 fixed V15-V17 FROM `session-audit-vagueness-2026-10-01.md`". I reviewed against that file (commit `985030ac`, branch `docs/session-2026-10-01`; `git cat-file -e origin/main:…` returns rc=128, so the file is still not on main). Coordinator plans: `brief-review-batch-20261003.md:16` assigns only this review. No brief assigned the V15-V17 fixes themselves.

Spec rows (from `985030ac`):
- V15 `:233`: "root `AGENTS.md` lists two stub/pairs exemptions; #1486 added a third". Fix: "`.claude/` has its own `CLAUDE.md` and is exempt from the stub check (so is `docs/research/kb/raw/**`, #1486);"
- V16 `:247`: "research rule header says items 2-4 are 'enforced', true only on the Workflow path". Fix: the heading "…items 2-4 are machine-enforced only inside the `research-sweep-run` workflow; in-lane and item 1 rely on this rule".
- V17 `:261`: "the research-enforcement spec carries no status…". Fix: insert the "**Status: SHIPPED in #1475 (`3a861923`)**…" line.

The diff matches all three verbatim (`AGENTS.md:61-62`, `.claude/rules/research-doc-sources.md:9`, `docs/specs/research-enforcement-2026-09-30.md:3-5`).

Facts checked at `e6bc086a`:
- `3a861923` is #1475's merge commit.
- #1471, #1473 and #1474 are all research-sweep-run follow-ups.
- The #1486 exemption is real in both check scripts (`check-claude-md-stub.sh:15,55`; `check-claude-agents-md-pairs.sh:16,39,43`).
- `AGENTS.md` is 11,978 of 12,000 chars.
- The in-lane path has no enforcement: `research-sweep/SKILL.md:84-89` only tells the agent what to do, and `research_fanout.py` has no mandatory-stage check.

**(a) Missing or only partly fixed:**
- V15 (minor): the claim says raw mirrors are exempt from "both `claude_md_import_stub` and `claude_agents_md_pairs`". The new text says "the stub check" only (`AGENTS.md:61`), while the commit message says "stub/pairs-exempt". This follows the audit's own replacement text, so it is faithful to the spec. But a reader of `:58-59` ("guaranteed by `claude_agents_md_pairs`") could still assume a raw mirror needs a pair.

**(b) Changes the audit did not ask for:** none.

**(c) Present but wrong or still vague:**
- V17 (note, not a defect): the status line was true at merge. #1471 has since closed (2026-10-03, after this PR), so the "follow-ups #1471 #1473 #1474" list is now partly stale.
- The spec body still contains the superseded "Today three sweeps…" (`:14`) and "a must-hit control query" (`:32`). That matches the audit's insert-only disposition, which handles them through the status pointer.
