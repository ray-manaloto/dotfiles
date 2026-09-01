# SPEC — research: make two process guarantees actually hold

## 1. Objective

The operator has stated two standing requirements. Both are currently carried by
prose and goodwill, which measurably does not hold — this session alone lost
track of work until it was reconstructed by hand, and surfaced open questions
only when the operator happened to ask.

  **R1.** Anything a codex lane works on is ALWAYS recorded in the
  planning-with-files task plan (`task_plan.md`), so it cannot be lost.

  **R2.** Anything that needs the operator's answer is ALWAYS surfaced to them as
  a usable prompt they can act on — not buried in prose, not silently guessed.

Produce a RESEARCHED DESIGN for making each hold. This is an investigation and a
proposal, not an implementation.

The failure this prevents is specific and already happened: this session's own
`.claude/rules/clarify-before-acting.md` gate can only judge the SHAPE of a
question that was asked. It is structurally blind to the question that was never
asked — the exact case R2 exists to cover. Any proposal that repeats that shape
is worthless, and saying so is a valid finding.

## 2. What to read first

- `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/ec02aa30-c480-4828-8d9c-3d7872e23daf/scratchpad/task_plan-snapshot.md` — the current task plan (~854 lines).
- `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/ec02aa30-c480-4828-8d9c-3d7872e23daf/scratchpad/notepad-snapshot.md` — this session's running findings; the
  narrative of what was nearly lost and how.
- `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/ec02aa30-c480-4828-8d9c-3d7872e23daf/scratchpad/advisor-report.md` — a prior advisory on an adjacent
  "make it unbypassable" question. Its reasoning about which layers can and
  cannot be trusted applies directly here; do not re-derive it, build on it.

In the repo:

- `.claude/rules/clarify-before-acting.md` — R2's existing partial mechanism,
  including its own admission of what no hook can see.
- `python/src/dotfiles_setup/ask_quality.py` — the enforcing gate (~10 KB).
- `.claude/settings.json` — how the PreToolUse matcher is wired.
- `.claude/rules/mise-tasks-only.md` — the repo's five-layer enforcement
  doctrine and its explicit statement that the hook FAILS OPEN on its own
  errors, and by design for `$(…)`, `sh -c`/`eval`, base64 and aliases.
- `.claude/rules/agent-report-persistence.md` and
  `.claude/rules/notepad-enforcement.md` — R1's existing partial mechanisms,
  and the recorded evidence that a rule nothing pushes into the prompt is not a
  layer at all.
- `python/src/dotfiles_setup/hook_guard.py` — the working example of a
  deterministic PreToolUse deny.
- `python/verification/suites.toml` — how this repo asserts that a chain of
  mechanisms still exists.

## 3. The questions to settle

**Q1 — For R1, what is the enforcement point?** A lane's work becomes known at
several moments: dispatch, its report, its commit, the caller's next turn. Which
of those can a deterministic mechanism actually observe? Be concrete about what
the harness exposes: hooks fire on tool calls in THIS session — determine whether
a subagent's tool calls are visible to the parent session's hooks, or only the
parent's own. That single fact decides most of the design, so settle it against
the offline harness docs (see §4) rather than assuming.

**Q2 — For R1, what does "recorded" mean such that a machine can check it?**
"The lane's work is in the plan" is not checkable. Propose something that is —
and state honestly what it does NOT guarantee. A gate that verifies an entry
exists cannot verify the entry is accurate or current; say so plainly rather
than implying more.

**Q3 — For R2, can an unasked question be detected at all?** This is the hard
one. Argue it from mechanism, not optimism. If the honest answer is that no
deterministic gate can detect it, say so and pivot to the strongest achievable
alternative — for example a forcing function at a natural boundary (turn end,
handoff, ship) that requires an explicit statement of open questions, including
the explicit statement that there are none. Consider whether the "explicit
none" form is checkable and whether it degrades into a rubber stamp.

**Q4 — For R2, what is the deliverable format?** The operator asked for
"user prompts for anything needed by me to answer". Define that artifact
precisely: where it lives, what it contains, how it is kept current, and how the
operator consumes it. Note this repo's existing `AskUserQuestion` standard
(recommendation first, PRO/CON per option, a citation) and say whether the new
artifact should reuse that shape or is a different thing.

**Q5 — Which layer for each?** Using the advisory's framing of trust layers,
place each proposal: rule prose / PreToolUse hook / mise task gate / hk step /
suites.toml contract / CI. For each, name the concrete bypass path. Be explicit
that a local layer is advisory in an agent's hands, and that this repo already
records the PreToolUse hook as fail-open.

## 4. Harness facts — settle these offline, do not guess

The knowledge-base repo carries the vendor's own Claude Code docs on disk:

    /Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code

Grep there for hook events, matcher values, subagent behaviour, and settings
semantics. Any claim about what the harness does must cite a file there, or a
live probe you ran — never assume. If a fact cannot be settled, mark it
UNVERIFIED and say what it would take to settle.

## 5. Deliverable

Write a report to:

    docs/research/kb/reports/agents/2026-09-01-process-enforcement-design.md

⚠️ Write it INCREMENTALLY — create the file early and update it as you go, never
hold findings in memory to write at the end. Two lanes died this session having
written nothing.

Structure:

- A verdict per requirement (R1, R2): is it enforceable, partially enforceable,
  or not enforceable — stated in one line before any detail.
- The design for each, at the layer you chose, with the concrete bypass path
  named.
- Options with explicit `PRO:` and `CON:`, and a recommendation with the one
  risk that decides it.
- What you could NOT settle, marked as such.
- A `## GitHub repos touched` enumeration (`.claude/rules/research-repo-enumeration.md`).

Then append a phase to `/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/ec02aa30-c480-4828-8d9c-3d7872e23daf/scratchpad/task_plan-snapshot.md`? NO — do not touch that
snapshot. The caller folds your design into the real plan.

## 6. Constraints

- Research and propose. Do NOT implement a hook, a gate, or a rule file, and do
  not edit `.claude/settings.json`, `hk.pkl`, or any rule.
- No new `scripts/*.sh` in any proposal — this repo's zero-bash-logic rule puts
  logic in `python/` behind a thin wrapper.
- Reject security theatre explicitly. If a proposal only appears to enforce, say
  so; a smaller honest guarantee beats a larger fake one.
- Prefer an existing mechanism over a new one — this repo has a hard
  research-before-building rule (`.claude/rules/use-tool-builtins.md`). If
  `ask_quality.py` or the suites.toml contract pattern can be extended, that
  beats inventing a parallel system.

## 7. Verification

    mise run lint

Report must include the file you wrote and its line count. There is no test to
run — the deliverable is a design.

## 8. Commit

COMMIT: lane — commit your report on the branch your worktree is already on. Do
not create or switch branches. Do not push, no PR.

## 9. PREMISES

- L1 `.claude/rules/clarify-before-acting.md` exists and states, in its own words, that "what no hook can see is an ask that never happened" — read this session.
- L2 `python/src/dotfiles_setup/ask_quality.py` exists and is ~10 KB; `.claude/settings.json` wires a PreToolUse matcher that includes `AskUserQuestion` — read this session.
- L3 `.claude/rules/mise-tasks-only.md` records that the PreToolUse hook FAILS OPEN on its own errors, and is fail-open by design for `$(…)`, `sh -c`/`eval`, base64 and aliases — read this session.
- L4 `.claude/rules/agent-report-persistence.md` records that a requirement absent from the agent's own definition went into none of four briefs, two agents died leaving nothing, and only one persisted on its own initiative — read this session.
- L5 `task_plan.md` is gitignored and machine-local, so it exists ONLY in the primary checkout and will NOT be present in your worktree. That is why a snapshot is provided at an absolute path outside the repo.
- L6 The knowledge-base offline claude-code doc tree is at `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/claude-code` — this is the repo's documented step-00 research source (`.claude/rules/research-doc-sources.md`).
- A1 ASSUMPTION: a subagent's tool calls do NOT fire the parent session's PreToolUse hooks. Held WITHOUT verification and it is load-bearing for Q1 — settle it against the offline docs in §4 before designing on it, and report what you find either way.
