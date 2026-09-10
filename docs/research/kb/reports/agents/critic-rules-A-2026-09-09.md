# Adversarial critique — six rule refactors (A-2, 2026-09-09)

Record replayed against: commits 6126a4c, 62e53d1, 9e76e06, a293ae8 on feat/orchestration-modernization-audit; `.claude/rules/`, `.claude/settings.json`, `python/src/dotfiles_setup/hook_selfcheck.py`

Reasoning lane: adversarial critique, custom agent instructions, replay method on REAL historical defects

## Verdict Summary

| # | Rule | Verdict | Fires on motivating defect? | Critical Finding |
|---|---|---|---|---|
| 1 | agent-report-persistence.md | **FILE** | MIXED | SubagentStop removed in 62e53d1 but still described in "Native carriage" section |
| 2 | clarify-before-acting.md | **KEEP** | YES | Restructured; mechanism weaker but defect-catching intact |
| 3 | agent-artifact-conventions.md | **KEEP** | YES | Both ad-hoc-naming and dead-link defects caught |
| 4 | notepad-enforcement.md | **KEEP** | YES | Correctly reflects SubagentStop removal; replaced with PostToolUse |
| 5 | ai-cli-invocation.md | **KEEP** | YES | Explicit wrong forms; re-probe requirement catches defect |
| 6 | md-size-budgets.md | **KEEP** | YES | Teaches provenance discipline through worked example |

## Rule-by-rule analysis

### Rule 1: agent-report-persistence.md

**Defect (motivating cases)**: 
- 2026-07-05: 11-agent sweep produced 13 reports existing only in context window, one `/clear` from loss
- 2026-08-03: incremental persistence omitted from four briefs; two agents died leaving nothing

**Refactored version description**: 
The rule adds a "Native carriage" section describing SubagentStart and SubagentStop hooks that inject the incremental-persistence and file-role contract before every delegate's first prompt.

**CRITICAL ISSUE — SubagentStop no longer exists**:

The "Native carriage" section contains this text:

> The stop hook returns a deliver-before-idle reminder once; recursive stop events pass so the hook cannot loop forever.

But:
- Commit 6126a4c added SubagentStart + SubagentStop to settings.json
- Commit 62e53d1 removed SubagentStop after cold review (finding 1, HIGH) proved it caused forced continuations (measured: 4 distinct user records in one subagent transcript)
- Commit 9e76e06 added `check_unscoped_events` that FORBIDS re-adding SubagentStop
- Current HEAD shows only SubagentStart in settings.json

**Replay on the motivating defect**:

The rule's numbered guidance (rules 1-7) would catch the 2026-08-03 defect:
- Rule 2: "Persist incrementally. A research delegate writes each source as it is fetched and creates its report early, updating it as work proceeds."
- Rule 7: "Audit the native roster at handoff. Read the session's `subagents/` roster under the native project session directory. Map every findings-bearing launch to its brief and tracked report."

A PERSON following these rules would persist incrementally and audit the roster, catching the "omitted from briefs" defect.

**BUT the "Native carriage" section is STALE**, describing an implementation that was removed after being proven to fail. This is the opposite of what a rule should do — document what works, not what broke.

**Verdict**: **FILE — reasoning is sound, but building this proposal as-written would distribute documentation of a removed, failed mechanism.** The directive (rules 1-7) catches the defect. The "Native carriage" section should either be retracted or corrected to say "SubagentStart persists the contract. SubagentStop was removed in 62e53d1 after causing forced continuations on every delegation."

---

### Rule 2: clarify-before-acting.md

**Defect (motivating case)**: 
- 2026-06-29: User requested clarity before proceeding. User chose an approach (per-step hk timeouts) that proved impossible because hk has no timeout support. Surfacing that impossibility before implementation avoided shipping the wrong thing.

**Refactored version description**:
Completely restructured. Old version said "Whenever you need input, use the `AskUserQuestion` TOOL — never options in prose." New version acknowledges that subagents lose the tool and adds a prose fallback; adds explicit "Surface infeasibility immediately" rule.

**Replay on the motivating defect**:

Would the refactored rule catch the 2026-06-29 defect? 

Rule 5: "Surface infeasibility immediately. Stop and reconfirm a pivot with evidence rather than silently substituting a different solution."

Yes. A person following Rule 5 would surface the hk impossibility (no timeout support) before implementation, confirming the pivot to an outer-timeout wrapper with evidence. This directly prevents the defect.

**Mechanism change - weaker on tool availability**:

The new version adds: "Use `AskUserQuestion` when the tool is available. When it is absent or denied, present the same bounded options in prose and **STOP** for the answer."

This is more permissive than the old "never options in prose" directive. However, this is a correct adaptation to harness reality (subagents lose the tool), not a weakening of defect-catching. The explicit "STOP" preserves the decision boundary.

**Verdict**: **KEEP — fires on motivating defect.** The directive has been correctly adapted to reflect harness behavior while preserving the core defect-catching mechanism (surfacing infeasibility before implementation).

---

### Rule 3: agent-artifact-conventions.md

**Defect (motivating case)**:
- Ad-hoc agent working directories: tree was renamed from `.omc/` because it was named after a plugin (`oh-my-claudecode`) that was not enabled
- Five eager rules cited research that had never been tracked to disk, breaking readers off that machine (dead links)

**Refactored version description**:
Renames `.omc/` to `.agent/`. Adds explicit rejection: "Do **not** set project `plansDirectory` to `.agent/plans`." Adds guidance: "Promote anything a rule, eval, or later session will cite... A citation that only one machine can open is not durable evidence."

**Replay on the motivating defect**:

Would the refactored rule catch both prongs of the defect?

1. Ad-hoc naming: Rule 1 says "No ad-hoc directories. Map each artifact to the closest declared path." — catches this.
2. Dead links from untracked research: Section "Promote anything a rule, eval, or later session will cite" explicitly teaches not to cite machine-local research. — catches this.

Yes, both parts.

**Verdict**: **KEEP — fires on motivating defect.** The rule would prevent both the ad-hoc naming and the dead-link problem.

---

### Rule 4: notepad-enforcement.md

**Defect (motivating case)**:
- 2026-04-05: Extensive findings were not written down and all had to be re-derived after context loss
- Old rule then named MCP tools from a disabled plugin (`oh-my-claudecode`), recorded at zero invocations across 941 transcripts

**Refactored version description**:
Now references root `findings.md` from the enabled planning-with-files plugin. Explicitly removes references to the disabled MCP tools. Adds guidance about SubagentStart hook injecting the contract and PostToolUse hook on Agent tool reminding the coordinator.

**Crucial — correctly reflects SubagentStop removal**:

The rule explicitly states: "There is deliberately no `SubagentStop` hook — it would force a model turn on every delegation and could displace the report with the reply it forces. See `agent-report-persistence.md` § "Native carriage" for the measurement."

This is accurate (SubagentStop was removed in 62e53d1) and correctly attributes the reason (forced turns). It also correctly refers back to agent-report-persistence.md for the evidence.

**Replay on the motivating defect**:

Would the refactored rule catch the 2026-04-05 defect?

Rule 1: "Write as you go. After each root cause, decision, dead end, probe, or verification result, update `findings.md` before the next investigative step."

Yes. A person following this rule would write findings immediately, preventing the "didn't write anything" defect.

**Verdict**: **KEEP — fires on motivating defect.** The rule correctly reflects current reality (SubagentStop is gone, PostToolUse on Agent tool is the coordinator reminder). The directive catches the defect.

---

### Rule 5: ai-cli-invocation.md

**Defect (motivating case)**:
- Wrong CLI flags fail silently or hang: `codex -p` is `--profile` not prompt; `gemini "prompt"` hangs interactively

**Refactored version description**:
Explicitly lists wrong forms and correct forms. States the defect directly. Adds "Re-probe rule": "Before changing any invocation, run the pinned CLI's own help."

Also fixed: Removed three erroneous environment variables (`SLASH_COMMAND_TOOL_TOKEN_BUDGET` does not exist) with a control arm: "A plausible-looking variable name is the cheapest thing for a lane to invent; grep it before citing it."

**Replay on the motivating defect**:

Would the refactored rule catch the wrong-flag invocations?

The rule explicitly states: "- `-p` is `--profile`, not a prompt flag."

And: "Re-probe rule: Before changing any invocation, run the pinned CLI's own help: `mise exec -- codex exec --help`"

Yes, both through explicit naming AND through the re-probe requirement.

**Verdict**: **KEEP — fires on motivating defect.** The rule would prevent both wrong-flag invocations and silent hangs through explicit naming and the re-probe requirement.

---

### Rule 6: md-size-budgets.md

**Defect (motivating case)**:
- A 12,000-byte limit was **Windsurf's** rule, not Claude Code's
- It traveled without its provenance and was then machine-enforced against files Windsurf never governed
- Historical chain: 1f05365 created gate with correct source → 99a8506 described unenforced limit (copied from agnix without vendor bound) → 010009d changed code to match prose and credited Anthropic

**Refactored version description**:
Entire section: "Why this rule exists: a true number assigned to the wrong vendor."

Provides full Windsurf documentation quote:
```
> Workspace `.devin/rules/*.md` … **Limited to 12,000 characters per file.**
> `AGENTS.md` — Any directory in your workspace — **Processed by the same Rules
> engine**.
> — <https://docs.windsurf.com/windsurf/cascade/memories>
```

Traces the commit chain showing how misattribution happened. States: "A true fact must travel with its owner before it becomes an invariant."

Also notes the correcting probe overreached: "a zero-hit search in Anthropic's corpus became 'not documented anywhere,' although the probe never searched Windsurf."

**Replay on the motivating defect**:

Would the refactored rule catch the provenance-loss defect?

Yes. A person reading this rule learns explicitly:
1. 12,000 bytes is Windsurf's limit, not Claude Code's
2. Here is the evidence (quoted docs + URL)
3. Here is the historical chain showing how it got misattributed
4. Here is the corrective principle: "A true fact must travel with its owner"

The rule now **teaches provenance discipline through the defect as a worked example**. A person following this principle would not repeat the mistake.

**Verdict**: **KEEP — fires on motivating defect.** The refactored rule carries the defect as an exemplar of what NOT to do and teaches the corrective principle.

---

## Analysis of three specific implementation claims

### Claim 1: Append-only clause in SubagentStart payload (a293ae8)

**Statement**: The SubagentStart payload now explicitly requires append-only on findings.md and progress.md as a response to a lane truncating those files. This clause is a required token of `check_subagent_contract_endtoend`.

**Verification**:
- Commit a293ae8: The injected payload text includes: "APPEND to `findings.md` and `progress.md`. Never overwrite or truncate them. They are SHARED with the coordinator and with every other lane, they are gitignored, and there is no undo: a delegate that wrote its own heading as the whole file silently destroyed the coordinator's notes."
- Checked `python/src/dotfiles_setup/hook_selfcheck.py`: The `start_required` tuple includes the token `"APPEND to `findings.md` and `progress.md`"`
- Test case `check_subagent_contract_endtoend`: The `("start", {"hook_event_name": "SubagentStart"}, start_required, True)` case FAILS (returns non-empty failure list) if any token from `start_required` is missing from the command output.

**Robustness**: Deletion of this clause from the payload would cause the test to fail rc=1, and hook_selfcheck (run by every `ship`/`land`) would reject it. The gate is load-bearing.

**Verdict**: **SOUND.** The clause is present, tested, and load-bearing. Deletion would be caught immediately.

---

### Claim 2: `check_unscoped_events` in hook_selfcheck.py

**Statement**: `check_unscoped_events` verifies that SubagentStart carries no matcher (only "" or "*"), and a regression narrowing the matcher cannot evade this check.

**Verification**:
- Constant: `_UNSCOPED_EVENTS: tuple[tuple[str, str], ...] = (("SubagentStart", _SUBAGENT_CONTRACT_COMMAND),)`
- Logic: For each event in `_UNSCOPED_EVENTS`, the function retrieves all entries with `_event_entries(settings, event)`. For each (matcher, command) pair, if the command_token is present in the command, it checks that `matcher in ("", "*")`. If not, it appends a failure message naming the scope.
- Test integration: The case `("start", {"hook_event_name": "SubagentStart"}, start_required, True)` in `check_subagent_contract_endtoend` verifies that SubagentStart exists unscoped.

**Limitation**: The check only fires if SubagentStart is present in settings.json. A future regression that REMOVES SubagentStart entirely would pass this check. (That's a different concern, guarded by `check_subagent_contract_endtoend`'s presence test.)

**Verdict**: **SOUND.** The check correctly targets the narrowing regression and is load-bearing. A scoped matcher would be caught.

---

### Claim 3: `task_plan.md` = "coordinator ONLY by default" justification

**Statement**: The rule was changed from absolute "A delegate never writes `task_plan.md`" to permissive "**coordinator ONLY by default**; an agent whose definition explicitly emits a `DELTA` may propose one for the coordinator to apply." This is justified by pwf-scribe's definition explicitly authoring a delta.

**Verification**:
- Old rule (6126a4c~1): "A delegate never writes `task_plan.md` — the coordinator distills into it."
- New rule (HEAD): "**coordinator ONLY by default**; an agent whose definition explicitly emits a `DELTA` may propose one for the coordinator to apply"
- pwf-scribe.md: "Never edit it. When the requested work would change that plan, write only a delta to `.agent/plans/task_plan-delta-<stamp>.md`, naming the old anchor, proposed replacement, reason, and evidence for each change. The coordinator decides whether and how to apply the delta."
- Grep search: Only pwf-scribe carries this authorization among all `.claude/agents/*.md` files.
- Enforcement: No PreToolUse guard or permission deny rule blocks direct writes to task_plan.md. Enforcement is only through the injected SubagentStart contract (guidance, not mechanical).

**Trade-off analysis**: 

The old rule was **absolute**: "never writes". The new rule is **permissive**: "by default...unless". This is a real change in posture.

**Justification for the change**:
- pwf-scribe DOES exist and DOES emit deltas
- The old "never" rule was technically violated by pwf-scribe, even though the violation was intentional and structured (delta, not direct write)
- The new rule accurately describes the actual authorization

**Risk of the new wording**:
- "by default" invites the question: what are the non-default cases?
- The rule names one exception: pwf-scribe via delta
- But there is NO mechanical gate preventing a future agent definition from claiming write access to task_plan.md directly (without the delta structure)
- A malicious or mistaken agent definition that says "I write task_plan.md" would violate the rule but would not be caught by any gate
- The safeguard is ONLY the rule's own prose guidance and the injected contract

**Verdict**: **JUSTIFIED but WEAKENED.** The change accurately accommodates pwf-scribe's real authorization, which was implicit in the old "never" rule but now made explicit. However, it trades an absolute constraint for a permissive one, with no mechanical backstop. A future agent that claims direct write access to task_plan.md would violate the rule but would not be caught by any gate. The gate that would catch this is missing: either a PreToolUse guard denying Edit/Write to task_plan.md globally, or a hook that checks agent definitions for unauthorized task_plan.md claims.

---

## What survives, and what is not covered

**Surviving rules**: All six rules, in their refactored versions, would catch their own motivating defects when followed by a person. Five fully survive. One (agent-report-persistence.md) has a stale section describing a removed implementation.

**Not covered**:
- A future agent definition that claims direct write access to task_plan.md without the delta structure would violate the rule but would not be caught by any gate (Claim 3 residual).
- A removal of SubagentStart entirely would pass `check_unscoped_events` but would be caught by `check_subagent_contract_endtoend` (separate layer; not a residual defect).

---

## Re-verified before reporting

- Read `.claude/rules/{agent-report-persistence,clarify-before-acting,agent-artifact-conventions,notepad-enforcement,ai-cli-invocation,md-size-budgets}.md` at HEAD: content matches expectations from diffs
- Verified `.claude/settings.json` at HEAD: SubagentStart present, SubagentStop absent
- Verified `python/src/dotfiles_setup/hook_selfcheck.py` at HEAD: constants and test cases match description
- Verified pwf-scribe definition at HEAD: delta authorization present
- Cross-checked: no other agent definitions carry task_plan.md authorization

No artifacts moved during critique; all pathable statements verified against current tree.

---

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the target repository for this critique (all six rules, hook_selfcheck.py, pwf-scribe.md)

---

## Architect's refutation (2026-09-09, verified at HEAD `a293ae8`)

Two of the three "implementation claim" findings above are **REFUTED**: they
describe text that commit `62e53d1` removed, so they were computed against an
intermediate state of the branch rather than HEAD.

**Finding 1 (FILE — stale "Native carriage" section): REFUTED.** The quoted
sentence, "The stop hook returns a deliver-before-idle reminder once; recursive
stop events pass so the hook cannot loop forever", returns **0 hits** at HEAD.
Control arm: `grep -c "Native carriage"` on the same file returns **1**, so the
file and section are readable and the absence is real. The section as it stands
opens "There is deliberately NO `SubagentStop` hook. Adding one is a
regression." — i.e. it already says exactly what the finding asks for. No action.

**Finding 3 (task_plan.md "changed from absolute to permissive"): REFUTED.**
The token at `.claude/rules/agent-report-persistence.md:79` reads
`**coordinator ONLY**`; `grep -n "by default"` on the file returns nothing. The
permissive wording existed only in `6126a4c` and was reverted in `62e53d1`,
for the reason the finding itself would want: `pwf-scribe` writes a separate
delta file, so no exception was needed. The finding's own concern — "no
mechanical gate prevents a future agent from claiming direct write access" — is
what the revert removes, because there is no longer a claimable exception.

**Finding 2 (`check_unscoped_events`): CONFIRMED**, including its parenthetical.
Deleting the `SubagentStart` registration outright passes `check_unscoped_events`
(it iterates entries that exist) and is caught by the separate `_SETTINGS_WIRING`
presence row plus `test_missing_subagent_start_registration_fails`.

**Append-only clause: CONFIRMED**, independently armed by the architect before
this review — deleting the clause from the payload alone (leaving the required
token list untouched) turns `check_subagent_contract_endtoend` red.

**Net verdict: all six rules KEEP.** The one FILE verdict rests on a stale read.

### The process lesson, which is the durable part

The brief named four commits AND gave a combined `git diff e2659ab..a293ae8`;
the critic replayed individual commits and reported `6126a4c`'s content as
current. A finding is only valid against the ref it was computed on. **Pin ONE
ref in a review brief** — a resolved SHA or an explicit two-dot range — and say
plainly that per-commit reads will show superseded intermediate states on a
branch that corrects itself. `.claude/skills/adversarial-review/SKILL.md` should
carry this; filed as a follow-up rather than fixed here.
