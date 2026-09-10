# Clarify Before Acting: Ask Until Sure on Ambiguous Work

When work is ambiguous, has multiple reasonable approaches, or is hard to
reverse, resolve the uncertainty before acting. Recommend an option, explain
both sides, cite the evidence, and keep asking until the answer is sufficient.

Use `AskUserQuestion` when the tool is available. When it is absent or denied,
present the same bounded options in prose and **STOP** for the answer. This
fallback applies to every ordinary subagent (the harness strips the tool even
when listed), `permissionMode: dontAsk`, `-p`, and
`--permission-prompts none`. A fallback question is still a question; do not
continue as though silence were consent.

A **fork** is different: it skips the tool filters and keeps the main
conversation's tool pool, so it is the one subagent shape that can still ask.

## Why this rule exists

Session 2026-06-29: the user requested hk-hang prevention and asked to be
questioned until the approach was certain. The selected idea—per-step hk
timeouts—proved impossible because hk has no timeout support. Surfacing that
before implementation and confirming the outer-timeout pivot prevented the
wrong system from being built.

## Rules

1. **Ask before ambiguous, multi-path, or irreversible work.** Resolve unclear
   scope, approach, or intent before deletes, pushes, merges, external effects,
   or other difficult-to-reverse actions.
2. **Recommend, do not merely enumerate.** Every question carries:

   - A recommendation. For single-select questions, put it first and end its
     label with `(Recommended)`.
   - Both sides. Every option description includes `PRO:` and `CON:`.
   - A citation: a `backticked/path`, `#NNN`, or URL. Label genuinely absent
     evidence with the literal `[no prior evidence]`; needing that escape is a
     prompt to search first.
   - A free-form route. The harness supplies "Other"; do not pad the choices.

3. **Use the native tool when possible; otherwise use the bounded fallback.**
   Apply the same recommendation, trade-off, and citation standard in prose,
   then stop. Never claim a subagent can call a tool the harness removed.
4. **Proceed on clear, low-risk, reversible tasks.** Verify discoverable facts
   yourself. Manufacturing questions is also a failure mode.
5. **Surface infeasibility immediately.** Stop and reconfirm a pivot with
   evidence rather than silently substituting a different solution.
6. **Keep asking until sure.** New ambiguity revealed by an answer warrants a
   new round.

## Timeout semantics are not project policy

`askUserQuestionTimeout` is a **USER-or-MANAGED** setting, not a project
`.claude/settings.json` key. Since v2.1.200 it accepts `60s`, `5m`, `10m`, or
`never` (the default). When the timer fires, Claude Code **submits the options
already selected**. That auto-continue is a partial answer, never silence.
`CLAUDE_AFK_TIMEOUT_MS` overrides the setting for one session.

Do not add `askUserQuestionTimeout` to this repository. The bounded fallback is
for tool unavailability or denial; a configured timeout still returns a real,
possibly partial answer that must be interpreted before work continues.

## The gate and its boundary

`.claude/settings.json` wires `PreToolUse` matcher
**`Bash|AskUserQuestion|Edit|Write|NotebookEdit`** to
`scripts/pretooluse-guard.sh`. `dotfiles_setup.ask_quality` denies tool-based
questions missing the recommendation, `PRO:`/`CON:`, or citation. The deny
prevents the call and returns its reason to the model; selfcheck exercises both
allow and deny arms through the registered wrapper.

Current native anchors (re-read 2026-09-09): ordinary subagents lose
`AskUserQuestion` even when explicitly allowed, while forks retain the parent
pool (`$CC/sub-agents.md:379-384`); project settings reload without restart
(`$CC/settings.md:646`); and a hook `deny` prevents the tool call
(`$CC/hooks.md:1744-1745`). Timeout scope and behavior are documented at
`$CC/settings-reference.md:2759-2774` and `$CC/tools-reference.md:125-137`.

⚠️ **The five-tool matcher above is an exact-string list, not a regular
expression.** Matcher evaluation depends on the characters in the value
(`$CC/hooks.md:285-297`): `*`/empty matches all; a value of only letters,
digits, `_`, `-`, spaces, `,` and the alternation bar is a list of **exact**
strings; *any other character* makes the whole value an **unanchored** JS
regex. Ours is on the exact path, so adding a single `.` or `^` would silently
reinterpret every alternative at once — on the regex path `Edit.*` matches
`NotebookEdit` too. Anchor with `^…$` if this ever needs regex semantics.

Availability is resolved at the call site. Do not route a question through a
different agent merely to obtain the tool unless that fork is already the
appropriate owner of the work.

For an ordinary subagent, the prose fallback preserves the decision boundary:
the delegate returns its recommendation and waits for the coordinator or user
to provide the missing choice.

The prose path has no enforcement callback. Its protection is the explicit
stop, which prevents work from racing ahead of the answer.

The hook cannot detect a question that was never attempted, cannot grade prose
fallbacks, and cannot make a stripped tool reappear. Judgment therefore stays
in this eager rule; automation only protects the call surface it can observe.
The standard has drifted repeatedly, so the ask-quality implementation remains
the mechanical layer for tool-based asks.

## Applies to

All non-trivial work: planning, multi-file changes, design choices,
destructive or outward-facing actions, and requests that under-determine the
result.

## See also

- `do-not.md` — invariants that clarification cannot waive.
- `mise-tasks-only.md` — the sibling PreToolUse guard.
- `probes-need-a-control-arm.md` — why both gate arms matter.
- `python/src/dotfiles_setup/ask_quality.py` — the enforcer.
- `docs/rules-evidence/clarify-before-acting.md` — probes and archaeology.
