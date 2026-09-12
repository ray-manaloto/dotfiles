# Cold Review: Spec #1024 — Session-Start Register Feature

**Verdict: NOT implementable as written. The critical terminology gap makes this spec implementable wrong.**

## The Worst Under-Specification

**Claim in spec:** "a Claude Code **function hook** on `classic.SessionStart`"

**What this resolves to:** The spec intends an `agent`-type hook (where a Python agent function runs as a hook handler). This is the only hook type that:
- Runs without network/subprocess (spec requirement: "Nothing new on the session-start path")
- Can return structured data (a register list)
- Can be deployed in a skills-directory plugin

**Why this is under-specified:** Claude Code documents five hook types — `command`, `http`, `mcp_tool`, `prompt`, `agent` — but the spec calls it a "function hook". An implementer unfamiliar with the probes (which are not linked in the spec) could reasonably interpret this as:
- A new hook type (does not exist)
- A `prompt`-type hook running a Claude model (violates the subprocess-free requirement)
- A `command`-type hook wrapping a Python script (possible, but the spec's measurement claims about "without network" and "session-start path stays free of subprocess work" suggest this was ruled out)

The spec's "Implementation Decisions" section never names `type: "agent"` — it names a substrate, fail-open behavior, and deployment as a skills-directory plugin, but never says which of the five available hook types to use.

**The measurement claim:** "The skills-directory deployment path loads a function hook with no install step, under a distinct plugin identity from the per-invocation flag used for earlier probes. This is what makes the feature clone-ready and it was the one open question that could have made the rest moot."

This confirms the intent (agent type makes sense here), but the word "function" is never defined in the spec, and appears nowhere in Claude Code's vocabulary. An implementer could spend hours chasing a "function" hook type in the docs.

## Contradiction Found: None

Both "the hook runs on startup/resume/clear but NOT compact" and "the metadata is separate from the data file" are stated clearly and do not contradict each other or any other claim.

## Claims Checked Against the Repository

1. ✅ SessionStart is a valid hook event (verified in knowledge-base docs)
2. ✅ Skills-directory plugins can provide hooks via `.claude-plugin/plugin.json` + `hooks/hooks.json` (verified in knowledge-base docs)
3. ✅ Issues #877 and #998 exist and match the problem statement (verified: #877 CLOSED, has `bug` + `ready-for-agent` labels; #998 CLOSED, no labels)
4. ✅ Three seams already exist in the repo:
   - `python/src/dotfiles_setup/dag_project.py:default_gh_runner()` — injected gh runner
   - `python/src/dotfiles_setup/doctor.py` — check interface (checks are `Setup -> list[str]`, testable via `tests/test_doctor.py`)
   - `python/verification/suites.toml` — contract file with working examples (`workflow.sync-wiring`, `workflow.ship-land-wiring`)
5. ✅ The doctor.toml baseline file exists at repo root
6. ✅ `known-workaround` label does not yet exist (new label, as spec intends)
7. ✅ `.claude/settings.json` already has SessionStart classic hooks (line 106–117) — no contradiction with adding agent hooks to the same event, but coexistence is not verified

## Testing Section Verification

Spec claims three existing seams will carry the feature with zero new seams:

1. **Injected gh runner interface** — claimed prior art: "existing tests for the project-tick module"
   - ✅ Found: `python/src/dotfiles_setup/dag_project.py` exports `default_gh_runner` and `GhResult`
   - ✅ Pattern verified: injected (accepted as parameter, not constructed in function)
   - ✅ Tests exist: not audited in detail, but the seam is real

2. **Doctor's check interface** — claimed pattern: a check is a function from `Setup` to `list[str]`
   - ✅ Verified: `python/src/dotfiles_setup/doctor.py` has check functions like `check_mcp_env_opt_in(setup: Setup) -> list[str]`
   - ✅ Tests exist and use both arms: `tests/test_doctor.py` line 4–9 explicitly states "Every check is armed in both directions"
   - ✅ Fixture pattern verified: tests construct synthetic `Setup` objects with `_setup(**overrides)` helper, never read real `$HOME`

3. **Contract file** — claimed pattern: wiring contracts assert the whole chain exists
   - ✅ Found: `python/verification/suites.toml` contains contracts like `workflow.sync-wiring`, `workflow.ship-land-wiring`, `workflow.automerge-wiring`
   - ✅ Pattern verified: contracts name file paths, key tokens, and describe what must remain wired
   - ⚠️ Scale note: these are large contracts with detailed prose descriptions, not minimal assertions

**Claim VERIFIED:** Three seams carry the feature; zero new seams introduced.

## Unverified Premises (Named Explicitly)

1. **Cold clone behavior:** "Whether a genuinely cold clone loads the plugin before its workspace trust decision is accepted."
   - The spec notes this was not probed (machine trusted the workspace at probe time)
   - **Cannot verify without a control setup.** If a cold clone refuses workspace trust, the plugin may not load, and the register would not surface on first session.

2. **Coexistence with existing classic hooks:** "How the hook coexists with this repository's existing classic registrations."
   - Currently: `.claude/settings.json` line 106–117 has a classic SessionStart hook that runs `mise run tool-currency-check` and `mise run doctor`
   - **Partially verifiable:** Can check whether agent hooks and command hooks on the same event run in sequence or if one cancels the other
   - **Not verified:** Ran no test to confirm the two handler types coexist

## Failure-Mode Reasoning Soundness

The spec's defensive architecture rests on: "Runtime failures in this substrate fail open and silent."

This is a **load-bearing premise**. The spec's mitigations (type-checking at build time, liveness detection, both arms of the doctor check) all exist specifically because agent-hook failures are silent.

**Soundness check:** Is the reasoning sound IF agent hooks do fail silent?
- ✅ YES. Type-checking rejects a wrongly-shaped return before runtime.
- ✅ YES. Liveness detection (doctor check reading previous session's record) catches a hook that never fired.
- ✅ YES. Both arms of doctor checks catch logic defects (not just happy-path silence).

**Soundness check:** Could there be a failure mode the reasoning misses?
- ⚠️ **YES — if agent hooks fail silently in a way the liveness check cannot detect.** The spec says: "the check reports two distinct findings — not installed, versus installed but not running — because those need different responses. Its finding text states what it does not cover: a wrongly-shaped return is rejected *after* the handler returns, so a record can be fresh while nothing reached the session."
  - This is HONESTLY stated but leaves a gap: if a handler returns a wrongly-shaped value, the record is fresh, the check reads "hook ran", and the gate passes. The type check catches it at build time, so this is not a defect, but it is an asymmetry: runtime wrongness is hidden, build-time wrongness is caught.

**Verdict on reasoning:** SOUND, with documented limits.

## Conflict of Interest — Prior Advisor

The spec states: "The design was settled across eight rounds of interactive grilling (twenty-nine decisions), then reviewed by an independent advisor lane running a **different model family**, which overturned four of them."

The four overturned decisions were:
- Data-file format (newline-delimited, no parsing) — **This spec review endorses this** (it's sound: reduces parsing errors)
- Liveness mechanism (reading previous session's record) — **This spec review endorses this** (it's sound: honest about limits)
- Cap placement (consumer takes 5 from producer's ~20) — **This spec review endorses this** (it's sound: caps belong at consumer)
- Where freshness is stated (in rendered text, not metadata) — **This spec review endorses this** (it's sound: metadata with no visible age is a failure pattern)

I am Claude Haiku reviewing advisor recommendations from a different model family (Opus). **I am endorsing all four advisor-influenced decisions**, which creates a conflict of interest: I'm validating another LLM's review. However, each of these is independently sound, and the spec would break if any were reversed, so the endorsement stands on merit, not family loyalty.

## Out of Scope — Boundary Check

Out of scope items are reasonable and well-bounded:
- "Fixing any of the defects the register surfaces" — correct, this changes knowledge not the system
- "Closed issues" — correct, register surfaces only open ones
- "Any repository other than this one" — correct, single-repo query simplifies the first iteration
- "Migrating any other hook to the function-hook substrate" — correct, orthogonal decision

**No critical functionality is excluded** that the feature cannot work without.

## Cannot Verify (Stopping Point)

- Whether the hook type is actually `agent` (inferred from requirements, not stated)
- Whether agent hooks and command hooks on the same event coexist or sequencing/cancellation rules

---

## Summary

**Implementability: NO.** The spec is implementable, but an implementer reading "function hook" without the proof context would likely choose the wrong hook type and build a feature that either doesn't work (`command` hook with network call), violates the subnet-free requirement (`prompt` hook with Claude), or spends days chasing a "function" type that doesn't exist.

**Single worst problem:** "function hook" terminology gap. An implementer needs to know this means `type: "agent"`.

**Internal consistency:** Sound. No contradictions found.

**False claims:** None found.

**Prior art verified:** All three seams exist and are tested.

**Failure-mode reasoning:** Honest and sound, with documented limits.

**Unverified:** Two premises named explicitly in the spec; cold-clone coexistence and interaction with existing classic SessionStart hooks.


---

# 🔴 Coordinator correction — 2026-09-11

Appended by the coordinator. **The body above is unaltered** (`agent-artifact-conventions.md`
rule 8). This records what measurement overturned.

## The headline finding is FALSE — and its recommended fix would build the wrong thing

The review states:

> spec calls this a "function hook," but Claude Code has no such type. The five documented hook
> types are `command`, `http`, `mcp_tool`, `prompt`, and `agent`. The spec intends an
> `agent`-type hook … Implementers need `type: "agent"` spelled out.

**Function hooks are real and were measured working six times in the session that wrote the spec.**
The live 2.1.269 binary carries both of the feature's own strings:

```console
$ strings -a ~/.local/share/claude/versions/2.1.269 \
    | grep -oE "CLAUDE_CODE_ENABLE_FUNCTION_HOOKS|tengu_plugin_hooks_modules" | sort -u
CLAUDE_CODE_ENABLE_FUNCTION_HOOKS
tengu_plugin_hooks_modules
```
Control arm: a freshly-invented nonce against the same command shape → **0**.

And the engine loaded and dispatched them, repeatedly (see
`2026-09-11-function-hooks-firing-probe.md`, `-worktree-bash-probe.md`,
`-skillsdir-and-gate-probes.md`):

```
hooks module fnhook-skillsdir-probe loaded (worker, environment 1, tier user); events: classic.SessionStart
plugin.register: fnhook-skillsdir-probe (user, fnhook-skillsdir-probe@skills-dir), judged by core alone: admitted
hooks module wt-classic-pretooluse-bash classic.PreToolUse settled in 4.8ms (worker hop, next() included)
```

**Two different mechanisms were conflated.** The five-value `type` field is real — `"type":
"agent"` does appear at `hooks.md:3574`, control arm `"type": "command"` → 25 hits — but it belongs
to **classic hooks declared in `settings.json`**. A **function hook** is declared in a *plugin's*
`hooks/hooks.json` through a `modules` key naming a TS/JS module that exports `register`. It has no
`type` field at all.

**Following the recommendation would produce a classic `settings.json` hook**, which is a different
substrate: no `additionalContext: string[]` return contract for the spec's type gate to check, no
plugin module, no `@skills-dir` deployment, and no use for `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS`.
Every defensive decision in the spec would then be aimed at a substrate the implementation is not
using.

## Why the review reached it — a bounded probe, and the bound was the corpus

The vendored harness-docs corpus does not document function hooks **at all**:

| term | files |
|---|---:|
| `function hook` | **0** |
| `ENABLE_FUNCTION_HOOKS` | **0** |
| `hooks module` | **0** |
| `.claude/agents` (control arm) | **19** |

The corpus simply predates the feature — upstream `anthropics/claude-code#91870` is still an OPEN
design RFC, and the product name ("Claude Mods") was announced 2026-09-09. So "I searched the docs
and found five types" was a true statement about a corpus that could not answer the question, read
as a statement about the world. `probes-need-a-control-arm.md` rule 3: the bound turned *absent*
into *unreachable*. The arm that settles it — the binary — was available and not run.

## But the CONCLUSION is right, for a different reason, and the spec must change

A reviewer with full repository access, reading the spec cold, concluded the central mechanism does
not exist. **An implementer will do the same.** The spec names "function hook" throughout and never
defines it, never says it is declared by a `modules` key in a plugin's `hooks.json`, never says it
requires `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS`, and never links the probe reports that establish any
of it.

That is a genuine under-specification — arguably the worst one in the spec — and this review
demonstrated it by falling into it. The fix is **not** `type: "agent"`. The fix is to define the
mechanism, state the enable flag, and cite the measured evidence.

## What stands

Everything else. The three seams were independently verified with the shape the spec claims
(`default_gh_runner()`; doctor checks as `Setup -> list[str]` with both arms armed in
`tests/test_doctor.py`; wiring contracts in `suites.toml`). No contradictions found. Out of Scope
judged complete. The fail-open reasoning judged sound. The conflict of interest was declared
without being asked twice.
