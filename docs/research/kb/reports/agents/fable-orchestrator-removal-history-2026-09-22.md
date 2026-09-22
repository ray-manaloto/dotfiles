# The request to remove fable-orchestrator: what the history shows (2026-09-22)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message. The harness neutralised `<`/`>` in transit; restored.
> Harness banner on receipt: "subagent output matched instruction-shaped pattern(s):
> settings-json" (relayed, not acted on).

**Lane limits.** This lane was read-only as instructed. I wrote nothing to `findings.md` or `progress.md`. My working notes are in the scratchpad at `.../b72c95e0-.../scratchpad/notes.md`, so this report has to be persisted by the coordinator.

**Search conditions.** AgentsView semantic and hybrid search were down ("index is building: 9% complete"). I used full-text search plus plain search over tool inputs and results, and left out session `b72c95e0` (this conversation). The AgentsView archive has **no coverage of 2026-07-18..26**: a search for "mise" in that window returned 0 hits. So the adoption conversation itself is not searchable, and adoption evidence comes from git. Graphify health came back `stale` (rc=3), so every repo claim below comes from reading the source directly.

Most `codex:`-prefixed hits are Claude transcripts that were imported in bulk on 2026-08-31, not native Codex sessions. I cite the original Claude session wherever one exists.

## 1. Every prior ruling about fable-orchestrator

| When | Where | Ray, verbatim or as recorded |
|---|---|---|
| 2026-07-22 | dotfiles `9eb06266` (#346), KB `57d34abd` | **Adoption.** "Enable the maintained CC plugins that implement the Fable-5 architect + cross-vendor executor pattern, per-project". Set `implementation lane = codex`. Session `016F37RH…` is a claude.ai id and is not in the archive. |
| 2026-07-24 | dotfiles `9f610e07` (#357) | Added the trigger line, **Fable-gated**. "Do NOT run /fable-orchestrator:setup here", because it writes to the stub-locked root `CLAUDE.md`. Also recorded that grok is absent. |
| 2026-08-03 21:49 | KB `5209ba3b` #346-367 @367 | `/fable-orchestrator:setup`, run after a loop of `/plugin` and `/reload-plugins --force`. |
| 2026-08-24 19:47 | KB `6347b2a5` #198 @198 | **Un-gating.** "why are you not using the /fable-orchestrator:orchestration skill? i want to use this going forward for all work so we can offload agent work to codex to reserve the remaining claude subscriptions where are running low for the week". At @201 the trigger was armed "regardless of session model". Landed as KB `fa4ed551` inside `f3bd4e4e` (#482): "Un-gated by Ray's ruling, with a note that `/fable-orchestrator:setup` will offer to re-gate it". |
| 2026-08-27 | dotfiles `da323dc4` (#790) | "un-gate the trigger line, matching knowledge-base". The `parity` gate was red. The "decline" re-gating note is in `.claude/CLAUDE.md:50-54` and in KB `.claude/CLAUDE.md:45-47`. |
| 2026-08-27 16:38 | `13897498` #768-791 @768 | A complaint and a misconception: "doesn't it use fable for the architect thinking/reasoning before sending to codex lanes". The answer at @775: "No — it never routes architect reasoning to Fable. `fable-advisor` is the only agent pinned `model: fable`". |
| 2026-08-27 23:51 / 2026-08-28 00:26 | KB `c3f2c373` @165, @257 | "use fable-advisor with codex-implementer", then "always use the fable-advisor with codex-implementer". Now KB `.claude/CLAUDE.md:34`. |
| 2026-08-31 05:23 | `4b7305b0` @581 | A principle stated in the planning-with-files (pwf) context: "less maintenance on our side… if there other plugins/skills/tools/etc that would achieve what we are doing instead of wasting our time maintaining claude vs actual real work". |
| 2026-08-31 19:47 | KB `fbb01460` @425 | "have all work done by codex lanes replace fable-adviser w a codex adviser using the model/effort of gpt-5.6-sol/xhigh". This produced `kb-codex-advisor`, later `codex-{sol,astra}-advisor`. |
| 2026-09-01 16:02 | `8dac106f` @84 | "there is no grok, add that to this project's rules and instructions to stop asking i told you to only use codex lanes for now". Now enforced by `.claude/CLAUDE.md:56-72` and the `orchestration.codex-only-lanes` contract. |
| 2026-09-12 12:41 | `814c5c84` @421 | **"What plugin? Just create our own version if needed"**. At @430 the assistant noted the implementer was the only role still borrowed from the plugin, whose agent hard-codes *"Never `danger-full-access`"*. That became #1039 (`ef32573d`), which added `codex-sol-implementer`. |
| 2026-09-21 19:46 | `dd442cf4` @253 | **The removal request.** "3. research how to remove /fable-orchestrator plugin and only use /codex-sdlc-team skill and team for all work that needs to offload to codex and only have one unified way to handle that via a skill that just provides skill args/parameters… take in the best of those features for our own homegrown plugin that is optimized for our workflow/process/protocol" |
| 2026-09-21 19:52 | `dd442cf4` @284 (AskUserQuestion) | Q9 → "Parity first, then one removal PR (Recommended)". Q10 (premise-verifier, fable-advisor, spec-contract/attestation hooks) → "Re-home as repo-owned (Recommended)". |
| 2026-09-21 20:05 | `dd442cf4` @318 (artifact comment) | "there should only be one entry point… skill(s) -> mise task(s) -> python library… code generated model/enums for all possible permutations… if needed create claude function hooks and codex hooks… to enforce this going forward" |
| 2026-09-21 20:24 / 20:27 | @334 / @346 | "must do a full review/research on claudex-loop and fable-advisor…". Then: "have a fable agent and codex astra model review it and then provide me the final feature matrix solution" |
| 2026-09-21 20:39 | @405 | Wrappers: "Yes, retire them via the entry point (Recommended)". Also an objection that `DannyMac180/fable-advisor` and the claudex-loop skills had not been researched, and "dont guess provide cited research". |
| 2026-09-21 21:18 / 21:33 | @526 / @582 | "Ratify A-D + addenda (Recommended)" and "Accept all three". Effort: "No default — caller must pass it". |
| 2026-09-22d | `task_plan.md:391` (Phase 10, from the excluded session) | "fable-orchestrator (vendored, upstream 404) gets the model via run-lane arg 4". |

**Failures and complaints that are on record:**
- **The model is hard-coded.** `run-lane.sh:91,112` in the plugin runs `codex exec --model "${MODEL:-gpt-5.6-sol}"`.
- **grok lanes are not installed**, which is why the 2026-09-01 ruling exists.
- **The live doctor costs money.** It spends "one real API call per installed lane" with no offline mode (`mise.toml:1325`; KB `mise.toml:455`).
- **The implementer lane substituted itself** instead of running codex (KB #559, open).
- **The premise hook never fires for our lanes.** It was measured dark: `codex-sol-implementer` rc=0 against the control `fable-orchestrator:codex-implementer` rc=2 (feature matrix §D).
- **The upstream is gone.** `gh api repos/mar3co/fable-orchestrator` returns 404, while the controls `DannyMac180/fable-advisor` (pushed 2026-09-22) and `chaseai-yt/claudex-loop` both return 200. The local marketplace clone points at the dead `git@github.com:mar3co/fable-orchestrator.git`, and its last commit is `78f9cb5` from 2026-08-13.

## 2. The planned replacement and where it stands

**What is planned (authoritative):**
- `task_plan.md:275-284` (item 9.7): one parameterised `/codex-sdlc-team` skill, parity first, then ONE removal PR covering the 2 keys in `settings.json`, `.claude/CLAUDE.md:45-89`, `rule-sync.toml` plus the knowledge-base, and at least 7 `suites.toml` contract blocks. `premise-verifier`, the advisor and the spec/attestation contract are re-homed on the Claude side.
- `task_plan.md:294-299`: the architecture ruling.
- `task_plan.md:301-321`: item 9.6b, done and ratified, which gates 9.7.
- The goal text is at `docs/agents/goal-history.md:1150,1183`.
- `task_plan.md:438`: Phase 9, including the 9.7 design, is **queued behind Phase 10**.

**The ratified matrix** (`docs/research/kb/reports/agents/feature-matrix-final-2026-09-21.md`):
- **A1-A5**: our own defects to fix first.
- **B1-B15**: what to migrate, including the premise-verifier agent, the PREMISES block, attestation bound to the spec's SHA-256, evidence grading, stability anchors, dissent as a status, and typed review tiers.
- **C**: what to keep.
- **D**: what to drop: grok, mix mode, the regex premise gate, the setup wizard, and fast mode.
- **Retire the 12 `codex-{sol,astra}-*` wrappers** (ruled).
- Its point 5: #1202 used **ZERO plugin agents**, so parity is "mostly writing that doctrine into our skill + B1".

**What exists today (source reads):**
- `python/src/dotfiles_setup/sdlc_team.py`, 1080 lines. `SdlcMode` has only `REVIEW` and `IMPLEMENT` (:48-52); the RESEARCH mode (item 9.2) is still missing. Matrix defects A1, A3 and A4 are all still **unfixed**:
  - `PLANNING_DISABLED` has 0 hits, against 2 in `codex_lane.py` as the control.
  - `timeout_s: float | None = None` at :70 and :147.
  - `workspace-write` at :747.
- `codex_lane.py` (637 lines) and `codex_lane_mirror.py` (170 lines) exist. Per the `mise.toml:727` comment, `codex_lane` is "NOT a wrapper around the fable-orchestrator plugin's run-lane.sh".
- `.claude/agents/` has all 12 `codex-{sol,astra}-*` lanes, implementer included, plus `cold-reviewer`, `gate-runner` and `spec-scribe`. There is **no `premise-verifier.md`** (0 hits), so B1 is not built.
- `.claude/workflows/gated-implementation.js:89-91,117-119` already points at our own `codex-sol-implementer` and `cold-reviewer`, not the plugin.
- The skill `.claude/skills/codex-sdlc-team/SKILL.md` exists but is not yet the parameterised single entry point.
- **Coupling that remains in dotfiles:**
  - `.claude/settings.json:194,225-228`
  - `.claude/CLAUDE.md:45-47,69,89`
  - `rule-sync.toml:29,40-41`
  - five `orchestration.*` contracts at `python/verification/suites.toml:2367-2416`, plus :2495
  - `codex-{sol,astra}-advisor.md`, which still name `fable-orchestrator:fable-advisor` and `codex-reviewer` as fallbacks
  - `tests/test_workflows_js.py:31,95`
- **Coupling that remains in knowledge-base, and is deeper:**
  - `.claude/CLAUDE.md:31-34`: the trigger, plus the "always consult an advisor before any `codex-implementer` dispatch" directive that names the plugin's `fable-advisor`.
  - `settings.json:195,224-227`.
  - `python/src/kb_setup/review.py:437`: the **DEFAULT cold-review lane is `cold:codex` = the plugin's `codex exec review`**.
  - `evals.py:490`: shells out to the plugin's `doctor.sh`.
  - `eval_cases.py:53`: a hard-coded cache path at version 1.14.0.
- `~/.config/mise/*.toml` has no fable references (0 hits).

## 3. GitHub issues

I searched both repos with `gh api /search/issues`. The probe can discriminate: it does return the adoption titles #346 and #357. **No issue in either repo proposes removing or replacing fable-orchestrator.** Item 9.7 exists only in `task_plan.md`.

Related open issues:
- **dotfiles:**
  - #884: codex lanes while tokens are constrained.
  - #994: gated-implementation orchestration.
  - #993: modernization epic, retire hand-written code.
  - #1137: enforce `sdlc-team` reachable only via the skill.
  - #1165: harden the request allowlist.
  - #1168: `hook_guard` blind to codex lanes.
  - #1155: implementer no-edit rule by hook.
  - #1115: `codex-sol-implementer` sits outside `PLANNING_DISABLED`.
  - #1119: advisor fallback path.
  - #354: eval epic.
- **knowledge-base:**
  - #559: the plugin's lane substituted itself.
  - #470: the premise gate is E-row only.
  - #446: fable-orchestrator absent from the corpus.
  - #14: orchestrator-routing.
  - #616: wrap cold-review CLI.
  - #445: lane model/effort.
  - #705: lanes shell out to a bare binary.
  - #324: `.codex/agents` drops `model:`.

## 4. Gaps: what the request needs that nothing covers yet

1. **There is no plan item, issue or matrix row for the knowledge-base.** Ray said "both". 9.7 only mentions syncing `rule-sync.toml` to the knowledge-base. Nothing plans replacing KB's default `cold:codex` lane (`review.py:437`), the `evals.py` doctor shell-out, KB `CLAUDE.md:34` (the advisor directive names `fable-advisor`), or the KB lanes `kb-codex-advisor` and `kb-codex-astra-*`. The KB has no `sdlc-team` at all (0 issues).
2. **Nothing covers "create our own version" as a plugin, as opposed to a skill.** The rulings say skill → mise task → python. Ray's words (@253: "our own homegrown plugin"; 2026-09-12: "create our own version") leave open whether to ship a packaged Claude plugin (marketplace or local plugin dir). No ruling covers packaging, cross-repo distribution to the knowledge-base, or versioning.
3. **Nothing covers the premise that parity must come first.** The upstream is 404 and the plugin cannot be reinstalled on a fresh machine: `settings.json` `extraKnownMarketplaces` points at a dead repo. That makes waiting a risk, and it is not written down anywhere as a reason to accelerate. The Phase 10 note "vendored… don't edit it" is only a workaround.
4. **Owed prerequisites that are still open:**
   - the premise-verifier pass over the matrix (`task_plan.md:320`)
   - probe 9.1c (#45482: read-only sandbox not honoured)
   - the premise-loop bound
   - the codex `--worktree` canary
   - items 9.2, 9.4, 9.11, 9.12, 9.13
   - matrix A1-A5 (confirmed still present)
5. **The replacement for `fable-advisor` on the Claude side is undecided.** Q10 says "re-home", but no `.claude/agents/*advisor*` pinned to `model: fable` exists; the local advisors are codex-only. KB `CLAUDE.md:35` also records a later "prefer codex lanes" ruling (2026-09-01), which is in tension with the earlier "always use the fable-advisor with codex-implementer".
6. **No defined contract test for parity.** Nothing measures "parity reached" before removal. Five `orchestration.*` contracts assert that the plugin is PRESENT, so the removal PR needs replacement contracts for the entry point. Issue #1137 is the closest.
7. **No filed issue for 9.7 itself**, in either repo.
8. **Codex history.** I found no native Codex user ruling on fable. Every Codex-agent hit traces back to imported Claude transcripts, so there is no Codex-only ruling on record to report.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — subject: git log, source greps, issue search
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — coupling sites, un-gating commit, issue search
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — 404 probe; local cache 1.21.0 read
- [DannyMac180/fable-advisor](https://github.com/DannyMac180/fable-advisor) — control arm for the 404 probe (200)
- [chaseai-yt/claudex-loop](https://github.com/chaseai-yt/claudex-loop) — control arm (200); predecessor named in the request
