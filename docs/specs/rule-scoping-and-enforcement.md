# Rule scoping + enforcement — shared understanding

Established by `/grilling`, 2026-09-02c, operator + architect. Frontier empty:
every branch visited, nothing silently assumed. **Design record — not yet an
implementation plan.**

## Problem

Two halves, and the operator's own diagnosis names the second:

1. **Volume.** ~126,940 B of instruction loads every session (`md-budget`);
   `.claude/rules/` is ~122 KB across 26 files, **24 of them eager**. A prior
   measurement put cold start at 157,575 B = **19.70% of a 200k window**, with
   ~2,425 B of margin.
2. **Drift.** *"We've been doing this already but have not been following it for
   all the requirements."* Confirmed: three of the four asks are **already
   decided, open, and unimplemented** — see Supersession.

## Facts that shaped the design (all verified this session)

- ⚠️ **`paths:` fires on READ, not on write.** Vendor: *"Path-scoped rules
  trigger when Claude **reads** files matching the pattern, not on every tool
  use."* A whole-file `Write` never fires it. **Write-triggered injection needs a
  hook, not `paths:`** — two mechanisms, not one.
- ⭐ **The trigger test has FOUR categories**, not two
  (`.claude/rules/md-size-budgets.md`):

  | Category | Disposition |
  |---|---|
  | File-triggered | safe to scope with `paths:` |
  | Behaviour-triggered | **must stay eager** |
  | Creation-triggered | **cannot be scoped** — you never read the file first |
  | Behaviour-triggered but niche | **convert to a SKILL** — loads on relevance |

  The fourth is a *conversion*, not a cut, so it does not fight fidelity.
- ⭐ **We already built a path-scoped injector.**
  `python/src/dotfiles_setup/mise_config_context.py` (9,219 B): PostToolUse on
  `Edit|Write|NotebookEdit`, 7 fnmatch globs, emits `additionalContext`,
  hand-rolled dedup at `.agent/state/mise-config-context/<key>.seen`.
  ⚠️ **Its key is `f"{session_id}--{agent_id}"`, not `session_id`** — measured
  defect: keyed on session alone, the first subagent consumed the reminder for
  every sibling (agent A 1,240 B, agent B zero). **Any new injector keys the same
  way.**
- **Injection field is `hookSpecificOutput.additionalContext`**; top-level is
  silently ignored. Cap 10,000 chars. `systemMessage` is terminal-only.
  `tool_input.file_path` (always absolute) is carried by PreToolUse /
  PostToolUse / PostToolUseFailure. **UserPromptSubmit carries no path.**
- ⭐ **Hooks have a native `if` path filter** (`"Edit(*.ts)"`, permission-rule
  syntax, tool events only). **None of our five handlers use it.**
- ⭐ **`InstructionsLoaded`** fires when a rule loads, carrying
  `load_reason:"path_glob_match"`, the rule's `globs`, and `trigger_file_path`.
  Output discarded — observes, cannot inject. **This is the audit channel for
  "did my scoped rules actually fire".** Also: rules **re-load after compaction**.
- **No harness dedup.** `once: true` exists but is *"only honored for hooks
  declared in skill frontmatter; ignored in settings files"*.
- **`FileChanged` is the wrong event** — no decision control, cannot inject,
  matcher is literal filenames.
- **Codex cannot mirror this.** Control-armed: no `file_path`, no `if`, no
  path-scoped instruction files. Matcher is a regex over the tool NAME. Its deny
  equivalent is `prefix_rule(decision="forbidden")` — command-prefix scoped.
  AGENTS.md is a cwd directory-walk capped at 32 KiB.
- **Deny rules block in every mode including `bypassPermissions`; hooks fail
  open** (exit 1 does not block, only exit 2; a timed-out PreToolUse does not
  block). ⚠️ **`clarify-before-acting.md` and `mise-tasks-only.md` both claim the
  HOOK deny applies in bypassPermissions — the vendor makes that claim for deny
  RULES only. UNVERIFIED, load-bearing, wants a live probe.**

## Settled decisions

| # | Decision |
|---|---|
| 1 | Scope is the **whole corpus** — 26 rules + AGENTS.md + CLAUDE.md + hooks + rule-bearing docs |
| 2 | **Procedure + hk gate + applied to all 26**, not instance fixes |
| 3 | **AGENTS.md**: extract path-specific content into scoped rules AND split subdirectory files by load |
| 4 | **Target ≈60 KB**, but **fidelity wins** — move archaeology to `docs/rules-evidence/`, never delete; miss the number rather than lose a fact |
| 5 | Eager rules need a **frontmatter flag + stated reason**, hk-gated. ⚠️ Prior research is emphatic: the flag must **GATE the load**, not merely document it |
| 6 | **Both agents, FULL CONTENT parity**, rules written **agent-neutral** — a rule that cannot be stated truthfully for both describes mechanism where it should describe the constraint |
| 7 | Detection: **static gate now** (4 checks), transcript-replay evals later |
| 8 | Dedup: **once per session per rule**, keyed `session_id--agent_id` |
| 9 | Trigger: **`paths:` for read-triggered, a PostToolUse hook for write-triggered** — superseding the earlier "whatever `paths:` does", which the read-trigger finding refuted |
| 10 | Lands on a **new branch off `main`**, after ITEM 11 ships |
| 11 | **Supersede and close** #283/#681/#687/#688; open ONE superseding issue |
| 12 | Logging: adopt `kb_setup.events`/`sinks` in new code **AND migrate all modules**, in **one migration commit** |

## Static gate — all four checks

1. Every scoped rule's globs match real files (an over-budget brace list is used
   **unexpanded and matches nothing, silently**; an invalid `[` matches nothing).
2. Every eager rule declares its reason.
3. The eager corpus stays under the byte target.
4. No suppression above file scope.

## Three denies

1. **Universal logger over `print`.** ⚠️ **Target is `kb_setup.events`/`sinks`,
   NOT structlog** — see Supersession. ruff `TID251` bans the API (spec decision
   D18, never configured).
2. **Codegen for models, enums and anything generatable.** Scope from a
   whole-project audit using a **refreshed** graphify graph AND `ty server` (LSP)
   — both.
3. **No suppression above file scope.** Ladder: code block > file > (never)
   project. **Existing violations are FIXED, not grandfathered** —
   `ruff.toml:18` (`tests/**/*.py`) and `:33` (`plugins/**/*.py`). An exception
   requires documented attempts and pros/cons, recorded **inline AND as an issue
   AND in rules-evidence**.

## Supersession — decided, open, never implemented

| Issue | State | Content |
|---|---|---|
| **#283** | OPEN | *"15 unscoped `.claude/rules/*.md` load every session (~16k est. tok); `paths:` frontmatter already proven on 4"* — title now stale, it is 24 |
| **#681** | OPEN | structured events into several sinks without blocking the caller |
| **#687** | OPEN | *"expand: forbid direct terminal writes on new code"* |
| **#688** | OPEN | *"contract: migrate the remaining modules off direct terminal writes"* |

### The logging decision chain — research → spec → REVERSAL → never built

1. **2026-08-08** research recommended **structlog + stdlib
   `QueueHandler`/`QueueListener`**, NDJSON; rejected loguru on its own docs'
   advice for libraries.
2. Same day, accepted as spec decisions **D17–D21**
   (`docs/specs/devcontainer-gcc162-dual-arch.md`), incl. **D18: ruff `TID251`
   bans `sys.stdout`**.
3. **2026-08-11 — REVERSED.** Verbatim from #681:

   > knowledge-base PR #273 has already shipped the reusable structured event
   > layer and human stdout/stderr + JSONL sinks (`kb_setup.events` /
   > `kb_setup.sinks`). **Do not build a second dotfiles-only logger.** Adopt the
   > shared KB event/sink contract instead.

**Verified today:** `kb_setup.events` and `kb_setup.sinks` are importable —
`HumanSink`, `JsonlSink`, `EventQueueHandler`, `Level`, `Tally`. structlog is
NOT in `pyproject.toml`, the KB contract is NOT adopted, `TID251` is NOT
configured.

⚠️ **This paragraph must survive the close of #681.** Losing it invites a third
structlog research round.

## Risks on the record

- **Decisions 11 and 12 were chosen against my recommendation**, concerns stated
  and overruled: closing issues discards provenance (mitigated by carrying the
  reversal verbatim into the superseding issue), and a single ~78-module
  migration commit is hard to review.
- **Decision 4 pushes toward deletion**; `memory-index-curation` records that
  shortening silently destroys facts living only in the shortened text.
  Mitigated by the fidelity ruling.
- **A real defect found, not yet filed:** `.codex/hooks.json` interpolates
  `${CLAUDE_PROJECT_DIR:-.}` — **Codex never sets it** (0 doc hits vs
  `CODEX_HOME` → 22), so every command silently falls back to `.` and works only
  while cwd is the repo root. The #343 shape on the Codex side. Runtime
  consequence SUSPECT, not live-probed. `.codex/hooks.json` also has **no
  PostToolUse handler**, so the existing injector is Claude-only.
- **`claude --version` = 2.1.258**; the `claude-code-expert` agent definition's
  ledger is 36 patches stale.
- **No published evidence** either way on instruction volume vs adherence. The
  19.70% figure is local. The premise that smaller-and-targeted beats
  bigger-and-always-on is **assumed, not established**.

## Research lanes feeding this

`injection-facts` · `rule-scoping-practices` · `prior-injection-research` ·
`logger-history` — all four reported; reports under
`docs/research/kb/reports/agents/2026-09-02-*`.

## GitHub repos touched

_None._ Design record; all inputs local to this repo and the sibling
knowledge-base clone.
