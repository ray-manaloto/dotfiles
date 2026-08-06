# Clarify Before Acting: Ask Until Sure on Ambiguous Work

When a task is ambiguous, admits multiple reasonable approaches, or is
hard to reverse, ask clarifying questions (via `AskUserQuestion`) and
keep asking across rounds until you are confident what to do. Do not
guess and proceed.

**Whenever you need input, use the `AskUserQuestion` TOOL — never options
in prose.** This is the *mechanism* rule and it is unconditional: it holds
even when nothing is ambiguous and the ask is just "which of these two"
or "please run X". Options in a message are not a question the harness
can answer; they cost the user a round-trip.

## Why this rule exists

Session 2026-06-29: the user asked for hk-hang prevention and explicitly
said *"keep asking questions until 100% sure on what to do"* and to
record the preference so it need not be repeated. In the same session the
user's chosen approach ("per-step hk timeouts") turned out to be
**impossible** — hk has no timeout support. Surfacing that and
re-confirming the pivot (an outer timeout wrapper) before building
avoided shipping the wrong thing.

## Rules

1. **Ask before acting on ambiguous / multi-path / irreversible work.**
   If there is genuine uncertainty about scope, approach, or intent, or
   the action is hard to undo (deletes, pushes, merges, external/
   outward-facing effects), resolve it with the user first.

2. **Recommend, don't just enumerate — with citations and both sides.**
   A question is a proposal to confirm, not a blank survey. Every ask
   carries all three (Ray, 2026-08-02), and **the first three are
   machine-enforced** by `dotfiles_setup.ask_quality` (below):

   - **A recommendation.** On a single-select question, the option you'd
     pick is **first** and its label ends `(Recommended)`; no other
     option claims it. (Multi-select is exempt — "recommended" is
     incoherent when the user picks several.)
   - **Pros and cons.** Every option's description carries `PRO:` and
     `CON:`. An option with no stated downside is a recommendation in
     disguise.
   - **A citation.** Ground the recommendation in something the user can
     open: a `backticked/path`, a `#NNN` issue/PR ref, or a URL. Cite
     what exists and **label it when thin** — if there is genuinely no
     prior evidence, say so with the literal `[no prior evidence]`, and
     treat needing that escape as a signal to go look first. Reaching
     for it routinely defeats the gate rather than satisfying it.
   - **Free-form is always available.** The harness adds "Other" to
     every question, so never apologise for imperfect options or pad the
     list to cover every case — offer the real choices and let the user
     write past them.

3. **Proceed directly on clear, low-risk, reversible tasks.** Do not
   manufacture questions for things with an obvious default or facts you
   can verify yourself — over-asking is its own failure mode. Pick the
   obvious option, state it, and move.

4. **Surface infeasibility immediately.** If a chosen approach turns out
   impossible or much worse than expected mid-flight, stop and
   re-confirm the pivot with evidence — never silently substitute a
   different solution for the one that was agreed.

5. **Keep asking until sure.** A second clarifying round is cheaper than
   rework. Don't stop at one question if the answer revealed new
   ambiguity.

## The gate (and the half of this rule no gate can carry)

`.claude/settings.json` wires `PreToolUse` matcher
**`Bash|AskUserQuestion|Edit|Write|NotebookEdit`** to
`scripts/pretooluse-guard.sh`; `hook_guard.decide_payload` dispatches on
`tool_name`, and `dotfiles_setup.ask_quality` **denies** an ask that is
missing the recommendation, the `PRO:`/`CON:` trade-offs, or the citation.
The deny is deterministic — it applies even in bypassPermissions mode — and
its reason names what to fix. `hook selfcheck` (run by `ship`/`land`) drives
both arms through the real wrapper, so the wiring cannot regress silently.

**Confirmed against the vendor docs and a live probe (2026-08-02)**, not
assumed: `AskUserQuestion` is a documented PreToolUse matcher value
(`$CC/hooks.md:1394`); hooks reload from `settings.json` **without a
restart** (`$CC/settings.md:177`); and a `deny` **prevents the call** while
its reason is **shown to Claude** (`$CC/hooks.md:1544`) — so a rejected ask costs the user
nothing and tells the agent exactly what to revise. The probe: an
otherwise-compliant ask minus its citation was denied through the wired path,
naming that one rule. `$CC` is the knowledge-base's offline claude-code doc
tree — see `research-doc-sources.md` step 00 for the path.

**What no hook can see is an ask that never happened.** A gate can only judge
the shape of a question you chose to ask; it is blind to the case this rule
exists for — quietly guessing instead. That half is carried by rule 1 and by
`feedback_clarify_before_acting`, and it is why this rule stays eager
(behaviour-triggered; see `md-size-budgets.md` § "the trigger test").

Why a gate at all for judgment-shaped guidance: the same standard has drifted
**three times** (2026-06-29 → 2026-07-30-e → 2026-08-02), and
`mise-tasks-only.md` records that markdown alone is "relying on the LLM, never
the only layer".

## Applies to

All non-trivial work: planning, multi-file changes, design choices,
destructive or outward-facing actions, and any task where the request
under-determines what to build.

## See also

- `do-not.md` — project invariants (some actions are never OK regardless
  of clarification).
- `mise-tasks-only.md` — the sibling PreToolUse guard, and the enforcement-layer
  doctrine this gate follows.
- `probes-need-a-control-arm.md` — why the gate ships with a passing arm as
  well as a failing one.
- `python/src/dotfiles_setup/ask_quality.py` — the enforcer.
- CLAUDE.md → `AGENTS.md` "Agent Instructions" — the policy index that
  references this rule.
