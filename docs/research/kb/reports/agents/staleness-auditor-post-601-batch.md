# Staleness audit — prose vs `bd4857c..b6fd9a0` (2026-08-06)

Scope: this repo's instruction and reference prose, audited against the five
commits on `fix/601-reflection-fixes` (`0782b9b` command-audit recursion,
`8530273` PreToolUse matcher, `f775f93` brief-persistence, `47eb739`
adversarial-review skill + critic, `b6fd9a0` classifier-axes gate).

Ground truth used, all measured at write-up time, not inherited:

- `.claude/settings.json:37` → `"matcher": "Bash|AskUserQuestion|Edit|Write|NotebookEdit"`
- `hook_selfcheck.py:88` → `("Bash", "AskUserQuestion", "Edit", "Write", "NotebookEdit")`
- `command_audit.project_transcripts` → roots + `rglob` (was `glob("*.jsonl")`)
- `dotfiles-setup verify run` → **116 passed, 0 failed, 4 skipped**, `rc=0`
- `dotfiles-setup check-doc-refs` → `OK: all doc path, task, and skill references resolve`, `rc=0`
- `kb-setup md-budget` → 52 instruction files, ~125,369 B eager, `rc=0`
- `wc -c tests/AGENTS.md` → **6,084** (was **4,888** at `bd4857c`)
- `docs/research/kb/reports/agents/601-codex-review-rounds.md:13-19` → the v1-v7 verdict table

**8 live defects. Never edited anything audited.**

| # | Verdict | Anchor | Claim | Probe + control arm |
|---|---|---|---|---|
| 1 | CONFIRMED-STALE | `python/src/dotfiles_setup/hook_selfcheck.py:58-59` | "PreToolUse must stay scoped, and to BOTH tools it guards" | same file `:79-88` says five; `.claude/settings.json:37` has five |
| 2 | CONFIRMED-STALE | `.claude/rules/mise-tasks-only.md:64`, `tests/TEST-INDEX.md:39`, `python/verification/suites.toml:1141` | the selfcheck drives "settings.json wiring + `Bash` matcher" | `_SETTINGS_WIRING` asserts five tools |
| 3 | CONFIRMED-STALE | `CONTEXT.md:59` | "Measured: **0 bypasses, ever.**" | `git log -S` → `d548d71`, pre-#343; refuted by `TEST-INDEX.md:40` and `mise-tasks-only.md:112` |
| 4 | CONFIRMED-STALE | GitHub issue **#606** body, "What it should emit" | the unqualified A3 stop condition "leaves rounds 4-7 untouched" | verdict table `601-codex-review-rounds.md:14-19`: v2 = SHIP/2 LOW ⇒ loop ends at v2 ⇒ 5 HIGH + 2 MEDIUM ship |
| 5 | CONFIRMED-STALE | GitHub issue **#606** body | "**the two questions** an enumeration CANNOT replace" | the shipped skill states **three** (Q-FRESH, Q-SCOPE, Q-CLAIM) |
| 6 | CONFIRMED-STALE | GitHub issue **#608** §N2 | "do not duplicate it here without deciding which home wins" | the decision landed in `47eb739` → `tests/AGENTS.md:71-83` |
| 7 | CONFIRMED-STALE | `.claude/skills/clear-prep/SKILL.md:173` | persist "under `docs/research/runs/<topic>/agents/`" | same file `:246` says `docs/research/kb/reports/agents/`; `agent-report-persistence.md:37-40` says "ONE path" |
| 8 | CONFIRMED-STALE | `docs/specs/eval-harness-design.md:136` | "(98 contracts)" | `verify run` → 116 |
| — | REFUTED (cleared) | `tests/AGENTS.md:71-83` vs `.claude/rules/probes-need-a-control-arm.md:54-66` | the caller's headline worry | compatible; see §Cleared |
| — | REFUTED (cleared) | `session-…-reflection.md:99` "4,888 B headroom" | did it propagate? | it did not — `4,888` appears in 2 files, both persisted; `601-reflect-process-design.md:549` has it RIGHT |
| — | INFORMATIONAL | 5 hits under `docs/research/kb/reports/**` | verbatim agent output | not normalised, per `agent-artifact-conventions.md` |

---

## 1 — LIVE. `hook_selfcheck.py` contradicts itself about the matcher, 20 lines apart

`python/src/dotfiles_setup/hook_selfcheck.py:58-64`, verbatim:

```
# PreToolUse must stay scoped, and to BOTH tools it guards: `Bash` (the
# mise-tasks-only redirects) and `AskUserQuestion` (the ask-quality standard,
# Ray 2026-08-02 — see dotfiles_setup.ask_quality). Each is asserted
# separately, because the matcher is one alternation string: a check that only
# looked for "Bash" would keep passing if AskUserQuestion were dropped from it,
# and the guard would go silently absent for that tool exactly as #343 did for
# off-root Bash.
```

Twenty lines below, in the same file, `:79-84`:

```
    # All five matcher tools are required, not just the two the guard started
    # with. The three file-modifying ones route to `branch_guard` (#400); with
    # only ("Bash", "AskUserQuestion") required, narrowing the live matcher
    # back would silently kill the write-time default-branch gate while ship
    # and land both stayed green — a check that can only pass
```

**Falsifier:** if the guard really guarded two tools, `_SETTINGS_WIRING[0][2]`
would hold two names.

**Probe:** `:88` → `("Bash", "AskUserQuestion", "Edit", "Write", "NotebookEdit")`.
**Second route:** `.claude/settings.json:37` →
`"matcher": "Bash|AskUserQuestion|Edit|Write|NotebookEdit"`.
`8530273` added the second comment and corrected the tuple, but left the first
comment — so the file now states both.

**Proposed replacement for `:58-59`:** *"PreToolUse must stay scoped, and to ALL
FIVE tools it guards: `Bash` (the mise-tasks-only redirects), `AskUserQuestion`
(the ask-quality standard, Ray 2026-08-02) and `Edit`/`Write`/`NotebookEdit`
(the #400 write-time branch guard)."*

## 2 — LIVE (minor, pre-existing). Three places call the selfcheck's scope the "`Bash` matcher"

- `.claude/rules/mise-tasks-only.md:64` — *"driving the WIRED guard end-to-end: settings.json wiring + `Bash` matcher,"*
- `tests/TEST-INDEX.md:39` — *"settings.json wiring + Bash-matcher assertions"*
- `python/verification/suites.toml:1141` — *"settings.json wiring + Bash matcher"*

These predate the batch (the matcher already carried `AskUserQuestion` from
2026-08-02), so `8530273` did not create them — but it *did* correct the
identical claim in `.claude/rules/clarify-before-acting.md:70-71`, which is what
makes leaving these three a live inconsistency rather than uniform staleness.

Suggested wording for all three: *"settings.json wiring + the five-tool
matcher"*.

## 3 — LIVE, highest-value. `CONTEXT.md:59` "0 bypasses, ever" is already refuted twice, and this batch widens the corpus 10×

`CONTEXT.md:59`, verbatim:

> `| **bypass / blocked / pre_rule** | `mise run command-audit` classes. Only **bypass** (matched a live rule AND ran) is an alarm. Measured: **0 bypasses, ever.** |`

**Falsifier:** a single command that matched a live rule and executed.

**Provenance probe:**

```
$ git log --oneline -1 -S'0 bypasses, ever' -- CONTEXT.md
d548d71 feat(docs): adopt the mattpocock tracker config + label vocabulary, hand-placed (#277)
```

— i.e. written before #343.

**Route 1 — this repo's own prose says the opposite, in two places.**
`tests/TEST-INDEX.md:40`: *"**that 0 was later falsified — #343 re-judged
against the guard live at each timestamp and found 125 genuine, because `since`
is only a proxy and the guard was not running at all off-root**"*.
`.claude/rules/mise-tasks-only.md:112-114`: *"#343 found **125** commands that
bypassed it entirely by never reaching it"*.

**Route 2 — `0782b9b` changes the corpus the number would be measured over.**
`project_transcripts` was `glob("*.jsonl")`; it is now roots + `rglob`. Per the
new docstring's measured histogram, 214 → 2,176 files, and the 1,962 it could
not see were *entirely subagent activity* — "the bulk of what a guard-coverage
audit exists to police".

So the figure is inherited, refuted, and now also measured over 9.8% of the
corpus. `probes-need-a-control-arm.md` rule 6 applies directly.

**Proposed replacement:** *"Only **bypass** (matched a live rule AND ran) is an
alarm. ⚠️ The audit's own class is not the last word: #343 re-judged against the
guard live at each timestamp and found **125** genuine bypasses that the
`since` proxy had scored 0. Re-derive before citing a count."*

## 4 — LIVE, P0. Issue #606 carries the stop condition the shipped skill says inverts the outcome

The lead asked specifically whether anything repeats the unqualified A3 form as
if it were the shipped rule. **It does: issue #606, in its "What it should
emit" section — the build spec for `mise run review-brief`.** Verbatim from
`gh issue view 606`:

> - **The stop condition** — *a review round returning SHIP with 0 HIGH and 0
>   MEDIUM ends the loop; LOWs become tickets.* Replayed against #601 this ends
>   the loop after v2, killing exactly rounds 1-3 (the wasted ones) and leaving
>   rounds 4-7 (the proportionate ones) untouched.

The shipped skill, `.claude/skills/adversarial-review/SKILL.md:81-89`, says the
opposite about the same replay:

> ⚠️ **The "bounded" qualifier is load-bearing, and dropping it inverts the
> rule.** Replayed against the #601 verdict table
> (`601-codex-review-rounds.md:13-19`), the unqualified form ends the loop at
> v2 — which was an *open-hunting* SHIP with 2 LOW. Rounds v4-v7 then never run,
> and **five HIGHs and two MEDIUMs ship** […]

**Second route — I settled it from the table itself rather than from either
prose.** `docs/research/kb/reports/agents/601-codex-review-rounds.md:13-19`:

```
| v2 | SHIP | 2 LOW | test control arm; doc accuracy |
| v4 | DO NOT SHIP | 1 HIGH | **real bug** — classify→execute race |
| v5 | DO NOT SHIP | 3 HIGH | **real bug** — queued-reply deadlock; residual race; execute_stop (→ #604) |
| v6 | DO NOT SHIP | 1 HIGH · 1 LOW | **real bug** — live-pid queued reply silent; TOCTOU traded |
| v7 | DO NOT SHIP | 2 MEDIUM | **bounded brief** — missing 5th axis (`tempo`); weak meta-tests |
```

v2 has 0 HIGH and 0 MEDIUM, so the unqualified predicate fires at v2 and v4-v7
never run: 1+3+1 = **5 HIGH** and **2 MEDIUM** ship. The skill is right; #606
and the reflection doc's A3 are wrong, and the arithmetic is in this repo.

**Live vs informational:** the reflection doc
(`session-20260806-review-loop-reflection.md:140-143`) is persisted agent output
— **informational, do not edit**. Issue #606 is **not** persisted material; it
is an open build spec that would ship the inverting rule into a renderer.

**Proposed replacement for #606's bullet:** *"The stop condition — a **BOUNDED**
round returning SHIP with 0 HIGH and 0 MEDIUM ends the loop; a SHIP from an
open-hunting round promotes to one bounded round instead. LOWs become tickets.
The 'bounded' qualifier is load-bearing: the unqualified form ends #601's loop
at v2 (an open-hunting SHIP with 2 LOW) and ships 5 HIGHs and 2 MEDIUMs. See
`.claude/skills/adversarial-review/SKILL.md` § 'The stop condition'."*

## 5 — LIVE (minor). Issue #606 says "two questions"; the shipped skill says three

#606: *"**The two questions an enumeration CANNOT replace.**"* — listing
Q-FRESH and Q-SCOPE. `.claude/skills/adversarial-review/SKILL.md:104` ships
**"Three questions an enumeration CANNOT replace"**, adding **Q-CLAIM** (the
operator-string clause audit), which the skill credits with three findings
across two rounds — the largest single yield in the table. Same drift class as
#4, same fix: sync #606 to the skill.

## 6 — LIVE (minor). Issue #608 §N2 states an open question that has been decided

#608 §N2, verbatim:

> **It has a sibling insight that belongs with it** (the post-mortem routes this
> one to `tests/AGENTS.md` rather than to the eager rule — do not duplicate it
> here without deciding which home wins)

`47eb739` decided it: the insight landed in `tests/AGENTS.md:71-83`. #608 should
record that its §N2 sibling is **shipped**, so a future implementer does not
re-open a settled routing question.

## 7 — LIVE. `clear-prep/SKILL.md:173` still names the retired persistence path

`.claude/skills/clear-prep/SKILL.md:170-173`, verbatim:

> Full subagent reports must already be on disk per
> `.claude/rules/agent-report-persistence.md`: every findings-bearing agent's
> final report persisted VERBATIM under `docs/research/runs/<topic>/agents/` at the
> moment it was received

The same file's checklist, `:246` — edited by `f775f93`, three lines of context
away — says:

> - [ ] Every findings-bearing agent's brief AND report persisted verbatim under `docs/research/kb/reports/agents/`; coverage audited.

And `.claude/rules/agent-report-persistence.md:37-40`:

> **ONE path.** `docs/research/kb/` is tracked and survives a fresh clone;
> the old `docs/research/runs/<topic>/agents/` does not.

**This one has a recorded cost.** `docs/rules-evidence/agent-report-persistence.md:38-41`:

> **an agent correctly followed the *old* rule, the caller looked in the *new*
> path, and wrongly reported the agent as non-compliant. One path.**

`f775f93` rewrote the sentence immediately following `:173` and left the stale
path in place. **Proposed replacement:** `docs/research/kb/reports/agents/`.

## 8 — LIVE (minor, pre-existing). A stale contract count in a tracked spec

`docs/specs/eval-harness-design.md:136` — *"(98 contracts)"*. Measured now:

```
$ uv run --project python dotfiles-setup verify run
116 passed, 0 failed, 4 skipped
rc=0
```

`b6fd9a0` added `workflow.classifier-axis-enforcement` (it PASSES — I read the
line). Pre-existing drift; every other count I found (115, 113) sits in a
receipt or a persisted report, where a point-in-time figure is correct by
construction.

---

## Cleared — checks I ran that found nothing (coverage, not luck)

**C1. `tests/AGENTS.md`'s third anti-pattern vs `probes-need-a-control-arm.md`.
COMPATIBLE — but not for the reason the brief proposed, and the difference
matters.**

`.claude/rules/probes-need-a-control-arm.md:54-66` governs mutation **validity**
on two counts: a mutation must *destroy* what the check looks for, and must be a
break that *could really happen* ("usually deleting the wiring line that calls a
function, not renaming the function").

`tests/AGENTS.md:71-83` concerns a mutation that is valid on **both** counts —
deleting the fix is exactly the realistic regression — and says its narrow blast
radius diagnoses the **test suite's axis enumeration**, not the mutation.

So the brief's framing ("mutations complete but IRRELEVANT") is off in a way
worth correcting: the new bullet's entire force is that it applies to a *good*
mutation. A reader who takes it as "only bad mutations" has inverted it. Nothing
in the rule claims a passing mutation test is evidence of quality, so there is
no textual contradiction — the two files are orthogonal, one about the probe and
one about the space the probe is run over.

Residual risk, and my one recommendation here: the compatibility is *inferable
but unstated*. `probes-need-a-control-arm.md` cross-references `tests/AGENTS.md`
only generically. A half-sentence in the new bullet — *"this does not weaken
`probes-need-a-control-arm.md` rule 2: run the mutation, then read its blast
radius as a statement about your axes"* — removes the discard risk the caller
was worried about.

**C2. The `4,888 B headroom` error did NOT propagate.** Control-armed:

```
$ grep -rn '4,888\|4888' --include='*.md' --include='*.toml' --include='*.pkl' .
docs/research/kb/reports/session-20260806-review-loop-reflection.md:99   (the error)
docs/research/kb/reports/agents/deep-research-takeover-20260730.md:104   (an x.com URL substring)
docs/research/kb/reports/agents/601-reflect-process-design.md:549        (CORRECT)
```

Control arm: `12,000` → 10+ files, so the probe reads this corpus.
Known-absent control, freshly invented for this run: `zorkflump` → 0.

`601-reflect-process-design.md:549` is the **source** the synthesis
mis-transcribed, and it has it right:
`| `tests/AGENTS.md` | **4,888 B** | AGM-003 **12,000** | **7,112 B** | ~800 B |`
— size 4,888, cap 12,000, headroom **7,112**. Both carriers are persisted
reports; **informational only, nothing to edit, nothing inherited it.**

For the record, the live number: `wc -c tests/AGENTS.md` → **6,084** (was 4,888
at `bd4857c`; `47eb739` added ~1,196 B). Real headroom **5,916 B**.
`kb-setup md-budget` → `rc=0`.

**C3. Cross-references in the two new files all resolve.** Every backticked path
in `.claude/skills/adversarial-review/SKILL.md` and
`.claude/agents/adversarial-critic.md` exists on disk; the one apparent miss
(`dag_tick.py`) is a bare basename inside a parenthetical, not a path reference.
`tests/AGENTS.md § "What a good test is here"` — heading present at
`tests/AGENTS.md:49`. `601-codex-review-rounds.md` — present.
`dotfiles-setup check-doc-refs` → `rc=0`, *"all doc path, task, and skill
references resolve"*.

**C4. `docs/skills-inventory.md` does NOT need a row for `adversarial-review`.**
Its stated scope (`:6-10`) is *"one row per skill in every **marketplace** we
have adopted"* — third-party skills. It names this repo's own skills only as
comparison notes (`:137`). False alarm, cleared.

**C5. `docs/hk-builtins-audit.md:64`** carries `| `classifier_axes` | hk.pkl |`
— regenerated, correct. Control arm: `bash-budget` (a sibling CLI subcommand)
→ 2 markdown files, so the probe finds CLI subcommands in prose;
`quibblewrangle-audit` (freshly invented, known-absent) → 0.

**C6. No hand-written enumeration of hk steps is broken by `classifier_axes`.**
`AGENTS.md`'s hk.pkl row lists five steps *illustratively* ("enforces
`no_lint_skip`, `require_pipefail`, …") and already omits ~10 others, so it is
not an enumeration. `CONTEXT.md`'s enforcement-vocabulary table defines terms,
not steps.

**C7. `.claude/rules/mise-tasks-only.md:70-79`** (the command-audit description)
is *more* accurate after `0782b9b`, not less — it says the loop "scans this
project's recent Claude Code transcript JSONL", which is now true of subagent
transcripts as well. Cleared.

**C8. `parity.toml` / `doctor.toml`** enumerate no agent or skill set — grep for
`agents/` / `skills/` in both → 0 hits. The new agent and skill need no
registration there. Cleared.

---

## NEEDS-VERIFICATION (one, for the caller to rule on)

**The new `classifier_axes` gate has no rule doc.** Every comparable gate in
this repo pairs an hk step with a `.claude/rules/*.md` ADR carrying its "Why
this rule exists" — `bash_logic_budget` ↔ `zero-bash-logic.md` is the closest
structural twin, and `classifier_tables.py` explicitly models itself on
`bash_budget`'s allowlist. `workflow.classifier-axis-enforcement` asserts the
hk-step ↔ CLI ↔ module ↔ tests chain but cannot assert a rule that does not
exist.

This is a **gap, not a stale claim** — I am not asserting it should be written,
because #607 and #608 both record the post-mortem's own position that *"prose
was not the lever"*. Flagging it so the omission is a decision rather than an
oversight. The probe that settles it: does any *other* hk step with a CLI
subcommand lack a rule file? (`lock-check`, `token-audit`, `hk-builtins-audit`
do — so the convention may be narrower than it looks.)

---

## Re-verified immediately before reporting

Re-read at write-up time, after all analysis: `.claude/settings.json:37`,
`python/src/dotfiles_setup/hook_selfcheck.py:50-96`,
`.claude/skills/clear-prep/SKILL.md:168-182` and `:246`, `CONTEXT.md:50-60`,
`tests/AGENTS.md` (full, plus `wc -c`),
`docs/research/kb/reports/agents/601-codex-review-rounds.md:1-30`, and issues
**#605-#608** fetched live via `gh issue view -R ray-manaloto/dotfiles` under a
45 s `subprocess` bound (there is no `timeout` binary on this host).
`git status --short` was clean at session start and I made no edits to any
audited file. **Nothing had moved under me.** The gates
(`verify run`, `check-doc-refs`, `md-budget`) were all run fresh in this session
with `rc` captured to a file, never through a pipe.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the audited prose, and issues #605-#608 read via `gh`.
