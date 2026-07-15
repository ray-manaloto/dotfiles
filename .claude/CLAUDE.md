<!-- OMC:START -->
<!-- OMC:VERSION:4.11.4 -->

# oh-my-claudecode - Intelligent Multi-Agent Orchestration

You are running with oh-my-claudecode (OMC), a multi-agent orchestration layer for Claude Code.
Coordinate specialized agents, tools, and skills so work is completed accurately and efficiently.

<operating_principles>
- Delegate specialized work to the most appropriate agent.
- Prefer evidence over assumptions: verify outcomes before final claims.
- Choose the lightest-weight path that preserves quality.
- Consult official docs before implementing with SDKs/frameworks/APIs.
- Research existing tools/native features/services BEFORE writing any custom code (hard gate — `.claude/rules/use-tool-builtins.md`); homegrown code is the last resort and needs written justification.
</operating_principles>

<delegation_rules>
Delegate for: multi-file changes, refactors, debugging, reviews, planning, research, verification.
Work directly for: trivial ops, small clarifications, single commands.
Route code to `executor` (use `model=opus` for complex work). Uncertain SDK usage → `document-specialist` (repo docs first; Context Hub / `chub` when available, graceful web fallback otherwise).
</delegation_rules>

<model_routing>
`haiku` (quick lookups), `sonnet` (standard), `opus` (architecture, deep analysis).
Direct writes OK for: `~/.claude/**`, `.omc/**`, `.claude/**`, `CLAUDE.md`, `AGENTS.md`.
</model_routing>

<skills>
Invoke via `/oh-my-claudecode:<name>`. Trigger patterns auto-detect keywords.
Tier-0 workflows include `autopilot`, `ultrawork`, `ralph`, `team`, and `ralplan`.
Keyword triggers: `"autopilot"→autopilot`, `"ralph"→ralph`, `"ulw"→ultrawork`, `"ccg"→ccg`, `"ralplan"→ralplan`, `"deep interview"→deep-interview`, `"deslop"`/`"anti-slop"`→ai-slop-cleaner, `"deep-analyze"`→analysis mode, `"tdd"`→TDD mode, `"deepsearch"`→codebase search, `"ultrathink"`→deep reasoning, `"cancelomc"`→cancel.
Team orchestration is explicit via `/team`.
Detailed agent catalog, tools, team pipeline, commit protocol, and full skills registry live in the native `omc-reference` skill when skills are available, including reference for `explore`, `planner`, `architect`, `executor`, `designer`, and `writer`; this file remains sufficient without skill support.
</skills>

<verification>
Verify before claiming completion. Size appropriately: small→haiku, standard→sonnet, large/security→opus.
If verification fails, keep iterating.
</verification>

<execution_protocols>
Broad requests: explore first, then plan. 2+ independent tasks in parallel. `run_in_background` for builds/tests.
Keep authoring and review as separate passes: writer pass creates or revises content, reviewer/verifier pass evaluates it later in a separate lane.
Never self-approve in the same active context — instead, route the approval pass to `code-reviewer` or `verifier`.
Before concluding OR advancing to the next task: zero pending tasks and EVERY applicable check green with evidence — local gates (lint, pytest, verify) plus PR checks and post-merge `main` CI where relevant. Verify from the real artifact (file `rc` / API `conclusion`), never a piped tail or a notification's exit code. See `.claude/rules/verify-before-advancing.md`.
</execution_protocols>

<hooks_and_context>
Hooks inject `<system-reminder>` tags. Key patterns: `hook success: Success` (proceed), `[MAGIC KEYWORD: ...]` (invoke skill), `The boulder never stops` (ralph/ultrawork active).
Persistence: `<remember>` (7 days), `<remember priority>` (permanent).
Kill switches: `DISABLE_OMC`, `OMC_SKIP_HOOKS` (comma-separated).
</hooks_and_context>

<cancellation>
`/oh-my-claudecode:cancel` ends execution modes. Cancel when done+verified or blocked; keep the mode running while work is incomplete.
</cancellation>

<worktree_paths>
State: `.omc/state/`, `.omc/state/sessions/{sessionId}/`, `.omc/notepad.md`, `.omc/project-memory.json`, `.omc/plans/`, `.omc/research/`, `.omc/logs/`
</worktree_paths>

## Agent skills

Config for the `mattpocock-skills` engineering flow. Lives here, because the root `CLAUDE.md` is
byte-exactly `@AGENTS.md` (`claude_md_import_stub`) and `AGENTS.md` is at 200/200 lines.

**These files are hand-placed, and stay that way.** `/setup-matt-pocock-skills` generates the same
config but writes it to the root `CLAUDE.md` and `docs/agents/*.md` — paths our gates reject (the
stub check, and agnix's `**/agents/*.md` frontmatter rule). Reach for the files below instead; they
are its output, already adapted.

### Issue tracker

GitHub Issues on `ray-manaloto/dotfiles`, via `gh`. See `docs/issue-tracker.md`.
**`gh pr create`/`merge` are guard-denied — use `mise run ship` / `mise run land`.**

### Triage labels

The five canonical roles, adopted verbatim (no remapping). See `docs/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` (glossary) + `docs/adr/`. See `docs/domain.md`.
**Our ADRs are `.claude/rules/*.md`** — each carries its own "Why this rule exists"; `docs/adr/`
holds only domain-shaped decisions.

## Setup

Say "setup omc" or run `/oh-my-claudecode:omc-setup`.

<!-- OMC:END -->
