# KB children of dotfiles#1310 — verification (2026-09-28)

KB origin/main = d8a205da (fetched 2026-09-28, rc=0). All four issues state=OPEN.

Shared context: all four issues were delivered by **KB#811** (squash `330b03e6`, merged 2026-09-24T09:14Z, parent `e8fe42ae`), later touched by **KB#820** (`c7c121cc`, 2026-09-27; grok/plugin history clauses dropped). Live arms are in **dotfiles `docs/receipts/1319.md`** (on dotfiles origin/main; dotfiles#1319 CLOSED). `kb-land -- 811` is recorded in dotfiles `docs/research/kb/reports/agents/ship-session-results-2026-09-24.md:26` (run 1 rc=1, Greptile pending) and `:35` (run 2 **rc=0**, "no binding checks — nothing verified remotely"). All four KB issues have **0 comments** (`gh api repos/.../issues/<n> --jq .comments` → 0; control: KB PR #811 → 3 comments, dotfiles#1310 → 1), so no close comment was ever posted.

Probe note: `git grep -E '#793\b'` returns 0 on this host (BSD `\b` unsupported). Control: same file with `'#793'` → 1 hit. All later greps use `([^0-9]|$)`.

## KB#793 — Retarget the tool-review workflow to the repo's own reviewer, plus a workflow-roster test — DELIVERED

| criterion | evidence (command → result, file:line on origin/main) | met? |
|---|---|---|
| Retarget Review phase to `kb-codex-astra-reviewer`; rewrite comment block | `git grep -n agentType origin/main -- .claude/workflows/` → `kb-tool-review.js:197 { agentType: 'kb-codex-astra-reviewer', … phase: 'Review' }`; comment `kb-tool-review.js:8,12` cites knowledge-base#793 + the roster test. Pre-change `e8fe42ae:kb-tool-review.js:188` was `fable-orchestrator:codex-reviewer` | yes |
| Test FAILS on the pre-change workflow and PASSES after | Re-derived by me: ran `undeclared_agent_types()` from `origin/main:tests/test_workflow_agent_roster.py` over `git archive` trees → `e8fe42ae` (pre) = `['kb-tool-review.js: fable-orchestrator:codex-reviewer']`; `origin/main` = `[]`. Also recorded in the 330b03e6 commit body ("FAILED on the pre-change workflow (recorded), passes after") | yes |
| Fixtures: plugin-namespaced fails, undeclared fails, `general-purpose` passes | `tests/test_workflow_agent_roster.py`: `test_a_plugin_namespaced_agent_fails` (`fable-orchestrator:codex-reviewer`), `test_an_undeclared_agent_fails` (`ghost-reviewer`), `test_a_builtin_and_a_declared_agent_pass` (`general-purpose`, `kb-synthesist`). Receipt 1319.md:30: guard tests 8 passed rc 0 | yes |
| Live: a real tool-review run reaches Review, dispatching `kb-codex-astra-reviewer` | dotfiles `docs/receipts/1319.md:31` (explicitly "also KB#793's arm"): run `wf_9a05aaf2-5f5` on cclint, workflow `completed` 1455 s, Review 1 agent, codex lane rc 0 on gpt-6-astra read-only; report `.agent/kb/lanes/kb-tool-review-1319-r2/review-cclint/review.md` | yes |
| Gate matrix green; landed with `mise run kb-land` | 330b03e6 body: "kb-gates 11/11 PASS … lint-docs rc=0"; ship-session-results-2026-09-24.md:35 `kb-land -- 811` #2 rc=0 | yes |

Proposed close comment: "Delivered in #811 (`330b03e6`): kb-tool-review.js:197 dispatches `kb-codex-astra-reviewer`; tests/test_workflow_agent_roster.py fails on pre-change `e8fe42ae` and passes on main (fixtures: plugin-namespaced/undeclared fail, general-purpose passes); live Review-phase run `wf_9a05aaf2-5f5` recorded in dotfiles docs/receipts/1319.md:31; kb-land -- 811 rc=0."

## KB#795 — Add a stopgap kb-codex-implementer agent — PARTIAL (live arm waived by Ray, not run)

| criterion | evidence (command → result, file:line on origin/main) | met? |
|---|---|---|
| Agent file exists with retirement tag and names the codex runner | `git show origin/main:.claude/agents/kb-codex-implementer.md` → `:2 name: kb-codex-implementer`; `:3` "STOPGAP … Tagged for retirement"; `:9-13` "STOPGAP — RETIRE when … tracked as dotfiles#1383 … Added by knowledge-base#795"; runner named `:32-33` (`mise.toml [tasks.kb-codex]`, `kb_setup.codex_run`) and launched `:39` `mise run kb-codex -- --write`. Codex twin `.codex/agents/kb-codex-implementer.toml:1-9` carries the same tag. Pointer updated to #1383 by KB#815 (MERGED 2026-09-26) | yes |
| Live: one real dispatch of a trivial, gate-checked task reports the runner's real exit code | **Not run.** dotfiles `docs/receipts/1319.md:33`: "`kb-codex-implementer` stopgap (optional) — not run — Ray, 2026-09-27 (AskUserQuestion): the stopgap is retired by #1383, so a live run would prove a lane scheduled for deletion". Also `removal-review-spec-2026-09-24.md:9` ("the `kb-codex-implementer` dispatch [was] not run"). Wider search: `git grep -n -F kb-codex-implementer origin/main -- docs \| grep -iE 'live\|dispatch\|spawn\|rc'` → only not-run/owed lines (1319.md:7,33; removal-session-2026-09-24.md:263 lists it as OWED). Control: same `git grep -l -F` shape for `claude-advisor` → 19 files. KB local `ls .agent/kb/lanes/*impl*` → no match; control: same dir lists `kb-tool-review-1319-r2` | **no (waived)** |
| Gate matrix green; landed with `mise run kb-land` | 330b03e6 body: kb-gates PASS (#793-#796 commit); ship-session-results-2026-09-24.md:35 `kb-land -- 811` rc=0 | yes |

Gap: the live-dispatch criterion was never met. Ray waived it 2026-09-27 because dotfiles#1383 (OPEN) retires the stopgap. Proposed close comment: "Agent + codex twin shipped in #811 (`330b03e6`) with the retirement tag pointing at dotfiles#1383 (KB#815); kb-land -- 811 rc=0. The live-dispatch criterion was deliberately NOT run: Ray waived it 2026-09-27 (dotfiles docs/receipts/1319.md:33) because #1383 deletes this lane. Closing as delivered-with-waiver." Alternative: leave it open and let #1383 supersede it.

## KB#796 — Rename kb-advisor to claude-advisor, port premise-verifier, add the new trigger line — DELIVERED

| criterion | evidence (command → result, file:line on origin/main) | met? |
|---|---|---|
| No live instruction surface references `kb-advisor`; `claude-advisor` exists; `premise-verifier` exists | `git grep -n -F kb-advisor origin/main -- CLAUDE.md AGENTS.md .claude .codex .agents mise.toml hk.pkl python tests` → 0 hits, rc=1. Control: `claude-advisor` over the same paths → 7 files. Repo-wide (excl. `sources/`) hits are only dated records: `docs/artifacts/*.html`, `docs/goals/2026-08-27-*`, `docs/research/reports/2026-08-*`, and `docs/research/README.md:76` (an index row describing a 2026-08-06 report). Files: `.claude/agents/claude-advisor.md` (`:2 name`, `:4 model: fable`, `:5 effort: xhigh`, `:18` no memory, `:27-33` kb-query + wiki grounding, `:57` Opus fallback), `.claude/agents/premise-verifier.md` (`:2`, MIT port header), `.codex/agents/premise-verifier.toml`. `kb-advisor.md/.toml` deleted by #811 (file list) | yes |
| New trigger line byte-identical to dotfiles' | dotfiles `origin/main:.claude/CLAUDE.md:45` vs KB `origin/main:.claude/CLAUDE.md:31`, whitespace-normalised → `cmp` rc=0. Fail arm: same compare with `ANY`→`SOME` → `cmp` rc=1. It is also the sole `lines` entry in dotfiles `rule-sync.toml:38-40`, and `mise run rule-sync` rc=0 across both repos (1319.md:26, 2026-09-26) | yes |
| Advisors line: consult-before-dispatch kept; lists kb-codex-advisor (default), kb-codex-astra-advisor, claude-advisor; drops `fable-advisor` | KB `.claude/CLAUDE.md:32`: "**Always consult an advisor before any codex implementer dispatch** … **Three** advisors are live: `kb-codex-advisor` … DEFAULT …; `kb-codex-astra-advisor` …; plus `claude-advisor` (Fable, escalation-only …)". `git grep -F fable-advisor … CLAUDE.md .claude .codex .agents` → 0 (rc=1); control `claude-advisor` → hits above | yes |
| orchestrator-routing skill + `.agents` mirror: no grok / plugin names | `git grep -n -iE 'grok\|fable-orchestrator\|fable-advisor' origin/main -- .claude/skills/orchestrator-routing .agents/skills/orchestrator-routing` → 0 (rc=1). Control `codex` over the same paths → 10 hits in each SKILL.md. Grok removed by KB#820 | yes |
| Live: one spawn each of `claude-advisor` and `premise-verifier` in KB returns a verdict | dotfiles `docs/receipts/1319.md:23` KB premise-verifier returned 2 CONFIRMED / 1 REFUTED (planted control refuted), transcript `…/b3a5b5da-…/subagents/agent-a8d386ef8146c95f4.jsonl`; `:24` KB claude-advisor returned AGREE (close KB#794), `agent-ad9f39535ec66de0f.jsonl`; report `docs/research/kb/reports/agents/1319-live-arm-knowledge-base-2026-09-25.md` | yes |
| Gate matrix green; landed with `mise run kb-land` | 330b03e6 body (#793-#796 commit): kb-gates PASS, `mise run test` rc=0, lint-docs rc=0; ship-session-results-2026-09-24.md:35 `kb-land -- 811` rc=0 | yes |

Proposed close comment: "Delivered in #811 (`330b03e6`), grok residue removed in #820: claude-advisor (fable/xhigh, escalation-only, no memory, Opus fallback, kb-query grounding) and premise-verifier exist, and kb-advisor is gone from every live surface. The trigger line is byte-identical to dotfiles `.claude/CLAUDE.md:45` (rule-sync rc=0). The live spawns of both agents returned verdicts (dotfiles docs/receipts/1319.md:23-24). kb-land -- 811 rc=0."

## KB#797 — Remove fable-orchestrator from knowledge-base — DELIVERED

| criterion | evidence (command → result, file:line on origin/main) | met? |
|---|---|---|
| Forbid contract equivalent to dotfiles `no-plugin-references` | `tests/test_no_plugin_references.py`: `FORBIDDEN = ("fable-orchestrator:", "fable-orchestrator@")` (`:23`) over 9 surface globs (`:25-35`), plus `test_every_surface_glob_matches_something` (`:52-55`) against a glob that scans nothing | yes |
| Forbid passes, and FAILS on a reintroduced reference (arm run + recorded) | Recorded: 330b03e6 body says "FAILS with a reference planted in the real .claude/agents/claude-advisor.md (armed, restored)"; in-test FAIL arm `:62-73`, clean control `:76-81`. **Re-derived by me:** ran `plugin_references()` over `git archive` trees → pre-change `e8fe42ae` = **17 hits** (e.g. `.claude/CLAUDE.md:31-34,45,47,51`, `.claude/settings.json:195: fable-orchestrator@`); `origin/main` = **0**; empty globs on main = `[]`. Receipt 1319.md:30: guard tests 8 passed, rc 0 | yes |
| Live-path grep for `fable-orchestrator:` = 0, with a known-present control | `git grep -l -F 'fable-orchestrator:' origin/main -- .claude .codex .agents python tests mise.toml hk.pkl CLAUDE.md` → 3 files, all tests: `test_no_plugin_references.py` (guard fixture), `test_workflow_agent_roster.py` (the #793 guard fixture), `test_brain.py:239,292` (brain tests, which the spec says to KEEP). **0 on every non-test live surface.** Control `kb-codex-implementer`, same scope → 8 files. Matches receipt 1319.md:30 | yes (0 outside the guard/brain fixtures the spec keeps) |
| Eval doctor shell-out, its case entry and mise wiring removed | `git grep -nE 'doctor_health\|lane-health\|DOCTOR_SCRIPT\|doctor\.sh' origin/main -- python tests mise.toml hk.pkl .claude` → only `tests/test_eval_cases.py:157` (a docstring noting the removal) and an unrelated `session-resume/SKILL.md:141 plan-doctor.sh`. Control, same grep at `e8fe42ae` → hits in mise.toml (1), eval_cases.py (9), evals.py (6), test_eval_cases.py (3), test_evals.py (7) | yes |
| Plugin enablement + marketplace keys removed from settings | `git show origin/main:.claude/settings.json \| grep -ni fable` → 0 (rc=1); control: same file has `enabledPlugins` (1). Pre-change `settings.json:195` had `fable-orchestrator@` | yes |
| Old trigger lines removed from Claude project config | `grep -cE '^- fable-orchestrator:'` → origin/main 0; control at `e8fe42ae` → 3 (pre `:32-34`, plus the old trigger at `:31`) | yes |
| Stale docstrings (review, codex runner, in-place edit) + ai-cli-invocation rule corrected | Remaining bare mentions are all past-tense provenance: `review.py:301,444` ("since-removed"), `codex_run.py:140` ("former"), `inplace_edit.py:30` (who proposed the guard), `.claude/rules/ai-cli-invocation.md:70` ("since-removed"), `mise.toml:172` ("was removed, dotfiles#1310") | yes |
| KEEP research corpus clone, registry entry, golden set, brain tests | `sources/fable-orchestrator.manifest` tracked; clone dir exists on disk, gitignored (`.gitignore:176 sources/*/`); `sources/REGISTRY.md:35` row #9; golden-set targets `eval_cases.py:318,326` (`fable-orchestrator.md`); `tests/test_brain.py:239,292`. (A first `ls-tree -d … \| grep fable` probe returned 0 because it was bounded to directories, and the clone dirs are untracked. Control `agent-harness` in the same listing → 1) | yes |
| dotfiles `mise run rule-sync` stays green after merge | 1319.md:26 (2026-09-26) rc=0. **Re-run by me 2026-09-28:** `mise run rule-sync` → `OK rule-sync: 1 plugin(s) + 1 line(s) + 22 rule(s) + 2 agent(s) hold`, **rc=0**, KB checkout at `d8a205da` = origin/main. The dotfiles checkout was `6c9576f0` (origin/main `9650c926`), but `git diff --stat` over rule-sync.toml, rule_sync.py and .claude/CLAUDE.md between them is empty (control: the full range changes 3 files). A first attempt through the `timeout` shim failed at rc=1 with "No version is set for shim: timeout", a broken shim and not a rule-sync result | yes |
| Gate matrix green; landed with `mise run kb-land` | 330b03e6 body (#797 commit): "kb-gates 11/11 PASS … lint-docs rc=0; dotfiles `mise run rule-sync` against this tree rc=0"; ship-session-results-2026-09-24.md:35 `kb-land -- 811` rc=0 | yes |

Proposed close comment: "Delivered in #811 (`330b03e6`). tests/test_no_plugin_references.py finds 17 hits on the pre-change tree `e8fe42ae` and 0 on main (FAIL arm recorded in the commit and in-test). The live-path grep has no hits outside the guard/brain test fixtures; control kb-codex-implementer → 8 files. Eval doctor, settings keys and old trigger lines are gone. Records are kept (manifest, REGISTRY.md:35, golden set, brain tests). dotfiles rule-sync rc=0 (re-run 2026-09-28 against KB d8a205da); kb-land -- 811 rc=0."

## Summary

| issue | verdict | gap |
|---|---|---|
| KB#793 | DELIVERED | — |
| KB#795 | PARTIAL | the live-dispatch criterion was never run; Ray waived it 2026-09-27 (dotfiles docs/receipts/1319.md:33) because dotfiles#1383 (OPEN) retires the stopgap |
| KB#796 | DELIVERED | — |
| KB#797 | DELIVERED | — |

Caveats: (1) the "landed with `mise run kb-land`" evidence is `kb-land -- 811` rc=0, which itself printed "no binding checks — nothing verified remotely" (ship-session-results-2026-09-24.md:35). (2) The "gate matrix green" evidence is the commit-body record, which I did not re-run. (3) All four issues are still OPEN with 0 comments.

## GitHub repos touched

- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — issues #793/#795/#796/#797, PRs #811/#815/#820, origin/main tree `d8a205da` and pre-change `e8fe42ae`
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — issues #1310/#1319/#1383, `docs/receipts/1319.md`, `rule-sync.toml`, `.claude/CLAUDE.md`, the ship-session-results/removal-review reports, `mise run rule-sync`

## Coordinator disposition (2026-09-28)

- KB#793, #796, #797 closed 05:30Z with comments derived from the proposed texts; KB#795 closed 05:30:48Z as delivered-with-waiver (Ray, 2026-09-28), not left for #1383. Each issue now has 1 comment. The report's "state=OPEN"/"0 comments" lines are as of its fetch, before the closes.
- Spot-checked by the coordinator with control arms: `kb-advisor` over the live surfaces → 0 files vs `claude-advisor` → 7; `kb-tool-review.js:197` dispatches `kb-codex-astra-reviewer`.
