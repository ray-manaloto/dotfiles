# Brief — seam-advisor (rule-injector PostToolUse seam), 2026-09-02d

Persisted per `.claude/rules/agent-report-persistence.md` rule 5: a
findings-bearing lane maps BOTH its brief and its report to an artifact. The
report is `2026-09-02-seam-advisor-rule-injector.md`; this is the prompt that
produced it, verbatim in substance.

**Lane:** `codex-advisor` (substituted for `fable-orchestrator:fable-advisor`
per `.claude/CLAUDE.md` while Claude tokens are constrained). Operator asked for
"@fable-adviser"; the substitution was stated to them, not made silently.

## The question put to it

Which seam carries write-triggered instruction-rule injection for the rule
scoping + enforcement feature:

- **A** — generalize `python/src/dotfiles_setup/mise_config_context.py`, the
  existing sole PostToolUse handler
  (`.claude/settings.json` PostToolUse `Edit|Write|NotebookEdit`).
- **B** — add a second, dedicated PostToolUse handler.
- **C** — use the hooks' native `if` path filter to narrow event delivery, with
  Python only building the payload.

## Constraints supplied

Spec decision 8 (dedup once per session per rule, keyed `session_id--agent_id`,
encoding the measured defect where the first subagent consumed the reminder for
every sibling — agent A 1,240 B, agent B zero); `additionalContext` is the only
honoured injection field, cap 10,000 chars; hooks fail open (only exit 2 blocks);
decision 6's both-agents full-content parity vs Codex's limits; the
`use-tool-builtins.md` hard gate; `zero-bash-logic.md`; the repo's dominant gate
shape (one hk step -> one `dotfiles-setup <verb>` -> one module -> one test).

## What was demanded back

1. A one-line verdict (A/B/C or a named hybrid).
2. **The single risk that decides it** — not a balanced survey.
3. Whether option C actually reduces custom code or only narrows event delivery;
   verify the "no handler uses `if` today" premise against `.claude/settings.json`.
4. Whether decision 6's full-content parity is satisfiable given Codex's
   constraints, or needs amending.
5. Any failure mode NOT in the supplied list.

Standing instructions: ground every claim in a `file:line` actually read; say
UNVERIFIED rather than assert; **and say plainly if one of my premises is wrong —
that is more valuable than agreement.** Persist incrementally; SendMessage last.

## Outcome

Verdict **A** (sharpened: retire rather than widen). It refuted **two** of my
premises — the Codex "structurally cannot" claim and the settings verb — and
surfaced four failure modes I had not listed. Both refutations were
independently re-verified by me before adoption. Instruction 5 is what produced
the highest-value half of the return; keep it in future advisor briefs.
