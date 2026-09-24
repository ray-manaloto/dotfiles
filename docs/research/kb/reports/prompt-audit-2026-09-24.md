# Prompt audit — 2026-09-24 (consolidated)

`/claude-api prompt-audit` over this repo's whole Claude-facing prompt surface.
Four parallel auditor lanes. Their verbatim reports are the detail; this file is
the index and the cross-cutting read.

| Slice | Verbatim report | Findings | Edits proposed |
|---|---|---|---|
| A — always-loaded rules + `AGENTS.md` files (~163 KB) | `agents/prompt-audit-A-eager-2026-09-24.md` | 45 | 40 hunks |
| B — repo-authored skills (~180 KB) | `agents/prompt-audit-B-skills-2026-09-24.md` | 51 | 75 hunks + 3 skill deletions |
| C — subagent roster `.claude/agents/` (~270 KB) | `agents/prompt-audit-C-agents-2026-09-24.md` | 27 | 15 edits (abbreviated; apply per file) |
| D — runtime-injected text (hooks, workflows) + vendored skills | `agents/prompt-audit-D-runtime-2026-09-24.md` | 12 | 5 hunks |

## Assumptions (Step 0)

- **Target model:** Claude Opus 5.5, the session default. Agents pinned to `sonnet`, `haiku` or `fable` were audited against Sonnet 5, Haiku 4.5 or Fable 5.1.
- **Out of scope:**
  - The repo makes no Anthropic API calls, so the Group 4 request-config checks (thinking, `budget_tokens`, prefill, sampling) have nothing to inspect.
  - `.codex/agents/*.toml` prompts target GPT models.
  - The vendored `graphify`, `context7-cli` and `find-docs` skills get findings only. A local edit would be overwritten on the next re-vendor.

## Headline: the classic dated patterns are absent

- None of these appear anywhere on the surface: "think step by step", scratchpad tags, prefill, word caps in rules, or "be thorough / don't be lazy".
- All-caps pressure words are rare: 28 lines repo-wide.
- The control arm (`mise run`) returned 366 hits on the same corpus, so the zeros are real.

The debt is of a different kind: **prompt text that contradicts enforcement or other prompt text**, and **stale specifics and history in always-loaded or high-traffic files**.

## Cross-cutting themes, by impact

1. **Instructions that tell Opus 5.5 to do what the repo forbids.** A model that follows the nearest, most specific instruction literally will obey these.
   - `gh pr checks --watch` and `gh run watch` are taught as canonical in `gh-cli-watch.md`, `verify-before-advancing.md`, `long-running-command-hangs.md` and `.github/workflows/AGENTS.md`. `hook_guard.py:557-568` denies both. [A: F-A16]
   - `pr-workflow` prescribes an unbounded `until … sleep 60` poll. The guard does not catch that shape, because the loop condition is a `$(…)` compare. [B-10]
   - The `devcontainer-workflow` task menu lists `mise run build` and `hk run pre-commit`. `ci-warning-investigator` bakes `dev-load` locally. The `git-branch-commit-push-workflow` skill teaches `gh pr create`, which the guard denies. [B-26, B-40, B-25]
   - The `ask_quality` deny says "do NOT fall back to prose", while `clarify-before-acting.md` says to use prose when the tool is "denied". [D2]
   - Contradictions between rules:
     - "REAPED background work" in `long-running-command-hangs.md` versus the harness docs, a measured `land` and `mise-tasks-only.md`. [F-A7]
     - The "every schema, forever" cost is repeated by `do-not.md` #11 and the `mcp2cli`/`mintlify` skills, but `research-doc-sources.md` declares it false. [F-A24, B-19]
2. **The graphify PreToolUse nudge.** "MANDATORY … You MUST run" fires on every search or read call with no dedup.
   - It names bare `graphify explain`/`path`, which `graphify-first.md` forbids.
   - Transcripts show it ignored: 202 injections, 0 queries in one session.
   - Proposed fix: factual wording plus once-per-session delivery. [D1a/D1b]
3. **Stale volatile facts.**
   - `graphify-operator` reads counts from the wrong `GRAPH_REPORT.md` line.
   - `codex-sol-implementer` assumes a 600 s Bash default; the real default is 120 s. This is #1155.
   - "All 50 secrets" appears in 9 agents and the secrets rule; the real count is 56.
   - `session-review` says "reads Codex and Codex", a mirror corruption that leaked into the source file.
   - `chezmoi-check` documents the removed `is_ephemeral`.
   - `tool-currency-check`'s hk grep can only return nothing.
   - The "200/200 lines", "20 shared tools", "3,116 tests" and "~38GB" figures are all stale. [C1-C3, B-30, B-39, B-31, F-A1/14/17/21]
4. **History in always-loaded rules and routing descriptions.**
   - Always-loaded rules carry dated incident narratives, "REVERSED"/"no longer"/"was once" phrasing, and retired-rule tombstones.
   - Six skill descriptions end in incident tails that ride in every skill listing.
   - Agents retell the 2026-08-03 run inside their protocols.
   - Where the evidence sibling does not already hold the text, the proposal moves it to `docs/rules-evidence/`. [F-A6/8/27/28/…, B-33, C15]
5. **Output-shaping fossils.**
   - Six agents cap their summaries at N words or lines.
   - Three codex lane descriptions still say they are a substitute "while Claude tokens are constrained".
   - `research-with-verification-gap-fill` is a five-month-old draft that depends on a disabled plugin, uses haiku/sonnet/opus routing and has a hard word cap. [C7, C5, B-34]

## Roster (Group 4)

- **Agents: no redundant specialists.** The Claude/codex pairs are the deliberate cross-family design.
- **Skills:** `handoff` and `session-handoff` are not duplicates, nor are `resume` and `session-resume`: one of each pair writes tracked handoffs that go to another surface, the other gitignored ones for the same clone. Three skills are proposed for deletion:
  - `git-branch-commit-push-workflow`: GitButler-era, teaches a denied command.
  - `uv-project-vs-directory-expertise`: duplicates `AGENTS.md` and adds a retired cache-clearing step.
  - `tmux-extended-keys`: superseded by `$CC/terminal-config.md`, and it prescribes host `chezmoi apply`.
- **Workflows:** three `agent()` calls do deterministic work (gate-runner, graphify-operator, the modernization-audit loader). They should become caller-side mise tasks. [D10]
- **Token accounting:** nothing measures hook-injected text per session. Adding that is the prerequisite for measuring any of these removals. [D11]

## Validated patch (Step 7)

`.agent/kb/structured/prompt-audit-2026-09-24.patch` is gitignored and machine-local. It holds A + B + D hunks 3-5, the three skill deletions, and the regenerated `.agents/` mirror: 77 files, +627/−1979. It applies to `docs/prompt-audit-2026-09-24` at `1c4977eb` (`git apply --check` rc=0).

I applied it in a scratch worktree and ran the gates there:

| Gate | Result |
|---|---|
| `uv run --project python pytest tests/ -q` | rc=0, 3781 passed, 2 skipped, 11 deselected |
| `dotfiles-setup verify run` | rc=0, 165 passed, 0 failed, 4 skipped |
| `mise run lint` | rc=0 |

The gates caught four defects in the auditors' proposals. They are fixed in the patch but not in the verbatim reports:

1. **F-A3 is withdrawn.** The grok text is load-bearing: eval `tier1.lanes-declared-or-degraded` requires `.claude/CLAUDE.md` to declare grok "NOT installed". Removing it failed 3 tests in `tests/test_eval_cases.py`.
2. **F-A2 was reworded.** "(it must fire on any session model)" tripped agnix's middle-zone "must" warning, which hk treats as an error. It now reads "(it fires on any session model)".
3. **B-37 was reworded.** It cited `schemas/codex_app_server_protocol.version`, a gitignored local file, and `test_doc_refs` failed on it.
4. **B-25, B-36 and B-42 needed extra deletions.** `skills-mirror` does not prune deleted skills, so each deletion also needs `git rm -r .agents/skills/<name>`.

Not in the validated patch: the C hunks (subagent prompts) and D hunks 1-2 (`graphify.py`).

## Proposed diff — status

- **A:** the combined patch applies cleanly (`git apply --check` rc=0).
- **B:** all 75 hunks apply; the 3 deletions are `git rm -r` followed by `mise run skills-mirror`.
- **B-30:** also needs a `PER_FILE["session-review"]` reversion in `skills_mirror.py`, or `skills_mirror_parity` fails.
- **D:** hunks 3-5 (`ask_quality.py`, `mise_config_context.py`, `settings.json`) apply. Hunks 1-2 (`graphify.py`) have malformed hunk headers and must be regenerated from the auditor's verified scratch code before applying.
- **C:** hunks are written with one line standing for several files, so apply them per file. Follow them with `mise run codex-lane-mirror`.
- **Required follow-ups inside the diff:**
  - F-A3 also edits `suites.toml:2412` and `tests/test_verify.py:181`.
  - Hunk 5 needs `mise run rule-sync` and `mise run plugin-health` afterwards.

Applied and shipped on branch `docs/prompt-audit-2026-09-24` (the validated patch plus these reports).

## Out-of-slice items surfaced

- The `hook_guard._is_wait_condition` guard misses `[ "$(cmd)" = X ]` loop conditions. [B-10]
- Two memories are refuted by live probes:
  - `feedback_gh_search_issues_repo_flag_broken`: the flag works now. [B-40]
  - `feedback_mintlify_cache_stale`: the URLs return 200, not 410. [B-23]
- `.codex/agents/*.toml` still carry "while Claude tokens are constrained". [C5]
- `home/dot_tmux.conf.tmpl` lacks the `extended-keys` lines that `$CC/terminal-config.md` documents. [B-42]
- `codex-sdlc-team.md` says omitting `-` makes codex hang, while `ai-cli-invocation.md` says it reads stdin. [C26]
- Subagents cannot use the Write tool in this harness ("Subagents should return findings as text"). All four lanes fell back to Bash appends, so the incremental-persistence contract depends on Bash.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — the audited surface.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — offline Claude Code docs (`$CC/`).
- [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) — nudge text owner; vendored skill.
- [upstash/context7](https://github.com/upstash/context7) — vendored `find-docs`/`context7-cli`.
- [OthmanAdi/planning-with-files](https://github.com/OthmanAdi/planning-with-files) — plugin hooks (installed cache).
- [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) — output-style plugin payloads (installed cache).
- [openai/codex-plugin-cc](https://github.com/openai/codex-plugin-cc) — codex plugin Stop hook (installed cache).
