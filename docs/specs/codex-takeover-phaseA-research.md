# Spec — codex-takeover Phase A: cited research + design (2026-10-05)

Parent record (READ FIRST): `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/.claude/worktrees/codex-takeover/docs/specs/codex-takeover-2026-10-05.md`.
Its "Ratified scope" table defines W0–W5. Issues: #1715 (W0) … #1720 (W5); umbrella #1721.
Phase A produces EVIDENCE and a DESIGN. It writes no production code. Phase B (implementation) is
specified by the architect from this output.

## 1. Objective

Produce a cited research report and a concrete design that let the architect write the Phase B
implementation spec without re-deriving anything. The failure this prevents: building takeover
machinery on unverified harness assumptions.

Answer each of the following.

- **W0.** Which wins for this repo, with evidence:
  - (a) zero CLAUDE.md files + the agents-md mod (`instructionFiles` = `claude-md-or-agents-md` or `claude-md-and-agents-md`);
  - (b) keep the root `CLAUDE.md` = `@AGENTS.md` stub.

  Include:
  - the mod's shipping status (built-in in which CC version? `agents-md@builtin` present in 2.1.289?);
  - known bugs and limits from anthropics/claude-code issues/PRs/discussions;
  - how openai/codex discovers AGENTS.md (hierarchy, size limit `project_doc_max_bytes`, fallback filenames) from its source/docs and issues;
  - the impact on the `claude_md_import_stub` and `claude_agents_md_pairs` gates, `rule-sync.toml`, and knowledge-base.
- **W5a.** The cheapest way to make `.claude/rules/*.md`, `.claude/CLAUDE.md` and the Claude skills visible to codex, within the 12,000-char AGENTS.md cap. Candidates: codex `project_doc_fallback_filenames`, nested AGENTS.md, an index with links, `.codex/skills` mirrors, codex config `instructions`/`developer_instructions`. Cite codex docs and source.
- **W1/W4/W5b design.** Module/task/data shapes for:
  - `session_registry` + `mise run lane-cards`;
  - `mise run takeover-check` and its launchd plist (15 min);
  - self-heal guardrails: no live Claude coordinator, launch lock, ≤1 codex coordinator, logged to the inbox;
  - a codex coordinator runbook (ship queue, SLOT GO, land).

  Reuse first: read `python/src/dotfiles_setup/coordinator_handoff.py`, `.claude/skills/coordinator-handoff/SKILL.md`, the watcher session `dotfiles-20261004T2100.watch` files under `.agent/plans/handoff-inbox/watch.md`, and `.agent/plans/main-checkout-ship-queue.md` (main checkout `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles`).
- **W3 design.** The digest miner. What `mise run command-audit` and `mise run session-review` already extract, and the minimal extension to cover `~/.codex/sessions/**` rollouts since 2026-10-02. Name its control arm.

## 2. Files (the ONLY paths you may create or modify)

- `docs/research/kb/reports/agents/codex-takeover-phaseA-2026-10-05.md` — the report. Create it EARLY and update it incrementally. End it with `## GitHub repos touched`.
- `docs/research/saved-searches/codex-takeover-2026-10-05.toml` — via `mise run research-saved-search` ONLY (read `python/src/dotfiles_setup/saved_searches.py` for its CLI). Never hand-written.
- `docs/research/kb/raw/codex-takeover/**` — raw sources and mirrors. The agents-md mod is already mirrored at `links/agents-md/`. Add firecrawl mirrors via `mise exec -- firecrawl scrape <url> --format markdown --only-main-content`.
- `docs/specs/codex-takeover-phaseB-design.md` — the design (interfaces, data shapes, file list, verification per W).

## 3. Interfaces

- Session inventory source: `claude agents --json --all` returns a JSON array. Each row has keys
  `cwd, id, kind, name, sessionId, startedAt, state`, where `state` is one of
  `working|blocked|stopped|done` (probed 2026-10-05 07:00).
- GitHub search: `gh api -X GET search/code` / `gh api '/search/issues?q=repo:o/r+term'`.
  NEVER `gh search issues --repo`: it returns 0 silently.

## 4. Constraints and invariants

- Research coverage minimum (Ray, verbatim): "search github repos issues/prs/discussions" and "github searches that can be saved and tuned and re-run for updates". Every search goes through `mise run research-saved-search`.
- Every 0-result search carries a control arm: a must-hit term plus a FRESH known-absent term (`.claude/rules/probes-need-a-control-arm.md`).
- Read-only toward everything outside §2:
  - no edits to `AGENTS.md`, `CLAUDE.md`, `.claude/**`, `python/**`, `mise.toml`;
  - no user-level files (`~/.claude/*`, `~/.codex/*`, `~/Library/LaunchAgents`);
  - no issue filing, no git push, no `gh pr` commands.
- Never `--ephemeral`.
- Do not print secret values.
- Cite every claim with a URL or `path:line` read in THIS run. Label anything unverified `A` (assumption).
- Do not duplicate these lanes; cite them as dependencies instead:
  - process-hardening (`docs/specs/process-hardening/`, guard parity for codex);
  - credit-fallback-finish (#1577, research-gate Stop-hook hijack);
  - handoff-automation-research (research 703e5612).

## 5. Verification

- The report exists, has a `## GitHub repos touched` section, and every W has a verdict or design row.
- `mise run research-saved-search` re-runs the saved file cleanly. Record the rc in the report.
- `mise run lint-docs` rc=0 (file-captured rc).

## 6. Commit

`lane`: commit only the §2 paths on `feat/codex-takeover`, with message
`docs(research): codex-takeover phase A research + design (#1721)`. Do not push.

## 7. PREMISES

| # | Kind | Claim | Source |
|---|---|---|---|
| 1 | L | Mod option `instructionFiles`, default `claude-md-or-agents-md`, four values | `docs/research/kb/raw/codex-takeover/links/agents-md/.claude-plugin/plugin.json` (userConfig) |
| 2 | L | Plugin options are read from user/`--settings`/managed settings only, not the project's | `…/links/agents-md/README.md` "Setting the option" |
| 3 | L | Default mode stands down when any `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` exists on the walk | `…/links/agents-md/README.md` first bullet list; `hooks/names/claude-names.ts` |
| 4 | L | Mod reads `AGENTS.md` and `.claude/AGENTS.md` | `…/links/agents-md/hooks/names/agents-names.ts` |
| 5 | L | AGENTS.md = 11,978 bytes, `.claude/CLAUDE.md` = 5,724 bytes | `wc -c`, 2026-10-05 06:58 |
| 6 | L | Installed CC 2.1.289, no `agents-md` in `claude plugin list` | probed 06:53 |
| 7 | L | `research-saved-search` task → `dotfiles_setup.saved_searches` (#1502) | `mise.toml:926-929` |
| 8 | I | `claude agents --json --all` row keys | probed 07:00 |
| 9 | A | Codex does not read `.claude/**` | to be VERIFIED from openai/codex source in W5a |
