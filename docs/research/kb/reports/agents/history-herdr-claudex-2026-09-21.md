# History check: herdr, claudex-loop, codex CLI wiring, fable-orchestrator inventory

Date: 2026-09-21
Repo: /Users/rmanaloto/dev/github/ray-manaloto/dotfiles (read-only fact-finding)

## Status: IN PROGRESS

## 1. herdr

**mise pin**: NOT in this repo's `mise.toml` or `.config/mise/conf.d/*.toml` (0 hits, control arm `fable-orchestrator` in same files: not checked directly but repo-wide `fable-orchestrator` = 92 hits vs `herdr` = 3 hits, both nonzero so grep discriminates).

It IS pinned in the **user-global** `~/.config/mise/config.toml:214`: `herdr = { version = "0.9.1", minimum_release_age = "0s" }`, and listed in the `minimum_release_age_excludes` array (line 14). This is outside this repo's review per `.claude/CLAUDE.md` MCP-registration caveat analog — a user-global tool, not a project-scoped one.

**Skills**: Three herdr skills exist at **user level** (`~/.claude/skills/herdr`, `~/.claude/skills/herdr-pre-release-audit`, `~/.claude/skills/herdr-throwaway-repro`) — confirmed present in this session's available-skills listing. **No repo-local skill** under `dotfiles/.claude/skills/` (0 matches for `herdr*` in that directory).

**Prior research mentions** (3 tracked report files, control arm `claudex`=1 hit / `graphify`=378 hits in same repo confirms grep discriminates):
1. `docs/research/kb/reports/agents/cx-research-orchestration-2026-09-10.md:89-95,290-303` — herdr classified as "Tier 3: Adjacent Infrastructure", "Runtime infrastructure for deploying coding agents (Rust-based)", beta/alpha, AGENTS.md+CLAUDE.md present. Treated as a reference/citation only, not adopted.
2. `docs/research/kb/reports/agents/2026-09-10-lane-briefs.md:44` — herdr named as one of five owner-cited orchestration references handed to a codex research lane (`cx-research-orchestration`), asking specifically how such systems stop an agent from reporting false success.
3. `docs/research/kb/reports/agents/2026-09-12-agentsview-field-research.md:546-550,884` — different herdr: `cpcloud/herdr-agentsview`, a Rust TUI consuming AgentsView data (unrelated to herdrdev/herdr the multiplexer); "look at only, not automation" tier; noted as bitten by upstream AgentsView schema drift.

No prior mise install, no issue, no session decision to adopt herdr as a repo tool — every hit is "cited as an external reference" or "the user-global tool the plugin skills already cover."

## 2. claudex-loop (chaseai-yt/claudex-loop)

**Exactly 1 tracked-file hit**: `docs/research/kb/reports/agents/2026-09-12-astra-codex-fanout.md`. Full section is "## Question 4: The claudex-loop Example" (lines 118-135, 199, 245, 264, 272).

**Conclusion at the time: UNRESOLVED, never fetched.** The codex lane doing that research ran in a read-only sandbox that blocked `curl`/network calls, so it could not inspect the actual repo. It could only speculate on three hypotheses (external process-spawn orchestration / a codex-native spawn API / Claude-team-spawns-codex) and explicitly flagged all three as **UNVERIFIED**, listing "fetch claudex-loop and inspect its implementation" as next steps for the operator (line 272) — which were apparently never carried out (no other report references it).

Adjacent finding from the same report: codex's CLI at the time had **no native spawn/fan-out API** (`codex exec --help` has no `--agent`/`--spawn`/`--delegate`; `grep -r spawn_agent .codex/agents/` = 0 matches, control arm `grep -r "name ="` = 10 matches — armed probe). The report's own recommended smallest-change path was "Claude wrapper fan-out" (give `.claude/agents/codex-sol-*.md` the `Agent` tool), not anything from claudex-loop.

## 3. Existing codex-CLI-driving surface (paths + one-line purpose)

| Path | Purpose |
|---|---|
| `.claude/rules/ai-cli-invocation.md` | THE canonical invocation contract (hand-kept argv block); `--ephemeral` blocks subagent spawning; `-s workspace-write` documented writable form; `--approve-for-me` mutually exclusive with `--sandbox`; `--full-context`/`--full-auto` do not exist; `-p` is `--profile` not prompt |
| `.claude/rules/codex-sdlc-team.md` | Six-specialist codex-side team roster, invoked only via `mise run sdlc-team`; hand-rolled `codex exec` for this team is guard-denied |
| `.claude/agents/codex-{sol,astra}-{adversarial-critic,advisor,claude-code-expert,implementer,operator,staleness-auditor}.md` | 12 Claude-side wrapper agent definitions (sol=authored, astra=mirrored) each hard-coding the CLI invocation for its role |
| `.codex/agents/codex-{sol,astra}-*.toml` + `.codex/agents/codex-sdlc-*.toml` | The codex-native agent-role TOML files these wrappers/`sdlc-team` dispatch to |
| `.codex/hooks.json` | codex-side hook config |
| `.codex/skills/graphify/**` | codex-platform graphify skill mirror (adopted, tracked since 2026-08-31) |
| `.claude/skills/codex-schema/SKILL.md`, `.agents/skills/codex-schema/SKILL.md` | Generate/check the codex app-server JSON schema for the exact installed version; load before hand-writing `.codex/agents/*.toml` because codex drops an invalid file silently |
| `.claude/skills/codex-sdlc-team/SKILL.md`, `.agents/skills/codex-sdlc-team/SKILL.md` | Operational detail for `mise run sdlc-team` |
| `.agents/skills/codex-task-orchestration/SKILL.md` (+ evals.json) | codex task-orchestration skill/eval harness |
| `python/src/dotfiles_setup/codex_lane.py` | Producer half of #613: writes lane record + verdict schema, runs `codex exec` with `--output-schema` + `-o`, settles for dag-tick's reaper |
| `python/src/dotfiles_setup/codex_lane_mirror.py` | Generates/checks codex-astra-* lanes mirrored from codex-sol-* |
| `python/src/dotfiles_setup/codex_agent_parity.py` | Asserts hand-authored codex agent lanes stay paired + at reasoning effort xhigh (also an hk step) |
| `python/src/dotfiles_setup/codex_agent_validate.py` | Validates codex SDLC agent files against schema + required roster |
| `python/src/dotfiles_setup/codex_schema.py` | Schema generation/check backing the codex-schema mise tasks |
| `python/src/dotfiles_setup/codex_verdict.py` | Verdict schema handling for codex lane output |
| `python/src/dotfiles_setup/sdlc_team.py` | The `mise run sdlc-team` typed-dispatch implementation (spec construction, sandbox selection, argv, detached launch, timeout supervision, artifact paths); deliberately omits `--ephemeral` because it delegates |
| `schemas/codex-agent.json`, `schemas/codex-config.json` | Vendored/derived schemas for `.codex/agents/*.toml` validation |
| `docs/specs/codex-sdlc-subagent-team.md`, `docs/specs/codex-sdlc-team-learning-loop.md`, `docs/specs/codex-sdlc-grilling-record.md` | Design/decision/verification specs for the SDLC team |
| `docs/agents/codex-task-orchestration.md` | Doc for the codex-task-orchestration skill |
| `fable-orchestrator:codex-implementer`, `fable-orchestrator:codex-reviewer` (plugin agents, not repo files) | Plugin-provided lanes referenced by `.claude/CLAUDE.md`'s routing table |

### Flag-by-flag findings (repo-wide grep, `docs/research/kb/reports/**` excluded)

- **`--ephemeral`**: used everywhere in the 12 wrapper agents and in `ai-cli-invocation.md`'s canonical block. ⚠️ Documented gotcha: it blocks subagent spawning ("Run without persisting session files to disk" — a spawned subagent needs a persisted thread) and hides the run from AgentsView. `sdlc_team.py` deliberately omits it (#1142) because it delegates.
- **`-s` / `--sandbox`**: `-s workspace-write` is the "documented writable sandbox form" per `ai-cli-invocation.md`. Measured 2026-09-12 (#1026), recorded in both `codex-{sol,astra}-implementer.md`: `-s workspace-write` → RC=1 (file not created, i.e. BLOCKED for git-tree writes under this repo's gates), `-s danger-full-access` → RC=0 (works). Same table repeated in `codex-{sol,astra}-operator.md`, with `-s workspace-write --add-dir <path>` also BLOCKED.
- **`danger-full-access`**: required by implementer/operator lanes because the repo's own gates (`mise run lint`, pytest, etc.) write outside the working tree (uv cache, mise state) — `workspace-write` cannot satisfy them. Config default: `sandbox_mode = "danger-full-access"` is set so every un-flagged codex call on this host already runs full-access; the advisor/critic/reviewer/expert/auditor lanes explicitly override to `read-only`. The implementer docs also quote a third-party plugin's stance ("Never `danger-full-access`") and call it "a sane default for [some other use case], not [applicable here]" — i.e. the repo consciously overrides that general guidance for its own gate-writing needs.
- **`--strict-config`**: **zero hits** anywhere in tracked files (control arm: `-s workspace-write` and `--ephemeral` both return many hits in the same grep pass, so the tool is not blind — the flag is simply never referenced).
- **`--dangerously-bypass-approvals-and-sandbox`**: explicitly named and BANNED — `codex-{sol,astra}-advisor.md`: "Never `--full-auto`, never `--dangerously-bypass-approvals-and-sandbox`, never a [...]".
- **`--dangerously-bypass-hook-trust`**: **zero hits** anywhere in tracked files. Same control arm as above; genuinely absent, never referenced or discussed.
- **`codex review` / `codex exec review`**: `python/src/dotfiles_setup/sdlc_team.py:621` and `tests/test_sdlc_team.py` treat "a codex review thread" as something that can be *observed* (ignored as non-specialist) rather than something the code itself invokes. `docs/receipts/575.md:142` records a real gotcha: **`codex exec review` has no `--cd`** — it reviews the invoking script's working directory, which is a hazard once parallel lanes run in worktrees. No agent/skill wraps `codex review`/`codex exec review` as a primary invocation path; the repo's review lanes instead use `codex exec` (implementer/reviewer roles) or `codex-lane` (#613's dag-based review lane).

## 4. codex version currency mechanism

- **Pin site (single source)**: `.config/mise/conf.d/shared.toml:44` — `"npm:@openai/codex" = { version = "0.154.0", allow_builds = ["@openai/codex"] }`. This is the SHARED host↔image fragment (per `AGENTS.md`'s Key Files table), so host and devcontainer image both resolve the same codex version. `mise-runtime.toml:60-61` comments confirm: "codex moved to the shared host↔image fragment ... the host's executor-lane codex and this tier's #613 review-lane codex pinned the same [version]".
- **mise.toml** carries extensive comments (lines 111-122) explaining the historical move OFF `aqua:openai/codex` (aqua's release only ships the Rust binary, no `codex agents` daemon/app-server) onto the npm package, but the actual `[tools]` pin lives in `shared.toml`, not `mise.toml` itself.
- **Renovate**: no codex-specific entry in `renovate.json` (0 hits for "openai" or "codex" as a customManager) — version bumps flow through Renovate's **native mise manager** (per `tool-currency-and-native-first.md`'s stated preference), which reads `shared.toml`'s `[tools]` table generically; no bespoke regex manager was needed for this pin.
- **`currency.toml`**: 0 hits for "codex" — codex is not in the deep-tracked/`mise run tool-currency` set; its currency is handled purely by mise+Renovate's version-bump PRs, not the daily currency-report engine.
- **`doctor.toml` `[codex]` section** (lines 272-280): governs **schema currency**, not version currency — "Codex app-server JSON schema currency... generated from the exact installed codex version... should be regenerated whenever codex is updated... Run `mise run codex-schema-generate`... `mise run codex-schema-check` to validate; doctor runs the same currency [check]". This is the mechanism that catches "codex was bumped but its JSON schema wasn't regenerated."
- **`codex-schema` skill** (`.claude/skills/codex-schema/SKILL.md`, mirrored at `.agents/skills/codex-schema/SKILL.md`): the human/agent-facing workflow — "Generate and check the codex app-server JSON schema for the EXACT installed codex version... Reach for it BEFORE hand-writing a `.codex/agents/*.toml`... codex DROPS an invalid agent file silently."
- Net mechanism: **one pin site** (`shared.toml`) + **generic Renovate mise-manager bump** + **doctor/skill-enforced schema regeneration** as the currency-check layer, no bespoke per-tool customManager or currency.toml entry.

## 5. `fable-orchestrator` complete wiring inventory (for removal)

### `.claude/settings.json`
- `enabledPlugins["fable-orchestrator@fable-orchestrator"] = true` (line 193)
- `extraKnownMarketplaces.fable-orchestrator = { source: { source: "github", repo: "mar3co/fable-orchestrator" } }` (lines 224-227)

### `.claude/CLAUDE.md` (all under "## Cross-vendor orchestration (Fable-5 architect + executor lanes)")
- Line 45: the eager UN-gated trigger line — "Without being reminded, on ANY session model: non-trivial implementation runs the fable-orchestrator architect-as-orchestrator flow — invoke the fable-orchestrator:orchestration skill before delegating..."
- Line 46: `fable-orchestrator: implementation lane = codex`
- Line 47: `fable-orchestrator: codex effort = xhigh`
- Lines 50-59: prose explaining why the trigger is deliberately un-gated, the `/fable-orchestrator:setup` re-gating trap ("decline"), and the "no grok here" doctrine
- Lines 60-70: routing table naming `fable-orchestrator:premise-verifier` and other lanes
- Line 89: "Adopted plugins ... `fable-orchestrator@fable-orchestrator` (Fable-5 architect + `codex` implementer lane, GPT-5.6 Sol)"
- Surrounding "There is no `grok` here" section (implicitly tied to fable-orchestrator's lane roster)

### `.claude/rules/codex-sdlc-team.md`
- No direct `fable-orchestrator` text hit in the earlier grep of rule files at top-level, but `.claude/token-routing.md` and `docs/agent-team.md` do reference it (see below) — codex-sdlc-team.md itself references only "the orchestration skill" generically per its own text; treat as adjacent, not a hard dependency.

### Agent definitions
- `.claude/agents/codex-astra-advisor.md`, `.claude/agents/codex-sol-advisor.md` — ban `--dangerously-bypass-approvals-and-sandbox`; these agents exist as fable-orchestrator's `fable-advisor` codex substitutes (per their own descriptions: "Codex ... substitute for fable-orchestrator:fable-advisor while Claude tokens are constrained")
- `.claude/agents/codex-astra-implementer.md`, `.claude/agents/codex-sol-implementer.md` — reference fable-orchestrator context in their sandbox-measurement narrative

### Other docs
- `.claude/token-routing.md` — permanent advisor-consult routing referenced from `.claude/CLAUDE.md` line ~89 ("⚠️ Permanent advisor-consult routing: see @token-routing.md")
- `docs/agent-team.md` — references fable-orchestrator in the broader agent-team design doc
- `docs/claude-plugin-config-hygiene.md` — documents the "both registrations live HERE, never in the root CLAUDE.md" trap for graphify/fable re-appending to root CLAUDE.md
- `docs/receipts/575.md` — receipt mentioning fable-orchestrator-related codex review lane work
- `docs/skills-inventory.md` — lists fable-orchestrator's skills in the repo's skill inventory
- `docs/specs/eval-harness-design.md`, `docs/specs/orchestration-pr-a-2026-09-09/spec-A1.md`, `spec-A1b.md` — design/spec docs written under the orchestration program that reference fable-orchestrator

### `rule-sync.toml` (cross-repo shared set with knowledge-base)
- Line 29: `"fable-orchestrator@fable-orchestrator"` — the plugin-enabled string is one of the synced values
- Lines 40-41: the exact trigger-line and mode-line text are part of the synced content (must match the sibling knowledge-base repo)

### `python/verification/suites.toml` (structured verification contracts — `mise run verify`)
- `orchestration.mode-line-declared` / trigger-declaration contract at **line 2210** — asserts `.claude/CLAUDE.md` carries the trigger line as a WHOLE LINE via `require_lines` (not `require_tokens`, deliberately, so a mere paraphrase/quote doesn't satisfy it)
- **Line 2217**: the exact un-gated trigger-line text as a required line
- **Line 2228**: `lines = ["- fable-orchestrator: implementation lane = codex"]` — mode-line contract
- **Line 2232**: contract binding "no grok CLI" routing — cold-review-lane-for-codex-diff-must-be-Claude reasoning, also via `require_lines`
- **Line 2246**: contract asserting BOTH orchestration plugins (`fable-orchestrator@fable-orchestrator` and presumably `antigravity@...`) are enabled `true` (not merely present) in `.claude/settings.json`, path-bound (#299) so no incidental rule-doc mention satisfies it
- **Line 2253**: the literal string `"fable-orchestrator@fable-orchestrator": true` as a required line
- **Line 2259**: contract about doctor.sh reading `.claude/CLAUDE.md`/root `CLAUDE.md` for the `codex fast mode` line (script-read vs model-read config placement)
- **Line 2337**: another literal-string requirement `'fable-orchestrator@fable-orchestrator"'`

**A complete removal would need to touch, at minimum**: `.claude/settings.json` (2 keys), `.claude/CLAUDE.md` (the whole "Cross-vendor orchestration" section, lines ~45-89), `rule-sync.toml` (3 lines, and the sibling knowledge-base repo's matching copy), `python/verification/suites.toml` (≥7 contract blocks around lines 2210-2337 that assert the above prose/config exist — these would need to be DELETED or rewritten, not just left to fail), plus updating `.claude/token-routing.md`, `docs/agent-team.md`, `docs/claude-plugin-config-hygiene.md`, `docs/skills-inventory.md`, and reconsidering whether the `codex-{sol,astra}-advisor.md` "substitute for fable-orchestrator:fable-advisor" framing still makes sense without the plugin.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles) — this repo; all inventory above
- [herdrdev/herdr](https://github.com/herdrdev/herdr) — cited only as external reference in prior research (Tier 3 adjacent infra); never adopted here
- [cpcloud/herdr-agentsview](https://github.com/cpcloud/herdr-agentsview) — unrelated Rust TUI also named "herdr", surfaced in an AgentsView tooling survey
- [chaseai-yt/claudex-loop](https://github.com/chaseai-yt/claudex-loop) — cited by the operator as an orchestration example; never fetched/resolved (sandbox network block); status UNRESOLVED
- [Cjbuilds/Codex-Orchestration](https://github.com/Cjbuilds/Codex-Orchestration) — related repo referenced in the same unresolved investigation, also not fetched
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator) — the enabled plugin providing the architect-as-orchestrator flow

## Addendum: AgentsView session history — claudex-loop WAS resolved, but never promoted to a tracked doc

The tracked report (`2026-09-12-astra-codex-fanout.md`) reflects only a **sandboxed codex advisor lane's** attempt, which was network-blocked and left claudex-loop UNRESOLVED. AgentsView session history shows the **coordinating Claude session** (not sandboxed) settled it the same day, in `dotfiles` session `7f1c108c-d85d-49c5-a95c-e224c0b2bb2b`, ordinals ~537-572 (2026-09-12T18:29-18:35Z; control-armed, `agentsview session search "claudex-loop" --fts`, 5 hits vs `fable-orchestrator` control arm nonzero too):

- **`claudex-loop` is NOT codex-native agent teams — it is external orchestration, the same pattern this repo already uses.** Read from its actual file tree (not README): ships `.claude-plugin/` + `.codex-plugin/plugin.json`, with `skills/codex-build/SKILL.md` and `skills/codex-review/SKILL.md` — i.e. **Claude skills that shell out to the codex CLI**, architecturally identical to this repo's `codex-sol-*`/`codex-astra-*` wrapper agents. Self-described (★1,802, Python, updated 2026-09-12): "four-phase plan hardening (recon, interrogate, Codex adversarial review, cross-model build & inspection)... **Whoever built it never grades it.**" — a discipline point the session treated as corroborating this repo's cross-family cold-review rule, not a new mechanism to adopt.
- **`codex exec` genuinely has no delegation/spawn flag** (armed grep for `agent|team|spawn|delegate|parallel|worker` → 4 hits, all singular-agent references).
- **`codex agents` is a TUI browser**, not a spawner — connects to "agent sessions on the shared local app-server daemon".
- **⭐ Correction discovered mid-session: `features.multi_agent_v2` IS a real, compiled-in, feature-gated capability** — found by running `strings -a` on the actual codex binary (control arm run first: known string count 31, confirms the instrument works — an earlier plain `grep -r` over the tree had returned 0 and was blindness, not an answer). It is **off by default** (`~/.codex/config.toml` `[features]` empty) and, even when enabled via `-c features.multi_agent_v2=true`, **does not change `codex exec --help`** — the capability lives behind the app-server daemon, not the `exec` subcommand this repo's wrappers use.
- **⚠️ `--strict-config` was tested live and found USELESS as a feature-name validity oracle**: `codex exec --strict-config -c features.multi_agent_v2=true --help` → rc=0, and `-c features.zqvbogus9=true` (bogus) → **also rc=0**. It does not reject unknown `features.*` keys, so it cannot be used to discover valid feature names or to confirm a feature is real.
- This finding IS already reflected in the vendored schema: `schemas/codex-agent.json` and `schemas/codex-config.json` both document `multi_agent_v2` (e.g. `codex-config.json:52` — "Whether multi-agent tools are enabled. Defaults to true. An enabled `features.multi_agent_v2` setting takes precedence.") — confirming the session's finding was real and is captured in the schema (generated via `mise run codex-schema-generate`), but **the narrative synthesis itself (claudex-loop = external orchestration; the app-server-only reachability of multi_agent_v2; the `--strict-config` gotcha) was never promoted to a tracked rule/doc/report** — it exists only in this AgentsView session and the gitignored `findings.md` from that session, both outside version control and easy to lose.

**Implication for the interview this fact-find is prep for**: if the goal is codex-driven multi-agent fan-out, `features.multi_agent_v2` is the one lead worth re-probing (specifically whether `codex app-server`/`remote-control` can expose it) — the session explicitly left that as "one probe left" and did not resolve it further in this history.

