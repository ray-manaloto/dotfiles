# Removal review: spec axis (2026-09-24)

Scope: dotfiles `3db81d8e...HEAD` (9ed414a0, 2c8cc745, d4b0b5c4), and knowledge-base `origin/main...HEAD` (76f95cfa, d94b0e82). Measured against the spec #1310, tickets #1311-#1319 and KB#793-#797, and the #1294 resolution. The live arms of #1319 are excluded, as the brief says.

## (a) Missing or partial

1. **KB#794**: *"A review invoked with no lane uses `cold:codex-astra` (asserted at the review CLI/function seam)"* and *"An old receipt carrying a legacy lane spelling still parses … (a test with a real historical spelling)"*. Neither exists. In `kb_setup/review.py:296-303` and `:437-440` only docstrings changed. `cli.py:831-834` still requires `--lanes` (so there is no default), and its example still reads `cold:codex`. The KB diff adds no review test. The "default" moved only in the skill prose.
2. **#1315**: *"An Opus cold review and a `premise-verifier` pass over the doctrine diff, with findings dispositioned and persisted."* No such report exists. `fable-orchestrator-removal-session-2026-09-24.md` records no doctrine review; its "Code review" section reads `_(pending)_`.
3. **#1314 / #796 / KB#795 live arms**: the `claude-advisor` and `premise-verifier` spawns, and the `kb-codex-implementer` dispatch, were not run. These are separate from the #1319 exclusion, because they are each ticket's own acceptance criteria.
4. **Story 18** (*"no contract asserts the old world"*): the description of `orchestration.codex-only-lanes` (`suites.toml:2405`) still cites *"`orchestration.mode-line-declared` above"*, which was deleted. It also still cites *"the plugin skill's review-tier table"*.

## (b) Not asked for

1. `CLAUDE.md` adds a lane row that runs `codex exec … review --commit` (`.claude/CLAUDE.md` lane table), and the doctrine names the same argv (`codex-sdlc-team/SKILL.md` review tiers). The spec puts *"The `codex exec review` MECHANISM"* out of scope. It is only doctrine, but it pins a concrete command that is waiting on #1297.
2. KB adds codex twins that no ticket asks for: `.codex/agents/premise-verifier.toml` and `.codex/agents/kb-codex-implementer.toml`. They are probably required by KB's `lane_recording` convention, but no justification is recorded.
3. `premise-verifier.md` adds `effort: xhigh`, and the spec says only *"Opus, Read/Grep/Glob"*. The header claims *"the upstream text, unedited"*, yet 2c8cc745 removes a body line.
4. `removed_plugins._claude_state_findings` flags an install under ANY `projectPath` on the machine. #1317 scopes it to *"either project's plugin state"*.

## (c) Present, but looks wrong

1. **Story 6** (*"three escalation triggers … stated in ONE place"*): KB states the triggers three times, in the `claude-advisor.md` description, in its body (`:72-74`), and in `.claude/CLAUDE.md:17`. KB has no `token-routing.md`-style single source.
2. **`owned-agents`** pins `model: fable` and `model: opus` as substrings (`suites.toml` owned-agents). A value such as `model: opus-4` would still pass. The spec asks that *"changing its pinned model FAILS"* the contract.
3. **The dotfiles roster regex** matches only single-quoted `agentType` (`test_workflows_js.py:21`), so a double-quoted dispatch escapes #1313. The KB regex handles both quote styles.

What checks out: #1311, #1312, #1313 (apart from c3), the #1316 contract set with `path_globs`, and the #1317 fixtures for both names, including the disabled claudex-loop. The commit order matches the PR sequence.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): spec #1310, tickets #1311-#1319, #1294, and the diff
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): tickets #793-#797 and the diff
