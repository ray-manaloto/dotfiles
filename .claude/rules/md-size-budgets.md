---
paths:
  - "hk.pkl"
  - "**/CLAUDE.md"
  - "**/AGENTS.md"
  - ".claude/rules/*.md"
  - ".claude/skills/**/SKILL.md"
---

# Markdown Size Budgets: By Load Class, and Only One Figure Is Anthropic's

Instruction-markdown budgets differ **by load class**, because the only thing
that justifies a size limit is **when the bytes are spent**. Enforced by
`dotfiles-setup md-budget` (hk step `md_size_budget`).

This rule is `paths:`-scoped, and legitimately so: its trigger genuinely *is* a
file — you only need it when editing `hk.pkl` or an instruction doc. That is the
test (below), applied to itself.

## The one documented figure

> "**Size**: target under 200 lines per CLAUDE.md file. Longer files consume
> more context and reduce adherence."
> — <https://code.claude.com/docs/en/memory> § Write effective instructions

It is a **soft guideline about a gradient, not a cliff**. The same page:

> "**CLAUDE.md files are loaded in full regardless of length**, though shorter
> files produce better adherence."

**Nothing truncates a CLAUDE.md at any size.** The 200-line/25KB *hard*
truncation applies to auto-memory `MEMORY.md` only — a file this repo does not
commit.

## Why this rule exists: we enforced a real number, against the wrong vendor

The predecessor step `claude_md_size_limit` enforced **200 lines AND 12,000
bytes** on every `CLAUDE.md`/`AGENTS.md`, captioned "max 12000 chars **per
Claude Code memory docs**".

**The number is real. The citation was wrong.** 12,000 is **Windsurf's** limit,
not Anthropic's:

> Workspace `.devin/rules/*.md` … **Limited to 12,000 characters per file.**
> `AGENTS.md` — Any directory in your workspace — **Processed by the same Rules
> engine**.
> — <https://docs.windsurf.com/windsurf/cascade/memories>

`mise run lint-docs` already enforces it as **agnix AGM-003** (Category:
`agents-md`, Tool: `windsurf`, Source type: `vendor_docs`). In Anthropic's corpus
the figure has **0 hits** (control-armed: 5 for MEMORY.md's cap, 12 for
`"200 lines"`) — so it was attributed to the wrong vendor, applied to the wrong
files (`CLAUDE.md` and rules, which Windsurf never reads), and duplicated a check
agnix already owns.

Provenance, from this repo's history:

1. `1f05365` — the gate is born enforcing **200 lines only**, correctly cited.
2. `99a8506` (#147) — `verify-before-advancing.md` describes the gate as
   "≤200-line / **≤12000-char**". The gate had **no char check** at that commit.
   Almost certainly copied from agnix's own AGM-003 warning — a real fact,
   **misfiled**.
3. `010009d` (#160 T13) — the mismatch is noticed and resolved **backwards**:
   the code is changed to match the doc, and the message credits Anthropic.

The lesson is not "someone invented a number" — it is that **a true fact
travelled without its source** until nobody could tell whose rule it was. It was
then applied to files the rule never governed, and it blocked real work (#290's
`tests/AGENTS.md` row).

### The correction that nearly wasn't made

The 2026-07-15 session that wrote this rule first concluded the figure was
**fabricated**, having grepped Anthropic's corpus with a proper control arm and
found nothing. The probe was sound; the *report* dropped its bound. "Not in
Anthropic's docs" became "not documented anywhere" — but the probe never
searched Windsurf, so it could not have found it. Only `agnix --strict` failing
surfaced the truth.

**A control arm proves a probe works INSIDE its bound. It says nothing outside
it.** That is `probes-need-a-control-arm.md` rule 3 (bound-limited searches are
suspect by construction) — violated here *while holding the rule*, which is why
it is recorded rather than quietly fixed.

## The budgets

| Class | Load semantics (documented) | Lines | Bytes |
|---|---|---|---|
| `eager_root` — root `CLAUDE.md` + `@import` closure, `.claude/CLAUDE.md` | "loaded in full at launch" | **200** | 24,000 |
| `rule_unscoped` — `.claude/rules/*.md` with no `paths:` | "loaded at launch with the same priority as `.claude/CLAUDE.md`" | **200** | 24,000 |
| `nested` — subdirectory `CLAUDE.md` + closure | "included when Claude reads files in those subdirectories"; not re-injected after `/compact` | **400** | 32,000 |
| `rule_scoped` — `.claude/rules/*.md` with `paths:` | "only load into context when Claude works with matching files" | **400** | 32,000 |
| `skill` — `.claude/skills/**/SKILL.md` | on invocation/relevance only | **500** | 32,000 |

**Every `AGENTS.md` additionally has a hard 12,000-char ceiling — owned by
agnix AGM-003, not by this gate.** That is Windsurf's rule for the file Windsurf
actually reads, so it is enforced by the tool that knows the vendor, and
`md_size_budget` does not duplicate it. Both must pass; for an `AGENTS.md`, AGM-003
binds first. When an `AGENTS.md` outgrows it, **move reference content to a
sibling doc and link it by path** (see `tests/TEST-INDEX.md`) — do not `@import`
it (agnix rejects Claude-only syntax in an agent-agnostic file) and do not add
the import to the `CLAUDE.md` stub (`claude_md_import_stub` forbids it).

Plus one **hard** limit: a `SKILL.md` `description` **> 1,536 chars is
truncated silently**, taking the keywords Claude matches on with it — the skill
simply stops being discovered. It is the only real cliff this repo can hit.

**The byte ceilings are ours**, not Anthropic's — anti-gaming backstops (a line
cap alone admits 200 × 400-char lines), sized never to bind before the
documented line limit. Label them as self-imposed. Do not re-attribute them
upstream; that error is the whole reason this file exists.

## Measurement rules

- **Budget the `@import` closure, not the file.** "Splitting into @path imports
  helps organization but doesn't reduce context, since imported files load at
  launch." A per-file cap is evadable by splitting — which the docs explicitly
  call a non-reduction.
- **The import directive is replaced, not added.** Counting it makes the root
  closure 201 lines and fails a file legitimately at 200.
- **Only `CLAUDE.md` is an entry point.** "Claude Code reads CLAUDE.md, not
  AGENTS.md" — an `AGENTS.md` reaches context only via its stub's import, so it
  is budgeted inside that closure, never standalone.
- **HTML comments are free in `CLAUDE.md`** ("stripped before the content is
  injected... without spending context tokens") — but that sentence says
  *CLAUDE.md files*. For rules and skills it is **undocumented**, so they pay
  full price. Never take a discount you cannot cite.

## Scoping: the trigger test (this is the load-bearing part)

Path-scoped rules "trigger when Claude **reads** files matching the pattern".
So scoping is safe only when the rule's trigger genuinely *is* reading a file.

- **File-triggered → safe to scope.** `ci-local-parity` (you read the workflow
  before editing it). This rule.
- **Behaviour-triggered → MUST stay eager.** `zero-skip-policy` (fires when a
  warning is about to be dismissed), `clean-git-state` (fires when validation is
  about to run), `do-not`, `verify-before-advancing`, `clarify-before-acting`,
  `probes-need-a-control-arm`. No glob predicts a decision.
- **Creation-triggered → CANNOT be scoped.** `zero-bash-logic` governs *new*
  `.sh` files; `omc-directory-conventions` governs *where to create* an
  artifact. You never read the file first, so the rule would be absent exactly
  when it is needed.
- **Behaviour-triggered but niche → a skill, not a rule.** "For task-specific
  instructions that don't need to be in context all the time, use skills
  instead, which only load when you invoke them or when Claude determines
  they're relevant." Skills load on *relevance*, which is the only mechanism
  that tracks a behavioural trigger.

**This was found the hard way:** `zero-skip-policy` and `clean-git-state` were
both `paths:`-scoped until 2026-07-15 — so the rules forbidding skipped warnings
and dirty-tree validation were silently absent from any session that didn't
touch the listed files. Un-scoping them *raises* eager context, and that is
correct: a judgment rule that is cheap and absent is worth less than one that is
costly and present.

The lever for eager context is therefore **trimming, not scoping** — cut what
Claude can derive from the codebase (directory layouts, dependency lists,
architecture overviews) and keep pitfalls, rationale, and conventions that
differ from tool defaults. That is `/doctor`'s documented heuristic.

## Applies to

Every tracked `CLAUDE.md`, `AGENTS.md`, `.claude/rules/*.md`, and
`.claude/skills/**/SKILL.md`. `plugins/**` is vendored and out of scope.

## See also

- `.omc/research/research-20260715-md-size-limits/report.md` — the primary-source
  audit; every figure control-armed.
- `python/src/dotfiles_setup/md_budget.py` — the enforcer.
- `.claude/rules/probes-need-a-control-arm.md` — why "0 hits" needed a control.
- `.claude/rules/use-tool-builtins.md` — the parent principle: check the source
  before inventing; here, before *enforcing*.
