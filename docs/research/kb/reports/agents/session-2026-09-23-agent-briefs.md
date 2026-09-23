# Agent briefs — session 2026-09-23 (`f643887b`), wayfinder map dotfiles#1293

Persisted per `.claude/rules/agent-report-persistence.md` / session-handoff §3c: the briefs
(the prompts handed TO each delegate), verbatim. Reports:
`codex-exec-review-settings-2026-09-23.md` (#1296) and `hk-2-0-impact-2026-09-23.md` (#1306).
Both delegates were `general-purpose` agents, `isolation: worktree`, background.

## Brief 1 — research ticket #1296 (branch `research/codex-exec-review-settings`)

````text
You are resolving research ticket #1296 ("Map every codex setting that governs exec review sandboxing and output") in ray-manaloto/dotfiles, part of wayfinder map #1293. Invoke the `mattpocock-skills:research` skill and follow it.

## Question
Which codex settings, environment variables, `.codex/config.toml` keys and CLI arguments bear on `codex exec review` sandboxing and output (`--commit`/`--base`, `-c review_model`, `-c sandbox_mode`, `--output-schema`, anything else)? `codex exec review` has NO `-s/--sandbox` flag, so read-only rests on config. Output: a cited matrix (setting | kind | effect on review sandbox/output | evidence file:line or URL | confidence) plus the exact candidate invocation(s) a later write-canary ticket (#1297) will test.

## Sources, in this order
1. agentsview history FIRST — prior research exists. Use the `agentsview-finding-history` skill.
2. Existing reports: `docs/research/kb/reports/agents/codex-entrypoint-design-2026-09-22.md` §5, `codex-0156-impact-2026-09-22.md`, `claudex-loop-full-research-2026-09-22.md`, `cx-research-cli-2026-09-10.md`.
3. `mise run codex-schema-generate` (the JSON schema for the installed codex) and `mise exec -- codex exec review --help`, `mise exec -- codex exec --help`. Record the installed codex version.
4. Offline vendor docs: `~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/` (grep it).
5. openai/codex source/changelog on GitHub only for gaps.

## Hard constraints
- READ-ONLY research. Do NOT run `codex exec` or `codex exec review` against the repo with prompts — the write-canary is ticket #1297, not yours. `--help` and schema generation are fine.
- Every probe states its control arm (`.claude/rules/probes-need-a-control-arm.md`); a 0-hit grep needs a known-present term run the same way.
- Persist INCREMENTALLY: create `docs/research/kb/reports/agents/codex-exec-review-settings-2026-09-23.md` early and update it as you go; save fetched raw sources to `.agent/kb/raw/<slug>.md`. End the report with a `## GitHub repos touched` section.
- You are in an isolated git worktree. Create branch `research/codex-exec-review-settings`, commit ONLY the report file on it (git add that one path; never `git add .`) with a message ending in:
  Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
  Do NOT push, open a PR, comment on or close issues, or edit any other file.
- Never print credential values.

## Final message
Return the full report verbatim, then: branch name, commit SHA, worktree path, and the one-paragraph answer to the Question.
````

## Brief 2 — research ticket #1306 (branch `research/hk-2-0-impact`)

````text
You are resolving research ticket #1306 ("What hk 2.0 changes for our hk configs and fmt doctrine") in ray-manaloto/dotfiles, part of wayfinder map #1293. Invoke the `mattpocock-skills:research` skill and follow it.

## Question
What does hk 2.0 (jdx/hk) break or change for: `hk.pkl`, `hk-common.pkl`, `hk-image.pkl` in dotfiles AND the hk config in `~/dev/github/ray-manaloto/knowledge-base`; the `mise run lint` / `mise run fmt` wrappers (`python/src/dotfiles_setup/lint.py`); and the "git add BEFORE `mise run fmt`" doctrine (root `AGENTS.md` § Tool management; `fix=true` can strand unstaged edits)? Output: a cited list of REQUIRED config/doctrine changes, removed/renamed features we rely on (e.g. pkl `amends` URL, builtins, `fix`/`check` semantics, stash behaviour, `depends`, pklr backend, `fail_fast`), and anything newly native that would let us retire custom code (per `.claude/rules/tool-currency-and-native-first.md`).

## Sources
- The currently pinned hk version (`mise.toml` / `.config/mise/conf.d/shared.toml`) vs the latest 2.x: the hk CHANGELOG, GitHub release notes for 2.0.0+, and the merged breaking-change PRs (docs lag code — CHANGELOG/PRs are authoritative). Follow `.claude/rules/research-doc-sources.md` (local mintlify cache → llms.txt → .md → ctx7).
- The Renovate hk v2 PR: `gh pr view 1090 -R ray-manaloto/dotfiles` (read-only).
- Our configs: grep them for every hk feature you flag, citing file:line.

## Hard constraints
- READ-ONLY research. Do not install hk 2.0, change pins, or run `mise run fmt`. `mise run lint` is not needed.
- Every probe states its control arm (`.claude/rules/probes-need-a-control-arm.md`); a 0-hit grep needs a known-present term run the same way.
- Persist INCREMENTALLY: create `docs/research/kb/reports/agents/hk-2-0-impact-2026-09-23.md` early and update it as you go; save fetched raw sources to `.agent/kb/raw/<slug>.md`. End with a `## GitHub repos touched` section.
- You are in an isolated git worktree. Create branch `research/hk-2-0-impact`, commit ONLY the report file (git add that one path; never `git add .`) with a message ending in:
  Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
  Do NOT push, open a PR, comment on or close issues, or edit any other file.

## Final message
Return the full report verbatim, then: branch name, commit SHA, worktree path, and a one-paragraph answer to the Question.
````

## Consumers (inbound pointers)

- #1296's report → consumed by the write-canary ticket dotfiles#1297 (arms A–G) and the step-0
  spec dotfiles#1310 (review doctrine must not promise `--output-schema`). No rule/skill consumer
  yet: deliberately orphaned from `.claude/rules/ai-cli-invocation.md` until #1297's canary
  measures it (a source-read claim is not a rule).
- #1306's report → consumed by dotfiles#1305 (Renovate grouping), dotfiles#1308 (plan-parity
  probe), and Phase 10 step 10. No rule/skill consumer until the hk 2 PR changes the fmt doctrine.

## GitHub repos touched

_None directly by this file (briefs only); the reports enumerate theirs._
