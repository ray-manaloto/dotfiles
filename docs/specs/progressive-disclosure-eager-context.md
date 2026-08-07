# Spec — Progressive disclosure for the eager instruction corpus

**Status:** SPEC ONLY. No code ships from the session that wrote this (Ray's
ruling, 2026-08-07). **Supersedes the scope of #476**, which is re-scoped to this
design; #476's measurements are preserved verbatim.

**Branch:** `spec/476-progressive-disclosure` · **Grilling:** 15 decisions across
5 rounds, 2026-08-07 · **Research:**
`docs/research/kb/reports/agents/cc-expert-lazy-context.md`

---

## 1. The measurement this rests on

Taken fresh 2026-08-07, using `kb_setup.md_budget`'s **own** classifier over
`git ls-files '*.md'` — not a second implementation, so the breakdown cannot
disagree with the gate. Control arm: per-file sum 114,422 B + `AGENTS.md`
10,954 B = **125,376 B**, byte-identical to the `kb-setup md-budget` CLI total.
Two routes, one answer.

| Surface | bytes | ~tokens |
|---|---|---|
| Repo eager (24 files) | 125,376 | 31,344 |
| `MEMORY.md` (auto-memory index; md-budget cannot see it) | 21,704 | 5,426 |
| **Total eager, every session** | **147,080** | **~36,770** |

Deferred, for contrast: 25 `SKILL.md` = 151,005 B · 242 memory files =
925,434 B · 2 `paths:`-scoped rules = 12,814 B.

`rule_unscoped` is **108,382 B = 86.4%** of repo-eager. The inherited
"~88% is unscoped rules" figure (dated 2026-07-28) was re-derived, not repeated,
and it holds.

### The defect in the current gate

**Every eager file is UNDER its own budget** — 40 to 196 lines against a 200-line
cap — so `md_size_budget` is green at 147 KB. The gate governs *files*; context is
spent by the *corpus*. A per-file budget is structurally incapable of seeing this,
and the corpus can grow indefinitely by adding individually-compliant files.

---

## 2. What the harness actually supports

Established by `claude-code-expert` at 2.1.224 with a **live `InstructionsLoaded`
probe**, not from docs alone. Full evidence and 13 ledger rows in the research
report; the load-bearing facts:

| Fact | Consequence for this design |
|---|---|
| ✅ `paths:` frontmatter on `.claude/rules/*.md` is **genuinely honoured** — 3-arm disjoint-glob probe, each arm loading one scoped rule and excluding the other | The `rule_scoped` class is real. File-shaped rules can move today. |
| ⚠️ **There is NO directory-entry trigger.** The complete load-reason set is `session_start`, `nested_traversal`, `path_glob_match`, `include`, `compact` | "Lazy-load when entering a directory" is **not available**. Nested `CLAUDE.md` loads on a *file read* anywhere in the subtree. |
| ⚠️ `CwdChanged` fires on every `cd` but has **no context lane** (stderr-to-user only) | Cannot be used for instruction delivery at all. |
| ⚠️ **Lazy instructions do NOT survive `/compact`** — root `CLAUDE.md` is re-injected; nested `CLAUDE.md` and `paths:`-scoped rules are not | Moving a rule lazy means it can silently vanish mid-session. This is a correctness cost, not a latency cost. |
| ⚠️ Hook `additionalContext` **warns against imperative phrasing** — it can trip prompt-injection defenses and be surfaced to the user instead of obeyed | Our entire corpus is written as imperatives. The hook lane needs a register change before it can carry rule prose. |
| Hook `additionalContext` caps at **10,000 chars** | The largest rule (12,925 B) cannot be delivered inline as one blob. |
| ⭐ `paths:` is a **`SKILL.md` field too**; `skillOverrides: "name-only"`; `skillListingBudgetFraction` | Three unused levers. |
| Skill listing shows name + `description` + `when_to_use`, capped 1,536 chars/skill | The judgment lane's budget: a few hundred bytes standing per rule instead of thousands. |

**No mechanism triggers on judgment.** Every lazy lane keys on an observable
event — a file read, a tool call, a prompt. The closest proxy is a **skill with a
sharp description**: the model reads every skill's name and description each turn
and decides relevance. That *is* judgment-triggered dispatch, but it is a model
decision, not a guarantee.

---

## 3. ⭐ The premise that changed: 86% unscoped ≠ 86% judgment-shaped

Classifying all 21 unscoped rules by **trigger shape** (§4) rather than by size
gives a materially different picture from the one this work started with:

| Class | rules | bytes | share of `rule_unscoped` | Addressable by |
|---|---|---|---|---|
| **File-shaped** | 4 | 12,444 | 11.5% | `paths:` — proven working |
| **Action-shaped** | 8 | 46,444 | 42.9% | hook lane (experiment) — most already gated |
| **Judgment-shaped** | 9 | 49,494 | 45.7% | directive eager + skill body |
| | **21** | **108,382** | 100% | (sums exactly to the measured total) |

The working assumption entering this exercise was that ~86% is judgment-shaped
and therefore unreachable. **It is 46%.** Over half the unscoped corpus has an
*observable* trigger, and 43% of it is already covered by a deterministic guard
whose prose merely duplicates the gate.

---

## 4. Per-rule classification — the reviewable artifact

Each row names the **concrete trigger** that justifies its class. A wrong row is
visible here, before any file moves. Bytes are the measured injected size.

### File-shaped → `paths:`-scoped rules

| Rule | bytes | Trigger | Proposed `paths:` |
|---|---|---|---|
| `local-devcontainer-first.md` | 4,209 | editing an image build input | `.devcontainer/**`, `docker-bake.hcl`, `mise.toml` |
| `persistence-gate-retry.md` | 3,234 | triaging a `persistence`/`verify-local` failure | `.devcontainer/**`, `mise.toml` |
| `research-repo-enumeration.md` | 2,601 | writing a research artifact | `docs/research/**/*.md` |
| `zero-bash-logic.md` | 2,400 | creating/editing a shell script | `scripts/*.sh`, `.devcontainer/scripts/*.sh`, `python/src/dotfiles_setup/bash_budget.py`, `hk.pkl` |

### Action-shaped → hook lane (deferred to experiment); most already gated

| Rule | bytes | Trigger | Existing gate |
|---|---|---|---|
| `secrets-out-of-the-shell-env.md` | 12,925 | printing/handling a credential in Bash | `secret_value_substitution`, `no_env_dump` |
| `mise-tasks-only.md` | 11,242 | a one-off command with a canonical task | `hook_guard` `_RULES` |
| `long-running-command-hangs.md` | 5,828 | launching a slow/unbounded command | `hook_guard` (backgrounded `mise run`, gate-piped-to-tail) |
| `do-not.md` | 5,613 | mixed; several items are tool calls | `branch_guard`, `hook_guard` |
| `agent-report-persistence.md` | 4,013 | an Agent-tool delegation returning | none (PostToolUse candidate) |
| `ai-cli-invocation.md` | 2,577 | invoking `codex`/`gemini`/`opencode` | none |
| `gh-cli-watch.md` | 2,499 | a `gh` wait | `no_grep_q_under_pipefail` (partial) |
| `clean-git-state.md` | 1,747 | about to run validation or commit | none |

### Judgment-shaped → directive eager (2–3 lines) + body in a skill

| Rule | bytes | Trigger (no glob predicts it) |
|---|---|---|
| `probes-need-a-control-arm.md` | 8,650 | about to believe or report a probe result |
| `research-doc-sources.md` | 8,257 | about to fetch documentation |
| `verify-before-advancing.md` | 7,307 | about to claim done / advance |
| `clarify-before-acting.md` | 5,960 | facing ambiguity (shape half already gated by `ask_quality`) |
| `tool-currency-and-native-first.md` | 5,727 | about to build or keep custom tooling |
| `use-tool-builtins.md` | 4,476 | about to hand-roll something a tool provides |
| `agent-artifact-conventions.md` | 4,298 | about to CREATE an artifact — the file does not exist yet |
| `zero-skip-policy.md` | 2,953 | a warning is about to be dismissed |
| `notepad-enforcement.md` | 1,866 | mid-research, a finding has just been made |

⚠️ Three of these declare in their own text that they cannot be scoped
(`agent-artifact-conventions`, `zero-skip-policy`, `clean-git-state`). Those
declarations are **honoured**: the directive stays eager in every case. Only the
body moves.

---

## 5. The design

### 5.1 Admission test (tiered)

A rule may leave the eager class **iff a named mechanism fires at its trigger
point** — a gate, a hook, a `paths:` glob, or a skill description. "Name the
mechanism, or stay eager." Grounding: only **5 of 21** eager rules currently
state why they must be eager; the other 16 are eager by default, not by argument.

### 5.2 The directive/body split for judgment rules

Each judgment-shaped rule becomes:

- **Eager:** 2–3 lines — the rule's name, the moment it binds, and a pointer.
  The *trigger* therefore never depends on a model decision.
- **Lazy:** the body, cases and archaeology, in a skill with a sharp description
  under the 1,536-char cap.

This extends the mechanism `docs/rules-evidence/` already established (17 files,
128 KB moved) with a lane whose content can be **pulled back in mid-session**,
which a `docs/` file cannot.

⚠️ Known cost, stated not smoothed: two homes per rule, and the directive can
drift from the body. That is the same multi-copy drift that motivated this work
(one #593 fact in five places). §5.4's gate is the mitigation.

### 5.3 The corpus ceiling — a ratchet

`kb_setup.md_budget` already computes `Report.eager_bytes`; **nothing fails on
it**. Wire it to a ceiling pinned at today's measured **125,376 B**, which can
only ever be lowered as migrations land. It is unarguable because the number is
measured rather than chosen, and it blocks the exact failure mode observed today:
growth by adding individually-compliant files.

⚠️ A ratchet makes the next genuinely-needed rule pay for the corpus's history.
The escape is a reviewed diff lowering or raising the pin with a stated reason —
never a suppression (`.claude/rules/zero-skip-policy.md`).

### 5.4 Instrumentation

A permanent `InstructionsLoaded` hook in the repo `.claude/settings.json`,
logging `load_reason | memory_type | file_path | trigger_file_path | globs` to a
gitignored path under `.agent/`. It joins the five hooks already wired there and
is covered by the same `hook_selfcheck` gate that `ship`/`land` run.

`/context` is the complementary read-out and needs no wiring.

---

## 6. The experiment

Two decisions are deliberately **not made** by this spec — the general unit of
disclosure, and what happens to `MEMORY.md`. Both wait on data.

### 6.1 What is measured

**Loaded** comes free from `InstructionsLoaded`. **Used** is scored by extending
`python/src/dotfiles_setup/command_audit.py`, which already mines this project's
transcript JSONL at `SessionEnd` and is contract-bound by
`workflow.command-audit-wiring`. This is an extra scorer, not new machinery.

⚠️ **Stated limitation, because it decides how the results may be read:** an
action-based scorer systematically **misses rules that worked by preventing
something** — and that is the class most of these rules belong to. A low "used"
score is therefore *not* evidence a rule is dead weight. It can support moving a
rule to a lazier lane; it must never, on its own, support deleting one.

### 6.2 The reject criterion (the failing arm)

**A lazy rule whose trigger condition occurred while the rule was NOT loaded**
rejects the lane for that rule. Post-compaction absence counts. This is directly
observable — the trace records both the load and the trigger — and needs no
judgement call.

⚠️ It can only adjudicate the file- and action-shaped classes, because the
judgment class has no observable trigger to compare against. That is a real
limit, and the judgment class is consequently the one whose directive stays
eager (§5.2) rather than being decided by this criterion.

### 6.3 Duration

**Per-class graduation, no global deadline.** A class moves when its own
criterion is met: file-shaped needs only a handful of matching reads (the 3-arm
probe effectively settled it once already); judgment-shaped waits much longer.

⚠️ Open-ended measurement is this repo's known failure mode — #476 has carried
measurements since filing without a design landing. Mitigation: §7's phase 1
ships a real reduction immediately, so no reduction is hostage to the slowest
question.

---

## 7. Phases

### Phase 1 — instrument + the file-shaped moves

1. Wire the `InstructionsLoaded` hook (§5.4).
2. Wire the corpus ratchet at 125,376 B (§5.3).
3. Add `paths:` frontmatter to the four file-shaped rules (§4). Expected
   reduction: **12,444 B** (~3,100 tokens), corpus to ~112,932 B.
4. Extend `command_audit` with the load-and-use scorer (§6.1).

⚠️ **Accepted risk, with rollback.** Step 3 moves rules exposed to the
compaction tax *before* that tax has been measured — the tension between
decision 7 (measure first) and decision 10 (ship phase 1 now), taken knowingly.
**Rollback is one-line per rule: delete the `paths:` frontmatter and the rule
returns to eager**, with no other change. Any reject-criterion hit in the trace
triggers it.

Every `paths:` value must respect the constraints the research surfaced: the
1,000-pattern / 4 MiB brace-expansion budget, and `[` as a bracket expression
(escape as `\[`).

### Phase 2 — judgment-rule directive/body split

Head-first by bytes. Each rule: extract the directive, move the body to a skill,
verify the skill's description is under 1,536 chars and actually triggers.
Expected reduction if all nine move: **~44,000 B** net of directives.

### Phase 3 — the action-shaped/hook question

Gated on the experiment. The hook lane must first answer, by prototype: does a
**declaratively rewritten** rule delivered via `additionalContext` get obeyed, or
surfaced to the user as suspicious text? Until that is measured, no action-shaped
rule moves.

### Phase 4 — `MEMORY.md`

Deferred entirely. The index is already a progressive-disclosure design (925 KB
behind 21.7 KB); the open question is why the *index* grows, and the trace is
what will answer it.

---

## 8. Non-goals

- **Byte reduction as the goal.** Ranked last. `docs/rules-evidence/` already
  moved 128 KB by that metric without changing how many rules load.
- **Deleting rules.** Nothing here is a deletion argument (§6.1).
- **Directory-entry loading.** Not available in the harness (§2).
- **Disabling auto-compact.** `.claude/CLAUDE.md` records `DISABLE_AUTO_COMPACT`
  as a deliberate NOT-set (it kills the PreCompact gate). Measure the tax; do not
  reverse that decision to avoid measuring it.

---

## 9. Open questions this spec does NOT answer

1. The general unit of disclosure beyond the judgment class — awaiting the trace.
2. `MEMORY.md`'s treatment — awaiting the trace.
3. Whether declaratively-rewritten rule prose survives the hook lane's
   prompt-injection defenses — awaiting a phase-3 prototype.
4. Whether the skill lane's model-decided triggering is reliable enough to carry
   more than a rule's body.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the corpus
  measured and classified; the gate, hooks and rules this spec changes
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) —
  `kb_setup.md_budget` (the shared budget engine) and the offline
  `agent-harness-docs` claude-code doc tree used as the semantics corpus
- [anthropics/claude-code](https://github.com/anthropics/claude-code) — the
  shipped CLI bundles byte-scanned for load-reason tokens, and the live
  `InstructionsLoaded` probe
