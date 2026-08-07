# issue-filer — the four "eventual" issues from the #601 post-mortem

**Session 2026-08-06 · agent `issue-filer` · delivered 19:59Z**

⚠️ **Provenance note.** This is the one report of the eight with no `report.md`
on disk — the agent reported the harness refused a subagent Write to that
filename and returned its findings as its delivery message instead. (Two sibling
agents wrote `report.md` without trouble in the same session, so the block was
not universal; a third worked around it as `DECISIONS.md`. The disagreement is
recorded rather than resolved.) The content below is that delivery message,
reproduced verbatim, so the record is not lost to a filename.

---

## Delivered

Four issues filed on `ray-manaloto/dotfiles`, all four verified as sub-issues of
map #556. No repo writes; no PR touched.

- **#605** — Add a `reflect` DAG node type: measure a review loop instead of
  noticing it
- **#606** — `mise run review-brief`: render a bounded adversarial-review brief
  by default
- **#607** — SUSPECT: `.claude/agents/rule-coverage-auditor.md` — answer "would
  it have caught anything?" before building
- **#608** — probes-need-a-control-arm: two proposed clauses (§N1
  claims-need-a-call-site, §N2 reachability-delta)

All carry the pre-existing `wayfinder:task` label (applied, not created — no
labels or milestones created).

## Sub-issue linkage, verified with a control arm

#556 went **29 → 33** sub-issues; 557-583 + 602 + 604 before, plus 605-608
after. Probe: all four report PRESENT; #601, #603, #600 report ABSENT — and #601
is a real OPEN issue (`dag_tick: blocked ∧ needs≠∅ must classify NEEDS_HUMAN…`)
that was simply never linked, so the ABSENT is a real negative rather than a
blind probe.

## §N1 collision check (the caller's explicit ask on #608)

It had NOT landed as of file time. Measured on
`.claude/rules/probes-need-a-control-arm.md` at `fix/601-dag-tick-needs-human`
HEAD, clean tree:

- `grep -c "control arm"` → **6** (positive control: the probe reads the file)
- `grep -c "call site"` → **0**
- `grep -c "reachab"` → **1** (rule 3's "unreachable" only)

#608's body carries that block verbatim *and* tells whoever picks it up to
re-run it rather than trust it, since the sibling agent's decision may land
after this filing.

---

## What happened to these afterwards (added by the caller at persistence time)

- **#606 became the session's P0.** It carried the post-mortem's unqualified A3
  stop condition verbatim, as the **build spec** for `mise run review-brief`,
  claiming it "leaves rounds 4-7 untouched". A staleness audit later settled
  from the verdict table that the unqualified form fires at v2 and ships
  **5 HIGH + 2 MEDIUM**. #606's body was corrected in place, with anchor asserts
  and both probe arms verified.
- **#608's §N1 question was answered**, and a comment recording the resolution
  was added: the write-time half stays filed, its review-time half shipped as
  **Q-CLAIM** in `.claude/skills/adversarial-review/SKILL.md`, and §N2's material
  landed in `tests/AGENTS.md`.
- **#610** was filed later the same session as a fifth sub-issue (the
  classifier-axes match/dict-dispatch residual), taking #556 to 34.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the repo the issues were filed on; #556, #601-#608.
