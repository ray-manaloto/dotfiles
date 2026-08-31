# Shared context — adoption review of the `planning-with-files` plugin

The operator is considering installing this Claude Code plugin into an existing,
heavily-gated repository. **Your job is to find what it would break, duplicate,
or silently change** — not to summarise what it does. The decision is the
operator's; you supply cited evidence.

Nothing is installed yet. This review happens BEFORE adoption, deliberately.

## The two trees

**The plugin (cloned, read-only):**
`/private/tmp/claude-501/-Users-rmanaloto-dev-github-ray-manaloto-dotfiles/84f08a9b-5231-4071-8759-b2d32945c99e/scratchpad/pwf/`

632 files, version 3.12.0, MIT. Ships skill trees for 60+ agent platforms
(`.agents/`, `.claude/`, `.codex/`, `.cursor/`, `.gemini/`, `.codebuddy/`,
`.mastracode/` and more), 13 slash commands, ~20 shell scripts, and hook
configs — including `hooks/hooks.json`, `claude-hook.sh` and `.codex/hooks.json`.

Its README says it creates `task_plan.md`, `findings.md`, `progress.md` in the
PROJECT ROOT, plus `.planning/YYYY-MM-DD-slug/` and `.active_plan`.

**The target repo:**
`/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/` (branch
`proto/bake-matrix-fields`)

What matters about it:

- **A PreToolUse guard chain.** `.claude/settings.json` wires
  `Bash|AskUserQuestion|Edit|Write|NotebookEdit` to `scripts/pretooluse-guard.sh`
  → `dotfiles-setup hook pretooluse`. It DENIES commands (redirecting to mise
  tasks), denies edits on the default branch, and denies malformed
  `AskUserQuestion` calls. Logic in `python/src/dotfiles_setup/hook_guard.py`,
  `branch_guard`, `ask_quality`. Rules: `.claude/rules/mise-tasks-only.md`,
  `.claude/rules/do-not.md` item 9, `.claude/rules/clarify-before-acting.md`.
- **SessionStart and SessionEnd hooks** already exist (project doctor; a
  command-audit transcript scan). See `.claude/CLAUDE.md`.
- **An `.agents/skills/` tree** with three entries: `codex-task-orchestration`,
  `graphify`, `session-review`. An hk step `session_review_skill_parity` asserts
  `.agents/skills/session-review/SKILL.md` is byte-identical to its `.claude/`
  twin. **The plugin ships its own `.agents/skills/planning-with-files/`.**
- **Machine-enforced conventions** in `hk.pkl`: `no_lint_skip` (no inline
  suppressions), `bash_logic_budget` (an allowlist + per-file line budget for
  `scripts/*.sh`; `plugins/**` is stated out of scope), `claude_md_import_stub`
  (root `CLAUDE.md` must be byte-exactly `@AGENTS.md`), `claude_agents_md_pairs`,
  `md_size_budget`, `no_env_dump`.
- **`AGENTS.md` is 11,875 / 12,000 bytes** — 125 bytes of headroom under agnix
  AGM-003. Any file that appends to it breaks the gate.
- **Existing agent-artifact conventions** (`.claude/rules/agent-artifact-conventions.md`):
  ALL agent working files go under `.agent/` (gitignored) or `docs/` (tracked).
  Rule 1 is literally "No ad-hoc directories."
- **Existing session machinery that overlaps this plugin's purpose:**
  `.claude/skills/session-handoff/SKILL.md`, `.claude/skills/session-resume/SKILL.md`,
  `.claude/rules/notepad-enforcement.md` (`.agent/notepad.md`),
  `.claude/rules/agent-report-persistence.md`.

## Why the operator wants it

Verbatim: *"we are losing too much information"*. An audit this session found 8
operator instructions that never reached any durable artifact, and 10 of 60
agent lanes whose reports were never persisted.

So the honest question is not "is this plugin good" but **"does it fix THAT
problem in THIS repo without breaking what already works?"**

## Rules for your report

- Every claim cited: `file:line` in one of the two trees.
- A negative claim ("it installs no hooks", "nothing collides") requires a
  stated control arm — grep for a term you KNOW is present, same command shape,
  so a zero is a real negative rather than a blind probe.
- Read the actual files. Do not infer behaviour from the README or from the
  plugin's own description of itself; the description is marketing until the
  code confirms it.
- Do not install anything, do not modify either tree, do not run its scripts.
- Rate each finding BLOCKER / SERIOUS / MINOR / NON-ISSUE, and say plainly when
  something is fine — a review that only finds problems is not discriminating.

End with `## GitHub repos touched`.
