# Cold review — 8dc9ab68 (codex model retarget)

- Subject: `8dc9ab68df043045832065a997d31d221624540b` (single commit, 25 files, +116/-59)
- Base: `origin/main` = merge-base `3740cceb6ea118846c2f63e5311db0da2260214f`
- Reviewer: cold-reviewer (Claude Opus 5.5), codex-lens fallback; author family Anthropic
- Started 2026-10-02T16:25 local; completed 2026-10-02.
- Memory: `memory: local` directory existed and was empty, so no prior review patterns applied.
- ⚠️ **The subject worktree moved during the review.** HEAD advanced to `8c9f9818`
  ("pin review_model on the review lens too", 16:32:08, touching only the two
  `codex-sdlc-team/SKILL.md` copies). Every gate and test result below was re-run
  against a `git archive 8dc9ab68` snapshot at `/tmp/cr8dc-full`, with a
  discriminating control arm. `8c9f9818` was NOT reviewed.
- Round shape: OPEN HUNTING (round 1, no enumerated domain). It cannot end the loop
  by any outcome and should promote to one bounded round.

## Verdict

**No HIGH or MEDIUM defects. 4 LOW, 4 INFO.** The retarget is mechanically complete:

- No live invocation site still names `gpt-5.6-sol` (E6).
- The new model IDs exist in codex 0.160.0's catalog and support `xhigh` (E1).
- The new argv forms parse (E4, E7).
- The parity, lane-mirror and skills-mirror gates pass on the pinned snapshot, and
  fail on a mutation (E3).
- The 4 affected test files pass on the pinned snapshot: 137 passed, 1
  environmental skip (E8).

The LOWs are validation and test gaps, plus prose claims with no enforcing line.

## Findings

| # | Severity | Claim | file:line | Evidence |
|---|---|---|---|---|
| F1 | LOW | The new `SdlcTeamRequest.model` field has no validation, while `effort` is validated, so `""`, `" "` and `"--sandbox"` all pass `_request_error`. The dispatch returns `dispatched`, and the bad model surfaces only after detach, in settlement. | `python/src/dotfiles_setup/sdlc_team.py:71`, `:648-665` (effort check at `:655-658`) | E9: `_request_error` returned `None` for all three bad models; control arm `effort=""` returned `effort must be a non-empty identifier`. |
| F2 | LOW | `test_dispatch_pins_model_and_effort` only exercises the default model. A regression that ignores `request.model` and hard-codes `SOL_MODEL` still passes, so the caller-override path is untested. | `tests/test_sdlc_team.py:414-435`; `python/src/dotfiles_setup/sdlc_team.py:812` | E10: mutation `request.model,` → `SOL_MODEL,` at `:812` gave armB rc=0 (still passes). Deleting the `--model` pair gave armC rc=1 (`ValueError` at test `:434`). Unmutated armA rc=0. `grep model tests/test_sdlc_team.py` finds no other dispatch-level model test. |
| F3 | LOW | The review lens pins the *session* model (`-m gpt-6-astra`), but `exec review` uses `review_model` when it is set, so a user-global `review_model` would silently override the "pinned" lens. Not live today (no `review_model` in user config, E2). Fixed by the later `8c9f9818`, which was outside this subject and not reviewed. | `.claude/skills/codex-sdlc-team/SKILL.md:187` (and `.agents/skills/codex-sdlc-team/SKILL.md:187`) | E5: codex docs `config-reference.md:32` — "Optional model override used by `/review` (defaults to the current session model)"; `cli__slash-commands.md:824-826`. |
| F4 | LOW | Q-CLAIM: the re-edited sentence "`--model` currently resolves to `gpt-6.1-sol` by inheritance from that same file" asserts user-global state with no enforcing line. (1) The mirror's model substitution makes the generated astra twins say the SAME file resolves to `gpt-6-astra`, so the twins contradict each other and the astra version is false today. (2) The clause just before it in the same paragraph ("runs at `medium`") is already false today: the file says `low`. (3) The sentence has rotted before: the 2026-09-28 SDLC run inherited `gpt-6-astra` while it read `gpt-5.6-sol`. | `.claude/agents/codex-sol-adversarial-critic.md:164-166`, `codex-sol-advisor.md:161-164`, `codex-sol-claude-code-expert.md:175-177`, `codex-sol-operator.md:128`, `codex-sol-staleness-auditor.md:145-147`; generated `codex-astra-advisor.md:166`, `codex-astra-operator.md:130` | E2 (user config: `gpt-6.1-sol` / `low`). E11 (2026-09-28 rollouts: inherited model `gpt-6-astra`). Mirror rule: `codex_lane_mirror.py:61,73` substitutes every occurrence of `SOL_MODEL`. Fix: drop the "currently resolves to X" clause. |
| F5 | INFO | Policy wording: `token-routing.md` and `MODEL_BY_PREFIX` say "Neither [family] is a default", but this diff makes sol the implicit default of `sdlc-team` and `codex-lane`. The skill's request documentation never mentions the new `model` field or its default. | `.claude/token-routing.md:28`; `python/src/dotfiles_setup/sdlc_team.py:71`; `python/src/dotfiles_setup/codex_lane.py:400`; `schemas/sdlc-team-request.json:20-23`; `.claude/skills/codex-sdlc-team/SKILL.md:37-56` | Read at the subject. The doctrine sentence is scoped to role lanes, so this is a documentation gap, not a code defect. |
| F6 | INFO | Q-CLAIM: the sol tomls' `description` and `developer_instructions` now say "running … on `gpt-6.1-sol`", but no sol toml has a `model` key. When codex spawns one natively by name, the model comes from the spawn or the parent. The claim holds only through the Claude wrapper's `--model`. Pre-existing structure; sibling ticket. | `.codex/agents/codex-sol-advisor.toml:12,18`, `codex-sol-adversarial-critic.toml:12,18`, `codex-sol-claude-code-expert.toml:12,21`, `codex-sol-staleness-auditor.toml:12,18`, `codex-sol-implementer.toml:11`, `codex-sol-operator.toml:11` | `grep -c '^model *='` = 0 for all 6 at the subject. Codex docs `agent-configuration__subagents.md:248-254`: unset values resolve as spawn value → `[agents]` → parent. |
| F7 | INFO | REFUTED hypothesis, recorded so it is not re-raised: "D15's sdlc-team pin reaches only the root thread, because the specialist tomls pin effort `high`". A real run shows every specialist at the parent's model and at `xhigh`, so CLI and parent values reached the children. The specialists' `model_reasoning_effort = "high"` was overridden in practice and is effectively dead config. Pre-existing; sibling ticket. | `.codex/agents/codex-sdlc-*.toml:9` (python-specialist `:4`) | E11: all 6 threads of run `fef427ec…` (parent `01a0eab3…`) record `{"model":"gpt-6-astra","effort":"xhigh"}` in `turn_context`. The tomls had `"high"` since `428a6ff7` (2026-09-15), before that run. |
| F8 | INFO | The `codex-lane` effort moves from `low` (inherited) to a fixed `xhigh`, with no override (`LANE_EFFORT` is a module constant). That applies to every DAG review lane and to the credit-costing `codex-lane-e2e` arm. `run_codex` has no timeout (pre-existing). The cost and latency impact is UNVERIFIED (no live lane was run). | `python/src/dotfiles_setup/codex_lane.py:117`, `:398-403`; `mise.toml:740-746` | E2 (inherited effort was `low`); code read at the subject. |

## Q-FRESH / Q-SCOPE / Q-CLAIM

- **Q-FRESH.** The diff adds no decision→action pairs. The model and effort are
  bound at argv construction (`codex_lane.py:398-403`, `sdlc_team.py:806-818`) and
  used immediately. The request default is bound at import time
  (`sdlc_team.py:71`), but `SOL_MODEL` is a constant, so there is no staleness
  window. N/A.
- **Q-SCOPE.**
  - F1, F2: in scope (new field, new test).
  - F3: in scope at `8dc9ab68`; already addressed by `8c9f9818`.
  - F4: in scope, because the diff re-edited the sentence. The mirror
    substitution behind it is a sibling.
  - F5: in scope (docs for the new field).
  - F6, F7: sibling tickets (pre-existing toml structure).
  - F8: in scope by design (D15); cost is an operator decision.
  - The longer-term fix (one model registry instead of `SOL_MODEL` imported from
    a mirror-generator module, a duplicate literal in `MODEL_BY_PREFIX`
    (`codex_agent_parity.py:123`), and a literal schema default) is a sibling.
    The commit message itself defers it to "the model registry".
- **Q-CLAIM: operator-facing strings this diff adds or changes, and what enforces each.**
  1. `main.py:2128-2129` help: "default: the pinned sol model, codex_lane_mirror.SOL_MODEL, at xhigh". Enforced by `codex_lane.py:400,402`. OK.
  2. `codex_lane.py:115-117` comment: "…~/.codex/config.toml, which is `low` there". True today (E2). Machine-local and dated. OK.
  3. `sdlc_team.py:809-810` comment: "Without it a lane ran whatever ~/.codex/config.toml named". Confirmed by E11. OK.
  4. SKILL.md `:187-189`: "(model + effort pinned … the lens inherited … effort `low`)". The "inherited low" part is true (E2). "Model pinned" is not fully enforced; see F3.
  5. 6 sol md/toml descriptions and bodies: "on codex (gpt-6.1-sol)". Enforced for the md wrappers by the parity gate (`codex_agent_parity.py:354`, `--model` marker). The toml path has no enforcement; see F6.
  6. Agent md "`--model` currently resolves to `gpt-6.1-sol` by inheritance". No enforcing line; see F4.
  7. `token-routing.md:27` "pinned to `gpt-6.1-sol`". Enforced by `MODEL_BY_PREFIX` plus the md check. OK.
  8. Commit-message claims:
     - "gpt-5.6-sol is 'Older generation'… gpt-6.1-sol is priority 1": verified (E1).
     - "astra twins … unchanged": verified (E3; no astra files in the diff).
     - "schema regenerated": verified (the `test_committed_schema_matches_its_canonical_model` drift test passes, E8).
     - "skills-mirror regenerated": verified (E3).

## Evidence log

- **E1 (catalog, verified).** `jq` over `~/.codex/models_cache.json` (client_version
  0.160.0, fetched 2026-10-02T21:25Z):
  - `gpt-6.1-sol`: priority 1, visibility list, levels include `xhigh`.
  - `gpt-6-astra`: priority 2, `xhigh` supported.
  - `gpt-5.6-sol`: priority 5, "Older generation workhorse model."

  Control arm: the same query returns `gpt-5.6-sol` with its old-generation
  description, so the probe discriminates.
- **E2 (user config, verified).** `grep -nE '^\s*(model|model_reasoning_effort|review_model|profile)\s*='
  ~/.codex/config.toml` → line 2 `model = "gpt-6.1-sol"`, line 3
  `model_reasoning_effort = "low"`. There is no `review_model` and no profile. The
  pattern did match `model` (positive arm), so the `review_model` absence is real.
  Only those key lines were read.
- **E3 (gates pinned at the subject).** The `dotfiles-setup` CLI resolves its repo
  root from its own package location (`main.py:3202`), so a first attempt at
  running it from the snapshot cwd silently checked the live worktree. A mutation
  arm exposed that (it stayed rc=0), and that run was discarded. The re-run called
  the gate functions with `sys.path` pointed at the snapshot's own source
  (`/tmp/cr8dc-gates.py`, asserting `dotfiles_setup.__file__` is under the
  snapshot):
  - `codex_lane_mirror_main(check)` = 0, `skills_mirror_main(check)` = 0,
    `codex_agent_parity_main` = 0.
  - Control arm: appending a byte to the snapshot's `codex-astra-advisor.md` and
    `.agents/skills/codex-sdlc-team/SKILL.md` turned the lane-mirror and
    skills-mirror results to 1, with DRIFT lines.
- **E4 (`codex exec review --help`, codex-cli 0.160.0).** The `review` subcommand
  accepts `-m, --model <MODEL>` and `-c, --config`, so the new lens argv parses.
- **E5 (codex docs, KB offline corpus dated 2026-08-16).**
  `config-file__config-reference.md:32` (`review_model` "defaults to the current
  session model"); `cli__slash-commands.md:824-826`.
- **E6 (residual `gpt-5.6`).** `git grep` at `8dc9ab68`, outside raw/runs/reports,
  hits only historical records: receipts 437/438, specs,
  `docs/agents/goal-history.md:1398`, a removed plugin's argv quoted in
  `docs/agent-team.md:423`, and an eval prompt. No live invocation site remains.
  Control: `gpt-6.1-sol` hits all 19 expected files.
- **E7 (`codex exec --help`).** `-m/--model`, `-c`, `-C/--cd`, `-o` and
  `--output-schema` all exist, so the sdlc-team and codex-lane argv parse.
- **E8 (pinned tests).** From `/tmp/cr8dc-full`:
  `pytest tests/test_codex_lane.py tests/test_sdlc_team.py tests/test_codex_lane_mirror.py tests/test_codex_agent_parity.py`
  → 137 passed, 1 skipped (`test_codex_agent_parity.py:150`, "Codex-app exported
  mirrors are gitignored and absent here", environmental), rc=0.
- **E9 (F1 probe).** `codec.decode` of a request with `model` in `''`, `' '`,
  `'--sandbox'`, `'gpt-6.1-sol'`: `_request_error` returned `None` for every one.
  Control: `effort: ""` returned "effort must be a non-empty identifier".
- **E10 (F2 mutation, snapshot copy at `/tmp/cr8dc-mut`).**
  - armA (unmutated): rc=0.
  - armB (`request.model` → `SOL_MODEL`): rc=0, the gap.
  - armC (`--model` pair deleted): rc=1.

  armC failing proves the snapshot's module was the one under test.
- **E11 (real run).** `~/dev/github/ray-manaloto/dotfiles/.agent/sdlc-runs/fef427ecb37740aebdd76ff528dd1713`
  (2026-09-28, status completed, 4 specialists observed). The `turn_context`
  `{model, effort}` of all 6 rollouts under `~/.codex/sessions/2026/09/28` that
  name parent `01a0eab3-…`: every one is `gpt-6-astra` / `xhigh`, including
  `sdlc-python/config/image/workflows-specialist`. Only those two fields and
  `session_meta` role fields were extracted.

## GitHub repos touched

_None._ All evidence came from the subject commit, the local codex install
(0.160.0 help and model cache), the local codex session rollouts, and the
knowledge-base offline codex docs corpus
(`~/dev/github/ray-manaloto/knowledge-base/sources/agent-harness-docs/docs/codex/`).
