# W3 — review doctrine layer (A1, A2c, A4, A4b)

> **Filename note:** the lead asked for `report.md`. The harness hard-blocks a
> subagent Write to that name ("Subagents should return findings as text, not
> write report files"), twice. This is the same content under a name that passes,
> since it is an input to the lead's apply step.

Written incrementally. Ordered by what the lead most needs.

---

## 1. A2c placement decision: **FILE it, do not apply it**

**It collides with FILE-item #4, and the collision is fatal to both placements
the brief named.**

### The argument

"Prose was not the lever" cannot mean *never write prose* — applied uniformly it
forbids A1, A4 and A4b too, all three of which the post-mortem prescribes. The
reading that discriminates: **prose added to an already-loaded eager corpus that
already says something adjacent has no marginal effect.** Test it against the
record:

- **§N1 as proposed** — a clause in `probes-need-a-control-arm.md`. That rule was
  eager and loaded during all 9 commits
  (`session-20260806-review-loop-reflection.md:258-260`: *21 of 23 rules are
  eager, every gate green on all 9 commits*), and it already carries rule 5
  (*"a result without its control is an opinion"*) and rule 6 (*"an INHERITED
  number is not a measurement"*). The author was holding that rule and wrote the
  string anyway. **Filing §N1 was correct.**
- **A2c in the same file** has the identical property: same rule, same corpus,
  same demonstrated non-firing.
- **A new eager rule** is the same bet with a fresh header, at ~1.5–2.5 KB in
  every session forever. Unscoped rules are ~88% of the eager corpus
  (`md-size-budgets.md:168-172`), which is why that trimming program exists.

### What I rejected, and why it loses

The best case for a *new* eager rule is **salience**: the post-mortem notes
failure class 4 is on its third instance and `secrets-out-of-the-shell-env.md`
*"documents it twice and still did not promote it to a directive"* (`:269-270`)
— implying burial, not prose-ness, was the failure. Genuine argument. It loses on
the adversarial-critic's own criterion: at commit 1 the author held 21 eager
rules including two that already say *carry a claim with its condition*
(`verify-before-advancing.md`'s closing callout). A 22nd header is not obviously
different. The review-question form, by contrast, **replays** — I can show it
firing.

Also rejected: a **`paths:`-scoped rule** (impossible — creation-triggered,
`md-size-budgets.md:143-146`) and a **machine gate** (deciding what "enforces" a
clause requires semantic judgement; unimplementable).

### What I applied instead

A2c's **review-time half**, as **Q-CLAIM** — a third required brief question in
the A4 skill, beside Q-FRESH and Q-SCOPE. Zero eager cost, finite co-domain.

**Residual, stated honestly:** review-time is later than write-time. The
post-mortem's claim is *"Loop A never starts"* (`:137`). Q-CLAIM gets F1/F2 into
round 1's report instead of round 2's and F7 into round 1 instead of round 4, so
commits 2 and 3 collapse and Loop A's substring guards get written once against
already-narrowed strings. Most of the benefit, not all of it. **The write-time
half is what should be filed**, with the note that its right future form is a
mechanism, not prose.

### Bonus: the post-mortem's own A4 spec expected three questions

`:148` specifies the skill as carrying *"the **three** questions stated
generically"*. §A2b (`:121`) is titled *"**Two** brief questions…"* and lists
only Q-FRESH and Q-SCOPE. The third slot is unfilled in the source document —
and A2c is a brief-shaped question. **My Q-CLAIM placement plausibly restores
what the author intended and lost in the write-up**, rather than inventing a
deviation.

### The motivating case, verified cold

`e9da8cb` `_needs_human_reason()` in `python/src/dotfiles_setup/dag_tick.py`
shipped **one string, three clauses**:

| Clause | Enforcing line | Outcome |
|---|---|---|
| `escalated — state=blocked with a needs payload` | the classifier's conjunction | fine |
| `never auto-respawned at any age` | **none** — the harness runs a second supervisor this module cannot close | HIGH, v1 |
| `(project + label dag:needs-human)` | **none** — nothing in this process writes the label | HIGH, v1 |
| its own replacement `never respawned BY THIS TICK` (`cf6e97d`) | **none** — `execute_respawn` did not re-check | HIGH, v4 (`8c87eec`) |

`cf6e97d`'s commit body states both v1 findings verbatim.

---

## 2. ⚠️ A DEFECT IN THE POST-MORTEM — A3's replay is wrong, and A3 as written ships defects

The most important thing I found. **Read this before applying A3 anywhere.**

### The verdict table, from the corpus (`601-codex-review-rounds.md:13-19`)

| Round | Verdict | Findings |
|---|---|---|
| v1 | DO NOT SHIP | 2 HIGH · 1 LOW |
| **v2** | **SHIP** | **2 LOW** |
| v3 | SHIP | 1 LOW |
| v4 | DO NOT SHIP | 1 HIGH — **real bug**, classify→execute race |
| v5 | DO NOT SHIP | 3 HIGH — **real bugs** |
| v6 | DO NOT SHIP | 1 HIGH · 1 LOW — **real bug** |
| v7 | DO NOT SHIP | 2 MEDIUM |

### The contradiction

A3 (`:139-143`) says: *"Applied to this record it ends the loop after v2 —
killing exactly rounds 1–3, the wasted ones — and does not touch rounds 4–7,
which were proportionate."*

Both halves are wrong:

1. **It does not kill rounds 1–3.** v1 was DO NOT SHIP, so it runs; v2 runs and
   *is* the terminating round. It kills **round 3 only**.
2. **It absolutely does touch rounds 4–7 — it deletes them.** If the loop ends
   at v2, v3 never runs, `397675b` (the commit answering v3's LOW) is never
   written, and brief v4 — whose stated trigger is *"What `397675b` changed"*
   (`601-codex-review-rounds.md:770`) — has nothing to review. v4/v5/v6/v7 never
   happen, and **F7, F8, F12 and F14 ship**: 5 HIGHs and 2 MEDIUMs, including
   the two the post-mortem itself says *"ship under any severity rule"* (`:22`).

That is precisely the document's own headline VERDICT at `:12-14`:

> *"Every stopping rule the team proposed, replayed against this record,
> **ships defects**."*

**A3 is a stopping rule.** It is condemned by the verdict on line 13 and
prescribed on line 139.

### The charitable reading, and why it still needs stating

A3 is coherent *conditional on A2 (§T2 + Fix 7) and A2c both being applied* —
those make F8/F12/F14 and F1/F2/F7 not exist, so A3 then ends a loop that had
nothing left to find. **But A3 shipped alone is defect-shipping**, and A2 is a
~30-line change plus a `classifier_tables.py` registry and cardinality gate that
is in nobody's current worklist. The post-mortem never states the dependency.

### The fix I made in the skill (a deliberate deviation — flagging it)

The stop condition is now **conditioned on the round being bounded**:

> A **bounded** round returning SHIP with 0 HIGH and 0 MEDIUM ends the loop.
> A SHIP from an **open-hunting** round does not — it promotes to a bounded
> round.

Not a patch of convenience; it falls out of the skill's own spine. A SHIP from an
unbounded round means *"I did not find anything"* — termination **conceded**, the
exact thing `:71-72` says v1–v6 could only do. A SHIP from a bounded round means
the enumerated domain was **verified**, which is a real completion signal.

Replayed: v2's SHIP (unbounded) does not end the loop; it promotes to a bounded
round 3, which asks the enumeration question — the question that found the axis
at v7. Plausibly reaches v7's outcome at round 3, and does not ship F7 (Q-FRESH
catches that at round 1 regardless). **Strictly better replay than A3's, and it
does not contradict `:13`.**

---

## 3. Other things in the post-mortem I think are wrong

1. **`:99-100` — "Measured headroom: 4,888 B under the 12,000 AGM-003 cap".**
   4,888 B is the **file size** of `tests/AGENTS.md` (`wc -c`). Real headroom is
   7,112 B / 7,136 chars. The lead's re-derivation was right. Conservative
   error, so nothing was mis-sized by it — but correct it before the figure is
   cited again.
2. **`:121` vs `:148` — two questions vs three.** §A2b is titled "Two brief
   questions"; A4's spec asks for "the three questions". See §1; I read this as a
   dropped third slot, not a contradiction to resolve by deleting one.
3. **`:143` — "It was absent from the IMPORTANT list."** True, but the stated
   reason for promoting it (cheapest, aimed at the real waste) is undercut by §2.
   Cheapness is not a virtue in a rule that ships HIGHs.
4. **Not wrong, but under-stated:** `:47-48` (*"Commits 2–5 never touched
   `execute_respawn`"*) implies a stronger and safer rule than A3 —
   **do not run a review round against code that has not moved.** It has no
   defect-shipping failure mode, because it never suppresses a round on
   *changed* code. It is now in the skill's round ladder. It deserved to be its
   own prescribed item.

---

## 4. Measured sizes, every artifact against its budget

| Artifact | Measured | Budget | Verdict |
|---|---|---|---|
| `tests/AGENTS.md` after A1 | 4,864 → **6,050 chars** (insert 1,185) | AGM-003 **12,000 chars** (`md-size-budgets.md:98`) | PASS, 5,950 spare |
| `.claude/skills/adversarial-review/SKILL.md` | **236 lines / 11,477 B** | `skill` class 500 lines / 32,000 B (`md-size-budgets.md:96`); agnix 500-line cap (`.agnix.toml:33`) | PASS |
| ↳ its `description` frontmatter | **578 chars** | **1,536-char silent-truncation cliff** (`md-size-budgets.md:107-109`) | PASS, 958 spare |
| `.claude/agents/adversarial-critic.md` | **187 lines / 9,930 B** | **UNBUDGETED** — `.claude/agents/*.md` absent from the class table (`md-size-budgets.md:90-96`) | in range: `staleness-auditor.md` 169/9,235; `claude-code-expert.md` 342/41,681 |
| ↳ its `description` frontmatter | 465 chars | no documented cliff for agent descriptions | — |

**Eager-corpus delta: 0 bytes.** Nothing here touches a `.claude/rules/*.md`.

*(`wc -c` gives 4,888 for `tests/AGENTS.md` vs 4,864 chars in Python — multi-byte
em dashes. AGM-003 caps **characters**, so the char figure binds.)*

---

## 5. Risk I could not close

`.claude/agents/adversarial-critic.md` carries **`effort: high`**, per `:230`. It
is a real Claude Code field for file-based subagents — `$CC/sub-agents.md:294`,
*"Options: `low`, `medium`, `high`, `xhigh`, `max`"* (control arm:
`disallowedTools`, which our existing agents already use, is documented at `:285`
in the same table, so the probe reads that schema table correctly).

**But** `.agnix.toml:95` sets `agents = true`, `:103` sets
`frontmatter_validation = true`, and the unknown-field escape `CC-SK-017` is
disabled for **skills only** (`:110`). If agnix v0.46.0's agent schema predates
`effort`, `mise run lint-docs` flags it. **I could not test — hk/agnix locked by
the in-flight ship.**

**Fallback: delete the line.** The agent works without it (effort inherits the
session); `model: opus` is the part that matters and is proven by
`staleness-auditor.md:4`. Do **not** add an `.agnix.toml` override for one
optional field.

Minor: `docs/receipts/574.md:43` names a planned `adversarial-reviewer` agent for
the DAG `review` node — different name from either of mine, worth reconciling
when that node is built. No collision today.

---

## 6. Deliverable status

- [x] A1 — `tests/AGENTS.md` third anti-pattern, 5 sentences
- [x] A2c — decided **FILE**; review-time half applied as Q-CLAIM in A4
- [x] A4 — `.claude/skills/adversarial-review/SKILL.md` (stop condition corrected per §2)
- [x] A4b — `.claude/agents/adversarial-critic.md`
- [x] `APPLY.md` — both `tests/AGENTS.md` anchors verified unique (`grep -c` → 1)
