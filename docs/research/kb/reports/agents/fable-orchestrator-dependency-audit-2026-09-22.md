# Fable-orchestrator removal + gpt-6 model move — dependency audit (2026-09-22)

> Persisted verbatim at receipt by the coordinator (session 2026-09-22d), from the
> delegate's final message. The harness neutralised `<`/`>` in transit; restored.
> Harness banner on receipt: "subagent output matched instruction-shaped pattern(s):
> settings-json" (relayed, not acted on). Coordinator note: Ray's model ruling is
> straight successors (gpt-5.6-sol → gpt-6-sol, gpt-5.6-luna → gpt-6-luna; astra
> unchanged) — the "decision for Ray" in §4 is answered by that ruling.

This lane was read-only. I edited no files, including `findings.md` and `progress.md`, so the coordinator needs to persist this report verbatim. I made no billable model calls; `codex debug models` only fetches the catalog. The graph came back `stale` (built at `9a6ea68f`, HEAD `4b6435aa`), so everything below comes from grepping the source.

### Bottom line

- **The upstream repo is gone.** The plugin is frozen at `1.21.0`, commit `78f9cb5`, dated 2026-08-13.
- **Dotfiles already covers about 80% of what the plugin does.** The pieces still missing are:
  - a Claude premise-verifier (missing in both repos)
  - a Fable advisor (missing in dotfiles; KB has one)
  - a codex-family reviewer for diffs Claude wrote (missing in dotfiles)
  - an implementer lane (missing in KB)
  - our own copy of the orchestration doctrine
- **The removal has to go in a fixed order across the two repos** because of the rule-sync gate (see step 5).
- **The model switch depends on a codex version bump.** Both repos pin codex `0.154.0`, and the server hides `gpt-6-sol` and `gpt-6-luna` from that version.

### 1. What the plugin provides (installed copy `~/.claude/plugins/cache/fable-orchestrator/fable-orchestrator/1.21.0`)

Both projects use the same install: `installed_plugins.json` has two project-scoped entries, KB installed 2026-07-23 and dotfiles 2026-08-14, both on version 1.21.0 at the same commit.

**Upstream status.**
- `gh api repos/mar3co/fable-orchestrator` returns 404, and so does the HTML page.
- Control arms: `cli/cli` returns 200, the owner `github.com/mar3co` returns 200, and the owner has 2 public repos, neither of them this one.
- `git ls-remote origin` from the marketplace clone fails with rc=128, "Repository not found".
- The marketplace clone's HEAD is `78f9cb5` (2026-08-13). `known_marketplaces.json` says `lastUpdated: 2026-09-15`, but that date is only when the clone was last checked; no new commits came in.
- **Conclusion:** the plugin no longer updates. It is MIT-licensed ("Copyright (c) 2026 Dan McAteer"), so we can fork it as long as we keep the notice.
- KB has an untracked clone at the same commit in `sources/fable-orchestrator/`, per `sources/fable-orchestrator.manifest:5`.

**Contents (2,578 lines in total):**

| Kind | Item | Notes |
|---|---|---|
| skill | `skills/orchestration/SKILL.md` (178 lines) | Routing doctrine, the seven-part spec contract with a PREMISES block, review tiers, and the fallback chain |
| agent | `codex-implementer.md` (Claude wrapper `model: sonnet`) | Calls `run-lane.sh codex` |
| agent | `codex-reviewer.md` (`sonnet`) | Runs `codex exec review` read-only |
| agent | `fable-advisor.md` (`model: fable`, tools Read/Grep/Glob) | 29 lines |
| agent | `premise-verifier.md` (`model: opus`, tools Read/Grep/Glob) | 75 lines |
| agent | `grok-implementer`, `grok-reviewer`, `grok-researcher` (`sonnet`) | Dead here: grok is not installed |
| command | `setup.md`, `doctor.md` | `doctor.sh` makes live, billable calls |
| hook | `hooks/hooks.json` | PreToolUse `matcher: "Agent"` running `premise-gate.sh` |
| script | `run-lane.sh`, `premise-gate.sh`, `doctor.sh`, plus 2 test scripts | |

**Config keys the plugin reads** (from `setup.md:19-23`, and parsed by `doctor.sh:29,36,49`):
- `fable-orchestrator: implementation lane = <grok|codex|mix>`
- `fable-orchestrator: codex fast mode = <on|off>`
- `fable-orchestrator: codex effort = <…>`
- `fable-orchestrator: grok effort = <…>`
- the trigger line naming the `fable-orchestrator:orchestration` skill

**Hardcoded models:**
- `gpt-5.6-sol`: `run-lane.sh:62,91,112`, `doctor.sh:57,71,82,84`, `agents/codex-implementer.md:30,143`, `SKILL.md:99`
- `grok-4.6`: `run-lane.sh:119`, `doctor.sh:120,180`, `grok-implementer.md:186`
- `model: fable` in `fable-advisor.md:4`; `model: opus` in `premise-verifier.md:4`
- The model can be overridden only through `run-lane.sh`'s 4th argument, `MODEL=${4:-}`.

**Premise-gate scope.** `premise-gate.sh:132-133` only matches agents named `codex-implementer` or `grok-implementer`, with or without a plugin prefix. **It never gated our own `codex-sol-implementer` or `codex-astra-implementer`**, so removing it takes away no protection those lanes currently have.

### 2. What depends on the plugin in each repo

Tracked files mentioning `fable-orchestrator`: dotfiles 107, KB 115. Control: `codex` appears in 594 and 604 files respectively.

Most of those files are archived reports under `docs/research/**`, `docs/receipts/**`, `sources/**`, `graphify-out/memory/**`, `docs/session-review/**` and `docs/currency/**`. **Keep those as records** (`agent-artifact-conventions.md` rule 8). The live surfaces are below.

**dotfiles**

| Surface | file:line | Action |
|---|---|---|
| enabledPlugins | `.claude/settings.json:194` | remove |
| extraKnownMarketplaces | `.claude/settings.json:225-228` | remove |
| trigger and config lines | `.claude/CLAUDE.md:45-47` | replace with our own skill's trigger |
| roster and prose | `.claude/CLAUDE.md:52,59,69,89` | replace |
| rule-sync shared set | `rule-sync.toml:29` (plugins), `:40-41` (lines) | replace; order constraint in step 5 |
| contracts | `suites.toml`: `orchestration.trigger-armed` (2367), `mode-line-declared` (2379, line 2386), `plugins-enabled` (2403-2411), `config-placement` (2416), `eval.cross-repo-rule-sync` (2495) | replace; `config-placement` can be removed |
| tests | `tests/test_rule_sync.py:27-28`, `tests/test_verify.py:180,184` | replace |
| tests | `tests/test_workflows_js.py:31,95` | keep; it is a fixture about plugin-prefixed names |
| eval `--live` | `eval_cases.py:54-57`, `main.py:1010`, `mise.toml:1325` | remove or repoint (see note below) |
| agents' prose | `codex-{sol,astra}-advisor.md:13-15,172,178`, `codex-{sol,astra}-implementer.md:18-20`, `.codex/agents/codex-{sol,astra}-advisor.toml:28-29` | replace pointers |
| docs | `.claude/token-routing.md:8`, `.claude/skills/adversarial-review/SKILL.md` and its `.agents` mirror (fable-advisor, codex-reviewer, grok-*), `docs/agent-team.md:419`, `docs/claude-plugin-config-hygiene.md:127,132` | replace |
| code docstrings | `codex_lane.py:17`, `codex_verdict.py:51,345`, `doc_refs.py:74`, `tests/test_codex_verdict.py:586`, `mise.toml:108,111,727` | keep as history, or reword |
| hook_guard | no match | none (control: `gh pr merge` has 4 hits in the same file) |
| doctor.toml | no plugin list | none; `plugin-health` reads what `settings.json` declares. The only effect is that `[listing] max_chars = 48110` is a ceiling, so removal lowers the count safely |

Note on the eval `--live` row: `eval_cases.py:57` points the doctor at the `1.14.0` cache path. Only `1.21.0` exists (control: the `1.21.0` directory lists), so this check already skips.

**knowledge-base**

| Surface | file:line | Action |
|---|---|---|
| enabledPlugins and marketplace | `.claude/settings.json:195,224-227` | remove |
| trigger, lane, effort and advisor-before-dispatch lines | `.claude/CLAUDE.md:31-34` | replace; line 34 is Ray's 2026-08-27 directive and needs a new target |
| prose | `.claude/CLAUDE.md:45,47,51` | replace |
| **runtime dispatch** | `.claude/workflows/kb-tool-review.js:188` `agentType: 'fable-orchestrator:codex-reviewer'` | **replace; this workflow breaks without it** |
| skills | `kb-review/SKILL.md:127,129,132` and `references/lanes.md:23`, `orchestrator-routing/SKILL.md:7,21,30,80`, plus their `.agents` mirrors | replace |
| eval `--live` | `eval_cases.py:53` (same stale 1.14.0 path), `evals.py:490,513`, `mise.toml:455` | remove or repoint |
| code docstrings | `review.py:299,437`, `codex_run.py:140`, `inplace_edit.py:30`, `rules/ai-cli-invocation.md:71` | reword |
| source corpus | `sources/REGISTRY.md:35`, the manifest, `eval_cases.py:323,331` (golden set `fable-orchestrator.md`), `test_prose.py`, `test_brain.py:239,292` | keep |

KB has no `rule-sync.toml`; dotfiles' `rule_sync.py` reads KB's files directly (control: `ls` returned ENOENT).

### 3. Plugin capability vs. what we already have

| Plugin capability | dotfiles | KB |
|---|---|---|
| orchestration doctrine (skill) | Partial: `.claude/CLAUDE.md` lanes table, `token-routing.md`, `gated-implementation.js`, `codex-sdlc-team` skill | `orchestrator-routing` skill (already "authoritative routing/fallback") |
| seven-part spec + PREMISES block | `spec-scribe`; `codex-sol-implementer.md:120` refuses a spec with no PREMISES block; `gated-implementation.js:15` requires `args.premises` | missing |
| codex-implementer | `codex-{sol,astra}-implementer`, `codex_lane.py`, `sdlc_team.py` | **missing**; KB dispatches the plugin's version (CLAUDE.md:34). `codex_run.py` is the runner a port would use |
| codex-reviewer (codex lens on a Claude-written diff) | **missing as an agent**; `sdlc-team` review mode is closest | `kb-codex-astra-reviewer` |
| cold review of a codex diff | `cold-reviewer` (opus/xhigh) | `kb-adversarial-verifier` (opus) |
| fable-advisor | **missing** (`codex-{sol,astra}-advisor` are codex substitutes) | `kb-advisor` (`model: fable`, effort high), plus `kb-codex-advisor`, `kb-codex-astra-advisor` |
| premise-verifier | **missing** | **missing** |
| premise-gate hook | wrapper preflight plus workflow arg (hook never covered our lanes) | missing |
| run-lane.sh | `codex_lane.py` (docstring `:17` explains why run-lane.sh was not reused) | `codex_run.py` |
| doctor.sh | `plugin-health`, `codex-schema`, `codex-agent-validate`, `eval` | `evals.py` |
| grok-*, setup | not applicable, remove | not applicable, remove |

### 4. Codex model inventory

**Prerequisite, re-derived with a control arm:**
- `codex debug models` on `~/.local/bin/codex` 0.156.0 lists `gpt-6-astra gpt-6-sol gpt-6-luna gpt-5.6-{sol,terra,luna}`.
- The same command via `mise exec` on 0.154.0 lists no gpt-6-sol and no gpt-6-luna.
- Supported effort levels on 0.156.0: `gpt-6-sol` has low through max plus **ultra**; `gpt-6-luna` stops at **max, with no ultra**.
- Every lane in both repos uses `xhigh` or lower, so all current effort settings are valid on Luna.
- The pins to bump: dotfiles `.config/mise/conf.d/shared.toml:44` and KB `mise.toml:239`, both `0.154.0`.

**dotfiles, the places that actually set the model:**
- `codex_lane_mirror.py:32` `SOL_MODEL = "gpt-5.6-sol"` and `:33` `ASTRA_MODEL = "gpt-6-astra"`
- `codex_agent_parity.py:122-123` `MODEL_BY_PREFIX`
- `--model gpt-5.6-sol` in the Claude wrappers: `codex-sol-implementer.md:169`, `codex-sol-operator.md:67`, `codex-sol-advisor.md:103`, and the other three sol roles
- The astra `.md` and `.toml` files are generated by `mise run codex-lane-mirror`
- Prose mentions: `token-routing.md:17-18`, `.claude/CLAUDE.md`
- Tests: `test_codex_lane_mirror.py:31,51-63,88`, `test_codex_agent_parity.py:61,302`

**dotfiles gap:** none of the `.codex/agents/*.toml` files sets `model =`. The grep returned 0, while the same grep shape finds `name =` in 18 files, so the probe works.
- Every codex-side twin, including `codex-sol-*` and all six `codex-sdlc-*`, therefore inherits `~/.codex/config.toml:2` `model = "gpt-6-astra"`.
- The prose at `codex-sol-advisor.md:122` and `codex-sol-operator.md:83` saying they "resolve to gpt-5.6-sol by inheritance" is wrong.

**knowledge-base, the places that set the model:**
- `.codex/config.toml:22` `default_subagent_model = "gpt-5.6-sol"`
- `kb-codex-astra-advisor.toml:38` and `kb-codex-astra-reviewer.toml:14,112` `gpt-6-astra`
- `kb-codex-advisor.toml:59` `--model gpt-5.6-sol`
- Docstrings: `codex_run.py:94`, `lane_recording.py:114`
- Test fixtures: `test_codex_lane.py`, `test_codex_review_evidence.py`
- Leave `graphify_native_extract.py` alone; it is graphify's own default, not ours.

**Sol vs. Luna:**
- **Sol:** implementer, advisor, adversarial-critic, staleness-auditor, claude-code-expert, cold-reviewer, the sdlc dispatcher and specialists, and the KB advisor and reviewer.
- **Luna** (cheap, mechanical, low or medium effort today):
  - dotfiles `.codex/agents`: `gate-runner` (low), `graphify-operator`, `issue-filer`, `pwf-scribe` (medium), and `codex-*-operator` (runs a single `mise run` task)
  - KB: `kb-extraction-worker`, `kb-corpus-curator` (medium)

**Decision for Ray:** "move everything to sol/luna" retires the **astra** family.
- The mirror, the parity map, the `codex-{sol,astra}` naming in `.claude/CLAUDE.md` and in the `orchestration.codex-only-lanes` contract (`suites.toml:2398`), and `codex-sdlc-team.md` would all need renaming, for example to `codex-luna-*`.
- Mirroring every role to Luna at xhigh, implementer and advisor included, would lower quality. My recommendation: **make sol the authored lane, and pin Luna explicitly only on the mechanical roles.**
- Changing the user-global `~/.codex/config.toml` default is an operator action. Pinning `model =` in each project TOML avoids having to touch it.

The earlier `gpt6-sol-luna-model-update-2026-09-22.md` inventory agrees with everything I re-checked: the pins, the `model =` gap, and the catalog.

### 5. Removal and replacement outline

1. **Codex pin (per-repo PR, first).** Bump to `0.156.0`: dotfiles `mise run lock-shared -- "npm:@openai/codex"`, then `lock-image` and `pin-parity`; KB `mise.toml:239`. Then run `codex-schema-generate`. **Arm:** 0.156.0 lists the gpt-6 models and 0.154.0 does not (already observed).
2. **Model strings (dotfiles).**
   - Change `SOL_MODEL` and `MODEL_BY_PREFIX` to `gpt-6-sol`, then update the sol wrappers and tests.
   - Decide what happens to astra (the decision above).
   - Add explicit `model =` lines to the `.codex/agents/*.toml` files: sol, or luna for the mechanical roles.
   - Run `codex-lane-mirror`, then `-- --check`, `codex-agent-parity` and `codex-agent-validate`.
   - **Arm:** revert one wrapper to `gpt-5.6-sol` and confirm parity fails.
3. **Model strings (KB).** Change `default_subagent_model`, the kb-codex advisor and reviewer pairs, and the docstrings.
4. **Build the replacements, in both repos, before removing anything.**
   - `premise-verifier` agent: opus, Read/Grep/Glob, ported from the MIT source with the notice kept.
   - `fable-advisor` for dotfiles, following KB's `kb-advisor` pattern.
   - A codex reviewer agent for dotfiles (port `kb-codex-astra-reviewer`).
   - A KB implementer (port `codex-sol-implementer` on top of `codex_run.py`).
   - An owned `orchestration` skill, with the doctrine slimmed to codex plus Claude only (drop grok), in dotfiles and KB (fold it into `orchestrator-routing`).
   - Optional: extend `hook_guard`'s PreToolUse matcher to `Agent` to enforce PREMISES. The matcher is an exact-string list, so add the string `Agent` and nothing regex-like.
5. **Cut over; the order is forced by rule-sync.** Rule-sync fails for everyone as soon as a required value is missing on one side.
   - **(a) dotfiles PR first:**
     - swap `rule-sync.toml` `[shared]` plugins and lines to the new trigger
     - update the `suites.toml` orchestration contracts and tests
     - update `.claude/CLAUDE.md` and `settings.json`
     - repoint the agent pointers
     - drop the eval `--live` doctor
     - **Problem:** the new trigger line is not in KB yet, so the check fails in dotfiles CI.
   - **Therefore:** first land a KB PR that **adds** the new trigger and skill and **keeps** the plugin. Then land the dotfiles PR that removes the plugin and swaps rule-sync. Then land the KB PR that removes the plugin and the old lines, and repoints `kb-tool-review.js:188` and `kb-review`.
   - The changes to `rule-sync.toml`, the contracts, the tests and `.claude/CLAUDE.md` **must land in the same PR.**
6. **Uninstall.** Remove `fable-orchestrator` from `installed_plugins.json` for both projects (operator step, `claude plugin` CLI), and disable the marketplace.

**Gates per PR:**
- `mise run lint`, pytest, `mise run verify`, `lint-docs`, `rule-sync` (needs the sibling clone; fails hard in CI)
- `mise run plugin-health`: the plugin must be absent and nothing may be reported as drift
- `codex-agent-parity`, `codex-agent-validate`, `codex-lane-mirror -- --check`, `pin-parity`
- **Arms:** `git grep -n 'fable-orchestrator:'` on live paths must return 0, while the same grep for `codex-sol-implementer` must still hit. Confirm that `/agents` or the skill listing shows the new agents and skills.
- **Live arms (billable, not run here):** one `--model gpt-6-sol` call and one `gpt-6-luna` call. Negative arms: `gpt-6-terra` must fail, and `luna` with `ultra` must fail. Check the model from the rollout's `turn_context`, not the startup banner.

**Risks:**
- KB's `kb-tool-review.js` fails hard if the old reviewer is still named.
- Ray's advisor-before-dispatch directive (KB CLAUDE.md:34) needs a named replacement advisor.
- The un-gated trigger doctrine currently rests on the plugin's skill.
- Adding a PreToolUse `Agent` hook means our guard fails open in a new place (#343).
- Renaming astra touches many rules and contracts.
- `gpt-5.5` retires on 2026-10-14; no gpt-5.6 retirement date is published.
- Unverified: whether 0.154.0 accepts an unlisted `--model gpt-6-sol`.

## GitHub repos touched

- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — plugin source (local 1.21.0 cache and marketplace clone); upstream 404 and ls-remote rc=128
- [cli/cli](https://github.com/cli/cli) — control arm for the `gh api` 404 probe
- [openai/codex](https://github.com/openai/codex) — installed 0.154.0 and 0.156.0 binaries, `codex debug models` server catalog (local only)
- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — dependency and model inventory (local clone)
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base) — dependency and model inventory (local clone)
