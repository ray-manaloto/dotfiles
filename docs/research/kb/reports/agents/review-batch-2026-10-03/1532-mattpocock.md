# #1532 — /mattpocock-skills:code-review (Standards + Spec)

- Range: `63c0b6dd..e6bc086a` (first parent → squash merge), read from git objects (no checkout)
- Spec: V15-V17 of `session-audit-vagueness-2026-10-01.md` (commit `985030ac`, not on main). The spec agent corrected the brief's pointer to the 10-01c file
- Verdict: **CLEAN on both axes**. 0 hard violations, 0 spec defects; 5 standards judgement calls + 2 spec notes (all LOW)

## Standards (verbatim, from `1532-mattpocock-standards.raw.md`)

# PR #1532 — STANDARDS axis (63c0b6dd..e6bc086a, 3 files +7/-3)

## Measurements (re-derived at e6bc086a, not inherited)
- `AGENTS.md`: **11,978 bytes / 11,892 chars** (`wc -m`, UTF-8), up from 11,937 bytes. That leaves **108 chars** under the 12,000 AGM-003 ceiling. Line count stays 194.
- The `docs/research/kb/raw/**` exemption is **TRUE**. Both `scripts/check-claude-md-stub.sh:55` and `scripts/check-claude-agents-md-pairs.sh:39,43` filter with `grep -v -E '^(\.claude|docs/research/kb/raw)/'`. Control arms:
  - a synthetic `docs/research/kb/raw/x/links/CLAUDE.md` is dropped;
  - `docs/research/kb/rawfoo/CLAUDE.md` and `.devcontainer/CLAUDE.md` are kept;
  - the real tree has 13 CLAUDE/AGENTS files, 0 under kb/raw, and the 2 `.devcontainer/` files survive the filter.
  - The exemption came from PR #1486 (`3a3ca862`, found by `git log -S`).
- Spec status line: `3a861923` = #1475 and is an ancestor of e6bc086a. #1471 is CLOSED; #1473 and #1474 are OPEN. `SKILL.md:56-69` contains the health control, the planner-or-README must-hit and the per-repo existence check. Everything checks out.

## (a) Hard violations
None found. Every new claim is true at e6bc086a, AGENTS.md stays under 12,000, and no verbatim tree was edited (rule 8 holds).

## (b) Judgement calls / smells
1. **Ceiling headroom (`.claude/CLAUDE.md:4`).** "within ~500 characters of the 12,000" is still literally true, but the headroom is now 108 chars. Another +2-line edit like this one would breach AGM-003. Under verify-before-advancing ("carry a number with its CONDITION"), the line should state the measured figure and when it was measured.
2. **Inconsistent citation, a Duplicated Code / Divergent Change smell.** `AGENTS.md:61` cites **#1486** (the PR). For the same fact, `.claude/CLAUDE.md:8` and the `hk.pkl:779-781` comment cite **#1472**, an issue that is still OPEN (about betterleaks F5). One exemption is now documented in 4+ places (AGENTS.md, .claude/CLAUDE.md, hk.pkl ×2, both scripts) under two different references. That is Shotgun Surgery waiting to happen. Pick one reference, ideally the PR, since it is what shipped.
3. **Imprecise scope, `AGENTS.md:61`.** The sentence says kb/raw is exempt "from the stub check", but the scripts exempt it from the **pairs** check too. This is inherited from the `.claude/` phrasing, so it adds no new error, just the same under-statement.
4. **Mysterious Name, `research-doc-sources.md:9`.** "in-lane" is not defined anywhere in the rule. The likely intent is "a research lane outside the workflow". The fix this PR makes for a vagueness finding (V15-V17) brings in a new vague term.
5. **Speculative status prose, spec:3-5.** Repeating as-built details in the spec ("health control, planner-or-README must-hit…") duplicates SKILL.md and will drift. The pointer alone is enough.

## GitHub repos touched
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — PR/issue state for #1472, #1486, #1471, #1473, #1474


## Spec (verbatim, from `1532-mattpocock-spec.raw.md`)

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


## Summary

- Standards: 0 hard, 5 judgement calls. Worst: AGENTS.md headroom is now **108 chars** under AGM-003 12,000, while `.claude/CLAUDE.md:4` still says "~500".
- Spec: 3/3 asks fixed verbatim. Worst note: the exemption is described as "stub check" only, but it also covers the pairs check.

No MED+ finding, so no issue filed. Headroom and #1472-vs-#1486 citation drift passed to the coordinator as notes.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issue/PR state #1471 #1472 #1473 #1474 #1475 #1486
