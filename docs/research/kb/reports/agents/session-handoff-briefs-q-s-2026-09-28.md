# Session-handoff §1c briefs Q–S (added 2026-09-28, Ray)

Companion to "Briefs M-P" (`session-2026-09-23d-agent-briefs.md`). Each lane is read-only except its own report file,
persisted incrementally to `docs/research/kb/reports/agents/session-audit-<kind>-<date>.md`. Sources for all three: the
session transcript (native `~/.claude/projects/<project>/<session-id>.jsonl` and its `subagents/`), `git log` of the
session's PRs, `task_plan.md`, `progress.md`, `findings.md`, and MEMORY.md with the files it links.

## Brief Q — process compliance

For EVERY PR this session shipped or landed, build one row: PR, diff class (behavior-bearing / mechanical / spec'd /
touches session tooling, the PreToolUse guard or the devcontainer), then for each required step the evidence or
MISSING: (1) `mise run lint`, pytest, `mise run verify` with a recorded `rc=`; (2) bundled `/code-review`; (3) the
cross-family lens per `.claude/skills/codex-sdlc-team/SKILL.md` § Review tiers (Anthropic-authored → codex review lens,
codex-authored → Opus `cold-reviewer`, resumed if it hit its turn cap); (4) `/mattpocock-skills:code-review` when a spec
file drove the diff; (5) the repo `verify` skill (`.claude/skills/verify/SKILL.md`) when the diff touched session
tooling, the guard or the devcontainer; (6) `land` rc and main CI conclusion. A step that did not run is a finding even
when the PR is green. Worked miss (2026-09-28): #1421/#1427/#1429 shipped without the repo `verify` skill, and #1426
(spec'd) without the mattpocock review, until Ray asked.

## Brief R — repeat offenders

List every mistake that occurred twice in the session, OR once while a memory, rule or skill already warned against it
(grep MEMORY.md, `.claude/rules/`, `.claude/skills/` for the shape). For each: the occurrences (transcript anchors), the
existing warning that failed to prevent it, and a proposed MACHINE check — a `hook_guard` rule, a test, a hk step, a
ship gate — with the file it lives in. "Add to memory" is not an acceptable disposition for a repeat: memory already
failed. If no mechanical check is feasible, say why and mark it for a Ray ruling. Worked case: the zsh `====` separator
aborted commands in four sessions despite `feedback_zsh_equals_expansion`, and was closed only by a guard (#1388).

## Brief S — retrieval misses

List every fact the session had to re-derive — by reading logs, transcripts or source, or by a first attempt that
failed — that a known file should have handed it directly. Examples of the shape (2026-09-28): the hook-selfcheck entry
point (`dotfiles-setup hook selfcheck`, not a mise task), `sync --check`, the graphify hook payload needing
`tool_input`, `jq` being pinned in `shared.toml`. For each: the cost (tool calls or a failed run), and the ONE file that
should carry it (skill, rule, a task's `--help`/description, or memory), with the exact line to add. Prefer the file
the agent already reads at that moment (the skill for that workflow) over MEMORY.md.

## GitHub repos touched

_None._
