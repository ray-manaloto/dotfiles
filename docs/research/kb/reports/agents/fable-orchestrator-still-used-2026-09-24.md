# Brief U — why is fable-orchestrator still used, on old codex + old models? (2026-09-24)

Lane: Opus `general-purpose`, read-only except this report. No codex review or model call was run.
Only `codex debug models` / `--help` / `--version` were run, which cost nothing.
Repo: dotfiles, branch `docs/session-2026-09-23d-handoff` at `e6599421`, plus uncommitted working-tree edits
by the coordinator. Graph health: `fresh (runtime=0.9.65)`.

## TL;DR

Ray thought this was fixed. Two things were fixed on 2026-09-23. Four things were not.

- **FIXED:** the host default codex. `5e258baf` (23:11) added `mise.toml:170`
  `disable_tools = ["npm:@openai/codex"]`, so `~/.local/bin/codex` now points at native 0.156.1.
- **FIXED:** the 12 in-repo wrappers. `86324c6a` (23:26) makes them launch through `mise exec -- codex exec`.
- **NOT FIXED:** the fable-orchestrator plugin launches bare `codex` from THIS Claude session's PATH, and that PATH
  was frozen in a shell snapshot at 19:09, four hours before `disable_tools` landed. `86324c6a`'s own commit body
  names this exact defect ("bare `codex` resolved from this session's PATH, captured before the host moved to
  native codex"). The fix was applied to our 12 wrappers and not to the plugin route. That route was then used for
  S3 and T. This repeats the known "fix the instance, not the class" mistake.
- **NOT FIXED, and not fixable by any PATH change:** the plugin HARD-CODES `--model "${MODEL:-gpt-5.6-sol}"`
  (`run-lane.sh:91,112`). Its `codex-reviewer` agent never passes the optional arg 4 (`codex-reviewer.md:86`). An
  explicit `--model` beats the user config's `model = "gpt-6-astra"`.
- **NOT FIXED anywhere yet:** our OWN `codex-sol-*` lanes still pin `--model gpt-5.6-sol` (e.g.
  `.claude/agents/codex-sol-adversarial-critic.md:105`). The move to `gpt-6-sol` is ruled (`task_plan.md:387-390`,
  `:427-428`) but scheduled for Phase 10 step 2b and the Phase 11 "step-2a remainder" (`task_plan.md:688-693`).
  So "old models" is not only a plugin problem.
- **ROUTING, the reason the plugin was reached at all:**
  - At HEAD, `/session-handoff` §1c named `fable-orchestrator:codex-reviewer` as the bugs lane
    (`git show HEAD:.claude/skills/session-handoff/SKILL.md:147`).
  - The eager `.claude/CLAUDE.md:45` trigger makes the plugin's orchestration skill "authoritative for routing
    … review tiers".
  - The CLAUDE.md lane table has NO row for reviewing a Claude-authored diff (`.claude/CLAUDE.md:64-71`), so the
    skill's default fills that gap: `codex-reviewer` (plugin `SKILL.md:54,167`).
- **The removal is ruled but queued:** Phase 10 step 0 (spec dotfiles#1310, OPEN; tickets #1311-#1319 OPEN) was
  ruled to run "FIRST — before any step that would trigger codex work or agents" (`task_plan.md:432-433`, `:490`).
  Phase 11 was later placed ahead of it (`task_plan.md:511`, `:762`). Phase 11 triggers codex work and agents.
  **These two rulings conflict, and nobody has named the conflict.**

## Q1 — routes that still send work to fable-orchestrator

Probe: `git grep -n fable-orchestrator` over live paths (excluding `docs/research`, specs, receipts,
`task_plan.md`). Control arm: the same grep hits `.claude/settings.json:194`, a line known to be present.

| # | Route | Where | Live effect | Already ruled? |
|---|---|---|---|---|
| R1 | `/session-handoff` §1c bugs row → `fable-orchestrator:codex-reviewer` | At HEAD: `.claude/skills/session-handoff/SKILL.md:147` and `.agents/skills/session-handoff/SKILL.md:147` (`git show HEAD:…`). Introduced by `5e258baf`. | **This is the route Briefs O, S3 and T took.** The working tree now has an UNCOMMITTED rewrite of both copies ("Do not route through the fable-orchestrator plugin …"). See Q3 for a defect in that rewrite. | Not specifically. It was written this session, after the Phase 10 removal ruling. |
| R2 | Eager trigger: "invoke the fable-orchestrator:orchestration skill … follow it as authoritative for routing, verification, review tiers, and advisor consults" | `.claude/CLAUDE.md:45` | The plugin skill's review tier sends a Claude-authored behaviour-bearing diff to `codex-reviewer` (plugin `skills/orchestration/SKILL.md:54,167`). The CLAUDE.md lane table (`:64-71`) overrides implementation, advisory and codex-diff review, but has **no row for a Claude-authored diff**. The plugin default therefore wins exactly where R1 fired. | Yes. D4 in `fable-orchestrator-removal-decision-2026-09-22.md:37` replaces it. |
| R3 | Mode and effort lines `fable-orchestrator: implementation lane = codex` and `codex effort = xhigh` | `.claude/CLAUDE.md:46-47` | These feed `EFFORT: xhigh` into plugin lanes. Brief T's report records "applied: xhigh" (`session-audit-final-codex-cold-review-2026-09-24.md:10`). | Yes (D5: mode-line contract deleted). |
| R4 | Premise verification → `fable-orchestrator:premise-verifier` | `.claude/CLAUDE.md:69` | A Claude-model agent. No codex is involved, so it plays no part in the old-codex symptom. | Yes (D1 ports it in-repo). |
| R5 | Advisor fallback pointers → `fable-orchestrator:fable-advisor` | `.claude/token-routing.md:8`; `.claude/agents/codex-{sol,astra}-advisor.md:13-15,217-225`; `.codex/agents/codex-{sol,astra}-advisor.toml:28-29` | Explicit selection only; no default route. Claude model. | Yes (D2 `claude-advisor`, #1294). |
| R6 | Plugin enabled for this project | `.claude/settings.json:194` (`true`), marketplace `:225-228` | Makes R1/R2 dispatchable. Also runs the plugin's `PreToolUse` hook on every `Agent` call (`hooks/hooks.json` → `premise-gate.sh`). That hook matches only the plugin's own names `codex-implementer`/`grok-implementer` (`premise-gate.sh:132-133`), so it is dark for our `codex-sol-implementer`. | Yes (removal PR, step 3 of §4). |
| R7 | Contracts that REQUIRE the plugin to stay enabled | `python/verification/suites.toml:2391-2437` (`orchestration.trigger-armed`, `mode-line-declared`, `plugins-enabled` requires `"fable-orchestrator@fable-orchestrator": true`); `:2520` (rule-sync contract token); `rule-sync.toml:28-42` (`[shared].plugins` + trigger lines must match knowledge-base) | Nothing is dispatched through these, but they **block a quick disable** (Q4). | Yes (D5/D6 and the §4 PR sequence). |
| R8 | knowledge-base workflow `kb-tool-review.js:188` → `agentType: 'fable-orchestrator:codex-reviewer'` | `knowledge-base/.claude/workflows/kb-tool-review.js:188`; KB `.claude/CLAUDE.md:31-34`; KB `.claude/settings.json:195` | **The only hard-coded runtime dispatch of a plugin agent in either repo.** It has the same 0.154.0/gpt-5.6-sol exposure whenever the launching session's PATH is stale. The model is ALWAYS gpt-5.6-sol. | Yes (K1, the "deciding risk" in the removal decision §5). |
| R9 | Codex harness: `[plugins."fable-orchestrator@fable-orchestrator"] enabled = true` (`~/.codex/config.toml:80-81`), trusted hook `:436-437`, marketplace `:601-605`; `claudex-loop` `enabled = true` `:254-255`, marketplace `:653-655` | user-global codex config (plugin block only was read) | Codex sessions load the plugin's skills and hook. | Yes (Addendum, `task_plan.md:468-471`: operator step to remove it and disable claudex-loop). Not done. |

Dotfiles saved workflows dispatch no plugin agent (`.claude/workflows/*.js` agentTypes are all in-repo:
`gated-implementation.js:91,102,119,131`, `graphify-refresh.js:71,84,100`).

**Evidence that R1 was the route actually used:** the report headers name it.
- Brief O: `session-audit-codex-cold-review-2026-09-23.md:1` ("fable-orchestrator:codex-reviewer (sonnet wrapper +
  run-lane.sh)").
- Brief S3: `session-audit-delta-codex-cold-review-2026-09-23.md:1`.
- Brief T: `session-audit-final-codex-cold-review-2026-09-24.md:7` ("`codex-cli 0.154.0`, GPT-5.6 Sol, via
  `fable-orchestrator` `codex-review` lane").

S3 reviewed `86324c6a`, the wrapper fix itself, and got no benefit from it.

**What was RULED:**
- Phase 10 Addendum (`task_plan.md:429-440`): remove fable-orchestrator from both repos, replace it with in-repo
  agents and skills, and run the removal "FIRST — before any step that would trigger codex work or agents".
- Order item 0 (`:490`) says the same.
- Addendum 2 (`:486`): step 0 spec = dotfiles#1310 (OPEN, `ready-for-agent`); tickets dotfiles #1311-#1319 (OPEN)
  and KB #793-#797.
- Phase 11 was then ruled "BEFORE Phase 10 step 0" (`:511`), with "Phase 10 step 0 … resumes after Phase 11"
  (`:762`).
- Phase 11's own order runs codex step-2a, the codex class fix and #1351 `/implement` (`:755-761`). All of that is
  codex work and agent dispatch. **So the "remove it before anything triggers codex/agents" ruling is being
  violated by the ordering that superseded it.** Neither ruling acknowledges the other. That conflict is the
  planning-level reason the plugin is still live.

## Q2 — why codex 0.154.0, and where `gpt-5.6-sol` comes from

### Binary: a stale Claude Code shell snapshot, not the repo config

| Probe | Result |
|---|---|
| `which -a codex` in this session | 1st hit `~/.local/share/mise/installs/npm-openai-codex/0.154.0/bin/codex`, then the mise shim, then `~/.local/bin/codex` |
| `codex --version` in this session | `codex-cli 0.154.0` |
| **Control arm:** a fresh `env -i HOME USER TERM zsh -lic` in the repo | `command -v codex` → `~/.local/share/mise/shims/codex`, `codex-cli 0.156.1` |
| `mise exec -- codex --version` from this session | `codex-cli 0.156.1` (mise rebuilds PATH and drops the disabled tool's dir) |
| `~/.local/bin/codex` | symlink → `~/.codex/packages/standalone/current/bin/codex` (`current` → `releases/0.156.1-aarch64-apple-darwin`, created Sep 23 23:37) |
| Shell snapshot the Bash tool sources | `~/.claude/shell-snapshots/snapshot-zsh-1790208590332-q0kqjd.sh`, mtime **Sep 23 19:09**. `grep -c "npm-openai-codex/0.154.0/bin"` = 1; a fresh nonsense-token control = 0 |
| `disable_tools` commit | `5e258baf` at **2026-09-23 23:11** (`git log -S`) |

So:
- The session's PATH was captured four hours before the host moved to native.
- `run-lane.sh:88,97` does `command -v codex` and runs bare `codex`, which resolves the npm dir that sits earlier on
  the frozen PATH.
- A fresh Claude session (new snapshot) would resolve native 0.156.1 even through the plugin. That is **inferred**
  from the `env -i` arm, not run through the plugin itself.
- The devcontainer and CI still ship npm 0.154.0 by design until Phase 10 step 2b (`task_plan.md:678-680`).

### Model: hard-coded in the plugin source

- `~/.claude/plugins/cache/fable-orchestrator/fable-orchestrator/1.21.0/scripts/run-lane.sh:91` (implement) and
  `:112` (review): `--model "${MODEL:-gpt-5.6-sol}"`. `MODEL` is positional arg 4 of `start` (`:57`).
- `agents/codex-reviewer.md:86` launches `"$RL" start codex-review "$SPEC" 600`. There is no arg 4, so it is always
  `gpt-5.6-sol`. The agent descriptions hard-code "GPT-5.6 Sol" too (`codex-reviewer.md:3,10`).
- The user-global `~/.codex/config.toml:2` is `model = "gpt-6-astra"`. The explicit CLI `--model` wins, so the
  config is irrelevant for plugin lanes.
- Installed plugin: 1.21.0 (2026-08-12), sha `78f9cb5`, project-scoped for both repos
  (`~/.claude/plugins/installed_plugins.json`). The upstream marketplace repo is reported 404
  (`fable-orchestrator-removal-decision-2026-09-22.md:15`), so no update will ever change the default.
- Our own lanes: `codex-sol-*` pin `--model gpt-5.6-sol` (`.claude/agents/codex-sol-*.md`, e.g.
  adversarial-critic `:105`, advisor `:105`, claude-code-expert `:116`, operator `:69`, staleness-auditor `:82`),
  and `.claude/token-routing.md:17` documents sol = `gpt-5.6-sol`. `gpt-6-sol` is ruled but not done.

### Can 0.154.0 even use gpt-6-sol? No. It is not in its catalog.

`codex debug models` (free, no model call):
- native 0.156.1 → `gpt-6-astra gpt-6-sol gpt-6-luna gpt-reserve gpt-5.6-sol gpt-5.6-terra gpt-5.6-luna gpt-5.5
  codex-auto-review`
- npm 0.154.0 → `gpt-6-astra gpt-reserve gpt-5.6-sol gpt-5.6-terra gpt-5.6-luna gpt-5.5 codex-auto-review`
  (no `gpt-6-sol`, no `gpt-6-luna`)

The arms discriminate: both lists carry `gpt-6-astra`, both return rc=0, and neither lists the nonexistent
`gpt-6-terra`. So `gpt-6-sol` requires native 0.156.x.

**Whether `--model gpt-6-sol` actually RUNS on 0.156.1 is UNVERIFIED.** "Listed" is not "runnable"
(`claudex-loop-full-research-2026-09-22.md:135`). The live arm is the Phase 11 step-2a item "live-arm `-m gpt-6-sol`
on 0.156.1 (fail arm: 0.154.0)" (`task_plan.md:689`). It was not run here, per the brief.

## Q3 — smallest changes to stop it NOW (without waiting for Phase 10 step 0)

Ordered cheapest first. None was applied: this lane is read-only.

1. **Commit the §1c rewrite that is already in the working tree, but fix its launch form first.**
   The uncommitted line says an Anthropic-authored diff "gets an OpenAI codex review launched with
   `mise exec -- codex exec review`". Taken literally it has three defects:
   - (a) **No sandbox pin.** `codex exec review` has no `-s` flag after the subcommand (`--help` on 0.156.1). The
     user config default is `sandbox_mode = "danger-full-access"`
     (`codex-exec-review-settings-2026-09-23.md:33,60`). A bare `codex exec review` is therefore LESS safe than the
     plugin, which at least pins `-c 'sandbox_mode="read-only"'` (`run-lane.sh:113`).
   - (b) The read-only allow-rule hole (git commit via user allow rules, arm D) is unmeasured. The write-canary is
     **#1297 (OPEN)**.
   - (c) No model. It inherits `gpt-6-astra`, not the ruled `gpt-6-sol`. That is acceptable for a cross-family lens
     but should be stated.

   Recommended interim text: the "recommended production form" already researched
   (`codex-exec-review-settings-2026-09-23.md:157-163`):

   ```bash
   mise exec -- codex exec -s read-only --ignore-rules review --commit <SHA> \
     -c 'sandbox_mode="read-only"' -c 'review_model="<model>"' \
     -c 'model_reasoning_effort="xhigh"' --json -o <final.txt>
   ```

   Label it "pending #1297". A range review (`A..B`) needs `--base <branch>`, or custom instructions with no target
   flag. The target flags are mutually exclusive with a PROMPT (`run-lane.sh:24-27`).
   - PRO: one line in two mirrored files; it fixes the actual route used; it is native 0.156.1 through `mise exec`.
   - CON: until #1297 runs, read-only rests on research, not a canary. It is a hand-typed argv in a skill (the
     class `ai-cli-invocation.md` warns against). And "the `exec review` MECHANISM is a ticket after step 2"
     (`task_plan.md:459-461`), so this runs slightly ahead of that ticket.
   - Gate: `mise run lint-docs`, plus whatever contract binds the §1c table.

2. **Add the missing lane-table row to `.claude/CLAUDE.md:64-71`: "Cold review of a Claude-authored diff".**
   It would name the same native form, or `cold-reviewer` with the "degraded, same-family" caveat, and explicitly
   say "not `fable-orchestrator:codex-reviewer`". This closes R2's gap for EVERY route, not just `/session-handoff`.
   Because the trigger at `:45` says the plugin skill is "authoritative", the row must say it overrides the skill's
   review tier.
   - PRO: fixes the class (any orchestrated review), not the instance.
   - CON: `.claude/CLAUDE.md` is rule-synced with KB for its trigger lines only. A new table row is not in
     `[shared].lines`, so it causes no cross-repo break, but KB keeps the gap. The file has an agnix/eager budget
     (`md_size_budget`).

3. **Deny the plugin's codex agents at the permission layer.** Add `"Agent(fable-orchestrator:codex-reviewer)"`
   and `"Agent(fable-orchestrator:codex-implementer)"` to `.claude/settings.json` `permissions.deny`. The syntax is
   documented: `$CC/sub-agents.md:689-702` ("`Agent(subagent-name)` … works for both built-in and custom
   subagents").
   - PRO: a hard, deterministic stop that fails closed. It leaves the plugin enabled, so R7's contracts and
     rule-sync stay green. premise-verifier and fable-advisor (Claude models, not affected) stay available.
   - CON: **it is UNVERIFIED that a plugin-namespaced type matches.** The docs example uses bare names. It needs
     both arms: denied on `fable-orchestrator:codex-reviewer`, allowed on `cold-reviewer`. A deny with no redirect is
     an outage unless item 1/2 names the replacement (`mise-tasks-only.md`: "a guard whose redirect target cannot
     perform the redirected action is … an outage"). It also does nothing for KB R8. KB would need its own deny,
     and KB's `kb-tool-review.js:188` would then fail hard; that is honest, but it is a behaviour change there.

4. **Restart the Claude session** (or `/clear` into a new process). This gives a new shell snapshot. The plugin's
   bare `codex` would then resolve 0.156.1 (inferred from the `env -i` arm).
   - PRO: zero edits; also fixes any other bare-`codex` caller in this session.
   - CON: fixes the BINARY only. The model stays `gpt-5.6-sol` (hard-coded). It does not stop the routing. The next
     stale snapshot (any future host tool move) re-creates the problem.

5. **Pass arg 4 or edit the plugin cache.** Rejected. The plugin agent never passes arg 4. Editing
   `~/.claude/plugins/cache/…/run-lane.sh` is unreviewed, outside the repo gates, overwritten on reinstall, and is
   work on a component that is being deleted. The removal decision (`:26`) already dropped "model via run-lane
   arg 4".

6. **Alternative non-plugin lanes, and what each costs.**
   - `codex-sol-adversarial-critic` / `codex-astra-adversarial-critic`
     - Pros: in-repo; already on `mise exec -- codex exec` → 0.156.1 (`86324c6a`); `--sandbox read-only`.
     - Cons: it is designed to attack a PROPOSAL, not to review a diff. The sol variant is still on `gpt-5.6-sol`.
       The astra variant (`gpt-6-astra`) is the one that is current today.
   - `mise run sdlc-team` with `mode: review`
     - Pros: the ruled single entry point.
     - Con 1: `review` is "ASKED not to write, not PREVENTED" (full access by design, `sdlc_team.py:747-757`).
     - Con 2: **a latent defect, found here.** `sdlc_team.py:724` does `shutil.which("codex")` and `:781` then
       builds `str(Path(codex).resolve())`. On any post-native PATH, `which` returns the mise shim, a symlink →
       `~/.local/bin/mise`. `resolve()` turns argv[0] into **`mise`**, so the launch becomes
       `mise exec -c 'model_reasoning_effort=…' -C <workdir> -o <out> -`. mise parses `-c` as "Command string to
       execute through a shell" (`mise exec --help`), and codex never runs.
     - Arms for Con 2: under `mise exec -- python3`, `which` → shim, and resolve → `/Users/rmanaloto/.local/bin/mise`.
       The control arm, on this session's stale PATH: `which` → the npm dir, resolve → `…/@openai/codex/bin/codex.js`,
       which works but is 0.154.0. So today sdlc-team runs either OLD codex (stale PATH) or NOT codex at all
       (fresh PATH).
     - Con 2 was not run end-to-end: that would dispatch a lane. It needs an issue plus a test before sdlc-team is
       relied on. An issue search (`gh api search/issues … sdlc_team shim`) found no existing issue; the control
       query `sdlc-team` returned 27 hits.
   - `cold-reviewer` (Opus): works, but for a Claude-authored diff it is same-family. `.claude/CLAUDE.md:84-85`
     already calls that "degraded, announce it".
   - `mise run codex-lane`: bare `CODEX_BIN = "codex"` (`codex_lane.py:113`), `--sandbox read-only`,
     `--output-schema`, optional `--model`. It shells through the shim, so it avoids the resolve bug. But it is the
     DAG-node verdict producer (#613) and needs a node; it is not a general diff review.

   **Recommendation:** do 1 (with the corrected argv) + 2 now. Add 3 only after its two-arm probe. Do 4 anyway at
   the handoff `/clear`, since it happens for free. File the sdlc_team resolve bug. Run #1297 and the `-m gpt-6-sol`
   live arm as the first two items of the Phase 11 step-2a remainder, since both gate the replacement lane.

## Q4 — disable the plugin immediately, or at step 0? What depends on it

**Recommendation: do NOT flip `enabled: false` in isolation now. Stop the ROUTES now (Q3 items 1-3). Resolve the
ordering conflict by asking Ray.** Reasons:

- **Contracts go red immediately.** `orchestration.plugins-enabled` requires the `true` token
  (`suites.toml:2429-2437`). `orchestration.trigger-armed` and `mode-line-declared` (`:2391-2411`) would keep
  passing while describing a flow that can no longer run. That is exactly the state `plugins-enabled` exists to
  catch. Tests would also need changing: `tests/test_rule_sync.py:27-28` and `tests/test_verify.py:180,184`.
- **Cross-repo red.** `rule-sync.toml:28-31` `[shared].plugins` requires the plugin enabled in BOTH repos. The
  rule-sync gate hard-FAILs in CI (#354 tier 0; `verify-before-advancing.md`), and dotfiles CI checks out KB main.
  A dotfiles-only disable fails that gate, and the KB-first ordering is what the removal decision's §4 PR sequence
  exists to handle.
- **The eager trigger would dangle.** `.claude/CLAUDE.md:45` (and KB `:31`) would tell every session to invoke a
  skill that no longer exists. `premise-verifier` (`:69`) and the `fable-advisor` fallbacks (R5) would dangle too,
  and their in-repo replacements (D1, D2 `claude-advisor`) do not exist yet.
- **KB runtime:** `kb-tool-review.js:188` hard-dispatches `fable-orchestrator:codex-reviewer`. A KB-side disable
  breaks that workflow until K1 lands.
- **What does NOT depend on it:**
  - dotfiles saved workflows (in-repo agentTypes only);
  - our `codex-sol-implementer` (the premise-gate hook never matched it, `premise-gate.sh:132-133`);
  - `codex_lane.py`, which deliberately does not call `run-lane.sh` (`codex_lane.py:12-29`);
  - the eval `--live` doctor, which points at a 1.14.0 path and can only skip (`eval_cases.py:54-57`,
    removal decision D7).
- **Everything a disable needs is already specified:** D1-D8 / K1-K8 and the 5-PR sequence
  (`fable-orchestrator-removal-decision-2026-09-22.md:29-61`), as #1310/#1311-#1319/KB#793-#797. "Disable now" is
  just steps 1-5 of that sequence, compressed.

**The decision Ray has to make:** the ruling says removal runs "FIRST — before any step that would trigger codex
work or agents" (`task_plan.md:432-433,490`), but Phase 11 (codex step-2a, codex class fix, #1351) was put ahead of
it (`:511,762`).
- Option A (recommended): keep Phase 11 first, and land Q3 items 1-2 (+3 once armed) as a small docs/config PR now.
  That honours the INTENT of the "first" ruling (no codex work routed through the plugin) at a fraction of the cost.
  - PRO: small change; no cross-repo churn.
  - CON: the plugin stays installed, and KB R8 stays live.
- Option B: pull Phase 10 step 0 ahead of Phase 11 `/implement`.
  - PRO: matches the ruling's letter.
  - CON: 5 PRs across 2 repos before the "asap" codex step-2a (Ray, `task_plan.md:759`).

This lane cannot ask. The coordinator should put A/B to Ray with `AskUserQuestion`.

## Side findings (for `task_plan.md`)

- S-1 (HIGH, latent): the `sdlc_team.py:724,781` shim-resolve bug in Q3 item 6. Class: any
  `Path(shutil.which(x)).resolve()` over a mise shim. A grep of `python/src` found no other `which("codex")` site.
- S-2 (MED): the §1c working-tree rewrite as written launches `codex exec review` with no sandbox pin under a
  `danger-full-access` user default (Q3 item 1a). Fix it before committing.
- S-3 (LOW): `.claude/CLAUDE.md:89-90` ("GPT-5.6 Sol") and `.claude/token-routing.md:17` are accurate today and
  go stale at step 2b. Put them on the step-2b PR's doc-sync list.
- S-4: KB `.claude/CLAUDE.md:31-34` and `kb-tool-review.js:188` share R2 and R8. Any Q3 fix in dotfiles leaves KB
  exposed.

## GitHub repos touched

- [ray-manaloto/dotfiles](https://github.com/ray-manaloto/dotfiles): source, config, plan, prior reports; issue
  state for #1297, #1310-#1313 and #1319; issue search for the sdlc_team bug.
- [ray-manaloto/knowledge-base](https://github.com/ray-manaloto/knowledge-base): live plugin references
  (`kb-tool-review.js:188`, `.claude/CLAUDE.md:31-34`, `settings.json:195`) and offline Claude Code docs
  (`sources/agent-harness-docs/docs/claude-code/{sub-agents,permissions}.md`) for `Agent()` deny syntax.
- [mar3co/fable-orchestrator](https://github.com/mar3co/fable-orchestrator): read from the installed cache 1.21.0
  (`scripts/run-lane.sh`, `agents/codex-reviewer.md`, `skills/orchestration/SKILL.md`, `hooks/hooks.json`,
  `scripts/premise-gate.sh`, `CHANGELOG.md`). No network fetch.
