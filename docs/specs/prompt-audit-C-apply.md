# Spec: apply prompt-audit report C to the subagent roster

Source of truth for every hunk: `docs/research/kb/reports/agents/prompt-audit-C-agents-2026-09-24.md`
(§ Findings C1–C15, § Proposed diff). Plan authority: `task_plan.md` "2026-09-24/25 session remainder", item 1
("Audit C5 SUPERSEDES the fable section's V4 — one edit to the sol lanes closes both").

## 1. Objective

Remove stale facts, dated incident stories, token-shortage-era routing text and wrong cross-references from the
subagent prompts, so agents stop acting on claims that are false today. The failures prevented:
- `graphify-operator` reads counts from the wrong line of `GRAPH_REPORT.md` (every delta "unparsable") — C1.
- `codex-sol-implementer`'s 540 s wait slice is auto-backgrounded at the 120 s Bash default (#1155) — C2.
- the orchestrator is told to use the codex critic/auditor/expert lanes only "while Claude tokens are constrained",
  a condition that no longer applies — C5.
- six prompts cite "50 secrets" (56 now), "`mise run` masks digits" as current, and misquote
  `.claude/rules/ai-cli-invocation.md` — C3, C4, C6.

## 2. Files

Modify (Claude wrappers, hand-authored):
- `.claude/agents/graphify-operator.md` (C1)
- `.claude/agents/codex-sol-implementer.md` (C2, C9)
- `.claude/agents/adversarial-critic.md` (C3, C6, C15)
- `.claude/agents/staleness-auditor.md` (C3, C6, C8, C15)
- `.claude/agents/claude-code-expert.md` (C3, C6, C10, C11, C15 §2 form at the "one agent in that run" sentence)
- `.claude/agents/codex-sol-adversarial-critic.md` (C3, C4, C5, C6, C15)
- `.claude/agents/codex-sol-staleness-auditor.md` (C3, C4, C5, C6, C8, C15)
- `.claude/agents/codex-sol-claude-code-expert.md` (C3, C4, C5 description + C5d-f body, C6, C11)
- `.claude/agents/codex-sol-advisor.md` (C4)
- `.claude/agents/codex-sol-operator.md` (C4e)
- `.claude/agents/claude-advisor.md` (C7a)
- `.claude/agents/premise-verifier.md` (C7b, including its provenance header line)
- `.claude/agents/issue-filer.md`, `.claude/agents/spec-scribe.md` (C7c-d)
- `.claude/agents/pwf-scribe.md` (C7e)
- `.claude/agents/graphify-researcher.md` (C7f)
- `.claude/agents/dockerfile-reviewer.md` (C12a, C12b, C13, C14)

Modify (codex agent TOMLs, sol only): `.codex/agents/codex-sol-{adversarial-critic,staleness-auditor,claude-code-expert}.toml`
— the `description` tail "use instead of X while Claude tokens are constrained" (C5, report's out-of-slice note).

Regenerate, never hand-edit: every `codex-astra-*` file in `.claude/agents/` and `.codex/agents/`, via
`mise run codex-lane-mirror` after the sol edits.

Do NOT touch any other file. In particular NOT `docs/secrets-doppler-fnox-keychain.md` (out of slice), not the report,
not `task_plan.md`/`findings.md`/`progress.md`.

## 3. Interfaces

Markdown agent files with YAML frontmatter; codex agent TOMLs validated by `schemas/codex-agent.json`. The hunks are
text replacements. Line numbers in the report are from 2026-09-24 and may have drifted: locate each hunk by its QUOTED
TEXT, not its line number. For C5 the new description tails are the report's C5a-c wording; for the TOMLs use the same
meaning in the TOML's own sentence shape ("… Runs on codex (gpt-5.6-sol), not Claude — the standing <role> lane;
<claude-agent> is the explicit Claude/Opus alternative.").

## 4. Constraints and invariants

- Apply ONLY C1–C15. C16–C27 are flag-only; make no edit for them.
- These strings must survive byte-identical wherever they occur (bound by `python/verification/suites.toml` and
  `python/src/dotfiles_setup/codex_agent_parity.py`): `PLANNING_DISABLED=1 mise exec -- codex exec`,
  `model_reasoning_effort=`, "Never substitute your own reasoning for a failed codex call", `claude-advisor`'s
  `model: fable` / `effort: xhigh`, `premise-verifier`'s `model: opus`, every `600000`, and every `model:`/`effort:`/
  `tools:` frontmatter line.
- Keep each file's meaning apart from the listed hunk. Do not reflow untouched paragraphs.
- The astra files are generated: edit sol, then run the mirror. `mise run codex-lane-mirror -- --check` must be clean.
- Where a hunk's quoted text is not found verbatim, STOP on that hunk and report it as licensed dissent (quote what
  you found instead); do not guess a substitute.
- Never pipe a gate into `head`/`tail`; redirect to a file and read the `rc=`. Never `--no-verify`. Do not commit.

## 5. Verification

Run all, each with a file-captured rc, and report every rc:
```
mise run codex-lane-mirror -- --check
mise run lint
uv run --project python pytest tests/ -x -q
mise run verify
mise run lint-docs
```
Plus, each must print 0 for `.claude/agents` and `.codex/agents`:
`grep -rlF 'Claude tokens are constrained'`, `grep -rlF 'All 50'`, `grep -rlF 'read line 8 of'`,
`grep -rlF 'caps a foreground Bash call at 600'`, `grep -rlF '2026-08-03 run'`, `grep -rlF '174 pages'`,
`grep -rlF 'masks digits'`.
Control arm for the greps: `grep -rlF 'codex-lane-mirror' .claude/agents .codex/agents python` must print >0.

## 6. Commit

`caller`. Leave the tree modified and unstaged; the architect reviews and commits.

## 7. PREMISES (read this session, 2026-09-28, on main 3ec04512; `.claude/agents` and `.codex/agents` unchanged through caee507d)

| # | Kind | Claim | Source |
|---|---|---|---|
| P1 | L | Every C1–C15 quoted string still exists in the named files (grep -F, per-file lists) | coordinator probe this session |
| P2 | L | `doctor.toml` `[fnox].env_true` has 56 entries | `tomllib` parse this session |
| P3 | L | `$CC` has 196 `.md` pages | `ls …/claude-code/*.md \| wc -l` this session |
| P4 | I | The mirror renders astra `.md` AND `.toml` from sol (`render_toml`) | `python/src/dotfiles_setup/codex_lane_mirror.py:35-36`, `:71` |
| P5 | L | `Claude tokens are constrained` appears in 6 `.codex/agents/*.toml` (3 sol + 3 astra) | grep this session |
| P6 | L | `600000` is absent from `codex-sol-implementer.md` and present in the other five sol wrappers | report C probe record; `grep` this session lists 10 files, implementer not among them |
| P7 | P | Bash default timeout 120 s; a timed-out call moves to background | `$CC/env-vars.md:185`, `$CC/agent-sdk__typescript.md:3423` (per report C) |
| P8 | A | The C5 routing rewording matches Ray's standing-lane doctrine | `.claude/CLAUDE.md` lane table (codex lanes are standing, not contingent) |
