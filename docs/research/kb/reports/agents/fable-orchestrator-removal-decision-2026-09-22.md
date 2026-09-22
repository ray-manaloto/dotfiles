# Fable decision — remove fable-orchestrator from both repos (2026-09-22)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> `fable-orchestrator:fable-advisor` final message. Ray deferred this decision to a
> Fable model ("decide as it dictates"). Inputs: fable-orchestrator-removal-history,
> fable-orchestrator-dependency-audit, feature-matrix-final-2026-09-21, the
> codex-sdlc-team skill + sdlc_team.py, task_plan.md Phase 9/10. Harness banner on
> receipt: "settings-json" instruction-shaped pattern (relayed, not acted on).

**Lane limits.** Read-only, no Bash: I could not run `mise run graphify-query` (both input reports measured the graph `stale`, rc=3) and wrote nothing to `findings.md`/`progress.md`. Persist this verbatim.

## 1. DECISION: remove — yes. Replacement = in-repo skill/agents per repo, NOT a packaged plugin.

Reasons, in order of weight:
- **A plugin is the failure mode we are leaving.** The only running copy is `~/.claude/plugins/cache/…/1.21.0`; KB `evals.py:512` already admits it "can vanish on GC"; `extraKnownMarketplaces` points at a 404 (`settings.json:225-228`, KB `:224-227`). **Phase 10 line 391's "vendored" is false for dotfiles**: a glob for `**/fable-orchestrator/**/plugin.json` returns 0 in dotfiles; KB has only the untracked research corpus at `sources/fable-orchestrator/` (a clone per its manifest, not an install). A homegrown plugin — local dir or marketplace — recreates a second distribution/version/reinstall path outside the gates (`md_size_budget` exempts vendored plugin content; `hook_selfcheck` covers settings hooks, not a plugin's `hooks.json`; `codex-agent-validate` covers `.codex/agents`).
- **There is nothing to package.** Matrix §5: #1202 used zero plugin agents and the premise hook was measured dark for our lanes (`premise-gate.sh:132-133` matches only `codex-implementer`/`grok-implementer`). The plugin's live contribution is 178 lines of doctrine text plus two Claude-side agent files (`premise-verifier.md` 75 lines, `fable-advisor.md` 29 lines, MIT).
- **The cross-repo mechanism already exists**: `rule_sync.py:133-163` gates plugins/lines/rule-stems across both repos. Use it; do not add a distribution channel.

Form: dotfiles doctrine lives in `codex-sdlc-team/SKILL.md` (Ray's single entry point, `task_plan.md:294-299`); KB doctrine stays in `orchestrator-routing` (already "authoritative" per dotfiles `.claude/CLAUDE.md:89`). Shared routing prose goes in one rule stem declared under `rule-sync.toml [shared].rules` so existence is gated in both repos.

## 2. WHEN: Phase 10 step **2b** — after step 2's KB mirror PR lands, before step 3.

- Do not jump ahead of steps 1-2: both are base rebuilds and on the critical path; the removal touches no image input.
- Do not wait for the Phase 9 remainder (line 438): 9.12 codegen, 9.13 hooks, and the 12-wrapper retirement are **not** preconditions — the plugin's referenced surface is small (section 3) and the dead upstream means the runtime break at KB `kb-tool-review.js:188` can happen any day with no warning. Parity-first is preserved; its scope is decoupled.
- Before step 3, because step 3 and 9.13 build hooks on the lane roster; removing the plugin after that touches the hook surface twice.
- Drop the step-2 sub-item "model via run-lane arg 4" (line 391): it is work on a thing being deleted, and no repo lane calls `run-lane.sh` (`codex_lane.py:17` docstring; `mise.toml:727`).
- Every item goes `/to-spec → /to-tickets → /implement`; **no issue exists for 9.7 in either repo** (history §3/§4.7), so ticketing is the first move.

## 3. Minimal parity checklist (must exist before the removal PRs)

**dotfiles**
- D1 `.claude/agents/premise-verifier.md` — opus, Read/Grep/Glob, ported from the MIT source with notice + upstream SHA `78f9cb5` in the header (matrix B1). Replaces the row at `.claude/CLAUDE.md:69`.
- D2 `.claude/agents/advisor.md` — `model: fable`, read-only, **escalation-only**, mirroring KB `CLAUDE.md:34` where the codex advisor is DEFAULT. Resolves the dangling fallbacks in `codex-{sol,astra}-advisor.md:13-15,172,178` and `token-routing.md:8`. Name it `advisor`, not `fable-advisor`, so a model change is not a rename (same reason KB:35 carries no date).
- D3 Doctrine section in `codex-sdlc-team/SKILL.md`: routing table, seven-part spec + PREMISES block (B2/B9), review-tier names (B10), fallback chain codex → Opus with grok gone, U1 opt-out note. Cross-family review of a Claude-written diff = `sdlc-team` `mode: review` — no new reviewer agent (single entry point; matrix D drops `codex exec review`).
- D4 New trigger line in `.claude/CLAUDE.md` naming our skill; the rewrite of `:45-89` must stay inside the 200-line `eager_root` budget.
- D5 Contracts (`suites.toml:2366-2421`): `trigger-armed` → new line; `mode-line-declared` and `config-placement` → delete (matrix D drops intent-parsed config lines); `codex-only-lanes` → premise row names ours; `plugins-enabled` → antigravity only; NEW `orchestration.owned-agents` (paths_required on D1/D2/skill, per_path_tokens `model: fable` / `model: opus`); NEW `orchestration.no-plugin-references` — `forbid_tokens` `fable-orchestrator:` and `fable-orchestrator@` over `.claude/CLAUDE.md`, `.claude/agents/*.md`, `.claude/workflows/*.js`, `.claude/settings.json`, `rule-sync.toml`, `.codex/agents/*.toml`, live skills. That forbid is the FAIL arm; arm it by reintroducing one line before merge.
- D6 `tests/test_rule_sync.py:27-28`, `tests/test_verify.py:180,184` updated; `test_workflows_js.py:31,95` kept (fixture).
- D7 Remove the eval `--live` doctor (`eval_cases.py:54-57`, `main.py:1010`, `mise.toml:1325`) — it points at a 1.14.0 path and can only skip.
- D8 Pointer rewrites + `codex-lane-mirror` regen: `.codex/agents/codex-{sol,astra}-advisor.toml:28-29`, `adversarial-review` skill + `.agents` mirror, `docs/agent-team.md:419`, `docs/claude-plugin-config-hygiene.md:127,132`.

**knowledge-base**
- K1 `kb-tool-review.js:188` → `kb-codex-astra-reviewer` (exists); rewrite the comment at `:9-12`. **The only runtime dispatch of a plugin agent in either repo.** Class fix: a test asserting every `agentType` in `.claude/workflows/*.js` is a declared in-repo `.claude/agents` name.
- K2 `review.py:437` default cold lane → `cold:codex-astra` — the one lane that reaches `_run_review` and collects evidence (`:434-436`); the default becomes the honest one. Keep the `:296-305` spelling map so old receipts still read (rule 8, no normalising records). Update `kb-review/SKILL.md:127-132`, `references/lanes.md:23`.
- K3 `CLAUDE.md:34` keeps "always consult an advisor before any codex implementer dispatch"; advisors = `kb-codex-advisor` (default), `kb-codex-astra-advisor`, `kb-advisor` (fable) — drop "the plugin's `fable-advisor`". New trigger line byte-identical to dotfiles' (`rule_sync._normalise` compares whitespace-normalised lines).
- K4 KB implementer: `kb-codex-implementer.md` on `codex_run.py`, same shape as its `kb-codex-*` siblings — a **stopgap** explicitly tagged for retirement when the entry point moves into `kb_setup` (later ticket; dependency direction today is dotfiles → kb_setup, so a shared `sdlc_team` is a separate refactor).
- K5 `premise-verifier.md` — same port as D1.
- K6 `orchestrator-routing/SKILL.md:7,21,30,80` + `.agents` mirrors — drop grok and plugin names.
- K7 Remove `evals.py:489-520` doctor shell-out, `eval_cases.py:53`, `mise.toml:455`; docstrings at `review.py:299,437`, `codex_run.py:140`, `inplace_edit.py:30`, `rules/ai-cli-invocation.md:71`.
- K8 `settings.json:195,224-227`; KB-side forbid contract equivalent to D5.
- Keep `sources/fable-orchestrator/`, `REGISTRY.md:35`, golden set, `test_brain.py` — records, and the port's provenance.

**Proof of parity (both arms, per `real-integration-evidence.md`)**: `mise run verify`, `rule-sync`, `plugin-health` green with the plugin absent; `git grep -n 'fable-orchestrator:'` on live paths = 0 while `codex-sol-implementer` still hits; then one real `mise run sdlc-team` review dispatch settling `completed`, one `Agent` spawn of `premise-verifier` returning a verdict in each repo, and one end-to-end `kb-tool-review.js` run reaching its Review phase.

## 4. PR sequence (forced by `find_rule_sync_gaps`: presence-only, every declared item must exist in BOTH repos; dotfiles CI checks out KB **main**)

0. Tickets: one spec, per-repo tickets (`/to-spec → /to-tickets`). Docs-only.
1. **dotfiles parity PR** (additive; plugin stays; `rule-sync.toml` untouched): D1-D3, new trigger ADDED beside the old, `owned-agents` contract.
2. **KB parity PR** (additive; plugin stays): K1-K6, new trigger added, old lines kept. Must `kb-land` before step 3 is opened, and pull KB main locally before `mise run rule-sync`.
3. **dotfiles removal PR — the ONE Ray ruled**: `rule-sync.toml:29,40-41` swap, `settings.json` 2 keys, `.claude/CLAUDE.md:45-89` rewrite, D5-D8. Single push; `ship` arms auto-merge and any follow-up push races it.
4. **KB removal PR**: K7-K8, old lines 31-33 removed.
5. Operator: uninstall the plugin for both projects, disable the marketplace, run the live arms.

## 5. Risks

**Deciding risk: K1.** `kb-tool-review.js:188` is the one place the plugin is executed, and it breaks today on any cache GC or fresh clone — the reason to act at step 2b rather than after Phase 9. Land KB parity before anything is removed and the removal PRs carry near-zero runtime risk.

Others: the 178-line doctrine rewrite must go through Opus cold review + `premise-verifier` (built in step 1, so it can verify its own doctrine); the `orchestration.*` contracts are #354's tier-0 evidence — keep a FAIL arm by reintroduction; `.claude/CLAUDE.md` 200-line budget; K4 is a wrapper of the class ruled for retirement (tag it); two doctrine copies drift — `rule-sync` gates stem existence only, so a content-hash axis is a small later ticket.

**Three rulings for Ray (recommended answers):**
1. Insert the removal as Phase 10 step 2b and delete line 391's "run-lane arg 4" sub-item? **Yes.**
2. Decouple the removal from 9.12 codegen, 9.13 hooks, the 12-wrapper retirement, and a KB `sdlc_team` port — those stay Phase 9 remainder? **Yes.**
3. Add a Fable-backed `advisor` in dotfiles as escalation-only (codex advisor default, mirroring KB:34)? **Yes** — it honours both the 2026-08-27 "advisor before implementer" and the 2026-09-01 "prefer codex" rulings without a date.

Files: `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/task_plan.md`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/verification/suites.toml`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/python/src/dotfiles_setup/rule_sync.py`, `/Users/rmanaloto/dev/github/ray-manaloto/dotfiles/rule-sync.toml`, `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/.claude/workflows/kb-tool-review.js`, `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/python/src/kb_setup/review.py`, `/Users/rmanaloto/dev/github/ray-manaloto/knowledge-base/.claude/CLAUDE.md`.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — plan, contracts, rule-sync, agents, skill (local clone)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — coupling sites, agents roster, review.py, evals.py (local clone)
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — via the two input reports only (404 upstream; KB corpus clone)
